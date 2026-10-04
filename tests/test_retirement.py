"""S44：expected 直接由 ERB/ヒロイン関連/INTAI.ERB 與 INTAI_CHARA_LIST.ERB 推導。"""
import pytest
from test_clothing_menu import data, ctx
from eragvt.game.retirement import retirement_gen, retirement_list, retirement_allowed, retirement_report
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng, dump_save, load_save
from eragvt.text import NullNarrationService


def finish(gen, value):
    from eragvt.game.input_request import TextInputRequest
    try:
        request=gen.send(value)
        while True:
            assert isinstance(request,TextInputRequest)
            request=gen.send('')
    except StopIteration:
        pass


def clean(ctx, points=600):
    c=ctx.state.charas[1]
    c.talent.clear(); c.abl.clear(); c.base.clear(); c.cflag.clear()
    c.base[ctx.data.index_of('BASE','攻撃')]=points
    return c


@pytest.mark.parametrize('enabled,count,menu,expected',[
    (False,4,169,False),(False,4,170,False),(True,1,169,True),
    (True,1,170,False),(True,2,170,True),(True,2,169,True)])
def test_gate(ctx,enabled,count,menu,expected):
    """SHOP.ERB@USERSHOP:289–292。"""
    ctx.state.flag[0]=512 if enabled else 0
    ctx.state.charas=ctx.state.charas[:count]
    assert retirement_allowed(ctx.state,menu)==expected


@pytest.mark.parametrize('status,valid',[(0,True),(1,True),(2,False),(3,False),(4,True),(9,True),(10,True),(11,True)])
def test_selection(ctx,status,valid):
    """INTAI_CHARA_LIST:12–15、40–47；只有狀態2/3拒絕，取消保留TARGET。"""
    st=ctx.state; st.target=2; st.charas[1].cflag[0]=status
    gen=retirement_gen(ctx); next(gen); gen.send(1)
    assert st.target==(1 if valid else 2)
    if valid: finish(gen,1)
    else: finish(gen,999)
    assert st.result[0]==0


@pytest.mark.parametrize('value',[-10,-1,0,4,1000])
def test_selection_invalid(ctx,value):
    """INTAI_CHARA_LIST:42；範圍1至CHARANUM-1。"""
    st=ctx.state; before=st.target
    gen=retirement_gen(ctx); next(gen); gen.send(value)
    assert st.target==before and st.result[0]==value
    finish(gen,999)


@pytest.mark.parametrize('answers',[(1,),(2,),(0,0),(0,2)])
def test_confirmation_cancel(ctx,answers):
    """INTAI@CHARA_INTAI:6–21／INPUT_ROOP:44：2合法，但不執行。"""
    st=ctx.state; before=list(st.charas); gen=retirement_gen(ctx)
    next(gen); gen.send(1)
    for value in answers[:-1]: gen.send(value)
    finish(gen,answers[-1])
    assert st.target==1 and st.charas==before and st.flag[251]==0 and st.savestr[50]==''


def test_confirmation_invalid_then_delete(ctx):
    """INTAI:34–37；DELCHARA只壓縮角色列表，不修其他角色CFLAG索引。"""
    st=ctx.state; clean(ctx); removed=st.charas[1]; following=st.charas[2]
    following.cflag[9]=3; following.cflag[240]=71; st.assi=3
    st.result[4]=87; st.results[0]='保留'; st.money=123
    gen=retirement_gen(ctx); next(gen); gen.send(1)
    for value in (-1,3,999): gen.send(value)
    assert st.charas[1] is removed
    gen.send(0)
    for value in (-1,3,999): gen.send(value)
    finish(gen,1)
    assert st.charanum==3 and st.charas[1] is following and st.target==0
    assert (following.cflag[9],following.cflag[240],st.assi)==(3,71,3)
    assert (st.flag[251],st.flag[252],st.money,st.result[0],st.result[4],st.results[0])==(1,1,123,0,87,'保留')
    assert '自主除隊' in st.savestr[50] and removed.name in st.savestr[50]


@pytest.mark.parametrize('points,expected',[(747,252),(746,252),(580,252),(579,252),(480,252),(479,253),(380,253),(379,253),(280,253),(279,253),(180,253),(179,253),(80,253),(79,253),(-1,253)])
def test_strength_thresholds(ctx,points,expected):
    """INTAI@MASSAGE_INTAI:87–110、318–330；LOCAL0=8時任何耗損皆至少後援。"""
    clean(ctx,points); ctx.state.target=1
    retirement_report(ctx)
    assert [ctx.state.flag[i] for i in (252,253,254,255)]==[int(i==expected) for i in (252,253,254,255)]


@pytest.mark.parametrize('kind,value,points,flag',[
    ('Ｃ感覚',3,600,252),('Ｃ感覚',3,479,253),
    ('従順',4,600,253),('従順',3,600,252),
    ('触手中毒',1,280,253),('触手中毒',1,279,253),
    ('噴乳中毒',1,80,253),('射精中毒',1,79,253)])
def test_report_score(ctx,kind,value,points,flag):
    """INTAI:131–215、318–330：LOCAL0從1依條件加1/2/4。"""
    c=clean(ctx,points); c.abl[ctx.data.index_of('ABL',kind)]=value; ctx.state.target=1
    retirement_report(ctx)
    assert ctx.state.flag[flag]==1 and sum(ctx.state.flag[i] for i in range(252,256))==1


@pytest.mark.parametrize('status,traits,reason,flag',[
    (9,{'毀滅倒計時':-10},'生贄虐殺',255),(9,{'毀滅倒計時':-11},'残虐処刑',255),
    (9,{'苗床化':1},'触手吸収',255),(9,{},'触手喰食',255),
    (1,{},'敗北幽閉',255),(4,{'四肢欠損':1},'残虐拷問',255),(4,{},'拉致監禁',255),
    (0,{'四肢欠損':1},'廃品除隊',None),(0,{'繁殖袋':1},'人格破滅',254),
    (0,{'四肢欠損':1,'繁殖袋':1},'人格破滅',254),
    (0,{'完堕ち':1},'自主除隊',252)])
def test_report_precedence(ctx,status,traits,reason,flag):
    """INTAI:222–332；缺肢分支不加252–255，停用的特殊處置分支不啟用。"""
    c=clean(ctx); c.cflag[0]=status; ctx.state.target=1
    for name,value in traits.items(): c.talent[ctx.data.index_of('TALENT',name)]=value
    retirement_report(ctx)
    assert reason in ctx.state.savestr[50]
    assert sum(ctx.state.flag[i] for i in range(252,256))==int(flag is not None)
    if flag: assert ctx.state.flag[flag]==1


@pytest.mark.parametrize('rows',['','甲<br> <br>','甲<br> <br>乙<br> <br>'])
def test_list_readonly(ctx,rows):
    """INTAI@CHAR_INTAI_LIST:344–361；空名簿及多列都不變動存檔。"""
    st=ctx.state; st.savestr[50]=rows; before=dump_save(st)
    retirement_list(ctx)
    assert dump_save(st)==before and st.result[0]==0


def test_append_and_persistence(ctx):
    """INTAI:334–341 SAVESTR50以原HTML形式追加；JSON保存既有欄位。"""
    clean(ctx); st=ctx.state; st.target=1; st.savestr[50]='舊記錄<br> <br>'
    retirement_report(ctx)
    saved,_=load_save(dump_save(st))
    assert saved.savestr[50]==st.savestr[50] and saved.flag[252]==1
    assert saved.savestr[50].startswith('舊記錄<br> <br>　　') and saved.savestr[50].endswith(' <br> <br>')


@pytest.mark.parametrize('menu,enabled',[(169,False),(169,True),(170,False),(170,True)])
def test_session_entry(data,tmp_path,menu,enabled):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,0,1): s.input(v)
    s.state.flag[0]=512 if enabled else 0
    count=s.state.charanum; s.input(menu)
    if enabled and menu==170:
        for v in (1,0,1): s.input(v)
    while s.phase==Phase.TURN and s.input_kind=='text': s.input('')
    assert s.phase==Phase.SHOP and s.state.charanum==count-int(enabled and menu==170)


@pytest.mark.parametrize('points,expected',[(280,253),(279,254),(180,254),(179,254),(80,254),(79,254)])
def test_longterm_threshold(ctx,points,expected):
    """INTAI:131–215：感覺3且中毒1使LOCAL0=1+0+2+0=3；LOCAL1>=5才療養。"""
    c=clean(ctx,points); ctx.state.target=1
    for name in ('Ｃ感覚','触手中毒'): c.abl[ctx.data.index_of('ABL',name)]=3
    retirement_report(ctx)
    assert ctx.state.flag[expected]==1


@pytest.mark.parametrize('values,line',[
    ((5,5,5,5),135),((4,4,4,4),138),
    ((0,0,5,0),143),((0,5,0,0),145),((0,0,0,5),147),((5,0,0,0),149),
    ((0,0,3,0),154),((0,3,0,0),156),((0,0,0,3),158),((3,0,0,0),160)])
def test_sense_branch_text(ctx,values,line):
    """INTAI:131–164：原文分支順序及文字，expected行號從ERB逐項選定。"""
    from eragvt.game.retirement_text import TEXT
    c=clean(ctx); ctx.state.target=1
    for name,value in zip(('Ｃ感覚','Ｖ感覚','Ａ感覚','Ｂ感覚'),values):
        c.abl[ctx.data.index_of('ABL',name)]=value
    retirement_report(ctx)
    expected=TEXT['INTAI.ERB',line][1].replace('%CALLNAME%',c.callname).replace('%STR:2500%',ctx.data.str_defaults[2500])
    assert expected in plain(ctx.out)


def plain(out):
    return '\n'.join(''.join(seg.text for part in line.parts for seg in part.segments) for line in out.lines)


@pytest.mark.parametrize('name,line,kind',[
    ('近距離得意',66,'TALENT'),('中距離得意',68,'TALENT'),('遠距離得意',70,'TALENT'),
    ('従順',175,'ABL'),('欲望',177,'ABL'),('奉仕精神',180,'ABL'),('マゾっ気',184,'ABL'),
    ('触手中毒',205,'ABL'),('自慰中毒',207,'ABL'),('精液中毒',209,'ABL'),('噴乳中毒',211,'ABL'),('射精中毒',213,'ABL')])
def test_other_branch_text(ctx,name,line,kind):
    """INTAI:64–75、174–215；保留第一個符合條件的分支。"""
    from eragvt.game.retirement_text import TEXT
    c=clean(ctx); ctx.state.target=1
    (c.abl if kind=='ABL' else c.talent)[ctx.data.index_of(kind,name)]=4
    retirement_report(ctx)
    expected=TEXT['INTAI.ERB',line][1].replace('%STR:2500%',ctx.data.str_defaults[2500])
    assert expected in plain(ctx.out)


def test_html_record_display_and_old_save(ctx):
    """INTAI:334–341、356；HTML_PRINT沿用HtmlManager.cs:326–331的br換行。"""
    st=ctx.state; loaded,_=load_save(dump_save(st))
    assert loaded.savestr[50]=='' and 50 not in loaded.savestr
    st.savestr[50]='　　甲                  自主除隊                 存命 <br> <br>　　乙                  後勤引退                 存命 <br> <br>'
    retirement_list(ctx)
    rendered=plain(ctx.out)
    assert '<br>' not in rendered and '甲' in rendered and '乙' in rendered
    assert any('甲' in line and '乙' not in line for line in rendered.splitlines())
    assert any('乙' in line and '甲' not in line for line in rendered.splitlines())


def test_retire_all_then_roster(ctx):
    """INTAI@OLD_GIRL:34–37；連續刪除至只有MASTER，紀錄仍完整。"""
    st=ctx.state; names=[c.name for c in st.charas[1:]]
    while st.charanum>1:
        gen=retirement_gen(ctx); next(gen); gen.send(1); gen.send(0); finish(gen,1)
        assert st.target==0
    assert st.flag[251]==len(names) and not retirement_allowed(st,170)
    for name in names: assert name in st.savestr[50]
    retirement_list(ctx)
    assert st.charanum==1


@pytest.mark.parametrize('record',['','甲<br> <br>乙<br> <br>'])
def test_session_roster_visible_until_enter(data,tmp_path,record):
    """INTAI:348、360 PRINTW必須在下一個LB前等確認，不能回SHOP把名簿遮掉。"""
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,0,1): s.input(v)
    st=s.state; st.flag[0]=512; st.savestr[50]=record; st.result[0]=83; st.results[0]='保留'
    s.input(169)
    assert s.phase==Phase.TURN and s.input_kind=='text'
    assert ('甲' if record else '現在記録はありません！') in '\n'.join(line.text for line in s.screen())
    assert st.result[0]==83 and st.results[0]=='保留'
    s.input('')
    assert s.phase==Phase.SHOP and s.input_kind=='number'


@pytest.mark.parametrize('answer',['','abc','0'])
def test_report_visible_before_deletion(data,tmp_path,answer):
    """INTAI:335、342等待先於OLD_GIRL:34–37刪除；EnterKey不寫RESULT/RESULTS。"""
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for v in (0,0,1): s.input(v)
    st=s.state; st.flag[0]=512; st.flag.set_bit(801,3,False)
    count=st.charanum; st.result[5]=78; st.results[0]='保留'
    for v in (170,1,0,1): s.input(v)
    waits=0
    while s.phase==Phase.TURN:
        assert s.input_kind=='text' and st.charanum==count and st.flag[251]==0
        assert (st.result[0],st.result[5],st.results[0])==(1,78,'保留')
        if st.savestr[50]:
            assert st.charas[1].name in '\n'.join(line.text for line in s.screen())
        waits+=1; assert waits<=7
        s.input(answer)
    assert waits==6 and st.charanum==count-1 and st.flag[251]==1


def test_web_empty_enter(data,tmp_path):
    """Web表單的文字通道允許空白Enter；名簿在回SHOP前可見。"""
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(0),narration=NullNarrationService())
    client=TestClient(app)
    for v in (0,0,1): client.post('/api/input',json={'value':v})
    app.state.session.state.flag[0]=512
    client.post('/api/input',json={'value':169})
    html=client.get('/').text
    assert '按 Enter 繼續' in html and '現在記録はありません！' in html
    import re
    field=re.search(r'<input[^>]+id="value"[^>]*>',html)[0]
    assert 'type="text"' in field and 'required' not in field
    response=client.post('/input',data={'value':''})
    assert response.status_code==200 and app.state.session.phase==Phase.SHOP
