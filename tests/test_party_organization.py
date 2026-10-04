"""S46：expected 依 SHOP_ORGANIZE_PARTY.ERB@SHOP_ORGANIZE_PARTY:98–167 推導。"""
import copy

import pytest
from test_clothing_menu import data, ctx
from eragvt.game.party_organization import party_organization_gen
from eragvt.game.session import GameSession, Phase
from eragvt.game import shop
from eragvt.state import FixedRng, GameRng, dump_save, load_save
from eragvt.text import NullNarrationService


def start(ctx):
    ctx.state.target = 0
    gen = party_organization_gen(ctx)
    next(gen)
    return gen


@pytest.mark.parametrize('value',[-1,0,4,49,51,99,101,999])
def test_invalid(ctx,value):
    gen=start(ctx); gen.send(value)
    assert ctx.state.target==0


@pytest.mark.parametrize('status,expected',[(0,1),(1,0),(2,0),(3,0),(4,1),(9,0),(10,0),(11,0),(12,1)])
def test_selection_states(ctx,status,expected):
    """:129 僅排除 1/2/3/9，:132 另排除 10/11；4 仍可手打。"""
    ctx.state.charas[1].cflag[0]=status
    gen=start(ctx); gen.send(1)
    assert ctx.state.target==expected


def test_select_deselect_and_invalid_keeps_selection(ctx):
    gen=start(ctx); gen.send(1); gen.send(-1)
    assert ctx.state.target==1
    gen.send(1)
    assert ctx.state.target==0


@pytest.mark.parametrize('selected,status,expected',[(0,0,0),(1,1,1),(1,2,1),(1,3,1),(1,4,1),(1,9,1),(1,10,1),(1,11,1)])
def test_toggle_invalid_target(ctx,selected,status,expected):
    gen=start(ctx); ctx.state.target=selected
    ctx.state.charas[1].cflag[0]=status
    ctx.state.charas[1].cflag[999]=1
    gen.send(100)
    assert ctx.state.target==expected
    assert ctx.state.charas[1].cflag[999]==1


@pytest.mark.parametrize('flag,expected,schedule',[(0,1,5),(1,0,103),(2,0,103)])
def test_toggle(ctx,flag,expected,schedule):
    c=ctx.state.charas[1]; c.cflag[999]=flag; c.cflag[100]=5
    gen=start(ctx); gen.send(1); gen.send(100)
    assert (c.cflag[999],c.cflag[100],ctx.state.target)==(expected,schedule,0)


@pytest.mark.parametrize('active,expected',[(5,1),(6,0),(7,0)])
def test_party_capacity(ctx,active,expected):
    st=ctx.state
    while st.charanum<active+2: st.charas.append(copy.deepcopy(st.charas[2]))
    for c in st.charas[1:]: c.cflag[999]=1; c.cflag[0]=0
    st.charas[1].cflag[999]=0
    gen=start(ctx); gen.send(1); gen.send(100)
    assert st.charas[1].cflag[999]==expected and st.target==0


@pytest.mark.parametrize('a,b',[(1,2),(2,1)])
@pytest.mark.parametrize('left,right',[(0,0),(0,1),(1,0),(1,1),(2,0)])
def test_swap_order(ctx,a,b,left,right):
    """:152–164：先交換非 MASTER 的 RELATION 欄，再交換出場位元，最後角色。"""
    st=ctx.state; st.assi=1; st.flag[798]=2
    originals=list(st.charas)
    for i,c in enumerate(st.charas):
        for j in range(st.charanum): c.relation[j]=i*10+j
        c.cflag[100]=5
    st.charas[1].cflag[999]=left; st.charas[2].cflag[999]=right
    gen=start(ctx); gen.send(a); gen.send(b)
    assert st.charas[1] is originals[2] and st.charas[2] is originals[1]
    assert [st.charas[i].relation[j] for i in range(4) for j in range(4)]==[
        0,1,2,3,20,22,21,23,10,12,11,13,30,32,31,33]
    assert [st.charas[i].cflag[999] for i in (1,2)]==[left,right]
    assert [st.charas[i].cflag[100] for i in (1,2)]==[103 if left==0 else 5,103 if right==0 else 5]
    assert (st.target,st.assi,st.flag[798])==(0,1,2)


@pytest.mark.parametrize('selected,incoming,expected',[(0,10,0),(0,11,0),(10,0,0),(11,0,0),(0,1,1),(10,1,1)])
def test_blocked_swap_precedence(ctx,selected,incoming,expected):
    gen=start(ctx); ctx.state.target=1
    ctx.state.charas[1].cflag[0]=selected; ctx.state.charas[2].cflag[0]=incoming
    before=list(ctx.state.charas); gen.send(2)
    assert ctx.state.charas==before and ctx.state.target==expected


@pytest.mark.parametrize('target,random,expected',[(0,0,1),(0,2,3),(2,None,2)])
@pytest.mark.parametrize('reserve,view',[(False,0),(True,1)])
def test_finish(ctx,target,random,expected,reserve,view):
    st=ctx.state; st.flag[61]=1; st.result[6]=89; st.results[0]='保留'
    for c in st.charas[1:]: c.cflag[999]=1
    if reserve: st.charas[3].cflag[999]=0
    st.rng=FixedRng([] if random is None else [random])
    gen=start(ctx); st.target=target
    with pytest.raises(StopIteration): gen.send(50)
    assert (st.target,st.flag[61],st.result[0],st.result[6],st.results[0])==(expected,view,0,89,'保留')
    assert st.rng.snapshot()==[]


@pytest.mark.parametrize('status,flag,shown',[(0,0,True),(10,0,True),(11,0,True),(1,0,False),(4,0,False),(9,0,False),(0,1,False),(0,2,False)])
def test_reserve_list(ctx,status,flag,shown):
    c=ctx.state.charas[1]; c.cflag[0]=status; c.cflag[999]=flag; c.callname='候補測試'
    shop.shop_show_status_reserve_list(ctx.state,ctx.data,ctx.out,True)
    assert ('候補測試' in '\n'.join(line.text for line in ctx.out.lines))==shown


def test_original_reversed_warning(ctx):
    ctx.state.charas[1].cflag[999]=0
    gen=start(ctx); gen.send(1)
    text='\n'.join(line.text for line in ctx.out.lines[-45:])
    assert '[100]パーティに加える' in text
    assert 'パーティ人数が最大に達しているため、パーティに加えられません。' in text


def test_session_visible_and_save(data,tmp_path):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,0,1,50): s.input(value)
    assert s.phase==Phase.TURN and s.state.target==0
    assert '[50] パーティ編成を完了する' in str(s.screen())
    s.input(1); s.input(100)
    assert '<< 控えメンバー >>' in str(s.screen())
    s.input(1); s.input(2)
    saved,_=load_save(dump_save(s.state))
    assert saved.to_json()==s.state.to_json()
    s.input(50)
    assert s.phase==Phase.SHOP


@pytest.mark.parametrize('count,status,allowed',[(2,0,False),(3,0,True),(3,1,False),(3,10,True),(3,11,True)])
def test_shop_entry_guard(data,tmp_path,count,status,allowed):
    """SHOP.ERB@USERSHOP:208–213：SAFE 計數包含 10/11；不要求 ACTIVE。"""
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,0,1): s.input(value)
    s.state.charas=s.state.charas[:count]
    for c in s.state.charas[1:]: c.cflag[0]=status
    s.input(50)
    assert (s.phase==Phase.TURN)==allowed
    assert ('[50] パーティ編成を完了する' in '\n'.join(line.text for line in s.screen()))==allowed


@pytest.mark.parametrize('reserve',[False,True])
@pytest.mark.parametrize('form,color',[(False,'#00ff96'),(True,'#fab432')])
@pytest.mark.parametrize('bulk',[0,1])
def test_selected_marker(ctx,reserve,form,color,bulk):
    st=ctx.state; st.target=1; st.flag[9]=bulk; st.charas[1].cflag[999]=0 if reserve else 1
    fn=shop.shop_show_status_reserve_list if reserve else shop.shop_show_status_party_list
    fn(st,ctx.data,ctx.out,form)
    selected=[seg for line in ctx.out.lines for part in line.parts for seg in part.segments if '◆' in seg.text]
    assert bool(selected)==(bulk==0)
    if selected: assert selected[0].color==color
    assert ctx.out.color is None


def test_web_party_buttons(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(0),narration=NullNarrationService())
    client=TestClient(app)
    for value in (0,0,1,50,1):
        assert client.post('/api/input',json={'value':value}).status_code==200
    html=client.get('/').text
    assert 'パーティ編成を完了する' in html and 'パーティから外す' in html
    assert '選択中のキャラ：なし' not in html
    client.post('/api/input',json={'value':100})
    html=client.get('/').text
    assert '控えメンバー' in html and '選択中のキャラ：なし' in html
    client.post('/api/input',json={'value':50})
    assert app.state.session.phase==Phase.SHOP


def test_show_shop_reserve_view(data,tmp_path):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,0,1): s.input(value)
    s.state.charas[3].cflag[999]=0
    s.state.charas[3].callname='候補表示確認'
    s.state.flag[61]=1
    s._show_shop()
    assert '候補表示確認' in '\n'.join(line.text for line in s.screen())
    s.state.flag[61]=0
    s._show_shop()
    assert '候補表示確認' not in '\n'.join(line.text for line in s.screen())
