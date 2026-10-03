"""S36：市民戰原作固定案例；expected 直接取 ERB 常數及分支。"""

import pytest

from test_narration_s30 import ctx, data, svc
from eragvt.state import FixedRng
from eragvt.game.battle import core, mob
from eragvt.game.battle.citizen import encount_citizen, sex_routine


@pytest.mark.parametrize("people,expected", [(0,5),(1,6),(2,7),(3,3),(12,12)])
def test_encounter(ctx, monkeypatch, people, expected):
    """●イベント戦闘_クズ市民共通.ERB@ENCOUNT_CITIZEN:4–58。"""
    st = ctx.state
    monkeypatch.setattr(core,"tentacle_level",lambda st: 4)
    st.flag[70],st.flag[71],st.flag[72],st.flag[73] = people,0,1,0
    st.tflag[19] = 99
    st.target_chara.tcvarn[9] = 99
    st.result[1],st.results[2] = 77,"保持"
    assert encount_citizen(ctx,6002,"強制麻痺") == 1150
    assert st.savestr[13] == "CITIZEN"
    assert [st.flag[n] for n in (70,71,72,73)] == [0,0,0,expected]
    assert [st.flag[n] for n in (10,11,12,13,14,15,16,17,22)] == [2,1150,expected,expected,500,0,140,0,-1]
    assert st.tflag[0] == -1 and st.tflag[19] == 0
    assert st.target_chara.tcvarn[0] == 0 and st.target_chara.tcvarn[9] == 0
    assert st.temp.turn_limit == 15
    assert core.get_battle_situation(st,"強制麻痺") == 1
    assert st.result[0] == 1150 and st.result[1] == 77 and st.results[2] == "保持"


@pytest.mark.parametrize("key,value", [("HP",1),("SYASEI",500),("SAKUSEI",30),("YUDAN",100),
    ("KOUGEKI",250),("BOUGYO",500),("BINSYOU",150),("CHISEI",10),
    ("SHORT",120),("MIDDLE",120),("LONG",120),("HOLD",180)])
def test_constant_stats(ctx,key,value):
    """CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_HP～HOLD:25–93：不套用等級補正。"""
    ctx.state.flag[73],ctx.state.flag[11],ctx.state.savestr[13] = 5,1150,"CITIZEN"
    assert core.tentacle_access(ctx,key) == value


@pytest.mark.parametrize("roll,expected", [(0,0),(19,0),(20,1),(39,1),(40,11),(59,11),(60,2),(79,2),(80,3),(94,3),(95,9)])
def test_routine(ctx,roll,expected):
    """CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_SEX_ROUTINE:144–200。"""
    st,c = ctx.state,ctx.state.target_chara
    for name in ("オトコ","母乳体質","清純派"):
        c.talent[ctx.data.index_of("TALENT",name)] = 0
    st.temp.cloth[1],st.temp.cloth[3],st.temp.cloth[4] = 0,0,100
    st.rng = FixedRng([roll,73])
    assert sex_routine(ctx) == expected
    assert st.rng.rand(100) == 73


@pytest.mark.parametrize("arg,expected", [(0,77),(1,77),(2,77),(3,77),(4,77)])
def test_reference(ctx,arg,expected):
    """SOURCE_CHECK:1152–1153：TRYCALLFORM 拼 MOB 而原作只有 CITIZEN，保留前值。"""
    ctx.state.flag[11] = 1150
    ctx.state.result[0] = 77
    assert mob.reaction_ref(ctx,arg) == expected


def test_missing_type_is_preserved(ctx):
    """CITIZEN_1.ERB@SEX_TYPE_MOB_901_COM2:405：原作編號是901，1150的COM2不存在。"""
    assert mob.sex_type(1150,2,77) == 77
    assert mob.sex_type(1150,3) == 2
    assert mob.sex_type(1150,11) == 1


def test_citizen_catalog(ctx,svc):
    """CITIZEN_1.ERB@MESSAGE_*；SOURCE_CHECK 的文字片段及既有地の文皆必須可執行。"""
    names = [n for n in svc.catalog.index if n.startswith(("MESSAGE_MOB_1150_","MESSAGE_BATTLE_MOB_1150_","MESSAGE_CITIZEN_"))]
    assert len(names) >= 13
    for name in names:
        assert svc.catalog.unsupported_reason(name) is None, (name,svc.catalog.unsupported_reason(name))


@pytest.mark.parametrize("prison,expected", [(0,0),(1,4)])
def test_defeat(ctx,monkeypatch,prison,expected):
    """BATTLE_COM_AFTER.ERB@SOURCE_CHECK:850–950：設定控制捕獲／釋放，CALL次序不能交換。"""
    from eragvt.game.battle import citizen,rape
    st,c = ctx.state,ctx.state.target_chara
    st.flag[804] = prison << 10
    st.flag[73],st.flag[11],st.savestr[13] = 5,1150,"CITIZEN"
    st.flag[799] = 3
    c.cflag[0] = 0
    before = c.exp[ctx.data.index_of("EXP","被姦経験")]
    calls = []
    def fake_calc(ctx,situation,sao,nakadashi):
        calls.append((situation,sao,nakadashi))
        yield "waiting"
    monkeypatch.setattr(rape,"calc_gangbang",fake_calc)
    gen = citizen.defeat(ctx)
    assert next(gen) == "waiting"
    with pytest.raises(core.BeginAfterTrain): next(gen)
    assert calls == [("戦闘後",5,2 if prison else 1)]
    assert c.cflag[0] == expected and st.tflag[98] == 2
    assert st.flag[799] == (2 if prison else 3)
    assert c.exp[ctx.data.index_of("EXP","被姦経験")] == before+1
    if prison: assert c.cflag[71] == 30


@pytest.mark.parametrize("distance", [0,2])
def test_timeup(ctx,distance):
    """BATTLE_COM_AFTER.ERB@SOURCE_CHECK:1117–1130；不裝觸手服，結果保持0。"""
    from eragvt.game.battle.source_check import _timeup
    ctx.state.flag[73],ctx.state.flag[11] = 5,1150
    ctx.state.target_chara.tcvarn[0] = distance
    ctx.state.tflag[98] = 0
    with pytest.raises(core.BeginAfterTrain): _timeup(ctx)
    assert ctx.state.tflag[98] == 0


@pytest.mark.parametrize("event", [6001,6002])
@pytest.mark.parametrize("result", [0,1,2])
def test_mission(ctx,monkeypatch,event,result):
    """6001/6002*.ERB@EVENT_BATTLE_MISSION_CHECKER_6001/6002:25–35：只有敗北失敗。"""
    from eragvt.game import raid
    ctx.state.flag[45],ctx.state.tflag[98] = event,result
    called = []
    monkeypatch.setattr(raid,"raid_mission_success",lambda c: called.append(1))
    monkeypatch.setattr(raid,"raid_mission_failure",lambda c: called.append(0))
    raid.mission_check(ctx,99)
    assert called == [int(result != 2)]


@pytest.mark.parametrize("n", [0,1,2,3,7,9,11,14])
def test_actual_commands(ctx,n):
    """CITIZEN_1.ERB@*_SEX_ROUTINE:144–200 會選到的指令經共用性攻擊入口。"""
    from eragvt.game.battle.sexcom import sex_comable
    encount_citizen(ctx,6002)
    ctx.state.target_chara.tcvarn[0] = 0
    ctx.state.temp.cloth[1],ctx.state.temp.cloth[3],ctx.state.temp.cloth[4] = 0,0,100
    ctx.state.target_chara.talent[ctx.data.index_of("TALENT","清純派")] = 0
    gen = sex_comable(ctx,n)
    try:
        choice = next(gen)
        for _ in range(20): choice = gen.send(0)
    except StopIteration:
        pass
    else:
        pytest.fail("指令未結束")


@pytest.mark.parametrize("event,outcome", [(6001,"escape"),(6002,"timeout"),(6002,"defeat")])
def test_train_returns_turnend(ctx,event,outcome):
    """BATTLE_TRAIN.ERB@EVENTTRAIN → SOURCE_CHECK → BATTLE_TRAIN_AFTER.ERB@EVENTEND。
    市民逃離走時間切れ；敗北不能清除救援目標標記以外的旗標。
    """
    from eragvt.game.battle import train
    from eragvt.game.action import Step
    st,c = ctx.state,ctx.state.target_chara
    encount_citizen(ctx,event)
    st.flag[804] = 0
    gen = train.run_train(ctx)
    next(gen)
    assert c.tcvarn[0] == 0 and st.temp.turn_limit == 15 and st.flag[700] == 1
    if outcome == "escape":
        c.tcvarn[0] = 2
        st.tflag[1] = 1
    elif outcome == "timeout": st.tflag[0] = 15
    else:
        c.base[0] = c.base[1] = c.base[2] = 0
    for _ in range(50):
        try: gen.send(4 if outcome == "escape" else 11)
        except StopIteration as stop:
            assert stop.value == Step.TURNEND
            break
    else: pytest.fail("戰鬥沒有返回TURNEND")
    assert st.flag[700] == 0
    assert st.tflag[98] == (2 if outcome == "defeat" else 0)


def test_missing_reference_blocks_command(ctx):
    """COMABLE.ERB@COM_ABLE103:991–996：缺 MOB_1150 → CATCH RETURN0。"""
    from eragvt.game.battle.restraint import _com_able_sex
    encount_citizen(ctx,6002)
    assert _com_able_sex(ctx,103,True,(255,0,255))[0] == 0


@pytest.mark.parametrize("roll,supplement,damage", [(0,"強制発情",0),(1,"強制麻痺",0),(2,"",450)])
def test_investigation_situation(ctx,roll,supplement,damage):
    """ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:368–413：CASE1只有顯示，CASE2才扣體力。"""
    from eragvt.game.gather import _citizen_encount_text
    st,c = ctx.state,ctx.state.target_chara
    c.base[0] = 1000
    st.rng = FixedRng([0,roll,73])
    assert _citizen_encount_text(ctx,c.callname) == supplement
    assert c.base[0] == 1000-damage
    assert st.rng.rand(100) == 73


def test_free_action_hook(ctx):
    """PASTIME_ナンパ.ERB@PASTIME_NANPA_RAPE:3086／酒ナンパ:1696 呼叫的原生hook。"""
    from eragvt.game.pastime_nanpa import hook_encount_citizen
    ctx.state.rng = FixedRng([0,73])
    hook_encount_citizen(ctx,6001)
    assert ctx.state.flag[45] == 6001 and ctx.state.flag[73] == 5
    assert ctx.state.target_chara.tcvarn[12] & core.HATUJOU
    assert ctx.state.rng.rand(100) == 73


@pytest.mark.parametrize("turn,hp,people,config,forbidden,expected", [
    (7,100,0,0,False,0),(8,100,0,0,False,1),(7,50,0,0,False,1),
    (1,100,0,1,False,1),(1,100,1,1,False,0),(8,100,0,0,True,0)])
def test_retreat(ctx,turn,hp,people,config,forbidden,expected):
    """COMMON_BATTLE_FUNC.ERB@CHECK_CAN_RETREAT_F:396–417。"""
    from eragvt.game.battle.func import check_can_retreat
    st,c = ctx.state,ctx.state.target_chara
    st.flag[73],st.flag[70],st.tflag[0] = 5,people,turn
    st.flag.set_bit(802,3,bool(config))
    c.tcvarn[0] = 2
    c.maxbase[0] = c.maxbase[1] = 100
    c.base[0],c.base[1] = hp,100
    if forbidden: core.add_battle_situation(st,"撤退不可")
    assert check_can_retreat(ctx) == expected


def test_forecast_static_local(ctx):
    """FORECAST.ERB@INT_EVAL:409–426；VariableLocal.cs:24–29、70–71：函式LOCAL保留。"""
    from eragvt.game.battle.enemy import int_eval
    st = ctx.state
    st.flag[73] = 5
    core.set_local(st,"INT_EVAL",0,40)
    st.rng = FixedRng([0,73])  # 市民不抽敵方補正，只抽最後權重池。
    int_eval(ctx,100,100)
    assert core.get_local(st,"INT_EVAL",0) == 40
    assert st.rng.rand(100) == 73
