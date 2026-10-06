"""S83：模式規則的expected取自原文，全部使用人工25歲前態。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.battle import after, enemy, palam, source_check, train
from eragvt.game.battle.core import BeginAfterTrain, P_GUARD, P_NORMAL, get_local
from eragvt.game.input_request import WaitInputRequest
from eragvt.state.constants import GameMode, MODE_OPTIONS
from eragvt.text import TextOutput
from tools.sim_adult import adult_data, assert_ages
from test_transformation_parts import make_context
from test_special_equipment import TrackingRng
from _gen_driver import run_no_input


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


def context(data, mode=GameMode.INSTANT):
    ctx = make_context(data)
    st, c = ctx.state, ctx.state.target_chara
    st.flag[0], st.flag[2], st.flag[3], st.flag[100] = MODE_OPTIONS[mode], 10, 7, 127
    st.flag[10], st.flag[11], st.savestr[13] = 0, 1, "BOSS"
    st.flag[700], st.flag[802], st.flag[850] = 1, 0, (1 << 14)
    st.day[0] = 0
    for n in (0, 1, 2):
        c.base[n], c.maxbase[n], c.base[50+n] = 500, 1000, 100
    for n in (10, 11, 12, 13):
        c.base[n] = c.maxbase[n] = 100
    st.rng = TrackingRng([])
    return ctx


# ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_KIRYOKUDOWN:1465–1562。
# Lv4、耐性0、MAX氣力1000→75*104/100=78；先clamp再GUTS，基礎扣減取GUTS後數字。
@pytest.mark.parametrize("enabled,current,command,expected,basis", [
    (True,500,4,422,61), (False,500,4,422,100),
    (True,50,100,1,76), (True,49,100,0,76),
    (True,1,100,0,100), (True,0,4,0,100),
])
def test_kiryoku_decline(data,enabled,current,command,expected,basis):
    ctx = context(data, GameMode.INSTANT if enabled else GameMode.NORMAL)
    st,c = ctx.state,ctx.state.target_chara
    c.base[1], c.base[2], st.temp.selectcom = current,0,command
    palam.palam_kiryokudown(ctx,0,0,0)
    assert (c.base[1],c.base[51]) == (expected,basis)
    assert c.maxbase[1] == 1000 and st.rng.bounds == []
    assert st.result[8] == 765 and st.results[8] == "尾格"


def test_kiryoku_display_precedes_guts(data):
    # PALAM_UP.ERB@PALAM_KIRYOKUDOWN:1545–1561：畫面50/25，GUTS後實扣49/24。
    ctx=context(data)
    ctx.out=TextOutput()
    st,c=ctx.state,ctx.state.target_chara
    c.base[1],c.base[2],st.temp.selectcom=50,0,100
    palam.palam_kiryokudown(ctx,0,0,0)
    assert [line.text for line in ctx.out.lines] == ["気力が50 気力基礎が25減った！"]
    assert (c.base[1],c.base[51]) == (1,76)


def test_kiryoku_zero_local_returns_without_clamp(data):
    # 同函式:1539–1542：LOCAL0先RETURN，BASE負值不因此重設或增加基礎。
    ctx=context(data)
    c=ctx.state.target_chara
    c.maxbase[1],c.base[1]=0,-3
    palam.palam_kiryokudown(ctx,0,0,0)
    assert (c.base[1],c.base[51]) == (-3,100)


def test_endless_zero_target_uses_normal_encounter_candidates(data):
    # ENCOUNT.ERB@ENCOUNT_BOSS:188–219、258–268：FLAG18=0略過索敵，從存活1..7選。
    # 可再次抽到剛擊破的1；不把註解的避免連戰擅修成RAND+1。
    from eragvt.game.battle.encount import encount_boss
    ctx=context(data,GameMode.SURVIVAL)
    st,c=ctx.state,ctx.state.target_chara
    st.flag[3],st.flag[18],st.flag[46],st.flag[47]=8,0,28,28
    c.cflag[100]=101
    st.rng=TrackingRng([0,0])
    assert encount_boss(ctx) == 1
    assert (st.flag[11],st.flag[18],st.flag[100]) == (1,1,127)
    assert st.rng.bounds == [100,7]


# 同檔@PALAM_SEITAISEIDOWN:1565–1668：服從門檻、Lv4倍率204/200、負基礎值不鉗制。
@pytest.mark.parametrize("arg,current,basis_before,expected,basis_after", [
    (499,500,100,500,100),(500,500,100,499,100),
    (999,500,100,499,100),(1000,500,100,498,99),
    (19999,500,100,490,95),(20000,500,100,488,94),
    (20000,3,1,0,0),(20000,4,1,0,-1),(20000,0,1,0,1),
])
@pytest.mark.parametrize("enabled",[False,True])
def test_seitaisei_decline(data,arg,current,basis_before,expected,basis_after,enabled):
    ctx=context(data,GameMode.INSTANT if enabled else GameMode.NORMAL)
    st,c=ctx.state,ctx.state.target_chara
    c.base[2],c.base[52]=current,basis_before
    palam.palam_seitaiseidown(ctx,arg,0)
    assert (c.base[2],c.base[52]) == (expected,basis_after if enabled else basis_before)
    assert c.maxbase[2] == 1000 and st.rng.bounds == []


# ERB/ゲーム内_戦闘処理/INSTANT_ARG_DOWN.ERB@INSTANT_ARG_DOWN:1–32。
# 五次/兩次均RAND5；4扣體力基礎10、其他扣當前BASE10–13，無下限，MAXBASE不變。
@pytest.mark.parametrize("transformed,rolls,expected", [
    (0,[0,1,2,3,4],[0,0,0,0,-9]),
    (1,[4,4],[1,1,1,1,-19]),
    (2,[0,0],[-1,1,1,1,1]),
])
def test_instant_wait_and_decline(data,transformed,rolls,expected):
    ctx=context(data)
    st,c=ctx.state,ctx.state.target_chara
    c.cflag[1]=transformed
    for n in (10,11,12,13,50):
        c.base[n]=1
    st.rng=TrackingRng(rolls)
    gen=train.instant_arg_down(ctx)
    assert isinstance(next(gen),WaitInputRequest)
    assert st.result[0] == 876 and st.results[0] == "保留字串"
    assert [c.base[n] for n in (10,11,12,13,50)] == [1]*5
    assert st.rng.bounds == []
    with pytest.raises(StopIteration):
        gen.send(None)
    assert [c.base[n] for n in (10,11,12,13,50)] == expected
    assert st.rng.bounds == [5]*len(rolls)
    assert get_local(st,"INSTANT_ARG_DOWN",1) == 0
    assert get_local(st,"INSTANT_ARG_DOWN",2) == rolls[-1]
    # 引擎函式落底寫RESULT:0=0，PRINTFORMW不寫數值/字串。
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67；GameView/EmueraConsole.cs:707–734。
    assert st.result[0] == 0 and st.result[8] == 765 and st.results[0] == "保留字串"
    assert [c.maxbase[n] for n in (10,11,12,13)] == [100]*4
    assert_ages(st)


# ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:311–333。
# DAY/14+擊破/10，90/135/180或20/40/60各+1，上限FLAG2；僅最後ELSEIF含GOTO。
@pytest.mark.parametrize("day,kills,limit,offset,expected", [
    (13,0,10,0,3),(14,0,10,100,99),
    (89,0,100,100,94),(90,0,100,100,93),
    (134,0,100,100,90),(135,0,100,100,89),
    (179,0,100,100,86),(180,0,100,100,85),
    (0,19,100,100,99),(0,20,100,100,97),
    (0,39,100,100,96),(0,40,100,100,94),
    (0,59,100,100,93),(0,60,100,100,91),
    (180,60,5,100,95),(0,0,10,-11,-10),
    (0,0,10,-110,-10),(0,0,10,-111,-101),
    (0,0,10,-1010,-1000),(0,0,10,-1011,-911),
])
def test_endless_deadline(data,day,kills,limit,offset,expected):
    ctx=context(data,GameMode.SURVIVAL)
    st=ctx.state
    st.day[0],st.day[1],st.flag[2],st.flag[3]=day,offset,limit,7+kills
    after._endless_deadline(ctx)
    assert st.day[1] == expected
    assert st.result[0] == 7 and st.result[8] == 765
    assert st.rng.bounds == []


# ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:142–165。
# 7次RAND11先更新累積傷害；ENDLESS保留bit、總數+1、重抽直到不同，不加1。
@pytest.mark.parametrize("mode",list(GameMode)[1:])
def test_victory_endless_options(data,monkeypatch,mode):
    from eragvt.game import opening
    ctx=context(data,mode)
    st=ctx.state
    st.flag[18],st.flag[301]=1,900
    endless=mode in (GameMode.SURVIVAL,GameMode.FREEPLAY,GameMode.SANDBOX)
    st.rng=TrackingRng([0]*7+([1,1,0] if endless else []))
    monkeypatch.setattr(source_check,"_supart_blood",lambda ctx: iter(()))
    monkeypatch.setattr(source_check,"_rescue_captives",lambda ctx: None)
    monkeypatch.setattr(opening,"research_quota",lambda st: None)
    with pytest.raises(BeginAfterTrain):
        run_no_input(source_check._victory(ctx))
    assert (st.flag[100],st.flag[3],st.flag[18]) == ((127,8,0) if endless else (126,7,0))
    assert st.flag[301] == 0 and st.tflag[98] == 1
    assert st.rng.bounds == [11]*7+([7]*3 if endless else [])
    assert st.result[8] == 765 and st.results[8] == "尾格"


# ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:520–540。
# 完全防禦跳過當前資源扣減，但仍減原LOCAL3/2；一般命中先clamp再扣基礎。
@pytest.mark.parametrize("enabled,guard,current,expected,basis", [
    (True,False,500,300,0),(False,False,500,300,100),
    (True,False,3,0,99),(True,True,500,500,50),
    (True,True,3,3,50),(True,False,0,0,100),
])
def test_enemy_decline(data,monkeypatch,enabled,guard,current,expected,basis):
    ctx=context(data,GameMode.INSTANT if enabled else GameMode.NORMAL)
    st,c=ctx.state,ctx.state.target_chara
    st.tflag[10],st.tflag[16]=3,-1
    c.tcvarn[0]=2
    c.base[1],c.tcvarn[2]=current,P_GUARD if guard else P_NORMAL
    # 命中判定／後續PALAM隔離，保留敵行動實際LOCAL計算與完全防禦RAND。
    monkeypatch.setattr(enemy,"act_hantei_tentacle_to_chara",lambda *args: 0)
    monkeypatch.setattr(enemy,"palam_cal",lambda *args: iter(()))
    monkeypatch.setattr(enemy,"shinkyou_change",lambda *args: None)
    # CHARA_STATE_CHANGE.ERB@STATE_CHANGE_BETOBETO:288–312：完全防禦略過RAND；HAIRAN仍抽。
    st.rng=TrackingRng([0,99] if guard else [99,99])
    run_no_input(enemy._enemy_action_once(ctx))
    assert (c.base[1],c.base[51]) == (expected,basis)
    assert st.rng.bounds == [100,100]


@pytest.mark.parametrize("mode",list(GameMode)[1:])
def test_event_comend_decline_order(data,monkeypatch,mode):
    # ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@EVENTCOMEND:929–986。
    # 先經驗/衰減/事件TURNEND，再INSTANT等待與下降；開關來自FLAG0而非模式名稱。
    from eragvt.game import raid
    ctx=context(data,mode)
    st,c=ctx.state,ctx.state.target_chara
    st.flag[20]=100
    c.nowex[0],c.palam[13],st.temp.selectcom=2,1000,4
    c.base[50]=100
    seen=[]
    monkeypatch.setattr(raid,"event_battle_turnend",lambda ctx: seen.append((c.ex[0],c.palam[13],c.base[50])))
    st.rng=TrackingRng([4]*5 if mode == GameMode.INSTANT else [])
    gen=train.event_comend(ctx)
    if mode == GameMode.INSTANT:
        assert isinstance(next(gen),WaitInputRequest)
        assert seen == [(2,950,100)] and c.base[50] == 100
        with pytest.raises(StopIteration):
            gen.send(None)
    else:
        run_no_input(gen)
    assert c.base[50] == (50 if mode == GameMode.INSTANT else 100)
    assert seen == [(2,950,100)]
