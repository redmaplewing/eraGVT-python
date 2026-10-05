"""S43：expected 由 ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB 推導。"""
import pytest
from test_clothing_menu import data, ctx
from eragvt.game.recruitment import recruitment_gen, recruitment_allowed
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng
from eragvt.text import NullNarrationService

@pytest.mark.parametrize("answer", [99, -1, 3, 100])
def test_cancel_invalid(ctx, answer):
    """@TSUIKAYOUSEI_NORMAL:19–21、155–157；只有99取消，其餘重讀。"""
    st=ctx.state; before=(st.charanum,st.flag[250],st.target,st.money)
    gen=recruitment_gen(ctx); next(gen)
    if answer==99:
        with pytest.raises(StopIteration): gen.send(answer)
        assert st.result[0]==0
    else:
        gen.send(answer)
        assert st.result[0]==answer
    assert (st.charanum,st.flag[250],st.target,st.money)==before

@pytest.mark.parametrize("sex", [0,1,2])
@pytest.mark.parametrize("feat", [0,1,2])
def test_join(ctx, sex, feat):
    """@TSUIKAYOUSEI_NORMAL:21–35、126–154：免費，加入一次，恢復TARGET。"""
    st=ctx.state; count=st.charanum; target=st.target; st.money=-1; st.flag[250]=7
    gen=recruitment_gen(ctx); next(gen); gen.send(sex)
    if sex!=2: gen.send(99)
    assert st.charanum==count+1 and st.flag[250]==8
    assert st.target==count
    if feat==0:
        gen.send(0)
        with pytest.raises(StopIteration): gen.send(0)
    else:
        with pytest.raises(StopIteration): gen.send(feat)
    c=st.charas[-1]
    assert (st.money,st.target,st.result[0])==(-1,target,0)
    assert c.cflag[999]==1 and c.cflag[240]==count
    assert c.abl[ctx.data.index_of('ABL','レベル')]==1
    if sex==1: assert c.talent[ctx.data.index_of('TALENT','オトコ')]==1

@pytest.mark.parametrize("count", [1,29,30,31])
@pytest.mark.parametrize("enabled", [False,True])
def test_gate(ctx,count,enabled):
    """SHOP.ERB@USERSHOP:293；DIM.ERH:25 登録最大人数=30。"""
    st=ctx.state
    while st.charanum<count: st.add_chara(ctx.data,0)
    st.charas=st.charas[:count]
    st.flag[0]=512 if enabled else 0
    assert recruitment_allowed(st)==(enabled and count<=29)

@pytest.mark.parametrize("active,status,expected",[(5,0,1),(6,0,0),(6,1,1),(6,10,0),(6,11,0),(6,9,1)])
def test_party_capacity(ctx,active,status,expected):
    """@TSUIKAYOUSEI_NORMAL:145–148；CHARANUM.ERB@CHARANUM_SAFE_PARTYCHECK:114–121。"""
    st=ctx.state
    while st.charanum<=active: st.add_chara(ctx.data,0)
    for c in st.charas[1:]: c.cflag[999]=1; c.cflag[0]=0
    st.charas[1].cflag[0]=status
    gen=recruitment_gen(ctx); next(gen); gen.send(2)
    with pytest.raises(StopIteration): gen.send(1)
    assert st.charas[-1].cflag[999]==expected

@pytest.mark.parametrize("enabled",[False,True])
def test_session_entry(data,tmp_path,enabled):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,0, 1000,1): s.input(v)
    s.state.flag[0]=512 if enabled else 0
    before=s.state.charanum
    s.input(180)
    if enabled:
        s.input(2); s.input(1)
    assert s.phase==Phase.SHOP
    assert s.state.charanum==before+int(enabled)

@pytest.mark.parametrize("sex,initialized",[(0,True),(1,True),(2,False)])
def test_initialization_order_and_items(ctx,sex,initialized):
    """@TSUIKAYOUSEI_NORMAL:29–39；FIRSTSETTING_CHARA_MAIN:9–21、344–350。"""
    st=ctx.state
    st.item[101]=7; st.item[701]=9
    for i in range(4): st.savestr[i]="保留"
    gen=recruitment_gen(ctx); next(gen); gen.send(sex)
    if sex!=2: gen.send(99)
    c=st.charas[-1]
    assert (c.callname!='汎用キャラ')==initialized
    assert (st.result[0]>0)==initialized
    assert (st.item[101],st.item[701])==(7,9)
    assert [st.savestr[i] for i in range(4)]==(['']*4 if initialized else ['保留']*4)
    with pytest.raises(StopIteration): gen.send(1)
    assert c.callname!='汎用キャラ'

@pytest.mark.parametrize("choice", [0,1,2])
def test_invalid_feat_inputs_do_not_add_again(ctx,choice):
    """@TSUIKAYOUSEI_NORMAL:137–138只回到第二個INPUT，並不重做ADDCHARA。"""
    st=ctx.state; before=st.charanum
    gen=recruitment_gen(ctx); next(gen); gen.send(choice)
    if choice!=2: gen.send(99)
    for value in (-1,3,99):
        gen.send(value)
        assert st.charanum==before+1 and st.flag[250]==1
        assert st.result[0]==value
    with pytest.raises(StopIteration): gen.send(1)


def test_cancel_preserves_other_result_cells(ctx):
    """Process.cs:249–252、Process.ScriptProc.cs:61–67均只寫RESULT:0。"""
    ctx.state.result[1]=123; ctx.state.results[0]='保留'
    gen=recruitment_gen(ctx); next(gen)
    with pytest.raises(StopIteration): gen.send(99)
    assert (ctx.state.result[0],ctx.state.result[1],ctx.state.results[0])==(0,123,'保留')


def test_feat_manual_toggle_limit(ctx):
    """@TSUIKAYOUSEI_NORMAL:101–123最多3項，超出仍等待，可取消已選項。"""
    st=ctx.state
    gen=recruitment_gen(ctx); next(gen); gen.send(0); gen.send(99)
    race=st.result[0]
    from eragvt.game.firstsetting import feat_able
    options=[i for i in range(100,300) if feat_able(ctx,race,i+1000)]
    assert len(options)>=4
    gen.send(0)
    for i in options[:4]: gen.send(i)
    gen.send(0)  # 4項不得確認
    gen.send(options[0])  # 取消第一項
    with pytest.raises(StopIteration): gen.send(0)
    c=st.charas[-1]
    assert [c.talent[1000+i] for i in options[:4]]==[0,1,1,1]

@pytest.mark.parametrize("setting,expected",[(0,'汎用キャラ'),(3,'あなた')])
def test_narrative_callname(ctx,setting,expected):
    """コモン関数.ERB@PRINT_CALLNAME:268–285；引数1省略は地文用。"""
    gen=recruitment_gen(ctx); next(gen); gen.send(2)
    ctx.state.charas[-1].cflag[6]=setting
    with pytest.raises(StopIteration): gen.send(1)
    assert expected+'にはフィートを設定しません' in [line.text for line in ctx.out.lines]
