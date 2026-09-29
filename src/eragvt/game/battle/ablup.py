"""能力の上昇：`ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP`（路徑相對 `source/earGVP/ERB/`）。

原作は `BEGIN ABLUP` を使わず、戦闘後（BATTLE_TRAIN_AFTER.ERB:131–137）などから `CALL _ABLUP, ARG` で自動上昇させる。
"""

from __future__ import annotations

from ..action import Ctx, config_check_other, print_callname, print_transcallname
from ..chara_common import is_female, is_male
from ..era import div
from ...state.character import Character
from .core import exp, mark, t, tc

# 各 @ABL_UP_n の段階表：レベル L→L+1 に必要な (JUEL 名, 量) と (EXP 名, 最低値)、Lv3→4／4→5 で異常経験が要るか。
# 値は ABL_UP_CHECK.ERB の各行（コメントに行番号）。


def _juel(ctx: Ctx, c: Character, name: str) -> int:
    return c.juel[ctx.data.index_of("JUEL", name)]


def _sub_juel(ctx: Ctx, c: Character, name: str, amount: int) -> None:
    c.juel[ctx.data.index_of("JUEL", name)] -= amount


def _abl(ctx: Ctx, c: Character, name: str) -> int:
    return c.abl[ctx.data.index_of("ABL", name)]


def _set_abl(ctx: Ctx, c: Character, name: str, value: int) -> None:
    c.abl[ctx.data.index_of("ABL", name)] = value


# (前提刻印, 前提値) / 各段階 ([(JUEL, 量)...], (EXP, 最低値) or None)
_ADDICTION = {
    # @ABL_UP_20 触手中毒:491–533（屈服刻印 2 未満なら上がらない）
    "触手中毒": (("屈服刻印", 2), "被姦経験", [
        ((("欲情", 500), ("屈服", 1000)), 10),
        ((("欲情", 1000), ("屈服", 2000)), 20),
        ((("欲情", 1500), ("屈服", 6000)), 50),
        ((("欲情", 3000), ("屈服", 9000)), 100),
        ((("欲情", 6000), ("屈服", 18000)), 200),
    ]),
    # @ABL_UP_21 自慰中毒:540–582
    "自慰中毒": (("恥辱刻印", 2), "自慰経験", [
        ((("欲情", 500), ("恥情", 1000)), 10),
        ((("欲情", 1000), ("恥情", 2000)), 20),
        ((("欲情", 1500), ("恥情", 3000)), 50),
        ((("欲情", 3000), ("恥情", 6000)), 100),
        ((("欲情", 6000), ("恥情", 12000)), 200),
    ]),
    # @ABL_UP_22 精液中毒:589–632
    "精液中毒": (("快楽刻印", 2), "精液経験", [
        ((("欲情", 500), ("屈服", 1000)), 10),
        ((("欲情", 1000), ("屈服", 2000)), 25),
        ((("欲情", 1500), ("屈服", 3000)), 50),
        ((("欲情", 3000), ("屈服", 6000)), 100),
        ((("欲情", 6000), ("屈服", 12000)), 200),
    ]),
}


def _abl_up_addiction(ctx: Ctx, c: Character, abl_name: str) -> int:
    (mark_name, need), exp_name, steps = _ADDICTION[abl_name]
    local = _abl(ctx, c, abl_name)
    if mark(ctx, c, mark_name) < need:
        return local
    for _ in range(5):  # REPEAT 5
        if 0 <= local <= 4:
            if local >= 3 and exp(ctx, c, "異常経験") == 0:  # Lv3→4、4→5 は `ELSEIF LOCAL == n && EXP:異常経験`
                continue
            juels, min_exp = steps[local]
            if all(_juel(ctx, c, j) >= a for j, a in juels) and exp(ctx, c, exp_name) >= min_exp:
                for j, a in juels:
                    _sub_juel(ctx, c, j, a)
                local += 1
    return local


# @ABL_UP_24 射精中毒:639–680（快Ｃ）／@ABL_UP_23 噴乳中毒:687–728（快Ｂ）
_EMIT = {
    "射精中毒": ("快Ｃ", "射精経験", 20, ((1000, 5), (3000, 10), (5000, 20), (10000, 50), (30000, 100))),
    "噴乳中毒": ("快Ｂ", "噴乳経験", 21, ((1000, 5), (3000, 10), (5000, 20), (10000, 50), (30000, 100))),
}


def _csvbase(ctx: Ctx, c: Character, index: int) -> int:
    """`汎用関数/コモン関数.ERB@CSVBASE_F, NO, index`:966–：キャラ CSV の BASE 初期値。"""
    from ..opening import _csvbase as csvbase

    return csvbase(ctx.data, c.no, index)


def _abl_up_emit(ctx: Ctx, c: Character, abl_name: str) -> int:
    juel_name, exp_name, base_idx, steps = _EMIT[abl_name]
    local = _abl(ctx, c, abl_name)
    for _ in range(5):
        if 0 <= local <= 4 and not (local >= 3 and exp(ctx, c, "異常経験") == 0):
            need, min_exp = steps[local]
            if _juel(ctx, c, juel_name) >= need and exp(ctx, c, exp_name) >= min_exp:
                _sub_juel(ctx, c, juel_name, need)
                local += 1
        # ゲージ最大値の再計算（毎回、ABL は更新前の値：:675–678／:723–726）
        mb = _csvbase(ctx, c, base_idx)
        if mb < 1:
            mb = 10000
        c.maxbase[base_idx] = max(div(mb * (10 - _abl(ctx, c, abl_name)), 10), 1000)
    return local


# 経験条件付きの単一珠：(JUEL, [(量, (EXP, 最低値) or None)]、触手の虜で経験条件を免除するか)
_SINGLE = {
    # @ABL_UP_15 マゾっ気:734–778
    "マゾっ気": ("苦痛", ((1000, None), (2000, 2), (5000, 4), (10000, 8), (20000, 16)), "苦痛快楽経験", False),
    # @ABL_UP_13 奉仕精神:783–827
    "奉仕精神": ("恭順", ((800, None), (2000, 2), (6000, 10), (12000, 20), (20000, 50)), "奉仕快楽経験", True),
    # @ABL_UP_14 露出癖:832–876
    "露出癖": ("恥情", ((1000, None), (3000, 2), (7000, 10), (12000, 20), (25000, 50)), "露出快楽経験", False),
    # @ABL_UP_11 欲望:938–975
    "欲望": ("欲情", ((500, None), (2000, None), (5000, None), (10000, None), (20000, None)), "", False),
    # @ABL_UP_12 技巧:980–1016
    "技巧": ("習得", ((1000, None), (2000, None), (4000, None), (8000, None), (20000, None)), "", False),
}


def _abl_up_single(ctx: Ctx, c: Character, abl_name: str) -> int:
    juel_name, steps, exp_name, toriko_ok = _SINGLE[abl_name]
    local = _abl(ctx, c, abl_name)
    for _ in range(5):
        if 0 <= local <= 4:
            need, min_exp = steps[local]
            if min_exp is not None and not (
                exp(ctx, c, exp_name) >= min_exp or (toriko_ok and t(ctx, c, "触手の虜") > 0)
            ):
                continue
            if _juel(ctx, c, juel_name) >= need:
                _sub_juel(ctx, c, juel_name, need)
                local += 1
    return local


def _abl_up_juujun(ctx: Ctx, c: Character) -> int:
    """`@ABL_UP_10` 従順:881–933：屈服を優先、足りなければ恐怖。"""
    local = _abl(ctx, c, "従順")
    for _ in range(5):
        if 0 <= local <= 4:
            need = (1000, 3000, 6000, 12000, 25000)[local]
            if _juel(ctx, c, "屈服") >= need:
                _sub_juel(ctx, c, "屈服", need)
                local += 1
            elif _juel(ctx, c, "恐怖") >= need:
                _sub_juel(ctx, c, "恐怖", need)
                local += 1
    return local


# @ABL_UP_0..3（:1021–1192）：感覚。必要な珠
_SENSE = {
    "Ｃ感覚": ("快Ｃ", (50, 500, 5000, 10000, 20000)),
    "Ｖ感覚": ("快Ｖ", (75, 750, 7500, 15000, 30000)),
    "Ａ感覚": ("快Ａ", (75, 750, 7500, 15000, 30000)),
    "Ｂ感覚": ("快Ｂ", (50, 500, 5000, 10000, 20000)),
}


def _abl_up_sense(ctx: Ctx, c: Character, abl_name: str) -> int:
    juel_name, needs = _SENSE[abl_name]
    local = _abl(ctx, c, abl_name)
    for _ in range(5):
        # :1026 など：`ABL:Ｖ感覚 + ABL:Ａ感覚 + ABL:Ｂ感覚 + LOCAL >= 35 && ABL:自分 >= 5` で BREAK
        # （4 関数とも同じ式：Ｃ以外では自分の ABL と LOCAL を二重に数える。原作どおり）
        if (
            _abl(ctx, c, "Ｖ感覚") + _abl(ctx, c, "Ａ感覚") + _abl(ctx, c, "Ｂ感覚") + local >= 35
            and _abl(ctx, c, abl_name) >= 5
        ):
            break
        if 0 <= local <= 4:
            need = needs[local]
            if _juel(ctx, c, juel_name) >= need:
                _sub_juel(ctx, c, juel_name, need)
                local += 1
    return local


def _abl_up_ex(ctx: Ctx, c: Character) -> list[int]:
    """`@ABL_UP_EX`:1195–1235。感覚 Lv5 以上の追加上昇。"""
    lv = [c.abl[i] for i in range(4)]
    for _ in range(15):
        if sum(max(x - 5, 0) for x in lv) >= 15:
            break
        for i in range(4):
            if c.abl[i] >= 5:
                cal = 20000
                for k in range(min(lv[i] - 5, 5)):
                    cal = cal * (150 - k * 5) // 100
                cal = cal // 2 * 5
                if sum(lv) >= 35:
                    break
                if c.juel[i] >= cal and lv[i] < 20:
                    c.juel[i] -= cal
                    lv[i] += 1
    return lv


def _raise(ctx: Ctx, c: Character, abl_name: str, value: int) -> None:
    if _abl(ctx, c, abl_name) < value:
        _set_abl(ctx, c, abl_name, value)
        idx = ctx.data.index_of("ABL", abl_name)
        ctx.out.printl(f"{ctx.data.names['ABL'].get(idx, '')}が{value}に上がった")
        if idx <= 3 and config_check_other(ctx.state, 6) == 1:
            raise NotImplementedError("裏プロフィール（MAKESEXUALPROFILE）は未移植")


def _talent_message(ctx: Ctx, lines: tuple[str, ...], talent_no: int, verb: str, kojo_code: str) -> None:
    """地の文/MESSAGE_SEX.ERB@MESSAGE_GETTALENT_*:1662–1847 の共通形。"""
    from ..action import kojo_root

    st, out = ctx.state, ctx.out
    name = print_transcallname(st, st.target)
    for line in lines:
        out.printl(line.format(n=name, c=print_callname(st, st.target)))
    out.printl(f"{name}は {ctx.data.names['TALENT'].get(talent_no, '')} {verb}")
    kojo_root(ctx, kojo_code)
    out.printl()


def ablup(ctx: Ctx, arg: int) -> None:
    """`@_ABLUP, ARG`:6–482。ARG=0 通常、2 は珠の取得のみ（ARG=1 幽閉は未使用）。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    if arg == 1:
        raise NotImplementedError("_ABLUP, 1（幽閉）は未移植")
    # :11–62 珠の取得
    out.set_color((105, 105, 105))
    if st.flag[999] == 1:
        out.printl(" * DEGUG　珠の入手 *")
    for count in range(12):
        idx = count + 6 if count > 3 else count
        p = c.palam[idx]
        for bound, got in ((100, 0), (300, 1), (600, 2), (1500, 10), (3000, 20), (6000, 100), (10000, 200),
                           (30000, 1000), (60000, 2000), (150000, 10000), (300000, 20000)):
            if p < bound:
                gain = got
                break
        else:
            gain = 100000
        # :46–47 `LOCAL:1 *= 135 / 100`：135/100 は整数除算で 1（原作どおり実質効果なし）
        if t(ctx, c, "背徳の烙印") > 0:
            gain *= 135 // 100
        c.juel[idx] += gain
        if st.flag[999] == 1:
            out.printl(f"　　取得する{ctx.data.names['PALAM'].get(idx, '')}の珠 : {gain}")
        if c.juel[idx] >= 999999 and idx >= 4:
            c.juel[idx] = 999999
        elif c.juel[idx] >= 99999999:
            c.juel[idx] = 99999999
    out.reset_color()
    if st.flag[999] == 1:
        out.printl()
    if arg == 2:
        return
    # :73–145 各能力（厳しいものから珠を消費）
    new = {
        "触手中毒": _abl_up_addiction(ctx, c, "触手中毒"),
        "自慰中毒": _abl_up_addiction(ctx, c, "自慰中毒"),
        "精液中毒": _abl_up_addiction(ctx, c, "精液中毒"),
        "射精中毒": _abl_up_emit(ctx, c, "射精中毒"),
        "噴乳中毒": _abl_up_emit(ctx, c, "噴乳中毒"),
        "マゾっ気": _abl_up_single(ctx, c, "マゾっ気"),
        "奉仕精神": _abl_up_single(ctx, c, "奉仕精神"),
        "露出癖": _abl_up_single(ctx, c, "露出癖"),
        "従順": _abl_up_juujun(ctx, c),
        "欲望": _abl_up_single(ctx, c, "欲望"),
        "技巧": _abl_up_single(ctx, c, "技巧"),
    }
    for name in ("Ｃ感覚", "Ｖ感覚", "Ａ感覚", "Ｂ感覚"):
        new[name] = _abl_up_sense(ctx, c, name)
    # :150–263 表示は ABL.CSV 順
    for name in ("Ｃ感覚", "Ｖ感覚", "Ａ感覚", "Ｂ感覚", "従順", "欲望", "技巧", "奉仕精神", "露出癖", "マゾっ気",
                 "触手中毒", "自慰中毒", "精液中毒", "噴乳中毒", "射精中毒"):
        _raise(ctx, c, name, new[name])
    # :266–331
    lv = _abl_up_ex(ctx, c)
    for i, name in enumerate(("Ｃ感覚", "Ｖ感覚", "Ａ感覚", "Ｂ感覚")):
        _raise(ctx, c, name, lv[i])
    _talents(ctx, c)
    # :482 GET_STATE_ABLUP（SHOP_TROPHY.ERB:443–：UNLOCK_ACHIEVEMENT のみ。実績は GLOBAL＝deviations.md「全域資料」）


def _talents(ctx: Ctx, c: Character) -> None:
    """:336–479 状態系素質。地の文が要るものは MESSAGE_SEX.ERB の文面を移植、未対応は停止。"""
    data = ctx.data
    a = lambda n: _abl(ctx, c, n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731

    def set_t(name: str, value: int) -> None:
        c.talent[data.index_of("TALENT", name)] = value

    # :336–346
    if (
        a("自慰中毒") + a("精液中毒") + a("噴乳中毒") + a("射精中毒") >= 6
        and a("欲望") >= 4
        and mark(ctx, c, "快楽刻印") >= 4
        and exp(ctx, c, "絶頂経験") >= 100
        and exp(ctx, c, "異常経験") >= 1
    ):
        if tl("初心") > 0 and tl("嬲られ体質") == 0:
            set_t("嬲られ体質", 1)
            _msg_naburare(ctx)
        elif tl("初心") == 0 and tl("淫乱") == 0:
            set_t("淫乱", 1)
            _talent_message(ctx, ("{n}の身体は注がれ続ける快楽に順応してしまい、", "絶えず刺激を欲するようになってしまった・・・"),
                            151, "になった", "GETTALENT_INRAN")
    # :348–352
    if (c.cflag[70] > 0 or c.cflag[286] + c.cflag[320] + c.cflag[321] > 4) and tl("嬲られ体質") == 0:
        set_t("嬲られ体質", 1)
        _msg_naburare(ctx)
    # :355–364
    toriko_lines = ("内外から叩き込まれる快楽が完全に{c}の精神を塗りつぶした、その瞬間。",
                    "{n}の中で最後まで張り詰めていた何かが、ぷつりと音を立てて切れてしまった・・・")
    if (
        tl("触手の虜") == 0
        and a("従順") + a("奉仕精神") >= 7
        and a("触手中毒") >= 4
        and mark(ctx, c, "屈服刻印") >= 4
        and mark(ctx, c, "恐怖刻印") + mark(ctx, c, "苦痛刻印") + mark(ctx, c, "恥辱刻印") >= 6
    ) or (tl("触手の虜") == 0 and tl("淫乱") >= 1 and a("触手中毒") >= 3 and exp(ctx, c, "幽閉経験") >= 1):
        set_t("触手の虜", 1)
        _talent_message(ctx, toriko_lines, 150, "になった", "GETTALENT_TORIKO")
    # :367–371 淫核
    if tl("淫核") == 0 and a("Ｃ感覚") >= 5 and c.ex[0] >= 50:
        set_t("淫核", 1)
        part = "陰茎" if is_male(data, c) else "陰核"
        _talent_message(ctx, (f"幾度も刺激を受けて慣らされた{{n}}の{part}は、", "そよ風程度の刺激すら快感として感じるようになってしまった・・・"), 153, "になった", "GETTALENT_INKAKU")
    # :374–378 淫壷（地の文に ESTRUS_TEXT_F が要る）
    if tl("淫壷") == 0 and a("Ｖ感覚") >= 5 and exp(ctx, c, "Ｖ経験") >= 200 and c.ex[1] >= 25:
        raise NotImplementedError("淫壷の取得（MESSAGE_GETTALENT_INTUBO の ESTRUS_TEXT_F）は未移植")
    # :381–385 淫尻
    if tl("淫尻") == 0 and a("Ａ感覚") >= 5 and exp(ctx, c, "Ａ経験") >= 200 and c.ex[2] >= 25:
        set_t("淫尻", 1)
        _talent_message(ctx, ("度重なる責めによって、数週間前とは比べ物にならないほど緩んだ{n}の菊門は、",
                              "埋められる快感と排泄の快感を深く刻み込まれてしまっていた・・・"), 155, "になった",
                        "GETTALENT_INJIRI")
    # :388–392 淫乳
    if tl("淫乳") == 0 and a("Ｂ感覚") >= 5 and c.ex[3] >= 50:
        set_t("淫乳", 1)
        _talent_message(ctx, ("触手によって責められ、弄ばれた{n}の胸はすっかり作り変えられ、",
                              "衣擦れ程度の刺激すら快感として感じるようになってしまった・・・"), 156, "になった",
                        "GETTALENT_INNYUU")
    # :395–399 清純派の消失
    if tl("初心") < 1 and tl("清純派") > 0 and (
        tl("触手の虜") > 0
        or tl("淫乱") > 0
        or a("欲望") + a("触手中毒") + a("自慰中毒") + a("精液中毒") + a("噴乳中毒") + a("射精中毒") >= 8
    ):
        set_t("清純派", -1)
        _talent_message(ctx, ("快楽を知った{n}の心は貞操観念を見失い", "かつての清純さは見る影もなくなってしまった・・・"),
                        301, "を失った", "LOSETALENT_SEIJUNHA")
    # :408–422 ふたなり
    if (tl("ふたなり") == 2 or tl("変身時ふたなり") == 2) and (
        a("射精中毒") >= 5 or exp(ctx, c, "射精経験") - c.cflag[39] >= 10
    ):
        raise NotImplementedError("寄生ふたなりの定着／消失は未移植")
    # :425–440 感度
    for part in ("Ｖ", "Ａ", "Ｂ", "Ｃ"):
        if tl(f"{part}鈍感") == 1 and a(f"{part}感覚") >= 3:
            set_t(f"{part}鈍感", 0)
        if tl(f"{part}敏感") == 0 and a(f"{part}感覚") >= 4:
            set_t(f"{part}敏感", 1)
    # :444–479 女体受容
    if tl("女体受容") == 0 and (
        tl("性別変化") % 10 == 1 or (tl("変身時ＴＳ") > 0 and is_female(data, c) and c.cflag[1] > 0)
    ):
        if (
            tl("触手の虜") > 0
            or tl("淫乱") > 0
            or tl("淫壷") > 0
            or (a("Ｖ感覚") >= 5 and a("精液中毒") + a("噴乳中毒") > a("射精中毒"))
            or exp(ctx, c, "出産経験") > 0
            or c.cflag[206] == 5
            or exp(ctx, c, "魅了経験") >= 200
            or (tl("両刀") > 0 and a("Ｖ感覚") >= 5)
        ):
            # 条件 3（:460）の LOVER_F 分岐は未移植のため、出産経験があれば安全側に停止する
            raise NotImplementedError("女体受容の取得は未移植")


def _msg_naburare(ctx: Ctx) -> None:
    _talent_message(ctx, ("幾度となく性玩具として弄ばれた{n}の身体は本人の自覚とは無関係に、",
                          "あらゆるオスを惹きつける淫靡なメスのフェロモンを漂わせるようになってしまった・・・"),
                    304, "になった", "GETTALENT_NABURARE")
