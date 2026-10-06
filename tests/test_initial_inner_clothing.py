"""S76：fresh-adult-25-v1；衣裝 expected 直接由 ERB 推導。"""
import copy

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.battle.cloth import cloth_no_inner, cloth_hosei, cloth_battle_sethp, refresh_cloth_data
from eragvt.game.opening import chara_make_finalize
from tools.sim_adult import adult_data, assert_ages
from test_transformation_parts import make_context
from test_special_equipment import TrackingRng


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


def initial_context(data):
    ctx = make_context(data)
    c = ctx.state.target_chara
    # DEFAULT@CHARA_MAKE_INITIALIZE:8–166：已設定者不進生成分支。
    c.cflag[34] = 1
    c.juel.clear()
    for name in ("人間", "真面目", "処女"):
        c.talent[data.index_of("TALENT", name)] = 1
    c.cstr[0], c.cstr[3] = "人工形態", "人工名乘"
    ctx.state.rng = TrackingRng([])
    return ctx


# CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE:387–418：任一形態兼用即不補300。
# CLOTH_STATUS_100/200無NOINNER；110/199/202/299有NOINNER1。
@pytest.mark.parametrize("outer,after,inner,ability,form,expected", [
    (0,0,0,1,0,(100,200,300,0)),
    (-1,-1,0,1,0,(0,0,300,0)),
    (100,200,0,1,0,(100,200,300,0)),
    (110,200,0,1,0,(110,200,0,0)),
    (100,202,0,1,0,(100,202,0,0)),
    (199,299,0,1,0,(199,299,0,0)),
    (100,202,0,0,0,(100,202,300,0)),
    (110,200,0,-1,0,(110,200,0,0)),
    (100,202,0,2,0,(100,202,300,0)),
    (100,202,-1,1,2,(100,202,0,2)),
    (110,202,308,1,2,(110,202,308,2)),
    (110,200,0,1,2,(110,200,300,0)),
    (100,202,0,0,2,(100,202,0,2)),
])
def test_finalize_defaults(data, outer, after, inner, ability, form, expected):
    ctx = initial_context(data)
    st, c = ctx.state, ctx.state.target_chara
    c.cflag[40], c.cflag[41], c.cflag[42], c.cflag[43] = outer, after, inner, -1
    c.cflag[1] = form
    c.talent[data.index_of("TALENT", "変身能力")] = ability
    chara_make_finalize(st, data, 1)  # 無ctx的招募／醫療等既有呼叫方式亦接通。
    assert tuple(c.cflag[i] for i in (40,41,42,1)) == expected
    assert c.cflag[43] == 0 and st.target == 1
    assert st.result[0] == 0  # 引擎 Process.ScriptProc.cs:61–67，自然落尾。
    assert st.result[8] == 765 and st.results[8] == "尾格"
    assert st.rng.bounds == []
    assert_ages(st)


# CLOTHDATAアウター_通常.ERB@CLOTH_HOSEI_NOINNER_106:1133–1140、
# _115:2875–2882、_117:3317–3324、_153:8525–8532；只看第14位恰為1。
@pytest.mark.parametrize("cid", [106,115,117,153])
@pytest.mark.parametrize("form", [0,1,2])
@pytest.mark.parametrize("digit,expected", [(0,0),(1,1),(2,0)])
def test_custom_noinner(data, cid, form, digit, expected):
    ctx = initial_context(data)
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[1] = form
    c.cflag[40 if form==0 else 41] = cid
    c.equip[cid-100 if form==0 else cid] = digit*10**13
    assert cloth_no_inner(ctx,1,registers=True) == expected
    assert st.result[0] == expected and st.results[0] == "保留字串"
    assert st.result[8] == 765 and st.results[8] == "尾格"
    assert st.rng.bounds == []


@pytest.mark.parametrize("form,expected", [(0,0),(1,1),(2,1)])
@pytest.mark.parametrize("registers", [False,True])
def test_argument_selects_form_but_target_supplies_clothes(data, form, expected, registers):
    # CLOTH_BATTLE.ERB@CLOTH_NO_INNER:454；省略角色由TARGET補齊：
    # reference/emuera-1824/Emuera/GameData/Variable/VariableParser.cs:107–119。
    ctx = initial_context(data)
    st = ctx.state
    st.charas.append(copy.deepcopy(st.target_chara))
    st.charas[1].cflag[40],st.charas[1].cflag[41] = 100,202
    st.charas[2].cflag[40],st.charas[2].cflag[41] = 110,200
    st.charas[2].cflag[1] = form
    result = cloth_no_inner(ctx,2,registers=True) if registers else cloth_no_inner(ctx,2)
    assert result == expected
    assert st.target == 1
    assert st.result[0] == (expected if registers else 876)
    assert st.results[0] == ("1" if registers and expected else "保留字串")
    assert st.result[8] == 765 and st.results[8] == "尾格"
    assert st.rng.bounds == []


@pytest.mark.parametrize("arg", [0,2])
@pytest.mark.parametrize("target_outer,expected", [(100,300),(110,0)])
def test_all_and_selected_finalize_keep_target(data, arg, target_outer, expected):
    ctx = initial_context(data)
    st = ctx.state
    st.charas.append(copy.deepcopy(st.target_chara))
    st.charas[1].cflag[40] = target_outer
    st.charas[1].cflag[42] = st.charas[2].cflag[42] = 0
    st.charas[2].cflag[40] = 110 if target_outer==100 else 100
    chara_make_finalize(st,data,arg,ctx=ctx)
    assert st.charas[2].cflag[42] == expected
    assert st.charas[1].cflag[42] == (expected if arg==0 else 0)
    assert st.charas[1].cflag[240] == (1 if arg==0 else 0)
    assert st.charas[2].cflag[240] == 2
    assert st.target == 1 and st.result[0] == 0
    assert st.rng.bounds == []
    assert_ages(st)


@pytest.mark.parametrize("outer,after,results,inner", [
    (100,200,"保留字串",300), (110,200,"1",0),
    (100,202,"1",0), (106,200,"保留字串",300),
])
def test_finalize_registers_and_battle_refresh(data,outer,after,results,inner):
    ctx = initial_context(data)
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[40],c.cflag[41],c.cflag[42] = outer,after,0
    chara_make_finalize(st,data,ctx=ctx)
    assert c.cflag[42] == inner and st.results[0] == results
    # CLOTH_BATTLE.ERB@CLOTH_BATTLE_SETHP:6–26；未穿內衣HP=0，300的HP=80。
    cloth_battle_sethp(ctx)
    assert (c.tcvarn[24],c.tcvarn[25]) == ((80,80) if inner else (0,0))
    refresh_cloth_data(ctx)
    assert st.temp.cloth[0] == int(outer==110)
    c.cflag[1] = 1
    refresh_cloth_data(ctx)
    assert st.temp.cloth[0] == int(after==202)
    assert st.rng.bounds == []
    assert_ages(st)


@pytest.mark.parametrize("outer,expected", [(0,0),(999,0),(110,1),(199,1),(202,1),(299,1),(401,1),(402,1)])
def test_static_and_missing_outer(data,outer,expected):
    ctx = initial_context(data)
    st = ctx.state
    st.target_chara.cflag[40] = outer
    assert cloth_no_inner(ctx,1,registers=True) == expected
    assert st.result[0] == expected
    assert st.results[0] == ("1" if expected else "保留字串")
    assert st.rng.bounds == []


@pytest.mark.parametrize("form,value,text", [(0,100,"100"),(1,110,"110")])
def test_register_mode_substring_order(data,form,value,text):
    # CLOTH_STATUS_110:1891的BOUGYO100@110；CLOTH_HOSEI:73–83先取100、變身再取110。
    # registers只同步字串；數值由CALL包裝者接收，不改既有純回傳慣例。
    ctx = initial_context(data)
    st = ctx.state
    st.target_chara.cflag[1] = form
    assert cloth_hosei(ctx,1,110,"BOUGYO",registers=True) == value
    assert st.results[0] == text and st.result[0] == 876
    assert st.result[8] == 765 and st.results[8] == "尾格"


@pytest.mark.parametrize("target_form,digit,expected", [(0,1,1),(0,0,0),(2,1,1)])
def test_argument_form_does_not_select_custom_equipment(data,target_form,digit,expected):
    ctx = initial_context(data)
    st = ctx.state
    st.charas.append(copy.deepcopy(st.target_chara))
    st.charas[2].cflag[1] = 1
    st.charas[1].cflag[1],st.charas[1].cflag[41] = target_form,106
    st.charas[1].equip[6 if target_form==0 else 106] = digit*10**13
    st.charas[2].equip[106] = (1-digit)*10**13
    assert cloth_no_inner(ctx,2,registers=True) == expected
    assert st.target == 1 and st.charas[1].cflag[1] == target_form


@pytest.mark.parametrize("form,outer,inner", [(0,106,0),(0,115,0),(1,117,0),(1,153,0)])
def test_finalize_custom_outer(data,form,outer,inner):
    ctx = initial_context(data)
    st,c = ctx.state,ctx.state.target_chara
    c.cflag[40 if form==0 else 41] = outer
    c.cflag[42] = 0
    c.equip[outer-100 if form==0 else outer] = 10**13
    chara_make_finalize(st,data,ctx=ctx)
    assert c.cflag[42] == inner and c.cflag[1] == 0
    assert st.rng.bounds == []


def editor_data(data,combined):
    """從人工定義建立新局；全部外衣同組以固定全角色finalize的TARGET讀取。"""
    data = copy.deepcopy(data)
    for no in (301,302,303):
        data.charas[no].cflag.update({40:100,41:202 if combined else 200,42:300})
    return data


def start_initial_battle(ctx):
    """保留初始化衣裝；只注入人工BOSS遭遇前態，無自然遭遇聲明。"""
    from test_transformation_parts import prepare_battle
    prepare_battle(ctx)
    ctx.state.target = 1


@pytest.mark.parametrize("combined,inner", [(False,300),(True,0)])
def test_real_editor_finalize_shop_and_battle(data,tmp_path,combined,inner):
    from eragvt.game.session import GameSession,Phase
    from eragvt.game.battle.train import run_train
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    from test_transformation_parts import QuietOutput
    s = GameSession(editor_data(data,combined),tmp_path,rng=GameRng(76),narration=NullNarrationService())
    s.out = QuietOutput()
    # FIRSTSETTING_CHARA_MAIN:305–309、CLOTH_SETTING_INNER:568–571，清零後99返回；
    # CHARA_MAKE_MAIN:206–210完成，再由EVENTFIRST:135再次FINALIZE。
    for value in (0,1,1,18,2,99):
        s.input(value)
        assert_ages(s.state)
    assert s.state.charas[1].cflag[42] == 0
    s.input(1000)
    assert s.state.charas[1].cflag[42] == inner
    s.input(1)
    assert s.phase == Phase.SHOP
    assert s.state.charas[1].cflag[42] == inner
    ctx = s._ctx()
    start_initial_battle(ctx)
    gen = run_train(ctx)
    assert next(gen) is None
    st,c = s.state,s.state.charas[1]
    assert c.tcvarn[24] == (0 if combined else 80)
    before,rng = st.to_json(),st.rng.snapshot()
    assert gen.send(998) is None
    assert st.to_json() == before and st.rng.snapshot() == rng
    assert gen.send(0) is None
    assert c.cflag[1] == 1 and c.cflag[42] == inner
    assert st.temp.cloth[0] == int(combined)
    assert st.target == 1
    assert all([x.base[40],x.base[41],x.maxbase[40],x.maxbase[41]] == [25]*4 for x in st.charas)
    assert_ages(st)
    gen.close()
    s.close()
