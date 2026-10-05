"""S55：expected 依 CHARA_MAKE.ERB@CHARA_MAKE_MAIN 與各 FIRSTSETTING 原文。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameState, GameRng
from eragvt.state.savefile import GlobalStore
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game.action import Ctx
from eragvt.game.creation_menu import creation_menu, common_setting
from eragvt.game.input_request import TextInputRequest

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

@pytest.fixture
def ctx(data):
    st=GameState.new(data,GameRng(42))
    st.swap_chara(0,1)
    st.del_chara(1)
    for _ in range(3): st.add_chara(data,0)
    return Ctx(st,data,TextOutput(),NullNarrationService(),GlobalStore())

@pytest.mark.parametrize("choice,key,values",[(1005,821,range(9)),(1006,822,range(10)),(1007,823,range(11))])
def test_languages_races(ctx,choice,key,values):
    # FIRSTSETTING_CHARA:1024–1068、FIRSTSETTING_CHARA_SYUZOKU:168–182。
    for value in values:
        g=common_setting(ctx,choice)
        next(g)
        with pytest.raises(StopIteration):g.send(value)
        assert ctx.state.flag[key]==value+(choice==1007)
        assert ctx.state.result[0]==0 # 隱含 RETURN

@pytest.mark.parametrize("choice,flag,slot",[(1001,5,10),(1002,6,11),(1004,7,12)])
def test_manual_strings(ctx,choice,flag,slot):
    g=common_setting(ctx,choice);next(g)
    assert isinstance(g.send(2),TextInputRequest)
    assert isinstance(g.send(""),TextInputRequest)
    with pytest.raises(StopIteration):g.send("測試%RESULTS%{ARG}")
    assert ctx.state.flag[flag]==1
    assert ctx.state.savestr[slot]=="測試%RESULTS%{ARG}"
    assert ctx.state.results[0]=="測試%RESULTS%{ARG}"

@pytest.mark.parametrize("choice,key",[(1008,824),(1009,825)])
@pytest.mark.parametrize("before,after",[(0,1),(1,0),(-1,0),(2,0)])
def test_toggle(ctx,choice,key,before,after):
    ctx.globals.mem.global_[22 if key==824 else 23]=before
    g=creation_menu(ctx);next(g);g.send(choice)
    assert ctx.state.flag[key]==after

def test_global_save_load_reset(ctx):
    g=creation_menu(ctx);next(g)
    g.send(1008);g.send(1009)
    g.send(170)
    assert isinstance(g.send(0),TextInputRequest)
    g.send("")
    assert ctx.globals.mem.global_[22]==ctx.globals.mem.global_[23]==1
    g.send(190)
    assert ctx.state.flag[824]==ctx.state.flag[825]==0
    g.send(180)
    assert ctx.state.flag[824]==ctx.state.flag[825]==1

def test_return_mode(ctx):
    g=creation_menu(ctx);next(g)
    with pytest.raises(StopIteration) as done:g.send(999)
    assert done.value.value==-1 and ctx.state.result[0]==-1

def test_title_original_empty_random(ctx):
    # TITLE:83–85 先清 RESULTS 再 WHILE != 空，因此不進迴圈。
    before=ctx.state.rng.snapshot()
    g=common_setting(ctx,1001);next(g);g.send(1);g.send(0)
    with pytest.raises(StopIteration):g.send(1)
    assert ctx.state.flag[5]==0 and ctx.state.savestr[10]==""
    assert ctx.state.rng.snapshot()==before

@pytest.mark.parametrize("genre",range(9))
def test_genre(ctx,genre):
    g=common_setting(ctx,1003);next(g);g.send(1);g.send(genre)
    with pytest.raises(StopIteration):g.send(1)
    assert ctx.state.flag[820]==genre+1

@pytest.mark.parametrize('choice,key,slot',[(1001,5,10),(1002,6,11),(1004,7,12)])
@pytest.mark.parametrize('action',[0,99])
def test_disable_cancel_keeps_text(ctx,choice,key,slot,action):
    ctx.state.flag[key]=1;ctx.state.savestr[slot]='既有值'
    g=common_setting(ctx,choice);next(g)
    before=len(ctx.out.lines)
    g.send(-1)
    assert len(ctx.out.lines)==before+1
    with pytest.raises(StopIteration):g.send(action)
    assert ctx.state.flag[key]==(0 if action==0 else 1)
    assert ctx.state.savestr[slot]=='既有值'
    assert ctx.state.result[0]==(99 if action==99 else 0)

@pytest.mark.parametrize('choice,key',[(1005,821),(1006,822),(1007,823)])
def test_language_invalid_cancel(ctx,choice,key):
    ctx.state.flag[key]=3
    g=common_setting(ctx,choice);next(g)
    count=len(ctx.out.lines)
    g.send(-1)
    assert len(ctx.out.lines)>count+1 # 原文 GOTO loop 重印
    with pytest.raises(StopIteration):g.send(99)
    assert ctx.state.flag[key]==(0 if choice==1007 else 3)

@pytest.mark.parametrize('choice,key,slot',[(1001,5,10),(1002,6,11),(1004,7,12)])
def test_manual_999(ctx,choice,key,slot):
    ctx.state.savestr[slot]='既有值'
    g=common_setting(ctx,choice);next(g);g.send(2)
    with pytest.raises(StopIteration):g.send('999')
    assert ctx.state.savestr[slot]==('999' if choice==1004 else '既有值')
    assert ctx.state.flag[key]==1

@pytest.mark.parametrize('action',[99,-1,5])
def test_genre_outer_original_fallthrough(ctx,action):
    ctx.state.flag[820]=3
    g=common_setting(ctx,1003);next(g)
    with pytest.raises(StopIteration):g.send(action)
    assert ctx.state.flag[820]==3 and ctx.state.result[0]==0

def test_genre_inner_cancel_and_hidden_keep(ctx):
    ctx.state.flag[820]=3
    for actions in ((1,99),(1,-1,2,2),(1,2,0,4,2)):
        g=common_setting(ctx,1003);next(g)
        for action in actions[:-1]:g.send(action)
        with pytest.raises(StopIteration):g.send(actions[-1])
        assert ctx.state.flag[820]==3

def test_crown_preset_writes_master_cstr_and_retains_flag_quirk(ctx):
    # CROWN:23–25；RANDOMNAMING_SELECT:435–437，ARG:2=0 寫 MASTER。
    class Rng:
        def rand(self,n):assert n==50;return 0
    ctx.state.rng=Rng()
    g=common_setting(ctx,1002);next(g);g.send(1);g.send(0);g.send(0)
    assert ctx.state.charas[0].cstr[202]==ctx.data.str_defaults[500]
    g.send(0) # CROWN:45 清 FLAG:6；再次選詞並不重新設 1。
    g.send(1);g.send(0)
    with pytest.raises(StopIteration):g.send(1)
    assert ctx.state.savestr[11]==ctx.data.str_defaults[600]
    assert ctx.state.flag[6]==0

def test_changing_call_rng_and_results(ctx):
    class Rng:
        def __init__(self):self.calls=[]
        def rand(self,n):self.calls.append(n);return len(self.calls)-1
    rng=Rng();ctx.state.rng=rng;ctx.state.results[0]='殘值'
    g=common_setting(ctx,1004);next(g);g.send(1)
    assert ctx.state.savestr[12]=='変身！'
    g.send(0)
    with pytest.raises(StopIteration):g.send(1)
    assert ctx.state.savestr[12]=='装着！' and rng.calls==[19,19]
    assert ctx.state.results[0]=='殘值'

def test_global_cancel_and_disk_reload(ctx,tmp_path):
    ctx.globals=GlobalStore.in_dir(tmp_path)
    ctx.globals.mem.global_[22]=1;ctx.globals.mem.globals_[15]='保存文字';ctx.globals.save()
    g=creation_menu(ctx);next(g)
    g.send(190);g.send(170);g.send(-1);g.send(99)
    fresh=GlobalStore.in_dir(tmp_path);assert fresh.load()
    assert fresh.mem.global_[22]==1 and fresh.mem.globals_[15]=='保存文字'
    ctx.globals=fresh;g.send(180)
    assert ctx.state.flag[824]==1 and ctx.state.savestr[10]=='保存文字'

def test_main_invalid_and_buttons(ctx):
    g=creation_menu(ctx);next(g)
    buttons={v for line in ctx.out.lines for _,v in line.buttons}
    assert {1000,999,200,170,180,190,*range(1001,1010),1,101,501}<=buttons
    count=len(ctx.out.lines);g.send(-1)
    assert len(ctx.out.lines)==count+1 and ctx.state.result[0]==-1

def test_preset_cancel_zero_and_other_halt(ctx):
    g=creation_menu(ctx);next(g);g.send(200);g.send(99)
    assert all(c.no==0 for c in ctx.state.charas[1:])
    g.send(200);g.send(0);g.send(0) # 拒絕後再選
    g.send(0);g.send(-1);g.send(1)
    assert [c.no for c in ctx.state.charas[1:]]==[301,302,303]
    from eragvt.game.creation_text import PRESETS
    other=next(i for kind,i in PRESETS if kind=='SETUMEI' and i!=0)
    g.send(200);g.send(other)
    with pytest.raises(NotImplementedError,match='SHOKISET_SELECT'):g.send(1)
    assert ctx.state.charanum==1 # SHOKISET:31–35 先刪除原角色再呼叫套組。

@pytest.mark.parametrize('choice',[6,7,8])
def test_dynamic_preset_description_stops_before_rng(ctx,choice):
    # 三個 SHOKISET_SETUMEI:8 都 SELECTCASE RAND:4；不可冒充純文字抽取。
    from eragvt.game.creation_text import PRESETS
    assert ('NAME',choice) in PRESETS and ('SETUMEI',choice) not in PRESETS
    before=ctx.state.rng.snapshot()
    g=creation_menu(ctx);next(g);g.send(200)
    with pytest.raises(NotImplementedError,match=f'SHOKISET_SETUMEI_{choice}'):
        g.send(choice)
    assert ctx.state.rng.snapshot()==before and ctx.state.charanum==4

@pytest.mark.parametrize('choice',[1,101,501])
def test_unported_entries_explicit_stop(ctx,choice):
    g=creation_menu(ctx);next(g)
    with pytest.raises(NotImplementedError):g.send(choice)
    if choice==101:
        assert ctx.state.charas[1].name=='汎用キャラ(♂)'
        assert ctx.state.charas[1].talent[ctx.data.index_of('TALENT','オトコ')]==1

def test_main_named_character_display_results(ctx):
    # CHARA_MAKE:95–116 呼叫兩個 STRING 查詢；:120–124 最後覆寫汎用人數。
    c=ctx.state.charas[3]
    c.callname='測試角色';c.talent[201]=1;c.talent[16]=1
    c.talent[ctx.data.index_of('TALENT','変身能力')]=-1
    ctx.state.result[1]=88;ctx.state.results[1]='保留'
    g=creation_menu(ctx);next(g)
    assert ctx.state.result[0]==2 and ctx.state.result[1]==88
    assert ctx.state.results[0]==ctx.data.names['TALENT'][16]
    assert ctx.state.results[1]=='保留'
    assert any('[人間] [真面目] [非戦闘員]' in line.text for line in ctx.out.lines)

def test_extract_reproducible():
    import runpy
    from pathlib import Path
    root=Path(__file__).parents[1]
    tool=runpy.run_path(str(root/'tools/extract_creation_menu.py'))
    assert tool['extract']()==(root/'src/eragvt/game/creation_text.py').read_text(encoding='utf-8')

def test_mode_return_preserves_original_flag8(data,tmp_path):
    from eragvt.game.session import GameSession
    s=GameSession(data,tmp_path,narration=NullNarrationService())
    s.input(0);s.input(0)
    assert s.state.charanum==4 and s.state.flag[8]==3
    s.input(999)
    assert s.state.charanum==1 and s.state.flag[8]==3
    assert (s.state.flag[100],s.state.flag[101],s.state.flag[852])==(0,0,5000)
    s.input(0)
    assert s.state.charanum==4 and s.state.flag[8]==6
    s.input(1000);s.input(1)
    assert s.phase.name=='SHOP'

@pytest.mark.parametrize('preset',[0,1])
def test_web_settings_save_reload(data,tmp_path,preset):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(7))
    client=TestClient(app)
    def send(v):
        response=client.post('/api/input',json={'value':v});assert response.status_code==200
        return response.json()
    for v in (0,preset,1001,2,'共通主題',1003,1,2,1,1008,1009,170,0,'',1000,1):send(v)
    assert app.state.session.phase.name=='SHOP'
    st=app.state.session.state
    assert (st.flag[820],st.flag[824],st.flag[825],st.savestr[10])==(3,1,1,'共通主題')
    for v in (200,5):send(v)
    st.flag[824]=0
    for v in (300,5):send(v)
    assert app.state.session.state.flag[824]==1
    fresh=create_app(data,tmp_path,rng_factory=lambda:GameRng(7))
    c2=TestClient(fresh)
    for v in (0,0):c2.post('/api/input',json={'value':v})
    st=fresh.state.session.state
    assert (st.flag[820],st.flag[824],st.flag[825],st.savestr[10])==(3,1,1,'共通主題')
