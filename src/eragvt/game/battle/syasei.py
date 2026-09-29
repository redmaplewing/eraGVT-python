"""触手の射精：`ゲーム内_戦闘処理/TENTACLE_SYASEI.ERB`（TENTACLE_SYASEI_UP／_CHECK／_POINT、TENTACLE_SAKUSEI）。

路徑相對 `source/earGVP/ERB/`。射精の地の文（`地の文/MESSAGE_SEX.ERB`:764–1060、状態変化なし）は
`core.chinobun` の 1 行に置き換える。悪堕ちキャラ・雑魚敵（901 妖精）の分岐は未移植で停止する。
"""

from __future__ import annotations

from ..action import Ctx, get_syuren, kojo_root, print_transcallname
from ..era import div, times
from ..tentacle import enemy_type_check
from .core import (
    KYOUKOUSOKU,
    P_HOUSHI,
    P_NASUGAMAMA,
    abl,
    run_chinobun,
    config_check_balance,
    t,
    tc,
    tentacle_access,
    unlock_achievement,
)
from .func import state_change_hairan, state_change_hatujou
from .ninsin import ninsin_hantei

# DIM.ERH:94–105
C_BIT, V_BIT, A_BIT, B_BIT, MOUTH, HAND, WAREME, BOUHATSU = 1, 2, 4, 8, 16, 32, 64, 128

_GIKOU = ("1.00", "1.10", "1.20", "1.25", "1.30", "1.35")
_SENSE = ("1.00", "1.05", "1.15", "1.25", "1.40", "1.80")
_BUST = {5: "1.40", 4: "1.35", 3: "1.30", 2: "1.25", 1: "1.20"}


def tentacle_syasei_up(ctx: Ctx, arg: int) -> None:
    """`@TENTACLE_SYASEI_UP, ARG`:4–84（ABL の値が 0〜5 以外なら補正なし：ELSEIF の列挙どおり）。"""
    st = ctx.state
    c = tc(ctx)
    g = abl(ctx, c, "技巧")
    if 0 <= g <= 5:
        arg = times(arg, _GIKOU[g])
    if st.temp.insert & V_BIT:
        s = abl(ctx, c, "Ｖ感覚")
        if 0 <= s <= 5:
            arg = times(arg, _SENSE[s])
    if st.temp.insert & A_BIT:
        s = abl(ctx, c, "Ａ感覚")
        if 0 <= s <= 5:
            arg = times(arg, _SENSE[s])
    if st.tflag[4] & B_BIT:
        f = _BUST.get(t(ctx, c, "巨乳"))
        if f:
            arg = times(arg, f)
    r = st.rng.rand(100)  # :67–77
    if r < 20:
        arg = times(arg, "0.90")
    elif r < 40:
        arg = times(arg, "0.95")
    elif r < 60:
        pass
    elif r < 80:
        arg = times(arg, "1.05")
    else:
        arg = times(arg, "1.10")
    if c.tcvarn[2] == P_NASUGAMAMA:
        arg = times(arg, "0.50")
    if c.tcvarn[2] == P_HOUSHI:
        arg = times(arg, "1.20")
    st.flag[15] += arg  # :84 FLAG:15（射精値）


def _clear_kyoukousoku(ctx: Ctx) -> None:
    v = tc(ctx).tcvarn
    if (v[12] & KYOUKOUSOKU) > 0:
        v[12] -= KYOUKOUSOKU


def tentacle_syasei_check(ctx: Ctx) -> tuple[int, int, int, int]:
    """`@TENTACLE_SYASEI_CHECK`:88–216。戻り値 (潤滑, 屈服, 恭順, 欲情) の UP 加算値。"""
    st = ctx.state
    f = st.flag
    if enemy_type_check(st, "AKUOTI") == 0 and f[11] == 901 and f[15] >= f[14]:
        raise NotImplementedError("雑魚敵（妖精）の敵絶頂（TENTACLE_SYASEI_CHECK:90–119）は未移植")
    if enemy_type_check(st, "AKUOTI") == 1 and f[15] >= f[14]:
        raise NotImplementedError("悪堕ちキャラの敵絶頂（TENTACLE_SYASEI_CHECK:120–149）は未移植")
    tf4 = st.tflag[4]
    if (tf4 == 0 or (tf4 & BOUHATSU)) and f[15] >= f[14]:  # :151–176
        if (f[15] >= f[14] * 2 and st.tflag[20] not in (15, 17, 19)) or (tf4 & BOUHATSU):
            st.tflag[3] += 200
            r = tentacle_syasei_point(ctx, 2)
            r = tentacle_sakusei(ctx, f[15] * 4, *r)
            f[15] = 0
            _clear_kyoukousoku(ctx)
            return r
        run_chinobun(ctx, "MESSAGE_SEX_TENTACLE_SYASEI_GAMAN")  # 地の文/MESSAGE_SEX.ERB:764–779
        tentacle_syasei_up(ctx, 50)
        return (0, 0, 0, 0)
    if f[15] >= f[14] * 2:  # :177–194
        st.tflag[3] += 200
        r = tentacle_syasei_point(ctx, 2)
        r = tentacle_sakusei(ctx, f[15] * 2, *r)
        f[15] = 0
        _clear_kyoukousoku(ctx)
        return r
    if f[15] >= f[14]:  # :195–212
        st.tflag[3] += 100
        r = tentacle_syasei_point(ctx, 1)
        r = tentacle_sakusei(ctx, f[15], *r)
        f[15] = f[15] - f[14]
        _clear_kyoukousoku(ctx)
        return r
    st.tflag[5] = 0  # :213–215
    return (0, 0, 0, 0)


_POINTS = {
    # 部位: (STAIN 番号, ARG=1 の (LOCAL:0, LOCAL:1, 従順係数, 欲望係数, 欲望加算), ARG=2 の同)
    WAREME: (3, (1000, 500, 100, 100, 0), (2000, 1000, 200, 200, 0), "WAREME"),
    V_BIT: (3, (2000, 1500, 200, 200, 2000), (4000, 3000, 400, 400, 2000), "VAGINA"),
    A_BIT: (4, (2000, 1000, 100, 100, 2000), (4000, 2000, 200, 200, 2000), "ANAL"),
    HAND: (1, (0, 250, 10, 10, 0), (0, 500, 20, 20, 0), "HAND"),
    MOUTH: (0, (0, 1000, 100, 100, 2000), (0, 2000, 200, 200, 2000), "MOUTH"),
    B_BIT: (2, (0, 500, 10, 10, 0), (0, 1000, 20, 20, 0), "BUST"),
}


def tentacle_syasei_point(ctx: Ctx, arg: int) -> tuple[int, int, int, int]:
    """`@TENTACLE_SYASEI_POINT, ARG`:220–568。悪堕ちキャラ分岐（LOCAL:3 = 0）は到達しない（呼び出し前に停止）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    loc = [0] * 6  # VARSET LOCAL（:221）。LOCAL:0,1,4,5 を返す。LOCAL:2 は精液量の合計
    out.printl()
    seieki = ctx.data.index_of("EXP", "精液経験")
    if st.tflag[4] == 0 or (st.tflag[4] & BOUHATSU):  # :223–234
        c.stain[1] |= 4
        st.tflag[5] |= BOUHATSU
        run_chinobun(ctx, "MESSAGE_SEX_TENTACLE_SYASEI_EXPLODE",  # MESSAGE_SEX.ERB:785–801（:800 KOJO_ROOT）
                     fallback=lambda: kojo_root(ctx, "SEX_TENTACLE_SYASEI_EXPLODE"))
        c.exp[seieki] += arg
        loc[2] += arg
    ju = abl(ctx, c, "従順")
    yo = abl(ctx, c, "欲望")
    for part in (WAREME, V_BIT, A_BIT, HAND, MOUTH, B_BIT):  # :236–559（記述順）
        if not (st.tflag[4] & part):
            continue
        stain_no, p1, p2, code = _POINTS[part]
        c.stain[stain_no] |= 4
        st.tflag[5] |= part
        if part == V_BIT:
            st.tflag[7] += arg  # :299
        if part == A_BIT:
            st.tflag[8] += arg  # :365
        if arg not in (1, 2):
            continue
        p = p1 if arg == 1 else p2
        sub = code + ("_HI" if arg == 2 else "")
        # MESSAGE_SEX.ERB:805–1063。WAREME(_HI) 以外は本文末尾で KOJO_ROOT(CFLAG:6, "SEX_TENTACLE_SYASEI_<sub>")
        run_chinobun(ctx, f"MESSAGE_SEX_TENTACLE_SYASEI_{sub}",
                     fallback=None if code == "WAREME" else (lambda s=sub: kojo_root(ctx, f"SEX_TENTACLE_SYASEI_{s}")))
        if part == V_BIT:  # :306／:326 受精判定
            ninsin_hantei(ctx, arg, 3 if arg == 1 else 15)
        loc[0] += p[0]
        loc[1] += p[1]
        loc[4] += p[2] * ju
        loc[5] += p[3] * yo + p[4]
        c.exp[seieki] += arg
        loc[2] += arg
        if part == V_BIT and t(ctx, c, "妊娠") in (4, 5):  # :345–351
            if t(ctx, c, "妊娠") == 5:
                out.printl(f"{print_transcallname(st, st.target)}の胎内に宿った新しい命が精液に汚されていく・・・")
            if st.rng.rand(2) == 0 and c.cflag[222] < 50 and c.cflag[222] not in (5, 8, 11):
                c.cflag[222] += 1
        if part == MOUTH:  # :505–508
            if st.tflag[20] != 16:
                state_change_hairan(ctx, arg)
            state_change_hatujou(ctx, 5)
    if config_check_balance(st, 3) > 0 and loc[2] > 0:  # :562–566
        out.printl(f"{print_transcallname(st, st.target)}は触手の精液からエネルギーを吸収した！")
        rand = st.rng.rand
        get_syuren(ctx, div(rand(10) + rand(loc[2] * 3) + loc[2] * 3 + 2, 2))
        out.printl()
    return (loc[0], loc[1], loc[4], loc[5])


def tentacle_sakusei(ctx: Ctx, arg: int, r1: int, r2: int, r3: int, r4: int) -> tuple[int, int, int, int]:
    """`@TENTACLE_SAKUSEI, ARG, ARG:1〜4`:572–607：射精による敵の体力消耗。ARG:1〜4 はそのまま返す。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if c.base[0] == 0 and c.base[1] == 0 and c.base[2] == 0:
        return (r1, r2, r3, r4)
    arg = div(arg - div(st.flag[14], 2), 10) + 500 + abl(ctx, c, "技巧") * 150
    if arg < 500:
        arg = 500
    if t(ctx, c, "背徳の烙印") > 0:
        arg *= div(135, 100)  # :581 `ARG *= 135 / 100`（整数除算で ×1：原作どおり）
    arg = div(arg * int(tentacle_access(ctx, "SAKUSEI")), 100)
    if st.flag[73] > 0:
        arg = 0
    st.flag[13] -= arg
    if st.flag[13] < 0:
        st.flag[13] = 0
    if st.flag[110] == 0:
        tentacle_access(ctx, "NAME")
    else:
        raise NotImplementedError("悪堕ちキャラの搾精表示は未移植")
    if st.flag[110] == 0 and st.flag[11] == 901:
        out.printw(f"は絶頂によって体力を{arg}消耗した！！")
    else:
        out.printw(f"は射精によって体力を{arg}消耗した！！")
    out.printl()
    if st.flag[13] <= 0:
        unlock_achievement(ctx, 267, "奇跡の逆転勝利")
    return (r1, r2, r3, r4)
