"""忠實手翻 ヒロイン関連/SEXUAL_PROFILE.ERB@MAKESEXUALPROFILE:12–108。

STRDATA 每次只抽一個候選，重抽不刪除候選；引擎依據：
reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:730–754。
文字資料見 profile_text（原文抽取），沒有 ERB 執行器。
"""
from .action import Ctx
from .profile_text import TABLES


def _pick(ctx: Ctx, name: str, group: int = 0) -> str:
    values = TABLES[name][group]
    return values[ctx.state.rng.rand(len(values))]


def _adjective(ctx: Ctx, family: str, level: int) -> str:
    # @MAKE_ADJ_BC:114–169／@MAKE_ADJ_VA:173–233。
    group = 0 if level >= 5 else 1 if level >= 3 else 2
    while True:
        value = _pick(ctx, "MAKE_ADJ_" + family, group)
        if value != "【冠名】":
            return value
        if ctx.state.flag[6] == 1:
            return ctx.state.savestr[11] + "(笑)"


def _verb(ctx: Ctx, part: str, level: int) -> str:
    # @MAKE_VERB_V:307–374／@MAKE_VERB_A:379–439。
    if part in ("B", "C", "P"):
        return _pick(ctx, "MAKE_VERB_BC")
    if part not in ("V", "A"):
        return "エラー"
    while True:
        value = _pick(ctx, "MAKE_VERB_" + part, 0 if level >= 5 else 1)
        if value != "【かけ声】":
            return value
        if ctx.state.flag[7] == 1:
            return ctx.state.savestr[12] + "(意味深)される"


def make_sexual_profile(ctx: Ctx, part: str, level: int) -> str:
    """@MAKESEXUALPROFILE:12–108；順序及 Lv11 不生成 Adj:1 照原文。"""
    adj = ["", "", "", ""]  # :23 VARSET Adj
    family = "BC" if part in ("B", "C", "P") else "VA" if part in ("V", "A") else ""
    if family:
        if level < 11:
            adj[1] = _adjective(ctx, family, level)
        if level >= 8:
            adj[0] = _pick(ctx, "MAKE_ONOMATOPE_" + family)
        if level >= 10:
            adj[2] = _adjective(ctx, family, level)
            while adj[2] == adj[1]:
                adj[2] = _adjective(ctx, family, level)
    if level >= 11:
        adj[3] = _pick(ctx, "MAKE_BAD_REPUTATION")
    if part == "B":
        body = "乳首"
    elif part in ("C", "P", "V", "A"):
        body = _pick(ctx, "MAKE_" + part + "_NAME", 0 if level >= 5 else 1)
    else:
        body = "エラー"
    adv = _pick(ctx, "MAKE_ADV_1") if 7 <= level < 9 else _pick(ctx, "MAKE_ADV_2") if level >= 9 else ""
    verb = _verb(ctx, part, level)
    return adj[3] + adj[2] + adj[1] + adj[0] + body + "を" + adv + verb + "のが好き"


def update_profile(ctx: Ctx, index: int, level: int) -> None:
    """ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP:153–207、276–330。"""
    from .battle.core import is_penis
    c, out = ctx.state.target_chara, ctx.out
    part = ("P" if is_penis(ctx) else "C") if index == 0 else ("V", "A", "B")[index - 1]
    c.cstr[45 + index] = make_sexual_profile(ctx, part, level)
    out.print("性癖：【")
    value = min(max(c.abl[index], 0), 10)
    out.set_color((255, 255 - 23 * value, 255 - 11 * value))
    out.print(c.cstr[45 + index])
    out.reset_color()
    out.printl("】を得た")
