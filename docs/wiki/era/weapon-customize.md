# 武器自訂（S49）

## 入口與角色資料

- `ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE3.ERB@CMD_STATUS_CHARA_SELECT_PAGE3:39–46`：
  狀態畫面 P3 [0]，僅角色 `CFLAG:0=0` 且 `FLAG:700=0` 可進入；處理成功回傳 1。
- `ERB/武器と衣装/武器カスタマイズ関連/WEAPON_CUSTOMIZE.ERB@WEAPON_CUSTOMIZE:8–80`：
  近／中／遠距離各提供名稱 [10／20／30]、風格 [12／22／32]；[999] 返回。
- `@SETTING_WEAPON_NAME:85–206`：手動名稱直接寫 `CSTR:5／6／7`，空白與空字串也照存；
  隨機選定後寫入；刪除清空；複製另距離時一併複製 `CDFLAG:距離:300`（武器名元位置），並立即返回。
- `@SETTING_FSTYLE:209–259`：0–10 全部可選，直接寫 `CDFLAG:距離:500`（戰鬥風格）；
  不扣錢、不扣碎片、不要求等級；999 取消，其他值重問。
- 資料索引：`CSV/Cdflag2.csv:70、73`。既有存檔已保存 CSTR／CDFLAG，無需改版本。
- 戰鬥實際透過 `game.battle.core.fstyle_name` 讀取同一格，`game.battle.hantei.fstyle_attack` 與各風格判定立即生效。

## 顯示威力與戰鬥威力

- `ERB/武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB@FSTYLE_ATTACK:42–111`：
  第三參數大於 0 時，先把 `CFLAG:53–56` 加入攻擊／防禦／敏捷／知性，再套衣裝、體型及風格公式。
- `WEAPON_CUSTOMIZE:25、42、59` 無條件傳第三參數 1，與一般戰鬥呼叫預設 0 不同。
  Python 增加選用參數，既有戰鬥呼叫維持預設值；顯示與戰鬥用同一算法，未更改其他規則。
- `FIGHT_STYLE.ERB@SET_FSTYLE_INFO:118–164` 寫共用 `RESULTS:0–2`；畫面等待時保留遠距離說明。

## 隨機名稱與保留欄

- `ERB/武器と衣装/武器カスタマイズ関連/WEAPON_NAME.ERB@GENERATE_WEAPON_STRS:4–139`：
  每輪 20 個候選；片假名／和名／混合、再生成、10 格保留／刪除、選定後 WAIT 與取消。
  保留欄滿後往前移一格；保留欄與計數是靜態暫存，重入保留但不存檔。
- 片假名：`GENERATE_WEAPON_STR.ERB@GENERATE_WEAPON_STR:2–2089`，兩或三個片段由語尾往前組成；
  保留候選遍歷順序、各音禁則、長度重試、相鄰音修正，以及已選中後仍消耗的 RAND。
- 和名：`GENERATE_WEAPON_STR_JP.ERB@GENERATE_WEAPON_STR_JP:57–3566`，依位置與類別挑選兩個詞，
  再依訓／音讀組合與原作重試機率取得讀音；濁音、數詞及別字的特殊處理均手翻。
- 附加詞：`GENERATE_ADD_STR.ERB@GENERATE_ADD_STR:7–364`，依風格、屬性、攻擊種類與武器種類挑選；
  保留權重、重複字重試、尾字篩選及注入 RNG 的呼叫順序。
- `tools/extract_weapon_customize.py` 只抽取固定文字與詞庫，沒有執行 ERB；
  原文有效候選總數與抽取數均為片假名 167、和名 205，另有 47 個附加詞群。
  `weapon_customize_text.py` 每個片段／和名詞條均附來源行號，註解中的範例不計入。

## 附加文字與元位置

- `WEAPON_NAME.ERB@WEAPON_ADD_STRS:141–527`：讀音顯示、前／後綴、分隔、引號、屬性、
  21 種武器種類（含自由輸入）與五種攻擊屬性；生成十個候選，可再生成或返回設定。
- 切換武器種類時照原表重設攻擊屬性；設定參數及自由輸入是靜態暫存。
  `LOCAL／LOCALS` 亦保留，只清原作明確清除的格；未顯示但被原碼接受的數值也照原樣處理。
- `:487–499` 元位置是「前綴 CP932 長度 × 100 ＋ 名稱本體 CP932 長度」。
  重入時依元位置取得原名，拆出 ` <讀音>`，不把上次前後綴再次加入。
- CLEARLINE 使用現有輸出層；設定與輸入回顯合計 27 行，生成區合計 15 行，改設定清 42 行。
  測試驗證連續重繪不增加行數、不刪前一畫面。

## 保留的原作行為

- 取消隨機命名也清除武器名元位置（`WEAPON_CUSTOMIZE:139–148`）；名稱本身保持原值。
- 直接輸入 50–59 可以選空保留欄；選定回傳成功並取得空名稱（`WEAPON_NAME:110–118`）。
- 和名同類排斥的 OR 條件照原式，純名詞／熟語也受排斥；不依註解自行修正。
- 附加設定某些灰色或未顯示值仍可手動輸入，照原作接受，不增設驗證。
- 附加文字的取消不改角色；生成時仍依原作抽附加詞，即使選「無附加」也消耗亂數。

## 引擎查證與驗收

- `reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`：INPUT／INPUTS 各只寫 RESULT:0／RESULTS:0。
- `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734`：WAIT／PRINTW 等按鍵，不寫輸入結果。
- `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023`：RETURN 只改指定結果格。
- `reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–554`：AND／OR 由左往右短路，
  未走到的 RAND 不消耗亂數；生成器按此順序手翻並用固定 RNG 驗證。
- `reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27`、
  `reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:328–333、514–520`：靜態變數及 LOCAL／LOCALS 按函式保留。
- `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:522–536`：SPLIT 包含空項；RESULT 寫完整數量，
  超出輸出容量時只複製前面部分，不報錯。
- `reference/emuera-1824/Emuera/_Library/LangManager.cs:17–20、40–85`：CP932 長度及 SUBSTRING 位移按 UTF-16 字元累計，
  半個全形位移向右取整；本機 .NET CP932 驗證 U+1F600 整串長 2、高代理單獨長 1，測試覆蓋代理字元邊界。
- 測試包含三距離／11 種風格、無效值／取消、命名與複製、保留欄、附加格式／種類、元位置重入、
  RNG 順序與重試、CP932／UTF-16、實際 Web 與存讀檔；無新增 UNVERIFIED／DEVIATION。
