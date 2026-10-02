"""幽閉コマンド：`ゲーム内_イベント発生/敗北幽閉中イベント/` の PRISON_COMABLE.ERB、COMMON_PRISON.ERB、PRISON_COM*_*.ERB（17 ファイル）
と `ゲーム内_戦闘処理/GAPING.ERB@PRISON_GAPING`:1298–1339。路徑相對 `source/earGVP/ERB/`。

各 PRISON_COMn は `VARSET LOCAL` で始まるので LOCAL は毎回 0 からの新しい配列でよい（静的 LOCAL の持ち越しなし）。
LOCAL:0〜11 = 取得する珠（快Ｃ〜恐怖）、LOCAL:100+n = EXP:n の上昇予定値（Exp.csv の番号：120 Ｖ経験 …）。
能力値ごとの `IF ABL == 0 … ELSEIF ABL >= 5` 表は `_lv`（負の値はどの分岐にも当たらず代入なし）。

地の文（`地の文/MESSAGE_PRISON.ERB`、`MESSAGE_OTHER.ERB` の PRISON 系）は S07 の catalog（`run_chinobun`）で出す。
catalog で実行できないとき（Null など）は佔位 1 行＋末尾の `TRYCALLFORM KOJO_ROOT(CFLAG:6, "PRISON_…")`。
"""

from __future__ import annotations

from ..body import set_profile
from ..action import Ctx, kojo_root
from ..battle.core import KANKAKU_NUM, abl, exp, run_chinobun, t, tc
from ..battle.sexcom import check_holyvirgin, incest, lostvirgin, palam_vabc_estimate
from ..chara_common import is_female, is_male
from ..era import div, isqrt, times

LOCAL_SIZE = 200
_UP_IDS = (0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17)  # COMMON_PRISON.ERB:25–36（快Ｃ〜快Ｂ、潤滑〜恐怖）


def _lv(v: int, table: tuple[int, ...]) -> int | None:
    """`IF X == 0 … ELSEIF X == 4 … ELSEIF X >= 5` 型の表（table は 0〜4 と 5 以上の 6 要素）。"""
    if v < 0:
        return None
    return table[min(v, 5)]


def _set(L: list[int], i: int, v: int | None) -> None:
    if v is not None:
        L[i] = v


# --- COMMON_PRISON.ERB ------------------------------------------------------------------------


def common_prison(ctx: Ctx, args: list[int], arg12: int = 0) -> None:
    """`@COMMON_PRISON, ARG:0〜ARG:12`:21–38：UP に入れ直して EVENT_PALAM_UP。"""
    from .event_palam import event_palam_up

    up = ctx.state.temp.up
    for pid, v in zip(_UP_IDS, args):
        up[pid] = v
    event_palam_up(ctx, arg12)


def common_prison_exp_sh(ctx: Ctx, a0: int, a1: int, a2: int, a3: int) -> tuple[int, int, int, int]:
    """`@COMMON_PRISON_EXP_SH, ARG:0〜3`:42–71（:44 `FOR COUNT, 0, 2` は ARG:0／ARG:1 のみ）。"""
    st = ctx.state
    a = [a0, a1, a2, a3]
    for i in range(2):
        a[i] = a[i] * 9 + st.rng.rand(a[i] + 1)
        if a[i] > 20:
            a[i] = 20 + div(a[i] - 20, 4)
    sh = st.shield
    if sh[1] > 0 and sh[2] <= 0:  # :50–56
        if a[1] > 0:
            a[1] += a[0]
            a[3] += a[2]
        a[0] = 0
        a[2] = 0
    elif sh[1] <= 0 and sh[2] > 0:  # :57–63
        if a[0] > 0:
            a[0] += a[1]
            a[2] += a[3]
        a[1] = 0
        a[3] = 0
    elif sh[1] > 0 and sh[2] > 0:  # :64–68
        a = [0, 0, 0, 0]
    st.set_result_x(*a)  # :71 RETURN ARG:0〜3（共用 RESULT）
    return a[0], a[1], a[2], a[3]


def common_prison_exp(ctx: Ctx, arg0: int, arg1: int) -> None:
    """`@COMMON_PRISON_EXP, ARG:0, ARG:1`:75–87。

    :87 GET_STATE_EXPUP（SHOP_TROPHY.ERB:506–）は実績（UNLOCK_ACHIEVEMENT → GLOBAL）のみ。
    DEVIATION: GLOBAL は読み書きしない（deviations.md「全域資料」）ので実行しない。
    """
    c = tc(ctx)
    local = arg0 - 100
    arg1 += ctx.state.temp.common_exp[local]
    if arg1 < 1:
        return
    name = ctx.data.names["EXP"].get(local, "")
    if name == "":
        return
    c.exp[local] += arg1
    ctx.out.printl(f"{name}：＋{arg1}")


def prison_gaping(ctx: Ctx, a0: int, a1: int, a2: int, a3: int, locs: tuple[int, int, int, int] = (0, 0, 0, 0)) -> tuple[int, int]:
    """`GAPING.ERB@PRISON_GAPING, ARG:0〜4, LOCAL:0〜3`:1298–1339（ARG:4 は未使用、LOCAL:0〜3 は触手サイズ表示の条件）。"""
    from ..action import config_check_maniac
    from ..battle.gaping import (
        a_gaping,
        gaping_size_to_point,
        get_a_gaping_exp,
        get_v_gaping_exp,
        print_tentacle_size,
        set_tentacle_size,
        set_tentacle_size_r,
        v_gaping,
    )

    st = ctx.state
    c = tc(ctx)
    st.temp.tentacle_size.clear()  # :1299 VARSET TENTACLE_SIZE
    if c.cflag[20] == 2:  # :1301–1306
        set_tentacle_size(ctx, 0, 0, c.cflag[20], st.flag[111], 0)
    else:
        set_tentacle_size(ctx, c.cflag[20], c.cflag[21], 0, 0, -st.tflag[10])
    set_tentacle_size_r(ctx)  # :1312
    if config_check_maniac(st, 16) == 1 and c.cflag[34] > 0:  # :1315–1316
        print_tentacle_size(ctx, *locs)
    if a0 > 0:  # :1320–1326
        a2 += get_v_gaping_exp(ctx, gaping_size_to_point(ctx, "Ｖ"), st.target, 1)
        r = v_gaping(ctx, gaping_size_to_point(ctx, "Ｖ"))
        if r > 0 and config_check_maniac(st, 16) == 1:
            ctx.out.printl(f"膣径：＋{div(r, 10)}.{r % 10} cm")
    if a1 > 0:  # :1328–1334
        a3 += get_a_gaping_exp(ctx, gaping_size_to_point(ctx, "Ａ"), st.target, 1)
        r = a_gaping(ctx, gaping_size_to_point(ctx, "Ａ"))
        if r > 0 and config_check_maniac(st, 16) == 1:
            ctx.out.printl(f"肛径：＋{div(r, 10)}.{r % 10} cm")
    st.set_result_x(a2, a3)  # :1336 RETURN ARG:2, ARG:3（共用 RESULT:0〜1）
    return a2, a3


# --- 共通の流れ ---------------------------------------------------------------------------------


def _msg(ctx: Ctx, name: str, kojo_code: str | None = None) -> None:
    """地の文（catalog）。実行できなければ佔位＋口上（各 MESSAGE_PRISON_* の末尾 `TRYCALLFORM KOJO_ROOT`）。"""
    run_chinobun(ctx, name, fallback=(lambda: kojo_root(ctx, kojo_code)) if kojo_code else None)


def _other(ctx: Ctx, name: str) -> None:
    """`SIF CFLAG:20 == 2 / CALL MESSAGE_OTHER_PRISON_*`（悪堕ちキャラによる幽閉のみ）。"""
    if tc(ctx).cflag[20] == 2:
        run_chinobun(ctx, name)


def _tail(ctx: Ctx, L: list[int]) -> None:
    """各 PRISON_COMn の「COMMON_PRISON → COMMON_PRISON_EXP_SH → PRISON_GAPING → COMMON_PRISON_EXP ×100 → PRINTL」
    （例：PRISON_COM0:180–199）。:191 `LOCAL:151 += RESULT:0` の RESULT:0 は ARG:2（= LOCAL:151）＋拡張経験なので
    LOCAL:151／152 は 2 倍＋拡張経験になる（原作どおり）。"""
    common_prison(ctx, L[0:12])
    L[120], L[121], L[151], L[152] = common_prison_exp_sh(ctx, L[120], L[121], L[151], L[152])
    r0, r1 = prison_gaping(ctx, L[120], L[121], L[151], L[152], (L[0], L[1], L[2], L[3]))
    L[151] += r0
    L[152] += r1
    for cc in range(100, 200):
        common_prison_exp(ctx, cc, L[cc])
    ctx.out.printl()


def _ablup1(ctx: Ctx) -> None:
    from ..battle.ablup import ablup

    ablup(ctx, 1)


def _ninsin(ctx: Ctx, a0: int, a1: int, a2: int = 0) -> None:
    """`SIF SHIELD:1 <= 0 / TRYCALL NINSIN_HANTEI, …`。"""
    from ..battle.ninsin import ninsin_hantei

    if ctx.state.shield[1] <= 0:
        ninsin_hantei(ctx, a0, a1, a2)


def _start(ctx: Ctx, tflag10: int, osen: tuple[int, int], incest_check: bool = True) -> list[int]:
    """`VARSET LOCAL / TFLAG:10 = n / CFLAG:30 += a + RAND:b / SIF INCEST_F(...) > 0 → LOCAL:141 += 1`。"""
    st = ctx.state
    c = tc(ctx)
    L = [0] * LOCAL_SIZE
    st.tflag[10] = tflag10
    c.cflag[30] += osen[0] + st.rng.rand(osen[1])
    if incest_check and incest(ctx, st.target, c.cflag[20] * 100 + c.cflag[21], 1) > 0:
        L[141] += 1
    return L


def _a(ctx: Ctx, name: str) -> int:
    return abl(ctx, tc(ctx), name)


def _virgin_break(ctx: Ctx, L: list[int], holy_check: bool, add: bool = False) -> None:
    """処女喪失：`TALENT:処女 == 1 && CHECK_HOLYVIRGIN_F()==0 && SHIELD:1 <= 0`（holy_check）または
    `TALENT:処女 > 0 && SHIELD:1 <= 0` → LOCAL:10 = 500（add なら += 500）、LOSTVIRGIN, 1。"""
    c = tc(ctx)
    v = t(ctx, c, "処女")
    if holy_check:
        cond = v == 1 and check_holyvirgin(ctx) == 0 and ctx.state.shield[1] <= 0
    else:
        cond = v > 0 and ctx.state.shield[1] <= 0
    if cond:
        L[10] = L[10] + 500 if add else 500
        lostvirgin(ctx, 1)


# 感覚 LV 表（0〜4、5 以上）
_C_LOW = (1, 2, 20, 100, 200, 400)
_V_EXP = (2, 5, 8, 11, 15, 20)  # LOCAL:120／121（Ｖ・Ａ経験）
_LOW = (1, 2, 20, 100, 200, 400)
_MID = (1, 5, 50, 250, 500, 1000)
_HIGH = (1, 10, 100, 500, 1000, 2000)
_HOUSHI_A = (5, 12, 25, 40, 62, 90)
_HOUSHI_B = (10, 25, 50, 80, 125, 180)


def _sense(ctx: Ctx, L: list[int], c_tbl, v_tbl, a_tbl, b_tbl, v_female_only: bool, a_needs_exp: bool = False) -> None:
    """快Ｃ／快Ｖ（＋LOCAL:120）／快Ａ（＋LOCAL:121）／快Ｂ の表。"""
    c = tc(ctx)
    _set(L, 0, _lv(_a(ctx, "Ｃ感覚"), c_tbl))
    if not v_female_only or is_female(ctx.data, c):
        vv = _a(ctx, "Ｖ感覚")
        _set(L, 120, _lv(vv, _V_EXP))
        _set(L, 1, _lv(vv, v_tbl))
    if not a_needs_exp or exp(ctx, c, "Ａ経験") > 0:
        aa = _a(ctx, "Ａ感覚")
        _set(L, 121, _lv(aa, _V_EXP))
        _set(L, 2, _lv(aa, a_tbl))
    _set(L, 3, _lv(_a(ctx, "Ｂ感覚"), b_tbl))


def _base_add(L: list[int], adds: tuple[int, int, int, int, int, int]) -> None:
    """習得〜恐怖の基本値（LOCAL:6〜11 += …）。"""
    for i, v in enumerate(adds):
        L[6 + i] += v


# --- PRISON_COM0〜7 ------------------------------------------------------------------------------


def prison_com0(ctx: Ctx) -> None:
    """`PRISON_COM0_Ｃ責め.ERB@PRISON_COM0`:6–205（C 中心攻め）。"""
    L = _start(ctx, 0, (5, 6))  # :8–50
    _sense(ctx, L, _HIGH, _LOW, _LOW, _MID, v_female_only=True)  # :53–124
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :127
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_A))  # :132–144
    _virgin_break(ctx, L, holy_check=True)  # :147–150
    _base_add(L, (20, 0, 100, 100, 100, 100))  # :153–168
    L[123] = 10  # :171
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_0")  # :174–175
    _msg(ctx, "MESSAGE_PRISON_COM_0", "PRISON_COM_0")  # :177
    _tail(ctx, L)  # :180–199
    _ablup1(ctx)  # :202
    _ninsin(ctx, 10, 30)  # :204–205


def prison_com1(ctx: Ctx) -> None:
    """`PRISON_COM1_Ｖ責め.ERB@PRISON_COM1`:6–237（V 中心攻め）。"""
    L = _start(ctx, 1, (5, 6))  # :8–49
    _sense(ctx, L, _LOW, _HIGH, (1, 5, 50, 250, 500, 1000), _LOW, v_female_only=False)  # :52–121
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :124
    _set(L, 5, _lv(_a(ctx, "従順"), (0, 0, 500, 1000, 2000, 5000)) if _a(ctx, "従順") >= 2 else None)  # :129–137
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :140–152
    _virgin_break(ctx, L, holy_check=False)  # :155–158
    vs = _a(ctx, "Ｖ感覚")
    _set(L, 8, _lv(vs, (500, 1000, 2000, 5000, 10000, 20000)))  # :161–173
    if vs in (0, 1, 2, 3):  # :176–185
        L[11] = (5000, 2000, 1000, 500)[vs]
    _base_add(L, (10, 100, 250, 250, 50, 250))  # :188–203
    L[123] = 25  # :206
    _msg(ctx, "MESSAGE_PRISON_COM_1", "PRISON_COM_1")  # :209
    _tail(ctx, L)
    _ablup1(ctx)  # :234
    _ninsin(ctx, 25, 60)  # :236–237


def prison_com2(ctx: Ctx) -> None:
    """`PRISON_COM2_Ａ責め.ERB@PRISON_COM2`:6–244（A 中心攻め）。"""
    L = _start(ctx, 2, (5, 6))  # :8–48
    _sense(ctx, L, _LOW, (1, 5, 50, 250, 500, 1000), (10, 50, 200, 500, 1000, 2000), _LOW, v_female_only=True)  # :51–122
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :125
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :130–142
    av = _a(ctx, "Ａ感覚")
    _set(L, 8, _lv(av, (100, 200, 500, 1000, 2000, 5000)))  # :145–157
    L[10] = (500, 400, 300, 200)[av] if av in (0, 1, 2, 3) else 100  # :160–170（ELSE は 4 以上と負）
    L[11] = (500, 400, 300, 200)[av] if av in (0, 1, 2, 3) else 100  # :173–183
    _virgin_break(ctx, L, holy_check=True, add=True)  # :186–189
    _base_add(L, (10, 0, 350, 50, 100, 250))  # :192–207
    L[123] = 25  # :210
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_2")  # :213–214
    _msg(ctx, "MESSAGE_PRISON_COM_2", "PRISON_COM_2")  # :216
    _tail(ctx, L)
    _ablup1(ctx)  # :241
    _ninsin(ctx, 25, 30)  # :243–244


def prison_com3(ctx: Ctx) -> None:
    """`PRISON_COM3_Ｂ責め.ERB@PRISON_COM3`:6–216（B 中心攻め）。"""
    L = _start(ctx, 3, (5, 6))  # :8–48
    _sense(ctx, L, _MID, _LOW, _LOW, _HIGH, v_female_only=True)  # :51–122
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :125
    _set(L, 5, _lv(_a(ctx, "従順"), (0, 0, 400, 600, 800, 1000)) if _a(ctx, "従順") >= 2 else None)  # :130–138
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :141–153
    _virgin_break(ctx, L, holy_check=True)  # :156–159
    _base_add(L, (10, 100, 100, 200, 0, 0))  # :162–177
    L[123] = 10  # :180
    L[124] = 5  # :182
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_3")  # :185–186
    _msg(ctx, "MESSAGE_PRISON_COM_3", "PRISON_COM_3")  # :188
    _tail(ctx, L)
    _ablup1(ctx)  # :213
    _ninsin(ctx, 10, 30)  # :215–216


def prison_com4(ctx: Ctx) -> None:
    """`PRISON_COM4_サド.ERB@PRISON_COM4`:6–236（S な攻め）。"""
    c = tc(ctx)
    L = _start(ctx, 4, (5, 6))  # :8–48
    _sense(ctx, L, _LOW, (1, 5, 50, 250, 500, 1000), (1, 5, 50, 250, 500, 1000), _LOW, v_female_only=True)  # :51–122
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :125
    maso = _a(ctx, "マゾっ気")
    _set(L, 8, _lv(maso, (200, 500, 1000, 2000, 3500, 5000)))  # :131–143
    if _a(ctx, "従順") < 3:  # :146–158
        L[11] = 1500 if maso < 3 else 500
    else:
        L[11] = 500 if maso < 3 else 100
    _set(L, 132, _lv(maso, (3, 4, 6, 10, 18, 34)))  # :161–173
    _virgin_break(ctx, L, holy_check=True)  # :176–179
    if is_male(ctx.data, c):  # :181–184
        L[1] = 0
        L[120] = 0
    _base_add(L, (0, 0, 800, 100, 800, 800))  # :187–202
    L[123] = 10  # :205
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_4")  # :208–209
    _msg(ctx, "MESSAGE_PRISON_COM_4", "PRISON_COM_4")  # :211
    _tail(ctx, L)
    _ablup1(ctx)  # :236


def prison_com5(ctx: Ctx) -> None:
    """`PRISON_COM5_強制奉仕_催眠.ERB@PRISON_COM5`:6–265（強制奉仕）。"""
    L = _start(ctx, 5, (10, 6))  # :8–48
    _sense(ctx, L, _LOW, _LOW, _LOW, _LOW, v_female_only=True, a_needs_exp=True)  # :51–125
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :128
    jj = _a(ctx, "従順")
    hs = _a(ctx, "奉仕精神")
    _set(L, 5, _lv(jj, (0, 0, 200, 500, 1000, 2000)) if jj >= 2 else None)  # :133–141
    _set(L, 6, _lv(hs, _HOUSHI_B))  # :144–156
    _set(L, 8, _lv(jj, (500, 1000, 1500, 2500, 3500, 5000)))  # :159–171
    if hs < 3:  # :174–184
        pass
    elif hs < 4:
        L[5] += 500
        L[6] += 100
    elif hs < 5:
        L[5] += 1000
        L[6] += 500
    else:
        L[5] += 2000
        L[6] += 1000
    if jj < 3:  # :187–188
        L[11] = 500
    _virgin_break(ctx, L, holy_check=True)  # :191–194
    _base_add(L, (20, 0, 100, 100, 100, 100))  # :197–212
    L[123] = 25  # :215
    L[124] = 10  # :217
    _set(L, 131, _lv(hs, (1, 2, 4, 8, 16, 32)))  # :219–231
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_5")  # :234–235
    _msg(ctx, "MESSAGE_PRISON_COM_5", "PRISON_COM_5")  # :237
    _tail(ctx, L)
    _ablup1(ctx)  # :262
    _ninsin(ctx, 25, 30)  # :264–265


def prison_com6(ctx: Ctx) -> None:
    """`PRISON_COM6_羞恥責め.ERB@PRISON_COM6`:6–250（羞恥な攻め）。"""
    L = _start(ctx, 6, (5, 6))  # :8–48
    _sense(ctx, L, _LOW, _LOW, _LOW, _LOW, v_female_only=True)  # :51–122
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :125
    ro = _a(ctx, "露出癖")
    _set(L, 8, _lv(ro, (1000, 1200, 1500, 2000, 2500, 3500)))  # :131–143
    _set(L, 9, _lv(ro, (1000, 1200, 1500, 2000, 2500, 3500)))  # :146–158
    _set(L, 11, _lv(ro, (800, 600, 300, 150, 50, 0)))  # :161–173
    _set(L, 7, _lv(ro, (0, 0, 100, 200, 400, 800)) if ro >= 2 else None)  # :176–184
    _base_add(L, (0, 200, 100, 400, 0, 200))  # :187–202
    L[123] = 10  # :205
    _set(L, 130, _lv(ro, (1, 2, 4, 8, 16, 32)))  # :207–219
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_6")  # :222–223
    _msg(ctx, "MESSAGE_PRISON_COM_6", "PRISON_COM_6")  # :225
    _tail(ctx, L)
    _ablup1(ctx)  # :250


def prison_com7(ctx: Ctx) -> None:
    """`PRISON_COM7_子触手.ERB@PRISON_COM7`:6–233（子触手に犯される）。INCEST_F の判定は無い。"""
    st = ctx.state
    c = tc(ctx)
    L = _start(ctx, 7, (10, 11), incest_check=False)  # :8–45
    _sense(ctx, L, _LOW, (1, 5, 50, 250, 500, 1000), (1, 5, 50, 250, 500, 1000), _LOW, v_female_only=False)  # :48–120
    ch = c.cflag[220]
    L[120] *= div(ch + 100, 100)  # :83
    L[1] *= isqrt(ch) + 1  # :84
    L[3] *= isqrt(ch) + 1  # :122
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :125
    jj = _a(ctx, "従順")
    _set(L, 5, _lv(jj, (0, 0, 500, 1000, 2000, 5000)) if jj >= 2 else None)  # :130–138
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :141–153
    _virgin_break(ctx, L, holy_check=False)  # :156–159
    L[8] = 800  # :162
    vs = _a(ctx, "Ｖ感覚")
    if vs in (0, 1, 2, 3):  # :165–174
        L[11] = (800, 400, 200, 100)[vs]
    _base_add(L, (10, 0, 500, 500, 0, 500))  # :177–192
    L[123] = 15 * ch  # :195
    L[124] = 2 * ch  # :197
    L[141] = ch  # :199
    if exp(ctx, c, "近親交配経験") == 0:  # :201–202
        L[150] = 1
    _msg(ctx, "MESSAGE_PRISON_COM_7", "PRISON_COM_7")  # :205
    _tail(ctx, L)
    _ablup1(ctx)  # :230
    # :232–233 `TRYCALL NINSIN_HANTEI,(15 * CFLAG:220),(MIN(EXP:TARGET:近親交配経験 * 5 + 20,120)),200`
    _ninsin(ctx, 15 * c.cflag[220], min(exp(ctx, st.target_chara, "近親交配経験") * 5 + 20, 120), 200)


# --- PRISON_COM100〜105 -------------------------------------------------------------------------


def prison_com100(ctx: Ctx) -> None:
    """`PRISON_COM100_ふたなり.ERB@PRISON_COM100`:6–146（ふたなり攻め）。"""
    data = ctx.data
    c = tc(ctx)
    L = _start(ctx, 100, (10, 5), incest_check=False)  # :8–44
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    if t(ctx, c, "ふたなり") < 1 and is_female(data, c):  # :46–61
        c.talent[ti("ふたなり")] = 1
        # :49 `SIF TALENT:変身時ふたなり < 1 && TALENT:変身能力 > 0; && ABL:射精中毒 >= 3`（`;` 以降は行中コメント：
        # reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:954–965）
        if t(ctx, c, "変身時ふたなり") < 1 and t(ctx, c, "変身能力") > 0:
            c.talent[ti("変身時ふたなり")] = 1
        L[11] = 800
        _other(ctx, "MESSAGE_OTHER_PRISON_HUTANARI")
        _msg(ctx, "MESSAGE_PRISON_HUTANARI", "PRISON_HUTANARI")
    else:  # :62–103
        _set(L, 0, _lv(_a(ctx, "Ｃ感覚"), (100, 150, 200, 600, 1000, 1500)))
        palam_vabc_estimate(ctx, L, 0, -1)  # :79
        _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :83–95
        _other(ctx, "MESSAGE_OTHER_PRISON_COM_100")
        _msg(ctx, "MESSAGE_PRISON_COM_100", "PRISON_COM_100")
    _base_add(L, (20, 100, 200, 200, 0, 50))  # :106–121
    _tail(ctx, L)
    _ablup1(ctx)  # :146


def _kakuchou_scale(value: int, e: int, factors: tuple[str, str, str]) -> int:
    """`IF EXP < 3 TIMES 0.10 / < 5 0.50 / < 8 0.80 / ELSE（何もしない）`。"""
    if e < 3:
        return times(value, factors[0])
    if e < 5:
        return times(value, factors[1])
    if e < 8:
        return times(value, factors[2])
    return value


def _by_exp(e: int, table: tuple[int, int, int, int]) -> int:
    """`IF EXP < 3 … ELSEIF < 5 … ELSEIF < 8 … ELSE …`。"""
    return table[0] if e < 3 else table[1] if e < 5 else table[2] if e < 8 else table[3]


def prison_com101(ctx: Ctx) -> None:
    """`PRISON_COM101_Ｖ拡張.ERB@PRISON_COM101`:6–208（V 拡張）。"""
    c = tc(ctx)
    L = _start(ctx, 101, (10, 5))  # :8–48
    vs = _a(ctx, "Ｖ感覚")
    _set(L, 120, _lv(vs, (5, 8, 11, 15, 20, 30)))  # :51–69
    _set(L, 1, _lv(vs, (100, 150, 200, 600, 1000, 1500)))
    e = exp(ctx, c, "Ｖ拡張経験")
    L[1] = _kakuchou_scale(L[1], e, ("0.10", "0.50", "0.80"))  # :71–78
    palam_vabc_estimate(ctx, L, 1, -1)  # :80
    L[8] = _by_exp(e, (500, 1000, 2000, 5000))  # :86–94
    L[9] = _by_exp(e, (500, 1000, 2000, 5000))  # :98–106
    L[10] = _by_exp(e, (1000, 800, 400, 100))  # :110–118
    L[11] = _by_exp(e, (1000, 800, 400, 100))  # :122–130
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_A))  # :133–145
    _virgin_break(ctx, L, holy_check=False, add=True)  # :148–151
    _msg(ctx, "MESSAGE_PRISON_COM_101", "PRISON_COM_101")  # :154
    _base_add(L, (20, 0, 500, 0, 100, 100))  # :157–172
    if c.cflag[202] == 0:  # :177–180
        c.cflag[202] = 1
        L[150] = 1
    _tail(ctx, L)
    _ablup1(ctx)  # :205
    _ninsin(ctx, 10, 30)  # :207–208


def prison_com102(ctx: Ctx) -> None:
    """`PRISON_COM102_Ａ拡張.ERB@PRISON_COM102`:6–209（A 拡張）。:105–106 は恥情の表なのに LOCAL:8 に代入（原作どおり）。"""
    c = tc(ctx)
    L = _start(ctx, 102, (10, 5))  # :8–48
    av = _a(ctx, "Ａ感覚")
    _set(L, 121, _lv(av, (5, 8, 11, 15, 20, 30)))  # :51–75
    _set(L, 152, _lv(av, (1, 1, 2, 2, 4, 8)))
    _set(L, 2, _lv(av, (100, 150, 200, 600, 1000, 1500)))
    e = exp(ctx, c, "Ａ拡張経験")
    L[2] = _kakuchou_scale(L[2], e, ("0.10", "0.50", "0.80"))  # :77–84
    palam_vabc_estimate(ctx, L, 2, -1)  # :87
    L[8] = _by_exp(e, (500, 1000, 2000, 5000))  # :93–101
    if e < 3:  # :105–113
        L[8] = 500
    elif e < 5:
        L[9] = 1000
    elif e < 8:
        L[9] = 2000
    else:
        L[9] = 5000
    L[10] = _by_exp(e, (1000, 800, 400, 100))  # :117–125
    L[11] = _by_exp(e, (1000, 800, 400, 100))  # :129–137
    _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_A))  # :140–152
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_102")  # :155–156
    _msg(ctx, "MESSAGE_PRISON_COM_102", "PRISON_COM_102")  # :158
    _base_add(L, (20, 0, 500, 0, 100, 100))  # :161–176
    if c.cflag[203] == 0:  # :181–184
        c.cflag[203] = 1
        L[150] = 1
    _tail(ctx, L)
    _ablup1(ctx)  # :209


def prison_com103(ctx: Ctx) -> None:
    """`PRISON_COM103_搾乳.ERB@PRISON_COM103`:6–144（搾乳）。"""
    c = tc(ctx)
    L = _start(ctx, 103, (10, 5), incest_check=False)  # :8–44
    if t(ctx, c, "母乳体質") == 0:  # :46–59
        c.talent[ctx.data.index_of("TALENT", "母乳体質")] = 1
        L[11] = 800
        _other(ctx, "MESSAGE_OTHER_PRISON_BONYU")
        _msg(ctx, "MESSAGE_PRISON_BONYU", "PRISON_BONYU")
    else:  # :60–101
        _set(L, 3, _lv(_a(ctx, "Ｂ感覚"), (100, 150, 200, 600, 1000, 1500)))
        palam_vabc_estimate(ctx, L, 3, -1)  # :77
        _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_A))  # :82–94
        _other(ctx, "MESSAGE_OTHER_PRISON_COM_103")
        _msg(ctx, "MESSAGE_PRISON_COM_103", "PRISON_COM_103")
    _base_add(L, (20, 200, 100, 100, 0, 0))  # :104–119
    _tail(ctx, L)
    _ablup1(ctx)  # :144


def prison_com104(ctx: Ctx) -> None:
    """`PRISON_COM104_苗床化.ERB@PRISON_COM104`:6–244（苗床化）。"""
    c = tc(ctx)
    L = _start(ctx, 104, (10, 11))  # :8–48
    vs = _a(ctx, "Ｖ感覚")
    if t(ctx, c, "苗床化") == 0:  # :50–99
        c.talent[ctx.data.index_of("TALENT", "苗床化")] = 1
        L[11] = 800
        L[150] = 1
        if t(ctx, c, "触手の虜"):
            L[124] = 4
        _set(L, 120, _lv(vs, _V_EXP))  # :65–83
        _set(L, 1, _lv(vs, (10, 50, 100, 250, 500, 1000)))
        palam_vabc_estimate(ctx, L, 1, -1)  # :86
        _virgin_break(ctx, L, holy_check=False)  # :90–93
        _other(ctx, "MESSAGE_OTHER_PRISON_NAEDOKO")
        _msg(ctx, "MESSAGE_PRISON_NAEDOKO", "PRISON_NAEDOKO")
    else:  # :100–198
        _set(L, 120, _lv(vs, (6, 15, 24, 33, 45, 60)))  # :102–120
        _set(L, 1, _lv(vs, (200, 300, 400, 600, 1200, 2000)))
        _set(L, 3, _lv(_a(ctx, "Ｂ感覚"), (1, 5, 20, 100, 200, 400)))  # :123–135
        palam_vabc_estimate(ctx, L, 1, 3, -1)  # :138
        jj = _a(ctx, "従順")
        _set(L, 5, _lv(jj, (0, 0, 1000, 1200, 1500, 2000)) if jj >= 2 else None)  # :143–151
        _virgin_break(ctx, L, holy_check=False)  # :154–157
        L[8] = 800  # :160
        if vs in (0, 1, 2, 3):  # :163–172
            L[11] = (800, 400, 200, 100)[vs]
        _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_A))  # :175–187
        L[123] = 120  # :190
        _other(ctx, "MESSAGE_OTHER_PRISON_COM_104")
        _msg(ctx, "MESSAGE_PRISON_COM_104", "PRISON_COM_104")
    _base_add(L, (20, 0, 250, 0, 250, 250))  # :201–216
    _tail(ctx, L)
    _ablup1(ctx)  # :241
    _ninsin(ctx, 120, 60)  # :243–244


def prison_com105(ctx: Ctx) -> None:
    """`PRISON_COM105_膨乳化.ERB@PRISON_COM105`:6–167（膨乳化）。"""
    from ..action import config_check_maniac

    st, data = ctx.state, ctx.data
    c = tc(ctx)
    L = _start(ctx, 105, (10, 5), incest_check=False)  # :8–44
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    limit_ = 2 + (3 if config_check_maniac(st, 19) == 1 else 0)
    if tl("巨乳") + max(0, tl("変身時胸サイズ変動")) < limit_:  # :47–81
        if tl("変身時胸サイズ変動") < 0:
            c.talent[ti("変身時胸サイズ変動")] += 1
            c.cflag[38] += 1
        else:
            if tl("巨乳") - tl("貧乳") < 0:
                c.talent[ti("貧乳")] -= 1
            else:
                c.talent[ti("巨乳")] += 1
            if (tl("巨乳") + tl("変身時胸サイズ変動") > 5) or (
                config_check_maniac(st, 19) == 0 and tl("巨乳") + tl("変身時胸サイズ変動") >= 2
            ):
                c.talent[ti("変身時胸サイズ変動")] -= 1
                c.cflag[38] -= 1
            c.cflag[37] += 1
        set_profile(data, c, st.result)  # :70 CALL SET_PROFILE, TARGET（FIRSTSETTING_CHARA_TALENT.ERB:4–19）
        L[11] = 800  # :73 恐怖　固定で
        _other(ctx, "MESSAGE_OTHER_PRISON_BOUNYU")  # :76–77
        _msg(ctx, "MESSAGE_PRISON_BOUNYU", "PRISON_BOUNYU")  # :79（地の文/MESSAGE_PRISON.ERB:594–、口上 :651）
    else:  # :82–124
        _set(L, 3, _lv(_a(ctx, "Ｂ感覚"), (100, 150, 200, 600, 1000, 1500)))
        palam_vabc_estimate(ctx, L, 3, -1)  # :99
        _set(L, 6, _lv(_a(ctx, "奉仕精神"), _HOUSHI_B))  # :104–116
        _other(ctx, "MESSAGE_OTHER_PRISON_COM_105")
        _msg(ctx, "MESSAGE_PRISON_COM_105", "PRISON_COM_105")
    _base_add(L, (20, 100, 200, 200, 0, 50))  # :127–142
    _tail(ctx, L)
    _ablup1(ctx)  # :167


# --- PRISON_COM200／201（産み付け）・300（毒液注射）・301（寄生）-----------------------------------


def prison_com200(ctx: Ctx) -> None:
    """`PRISON_COM200_Ｖ産み付け.ERB@PRISON_COM200`:6–203（V に産卵）。"""
    c = tc(ctx)
    L = _start(ctx, 200, (10, 10))  # :8–48
    vs = _a(ctx, "Ｖ感覚")
    _set(L, 120, _lv(vs, (5, 8, 11, 15, 20, 30)))  # :51–75
    _set(L, 151, _lv(vs, (1, 1, 2, 2, 4, 8)))
    _set(L, 1, _lv(vs, (300, 450, 600, 800, 1200, 2000)))
    e = exp(ctx, c, "出産経験")
    L[1] = _kakuchou_scale(L[1], e, ("0.30", "0.50", "0.80"))  # :77–84
    palam_vabc_estimate(ctx, L, 1, -1)  # :87
    _umitsuke_rest(L, e)  # :93–148
    _msg(ctx, "MESSAGE_PRISON_COM_200", "PRISON_COM_200")  # :151
    _base_add(L, (0, 0, 500, 0, 500, 500))  # :154–169
    if c.cflag[204] == 0:  # :172–175
        c.cflag[204] = 1
        L[150] = 1
    _tail(ctx, L)
    _ablup1(ctx)  # :200
    _ninsin(ctx, 50, 4000000)  # :202–203


def _umitsuke_rest(L: list[int], e: int) -> None:
    """PRISON_COM200／201 :93–148（恭順・屈服・恥情・苦痛・恐怖。恭順は出産経験 3 未満なら代入なし）。"""
    if e >= 3:
        L[5] = _by_exp(e, (0, 200, 1000, 5000))
    L[8] = _by_exp(e, (500, 1000, 2000, 5000))
    L[9] = _by_exp(e, (800, 400, 200, 50))
    L[10] = _by_exp(e, (1500, 1000, 500, 200))
    L[11] = _by_exp(e, (1500, 1000, 500, 200))


def prison_com201(ctx: Ctx) -> None:
    """`PRISON_COM201_Ａ産み付け.ERB@PRISON_COM201`:6–200（A に産卵）。"""
    c = tc(ctx)
    L = _start(ctx, 201, (10, 10))  # :8–48
    av = _a(ctx, "Ａ感覚")
    _set(L, 121, _lv(av, (5, 8, 11, 15, 20, 30)))  # :51–75
    _set(L, 152, _lv(av, (1, 1, 2, 2, 4, 8)))
    _set(L, 2, _lv(av, (300, 450, 600, 800, 1200, 2000)))
    e = exp(ctx, c, "出産経験")
    L[2] = _kakuchou_scale(L[2], e, ("0.30", "0.50", "0.80"))  # :77–84
    palam_vabc_estimate(ctx, L, 2, -1)  # :87
    _umitsuke_rest(L, e)  # :93–148
    _msg(ctx, "MESSAGE_PRISON_COM_201", "PRISON_COM_201")  # :151
    _base_add(L, (0, 0, 500, 0, 500, 500))  # :154–169
    if c.cflag[205] == 0:  # :172–175
        c.cflag[205] = 1
        L[150] = 1
    _tail(ctx, L)
    _ablup1(ctx)  # :200


def prison_com300(ctx: Ctx) -> None:
    """`PRISON_COM300_毒液注射.ERB@PRISON_COM300`:6–210（注射：淫乱系素質）。"""
    from ..battle.ablup import message_gettalent

    c = tc(ctx)
    L = _start(ctx, 300, (20, 10))  # :8–48
    cs = _a(ctx, "Ｃ感覚")
    L[0] = (500, 700, 900, 1100, 1300)[cs] if cs in (0, 1, 2, 3, 4) else 1500  # :51–63（ELSE は 5 以上と負）
    tbl = (500, 700, 900, 1100, 1300, 1500)
    if is_female(ctx.data, c):  # :66–86
        vs = _a(ctx, "Ｖ感覚")
        _set(L, 120, _lv(vs, _V_EXP))
        _set(L, 1, _lv(vs, tbl))
    if exp(ctx, c, "Ａ経験") > 0:  # :90–110
        av = _a(ctx, "Ａ感覚")
        _set(L, 121, _lv(av, _V_EXP))
        _set(L, 2, _lv(av, tbl))
    _set(L, 3, _lv(_a(ctx, "Ｂ感覚"), tbl))  # :113–125
    palam_vabc_estimate(ctx, L, 0, 1, 2, 3, -1)  # :128
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_300")  # :133–134
    _msg(ctx, "MESSAGE_PRISON_COM_300", "PRISON_COM_300")  # :136
    _base_add(L, (0, 1000, 500, 0, 500, 500))  # :139–154
    _tail(ctx, L)
    ti = lambda n: ctx.data.index_of("TALENT", n)  # noqa: E731
    if t(ctx, c, "淫核") == 0 and _a(ctx, "Ｃ感覚") >= 5:  # :181–185
        c.talent[ti("淫核")] = 1
        message_gettalent(ctx, "INKAKU")
    if t(ctx, c, "淫壷") == 0 and _a(ctx, "Ｖ感覚") >= 5 and exp(ctx, c, "Ｖ経験") >= 200:  # :188–192
        c.talent[ti("淫壷")] = 1
        message_gettalent(ctx, "INTUBO")
    if t(ctx, c, "淫尻") == 0 and _a(ctx, "Ａ感覚") >= 5 and exp(ctx, c, "Ａ経験") >= 200:  # :195–199
        c.talent[ti("淫尻")] = 1
        message_gettalent(ctx, "INJIRI")
    if t(ctx, c, "淫乳") == 0 and _a(ctx, "Ｂ感覚") >= 5:  # :202–206
        c.talent[ti("淫乳")] = 1
        message_gettalent(ctx, "INNYUU")
    _ablup1(ctx)  # :210


def prison_com301(ctx: Ctx) -> None:
    """`PRISON_COM301_寄生.ERB@PRISON_COM301`:6–109（寄生）。"""
    c = tc(ctx)
    L = _start(ctx, 301, (40, 15), incest_check=False)  # :8–44
    c.talent[ctx.data.index_of("TALENT", "寄生")] = 1  # :47
    L[156] = 1  # :50
    L[8] = 800  # :53
    if t(ctx, c, "触手の虜") == 0:  # :56–60
        L[11] = 1000
    else:
        L[5] = 1000
    _other(ctx, "MESSAGE_OTHER_PRISON_COM_301")  # :63–64
    _msg(ctx, "MESSAGE_PRISON_COM_301", "PRISON_COM_301")  # :66
    _base_add(L, (0, 0, 500, 0, 500, 500))  # :69–84
    _tail(ctx, L)
    _ablup1(ctx)  # :109


# --- PRISON_COMABLE.ERB ----------------------------------------------------------------------------


def prison_comable(ctx: Ctx, arg: int) -> None:
    """`@PRISON_COMABLE, ARG`:93–348。

    `GOTO SHIELDED` は IF ARG == -1 ブロック内の `$SHIELDED`（:99）へ飛び、ENDIF（何もしない命令：
    reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1822–1831）を経て SELECTCASE をやり直す。
    $ラベルを IF 内に置くことは許される（`GameProc/ErbLoader.cs`:900–921 は PRINTDATA 等のみ禁止）。
    """
    st, data = ctx.state, ctx.data
    c = tc(ctx)
    sh = st.shield
    male = lambda: is_male(data, c)  # noqa: E731
    otoko_no_ko = lambda: t(ctx, c, "男の娘") > 0  # noqa: E731
    shielded = arg == -1
    while True:
        if shielded:  # :99–116
            cand = [i for i in range(KANKAKU_NUM) if c.base[i + 30] < 1]
            arg = cand[st.rng.rand(len(cand))] if cand else st.rng.rand(KANKAKU_NUM)
            shielded = False
        if arg == 0:  # :131–132
            prison_com0(ctx)
        elif arg == 1:  # :134–146
            if otoko_no_ko():
                prison_com2(ctx)
            elif male():
                prison_com0(ctx)
            else:
                prison_com1(ctx)
        elif arg == 2:
            prison_com2(ctx)
        elif arg == 3:
            prison_com3(ctx)
        elif arg == 4:
            prison_com4(ctx)
        elif arg == 5:
            prison_com5(ctx)
        elif arg == 6:  # :160–166
            if t(ctx, c, "感情乏しい") > 0:
                prison_com4(ctx)
            else:
                prison_com6(ctx)
        elif arg == 7:  # :168–183
            if sh[1] > 0:
                shielded = True
                continue
            if otoko_no_ko():
                prison_com2(ctx)
            elif male():
                prison_com0(ctx)
            elif check_holyvirgin(ctx) == 1:
                prison_com5(ctx)
            else:
                prison_com7(ctx)
        elif arg == 100:  # :185–194
            if sh[0] > 0:
                shielded = True
                continue
            from ..action import config_check_maniac

            if male() or config_check_maniac(st, 1) == 0:
                prison_com0(ctx)
            else:
                prison_com100(ctx)
        elif arg == 101:  # :196–220
            if sh[1] > 0:
                shielded = True
                continue
            if otoko_no_ko() and exp(ctx, c, "Ａ経験") < 20:
                prison_com2(ctx)
            elif otoko_no_ko():
                if sh[2] > 0:
                    shielded = True
                    continue
                prison_com102(ctx)
            elif male():
                prison_com0(ctx)
            elif check_holyvirgin(ctx) == 1:
                prison_com5(ctx)
            elif exp(ctx, c, "Ｖ経験") < 20:
                prison_com1(ctx)
            else:
                prison_com101(ctx)
        elif arg == 102:  # :223–232
            if sh[2] > 0:
                shielded = True
                continue
            if exp(ctx, c, "Ａ経験") < 20:
                prison_com2(ctx)
            else:
                prison_com102(ctx)
        elif arg == 103:  # :235–244
            if sh[3] > 0:
                shielded = True
                continue
            from ..action import config_check_maniac

            if male() or config_check_maniac(st, 2) == 0:
                prison_com3(ctx)
            else:
                prison_com103(ctx)
        elif arg == 104:  # :246–271
            if sh[1] > 0:
                shielded = True
                continue
            if otoko_no_ko():
                prison_com5(ctx)
            elif male():
                prison_com0(ctx)
            elif check_holyvirgin(ctx) == 1:
                prison_com5(ctx)
            elif abl(ctx, c, "Ｖ感覚") < 5 and exp(ctx, c, "Ｖ拡張経験") < 10:
                if exp(ctx, c, "Ｖ経験") < 20:
                    prison_com1(ctx)
                else:
                    prison_com101(ctx)
            else:
                prison_com104(ctx)
        elif arg == 105:  # :273–282
            if sh[3] > 0:
                shielded = True
                continue
            from ..action import config_check_maniac

            if male() or config_check_maniac(st, 18) == 0:
                prison_com3(ctx)
            else:
                prison_com105(ctx)
        elif arg == 200:  # :284–318
            if sh[1] > 0:
                shielded = True
                continue
            if otoko_no_ko():
                if sh[2] > 0:
                    shielded = True
                    continue
                prison_com201(ctx) if exp(ctx, c, "Ａ拡張経験") > 3 else prison_com102(ctx)
            elif male():
                prison_com0(ctx)
            elif check_holyvirgin(ctx) == 1:
                if sh[2] > 0:
                    shielded = True
                    continue
                prison_com201(ctx) if exp(ctx, c, "Ａ拡張経験") > 3 else prison_com102(ctx)
            elif exp(ctx, c, "Ｖ拡張経験") > 3:
                prison_com200(ctx)
            else:
                prison_com101(ctx)
        elif arg == 201:  # :320–329
            if sh[2] > 0:
                shielded = True
                continue
            prison_com201(ctx) if exp(ctx, c, "Ａ拡張経験") > 3 else prison_com102(ctx)
        elif arg == 300:  # :331–332
            prison_com300(ctx)
        elif arg == 301:  # :334–347
            from ..action import config_check_maniac

            if t(ctx, c, "寄生") or config_check_maniac(st, 3) == 0:
                r = st.rng.rand(3)
                if r == 0:
                    prison_com0(ctx)
                elif r == 1:
                    prison_com1(ctx)
                else:
                    prison_com300(ctx)
            else:
                prison_com301(ctx)
        return
