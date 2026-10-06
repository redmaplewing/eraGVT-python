"""衣装の戦闘処理：`武器と衣装/衣装関連/CLOTH_BATTLE.ERB` と `CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI`。

路徑相對 `source/earGVP/ERB/`。`CLOTH_NO_INNER` 等（DIM.ERH:139–143）は `state.temp.cloth` に置く
（キー：0 NO_INNER、1 OUTER_PER、2 OUTER_DEF、3 INNER_PER、4 INNER_DEF）。
"""

from __future__ import annotations

import re

from ..action import Ctx, kojo_root, print_transcallname
from ..era import div, limit
from ..tentacle import enemy_type_check
from .core import P_V_GUARD, percent_cal

NO_INNER, OUTER_PER, OUTER_DEF, INNER_PER, INNER_DEF = 0, 1, 2, 3, 4
DEFAULT_OUTER_DEF = 75  # DIM.ERH:150
DEFAULT_INNER_DEF = 50  # DIM.ERH:151

# `@CLOTH_STATUS_{ID}` が SAVESTR:0 に入れる補正文字列（衣装関連/CLOTHDATA*.ERB から抽出）。
# イベント専用装備（990–992）は `raid.battle_event_cloth_status`（S20）。
CLOTH_STATUS: dict[int, str] = {
    0: 'SLOT-1,HP0,def0,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:73
    100: 'SLOT-1,HP100,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:84
    101: 'HP100,KOUGEKI110@120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:96
    102: 'HP110,KOUGEKI100@110,BOUGYO110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:277
    103: 'HP90,KOUGEKI100@110,BINSYOU110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:522
    104: 'HP120,LIQUID100@70,TAIRYOKU75,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:688
    105: 'HP100,WAVE100@40,KIRYOKU75,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:927
    106: 'HP100,DEF!,CRITICAL0@5,SEITAISEI80,NOINNER!,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:1119
    107: 'HP100,YUDAN120,KOUGEKI100@105,BOUGYO100@105,BINSYOU100@105,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:1364
    108: 'HP120,YUDAN120,SEITAISEI100@80,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:1541
    109: 'HP90,CHISEI110,KOUGEKI100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:1710
    110: 'HP70,BINSYOU130,NOINNER1,DEF35,SHYNESS130,BOUGYO100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:1890
    111: 'HP110,YUDAN130,NOINNER1,DEF25,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:2044
    112: 'HP100,KOUGEKI110,CRITICAL3,HIT0@15,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:2228
    113: 'HP100,HEALUP50,BOUGYO100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:2412
    114: 'HP130,LIQUID80,WAVE60,KOUGEKI100@105,BOUGYO100@105,BINSYOU100@105',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:2570
    115: 'HP100,DEF!,CRITICAL5,YUDAN110,AIRPLUS0@1,NOINNER!',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:2862
    116: 'HP110,BOUGYO110,CRITICAL3,AVOID0@15',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3122
    117: 'HP80,DEF!,AIRPLUS1,SHYNESS110,KOUGEKI100@110,BINSYOU100@110,NOINNER!',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3303
    118: 'SLOT-1,HP120,DEF50,AIRPLUS1,NOINNER1,BOUGYO100@110,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3509
    119: 'HP120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3522
    120: 'HP120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3738
    121: 'HP100,BOUGYO110@120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:3996
    122: 'HP80,KOUGEKI120@130,BOUGYO80,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4128
    123: 'HP80,BINSYOU110@120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4315
    124: 'HP70@140,BOUGYO110,LIQUID70,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4510
    125: 'HP100,TAIRYOKU75,KOUGEKI100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4733
    126: 'SLOT-1,HP100,KIRYOKU75,KOUGEKI100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4886
    127: 'SLOT-1,HP100,KOUGEKI120@130,BINSYOU80,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4898
    128: 'SLOT-1,HP120,BOUGYO120@130,BINSYOU80,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4910
    129: 'SLOT-1,HP120,CRITICAL4@8,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4922
    130: 'HP70,HEALUP50,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:4934
    131: 'HP110,EXBOOST30,CRITICAL0@5,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5109
    132: 'HP100,HEALUP50,CHISEI100@120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5251
    133: 'SLOT-1,HP50@125,YUDAN150,SHYNESS130,DEF60,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5440
    134: 'SLOT-1,HP120,CRITICAL5,BINSYOU100@120,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5452
    135: 'SLOT-1,HP140,BOUGYO120@130,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5464
    136: 'SLOT-1,HP160,AIRPLUS1,NOINNER1,DEF50,SHYNESS130,KOUGEKI100@110,BOUGYO100@110,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5476
    137: 'HP130,KOUGEKI110,CRITICAL5,EXBOOST0@30,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5488
    138: 'HP150,KOUGEKI120,BOUGYO120,BINSYOU50,EXBOOST0@30,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5678
    139: 'HP100,CHISEI120,AIRPLUS1,EXBOOST0@30,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:5838
    140: 'HP120,BINSYOU110,TAIRYOKU75,KIRYOKU75,EXBOOST0@30,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6005
    141: 'HP100,YUDAN130,BOUGYO100@125,BINSYOU100@125,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6162
    142: 'HP100,YUDAN130,KOUGEKI100@125,CHISEI100@125,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6335
    143: 'HP80,BINSYOU120@130,BOUGYO80,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6492
    144: 'HP80,KOUGEKI110@120,BINSYOU110@120,BOUGYO80,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6658
    145: 'HP120,AIRPLUS1,WAVE40,NOINNER1,DEF35,SHYNESS130,KOUGEKI100@110,BOUGYO100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6810
    146: 'HP100,LIQUID70,KOUGEKI100@110,BOUGYO100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:6958
    147: 'HP100,WAVE70,KOUGEKI100@110,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:7281
    148: 'HP90,YUDAN140,BOUGYO100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:7511
    149: 'HP80,EXBOOST30,WAVE40,DEF80,SHYNESS110,KOUGEKI100@110,CHISEI100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:7721
    150: 'HP90,YUDAN140,BINSYOU100@110,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:7904
    151: 'HP100,TAIRYOKU75,KIRYOKU75,CHISEI100@110,CRITICAL0@5',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:8097
    152: 'HP100,YUDAN130,LIQUID70,NOINNER1,AIRPLUS0@1',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:8327
    153: 'HP90,DEF!,AVOID010,CRITICAL3,KOUGEKI100@110,BINSYOU100@110,NOINNER!',  # 武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB:8511
    196: 'HP35,KOUGEKI500@800,BINSYOU100@30,YUDAN200,LIQUID200,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_特殊.ERB:15
    197: 'SLOT-1,HP90,CHISEI130,KOUGEKI50,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_特殊.ERB:219
    198: 'SLOT-1,HP45,DEF70,YUDAN250,SHYNESS150,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_特殊.ERB:230
    199: 'HP-1,KOUGEKI!,BOUGYO!,BINSYOU!,CHISEI125,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_特殊.ERB:243
    200: 'SLOT3,HP120,DEF50,TAIRYOKU90,KIRYOKU90,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:10
    201: 'SLOT4,HP100,TAIRYOKU90,KIRYOKU90,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:22
    202: 'SLOT5,HP80,DEF25,TAIRYOKU90,KIRYOKU90,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:34
    299: 'SLOT2,HP-1,DEF25,TAIRYOKU90,KIRYOKU90,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:48
    300: 'SLOT-1,HP80,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:36
    301: 'HP80,YUDAN110,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:60
    302: 'HP80,SEITAISEI85,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:264
    303: 'HP100,YUDAN110,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:467
    304: 'HP60,YUDAN120,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:672
    305: 'HP70,LIQUID70,SHYNESS80,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:880
    306: 'HP90,LIQUID90,SHYNESS20,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1122
    307: 'SLOT-1,HP80,ANTIBUP20,CRITICAL2,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1205
    308: 'SLOT-1,HP120,ANTICUP10,SHYNESS60,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1216
    309: 'HP80,CRITICAL4,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1227
    310: 'HP70,YUDAN110,SEITAISEI85,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1298
    311: 'SLOT-1,HP110,SEITAISEI85,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1488
    312: 'HP90,YUDAN105,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1499
    313: 'HP120,YUDAN90,ANTICUP10,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1728
    314: 'HP120,YUDAN25,ANTICUP10,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1897
    397: 'SLOT-1,HP90,AVOID!,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:1988
    398: 'SLOT-1,HP40,ANTICUP10,YUDAN150,SEITAISEI95,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:2011
    399: 'SLOT-1,HP80,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:2022
    400: 'SLOT-1,HP-1,',  # 武器と衣装/衣装関連/CLOTHDATAインナー.ERB:49
    401: 'SLOT1,HP-1,DEF25,KOUGEKI120,TAIRYOKU90,KIRYOKU110,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:61
    402: 'SLOT4,HP-1,DEF5,KOUGEKI150,TAIRYOKU90,KIRYOKU110,SHYNESS150,NOINNER1,',  # 武器と衣装/衣装関連/CLOTHDATAアウター_変身専用.ERB:77
}

_ADD_MODES = ("CRITICAL", "ANTIBUP", "ANTICUP", "HEALUP", "EXBOOST", "AIRPLUS", "HIT", "AVOID")


def _toint(s: str) -> int:
    """TOINT（GameData/Function/Creator.Method.cs@ToIntMethod:2357–）：数字列以外は 0。"""
    return int(s) if re.fullmatch(r"[+-]?[0-9]+", s) else 0


def _find(s: str, word: str, start: int) -> int:
    """STRFIND（ASCII 文字列なのでバイト位置＝文字位置）。"""
    return s.find(word, max(start, 0))


def _substring(s: str, start: int, length: int) -> str:
    """SUBSTRING（_Library/LangManager.cs@GetSubStringLang:40–：length < 0 は末尾まで）。"""
    if start >= len(s) or length == 0:
        return ""
    if length < 0:
        return s[start:]
    return s[start : start + length]


def figure_split(value: int, n: int) -> int:
    """`汎用関数/FIGURE_SPLIT.ERB@FIGURE_SPLIT`：n 桁目（C# の `/`・`%`）。"""
    for _ in range(max(n - 1, 0)):
        value = div(value, 10)
    return value - div(value, 10) * 10


def _special_hosei(ctx: Ctx, cid: int, mode: str) -> int:
    """CLOTHDATAアウター_通常.ERB@CLOTH_HOSEI_DEF_106:1124–1140、
    @CLOTH_HOSEI_DEF_115:2866–2882、@CLOTH_HOSEI_DEF_117:3308–3324、
    @CLOTH_HOSEI_DEF_153:8516–8532（各含NOINNER）；
    CLOTHDATAアウター_特殊.ERB@CLOTH_HOSEI_KOUGEKI_199:249–271；
    CLOTHDATAインナー.ERB@CLOTH_HOSEI_AVOID_397:1993–2001。

    原函式未帶角色參數，故讀 TARGET，不讀外層 CLOTH_HOSEI 的 ARG。
    """
    c = ctx.state.target_chara
    eid = cid - 100 if c.cflag[1] == 0 else cid
    if cid in (106, 115, 117, 153):
        noinner = int(figure_split(c.equip[eid], 14) == 1)
        if mode == "NOINNER":
            return noinner
        return DEFAULT_OUTER_DEF - 50 if noinner else DEFAULT_OUTER_DEF + (5 if cid == 117 else 0)
    if cid == 199:
        value = 125 + figure_split(c.equip[eid], 2) * 25
        if figure_split(c.equip[eid], 3) == {"KOUGEKI": 1, "BOUGYO": 2, "BINSYOU": 3}[mode]:
            value += 25
        if figure_split(c.equip[eid], 4) == 4:
            from ..era import times
            value = times(value, "1.3")
        return value
    if cid == 397:
        return 155 if (c.cflag[1] == 0 and c.cflag[40] == 0) or (c.cflag[1] > 0 and c.cflag[41] == 0) else 100
    raise ValueError((cid, mode))


def cloth_hosei(ctx: Ctx, who: int, cid: int, mode: str, shopr: int = 0, *, registers: bool = False) -> int:
    """`CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI(ARG,ID,MODE,SHOPR)`:8–153。

    registers供CALL包裝者同步SUBSTRING的RESULTS:0；數值RESULT仍由呼叫者接回傳值。
    """
    st = ctx.state
    if cid in (990, 991, 992):
        # イベント専用装備（CLOTHDATA※イベント専用装備.ERB@CLOTH_STATUS_990〜992：S20 `raid.battle_event_cloth_status`）
        from ..raid import battle_event_cloth_status

        text = battle_event_cloth_status(ctx, cid)
    elif cid not in CLOTH_STATUS:
        # TRYCCALLFORM CLOTH_STATUS_{ID} → CATCH で SAVESTR:0 = ""（:23–26）。未定義番号。
        text = ""
    else:
        text = CLOTH_STATUS[cid]
    st.savestr[0] = text  # :25／各 @CLOTH_STATUS_* は SAVESTR:0 に代入する
    res = -99999
    sp = _find(text, mode, 0)
    if sp > -1:
        sp += len(mode)
        if _find(text, "!", sp) == sp:
            res = _special_hosei(ctx, cid, mode)
        ep = _find(text, "@", sp)
        sep = _find(text, ",", sp)
        if ep > sep:
            ep = -1
        if _find(text, "!", sp) == sp:
            pass
        elif ep > -1:
            value = _substring(text, sp, ep - sp)
            if registers:
                st.results[0] = value
            res = _toint(value)
            if st.charas[who].cflag[1] > 0:
                sp = ep + 1
                ep = _find(text, ",", sp)
                value = _substring(text, sp, ep - sp)
                if registers:
                    st.results[0] = value
                res = _toint(value)
        else:
            ep = _find(text, ",", sp)
            value = _substring(text, sp, ep - sp)
            if registers:
                # 原文:88–91 SUBSTRING→RESULTS；引擎
                # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:393–404。
                st.results[0] = value
            res = _toint(value)
    if res == -99999:
        if shopr == 1:
            return res
        if mode in ("KOUGEKI", "BOUGYO", "BINSYOU", "CHISEI", "SEITAISEI", "YUDAN", "LIQUID", "WAVE", "SHYNESS"):
            res = 100
        elif mode in ("TAIRYOKU", "KIRYOKU"):
            res = 95
        elif mode == "DEF":
            res = DEFAULT_INNER_DEF if 300 <= cid <= 400 else DEFAULT_OUTER_DEF
        else:
            res = 0
    if cid == 0:
        return res
    # :132–136 重装・軽装レベル（TARGET の CFLAG:1 を見る）
    local = cid - 100 if st.target_chara.cflag[1] == 0 and 100 <= cid <= 199 else cid
    eq = st.target_chara.equip[local]  # :140–147 未指定角色的 EQUIP 讀 TARGET。
    if mode == "HP":
        if res != -1:
            res += 5 * (figure_split(eq, 11) - figure_split(eq, 10))
    elif mode == "HIT":
        res *= -1
        res += figure_split(eq, 10) - figure_split(eq, 11)
    elif mode == "DEF":
        res -= 5 * (figure_split(eq, 13) - figure_split(eq, 12))
    return res


def customize_commonparts_cal(ctx: Ctx, value: int, mode: str) -> int:
    """`CLOTHDATAカスタム.ERB@CLOTH_CUSTOMIZE_COMMONPARTS_CAL`:9–18（TARGET の EQUIP:600–699）。"""
    from ..clothing_text import PARTS

    c = ctx.state.target_chara
    for i in range(600, 700):
        if c.equip[i]:
            value += PARTS.get(i, {}).get(mode, 0)
    return value


def cloth_battle_hosei(ctx: Ctx, mode: str, who: int = -999, *, registers: bool = False) -> int:
    """`CLOTH_BATTLE.ERB@CLOTH_BATTLE_HOSEI, ARGS, ARG`:331–383。"""
    st = ctx.state
    keep = st.target
    if who != -999:
        st.target = who
    try:
        c = st.target_chara
        v = c.tcvarn
        local = 0 if mode in _ADD_MODES else 100

        def apply(r: int) -> None:
            nonlocal local
            if mode in _ADD_MODES:
                local += r
            else:
                local = div(local * r, 100)

        if c.cflag[1] == 0:
            if not (st.flag[700] and (v[21] == 0 or percent_cal(v[21], v[20]) < 1) and keep == st.target):
                apply(cloth_hosei(ctx, st.target, c.cflag[40], mode, registers=registers))
        else:
            if not (st.flag[700] and (v[23] == 0 or percent_cal(v[23], v[22]) < 1) and keep == st.target):
                apply(cloth_hosei(ctx, st.target, c.cflag[41], mode, registers=registers))
        # :366 `FLAG:700 && (...) || CLOTH_NO_INNER > 0 && KEEP_TARGET == TARGET`
        # （&&・|| は同優先度で左結合：((A && B) || C) && D）
        broken = st.flag[700] and (v[25] == 0 or percent_cal(v[25], v[24]) < 1)
        if not ((broken or st.temp.cloth[NO_INNER] > 0) and keep == st.target):
            apply(cloth_hosei(ctx, st.target, c.cflag[42], mode, registers=registers))
        if c.cflag[1] > 0 and (mode != "HP" or local != -1):
            local = customize_commonparts_cal(ctx, local, mode)
        return local
    finally:
        st.target = keep


def cloth_no_inner(ctx: Ctx, who: int, *, registers: bool = False) -> int:
    """`CLOTH_BATTLE.ERB@CLOTH_NO_INNER`:452–455。

    ARG只決定形態，省略角色的外層CFLAG讀TARGET衣裝；引擎
    reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs:107–119。
    既有原生呼叫者自行管理暫存；finalize以registers=True模擬CALL邊界。
    """
    st = ctx.state
    if registers:
        st.result[0] = 0
    cid = st.target_chara.cflag[41 if st.charas[who].cflag[1] > 0 else 40]
    result = cloth_hosei(ctx, st.target, cid, "NOINNER", registers=registers)
    if registers:
        # RETURN只覆寫傳入格：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2014–2023。
        st.result[0] = result
    return result


def cloth_check(ctx: Ctx, who: int) -> int:
    """`@CLOTH_CHECK(ARG)`（:390–401）。"""
    c = ctx.state.charas[who]
    local = 0
    if c.cflag[1] == 0 and c.tcvarn[21] > 0:
        local |= 2
    elif c.cflag[1] == 1 and c.tcvarn[23] > 0:
        local |= 4
    if c.tcvarn[25] > 0 or (ctx.state.temp.cloth[NO_INNER] > 0 and local > 0):
        local |= 1
    return local


def cloth_battle_sethp(ctx: Ctx) -> None:
    """`@CLOTH_BATTLE_SETHP`（:6–26）。"""
    st = ctx.state
    c = st.target_chara
    r = cloth_hosei(ctx, st.target, c.cflag[40], "HP")
    c.tcvarn[20] = r
    c.tcvarn[21] = r
    keep = c.cflag[1]
    c.cflag[1] = 1
    r = cloth_hosei(ctx, st.target, c.cflag[41], "HP")
    if r != -1:
        r = customize_commonparts_cal(ctx, r, "HP")
    c.tcvarn[22] = r
    c.tcvarn[23] = r
    c.cflag[1] = keep
    r = cloth_hosei(ctx, st.target, c.cflag[42], "HP")
    c.tcvarn[24] = r
    c.tcvarn[25] = r


def refresh_cloth_data(ctx: Ctx) -> None:
    """`@REFRESH_CLOTH_DATA`（:459–517）。"""
    st = ctx.state
    c = st.target_chara
    v = c.tcvarn
    cl = st.temp.cloth
    if c.cflag[1] == 0:
        cl[OUTER_PER] = percent_cal(v[21], v[20])
        cl[OUTER_DEF] = cloth_hosei(ctx, st.target, c.cflag[40], "DEF")
        if v[20] > 0 and v[22] > 0:
            v[23] = div(v[22] * cl[OUTER_PER], 100)
    else:
        cl[OUTER_PER] = percent_cal(v[23], v[22])
        cl[OUTER_DEF] = cloth_hosei(ctx, st.target, c.cflag[41], "DEF")
        if v[20] > 0 and v[22] > 0:
            v[21] = div(v[20] * cl[OUTER_PER], 100)
    cl[INNER_PER] = percent_cal(v[25], v[24])
    if c.cflag[1] == 0 and v[20] < 0:
        cl[OUTER_PER] = 0
    if c.cflag[1] > 0 and v[22] < 0:
        cl[OUTER_PER] = 0
    if v[24] < 0:
        cl[INNER_PER] = 0
    if cloth_no_inner(ctx, st.target) > 0:
        cl[INNER_PER] = cl[OUTER_PER]
        cl[NO_INNER] = 1
        cl[INNER_DEF] = cloth_hosei(ctx, st.target, c.cflag[40 if c.cflag[1] == 0 else 41], "DEF")
        if v[24] > 0 and v[20 if c.cflag[1] == 0 else 22] > 0:
            v[25] = div(v[24] * cl[OUTER_PER], 100)
    else:
        cl[NO_INNER] = 0
        cl[INNER_DEF] = cloth_hosei(ctx, st.target, c.cflag[42], "DEF")
        if cloth_hosei(ctx, st.target, c.cflag[41 if c.cflag[1] == 0 else 40], "NOINNER") > 0:
            src, dst, base = (20, 23, 22) if c.cflag[1] == 0 else (22, 21, 20)
            if v[src] > 0 and v[24] > 0:
                v[dst] = div(v[base] * (cl[OUTER_PER] + cl[INNER_PER]), 200)
            elif v[src] > 0:
                v[dst] = div(v[base] * cl[OUTER_PER], 100)
            elif v[24] > 0:
                v[dst] = div(v[base] * cl[INNER_PER], 100)


def costume_name(ctx: Ctx, who: int, trans: int = -1) -> str:
    """`@COSTUME_NAME(ARG, trans = -1)`（:409–434）：trans = 0 は変身前、-1 は現在の状態（CFLAG:1 == 0 なら変身前）、他は変身後。"""
    c = ctx.state.charas[who]
    items = ctx.data.items
    if trans == 0 or (trans == -1 and c.cflag[1] == 0):
        cid = c.cflag[40]
        if cid == 0:
            return ""
        if cid == 990:
            return c.cstr[80]
        if c.cstr[8] != "":
            return c.cstr[8]
        return items[cid].name if cid in items else ""
    cid = c.cflag[41]
    if cid == 0:
        return ""
    if cid == 991:
        return c.cstr[81]
    if c.cstr[9] != "":
        return c.cstr[9]
    return items[cid].name if cid in items else ""


def inner_name(ctx: Ctx, who: int) -> str:
    """`@INNER_NAME(ARG)`（:437–446）。"""
    c = ctx.state.charas[who]
    cid = c.cflag[42]
    if cid == 0:
        return ""
    if cid == 992:
        return c.cstr[82]
    return ctx.data.items[cid].name if cid in ctx.data.items else ""


def _attacker_prefix(ctx: Ctx) -> None:
    """MESSAGE_BATTLE_CLOTH_*:1544–1550 の「敵名 の攻撃により、」。"""
    from .core import tentacle_access

    from .core import print_enemy_prefix

    st = ctx.state
    if st.tflag[0] >= 0:
        print_enemy_prefix(ctx)
        ctx.out.print("の攻撃により、")


def cloth_battle_damage(ctx: Ctx, arg: int, arg1: int = 0) -> None:
    """`@CLOTH_BATTLE_DAMAGE, ARG, ARG:1`（:197–324）。"""
    st = ctx.state
    c = st.target_chara
    v = c.tcvarn
    cl = st.temp.cloth
    l0, l1, l2, l3 = 0, 0, 50, arg
    if st.tflag[23] == -1:
        return
    if c.cflag[42] == 398 and arg > 0:
        l3 = max(div(l3, 6), 1) if v[2] == P_V_GUARD else max(div(l3, 3), 1)
    outer, outer_max, outer_cid = (21, 20, c.cflag[40]) if c.cflag[1] == 0 else (23, 22, c.cflag[41])
    l2 = cloth_hosei(ctx, st.target, outer_cid, "DEF")
    if v[outer_max] > 0 or v[24] > 0:
        if v[outer] > 0 or v[25] > 0:
            if v[outer] == 0 or percent_cal(v[outer], v[outer_max]) < l2:
                ni = cloth_no_inner(ctx, st.target)
                if v[25] > 0 and ni == 0:
                    if v[0] != 0 and arg1 == 0:
                        l3 = div(l3, 3)
                    l1 = percent_cal(v[25], v[24])
                    v[25] = limit(v[25] - l3, 0, v[25])
                    if arg1 == 0 and v[25] > 0:
                        arg = div(arg, 3)
                elif arg1 == 0 and v[25] > 0:
                    arg = div(arg, 6)
            l0 = percent_cal(v[outer], v[outer_max])
            v[outer] = limit(v[outer] - arg, 0, v[outer])
    refresh_cloth_data(ctx)
    out = ctx.out
    name = print_transcallname(st, st.target)
    if l0 > 0 and v[outer] <= 0 and v[outer_max] > 0:
        _attacker_prefix(ctx)  # MESSAGE_BATTLE_CLOTH_OUTERBREAK:1563–1576
        out.printl(f"{name}の{costume_name(ctx, st.target)}は完全に布切れと化してしまった・・・")
        out.printl("アウターの機能が完全に失われた！")
        kojo_root(ctx, "BATTLE_CLOTH_OUTERBREAK")
        out.printl()
        if enemy_type_check(st, "AKUOTI") == 1:
            from .core import msg_other

            msg_other(ctx, "BATTLE_CLOTH_OUTERBREAK")
    elif l0 >= cl[OUTER_DEF] and percent_cal(v[outer], v[outer_max]) < cl[OUTER_DEF] and v[outer_max] > 0:
        _attacker_prefix(ctx)  # MESSAGE_BATTLE_CLOTH_OUTERDAMAGE:1543–1560
        out.printl(f"{name}の{costume_name(ctx, st.target)}の端々が破れ始めた・・・")
        if cl[NO_INNER] > 0:
            out.printl("アウターの挿入抵抗機能が失われた！")
        else:
            out.printl("アウターの下着防護機能が失われた！")
        kojo_root(ctx, "BATTLE_CLOTH_OUTERDAMAGE")
        out.printl()
        if enemy_type_check(st, "AKUOTI") == 1:
            from .core import msg_other

            msg_other(ctx, "BATTLE_CLOTH_OUTERDAMAGE")
    if l1 and v[25] <= 0 and v[24] > 0:
        _inner_break_message(ctx)
        if enemy_type_check(st, "AKUOTI") == 1:
            from .core import msg_other

            msg_other(ctx, "BATTLE_CLOTH_INNERBREAK")
    elif l1 >= cl[INNER_DEF] and percent_cal(v[25], v[24]) < cl[INNER_DEF] and v[24] > 0:
        _attacker_prefix(ctx)  # MESSAGE_BATTLE_CLOTH_INNERDAMAGE:1579–1597
        out.print(f"{name}の{inner_name(ctx, st.target)}")
        if c.cflag[42] == 398:
            out.printl("が今にも剥がれそうになっている・・・")
        else:
            out.printl("までも破れ始めてしまった・・・")
        out.printl("インナーの挿入抵抗機能が失われた！")
        kojo_root(ctx, "BATTLE_CLOTH_INNERDAMAGE")
        out.printl()
        if enemy_type_check(st, "AKUOTI") == 1:
            from .core import msg_other

            msg_other(ctx, "BATTLE_CLOTH_INNERDAMAGE")


def _inner_break_message(ctx: Ctx) -> None:
    """`地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CLOTH_INNERBREAK`:1600–1631（原作の重複文言もそのまま）。"""
    from .core import tentacle_access

    st = ctx.state
    out = ctx.out
    c = st.target_chara
    name = print_transcallname(st, st.target)
    items = ctx.data.items
    if st.tflag[0] >= 0:
        from .core import print_enemy_prefix

        print_enemy_prefix(ctx)
        out.print("の攻撃により、")
        if c.cflag[42] == 398:
            iname = items[398].name if 398 in items else ""
            out.print(f"に{iname}を剥ぎ取られ、{name}の")
            out.printl("秘部が露わにされてしまっている・・・")
        else:
            out.print(f"の攻撃により、{name}の{inner_name(ctx, st.target)}")
            out.printl("はもはや下着としての機能を果たしていない・・・")
    else:
        if c.cflag[42] == 398:
            iname = items[398].name if 398 in items else ""
            out.print(f"{iname}は剥がれ落ち、{name}の")
            out.printl("秘部が露わにされてしまっている・・・")
        else:
            out.print(f"{name}の{inner_name(ctx, st.target)}")
            out.printl("はもはや下着としての機能を果たしていない・・・")
    out.printl("インナーの機能が完全に失われた！")
    kojo_root(ctx, "BATTLE_CLOTH_INNERBREAK")
    out.printl()
