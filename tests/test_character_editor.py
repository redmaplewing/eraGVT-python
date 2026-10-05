"""S60：expected 來自 FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN。"""
import pytest
from test_clothing_menu import data, ctx
from eragvt.game.character_editor import character_editor


def test_confirm_restores_inventory_and_clears_savestr(ctx):
    """主入口:9–34、318–353；未命名ITEM仍在退出時歸零。"""
    st=ctx.state
    st.item[101]=7; st.item[699]=8; st.item[701]=9
    for i in range(4): st.savestr[i]='暫存'
    target=st.target
    gen=character_editor(ctx,1); next(gen)
    assert st.item[101]==1
    assert st.savestr[0]=='暫存'
    with pytest.raises(StopIteration): gen.send(99)
    assert st.item[101]==7 and st.item[701]==9
    assert st.item[699]==(8 if ctx.data.items.get(699) and ctx.data.items[699].name else 0)
    assert [st.savestr[i] for i in range(4)]==['']*4
    assert st.target==target and st.result[0]==0


@pytest.mark.parametrize('choice,unique,transform,status,restricted',[
    (0,1,1,0,0),(4,0,1,0,1),(4,1,1,0,0),(7,1,1,0,0),
    (8,1,1,0,0),(10,1,1,0,0),(11,0,0,0,0),(17,0,1,3,0),
    (24,0,-1,0,0),(999,0,1,0,1),(-1,0,1,0,0),(1000,0,1,0,0),
])
def test_gates_reject_without_effect(ctx,choice,unique,transform,status,restricted):
    """主入口:237–336；不符合條件留在同一INPUT，沒有重新繪製/亂數。"""
    st=ctx.state; c=st.charas[1]
    c.talent[ctx.data.index_of('TALENT','固有キャラ')]=unique
    c.talent[ctx.data.index_of('TALENT','変身能力')]=transform
    c.cflag[0]=status
    gen=character_editor(ctx,1,restricted=restricted); next(gen)
    before=len(ctx.out.lines)
    gen.send(choice)
    assert len(ctx.out.lines)<=before+1
    with pytest.raises(StopIteration): gen.send(99)


def test_callname_return_edit_and_reentry(ctx):
    """主入口:245–251、CALLNAME:1072–1105；即時更新，再入保留。"""
    c=ctx.state.charas[1]; old=c.callname
    gen=character_editor(ctx,1); next(gen)
    gen.send(2); gen.send(99)
    assert c.callname==old
    gen.send(2); gen.send(1); gen.send('試驗呼稱')
    assert c.callname=='試驗呼稱'
    with pytest.raises(StopIteration): gen.send(99)
    gen=character_editor(ctx,1); next(gen)
    assert c.callname=='試驗呼稱'
    with pytest.raises(StopIteration): gen.send(99)


def test_trans_callname_requires_name_flag(ctx):
    """主入口:277–287：變身名未啟用時12直接重畫，不開子選單。"""
    c=ctx.state.charas[1]
    c.talent[ctx.data.index_of('TALENT','変身能力')]=1
    c.cflag[2]=0; c.cflag[3]=0
    gen=character_editor(ctx,1); next(gen); gen.send(12)
    assert c.cflag[3]==0
    with pytest.raises(StopIteration): gen.send(99)


def test_clothing_cancel_and_confirm(ctx):
    """主入口:296–311；衣裝取消[0]及確認[1]回同一編輯器。"""
    c=ctx.state.charas[1]; old=c.cflag[40]
    gen=character_editor(ctx,1); next(gen)
    gen.send(16); gen.send(101); gen.send(0)
    assert c.cflag[40]==old
    gen.send(16); gen.send(101); gen.send(1)
    assert c.cflag[40]==101
    with pytest.raises(StopIteration): gen.send(99)

def test_name_manual_and_default(ctx):
    """NAME:550–613、687–693：姓名同步CALLNAME及原本相同的變身呼稱。"""
    from eragvt.game.character_name import character_name
    c=ctx.state.charas[1]; c.cstr[1]=c.callname
    gen=character_name(ctx,1); next(gen)
    gen.send(1); gen.send('測試')
    with pytest.raises(StopIteration):gen.send('名稱')
    assert (c.name,c.callname,c.cstr[200],c.cstr[10],c.cstr[1])==('測試名稱','名稱','名稱','測試','名稱')


@pytest.mark.parametrize('r,expected',[(0,'苗字呼稱'),(1,'呼稱・苗字'),(99,'原本')])
def test_name_order_returns_to_name_menu(ctx,r,expected):
    """NAME:622–644：順序子頁返回姓名選單，不修改CALLNAME。"""
    from eragvt.game.character_name import character_name
    c=ctx.state.charas[1];c.name='原本';c.cstr[10]='苗字';c.callname='呼稱'
    gen=character_name(ctx,1);next(gen);gen.send(3)
    gen.send(r) # PRINTW等待
    gen.send('')
    assert c.name==expected and c.callname=='呼稱'
    with pytest.raises(StopIteration):gen.send(99)


def test_random_name_draw_order(ctx):
    """NAME_RANDOM:811–968、1000–1020：日文20次姓/名交錯，RETURN語言。"""
    from eragvt.game.character_name import random_character_name
    class Rng:
        calls=[]
        def rand(self,n):self.calls.append(n);return 0
    ctx.state.rng=Rng()
    gen=random_character_name(ctx,1);next(gen);gen.send(200)
    with pytest.raises(StopIteration):gen.send(0)
    assert ctx.state.rng.calls==[500,500]*20
    assert ctx.state.results[0]==ctx.data.str_defaults[3000]+ctx.data.str_defaults[12000]
    assert ctx.state.result[0]==0 and ctx.state.result[1]==0

@pytest.mark.parametrize('choice,number,expected,subjective',[(0,0,0,0),(1,0,1,0),(2,0,2,1),(3,0,3,0),(99,0,-2,0),(90,301,301,0)])
def test_kojo_select(ctx,choice,number,expected,subjective):
    """KOJO:1142–1176；99是停用口上，2同時啟用主觀。"""
    from eragvt.game.character_editor import kojo_setting
    c=ctx.state.charas[1];c.no=number
    c.talent[ctx.data.index_of('TALENT','主観視点')]=0
    gen=kojo_setting(ctx,1);next(gen);gen.send(0);gen.send(choice)
    with pytest.raises(StopIteration):gen.send('')
    assert c.talent[ctx.data.index_of('TALENT','口上設定')]==expected
    assert c.talent[ctx.data.index_of('TALENT','主観視点')]==subjective


def test_weapon_decode_and_draw_residuals(ctx):
    """MAIN:23–34、112–137；杯數只改RESULT:0/RESULTS:0，INITIALIZE不再跑。"""
    c=ctx.state.charas[1];st=ctx.state
    c.cstr[15]='測試劍//未使用//連続';c.cstr[16]='測試弓//未使用//装甲'
    # 選用明確身體前態，不從Python輸出反推expected。
    from eragvt.game.body import HEIGHT,WEIGHT,BUST,WAIST,HIP,BREAST_WEIGHT
    for slot,value in ((HEIGHT,1600),(WEIGHT,500),(BUST,800),(WAIST,600),(HIP,800),(BREAST_WEIGHT,10)):c.base[slot]=value
    for name,value in (('身長指定',1600),('体重指定',500),('胸囲指定',800),('胴囲指定',600),('腰囲指定',800),('胸の重量指定',10)):c.talent[ctx.data.index_of('TALENT',name)]=value
    before=st.rng.snapshot()
    gen=character_editor(ctx,1);next(gen)
    assert (c.cstr[5],c.cstr[6],c.cstr[15],c.cstr[16],c.cstr[17])==('測試劍','測試弓','','','')
    assert st.result[0]==0
    assert st.result[2]==1600 and st.result[3]==500
    drawing=len(ctx.out.lines);residual=(list(st.result[i] for i in range(1,8)),st.results[0])
    gen.send(-777)
    assert len(ctx.out.lines)==drawing and st.rng.snapshot()==before
    assert ([st.result[i] for i in range(1,8)],st.results[0])==residual
    with pytest.raises(StopIteration):gen.send(99)

@pytest.mark.parametrize('sex',[0,1])
def test_opening_editor_web_and_recruitment(data,tmp_path,sex):
    """CHARA_MAKE:142–145/202–204、TSUIKAYOUSEI_NORMAL:35的真實Web呼叫鏈。"""
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.state import GameRng
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(7))
    client=TestClient(app)
    def send(value):
        response=client.post('/api/input',json={'value':value})
        assert response.status_code==200
        return response.json()
    for value in (0,0,101 if sex else 1,2,1,'入口呼稱',99,1):
        send(value)
    assert app.state.session.state.charas[1].callname=='入口呼稱'
    for value in (99,1000,1):send(value)
    assert app.state.session.phase.name=='SHOP'
    st=app.state.session.state
    st.flag[0]|=512
    before=st.charanum
    for value in (180,sex,2,99,2,1,'追加呼稱',99,1):send(value)
    assert app.state.session.phase.name=='SHOP'
    assert st.charanum==before+1 and st.charas[-1].callname=='追加呼稱'


def test_extract_character_text_reproducible():
    import runpy
    from pathlib import Path
    root=Path(__file__).parents[1]
    assert runpy.run_path(str(root/'tools/extract_character_editor.py'))['extract']()==(root/'src/eragvt/game/character_editor_text.py').read_text(encoding='utf-8')
