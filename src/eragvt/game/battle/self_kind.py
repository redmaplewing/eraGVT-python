"""自慰：`ゲーム内_イベント発生/強制発生イベント/FORCE_夜間自慰.ERB`（路徑相對 `source/earGVP/ERB/`）。

SELF_NIGHT（:5–61）は `turnend.self_night`、SELF_BATTLEEND（:65–72）・SELF_CHECK（:77–178）・SELF_KIND（:182–247）・
SELF_N／B／A／V（:251–811）はここ。呼び出し元：
- 強制自慰：`SEX_SPCOM6.ERB@SEX_SPCOM6`:45 `CALL SELF_KIND, TARGET, 0`（`sexcom.sex_spcom6`）
- 戦闘後自慰：`SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLEEND`:12–13 `CALL SELF_BATTLEEND, TARGET`（`after.subevent_battleend`）
- 夜間自慰：`SHOP_TURNEND.ERB@EVENTTURNEND`:116 `CALL SELF_NIGHT`（`turnend.self_night`：:22 で TARGET = 対象キャラ）
いずれも ARG == TARGET。PALAM_VABCestimate・PALAM_CAL・地の文は TARGET を見るので、ここでも ARG == TARGET を前提にする。

地の文 `地の文/MESSAGE_SEX.ERB`@MESSAGE_SELF_NIGHT:1070／BATTLEEND:1092／N:1106／B:1146／A:1182／V:1211 と
`地の文/MESSAGE_OTHER.ERB`@MESSAGE_OTHER_SELF_N:1497／B:1507／A:1517／V:1527 は catalog（本文と KOJO_ROOT のみ、
RAND・状態変化なし：grep 確認）。fallback は末尾の `TRYCALLFORM KOJO_ROOT`。

引擎語意：
- SELF_KIND の `#DIM Ｖ自慰可`／`#DIM Ａ自慰可` は静的（呼び出しをまたいで保持、ResetData／読込でのみ 0：
  `reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs@SetDefaultLocalValue`:514–520、
  `GameProc/UserDefinedVariable.cs`:27）。関数内で 0 に戻す文は無い → 一度 1 になると以後どのキャラでも 1（原作どおり、
  `st.temp.locals`）。
- `VARSET NOWEX` は TARGET の配列全体（`GameProc/Function/Instraction.Child.cs`:1132–1164）。
- `&&` は短絡（`GameData/Expression/OperatorMethod.cs`:532–536）。
- SELF_N／B／A／V の `REPEAT 12 / LOCAL:COUNT = 0` で LOCAL:0〜11 は毎回 0、LOCAL:12 は必ず代入 → 前回値は残らない。
"""

from __future__ import annotations

from ..counting import count_loop
from collections.abc import Generator

from ..action import Ctx, kojo_root, kojo_root_full
from ..chara_common import is_female
from ..era import times
from ..tentacle import enemy_type_check
from .core import run_chinobun, t

_V_OK = ("SELF_KIND#Ｖ自慰可", 0)
_A_OK = ("SELF_KIND#Ａ自慰可", 0)

# 技巧ボーナス（各 SELF_*：技巧 0／1 は補正なし、負の値も補正なし）
_GIKOU = {2: "1.10", 3: "1.25", 4: "1.50"}


def _tbl(v: int, table: tuple[int, ...]) -> int:
    """`IF ABL == 0 … ELSEIF ABL >= 5` の 6 段表（負の値はどれにも当たらず 0）。"""
    if v < 0:
        return 0
    return table[min(v, 5)]


def _gikou(v: int, x: int) -> int:
    if v >= 5:
        return times(x, "2.00")
    if v in _GIKOU:
        return times(x, _GIKOU[v])
    return x


def self_check(ctx: Ctx, who: int) -> int:
    """`@SELF_CHECK, ARG`:77–178。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    p = c.palam[data.index_of("PALAM", "欲情")]
    if p == 0:  # :84–110
        local = 0
    else:
        for bound, val in ((100, 1), (300, 2), (600, 4), (1500, 6), (3000, 8), (6000, 10), (10000, 12), (30000, 15),
                           (60000, 18), (150000, 21), (300000, 25)):
            if p < bound:
                local = val
                break
        else:
            local = 30
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    step = ("0.25", "0.50", "0.75", "1.00", "1.25", "1.50")
    if a("欲望") >= 0:  # :114–126（負の値はどの分岐にも当たらない）
        local = times(local, step[min(a("欲望"), 5)])
    if a("露出癖") >= 0:  # :129–141
        local = times(local, step[min(a("露出癖"), 5)])
    onani = a("自慰中毒")  # :144–154
    if onani >= 1:
        local = times(local, {1: "1.25", 2: "1.50", 3: "2.00", 4: "2.50"}.get(onani, "4.00"))
    if t(ctx, c, "淫乱") == 1:  # :157–158
        local = times(local, "2.00")
    r = st.rng.rand(100)  # :161–172
    for bound, fac in ((20, "0.80"), (40, "0.90"), (60, "1.00"), (80, "1.10")):
        if r < bound:
            local = times(local, fac)
            break
    else:
        local = times(local, "1.20")
    return 1 if local >= 15 else 0  # :175–178


def self_battleend(ctx: Ctx, arg: int) -> Generator[None, int, None]:
    """`@SELF_BATTLEEND, ARG`:65–72。"""
    from .ablup import ablup

    if self_check(ctx, arg) == 1:
        run_chinobun(ctx, "MESSAGE_SELF_BATTLEEND", fallback=lambda: kojo_root(ctx, "SELF_BATTLEEND"))  # :69
        yield from self_kind(ctx, arg, 1)  # :70
        ablup(ctx, 0)  # :71


def self_kind(ctx: Ctx, arg: int, arg1: int) -> Generator[None, int, None]:
    """`@SELF_KIND, ARG, ARG:1`:182–247。ARG:1 == 1 は戦闘後自慰（悪堕ちキャラ戦の目撃地の文のみに影響）。"""
    st, data = ctx.state, ctx.data
    c = st.charas[arg]
    loc = st.temp.locals
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    fem = lambda: is_female(data, c)  # noqa: E731
    c.nowex.clear()  # :189 VARSET NOWEX（TARGET = ARG）
    # :192–200（`素質 > 0 && RAND:3 == 0 && ISFEMALE(ARG)`：左から短絡）
    if t(ctx, c, "淫壷") > 0 and st.rng.rand(3) == 0 and fem():
        yield from self_v(ctx, arg, arg1)
    elif t(ctx, c, "淫尻") > 0 and st.rng.rand(3) == 0:
        yield from self_a(ctx, arg, arg1)
    elif t(ctx, c, "淫乳") > 0 and st.rng.rand(3) == 0:
        yield from self_b(ctx, arg, arg1)
    elif t(ctx, c, "淫核") > 0 and st.rng.rand(3) == 0:
        yield from self_n(ctx, arg, arg1)
    c.nowex.clear()  # :203
    if a("Ｖ感覚") >= 1:  # :206–209（静的 #DIM：0 に戻さない）
        loc[_V_OK] = 1
    if a("Ａ感覚") > 1:
        loc[_A_OK] = 1
    v_ok, a_ok = loc.get(_V_OK, 0), loc.get(_A_OK, 0)
    if v_ok == 0 and a_ok == 0:  # :211–217
        if st.rng.rand(100) < 50:
            yield from self_n(ctx, arg, arg1)
        else:
            yield from self_b(ctx, arg, arg1)
    elif v_ok == 1:  # :218–226
        r = st.rng.rand(99)
        if r < 33:
            yield from self_n(ctx, arg, arg1)
        elif r < 66 and fem():
            yield from self_v(ctx, arg, arg1)
        else:
            yield from self_b(ctx, arg, arg1)
    elif a_ok == 1:  # :227–235
        r = st.rng.rand(99)
        if r < 33:
            yield from self_n(ctx, arg, arg1)
        elif r < 66:
            yield from self_b(ctx, arg, arg1)
        else:
            yield from self_a(ctx, arg, arg1)
    # :236–247 `ELSEIF Ｖ自慰可 == 1 && Ａ自慰可 == 1` は :218 の Ｖ自慰可 == 1 に先に当たるので到達しない（原作どおり）


def _other(ctx: Ctx, arg1: int, kind: str) -> None:
    """`SIF ENEMY_TYPE_CHECK_F("AKUOTI") == 1 && ARG:1 == 1 / CALL MESSAGE_OTHER_SELF_x`。"""
    st = ctx.state
    if enemy_type_check(st, "AKUOTI") == 1 and arg1 == 1:
        e = st.charas[st.flag[111]]
        run_chinobun(ctx, f"MESSAGE_OTHER_SELF_{kind}",
                     fallback=lambda: kojo_root_full(ctx, e.cflag[6], f"OTHER_SELF_{kind}"))


def _tail(ctx: Ctx, arg: int, arg1: int, kind: str, L: list[int], kutsu: tuple, chijo: tuple, l12: int) -> Generator[None, int, None]:
    """各 SELF_x の地の文以降（屈服・恥情・欲情・習得・体力消費 → PALAM_CAL）。"""
    from .palam import palam_cal

    c = ctx.state.charas[arg]
    a = lambda n: c.abl[ctx.data.index_of("ABL", n)]  # noqa: E731
    run_chinobun(ctx, f"MESSAGE_SELF_{kind}", fallback=lambda: kojo_root(ctx, f"SELF_{kind}"))
    _other(ctx, arg1, kind)
    L[8] = _tbl(a("露出癖"), kutsu)  # 屈服
    L[9] = _tbl(a("露出癖"), chijo)  # 恥情
    onani = a("自慰中毒")
    if onani >= 1:  # 欲情（自慰中毒 0 は代入なし → LOCAL:7 = 0 のまま）
        L[7] = (1000, 2000, 5000, 10000, 20000)[min(onani, 5) - 1]
    if onani >= 0:  # 習得
        L[6] = (200, 400, 800, 1000, 2000, 4000)[min(onani, 5)]
    L[12] = l12
    yield from palam_cal(ctx, *L[:12], losebase=L[12])


def self_n(ctx: Ctx, arg: int, arg1: int) -> Generator[None, int, None]:
    """`@SELF_N, ARG, ARG:1`:251–406。"""
    from .sexcom import palam_vabc_estimate

    data = ctx.data
    c = ctx.state.charas[arg]
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :255–257
    c.exp[data.index_of("EXP", "自慰経験")] += 1  # :260
    L[0] = _tbl(a("Ｃ感覚"), (200, 1000, 2000, 4000, 10000, 20000))  # :262–274
    L[3] = _tbl(a("Ｂ感覚"), (200, 400, 1000, 2000, 4000, 10000))  # :277–289
    if t(ctx, c, "処女") < 1 and is_female(data, c):  # :292–307
        c.exp[data.index_of("EXP", "Ｖ経験")] += 1
        L[1] = _tbl(a("Ｖ感覚"), (200, 400, 1000, 4000, 10000, 20000))
    g = a("技巧")  # :310–328
    L[0], L[1], L[3] = _gikou(g, L[0]), _gikou(g, L[1]), _gikou(g, L[3])
    palam_vabc_estimate(ctx, L, 0, 1, 3, -1)  # :331
    yield from _tail(ctx, arg, arg1, "N", L, (50, 100, 200, 500, 1000, 2000), (50, 100, 200, 500, 1000, 2000), 150)


def self_b(ctx: Ctx, arg: int, arg1: int) -> Generator[None, int, None]:
    """`@SELF_B, ARG, ARG:1`:410–525。"""
    from .sexcom import palam_vabc_estimate

    data = ctx.data
    c = ctx.state.charas[arg]
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :413–415
    c.exp[data.index_of("EXP", "自慰経験")] += 1  # :418
    L[3] = _tbl(a("Ｂ感覚"), (200, 400, 1000, 2000, 4000, 10000))  # :421–433
    L[3] = _gikou(a("技巧"), L[3])  # :436–446
    palam_vabc_estimate(ctx, L, 3, -1)  # :449
    yield from _tail(ctx, arg, arg1, "B", L, (50, 100, 200, 500, 1000, 2000), (100, 200, 500, 1000, 2000, 4000), 100)


def self_a(ctx: Ctx, arg: int, arg1: int) -> Generator[None, int, None]:
    """`@SELF_A, ARG, ARG:1`:529–641。Ａ感覚 0／1 は快Ａ の代入なし（0）。"""
    from .sexcom import palam_vabc_estimate

    data = ctx.data
    c = ctx.state.charas[arg]
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :533–535
    c.exp[data.index_of("EXP", "自慰経験")] += 1  # :538
    c.exp[data.index_of("EXP", "Ａ経験")] += 1  # :539
    L[2] = _a_table(a("Ａ感覚"), (2000, 4000, 10000, 20000))  # :541–549
    L[2] = _gikou(a("技巧"), L[2])  # :552–562
    palam_vabc_estimate(ctx, L, 2, -1)  # :565
    yield from _tail(ctx, arg, arg1, "A", L, (100, 200, 500, 1000, 2000, 4000), (100, 200, 500, 1000, 2000, 4000), 150)


def _a_table(v: int, table: tuple[int, int, int, int]) -> int:
    """`IF ABL:Ａ感覚 == 2 … ELSEIF >= 5`（0／1／負は代入なし）。"""
    if v < 2:
        return 0
    return table[min(v, 5) - 2]


def self_v(ctx: Ctx, arg: int, arg1: int) -> Generator[None, int, None]:
    """`@SELF_V, ARG, ARG:1`:645–811。"""
    from .sexcom import palam_vabc_estimate

    data = ctx.data
    c = ctx.state.charas[arg]
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    vexp = data.index_of("EXP", "Ｖ経験")
    L = [0 for _ in count_loop(ctx.state, 12)] + [0]  # :649–651
    c.exp[data.index_of("EXP", "自慰経験")] += 1  # :654
    if t(ctx, c, "処女") >= 1:  # :656–669 処女：減少、経験なし
        L[1] = _tbl(a("Ｖ感覚"), (100, 200, 500, 2000, 4000, 10000))
    elif t(ctx, c, "淫尻") > 0:  # :671–685 二穴
        c.exp[vexp] += 1
        L[1] = _tbl(a("Ｖ感覚"), (200, 400, 1000, 3000, 7500, 15000))
    else:  # :686–701
        c.exp[vexp] += 1
        L[1] = _tbl(a("Ｖ感覚"), (200, 400, 1000, 4000, 10000, 20000))
    if t(ctx, c, "淫尻") > 0:  # :704–715
        c.exp[data.index_of("EXP", "Ａ経験")] += 1
        L[2] = _a_table(a("Ａ感覚"), (1000, 3000, 7500, 15000))
    g = a("技巧")  # :718–732
    L[1], L[2] = _gikou(g, L[1]), _gikou(g, L[2])
    palam_vabc_estimate(ctx, L, 1, 2, -1)  # :735
    yield from _tail(ctx, arg, arg1, "V", L, (50, 100, 200, 500, 1000, 2000), (50, 100, 200, 500, 1000, 2000), 150)
