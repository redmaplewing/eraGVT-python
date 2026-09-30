# 拡張度與いちゃラブセックス（S11）

ERB 路徑相對 `source/earGVP/ERB/`，引擎路徑相對 `reference/emuera-1824/Emuera/`。

## 1. 拡張度（`ゲーム内_戦闘処理/GAPING.ERB`，Python：`eragvt.game.battle.gaping`）

### 變數

| 變數 | 意義 | 寫入處 |
|---|---|---|
| CFLAG:34 | 體型成長曲線（≠ 0 才有拡張系統） | GENERATE_BODYLINE、CHARA_SIZE_DEFAULT、`CHARA_MAKE_DEFAULT.ERB`:980（汎用キャラ = 1）。初期セットは 0 |
| CFLAG:35／36 | Ｖ／Ａ拡張度（point） | V_GAPING／A_GAPING（++）、PRINTFORM_GAPING_NOW（初期值）、CALC_GANGBANG、MESSAGE_BATTLE:1802（未移植處） |
| EXP:Ｖ拡張経験／Ａ拡張経験 | 拡張經驗 | GET_*_GAPING_EXP（OPTION 0）、COMMON_PRISON_EXP（幽閉） |
| TENTACLE_SIZE:0／1:部位 | 觸手 1 本的粗細／合計（mm） | SET_TENTACLE_SIZE*（S06） |

rank（`GAPING_RANK`:81–140）＝拡張度的下限表 5,15,25,40,60,85,115,155,205,265,335,465,635,765,935,1065,1205 → 0〜17；
`GAPING_SIZE`:342–427 把拡張度換成 mm（依身長 BASE:43／腰囲 BASE:47 與變身狀態，GET_HEIGHT／GET_HIP:584–639）。

### 流程

- 戰鬥：`PALAM_UP.ERB@PALAM_CALC_GAPING`:771–800（PALAM_UP:92 每次）→ TFLAG:1 == 0 時：
  1. `FLAG:700 > 0 && CONFIG_CHECK_MANIAC_F(16) == 1 && CFLAG:34 > 0` → `PRINT_TENTACLE_SIZE, UP:快Ｃ〜快Ｂ`（觸手 rank 表示）。
  2. Ｖ／Ａ插入中（`TENTACLE_SIZE:1:部位 > 0 && INSERT & 部位`）→ GET_*_GAPING_EXP(GAPING_SIZE_TO_POINT) → V_GAPING／A_GAPING，
     增加量 > 0 且 MANIAC(16) 時印「　膣径：＋x.y cm」。
- 幽閉：`PRISON_GAPING`:1298–1339（各 PRISON_COMn 的末尾）：同上，但 GET_*_GAPING_EXP 用 `OPTION = 1`（只回傳值，
  經驗由 COMMON_PRISON_EXP 加算）。S08 的 Python 誤傳 OPTION 0（CFLAG:34 = 0 時無影響），S11 修正。
- 既定コンフィグ：FLAG:850 = 0 → MANIAC(16)（拡張度表示）＝1、MANIAC(17)（極端な拡張の抑制なし）＝1、MANIAC(20)＝1。

### V_GAPING／A_GAPING（:851–998）

ARG（GAPING_SIZE_TO_POINT＝觸手 rank − 自身 rank，插入中且觸手較粗再 +3）的**平方**次迴圈，每次
`UPRATE > RAND:10000` 則拡張度 +1。UPRATE = 2500 − (POWER(拡張度,2)/150 + rank×100) × 年齢係數 / 20 + 經驗補正 ± 素質、
ARG ≥ 5／6／7／8 加 500／1000／2000／4000，LIMIT（V：50–9999、A：500–9999）。MANIAC(17) == 0 時 ≥ 154 就 RETURN、
UPRATE /3、>110 壓回 110。回傳 GAPING_SIZE 差（mm；V 在処女時 0）。

### 照原作移植的怪處（deviations.md「原作行為」S11）

- **CFLAG:35／36 的初期值只在「顯示拡張度」時設定**：`PRINTFORM_GAPING_NOW`:800–808（年齢等 → 20 前後，再以經驗×10 跑 V_GAPING）。
  呼叫者只有戰鬥畫面的 `SHOW_STATUS_PALAM`（需 `CONFIG_CHECK_SCREEN_F(5)`，FLAG:801 bit 5；既定 FLAG:801 = 1 → 不顯示）
  與ステータス畫面 PAGE5（`[800]`，未移植）。所以不開ステータス畫面時拡張度從 0（rank 0＝繊毛）開始，第一次被插入就
  一口氣上升（實測 0 → 55，＋3.8 cm）。全 ERB grep `CFLAG…:35／36` 的代入只有上表各處。
- GET_V／A_GAPING_EXP 的 LOCAL 是靜態（`GameData/Variable/VariableToken.cs`:1712–1737）且 ARG < 3 時不代入 →
  沿用上次值（例：上次 2 → 這次 ARG 0 也 +2）。
- V_GAPING／A_GAPING／GET_*_GAPING_EXP 的早期 RETURN（ISMALE・CFLAG:34 == 0・ARG == 0・抑制上限）不還原 TARGET（`TARGET = TAR` 後直接
  RETURN）。PRINTFORM_GAPING_NOW 對 TARGET 以外的角色呼叫時，經驗 0 → TARGET 會變成該角色。
- GAPING_RANK_STR 的 LOCALS 是靜態：未知的 ARGS 回傳上次值。

### 表示

- `PRINT_TENTACLE_SIZE`／`PRINTFORM_GAPING_NOW` 用 HTML_PRINT：`TextOutput.html_print`（獨立一行、`[n]` 不變按鈕、
  `<nonbutton title>` 變成 Part.title＝Web 的 tooltip；`GameView/EmueraConsole.Print.cs@PrintHtml`:344–357）。
- PRINTFORM_GAPING_NOW 已移植但目前沒有可到達的呼叫者；`train.show_status` 在 FLAG:801 bit 5 時停止（到達前需先移植コンフィグ）。

### 未移植（停止）

- `MESSAGE_SEX_SPCOM7`:1234–1279 羞恥プレイの「[1]映像を見る」：INPUTS 已接（`sexmsg.msg_spcom7` generator），輸入 "1" 進
  `MESSAGE_SEX_VIDEO_SITE_Window`（`地の文/MESSAGE_WindowLibrary_VideoHostSite.ERB`，1473 行的視窗描畫＋GOTO／INPUTS 迴圈）→ 停止。
- 除錯表示（FLAG:999）、PREGNANT_SOURCE_NINSIN:566 出產時的 V_GAPING、CALC_GANGBANG、TRANS_SEX 等（各系統本體未移植）。

## 2. いちゃラブセックス（`ゲーム内_イベント発生/強制発生イベント/FORCE_いちゃラブセックス.ERB`，Python：`eragvt.game.lovesex`）

呼叫：`SHOP_TURNEND.ERB@EVENTTURNEND`:112（夜 TIME == 1）。`turnend.event_turnend` 因此改為 generator。

### LOVESEX_NIGHT（:5–96）的條件（每名 CFLAG:999 ≠ 0 的角色，TARGET 逐一切換、最後還原）

1. 生存（CFLAG:0 == 0）、疲勞 CFLAG:99 < 30。
2. TALENT:交際相手（Talent.csv:202：1 片思い／2 彼氏持ち／3 婚約／4 人妻／5 未亡人）1–4；片思いは再 `RAND:10 > 4` 就跳過（‖ 短絡）。
3. ISHOLE、男性需 Ａ感覚 ≥ 2；聖処女需 奉仕＋精液中毒＋Ａ感覚 ≥ 3；ISMANLY 的片思い跳過。
4. 処女：DAY < 天數（彼氏 12／婚約 6／人妻 3，學生 1–4 另加 16／8／4／2）時 `RAND:4 != 0` 跳過。
5. 機率 LOCAL:1 = 欲望×5 + 精液中毒×2 + 奉仕（1–5 → 15/20/25/30/35），`RAND:100 < LOCAL:1`。
   預設開局 ABL 全 0 → 機率 0，幾乎不發生（S10 的停止是條件判定前就停）。
6. 片思い → `MESSAGE_KATAOMOI_NIGHT`（RAND:100 ≥ 95 失戀 交際相手 = 0、≥ 65 保留、其餘 +1）；其他 → MESSAGE_LOVESEX_NIGHT →
   LOVESEX_KIND → `_ABLUP, 0` → PRINTW → VARSET PALAM。

### LOVESEX_KIND／SEX_V／SEX_A

- KIND：VARSET NOWEX、`RAND:10`：淫壷且 > 5 → SEX_V 一次（之後的 SEX_V 為二回目 ARG:1 = 1）；淫尻 → SEX_A；Ａ感覚 ≥ 2 的女性
  `RAND:100 ≥ 50` → SEX_V、否則 SEX_A。
- SEX_V：快Ｃ／Ｖ／Ｂ 依感覺 Lv 表、処女 → 処女 = −1・CFLAG:206 = 5・苦痛 2500、技巧倍率、PALAM_VABCestimate、地の文、
  屈服・恥情（露出癖）、欲情・習得（奉仕）、`PALAM_CAL`（體力消耗 150）；非ゴム → CFLAG:218++、AFTER_PILL(TARGET, 75, 愛する人)、
  女性 → `NINSIN_HANTEI, 6, 800, 愛する人`（DIM.ERH:256 `愛する人 = -3` → PAPA_ID −3 = 一般人分岐 :93–96，S11 移植）。
- 地の文 MESSAGE_SEX_V 的処女文（:1301）在 SEX_V:221 把処女改成 −1 之後才判定 → 非聖処女不會出現（原作行為）。
- SEX_V_CONDOM（CONFIG_CHECK_EVENT_F(6)，既定 OFF）：靜態 `イチャックス回数` > RAND:3+2+交際中人數 → 詢問生セックス（INPUT）。
- AFTER_PILL（`PREGNANT_SOURCE_NINSIN.ERB`:898–957，CONFIG_CHECK_OTHER_F(3)，既定 OFF）：$500 服用（INPUT）。
- 受精成立（NINSIN_HANTEI:140 以降）仍停止。

### 地の文

catalog 執行 4 函式；`MESSAGE_KATAOMOI_NIGHT` 的 TALENT 代入（:1559、:1575）登記在 `narration/hooks.py` 的 `LOVESEX_HOOK_LINES`。
Null 時的 fallback 只照 ERB 順序抽 RAND（MESSAGE_SEX_V:1315／1352、SEX_A:1419／1429、KATAOMOI:1547）並做 KATAOMOI 的交際相手變化，
亂數序列與 catalog 路徑一致。

### 靜態變數與讀檔

LOCAL 與非 SAVEDATA `#DIM`（イチャックス回数、GET_*_GAPING_EXP 的 LOCAL…）在 LOADGAME 時重設（`GameData/Variable/VariableEvaluator.cs`:2174、2340
`SetDefaultLocalValue`）→ 放在不存檔的 `st.temp.locals` 與原作一致。
