"""外衣199：ERB/ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_ACTTENTACLESUIT:309–507。

遊戲規則手翻；純顯示片段及地の文沿catalog，事件／口上沿generator等待。
&&／||短路：reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–555。
TIMES截斷：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916。
落尾RESULT0=0：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
"""
from ..action import kojo_root_gen
from ..chara_common import is_female, is_male, seikaku_check
from ..era import div, times
from .cloth import figure_split
from .core import P_NOTHING, P_NORMAL, P_NASUGAMAMA, P_UKEIRERU, seikaku_hosei_palam
from .ninsin import ninsin_hantei
from .palam import (palam_hosei_pose, palam_hosei_seitaisei, palam_hosei_talent,
                    palam_hosei_poisoning, palam_hosei_random)
from .sexcom import check_holyvirgin, sex_comex


def _text(ctx, line, amount=0, suit_name=""):
    """內嵌文字片段不改變外層RESULT；借用LOCAL／LOCALS顯示原快照。"""
    name = f"MESSAGE_TENTACLE_SUIT_{line}"
    st = ctx.state
    key = (name, 0)
    old = st.temp.locals.get(key)
    name_key = ((name, "LOCALS"), (0,))
    old_name = st.temp.narr.get(name_key)
    result = st.result[0]
    st.temp.locals[key] = amount
    st.temp.narr[name_key] = suit_name
    try:
        yield from ctx.narration.run_event_gen(ctx, name)
    finally:
        if old is None:
            st.temp.locals.pop(key, None)
        else:
            st.temp.locals[key] = old
        if old_name is None:
            st.temp.narr.pop(name_key, None)
        else:
            st.temp.narr[name_key] = old_name
        st.result[0] = result


def act_tentacle_suit(ctx):
    """原文兩項穿戴早退、耐性消耗／事件、COMMON_PALAM結算。"""
    st, c = ctx.state, ctx.state.target_chara
    v = c.tcvarn
    if (c.cflag[1] == 0 and c.cflag[40] != 199) or (c.cflag[1] > 0 and c.cflag[41] != 199):
        st.result[0] = 0
        return
    # :317–323在地の文／口上前取得名稱；後續角色文字變動不重算這份LOCALS。
    suit_name = (c.cstr[8] if c.cflag[1] == 0 and c.cstr[8]
                 else c.cstr[9] if c.cstr[9] else ctx.data.names["ITEM"].get(199, ""))
    eq = c.equip[99 if c.cflag[1] == 0 else 199]
    strength, bonus, mode = (figure_split(eq, n) for n in (2, 3, 4))
    if c.base[2] > 0 and mode != 4 and (mode != 3 or st.rng.rand(100) >= 5):
        cost = 7 + st.rng.rand(5) + strength * 7
        if bonus > 0:
            cost += 2
        if mode in (1, 2, 3):
            cost = times(cost, {1: "0.9", 2: "0.8", 3: "0.5"}[mode])
        c.base[2] = max(c.base[2] - cost, 0)
        yield from _text(ctx, 338, cost)
        if c.base[2] == 0:
            yield from _text(ctx, 341)
        yield from _text(ctx, 342)
    else:
        ctx.out.printl()
        result = sex_comex(ctx, 0, 0, 15)
        local = [div(x * (100 + strength * 20), 100) for x in result] + [0]
        if mode in (1, 2):
            local = [times(x, "1.1" if mode == 1 else "1.2") for x in local]
        # :358 地の文含KOJO_ROOT；用S71事件通道等待，不能同步代答。
        if not (yield from ctx.narration.run_event_gen(ctx, "MESSAGE_SUBEVENT_BATTLE_ACTTENTACLESUIT")):
            yield from kojo_root_gen(ctx, "SUBEVENT_BATTLE_ACTTENTACLESUIT")
        virgin = ctx.data.index_of("TALENT", "処女")
        if v[0] == 0:
            if v[2] not in (P_NOTHING, P_NORMAL, P_NASUGAMAMA, P_UKEIRERU):
                v[2] = P_NORMAL
        elif is_male(ctx.data, c):
            local[1] = 0
        elif v[41] == 1:
            if c.palam[10] >= 500:
                local[1], local[2] = times(local[1], "1.3"), times(local[2], "1.3")
                if c.talent[virgin] == 1 and check_holyvirgin(ctx) == 0:
                    local[10] += 10000
                    c.talent[virgin], c.cflag[206], v[1] = -1, 4, 1
            else:
                v[41] = 0
        elif v[41] == 2:
            if c.talent[virgin] < 1:
                local[1] = times(local[1], "1.5")
            local[2] = times(local[2], "1.5")
        elif v[41] >= 3:
            high = v[41] == 3
            suffix = "_HI" if high else ""
            if c.talent[virgin] < 1 and is_female(ctx.data, c):
                yield from _text(ctx, 395 if high else 426, suit_name=suit_name)
                yield from kojo_root_gen(ctx, "SEX_TENTACLE_SYASEI_VAGINA" + suffix)
                ctx.out.printl()
            yield from _text(ctx, 402 if high else 433, suit_name=suit_name)
            yield from kojo_root_gen(ctx, "SEX_TENTACLE_SYASEI_ANAL" + suffix)
            ctx.out.printl()
            if high:
                if c.talent[virgin] < 1:
                    local[1] *= 2
                local[2] *= 2
                if is_female(ctx.data, c):
                    c.stain[3] |= 4
                c.stain[4] |= 4
            else:
                local[1], local[2] = times(local[1], "1.7"), times(local[2], "1.7")
            if c.talent[virgin] < 1:
                yield from ninsin_hantei(ctx, 2 if high else 1, 3, 200)
            c.exp[ctx.data.index_of("EXP", "精液経験")] += 2 if high else 1
        c.exp[ctx.data.index_of("EXP", "被姦経験")] += 1
        v[41] = -1 if v[0] == 0 else 1 if v[41] == -1 else v[41] + 1
        c.nowex.clear()  # @SUBEVENT_BATTLE_PRECALCRESET:19–20。
        # :466–506刻意用LOCAL索引0–12；不改映射、不補PALAM 10–17偏移。
        for index, value in enumerate(local):
            if value > 0:
                value = palam_hosei_pose(ctx, value)
                value = palam_hosei_seitaisei(ctx, value)
                value = palam_hosei_talent(ctx, index, value)
                value = seikaku_hosei_palam(seikaku_check(ctx.data, c), index, value)
                if index + 10 - 4 in (11, 13, 14):
                    value = palam_hosei_poisoning(ctx, value)
                value = palam_hosei_random(ctx, value)
                if value <= 0:
                    value = 1
                if value > 999999 and index >= 4:
                    value = 999999
            st.temp.common_palam[index] += value
    st.result[0] = 0
