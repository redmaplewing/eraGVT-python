"""S54：DEFAULT@CHARA_MAKE_INITIALIZE:8–164／SET_FEAT_DEFAULT:1500–1776 原文推導。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameState, FixedRng, GameRng
from eragvt.text import TextOutput
from eragvt.game.action import Ctx
from eragvt.game.chara_make import initialize_race, initialize_personality
from eragvt.narration.service import CatalogNarrationService

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService.from_csv_dir(default_csv_dir(), data)

class Rolls(FixedRng):
    def __init__(self, values):
        super().__init__(values)
        self.bounds=[]
    def rand(self,n):
        self.bounds.append(n)
        return super().rand(n)

def fresh(data,catalog,rolls):
    st=GameState.new(data,Rolls(rolls));st.add_chara(data,0)
    return Ctx(st,data,TextOutput(),catalog),st.charanum-1

# FEAT_ABLE_F:92–239，各族的六項候選；不從 Python 的候選表反推。
FEATS=[
    ("平凡","巻き込まれ体質","秘められし力","ラッキーチャーム","祝福","不屈"),
    ("攻勢構築","秘められし力","生粋の戦士","ホットスタート","狩人の勘","心眼"),
    ("魔力貯蔵","ラッキーチャーム","空中浮遊","フルバースト","不老長寿","叡智の冠"),
    ("超反応","剛腕","空中浮遊","ホットスタート","フルバースト","スタミナ"),
    ("神器の担い手","有翼","空中浮遊","祝福","叡智の冠","背徳の烙印"),
    ("闘争本能","有翼","生粋の戦士","不屈","狩人の勘","背徳の烙印"),
    ("溢れる生命力","生粋の戦士","剛腕","不屈","スタミナ","不老長寿"),
    ("精霊交信","小さな体躯","不老長寿","叡智の冠","心眼","人外の美貌"),
    ("獣性の証","小さな体躯","スタミナ","狩人の勘","心眼","エアマスター"),
    ("夜魔の貴族","剛腕","有翼","人外の美貌","背徳の烙印","エアマスター"),
    ("超反応","剛腕","空中浮遊","ホットスタート","フルバースト","スタミナ"),
]
@pytest.mark.parametrize("setting",range(1,12))
def test_each_race_all_remaining_feats(data,catalog,setting):
    # 枠 3、不選預設；FOR 終點開始時求值，所以全部六項都拿（吸血鬼已一項）。
    n=5 if setting==10 else 6
    ctx,sel=fresh(data,catalog,[1,1,0]+[0]*n);st=ctx.state;c=st.charas[sel]
    st.flag[823]=setting;st.flag[824]=1
    st.results[0]="殘值";st.result[9]=789
    initialize_race(st,data,sel,ctx=ctx)
    assert {data.names['TALENT'][i] for i in range(1100,1300) if c.talent[i]}==set(FEATS[setting-1])
    assert st.rng.bounds==[8,4,4]+list(range(n,0,-1))
    assert st.rng.snapshot()==[] and st.temp.randchoose[0]==0
    assert (st.result[0],st.result[9],st.results[0])==(0,789,"殘值")

@pytest.mark.parametrize("setting,rolls,expected,bounds",[
    (1,[0,1,0,1],("平凡",),[8,4,4,2]),
    (2,[0,1,0],("攻勢構築",),[8,4,4]),
    (3,[0,1,0],("魔力貯蔵",),[8,4,5]),
    (4,[0,1,0,1],("超反応",),[8,4,2,3]),
    (5,[0,1,1],("神器の担い手",),[8,4,4]),
    (6,[0,1,1],("闘争本能",),[8,4,4]),
    (7,[0,1,1],("溢れる生命力",),[8,4,4]),
    (8,[0,1,1],("精霊交信",),[8,4,4]),
    (9,[0,1,1],("獣性の証",),[8,4,4]),
    (10,[0,1,0],("夜魔の貴族","剛腕","有翼"),[8,4,4]),
    (11,[0,1,0,1],("超反応",),[8,4,2,3]),
])
def test_race_preset_short_circuit(data,catalog,setting,rolls,expected,bounds):
    ctx,sel=fresh(data,catalog,rolls);st=ctx.state;st.flag[823]=setting;st.flag[824]=1
    initialize_race(st,data,sel,ctx=ctx)
    assert {data.names['TALENT'][i] for i in range(1100,1300) if st.charas[sel].talent[i]}==set(expected)
    assert st.rng.bounds==bounds and st.rng.snapshot()==[]

@pytest.mark.parametrize("flag",[0,2,-1])
def test_only_feat_flag_one_enables(data,catalog,flag):
    ctx,sel=fresh(data,catalog,[]);st=ctx.state;st.flag[823]=1;st.flag[824]=flag
    initialize_race(st,data,sel,ctx=ctx)
    assert st.rng.bounds==[] and not any(st.charas[sel].talent[i] for i in range(1100,1300))

def test_existing_race_unchanged(data,catalog):
    ctx,sel=fresh(data,catalog,[]);st=ctx.state;c=st.charas[sel]
    c.talent[201]=1;c.talent[data.index_of('TALENT','心眼')]=1;st.flag[824]=1;st.flag[823]=10
    initialize_race(st,data,sel,ctx=ctx)
    assert c.talent[201]==1 and c.talent[210]==0 and st.rng.bounds==[]
    assert c.talent[data.index_of('TALENT','心眼')]==1

# 有效 .ERB 的 KOJO_0_COLOR 定義共 12 個；.ERB.org 不算另一個定義。
COLORS=(10,12,13,14,16,17,20,21,22,24,25,27)
@pytest.mark.parametrize("personality",COLORS)
def test_existing_color_executes_and_resets(data,catalog,personality):
    ctx,sel=fresh(data,catalog,[personality-10]);st=ctx.state;st.flag[825]=1
    ctx.out.set_color("#00007b");st.result[1]=77;st.results[0]='保留'
    initialize_personality(st,data,sel,ctx=ctx)
    assert st.charas[sel].talent[personality]==1
    assert st.rng.bounds==[18] and st.rng.snapshot()==[]
    assert ctx.out.color==TextOutput().color and ctx.out.lines==[]
    assert st.result[0]==personality and st.result[1]==77 and st.results[0]=='保留'

@pytest.mark.parametrize("missing",[11,15,18,19,23,26])
@pytest.mark.parametrize("flag",[1,2,-1])
def test_missing_color_redraw_keeps_earlier_talent(data,catalog,missing,flag):
    ctx,sel=fresh(data,catalog,[missing-10,17]);st=ctx.state;st.flag[825]=flag
    initialize_personality(st,data,sel,ctx=ctx)
    c=st.charas[sel]
    assert c.talent[missing]==c.talent[27]==1
    assert st.result[0]==missing # SEIKAKU_CHECK 取第一個，並非最後抽到的 27。
    assert st.rng.bounds==[18,18] and st.rng.snapshot()==[]

@pytest.mark.parametrize("duplicates,draws",[(0,100),(1,50),(2,34)])
def test_retry_counter_includes_each_prior_duplicate(data,catalog,duplicates,draws):
    ctx,sel=fresh(data,catalog,[1]*draws);st=ctx.state
    while sel<duplicates+1:st.add_chara(data,0);sel+=1
    for i in range(1,duplicates+1):st.charas[i].talent[11]=1
    st.flag[825]=1;ctx.out.set_color("#00007b")
    initialize_personality(st,data,sel,ctx=ctx)
    assert st.rng.bounds==[18]*draws and st.rng.snapshot()==[]
    assert ctx.out.color=="#00007b" # 缺函式不 RESETCOLOR。
    assert st.charas[sel].talent[11]==1 and st.result[0]==11

@pytest.mark.parametrize("enabled",[0,1])
def test_existing_personality_not_overwritten(data,catalog,enabled):
    ctx,sel=fresh(data,catalog,[]);st=ctx.state;c=st.charas[sel]
    c.talent[24]=1;c.cflag[8]=32;st.flag[825]=enabled
    st.result[0]=55;before=c.base.copy()
    initialize_personality(st,data,sel,ctx=ctx)
    assert c.base==before and c.cflag[8]==32 and st.result[0]==55 and st.rng.bounds==[]


def test_color_16_clears_original_narration_variable(data,catalog):
    # ★KOJO_0_16_真面目/■メニュー.ERB@KOJO_0_COLOR_16:24–34：註解函式標頭不形成新函式。
    ctx,sel=fresh(data,catalog,[6]);st=ctx.state;st.flag[825]=1
    key=("真面目_フラグ_シチュ",(0,));st.temp.narr[key]="原值"
    initialize_personality(st,data,sel,ctx=ctx)
    assert st.temp.narr[key]=="" and catalog.failures==[]

@pytest.mark.parametrize("preset",[0,1])
def test_web_global_generation_settings_and_save_load(data,tmp_path,preset):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.state.savefile import GlobalStore,GameIdentity
    store=GlobalStore.in_dir(tmp_path,GameIdentity.from_data(data))
    store.mem.global_[21]=1;store.mem.global_[22]=1;store.mem.global_[23]=1;store.save()
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(7))
    client=TestClient(app)
    def send(value):
        response=client.post('/api/input',json={'value':value});assert response.status_code==200
        return response.json()
    send(0);send(preset);assert send(1)['phase']=='shop'
    st=app.state.session.state
    assert st.flag[824]==st.flag[825]==1
    traits=[c.talent.copy() for c in st.charas]
    if preset==0:
        for c in st.charas[1:]:
            assert any(c.talent[data.index_of('TALENT',name)] for name in FEATS[0])
            assert any(c.talent[n] for n in COLORS)
    assert app.state.session.narration.failures==[]
    send(200);send(0);send(300);assert send(0)['phase']=='shop'
    assert [c.talent for c in app.state.session.state.charas]==traits
    assert app.state.session.state.flag[824]==app.state.session.state.flag[825]==1

def test_noninteractive_opening_loads_catalog_lazily(data):
    from eragvt.game.opening import event_first
    from eragvt.state.savefile import GlobalStore
    store=GlobalStore();store.mem.global_[22]=store.mem.global_[23]=1
    st=GameState.new(data,GameRng(7));out=TextOutput();out.set_color('#123456')
    event_first(st,data,store=store,out=out)
    assert st.flag[824]==st.flag[825]==1
    assert all(any(c.talent[n] for n in COLORS) for c in st.charas[1:])
    assert out.color==TextOutput().color


def test_duplicate_success_does_not_force_redraw(data,catalog):
    # DEFAULT:118–133：重複只加計數；成功仍在同輪 BREAK。
    ctx,sel=fresh(data,catalog,[0]);st=ctx.state;st.flag[825]=1
    st.charas[1].talent[10]=1
    initialize_personality(st,data,sel,ctx=ctx)
    assert st.charas[sel].talent[10]==1 and st.rng.bounds==[18]

def test_disabled_kojo_filter_does_not_call_catalog(data):
    ctx,sel=fresh(data,None,[1]);st=ctx.state;st.flag[825]=0
    initialize_personality(st,data,sel,ctx=ctx)
    assert st.charas[sel].talent[11]==1 and st.rng.bounds==[18]

def test_existing_feat_excluded_from_draw(data,catalog):
    ctx,sel=fresh(data,catalog,[1,1,0]+[0]*5);st=ctx.state;c=st.charas[sel]
    st.flag[823]=st.flag[824]=1;c.talent[data.index_of('TALENT','平凡')]=2
    initialize_race(st,data,sel,ctx=ctx)
    assert c.talent[data.index_of('TALENT','平凡')]==2
    assert st.rng.bounds==[8,4,4,5,4,3,2,1]

def test_color_call_side_effects_observed_before_reset(data,catalog):
    class Observe:
        def run_function(self,ctx,name):
            assert name=='KOJO_0_COLOR_10'
            ok=catalog.run_function(ctx,name)
            assert ctx.out.color=='#b4dcfa' # KOJO_0_10_臆病.ERB@KOJO_0_COLOR_10:15–16。
            assert ctx.state.result[0]==0 # 函式終端 RETURN 0。
            return ok
    ctx,sel=fresh(data,Observe(),[0]);ctx.state.flag[825]=1;ctx.state.result[0]=777
    initialize_personality(ctx.state,data,sel,ctx=ctx)
    assert ctx.out.color is None and ctx.state.result[0]==10


def test_no_catalog_stops_instead_of_inventing_missing_functions(data):
    from eragvt.text import NullNarrationService
    ctx,sel=fresh(data,NullNarrationService(),[]);ctx.state.flag[825]=1
    with pytest.raises(NotImplementedError,match='catalog'):
        initialize_personality(ctx.state,data,sel,ctx=ctx)
    assert ctx.state.rng.bounds==[]

def test_existing_but_failed_color_is_not_missing(data,catalog):
    class Broken:
        def run_function(self,ctx,name):return False
    service=Broken();service.catalog=catalog.catalog
    ctx,sel=fresh(data,service,[0]);ctx.state.flag[825]=1
    with pytest.raises(NotImplementedError,match='存在但無法執行'):
        initialize_personality(ctx.state,data,sel,ctx=ctx)
    assert ctx.state.rng.bounds==[18]
