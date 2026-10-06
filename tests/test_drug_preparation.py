"""S42：expected 取自 ACTIONsub_DRUG_PREPARATION.ERB，不由實作回推。"""
from copy import deepcopy

import pytest

from test_clothing_menu import data, ctx
from eragvt.game.drug_preparation import drug_preparation_gen
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng
from eragvt.text import NullNarrationService


def begin(ctx, command):
    gen = drug_preparation_gen(ctx)
    next(gen)
    gen.send(command)
    return gen


def put(ctx, name, value):
    ctx.state.charas[1].talent[ctx.data.index_of('TALENT', name)] = value


@pytest.mark.parametrize('count,confirm,cost,stock', [(0,0,0,0),(-1,0,0,0),(1,0,125,1),(2,0,250,2),(3,0,0,0),(2,1,0,0)])
def test_purchase(ctx,count,confirm,cost,stock):
    """@DRUG_PREPARATION:143–175：數量先驗資金，確認後扣款。"""
    ctx.state.money=250
    gen=begin(ctx,13)
    gen.send(count)
    if 0<count<=2: gen.send(confirm)
    assert (ctx.state.money,ctx.state.flag[201])==(250-cost,stock)


@pytest.mark.parametrize('command,name,cost', [(0,'触手の虜',5),(2,'母乳体質',2),(3,'寄生',2),(4,'苗床化',2)])
@pytest.mark.parametrize('enough', [False,True])
def test_removal_cost(ctx,command,name,cost,enough):
    """@CHARA_LIST_DRUG:601–665；不足不進角色選擇。"""
    put(ctx,name,1)
    ctx.state.flag[200]=cost if enough else cost-1
    gen=begin(ctx,command)
    if enough: gen.send(1)
    assert ctx.state.charas[1].talent[ctx.data.index_of('TALENT',name)]==(0 if enough else 1)
    assert ctx.state.flag[200]==(0 if enough else cost-1)


@pytest.mark.parametrize('command,flag,value,cost,expected', [(20,32,1,0,0),(21,32,499999999999999999,0,499999999999999999),(21,32,500000000000000000,1250,50000000000000000)])
def test_treatment_threshold(ctx,command,flag,value,cost,expected):
    """@CHARA_LIST_DRUG:959–984。"""
    ctx.state.money=1250; ctx.state.flag[200]=10
    ctx.state.charas[1].cflag[flag]=value
    gen=begin(ctx,command); gen.send(1)
    assert (ctx.state.money,ctx.state.charas[1].cflag[flag])==(1250-cost,expected)


@pytest.mark.parametrize('command,pre,post',[(30,1,-1),(30,2,2),(31,0,0)])
def test_growth_state(ctx,command,pre,post):
    """@CHARA_LIST_DRUG:986–1019：純狀態變更，225是成長計數。"""
    put(ctx,'未熟',pre); put(ctx,'性徴停滞',1 if command==30 else 0)
    ctx.state.charas[1].cflag[225]=1
    ctx.state.flag[200]=1
    gen=begin(ctx,command); gen.send(1)
    assert ctx.state.charas[1].talent[ctx.data.index_of('TALENT','未熟')]==post
    assert ctx.state.charas[1].talent[ctx.data.index_of('TALENT','性徴停滞')]==(command==31)
    assert ctx.state.flag[200]==0


@pytest.mark.parametrize('count,expected,stock', [(-1,2,3),(0,0,5),(1,1,4),(5,5,0)])
def test_prescribe(ctx,count,expected,stock):
    """@CHARA_LIST_DRUG:840–865：處方庫存轉移；負數取消。"""
    put(ctx,'妊娠',0)
    ctx.state.flag[201]=3; ctx.state.charas[1].cflag[241]=2
    gen=begin(ctx,14); gen.send(1); gen.send(count)
    assert (ctx.state.charas[1].cflag[241],ctx.state.flag[201])==(expected,stock)


@pytest.mark.parametrize('fatigue,key,cost,remaining', [(1,0,500,0),(19,0,500,14),(20,0,0,20),(21,0,5500,0),(21,2,0,21),(10,1,0,10),(11,1,1500,0),(29,1,1500,9),(30,1,0,30)])
def test_maintenance_original_keys(ctx,fatigue,key,cost,remaining):
    """@CHARA_LIST_DRUG:898–939：完整維修原文接受0，畫面印2。"""
    put(ctx,'ロボっ子',1)
    ctx.state.money=5500; ctx.state.charas[1].cflag[99]=fatigue
    gen=begin(ctx,15); gen.send(1); gen.send(key)
    assert (ctx.state.money,ctx.state.charas[1].cflag[99])==(5500-cost,remaining)


def test_web_purchase_return(data,tmp_path):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,1, 1000,1,0): s.input(value)
    s.state.money=250
    for value in (113,13,2,0,999): s.input(value)
    assert s.phase==Phase.SHOP
    assert (s.state.money,s.state.flag[201])==(0,2)


@pytest.mark.parametrize('cmd,pregnant,days,expected,cost',[(10,0,0,0,50),(10,4,2,4,50),(10,4,3,5,50),(10,1,0,1,50),(11,4,0,5,250),(11,1,0,1,250),(11,3,0,3,250),(11,5,55,5,250)])
def test_diagnosis(ctx,cmd,pregnant,days,expected,cost):
    """@CHARA_LIST_DRUG:704–814；精密檢查入口需500但僅扣250。"""
    put(ctx,'妊娠',pregnant); ctx.state.charas[1].cflag[222]=days; ctx.state.money=500
    gen=begin(ctx,cmd); gen.send(1)
    assert (_talent(ctx,'妊娠'),ctx.state.money)==(expected,500-cost)


def _talent(ctx,name):
    return ctx.state.charas[1].talent[ctx.data.index_of('TALENT',name)]


@pytest.mark.parametrize('stage',[1,3,5])
@pytest.mark.parametrize('status',[0,10])
def test_surgery_resets_exact_fields(ctx,stage,status):
    """@CHARA_LIST_DRUG:816–838；入院者CALL後RESULT=0，疲勞加在索引0。"""
    c=ctx.state.charas[1]; put(ctx,'妊娠',stage); c.cflag[0]=status
    for i in range(221,234): c.cflag[i]=9
    c.cflag[99]=3; ctx.state.money=7000
    gen=begin(ctx,12); gen.send(1)
    assert _talent(ctx,'妊娠')==0 and ctx.state.money==0
    assert [c.cflag[i] for i in (221,222,226,227,228,230,232,233)]==[0]*8
    assert (c.cflag[229],c.cflag[231],c.cflag[99],c.cflag[0])==(9,9,3 if status==10 else 28,0)
    assert ctx.state.charas[0].cflag[99]==(25 if status==10 else 0)


@pytest.mark.parametrize('normal,trans,expected',[(1,0,(0,0)),(2,2,(0,0)),(3,0,(3,0)),(0,3,(0,3)),(3,3,(3,3))])
def test_two_form_removal(ctx,normal,trans,expected):
    """@CHARA_LIST_DRUG:615–634；(3,0)手動輸入會扣材料但沒有可移除值。"""
    put(ctx,'ふたなり',normal); put(ctx,'変身時ふたなり',trans); ctx.state.flag[200]=2
    gen=begin(ctx,1); gen.send(1)
    assert (_talent(ctx,'ふたなり'),_talent(ctx,'変身時ふたなり'))==expected
    assert ctx.state.flag[200]==(2 if normal==trans==3 else 0)


@pytest.mark.parametrize('a,b,big,small,expected',[(0,1,0,0,(0,0,0,0)),(2,-1,1,0,(1,0,0,0)),(1,0,0,2,(0,0,0,2)),(0,-1,0,0,(0,-1,0,0))])
def test_size_treatment(ctx,a,b,big,small,expected):
    """@CHARA_LIST_DRUG:666–702；只按原作調整兩種形態。"""
    c=ctx.state.charas[1]; c.cflag[37]=a; c.cflag[38]=b
    put(ctx,'巨乳',big); put(ctx,'貧乳',small); ctx.state.flag[200]=2
    gen=begin(ctx,5); gen.send(1)
    assert (c.cflag[37],c.cflag[38],_talent(ctx,'巨乳'),_talent(ctx,'貧乳'))==expected
    assert ctx.state.flag[200]==0


@pytest.mark.parametrize('counter,used',[(-1,True),(0,False),(1,True),(14,True),(15,False)])
def test_growth_counter_input_boundary(ctx,counter,used):
    put(ctx,'性徴停滞',0); ctx.state.charas[1].cflag[225]=counter; ctx.state.flag[200]=1
    gen=begin(ctx,31); gen.send(1)
    assert ctx.state.flag[200]==1-int(used)


@pytest.mark.parametrize('sex',[0,1])
@pytest.mark.parametrize('feat',[0,1,2])
def test_robot_join_default(ctx,sex,feat):
    """@DRUG_PREPARATION:280–430：性別選擇、扣50000、預設確認、特徵選單、還原TARGET。"""
    st=ctx.state; st.money=50000; st.target=2; old=st.charanum
    old_items=[st.item[i] for i in range(100,700)]
    gen=begin(ctx,100); gen.send(sex); gen.send(99)
    assert st.charanum==old+1 and st.money==0
    gen.send(feat)
    if feat==0: gen.send(0)
    c=st.charas[-1]
    assert c.talent[ctx.data.index_of('TALENT','ロボっ子')]==1
    assert c.talent[ctx.data.index_of('TALENT','未熟')]==2
    assert c.talent[ctx.data.index_of('TALENT','オトコ')]==sex
    assert c.cflag[240]>0 and st.target==2
    assert [st.item[i] for i in range(100,700)]==old_items
    assert [st.savestr[i] for i in range(4)]==['']*4
    assert st.result[0]==0


def test_robot_cancel(ctx):
    st=ctx.state; st.money=50000; old=st.charanum
    gen=begin(ctx,100); gen.send(2); gen.send(99)
    assert (st.charanum,st.money)==(old,50000)


def test_hidden_repair(ctx):
    ctx.state.flag[54]=5; ctx.state.flag[200]=40; ctx.state.money=25000
    put(ctx,'四肢欠損',1)
    gen=begin(ctx,51); gen.send(0); gen.send(1)
    assert (ctx.state.money,ctx.state.flag[200],_talent(ctx,'四肢欠損'),_talent(ctx,'共生'))==(0,0,0,1)


@pytest.mark.parametrize('invalid', [(), (2, -1, 999)])
@pytest.mark.parametrize('answer', [0, 1])
def test_hidden_confirmation_repair(ctx,invalid,answer):
    """已授權修復：@DRUG_PREPARATION:229–276；否依後續裁決提示未完成並停止，錯值重問，不執行支線。"""
    st=ctx.state; st.flag[54]=5; st.flag[200]=40; st.money=25000
    put(ctx,'四肢欠損',1)
    gen=begin(ctx,51); ctx.out.drain()
    for value in invalid:
        gen.send(value)
        assert '正しい値を入力してください' in '\n'.join(line.text for line in ctx.out.drain())
        assert (st.money,st.flag[200],_talent(ctx,'四肢欠損'),_talent(ctx,'共生'))==(25000,40,1,0)
    before=deepcopy(st.charas)
    if answer==1:
        with pytest.raises(NotImplementedError, match="AMPUTEE.*原作移植未完成.*本支線停止且未執行"):
            gen.send(answer)
        assert st.charas==before
    else:
        gen.send(answer); gen.send(1)
    assert (st.money,st.flag[200],_talent(ctx,'四肢欠損'),_talent(ctx,'共生'))==((0,0,0,1) if answer==0 else (25000,40,1,0))
    assert not any('少女研究者' in line.text for line in ctx.out.lines)
    with pytest.raises(StopIteration): gen.send(999)


@pytest.mark.parametrize('money,parts,message',[(24999,40,'資金'),(25000,39,'触手の欠片'),(25000,40,None)])
def test_hidden_confirmation_resources_and_character_cancel(ctx,money,parts,message):
    """@DRUG_PREPARATION:234–243、@CHARA_LIST_DRUG:592–596：不足返回，角色999取消。"""
    st=ctx.state; st.flag[54]=5; st.flag[200]=parts; st.money=money
    put(ctx,'四肢欠損',1)
    gen=begin(ctx,51); ctx.out.drain(); gen.send(0)
    if message: assert any(message in line.text for line in ctx.out.lines)
    else: gen.send(999)
    assert (st.money,st.flag[200],_talent(ctx,'四肢欠損'),_talent(ctx,'共生'))==(money,parts,1,0)
    with pytest.raises(StopIteration): gen.send(999)


@pytest.mark.parametrize('answer,expected',[(0,(0,0,0,1)),(1,(25000,40,1,0))])
def test_web_hidden_confirmation_halts_unfinished_branch(data,tmp_path,answer,expected):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,1, 1000,1,0): s.input(value)
    st=s.state; st.money=25000; st.flag[200]=40; st.flag[54]=5
    missing=data.index_of('TALENT','四肢欠損'); symbiosis=data.index_of('TALENT','共生')
    st.charas[1].talent[missing]=1
    before=deepcopy(st.charas)
    for value in (113,51,2,-1,answer): s.input(value)
    if answer==0:
        s.input(1); s.input(999)
        assert s.phase==Phase.SHOP
    else:
        assert s.phase==Phase.HALTED
        assert st.charas==before
        assert any("AMPUTEE 原作移植未完成；本支線停止且未執行" in line.text for line in s.out.lines)
        assert not any("少女研究者" in line.text for line in s.out.lines)
    assert (st.money,st.flag[200],st.charas[1].talent[missing],st.charas[1].talent[symbiosis])==expected


def test_invalid_cancel_result_and_no_accidental_buttons(ctx):
    gen=drug_preparation_gen(ctx); next(gen)
    lines=ctx.out.drain()
    values=[value for line in lines for _,value in line.buttons]
    assert values==[0,1,2,3,4,5,10,11,12,13,14,20,21,30,31,100,999]
    gen.send(987); gen.send(13)
    assert ctx.state.result[0]==13
    gen.send(0)
    with pytest.raises(StopIteration): gen.send(999)
    assert ctx.state.result[0]==999


@pytest.mark.parametrize('command,cost',[(10,50),(11,500),(12,7000),(13,125),(21,1250)])
def test_money_gate(ctx,command,cost):
    ctx.state.money=cost-1
    gen=begin(ctx,command)
    assert '資金が足りません' in '\n'.join(line.text for line in ctx.out.lines)
    with pytest.raises(StopIteration): gen.send(999)
    assert ctx.state.money==cost-1


@pytest.mark.parametrize('command',[0,1,2,3,4,5,10,11,12,14,15,20,21,30,31])
def test_character_cancel_and_invalid_index(ctx,command):
    ctx.state.flag[200]=100; ctx.state.flag[201]=10; ctx.state.money=10000
    put(ctx,'ロボっ子',1)
    gen=begin(ctx,command)
    for value in (-1,0,ctx.state.charanum): gen.send(value)
    gen.send(999)
    assert ctx.state.result[0]==999
    with pytest.raises(StopIteration): gen.send(999)
    assert (ctx.state.flag[200],ctx.state.flag[201],ctx.state.money)==(100,10,10000)


def test_removal_hidden_input_eligibility(ctx):
    """@CHARA_LIST_DRUG:485只隱藏共生者；647實際輸入仍允許。"""
    put(ctx,'寄生',1); put(ctx,'共生',1); ctx.state.flag[200]=2
    gen=begin(ctx,3)
    assert 1 not in [v for line in ctx.out.lines[-5:] for _,v in line.buttons]
    gen.send(1)
    assert (_talent(ctx,'寄生'),_talent(ctx,'共生'),ctx.state.flag[200])==(0,1,0)


def test_repeated_purchase_and_invalid_confirmation(ctx):
    ctx.state.money=375
    gen=begin(ctx,13); gen.send(1); gen.send(2)
    assert (ctx.state.money,ctx.state.flag[201])==(375,0)
    gen.send(0); gen.send(13); gen.send(2); gen.send(0)
    assert (ctx.state.money,ctx.state.flag[201])==(0,3)


def test_prescription_over_limit_keeps_waiting(ctx):
    put(ctx,'妊娠',0); ctx.state.flag[201]=2
    gen=begin(ctx,14); gen.send(1); gen.send(3)
    assert ctx.state.flag[201]==2
    gen.send(2)
    assert ctx.state.flag[201]==0 and ctx.state.charas[1].cflag[241]==2


@pytest.mark.parametrize('fatigue,money,key',[(1,499,0),(11,1499,1),(21,5499,0)])
def test_maintenance_funds(ctx,fatigue,money,key):
    put(ctx,'ロボっ子',1); ctx.state.money=money; ctx.state.charas[1].cflag[99]=fatigue
    gen=begin(ctx,15); gen.send(1); gen.send(key)
    assert (ctx.state.money,ctx.state.charas[1].cflag[99])==(money,fatigue)


@pytest.mark.parametrize('pre,post',[(0,2),(2,0),(-1,0)])
def test_robot_organ_switch(ctx,pre,post):
    put(ctx,'ロボっ子',1); put(ctx,'未熟',pre)
    gen=begin(ctx,15); gen.send(1); gen.send(3)
    assert _talent(ctx,'未熟')==post


@pytest.mark.parametrize('roll,expected',[(0,15),(14,1)])
def test_size_rng_range(ctx,roll,expected):
    from eragvt.state.rng import FixedRng
    c=ctx.state.charas[1]; c.cflag[37]=1; put(ctx,'膨乳改造値',20); ctx.state.flag[200]=2
    # 進入選單問候0，治療RAND(5,20)，重畫問候0。
    ctx.state.rng=FixedRng([0,roll,0])
    gen=begin(ctx,5); gen.send(1)
    assert _talent(ctx,'膨乳改造値')==expected


def test_result_tails_preserved(ctx):
    """reference/emuera-1824/Emuera/GameProc/Process.cs:249–252；INPUT只寫RESULT:0。"""
    ctx.state.result[8]=77; ctx.state.results[2]='保留'
    gen=begin(ctx,13); gen.send(1); gen.send(0)
    assert (ctx.state.result[8],ctx.state.results[2])==(77,'保留')
