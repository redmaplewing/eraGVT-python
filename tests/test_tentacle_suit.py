"""S75：全新人工25歲；expected由SUBEVENT_BATTLEE原文推導。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.battle import source_check as sc
from eragvt.text import NullNarrationService
from tools.sim_adult import adult_data, assert_ages
from test_special_equipment import TrackingRng, prepare_equipment_battle
from test_transformation_parts import make_context


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


def suit_context(data, form=0, equipment=0, resistance=100, rolls=()):
    ctx = make_context(data)
    st, c = ctx.state, ctx.state.target_chara
    c.cflag[1] = form
    c.cflag[40 if form == 0 else 41] = 199
    c.equip[99 if form == 0 else 199] = equipment
    c.base[2] = resistance
    c.maxbase[2] = 100
    st.rng = TrackingRng(rolls)
    return ctx


def finish(ctx):
    from eragvt.game.battle.tentacle_suit import act_tentacle_suit
    with pytest.raises(StopIteration):
        next(act_tentacle_suit(ctx))
    assert ctx.state.target == 1
    assert ctx.state.result[0] == 0
    assert ctx.state.results[8] == "尾格"
    assert_ages(ctx.state)


# BATTLE_COM_AFTER.ERB@SOURCE_CHECK:448–454，隔離下游衣裝算法以觀察LOCAL:1。
@pytest.mark.parametrize("form", [0, 1, 2])
@pytest.mark.parametrize("garment,digit,expected", [(199,0,0),(199,1,210),(100,0,210)])
def test_motion_mask(data, monkeypatch, form, garment, digit, expected):
    ctx = suit_context(data, form, digit)
    c = ctx.state.target_chara
    c.cflag[40 if form == 0 else 41] = garment
    c.tcvarn[20 if form == 0 else 22] = -1
    c.tcvarn[24] = -1
    c.abl[data.index_of("ABL", "Ｃ感覚")] = 7
    ctx.state.temp.selectcom = 1
    monkeypatch.setattr(sc, "cloth_check", lambda *_: 0)
    monkeypatch.setattr(sc, "cloth_battle_hosei", lambda *_: 0)
    monkeypatch.setattr(sc, "is_penis", lambda *_: False)
    sc._motion_palam(ctx)
    assert ctx.state.temp.common_palam[0] == expected


# SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_ACTTENTACLESUIT:325–342。
@pytest.mark.parametrize("form", [0, 1, 2])
@pytest.mark.parametrize("equipment,start,rolls,end,bounds", [
    (0,100,[0],93,[5]), (0,100,[4],89,[5]),
    (120,100,[4],73,[5]), (1120,100,[4],76,[5]),
    (2120,100,[4],79,[5]), (3120,100,[5,4],87,[100,5]),
    (3120,1,[99,0],0,[100,5]), (0,1,[0],0,[5]),
    (90,100,[4],26,[5]),
    (-90,100,[0],156,[5]), (9000,100,[0],93,[5]),
])
def test_resistance_cost(data, form, equipment, start, rolls, end, bounds):
    ctx = suit_context(data, form, equipment, start, rolls)
    c = ctx.state.target_chara
    c.nowex[3] = 72
    c.tcvarn[41] = 9
    finish(ctx)
    assert c.base[2] == end
    assert c.nowex[3] == 72 and c.tcvarn[41] == 9
    assert ctx.state.rng.bounds == bounds
    assert ctx.state.result[8] == 765


@pytest.mark.parametrize("form", [0,1,2])
def test_unworn_returns_without_rng(data, form):
    ctx = suit_context(data,form)
    c = ctx.state.target_chara
    c.cflag[40 if form==0 else 41] = 100
    c.cflag[41 if form==0 else 40] = 199
    finish(ctx)
    assert c.base[2] == 100 and ctx.state.rng.bounds == []
    assert ctx.state.result[8] == 765


# SOURCE_CHECK:449–454的兩個獨立bit；-1才代表不可破壞，0/1不算。
@pytest.mark.parametrize("form", [0,1,2])
@pytest.mark.parametrize("digit,outer,inner,noinner,expected", [
    (0,-1,-1,1,(0,660)), (1,-1,-1,1,(210,165)),
    (1,-1,0,0,(0,165)), (1,-1,0,1,(210,165)),
    (1,0,-1,0,(210,660)), (1,0,0,1,(0,660)),
    (1,1,1,1,(0,660)), (-1,-1,-1,1,(210,165)),
])
def test_motion_durability_bits(data,monkeypatch,form,digit,outer,inner,noinner,expected):
    ctx = suit_context(data,form,digit)
    st,c = ctx.state,ctx.state.target_chara
    c.tcvarn[20 if form==0 else 22],c.tcvarn[24] = outer,inner
    st.temp.cloth[0] = noinner
    c.palam[13] = 2000
    c.abl[data.index_of("ABL","Ｃ感覚")] = c.abl[data.index_of("ABL","Ｂ感覚")] = 7
    st.temp.selectcom = 1
    monkeypatch.setattr(sc,"cloth_check",lambda *_: 0)
    monkeypatch.setattr(sc,"cloth_battle_hosei",lambda *_: 0)
    monkeypatch.setattr(sc,"is_penis",lambda *_: False)
    sc._motion_palam(ctx)
    assert tuple(st.temp.common_palam[i] for i in (0,3)) == expected


@pytest.fixture
def unit_effect(monkeypatch):
    """只隔離既有相依，核對本函式的LOCAL→補正呼叫次序與參數。"""
    from eragvt.game.battle import tentacle_suit as suit
    calls = []
    def sex(cx, *args):
        calls.append(("sex",args))
        values = [100,101,103,100,100,100,100,100,100,100,100,100]
        cx.state.set_result_x(*values)
        return values
    monkeypatch.setattr(suit,"sex_comex",sex)
    for name in ("palam_hosei_pose","palam_hosei_seitaisei","palam_hosei_poisoning","palam_hosei_random"):
        def identity(cx,value,_name=name):
            calls.append((_name,value))
            return value
        monkeypatch.setattr(suit,name,identity)
    monkeypatch.setattr(suit,"palam_hosei_talent",lambda cx,index,value: value)
    monkeypatch.setattr(suit,"seikaku_hosei_palam",lambda char,index,value: value)
    def pregnancy(cx,*args):
        calls.append(("pregnancy",args))
        return 0
        yield
    monkeypatch.setattr(suit,"ninsin_hantei",pregnancy)
    return calls


# SUBEVENT_BATTLEE.ERB:325短路；:346–355加成先整除、再TIMES。
@pytest.mark.parametrize("form", [0,1,2])
@pytest.mark.parametrize("equipment,resistance,rolls,expected,bounds", [
    (0,0,[],(101,103),[]), (0,-1,[],(101,103),[]),
    (4000,100,[],(101,103),[]), (3000,100,[4],(101,103),[100]),
    (3000,0,[],(101,103),[]), (1020,0,[],(155,158),[]),
    (2020,0,[],(169,172),[]), (90,0,[],(282,288),[]),
])
def test_event_trigger_and_scaling(data,unit_effect,form,equipment,resistance,rolls,expected,bounds):
    ctx = suit_context(data,form,equipment,resistance,rolls)
    c = ctx.state.target_chara
    c.tcvarn[0],c.tcvarn[41] = 1,0
    c.nowex[3] = 72
    ctx.state.result[20] = 345
    finish(ctx)
    assert tuple(ctx.state.temp.common_palam[i] for i in (1,2)) == expected
    assert c.base[2] == resistance and c.tcvarn[41] == 1
    assert c.nowex[3] == 0 and ctx.state.result[20] == 345
    assert ctx.state.rng.bounds == bounds
    assert unit_effect[0] == ("sex",(0,0,15))
    assert sum(x[0]=="palam_hosei_poisoning" for x in unit_effect) == 3


# :359–460；mode4強制事件，正耐性不會阻止，潤滑門檻500。
@pytest.mark.parametrize("stage,virgin,lub,male,expected,next_stage,lost,semen,stains,preg", [
    (-1,0,0,0,(101,103),1,False,0,(0,0),None),
    (0,0,0,0,(101,103),1,False,0,(0,0),None),
    (1,1,499,0,(101,103),1,False,0,(0,0),None),
    (1,1,500,0,(131,133),2,True,0,(0,0),None),
    (1,2,500,0,(131,133),2,False,0,(0,0),None),
    (1,0,500,0,(131,133),2,False,0,(0,0),None),
    (2,1,0,0,(101,154),3,False,0,(0,0),None),
    (2,0,0,0,(151,154),3,False,0,(0,0),None),
    (3,1,0,0,(101,206),4,False,2,(4,4),None),
    (3,0,0,0,(202,206),4,False,2,(4,4),(2,3,200)),
    (4,1,0,0,(171,175),5,False,1,(0,0),None),
    (4,0,0,0,(171,175),5,False,1,(0,0),(1,3,200)),
    (9,-1,0,0,(171,175),10,False,1,(0,0),(1,3,200)),
    (1,1,500,1,(0,103),2,False,0,(0,0),None),
    (3,0,0,1,(0,103),4,False,0,(0,0),None),
    (4,0,0,1,(0,103),5,False,0,(0,0),None),
])
def test_event_stages(data,unit_effect,stage,virgin,lub,male,expected,next_stage,lost,semen,stains,preg):
    ctx = suit_context(data,0,4000)
    c = ctx.state.target_chara
    c.tcvarn[0],c.tcvarn[41] = 1,stage
    c.palam[10] = lub
    c.talent[data.index_of("TALENT","処女")] = virgin
    c.talent[data.index_of("TALENT","オトコ")] = male
    finish(ctx)
    assert tuple(ctx.state.temp.common_palam[i] for i in (1,2)) == expected
    assert c.tcvarn[41] == next_stage
    assert c.talent[data.index_of("TALENT","処女")] == (-1 if lost else virgin)
    assert (c.cflag[206],c.tcvarn[1]) == ((4,1) if lost else (0,0))
    assert ctx.state.temp.common_palam[10] == (10100 if lost else 100)
    assert tuple(c.stain[i] for i in (3,4)) == stains
    assert c.exp[data.index_of("EXP","精液経験")] == semen
    assert c.exp[data.index_of("EXP","被姦経験")] == 1
    assert [x[1] for x in unit_effect if x[0]=="pregnancy"] == ([] if preg is None else [preg])


@pytest.mark.parametrize("pose,expected", [(-1,-1),(0,0),(2,2),(4,4),(1,0),(3,0),(5,0),(100,0)])
@pytest.mark.parametrize("male", [0,1])
def test_pose_branch_precedes_gender(data,unit_effect,pose,expected,male):
    ctx = suit_context(data,0,4000)
    c = ctx.state.target_chara
    c.tcvarn[2],c.tcvarn[41] = pose,3
    c.talent[data.index_of("TALENT","オトコ")] = male
    finish(ctx)
    assert c.tcvarn[2] == expected and c.tcvarn[41] == -1
    assert ctx.state.temp.common_palam[1] == 101
    assert not any(x[0]=="pregnancy" for x in unit_effect)


def test_real_parameter_pipeline(data):
    # SEX_COMEX:184–250四部位強度70%，感覺0→280/280/28/280；
    # :296–328低潤滑→LOCAL10/11=1000；PALAM_HOSEI:440–460耐性0→1.7。
    ctx = suit_context(data,0,0,0,[50]*6)
    ctx.state.result[20] = 345
    finish(ctx)
    assert [ctx.state.temp.common_palam[i] for i in range(13)] == [476,476,47,476,0,0,0,0,0,0,1700,1700,0]
    assert ctx.state.rng.bounds == [100]*6
    assert ctx.state.result[8] == 0 and ctx.state.result[20] == 345


def test_parameter_order_and_limits(data,monkeypatch):
    from eragvt.game.battle import tentacle_suit as suit
    ctx = suit_context(data,0,4000)
    values = [2_000_000,1,0,-7,2_000_000,2,0,3,4,0,0,0]
    calls = []
    monkeypatch.setattr(suit,"sex_comex",lambda *_: values)
    for name in ("palam_hosei_pose","palam_hosei_seitaisei","palam_hosei_poisoning"):
        def identity(cx,value,_name=name):
            calls.append((_name,value))
            return value
        monkeypatch.setattr(suit,name,identity)
    monkeypatch.setattr(suit,"palam_hosei_talent",lambda cx,i,x: calls.append(("talent",i)) or x)
    monkeypatch.setattr(suit,"seikaku_hosei_palam",lambda cx,i,x: calls.append(("personality",i)) or x)
    monkeypatch.setattr(suit,"palam_hosei_random",lambda cx,x: calls.append(("random",x)) or (0 if x==1 else x))
    finish(ctx)
    assert [ctx.state.temp.common_palam[i] for i in range(13)] == [2_000_000,1,0,-7,999999,2,0,3,4,0,0,0,0]
    # 正值才走補正；0/負數不進RNG或下限，PALAM:4開始封頂。
    assert [x[1] for x in calls if x[0]=="talent"] == [0,1,4,5,7,8]
    assert [x[1] for x in calls if x[0]=="palam_hosei_poisoning"] == [2,3,4]
    assert [x[0] for x in calls[:6]] == ["palam_hosei_pose","palam_hosei_seitaisei","talent","personality","random","palam_hosei_pose"]


@pytest.fixture(scope="module")
def catalog(data):
    from eragvt.narration.service import CatalogNarrationService
    return CatalogNarrationService(default_csv_dir().parent/"ERB", data)


class SuitNarration(NullNarrationService):
    """只執行本次原地文及純顯示片段，其餘沿Null。"""
    def __init__(self, catalog):
        self.catalog = catalog
        self.calls = []

    def run_event_gen(self, ctx, name, args=None):
        if name.startswith("MESSAGE_TENTACLE_SUIT_") or name == "MESSAGE_SUBEVENT_BATTLE_ACTTENTACLESUIT":
            self.calls.append(name)
            return (yield from self.catalog.run_event_gen(ctx,name,args))
        return False


@pytest.mark.parametrize("equipment,resistance,stage,expected", [
    (0,100,0,[338,339,342]), (0,1,0,[338,339,341,342]),
    (4000,100,3,[396,398,403,405,406]), (4000,100,4,[427,429,434,436]),
])
def test_catalog_fragments(data,catalog,unit_effect,monkeypatch,equipment,resistance,stage,expected):
    from eragvt.narration.runtime import Interp
    ctx = suit_context(data,0,equipment,resistance,[0])
    ctx.narration = SuitNarration(catalog)
    c = ctx.state.target_chara
    c.tcvarn[0],c.tcvarn[41] = 1,stage
    seen = []
    original = Interp._print
    def trace(self,node,frame):
        if frame.name.startswith("MESSAGE_TENTACLE_SUIT_"):
            seen.append((node.line,ctx.out._bold,ctx.state.result[0]))
        return original(self,node,frame)
    monkeypatch.setattr(Interp,"_print",trace)
    finish(ctx)
    assert [x[0] for x in seen] == expected
    assert all(bold == (line in (396,403,427,434)) for line,bold,_ in seen)
    assert not any(key[0].startswith("MESSAGE_TENTACLE_SUIT_") for key in ctx.state.temp.locals)
    assert not catalog.failures and not ctx.out._bold


@pytest.mark.parametrize("form,normal,transformed,expected", [
    (0,"平常衣","變身衣","平常衣"), (0,"","變身衣","變身衣"),
    (0,"","",None), (1,"平常衣","變身衣","變身衣"),
    (1,"平常衣","",None), (2,"平常衣","變身衣","變身衣"),
])
def test_catalog_suit_name_snapshot(data,catalog,unit_effect,monkeypatch,form,normal,transformed,expected):
    from eragvt.narration.runtime import Interp
    from eragvt.narration.expr import Var
    ctx = suit_context(data,form,4000)
    c = ctx.state.target_chara
    c.cstr[8],c.cstr[9] = normal,transformed
    c.tcvarn[0],c.tcvarn[41] = 1,3
    class ChangingNarration(SuitNarration):
        def run_event_gen(self,cx,name,args=None):
            result = yield from super().run_event_gen(cx,name,args)
            if name == "MESSAGE_SUBEVENT_BATTLE_ACTTENTACLESUIT":
                c.cstr[8] = c.cstr[9] = "後續變更"
            return result
    ctx.narration = ChangingNarration(catalog)
    seen = []
    original = Interp._print
    def trace(self,node,frame):
        if frame.name.startswith("MESSAGE_TENTACLE_SUIT_") and node.line==398:
            seen.append(self._private_get(frame,Var("LOCALS",[])))
        return original(self,node,frame)
    monkeypatch.setattr(Interp,"_print",trace)
    finish(ctx)
    assert seen == [data.names["ITEM"][199] if expected is None else expected]
    assert not any(isinstance(key[0],tuple) and key[0][0].startswith("MESSAGE_TENTACLE_SUIT_") for key in ctx.state.temp.narr)


def prepare_suit_battle(ctx, mode):
    """人工BOSS先制前態：兩種外衣皆199；由原COM201完成變身後結算。"""
    prepare_equipment_battle(ctx,0)
    c = ctx.state.target_chara
    c.cflag[40] = c.cflag[41] = 199
    c.equip[99],c.equip[199] = 1000,4000 if mode=="event" else 0
    c.base[2] = c.maxbase[2] = 100
    ctx.state.result[99] = 345
    # 只驗外衣199，本次無200衣裝的零件。
    for slot in (601,602,661):
        c.equip[slot] = 0


@pytest.mark.parametrize("mode,stage,count", [("cost",0,0),("event",1,1)])
def test_real_train_command(data,catalog,mode,stage,count):
    from eragvt.game.battle.train import run_train
    ctx = make_context(data,SuitNarration(catalog))
    prepare_suit_battle(ctx,mode)
    st,c = ctx.state,ctx.state.target_chara
    gen = run_train(ctx)
    assert next(gen) is None
    before,rng,initiative = st.to_json(),st.rng.snapshot(),st.tflag[24]
    assert gen.send(998) is None
    assert st.to_json() == before and st.rng.snapshot() == rng
    assert gen.send(201) is None
    assert (c.cflag[1],c.tcvarn[41]) == (1,stage)
    assert c.exp[data.index_of("EXP","被姦経験")] == count
    assert st.flag[13] == 3000
    if mode == "cost":
        assert (c.base[0],c.base[1],c.base[2]) == (700,700,93)
    else:
        # PALAM_UP:165–213二次派生後，:320–330在stage!=0扣體氣耐性。
        # 本整合驗呼叫邊界；外衣完整精確算式另由上方原文table驗證。
        assert 0 < c.base[0] < 700 and 0 < c.base[1] < 700 and 0 < c.base[2] < 100
    assert st.temp.selectcom == st.temp.prevcom == 201
    assert st.tflag[24] == initiative-1
    # 訓練初始化／外衣相關RETURN可寫低位RESULT；遠尾格不受其影響。
    assert st.result[99] == 345 and st.results[8] == "尾格"
    assert ctx.narration.calls and not catalog.failures
    assert_ages(st)
    gen.close()


def test_real_pregnancy_wait_does_not_advance_event(data):
    from eragvt.game.battle.tentacle_suit import act_tentacle_suit
    ctx = suit_context(data,1,4000,100,[0,0,2,20]+[50]*6)
    st,c = ctx.state,ctx.state.target_chara
    st.flag[2] = 100
    c.tcvarn[0],c.tcvarn[41] = 1,3
    c.talent[data.index_of("TALENT","変身時ＴＳ")] = 1
    for slot in (13,14,30,31,32,33,34,35,36,37):
        c.cstr[slot] = "黒" if slot>=30 else "短髮"
    c.cstr[14],c.cstr[31],c.cstr[34],c.cstr[35],c.cstr[37] = "長髮","赤","青","緑","褐色"
    c.nowex[3] = 72
    gen = act_tentacle_suit(ctx)
    assert next(gen) is None
    # SUBEVENT:421的NINSIN_HANTEI→NINSIN_FLAG:227–246→TS等待；
    # :423之後尚未發生。SEX_COMEX已先給V/A各1，stage/COMMON_PALAM未結算。
    assert c.talent[data.index_of("TALENT","妊娠")] == 1
    assert c.tcvarn[41] == 3 and c.nowex[3] == 72
    assert c.exp[data.index_of("EXP","精液経験")] == c.exp[data.index_of("EXP","被姦経験")] == 0
    assert c.exp[data.index_of("EXP","Ｖ経験")] == c.exp[data.index_of("EXP","Ａ経験")] == 1
    assert not any(st.temp.common_palam[i] for i in range(13))
    rng = st.rng.snapshot()
    assert rng == [50]*6
    assert gen.send(9) is None
    assert st.rng.snapshot() == rng and c.tcvarn[41] == 3
    for answer in (0,1,0):
        assert gen.send(answer) is None
    with pytest.raises(StopIteration):
        gen.send(1)
    assert c.tcvarn[41] == 4 and c.nowex[3] == 0
    assert c.exp[data.index_of("EXP","精液経験")] == 2
    assert c.exp[data.index_of("EXP","被姦経験")] == 1
    assert c.exp[data.index_of("EXP","Ｖ経験")] == c.exp[data.index_of("EXP","Ａ経験")] == 1
    assert st.rng.snapshot() == [] and st.result[0] == 0
    assert_ages(st)


@pytest.mark.parametrize("mode,count", [("cost",0),("event",1)])
def test_web_real_suit_boundary(data,catalog,tmp_path,mode,count):
    from fastapi.testclient import TestClient
    from eragvt.game.battle.train import run_train
    from eragvt.web import create_app
    svc = SuitNarration(catalog)
    app = create_app(data,tmp_path,narration=svc)
    session = app.state.session
    cx = make_context(data,svc)
    session.state,session.out = cx.state,cx.out
    ctx = session._ctx()
    prepare_suit_battle(ctx,mode)
    session._run_gen(run_train(ctx),lambda: None)
    with TestClient(app) as client:
        before,rng = ctx.state.to_json(),ctx.state.rng.snapshot()
        assert client.post("/api/input",json={"value":998}).status_code == 200
        assert ctx.state.to_json() == before and ctx.state.rng.snapshot() == rng
        assert client.post("/api/input",json={"value":201}).status_code == 200
        c = ctx.state.target_chara
        assert c.cflag[1] == 1 and ctx.state.temp.prevcom == 201
        assert c.exp[data.index_of("EXP","被姦経験")] == count
        assert c.tcvarn[41] == count
        assert ctx.state.result[99] == 345
        assert_ages(ctx.state)
