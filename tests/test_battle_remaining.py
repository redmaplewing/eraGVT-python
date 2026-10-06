"""S81：全新25歲人工前態；expected逐項取自ERB，不輸出敘事。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import turnend
from eragvt.game.battle import enemy
from eragvt.game.battle.core import P_GUARD
from tools.sim_adult import adult_data, assert_ages
from test_transformation_parts import make_context
from test_special_equipment import TrackingRng
from _gen_driver import run_no_input


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


# ERB/汎用関数/SEX_GENDER.ERB@ISHOLE:52–66、@ISGIRLY:28–37。
@pytest.mark.parametrize("who,male,girly,equal,expected", [
    (0,1,0,0,True), (1,0,0,0,True), (1,-1,0,0,True),
    (1,1,0,0,False), (1,1,1,0,True), (1,1,-1,0,True),
    (1,1,0,1,True), (1,0,0,1,True),
])
def test_turnend_ishole(data,who,male,girly,equal,expected):
    ctx=make_context(data)
    st=ctx.state
    c=st.charas[who]
    c.talent[data.index_of("TALENT","オトコ")]=male
    c.talent[data.index_of("TALENT","男の娘")]=girly
    # CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F:43–47，位元反向。
    st.flag[850]=(1-equal) << 5
    st.rng=TrackingRng([])
    assert turnend._ishole(ctx,who) is expected
    assert st.target == 1 and st.result[0] == 876
    assert st.result[8] == 765 and st.results[8] == "尾格"
    assert st.rng.bounds == []
    assert_ages(st)


def prepare_recovery(ctx,kind="last1",powered=False,hp=10000,current=5000):
    st,c=ctx.state,ctx.state.target_chara
    st.flag[10] = 1 if kind.startswith("last") else 2 if kind == "mob" else 0
    st.flag[11] = 2 if kind == "last2" else 1150 if kind == "citizen" else 1
    st.flag[101] = 2 if kind == "last2" else 1 if kind == "last1" else 0
    st.flag[100] = 0 if kind.startswith("last") else 127
    st.flag[21] = 1
    st.flag[73] = int(kind == "citizen")
    st.flag[110] = int(kind == "akuoti")
    st.flag[111] = 1
    st.flag[803] = int(powered) << 5
    st.savestr[13] = "BOSS"
    st.flag[12],st.flag[13] = hp,current
    st.flag[16],st.flag[17] = 100,90
    st.tflag[2],st.tflag[10],st.tflag[16] = 0,4,-1
    c.tcvarn[0],c.tcvarn[2] = 2,P_GUARD
    st.rng=TrackingRng([])


# ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:574–617。
# 末王4%、雜魚16%、其他8%；非悪堕ち再除2+LASTBOSS_REST(0/8)。
@pytest.mark.parametrize("kind,powered,hp,current,expected", [
    ("boss",False,10000,5000,5400), ("boss",True,10000,5000,5400),
    ("last1",False,10000,5000,5200), ("last1",True,50000,25000,25200),
    ("last2",False,10000,5000,5200), ("last2",True,50000,25000,25200),
    ("mob",False,10000,5000,5800), ("mob",True,10000,5000,5800),
    ("citizen",False,10000,5000,5400), ("akuoti",True,10000,5000,5800),
    ("last1",True,10049,5000,5040), ("last1",False,101,100,101),
    ("last2",True,100,100,100), ("mob",False,101,50,58),
])
def test_enemy_recovery(data,monkeypatch,kind,powered,hp,current,expected):
    ctx=make_context(data)
    prepare_recovery(ctx,kind,powered,hp,current)
    monkeypatch.setattr(enemy,"palam_cal",lambda *args: iter(()))
    run_no_input(enemy._enemy_action_once(ctx))
    st=ctx.state
    assert st.flag[13] == expected
    assert st.flag[17] == 65 and st.tflag[2] == 0
    assert st.target == 1 and st.result[8] == 765 and st.results[8] == "尾格"
    assert st.rng.bounds == []
    assert_ages(st)


@pytest.mark.parametrize("kind,rolls,bounds", [
    ("last1",[98],[100]),
    # 末王2第一形態體力0→專用行動2；FLAG902將2轉4，並非直接抽到4。
    ("last2",[0,30],[100,100]),
])
@pytest.mark.parametrize("powered",[False,True])
def test_lastboss_recovery_reachable(data,monkeypatch,kind,rolls,bounds,powered):
    # ENEMY_ACTION.ERB@SELECT_TENTACLE_ACTION:1019–1069；末王1:134–152、末王2:299–318。
    ctx=make_context(data)
    prepare_recovery(ctx,kind,powered)
    monkeypatch.setattr(enemy,"palam_cal",lambda *args: iter(()))
    monkeypatch.setattr(enemy,"attack_place_decision",lambda ctx: None)
    st=ctx.state
    st.flag[902]=int(kind == "last2")
    if kind == "last2":
        st.target_chara.base[0]=0
    st.rng=TrackingRng(rolls)
    enemy.select_tentacle_action(ctx)
    assert st.tflag[10] == 4
    assert st.rng.bounds == bounds
    run_no_input(enemy._enemy_action_once(ctx))
    assert st.flag[13] == (5040 if powered else 5200)


@pytest.mark.parametrize("male,girly,equal,bounds", [
    (1,0,0,[]),(1,1,0,[70]),(0,0,0,[70]),(1,0,1,[70]),
])
def test_akuoti_candidate_gate(data,male,girly,equal,bounds):
    # FORCE_悪堕ちキャラの淫謀.ERB@AKUOTI_ATTACK:7–25。
    # 防衛10000→RAND70；69不小於白天門檻40，真呼叫者正常返回，沒有執行事件敘事。
    ctx=make_context(data)
    st,c=ctx.state,ctx.state.target_chara
    c.cflag[0]=3
    c.talent[data.index_of("TALENT","オトコ")]=male
    c.talent[data.index_of("TALENT","男の娘")]=girly
    st.flag[850]=(1-equal)<<5
    st.flag[852],st.flag[111]=10000,77
    st.rng=TrackingRng([69])
    run_no_input(turnend.akuoti_attack(ctx))
    assert st.flag[111] == 77 and st.rng.bounds == bounds
    assert st.target == 1


# ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF*.ERB：38個@COM定義。
SOURCE_COMMANDS=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,40,44,45,46,47,69,70,71,72,73,74,99,100,101,102,103,104,201,202,203)


@pytest.mark.parametrize("number",SOURCE_COMMANDS)
def test_all_source_commands_dispatch(data,monkeypatch,number):
    from eragvt.game.battle import commands,restraint
    ctx=make_context(data)
    called=[]
    def marker(ctx,*args):
        called.append(True)
        return 81
        yield
    # 只隔離指令內容，保留真run_com選路；expected為原作全部38個入口均能分派。
    for name in ("com0","com_attack","com4","com5","com6","com7","com99","com69","com16","com17","com_ex_gauge","com70","com73","com74"):
        monkeypatch.setattr(commands,name,marker)
    for key in restraint.RESTRAINT_COMS:
        monkeypatch.setitem(restraint.RESTRAINT_COMS,key,marker)
    assert run_no_input(commands.run_com(ctx,number)) == 81
    assert called == [True]


@pytest.mark.parametrize("kind,number",[("boss",n) for n in range(1,8)]+[("last1",1),("last2",2)]+[("mob",n) for n in (1,2,3,101,102,201,301,501,601,701,702,801,802,803,901,902)]+[("citizen",1150)])
def test_legal_enemy_data_dispatch(data,kind,number):
    # COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:198–309；_SHORT固定值，無RNG。
    from eragvt.game.battle.core import tentacle_access
    ctx=make_context(data)
    prepare_recovery(ctx,kind)
    ctx.state.flag[11]=number
    # 各原始資料的SHORT值另由既有test_battle/test_mob_battle覆蓋；本案例驗合法路由不落守衛。
    assert isinstance(tentacle_access(ctx,"SHORT"),int)
    assert ctx.state.rng.bounds == []


@pytest.mark.parametrize("kind",["last1","last2"])
@pytest.mark.parametrize("powered",[False,True])
def test_real_train_recovery(data,kind,powered):
    from eragvt.game.battle.train import run_train
    from eragvt.state import GameRng
    from test_transformation_parts import prepare_battle
    ctx=make_context(data)
    prepare_battle(ctx)
    prepare_recovery(ctx,kind,powered,50000 if powered else 10000,25000 if powered else 5000)
    st=ctx.state
    st.rng=GameRng(81)
    gen=run_train(ctx)
    assert next(gen) is None
    # 人工前態停在原生戰鬥輸入：下一次敵行動4；非自然遭遇。
    st.tflag[24]=0
    st.tflag[10],st.tflag[16]=4,-1
    st.flag[14],st.flag[15]=1000,0
    if kind == "last2":
        st.flag[21]=2  # HP50%時已進第二形態，避免人工前態落入另外的轉階段事件。
    assert gen.send(7) is None
    assert st.flag[13] == (25200 if powered else 5200)
    assert st.temp.prevcom == 7
    assert_ages(st)
    gen.close()
