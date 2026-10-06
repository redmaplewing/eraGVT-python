"""S80：共用戰鬥側事件；原文狀態手翻，純顯示沿catalog。

ERB/ゲーム内_戦闘処理/SUPART_BLOOD.ERB@SUPART_BLOOD:1–177。
ERB/地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_RESCUE_DEADNUM:1739–1810。
落尾清RESULT0：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
其餘RESULT保留：reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740。
"""
from ..action import config_check_screen
from ..chara_common import charatalent, is_female, is_male
from ..tentacle import enemy_type_check
from .core import add_randchoose, choicecount, clear_randchoose, randchoose_f, config_check_balance


def _text(ctx, name, local=0):
    """內嵌顯示不另造CALL的RESULT副作用，LOCAL值只提供原文顯示。"""
    st = ctx.state
    key = (name, 0)
    saved, result = st.temp.locals.get(key), st.result[0]
    st.temp.locals[key] = local
    try:
        yield from ctx.narration.run_event_gen(ctx, name, waits=True)
    finally:
        if saved is None:
            st.temp.locals.pop(key, None)
        else:
            st.temp.locals[key] = saved
        st.result[0] = result


def rescue_deadnum(ctx):
    st, data = ctx.state, ctx.data
    ti = lambda name: data.index_of("TALENT",name)
    clear_randchoose(st)
    st.result[0] = 0
    for index in range(1, st.charanum):
        c = st.charas[index]
        if c.cflag[0] == 9 and c.talent[ti("苗床化")]:
            add_randchoose(st,index)
    if choicecount(st) == 0:
        return
    yield from _text(ctx, "MESSAGE_DISCOVERY_START")
    st.flag[112] = randchoose_f(st)
    yield from _text(ctx, "MESSAGE_DISCOVERY_BODY")
    # :1785 FORCEWAIT之後才更動角色；不刪角色，不變更TARGET。
    c = st.charas[st.flag[112]]
    for slot,value in ((0,-1),(20,0),(21,0),(30,0),(31,0),(100,103),(220,0)):
        c.cflag[slot] = value
    for slot in range(3):
        c.base[slot] = 1
    for name in ("四肢欠損","繁殖袋"):
        c.talent[ti(name)] = 1
    for name in ("母乳体質","苗床化"):
        c.talent[ti(name)] = max(c.talent[ti(name)],1)
    c.cflag[35] += 300
    c.cflag[36] += 300
    for name,value in (("貧乳",0),("巨乳",5),("淫乳",1),("淫核",1),("淫壷",1),("淫尻",1)):
        c.talent[ti(name)] = value
    yield from _text(ctx, "MESSAGE_DISCOVERY_END")
    st.result[0] = 0


def supart_blood(ctx):
    st, data = ctx.state, ctx.data
    c = st.target_chara
    tt = lambda name: c.talent[data.index_of("TALENT",name)]
    if config_check_balance(st,4) > 0 and st.flag[11] > 0:
        yield from _text(ctx,"MESSAGE_BLOOD_3")
        yield from _text(ctx,"MESSAGE_BLOOD_5" if config_check_screen(st,3)==0 else "MESSAGE_BLOOD_8")
        if st.flag[11] < 5:
            yield from _text(ctx,"MESSAGE_BLOOD_13")
            from ..trans_sex import ts_mtof, ts_ftom, ts_normal
            if st.flag[11] == 2 and is_female(data,c) and tt("変身時ＴＳ") > 0 and c.cflag[1] > 0:
                yield from _text(ctx,"MESSAGE_BLOOD_18")
                yield from ts_mtof(ctx,st.target)
                yield from _text(ctx,"MESSAGE_BLOOD_27")
            elif st.flag[11] == 2 and is_male(data,c) and tt("変身時ＴＳ") > 0 and c.cflag[1] > 0:
                yield from _text(ctx,"MESSAGE_BLOOD_32")
                yield from ts_ftom(ctx,st.target)
                yield from _text(ctx,"MESSAGE_BLOOD_41")
            elif st.flag[11] == 2 and is_male(data,c) and charatalent(data,c,0,"オトコ") > 0:
                yield from _text(ctx,"MESSAGE_BLOOD_46")
                yield from ts_normal(ctx,st.target)
                yield from _text(ctx,"MESSAGE_BLOOD_55")
            boss = st.flag[11]
            local = 2*boss+98
            st.temp.locals[("SUPART_BLOOD",0)] = local
            if c.talent[local] == 0:
                c.talent[local+1] -= 10
                c.talent[local] += 10
                yield from _text(ctx,"MESSAGE_BLOOD_63",local)
            elif c.abl[boss-1] < 5:
                c.juel[boss-1] += 25421
                yield from _text(ctx,"MESSAGE_BLOOD_68")
            elif c.talent[boss+152] == 0 and c.abl[boss-1] >= 5:
                c.talent[boss+152] += 10
                suffix = {1:"INKAKU",2:"INTUBO",3:"INJIRI",4:"INNYUU"}[boss]
                yield from ctx.narration.run_event_gen(ctx,"MESSAGE_GETTALENT_"+suffix,waits=True)
            else:
                c.nowex[boss-1] = 2
                yield from _text(ctx,"MESSAGE_BLOOD_85")
        elif st.flag[11] in (5,6,7):
            boss = st.flag[11]
            start,end,changes = {
                5:(89,96,((15,3),)), 6:(99,105,((20,2),)), 7:(108,117,((14,3),(21,2)))
            }[boss]
            yield from _text(ctx,f"MESSAGE_BLOOD_{start}")
            for slot,delta in changes:
                c.abl[slot] = min(c.abl[slot]+delta,5)
            yield from _text(ctx,f"MESSAGE_BLOOD_{end}")
        st.temp.locals[("SUPART_BLOOD",0)] = 0
        # :123–174不清NOWEX；逐部位讀原殘值，地文／口上可等待。
        for index,part in enumerate("CVAB"):
            value = c.nowex[index]
            if value in (1,2):
                suffix = part + ("_HI" if value==2 else "")
                yield from ctx.narration.run_event_gen(ctx,"MESSAGE_SEX_ECSTASY_"+suffix,waits=True)
                if enemy_type_check(st,"AKUOTI") == 1:
                    yield from ctx.narration.run_event_gen(ctx,"MESSAGE_OTHER_SEX_ECSTASY_"+suffix,waits=True)
        from ..achievements import get_state_ablup
        get_state_ablup(ctx,st.target)
    st.result[0] = 0
