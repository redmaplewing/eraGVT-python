"""S80：原文推導；全新25歲人工資料，不輸出敘事。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.battle.func import act_limit
from eragvt.game.battle import source_check as sc
from tools.sim_adult import adult_data, assert_ages
from test_transformation_parts import make_context
from test_special_equipment import TrackingRng
from test_trans_sex import drive
from eragvt.game.input_request import WaitInputRequest
from eragvt.text import NullNarrationService


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


# COMMON_BATTLE_FUNC.ERB@ACT_LIMIT:275–291：嚴格<11，空中仍RETURN1。
@pytest.mark.parametrize("audience,citizens,turn,distance,air,roll,expected,bounds", [
    (1,1,3,3,0,0,1,[100]), (1,1,3,3,0,10,1,[100]),
    (1,1,3,3,0,11,0,[100]), (1,1,3,3,1,0,1,[100]),
    (0,1,3,3,0,0,0,[]), (1,0,3,3,0,0,0,[]),
    (1,1,2,3,0,0,0,[]), (1,1,3,2,0,0,0,[]),
])
def test_audience(data,audience,citizens,turn,distance,air,roll,expected,bounds):
    ctx = make_context(data)
    st,c = ctx.state,ctx.state.target_chara
    st.flag[72],st.flag[70],st.tflag[30] = audience,citizens,turn
    c.tcvarn[0],c.tcvarn[216] = distance,air
    st.rng = TrackingRng([roll])
    assert act_limit(ctx) == expected
    assert st.rng.bounds == bounds
    assert c.tcvarn[216] == air and st.target == 1


def blood_context(data,boss=1):
    ctx = make_context(data)
    ctx.state.flag[803] |= 1 << 4
    ctx.state.flag[11] = boss
    ctx.state.rng = TrackingRng([])
    return ctx


# SUPART_BLOOD.ERB@SUPART_BLOOD:59–86：四部位、四條互斥分支。
@pytest.mark.parametrize("boss",[1,2,3,4])
@pytest.mark.parametrize("sensitive,abl,talent,expected", [
    (0,5,1,(10,-10,0,1,0)), (1,4,1,(1,0,25421,1,0)),
    (1,5,0,(1,0,0,10,0)), (1,5,1,(1,0,0,1,2)),
    (-1,6,-1,(-1,0,0,-1,2)),
])
def test_blood_parts(data,boss,sensitive,abl,talent,expected):
    ctx = blood_context(data,boss)
    st,c = ctx.state,ctx.state.target_chara
    c.talent[2*boss+98],c.abl[boss-1],c.talent[boss+152] = sensitive,abl,talent
    drive(sc._supart_blood(ctx))
    assert (c.talent[2*boss+98],c.talent[2*boss+99],c.juel[boss-1],c.talent[boss+152],c.nowex[boss-1]) == expected
    assert st.rng.bounds == [] and st.result[0] == 0
    assert st.result[8] == 765 and st.results[8] == "尾格" and st.target == 1
    assert_ages(st)


@pytest.mark.parametrize("boss,slot,delta",[(5,15,3),(6,20,2),(7,14,3),(7,21,2)])
@pytest.mark.parametrize("start",[-2,0,3,5,7])
def test_blood_levels(data,boss,slot,delta,start):
    ctx = blood_context(data,boss)
    c = ctx.state.target_chara
    c.abl[slot] = start
    drive(sc._supart_blood(ctx))
    assert c.abl[slot] == min(start+delta,5)


@pytest.mark.parametrize("enabled,boss",[(False,1),(True,0),(True,-1)])
def test_blood_disabled(data,enabled,boss):
    ctx = blood_context(data,boss)
    if not enabled:
        ctx.state.flag[803] = 0
    before = ctx.state.target_chara.to_json()
    drive(sc._supart_blood(ctx))
    assert ctx.state.target_chara.to_json() == before
    assert ctx.state.rng.bounds == [] and ctx.state.result[0] == 0


# MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_RESCUE_DEADNUM:1741–1810。
@pytest.mark.parametrize("statuses,plants,roll,picked", [
    ([9],[0],0,None), ([1],[1],0,None), ([9],[1],0,1),
    ([9,9],[2,-1],1,2), ([0,9,9],[1,1,1],0,2),
])
def test_discovery(data,statuses,plants,roll,picked):
    ctx = make_context(data)
    st = ctx.state
    ti = lambda n: data.index_of("TALENT",n)
    for i,(status,plant) in enumerate(zip(statuses,plants),1):
        c = st.charas[1] if i==1 else st.add_chara(data,0)
        c.cflag.clear(); c.talent.clear()
        c.cflag[0],c.talent[ti("苗床化")] = status,plant
        c.cflag[35],c.cflag[36] = 10,20
        c.talent[ti("母乳体質")] = 2
    # master即使符合亦排除；候選暫存每次重建。
    st.charas[0].cflag[0],st.charas[0].talent[ti("苗床化")] = 9,1
    st.temp.randchoose[0],st.temp.randchoose[1],st.flag[112] = 1,999,77
    st.rng = TrackingRng([roll])
    drive(sc._rescue_deadnum(ctx))
    assert st.target == 1 and st.result[0] == 0
    assert st.result[8] == 765 and st.results[8] == "尾格"
    if picked is None:
        assert st.flag[112] == 77 and st.rng.bounds == []
    else:
        c = st.charas[picked]
        assert st.flag[112] == picked
        assert [c.cflag[i] for i in (0,20,21,30,31,100,220)] == [-1,0,0,0,0,103,0]
        assert [c.base[i] for i in range(3)] == [1,1,1]
        assert (c.cflag[35],c.cflag[36]) == (310,320)
        assert [c.talent[ti(n)] for n in ("四肢欠損","繁殖袋","母乳体質","苗床化","貧乳","巨乳","淫乳","淫核","淫壷","淫尻")] == [1,1,2,max(plants[picked-1],1),0,5,1,1,1,1]
        assert st.rng.bounds == [sum(s==9 and p!=0 for s,p in zip(statuses,plants))]
    assert_ages(st)


class SideNarration(NullNarrationService):
    """本次原catalog片段照跑；其他敘事Null，保留所有本次輸入。"""
    def __init__(self,catalog):
        self.catalog,self.calls = catalog,[]

    def run_function(self,ctx,name,args=None):
        if name == "MESSAGE_AUDIENCE_INTERFERENCE":
            self.calls.append(name)
            return self.catalog.run_function(ctx,name,args)
        return False

    def run_event_gen(self,ctx,name,args=None,*,waits=False):
        self.calls.append(name)
        if name.startswith(("MESSAGE_BLOOD_","MESSAGE_DISCOVERY_")):
            return (yield from self.catalog.run_event_gen(ctx,name,args,waits=waits))
        return False


@pytest.fixture(scope="module")
def catalog(data):
    from eragvt.narration.service import CatalogNarrationService
    return CatalogNarrationService(default_csv_dir().parent/"ERB",data)


def finish_waits(gen, on_wait=lambda: None):
    count = 0
    try:
        value = next(gen)
        while True:
            assert isinstance(value,WaitInputRequest)
            count += 1
            on_wait()
            value = gen.send(None)
    except StopIteration:
        return count


@pytest.mark.parametrize("fast,expected",[(0,5),(1,3)])
def test_blood_catalog_waits_once(data,catalog,fast,expected):
    ctx = blood_context(data)
    ctx.narration = SideNarration(catalog)
    st,c = ctx.state,ctx.state.target_chara
    st.flag[801] = fast << 3
    states = []
    count = finish_waits(sc._supart_blood(ctx),lambda: states.append(c.talent[100]))
    assert count == expected
    assert states == [0]*(expected-1)+[10]
    assert c.talent[101] == -10 and st.result[8] == 765
    assert not catalog.failures


def test_discovery_catalog_waits_before_recovery(data,catalog):
    ctx = make_context(data,SideNarration(catalog))
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[0],c.talent[data.index_of("TALENT","苗床化")] = 9,1
    st.rng = TrackingRng([0,1,2])
    states = []
    assert finish_waits(sc._rescue_deadnum(ctx),lambda: states.append((c.cflag[0],c.cflag[35]))) == 8
    # :1753,1754,1760,1762,1769,1772,1785,1810；PRINTDATA的兩次RAND保留。
    assert states[:-1] == [(9,0)]*(len(states)-1)
    assert states[-1] == (-1,300)
    assert c.cflag[35] == 300 and st.rng.bounds == [1,3,4]
    assert not catalog.failures


@pytest.mark.parametrize("kind,male,answers,change",[
    ("mtof",1,[0,0,0,0],1), ("ftom",0,[0,0,0,0],10),
    ("normal",1,[3,1,0,1,7,0],11),
])
def test_blood_real_ts_inputs(data,kind,male,answers,change):
    from eragvt.game.battle.func import transform
    ctx = blood_context(data,2)
    st,c = ctx.state,ctx.state.target_chara
    c.talent[data.index_of("TALENT","オトコ")] = male
    if kind != "normal":
        c.talent[data.index_of("TALENT","変身時ＴＳ")] = 1
        # 四種外觀不同才各有原生選單。
        for a,b in ((13,14),(30,31),(32,34),(36,37)):
            c.cstr[a],c.cstr[b] = "黒","赤"
        transform(ctx,1)
    drive(sc._supart_blood(ctx),answers)
    assert c.talent[data.index_of("TALENT","性別変化")] == change
    assert c.talent[102] == 10 and st.target == 1 and st.result[0] == 0
    assert_ages(st)


@pytest.mark.parametrize("akuoti",[False,True])
def test_blood_residual_nowex_message_order(data,akuoti):
    ctx = blood_context(data,8)  # 未定義種類仍有開頭／NOWEX／成就，不捏造數值效果。
    st,c = ctx.state,ctx.state.target_chara
    st.flag[110] = int(akuoti)
    class Trace(NullNarrationService):
        def run_event_gen(self,cx,name,args=None,*,waits=False):
            seen.append(name)
            if False: yield
            return True
    seen=[]; ctx.narration=Trace()
    for i,v in enumerate((1,2,3,2)): c.nowex[i]=v
    drive(sc._supart_blood(ctx))
    expected=[]
    for suffix in ("C","V_HI","B_HI"):
        expected.append("MESSAGE_SEX_ECSTASY_"+suffix)
        if akuoti: expected.append("MESSAGE_OTHER_SEX_ECSTASY_"+suffix)
    assert seen[2:] == expected
    assert [c.nowex[i] for i in range(4)] == [1,2,3,2]


def prepare_side_battle(ctx,mode):
    from test_special_equipment import prepare_equipment_battle
    prepare_equipment_battle(ctx,0 if mode.startswith("audience") else 506)
    st,c = ctx.state,ctx.state.target_chara
    st.flag[11] = 2 if mode=="blood-ts" else 1
    st.flag[850] |= 1 << 14
    st.flag[803] = (1 << 4) if mode in ("blood-on","blood-ts") else 0
    if not mode.startswith("audience"):
        st.flag[13] = 1
    if mode.startswith("discovery"):
        lost=st.add_chara(ctx.data,0)
        lost.cflag.clear(); lost.talent.clear()
        lost.cflag[0]=9
        lost.talent[ctx.data.index_of("TALENT","苗床化")]=1
        if mode=="discovery-on": st.flag[850] &= ~(1 << 14)
    if mode=="blood-ts":
        c.talent[ctx.data.index_of("TALENT","オトコ")]=1
    c.abl[ctx.data.index_of("ABL","レベル")]=1
    for slot in (601,602,661): c.equip[slot]=0


def audience_prestate(st,mode):
    # 人工回合前態；BEGIN TRAIN會清TFLAG，故於首次原生選單建立後設定。
    st.flag[72],st.flag[70],st.tflag[30] = int(mode=="audience-on"),1,3
    st.target_chara.tcvarn[0]=3


@pytest.mark.parametrize("mode",["audience-on","audience-off","blood-on","blood-off","discovery-on","discovery-off"])
def test_real_train_and_web(data,catalog,tmp_path,mode):
    from fastapi.testclient import TestClient
    from eragvt.game.battle.train import run_train
    from eragvt.web import create_app
    svc=SideNarration(catalog)
    app=create_app(data,tmp_path,narration=svc)
    session=app.state.session
    cx=make_context(data,svc)
    session.state,session.out=cx.state,cx.out
    ctx=session._ctx(); st=ctx.state
    prepare_side_battle(ctx,mode)
    session._run_gen(run_train(ctx),lambda: None)
    if mode.startswith("audience"): audience_prestate(st,mode)
    with TestClient(app) as client:
        client.post("/api/input",json={"value":201})
        confirms=0
        while session.input_kind=="wait":
            confirms+=1
            assert confirms<15
            screen=client.get("/api/screen").json()
            client.post("/api/input",json={"value":"","input_token":screen["input_token"]})
        if mode.startswith("audience"):
            assert st.target_chara.cflag[1] == int(mode=="audience-off")
            assert st.flag[13]==3000
        else:
            assert st.tflag[98]==1 and st.flag[700]==0
            assert st.target_chara.talent[100]==(10 if mode=="blood-on" else 0)
            if mode.startswith("discovery"):
                assert st.charas[2].cflag[0]==(-1 if mode=="discovery-on" else 9)
        assert confirms==({"blood-on":5,"discovery-on":8}.get(mode,0))
        assert not catalog.failures
        assert_ages(st)
    session.close()


@pytest.mark.parametrize("air",[0,1])
def test_audience_stops_attack_before_distance_combo(data,catalog,air):
    from eragvt.game.battle.commands import com_attack
    ctx=make_context(data,SideNarration(catalog))
    st,c=ctx.state,ctx.state.target_chara
    audience_prestate(st,"audience-on")
    c.tcvarn[216]=air
    st.rng=TrackingRng([10])
    # COMF3:6–8在ATTACK_AIR_FLAG與連續距離遞增之前RETURN1。
    assert drive(com_attack(ctx,3))==1
    assert st.tflag[30]==3 and c.tcvarn[216]==air
    assert ctx.narration.calls==([] if air else ["MESSAGE_AUDIENCE_INTERFERENCE"])
    assert st.rng.bounds==[100] and st.result[0]==1


def test_jump_palam_victory_wait_chain(data,catalog):
    from eragvt.game.battle.palam import palam_up
    from eragvt.game.battle.core import BeginAfterTrain
    ctx=make_context(data,SideNarration(catalog))
    prepare_side_battle(ctx,"blood-on")
    st,c=ctx.state,ctx.state.target_chara
    st.flag[13],st.flag[700]=0,1
    c.tcvarn[0]=3
    gen=palam_up(ctx)
    assert isinstance(next(gen),WaitInputRequest)
    assert st.tflag[98]==1 and c.talent[100]==0
    count=1
    with pytest.raises(BeginAfterTrain):
        while True:
            assert isinstance(gen.send(None),WaitInputRequest)
            count+=1
            assert count<10
    assert count==5 and c.talent[100]==10


def test_new_fragments_are_display_only(catalog):
    from eragvt.narration.catalog import _TEXT_FRAGMENTS
    from eragvt.narration import nodes as N
    for name in _TEXT_FRAGMENTS:
        if name.startswith(("MESSAGE_BLOOD_","MESSAGE_DISCOVERY_","MESSAGE_AUDIENCE_")):
            assert catalog.catalog.unsupported_reason(name) is None
            body=list(N.iter_stmts(catalog.catalog.get(name).body))
            assert not any(isinstance(n,(N.Assign,N.CallStmt,N.Input)) for n in body)


def test_cannot_reapply_effect_while_waiting(data,catalog,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    svc=SideNarration(catalog)
    app=create_app(data,tmp_path,narration=svc)
    session=app.state.session
    ctx=blood_context(data); session.state,session.out=ctx.state,ctx.out
    st=session.state
    session._run_gen(sc._supart_blood(session._ctx()),lambda: None)
    with TestClient(app) as client:
        for _ in range(5):
            screen=client.get("/api/screen").json()
            assert screen["input_kind"]=="wait"
            body={"value":"","input_token":screen["input_token"]}
            client.post("/api/input",json=body)
            after=st.to_json()
            client.post("/api/input",json=body)
            assert st.to_json()==after
        assert st.target_chara.talent[100]==10
        assert st.target_chara.talent[101]==-10
    session.close()
