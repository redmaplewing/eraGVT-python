# 通關繼承（S37）

原作主體：`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION`；
下列未重複寫路徑的行號均指此函式。實作：`src/eragvt/game/succession.py`。

## 入口與選單

- `ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING:3–69`：通關後評分、可選存檔，
  再將設施金額加回 MONEY 後跳入 SUCCESSION。讀取通關存檔由
  `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTLOAD:13–14` 走相同入口。
- :16–29 清 FLAG:64、計算女兒數，按角色順序解除變身；:31–268 計算周回點。
  周回累計、模式、評價、稱號及 ENDLESS 擊破獎勵先乘周回倍率；實績點除10截斷後加入，
  最後取 GLOBAL:115 與本次點數最大值。此處不寫 GLOBAL:115、不 SAVEGLOBAL。
- :316–320 先把 FLAG:901–910 複製到 LOCAL，再立刻 VARSET LOCAL，故三頁選項初始全部未選。
  第1頁角色／性成長／女兒／等級／戰技／資金／基礎值／防衛力／碎片研究／衣裝／魅了；
  第2頁周回加成及互斥選項；第3頁人氣重置。點數不足輸入不得改資料。
- :674–747 資金選項5扣16點，但切到其他比例或清除時部分分支退 `5*4=20` 點；照原作保留。
  :442 的振り解く強化灰色門檻為1點，但 :919 真正購買門檻為4點；人氣重置免費卻在少於8點時灰色。
- :1017–1041 無選角時再次確認；模式選單可返回繼承選擇。
  `ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:297–407` 的 SANDBOX 可見但禁選；
  選超過1角色時 SOLO 同樣禁選。其他模式依原文 FLAG:0 位元組合。
- 角色選擇 :560 只有上界檢查，輸入負數會索引不存在角色；Python 明確停止，未另造負索引角色。

## 重置與保留

- :1043–1096 只清列出的 DAY、TIME、FLAG 區間；DAY:2、FLAG:8／854／999 與其他未列欄位保留。
  FLAG:50–53 可留設施，FLAG:54 可留研究；重建7個ボス及1個Ｋ触手。
- :1104–1373 對 CFLAG:0=999 角色逐欄處理；性成長、等級、戰技、衣裝、魅了各有獨立區間。
  性成長不保留會清 CFLAG:200–238，因此即使購買女兒繼承，女兒身分231仍會被清。
  EXP:58 不保留時原作讀的是 **CSVCFLAG_F**，保留時100以上僅留四分之一，照原作保留。
- :1263–1265 女體受容的 SWAP 沒寫角色索引，實際交換 TARGET 的男性苦手／女性苦手，
  並非正在重置的 CCOUNT。TS 身體資料沿用既有 GENERATE_CHAR_SIZE，含 RESULT:0–7。
- :1374–1399 未選角色透過相鄰 SWAPCHARA 移到末尾，同步逐角色交換 RELATION 欄，
  再清雙向末欄並刪除。:1383 寫的是 `LOCAL == MASTER`，不是 CCOUNT:2；
  前一個汎用角色沒有性格而 LOCAL=0 時，後續所有 RELATION 交換都會跳過，照原作保留。
- :1401–1442 資金加1000；保留設施時先扣先前設施退款；防衛力5000加購買值。
  不留衣裝只清 ITEM:101–199、301–399、401–699，邊界100／200／300／400保留。
  PALAM、TCVARn、TFLAG、RESULTS 等未列清除項目，不額外清空。

## 續行與必要依賴

- :1444–1490 決定人數並補汎用角色，GLOBAL:100–102 有通關數時提供增減人數選單；
  SOLO 固定1人，其他模式預設至少3人。:1491–1550 扣已用修練P、下限0，再加基礎值獎勵。
- :1560 `CHARA_MAKE_MAIN, LOCAL:16` 沿用既有預設 [1000] 路徑。
  `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:145、203` 僅手動編輯傳 ARG；
  :206–209 預設完成直接呼叫 CHARA_MAKE_FINALIZE，不讀 ARG。獎勵已在 SUCCESSION 加入 JUEL，
  因此預設路徑不需新增參數，也不改選初期セット。
- :1563–1622 設口上號、恢復結界、MESSAGE_FIRST（使用現有可等待的口上呼叫）、前排名單、
  衣裝所持品、HEROINE_PRESET 設定選單、探索目標及 FLASHNEWS 文字；FLAG:64=-1 後 BEGIN SHOP。
  必須立即終止舊 TURNEND；EVENTSHOP 把繼承標記清0並進第1天白天，再依引擎規則自動存檔。
- 天使の樹仍為後續獨立系統；選 HARDCORE 可能在後續周回遇到既有停止點，不繞過。

## 引擎查證

- 角色交換／刪除：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1061–1066、1165–1174`，
  只改角色清單，不自動改 TARGET／ASSI／RELATION。
- CSV 查詢：同檔 :1383–1419，BASE 取模板 Maxbase、未定義欄位0；
  `ERB/汎用関数/コモン関数.ERB@CSVBASE_F:966–969` 等包裝先改 RESULT:0 再 RETURNF。
- FOR 半開區間：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1731–1743`。
- 普通函式終端將 RESULT:0 寫0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`；
  多值 RESULT 只覆寫傳回格數：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740`。
- BEGIN SHOP：`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:614–640` 進 EVENTSHOP，
  不 RESETDATA；calledWhenNormal 為真時自動存檔。
- SAVEGAME 返回：同檔 :865–869、926–934；RESULTS 不存而 RESULT 存：
  `reference/emuera-1824/Emuera/GameData/Variable/VariableCode.cs:44、94、105、110`，寫出範圍見同目錄 `VariableData.cs:663–674`，沿用既有存檔模型。

## 驗證

- 新增36個 table-driven／生成器測試；點數倍率、實績門檻、各頁無效輸入、退款怪處、娘取消、
  SOLO限制、CSV精確區間、資金設施、道具邊界、RELATION移位及LOCAL殘值、TS省略索引均有原文 expected。
- 既有末王整合改為通關→SAVEGAME→讀檔繼承→SHOP；末王已擊破前置與致死傷害為**人工狀態**，
  不冒充自然通關模擬。另直接測試保留角色繼承並補新角到預設人數。
- 完整pytest：2211 passed, 1 warning；標準500局default246上限／4回標題、tokusou250上限，catalog失敗0。
  10批exit0、seed全集及log／JSONL一致均核對，產物 `tmp/s37/`。無新增 UNVERIFIED／DEVIATION。
