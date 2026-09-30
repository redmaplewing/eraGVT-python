"""淫紋：`ヒロイン関連/CHARA_TATTOO.ERB`（路徑相對 `source/earGVP/ERB/`）。

CFLAG:32 の構成（:44–93、:158–237 から）：`進行度 * 10^16 + 追加淫紋ビット * 10^14 + Σ 部位(0..3)の模様番号 * 100^部位`。
対象は TARGET（ABL／TALENT／CFLAG を添字 1 個で参照：`reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs`:107–119）。
関数の `#DIM`／LOCAL は呼び出し間で保持される（`TempVars.locals`）。`@PRINT_TATTOO`（:239–474）と `@TATTOO_LIB`（:478–1409）は
表示のみ（代入は自身の #DIM と RESULTS、RAND なし：grep 確認）なので、catalog で実行できなければ 1 行の佔位にする（deviations.md）。
"""

from __future__ import annotations

from .action import Ctx, config_check_maniac
from .battle.core import KANKAKU_NUM, t, tc
from .era import div, limit, mod

PROG_UNIT = 10000000000000000  # 10^16：進行度の桁
C_BIT, V_BIT, A_BIT, B_BIT = 1, 2, 4, 8  # DIM.ERH:95–101 Ｃ／Ｖ／Ａ／Ｂ


def _talent_i(ctx: Ctx, i: int) -> int:
    return tc(ctx).talent[i]


def tattoo_lv_cal(ctx: Ctx, arg: int) -> int:
    """`@TATTOO_LV_CAL(ARG)`:31–38：`ABL:ARG * (TALENT:(ARG*2+100) + 5) / 5 * (5 - TALENT:(ARG*2+101)) / 5
    * (TALENT:(ARG+153) + 2) / 2`（乗除は同順位・左結合）。"""
    c = tc(ctx)
    v = c.abl[arg] * (c.talent[arg * 2 + 100] + 5)
    v = div(v, 5) * (5 - c.talent[arg * 2 + 101])
    v = div(v, 5) * (c.talent[arg + 153] + 2)
    return div(v, 2)


def tattoo_position(ctx: Ctx) -> int:
    """`@TATTOO_POSITION`:7–25：感覚 LV 補正値が最大の部位（同値なら先の部位、:21–22 で V と同値なら V）。"""
    cv0 = cv1 = cv2 = 0  # :11 VARSET CAL_VAR
    for i in range(KANKAKU_NUM):
        cv0 = tattoo_lv_cal(ctx, i)
        if cv0 > cv1:
            cv1 = cv0
            cv2 = i
    if cv1 == tattoo_lv_cal(ctx, 1):
        cv2 = 1
    return cv2


def _des(cflag32: int, i: int) -> int:
    """:165–167 `DES_VAR:i = CFLAG:32 / POWER(100, i) % 100`。"""
    return mod(div(cflag32, 100**i), 100)


def tattoo_access(ctx: Ctx, key: str, arg: int = 0) -> int | str:
    """`@TATTOO_ACCESS, ARGS, ARG`:158–237。"POSITION_STR" は RESULTS（文字列）を返す。"""
    st = ctx.state
    c = tc(ctx)
    v = c.cflag[32]
    des = [_des(v, i) for i in range(8)]
    if key == "PROGRESS_VAR":  # :172–173
        return div(v, PROG_UNIT)
    if key == "TATTOO_RANK":  # :176–185
        if arg < KANKAKU_NUM:
            return div(tattoo_lv_cal(ctx, arg) * (div(v * 5, 100000000000000000) + 50), 800)
        total = sum(tattoo_lv_cal(ctx, i) for i in range(KANKAKU_NUM))
        return div(total * (div(v * 5, 100000000000000000) + 50), 2000)
    if key == "TATTOO_TYPE":  # :188–189
        return des[arg]
    if key == "POSITION_NUM":  # :192–193
        return sum(1 for i in range(4) if des[i] > 0)
    if key == "POSITION_BIT":  # :196–206
        r = 0
        for i, b in enumerate((C_BIT, V_BIT, A_BIT, B_BIT)):
            if des[i]:
                r += b
        return r
    if key == "POSITION_STR":  # :209–229（LOCALS は関数の静的変数：どれも無ければ前回の値のまま）
        slot = ("TATTOO_ACCESS", "LOCALS")
        if sum(1 for i in range(4) if des[i] > 0) > 1:
            if des[2] == 0 and des[3] == 0:
                s = "腹部"
            elif des[3] == 0:
                s = "下半身"
            else:
                s = "体中"
            st.temp.locals[slot] = s  # type: ignore[assignment]
            return s
        s = st.temp.locals.get(slot, "")  # type: ignore[assignment]
        for i, name in enumerate(("下腹部", "腹部", "右臀部", "左乳房")):
            if des[i]:
                s = name
        st.temp.locals[slot] = s  # type: ignore[assignment]
        return str(s)
    raise KeyError(key)


def save_tattoo(ctx: Ctx, arg: int) -> None:
    """`@SAVE_TATTOO, ARG`:44–88。"""
    st = ctx.state
    c = tc(ctx)
    rand = st.rng.rand
    if t(ctx, c, "触手の虜") == 0:  # :47–48
        return
    arg = limit(arg, 0, 100)  # :51
    if config_check_maniac(st, 10) == 0 and c.cflag[0] == 1:  # :53–56
        arg = div(c.cflag[32], PROG_UNIT)
        arg = limit(arg + 5 + rand(6), 0, 100)
    inn = sum(_talent_i(ctx, 153 + i) for i in range(KANKAKU_NUM))  # 淫核＋淫壷＋淫尻＋淫乳
    if c.cflag[32] == 0:  # :57–71
        c.cflag[32] = arg * PROG_UNIT
        local = config_check_maniac(st, 8)
        if config_check_maniac(st, 7) == 1 and inn > 0:
            for i in range(KANKAKU_NUM):
                if _talent_i(ctx, i + 153):
                    c.cflag[32] += (local * (rand(19) + 1) + 1) * 100**i
        else:
            pos = tattoo_position(ctx)
            c.cflag[32] += (local * (rand(19) + 1) + 1) * 100**pos
    else:  # :72–87
        c.cflag[32] = mod(c.cflag[32], PROG_UNIT)
        c.cflag[32] += arg * PROG_UNIT
        if config_check_maniac(st, 7) == 1 and inn > 0:
            local = tattoo_access(ctx, "POSITION_BIT")
            for i in range(KANKAKU_NUM):
                if (int(local) >> i) & 1 == 0 and _talent_i(ctx, i + 153):
                    c.cflag[32] += (config_check_maniac(st, 8) * (rand(19) + 1) + 1) * 100**i


def bitnum(arg: int) -> int:
    """`@BITNUM, ARG`:138–151（DO … LOOP：0 でも 1 回回る）。"""
    cal, res = arg, 0
    while True:
        if mod(cal, 2):
            res += 1
        cal = div(cal, 2)
        if not cal > 0:
            return res


def save_tattoo_additional(ctx: Ctx) -> None:
    """`@SAVE_TATTOO_ADDITIONAL, ARG`:94–132（追加淫紋。ARG は未使用）。"""
    st = ctx.state
    c = tc(ctx)
    bit = sum(1 for i in range(KANKAKU_NUM) if _talent_i(ctx, i + 153))
    if bit < KANKAKU_NUM:  # :106–107
        return
    bit = int(tattoo_access(ctx, "TATTOO_TYPE", 7))  # :110–111
    if bitnum(bit) >= 5:
        return
    while True:  # :116–128
        r = st.rng.rand(7)
        if bit & (2**r):
            r = -1
        if r > 2 and mod(r, 2) and bit & (2 ** (r + 1)):
            r = -1
        if r > 2 and mod(r, 2) == 0 and bit & (2 ** (r - 1)):
            r = -1
        if not r < 0:
            break
    bit |= 1 << r  # :130 SETBIT
    v = c.cflag[32]
    c.cflag[32] = mod(v, 1000000000000) + div(v, PROG_UNIT) * PROG_UNIT + bit * 100000000000000  # :131


def print_tattoo(ctx: Ctx, arg: int, arg1: int = 0) -> None:
    """`@PRINT_TATTOO, ARG, ARG:1`:239–474（表示のみ）。

    DEVIATION（表示のみ）：catalog で実行できない（`CHKFONT` 未対応など）場合は「〈淫紋：…〉」の 1 行で代える。
    状態は変えず RAND も引かない関数なので、代わりの表示でも以降の処理は原作と同じ。
    """
    if ctx.narration.run_function(ctx, "PRINT_TATTOO", [arg, arg1]):
        return
    ctx.out.print(f"〈淫紋：PRINT_TATTOO {arg}〉")
