"""S66：CHARA_MAKE.ERB@CHARA_MAKE_MAIN:148–200、323–359 原文 expected。"""
import pytest

from tools.sim_adult import adult_data, assert_ages
from eragvt.data import load_game_data, default_csv_dir
from eragvt.state import GameState, GameRng
from eragvt.state.savefile import GlobalStore
from eragvt.state.constants import GameMode, MODE_OPTIONS, GameOption
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game.action import Ctx
from eragvt.game.creation_menu import creation_menu


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st=GameState.new(data,GameRng(66));st.swap_chara(0,1);st.del_chara(1)
    for _ in range(3):st.add_chara(data,0)
    st.flag[8]=3
    return Ctx(st,data,TextOutput(),NullNarrationService(),GlobalStore())


def buttons(ctx):
    return {v for line in ctx.out.lines for _,v in line.buttons}


# 原文逐條優先序：0→1→3→4→9→0；無權限則略過，SOLO略3。
@pytest.mark.parametrize('unlocks,sequence', [
    ((),[0]),((258,),[1,0]),((262,),[3,0]),((278,),[4,0]),((212,),[9,0]),
    ((258,262),[1,3,0]),((258,278),[1,4,0]),((258,212),[1,9,0]),
    ((262,278),[3,4,0]),((262,212),[3,9,0]),((278,212),[4,9,0]),
    ((258,262,278),[1,3,4,0]),((258,262,212),[1,3,9,0]),
    ((258,278,212),[1,4,9,0]),((262,278,212),[3,4,9,0]),
    ((258,262,278,212),[1,3,4,9,0]),
])
def test_state_unlock_cycles(ctx,unlocks,sequence):
    for k in unlocks:ctx.globals.mem.global_[k]=1
    c=ctx.state.charas[2];exp=ctx.data.index_of('EXP','陥落経験')
    c.exp[exp]=7;c.cflag[41]=200;c.cflag[71]=11
    others=[x.to_json() for x in (ctx.state.charas[0],ctx.state.charas[1],ctx.state.charas[3])]
    before=ctx.state.rng.snapshot();ctx.state.target=3
    g=creation_menu(ctx);next(g)
    for expected in sequence:
        g.send(502)
        assert c.cflag[0]==expected
        assert c.exp[exp]==7+(expected==3)
        label={0:' ― ',1:'幽閉',3:'悪堕ち',4:'監禁',9:'死亡'}[expected]
        assert any(f'[502][{label}]' in l.text for l in ctx.out.lines[-20:])
    assert c.cflag[41]==(401 if 262 in unlocks else 200)
    assert c.cflag[71]==(30 if 278 in unlocks else 11)
    assert [x.to_json() for x in (ctx.state.charas[0],ctx.state.charas[1],ctx.state.charas[3])]==others
    assert ctx.state.target==3 and ctx.state.rng.snapshot()==before


@pytest.mark.parametrize('before,expected,exp_delta',[(0,0,0),(1,0,0),(2,2,0),(3,0,-1),(4,0,0),(9,0,0),(-1,-1,0),(999,999,0)])
def test_existing_state_without_unlocks(ctx,before,expected,exp_delta):
    c=ctx.state.charas[1];c.cflag[0]=before;c.cflag[41]=200;c.cflag[71]=23
    exp=ctx.data.index_of('EXP','陥落経験');c.exp[exp]=0
    g=creation_menu(ctx);next(g);g.send(501)
    assert c.cflag[0]==expected and c.exp[exp]==exp_delta
    assert c.cflag[41]==(401 if before==3 else 200) and c.cflag[71]==23


@pytest.mark.parametrize('free,solo,unlocks,sequence',[
    (False,True,(262,),[0]),(False,True,(258,262,278,212),[1,4,9,0]),
    (True,False,(),[1,3,4,9,0]),(True,True,(),[1,4,9,0]),
])
def test_state_mode_options(ctx,free,solo,unlocks,sequence):
    ctx.state.flag[0]=(int(free)<<GameOption.NO_ACHIEVEMENT_END)|(int(solo)<<GameOption.SOLO)
    for k in unlocks:ctx.globals.mem.global_[k]=-1  # 非零權限，不限正值。
    g=creation_menu(ctx);next(g)
    for expected in sequence:
        g.send(501);assert ctx.state.charas[1].cflag[0]==expected


@pytest.mark.parametrize('mode,clears,allowed',[
    (GameMode.NORMAL,(0,0,0),False),(GameMode.NORMAL,(1,0,0),True),
    (GameMode.HARDCORE,(0,1,0),True),(GameMode.SURVIVAL,(0,0,1),True),
    (GameMode.FREEPLAY,(0,0,0),False),(GameMode.SANDBOX,(0,0,0),True),
    (GameMode.INSTANT,(0,0,0),False),(GameMode.INSTANT,(0,1,0),True),
    (GameMode.SOLO,(1,1,1),False),(GameMode.NORMAL,(-1,1,0),False),
])
def test_count_visibility_and_manual_permission(ctx,mode,clears,allowed):
    ctx.state.flag[0]=MODE_OPTIONS[mode]
    for k,v in zip((100,101,102),clears):ctx.globals.mem.global_[k]=v
    g=creation_menu(ctx);next(g);assert (300 in buttons(ctx))==allowed
    ctx.out.clearline(len(ctx.out.lines));g.send(300)
    assert ({2,3,4,5,6,99}<=buttons(ctx))==allowed
    if allowed:
        title='周回クリアボーナス：' if sum(clears)>0 else 'サンドボックス：'
        assert any(title in l.text for l in ctx.out.lines)
        g.send(99)
    assert ctx.state.charanum==4 and ctx.state.flag[8]==3


@pytest.mark.parametrize('count',range(2,7))
def test_count_resize_preserves_prefix_and_indices(ctx,count):
    """ADD/DEL不改TARGET、ASSI或RESULT：VariableEvaluator.cs:1026–1067；Instraction.Child.cs:934–965。"""
    ctx.globals.mem.global_[100]=1
    st=ctx.state;st.target=3;st.assi=3;st.result[1]=88;st.results[0]='殘值';st.results[1]='保留'
    old=list(st.charas);snap=[c.to_json() for c in old];rng=st.rng.snapshot()
    g=creation_menu(ctx);next(g);g.send(300);g.send(count)
    assert st.charanum==count+1 and st.flag[8]==count
    assert st.charas[:min(4,count+1)]==old[:min(4,count+1)]
    assert [c.to_json() for c in st.charas[:min(4,count+1)]]==snap[:min(4,count+1)]
    assert all(c.no==0 and c.callname=='汎用キャラ' and c.cflag[240]==0 for c in st.charas[4:])
    assert (st.target,st.assi,st.result[0],st.result[1],st.results[0],st.results[1])==(3,3,count,88,'殘值','保留')
    assert st.rng.snapshot()==rng
    g.send(300);g.send(99);assert st.charanum==count+1


def test_count_invalid_cancel_and_stale_indices(ctx):
    ctx.globals.mem.global_[100]=1
    g=creation_menu(ctx);next(g);g.send(300)
    for v in (-1,0,1,7,1000):
        n=len(ctx.out.lines);g.send(v)
        assert len(ctx.out.lines)==n+1 and ctx.state.charanum==4 and ctx.state.result[0]==v
    g.send(99);g.send(300);g.send(6);g.send(506)
    g.send(300);g.send(2)
    for v in (503,506,500,507):
        n=len(ctx.out.lines);g.send(v);assert len(ctx.out.lines)==n+1
    assert ctx.state.charanum==3


def test_sandbox_solo_count_exception(ctx):
    # MAIN:323：NO_ACHIEVEMENT_END位元在SOLO排除條件外。
    ctx.state.flag[0]=(1<<GameOption.NO_ACHIEVEMENT_END)|(1<<GameOption.SOLO)
    g=creation_menu(ctx);next(g);assert 300 in buttons(ctx)
    g.send(300);g.send(6);assert ctx.state.charanum==7


@pytest.mark.parametrize('status_choice,expected_bonus',[(None,7),(501,1),(502,2)])
def test_status_overwrites_main_arg_for_csv_bonus(ctx,status_choice,expected_bonus):
    """MAIN:149 ARG=角色索引，後續:203傳給FIRSTSETTING_CHARA_MAIN；該函式:323加bonus*10。"""
    g=creation_menu(ctx,bonus=7);next(g)
    if status_choice is not None:g.send(status_choice)
    g.send(1);c=ctx.state.charas[1];point=ctx.data.index_of('PALAM','修練P');before=c.juel[point]
    g.send(999);g.send(99)
    assert c.juel[point]==before+expected_bonus*10
    g.send(99)


@pytest.mark.parametrize('preset',[0,1])
@pytest.mark.parametrize('second_state',[3,4])
def test_web_count_and_initial_states_to_shop(data,tmp_path,preset,second_state):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(66),narration=NullNarrationService())
    s=app.state.session
    for k in (100,258,262,278,212):s.globals.mem.global_[k]=1
    s.globals.save()
    client=TestClient(app)
    def send(v):
        response=client.post('/api/input',json={'value':v});assert response.status_code==200
        assert_ages(s.state);return response.json()
    for v in (0,preset,300,99,300,6,501,502,502):send(v)
    if second_state==4:send(502)
    for v in (503,503,503,503,300,5,300,99):send(v)
    assert [c.cflag[0] for c in s.state.charas[1:]]==[1,second_state,9,0,0]
    for v in (1000,1):screen=send(v)
    assert screen['phase']=='shop' and s.state.charanum==6 and s.state.flag[8]==5
    assert [c.cflag[0] for c in s.state.charas[1:]]==[1,second_state,9,0,0]
    assert all(c.callname!='汎用キャラ' and c.cflag[240]>0 for c in s.state.charas[1:])


def test_succession_creation_count_and_state(data,tmp_path):
    """SUCCESSION.ERB@SUCCESSION:1491–1560：引繼先分配角色／點數，再進共用主製作。"""
    from eragvt.game.session import GameSession
    from eragvt.game.succession import succession_gen
    from eragvt.game.action import Step
    s=GameSession(data,tmp_path,rng=GameRng(66),narration=NullNarrationService())
    for value in (0,0,1000,1):s.input(value)
    st=s.state;st.flag[854]=1;old=st.charas[2]
    s.globals.mem.global_[100]=s.globals.mem.global_[258]=1;s.globals.save()
    ctx=Ctx(st,data,TextOutput(),NullNarrationService(),s.globals)
    g=succession_gen(ctx,1);next(g)
    for value in (0,2,999,999,1,0):g.send(value)
    assert st.charas[1] is old and st.charanum==4
    for value in (300,6,300,2,501,300,99):g.send(value)
    assert st.charas[1] is old and st.charanum==3 and st.charas[1].cflag[0]==1
    g.send(1000)
    with pytest.raises(StopIteration) as done:g.send(1)
    assert done.value.value==Step.SHOP
    assert st.charanum==3 and st.charas[1].cflag[0]==1
    assert_ages(st)
