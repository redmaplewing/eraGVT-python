# 戰鬥（TRAIN）結構概觀

只寫架構；計算式細節留給 S05／S06。S05 的 Python 對應在 `src/eragvt/game/battle/`（各模組 docstring 註明對應的 ERB 函式）；
本作的 `@COM_ABLE` 在引擎列舉時全部回 0，TRAIN 的輸入一律經 `@USERCOM` → `DOTRAIN`（見 `docs/wiki/bridge/unresolved.md`）。路徑相對 `source/earGVP/ERB/ゲーム内_戦闘処理/`（另註明者除外）。
戰鬥是 era 標準「調教」階段改造而成：玩家角色 = `TARGET`，敵人資料放在 `FLAG:10–22` 與 `TFLAG`／`TCVARn`。

## 1. 進入戰鬥（遭遇）

| 來源 | 呼叫 | 出處 |
|---|---|---|
| 出撃 | `CALL ENCOUNT` → `ENCOUNT_ENEMY`（洗腦／墮落角色，:19）→ 無則 `ENCOUNT_BOSS`（:137）；再無則 `MOB_TENTACLE_ENCOUNT`（:429） | `ENCOUNT.ERB@ENCOUNT`:5、`ゲーム内_行動実行処理/ACTION.ERB`:80–95 |
| 防衛 | `CALL GUARD` 後依結果 `BEGIN TRAIN` | `ACTION.ERB`:119–129 |
| 情報收集／自由行動中事件 | `GATHER_INFORMATION`／`PASTIME` 回傳非 0 → `BEGIN TRAIN` | `ACTION.ERB`:150–160 |
| 回合末襲擊／救援 | `RAID_HANTEI` 設 `FLAG:45`，經共通檔 `BEGIN TRAIN` | `ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_襲撃共通.ERB`:178、`●イベント戦闘_救援共通.ERB`:216 |

敵人種類以 `ENEMY_TYPE_CHECK_F("BOSS" / "LASTBOSS" / "MOB" / "AKUOTI" / "CITIZEN")` 判定；
`FLAG:10`（0 ボス、1 ラスボス、2 雜魚）＋ `FLAG:11`（番號）決定資料檔：

- `触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB`（1 Ｃ〜7 Ｈ触手）、`TENTACLE_LASTBOSS_{n}_*.ERB`（Ｋ触手、天使の樹）
- `触手データ/雑魚敵/`、`触手データ/クズ市民/`（`FLAG:73` = 人數）
- 洗腦／墮落角色：`FLAG:110 = 1`、`FLAG:111` = 角色番號，能力直接取該角色的 BASE。
- 存取介面：`COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS`:198（`"NAME"`、`"CHISEI"` 等字串鍵），
  BOSS 性攻擊例行 `TENTACLE_{種別}_{番號}_SEX_ROUTINE`（:249、:303）。
- 敵 HP：`FLAG:12`（最大）/`FLAG:13`（現在）。

## 2. 戰鬥開始：`BATTLE_TRAIN.ERB@EVENTTRAIN`（:4）

1. 非事件戰（`FLAG:45 == 0`）：`INITBATTLESITUATION()`（:17）、`VARSET TCVARn`、
   `ターン上限 = (FLAG:10 == 2 ? 15 # 50)`（:20，雜魚 15／BOSS 50），初期距離 `TCVARn:0 = 3`（遠距離，:27；クズ市民戰為 0）。
2. 重設 `TFLAG`、`EX_COM` 等；`MAX_PALAM` 清空；`BASE:射精 = BASE:噴乳 = 0`；空中ダッシュ補滿（上限 8）。
3. 衣裝 HP（`CLOTH_BATTLE_SETHP`:96）、事件戰的強制狀態（`GETBATTLESITUATION("強制発情")` 等）。
4. 敵方第一手：`SELECT_ENEMY_ACTION`（墮落角色）或 `SELECT_TENTACLE_ACTION`（:135，`ENEMY_ACTION.ERB`:1019）。
5. `FLAG:700 = 1`（戰鬥中，:139）；解析度 `FLAG:20` 取自 `FLAG:500+n`／`600+n`。
6. **先制**：`INITIATIVE = MIN(SQRT(EXP:戦闘経験),20) + MIN(SQRT(知性比),25) + 5`（:169），
   加上觸手殘數、精霊交信／狩人の勘等加值；迴圈 `RAND:100 < INITIATIVE` 時 `TFLAG:24 += 1` 且 `INITIATIVE *= 3/4`（:202–207，`GOTO INITIATIVE_LOOP`）。
   `TFLAG:24` = 先制攻擊回合數。

## 3. 每回合（玩家）

```
@SHOW_STATUS (BATTLE_SHOW_STATUS.ERB:3)     狀態列、距離、剩餘回合（ターン上限 - TFLAG:0）
@SHOW_USERCOM (BATTLE_COM.ERB:4)            依 TCVARn:8 分頁列出可用指令
輸入
@USERCOM (BATTLE_COM.ERB:572)
   999 → 撤退判定 ACT_HANTEI_TETTAI_TENTACLE（COMMON_BATTLE_HANTEI.ERB:1056）成功 → BEGIN AFTERTRAIN
   800 → 狀態畫面；810/820/830 → 切換指令分頁；898/899 → 顯示設定位元
   <400 → TRYCALLFORM COM_ABLE{n}；可用則 DOTRAIN n
DOTRAIN n：@EVENTCOM → @COMn → @SOURCE_CHECK → @EVENTCOMEND
```

指令分頁（`@SHOW_USERCOM`）：`[810] 特殊`（睨む／罵倒／反抗／説得／EX／SP變身…）、
`[820] 攻撃`（拘束中為「性技」）、`[830] 補助`（拘束中為「拘束」）。

### 指令一覽（`CSV/Train.csv`）

| 番號 | 指令 | 分類 |
|---|---|---|
| 0, 201–203 | 変身する（近／中／遠距離で変身） | 變身 |
| 1–3 | 近／中／遠距離攻撃 | 攻擊 |
| 4–7 | 防御、距離をとる、背後に回る、見切り | 補助 |
| 8–15 | 振り解く、暴れる、耐える、なすがまま、受け入れる、奉仕する、Ｖ挿入防御、救出する | 拘束中 |
| 16, 17 | *エアストライク、*バースト攻撃（`*` = 連動用，非直接選擇） | 特殊攻擊 |
| 40 | 引き剥がす | |
| 44–47 | 睨みつける、罵倒する、反抗する、説得する | 特殊 |
| 69, 70–74 | 何もしない、ＳＰバースト、*EX攻、*EX防、ＳＰ変身、ＳＰフルバースト | 特殊 |
| 99 | ギブアップ | |
| 100–104 | 手淫／フェラ／足コキ攻撃、素股焦らし、搾り取る | 性技（拘束中反擊） |

- 實作：`戦闘コマンド(ヒロイン)/COMF{n}.ERB@COM{n}`；可用判定 `COMABLE.ERB@COM_ABLE{n}`；
  名稱顯示 `PRINT_COMNAME.ERB`；移動選擇 `MOVESELECT.ERB`。
- 攻擊共通：`COM_ATTACK_COMMON.ERB`；命中判定 `COMMON_BATTLE_HANTEI.ERB@ACT_HANTEI_CHARA_TO_TENTACLE`（:6）、
  傷害 `@DAMAGE`（:1175）。
- 輔助系統：連擊 `COMBO_ATTACK.ERB`、反擊 `HANGEKI_STYLE.ERB`、攻擊預測 `FORECAST.ERB`、戰報 `REPORT.ERB@BATTLE_REPORT`（:6）。

`@EVENTCOM`（:666）：清 `TFLAG:4`、`TCVARn:2 = 体勢：通常`、`VARSET COMMON_PALAM`（指令 16/17/71/72 略過）。

## 4. `@SOURCE_CHECK`（`BATTLE_COM_AFTER.ERB`:2）——回合的核心

依序：

1. 疲勞累計（SP 變身中 `TFLAG:99`）、裝備特效（CFLAG:43 506/507/509）、ラスボス形態變化（`FLAG:21`）。
2. **勝利判定**（:115–435）：`FLAG:13 <= 0` → `TFLAG:98 = 1`、勝利訊息／成就／救出被幽閉角色／`AFTER_KILLED_BOSS` →
   `BEGIN AFTERTRAIN`（:435）。
3. 狀態異常持續、衣裝損壞、觸手服事件（`SUBEVENT_BATTLE_ACTTENTACLE*`）。
4. **敵方行動**：觸手體勢崩（`TFLAG:1 == 1`）則只重選下回合行動並 `PALAM_CAL` 全 0；
   否則 `CALL ENEMY_ACTION`（:832，`ENEMY_ACTION.ERB`:4）。
   - `TCVARn:0 > 0`（非拘束）：依 `TFLAG:10`（或預約 `TFLAG:16`）執行攻擊／絡みつく等。
   - 拘束中：`ENEMY_ACTION_SEX_ROUTINE`（:1162）→ `戦闘コマンド(性攻撃)/SEX_COMABLE.ERB@SEX_COMABLE` →
     `SEX_COM{n}.ERB@SEX_COM{n}`（0–20，依部位 CVAB 與強度）；另有 SP 性攻擊 `SEX_SPCOM0–15.ERB` 與追加責め `SEX_COMEX.ERB`、自動Ｖ防禦 `AUTO_V_DEFENCE.ERB`。
5. **敗北判定**（:847〜）：
   - クズ市民戰被監禁（:850）；
   - 一般：`BASE:体力 == 0 && BASE:気力 == 0 && BASE:性耐性 == 0 && FLAG:13 > 0`，且非雜魚／市民（:955）→
     `TFLAG:98 = 2` → 幽閉（觸手／洗腦角色／墮落角色）→ `BEGIN AFTERTRAIN`（:1095）。
   - 強拘束或丸飲み準備中則延後敗北（`ターン内敗北キャンセル`），先演出到結束。
6. **時間切れ**（:1101〜）：`ターン上限 != -1 && TFLAG:0 >= ターン上限`（或クズ市民戰脫離拘束）→ `BEGIN AFTERTRAIN`（:1130）。
7. 其後：發情→排卵判定、素股焦らし的下回合預約等。

## 5. PALAM 計算

- 入口：`COMMON_PALAM_CAL.ERB@PALAM_CAL`（:10）——12 個引數依序填入 `UP:快Ｃ,快Ｖ,快Ａ,快Ｂ,潤滑,恭順,習得,欲情,屈服,恥情,苦痛,恐怖`，
  第 13 個為 `LOSEBASE:体力`，然後 `CALL PALAM_UP`。
- `PALAM_UP.ERB@PALAM_UP`（:13）：套用補正 `PALAM_HOSEI_*`（素質、性格、觸手、姿勢、亂數，:378–643）、
  絕頂 `PALAM_CALC_ECSTASY`（:826）、射精／噴乳（:858、:926）、體力／氣力／性耐性減少（:1404、:1465、:1565）、
  刻印取得 `GOT_SEX_MARK_CHECK`（:1767，係數表在 `PALAM_UP.ERH`）。
- 常數：`CSV定数定義/PALAM.ERH`（`PALAM上限 = 999999`、部位對照表）。

## 6. 回合結束：`@EVENTCOMEND`（`BATTLE_COM.ERB`:685）

戰報 `BATTLE_REPORT`（:692）、心境持續、空中ダッシュ回復、連擊旗標、衣裝更新、量表增減（`TCVARn:6`）、
氣力 0 時解除變身（`TRANSFORM, 0`）、心境變化 `SHINKYOU_CHANGE`、事件戰回合處理 `EVENT_BATTLE_TURNEND_{FLAG:45}`（:981）。

## 7. 結束：`BATTLE_TRAIN_AFTER.ERB@EVENTEND`（:2）

依 `TFLAG:98` 發放：能力上升 `_ABLUP`、修練P `GET_SYUREN`、經驗 `GET_EXP_BATTLE`、金錢 `GET_MONEY`、觸手の欠片 `GET_KAKERA`、
觸手等級 `TENTACLE_LEVEL`、懷孕判定、變身解除、事件戰任務成敗（`EVENT_BATTLE_MISSION_CHECKER_{FLAG:45}`）；
最後 `BEGIN TURNEND`（:536）。

## 8. S05 前需要先解的疑點

- `TFLAG:0`（戰鬥回合數）在 ERB 中找不到遞增處（見 unresolved）。
- 雜魚／クズ市民戰在體力等歸零時的結束路徑（:955 排除了 MOB/CITIZEN）。
