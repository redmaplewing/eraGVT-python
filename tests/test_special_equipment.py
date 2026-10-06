"""S74：原文推導的人工25歲前態；敘事只比節點行號。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.battle import source_check as sc
from eragvt.game.battle.core import BeginAfterTrain
from eragvt.narration.runtime import Interp
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng
from eragvt.text import NullNarrationService
from tools.sim_adult import adult_data, assert_ages
from test_transformation_parts import make_context, prepare_battle


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService(default_csv_dir().parent / "ERB", data)


class TrackingRng(FixedRng):
    def __init__(self, values):
        super().__init__(values)
        self.bounds = []

    def rand(self, n):
        self.bounds.append(n)
        return super().rand(n)


def effect_context(data, equipment, rolls, narration=None):
    ctx = make_context(data, narration)
    st, c = ctx.state, ctx.state.target_chara
    c.cflag[43] = equipment
    # FLAG700=0只停在SOURCE_CHECK:439，三種裝備仍照原位執行。
    st.flag[13], st.flag[700] = 1000, 0
    st.rng = TrackingRng(rolls)
    return ctx


def finish_effect(ctx):
    with pytest.raises(StopIteration):
        next(sc.source_check(ctx))
    assert ctx.state.result[8] == 765
    assert ctx.state.results[8] == "尾格"
    assert_ages(ctx.state)


# MISC_PATCH.ERB@HP_AUTOREGAIN:44–51：整數除法朝零，無下限補正。
@pytest.mark.parametrize("maximum,current,roll,expected", [
    (1000,500,0,520), (1000,500,6,580), (1000,999,6,1000),
    (1000,1000,0,1000), (1000,1100,6,1000), (49,0,0,0),
    (0,0,0,0), (0,5,6,0), (1000,-100,0,-80),
    (-100,-200,0,-202), (-100,-99,0,-101), (-100,-98,0,-100),
])
@pytest.mark.parametrize("form", [0,1,2])
def test_regain(data, maximum, current, roll, expected, form):
    ctx = effect_context(data,507,[roll])
    c = ctx.state.target_chara
    c.cflag[1] = form
    c.maxbase[0],c.base[0] = maximum,current
    finish_effect(ctx)
    assert c.base[0] == expected and c.base[1] == 500
    assert ctx.state.rng.bounds == [7]
    assert ctx.state.result[0] == 0


# MISC_PATCH.ERB@SERVANT:57–83：原文先累加再比較，嚴格<，不封頂。
@pytest.mark.parametrize("roll,prior,enemy,threshold,expected", [
    (0,0,0,1,25), (0,0,0,0,0), (24,0,0,25,49),
    (24,0,1,25,24), (4,10,10,25,39), (5,10,10,25,15),
    (9,-20,-10,0,14), (10,100,10,25,110), (14,0,0,0,14),
    (15,0,0,0,15), (19,0,0,0,19), (20,0,0,0,20),
])
@pytest.mark.parametrize("citizen", [0,1])
def test_servant(data, roll, prior, enemy, threshold, expected, citizen):
    ctx = effect_context(data,509,[roll])
    st = ctx.state
    st.tflag[3],st.flag[17],st.flag[16],st.flag[73] = prior,enemy,threshold,citizen
    finish_effect(ctx)
    assert st.tflag[3] == expected
    assert st.flag[13] == 1000 and st.target_chara.base[0] == 500
    assert st.rng.bounds == [25] and st.result[0] == 0


# MISC_PATCH.ERB@TK_DRONE:4–39；DAMAGE依賴用可觀察stub隔離分支算術。
@pytest.mark.parametrize("roll,attack,expected", [
    (0,999,50), (4,333,63), (5,333,116), (19,333,163),
    (20,333,316), (25,333,333), (25,-333,167), (25,-2000,-250),
])
@pytest.mark.parametrize("power", [0,1,5])
@pytest.mark.parametrize("citizen", [0,1])
def test_drone_formula_and_power_restoration(data,monkeypatch,roll,attack,expected,power,citizen):
    from eragvt.game.battle import hantei
    ctx = effect_context(data,506,[roll,42])
    st,c = ctx.state,ctx.state.target_chara
    c.tcvarn[3] = power
    st.flag[73] = citizen
    calls = []
    def damage(cx,kind):
        calls.append((kind,c.tcvarn[3],cx.state.rng.rand(100)))
        return attack
    monkeypatch.setattr(hantei,"damage",damage)
    finish_effect(ctx)
    assert calls == [("ATTACK_RANGE_LONG",power & ~1,42)]
    assert c.tcvarn[3] == power
    assert st.flag[13] == 1000 - (0 if citizen else expected)
    assert st.rng.bounds == [26,100] and st.result[0] == 0


@pytest.mark.parametrize("equipment", [0,505,508,510,-506])
def test_unrelated_equipment_no_rng_or_result_write(data,equipment):
    ctx = effect_context(data,equipment,[])
    finish_effect(ctx)
    assert ctx.state.result[0] == 876
    assert ctx.state.rng.bounds == []


@pytest.mark.parametrize("equipment,roll,expected", [(506,0,950),(507,6,1000),(509,24,1000)])
def test_equipment_precedes_victory_motion_and_enemy(data,monkeypatch,equipment,roll,expected):
    from eragvt.game.battle import hantei
    ctx = effect_context(data,equipment,[roll])
    st = ctx.state
    st.flag[700] = 1
    monkeypatch.setattr(hantei,"damage",lambda *_: 100)
    def motion(cx):
        assert st.flag[13] == expected
        assert st.target_chara.base[0] == (580 if equipment==507 else 500)
        assert st.tflag[3] == (24 if equipment==509 else 0)
        raise RuntimeError("motion boundary")
    monkeypatch.setattr(sc,"_motion_palam",motion)
    with pytest.raises(RuntimeError,match="motion boundary"):
        next(sc.source_check(ctx))
    if equipment==506:
        st.flag[13] = 49
        st.rng = FixedRng([0])
        def victory(cx):
            assert st.flag[13] == -1  # 不把敵HP封在0。
            raise BeginAfterTrain()
        monkeypatch.setattr(sc,"_victory",victory)
        with pytest.raises(BeginAfterTrain):
            next(sc.source_check(ctx))


class EquipmentNarration(NullNarrationService):
    def __init__(self,catalog):
        self.catalog = catalog
        self.calls = []

    def run_function(self,ctx,name,args=None):
        if name.startswith("MESSAGE_EQUIPMENT_"):
            self.calls.append(name)
            return self.catalog.run_function(ctx,name,args)
        return False


@pytest.mark.parametrize("equipment,roll,citizen,expected", [
    (506,0,0,[19,20,25,37,39]), (506,5,0,[19,20,28,37,39]),
    (506,20,0,[19,20,31,37,39]), (506,25,1,[19,20,22,39]),
    (507,0,0,[50,51]),
    (509,0,0,[61,63,65]), (509,5,0,[61,63,69]), (509,5,1,[59,63,67]),
    (509,10,0,[61,63,71]), (509,15,0,[61,63,75]), (509,15,1,[59,63,73]),
    (509,20,0,[61,63,79]), (509,20,1,[59,63,77]),
])
def test_catalog_nodes(data,catalog,monkeypatch,equipment,roll,citizen,expected):
    from eragvt.game.battle import hantei
    seen = []
    original = Interp._print
    def trace(self,node,frame):
        if frame.name.startswith("MESSAGE_EQUIPMENT_"):
            seen.append(node.line)
        return original(self,node,frame)
    monkeypatch.setattr(Interp,"_print",trace)
    monkeypatch.setattr(hantei,"damage",lambda *_: 333)
    ctx = effect_context(data,equipment,[roll],EquipmentNarration(catalog))
    ctx.state.flag[73] = citizen
    finish_effect(ctx)
    assert seen == expected
    assert not catalog.failures
    assert ctx.state.results[0] == "保留字串"
    assert not any(key[0].startswith("MESSAGE_EQUIPMENT_") for key in ctx.state.temp.locals)


@pytest.mark.parametrize("form", [0,1,2])
@pytest.mark.parametrize("power", [0,1,5])
@pytest.mark.parametrize("citizen", [0,1])
def test_drone_real_damage_and_rng(data,form,power,citizen):
    ctx = effect_context(data,506,[25,42])
    st,c = ctx.state,ctx.state.target_chara
    enemy = st.add_chara(data,0)
    enemy.maxbase[11] = 0
    st.flag[111] = 2
    st.flag[73] = citizen
    c.cflag[1],c.tcvarn[3] = form,power
    c.maxbase[10] = 0
    c.cdflag.clear()
    # FIGHT_STYLE.ERB@FSTYLE_ATTACK:46–98攻擊0；COMMON_BATTLE_HANTEI.ERB@DAMAGE:
    # 1317–1351仍為0，1454得500，RAND100=42不補正；25%+250=375。
    # FLAG73>0時DAMAGE:1514改1，但仍抽RAND100；TK_DRONE:23最後改0。
    finish_effect(ctx)
    assert st.flag[13] == (1000 if citizen else 625)
    assert c.tcvarn[3] == power
    assert st.rng.bounds == [26,100]


def prepare_equipment_battle(ctx,equipment):
    """run_train前設定：與S73同人工先制前態，無代選或更換產品規則。"""
    prepare_battle(ctx)
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[43] = equipment
    st.flag[16],st.flag[17] = 100,0
    # TENTACLE_SYASEI.ERB@TENTACLE_SYASEI:84–206：正閾值避免0>=0的其他結算。
    st.flag[14],st.flag[15] = 1000,0


@pytest.mark.parametrize("equipment,hp,enemy_hp,reaction", [
    (506,700,2950,0), (507,720,3000,0), (509,700,3000,24),
])
def test_real_train_command_effect_and_next_input(data,catalog,equipment,hp,enemy_hp,reaction):
    from eragvt.game.battle.train import run_train
    svc = EquipmentNarration(catalog)
    ctx = make_context(data,svc)
    prepare_equipment_battle(ctx,equipment)
    st,c = ctx.state,ctx.state.target_chara
    gen = run_train(ctx)
    assert next(gen) is None
    before,rng = st.to_json(),st.rng.snapshot()
    initiative = st.tflag[24]
    assert gen.send(998) is None
    assert st.to_json() == before and st.rng.snapshot() == rng
    # COMF0.ERB@COM201:118–120→COM0；先制期間變身，回復20%。
    assert gen.send(201) is None
    assert (c.cflag[1],c.base[0],c.base[1]) == (1,hp,700)
    assert st.flag[13] == enemy_hp
    # SERVANT+25由PALAM_UP.ERB@PALAM_UP_ENEMY_REACTION:1823–1852結算：25−1=24。
    assert (st.flag[17],st.tflag[3]) == (reaction,0)
    assert st.temp.selectcom == st.temp.prevcom == 201
    # SOURCE_CHECK:1313–1316：先制餘額減1；保留EVENTTRAIN的原抽選結果。
    assert (c.tcvarn[4],c.tcvarn[6],st.tflag[24]) == (12,0,initiative-1)
    assert svc.calls and not catalog.failures
    assert (st.result[8],st.results[8]) == (765,"尾格")
    assert_ages(st)
    gen.close()


def test_web_equipment_boundary(data,catalog,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.game.battle.train import run_train
    from eragvt.web import create_app
    svc = EquipmentNarration(catalog)
    app = create_app(data,tmp_path,narration=svc)
    session = app.state.session
    cx = make_context(data,svc)
    session.state,session.out = cx.state,cx.out
    ctx = session._ctx()
    prepare_equipment_battle(ctx,507)
    session._run_gen(run_train(ctx),lambda: None)
    with TestClient(app) as client:
        before = ctx.state.to_json()
        assert client.post("/api/input",json={"value":998}).status_code == 200
        assert ctx.state.to_json() == before
        assert client.post("/api/input",json={"value":201}).status_code == 200
        c = ctx.state.target_chara
        assert (c.cflag[1],c.base[0],c.base[1]) == (1,720,700)
        assert ctx.state.temp.prevcom == 201
        assert_ages(ctx.state)


@pytest.mark.parametrize("roll,line", [(5,67),(15,73),(20,77)])
def test_servant_enemy_type_and_flag73_are_distinct(data,catalog,roll,line):
    svc = EquipmentNarration(catalog)
    ctx = effect_context(data,509,[roll],svc)
    # コモン関数.ERB@ENEMY_TYPE_CHECK_F:1356–1371：FLAG110>0不是CITIZEN，
    # 但MISC_PATCH.ERB@SERVANT:66/72/76只判FLAG73>0。
    ctx.state.flag[110],ctx.state.flag[73] = 1,1
    finish_effect(ctx)
    assert svc.calls == ["MESSAGE_EQUIPMENT_SERVANT_OTHER",
                         "MESSAGE_EQUIPMENT_SERVANT_START",f"MESSAGE_EQUIPMENT_SERVANT_{line}"]


@pytest.mark.parametrize("attack,citizen,lines", [
    (333,0,[19,20,31,37,39]), (-2000,0,[19,20,31,39]), (333,1,[19,20,22,39]),
])
def test_drone_fonts_and_inline_result(data,catalog,monkeypatch,attack,citizen,lines):
    from eragvt.game.battle import hantei
    ctx = effect_context(data,506,[25],EquipmentNarration(catalog))
    ctx.state.flag[73] = citizen
    ctx.out.set_italic(True)
    ctx.out.set_color("#123456")
    seen = []
    original = Interp._print
    def trace(self,node,frame):
        if frame.name.startswith("MESSAGE_EQUIPMENT_"):
            seen.append((node.line,ctx.out._bold,ctx.out._italic,ctx.state.result[0]))
        return original(self,node,frame)
    monkeypatch.setattr(Interp,"_print",trace)
    monkeypatch.setattr(hantei,"damage",lambda *_: attack)
    finish_effect(ctx)
    assert [x[0] for x in seen] == lines
    assert all(bold == (line==37) and italic == (line!=39) and result==attack
               for line,bold,italic,result in seen)
    assert not ctx.out._bold and not ctx.out._italic
    assert ctx.out._color == "#123456"


def test_fatigue_precedes_drone(data,monkeypatch):
    from eragvt.game.battle import hantei
    ctx = effect_context(data,506,[0])
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[99],st.tflag[99],c.tcvarn[3] = 19,1,5
    def damage(cx,kind):
        # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:12–35先結算疲勞再調用裝備。
        assert (c.cflag[99],st.tflag[99],c.tcvarn[3]) == (20,0,4)
        return 100
    monkeypatch.setattr(hantei,"damage",damage)
    finish_effect(ctx)
    assert c.tcvarn[3] == 5
