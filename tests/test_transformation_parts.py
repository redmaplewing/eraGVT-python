"""S73：人工25歲；只記錄原文PRINT節點行號，不摘錄／輸出敘事。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.battle import commands
from eragvt.narration.runtime import Interp
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameState
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages

NAME = "MESSAGE_BATTLE_CHARA_NANORI_BYOUSHA"


class QuietOutput(TextOutput):
    def print(self, text):
        pass

    def print_plain(self, text):
        pass


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService(default_csv_dir().parent / "ERB", data)


def make_context(data, narration=None):
    st = GameState.new(data, FixedRng([]))
    st.charas = st.charas[:1]
    c = st.add_chara(data, 0)
    c.name = c.callname = "人工成年25"
    for a in (c.cflag, c.talent, c.abl, c.exp, c.ex, c.equip):
        a.clear()
    c.cflag[6] = 99999
    c.cflag[40], c.cflag[41], c.cflag[42] = 100, 200, 300
    c.talent[data.index_of("TALENT", "変身能力")] = 1
    c.base[0] = c.base[1] = 500
    c.maxbase[0] = c.maxbase[1] = 1000
    st.target = st.flag[799] = 1
    st.result[0], st.result[8] = 876, 765
    st.results[0], st.results[8] = "保留字串", "尾格"
    assert_ages(st)
    return Ctx(st, data, QuietOutput(), narration or NullNarrationService())


@pytest.fixture
def ctx(data, catalog):
    return make_context(data, catalog)


@pytest.fixture
def trace(monkeypatch):
    seen = []
    original = Interp._print

    def traced(self, node, frame):
        if frame.name == NAME:
            seen.append(node.line)
        return original(self, node, frame)

    monkeypatch.setattr(Interp, "_print", traced)
    return seen


# 地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_NANORI_BYOUSHA:221–267。
# 四項所有組合的連接詞、順序，由原文LOCAL計數推導。
@pytest.mark.parametrize("parts,prefix", [
    ((), []), ((600,), [224,227]), ((601,), [234,237]),
    ((602,), [246,249]), ((603,), [258,263]),
    ((600,601), [224,232,234,237]),
    ((600,602), [224,242,246,249]),
    ((600,603), [224,254,258,261]),
    ((601,602), [234,242,246,249]),
    ((601,603), [234,254,258,261]),
    ((602,603), [246,254,258,261]),
    ((600,601,602), [224,232,234,244,246,249]),
    ((600,601,603), [224,232,234,256,258,263]),
    ((600,602,603), [224,242,246,256,258,263]),
    ((601,602,603), [234,242,246,256,258,263]),
    ((600,601,602,603), [224,232,234,244,246,254,258,261]),
])
def test_prefix_combinations(ctx, trace, parts, prefix):
    for p in parts:
        ctx.state.target_chara.equip[p] = 1
    commands._msg_nanori_byousha(ctx)
    assert trace == prefix + [276,288,341]


@pytest.mark.parametrize("parts,middle,suffix", [
    ((672,), [270], []), ((673,), [272], []), ((672,673), [270,272], []),
    ((660,), [], [303]), ((661,), [], [305]), ((664,), [], [307]),
    ((690,), [], [310,330]), ((691,), [], [312,330]), ((693,), [], [314,330]),
    ((680,), [], [322,330]), ((681,), [], [327,330]),
    ((690,691,693,680,681), [], [310,312,314,321,322,326,327,330]),
    ((680,681), [], [322,327,330]),  # LOCAL只計腳部，不在第一個手部後遞增。
    ((660,661,664,690,680), [], [303]),
    ((661,664,693,681), [], [305]), ((664,690,680), [], [307]),
    ((600,601,602,603,672,673,660,661,664,690,691,693,680,681),
     [224,232,234,244,246,254,258,261,270,272], [303]),
])
def test_parts_order_and_priority(ctx, trace, parts, middle, suffix):
    # 同函式:269–272、301–336：披肩優先660→661→664，其餘組合獨立輸出。
    for p in parts:
        ctx.state.target_chara.equip[p] = 1
    commands._msg_nanori_byousha(ctx)
    assert trace == middle + [276,288] + suffix + [341]


@pytest.mark.parametrize("equip,expected", [
    ({600:2,601:1}, [234,276,288,341]),  # >0總和，但只有==1才輸出。
    ({600:-1,601:1}, [234,276,288,341]),
    ({660:2,690:1}, [276,288,310,330,341]),
    ({690:2,680:1}, [276,288,321,322,330,341]),
    ({660:2}, [276,288,341]),
    ({672:2,673:-1}, [276,288,341]),
    ({604:1,662:1,670:1,682:1,692:1}, [276,288,341]),
])
def test_exact_value_guards(ctx, trace, equip, expected):
    for p, value in equip.items():
        ctx.state.target_chara.equip[p] = value
    commands._msg_nanori_byousha(ctx)
    assert trace == expected


@pytest.mark.parametrize("suit,inner,trait,ability,beginner,expected", [
    (200,300,0,0,0,[276,288]), (201,300,0,0,0,[278,288]),
    (202,300,0,0,0,[280,288]), (299,300,0,0,0,[282,288]),
    (401,300,0,0,0,[284,288]), (199,300,0,0,0,[286,288]),
    (100,300,0,0,0,[297]), (0,300,1,3,0,[297]),
    (0,0,0,2,0,[294]), (0,0,0,3,0,[292]),
    (0,0,1,0,0,[292]), (0,0,1,3,1,[294]),
])
@pytest.mark.parametrize("transformed", [0,1,2])
def test_suit_reads_post_transform_slot_before_transform(ctx, trace, suit, inner, trait, ability, beginner, expected, transformed):
    # :274–299只讀CFLAG41/42，未依CFLAG1或服裝耐久過濾零件。
    c = ctx.state.target_chara
    c.cflag[1], c.cflag[41], c.cflag[42] = transformed, suit, inner
    c.equip[601] = 1
    c.talent[ctx.data.index_of("TALENT","淫乱")] = trait
    c.talent[ctx.data.index_of("TALENT","初心")] = beginner
    c.abl[ctx.data.index_of("ABL","露出癖")] = ability
    commands._msg_nanori_byousha(ctx)
    assert trace == [234,237] + expected + [341]


@pytest.mark.parametrize("named", [0,1])
def test_side_effects_and_reentry(ctx, trace, named):
    # VARSET LOCAL與#DIM CUSTOMIZABLE不改遊戲狀態；函式落尾RESULT0=0。
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    st = ctx.state
    st.target_chara.cflag[2] = named
    st.target_chara.equip[601] = 1
    before = st.to_json()
    before["result"].pop("0")  # 原函式落尾歸零；其餘存檔狀態完全相同。
    ctx.out.set_color((12,34,56))
    color = ctx.out._color
    commands._msg_nanori_byousha(ctx)
    assert st.to_json() == before
    assert (st.result[0],st.result[8]) == (0,765)
    assert (st.results[0],st.results[8]) == ("保留字串","尾格")
    assert ctx.out._color == color
    assert st.rng.snapshot() == []
    assert trace == [234,237,276,288,339 if named else 341]
    trace.clear()
    st.target_chara.equip[601] = 0
    commands._msg_nanori_byousha(ctx)
    assert trace == [276,288,339 if named else 341]  # CUSTOMIZABLE未寫入，沒有334。
    assert not ctx.narration.failures
    assert_ages(st)


def test_null_keeps_return_semantics(data):
    ctx = make_context(data)
    ctx.state.target_chara.equip[601] = 1
    commands._msg_nanori_byousha(ctx)
    assert (ctx.state.result[0],ctx.state.result[8]) == (0,765)


class PartsNarration(NullNarrationService):
    """只接本次原catalog，其餘敘事採Null；數值規則全部真實執行。"""
    def __init__(self, catalog):
        self.catalog = catalog
        self.calls = []

    def run_function(self, ctx, name, args=None, hooks=None):
        if name != NAME:
            return False
        c = ctx.state.target_chara
        self.calls.append((c.cflag[1],c.tcvarn[10],c.base[0],c.base[1]))
        return self.catalog.run_function(ctx,name,args,hooks)


@pytest.mark.parametrize("distance,answer,rolls,expected", [
    (3,1,[7],(1,37,700,700)),
    (3,2,[],(2,0,700,700)),
    (1,3,[],(3,0,800,800)),
    (3,3,[],(3,0,700,700)),
])
def test_real_com0_selection_and_followup(data,catalog,trace,distance,answer,rolls,expected):
    # COMF0.ERB@COM0:21–32 描寫在TRANSFORM(:51)及回復(:57–112)之前。
    # MOVESELECT.ERB@TRANSFORM_MOVESELECT:2–86；無效輸入重問，亂數只在移動1加EX。
    svc = PartsNarration(catalog)
    ctx = make_context(data,svc)
    st,c = ctx.state,ctx.state.target_chara
    c.tcvarn[0] = distance
    c.equip[601],c.equip[602],c.equip[661],c.equip[673] = 1,1,1,1
    st.rng = FixedRng(rolls)
    st.temp.selectcom = 0
    gen = commands.com0(ctx)
    assert next(gen) is None
    before = st.to_json()
    assert gen.send(998) is None
    assert st.to_json() == before and st.rng.snapshot() == rolls
    assert not svc.calls
    with pytest.raises(StopIteration) as end:
        gen.send(answer)
    assert end.value.value == 1
    assert svc.calls == [(0,1,500,500)]
    assert trace == [234,242,246,249,272,276,288,305,341]
    assert (c.tcvarn[0],c.tcvarn[6],c.base[0],c.base[1]) == expected
    assert (c.cflag[1],c.tcvarn[10],c.tcvarn[23]) == (1,1,10)
    assert st.tflag[25] == (1 if answer==2 else 0)
    assert st.rng.snapshot() == []
    assert (st.result[8],st.results[8]) == (765,"尾格")
    # 同場第二次不再執行名乗り描寫；不新增原作沒有的零件／衣裝狀態補正。
    c.cflag[1] = 0
    st.tflag[24] = 1
    with pytest.raises(StopIteration):
        next(commands.com0(ctx))
    assert len(svc.calls) == 1
    assert_ages(st)


def prepare_battle(ctx):
    """人工BOSS入口；固定RNG讓先制成立，本回合沒有敵方攻擊。"""
    st,c = ctx.state,ctx.state.target_chara
    st.flag[2] = 100
    st.savestr[13] = "BOSS"
    st.flag[11],st.flag[12],st.flag[13] = 3,10000,3000
    # S86 顯示原 COLOR_BAR 需要完整遭遇前態；ENCOUNT.ERB@ENCOUNT_BOSS:284–289。
    from eragvt.game.battle.core import tentacle_access
    st.flag[14],st.flag[15] = int(tentacle_access(ctx,"SYASEI")),0
    st.flag[46],st.flag[47],st.flag[100] = 28,36,127
    c.equip[601] = c.equip[602] = c.equip[661] = 1  # 200有三槽，組合無互斥。
    st.rng = FixedRng([0]*500)


def test_real_train_returns_to_menu(data,catalog,trace):
    from eragvt.game.battle.train import run_train
    svc = PartsNarration(catalog)
    ctx = make_context(data,svc)
    prepare_battle(ctx)
    st,c = ctx.state,ctx.state.target_chara
    gen = run_train(ctx)
    assert next(gen) is None
    before = st.to_json()
    rng = st.rng.snapshot()
    assert gen.send(998) is None
    assert st.to_json() == before and st.rng.snapshot() == rng
    assert gen.send(0) is None
    assert svc.calls == [(0,1,500,500)]
    assert trace == [234,242,246,249,276,288,305,341]
    assert c.cflag[1] == 1
    assert st.temp.selectcom == st.temp.prevcom == 0
    assert c.tcvarn[10] == 1
    # COM0回復20%；先制跳過攻擊，PALAM_UP:320的拘束門檻不成立，不消耗體氣。
    assert (c.base[0],c.base[1]) == (700,700)
    # BATTLE_COM.ERB@EVENTCOMEND:738–787：通常+12，無EXBOOST，結算後清增量。
    assert (c.tcvarn[4],c.tcvarn[6]) == (12,0)
    # CLOTHDATAアウター_変身専用.ERB@CLOTH_STATUS_200:10為HP120；
    # CLOTHDATAカスタム.ERB@CLOTH_CUSTOM_HOSEI_HP_601:39–41加10。
    assert (c.tcvarn[22],c.tcvarn[23]) == (130,130)
    assert st.target == 1
    assert_ages(st)
    gen.close()


def test_web_transform_and_readback(data,catalog,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.game.battle.train import run_train
    from eragvt.web import create_app
    svc = PartsNarration(catalog)
    app = create_app(data,tmp_path,narration=svc)
    session = app.state.session
    session.state = make_context(data,svc).state
    session.out = QuietOutput()
    ctx = session._ctx()
    prepare_battle(ctx)
    gen = run_train(ctx)
    session._run_gen(gen,lambda: None)
    with TestClient(app) as client:
        before = ctx.state.to_json()
        rng = ctx.state.rng.snapshot()
        assert client.post("/api/input",json={"value":998}).status_code == 200
        assert ctx.state.to_json() == before and ctx.state.rng.snapshot() == rng
        response = client.post("/api/input",json={"value":0})
        assert response.status_code == 200
        c = ctx.state.target_chara
        assert (c.cflag[1],c.base[0],c.base[1],c.tcvarn[4]) == (1,700,700,12)
        assert svc.calls == [(0,1,500,500)]
        assert (ctx.state.result[8],ctx.state.results[8]) == (765,"尾格")
        assert_ages(ctx.state)
    gen.close()
