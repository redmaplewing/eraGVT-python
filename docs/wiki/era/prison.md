# 幽閉（敗北 → 幽閉中事件 → 脫出／救出・洗腦・悪堕ち・取り込まれ）

ERB 路徑相對 `source/earGVP/ERB/`，引擎相對 `reference/emuera-1824/Emuera/`。Python：`eragvt.game.prison`（event／commands／
event_palam）、`eragvt.game.party`、`eragvt.game.tattoo`、`eragvt.game.ending`、`turnend.inmon_recovery`。

## 相關 CFLAG（依 `CSV定数定義/CFLAG.ERH` 與原文註解）

| CFLAG | 意義 | 依據 |
|---|---|---|
| 0 | 狀態：-1 救出直後、0 無事、1 幽閉、2 洗脳、3 悪堕ち、4 クズ監禁、9 死亡（取り込まれ）、10 出産直前、11 育児中 | CFLAG.ERH:13–22 |
| 20 | 幽閉者的敵種：0 ボス、1 ラスボス、2 悪堕ちキャラ（＝敗北時的 FLAG:10） | BATTLE_COM_AFTER.ERB:1031–1034、PRISON.ERB:49–60、COMMON_TENTACLE_DATA.ERB:315–343 |
| 21 | 幽閉者番號（ボス 1–7；悪堕ちキャラ則為其固有番號 CFLAG:240） | 同上 |
| 23 | 遭遇率上升效果（幽閉結局時歸零） | PRISON.ERB:386／:423 |
| 30 | 汚染度（超過 CHECK_CONTAMINATION 的閾值即陥落） | PRISON.ERB:167、:430–443 |
| 31 | 幽閉中被姦次數（每回合 1 次，`/2` 為幽閉日數） | PRISON.ERB:165、SHOP_SHOW_SITUATION_LIST.ERB:84 |
| 32 | 淫紋：進行度 ×10^16 + 追加淫紋 bit ×10^14 + Σ 部位花紋 ×100^部位 | CHARA_TATTOO.ERB:44–237 |
| 202–205 | Ｖ拡張・Ａ拡張・Ｖ産卵・Ａ産卵 的首次旗標（異常経験 +1） | PRISON_COM101／102／200／201 |
| 220 | 本次幽閉產下的子触手數（30% 機率被子触手侵犯） | PRISON.ERB:111–113 |
| 999 | 隊伍成員（SET_PARTYMEMBER 設 0、RECOVER_TO_PARTY 設 1） | SET_PARTYMEMBER.ERB:22–26 |

設定：`CONFIG_CHECK_PRISON_F(n)` = FLAG:804 bit n（基本セット FLAG:804 = 1 → 只有 bit0：允許 TS）。
bit1 洗脳／悪堕ち、2 苗床化者改為取り込み、3 嬲られ体質・非戰鬥員不陥落、4 容貌變化、9 悪堕ち優先。
`CONFIG_CHECK_MANIAC_F(n)` = 1 − FLAG:850 bit n（基本セット全為 1）：6 淫紋、7 多部位、9 救出後仍進行、10 與汚染度連動、14 リョナ。

## 流程

```
戰鬥敗北 BATTLE_COM_AFTER.ERB:1031–1043  CFLAG:0=1, 20=FLAG:10, 21=FLAG:11, 幽閉経験+1, FLAG:799-1
→ EVENTEND 敗北分岐 → @EVENTTURNEND
   :19 SET_PARTYMEMBER：離隊者以 SHIFTBACK_CHARA 移到最後（RELATION 的列一起轉；SWAPCHARA 不調整 TARGET）
   :52 RECALC_PARTYMEMBER：CFLAG:0 == -1 → AFTER_RESCUED，否則 → INMON_RECOVERY
   :103 PRISON：對每個 CFLAG:0 == 1 的角色設 TARGET 後執行 PRISON_EVENT（TARGET 不還原）
```

**PRISON_EVENT（PRISON.ERB:38–427）**
1. 地の文：TS 對象（オトコ＋TS 選項）／首次被姦（幽閉経験 ≤ 1 → FIRST，否則 START）／一般（PRISENTENCE）。
2. SHIELD:0–3 = BASE:30–33 > 0。
3. ISHOLE 時：子触手 30% → COMABLE 7，否則該ボスの `PRISON_ROUTINE`（各ボスの機率表）→ 回傳 0 時用通用表（:122–158，每 12%）。
   被姦経験 +1、CFLAG:31 +1、CFLAG:30 += 3 + RAND:4（神器の担い手 +3、闘争本能 +6）。
   陥落旗標 = 幽閉中 且（汚染度 > CHECK_CONTAMINATION 或 完堕ち）。有触手の虜 則處理淫紋（顯示＋SAVE_TATTOO）。TRANSFORM 0。
4. 脫出：CFLAG:31 > 10 且（ソロ且未陥落 或 サンドボックス）且 RAND:4 == 0 → 體力等歸 0、各 CFLAG 歸 0、AFTER_RESCUED。
5. 末路１（陥落且洗脳選項 ON…）：無触手の虜 → 洗脳（CFLAG:0=2）；有 → 悪堕ち（3、陥落経験、CFLAG:41=401、追加淫紋、容貌變化）。
   ソロ → ENDING_4。經驗值 20／40 ×(5+Lv)+RAND。
6. 末路２（未陥落而 CFLAG:31 > 19，且洗脳選項 OFF 等）→ 取り込まれ（CFLAG:0=9、苗床化；リョナ 時加四肢欠損・繁殖袋）。ソロ → ENDING_5。

**幽閉指令（PRISON_COMn）** 共通：`VARSET LOCAL`、TFLAG:10 = n、汚染度增加、INCEST_F → 近親交配、依感覺 LV 表決定珠（LOCAL:0–11）
與經驗（LOCAL:100+n = EXP:n）、PALAM_VABCestimate、處女喪失、地の文、COMMON_PRISON（UP → EVENT_PALAM_UP）、
COMMON_PRISON_EXP_SH（×9＋RAND、超過 20 壓縮、依結界合併）、PRISON_GAPING、COMMON_PRISON_EXP（顯示並加算）、_ABLUP 1、NINSIN_HANTEI。
PRISON_COMABLE 依身體（男の娘・オトコ・聖処女・經驗不足）與部位結界替換指令（結界 → `GOTO SHIELDED`，在無結界部位中 RAND）。

**出口**
- 救出：擊破同一ボス（FLAG:10／11）時，被其幽閉／洗脳的角色 CFLAG:0 = -1（BATTLE_COM_AFTER.ERB:203–262）。
  戰鬥指令 15「救出する」（COMF15.ERB）：在同ボス戰且對方油斷時成功 → TFLAG:19 = 1，撤退成功時 KYUSHUTU_SUCCESS（-1）。
- AFTER_RESCUED（回合結束時）：治療、TRANSFORM 0、改為休憩、淫紋 ×7/10、懷孕 → 出産直前，其餘 → RECOVER_TO_PARTY（有空位則回隊）。
- 救出後淫紋（INMON_RECOVERY）：有触手の虜 則每回合進行，達 100 時以存活ボス為支配者而悪堕ち（変身能力 ≥ 0）／自行被幽閉。

## 照原作移植的怪處

- EVENT_PALAM_UP 的迴圈只到 UP:0–11（習得〜恐怖 不 ×9），幽閉中 UP:0–11 被「補正 %／100」**覆寫**（:134–140）。
- 恥情加成的絶頂次數看的是從未代入的 LOCAL:100–103（恆為 ×1）。巨乳 補正加在 快Ｖ（:220–229）。
- PRISON_GAPING 的回傳值包含 ARG:2／3，所以 LOCAL:151／152 變 2 倍。PRISON_COM102 的恥情表 :105 代入 LOCAL:8。
- `今回陥落するフラグ` 與 PRISON_EVENT 的 LOCAL 是靜態的（ISHOLE == 0 跳過時沿用上次值；:175 的 LOCAL:2 是上次淫紋判定值）。
- SET_PARTYMEMBER 在 SHIFTBACK 後仍前進到 CCOUNT+1（遞補上來的角色本輪不判定）。
- AFTER_RESCUED:23 寫的是 `FLAG:32 = 0`（不是 CFLAG）。SHOP_SHOW_SITUATION_LIST 不還原 FLAG:11。
- TFLAG:9（救出時間切れ）全作沒有代入處（grep）→ KYUSHUTU_TIMEUP 的地の文不會出現。

## 三種TS與首次事件（S70，W03／B05）

原生邏輯位於`game/trans_sex.py`。`ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF:4–173`、
`@TS_FtoM:179–346`、`@TS_NORMAL:352–925`保持逐題INPUT，不插入SIZE_SETTING或代按。
`ERB/地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST:97／113／150`三hook共用此實作。
`event_turnend → prison → prison_event → _msg_first`均以yield from傳遞；catalog用既有run_event_gen，Null按相同條件分派。

| 函式 | 形態與數值 | 外貌輸入 |
|---|---|---|
| TS_MtoF | 必要時先變身；清體格／胸差值、BASE年齡取MAXBASE；兩次AIRPLUS間沒有裝備改動；性別變化1、TS=-1；有曲線只重算通常尺寸 | 髮型、髮／瞳／膚色均逐題選擇通常形態保留或取變身形態 |
| TS_FtoM | 必要時先變身；性別變化10、TS=-1；MAXBASE年齡取BASE；按原式讀通常體格、清差值、複製外見；有曲線只重算變身尺寸 | 髮型改通常形態，其他三組顏色改變身形態；不可反向統一 |
| TS_NORMAL | 先解除變身；通常胸／體格／外見；有變身能力且無TS時另詢問變身值；有曲線依序重算變身→通常 | 髮型改通常；每組顏色先通常後條件式詢問變身，前題使兩者相等時後題消失 |

原先CFLAG1>0只記為TRANS=1，結尾回到1；普通形態則維持0。成功恢復原TARGET、RETURN1。
TS_NORMAL普通形態已為女性時，原文:357–362先令TARGET=ARG再錯誤PRINTW／RETURN0，**沒有恢復TARGET**；照原作保留。
TS_NORMAL:566–572的部分胸差值及:628–631的體格差值採相加，照原式保留。
「配合另一形態」的普通胸／普通體格分支沒有對應賦值，不能自行補清零。
外見顯示1–6以外走ELSE「普通」；這是原文fallback，不是額外驗證規則。

引擎依據：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`的INPUT只寫RESULT0；
`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023`與
`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740`的RETURN只覆寫提供的格；
`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`函式終端只寫RESULT0=0。
尺寸共用既有GENERATE_CHAR_SIZE，保留RESULT1–7；RESULT8與RESULTS尾值不清除。

`tests/test_trans_sex.py`68案使用全新25歲兩形態，涵蓋選項／無效值、尺寸／尾值、原變身狀態、
Null／catalog三種真hook及完整EVENTTURNEND恢復到SHOP（seed70、結界前態隔離妊娠，未mock下游）。
初次六檔定向362通過，文字修正後四檔定向253通過；`tmp/s70/browser_fixture.py`是Null／臨時存檔的首次事件TS函式邊界，
不是自然幽閉全流程。主代理真瀏覽器、全pytest及正式500紀錄見STATUS；未宣稱整列B05完成。
TS選單尾端全形空白依原文保留，含`ERB/ヒロイン関連/TRANS_SEX.ERB@TS_NORMAL:642／682`通常／變身後[6]的不同尾空白；文字邊界測試直接取原文比對。舊PRINTW等待差異仍見既有[WAIT偏離](../bridge/deviations.md)。

## 剩餘範圍

兩隻末王、悪堕ち幽閉、容貌變化／回復皆已接；資料分派guard仍依PLAYABILITY歸W05核對。
S71已接`battle/ninsin.py@ninsin_flag`／`@ninsin_ts_fix`、幽閉命令與routine的輸入續行；`tentacle_access_prison`的NAME／PALAM_HOSEI保持同步，PRISON_ROUTINE由`prison_routine`等待後回傳（詳[妊娠](pregnancy.md)）。整個生命週期仍未完成，
SUPART_BLOOD仍W05；女體受容與裝備相依仍W03。W02經歷既有範圍阻塞不因本項解除。
