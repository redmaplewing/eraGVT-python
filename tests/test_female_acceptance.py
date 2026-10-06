"""S72：人工25歲兩形態，expected 由 ABL_UP_CHECK.ERB@_ABLUP:444–479 推導。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.battle.ablup import ablup
from eragvt.game.battle.func import transform
from eragvt.state import FixedRng, GameState
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages


class QuietOutput(TextOutput):
    """驗證僅處理數值；不輸出既有敘事。"""
    def print(self, text):
        pass

    def print_plain(self, text):
        pass


class TraceNarration(NullNarrationService):
    def __init__(self):
        self.calls = []
        self.kojo = []

    def run_function(self, ctx, name, args=None, hooks=None):
        if "TSJYUYOU" in name:
            c = ctx.state.target_chara
            values = tuple(c.talent[ctx.data.index_of("TALENT", n)] for n in
                           ("女体受容", "男性苦手", "女性苦手"))
            self.calls.append((name, ctx.state.target, values))
        return False

    def call_kojo(self, ctx, c_no, code):
        self.kojo.append(code)
        return super().call_kojo(ctx, c_no, code)


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, FixedRng([]))
    st.charas = st.charas[:1]
    for i in (1, 2):
        c = st.add_chara(data, 0)
        c.name = c.callname = f"人工成年{i}"
        c.talent.clear()
        c.cflag.clear()
        c.abl.clear()
        c.exp.clear()
        c.ex.clear()
        c.cflag[6], c.cflag[240], c.cflag[999] = 99999, 40+i, 1
        c.abl[data.index_of("ABL", "レベル")] = 10
    st.target = 1
    st.result[0], st.result[8] = 876, 765
    st.results[0], st.results[8] = "保留字串", "尾格"
    cx = Ctx(st, data, QuietOutput(), TraceNarration())
    put(cx, "TALENT", {"性別変化": 1, "男性苦手": 2, "女性苦手": -1})
    assert_ages(st)
    return cx


def put(ctx, kind, values):
    array = getattr(ctx.state.target_chara, kind.lower())
    for key, value in values.items():
        array[key if isinstance(key, int) else ctx.data.index_of(kind, key)] = value


def traits(ctx):
    return tuple(ctx.state.charas[1].talent[ctx.data.index_of("TALENT", n)] for n in
                 ("女体受容", "男性苦手", "女性苦手"))


@pytest.mark.parametrize("tal,abilities,experience,flags,code", [
    ({"触手の虜":1,"淫乱":1}, {}, {}, {}, "TORIKO"),
    ({"淫乱":1}, {}, {}, {}, "INRAN"),
    ({"淫壷":1}, {}, {}, {}, "INRAN"),
    ({}, {"Ｖ感覚":5,"精液中毒":2,"噴乳中毒":2,"射精中毒":3}, {}, {}, "INRAN"),
    ({}, {"Ｖ感覚":4,"精液中毒":4}, {}, {}, None),
    ({}, {"Ｖ感覚":5,"精液中毒":2,"噴乳中毒":1,"射精中毒":3}, {}, {}, None),
    ({}, {}, {"出産経験":1}, {230:-3}, "FEMININE"),
    ({}, {}, {"出産経験":1}, {230:-1}, None),
    ({}, {}, {"出産経験":0}, {230:-3}, None),
    ({}, {}, {}, {206:5}, "FEMININE"),
    ({}, {}, {}, {206:4}, None),
    ({}, {}, {"魅了経験":199}, {}, None),
    ({}, {}, {"魅了経験":200}, {}, "CHARM"),
    ({"両刀":1}, {"Ｖ感覚":5}, {}, {}, "RYOUTOU"),
    ({"両刀":1}, {"Ｖ感覚":4}, {}, {}, None),
    ({"両刀":1,"淫壷":1}, {"Ｖ感覚":5}, {"魅了経験":200}, {206:5}, "INRAN"),
    ({"両刀":1}, {"Ｖ感覚":5}, {"魅了経験":200}, {206:5}, "FEMININE"),
    ({"両刀":1}, {"Ｖ感覚":5}, {"魅了経験":200}, {}, "CHARM"),
])
def test_branches_and_priority(ctx, tal, abilities, experience, flags, code):
    for kind, values in (("TALENT",tal),("ABL",abilities),("EXP",experience),("CFLAG",flags)):
        put(ctx, kind, values)
    ablup(ctx, 1)
    assert traits(ctx) == ((1,-1,2) if code else (0,2,-1))
    assert ctx.narration.calls == ([(f"MESSAGE_GETTALENT_TSJYUYOU_{code}",1,(1,-1,2))] if code else [])
    # MESSAGE_SEX.ERB@MESSAGE_GETTALENT_TSJYUYOU_RYOUTOU:1846 原樣呼叫CHARM。
    if code:
        assert ctx.narration.kojo[-1] == f"GETTALENT_TSJYUYOU_{'CHARM' if code=='RYOUTOU' else code}"
    before = list(ctx.narration.calls)
    ablup(ctx, 1)
    assert ctx.narration.calls == before
    assert traits(ctx) == ((1,-1,2) if code else (0,2,-1))
    assert ctx.state.target == 1
    # 自然終端：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    assert (ctx.state.result[0],ctx.state.result[8]) == (0,765)
    assert (ctx.state.results[0],ctx.state.results[8]) == ("保留字串","尾格")
    assert ctx.state.rng.snapshot() == []
    assert_ages(ctx.state)


@pytest.mark.parametrize("change,ts,male,form,accepted,expected", [
    (1,0,1,0,0,1),(11,0,0,0,0,1),(21,0,0,1,0,1),
    (0,1,0,1,0,1),(0,2,0,2,0,1),(0,1,0,0,0,0),
    (0,1,1,1,0,0),(0,0,0,1,0,0),(2,0,0,0,0,0),
    (1,0,0,0,1,1),(1,0,0,0,-1,-1),(-9,0,0,0,0,0),
])
def test_outer_gate(ctx,change,ts,male,form,accepted,expected):
    put(ctx,"TALENT",{"性別変化":change,"変身時ＴＳ":ts,"オトコ":male,"女体受容":accepted})
    put(ctx,"CFLAG",{1:form})
    put(ctx,"EXP",{"魅了経験":200})
    ablup(ctx,1)
    assert traits(ctx) == ((1,-1,2) if accepted==0 and expected==1 else (expected,2,-1))
    assert ctx.state.target_chara.cflag[1] == form


@pytest.mark.parametrize("birth,father,relation_index,bit,expected", [
    (1,-142,2,31,1),(1,-142,2,32,1),(1,-142,2,33,1),(1,-142,2,34,1),
    (1,-142,2,30,0),(1,-142,1,32,0),(0,-142,2,32,0),
    (1,-100,0,32,0),(1,-999,0,32,1),(1,-999,2,32,0),
])
def test_father_id_and_directional_relation(ctx,birth,father,relation_index,bit,expected):
    # CHARA_RELATION.ERB@LOVER_F:1024–1028；コモン関数.ERB@CHARAID_F:1062–1070，找不到回0。
    put(ctx,"EXP",{"出産経験":birth})
    put(ctx,"CFLAG",{230:father})
    ctx.state.target_chara.relation[relation_index] = 1 << bit
    ablup(ctx,1)
    assert traits(ctx)[0] == expected


def test_real_transform_retains_acceptance(ctx):
    put(ctx,"TALENT",{"性別変化":0,"オトコ":1,"変身時ＴＳ":1,"変身能力":1})
    put(ctx,"EXP",{"魅了経験":200})
    c = ctx.state.target_chara
    transform(ctx,1)
    body = (dict(c.equip.items()),dict(c.cstr.items()),c.cflag[228])
    ablup(ctx,1)
    assert traits(ctx) == (1,-1,2)
    assert c.cflag[1] == 1
    assert (dict(c.equip.items()),dict(c.cstr.items()),c.cflag[228]) == body
    transform(ctx,0)
    ablup(ctx,1)
    transform(ctx,1)
    ablup(ctx,1)
    assert traits(ctx) == (1,-1,2)
    assert len(ctx.narration.calls) == 1
    assert_ages(ctx.state)


def prepare_night(ctx):
    st = ctx.state
    st.time = 1
    st.flag[2] = 100
    put(ctx,"TALENT",{"男性苦手":0,"女性苦手":0})
    put(ctx,"ABL",{"Ｃ感覚":3})
    put(ctx,"EXP",{"魅了経験":200})
    st.rng = FixedRng([0]*500)


def test_real_night_input_to_ability_update(ctx):
    # FORCE_夜這い.ERB@YOBAI:77–95 → @YOBAI_EVENT:504–513 →
    # @YOBAI_ACTION:1048、1063、2645，保留TARGET切換與全員解除變身。
    from eragvt.game.yobai import yobai
    prepare_night(ctx)
    gen = yobai(ctx)
    assert next(gen) is None
    before = ctx.state.rng.snapshot()
    assert gen.send(998) is None
    assert ctx.state.rng.snapshot() == before
    assert traits(ctx)[0] == 0
    with pytest.raises(StopIteration):
        gen.send(2)
    assert traits(ctx)[0] == 1
    assert ctx.narration.calls == [("MESSAGE_GETTALENT_TSJYUYOU_CHARM",1,(1,0,0))]
    assert ctx.state.target == 2
    assert all(c.cflag[1] == 0 for c in ctx.state.charas[1:])
    assert ctx.state.result[0] == 0
    assert ctx.state.result[8] == 765
    assert (ctx.state.results[0],ctx.state.results[8]) == ("保留字串","尾格")
    assert_ages(ctx.state)


def prepare_battle(ctx):
    st = ctx.state
    st.flag[2] = 100
    st.savestr[13] = "BOSS"
    st.flag[11],st.flag[12],st.flag[13] = 3,10000,3000
    st.flag[46],st.flag[47],st.flag[100] = 28,36,127
    put(ctx,"TALENT",{"性別変化":0,"オトコ":1,"変身時ＴＳ":1,"変身能力":1})
    put(ctx,"EXP",{"魅了経験":200})
    transform(ctx,1)
    st.rng = FixedRng([0]*500)


def test_real_battle_retreat_to_ability_update(ctx):
    # BATTLE_TRAIN.ERB@USERCOM:573–599 → BATTLE_TRAIN_AFTER.ERB@EVENTEND:131–137、204–206。
    from eragvt.game.battle.train import run_train
    from eragvt.game.action import Step
    prepare_battle(ctx)
    gen = run_train(ctx)
    assert next(gen) is None
    before = ctx.state.rng.snapshot()
    assert gen.send(998) is None
    assert ctx.state.rng.snapshot() == before
    assert traits(ctx)[0] == 0
    with pytest.raises(StopIteration) as end:
        gen.send(999)
    assert end.value.value == Step.TURNEND
    assert traits(ctx) == (1,-1,2)
    assert ctx.narration.calls == [("MESSAGE_GETTALENT_TSJYUYOU_CHARM",1,(1,-1,2))]
    assert ctx.state.target == 1
    assert ctx.state.target_chara.cflag[1] == 0
    assert ctx.state.result[0] == 0
    assert ctx.state.result[8] == 765
    assert (ctx.state.results[0],ctx.state.results[8]) == ("保留字串","尾格")
    assert_ages(ctx.state)


@pytest.fixture(scope="module")
def catalog(data):
    from eragvt.narration.service import CatalogNarrationService
    return CatalogNarrationService(default_csv_dir().parent/"ERB",data)


@pytest.mark.parametrize("code,line",[("TORIKO",1801),("INRAN",1813),("FEMININE",1823),("CHARM",1835),("RYOUTOU",1846)])
def test_original_catalog_dispatch_only(ctx,catalog,monkeypatch,code,line):
    # MESSAGE_SEX.ERB@MESSAGE_GETTALENT_TSJYUYOU_*：抽原呼叫節點，不輸出／摘錄敘事。
    from dataclasses import replace
    from eragvt.narration.nodes import CallStmt, Print
    name = f"MESSAGE_GETTALENT_TSJYUYOU_{code}"
    original = catalog.catalog.get(name)
    assert all(isinstance(n,(CallStmt,Print)) for n in original.body)
    calls = [n for n in original.body if isinstance(n,CallStmt)]
    assert len(calls) == 1 and calls[0].line == line
    monkeypatch.setitem(catalog.catalog._parsed,name,replace(original,body=calls))
    monkeypatch.setitem(catalog.catalog._support,name,None)
    class DispatchOnly(TraceNarration):
        def run_function(self,cx,func,args=None,hooks=None):
            return catalog.run_function(cx,func,args,hooks)
    ctx.narration = DispatchOnly()
    if code == "TORIKO": put(ctx,"TALENT",{"触手の虜":1})
    elif code == "INRAN": put(ctx,"TALENT",{"淫壷":1})
    elif code == "FEMININE": put(ctx,"CFLAG",{206:5})
    elif code == "CHARM": put(ctx,"EXP",{"魅了経験":200})
    else:
        put(ctx,"TALENT",{"両刀":1})
        put(ctx,"ABL",{"Ｖ感覚":5})
    ablup(ctx,1)
    assert traits(ctx) == (1,-1,2)
    assert ctx.narration.kojo[-1] == f"GETTALENT_TSJYUYOU_{'CHARM' if code=='RYOUTOU' else code}"


@pytest.mark.parametrize("entry,answer,target",[("night",2,2),("battle",999,1)])
def test_web_real_lifecycle_boundary(ctx,tmp_path,entry,answer,target):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.game.yobai import yobai
    from eragvt.game.battle.train import run_train
    (prepare_night if entry=="night" else prepare_battle)(ctx)
    app = create_app(ctx.data,tmp_path,narration=NullNarrationService())
    session = app.state.session
    session.state, session.out = ctx.state, QuietOutput()
    session.globals.mem.global_[256] = 1  # 人工前態200經驗，其100門檻成就已取得。
    complete = []
    generator = (yobai if entry=="night" else run_train)(session._ctx())
    session._run_gen(generator,lambda: complete.append(True))
    before = ctx.state.rng.snapshot()
    with TestClient(app) as client:
        assert client.get("/api/screen").status_code == 200
        assert client.post("/api/input",json={"value":998}).status_code == 200
        assert not complete and traits(ctx)[0] == 0
        assert ctx.state.rng.snapshot() == before
        assert client.post("/api/input",json={"value":answer}).status_code == 200
    assert complete == [True]
    assert session._turn is None
    assert traits(ctx)[0] == 1
    assert ctx.state.target == target
    assert (ctx.state.result[0],ctx.state.result[8]) == (0,765)
    assert_ages(ctx.state)
