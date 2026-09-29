# 行動（CFLAG:100）的執行與影響範圍

路徑相對 `source/earGVP/ERB/`。入口 `ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN`:6–175，一次處理一名角色
（`FLAG:799` = 目前輪到的 index），`BEGIN TURNEND` → `@EVENTTURNEND`:15 若還有人沒行動就 `JUMP ACTION_MAIN`。
Python：`eragvt.game.action`（ACTION_MAIN／REST／TRAINING）、`eragvt.game.turnend`（TURNEND／EVENTSHOP）。

## ACTION_MAIN 共通處理（每名角色）

- `FLAG:799 == 0` 時記下 `FLAG:798 = TARGET`（回合結束後 TARGET 回到這裡）並印「行動開始！」。
- `FLAG:43` = 預約「支援」且可行動的人數（≥ `CHARANUM_ACTIVE` 則 0）；`FLAG:10/11/45/48` 清 0。
- `CFLAG:0 != 0`（非無事）→ 直接 TURNEND；控え（`CFLAG:999 == 0`）→ 無聲 `REST`；無預約 → 改為休憩。
- `IS_ACTION_INCAPABLE` 成立 → `ACTION_NGREASON` 訊息 + `REST`。

## 各行動（S04 狀態）

| 行動 | 函式 | 對狀態的影響（摘要） | S04 |
|---|---|---|---|
| 出撃 101 | `ENCOUNT`／`MOB_TENTACLE_ENCOUNT` | `FLAG:41++`；遭遇 → `BEGIN TRAIN`（戰鬥），未遭遇 → TURNEND | S05 |
| 鍛錬 102 | `ACTION_TRAINING.ERB@TRAINING` | INPUT 選 0–10；體力 −`TRAINING_DOWNTAIRYOKU`、`BASEUP`（BASE 基礎值＋LEVELSTATUS）、戰技 EXP＋`SENGIUP`、`GET_EXP`（JUEL:50，升級）、`GET_SYUREN`（JUEL:20）、`CFLAG:101` = 選項 | 已翻 |
| 休憩 103 | `ACTION_REST.ERB@REST` | 體力／氣力回復（設施 FLAG:51、素質、疲勞 CFLAG:99 修正）、性耐性全滿、疲勞減少、`CFLAG:101 = -1` | 已翻 |
| 活動 104 | `ACTION_SEISAN.ERB@SEISAN` → `特別活動/SEISAN_0..8` | INPUT 選 9 種（打工、研究、驅除、賣春、AV、便器、偶像…），MONEY、EXP、JUEL、`_ABLUP`、變身 `TRANSFORM`；`CFLAG:111` 排程 | 未翻 |
| 防衛 105 | `ACTION_GUARD.ERB@GUARD` | `FLAG:41++`；`ENCOUNT`／雜魚戰 → TRAIN；未遭遇：體力・氣力 −12%（SYOUHI_KEIGEN）、`FLAG:852 += 125 + Lv*2 + RAND:26` | 未翻（遭遇判定屬 S05） |
| 支援 106 | `ACTION_SUPPORT.ERB@SUPPORT` | 前線 0 人且 `FLAG:41 == 0` → 改休憩（已翻）；否則體力・氣力 −24%/18%（依 FLAG:43）、修練P 15–25、`GET_EXP`（依 `TENTACLE_LEVEL`）、知性基礎 +0–2 | 本體未翻 |
| 情報 107 | `ACTION_GATHER_INFORMATION.ERB` | `ENCOUNT_CITIZEN`（クズ市民）→ `FLAG:73 > 0` 時 TRAIN；`RESEARCH_PROGRESS`、MONEY、EXP 多種、`CFLAG:120–122`、懷孕判定 | 未翻 |
| 自由 108 | `ACTION_PASTIME.ERB@PASTIME` | 學校／街／遠出／運動（亂數或排程 `CFLAG:113`）、`CFLAG:320–354`、魅了經驗；`FLAG:73 > 0` 時 TRAIN | 未翻 |

未翻的行動在 `action_main` 丟 `NotImplementedError`；Web session 捕捉後顯示「未實作のため停止」並停住
（見 `docs/wiki/bridge/deviations.md`）。

## 回合結束之後（EVENTTURNEND → BEGIN SHOP → EVENTSHOP）

`SHOP_TURNEND.ERB@EVENTTURNEND`:3–139 → `BEGIN SHOP`（此時 SystemState = Normal，會自動存檔：
`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs`:609–611、633，`Process.State.cs`:271–273）
→ `@EVENTSHOP`:158–215（晝夜切換、回復、日期、收支）→ 自動存檔 → `@SHOW_SHOP`。

開局狀態（NORMAL＋特装戦隊、config 基本セット：FLAG:801=1、802=15、804=1、805=2、850=0）下各夜間事件：

| 事件 | 開始條件 | 開局狀態 |
|---|---|---|
| INTIMIDATION／KIDNAPPING | PRISON config bit10（OFF）／CFLAG:0 == 4 | 不觸發 |
| PRISON | CFLAG:0 == 1 或 GAMEOVER 模式 | 不觸發 |
| BIRTH_HANTEI／GROW_HANTEI | 素質「妊娠」1/3/4/5；育兒 CFLAG:0 == 11、CFLAG:22、225 | 不觸發 |
| AKUOTI_ATTACK | CFLAG:0 == 3 | 不觸發 |
| LOVESEX_NIGHT | 夜、交際相手 1–4 | 不觸發（交際相手 0） |
| SELF_NIGHT | 夜、RAND:100 < 欲望*5 + 触手中毒*2 + 自慰中毒段階 | 機率 0 |
| YOBAI | 夜、淫核等素質或感覺 ABL ≥ 3 | 不觸發 |
| RAID_HANTEI | DAY ≥ 3、有人沒出撃／防衛、依防衛力 RAND | **會觸發** → DEVIATION 跳過 |
| PARASITE | 素質「寄生」；迴圈會把 FLAG:799 覆寫成 CHARANUM-1（SHOW_SHOP:20 歸 0） | 不觸發 |
| SMALL_TENTACLE_HANTEI | 夜、FLAG:44（子触手數）> 0 | FLAG:44 > 0 後**會觸發** → DEVIATION 跳過 |
| BIRTH_AUTO_RANDOM | 防衛力 < 10000 時 1/(防衛力/100)：FLAG:44 += 1（已翻）；苗床死亡角色出產（未翻） | 前半會觸發（已翻） |
| ENDING | 全ボス撃破（ENDING_2）、日數超過（ENDING_3：開局 NORMAL 為 11 日目夜） | 11 日目夜觸發 → NotImplemented |
