"""深夜の子触手襲来（S18）：`ゲーム内_イベント発生/強制発生イベント/FORCE_深夜の子触手襲来.ERB`（路徑相對 `source/earGVP/ERB/`）。

呼び出し元は `インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP`:162–163（`SIF CONFIG_CHECK_EVENT_F(1) > 0`）のみ。
SMALL_PRISON_COM の Ｖ襲来が AFTER_PILL（INPUT）を呼ぶので、SMALL_TENTACLE_HANTEI 以下はジェネレータ。

地の文 `地の文/MESSAGE_RAID.ERB` の MESSAGE_SMALL_ATTACK／_FAILED／_SUCCESS／MESSAGE_SMALL_PRISON_COM_0〜6 は状態変化を
含まない（代入・CALL なし）ので S07 catalog（`run_chinobun`）で出す。地の文は状態変化の**前**に呼ばれる（例：:195 → :201 ふたなり化）。

引擎語意：
- キャラ変数の添字省略は TARGET（`reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs`:91–134）。
  :105 `SIF ISHOLE() == 0` は候補 LOCAL ではなく呼び出し時の TARGET を見る（原作どおり）。
- `&&`／`||` は短絡（`GameData/Expression/OperatorMethod.cs`:532–536）：:130–137 の RAND は素質が条件を満たすときだけ引く。
- SMALL_PRISON_COM は :170 `VARSET LOCAL` で始まるので LOCAL は毎回 0 から（LOCAL のサイズは既定 1000：
  `GameData/ConstantData.cs`:148）。`POWER LOCAL:130, ABL:露出癖, 2` は累乗（`GameProc/Process.ScriptProc.cs`:326–338）。
- 関数末尾まで流れ落ちると RESULT = 0（`GameProc/Process.ScriptProc.cs`:61–67）。
"""

from __future__ import annotations

from collections.abc import Generator

from .action import Ctx, config_check_maniac
from .battle.core import abl, is_hole, is_manly, run_chinobun, t, tc
from .chara_common import is_female, is_male
from .shop import charanum_active

InputGen = Generator[None, int, int]

_LOCAL_SIZE = 200


def small_tentacle_hantei(ctx: Ctx) -> Generator[None, int, None]:
    """`@SMALL_TENTACLE_HANTEI`:8–76。"""
    st, out = ctx.state, ctx.out
    if charanum_active(st) == 0:  # :11–12
        return
    local = 0  # :15–26（繁殖袋／四肢欠損の CONTINUE は LOCAL++ の後なので数に影響しない）
    for i in range(1, st.charanum):
        if st.charas[i].cflag[999] == 0:
            continue
        if is_hole(ctx, i):
            local += 1
    if local < 1:
        return
    if st.time != 1:  # :29–30
        return
    local = st.flag[44] - sum(c.cflag[220] for c in st.charas)  # :32–35（FOR CCOUNT, 0, CHARANUM：MASTER も含む）
    if local < 1:  # :37–38
        return
    saved = st.target  # :39
    d = st.flag[852]  # :41–55
    for bound, n in ((1000, 3), (2500, 4), (5000, 8), (10000, 16), (15000, 32), (20000, 64)):
        if d < bound + local * 50:
            l2 = st.rng.rand(n)
            break
    else:
        l2 = st.rng.rand(128)
    if l2 == 0 and st.rng.rand(12 - st.flag[52] * 2) != 0:  # :56–57
        yield from small_tentacle_attack(ctx)
    elif st.rng.rand(20) == 10:  # :59–60 最低でも 5%
        yield from small_tentacle_attack(ctx)
    elif st.rng.rand(local) >= 9:  # :62–73
        st.flag[44] -= 1
        out.drawline()
        if st.flag[52] and (st.rng.rand(st.flag[52]) != 0 or l2 != 0):
            out.printw("子触手は防衛システムに引っかかって黒焦げにされた...")
        elif st.rng.rand(2) == 0:
            out.printw("子触手は何かの動物に襲われた...")
        else:
            out.printw("子触手は迷子になった...")
    st.target = saved  # :76


def small_tentacle_attack(ctx: Ctx) -> Generator[None, int, None]:
    """`@SMALL_TENTACLE_ATTACK`:81–110。"""
    st, out = ctx.state, ctx.out
    local = st.rng.rand(100)  # :82
    tries = 0  # :83 LOCAL:1
    out.drawline()  # :84
    if local < 25:  # :86–88 1/4 で見つかって処分
        run_chinobun(ctx, "MESSAGE_SMALL_ATTACK_FAILED")
        st.flag[44] -= 1
        return
    while True:  # $LOOP :91–106
        if tries >= 99:  # :93–98
            out.printw("子触手は迷子になった...")
            st.flag[44] -= 1
            out.drawline()
            return
        local = st.rng.rand(st.charanum - 1) + 1  # :99
        tries += 1
        c = st.charas[local]
        if c.cflag[999] == 0:  # :101–102
            continue
        if c.cflag[0] != 0:  # :103–104
            continue
        if not is_hole(ctx):  # :105–106 ISHOLE() は TARGET（候補ではない：原作どおり）
            continue
        break
    st.target = local  # :108
    yield from small_prison_event(ctx)  # :109


def small_prison_event(ctx: Ctx) -> Generator[None, int, None]:
    """`@SMALL_PRISON_EVENT`:116–163。"""
    from .battle.sexcom import check_holyvirgin

    st, data, out = ctx.state, ctx.data, ctx.out
    if charanum_active(st) == 0:  # :118–119
        return
    out.drawline()  # :121
    run_chinobun(ctx, "MESSAGE_SMALL_ATTACK")  # :122
    run_chinobun(ctx, "MESSAGE_SMALL_ATTACK_SUCCESS")  # :123
    c = tc(ctx)
    rand = st.rng.rand
    while True:  # :127–160
        kind = rand(7)
        if t(ctx, c, "ふたなり") > 0 and rand(10) == 0:
            kind = 0
        if t(ctx, c, "処女") < 1 and rand(11) == 0:
            kind = 1
        if t(ctx, c, "母乳体質") > 0 and rand(12) == 0:
            kind = 3
        if kind == 0 and is_female(data, c) and config_check_maniac(st, 1) == 0:  # :139–140
            kind = 1
        if kind == 1 and is_male(data, c):  # :143–151
            kind = 0 if is_manly(ctx) else 2
        if kind != 1 or check_holyvirgin(ctx) == 0:  # :158–159
            break
    yield from small_prison_com(ctx, kind)  # :162
    out.printw()  # :163


def _tbl(v: int, table: dict[int, int], default: int | None = None) -> int | None:
    """`IF ABL == 0 … ELSEIF … ELSE` 型（default が None なら ELSE なし＝該当しなければ代入しない）。"""
    return table.get(v, default)


def _set(L: list[int], i: int, v: int | None) -> None:
    if v is not None:
        L[i] = v


_SENSE = {0: 6, 1: 50, 2: 200, 3: 600, 4: 900}  # Ｃ・Ａ・Ｂ（:175–187 等。ELSE 1200）


def small_prison_com(ctx: Ctx, arg: int) -> Generator[None, int, None]:
    """`@SMALL_PRISON_COM, ARG`:168–556。"""
    from .battle.ablup import ablup
    from .battle.ninsin import after_pill, ninsin_hantei
    from .battle.sexcom import palam_vabc_estimate
    from .body import set_profile
    from .prison.commands import common_prison, common_prison_exp

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    rand = st.rng.rand
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    L = [0] * _LOCAL_SIZE  # :170 VARSET LOCAL
    if arg == 0:  # Ｃ襲来 :171–211
        L[0] = _tbl(a("Ｃ感覚"), _SENSE, 1200)
        palam_vabc_estimate(ctx, L, 0, -1)  # :190
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_0")  # :195
        if c.base[30]:  # :197 BASE:Ｃ結界耐久力
            pass
        elif t(ctx, c, "ふたなり") < 1 and is_female(data, c):  # :201–205 寄生ふたなりにする
            c.talent[ti("ふたなり")] = 2
            if t(ctx, c, "変身時ふたなり") < 1:
                c.talent[ti("変身時ふたなり")] = 2
            c.cflag[39] = c.exp[data.index_of("EXP", "射精経験")]
        else:  # :206–210
            L[153] += 5
            L[0] *= 3
    elif arg == 1:  # Ｖ襲来 :212–265
        L[1] = _tbl(a("Ｖ感覚"), {0: 10, 1: 20, 2: 40, 3: 100, 4: 200}, 400)
        palam_vabc_estimate(ctx, L, 1, -1)  # :230
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_1")  # :235
        if not c.base[31]:  # :237 BASE:Ｖ結界耐久力
            L[120] = 4 + rand(5)  # :241
            if t(ctx, c, "処女") < 1:  # :244–249
                L[123] = 15 + rand(16)
                L[124] = 1 + rand(2)
            if t(ctx, c, "処女") > 0:  # :251–258
                c.talent[ti("処女")] = -1
                c.cflag[206] = 1
                L[120] = 1
                L[10] = 500
            else:
                L[1] *= 3
            if t(ctx, c, "処女") < 1:  # :259–264（処女喪失直後も成立：LOCAL:123 = 0 のまま NINSIN_HANTEI）
                yield from after_pill(ctx, st.target, 35, 200)
                ninsin_hantei(ctx, L[123], 30, 200)
    elif arg == 2:  # Ａ襲来 :266–300
        L[2] = _tbl(a("Ａ感覚"), _SENSE, 1200)
        palam_vabc_estimate(ctx, L, 2, -1)  # :285
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_2")  # :290
        if not c.base[32]:  # :292 BASE:Ａ結界耐久力
            L[121] = 4 + rand(5)
            L[123] = 15 + rand(16)
    elif arg == 3:  # Ｂ襲来 :301–363
        L[3] = _tbl(a("Ｂ感覚"), _SENSE, 1200)
        palam_vabc_estimate(ctx, L, 3, -1)  # :320
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_3")  # :325
        if not c.base[33]:  # :327 BASE:Ｂ結界耐久力
            L[123] = 5 + rand(11)  # :331
            if is_female(data, c):  # :333–362
                if config_check_maniac(st, 2) == 0:
                    pass  # 母乳×なら何もしない
                elif t(ctx, c, "母乳体質") == 0:
                    c.talent[ti("母乳体質")] = 1
                elif config_check_maniac(st, 18) == 1 and (
                    t(ctx, c, "巨乳") < 2 or (config_check_maniac(st, 19) == 1 and t(ctx, c, "巨乳") < 5)
                ):
                    big, var = t(ctx, c, "巨乳"), t(ctx, c, "変身時胸サイズ変動")
                    if (big + var > 5) or (config_check_maniac(st, 19) == 0 and big + var >= 2):  # :343–346
                        c.talent[ti("変身時胸サイズ変動")] -= 1
                        c.cflag[38] -= 1
                    if t(ctx, c, "巨乳") - t(ctx, c, "貧乳") < 0:  # :349–353
                        c.talent[ti("貧乳")] -= 1
                    else:
                        c.talent[ti("巨乳")] += 1
                    c.cflag[37] += 1  # :354
                    set_profile(data, c)  # :356 SET_PROFILE, TARGET
                else:  # :357–359
                    L[154] += 5
                    L[3] *= 3
    elif arg == 4:  # 苦痛襲来 :364–425
        m = a("マゾっ気")
        _set(L, 8, _tbl(m, {0: 50, 1: 100, 2: 200, 3: 500, 4: 1000, 5: 2000}))  # :369–381（ELSE なし）
        L[10] = 5000  # :384
        if a("従順") < 3:  # :387–399
            L[11] = 1000 if m < 3 else 500
        else:
            L[11] = 200 if m < 3 else 100
        L[123] = 30 + rand(31)  # :402
        L[124] = 5 + rand(11)  # :404
        _set(L, 132, _tbl(m, {0: 1, 1: 2, 2: 4, 3: 8, 4: 14, 5: 25}))  # :407–419
        palam_vabc_estimate(ctx, L, -1)  # :422（部位なし）
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_4")  # :425
    elif arg == 5:  # 奉仕襲来 :427–496
        j = a("従順")
        _set(L, 5, 200 if j <= 2 else _tbl(j, {3: 500, 4: 1000, 5: 2000}))  # :431–439
        g = a("技巧")
        _set(L, 6, 4000 if g >= 5 else _tbl(g, {0: 100, 1: 200, 2: 500, 3: 1000, 4: 2000}))  # :443–455
        _set(L, 8, _tbl(j, {0: 100, 1: 200, 2: 500, 3: 1000, 4: 2000, 5: 5000}))  # :458–470
        h = a("奉仕精神")  # :473–483
        if h < 3:
            pass
        elif h < 4:
            L[5] += 200
            L[6] += 50
        elif h < 5:
            L[5] += 500
            L[6] += 100
        else:
            L[5] += 1000
            L[6] += 200
        L[123] = 10 + rand(11)  # :486
        L[124] = 5 + rand(11)  # :488
        L[131] += 1  # :490
        palam_vabc_estimate(ctx, L, -1)  # :493
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_5")  # :496
    elif arg == 6:  # 羞恥襲来 :498–542
        r = a("露出癖")
        _set(L, 9, _tbl(r, {0: 100, 1: 200, 2: 500, 3: 1000, 4: 2000, 5: 5000}))  # :502–514
        _set(L, 7, _tbl(r, {1: 100, 2: 200, 3: 500, 4: 1000, 5: 2000}))  # :517–527
        L[130] = r * r  # :530 POWER LOCAL:130, ABL:露出癖, 2
        L[130] += 1  # :531
        L[140] += 5  # :533
        L[123] = 5 + rand(11)  # :536
        palam_vabc_estimate(ctx, L, -1)  # :539
        run_chinobun(ctx, "MESSAGE_SMALL_PRISON_COM_6")  # :542
    common_prison(ctx, L[0:12])  # :546（ARG:12 省略 = 0：結界が反応する）
    for cc in range(100, 200):  # :549–551
        common_prison_exp(ctx, cc, L[cc])
    out.printl()  # :553
    ablup(ctx, 1)  # :556
