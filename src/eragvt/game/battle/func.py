"""戦闘の共通関数：変身・行動制限・撤退可否・戦闘支援・コンボ・状態異常。

路徑相對 `source/earGVP/ERB/`：`ゲーム内_戦闘処理/COMMON_BATTLE_FUNC.ERB`、`COMBO_ATTACK.ERB`、
`BATTLE_SHOW_STATUS.ERB@CALC_CHISEI_SHIEN`、`ヒロイン関連/CHARA_STATE_CHANGE.ERB`。
"""

from __future__ import annotations

from ...state.constants import ActionPlan
from ..action import Ctx, config_check_event, config_check_screen, kojo_root, print_transcallname
from ..chara_common import charatalent, is_male, seikaku_check
from ..era import div, isqrt, times
from ..shop import is_action_incapable
from ..tentacle import enemy_type_check
from .cloth import cloth_battle_hosei, cloth_no_inner, NO_INNER
from .core import (
    HAIRAN,
    HATUJOU,
    KIZETU,
    MAHI,
    P_EX_HANGEKI,
    P_HANGEKI,
    percent_cal,
    print_distance,
    seikaku_hosei_palam,
    t,
    tc,
)


# --- @TRANSFORM（COMMON_BATTLE_FUNC.ERB:426–608）----------------------------------------


def transform(ctx: Ctx, arg: int, who: int = -999) -> int:
    """`@TRANSFORM, ARG, ARG:1`：変身状態を ARG（0 通常、1 変身、2 SP 変身）に。"""
    st, data = ctx.state, ctx.data
    if who == -999:
        who = st.target
    c = st.charas[who]
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    if c.cflag[1] == arg:
        return 0
    if c.cflag[1] == 0 and arg == 0:
        return 0
    airplus = cloth_battle_hosei(ctx, "AIRPLUS", who)
    r = cloth_battle_hosei(ctx, "AIRPLUS", who)
    if airplus == 0 and r > 0:
        c.maxbase[22] += 1
        c.base[22] = c.maxbase[22]
        if c.base[22] >= 5:
            c.base[22] = 5
    elif airplus == 1 and r == 0:
        c.maxbase[22] -= 1
        c.base[22] = c.maxbase[22]
        if c.base[22] < 0:
            c.base[22] = 0
    tal = c.talent
    if arg > 0:
        if tt("変身時ＴＳ") > 0 and charatalent(data, c, 1, "オトコ") == 0:
            tal[ti("オトコ")] = -1
            tal[ti("処女")] = 1
            if tt("変身時非処女") > 0:
                tal[ti("処女")] = -1
            if tt("変身時濡れやすさ変動") == 1:
                tal[ti("濡れやすい")] = 1
            elif tt("変身時濡れやすさ変動") == -1:
                tal[ti("濡れにくい")] = 1
            if tt("変身時Ｖ感覚変動") == 1:
                tal[ti("Ｖ敏感")] = 1
            elif tt("変身時Ｖ感覚変動") == -1:
                tal[ti("Ｖ鈍感")] = 1
        elif tt("変身時ＴＳ") > 0 and charatalent(data, c, 1, "オトコ") > 0:
            tal[ti("オトコ")] = 1
            if tt("処女") > 0:
                tal[ti("処女")] -= 5
            if st.target_chara.tcvarn[12] & HAIRAN:
                st.target_chara.tcvarn[12] -= HAIRAN
            for n in ("濡れやすい", "濡れにくい", "Ｖ敏感", "Ｖ鈍感", "貧乳", "巨乳"):
                tal[ti(n)] *= -1
        v = max(tt("巨乳"), 0) - max(tt("貧乳"), 0) + tt("変身時胸サイズ変動")
        _set_bust(ctx, c, v)
        v = max(tt("長身"), 0) - max(tt("小柄"), 0) + tt("変身時体格変動")
        _set_body(ctx, c, v)
        _swap(tal, ti("男の娘"), ti("変身時男の娘"))
        _swap(tal, ti("ふたなり"), ti("変身時ふたなり"))
        # :530 `SIF TFLAG:700 > 0`（FLAG ではなく TFLAG:700。TFLAG:700 はどこでも立たないので実質不成立：原作どおり）
        if st.tflag[700] > 0:
            st.target_chara.tcvarn[10] = 1
    else:
        if tt("変身時ＴＳ") > 0 and charatalent(data, c, 0, "オトコ") > 0:
            tal[ti("オトコ")] = 1
            if tt("処女") == -1:
                tal[ti("変身時非処女")] = 1
            tal[ti("処女")] = 0
            if st.target_chara.tcvarn[12] & HAIRAN:
                st.target_chara.tcvarn[12] -= HAIRAN
            for n in ("濡れやすい", "濡れにくい", "Ｖ敏感", "Ｖ鈍感"):
                tal[ti(n)] = 0
        elif tt("変身時ＴＳ") > 0 and charatalent(data, c, 0, "オトコ") == 0:
            tal[ti("オトコ")] = 0
            if tt("処女") < -2:
                tal[ti("処女")] += 5
            for n in ("濡れやすい", "濡れにくい", "Ｖ敏感", "Ｖ鈍感", "貧乳", "巨乳"):
                tal[ti(n)] *= -1
        v = max(tt("巨乳"), 0) - max(tt("貧乳"), 0) - tt("変身時胸サイズ変動")
        _set_bust(ctx, c, v, untransform=True)
        v = max(tt("長身"), 0) - max(tt("小柄"), 0) - tt("変身時体格変動")
        _set_body(ctx, c, v)
        _swap(tal, ti("男の娘"), ti("変身時男の娘"))
        _swap(tal, ti("ふたなり"), ti("変身時ふたなり"))
    c.cflag[1] = arg
    # :605–606 `CALL CLOTH_NO_INNER, TARGET` → CLOTH_NO_INNER = RESULT
    st.temp.cloth[NO_INNER] = cloth_no_inner(ctx, st.target)
    return 1


def _swap(tal, a: int, b: int) -> None:
    tal[a], tal[b] = tal[b], tal[a]


def _set_bust(ctx: Ctx, c, v: int, untransform: bool = False) -> None:
    """:492–513（変身）／:561–585（解除。0 の場合も 0/0 に設定される）。"""
    ti = lambda n: ctx.data.index_of("TALENT", n)  # noqa: E731
    small, big = ti("貧乳"), ti("巨乳")
    if v <= -2:
        c.talent[small], c.talent[big] = 2, 0
    elif v == -1:
        c.talent[small], c.talent[big] = 1, 0
    elif v == 0:
        if untransform:
            c.talent[small], c.talent[big] = 0, 0
    elif v >= 5:
        c.talent[small], c.talent[big] = 0, 5
    else:
        c.talent[small], c.talent[big] = 0, v


def _set_body(ctx: Ctx, c, v: int) -> None:
    """:515–524／:587–596。"""
    ti = lambda n: ctx.data.index_of("TALENT", n)  # noqa: E731
    small, tall = ti("小柄"), ti("長身")
    if v < 0:
        c.talent[small], c.talent[tall] = 1, 0
    elif v == 0:
        c.talent[small], c.talent[tall] = 0, 0
    else:
        c.talent[small], c.talent[tall] = 0, 1


# --- @ACT_LIMIT（COMMON_BATTLE_FUNC.ERB:196–390）----------------------------------------


def _land_and_print(ctx: Ctx) -> None:
    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[216] & 1:
        c.tcvarn[216] = 4
    if t(ctx, c, "有翼") > 0:
        st.tflag[99] += 1
    print_distance(ctx)
    ctx.out.printl()
    ctx.out.printl(f"{print_transcallname(st, st.target)}の様子がおかしい・・・")


_DISACTION = {  # MESSAGE_BATTLE_DISACTION_*（地の文/MESSAGE_BATTLE.ERB:1975–2021）
    0: ("KAIRAKU", "快楽"),
    1: ("KUTUU", "苦痛"),
    2: ("KUTUZYOKU", "屈辱"),
    3: ("KYOUHU", "恐怖"),
    4: ("TIZYOKU", "恥辱"),
}


def act_limit(ctx: Ctx) -> int:
    """`@ACT_LIMIT`：刻印・素質による行動不能判定。1 なら行動できない。"""
    st = ctx.state
    c = tc(ctx)
    if st.flag[72] > 0 and st.flag[70] > 0 and st.tflag[30] == 2 and c.tcvarn[0] == 3:
        ctx.out.printl()
        ctx.out.printl(f"戦っている{print_transcallname(st, st.target)}の後ろにいる観衆が")
        ctx.out.printl("さっきよりも近づいている気がする")
    if t(ctx, c, "触手の虜") == 1:
        if st.rng.rand(100) < 6:
            _land_and_print(ctx)
            # MESSAGE_BATTLE_DISACTION_TORIKO（MESSAGE_BATTLE.ERB:1975–1980）
            ctx.out.printl(f"{print_transcallname(st, st.target)}は不意にこれまでの数々の陵辱を思い出してしまい")
            ctx.out.printl("体が竦んでしまった・・・")
            kojo_root(ctx, "BATTLE_DISACTION_TORIKO")
            ctx.out.printw()
            return 1
    if t(ctx, c, "寄生") == 1:
        raise NotImplementedError("ACT_LIMIT：寄生による行動制限は未移植")
    if t(ctx, c, "妊娠") in (4, 5) and c.cflag[222] >= 56:
        raise NotImplementedError("ACT_LIMIT：妊娠後期の行動制限は未移植")
    if st.flag[72] > 0 and st.flag[70] > 0 and st.tflag[30] > 2 and c.tcvarn[0] == 3:
        raise NotImplementedError("ACT_LIMIT：クズ市民観衆による妨害は未移植")
    for count in range(5):
        m = c.mark[count]
        base = {0: 0, 1: 60, 2: 120, 3: 180, 4: 240, 5: 300}.get(m)
        if base is None:
            # MARK が 0–5 以外なら LOCAL は前回値（静的 LOCAL）。刻印は 0–5 の範囲でしか増えない。
            raise NotImplementedError(f"ACT_LIMIT：MARK:{count} = {m}（範囲外）")
        palam_id = {0: 13, 1: 16, 2: 14, 3: 17, 4: 15}[count]
        local = seikaku_hosei_palam(seikaku_check(ctx.data, c), palam_id, base)
        if st.flag[905]:
            local = 0
        elif st.flag[910]:
            local *= 2
        if local > 0:
            if st.rng.rand(10000) < local:
                _land_and_print(ctx)
                # MESSAGE_BATTLE_DISACTION_*（地の文/MESSAGE_BATTLE.ERB:1983–2021）
                _disaction_message(ctx, count)
                return 1
    return 0


def _disaction_message(ctx: Ctx, count: int) -> None:
    """`MESSAGE_BATTLE_DISACTION_KAIRAKU` 等（MESSAGE_BATTLE.ERB:1983–2021）。"""
    st = ctx.state
    code, word = _DISACTION[count]
    ctx.out.printl(f"{print_transcallname(st, st.target)}は不意にこれまでに与えられた{word}を思い出してしまい")
    ctx.out.printl("体が竦んでしまった・・・")
    kojo_root(ctx, f"BATTLE_DISACTION_{code}")
    ctx.out.printw()


def check_can_retreat(ctx: Ctx) -> int:
    """`@CHECK_CAN_RETREAT_F`（COMMON_BATTLE_FUNC.ERB:396–417）。"""
    st = ctx.state
    c = tc(ctx)
    if st.flag[999] == 0:
        if c.tcvarn[0] == 0:
            return 0
        if st.flag[73] > 0:
            raise NotImplementedError("クズ市民戦の撤退判定は未移植")
    return 1


# --- @CALC_CHISEI_SHIEN（BATTLE_SHOW_STATUS.ERB:467–505）--------------------------------


def calc_chisei_shien(ctx: Ctx, arg: int) -> int:
    st, data = ctx.state, ctx.data
    total = 0
    for i in range(st.charanum):
        if i == 0 or i > 6:
            continue
        if is_action_incapable(data, st, ActionPlan.SUPPORT, i) > 0:
            continue
        c = st.charas[i]
        if c.cflag[100] != ActionPlan.SUPPORT:
            continue
        if arg == 0:
            cal = div(c.maxbase[13], 4)
        elif arg == 1:
            cal = div(c.maxbase[13], 8)
        elif arg == 2:
            cal = div(max(c.base[13] - 100, 2), 2)
        else:
            raise ValueError(arg)
        cal = div(cal * cloth_battle_hosei(ctx, "CHISEI", i), 100)
        if c.cflag[43] == 511:
            cal = div(cal * 110, 100) + 5
        if t(ctx, c, "献身的") > 0:
            cal = div(cal * 110, 100) + 5
        if t(ctx, c, "四肢欠損") > 0:
            cal = div(cal * 150, 100) + 5
        if t(ctx, st.target_chara, "自分勝手") > 0:
            cal = div(cal * 25, 100)
        total += cal
    return total


# --- コンボ（COMBO_ATTACK.ERB）--------------------------------------------------------


def get_air_strike(ctx: Ctx, arg: int) -> int:
    """`@GET_AIR_STRIKE`:8–23。"""
    c = tc(ctx)
    if arg == 1:
        v = max(50 - div(c.cflag[99], 5) * 5, 25)
        if t(ctx, c, "エアマスター") > 0:
            v += 25
        return v
    if arg == 2:
        return 25
    if arg == 3:
        return 10
    raise ValueError(arg)


def get_brave_hit(ctx: Ctx, arg: int, kind: str) -> int:
    """`@GET_BRAVE_HIT`:27–66。"""
    c = tc(ctx)
    if arg < 4:
        v = 3 + arg * 3
    elif arg < 7:
        v = 6 + arg * 2
    else:
        v = 12 + arg
    v = min(v, 25)
    tt = lambda n: t(ctx, c, n)  # noqa: E731
    d = c.tcvarn[0]
    if kind == "命中" and d == 1:
        v = times(v, "3" if tt("近距離得意") else "1.1" if tt("近距離苦手") else "1.7")
    elif kind == "回避" and d == 2:
        v = times(v, "0.8" if tt("中距離得意") else "0.9" if tt("中距離苦手") else "0.85")
    elif kind == "回避" and d == 3:
        v = times(v, "0.7" if tt("遠距離得意") else "0.8" if tt("遠距離苦手") else "0.75")
    return v


def get_chain_hit(ctx: Ctx, arg: int) -> int:
    """`@GET_CHAIN_HIT`:69–80（:73 は LOCAL を見ているが LOCAL は :72 で代入されない側。静的 LOCAL の前回値）。"""
    st = ctx.state
    prev = st.temp.locals.get(("GET_CHAIN_HIT", 0), 0)
    if arg < 6:
        v = 100 + arg * 3
    elif prev < 11:
        v = 105 + arg * 2
    else:
        v = 115 + arg
    v = min(v, 200)
    st.temp.locals[("GET_CHAIN_HIT", 0)] = v
    return v


def get_counter_attack(ctx: Ctx, arg: int) -> int:
    """`@GET_COUNTER_ATTACK`:83–90。"""
    b = tc(ctx).base[11]
    if arg == 1:
        return 6 + min(div(isqrt(max(b - 80, 0)), 2), 15)
    if arg == 2:
        return 35 + min(isqrt(max(b - 100, 0)), 25)
    raise ValueError(arg)


def get_evader_atk(ctx: Ctx, arg: int) -> int:
    """`@GET_EVADER_ATK`:93–104（GET_CHAIN_HIT と同じ静的 LOCAL の癖）。"""
    st = ctx.state
    prev = st.temp.locals.get(("GET_EVADER_ATK", 0), 0)
    if arg < 6:
        v = 100 + arg * 3
    elif prev < 11:
        v = 105 + arg * 2
    else:
        v = 115 + arg
    v = min(v, 200)
    st.temp.locals[("GET_EVADER_ATK", 0)] = v
    return v


def get_evader_crt(arg: int) -> int:
    """`@GET_EVADER_CRT`:105–114。"""
    v = arg if arg < 6 else -3 + arg * 2
    return min(v, 15)


# --- 状態異常（ヒロイン関連/CHARA_STATE_CHANGE.ERB）---------------------------------------


def _state_on(ctx: Ctx, head: str, name: str, color: tuple[int, int, int], tail: str, bit: int) -> None:
    st = ctx.state
    out = ctx.out
    out.print(f"{print_transcallname(st, st.target)}{head}")
    out.set_bold(True)
    out.set_color(color)
    out.print(f"[{name}]")
    out.reset_color()
    out.set_bold(False)
    out.printl(tail)
    out.printw()
    tc(ctx).tcvarn[12] |= bit


def _kizetu_menu(ctx: Ctx) -> None:
    c = tc(ctx)
    if config_check_screen(ctx.state, 2) > 0:
        c.tcvarn[8] = 2 if c.tcvarn[0] == 0 else 0


def state_change_kizetu_damage(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_KIZETU_DAMAGE, ARG`:6–50。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    if v[12] & KIZETU:
        return
    if c.cflag[1] == 2:
        return
    if t(ctx, c, "生粋の戦士") > 0:
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(2) == 0:
        return
    r = percent_cal(arg, c.maxbase[0])
    if v[200] > 0:
        return
    if v[2] in (P_HANGEKI, P_EX_HANGEKI) and r <= 15:
        return
    local = 0
    if r >= 30:
        local += div(max(r - 30, 0), 4)
    if c.cflag[99] >= 20:
        local += max(c.cflag[99] - 20, 0) * 2 + 10
    elif c.cflag[99] >= 10:
        local += max(c.cflag[99] - 10, 0)
    local = max(0, min(local, 50))
    if st.rng.rand(150) < local:
        _state_on(ctx, "は大きすぎるダメージによって", "気絶", (250, 180, 50), "した！", KIZETU)
        _kizetu_menu(ctx)


def state_change_kizetu(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_KIZETU, ARG`:208–236。"""
    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[12] & KIZETU:
        return
    if c.cflag[1] == 2:
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(2) == 0:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は", "気絶", (250, 180, 50), "してしまった！", KIZETU)
    _kizetu_menu(ctx)


def state_change_hairan(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_HAIRAN, ARG`:238–263。"""
    st = ctx.state
    c = tc(ctx)
    if t(ctx, c, "妊娠") > 0:
        return
    if c.tcvarn[12] & HAIRAN:
        return
    if c.cflag[1] == 2:
        return
    if is_male(ctx.data, c):
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(2) == 0:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は強制的に", "排卵", (150, 0, 250), "状態にされてしまった！", HAIRAN)


def state_change_hatujou(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_HATUJOU, ARG`:265–286。"""
    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[12] & HATUJOU:
        return
    if c.cflag[1] == 2:
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(2) == 0:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は媚薬の効果で", "発情", (250, 0, 150), "してしまった！", HATUJOU)


def state_change_betobeto(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_BETOBETO, ARG`:288–312。"""
    from .core import BETOBETO

    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[12] & BETOBETO:
        return
    if c.cflag[1] == 2:
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(4) != 0:
        return
    if c.tcvarn[200] > 0:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は粘液で全身が", "べとべと", (0, 250, 150), "になってしまった！", BETOBETO)


def state_change_extraeffect(ctx: Ctx) -> None:
    """`@STATE_CHANGE_EXTRAEFFECT(TCVARn:15)`（:342–359）：TCVARn:14 を設定するのは雑魚／イベント敵のみ。"""
    raise NotImplementedError("エネミー独自の追加効果（STATE_CHANGE_EXTRAEFFECT）は未移植")


def attack_air_flag(ctx: Ctx) -> None:
    """`COM_ATTACK_COMMON.ERB@ATTACK_AIR_FLAG`:433–450。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    if v.get_bit(216, 1) and not v.get_bit(216, 0):
        v[216] = 4
        if t(ctx, c, "有翼") > 0:
            st.tflag[99] += 1
    elif v.get_bit(216, 0) and c.base[22]:
        v.set_bit(216, 1)
        c.base[22] -= 1
        st.tflag[99] += 1
        if t(ctx, c, "空中浮遊") > 0:
            st.tflag[99] -= 1
        if t(ctx, c, "エアマスター") > 0:
            st.tflag[99] += 1


def cheers_enabled(ctx: Ctx) -> bool:
    """`CONFIG_CHECK_EVENT_F(3) > 0`（応援・クズ市民）。"""
    return config_check_event(ctx.state, 3) > 0


def is_akuoti(ctx: Ctx) -> bool:
    return enemy_type_check(ctx.state, "AKUOTI") == 1


def kojo(ctx: Ctx, code: str) -> int:
    return kojo_root(ctx, code)


def state_change_ex(ctx: Ctx, arg: int) -> None:
    """`ヒロイン関連/CHARA_STATE_CHANGE.ERB@STATE_CHANGE_EX, ARG`:54–121（絶頂による恍惚・気絶・腰くだけ）。"""
    from .core import KOSHIKUDAKE, KOUKOTSU, tentacle_access

    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    rand = st.rng.rand
    if c.cflag[1] == 2:
        return
    total = sum(c.abl[i] for i in range(4))  # :59–61 LOCAL:1
    count = 0
    # :63–78 恍惚（GOTO SKIP_1 で飛ばす条件は左から評価。祝福の RAND は `&&` の短絡）
    if not t(ctx, c, "闘争本能") > 0 and not (t(ctx, c, "祝福") > 0 and arg < 100 and rand(2) == 0):
        if (rand(100) < min(arg * arg * 4 + total * 4, 75) or (v[12] & HATUJOU)) and (v[12] & KIZETU) == 0 and (
            v[12] & KOUKOTSU
        ) == 0:
            _state_on_nowait(ctx, "は絶頂の余韻で", "恍惚", (255, 182, 193), "としている！", KOUKOTSU)
            count += 1
    # :81–102 気絶
    if not (t(ctx, c, "祝福") > 0 and arg < 100 and rand(2) == 0):
        name = str(tentacle_access(ctx, "GETNAME"))
        if rand(100) < arg * arg * 8 and (v[12] & KIZETU) == 0 and (v[12] & KOUKOTSU) == 0 and name != "Ｈ触手":
            _state_on_nowait(ctx, "は激しい絶頂によって", "気絶", (250, 180, 50), "した！", KIZETU)
            _kizetu_menu(ctx)
            count += 1
    # :105–118 腰くだけ
    if not (t(ctx, c, "祝福") > 0 and arg < 100 and rand(2) == 0):
        if rand(100) < arg * arg * 12 + 5 and (v[12] & KOSHIKUDAKE) == 0:
            _state_on_nowait(ctx, "は", "腰くだけ", (150, 0, 250), "になってしまった！", KOSHIKUDAKE)
            count += 1
    if count > 0:
        ctx.out.printw()


def _state_on_nowait(ctx: Ctx, head: str, name: str, color: tuple[int, int, int], tail: str, bit: int) -> None:
    """`_state_on` の PRINTW なし版（STATE_CHANGE_EX／DENGEKI は最後にまとめて PRINTW）。"""
    st = ctx.state
    out = ctx.out
    out.print(f"{print_transcallname(st, st.target)}{head}")
    out.set_bold(True)
    out.set_color(color)
    out.print(f"[{name}]")
    out.reset_color()
    out.set_bold(False)
    out.printl(tail)
    tc(ctx).tcvarn[12] |= bit


def state_change_dengeki(ctx: Ctx, arg: int = 100) -> None:
    """`@STATE_CHANGE_DENGEKI(ARG=100)`:125–177。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    rand = st.rng.rand
    count = 0
    if rand(100) > arg:
        return
    if c.cflag[1] == 2:
        return
    skip2 = False
    if t(ctx, c, "生粋の戦士") > 0:  # GOTO SKIP_1（気絶判定を飛ばす）
        pass
    elif t(ctx, c, "祝福") > 0 and rand(2) == 0:  # GOTO SKIP_2（両方飛ばす）
        skip2 = True
    elif v[200] > 0:
        skip2 = True
    elif rand(100) < 10 and (v[12] & KIZETU) == 0:
        _state_on_nowait(ctx, "は電流のショックで", "気絶", (250, 180, 50), "した！", KIZETU)
        _kizetu_menu(ctx)
        count += 1
    if not skip2:  # $SKIP_1（:158）
        if not (t(ctx, c, "祝福") > 0 and rand(2) == 0):
            if rand(100) < 75 and (v[12] & MAHI) == 0:
                _state_on_nowait(ctx, "は全身が", "麻痺", (250, 250, 0), "した！", MAHI)
                count += 1
    if count > 0:
        ctx.out.printw()


def state_change_mahi(ctx: Ctx, arg: int) -> None:
    """`@STATE_CHANGE_MAHI, ARG`:180–203。"""
    st = ctx.state
    c = tc(ctx)
    if c.tcvarn[12] & MAHI:
        return
    if c.cflag[1] == 2:
        return
    if t(ctx, c, "祝福") > 0 and arg < 100 and st.rng.rand(2) == 0:
        return
    if c.tcvarn[200] > 0:
        return
    if st.rng.rand(100) > arg:
        return
    _state_on(ctx, "は全身が", "麻痺", (250, 250, 0), "してしまった！", MAHI)
