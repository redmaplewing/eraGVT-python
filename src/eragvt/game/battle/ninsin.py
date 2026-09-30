"""受精判定：`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_HANTEI`:11–165 と `@CHECK_HININ_F`:774–808、
`ヒロイン関連/ESTRUS_CYCLE.ERB@ESTRUS_TEXT_F`:30–46。

路徑相對 `source/earGVP/ERB/`。受精が成立した場合（:140 の判定が真）の NINSIN_SUBMIT／NINSIN_FLAG 以降
（妊娠状態の設定と地の文）は未移植で停止する（S06 規格「懷孕判定若走到可停止並登記」）。
"""

from __future__ import annotations

from ..action import Ctx, config_check_other
from ..chara_common import is_male
from ..era import div, isqrt
from ..tentacle import enemy_type_check
from .core import HAIRAN, HATUJOU, exp, t, tc


def check_pregnant(ctx: Ctx, who: int) -> int:
    """`@CHECK_PREGNANT_F(ARG)`:813–820。"""
    c = ctx.state.charas[who]
    p = t(ctx, c, "妊娠")
    return 1 if p in (1, 3) or (p == 5 and c.cflag[222] >= 11) else 0


def estrus_text(ctx: Ctx, who: int) -> str:
    """`@ESTRUS_TEXT_F(ARG, footertext="")`（ESTRUS_CYCLE.ERB:30–46）。"""
    c = ctx.state.charas[who]
    if t(ctx, c, "未熟") > 0 or is_male(ctx.data, c) or check_pregnant(ctx, who) > 0:
        return ""
    ab = t(ctx, c, "排卵異常")
    d = c.cflag[217]
    if 13 - ab <= d <= 15:
        return "危険日"
    if ab >= 3 or (16 <= d <= (19 if ab == 2 else 18)):
        return "危険日"
    return ""


def check_hinin(ctx: Ctx, who: int, arg1: int) -> int:
    """`@CHECK_HININ_F(ARG, ARG:1)`:774–808。"""
    st = ctx.state
    c = st.charas[who]
    local = 0
    if st.flag[700] > 0:
        # :780 `CFLAG:ARG:41 == 299 && CFLAG:1 > 0`（後半の CFLAG:1 は TARGET のもの：原作どおり）
        if c.cflag[41] == 299 and st.target_chara.cflag[1] > 0:
            local = 100
        elif c.cflag[241] > 0 and enemy_type_check(st, "AKUOTI") > 0:
            local = 80
        elif c.cflag[241] > 0:
            local = 5
        if t(ctx, c, "避妊結界") > 0 and c.base[2] > 0:
            local = 100
    else:
        if c.cflag[241] > 0 and arg1 < 0:
            local = 80
        elif c.cflag[241] > 0:
            local = 5
        if t(ctx, c, "避妊結界") > 0 and c.base[2] > 0 and arg1 > 0:
            local = 100
    return 1 if st.rng.rand(100) < local else 0


def charaid(ctx: Ctx, arg: int) -> int:
    """`汎用関数/コモン関数.ERB@CHARAID_F, ARG`:1062–1070：CFLAG:240（固有番号）== ARG のキャラ番号、無ければ 0。"""
    st = ctx.state
    for i in range(st.charanum):
        if i == 0:  # MASTER
            continue
        if st.charas[i].cflag[240] == arg:
            return i
    return 0


def ninsin_hantei(ctx: Ctx, arg0: int, arg1: int, arg2: int = 0) -> int:
    """`@NINSIN_HANTEI, ARG:0（射精量）, ARG:1（係数）, ARG:2 = 0`:11–165。"""
    st = ctx.state
    c = tc(ctx)
    if is_male(ctx.data, c):  # :16–21
        return 0
    if t(ctx, c, "未熟") > 0:
        return 0
    if t(ctx, c, "妊娠") > 0:
        return 0
    if config_check_other(st, 2) > 0:  # :23–24 常時避妊モード
        return 0
    if check_hinin(ctx, st.target, arg2) == 1:  # :26–36
        if st.flag[700] > 0:
            st.tflag[6] += arg0
        return 0
    if st.flag[700] > 0:
        arg0 += st.tflag[6]
    st.tflag[6] = 0
    # :39–67 父親の ID
    if c.cflag[0] in (1, 2, 3, 9) and arg2 == 0:
        papa = c.cflag[21] + (c.cflag[20] == 1) * 100
    elif st.flag[700] > 0 and arg2 == 0:
        if enemy_type_check(st, "AKUOTI") > 0:
            raise NotImplementedError("悪堕ちキャラによる受精判定は未移植")
        papa = st.flag[11]
        if enemy_type_check(st, "LASTBOSS") >= 1:
            papa += 100
        elif enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1:
            papa += 200
    elif arg2 != 0:  # :61–66
        papa = arg2
        o = st.charas[charaid(ctx, -arg2 - 100)]
        if (t(ctx, o, "ふたなり") == 2 or t(ctx, o, "変身時ふたなり") == 2) and st.rng.rand(4) != 0:
            papa = 200
    else:
        # PAPA_ID = 0 → :72–97 のどれにも当たらず PREG_PER（静的 #DIM）は前回の値のまま
        raise NotImplementedError("NINSIN_HANTEI：父親 ID 0（戦闘外・幽閉外）は未移植")
    c.cflag[221] += arg0  # :69
    birth = exp(ctx, c, "出産経験")
    pper = 0  # #DIM PREG_PER（関数ごとに保持されるが :74 以降で必ず代入される分岐のみ到達）
    if papa > 0:  # :72–75
        c.cflag[232] += arg0
        pper = isqrt(div(arg1 * c.cflag[232] * (birth + 1), 2))
    elif papa <= -100:  # :77–92
        raise NotImplementedError("NINSIN_HANTEI：仲間キャラの父親（PAPA_ID <= -100）は未移植")
    elif papa <= -1:  # :93–96 一般人（いちゃラブセックスの `愛する人` = -3：DIM.ERH:256）
        c.cflag[233] += arg0
        pper = isqrt(div(arg1 * c.cflag[233] * (birth + 1), 2))
    else:
        # PAPA_ID == 0 は :72–94 のどれにも当たらず PREG_PER（静的 #DIM）が前回値のまま
        raise NotImplementedError("NINSIN_HANTEI：PAPA_ID == 0 は未移植")
    if st.flag[700] == 1:  # :99–121
        pper *= 2
    if t(ctx, c, "苗床化"):
        pper *= 4
    if st.flag[909]:
        pper *= 2
    if t(ctx, c, "避妊結界") > 0 and papa > 0:
        pper *= 2
    if t(ctx, c, "獣性の証") > 0:
        pper = div(pper * 125, 100)
    if t(ctx, c, "祝福") > 0:
        pper = div(pper * 150, 100)
    if t(ctx, c, "不老長寿") > 0:
        pper = div(pper * 75, 100)
    if c.tcvarn[12] & HATUJOU:
        pper *= 2
    if estrus_text(ctx, st.target) != "":
        pper = div(pper * 3, 2)
    if c.tcvarn[12] & HAIRAN:
        pper = 1000
    if st.flag[999] == 1:  # :125–138
        raise NotImplementedError("デバッグモードの妊娠確率入力は未移植")
    # :140 `RAND:1000 < … && TALENT:妊娠 == 0`（RAND を先に引く）
    if st.rng.rand(1000) < pper + 100 * (c.cflag[0] == 0) and t(ctx, c, "妊娠") == 0:
        raise NotImplementedError("受精成立（NINSIN_SUBMIT／NINSIN_FLAG 以降の妊娠処理）は未移植")
    return 0


def _dot_after(ctx: Ctx) -> None:
    """`汎用関数/PRINT_LINE.ERB@DOT_AFTER, 1`:34–43。"""
    from ..action import config_check_screen

    out = ctx.out
    if config_check_screen(ctx.state, 3) == 0:
        out.printw("・・")
        out.printw("・・・・")
    else:
        out.printl("・・")
        out.printl("・・・・")
    out.printw("・・・・・・")


def after_pill(ctx: Ctx, arg: int, arg1: int, arg2: int):
    """`@AFTER_PILL, ARG, ARG:1, ARG:2`:898–957（ジェネレータ：INPUT）。ARG:1 = 成功率、ARG:2 = CHECK_HININ_F へ渡す父親。

    既定コンフィグ（FLAG:805 = 2：オープニング処理.ERB の初期設定）では CONFIG_CHECK_OTHER_F(3) == 0 で即 RETURN。"""
    from ..action import print_callname

    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    if config_check_other(st, 3) == 0:
        return 0
    if is_male(ctx.data, c):
        return 0
    if t(ctx, c, "未熟") > 0:
        return 0
    if t(ctx, c, "妊娠") in (1, 3, 5):
        return 0
    if c.cflag[241] > 0:
        return 0
    if config_check_other(st, 2) > 0:  # :911–912 常時避妊モード
        return 0
    out.printl()
    _dot_after(ctx)
    out.printl()
    out.printl(f"{print_callname(st, arg, 1)}は膣内射精されたことを自覚している…")
    out.print("時間が経ち過ぎて効果がないかもしれないが、" if arg1 < 25 else "このままでは妊娠してしまうかもしれないが、")
    out.printl("$500支払って緊急用アフターピルを飲んでおくべきだろうか？")
    out.printl("[0]アフターピルは飲まない")
    out.printl(f"[1]アフターピルを飲んで避妊する（所持金:${st.money}）")
    lcount = out.linecount  # :925
    while True:  # :926–957
        r = yield
        if r == 0:
            out.printl(f"{print_callname(st, arg)}はアフターピルを飲まないことにした…")
            return 0
        if r == 1:
            if st.money >= 500:
                st.money -= 500
                out.printl(f"{print_callname(st, arg)}はアフターピルを飲んだ…")
                out.printl("身体の底に疲労が蓄積した……（＋１５）")
                c.cflag[99] += 15
                if st.rng.rand(100) < arg1:  # :936–940（:938 は CHECK_HININ_F（RAND を引く）が && の左辺）
                    c.cflag[241] = 1
                    if check_hinin(ctx, arg, arg2) > 0 and c.cflag[222] == 0:
                        c.talent[ctx.data.index_of("TALENT", "妊娠")] = 0
                if st.flag[999] == 1:  # :941–948
                    raise NotImplementedError("デバッグ表示（AFTER_PILL:943–950）は未移植")
            else:
                out.printl("なんと、所持金が足りない！")
            return 0
        out.printl("妊娠の可能性に慌ててしまう気持ちも分かるが、ここは冷静になるべきだろう…")
        out.printw()
        out.clearline(out.linecount - lcount)
