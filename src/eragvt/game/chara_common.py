"""角色共通函式（`汎用関数/`、`ヒロイン関連/` 的翻寫）。路徑相對 `source/earGVP/ERB/`。"""

from __future__ import annotations

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.character import Character
from ..state.constants import Base
from .era import div, isqrt, limit, times


def talent(data: GameData, chara: Character, name: str) -> int:
    """`TALENT:chara:名稱`。"""
    return chara.talent[data.index_of("TALENT", name)]


def is_female(data: GameData, chara: Character) -> bool:
    """`汎用関数/SEX_GENDER.ERB@ISFEMALE`:121–129。"""
    return talent(data, chara, "オトコ") <= 0


def is_male(data: GameData, chara: Character) -> bool:
    """`汎用関数/SEX_GENDER.ERB@ISMALE`:131–139。"""
    return talent(data, chara, "オトコ") > 0


def seikaku_check(data: GameData, chara: Character) -> int:
    """`ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_CHECK_F`:41–56（"GET_TALENT_VALUE" も同じ走査、:5–33）：
    TALENT 10 から TALENTNAME が空でない個数ぶん走査し、値が 1 の最初の番号。無ければ 0。"""
    count = sum(1 for i in range(10, 50) if data.names["TALENT"].get(i, "") != "")
    for i in range(10, 10 + count):
        if chara.talent[i] == 1:
            return i
    return 0


def syuzoku_check(chara: Character) -> int:
    """`ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_CHECK`（"GET_SYUZOKU_VALUE"）:5–24：
    TALENT 201〜249 で最初に >0 の番號。無ければ 0。"""
    for i in range(201, 250):
        if chara.talent[i] > 0:
            return i
    return 0


def charatalent(data: GameData, chara: Character, transformed: int, name: str) -> int:
    """`汎用関数/コモン関数.ERB@CHARATALENT_F`:1079–1321。

    ARG:1（`transformed`）= 0 なら通常時、>0 なら変身時の素質を返す。変身中（CFLAG:1 > 0）は TALENT が
    変身後の値になっているので、分岐（:1083–1206）で通常時の値を逆算する。
    """
    t = lambda n: talent(data, chara, n)  # noqa: E731
    result = ""
    if chara.cflag[1] > 0:  # :1083 変身時
        if transformed > 0:  # :1084–1130 現在の TALENT がそのまま変身時の値
            result = _plain_talent_name(data, chara, name, "変身時外見")
        else:  # :1131–1205 通常時の値を逆算
            if name in ("小柄", "長身"):
                v = t("長身") - t("小柄") - t("変身時体格変動")
                if v < 0:
                    result = "小柄"
                elif v > 0:
                    result = "長身"
                elif t("変身時体格変動") == 0:
                    result = "小柄" if t("小柄") > 0 else "長身" if t("長身") > 0 else ""
            elif name in _BUSTS:
                v = t("巨乳") - t("貧乳") - t("変身時胸サイズ変動")
                result = _bust_name(v)
                if v == 0 and t("変身時胸サイズ変動") == 0:
                    result = _plain_bust(data, chara)
            elif name == "オトコ":
                if is_female(data, chara):
                    if t("変身時ＴＳ") > 0:
                        result = "オトコ"
                elif t("変身時ＴＳ") == 0:
                    result = "オトコ"
            elif name == "男の娘":
                result = "男の娘" if t("変身時男の娘") > 0 else ""
            elif name == "ふたなり":
                result = "ふたなり" if t("変身時ふたなり") > 0 else ""
            elif name in _APPEARANCE:
                result = _APPEARANCE_BY_VALUE.get(t("外見"), "")
    elif transformed > 0:  # :1209–1267
        if name in ("小柄", "長身"):
            v = t("長身") - t("小柄") + t("変身時体格変動")
            result = "小柄" if v < 0 else "長身" if v > 0 else ""
        elif name in _BUSTS:
            v = t("巨乳") - t("貧乳") + t("変身時胸サイズ変動")
            if is_male(data, chara):
                if t("変身時ＴＳ") == 0:
                    v = 0
            elif t("変身時ＴＳ") > 0:
                v = 0
            result = _bust_name(v)
        elif name == "オトコ":
            if is_male(data, chara):
                if t("変身時ＴＳ") == 0:
                    result = "オトコ"
            elif t("変身時ＴＳ") > 0:
                result = "オトコ"
        elif name == "男の娘":
            result = "男の娘" if t("変身時男の娘") > 0 else ""
        elif name == "ふたなり":
            result = "ふたなり" if t("変身時ふたなり") > 0 else ""
        elif name in _APPEARANCE:
            result = _APPEARANCE_BY_VALUE.get(t("変身時外見"), "")
    else:  # :1268–1315
        result = _plain_talent_name(data, chara, name, "外見")
    return 1 if result == name else 0


_BUSTS = ("絶壁", "貧乳", "巨乳", "爆乳", "超乳", "魔乳", "奇乳")


def _plain_bust(data: GameData, chara: Character) -> str:
    """TALENT:貧乳／巨乳 の値から胸の素質名（:1090–1104 などの共通形）。"""
    hin, kyo = talent(data, chara, "貧乳"), talent(data, chara, "巨乳")
    if hin == 2:
        return "絶壁"
    if hin == 1:
        return "貧乳"
    return {5: "奇乳", 4: "魔乳", 3: "超乳", 2: "爆乳", 1: "巨乳"}.get(kyo, "")


def _plain_talent_name(data: GameData, chara: Character, name: str, appearance: str) -> str:
    """TALENT をそのまま読む分岐（:1084–1130、:1268–1315）。外見系は `appearance`（外見／変身時外見）の値で判定。"""
    t = lambda n: talent(data, chara, n)  # noqa: E731
    if name in ("小柄", "長身"):
        return "小柄" if t("小柄") > 0 else "長身" if t("長身") > 0 else ""
    if name in _BUSTS:
        return _plain_bust(data, chara)
    if name == "オトコ":
        return "オトコ" if is_male(data, chara) else ""
    if name == "男の娘":
        return "男の娘" if t("男の娘") > 0 else ""
    if name == "ふたなり":
        return "ふたなり" if t("ふたなり") > 0 else ""
    if name in _APPEARANCE:
        return _APPEARANCE_BY_VALUE.get(t(appearance), "")
    return ""


_APPEARANCE = ("安産型", "むちむち", "イカ腹", "スレンダー", "巨尻", "爆尻")
_APPEARANCE_BY_VALUE = {i + 1: n for i, n in enumerate(_APPEARANCE)}


def _bust_name(v: int) -> str:
    if v < -1:
        return "絶壁"
    if v < 0:
        return "貧乳"
    if v > 4:
        return "奇乳"
    if v > 3:
        return "魔乳"
    if v > 2:
        return "超乳"
    if v > 1:
        return "爆乳"
    if v > 0:
        return "巨乳"
    return ""


# --- LEVELSTATUS -------------------------------------------------------------

# `汎用関数/コモン関数.ERB@FEAT_BONUS_F`:802：素質 → (体力, 気力, 性耐性, 攻撃, 防御, 敏捷, 知性) の補正
_FEAT_BONUS: list[tuple[str, tuple[int, int, int, int, int, int, int]]] = [
    ("超反応", (0, 0, 0, -5, 0, 0, 0)),
    ("神器の担い手", (0, 0, -10, 5, 5, 5, 0)),
    ("闘争本能", (0, 0, -5, 10, 0, 0, 0)),
    ("溢れる生命力", (0, 0, 0, 0, 0, 0, -15)),
    ("精霊交信", (0, 0, 0, -5, -5, -5, 10)),
    ("獣性の証", (0, 0, 0, 0, 0, 0, -10)),
    ("夜魔の貴族", (100, 100, 10, 10, 10, 10, 10)),
    ("秘められし力", (0, 0, 0, -5, -5, -5, -5)),
    ("ラッキーチャーム", (0, 0, 0, -5, -5, -5, -5)),
    ("剛腕", (0, 0, 0, 5, 0, 0, 0)),
    ("有翼", (0, 0, 0, 0, 5, 0, 0)),
    ("小さな体躯", (0, 0, 0, 0, 0, 5, 0)),
    ("叡智の冠", (-50, -50, -5, 0, 0, 0, 10)),
    ("狩人の勘", (0, 0, 0, 0, 0, 0, -5)),
    ("心眼", (0, 0, 0, 0, -5, -5, 0)),
]


def feat_bonus(data: GameData, chara: Character, which: int) -> int:
    """`FEAT_BONUS_F(ARG, which)`：which = 0 体力 1 気力 2 性耐性 3 攻撃 4 防御 5 敏捷 6 知性。"""
    total = 0
    for name, bonus in _FEAT_BONUS:
        if talent(data, chara, name) > 0:
            total += bonus[which]
    return total


def levelstatus_up(base: int, level: int, growth: int, cap: int = 0) -> int:
    """`@LEVELSTATUS_UP`（コモン関数.ERB:901–918）：
    ((√(220·Lv) + 95)·BASE + (5.2·Lv + 95)·成長値) / 100、上限 cap（0 なら無し）、下限 1。"""
    local0 = isqrt(220 * level)
    local1 = times(52 * level, "0.1")
    local2 = (local1 + 95) * growth
    local2 += (local0 + 95) * base
    local2 = div(local2, 100)
    if local2 > cap and cap:
        local2 = cap
    if local2 < 1:
        local2 = 1
    return local2


def level_status(data: GameData, state: GameState, index: int) -> None:
    """`@LEVELSTATUS, ARG`（コモン関数.ERB:885–894）。ARG == 0 は TARGET。"""
    if index == 0:
        index = state.target
    c = state.charas[index]
    lv = c.abl[data.index_of("ABL", "レベル")]
    b = c.base
    c.maxbase[Base.HP] = levelstatus_up(b[50] + feat_bonus(data, c, 0), lv, 400 + div(b[50] - 1000, 5), 99999)
    c.maxbase[Base.ENERGY] = levelstatus_up(b[51] + feat_bonus(data, c, 1), lv, 400 + div(b[51] - 1000, 5), 99999)
    c.maxbase[Base.SEX_RESIST] = levelstatus_up(
        b[52] + feat_bonus(data, c, 2), div(lv, 3) + 1, 10 + div(b[52] - 100, 2), 9999
    )
    for which, idx in ((3, Base.ATTACK), (4, Base.DEFENSE), (5, Base.AGILITY), (6, Base.INTELLECT)):
        c.maxbase[idx] = levelstatus_up(b[idx] + feat_bonus(data, c, which), lv, 50, 9999)
    baseup_cal_shield(data, state, index)


def cal_shield(data: GameData, chara: Character) -> int:
    """`@CAL_SHIELD_F`（コモン関数.ERB:653–656）：結界耐久最大値。"""
    m = chara.maxbase
    lv = chara.abl[data.index_of("ABL", "レベル")]
    return div(isqrt(div(m[Base.ENERGY] * m[Base.SEX_RESIST] * m[Base.DEFENSE] * m[Base.DEFENSE], 160)), 2) + 1500 + min(
        lv * 1000, 50000
    )


def baseup_cal_shield(data: GameData, state: GameState, index: int) -> None:
    """`@BASEUP_CAL_SHIELD, ARG`（コモン関数.ERB:638–648）：Ｃ〜Ｂ結界（TALENT 190〜193）を持つ部位の結界耐久を更新。"""
    c = state.charas[index]
    for k in range(4):
        if c.talent[190 + k] > 0:
            shield = cal_shield(data, c)
            up = max(shield - c.maxbase[30 + k], 0)
            c.maxbase[30 + k] = shield
            if c.base[30 + k] > 0 or state.day[0] == 0:
                c.base[30 + k] = limit(c.base[30 + k] + up, 0, c.maxbase[30 + k])
