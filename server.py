"""Two-player room-code relay and FIFO random matchmaking. Game authority is player 1."""
import asyncio, json, os, secrets, string, time
from aiohttp import web, WSMsgType

ROOMS = {}
WAITING = []
CLIENTS = {}
VERSION = "0.1.59"
MAX_CLIENTS = int(os.getenv("MAX_CLIENTS", "300"))

async def send(ws, data):
    if not ws.closed:
        try: await ws.send_json(data)
        except (ConnectionError, RuntimeError): pass

def roster(value):
    return isinstance(value,list) and 1 <= len(value) <= 3 and all(type(x) is int and 0 <= x < 7 for x in value) and len(set(value)) == len(value)

async def leave(ws):
    if ws in WAITING: WAITING.remove(ws)
    info = CLIENTS.get(ws,{})
    code = info.pop("room", None)
    room = ROOMS.pop(code, None)
    if room:
        for peer in room["players"]:
            if peer is not ws:
                CLIENTS.get(peer,{}).pop("room",None)
                await send(peer,{"kind":"peer_left","message":"對手已離線，請返回工廠重新連線。"})

async def pair(code, first, second):
    ROOMS[code] = {"players":[first,second],"created":time.monotonic(),"active":True}
    for peer in [first,second]: CLIENTS[peer]["room"] = code
    for role,peer in enumerate([first,second]):
        await send(peer,{"kind":"matched","role":role,"code":code,"rosters":[CLIENTS[first]["roster"],CLIENTS[second]["roster"]]})

async def websocket(request):
    if len(CLIENTS) >= MAX_CLIENTS: raise web.HTTPServiceUnavailable()
    ws = web.WebSocketResponse(heartbeat=20,receive_timeout=90,max_msg_size=524288)
    await ws.prepare(request)
    CLIENTS[ws] = {"window":time.monotonic(),"count":0,"lobby":0}
    try:
        async for message in ws:
            if message.type != WSMsgType.TEXT: continue
            info = CLIENTS[ws]
            now = time.monotonic()
            if now-info["window"] >= 1:
                info.update(window=now,count=0,lobby=0)
            info["count"] += 1
            if info["count"] > 100:
                await ws.close(code=1008,message=b"Rate limit")
                break
            try: data = json.loads(message.data)
            except (ValueError,TypeError): continue
            if not isinstance(data,dict): continue
            kind = data.get("kind")
            if kind in ("create","join","random"):
                info["lobby"] += 1
                if info["lobby"] > 3: continue
                if data.get("version") != VERSION:
                    await send(ws,{"kind":"error","message":"版本不一致，請雙方更新至相同版本。"}); continue
                if not roster(data.get("roster")):
                    await send(ws,{"kind":"error","message":"請先選擇一至三輛不同坦克。"}); continue
                await leave(ws)
                info["roster"] = data["roster"]
                if kind == "create":
                    code = "".join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(6))
                    while code in ROOMS: code = secrets.token_hex(3).upper()
                    ROOMS[code] = {"players":[ws],"created":now,"active":False}
                    info["room"] = code
                    await send(ws,{"kind":"created","code":code})
                elif kind == "join":
                    code = str(data.get("code", "")).strip().upper()
                    room = ROOMS.get(code)
                    if not room or room["active"] or room["players"][0].closed:
                        await send(ws,{"kind":"error","message":"房間不存在、已滿或已失效。"}); continue
                    await pair(code,room["players"][0],ws)
                else:
                    while WAITING and WAITING[0].closed: WAITING.pop(0)
                    if WAITING:
                        peer = WAITING.pop(0)
                        code = secrets.token_hex(3).upper()
                        await pair(code,peer,ws)
                    else:
                        WAITING.append(ws)
                        await send(ws,{"kind":"queued","message":"正在尋找對手，可取消配對。"})
            elif kind == "leave": await leave(ws)
            elif kind in ("command","state","event","shop","shop_done","restart_vote"):
                room = ROOMS.get(info.get("room"))
                if not room or not room["active"]: continue
                role = room["players"].index(ws)
                if kind in ("state","event","shop","shop_done") and role != 0: continue
                if kind == "command" and role != 1: continue
                if not isinstance(data.get("payload"),str) or len(data["payload"]) > 500000: continue
                await send(room["players"][1-role],data)
    finally:
        await leave(ws)
        CLIENTS.pop(ws,None)
    return ws

async def health(request):
    return web.json_response({"ok":True,"version":VERSION})

async def cleanup(app):
    while True:
        await asyncio.sleep(30)
        for code,room in list(ROOMS.items()):
            if not room["active"] and time.monotonic()-room["created"] > 900:
                for peer in list(room["players"]):
                    await send(peer,{"kind":"peer_left","message":"等待房間已逾時，請重新建立。"})
                    await leave(peer)

async def lifecycle(app):
    task = asyncio.create_task(cleanup(app))
    yield
    task.cancel()
    for ws in list(CLIENTS): await ws.close()

app = web.Application()
app.add_routes([web.get("/health",health),web.get("/ws",websocket)])
app.cleanup_ctx.append(lifecycle)
if __name__ == "__main__": web.run_app(app,host="0.0.0.0",port=int(os.getenv("PORT","8080")))
