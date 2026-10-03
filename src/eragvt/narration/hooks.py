"""狀態變化行的 hook：地の文函式中「已在 `eragvt.game.battle.sexmsg` 以 Python 移植過」的狀態變化行。

抽取器遇到下表的 `(函式, 行)` 時，照常解析該行但標為 `Hook`：
- 代入・SETBIT（FLAG:900、TFLAG:4／21／23、TENTACLE_SIZE、CFLAG:206、TCVARn:12／25）→ 執行器以「可寫入狀態」模式執行。
- CALL（下表 `HOOK_CALLS` 的函式）→ 呼叫既有的 Python 移植（`gaping`／`syasei`／`ninsin`／`sexcom`）。
其餘任何對非 LOCAL 變數的代入仍是 unsupported（不會被悄悄吞掉）。

每一列：`(函式名, ERB 行號): (原文, sexmsg 中對應的 Python 函式, 該函式註解中涵蓋此行的引用)`。
`tests/test_narration.py::test_hook_table_matches_sexmsg` 檢查：原文與 ERB 一致、引用確實出現在 sexmsg 對應函式的原始碼中、
且這些函式中所有非 LOCAL 代入／狀態 CALL 都在表內。ERB 路徑：`地の文/MESSAGE_SEX_COM.ERB`、`地の文/MESSAGE_SEX_COMSP.ERB`。
"""

from __future__ import annotations

from typing import Optional

HOOK_LINES: dict[tuple[str, int], tuple[str, str, str]] = {
    ("MESSAGE_SEX_COM0", 383): ('SETBIT TFLAG:21,1', "msg_com0", ":380–384"),
    ("MESSAGE_SEX_COM1", 443): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com1", ":437–456"),
    ("MESSAGE_SEX_COM1", 448): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com1", ":437–456"),
    ("MESSAGE_SEX_COM1", 454): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｃ","","単数"', "msg_com1", ":437–456"),
    ("MESSAGE_SEX_COM1", 455): ('TENTACLE_SIZE:0:Ｃ = TENTACLE_SIZE:0:Ｖ', "msg_com1", ":437–456"),
    ("MESSAGE_SEX_COM1", 512): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｃ","繊毛","複数"', "msg_com1", ":511"),
    ("MESSAGE_SEX_COM1", 619): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com1", ":613–665"),
    ("MESSAGE_SEX_COM1", 624): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com1", ":613–665"),
    ("MESSAGE_SEX_COM1", 663): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｃ","","単数"', "msg_com1", ":613–665"),
    ("MESSAGE_SEX_COM1", 664): ('TENTACLE_SIZE:0:Ｃ = TENTACLE_SIZE:0:Ｖ', "msg_com1", ":613–665"),
    ("MESSAGE_SEX_COM1", 713): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｃ","繊毛","複数"', "msg_com1", ":712"),
    ("MESSAGE_SEX_COM1", 827): ('SETBIT TFLAG:21,1', "msg_com1", ":824–828"),
    ("MESSAGE_SEX_COM2", 887): ('FLAG:900 = 1', "msg_com2", ":853"),
    ("MESSAGE_SEX_COM2", 915): ('FLAG:900 = 1', "msg_com2", ":888"),
    ("MESSAGE_SEX_COM2", 950): ('FLAG:900 = 2', "msg_com2", ":916"),
    ("MESSAGE_SEX_COM2", 1023): ('CALL TENTACLE_SYASEI_UP, 100', "msg_com2", ":968–1027"),
    ("MESSAGE_SEX_COM2", 1025): ('TFLAG:4 = TFLAG:4 | ワレメ', "msg_com2", ":968–1027"),
    ("MESSAGE_SEX_COM2", 1027): ('TFLAG:4 = 0', "msg_com2", ":968–1027"),
    ("MESSAGE_SEX_COM2", 1052): ('FLAG:900 = 3', "msg_com2", ":1052"),
    ("MESSAGE_SEX_COM2", 1054): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com2", ":1052"),
    ("MESSAGE_SEX_COM2", 1056): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","","単数"', "msg_com2", ":1052"),
    ("MESSAGE_SEX_COM2", 1212): ('TFLAG:4 = TFLAG:4 - ワレメ', "msg_com2", ":1179–1277"),
    ("MESSAGE_SEX_COM2", 1213): ('TFLAG:4 = TFLAG:4 | 手', "msg_com2", ":1179–1277"),
    ("MESSAGE_SEX_COM2", 1215): ('TFLAG:4 = TFLAG:4 | 胸', "msg_com2", ":1179–1277"),
    ("MESSAGE_SEX_COM2", 1272): ('CALL NINSIN_HANTEI,2,50', "msg_com2", ":1179–1277"),
    ("MESSAGE_SEX_COM2", 1274): ('CALL NINSIN_HANTEI,1,10', "msg_com2", ":1179–1277"),
    ("MESSAGE_SEX_COM2", 1282): ('SETBIT TFLAG:21,1', "msg_com2", ":1279–1283"),
    ("MESSAGE_SEX_COM3", 1523): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","たくさん"', "msg_com3", ":1499–1526"),
    ("MESSAGE_SEX_COM3", 1525): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","複数"', "msg_com3", ":1499–1526"),
    ("MESSAGE_SEX_COM3", 1554): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_com3", ":1527–1557"),
    ("MESSAGE_SEX_COM3", 1556): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","","単数"', "msg_com3", ":1527–1557"),
    ("MESSAGE_SEX_COM3", 1858): ('SETBIT TFLAG:21,1', "msg_com3", ":1855–1865"),
    ("MESSAGE_SEX_COM3", 1861): ('SETBIT TFLAG:21,3', "msg_com3", ":1855–1865"),
    ("MESSAGE_SEX_COM3", 1864): ('SETBIT TFLAG:21,2', "msg_com3", ":1855–1865"),
    ("MESSAGE_SEX_COM4", 1942): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","普通","単数"', "msg_com4", ":1904–1945"),
    ("MESSAGE_SEX_COM4", 1944): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","","複数"', "msg_com4", ":1904–1945"),
    ("MESSAGE_SEX_COM4", 2053): ('SETBIT TFLAG:21,1', "msg_com4", ":2050–2054"),
    ("MESSAGE_SEX_COM5", 2201): ('CALL LOSTVIRGIN', "msg_com5", ":2200–2201"),
    ("MESSAGE_SEX_COM5", 2294): ('SETBIT TFLAG:21,1', "msg_com5", ":2291–2298"),
    ("MESSAGE_SEX_COM5", 2297): ('SETBIT TFLAG:21,3', "msg_com5", ":2291–2298"),
    ("MESSAGE_SEX_COM6", 2340): ('FLAG:900 = 1', "msg_com6", ":2315"),
    ("MESSAGE_SEX_COM6", 2351): ('FLAG:900 = 1', "msg_com6", ":2341"),
    ("MESSAGE_SEX_COM6", 2371): ('FLAG:900 = 1', "msg_com6", ":2352"),
    ("MESSAGE_SEX_COM6", 2376): ('FLAG:900 = 2', "msg_com6", ":2372"),
    ("MESSAGE_SEX_COM6", 2443): ('SETBIT TFLAG:21,1', "msg_com6", ":2440–2444"),
    ("MESSAGE_SEX_COM7", 2469): ('FLAG:900 = 1', "msg_com7", ":2461–2500"),
    ("MESSAGE_SEX_COM7", 2481): ('FLAG:900 = 2', "msg_com7", ":2461–2500"),
    ("MESSAGE_SEX_COM7", 2499): ('FLAG:900 = 1', "msg_com7", ":2461–2500"),
    ("MESSAGE_SEX_COM7", 2535): ('FLAG:900 = 3', "msg_com7", ":2501"),
    ("MESSAGE_SEX_COM7", 2601): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","細い","たくさん"', "msg_com7", ":2588–2604"),
    ("MESSAGE_SEX_COM7", 2603): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","繊毛","たくさん"', "msg_com7", ":2588–2604"),
    ("MESSAGE_SEX_COM7", 2634): ('SETBIT TFLAG:21,1', "msg_com7", ":2631–2635"),
    ("MESSAGE_SEX_COM8", 2660): ('FLAG:900 = 1', "msg_com8", ":2650–2703"),
    ("MESSAGE_SEX_COM8", 2665): ('FLAG:900 = 2', "msg_com8", ":2650–2703"),
    ("MESSAGE_SEX_COM8", 2691): ('FLAG:900 = 3', "msg_com8", ":2650–2703"),
    ("MESSAGE_SEX_COM8", 2696): ('FLAG:900 = 4', "msg_com8", ":2650–2703"),
    ("MESSAGE_SEX_COM8", 2702): ('FLAG:900 = 4', "msg_com8", ":2650–2703"),
    ("MESSAGE_SEX_COM8", 2714): ('FLAG:900 = 5', "msg_com8", ":2704–2757"),
    ("MESSAGE_SEX_COM8", 2719): ('FLAG:900 = 2', "msg_com8", ":2704–2757"),
    ("MESSAGE_SEX_COM8", 2745): ('FLAG:900 = 3', "msg_com8", ":2704–2757"),
    ("MESSAGE_SEX_COM8", 2750): ('FLAG:900 = 4', "msg_com8", ":2704–2757"),
    ("MESSAGE_SEX_COM8", 2756): ('FLAG:900 = 4', "msg_com8", ":2704–2757"),
    ("MESSAGE_SEX_COM8", 2766): ('SETBIT TFLAG:21,7', "msg_com8", ":2764–2767"),
    ("MESSAGE_SEX_COM9", 2794): ('FLAG:900 = 1', "msg_com9", ":2791–2799"),
    ("MESSAGE_SEX_COM9", 2798): ('FLAG:900 = 2', "msg_com9", ":2791–2799"),
    ("MESSAGE_SEX_COM9", 2823): ('SETBIT TFLAG:21,7', "msg_com9", ":2821–2824"),
    ("MESSAGE_SEX_COM10", 2919): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｂ","細い","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2921): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｂ","繊毛","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2929): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","細い","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2931): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","繊毛","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2939): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","細い","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2941): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","繊毛","たくさん"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2950): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｃ","細い","単数"', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2963): ('FLAG:900 = 2', "msg_com10", ":2884–2963"),
    ("MESSAGE_SEX_COM10", 2973): ('SETBIT TFLAG:21,1', "msg_com10", ":2970–2974"),
    ("MESSAGE_SEX_COM11", 3079): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","細い","たくさん"', "msg_com11", ":3066–3090"),
    ("MESSAGE_SEX_COM11", 3081): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","繊毛","たくさん"', "msg_com11", ":3066–3090"),
    ("MESSAGE_SEX_COM11", 3086): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","細い","たくさん"', "msg_com11", ":3066–3090"),
    ("MESSAGE_SEX_COM11", 3088): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","繊毛","たくさん"', "msg_com11", ":3066–3090"),
    ("MESSAGE_SEX_COM11", 3149): ('SETBIT TFLAG:21,1', "msg_com11", ":3146–3152"),
    ("MESSAGE_SEX_COM11", 3151): ('SETBIT TFLAG:21,2', "msg_com11", ":3146–3152"),
    ("MESSAGE_SEX_COM12", 3273): ('SETBIT TFLAG:21,2', "msg_com12", ":3271–3276"),
    ("MESSAGE_SEX_COM12", 3275): ('SETBIT TFLAG:21,7', "msg_com12", ":3271–3276"),
    ("MESSAGE_SEX_COM13", 3359): ('SETBIT TFLAG:21,7', "msg_com13", ":3357–3360"),
    ("MESSAGE_SEX_COM14", 3391): ('FLAG:900 = 1', "msg_com14", ":3388"),
    ("MESSAGE_SEX_COM14", 3395): ('FLAG:900 = 2', "msg_com14", ":3392"),
    ("MESSAGE_SEX_COM14", 3399): ('FLAG:900 = 1', "msg_com14", ":3396"),
    ("MESSAGE_SEX_COM14", 3403): ('FLAG:900 = 1', "msg_com14", ":3400–3404"),
    ("MESSAGE_SEX_SPCOM0", 220): ('SETBIT TFLAG:21,1', "msg_spcom0", ":217–221"),
    ("MESSAGE_SEX_SPCOM1", 419): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_spcom1", ":417"),
    ("MESSAGE_SEX_SPCOM1", 421): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","","単数"', "msg_spcom1", ":417"),
    ("MESSAGE_SEX_SPCOM1", 424): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","普通","単数"', "msg_spcom1", ":417"),
    ("MESSAGE_SEX_SPCOM1", 426): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","","単数"', "msg_spcom1", ":417"),
    ("MESSAGE_SEX_SPCOM1", 581): ('SETBIT TFLAG:21,1', "msg_spcom1", ":578–585"),
    ("MESSAGE_SEX_SPCOM1", 584): ('SETBIT TFLAG:21,3', "msg_spcom1", ":578–585"),
    ("MESSAGE_SEX_SPCOM2", 600): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","","たくさん"', "msg_spcom2", ":599–601"),
    ("MESSAGE_SEX_SPCOM2", 636): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","たくさん"', "msg_spcom2", ":620–644"),
    ("MESSAGE_SEX_SPCOM2", 638): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","太い","複数"', "msg_spcom2", ":620–644"),
    ("MESSAGE_SEX_SPCOM2", 641): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","普通","たくさん"', "msg_spcom2", ":620–644"),
    ("MESSAGE_SEX_SPCOM2", 643): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","太い","複数"', "msg_spcom2", ":620–644"),
    ("MESSAGE_SEX_SPCOM2", 651): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","普通","たくさん"', "msg_spcom2", ":645–654"),
    ("MESSAGE_SEX_SPCOM2", 653): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","太い","複数"', "msg_spcom2", ":645–654"),
    ("MESSAGE_SEX_SPCOM2", 687): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_spcom2", ":655–690"),
    ("MESSAGE_SEX_SPCOM2", 689): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","太い","単数"', "msg_spcom2", ":655–690"),
    ("MESSAGE_SEX_SPCOM2", 775): ('SETBIT TFLAG:21,1', "msg_spcom2", ":772–779"),
    ("MESSAGE_SEX_SPCOM2", 778): ('SETBIT TFLAG:21,3', "msg_spcom2", ":772–779"),
    ("MESSAGE_SEX_SPCOM3", 900): ('SETBIT TFLAG:21,1', "msg_spcom3", ":897–901"),
    ("MESSAGE_SEX_SPCOM4", 949): ('SETBIT TFLAG:21,7', "msg_spcom4", ":947–950"),
    ("MESSAGE_SEX_SPCOM5", 1090): ('SETBIT TFLAG:21,1', "msg_spcom5", ":1087–1093"),
    ("MESSAGE_SEX_SPCOM5", 1092): ('SETBIT TFLAG:21,2', "msg_spcom5", ":1087–1093"),
    ("MESSAGE_SEX_SPCOM7", 1147): ('FLAG:900 = 1', "msg_spcom7", ":1136"),
    ("MESSAGE_SEX_SPCOM7", 1152): ('TCVARn:25 = 0', "msg_spcom7", ":1148–1228"),
    ("MESSAGE_SEX_SPCOM7", 1228): ('FLAG:900 = 2', "msg_spcom7", ":1148–1228"),
    ("MESSAGE_SEX_SPCOM7", 1293): ('FLAG:900 = 3', "msg_spcom7", ":1229–1293"),
    ("MESSAGE_SEX_SPCOM9", 1367): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","たくさん"', "msg_spcom9", ":1366–1372"),
    ("MESSAGE_SEX_SPCOM9", 1369): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","太い","複数"', "msg_spcom9", ":1366–1372"),
    ("MESSAGE_SEX_SPCOM9", 1371): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","極太","単数"', "msg_spcom9", ":1366–1372"),
    ("MESSAGE_SEX_SPCOM9", 1482): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom9", ":1474–1483"),
    ("MESSAGE_SEX_SPCOM9", 1571): ('SETBIT TFLAG:21,3', "msg_spcom9", ":1568–1574"),
    ("MESSAGE_SEX_SPCOM9", 1573): ('SETBIT TFLAG:21,7', "msg_spcom9", ":1568–1574"),
    ("MESSAGE_SEX_SPCOM10", 1588): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","普通","たくさん"', "msg_spcom10", ":1587–1593"),
    ("MESSAGE_SEX_SPCOM10", 1590): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","太い","複数"', "msg_spcom10", ":1587–1593"),
    ("MESSAGE_SEX_SPCOM10", 1592): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ａ","極太","単数"', "msg_spcom10", ":1587–1593"),
    ("MESSAGE_SEX_SPCOM10", 1645): ('SETBIT TFLAG:21,3', "msg_spcom10", ":1642–1648"),
    ("MESSAGE_SEX_SPCOM10", 1647): ('SETBIT TFLAG:21,7', "msg_spcom10", ":1642–1648"),
    ("MESSAGE_SEX_SPCOM11", 1661): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","","単数"', "msg_spcom11", ":1661"),
    ("MESSAGE_SEX_SPCOM11", 1750): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom11", ":1687–1751"),
    ("MESSAGE_SEX_SPCOM11", 1820): ('SETBIT TFLAG:21,1', "msg_spcom11", ":1817–1824"),
    ("MESSAGE_SEX_SPCOM11", 1823): ('SETBIT TFLAG:21,3', "msg_spcom11", ":1817–1824"),
    ("MESSAGE_SEX_SPCOM12", 1904): ('SETBIT TFLAG:21,7', "msg_spcom12", ":1902–1905"),
    ("MESSAGE_SEX_SPCOM13", 2018): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom13", ":2011–2018"),
    ("MESSAGE_SEX_SPCOM13", 2058): ('TCVARn:12 |= 気絶', "msg_spcom13", ":2058"),
    ("MESSAGE_SEX_SPCOM14", 2229): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom14", ":2144–2241"),
    ("MESSAGE_SEX_SPCOM14", 2275): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom14", ":2259–2313"),
    ("MESSAGE_SEX_SPCOM14", 2310): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","普通","単数"', "msg_spcom14", ":2259–2313"),
    ("MESSAGE_SEX_SPCOM14", 2312): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","太い","単数"', "msg_spcom14", ":2259–2313"),
    ("MESSAGE_SEX_SPCOM15", 2350): ('CALL SET_TENTACLE_SIZE_BY_MESSAGE,"Ｖ","太い","単数"', "msg_spcom15", ":2350"),
    ("MESSAGE_SEX_SPCOM15", 2360): ('SETBIT CFLAG:TARGET:206,3', "msg_spcom15", ":2356–2360"),
    ("MESSAGE_SEX_SPCOM13_PRE", 1926): ('TFLAG:23 += 1', "msg_spcom13_pre", ":1926"),
    ("MESSAGE_SEX_SPCOM13_MISS", 2117): ('TFLAG:23 += 1', "msg_spcom13_miss", ":2117"),
}

# S08：幽閉の地の文（`地の文/MESSAGE_PRISON.ERB`）の状態変化行。(函式名, 行): (原文, 意味)。
# FLAG:900 は直後の KOJO_ROOT の「ランダム分岐フラグ」（KOJO_ROOT が 0 に戻す）。TALENT:膨乳改造値 は膨乳化の地の文で加算。
# TS_* は幽閉時の性別変化（TS オプション ON かつオトコのキャラのみ）で未移植 → 実行時に停止（eragvt.game.prison.event.ts_change）。
# UNLOCK_ACHIEVEMENT は実績（GLOBAL）のみ＝何もしない（deviations.md「全域資料」）。
# tests/test_prison.py::test_prison_hook_table_matches_erb が原文一致と「表外の代入が無い」ことを確認する。
PRISON_HOOK_LINES: dict[tuple[str, int], tuple[str, str]] = {
    ("MESSAGE_PRISON_PRISENTENCE_FIRST", 9): ('CALL UNLOCK_ACHIEVEMENT(275,"女性の宿命")', "実績のみ"),
    ("MESSAGE_PRISON_PRISENTENCE_FIRST", 97): ("CALL TS_MtoF, TARGET", "TS（未移植・停止）"),
    ("MESSAGE_PRISON_PRISENTENCE_FIRST", 113): ("CALL TS_NORMAL, TARGET", "TS（未移植・停止）"),
    ("MESSAGE_PRISON_PRISENTENCE_FIRST", 150): ("CALL TS_FtoM, TARGET", "TS（未移植・停止）"),
    ("MESSAGE_PRISON_COM_1", 813): ("FLAG:900 = 1", "口上分岐"),
    ("MESSAGE_PRISON_COM_1", 830): ("FLAG:900 = 32", "口上分岐"),
    ("MESSAGE_PRISON_COM_1", 846): ("FLAG:900 = 22", "口上分岐"),
    ("MESSAGE_PRISON_COM_1", 851): ("FLAG:900 = 12", "口上分岐"),
    ("MESSAGE_PRISON_COM_1", 868): ("FLAG:900 = 3", "口上分岐"),
    ("MESSAGE_PRISON_COM_2", 907): ("FLAG:900 = 1", "口上分岐"),
    ("MESSAGE_PRISON_COM_2", 921): ("FLAG:900 = 32", "口上分岐"),
    ("MESSAGE_PRISON_COM_2", 937): ("FLAG:900 = 22", "口上分岐"),
    ("MESSAGE_PRISON_COM_2", 942): ("FLAG:900 = 12", "口上分岐"),
    ("MESSAGE_PRISON_COM_4", 1031): ("FLAG:900 = 1", "口上分岐"),
    ("MESSAGE_PRISON_COM_4", 1049): ("FLAG:900 = 2", "口上分岐"),
    ("MESSAGE_PRISON_COM_6", 1145): ("FLAG:900 = 1", "口上分岐"),
    ("MESSAGE_PRISON_COM_6", 1184): ("FLAG:900 = 2", "口上分岐"),
    ("MESSAGE_PRISON_COM_6", 1224): ("FLAG:900 = 3", "口上分岐"),
    ("MESSAGE_PRISON_COM_6", 1262): ("FLAG:900 = 4", "口上分岐"),
    ("MESSAGE_PRISON_COM_105", 1760): ("TALENT:TARGET:膨乳改造値 += RAND(10,30)", "膨乳改造値"),
    ("MESSAGE_PRISON_COM_105", 1779): ("TALENT:TARGET:膨乳改造値 += RAND(20,40)", "膨乳改造値"),
}

# S11：いちゃラブ（片思いの告白）の地の文 `地の文/MESSAGE_SEX.ERB@MESSAGE_KATAOMOI_NIGHT` の状態変化行。(函式名, 行): (原文, 意味)。
# Python 側の fallback は `eragvt.game.lovesex.message_kataomoi_night`。
# tests/test_lovesex.py::test_lovesex_hook_table_matches_erb が原文一致と「表外の代入が無い」ことを確認する。
LOVESEX_HOOK_LINES: dict[tuple[str, int], tuple[str, str]] = {
    ("MESSAGE_KATAOMOI_NIGHT", 1559): ("TALENT:交際相手 = 0", "告白を断られる（片思い解消）"),
    ("MESSAGE_KATAOMOI_NIGHT", 1575): ("TALENT:交際相手 += 1", "告白成功（片思い → 彼氏持ち）"),
}

# S13：出産の地の文 `地の文/MESSAGE_NINSIN.ERB@MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN` の状態変化行（子供の性別）。
# Python 側の fallback は `eragvt.game.child.message_birth_daughter_human_origin`。
# tests/test_pregnancy.py::test_ninsin_hook_table_matches_erb が原文一致と「表外の代入が無い」ことを確認する。
NINSIN_HOOK_LINES: dict[tuple[str, int], tuple[str, str]] = {
    ("MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN", 731): ("CFLAG:TARGET:226 = 0", "女の子"),
    ("MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN", 734): ("CFLAG:TARGET:226 = 1", "男の子"),
}

# S28b：特別活動の地の文の状態変化行。(函式名, 行): (原文, 意味)。ERB 路徑：`地の文/特別活動関係/MESSAGE_SEISAN_3_PROSTITUTION.ERB`、
# `地の文/MESSAGE_CITIZEN_TRAIN.ERB`（援助交際の変態プレイから `(TARGET,"男","特別活動")` で呼ばれる）。
# FLAG:900 は直後の KOJO_ROOT の「ランダム分岐フラグ」（KOJO_ROOT が 0 に戻す）。`TARGET=ARG` は呼び出し元が TARGET を渡すので
# 値は変わらない。犬プレイの EXP 加算（:399–403）は `嬲られ体質` 等の条件付き（Python 側の fallback は `eragvt.game.seisan`）。
# tests/test_seisan.py::test_seisan_hook_table_matches_erb が原文一致と「表外の代入が無い」ことを確認する。
SEISAN_HOOK_LINES: dict[tuple[str, int], tuple[str, str]] = {
    ("MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", 127): ("FLAG:900 = 4", "口上分岐"),
    ("MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", 133): ("FLAG:900 = 3", "口上分岐"),
    ("MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", 139): ("FLAG:900 = 2", "口上分岐"),
    ("MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", 145): ("FLAG:900 = 1", "口上分岐"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 191): ("TARGET=ARG", "対象キャラ"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 399): ("EXP:精液経験 += 2 + RAND(2,5)", "獣姦の経験"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 400): ("EXP:絶頂経験 += 3 + RAND(2,5)", "獣姦の経験"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 401): ("EXP:異常経験 += 1", "獣姦の経験"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 402): ("EXP:Ｖ拡張経験 += 2 + RAND(2,5)", "獣姦の経験"),
    ("MESSAGE_CITIZEN_TRAIN_DOG", 403): ("EXP:Ｖ経験 += 3 +RAND(3,6)", "獣姦の経験"),
    ("MESSAGE_CITIZEN_TRAIN_KANCHO", 419): ("TARGET=ARG", "対象キャラ"),
}

# S28c1：自由行動中イベント（`ゲーム内_イベント発生/自由行動中イベント/`）のうち本文中心の関数（地の文扱い：`eragvt.game.pastime._chinobun`）
# の状態変化行。(函式名, 行): (原文, 意味)。函式名は catalog の大文字キー。ERB：`PASTIME_ファッション.ERB`、`PASTIME_運動する.ERB`、
# `PASTIME_学校に行く.ERB`。Python 側の fallback（catalog で実行できないとき）は `eragvt.game.pastime` の `_FALLBACKS`。
# tests/test_pastime.py::test_pastime_hook_table_matches_erb が原文一致と「表外の代入が無い」（＝catalog で実行可能）ことを確認する。
PASTIME_HOOK_LINES: dict[tuple[str, int], tuple[str, str]] = {
    ("PASTIME_FASHION", 346): ("CFLAG:310 += 1", "TS 娘・完全／強制女体化のファッション回数"),
    ("MESSAGE_PASTIME_FITNESSCLUB", 370): ("CFLAG:335 += 1", "フィットネスクラブ回数（変身時ＴＳ）"),
    ("MESSAGE_PASTIME_FITNESSCLUB", 372): ("CFLAG:334 += 1", "フィットネスクラブ回数"),
    ("MESSAGE_PASTIME_MASSAGESALON", 406): ("CFLAG:339 += 1", "マッサージサロン回数（変身時ＴＳ）"),
    ("MESSAGE_PASTIME_MASSAGESALON", 408): ("CFLAG:338 += 1", "マッサージサロン回数"),
    ("MESSAGE_PASTIME_POOL", 447): ("CFLAG:270 = 0", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 450): ("CFLAG:270 = 1", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 453): ("CFLAG:270 = 2", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 456): ("CFLAG:270 = 3", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 464): ("CFLAG:270 = 99", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 467): ("CFLAG:270 = 4", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 470): ("CFLAG:270 = 5", "水着の種類"),
    ("MESSAGE_PASTIME_POOL", 642): ("CFLAG:343 += 1", "プール回数（変身時ＴＳ）"),
    ("MESSAGE_PASTIME_POOL", 644): ("CFLAG:342 += 1", "プール回数"),
    ("MESSAGE_SCHOOL_CLASSWORK_CL", 565): ("EXP:自慰経験 += 1", "授業中自慰"),
    ("MESSAGE_SCHOOL_CLASSWORK_CL", 568): ("EXP:絶頂経験 += 1", "授業中自慰"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 720): ("TALENT:処女 = -1", "処女喪失"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 721): ("CFLAG:206 = 11", "処女喪失の原因"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 747): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 754): ("EXP:絶頂経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 866): ("TALENT:処女 = -1", "処女喪失"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 867): ("CFLAG:206 = 11", "処女喪失の原因"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 915): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 922): ("EXP:絶頂経験 += 5", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 925): ("EXP:フェラ経験 += 3", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 929): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 936): ("EXP:絶頂経験 += 5", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 942): ("EXP:フェラ経験 += 3", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1018): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1025): ("EXP:絶頂経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1184): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1191): ("EXP:絶頂経験 += 5", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1194): ("EXP:フェラ経験 += 3", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1197): ("EXP:射精経験 += 3", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1201): ("EXP:被姦経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1208): ("EXP:絶頂経験 += 5", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1214): ("EXP:フェラ経験 += 3", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1217): ("EXP:射精経験 += 1", "体育の経験"),
    ("MESSAGE_SCHOOL_CLASSWORK_PE", 1317): ("CFLAG:42 = 0", "水泳でインナーを失う"),
    ("MESSAGE_SCHOOL_CLUBACTIVITIES", 1651): ("CFLAG:355 += 1", "部活動回数（変身中）"),
    ("MESSAGE_SCHOOL_CLUBACTIVITIES", 1653): ("CFLAG:354 += 1", "部活動回数"),
}

# hook 化してよい CALL 先 → Python 移植（呼び出し時に import）
HOOK_CALLS = {
    "SET_TENTACLE_SIZE_BY_MESSAGE": ("eragvt.game.battle.gaping", "set_tentacle_size_by_message"),
    "TENTACLE_SYASEI_UP": ("eragvt.game.battle.syasei", "tentacle_syasei_up"),
    "NINSIN_HANTEI": ("eragvt.game.battle.ninsin", "ninsin_hantei"),
    "LOSTVIRGIN": ("eragvt.game.battle.sexcom", "lostvirgin"),
    "UNLOCK_ACHIEVEMENT": ("eragvt.game.battle.core", "unlock_achievement"),
    "TS_MTOF": ("eragvt.game.prison.event", "ts_change"),
    "TS_NORMAL": ("eragvt.game.prison.event", "ts_change"),
    "TS_FTOM": ("eragvt.game.prison.event", "ts_change"),
}

# hook の代入で書き込んでよい変数
HOOK_WRITABLE = {"FLAG", "TFLAG", "TENTACLE_SIZE", "CFLAG", "TCVARN", "TALENT", "EXP", "TARGET"}


def match_hook(func: str, line: int, text: str) -> Optional[str]:
    prow = (
        PRISON_HOOK_LINES.get((func, line))
        or LOVESEX_HOOK_LINES.get((func, line))
        or NINSIN_HOOK_LINES.get((func, line))
        or SEISAN_HOOK_LINES.get((func, line))
        or PASTIME_HOOK_LINES.get((func, line))
    )
    if prow is not None:
        return f"{func}:{line}" if prow[0] == text.strip() else None
    row = HOOK_LINES.get((func, line))
    if row is None:
        return None
    if row[0] != text.strip():
        return None  # 原文が変わっていれば hook にしない（→ unsupported のまま）
    return f"{func}:{line}"
