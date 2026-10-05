"""S41：預期由 ERB/インターミッション画面/SHOP_CHARA_POWERUP.ERB@CHARA_POWERUP 推導。"""
import pytest

from test_clothing_menu import data, ctx
from eragvt.game.character_powerup import character_powerup_gen
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng
from eragvt.text import NullNarrationService


def start(ctx, points=1000):
    c = ctx.state.charas[1]
    c.juel[20] = points
    gen = character_powerup_gen(ctx)
    next(gen)
    gen.send(1)
    return gen, c


@pytest.mark.parametrize('command,slot,amount', [(2,50,50),(12,51,50),(22,52,5),(32,10,5),(42,11,5),(52,12,5),(62,13,5),(3,50,100)])
@pytest.mark.parametrize('points', [49,50,99,100])
def test_base_cost_and_deferred_commit(ctx,command,slot,amount,points):
    """:372–384／481–491：每段50P，體氣50、其餘5；確認前不寫角色。"""
    gen,c = start(ctx,points)
    old = c.base[slot]
    cost = 100 if command == 3 else 50
    gen.send(command)
    assert (c.base[slot],c.juel[20]) == (old,points)
    gen.send(100)
    assert (c.base[slot],c.juel[20]) == (old+(amount if points>=cost else 0), points-(cost if points>=cost else 0))
    gen.send(100)
    assert c.base[slot] == old+(amount if points>=cost else 0)


@pytest.mark.parametrize('commands,gain,cost', [([3,0],0,0),([3,1],50,50),([2,0],50,50),([1,0],0,0),([3,200],0,0),([3,999],0,0)])
def test_undo_and_cancel(ctx,commands,gain,cost):
    gen,c = start(ctx)
    old=c.base[50]
    for command in commands:
        if command==999:
            with pytest.raises(StopIteration): gen.send(command)
        else: gen.send(command)
    if commands[-1]!=999: gen.send(100)
    assert (c.base[50],c.juel[20]) == (old+gain,1000-cost)


@pytest.mark.parametrize('mark,palam', [(0,13),(1,16),(2,14),(3,17),(4,15)])
def test_marks_cost_history_and_reset(ctx,mark,palam):
    """:172–190／386–391／493–498：無性格補正，3→2費300，2→1費200。"""
    c=ctx.state.charas[1]
    for i in range(10,50): c.talent[i]=0
    c.mark[mark]=3
    gen,c=start(ctx,500)
    gen.send(70+mark); gen.send(70+mark); gen.send(70+mark)
    gen.send(100)
    assert (c.mark[mark],c.mark[90+mark],c.juel[20])==(1,3,0)


def test_mark_double_personality_rounding(ctx):
    """:190；CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_PALAM_F：性格12欲情1.15，100→115→132。"""
    c=ctx.state.charas[1]
    for i in range(10,50): c.talent[i]=0
    c.talent[12]=1; c.mark[0]=1
    gen,c=start(ctx,132)
    gen.send(70); gen.send(100)
    assert (c.mark[0],c.juel[20])==(0,0)


@pytest.mark.parametrize('commands,point_cost,money_cost', [([80],30,0),([85],0,625),([80,85],0,625),([85,80],30,0),([80,80],0,0),([85,85],0,0),([85,89],0,0),([85,200],0,0)])
def test_shield_rebuild_modes(ctx,commands,point_cost,money_cost):
    c=ctx.state.charas[1]
    c.talent[190]=1; c.abl[50]=1
    ctx.state.day[0]=1; ctx.state.money=625
    c.base[30]=0
    gen,c=start(ctx,30)
    for command in commands: gen.send(command)
    gen.send(100)
    assert (c.juel[20],ctx.state.money)==(30-point_cost,625-money_cost)
    assert c.base[30] == (c.maxbase[30] if point_cost or money_cost else 0)


@pytest.mark.parametrize('male,ts,expected', [(0,0,3),(1,0,2),(0,1,2)])
def test_shield_acquisition_limit(ctx,male,ts,expected):
    c=ctx.state.charas[1]
    for i in (*range(190,194),303): c.talent[i]=0
    c.talent[ctx.data.index_of('TALENT','オトコ')]=male
    c.talent[ctx.data.index_of('TALENT','変身時ＴＳ')]=ts
    gen,c=start(ctx,200)
    for cmd in (90,91,92,93): gen.send(cmd)
    gen.send(100)
    assert sum(c.talent[i] for i in range(190,194))==expected
    assert c.juel[20]==200-50*expected


@pytest.mark.parametrize('commands,expected', [([91,94],(1,0)),([94,91],(0,1)),([90,90],(0,0))])
def test_v_and_contraceptive_exclusive(ctx,commands,expected):
    c=ctx.state.charas[1]
    for i in (*range(190,194),303): c.talent[i]=0
    gen,c=start(ctx)
    for cmd in commands: gen.send(cmd)
    gen.send(100)
    assert (c.talent[191],c.talent[ctx.data.index_of('TALENT','避妊結界')])==expected


@pytest.mark.parametrize('inputs,target', [([999],2),([4,999],1),([500,999],1),([500,4,999],2)])
def test_target_restore_uses_latest_loop(ctx,inputs,target):
    """:60–61／336–342：每圈LOCAL:99被覆寫，並非永久保留進入前TARGET。"""
    ctx.state.target=2
    gen,c=start(ctx)
    for value in inputs[:-1]: gen.send(value)
    with pytest.raises(StopIteration): gen.send(inputs[-1])
    assert ctx.state.target==target
    assert ctx.state.result[0]==0


@pytest.mark.parametrize('state,member', [(1,1),(9,1),(0,0)])
def test_selection_eligibility(ctx,state,member):
    c=ctx.state.charas[1]; c.cflag[0]=state; c.cflag[999]=member
    gen=character_powerup_gen(ctx); next(gen); gen.send(1)
    assert '正しい値を入力してください' in '\n'.join(l.text for l in ctx.out.lines)
    with pytest.raises(StopIteration): gen.send(999)


def test_session_shop_strengthening_and_return(data,tmp_path):
    s=GameSession(data,tmp_path,rng=GameRng(0),narration=NullNarrationService())
    for value in (0,0, 1000,1): s.input(value)
    c=s.state.charas[1]; c.juel[20]=50; before=c.base[50]
    for value in (111,1,2,100,999): s.input(value)
    assert s.phase==Phase.SHOP
    assert (c.base[50],c.juel[20])==(before+50,0)
    s.input(111); s.input(1)
    assert str(c.maxbase[0]) in '\n'.join(l.text for l in s.out.lines)


@pytest.mark.parametrize('points,commands,left', [(49,[90],49),(50,[90,90,90],0),(100,[90,100,90],50)])
def test_acquisition_cost_repeat_and_undo(ctx,points,commands,left):
    c=ctx.state.charas[1]
    for i in (*range(190,194),303): c.talent[i]=0
    gen,c=start(ctx,points)
    for cmd in commands: gen.send(cmd)
    gen.send(100)
    assert c.juel[20]==left
    assert c.talent[190]==int(points>=50)


@pytest.mark.parametrize('points,money,command,spend', [(29,625,80,False),(30,624,85,False),(30,625,85,True),(30,626,85,True)])
def test_rebuild_resource_boundary(ctx,points,money,command,spend):
    c=ctx.state.charas[1]; c.talent[190]=1; c.abl[50]=1
    c.base[30]=0; ctx.state.day[0]=1; ctx.state.money=money
    gen,c=start(ctx,points)
    gen.send(command); gen.send(100)
    assert (c.base[30]>0)==spend
    assert ctx.state.money==money-(625 if spend else 0)


def test_rebuild_unlisted_talent_and_full_bar(ctx):
    """:399–425：輸入分支未檢查TALENT，隱藏的指令也可操作。"""
    c=ctx.state.charas[1]; c.talent[190]=0
    c.base[30]=5; c.maxbase[30]=50
    gen,c=start(ctx,60)
    gen.send(80); gen.send(100)
    assert (c.base[30],c.juel[20])==(50,30)
    gen.send(80); gen.send(100)
    assert (c.base[30],c.juel[20])==(50,30)


@pytest.mark.parametrize('command', [79,200])
def test_mark_reset_preserves_history(ctx,command):
    c=ctx.state.charas[1]; c.mark[0]=2; c.mark[90]=5
    gen,c=start(ctx)
    gen.send(70); gen.send(command); gen.send(100)
    assert (c.mark[0],c.mark[90],c.juel[20])==(2,5,1000)
    gen.send(70); gen.send(100)
    assert c.mark[90]==5


@pytest.mark.parametrize('slot,command,cap', [(50,2,99999),(51,12,99999),(52,22,9999),(10,32,9999),(11,42,9999),(12,52,9999),(13,62,9999)])
def test_cap_does_not_block_base_purchase(ctx,slot,command,cap):
    """:372–384 無基礎值上限；LEVELSTATUS_UP 僅限制 MAXBASE。"""
    c=ctx.state.charas[1]; c.base[slot]=1000000; c.abl[50]=1
    gen,c=start(ctx,50)
    gen.send(command); gen.send(100)
    idx=(0,1,2,10,11,12,13)[(50,51,52,10,11,12,13).index(slot)]
    assert c.maxbase[idx]==cap
    assert c.base[slot]==1000000+(50 if slot in (50,51) else 5)
    assert c.juel[20]==0


def test_preview_expected_and_shared_results(ctx):
    """:549–558＋コモン関数.ERB@LEVELSTATUS_UP：Lv1知性105→(109×105+100×50)/100=164。"""
    c=ctx.state.charas[1]
    for i in list(c.talent): c.talent[i]=0
    c.abl[50]=1; c.base[13]=100; c.maxbase[13]=159
    ctx.state.result[4]=123; ctx.state.results[2]='保留'
    gen,c=start(ctx,50)
    gen.send(62)
    assert c.maxbase[13]==159
    assert ctx.state.results[0]==' 164'
    gen.send(100)
    assert c.maxbase[13]==164
    assert (ctx.state.result[4],ctx.state.results[2])==(123,'保留')
    with pytest.raises(StopIteration): gen.send(999)
    assert ctx.state.result[0]==0


def test_switch_discards_pending_and_skips_ineligible(ctx):
    c=ctx.state.charas[1]; c2=ctx.state.charas[2]; c3=ctx.state.charas[3]
    c2.cflag[0]=1
    old=c.base[50]; old3=c3.base[50]
    gen,c=start(ctx)
    gen.send(2); gen.send(500)
    assert ctx.state.target==3
    gen.send(100)
    assert c.base[50]==old and c3.base[50]==old3
    gen.send(300)
    assert ctx.state.target==1


@pytest.mark.parametrize('invalid', [-1,4,69,75,84,95,301,501,1000])
def test_invalid_input_no_purchase(ctx,invalid):
    gen,c=start(ctx)
    old=c.base[50]
    gen.send(invalid); gen.send(100)
    assert (c.base[50],c.juel[20])==(old,1000)


def test_single_character_bypasses_eligibility(ctx):
    """:29–36：CHARANUM<3直接指定1，不經CHARA_LIST條件。"""
    ctx.state.charas[:]=ctx.state.charas[:2]
    c=ctx.state.charas[1]; c.cflag[0]=9; c.cflag[999]=0; c.juel[20]=50
    old=c.base[50]
    gen=character_powerup_gen(ctx); next(gen); gen.send(2); gen.send(100)
    assert c.base[50]==old+50


@pytest.mark.parametrize('initial,after,color', [(0,1,'#000028'),(1,0,'#000000'),(2,3,'#000000')])
def test_hidden_debug_toggle(ctx,initial,after,color):
    ctx.state.flag[999]=initial
    gen,c=start(ctx); gen.send(400)
    assert ctx.state.flag[999]==after
    assert ctx.out.bgcolor==color


def test_plain_labels_are_not_clickable(ctx):
    """@CHARA_POWERUP:124、131、138、146、193、230、280、314、317、323：原文全部PRINTPLAIN。"""
    ctx.state.charas[1].talent[190]=1
    gen,c=start(ctx)
    labels=('合 計','体力','刻印','再構築','結界の獲得')
    rows=[line for line in ctx.out.lines if any(label in line.text for label in labels)]
    assert rows
    for line in rows:
        for part in line.parts:
            if any(label in part.text for label in labels):
                assert part.button is None
    base_row=next(line for line in rows if '体力' in line.text)
    assert [value for _,value in base_row.buttons]==[0,1,2,3]
