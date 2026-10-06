"""S45：expected依 ERB/インターミッション画面/SHOP_ENHANCING.ERB@HOME_ENHANCING 推導。"""
import pytest
from test_clothing_menu import data, ctx
from eragvt.game.facilities import facilities_gen
from eragvt.game.input_request import TextInputRequest
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng, FixedRng, dump_save, load_save
from eragvt.text import NullNarrationService


def answer(gen,value):
    request=gen.send(value)
    while isinstance(request,TextInputRequest): request=gen.send('')
    return request


def leave(gen,value=999):
    with pytest.raises(StopIteration): gen.send(value)


@pytest.mark.parametrize('choice,slot,unit',[(0,50,5000),(1,51,1000),(2,52,10000),(4,54,5)])
@pytest.mark.parametrize('level',[0,1,2,3,4])
@pytest.mark.parametrize('delta',[-1,0])
def test_level_cost(ctx,choice,slot,unit,level,delta):
    """@HOME_ENHANCING:54–144、296–325；下一級費用=unit*(當前級+1)。"""
    st=ctx.state; st.flag[slot]=level; cost=unit*(level+1)
    if choice==4: st.flag[200]=cost+delta; st.money=71
    else: st.money=cost+delta; st.flag[200]=71
    st.result[6]=89; st.results[0]='保留'; target=st.target
    gen=facilities_gen(ctx); next(gen); answer(gen,choice); answer(gen,0)
    assert st.flag[slot]==level+int(delta==0)
    assert (st.flag[200] if choice==4 else st.money)==(0 if delta==0 else cost-1)
    assert (st.money if choice==4 else st.flag[200])==71
    leave(gen)
    assert (st.result[0],st.result[6],st.results[0],st.target)==(0,89,'保留',target)


@pytest.mark.parametrize('choice,slot',[(0,50),(1,51),(2,52),(4,54)])
@pytest.mark.parametrize('level',[5,6])
def test_maximum(ctx,choice,slot,level):
    st=ctx.state; st.flag[slot]=level; st.money=9999999; st.flag[200]=999
    gen=facilities_gen(ctx); next(gen); answer(gen,choice); leave(gen)
    assert (st.flag[slot],st.money,st.flag[200])==(level,9999999,999)


@pytest.mark.parametrize('choice,slot',[(0,50),(1,51),(2,52),(4,54)])
def test_decline_and_bad_confirmation(ctx,choice,slot):
    """各INPUT_LOOP_SELECT只接受0/1；999也不是確認畫面的取消值。"""
    st=ctx.state; st.flag[slot]=2; before=dump_save(st)
    gen=facilities_gen(ctx); next(gen); answer(gen,choice)
    for value in (-1,2,999): answer(gen,value)
    answer(gen,1); leave(gen)
    assert dump_save(st)==before


# 原作:186–281，順序、價格與prerequisite皆直接抄錄規則，非讀Python常數。
RELAX=[(0,1,0,500),(0,512,1,4500),(0,1024,513,8500),(0,2048,1537,100000),
       (1,2,0,12000),(1,4,2,95000),(2,8,0,25800),(3,16,0,50000),
       (4,32,0,100000),(5,64,0,200000),(5,128,64,500000),(6,256,0,1500000)]


@pytest.mark.parametrize('choice,bit,prior,cost',RELAX)
@pytest.mark.parametrize('delta',[-1,0])
def test_relax_purchase(ctx,choice,bit,prior,cost,delta):
    st=ctx.state; st.flag[53]=prior; st.money=cost+delta
    gen=facilities_gen(ctx); next(gen); answer(gen,3); answer(gen,choice)
    assert st.flag[53]==(prior|bit if delta==0 else prior)
    assert st.money==(0 if delta==0 else cost-1)
    answer(gen,99); leave(gen)


@pytest.mark.parametrize('choice,owned',[(0,3585),(1,6),(2,8),(3,16),(4,32),(5,192),(6,256)])
def test_already_owned(ctx,choice,owned):
    """:186–286：該按鈕系列全部持有時輸入屬錯值，不能重扣款。"""
    st=ctx.state; st.flag[53]=owned; st.money=2000000
    gen=facilities_gen(ctx); next(gen); answer(gen,3); answer(gen,choice)
    assert st.flag[53]==owned and st.money==2000000
    answer(gen,99); leave(gen)


@pytest.mark.parametrize('mask,can_enter',[(4095,False),(8191,True)])
def test_all_owned_exact_mask(ctx,mask,can_enter):
    """:148只比較==4095，不把其他高位當成完成。"""
    ctx.state.flag[53]=mask
    gen=facilities_gen(ctx); next(gen); answer(gen,3)
    if can_enter: answer(gen,99)
    leave(gen)


def test_bad_main_and_relax_inputs(ctx):
    gen=facilities_gen(ctx); next(gen)
    for value in (-1,5,99): answer(gen,value)
    answer(gen,3)
    for value in (-1,7,999): answer(gen,value)
    answer(gen,99); leave(gen)


def buy_level(ctx,choice,slot):
    ctx.state.money=100000; ctx.state.flag[200]=100
    gen=facilities_gen(ctx); next(gen); answer(gen,choice); answer(gen,0); leave(gen)


def test_purchased_rest_effect(ctx):
    """ACTION_REST.ERB@REST:9–18、59–65；Lv1→2，1000HP回復40%+200=600。"""
    from eragvt.game.action import rest
    st=ctx.state; st.target=1; c=st.charas[1]; c.talent.clear(); c.cflag.clear()
    c.maxbase[0]=1000; c.base[0]=0; st.flag[51]=1
    buy_level(ctx,1,51); rest(ctx)
    assert c.base[0]==600


def test_purchased_training_effect(ctx):
    """ACTION_TRAINING.ERB@TRAINING_DOWNTAIRYOKU:329–337；Lv1耗200→Lv2耗180。"""
    from eragvt.game.shop import training_downtairyoku
    st=ctx.state; st.target=1; c=st.charas[1]; c.talent.clear(); c.maxbase[0]=1000; c.base[50]=1000
    st.flag[50]=1; buy_level(ctx,0,50)
    assert training_downtairyoku(ctx.data,st,1)==180


def test_purchased_defence_effect(ctx):
    """SHOP_TURNEND.ERB@DAILY_DEFENCE_CHANGE:441–443；Lv0→1每回合加5。"""
    from eragvt.game.turnend import daily_defence_change
    st=ctx.state; st.flag[52]=0; st.flag[852]=0; st.flag[41]=0
    buy_level(ctx,2,52); daily_defence_change(ctx)
    assert st.flag[852]==5


def test_purchased_research_effect(ctx):
    """CLOTHDATAアウター_特殊.ERB@CLOTH_CUSTOMIZE_OPTION_199:323–334；Lv0→1解鎖。"""
    from eragvt.game.clothing_custom import category_blocked,choice_blocked
    st=ctx.state; st.flag[54]=0; buy_level(ctx,4,54)
    assert not category_blocked(199,0,[0]*4,st.flag[54])
    assert not choice_blocked(199,1,1,[0]*4,0,st.flag[54])
    assert choice_blocked(199,1,2,[0]*4,0,st.flag[54])


def test_purchased_relax_effect(ctx):
    """SHOP_TURNEND.ERB@RECOVERY_OVER_TIME:662–663；購入觀葉植物且RAND2=0恢復疲勞1。"""
    from eragvt.game.turnend import recovery_over_time
    st=ctx.state; st.flag[53]=0; st.money=500; st.time=1
    for c in st.charas: c.talent.clear(); c.cflag.clear()
    st.charas[1].cflag[99]=10; st.rng=FixedRng([0])
    gen=facilities_gen(ctx); next(gen); answer(gen,3); answer(gen,0); answer(gen,99); leave(gen)
    recovery_over_time(ctx)
    assert st.charas[1].cflag[99]==9


@pytest.mark.parametrize('gameover',[False,True])
def test_session(data,tmp_path,gameover):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,1, 1000,1,0): s.input(v)
    if gameover: s.state.flag[0]=0
    s.input(150)
    assert s.phase==(Phase.SHOP if gameover else Phase.TURN)
    if not gameover:
        assert '施設を拡張します' in '\n'.join(line.text for line in s.screen())
        s.input(999); assert s.phase==Phase.SHOP


def test_visible_wait_and_save(ctx):
    """PRINTW在重繪前等待，RESULT(S)不受Enter影響；FLAG50–54皆沿用現有存檔。"""
    st=ctx.state; st.flag[50]=1; st.money=10000; st.result[8]=7; st.results[0]='保留'
    gen=facilities_gen(ctx); next(gen); answer(gen,0)
    assert isinstance(gen.send(0),TextInputRequest)
    assert st.money==0 and st.flag[50]==2 and st.result[0]==0 and st.results[0]=='保留'
    answer(gen,''); leave(gen)
    loaded,_=load_save(dump_save(st))
    assert loaded.flag[50]==2 and loaded.money==0 and loaded.result[8]==7


@pytest.mark.parametrize('choice,slot,cost',[(0,50,'10000'),(1,51,'2000'),(2,52,'20000'),(4,54,'10')])
def test_interpolation_and_confirm_buttons(ctx,choice,slot,cost):
    """原作:44–48、60/91/122/303；無效輸入後CLEARLINE只刪輸入及錯誤。"""
    st=ctx.state; st.flag[slot]=1
    gen=facilities_gen(ctx); next(gen); answer(gen,choice)
    output='\n'.join(line.text for line in ctx.out.lines)
    assert cost in output and '\\@' not in output and '{FLAG:' not in output and '{MONEY}' not in output
    answer(gen,2)
    assert ctx.out.lines[-2].text=='[0]はい' and ctx.out.lines[-1].text=='[1]いいえ'
    answer(gen,1); leave(gen)


@pytest.mark.parametrize('mask,choice,bit,cost',[(512,0,1,500),(4,1,2,12000),(128,5,64,200000)])
def test_incomplete_upgrade_mask(ctx,mask,choice,bit,cost):
    """:186–281 ELSEIF優先序；非連續bit仍從該按鈕第一個未持有者購買，不自動補齊。"""
    st=ctx.state; st.flag[53]=mask; st.money=cost
    gen=facilities_gen(ctx); next(gen); answer(gen,3); answer(gen,choice)
    assert st.flag[53]==mask|bit and st.money==0
    answer(gen,99); leave(gen)


def test_purchase_final_relax_returns_main(ctx):
    """:147–150成功購入最後一項後，等待「已無可追加」才回主選單。"""
    st=ctx.state; st.flag[53]=4095-256; st.money=1500000
    gen=facilities_gen(ctx); next(gen); answer(gen,3)
    assert isinstance(gen.send(6),TextInputRequest)
    assert st.flag[53]==4095
    assert isinstance(gen.send(''),TextInputRequest)
    assert 'もう追加できるものがありません' in ctx.out.lines[-2].text
    answer(gen,''); leave(gen)


def test_session_wait_visible_and_no_active_needed(data,tmp_path):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,1, 1000,1,0): s.input(v)
    st=s.state; st.charas=st.charas[:1]; st.target=0; st.money=10000; st.flag[50]=1
    st.result[7]=456; st.results[0]='保留'
    for v in (150,0,0): s.input(v)
    assert s.phase==Phase.TURN and s.input_kind=='text'
    assert '設備レベルが上がりました！' in '\n'.join(line.text for line in s.screen())
    assert st.flag[50]==2 and st.money==0
    s.input('任意輸入'); assert s.input_kind=='number'
    assert (st.result[0],st.result[7],st.results[0])==(0,456,'保留')
    s.input(999); assert s.phase==Phase.SHOP


def test_web_wait_empty_enter(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(0),narration=NullNarrationService())
    client=TestClient(app)
    for v in (0,1, 1000,1,0): client.post('/api/input',json={'value':v})
    st=app.state.session.state; st.money=10000; st.flag[50]=1
    for v in (150,0,0): client.post('/api/input',json={'value':v})
    html=client.get('/').text
    assert '設備レベルが上がりました！' in html and '按 Enter 繼續' in html
    response=client.post('/input',data={'value':''})
    assert response.status_code==200 and app.state.session.input_kind=='number'
    assert 'Lv.2' in response.text
