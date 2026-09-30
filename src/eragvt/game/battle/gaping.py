"""触手サイズと拡張：`ゲーム内_戦闘処理/GAPING.ERB`（SET_TENTACLE_SIZE 系・GAPING_SIZE 系）と
`PALAM_UP.ERB@PALAM_CALC_GAPING`:771–816、ボス触手の `TENTACLE_BOSS_{n}_TENTACLE_SIZE`。

路徑相對 `source/earGVP/ERB/`。TENTACLE_SIZE／TENTACLE_NUM は `st.temp.tentacle_size[(i, j)]`（DIM.ERH:159–160）。

拡張（V_GAPING／A_GAPING／GET_*_GAPING_EXP）は CFLAG:34 == 0 なら何もしない（GAPING.ERB:864–865、942–943、
1015–1016、1044–1045）。CFLAG:34（成長曲線）を書くのは GENERATE_BODYLINE（CHARA_SIZE.ERB:540）・
CHARA_SIZE_DEFAULT（CHARA_SIZE_UI.ERB:2157）・CHARA_MAKE_BASE_PROFILE:980 で、初期セットのキャラ（NO ≠ 0）は
原作でもどれも通らない（`eragvt.game.body`、`docs/wiki/era/body-profile.md`）ため 0 のまま。0 以外に到達したら停止する。
身長・腰囲（BASE:43／47）も同じ理由で 0（膨乳化の SET_PROFILE 後は非 0）。式は原作どおり。
"""

from __future__ import annotations

from ..action import Ctx, config_check_maniac
from ..era import div, isqrt, times
from .core import t, tc, tentacle_level

# DIM.ERH:94–105
C_BIT, V_BIT, A_BIT, B_BIT = 1, 2, 4, 8


def _sz(st) -> object:
    return st.temp.tentacle_size


def _num(st) -> object:
    return st.temp.tentacle_num


# --- GAPING_RANK 系（GAPING.ERB:81–332）---------------------------------------------------

_RANK_BOUNDS = (5, 15, 25, 40, 60, 85, 115, 155, 205, 265, 335, 465, 635, 765, 935, 1065, 1205)


def gaping_rank(arg: int) -> int:
    """`@GAPING_RANK(ARG)`:81–140。"""
    for i, b in enumerate(_RANK_BOUNDS):
        if arg < b:
            return i
    return 17


_RANK_POINT = {0: 0, 1: 5, 2: 15, 3: 25, 4: 40, 5: 60, 6: 85, 7: 115, 8: 155, 9: 205, 10: 265, 11: 335, -1: -5,
               12: 465, 13: 635, 14: 765, 15: 935, 16: 1065, 17: 1205}


def gaping_rank_to_point(arg: int) -> int:
    """`@GAPING_RANK_TO_POINT(ARG)`:286–332（該当なしは VARSET 後の 0）。"""
    return _RANK_POINT.get(arg, 0)


def get_height(ctx: Ctx, con: int, tar: int) -> int:
    """`@GET_HEIGHT(CON, TAR)`:584–608。TAR == 0 のときは TARGET を変えない（現在の TARGET）。"""
    st = ctx.state
    if tar < 0:
        return 1581
    c = st.charas[tar] if tar > 0 else st.target_chara
    if con == 0 or t(ctx, c, "変身能力") != 1:
        return c.base[43]
    return c.maxbase[43]


def get_hip(ctx: Ctx, con: int, tar: int) -> int:
    """`@GET_HIP(CON, TAR)`:615–639。"""
    st = ctx.state
    if tar < 0:
        return 816
    c = st.charas[tar] if tar > 0 else st.target_chara
    if con == 1 or t(ctx, c, "変身能力") != 1 or (con == 0 and c.cflag[1] == 0):
        return c.base[47]
    return c.maxbase[47]


def _gs(ctx: Ctx, n: int, con: int, tar: int) -> int:
    """`@GAPING_SIZE_01`〜`_17`（:431–575）。"""
    h = lambda: get_height(ctx, con, tar)  # noqa: E731
    hip = lambda: get_hip(ctx, con, tar)  # noqa: E731
    if n == 1:
        return div(_gs(ctx, 2, con, tar) * 10, 20)
    if n == 2:
        return div(h() * 10, 1054)
    if n == 3:
        lo = _gs(ctx, 2, con, tar)
        return div((_gs(ctx, 4, con, tar) - lo) * 10, 25) + lo
    if n == 4:
        return div(h() * 100, 3952)
    if n == 5:
        lo = _gs(ctx, 4, con, tar)
        return div((_gs(ctx, 6, con, tar) - lo) * 15, 35) + lo
    if n == 6:
        return div(h() * 100, 2108)
    if n == 7:
        lo = _gs(ctx, 6, con, tar)
        return div((_gs(ctx, 8, con, tar) - lo) * 40, 85) + lo
    if n == 8:
        return div(h() * 10, 131) + 40
    if n == 9:
        lo = _gs(ctx, 8, con, tar)
        return div((_gs(ctx, 10, con, tar) - lo) * 40, 83) + lo
    if n == 10:
        return div(h() * 10, 160) + 20
    if n == 11:
        lo = _gs(ctx, 10, con, tar)
        return div((_gs(ctx, 12, con, tar) - lo) * 40, 81) + lo
    if n == 12:
        return div(h() * 10, 131) + 40
    if n == 13:
        lo = _gs(ctx, 12, con, tar)
        return div((_gs(ctx, 14, con, tar) - lo) * 45, 90) + lo
    if n == 14:
        return div(hip() * 100, 314)
    if n == 15:
        return div(hip() * 13849, 31415)
    if n == 16:
        return div(hip() * 13660, 31415)
    if n == 17:
        return div(hip() * 13740, 31415)
    raise ValueError(n)


def gaping_size(ctx: Ctx, arg: int, con: int = -1, tar: int = -1) -> int:
    """`@GAPING_SIZE(ARG, CON = -1, TAR = -1)`:342–427。"""
    st = ctx.state
    if tar == -1:
        tar = st.target
    if con == -1:
        con = st.charas[tar].cflag[1]
    d_rank = gaping_rank(arg)
    m0 = div(gaping_rank_to_point(d_rank) + gaping_rank_to_point(d_rank + 1), 2)
    if arg > m0:
        m1 = div(gaping_rank_to_point(d_rank + 1) + gaping_rank_to_point(d_rank + 2), 2)
    else:
        m1 = m0
        m0 = div(gaping_rank_to_point(d_rank) + gaping_rank_to_point(d_rank - 1), 2)
        d_rank -= 1
    d0 = d1 = 0  # #DIM D_SIZE：どの分岐にも当たらない（D_RANK == -1、17）場合は 0 のまま
    if d_rank == 0:
        d0, d1 = 0, _gs(ctx, 1, con, tar)
    elif 1 <= d_rank <= 16:
        d0, d1 = _gs(ctx, d_rank, con, tar), _gs(ctx, d_rank + 1, con, tar)
    if d_rank > 16:
        return div((arg - 125) * get_height(ctx, con, tar), 1581) + _gs(ctx, 11, con, tar)
    return div((d1 - d0) * (arg - m0), m1 - m0) + d0


def gaping_size_to_rank(ctx: Ctx, arg: int, con: int = 0, tar: int = 0) -> int:
    """`@GAPING_SIZE_TO_RANK(ARG, CON, TAR)`:646–689（引数省略時 CON = TAR = 0）。"""
    for n in range(1, 18):
        if arg < _gs(ctx, n, con, tar):
            return n - 1
    return 17


def gaping_size_to_point(ctx: Ctx, part: str) -> int:
    """`@GAPING_SIZE_TO_POINT(ARGS, TAR)`:700–745（TAR 省略 = 0 → TARGET のまま）。"""
    from ..chara_common import is_male

    st = ctx.state
    c = st.target_chara
    if part not in ("Ｖ", "Ａ"):
        return 0
    if is_male(ctx.data, c) and part == "Ｖ":
        return 0
    if part == "Ｖ":
        p_size = gaping_size(ctx, c.cflag[35], 0)
        p_rank = gaping_rank(c.cflag[35])
        e_size = _sz(st)[(1, 1)]
        local = (e_size > p_size) * 3 if (st.temp.insert & V_BIT) or c.cflag[0] == 1 else 0
    else:
        p_size = gaping_size(ctx, c.cflag[36], 0)
        p_rank = gaping_rank(c.cflag[36])
        e_size = _sz(st)[(1, 2)]
        local = (e_size > p_size) * 3 if (st.temp.insert & A_BIT) or c.cflag[0] == 1 else 0
    return local + max(0, min(gaping_size_to_rank(ctx, e_size) - p_rank, 99))


def _need_no_gaping(ctx: Ctx) -> None:
    if tc(ctx).cflag[34] != 0:
        raise NotImplementedError("拡張度（CFLAG:34 != 0 の V_GAPING／A_GAPING／PRINT_TENTACLE_SIZE）は未移植")


def get_v_gaping_exp(ctx: Ctx, arg: int) -> int:
    """`@GET_V_GAPING_EXP`:1004–1029（CFLAG:34 == 0 → RETURN 0）。ISMALE の早期 RETURN も 0。"""
    from ..chara_common import is_male

    if is_male(ctx.data, tc(ctx)):
        return 0
    _need_no_gaping(ctx)
    return 0


def get_a_gaping_exp(ctx: Ctx, arg: int) -> int:
    """`@GET_A_GAPING_EXP`:1035–1059。"""
    _need_no_gaping(ctx)
    return 0


def v_gaping(ctx: Ctx, arg: int) -> int:
    """`@V_GAPING`:851–925。"""
    from ..chara_common import is_male

    if is_male(ctx.data, tc(ctx)):
        return 0
    _need_no_gaping(ctx)
    return 0


def a_gaping(ctx: Ctx, arg: int) -> int:
    """`@A_GAPING`:932–998。"""
    _need_no_gaping(ctx)
    return 0


# --- ボス触手のサイズ補正（触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB@..._TENTACLE_SIZE）--------------


def boss_tentacle_size(ctx: Ctx, boss: int, arg: int) -> tuple[int, ...]:
    """RETURN LOCAL:0〜LOCAL:7（C・V・A・B の補正 % と本数）。RAND は ERB の記述順に引く。"""
    rand = ctx.state.rng.rand
    if boss == 1:  # TENTACLE_BOSS_1_Ｃ触手.ERB:202–220
        l0, l4 = 200, rand(3) + 1
        if arg == 3:
            l1, l5 = 100, 1
        else:
            l1, l5 = 60, rand(5) + 1
        l2, l6 = 60, rand(5) + 1
        l3, l7 = 80, rand(3) + 1
    elif boss == 2:  # TENTACLE_BOSS_2_Ｖ触手.ERB:213–232
        l0, l4 = 60, rand(25) + 25
        if arg in (1009, -101):
            l1, l5 = 150, 1
        else:
            l1, l5 = 90, rand(3) + 1
        l2, l6 = 60, rand(5) + 1
        l3, l7 = 100, 1
    elif boss == 3:  # TENTACLE_BOSS_3_Ａ触手.ERB:230–248
        l0, l4 = 85, rand(5) + 2
        l1, l5 = 60, rand(5) + 1
        if arg in (1010, -102):
            l2, l6 = 180, 1
        else:
            l2, l6 = 90, rand(3) + 1
        l3, l7 = 95, rand(3) + 2
    elif boss == 4:  # TENTACLE_BOSS_4_Ｂ触手.ERB:213–231
        l0, l4 = 70, rand(4) + 1
        if arg == 1011:
            l1, l5 = 120, 1
        else:
            l1, l5 = 80, rand(3) + 1
        l2, l6 = 70, rand(4) + 1
        l3, l7 = 180, 2
    elif boss == 5:  # TENTACLE_BOSS_5_Ｓ触手.ERB:210–223
        l0, l4 = 40, rand(50) + 20
        l1, l5 = 160, 1
        l2, l6 = 150, 1
        l3, l7 = 50, rand(40) + 25
    elif boss == 6:  # TENTACLE_BOSS_6_Ｐ触手.ERB:237–250
        l0, l4 = 190, 1
        l1, l5 = 30, rand(90) + 5
        l2, l6 = 150, 1
        l3, l7 = 30, rand(90) + 5
    elif boss == 7:  # TENTACLE_BOSS_7_Ｈ触手.ERB:219–233
        l0, l4 = 80, rand(5) + 1
        l1, l5 = 80, rand(5) + 1
        l2, l6 = 80, rand(5) + 1
        l3, l7 = 80, rand(5) + 1
    else:
        raise NotImplementedError(f"TENTACLE_BOSS_{boss}_TENTACLE_SIZE は未移植")
    return (l0, l1, l2, l3, l4, l5, l6, l7)


# --- SET_TENTACLE_SIZE（GAPING.ERB:1069–1170）--------------------------------------------


def set_tentacle_size(ctx: Ctx, arg0: int, arg1: int, arg2: int, arg3: int, arg4: int) -> None:
    """`@SET_TENTACLE_SIZE, ARG:0（FLAG:10）, ARG:1（FLAG:11）, ARG:2（悪堕ち）, ARG:3（FLAG:111）, ARG:4（コマンド）`。"""
    st = ctx.state
    rand = st.rng.rand
    sz, num = _sz(st), _num(st)
    if arg2 > 0:
        raise NotImplementedError("悪堕ちキャラの触手サイズ（SET_TENTACLE_SIZE ARG:2 > 0）は未移植")
    result = tentacle_level(st)  # :1074
    if config_check_maniac(st, 20) == 1:  # :1077–1078
        result *= 10
    if arg4 == 1006 and st.flag[700] == 1:  # :1082–1089 強制自慰
        for i in range(4):
            sz[(0, i)] = _gs(ctx, 2, tc(ctx).cflag[1], st.target)
            num[(0, i)] = 2 + rand(4)
        return
    if arg0 == 0:  # :1123–1128 ボス
        local = isqrt((result * 2 + 30) * 50)
        if config_check_maniac(st, 20) == 0:
            local = isqrt(local * 40)
        r = boss_tentacle_size(ctx, arg1, arg4)
    else:
        raise NotImplementedError("ラスボス／雑魚敵の触手サイズ（SET_TENTACLE_SIZE ARG:0 != 0）は未移植")
    sz[(0, 0)] = div(local * r[0], 520 + rand(161)) + 2  # :1159–1169
    num[(0, 0)] = r[4]
    sz[(0, 1)] = div(local * r[1], 90 + rand(21))
    num[(0, 1)] = r[5]
    sz[(0, 2)] = div(local * r[2], 90 + rand(21))
    num[(0, 2)] = r[6]
    sz[(0, 3)] = div(local * r[3], 255 + rand(91)) + 5
    num[(0, 3)] = r[7]


_PART_INDEX = {"Ｃ": 0, "Ｖ": 1, "Ａ": 2, "Ｂ": 3}


def set_tentacle_size_by_message(ctx: Ctx, part: str, size: str, count: str) -> None:
    """`@SET_TENTACLE_SIZE_BY_MESSAGE, ARGS:0, ARGS:1, ARGS:2`:1176–1255。"""
    st = ctx.state
    rand = st.rng.rand
    sz, num = _sz(st), _num(st)
    s = _PART_INDEX.get(part, 0)  # #DIM SELECT（該当なしは 0 のまま）
    cur = sz[(0, s)]
    if size == "繊毛":
        if cur >= 15:
            sz[(0, s)] = rand(10) + 5
    elif size == "細い":
        if cur < 15:
            sz[(0, s)] = rand(10) + 15
        elif cur >= 40:
            sz[(0, s)] = rand(15) + 25
    elif size == "普通":
        if cur < 40:
            sz[(0, s)] = rand(20) + 40
        elif cur >= 85:
            sz[(0, s)] = rand(25) + 60
    elif size == "太い":
        if cur < 85:
            sz[(0, s)] = rand(30) + 85
        elif cur >= 155:
            sz[(0, s)] = rand(40) + 115
    elif size == "極太":
        if cur < 155:
            sz[(0, s)] = rand(50) + 155
    cur = sz[(0, s)]
    if count == "たくさん":
        for b, n in ((5, 128), (15, 64), (25, 32), (40, 16), (60, 8), (85, 4), (115, 3), (155, 2)):
            if cur < b:
                num[(0, s)] = rand(n) + 2
                break
        else:
            num[(0, s)] = 2
    elif count == "複数":
        for b, n in ((5, 64), (15, 32), (25, 16), (40, 8), (60, 4), (85, 3), (115, 2)):
            if cur < b:
                num[(0, s)] = rand(n) + 2
                break
        else:
            num[(0, s)] = 2
    elif count == "単数":
        num[(0, s)] = 1


def set_tentacle_pool(ctx: Ctx) -> int:
    """`@SET_TENTACLE_POOL`:1259–1286。"""
    st = ctx.state
    c = tc(ctx)
    num = _num(st)
    pool = 0
    for i in range(4):
        if c.base[30 + i] > 0 and (st.tflag[10] != 1006 or c.cflag[0] == 1):
            num[(1, i)] = 0
            pool += 1
        else:
            num[(1, i)] = num[(0, i)]
    if pool > 0:
        for i in range(4):
            num[(1, i)] = div(num[(1, i)] * (100 + pool * 25), 100)
            if num[(0, i)] == num[(1, i)]:
                num[(1, i)] += 1
                num[(0, i)] += 1
    set_tentacle_size_r(ctx)
    return 1


def _size_r(st) -> None:
    sz, num = _sz(st), _num(st)
    for i in range(4):
        if num[(0, i)] > 2:
            sz[(1, i)] = div(sz[(0, i)] * (num[(0, i)] + 4), 3)
        else:
            sz[(1, i)] = sz[(0, i)] * num[(0, i)]


def set_tentacle_size_r(ctx: Ctx) -> None:
    """`@SET_TENTACLE_SIZE_R`:1341–1385。"""
    st = ctx.state
    sz, num = _sz(st), _num(st)
    for i in range(4):  # :1342–1360
        if num[(0, i)] > 2:
            sz[(1, i)] = div(sz[(0, i)] * (num[(0, i)] + 4), 3)
        else:
            sz[(1, i)] = sz[(0, i)] * num[(0, i)]
        if config_check_maniac(st, 20) == 1:
            l1 = gaping_size(ctx, 154 - st.rng.rand(19))
            l2 = gaping_size(ctx, 155)
            if sz[(1, i)] >= l2:
                if num[(0, i)] > 2:
                    sz[(0, i)] = div(l1, num[(0, i)] + 4) * 3
                else:
                    sz[(0, i)] = div(l1, num[(0, i)])
    tf = st.tflag
    if 15 <= tf[10] <= 20 and st.flag[700]:  # :1362–1369
        for i in range(4):
            if (i == 1 and (tf[109] & V_BIT) and (st.temp.insert & V_BIT)) or (
                i == 2 and (tf[109] & A_BIT) and (st.temp.insert & A_BIT)
            ):
                sz[(0, i)] = tf[i + 101]
                num[(0, i)] = tf[i + 105]
                num[(1, i)] = tf[i + 105]
    elif (tf[10] == 1009 and st.flag[700]) or (tf[10] == 101 and st.flag[700] == 0):
        sz[(0, 1)] = times(sz[(0, 1)], "1.3")
    elif (tf[10] == 1010 and st.flag[700]) or (tf[10] == 102 and st.flag[700] == 0):
        sz[(0, 2)] = times(sz[(0, 2)], "1.3")
    _size_r(st)  # :1378–1384


# --- PALAM_CALC_GAPING（PALAM_UP.ERB:771–816）-------------------------------------------


def palam_calc_gaping(ctx: Ctx) -> None:
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    sz = _sz(st)
    local1 = get_local_gaping(st)
    if st.tflag[1] == 0:
        if st.flag[700] > 0 and config_check_maniac(st, 16) == 1 and c.cflag[34] > 0:
            _need_no_gaping(ctx)  # PRINT_TENTACLE_SIZE
        local1 = 0
        ins = st.temp.insert
        if sz[(1, 1)] > 0 and (ins & V_BIT):
            get_v_gaping_exp(ctx, gaping_size_to_point(ctx, "Ｖ"))
        if sz[(1, 2)] > 0 and (ins & A_BIT):
            get_a_gaping_exp(ctx, gaping_size_to_point(ctx, "Ａ"))
        if sz[(1, 1)] > 0 and (ins & V_BIT):
            r = v_gaping(ctx, gaping_size_to_point(ctx, "Ｖ"))
            if r > 0 and config_check_maniac(st, 16) == 1:
                out.printl(f"　膣径：＋{div(r, 10)}.{r % 10} cm")
                local1 = 1
        if sz[(1, 2)] > 0 and (ins & A_BIT):
            r = a_gaping(ctx, gaping_size_to_point(ctx, "Ａ"))
            if r > 0 and config_check_maniac(st, 16) == 1:
                if local1 == 0:
                    out.printl()
                out.printl(f"　肛径：＋{div(r, 10)}.{r % 10} cm")
                local1 = 1
    st.temp.locals[("PALAM_CALC_GAPING", 1)] = local1
    if local1 == 1:  # :801–802（TFLAG:1 != 0 のときは静的 LOCAL:1 の前回値を見る）
        out.printl()
    if c.cflag[202] == 0 and st.tflag[20] == 1009:  # :805–809
        c.cflag[202] = 1
        c.exp[ctx.data.index_of("EXP", "異常経験")] += 1
        out.printl("異常経験＋1")
    if c.cflag[203] == 0 and st.tflag[20] == 1010:  # :812–816
        c.cflag[203] = 1
        c.exp[ctx.data.index_of("EXP", "異常経験")] += 1
        out.printl("異常経験＋1")


def get_local_gaping(st) -> int:
    return st.temp.locals.get(("PALAM_CALC_GAPING", 1), 0)

