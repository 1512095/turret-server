# 砲塔遠端對戰伺服器（0.1.59）

## 目前狀態

遊戲已加入房間碼與隨機配對入口。這份伺服器尚未部署，因此還沒有公開網址；部署完成後兩位玩家填入同一網址才可跨網路對戰。APK 與伺服器版本必須一致。

## 用 Render 部署

1. 解壓縮此資料夾，在 GitHub 建立一個新專案（repository）。
2. 將 server.py、requirements.txt、Dockerfile、render.yaml 上傳到該專案根目錄。只需要這些伺服器檔案，不必上傳遊戲或音樂。
3. 登入 Render：https://dashboard.render.com/ 。點 New → Web Service，連接剛建立的 GitHub 專案。
4. Language 選 Python 3。
5. Build Command 填：`pip install -r requirements.txt`
6. Start Command 填：`python server.py`
7. Health Check Path 填：`/health`。保持單一執行個體、單一程序；目前房間資料保存在該程序記憶體中，不要開多 worker。
8. 方案與費用依平台當時顯示選擇。點 Create Web Service，等待部署成功。
9. 取得網址，例如 https://你的名稱.onrender.com 。瀏覽 /health 應顯示 ok 為 true。
10. 遊戲內填入 `wss://你的名稱.onrender.com/ws`。注意開頭改成 wss，結尾加 /ws。

官方操作說明：https://render.com/docs/web-services
WebSocket 說明：https://render.com/docs/websocket

## 兩人如何玩

1. 雙方都安裝 0.1.59。
2. 在工廠各自選好「我方」一至三輛坦克，點下方「遠端對戰」。
3. 填入相同伺服器網址。
4. 指定朋友：一人按「建立房間」，把六位碼給另一人，另一人輸入後按「加入房間」。
5. 隨機對戰：雙方按「隨機配對」，找到另一位等待玩家後自動開戰；不會以人機假裝真人。
6. 各自製造技能、獻祭、裝載技能與指定目標。雙方按「準備完成」後統一演出射擊。
7. 結算後雙方按「再來一次」才會重開；有人返回工廠或斷線時，另一人收到提示。
8. 連線模式要移回已裝載技能時，使用「移回儲存間」按鈕，等資料同步後再從技能欄拖曳裝載。

## 自己電腦／區域網路啟動

安裝 Python 3.12 後，在本資料夾執行：

```
python -m pip install -r requirements.txt
python server.py
```

同一區域網路可使用 `ws://電腦區域網路IP:8080/ws`，電腦需允許防火牆入站。這不是跨網路公開部署；手機不要填 localhost，因為那會指向手機自己。

## 此版本範圍

- 伺服器負責房間碼、配對與訊息轉送；玩家一裝置負責戰鬥判定與獻祭抽卡，另一台同步權威資料。
- 有版本檢查、房間人數限制、訊息大小限制、速率限制與連線心跳。
- 未加入帳號、排名、跨伺服器配對、斷線續局或房主轉移。任一方離線結束該場連線。
- 公開競技營運前，仍應將戰鬥權威移到伺服器，避免房主修改遊戲數據。
- 目前完成程式與匯出，尚未以兩台手機、公開伺服器實測。
- 伺服器重啟會清空房間與等待配對清單。
