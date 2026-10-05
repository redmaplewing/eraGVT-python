# 主流程與呼叫鏈

起點：`ERB/※ゲーム開始からのフロー.txt`（原作者寫的概略）。本頁以實際 ERB 驗證並補上函式名。
路徑一律相對 `source/earGVP/ERB/`。

注意：`ERB/` 直下的 `SHOP*.ERB`（`SHOP.ERB`、`SHOP_TURNEND.ERB` 等 7 個）都只有 5 行註解，
說明檔案已移到 `インターミッション画面/`，**不是**實作。

## 0. Emuera 階段（BEGIN）與事件函式

以下全部對照引擎原始碼 `reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs`（下稱 SystemProc）確認。
原作沒有自訂 `@SYSTEM_TITLE`，標題畫面用 Emuera 預設（SystemProc@beginTitle:133–188：GameBase.csv 的タイトル／
バージョン（`0.408`）／作者／(製作年)／追加情報，選項 `[0] 最初からはじめる`、`[1] ロードしてはじめる`）。

| 階段 | 引擎呼叫的事件函式（依序） | 原作位置 |
|---|---|---|
| 新遊戲 | `ResetData` → 依**檔名番號**加入角色 0（Chara000）→ 加入「最初からいるキャラ」999 → `@EVENTFIRST`（SystemProc@endOpenning:197–209、@beginFirst:233–242） | `ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`（:19） |
| LOADGAME 後 | `@SYSTEM_LOADEND`（無）→ `@EVENTLOAD` → 沒有 BEGIN 就直接 `@SHOW_SHOP`（**不**呼叫 EVENTSHOP、不自動存檔）（@beginDataLoaded:757–780） | `オープニング処理.ERB@EVENTLOAD`（:4） |
| SHOP | `@EVENTSHOP` → 自動存檔（`オートセーブを行なう:YES` 且 BEGIN SHOP 是在一般狀態下呼叫時；99 號、`@SAVEINFO` 產生說明）→ 迴圈 {`@SHOW_SHOP` → 輸入 → `@USERSHOP`}（@beginShop:614–628、@endCallEventShop:630–640、@beginAutoSave:642–654、@endAutoSave:670–680、@shopWaitInput:691–735） | `インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP`（:141）、`SHOP.ERB@SHOW_SHOP`（:5）、`@USERSHOP`（:192） |
| TRAIN（戰鬥） | `UpdateInBeginTrain`（TFLAG/TSTR 清零）→ `@EVENTTRAIN` →（NEXTCOM）→ 迴圈 {`@SHOW_STATUS` → 對 Train.csv 每個指令 `@COM_ABLEn` → `@SHOW_USERCOM` → 輸入}（@beginTrain:249–264、@endCallEventTrain:266–293、@endCallComAbleXX:314–370） | `ゲーム内_戦闘処理/BATTLE_TRAIN.ERB@EVENTTRAIN`（:4）、`BATTLE_SHOW_STATUS.ERB@SHOW_STATUS`（:3）、`BATTLE_COM.ERB@SHOW_USERCOM`（:4） |
| TRAIN 輸入 | 輸入值是「有名稱且 COM_ABLE 非 0」的指令番號 → 直接 DOTRAIN；否則 `RESULT = 輸入值` → `@USERCOM`（@trainWaitInput:395–427） | `BATTLE_COM.ERB@USERCOM`（:572） |
| DOTRAIN n | `@EVENTCOM` → `@COMn` → **`RESULT != 0` 時**才 `@SOURCE_CHECK` → SOURCE 清空 → `@EVENTCOMEND`（@doTrain:430–485） | `BATTLE_COM.ERB@EVENTCOM`（:666）、`戦闘コマンド(ヒロイン)/COMF*.ERB@COMn`、`BATTLE_COM_AFTER.ERB@SOURCE_CHECK`（:2）、`BATTLE_COM.ERB@EVENTCOMEND`（:685） |
| AFTERTRAIN | `@EVENTEND`（@beginAfterTrain:524–534） | `ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND`（:2），結尾 `BEGIN TURNEND`（:536） |
| TURNEND | `@EVENTTURNEND`（@beginTurnend:602–612）。**沒有 BEGIN 就結束會是錯誤**「予期しないスクリプト終端」（@endNormal:993–996），不會自動進 SHOP | `インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`（:3） |

- `@EVENTSHOP` 執行中呼叫的 BEGIN 會被延後到自動存檔之後才生效（`GameProc/Process.State.cs@Begin`:262–266、SystemProc@endAutoSave:670–675）。
- `@USERSHOP` 結束（沒有 BEGIN）→ 再次 `@SHOW_SHOP`（@endCallEventBuy:737–755）。本作 `_Replace.csv` 販売アイテム数 0，所有輸入都交給 `@USERSHOP`。
- 函式自然結束（沒寫 RETURN）時 `RESULT = 0`（`GameProc/Process.ScriptProc.cs`:61–67）。
- 原作的 `@EVENTSAVE`、`@EVENTBUY`、`@CALLTRAINEND`、`@SYSTEM_AUTOSAVE`、`@SYSTEM_LOADEND` 皆未定義。

## 1. 新遊戲：`@EVENTFIRST`（オープニング処理.ERB）

| 行 | 動作 |
|---:|---|
| 29–45 | `LOADGLOBAL`；有全域資料則 `CALL UPDATE`（§10），否則初始化 `MOB_FLAG` 為 100 |
| 48–49 | `TIME = 1`、`MONEY = 5000` |
| 51 | `CALL CONFIG_INIT(1)`（`SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`） |
| 53–59 | 初期持有衣裝 `ITEM:100,200,201,202,299,300,401 = 1` |
| 63–64 | `SWAPCHARA 0, 1` / `DELCHARA 1`：MASTER 放成 Chara999 ダミー（`GameBase.csv` 最初からいるキャラ,999） |
| 67–87 | 模式選擇迴圈 `CALL MODE_SELECT`（:297）；每次重設 `FLAG:100/101`、`FLAG:852 = 5000`（防衛力） |
| 90–105 | `FLAG:50 = FLAG:51 = 1`（設施等級）；`CALL GET_BOSS_ERB_NUM` → `FLAG:3`；`FLAG:4 = 1`；`FLAG:100` 逐位 SETBIT |
| 111–135 | 角色製作：solo 模式 1 人、否則 3 人 `ADDCHARA 0`（汎用キャラ），`CALL CHARA_MAKE_MAIN, 0`（`SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB`），`CALL CHARA_MAKE_FINALIZE`（`CHARA_MAKE_DEFAULT.ERB`:221）。**預設（不改設定直接 [1000]）的實際執行順序見下方「預設路徑」** |
| 143–166 | 每名角色設定 `CFLAG:6`（口上番號，依 `NO` 與 `TALENT:口上設定`）、`CFLAG:100 = 予定_休憩` |
| 169, 173 | `CALL SET_LIMIT_DAY`（:411）、`CALL HEROINE_PRESET`（:617，§10：[0]〜[3] → `CONFIG_INIT`） |
| 177–238 | 是否顯示序章（`INPUT` 0/1） |
| 242–250 | 預設墮落角色 → `CORRUPT_CHANGE_LOOKS_MAIN` |
| 254–267 | 每名角色 `CALL MESSAGE_FIRST`（口上）；`LOCAL <= パーティ人数最大値` 者 `CFLAG:999 = 1`（入隊） |
| 269–283 | 角色裝備中的衣裝（`CFLAG:40–43`、`EQUIP:600–699`）登記為持有 |
| 286–292 | `FLAG:41 = 1`、`CALL RESEARCH_QUOTA`、`CALL UPDATE`（§10）、**`BEGIN SHOP`** |

**預設路徑（S10 查證；玩家在所有選單都不改設定直接確定，程式：`opening.event_first(preset=None)`、`game/chara_make.py`）**

MODE_SELECT（:297）沒有預設值，`[1] NORMAL` 是第一個選項（S03 起沿用）。之後：

1. `ADDCHARA 0` ×3（:115–122）：Chara000 → `NO = 0`、`CALLNAME = "汎用キャラ"`（`reference/emuera-1824/Emuera/GameData/Variable/CharacterData.cs`:99–101，
   `CSV/Chara/Chara000汎用キャラ(女性).CSV`：基礎 体力・気力 1000／其他 100、珠 修練Ｐ 200、CFLAG:10/11/40/41/42 = 25/110/100/200/300、CSTR:12–14/18）。
2. `CHARA_MAKE_MAIN`（CHARA_MAKE.ERB:5）：`LOADGLOBAL` 失敗 → 共通設定 FLAG:5–7・820–825、SAVESTR:10–12 全為 0／空（:9–21）＝主題なし、
   変身名なし、苗字／名前の言語「デフォルト」、種族「ランダム」、フィート「なし」、性格「完全ランダム」。`[1000]`（:206–209）→ `CHARA_MAKE_FINALIZE`。
3. 第 1 次 `CHARA_MAKE_FINALIZE`（DEFAULT:221）對 SELECT = 1..3 **逐人**：`CHARA_MAKE_INITIALIZE`（DEFAULT:5）→ 其餘 FINALIZE 本體（:233–487）。
   INITIALIZE 的順序：種族 `RAND:24`（FLAG:823 = 0，:36–66；FLAG:824 = 0 → 不呼叫 SET_FEAT_DEFAULT）→ 性格 `RAND:18`（FLAG:825 = 0 →
   WHILE 第 1 圈就 BREAK，:77–140）→ SEIKAKU_HOSEI_F 修正 BASE 0–2・10–13（:141–153）→ 一人称 CFLAG:8（:155–164）→
   `CHARA_MAKE_BASE_PROFILE`（:493）的汎用分岐（:507–980）：処女・清純派 → GENERATE_BODYLINE → AGE_SETTING → STATUS_TALENT（:985）→
   STATUS_TALENT_FLAVOR（:1063）→ CHARA_SIZE_DEFAULT → 髪型 STR:30000〜 → 人間なら変身能力 → 名字與外見色（STR:3000〜、12000〜）→
   NAME／CALLNAME／CSTR:10・200 → 變身名＝CALLNAME、名乗り（FIRSTSETTING_CHANGINGCALL_DETAIL）→ 一人称低機率變更 → `CFLAG:34 = 1`。
   CALLNAME 因此不再是「汎用キャラ」，INITIALIZE 末尾（:169–209）的變身名載入也會對這名角色執行（已設定，實際不變）。
   FINALIZE 本體：修練Ｐ 200 → `CFLAG:(50+RAND:7)` 20 次、LEVELSTATUS 等（同 S03）。
   `STATUS_TALENT_SEIKAKU`（精神素質）只由キャラメイク畫面（FIRSTSETTING_CHARA_SEIKAKU.ERB:230）呼叫，預設路徑不經過。
4. EVENTFIRST:135 第 2 次 FINALIZE：INITIALIZE 的種族／性格已設定 → 跳過；BASE_PROFILE 走 CSV 分岐（CALLNAME ≠ 汎用キャラ），
   `CFLAG:34 = 1 ≠ 0` → 不再生成，RETURN（:496–505）；修練Ｐ 已用完；LEVELSTATUS 再套一次（同 S03）。
5. :143–166 `CFLAG:6`：`NO == 0` → 0；ロボっ子 → 2；再依 `TALENT:口上設定`（汎用キャラ為 0）女性 → **0**（男性 → 1）。
   所以 3 名全部是 0（女性汎用口上，`KOJO_0_*_{性格}`）。

**開局要點（S03 翻寫時確認，程式：`src/eragvt/game/opening.py`）**
- `CHARA_MAKE_FINALIZE` 會執行兩次：角色製作選單 `[1000]`（`SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB`:210）
  與 EVENTFIRST:135。第二次以第一次的 BASE 當「体力基礎」再算一次 `LEVELSTATUS`，所以開局的最大體力等
  是「升級公式套兩次」的結果（例：Chara301 體力 CSV 1400 → 2006 → 2787）。
- 角色 CSV 的 `相性`（RELATION，索引＝對方 CSV 番号）只有在 `HEROINE_PRESET` 選 `[30]` 時才經
  `SYSTEM/キャラメイキング関連/FIRSTSETTING_CONVERTCSV.ERB@CONVERT_RELATION`:3–23 轉成以登錄 index 為索引；
  直接開始遊戲時維持 CSV 原值。
- `CFLAG:240`（固有番號）= 登錄 index（CHARA_MAKE_DEFAULT.ERB:242–243）。

S55 已接通 `CHARA_MAKE_MAIN` 的主選單與共通設定、全域存讀、完成與返回；詳見
`creation-menu.md`。既有二擇開局後先顯示製作畫面，按 `[1000]` 才繼續 HEROINE_PRESET；
非互動 helper 與標準模擬只多送這個直接確定步驟。

初期セット（**不是**預設，是キャラメイク畫面的 `[200]` 選項；本程式 `event_first(preset=PRESET_TOKUSOU)`）：`SYSTEM/キャラメイキング関連/初期セット/*.ERB@SHOKISET_SELECT_n` 以
`ADDCHARA <CSV番号>` 加入 CSV 角色，例如 `0_特捜戦隊.ERB@SHOKISET_SELECT_0` 加 301/302/303，
之後 `CALL SHOKISET_CSVFIX`（`SHOKISET.ERB`:96）。由 `SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI` 選單呼叫。

## 2. 讀檔：`@EVENTLOAD`

`CALL UPDATE`（`バージョン間互換処理.ERB@UPDATE`:95：先做 GLOBAL 部分（§10），再做存檔版本升級；後者全部是
`LASTLOAD_VERSION < n`（n ≦ 408）的分岐，版本 408 的存檔不會改動狀態）；`FLAG:999` 決定背景色；`FLAG:64 > 0`（已通關）則 `JUMP ENDING`。
之後直接 `@SHOW_SHOP`（見 §0）。

## 3. 回合開始：`@EVENTSHOP`（SHOP_TURNEND.ERB:141）

- `DAY == 0`（剛開局）：`DAY = 1`、`TIME = 0`、`FLAG:64 = FLAG:799 = 0`、`TARGET = 1`，`JUMP SHOW_SHOP`。
  EVENTSHOP 回來後引擎還會自動存檔並**再呼叫一次** `@SHOW_SHOP`（§0），因此開局 SHOP 畫面實際畫兩次（中間有 `@LB` 清畫面）。
- 其餘：`PARASITE`、`SMALL_TENTACLE_HANTEI`（config）、`BIRTH_AUTO_RANDOM`；`FLAG:41 = FLAG:43 = 0`；
  `INVERTBIT TIME, 0`（晝夜切換，TIME 0=晝 1=夜）；`CALL RECOVERY_OVER_TIME`（:591）；
  `TIME == 0` 時 `DAY += 1` 並 `CALL CALC_INCOME_EXPEND`（:771）；新聞 `FLAG:60`；`CHECK_SHIELD_ALL`；
  `TARGET = FLAG:798`。

**一「回合」= 半天**（晝或夜）；兩回合一天。

## 4. 主選單：`@SHOW_SHOP` / `@USERSHOP`（インターミッション画面/SHOP.ERB）

`@SHOW_SHOP` 顯示新聞、BOSS 資訊、隊伍列表、選單。`@USERSHOP` 的分派（`SELECTCASE RESULT`，:195）：

| 輸入 | 動作 |
|---|---|
| 1..CHARANUM-1 | 切換操作角色 `TARGET` |
| 50 | `SHOP_ORGANIZE_PARTY`（S46 已接通；規則與原作反向警告見 `party-organization.md`） |
| 100 | `USERSHOP_ACTION_CONFIRM`（:503）→ 確認後 **`JUMP ACTION_MAIN`**。確認的 `SELECTCASE` 只有 `CASE 9`，其餘（含 `[1]はい`）都 `RETURN 0` 中斷（:521–532） |
| 101–108 | `USERSHOP_SET_ACTION, RESULT, FLAG:9`：設定 `CFLAG:100`（行動預約，常數見 variables.md） |
| 110 / 111 / 112 / 113 / 120 | 狀態、強化、衣裝設定、醫務室、衣裝購入 |
| 130 / 150 / 160 | 狀況確認、設施擴張、行程設定 |
| 169 / 170 / 180 | 引退者名簿、引退、新人（需 `OPTION_加入引退有り`） |
| 200 / 300 | `SAVEGAME` / `LOADGAME` |
| 700 / 800 | `CONFIG` / `SHOW_TROPHY` |

## 5. 行動執行：`@ACTION_MAIN`（ゲーム内_行動実行処理/ACTION.ERB:6）

**一次只處理一名角色**，靠 TURNEND 迴圈逐一輪到每人：

1. `FLAG:799 == 0` → 記下 `FLAG:798 = TARGET`（:10–14）。`FLAG:799 += 1`（:17）。
2. `FLAG:799 >= CHARANUM` → `BEGIN TURNEND`（全員結束，:20）。
3. 計算戰鬥支援人數 `FLAG:43`；重設戰鬥旗標 `FLAG:10/11/45/48`。
4. 非「無事」→ `BEGIN TURNEND`（:43）。`TARGET = FLAG:799`。候補（`CFLAG:999 == 0`）→ `REST` + `BEGIN TURNEND`。
5. 未預約 → 休憩；`IS_ACTION_INCAPABLE` → 顯示原因、`REST`、`BEGIN TURNEND`（:67–71）。
6. 依 `CFLAG:100` 分派（:74）：

| 行動 | 呼叫 | 之後 |
|---|---|---|
| 予定_出撃 101 | `FLAG:41++`；`CALL ENCOUNT`（`ゲーム内_戦闘処理/ENCOUNT.ERB`:5），無則 `MOB_TENTACLE_ENCOUNT`（:429） | 遭遇 → `BEGIN TRAIN`；否 → `BEGIN TURNEND` |
| 予定_鍛錬 102 | `CALL TRAINING`（`ACTION_TRAINING.ERB`:3） | `BEGIN TURNEND` |
| 予定_休憩 103 | `CALL REST`（`ACTION_REST.ERB`:3） | `BEGIN TURNEND` |
| 予定_活動 104 | `CALL SEISAN` | `BEGIN TURNEND` |
| 予定_防衛 105 | `CALL GUARD` | 遭遇 → `BEGIN TRAIN`，否則 TURNEND |
| 予定_支援 106 | `CALL SUPPORT`（人數不足則 REST） | `BEGIN TURNEND` |
| 予定_情報 107 | `CALL GATHER_INFORMATION` | 事件戰 → `BEGIN TRAIN`，否則 TURNEND |
| 予定_自由 108 | `CALL PASTIME` | 事件戰 → `BEGIN TRAIN`，否則 TURNEND |

## 6. 回合結束：`@EVENTTURNEND`（SHOP_TURNEND.ERB:3）

1. 重設 `FLAG:70–72`、`VARSET MAX_PALAM`。
2. **`FLAG:799 < CHARANUM && FLAG:45 == 0` → `JUMP ACTION_MAIN`**（下一名角色，:16–17）。
3. 全員行動完：`SET_PARTYMEMBER`；還原 TARGET；`CALL ENDING`（`ゲーム内_イベント発生/エンディング/ENDING.ERB`:3）——
   `FLAG:999 == -999` 回標題；`FLAG:64 != 0` → `JUMP SHOW_SHOP`。
4. `CALL RECALC_PARTYMEMBER`（:55，定義 :220）；若是襲擊戰後回來（`FLAG:45 > 0`）→ 清旗標、`BEGIN SHOP`。
5. `FLAG:799 = 0`、`FLAG:49 = 0`、`BOSS_TENTACLE_RECOVER`、每名角色 `MESSAGE_TURNEND`（口上）。
6. 夜間事件：脅迫／監禁、`PRISON`（幽閉）、`BIRTH_HANTEI`、`GROW_HANTEI`、`AKUOTI_ATTACK`、
   `LOVESEX_NIGHT`、`SELF_NIGHT`、`YOBAI`（config）、`DAILY_DEFENCE_CHANGE`、`DAILY_POPULARITY_CHANGE`。
7. `CALL RAID_HANTEI`（`強制発生イベント/FORCE_襲撃or救援イベント発生.ERB`:9，config）——
   發生時設 `FLAG:45` 並經 `イベントから派生する特殊戦闘/●イベント戦闘_襲撃共通.ERB`:178 `BEGIN TRAIN`。
   `JUMP RAID_RESCUE`（救援 FLAG:45 = 2〜5，昼・可選擇見送り）／`RAID_ATTACK`（襲撃 3001〜3004）；JUMP 先 RETURN 時 RAID_HANTEI 也 RETURN
   （`reference/emuera-1824/Emuera/GameProc/Process.State.cs`:368–378）。各イベントの EXEC が シチュエーション・ターン上限・
   TCVARn:0 を設定 → ENCOUNT_BOSS（FLAG:45 > 0 は遭遇率 100%、`MESSAGE_RAID_BOSS`）→ BEGIN TRAIN。戰後 EVENTEND で
   `EVENT_BATTLE_MISSION_CHECKER_{FLAG:45}` → `RAID_MISSION_SUCCESS／FAILURE`，BEGIN TURNEND → 第 2・4 步。3002 的繁殖袋／四肢欠損
   不戰鬥直接拉致（CFLAG:0 = 9）→ BEGIN TURNEND。Python：`eragvt.game.raid`（S20）。
8. `FLAG:45 == 0` → `BEGIN SHOP`（回到第 3 節）。

各行動對狀態的影響、開局狀態下各夜間事件是否觸發：見 `actions.md`（S04）。注意 `@EVENTSHOP` 的 `PARASITE`
（`FORCE_深夜の寄生触手暴走.ERB`:8–9）會把 `FLAG:799` 覆寫成 `CHARANUM-1`，由 `SHOW_SHOP`:20 歸 0。

## 7. 戰鬥（TRAIN）

結構另見 `battle-overview.md`。出口一律 `BEGIN AFTERTRAIN` → `@EVENTEND`（經驗、金錢、修練P、
變身解除、事件戰任務判定）→ `BEGIN TURNEND`（BATTLE_TRAIN_AFTER.ERB:536）→ 第 6 節，
並因 `FLAG:799 < CHARANUM` 繼續下一名角色。

## 8. 口上派發（不讀內容，只記機制）

地の文函式（`地の文/MESSAGE.ERB@MESSAGE_FIRST` 等）統一呼叫
`TRYCALLFORM KOJO_ROOT(CFLAG:6, "代碼")`（`口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT`:12）：

- `CFLAG:6`（口上番號）為 0（女性汎用）或 1（オトコ汎用）時，呼叫
  `KOJO_{番號}_{代碼}_{SEIKAKU_CHECK_F(TARGET)}`（依性格分檔，`口上/女性汎用口上/KOJO_0_12_勝気.ERB` 等）。
- 其他番號呼叫 `KOJO_{番號}_{代碼}`（專用口上，`口上/固有キャラ専用口上/kojo_<番號>_*.ERB`）。
- 代碼含 `OTHER_` 時改用對手（`FLAG:111`）的性格；氣絕中或結界擋下對應性攻擊時不輸出。
- 找不到函式時 `RETURN -1`，呼叫端據此決定是否回落地の文。

→ 這正是 PLAN 的 `NarrationService` 介面：`(口上番號, 代碼, 性格) → 文字 | 無`。

## 9. ゲームオーバーモード（S12）

路徑：GAMEMODE.ERB = `ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB`、ENDING.ERB = `ゲーム内_イベント発生/エンディング/ENDING.ERB`。

- **定義**：`FLAG:0`（オプション bit 列）＝ 0。`MODE_GAMEOVER = 0`、`モードオプション:0 = 0b00000000000`（`DIM.ERH`:40、:83–92）。
  `CHECK_GAMEOVER_F()` = `GAME_MODE_CHECK_F() == MODE_GAMEOVER`（GAMEMODE.ERB:116–118）＝ FLAG:0 == 0。
  `GAME_MODE_CHECK`（CALL 版、:124–130）は FLAG:906（周回で時間制限解除）≠ 0 のとき各モードに `| 64` して比べる（@SAVEINFO が使用）。
  FLAG:0 = 0 なので `GAME_OPTION_CHECK_F(任意)` も全部 0（ソロ・サンドボックス等の分岐も通らない）。
- **入口**：`CHANGE_GAMEOVER_MODE`（:112–114）= `FLAG:0 = 0`、`DAY:2 = DAY*2+TIME`（RETURN 無し、次の `@` で関数終端：
  `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs`:61–67）。呼び出し元は ENDING_1（全滅、:295–302）、
  ENDING_4（ソロ洗脳／悪堕ち、:553–563）、ENDING_5（ソロ取り込まれ、:645–654）。いずれも続けて `FLAG:999 = -998`、`FORCEWAIT`
  で**呼び出し元へ戻る**（タイトルに戻らない）。
  - ENDING_1 ← `BATTLE_TRAIN_AFTER.ERB@EVENTEND`:527–528（SAFE + ENSLAVED が 0、非ソロ、非サンドボックス、非ゲームオーバー）→ :536 `BEGIN TURNEND`。
    敗北で `FLAG:799 -= 1`（`BATTLE_COM_AFTER.ERB`:1091–1092）されているので、EVENTTURNEND:15–16 から残りキャラの ACTION_MAIN
    （全員操作不能 → スキップ、FLAG:799 == 0 なら「行動開始！」がもう一度出る）→ TURNEND 本体。
  - ENDING_4／5 ← `PRISON.ERB@PRISON_EVENT`:367–370／:417–420（DRAWLINE・RETURN）→ `@PRISON`:32–33 `FLAG:999 == -998` で BREAK。
- **`FLAG:999 = -998`**：FLAG:999 は本来デバッグフラグ（== 1）。-998 は「ゲームオーバーモードに入った直後」の目印で、
  次の `@PRISON`（:5–8）が 0 に戻す。-998 のまま通る読み取りは `IF FLAG:999`（非 0 判定）系のみ意味を持つ：
  ソロの ENDING_4／5 の後は同ターンの SHOW_SHOP:26 で背景色 0,0,40（Web も `FLAG:999` 非 0 で同色）。
  全 ERB の `FLAG:999` 參照 100 行（口上 0）を確認済み、他は `== 1`／`> 0` 判定か、この区間では通らない。
- **ゲームオーバーモード中の流れ**（全員 CFLAG:0 ≠ 0 のまま、救出も脱出（:295 はソロ／サンドボックスのみ）も無い）：
  SHOP → [100]（確認なし：SHOP.ERB:504／:534）→ ACTION_MAIN は全員スキップ → EVENTTURNEND → `@PRISON` が
  **CFLAG:0 に関係なく全キャラ**（洗脳 2・悪堕ち 3・取り込まれ 9 も）に PRISON_EVENT（:13）→ … → SHOP。
  陥落判定は CFLAG:0 == 1 のみ（:187）。地の文 `MESSAGE_PRISON_PRISENTENCE`:225–258 に 2／3／9 用の文あり。
- **CHECK_GAMEOVER_F の分岐**（`CHECK_GAMEOVER_F|GAME_MODE_CHECK|MODE_GAMEOVER` を全 ERB で grep：定義込み 43 行、口上 0）：SHOP.ERB:133–171（行動選択・強化・衣装・メディカル・購入・施設・スケジュールを
  隠す）、:253–277（同じ番号の入力を無視）、:405（殲滅猶予を出さない）、:504／:534（確認なし）、:617（行動予定を変えない）；
  SHOP_TURNEND.ERB:186（支援金・支出なし）、:199（ニュース FLAG:60 = 10001）、:380（防衛力 0）、:461（人気度変動なし）；
  SET_PARTYMEMBER.ERB:10（妊娠による出撃取消メッセージなし）；BATTLE_TRAIN_AFTER.ERB:527；ENDING.ERB:9／:74（クリア・日数超過判定なし）；
  PRISON.ERB:13；地の文 MESSAGE_PRISON.ERB:225–258（catalog）。未移植系統内：PREGNANT_CHILD_BIRTH.ERB:127／:154、
  FORCE_悪堕ちキャラの淫謀.ERB:1609（AKUOTI_EVENT）、SCORE／SUCCESSION（GAME_MODE_CHECK_F、結局後）。
- **注意**：防衛力 0 のため `AKUOTI_ATTACK`（悪堕ちキャラが居れば）は毎ターン必ず発生（AKUOTI_EVENT 未移植 → 停止）。
  取り込まれ（CFLAG:0 = 9、苗床化）が居ると `BIRTH_AUTO_RANDOM`:671– の苗床出産が毎ターン 1/4 で発生（未移植 → 停止）。
  FLASHNEWS の 10001 番（DAY:2 から経過ターン数を出す、FLAG:11 = 7 で 1〜9 ターン目は固定文）は S26 で移植（`eragvt.game.flashnews`）。

## 10. コンフィグと GLOBAL（S24，Python：`eragvt.game.config`、`state.savefile.GlobalStore`）

- **引擎**：`SAVEGLOBAL` 寫 GLOBAL・GLOBALS・`#DIM GLOBAL SAVEDATA`（本作只有 `MOB_GLOBAL`，DIM.ERH:170）全部到 `global.sav`，附遊戲代碼・版本
  （`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@SaveGlobal`:2200–2252、`VariableData.cs`:904–935）。
  `LOADGLOBAL` 檔案不存在／代碼・版本不符／讀取錯誤 → RESULT 0、記憶體不變；成功 → 全部置換（未存的元素補 0：
  `Sub/EraDataStream.cs@ReadInt64Array`:77–102）、RESULT 1（`@LoadGlobal`:2256–2310、`Instraction.Child.cs`:1285–1298）。
  GLOBAL 記憶體**不會**被新遊戲／RESETDATA／讀檔清掉（`@ResetData`:1132–1141），只有程式啟動與 RESETGLOBAL（本作 0 件）。
  Python：記憶體＝`GlobalStore.mem`（Web 每個 app 一份），檔案＝`saves/global.json`。
- **`@UPDATE`**（:95–128）：PRINTL → LOADGLOBAL 成功時 `UPDATE_GLOBAL` → FLAG:800 bit0（自動ロード）則 FLAG:801〜805 = GLOBAL:11〜15
  （GLOBAL:0+1+2 ≠ 0 才印訊息）→ **一律** FLAG:850 = GLOBAL:4、MOB_FLAG = MOB_GLOBAL（不存在的雑魚番號 = 0）。呼叫處：EVENTFIRST:32／:291、EVENTLOAD:7。
- **`@UPDATE_GLOBAL`**（:12–91）：依 GLOBAL:3（全域資料版本）逐版修正，最後 `GLOBAL:3 = 408` 並 SAVEGLOBAL。GLOBAL:3 = 0 時：
  GLOBAL:11〜14 = 4／31／88／5、GLOBAL:15 = 0、GLOBAL:4 反轉 bit 7・8・9・11・12・16・17・19・20、MOB_FLAG／MOB_GLOBAL:0:1 = 100 等。
  **注意**：CONFIG 的 [1]／[9999]、性嗜好／雑魚／変身フィルタ的 [200] 只 SAVEGLOBAL、不設 GLOBAL:3 → 初次存下的設定在下一次 UPDATE 會被上述值蓋掉（原作行為；S59已裁決僅新GlobalStore初始化版本，既有版本0檔仍遷移，詳見[成就](achievements.md)）。
- **CONFIG_INIT(ARG)**（CONFIG_初期設定.ERB:4–61，FLAG:800〜805）：0 = (1, GLOBAL:11〜15)；1 基本 = (0,1,15,263,1,2)；
  2 淫獄 = (0,25,31,391,247,67)；3 クズ市民 = (0,25,63,391,1271,67)。EVENTFIRST:51 先以 1 初始化，HEROINE_PRESET:758 再以選擇值覆寫。
- **HEROINE_PRESET**（:617–759）：[20+n] ステータス（S25）、[30] 相関関係設定（S51，見 [關係設定](relation-setting.md)）、[10] `CONFIG("mainmenu")`、
  [0]〜[3] → CONFIG_INIT；其他值無聲重新輸入。本程式預設輸入仍是 [1]。
- **MODE_SELECT [200]**（:393–402）：FLAG:801〜805 = GLOBAL:11〜15 → UPDATE_GLOBAL → CONFIG("mainmenu")。FLAG 之後會被 CONFIG_INIT 覆寫，
  留下的只有 GLOBAL（與 :291 UPDATE 讀回的 FLAG:850／MOB_FLAG）。本程式放在開局 2 択畫面（deviations「開局的 UI 跳過」）。
- **CONFIG(FROM)**（CONFIG_SYSTEM.ERB:68–513）：2 頁。[0] FLAG:800 bit0、[10–17] FLAG:801、[30–34] FLAG:802（[33] 關掉時連 bit5 清除）、
  [35] 只在 bit3 ON 時反轉、[36]、[50–58] FLAG:803、[60–71] FLAG:804、[72–80] FLAG:805（[74]／[75] 互斥）；[1] 存 GLOBAL、[2] 讀 GLOBAL＋UPDATE_GLOBAL、
  [1000]／[2000]／[3000] 各フィルタ（存 GLOBAL:4／MOB_GLOBAL／GLOBAL:51〜59 並 SAVEGLOBAL）、[999] 返回、[9999] 存 GLOBAL 後返回。
  FROM = "mainmenu" 時 [999]／[9999] 不顯示但仍可輸入。SHOP [700]（SHOP.ERB:302–303）以 FROM = "" 呼叫。
- 選單編號與 FLAG:804 的位元：[60+n] = bit n（[69] bit9「觸手の虜無しでも悪堕ち」、[70] bit10 クズ市民幽閉、[71] bit11）。
  CONFIG_SYSTEM.ERB:43–54 的註解編號（9 = クズ市民…）與選單不一致，以選單與使用處為準。

