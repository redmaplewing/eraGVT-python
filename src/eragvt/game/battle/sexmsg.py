"""性攻撃の地の文：`地の文/MESSAGE_SEX_COM.ERB`（MESSAGE_SEX_COM0〜20）と `地の文/MESSAGE_SEX_COMSP.ERB`
（MESSAGE_SEX_SPCOM0〜15）の**状態変化だけ**を移植する。

路徑相對 `source/earGVP/ERB/`。本文は `core.chinobun` の 1 行に置き換え（deviations.md「性攻撃の地の文」）、
各関数の KOJO_ROOT 呼び出し（FLAG:900 のリセットを含む）はそのまま呼ぶ。状態変化の洗い出しは
「代入・SETBIT・CALL を含む行とそれを囲む制御構造」を全行について確認した（PRINT／DATA 行と
MESSAGE_SEX_STATE（`地の文/MESSAGE_SEX_COMEX.ERB`:3–40、表示のみ）を除く）。
本文の選択にしか使われない RAND は引かない。制御構造の条件に入っている RAND（その後の分岐で状態が変わるもの）は
ERB の評価順どおりに引く。

引数は `ARG:0 = EX_COM`（追加責め部位）、`ARG:1 = SH_COM`（結界で阻まれた部位）。
"""

from __future__ import annotations

import functools

from ..action import Ctx, config_check_maniac, kojo_root
from ..chara_common import is_female, is_male
from ..tentacle import enemy_type_check
from .core import (
    DARAKU,
    P_V_GUARD,
    chinobun,
    get_battle_situation,
    is_penis,
    message_branch,
    t,
    tc,
)
from .gaping import set_tentacle_size_by_message as by_msg

C, V, A, B = 1, 2, 4, 8
MOUTH, HAND, WAREME = 16, 32, 64


def istentacler(ctx: Ctx, who: int = -1) -> int:
    """`汎用関数/SEX_GENDER.ERB@ISTENTACLER(ARG=-1)`:169–179（ARG == 0 は常に 1）。"""
    st = ctx.state
    if who == 0:
        return 1
    c = st.charas[st.target if who == -1 else who]
    return 1 if t(ctx, c, "寄生") and config_check_maniac(st, 13) == 1 else 0


def _filming(ctx: Ctx) -> bool:
    """`FLAG:71 || GETBATTLESITUATION("常時撮影")`。"""
    st = ctx.state
    return bool(st.flag[71] or get_battle_situation(st, "常時撮影"))


def _akuoti(ctx: Ctx) -> bool:
    return enemy_type_check(ctx.state, "AKUOTI") == 1


def _catalog(name: str, erb_args: int = 2):
    """S07：catalog で `name` を実行できればそれで終わり（本文・RAND・状態変化を ERB の順で：状態変化行は
    `eragvt.narration.hooks` 経由で下の Python 移植と同じ処理を呼ぶ）。実行できなければ従来の Python 移植。
    erb_args = 原作の CALL で渡す引数の数（`CALL MESSAGE_SEX_COM8` のように引数なしのものは 0）。"""

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(ctx: Ctx, *args):
            if ctx.narration.run_function(ctx, name, list(args[:erb_args])):
                return None
            return fn(ctx, *args)

        return wrapper

    return deco


def _head(ctx: Ctx, n: str) -> None:
    chinobun(ctx, f"MESSAGE_SEX_{n}")


def _sz(ctx: Ctx, part: int) -> int:
    return ctx.state.temp.tentacle_size[(0, part)]


def _film_any(ctx: Ctx, arg: int, bit: int) -> None:
    """`IF FLAG:71 || 常時撮影 / SIF (ARG & Ｃ) || … || (ARG & Ｂ) / SETBIT TFLAG:21,bit`。"""
    if _filming(ctx) and (arg & (C | V | A | B)):
        ctx.state.tflag.set_bit(21, bit)


# --- MESSAGE_SEX_COM.ERB ------------------------------------------------------------


@_catalog("MESSAGE_SEX_COM0", 2)
def msg_com0(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM0`:7–384。"""
    _head(ctx, "COM0")
    kojo_root(ctx, "SEX_COM0")  # :377
    _film_any(ctx, arg, 1)  # :380–384


@_catalog("MESSAGE_SEX_COM1", 2)
def msg_com1(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM1`:388–829。"""
    st = ctx.state
    _head(ctx, "COM1")
    f111 = st.flag[111]
    kizetu = tc(ctx).tcvarn[12] & 1

    def v_insert(cond_akuoti: bool, skip: bool) -> None:
        if cond_akuoti:
            if not skip:
                by_msg(ctx, "Ｖ", "普通", "単数")
        else:
            by_msg(ctx, "Ｖ", "普通", "単数")
        if arg & C:
            by_msg(ctx, "Ｃ", "", "単数")
            st.temp.tentacle_size[(0, 0)] = st.temp.tentacle_size[(0, 1)]

    fut111 = t(ctx, st.charas[f111], "ふたなり") > 0
    male111 = is_male(ctx.data, st.charas[f111])
    if kizetu:  # :400
        if is_penis(ctx):  # :401
            pass
        elif arg & V:  # :437–456（:438 は `(悪堕ち && 寄生) || ISPENIS(FLAG:111)`：左結合）
            v_insert((_akuoti(ctx) and istentacler(ctx, f111) == 1) or is_penis(ctx, f111), fut111 or male111)
        elif st.rng.rand(2) == 0 and (arg & C) and (st.flag[110] == 0 or istentacler(ctx, f111) == 1):  # :511
            by_msg(ctx, "Ｃ", "繊毛", "複数")
    else:
        if is_penis(ctx):  # :574
            pass
        elif (arg & V) or ((arg & C) and _akuoti(ctx)):  # :613–665
            v_insert(_akuoti(ctx) and (istentacler(ctx, f111) == 1 or is_penis(ctx, f111)),
                     male111 or istentacler(ctx, f111) == 0)
        elif st.rng.rand(2) == 0 and (arg & C) and (st.flag[110] == 0 or istentacler(ctx, f111) == 1):  # :712
            by_msg(ctx, "Ｃ", "繊毛", "複数")
    kojo_root(ctx, "SEX_COM1")  # :821
    _film_any(ctx, arg, 1)  # :824–828


@_catalog("MESSAGE_SEX_COM2", 2)
def msg_com2(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM2`:832–1284。"""
    from .syasei import tentacle_syasei_up
    from .ninsin import ninsin_hantei

    st = ctx.state
    c = tc(ctx)
    _head(ctx, "COM2")
    f111 = st.flag[111]
    if _akuoti(ctx) and istentacler(ctx, f111) == 0:  # :853
        st.flag[900] = 1
    elif st.rng.rand(4) == 0 and (arg & C):  # :888
        st.flag[900] = 1
    elif st.rng.rand(3) == 0 and (arg & C):  # :916
        st.flag[900] = 2
    else:  # :951
        if arg & V:  # :968–1027
            tentacle_syasei_up(ctx, 100)
            st.tflag[4] |= WAREME
            if st.rng.rand(100) < 10:
                st.tflag[4] = 0
        st.flag[900] = 3  # :1052
        if _sz(ctx, 1) < 40:
            by_msg(ctx, "Ｖ", "普通", "単数")
        else:
            by_msg(ctx, "Ｖ", "", "単数")
    kojo_root(ctx, "SEX_COM2")  # :1171
    if st.flag[15] >= st.flag[14] and (st.tflag[4] & WAREME):  # :1179–1277
        if c.tcvarn[2] == P_V_GUARD:
            st.tflag[4] -= WAREME
            st.tflag[4] |= HAND
            if st.flag[15] >= st.flag[14] * 2:
                st.tflag[4] |= B
        elif st.flag[15] >= st.flag[14] * 2:
            ninsin_hantei(ctx, 2, 50)
        else:
            ninsin_hantei(ctx, 1, 10)
    _film_any(ctx, arg, 1)  # :1279–1283


@_catalog("MESSAGE_SEX_COM3", 2)
def msg_com3(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM3`:1287–1866。"""
    st = ctx.state
    _head(ctx, "COM3")
    f111 = st.flag[111]
    rand = st.rng.rand
    if _akuoti(ctx) and istentacler(ctx, f111) == 0 and is_penis(ctx, f111):  # :1308
        pass
    elif rand(5) == 0 or rand(4) == 0 or rand(3) == 0:  # :1432／:1456／:1480（状態変化なし）
        pass
    elif rand(2) == 0:  # :1499–1526
        if _sz(ctx, 1) >= 155:
            by_msg(ctx, "Ｖ", "普通", "たくさん")
        else:
            by_msg(ctx, "Ｖ", "普通", "複数")
    else:  # :1527–1557
        if _sz(ctx, 1) < 40:
            by_msg(ctx, "Ｖ", "普通", "単数")
        else:
            by_msg(ctx, "Ｖ", "", "単数")
    kojo_root(ctx, "SEX_COM3")  # :1561
    if _filming(ctx):  # :1855–1865
        if arg & (C | B):
            st.tflag.set_bit(21, 1)
        if arg & (V | A):
            st.tflag.set_bit(21, 3)
        if (arg & V) == 0:
            st.tflag.set_bit(21, 2)


@_catalog("MESSAGE_SEX_COM4", 2)
def msg_com4(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM4`:1869–2056。"""
    st = ctx.state
    _head(ctx, "COM4")
    if _akuoti(ctx) and istentacler(ctx, st.flag[111]) == 0:  # :1881
        pass
    elif st.rng.rand(2) == 0 and (arg & A):  # :1904–1945
        if _sz(ctx, 2) < 40:
            by_msg(ctx, "Ａ", "普通", "単数")
        else:
            by_msg(ctx, "Ａ", "", "複数")
    kojo_root(ctx, "SEX_COM4")  # :2047
    _film_any(ctx, arg, 1)  # :2050–2054


@_catalog("MESSAGE_SEX_COM5", 2)
def msg_com5(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM5`:2059–2300。:2200–2201 `SIF TALENT:処女 > 0 / CALL LOSTVIRGIN`（SEX_COM5 側で既に
    喪失済みなら TALENT:処女 は -1）。"""
    st = ctx.state
    c = tc(ctx)
    _head(ctx, "COM5")
    if (arg & V) and c.tcvarn[2] != P_V_GUARD and t(ctx, c, "処女") > 0:  # :2188–2201
        from .sexcom import lostvirgin

        lostvirgin(ctx)
    kojo_root(ctx, "SEX_COM5")  # :2221
    if _filming(ctx):  # :2291–2298
        if arg & (C | B):
            st.tflag.set_bit(21, 1)
        if arg & (V | A):
            st.tflag.set_bit(21, 3)


@_catalog("MESSAGE_SEX_COM6", 2)
def msg_com6(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM6`:2303–2446。"""
    st = ctx.state
    c = tc(ctx)
    _head(ctx, "COM6")
    if _akuoti(ctx) and istentacler(ctx, st.flag[111]) == 0:  # :2315
        st.flag[900] = 1
    elif st.rng.rand(4) == 0 and t(ctx, c, "巨乳") > 0 and (arg & B):  # :2341
        st.flag[900] = 1
    elif st.rng.rand(2) == 0 and (arg & B):  # :2352
        st.flag[900] = 1
    elif arg & B:  # :2372
        st.flag[900] = 2
    kojo_root(ctx, "SEX_COM6")  # :2437
    _film_any(ctx, arg, 1)  # :2440–2444


@_catalog("MESSAGE_SEX_COM7", 2)
def msg_com7(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM7`:2449–2636。"""
    st = ctx.state
    c = tc(ctx)
    _head(ctx, "COM7")
    if _akuoti(ctx) and istentacler(ctx, st.flag[111]) == 0:  # :2461–2500
        if (arg & B) == 0:
            pass
        elif is_male(ctx.data, c):
            st.flag[900] = 1
        elif st.rng.rand(2) == 0:
            st.flag[900] = 2
        else:
            st.flag[900] = 1
    elif arg & B:  # :2501
        st.flag[900] = 3
    if arg & V:  # :2588–2604
        if _sz(ctx, 1) >= 40:
            by_msg(ctx, "Ｖ", "細い", "たくさん")
        else:
            by_msg(ctx, "Ｖ", "繊毛", "たくさん")
    kojo_root(ctx, "SEX_COM7")  # :2628
    _film_any(ctx, arg, 1)  # :2631–2635


@_catalog("MESSAGE_SEX_COM8", 0)
def msg_com8(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_COM8`:2639–2768（残酷表現 OFF／気絶の分岐以外は RAND:4 で FLAG:900 を決める）。"""
    st = ctx.state
    _head(ctx, "COM8")
    kizetu = tc(ctx).tcvarn[12] & 1
    if not _akuoti(ctx):  # :2650–2703
        if config_check_maniac(st, 14) == 0:
            pass
        elif not kizetu:
            st.flag[900] = {3: 1, 2: 2, 1: 3, 0: 4}[st.rng.rand(4)]
        else:
            st.flag[900] = 4
    else:  # :2704–2757
        if config_check_maniac(st, 14) == 0:
            pass
        elif not kizetu:
            st.flag[900] = {3: 5, 2: 2, 1: 3, 0: 4}[st.rng.rand(4)]
        else:
            st.flag[900] = 4
    kojo_root(ctx, "SEX_COM8")  # :2761
    if _filming(ctx):  # :2764–2767
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_COM9", 0)
def msg_com9(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_COM9`:2771–2825。"""
    st = ctx.state
    _head(ctx, "COM9")
    st.flag[900] = 1 if st.rng.rand(2) == 0 else 2  # :2791–2799
    kojo_root(ctx, "SEX_COM9")  # :2818
    if _filming(ctx):  # :2821–2824
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_COM10", 2)
def msg_com10(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM10`:2829–2975。"""
    st = ctx.state
    _head(ctx, "COM10")
    if _akuoti(ctx) and istentacler(ctx, st.flag[111]) == 0:  # :2850
        pass
    else:  # :2884–2963
        if arg & (C | V | A | B):  # :2907
            thick = _sz(ctx, 1) >= 40  # :2918／:2928／:2938 はどれも TENTACLE_SIZE:0:快Ｖ を見る（原作どおり）
            if arg & B:
                by_msg(ctx, "Ｂ", "細い" if thick else "繊毛", "たくさん")
            thick = _sz(ctx, 1) >= 40
            if arg & V:
                by_msg(ctx, "Ｖ", "細い" if thick else "繊毛", "たくさん")
            thick = _sz(ctx, 1) >= 40
            if arg & A:
                by_msg(ctx, "Ａ", "細い" if thick else "繊毛", "たくさん")
            if arg & C:
                by_msg(ctx, "Ｃ", "細い", "単数")
        st.flag[900] = 2
    kojo_root(ctx, "SEX_COM10")  # :2967
    _film_any(ctx, arg, 1)  # :2970–2974


@_catalog("MESSAGE_SEX_COM11", 2)
def msg_com11(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM11`:2978–3153。"""
    st = ctx.state
    _head(ctx, "COM11")
    if arg & (C | V | A):  # :3066–3090
        if arg & V:
            by_msg(ctx, "Ｖ", "細い" if _sz(ctx, 1) >= 40 else "繊毛", "たくさん")
        if arg & A:
            by_msg(ctx, "Ａ", "細い" if _sz(ctx, 1) >= 40 else "繊毛", "たくさん")
    kojo_root(ctx, "SEX_COM11")  # :3093
    if _filming(ctx):  # :3146–3152
        if arg & (C | V | A | B):
            st.tflag.set_bit(21, 1)
        st.tflag.set_bit(21, 2)


@_catalog("MESSAGE_SEX_COM12", 0)
def msg_com12(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_COM12`:3156–3277。"""
    st = ctx.state
    _head(ctx, "COM12")
    kojo_root(ctx, "SEX_COM12")  # :3223
    if _filming(ctx):  # :3271–3276
        st.tflag.set_bit(21, 2)
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_COM13", 2)
def msg_com13(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_COM13`:3280–3361。:3354 は KOJO_ROOT を通さない `TRYCALLFORM KOJO_{CFLAG:6}_SEX_COM13`
    （口上未移植：deviations.md「口上」、見つからない扱いで何もしない）。"""
    st = ctx.state
    _head(ctx, "COM13")
    if _filming(ctx):  # :3357–3360
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_COM14", 0)
def msg_com14(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_COM14`:3365–3410。:3408 は `TRYCALLFORM KOJO_{CFLAG:6}_SEX_COM14`（KOJO_ROOT ではないので
    FLAG:900 はリセットされない：原作どおり）。"""
    st = ctx.state
    cl = st.temp.cloth
    c = tc(ctx)
    _head(ctx, "COM14")
    if cl[1] < cl[2] and c.cflag[42] == 398:  # :3388
        st.flag[900] = 1
    elif st.rng.rand(3) == 0 and (st.flag[110] == 0 or istentacler(ctx, st.flag[111]) == 1):  # :3392
        st.flag[900] = 2
    elif st.rng.rand(4) == 0:  # :3396
        st.flag[900] = 1
    else:  # :3400–3404
        st.flag[900] = 1


def _msg_plain(ctx: Ctx, n: int) -> None:
    """MESSAGE_SEX_COM15〜20（:3414–3990）：状態変化なし、最後に KOJO_ROOT。"""
    _head(ctx, f"COM{n}")
    kojo_root(ctx, f"SEX_COM{n}")


# --- MESSAGE_SEX_COMSP.ERB -----------------------------------------------------------


@_catalog("MESSAGE_SEX_SPCOM0", 2)
def msg_spcom0(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM0`:12–224。"""
    _head(ctx, "SPCOM0")
    kojo_root(ctx, "SEX_SPCOM0")  # :116
    _film_any(ctx, arg, 1)  # :217–221


@_catalog("MESSAGE_SEX_SPCOM1", 2)
def msg_spcom1(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM1`:228–588。"""
    st = ctx.state
    _head(ctx, "SPCOM1")
    f111 = st.flag[111]
    c111 = st.charas[f111]
    if _akuoti(ctx) and istentacler(ctx, f111) == 0 and (t(ctx, c111, "ふたなり") > 0 or is_male(ctx.data, c111)):
        kojo_root(ctx, "SEX_SPCOM1")  # :371
    else:  # :417–
        if _sz(ctx, 1) < 40:
            by_msg(ctx, "Ｖ", "普通", "単数")
        else:
            by_msg(ctx, "Ｖ", "", "単数")
        if _sz(ctx, 2) < 40:
            by_msg(ctx, "Ａ", "普通", "単数")
        else:
            by_msg(ctx, "Ａ", "", "単数")
        kojo_root(ctx, "SEX_SPCOM1")  # :524
    if _filming(ctx):  # :578–585
        if arg & (C | B):
            st.tflag.set_bit(21, 1)
        if arg & (V | A):
            st.tflag.set_bit(21, 3)


@_catalog("MESSAGE_SEX_SPCOM2", 2)
def msg_spcom2(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM2`:592–781。"""
    st = ctx.state
    c = tc(ctx)
    _head(ctx, "SPCOM2")
    if _sz(ctx, 2) < 40:  # :599–601
        by_msg(ctx, "Ａ", "", "たくさん")
    vg = c.tcvarn[2] == P_V_GUARD
    if not vg and (arg & V):  # :620–644
        if _sz(ctx, 1) < 40:
            by_msg(ctx, "Ｖ", "普通", "たくさん")
        elif _sz(ctx, 1) >= 60:
            by_msg(ctx, "Ｖ", "太い", "複数")
        if _sz(ctx, 2) < 40:
            by_msg(ctx, "Ａ", "普通", "たくさん")
        elif _sz(ctx, 2) >= 60:
            by_msg(ctx, "Ａ", "太い", "複数")
    elif arg & A:  # :645–654
        if _sz(ctx, 2) < 40:
            by_msg(ctx, "Ａ", "普通", "たくさん")
        elif _sz(ctx, 2) >= 60:
            by_msg(ctx, "Ａ", "太い", "複数")
    elif arg & V:  # :655–690
        if not vg:
            if _sz(ctx, 1) < 40:
                by_msg(ctx, "Ｖ", "普通", "単数")
            elif _sz(ctx, 1) >= 60:
                by_msg(ctx, "Ｖ", "太い", "単数")
    kojo_root(ctx, "SEX_SPCOM2")  # :722
    if _filming(ctx):  # :772–779
        if arg & (C | B):
            st.tflag.set_bit(21, 1)
        if arg & (V | A):
            st.tflag.set_bit(21, 3)


@_catalog("MESSAGE_SEX_SPCOM3", 2)
def msg_spcom3(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM3`:785–903。"""
    _head(ctx, "SPCOM3")
    kojo_root(ctx, "SEX_SPCOM3")  # :894
    _film_any(ctx, arg, 1)  # :897–901


@_catalog("MESSAGE_SEX_SPCOM4", 0)
def msg_spcom4(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_SPCOM4`:907–952。"""
    st = ctx.state
    _head(ctx, "SPCOM4")
    kojo_root(ctx, "SEX_SPCOM4")  # :944
    if _filming(ctx):  # :947–950
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_SPCOM5", 2)
def msg_spcom5(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM5`:956–1095。"""
    st = ctx.state
    _head(ctx, "SPCOM5")
    kojo_root(ctx, "SEX_SPCOM5")  # :1057
    if _filming(ctx):  # :1087–1093
        if arg & (C | V | A | B):
            st.tflag.set_bit(21, 1)
        st.tflag.set_bit(21, 2)


@_catalog("MESSAGE_SEX_SPCOM6", 0)
def msg_spcom6(ctx: Ctx) -> None:
    """`@MESSAGE_SEX_SPCOM6`:1099–1122。"""
    _head(ctx, "SPCOM6")
    kojo_root(ctx, "SEX_SPCOM6")  # :1120


def msg_spcom7(ctx: Ctx):
    """`@MESSAGE_SEX_SPCOM7`:1126–1300（ジェネレータ：:1235–1238 の INPUTS）。

    catalog では INPUTS（:1237）が子集合外のため常に Python 移植（本文は佔位）。
    :1234–1240 CFLAG:34 > 0 なら「[1]映像を見る」を出して INPUTS、CLEARLINE。RESULTS == "1" なら動画サイト
    （MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window：独自ウィンドウ描画＋GOTO／INPUTS ループ）
    に入るが未移植のため停止。
    DEVIATION: Web の入力は整数のみなので、INPUTS の文字列は `str(整数)`（空文字・非数値は入力できない）。"""
    if ctx.narration.run_function(ctx, "MESSAGE_SEX_SPCOM7", []):
        return
    st = ctx.state
    c = tc(ctx)
    cl = st.temp.cloth
    _head(ctx, "SPCOM7")
    if _akuoti(ctx) and istentacler(ctx, st.flag[111]) == 0 and is_female(ctx.data, c) and (
        message_branch(ctx) & DARAKU
    ) == 0:  # :1136
        st.flag[900] = 1
    elif st.flag[70] + st.flag[71] > 0:  # :1148–1228
        # :1151 `FLAG:11 == 7 && TCVARn:25 > 0 && RAND:2 == 0 && …`（短絡：前 2 条件が真のときだけ RAND）
        if st.flag[11] == 7 and c.tcvarn[25] > 0 and st.rng.rand(2) == 0 and cl[1] < cl[2] and cl[0] == 0:
            c.tcvarn[25] = 0
        st.flag[900] = 2
    else:  # :1229–1293
        results = "0"
        if c.cflag[34] > 0:  # :1234–1238
            lcount = ctx.out.linecount
            ctx.out.printl("[1]映像を見る")
            # DEVIATION: INPUTS は任意の文字列だが、Web の入力は整数のみ → str(整数)（deviations.md「INPUTS 只能輸入整數」）
            results = str((yield))  # INPUTS（Instraction.Child.cs:642–667、EmueraConsole.cs:722–728）
            ctx.out.clearline(ctx.out.linecount - lcount)
        if results == "1":  # :1242
            raise NotImplementedError("動画サイト表示（MESSAGE_SEX_VIDEO_SITE_Window、MESSAGE_SEX_SPCOM7:1242–1279）は未移植")
        st.flag[900] = 3
    kojo_root(ctx, "SEX_SPCOM7")  # :1297


@_catalog("MESSAGE_SEX_SPCOM8", 2)
def msg_spcom8(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM8`:1304–1356。"""
    _head(ctx, "SPCOM8")
    kojo_root(ctx, "SEX_SPCOM8")  # :1351


@_catalog("MESSAGE_SEX_SPCOM9", 2)
def msg_spcom9(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM9`:1359–1576。"""
    st = ctx.state
    c = tc(ctx)
    _head(ctx, "SPCOM9")
    if _sz(ctx, 1) < 60:  # :1366–1372
        by_msg(ctx, "Ｖ", "普通", "たくさん")
    elif _sz(ctx, 1) < 115:
        by_msg(ctx, "Ｖ", "太い", "複数")
    else:
        by_msg(ctx, "Ｖ", "極太", "単数")
    if t(ctx, c, "処女") > 0:  # :1474–1483
        c.cflag.set_bit(206, 3)
    kojo_root(ctx, "SEX_SPCOM9")  # :1559
    if _filming(ctx):  # :1568–1574
        if arg & V:
            st.tflag.set_bit(21, 3)
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_SPCOM10", 2)
def msg_spcom10(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM10`:1580–1650。"""
    st = ctx.state
    _head(ctx, "SPCOM10")
    if _sz(ctx, 2) < 60:  # :1587–1593
        by_msg(ctx, "Ａ", "普通", "たくさん")
    elif _sz(ctx, 2) < 115:
        by_msg(ctx, "Ａ", "太い", "複数")
    else:
        by_msg(ctx, "Ａ", "極太", "単数")
    kojo_root(ctx, "SEX_SPCOM10")  # :1628
    if _filming(ctx):  # :1642–1648
        if arg & A:
            st.tflag.set_bit(21, 3)
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_SPCOM11", 2)
def msg_spcom11(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM11`:1654–1826。"""
    from .sexcom import check_holyvirgin

    st = ctx.state
    c = tc(ctx)
    _head(ctx, "SPCOM11")
    by_msg(ctx, "Ｖ", "", "単数")  # :1661
    if check_holyvirgin(ctx) != 1 and t(ctx, c, "処女") > 0:  # :1687–1751
        c.cflag.set_bit(206, 3)
    kojo_root(ctx, "SEX_SPCOM11")  # :1804
    if _filming(ctx):  # :1817–1824
        if arg & B:
            st.tflag.set_bit(21, 1)
        if (arg & V) and check_holyvirgin(ctx) == 0:
            st.tflag.set_bit(21, 3)


@_catalog("MESSAGE_SEX_SPCOM12", 0)
def msg_spcom12(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM12`:1830–1907。"""
    st = ctx.state
    _head(ctx, "SPCOM12")
    kojo_root(ctx, "SEX_SPCOM12")  # :1856
    if _filming(ctx):  # :1902–1905
        st.tflag.set_bit(21, 7)


@_catalog("MESSAGE_SEX_SPCOM13_PRE", 0)
def msg_spcom13_pre(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM13_PRE`:1911–1926（丸飲み準備）。"""
    _head(ctx, "SPCOM13_PRE")
    ctx.state.tflag[23] += 1  # :1926


@_catalog("MESSAGE_SEX_SPCOM13", 0)
def msg_spcom13(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM13`:1929–2105（KOJO_ROOT は FORCEPRINT = 1）。"""
    c = tc(ctx)
    _head(ctx, "SPCOM13")
    kojo_root(ctx, "SEX_SPCOM13", 1)  # :1969
    kojo_root(ctx, "SEX_SPCOM13_FINISHER_0", 1)  # :1987
    kojo_root(ctx, "SEX_SPCOM13_FINISHER_1", 1)  # :2002
    if t(ctx, c, "処女") > 0:  # :2011–2018
        c.cflag.set_bit(206, 3)
    kojo_root(ctx, "SEX_SPCOM13_FINISHER_2", 1)  # :2028
    kojo_root(ctx, "SEX_SPCOM13_FINISHER_3", 1)  # :2042
    c.tcvarn[12] |= 1  # :2058 気絶
    # :2062–2101 FINISHER 4〜10 の口上と射精の地の文（状態変化なし）
    for i in range(4, 11):
        kojo_root(ctx, f"SEX_SPCOM13_FINISHER_{i}", 1)


@_catalog("MESSAGE_SEX_SPCOM13_MISS", 0)
def msg_spcom13_miss(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM13_MISS`:2109–2119。"""
    _head(ctx, "SPCOM13_MISS")
    ctx.state.tflag[23] += 1  # :2117


@_catalog("MESSAGE_SEX_SPCOM14", 2)
def msg_spcom14(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM14`:2123–2323。"""
    c = tc(ctx)
    _head(ctx, "SPCOM14")
    if t(ctx, c, "交際相手") > 0 and (c.tcvarn[12] & 1):  # :2144–2241
        if t(ctx, c, "処女") > 0:
            c.cflag.set_bit(206, 3)
    else:  # :2259–2313
        if t(ctx, c, "処女") > 0:
            c.cflag.set_bit(206, 3)
        if _sz(ctx, 1) < 40:
            by_msg(ctx, "Ｖ", "普通", "単数")
        elif _sz(ctx, 1) >= 60:
            by_msg(ctx, "Ｖ", "太い", "単数")
    kojo_root(ctx, "SEX_SPCOM14")  # :2320


@_catalog("MESSAGE_SEX_SPCOM15", 2)
def msg_spcom15(ctx: Ctx, arg: int, arg1: int) -> None:
    """`@MESSAGE_SEX_SPCOM15`:2327–2362。"""
    c = tc(ctx)
    _head(ctx, "SPCOM15")
    kojo_root(ctx, "SEX_SPCOM15")  # :2347
    by_msg(ctx, "Ｖ", "太い", "単数")  # :2350
    if t(ctx, c, "処女") > 0:  # :2356–2360
        c.cflag.set_bit(206, 3)


def msg_plain(ctx: Ctx, n: int) -> None:
    """MESSAGE_SEX_COM15〜20（`CALL MESSAGE_SEX_COMn, EX_COM, SH_COM`）。"""
    st = ctx.state
    if ctx.narration.run_function(ctx, f"MESSAGE_SEX_COM{n}", [st.temp.ex_com, st.temp.sh_com]):
        return
    _msg_plain(ctx, n)
