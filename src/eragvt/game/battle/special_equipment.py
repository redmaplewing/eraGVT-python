"""ERB/ゲーム内_戦闘処理/MISC_PATCH.ERB：特殊裝備的原生回合效果。

三函式均無INPUT／RETURN；落尾寫RESULT:0=0，其餘元素保留。
引擎：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67、
reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740。
整數除法朝零：reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:298–312。
只有PRINT／字型節點交給catalog，不把條件或狀態操作交給解譯器。
"""
from ..action import Ctx
from ..era import div
from ..tentacle import enemy_type_check
from .core import run_chinobun


def _text(ctx: Ctx, name: str, amount: int = 0) -> None:
    """純顯示片段借用LOCAL:1；不留下別名函式的LOCAL或額外CALL的RESULT。"""
    st = ctx.state
    name = "MESSAGE_EQUIPMENT_" + name
    key = (name, 1)
    previous = st.temp.locals.get(key)
    result = st.result[0]
    st.temp.locals[key] = amount
    try:
        run_chinobun(ctx, name)
    finally:
        if previous is None:
            st.temp.locals.pop(key, None)
        else:
            st.temp.locals[key] = previous
        st.result[0] = result


def tk_drone(ctx: Ctx) -> None:
    """ERB/ゲーム内_戦闘処理/MISC_PATCH.ERB@TK_DRONE:3–39。"""
    from .hantei import damage

    st, c = ctx.state, ctx.state.target_chara
    roll = st.rng.rand(26)
    powered = c.tcvarn.get_bit(3, 0)
    if powered:
        c.tcvarn.set_bit(3, 0, False)
    st.result[0] = damage(ctx, "ATTACK_RANGE_LONG")
    if powered:
        c.tcvarn.set_bit(3, 0, True)
    amount = div(st.result[0] * roll, 100)
    _text(ctx, "DRONE_START")
    if st.flag[73] > 0:
        _text(ctx, "DRONE_CITIZEN")
        amount = 0
    elif roll < 5:
        _text(ctx, "DRONE_LOW")
        amount += 50
    elif roll < 20:
        _text(ctx, "DRONE_MIDDLE")
        amount += 100
    else:
        _text(ctx, "DRONE_HIGH")
        amount += 250
    st.flag[13] -= amount
    ctx.out.set_bold(True)
    if amount > 0:
        _text(ctx, "DRONE_DAMAGE", amount)
    ctx.out.set_bold(False)
    _text(ctx, "DRONE_END")
    st.result[0] = 0


def hp_autoregain(ctx: Ctx) -> None:
    """ERB/ゲーム内_戦闘処理/MISC_PATCH.ERB@HP_AUTOREGAIN:43–52。"""
    st, c = ctx.state, ctx.state.target_chara
    roll = 2 + st.rng.rand(7)
    amount = div(c.maxbase[0] * roll, 100)
    if c.base[0] + amount >= c.maxbase[0]:
        amount = c.maxbase[0] - c.base[0]
    c.base[0] += amount
    if amount > 0:
        _text(ctx, "REGAIN", amount)
    st.result[0] = 0


def servant(ctx: Ctx) -> None:
    """ERB/ゲーム内_戦闘処理/MISC_PATCH.ERB@SERVANT:56–83。"""
    st = ctx.state
    roll = st.rng.rand(25)
    _text(ctx, "SERVANT_CITIZEN" if enemy_type_check(st, "CITIZEN") == 1 else "SERVANT_OTHER")
    _text(ctx, "SERVANT_START")
    if roll < 5:
        line = 65
    elif roll < 10 and st.flag[73] > 0:
        line = 67
    elif roll < 10:
        line = 69
    elif roll < 15:
        line = 71
    elif roll < 20 and st.flag[73] > 0:
        line = 73
    elif roll < 20:
        line = 75
    elif st.flag[73] > 0:
        line = 77
    else:
        line = 79
    _text(ctx, f"SERVANT_{line}")
    st.tflag[3] += roll
    if st.flag[17] + st.tflag[3] < st.flag[16]:
        st.tflag[3] += 25
    st.result[0] = 0
