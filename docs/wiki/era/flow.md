# 主流程與呼叫鏈

起點：`ERB/※ゲーム開始からのフロー.txt`（原作者寫的概略）。本頁以實際 ERB 驗證並補上函式名。
路徑一律相對 `source/earGVP/ERB/`。

注意：`ERB/` 直下的 `SHOP*.ERB`（`SHOP.ERB`、`SHOP_TURNEND.ERB` 等 7 個）都只有 5 行註解，
說明檔案已移到 `インターミッション画面/`，**不是**實作。

## 0. Emuera 階段（BEGIN）與事件函式

原作沒有自訂 `@SYSTEM_TITLE`，標題畫面用 Emuera 預設（`GameBase.csv` 的タイトル）。
遊戲流程靠 Emuera 內建的「階段」切換，ERB 用 `BEGIN 階段名` 跳轉：

| 階段 | Emuera 呼叫的事件函式（依序） | 原作位置 |
|---|---|---|
| FIRST（新遊戲） | `@EVENTFIRST` | `ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`（:19） |
| LOADGAME 後 | `@EVENTLOAD` | `ゲーム内_イベント発生/オープニング処理.ERB@EVENTLOAD`（:4） |
| SHOP | `@EVENTSHOP` → 迴圈 {`@SHOW_SHOP` → 輸入 → `@USERSHOP`} | `インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP`（:141）、`インターミッション画面/SHOP.ERB@SHOW_SHOP`（:5）、`@USERSHOP`（:192） |
| TRAIN（戰鬥） | `@EVENTTRAIN` → 迴圈 {`@SHOW_STATUS` → `@SHOW_USERCOM` → 輸入 → `@USERCOM`} | `ゲーム内_戦闘処理/BATTLE_TRAIN.ERB@EVENTTRAIN`（:4）、`BATTLE_SHOW_STATUS.ERB@SHOW_STATUS`（:3）、`BATTLE_COM.ERB@SHOW_USERCOM`（:4）、`@USERCOM`（:572） |
| DOTRAIN n | `@EVENTCOM` → `@COMn` → `@SOURCE_CHECK` → `@EVENTCOMEND` | `BATTLE_COM.ERB@EVENTCOM`（:666）、`戦闘コマンド(ヒロイン)/COMF*.ERB@COMn`、`BATTLE_COM_AFTER.ERB@SOURCE_CHECK`（:2）、`BATTLE_COM.ERB@EVENTCOMEND`（:685） |
| AFTERTRAIN | `@EVENTEND` | `ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND`（:2），結尾 `BEGIN TURNEND`（:536） |
| TURNEND | `@EVENTTURNEND` | `インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`（:3） |

DOTRAIN 內部順序是 Emuera／eramaker 規格，不是原作寫的（見 unresolved）。
原作的 `@EVENTSAVE`、`@EVENTBUY`、`@CALLTRAINEND` 皆未定義。

## 1. 新遊戲：`@EVENTFIRST`（オープニング処理.ERB）

| 行 | 動作 |
|---:|---|
| 29–45 | `LOADGLOBAL`；有全域資料則 `CALL UPDATE`，否則初始化 `MOB_FLAG` 為 100 |
| 48–49 | `TIME = 1`、`MONEY = 5000` |
| 51 | `CALL CONFIG_INIT(1)`（`SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`） |
| 53–59 | 初期持有衣裝 `ITEM:100,200,201,202,299,300,401 = 1` |
| 63–64 | `SWAPCHARA 0, 1` / `DELCHARA 1`：MASTER 放成 Chara999 ダミー（`GameBase.csv` 最初からいるキャラ,999） |
| 67–87 | 模式選擇迴圈 `CALL MODE_SELECT`（:297）；每次重設 `FLAG:100/101`、`FLAG:852 = 5000`（防衛力） |
| 90–105 | `FLAG:50 = FLAG:51 = 1`（設施等級）；`CALL GET_BOSS_ERB_NUM` → `FLAG:3`；`FLAG:4 = 1`；`FLAG:100` 逐位 SETBIT |
| 111–135 | 角色製作：solo 模式 1 人、否則 3 人 `ADDCHARA 0`（汎用キャラ），`CALL CHARA_MAKE_MAIN, 0`（`SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB`），`CALL CHARA_MAKE_FINALIZE`（`CHARA_MAKE_DEFAULT.ERB`:221） |
| 143–166 | 每名角色設定 `CFLAG:6`（口上番號，依 `NO` 與 `TALENT:口上設定`）、`CFLAG:100 = 予定_休憩` |
| 169, 173 | `CALL SET_LIMIT_DAY`（:411）、`CALL HEROINE_PRESET`（:617） |
| 177–238 | 是否顯示序章（`INPUT` 0/1） |
| 242–250 | 預設墮落角色 → `CORRUPT_CHANGE_LOOKS_MAIN` |
| 254–267 | 每名角色 `CALL MESSAGE_FIRST`（口上）；`LOCAL <= パーティ人数最大値` 者 `CFLAG:999 = 1`（入隊） |
| 269–283 | 角色裝備中的衣裝（`CFLAG:40–43`、`EQUIP:600–699`）登記為持有 |
| 286–292 | `FLAG:41 = 1`、`CALL RESEARCH_QUOTA`、`CALL UPDATE`、**`BEGIN SHOP`** |

預設隊伍（初期セット）：`SYSTEM/キャラメイキング関連/初期セット/*.ERB@SHOKISET_SELECT_n` 以
`ADDCHARA <CSV番号>` 加入 CSV 角色，例如 `0_特捜戦隊.ERB@SHOKISET_SELECT_0` 加 301/302/303，
之後 `CALL SHOKISET_CSVFIX`（`SHOKISET.ERB`:96）。由 `SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI` 選單呼叫。

## 2. 讀檔：`@EVENTLOAD`

`CALL UPDATE`（`バージョン間互換処理.ERB@UPDATE`:95，存檔版本升級）；`FLAG:999` 決定背景色；
`FLAG:64 > 0`（已通關）則 `JUMP ENDING`。之後 Emuera 回到存檔時的 SHOP 階段。

## 3. 回合開始：`@EVENTSHOP`（SHOP_TURNEND.ERB:141）

- `DAY == 0`（剛開局）：`DAY = 1`、`TIME = 0`、`FLAG:64 = FLAG:799 = 0`、`TARGET = 1`，`JUMP SHOW_SHOP`。
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
| 50 | `SHOP_ORGANIZE_PARTY`（隊伍編成） |
| 100 | `USERSHOP_ACTION_CONFIRM`（:503）→ 確認後 **`JUMP ACTION_MAIN`** |
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
8. `FLAG:45 == 0` → `BEGIN SHOP`（回到第 3 節）。

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
