"""S38 人工前置狀態；預期直接依原作函式，不代表自然通關。"""
from eragvt.game.prison.event import prison_routine
from _gen_driver import as_generator, run_no_input
import pytest

from test_lastboss import ctx as base_ctx, data, _lastboss_battle
from eragvt.narration.service import CatalogNarrationService
from eragvt.data import default_csv_dir


@pytest.fixture(scope="module")
def narration(data):
    return CatalogNarrationService(default_csv_dir().parent / "ERB", data)


@pytest.fixture
def ctx(base_ctx,narration):
    base_ctx.narration=narration
    return base_ctx
from eragvt.game.battle.core import tentacle_access, tentacle_status_hosei, lastboss_attack_routine
from eragvt.game.battle import source_check
from eragvt.state import FixedRng


def ready(ctx, phase=1):
    _lastboss_battle(ctx.state)
    ctx.state.flag[101] = 2
    ctx.state.flag[11] = 2
    ctx.state.flag[21] = phase


@pytest.mark.parametrize('phase,name,short,middle,long,hold,yudan,agility', [
    (1,'天使の樹',250,240,230,350,1500,50),
    (2,'楽園の花',150,150,150,140,3000,200),
    (3,'堕落の核',85,85,85,90,6000,250),
    (4,'堕落の核',85,85,85,90,6000,100),
])
def test_data(ctx, phase,name,short,middle,long,hold,yudan,agility):
    # ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_LASTBOSS_2_天使の樹.ERB@TENTACLE_LASTBOSS_2_GETNAME:8–245。
    ready(ctx,phase)
    assert tentacle_access(ctx,'GETNAME') == name
    assert [tentacle_access(ctx,k) for k in ('SHORT','MIDDLE','LONG','HOLD','YUDAN')] == [short,middle,long,hold,yudan]
    assert tentacle_access(ctx,'BINSYOU') == tentacle_status_hosei(ctx.state,agility)


@pytest.mark.parametrize('phase,hp,mp,rolls,expected', [
    (1,100,100,[69],1),(1,100,100,[70],3),(1,0,100,[69],2),
    (2,30,60,[79],3),(2,30,60,[80],6),(2,60,30,[1,10],6),
    (3,60,30,[0],2),(3,60,30,[1,1,1,69],1),
    (2,0,100,[79],3),(2,100,0,[79],1),(4,0,0,[],2),
])
def test_attack(ctx,phase,hp,mp,rolls,expected):
    # 同檔 @TENTACLE_LASTBOSS_2_ATTACK_ROUTINE:299–372，含短路亂數消耗。
    ready(ctx,phase)
    c=ctx.state.charas[ctx.state.target]
    c.maxbase[0]=c.maxbase[1]=100
    c.base[0],c.base[1]=hp,mp
    ctx.state.rng=FixedRng(rolls)
    assert lastboss_attack_routine(ctx)==expected
    assert ctx.state.rng.snapshot()==[]


@pytest.mark.parametrize('phase,hp,newphase,newhp',[
    (1,76,1,76),(1,75,2,75),(2,38,2,38),(2,37,3,37),
    (3,11,3,11),(3,10,4,70),(4,1,4,1),
])
def test_phase(ctx,phase,hp,newphase,newhp):
    # ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:40–112。
    ready(ctx,phase)
    st=ctx.state
    st.flag[12],st.flag[13],st.flag[700]=100,hp,0
    assert list(source_check.source_check(ctx))==[]
    assert (st.flag[21],st.flag[13])==(newphase,newhp)


@pytest.mark.parametrize('phase,distance,mask,raw',[
    (1,1,0,315),(1,1,1,210),(1,2,0,425),(1,2,2,170),
    (1,3,0,675),(1,3,4,150),(2,1,0,52),(3,2,0,42),(4,3,0,18),
])
def test_armor(ctx,phase,distance,mask,raw):
    # 同原檔 @TENTACLE_LASTBOSS_2_BOUGYO:88–133；每個 TIMES 各自截斷。
    ready(ctx,phase)
    c=ctx.state.target_chara
    c.base[ctx.data.index_of('BASE','攻撃')]=100
    c.tcvarn[0]=distance
    ctx.state.tflag[13]=mask
    assert tentacle_access(ctx,'BOUGYO') == tentacle_status_hosei(ctx.state,raw,25)


def test_static_sakusei(ctx):
    # _SAKUSEI:47–53；phase 0 不代入 LOCAL，跨呼叫保留。
    ready(ctx,0)
    assert tentacle_access(ctx,'SAKUSEI')==0
    ctx.state.flag[21]=2
    assert tentacle_access(ctx,'SAKUSEI')==50
    ctx.state.flag[21]=0
    assert tentacle_access(ctx,'SAKUSEI')==50
    ctx.state.flag[21]=4
    assert tentacle_access(ctx,'SAKUSEI')==25


@pytest.mark.parametrize('phase,roll,expected',[(1,0,0),(1,95,1006),(2,0,1),(2,99,1007)])
def test_choice_pool(ctx,phase,roll,expected):
    # _SEX_ROUTINE:379–551，FOR 終點在進入時固定：引擎 Instraction.Child.cs:1737。
    from eragvt.game.battle.sexcom import lastboss_sex_routine
    ready(ctx,phase)
    c=ctx.state.target_chara
    c.talent.clear()
    c.abl.clear()
    ctx.state.rng=FixedRng([roll]*101+[100])
    assert lastboss_sex_routine(ctx,2)==expected
    assert ctx.state.temp.randchoose[0]==101
    assert ctx.state.rng.snapshot()==[]


def test_choice_overfull_pool_and_unused_random(ctx):
    from eragvt.game.battle.sexcom import lastboss_sex_routine
    ready(ctx)
    c=ctx.state.target_chara
    c.talent.clear()
    c.abl.clear()
    c.abl[ctx.data.index_of('ABL','自慰中毒')]=34
    ctx.state.rng=FixedRng([99]*102+[101])
    assert lastboss_sex_routine(ctx,2)==1006
    assert ctx.state.temp.randchoose[0]==102
    assert ctx.state.rng.snapshot()==[]


@pytest.mark.parametrize('roll,command',[(0,100),(5,101),(14,102),(19,103),(27,200),
                                     (35,201),(43,300),(51,301),(59,104),(67,105),(68,None)])
def test_prison(ctx,monkeypatch,roll,command):
    from eragvt.game.prison.event import tentacle_access_prison
    from eragvt.game.prison import commands
    ready(ctx,2)
    c=ctx.state.target_chara
    c.cflag[20],c.cflag[21]=1,2
    calls=[]
    monkeypatch.setattr(commands,'prison_comable',as_generator(lambda ctx,com:calls.append(com)))
    ctx.state.rng=FixedRng([roll])
    assert run_no_input(prison_routine(ctx, ctx.state.target))==int(command is not None)
    assert calls==([] if command is None else [command])
    assert tentacle_access_prison(ctx,ctx.state.target,'GETNAME')=='楽園の花'
    # COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:338，誤用一般BOSS_2補正照原作。
    assert tentacle_access_prison(ctx,ctx.state.target,'PALAM_HOSEI')==(100,120,100,100,100,100,100,100,100,100,100,100)


def test_encounter_and_final_victory(ctx):
    from eragvt.game.battle import encount
    from eragvt.game.battle.core import BeginTurnend
    ready(ctx,4)
    st=ctx.state
    st.flag[47]=st.flag[46]
    st.charas[1].cflag[100]=101
    st.rng=FixedRng([99,0,0])
    assert encount.encount(ctx)==1
    assert (st.flag[10],st.flag[11],st.flag[21])==(1,2,4)
    assert st.flag[12]==tentacle_status_hosei(st,10000,2500)
    st.flag[13]=0
    st.rng=FixedRng([0]*100)
    # 最終形態歸零後 LASTBOSS == 1，接入既有勝利、解救與TURNEND。
    with pytest.raises(BeginTurnend):
        next(source_check.source_check(ctx))
    assert (st.flag[21],st.flag[101],st.flag[64])==(0,0,-1)


def test_phase_result_and_local(ctx):
    from eragvt.game.battle.angel_tree import change_phase
    ready(ctx,3)
    st=ctx.state
    st.flag[12],st.flag[13]=100,10
    st.result[1]=987
    change_phase(ctx)
    assert st.temp.locals[('SOURCE_CHECK',0)]==60
    assert (st.result[0],st.result[1])==(10,987)
    assert any('体力が60回復' in line.text for line in ctx.out.lines)
    assert not ctx.narration.failures


def test_access_shared_results(ctx):
    ready(ctx,2)
    st=ctx.state
    st.result[1]=321
    st.results[2]='殘值'
    assert tentacle_access(ctx,'GETNAME')=='楽園の花'
    assert (st.result[0],st.result[1],st.results[0],st.results[2])==(0,321,'楽園の花','殘值')
    tentacle_access(ctx,'SHORT')
    assert st.result[0]==150
    assert st.results[0]=="【エラー：BOSS_2に対するTENTACLE_ACCESS('SHORT')関数失敗】"


@pytest.mark.parametrize('distance,mask,blocked',[(1,0,True),(1,1,False),(2,1,True),(2,2,False),(3,4,True),(3,1,False)])
def test_shell_overrides_hit_after_roll(ctx,monkeypatch,distance,mask,blocked):
    # COM_ATTACK_COMMON:60 用 TFLAG:13 & TCVARn:0，故遠距離=3 與防禦公式 bit4 不同。
    from eragvt.game.battle import commands
    from eragvt.state import GameRng
    ready(ctx)
    st=ctx.state
    st.rng=GameRng(3)
    st.target_chara.tcvarn[0]=distance
    st.tflag[13]=mask
    st.flag[13]=10000
    calls=[]
    def hit(*args):
        calls.append('hit')
        return 1,0
    def guard(*args):
        calls.append('guard')
        return 0
    monkeypatch.setattr(commands,'act_hantei_chara_to_tentacle',hit)
    monkeypatch.setattr(commands,'act_hantei_chara_to_tentacle_guard',guard)
    monkeypatch.setattr(commands,'damage',lambda *args:100)
    monkeypatch.setattr(commands,'fstyle_name',lambda *args:'標準')
    commands.com_attack_common(ctx)
    assert calls==(['hit','guard'] if blocked else ['hit'])
    assert (st.flag[13]==10000)==blocked


def test_palam_and_size_results(ctx):
    from eragvt.game.battle.core import tentacle_palam_hosei
    from eragvt.game.battle.gaping import set_tentacle_size
    ready(ctx,3)
    st=ctx.state
    st.result[12]=654
    assert tentacle_palam_hosei(ctx)==(100,100,100,100,100,50,50,50,200,200,200,200)
    st.rng=FixedRng([6,2,0,3,0,0,0,0])
    set_tentacle_size(ctx,1,2,0,0,3)
    assert [st.temp.tentacle_num[(0,i)] for i in range(4)]==[9,3,1,5]
    assert [st.result[i] for i in range(8)]==[0,100,100,90,9,3,1,5]
    assert st.result[12]==654
    assert st.rng.snapshot()==[]


@pytest.mark.parametrize('cycles,hardcore,unlocks',[(0,False,False),(0,True,False),(1,False,False),(1,True,True)])
def test_unlock_only_after_hardcore_succession(ctx,cycles,hardcore,unlocks):
    # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:176–180、270–272：由K觸手實際擊破入口驗證門檻。
    from eragvt.state.constants import GameOption
    from eragvt.game.battle.core import BeginAfterTrain, BeginTurnend
    from eragvt.state import GameRng
    st=ctx.state
    _lastboss_battle(st)
    st.flag[854]=cycles
    st.flag.set_bit(0,GameOption.HARDCORE,hardcore)
    st.flag[13]=0
    st.rng=GameRng(0)
    with pytest.raises(BeginAfterTrain if unlocks else BeginTurnend):
        source_check._victory(ctx)
    assert (st.flag[101],st.flag[21])==((2,1) if unlocks else (0,0))


@pytest.mark.parametrize('phase,name',[(1,'天使の樹'),(2,'楽園の花'),(3,'堕落の核'),(4,'堕落の核')])
def test_shop_and_prison_name_follow_global_phase(ctx,phase,name):
    from eragvt.game.shop import shop_show_boss_info
    from eragvt.game.prison.event import tentacle_access_prison
    ready(ctx,phase)
    st=ctx.state
    st.flag[4]=2
    st.target_chara.cflag[20],st.target_chara.cflag[21]=1,2
    shop_show_boss_info(st,ctx.data,ctx.out)
    assert f'[{name}]' in ''.join(line.text for line in ctx.out.lines)
    assert tentacle_access_prison(ctx,st.target,'GETNAME')==name


def test_defeat_to_prison(ctx):
    from eragvt.game.battle.core import BeginAfterTrain
    from eragvt.game.prison.event import prison
    from eragvt.state import GameRng
    ready(ctx,2)
    st=ctx.state
    st.rng=GameRng(19)
    with pytest.raises(BeginAfterTrain):
        run_no_input(source_check._battle_lose(ctx))
    assert (st.target_chara.cflag[0],st.target_chara.cflag[20],st.target_chara.cflag[21])==(1,1,2)
    prison(ctx)
    assert not ctx.narration.failures


def test_session_final_form_clear(data,tmp_path,narration):
    # 人工周回末王前置；由真實SHOP出擊／TRAIN／TURNEND／ENDING走至繼承選單。
    from test_lastboss import _session
    from eragvt.game.session import Phase
    from eragvt.state.constants import GameOption
    session=_session(data,tmp_path,seed=4)
    session.narration=narration
    st=session.state
    st.flag[100],st.flag[101],st.flag[21],st.flag[854]=0,2,4,1
    st.flag.set_bit(0,GameOption.HARDCORE,True)
    st.flag[47]=st.flag[46]
    st.flag[402]=100000000
    st.charas[1].cflag[100]=101
    for c in st.charas[2:]:
        c.cflag[100]=103
    session.input(100)
    if session.phase==Phase.ACTION_CONFIRM:
        session.input(9)
    for _ in range(3000):
        if any('データ引き継ぎ' in line.text for line in session.out.lines[-30:]):
            break
        assert session.phase!=Phase.HALTED, '\n'.join(line.text for line in session.out.lines[-3:])
        if session.phase==Phase.SAVE_SELECT:
            session.input(5)
        elif '[1]いいえ' in [line.text for line in session.out.lines[-6:]]:
            session.input(0)
        else:
            buttons=[v for line in session.out.lines[-30:] for _,v in line.buttons]
            session.input(1 if 1 in buttons else 0)
    assert any('データ引き継ぎ' in line.text for line in session.out.lines[-30:])
    assert (st.flag[21],st.flag[101])==(0,0)
    session.input(999)
    session.input(0)
    session.input(1)
    session.input(0)
    # SUCCESSION.ERB@SUCCESSION:1560 → CHARA_MAKE.ERB@CHARA_MAKE_MAIN:207–210。
    session.input(1000)  # 保留預設角色設定，明確完成角色製作。
    session.input(1)
    assert session.phase==Phase.SHOP
    session.close()
