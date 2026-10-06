"""市民戰：既有 ERB 規則的手工轉換，顯示沿用原文 catalog。"""

from ..action import Ctx
from ..chara_common import is_male
from . import core


def encount_citizen(ctx: Ctx, event: int = 0, supplement: str = "") -> int:
    """ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_クズ市民共通.ERB@ENCOUNT_CITIZEN:4–58。"""
    from .cloth import cloth_battle_sethp, refresh_cloth_data
    from .func import state_change_hatujou

    st,f = ctx.state,ctx.state.flag
    st.savestr[13] = "CITIZEN"
    if event > 0:
        core.tc(ctx).tcvarn.clear()
        st.tflag.clear()
        st.tflag[0] = -1
        cloth_battle_sethp(ctx)
        refresh_cloth_data(ctx)
        f[45] = event
        # 6001/6002 クズ市民の*.ERB@EVENT_BATTLE_EXEC_6001/6002:4–23。
        if event in (6001,6002):
            ctx.out.drawline()
            if event == 6001:
                state_change_hatujou(ctx,100)
            st.temp.turn_limit = 15
            core.add_battle_situation(st,"先制無し,支援無効,レイプなし," + (supplement+"," if event == 6002 else ""))
    f[10] = 2
    f[73] += f[70]+f[71]
    f[70] = f[71] = f[72] = 0
    if f[73] < 3:
        f[73] += 5
    f[11] = 1150
    f[12] = f[13] = f[73]
    f[14],f[15] = int(access(ctx,"SYASEI")),0
    f[16],f[17] = int(access(ctx,"YUDAN"))+core.tentacle_level(st)*10,0
    f[22] = -1
    st.result[0] = 1150
    return 1150


def access(ctx: Ctx, key: str):
    """ERB/ゲーム内_戦闘処理/触手データ/クズ市民/CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_*:10–137。"""
    st = ctx.state
    st.results[0] = f"【エラー：{st.savestr[13]}_{st.flag[11]}に対するTENTACLE_ACCESS('{key}')関数失敗】"
    if key in ("NAME","GETNAME"):
        st.results[0] = "クズ市民"
        st.result[0] = 0
        if key == "NAME":
            ctx.out.print(st.results[0])
            return ""
        return st.results[0]
    if key == "ATTACK_ROUTINE":
        roll = st.rng.rand(100)
        core.set_local(st,"TENTACLE_CITIZEN_1150_ATTACK_ROUTINE",0,roll)
        st.result[0] = 2 if roll < 45 else 0
        return st.result[0]
    st.result[0] = {"HP":1,"SYASEI":500,"SAKUSEI":30,"YUDAN":100,"KOUGEKI":250,
            "BOUGYO":500,"BINSYOU":150,"CHISEI":10,"SHORT":120,"MIDDLE":120,"LONG":120,"HOLD":180}[key]
    return st.result[0]


def sex_routine(ctx: Ctx) -> int:
    """ERB/ゲーム内_戦闘処理/触手データ/クズ市民/CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_SEX_ROUTINE:144–200。"""
    from .sexcom import check_holyvirgin
    st,c = ctx.state,core.tc(ctx)
    roll = st.rng.rand(100)
    core.set_local(st,"TENTACLE_CITIZEN_1150_SEX_ROUTINE",0,roll)
    covered = st.temp.cloth[1] > 90 or st.temp.cloth[3] >= st.temp.cloth[4]
    if roll < 15 and core.t(ctx,c,"母乳体質"):
        return 14 if covered else 7 if core.is_hole(ctx) else 1
    if roll < 20: return 0
    if roll < 40: return 14 if covered else 1
    if roll < 60: return 11 if core.is_hole(ctx) else 1
    if roll < 80: return 14 if covered else 1 if is_male(ctx.data,c) else 2
    # 原作 TCVAR:12 非 TCVARn；內建 TCVAR 未曾被原作寫入，BEGIN TRAIN 清零：
    # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1458–1460。
    if (roll < 95 or (st.tflag[20] == 3 and roll < 90)) and check_holyvirgin(ctx) == 0:
        return 14 if covered else 1 if is_male(ctx.data,c) else 3
    return 9


def defeat(ctx: Ctx):
    """ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:850–950。

    顯示片段直接抽原文；SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_RAPED_CITIZEN:55–65。
    """
    from ..action import config_check_prison
    from .mob import message
    from .palam import palam_cal
    from .rape import calc_gangbang

    st,c = ctx.state,core.tc(ctx)
    st.tflag[98] = 2
    message(ctx,"MESSAGE_CITIZEN_DEFEAT")
    message(ctx,"MESSAGE_SUBEVENT_BATTLE_RAPED_CITIZEN")
    c.exp[ctx.data.index_of("EXP","被姦経験")] += 1
    c.nowex.clear()
    yield from palam_cal(ctx,*(core.get_local(st,"SUBEVENT_BATTLE_RAPED_CITIZEN",i) for i in range(12)))
    if config_check_prison(st,10):
        yield from calc_gangbang(ctx,"戦闘後",5,2)
        message(ctx,"MESSAGE_CITIZEN_CAPTURE")
        # :882 的 IF 1==0 短路，不抽 RAND(24)。
        message(ctx,"MESSAGE_CITIZEN_CAPTURE_END")
        message(ctx,"MESSAGE_CITIZEN_HIACED",[st.target,"男たち","脅迫"])
        ctx.out.reset_color()
        c.cflag[0],c.cflag[71] = 4,30
    else:
        message(ctx,"MESSAGE_CITIZEN_RELEASE")
        yield from calc_gangbang(ctx,"戦闘後",5,1)
    ctx.out.printl()
    if c.cflag[0] in (1,9,4):
        st.flag[799] -= 1
    raise core.BeginAfterTrain()
