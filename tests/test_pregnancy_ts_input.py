"""S71：原作狀態轉換／輸入續行；全部前態為人工25歲兩形態。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.battle import ninsin
from eragvt.game.battle.func import transform
from eragvt.state import GameState, FixedRng
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, FixedRng([]))
    st.charas = st.charas[:1]
    c = st.add_chara(data, 0)
    c.name = c.callname = "人工成年TS"
    c.talent.clear()
    c.cflag.clear()
    c.cflag[6] = 99999
    st.target = 1
    st.flag[2] = 100  # 場景有效期限，供真實TENTACLE_LEVEL除數使用。
    st.result[8], st.results[0], st.results[8] = 765, "保留字串", "尾格"
    for slot in (13, 14, 30, 31, 32, 33, 34, 35, 36, 37):
        c.cstr[slot] = "黒" if slot >= 30 else "短髮"
    c.cstr[14] = "長髮"
    c.cstr[31], c.cstr[34], c.cstr[35], c.cstr[37] = "赤", "青", "緑", "褐色"
    assert_ages(st)
    return Ctx(st, data, TextOutput(), NullNarrationService())


def set_t(ctx, name, value):
    ctx.state.target_chara.talent[ctx.data.index_of("TALENT", name)] = value


def trait(ctx, name):
    return ctx.state.target_chara.talent[ctx.data.index_of("TALENT", name)]


def prepare_ts(ctx):
    set_t(ctx, "オトコ", 1)
    set_t(ctx, "変身能力", 1)
    set_t(ctx, "変身時ＴＳ", 1)
    transform(ctx, 1)


def drive(gen, answers=()):
    answers = iter(answers)
    try:
        next(gen)
        while True:
            answer = next(answers, None)
            assert answer is not None, "未提供真實INPUT回答"
            gen.send(answer)
    except StopIteration as exc:
        assert next(answers, None) is None, "流程提早結束"
        return exc.value


def assert_conversion(ctx, result_tail=765):
    c = ctx.state.target_chara
    assert (ctx.state.target, c.cflag[1], trait(ctx, "性別変化"), trait(ctx, "変身時ＴＳ")) == (1, 1, 1, -1)
    assert [c.cstr[i] for i in (13,30,32,33,36)] == ["長髮", "黒", "青", "緑", "黒"]
    assert ctx.state.result[8] == result_tail
    assert (ctx.state.results[0], ctx.state.results[8]) == ("保留字串", "尾格")
    assert_ages(ctx.state)


def test_flag_normal_wait_and_resume(ctx):
    # ERB/ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_FLAG:214–218、248–256。
    prepare_ts(ctx)
    ctx.state.target_chara.cflag[230] = -1
    ctx.state.rng = FixedRng([20])
    gen = ninsin.ninsin_flag(ctx)
    assert next(gen) is None
    assert trait(ctx, "妊娠") == 4
    assert ctx.state.target_chara.cflag[228] == 266
    assert ctx.state.rng.snapshot() == []
    assert gen.send(9) is None
    assert ctx.state.rng.snapshot() == []
    # 0髮型、1髮色、0瞳色、1膚色；原作TS_MtoF的各題不加額外確認。
    for answer in (0,1,0):
        assert gen.send(answer) is None
    with pytest.raises(StopIteration):
        gen.send(1)
    assert_conversion(ctx)
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize("female,ts,form", [(1,1,0),(1,0,1),(0,1,1)])
def test_fix_nonconversion(ctx, female, ts, form):
    # 同檔@NINSIN_TS_FIX:263–270：只有女性且TS且已變身才轉換。
    set_t(ctx,"オトコ",1-female)
    set_t(ctx,"変身時ＴＳ",ts)
    ctx.state.target_chara.cflag[1] = form
    assert drive(ninsin.ninsin_ts_fix(ctx)) is None
    assert trait(ctx,"性別変化") == 0
    assert ctx.state.target_chara.cstr[13] == "短髮"
    assert ctx.state.target_chara.cflag[1] == form


@pytest.mark.parametrize("enabled,draws,preg,size,count", [(0,[2,20],1,264,3),(1,[0,2,20],1,264,3),(1,[99,20],3,266,0)])
def test_check_after_branches(ctx, enabled, draws, preg, size, count):
    # 同檔@NINSIN_CHECK_AFTER:171–189；NUM_CHILD_TENTACLE:583–584，PREGNANT_RANDOM_SIZE:833–839。
    prepare_ts(ctx)
    set_t(ctx,"妊娠",2)
    ctx.state.flag[805] = enabled
    ctx.state.rng = FixedRng(draws)
    drive(ninsin.ninsin_check_after(ctx), [9,0,1,0,1])
    assert (trait(ctx,"妊娠"),ctx.state.target_chara.cflag[228],ctx.state.target_chara.cflag[227]) == (preg,size,count)
    assert ctx.state.rng.snapshot() == []
    assert_conversion(ctx)
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize("preg,female", [(0,1),(1,1),(3,1),(4,1),(2,0)])
def test_check_after_noop(ctx,preg,female):
    set_t(ctx,"妊娠",preg)
    set_t(ctx,"オトコ",1-female)
    drive(ninsin.ninsin_check_after(ctx))
    assert trait(ctx,"妊娠") == preg
    assert ctx.state.result[8] == 765


@pytest.mark.parametrize("outcome,enemy", [(0,"BOSS"),(1,"MOB"),(1,"BOSS"),(2,"BOSS")])
def test_eventend_real_wait_then_cleanup(ctx,outcome,enemy):
    # ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:204/252/300/393：
    # 確認後才TRANSFORM 0；:479–480清BASE、:516清TCVARn、:536回TURNEND。
    from eragvt.game.action import Step
    from eragvt.game.battle.after import event_end
    st,c=ctx.state,ctx.state.target_chara
    prepare_ts(ctx)
    set_t(ctx,"妊娠",2)
    c.abl[ctx.data.index_of("ABL","レベル")]=10
    c.cflag[999]=1
    c.base[20],c.base[21]=17,18
    c.tcvarn[99]=123
    st.savestr[13]=enemy
    st.flag[11]=3
    st.flag[12],st.flag[13]=10000,3000
    st.flag[46],st.flag[47]=28,36
    st.flag[700]=1
    st.flag[73]=1
    st.flag[805]=0
    st.flag[100]=127
    st.tflag[98]=outcome
    st.rng=FixedRng([0]*200)
    gen=event_end(ctx)
    assert next(gen) is None
    assert (c.base[20],c.base[21],c.tcvarn[99]) == (17,18,123)
    pending_rng=st.rng.snapshot()
    assert gen.send(9) is None
    assert st.rng.snapshot() == pending_rng
    for answer in (0,1,0):
        assert gen.send(answer) is None
    with pytest.raises(StopIteration) as end:
        gen.send(1)
    assert end.value.value == Step.TURNEND
    assert (trait(ctx,"妊娠"),trait(ctx,"性別変化"),trait(ctx,"変身時ＴＳ")) == (1,1,-1)
    assert (c.base[20],c.base[21],c.tcvarn[99],c.cflag[1]) == (0,0,0,0)
    assert st.target == 1
    assert_ages(st)


@pytest.mark.parametrize("entry", ["palam_cal","command","command2"])
def test_shared_settlement_real_wait(ctx,entry):
    # ERB/ゲーム内_戦闘処理/COMMON_PALAM_CAL.ERB@PALAM_CAL:24 →
    # PALAM_UP.ERB@PALAM_UP:145 → TENTACLE_SYASEI.ERB@TENTACLE_SYASEI_CHECK:202 →
    # @TENTACLE_SYASEI_POINT:306 → PREGNANT_SOURCE_NINSIN.ERB@NINSIN_FLAG:256。
    from eragvt.game.battle.palam import palam_cal
    from eragvt.game.battle.sexcom import _run
    st,c=ctx.state,ctx.state.target_chara
    prepare_ts(ctx)
    other=st.add_chara(ctx.data,0)
    other.talent.clear()
    other.cflag.clear()
    other.cflag[240]=2
    other.talent[ctx.data.index_of("TALENT","オトコ")]=1
    other.name=other.callname="人工成年乙"
    st.savestr[13]="BOSS"
    st.flag[110],st.flag[111]=1,2
    st.flag[11]=3
    st.flag[700]=1
    st.flag[12],st.flag[13]=100000,100000
    st.flag[14],st.flag[15]=100,100
    st.tflag[4]=64 if entry=="command2" else 2
    st.tflag[18]=2
    c.cflag[217]=0
    st.flag[805]=0
    st.rng=FixedRng([0]*300)
    gen=palam_cal(ctx,*([0]*12)) if entry=="palam_cal" else _run(ctx,2 if entry=="command2" else 0,0)
    assert next(gen) is None
    assert trait(ctx,"妊娠") == 4
    # TENTACLE_SYASEI_CHECK在TS等待之後才扣FLAG:15；不先完成結算。
    assert st.flag[15] >= 100
    pending=st.rng.snapshot()
    assert gen.send(9) is None
    assert st.rng.snapshot() == pending
    for answer in (0,1,0):
        assert gen.send(answer) is None
    with pytest.raises(StopIteration) as end:
        gen.send(1)
    assert end.value.value == (None if entry=="palam_cal" else 1)
    # SEX_COM0.ERB@SEX_COM0:37增加50；TENTACLE_SYASEI.ERB@TENTACLE_SYASEI_UP:69–70
    # RAND=0乘0.90，增加45；CHECK:210再扣100，剩45。
    assert st.flag[15] == (0 if entry=="palam_cal" else 45)
    # SEX_COMEX.ERB@SEX_COMEX:338覆寫RESULT:0–11，這個前態第8格為0。
    assert_conversion(ctx, 765 if entry=="palam_cal" else 0)


@pytest.fixture(scope="module")
def catalog(data):
    from eragvt.narration.service import CatalogNarrationService
    return CatalogNarrationService(default_csv_dir().parent/"ERB", data)


@pytest.mark.parametrize("name,line", [("PASTIME_NANPA_TAKEOUT",3019),
    ("PASTIME_SAKE_NANPA_TAKEOUT",1606),("PASTIME_CHIKAN_TAKEOUT",1732),("MESSAGE_SEX_COM2",1274)])
def test_catalog_original_hook_waiting_boundary(ctx,catalog,monkeypatch,name,line):
    # 各同名ERB@TAKEOUT原呼叫行；只取原NINSIN_HANTEI hook執行，
    # 不執行敘事／其他狀態生成。驗真實自由行動_run→run_event_gen→native hook通道。
    from dataclasses import replace
    from eragvt.game.pastime_nanpa import _run
    from eragvt.narration.nodes import Hook, iter_stmts
    original=catalog.catalog.get(name)
    hook=next(n for n in iter_stmts(original.body) if isinstance(n,Hook) and n.line==line)
    assert hook.args[0].name == "NINSIN_HANTEI"
    monkeypatch.setitem(catalog.catalog._parsed,name,replace(original,body=[hook],calls=set(),dynamic_calls=[],unsupported=[]))
    monkeypatch.setitem(catalog.catalog._support,name,None)

    class HookNarration(NullNarrationService):
        def run_event_gen(self,cx,func,args=None):
            return (yield from catalog.run_event_gen(cx,func,args))

    ctx.narration=HookNarration()
    prepare_ts(ctx)
    if name=="MESSAGE_SEX_COM2":
        # 該原hook未傳ARG:2，設人工同伴來源，使正常狀態分支與其他案例相同。
        other=ctx.state.add_chara(ctx.data,0)
        other.talent.clear()
        other.cflag.clear()
        other.cflag[240]=2
        other.talent[ctx.data.index_of("TALENT","オトコ")]=1
        ctx.state.flag[110],ctx.state.flag[111],ctx.state.flag[700]=1,2,1
        ctx.state.flag[11]=3
        ctx.state.savestr[13]="BOSS"
    ctx.state.rng=FixedRng([0,0,20])  # CHECK_HININ、HANTEI成功、SIZE。
    from eragvt.game.battle.sexmsg import msg_com2
    gen=msg_com2(ctx,0,0) if name=="MESSAGE_SEX_COM2" else _run(ctx,name,[],"hook邊界")
    assert next(gen) is None
    assert trait(ctx,"妊娠") == 4
    assert ctx.state.target_chara.cflag[228] == 266
    assert ctx.state.rng.snapshot() == []
    assert gen.send(9) is None
    assert ctx.state.rng.snapshot() == []
    for answer in (0,1,0):
        assert gen.send(answer) is None
    with pytest.raises(StopIteration) as end:
        gen.send(1)
    # 原函式終端清RESULT:0；其他尾格不動。
    assert end.value.value == (None if name=="MESSAGE_SEX_COM2" else 0)
    assert_conversion(ctx)
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize("form,boss", [(0,2),(1,1),(1,2),(2,0)])
def test_prison_readers_and_routine_return(ctx,form,boss):
    # ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:314–343。
    # 各BOSS routine以RAND=99走RETURN 0；同步getter維持原資料型別。
    from eragvt.game.prison.event import tentacle_access_prison, prison_routine
    c=ctx.state.target_chara
    c.cflag[20],c.cflag[21]=form,boss
    ctx.state.rng=FixedRng([99] if form!=2 else [])
    assert isinstance(tentacle_access_prison(ctx,1,"NAME"),str)
    assert isinstance(tentacle_access_prison(ctx,1,"GETNAME"),str)
    assert isinstance(tentacle_access_prison(ctx,1,"PALAM_HOSEI"),tuple)
    assert drive(prison_routine(ctx,1)) == 0
    assert ctx.state.rng.snapshot() == []


@pytest.mark.parametrize("conf,status,roll,preg,count,size", [
    (0,1,0,1,1,70),(1,1,0,1,1,70),(1,0,0,3,0,212),(1,1,99,3,0,212)])
def test_flag_immediate_branch(ctx,conf,status,roll,preg,count,size):
    # PREGNANT_SOURCE_NINSIN.ERB@NINSIN_FLAG:227–245：OR之後仍要求CFLAG:0==1。
    prepare_ts(ctx)
    c=ctx.state.target_chara
    c.cflag[21],c.cflag[0],c.cflag[230]=2,status,2
    ctx.state.flag[805]=conf
    ctx.state.rng=FixedRng(([roll] if conf else [])+([0,0] if preg==1 else [0]))
    drive(ninsin.ninsin_flag(ctx),[0,1,0,1])
    assert (trait(ctx,"妊娠"),c.cflag[227],c.cflag[228]) == (preg,count,size)
    assert ctx.state.rng.snapshot() == []
    assert_conversion(ctx)
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize("ts,form", [(0,0),(0,1),(1,0)])
def test_flag_normal_nonconversion(ctx,ts,form):
    # @NINSIN_FLAG:248–257：女性但沒有TS／未變身不呼叫TS_MtoF。
    set_t(ctx,"変身時ＴＳ",ts)
    c=ctx.state.target_chara
    c.cflag[1],c.cflag[230]=form,-1
    ctx.state.rng=FixedRng([20])
    drive(ninsin.ninsin_flag(ctx))
    assert (trait(ctx,"妊娠"),trait(ctx,"性別変化"),c.cflag[1]) == (4,0,form)
    assert ctx.state.rng.snapshot() == []


@pytest.mark.parametrize("success", [True,False])
def test_hantei_return_register(ctx,success):
    # PREGNANT_SOURCE_NINSIN.ERB@NINSIN_HANTEI:162–165的RETURN 1／0。
    # 普通來源3×800/2開根號=34，角色狀態0再加100；RAND=999不成立。
    prepare_ts(ctx)
    ctx.state.result[0]=876
    ctx.state.rng=FixedRng([0,0,20] if success else [0,999])
    result=drive(ninsin.ninsin_hantei(ctx,3,800,-1),[0,1,0,1] if success else [])
    assert result == ctx.state.result[0] == int(success)
    assert ctx.state.result[8] == 765
    assert ctx.state.rng.snapshot() == []


def test_prison_real_routine_wait(ctx):
    # TENTACLE_BOSS_2_Ｖ触手.ERB@TENTACLE_BOSS_2_PRISON_ROUTINE:192–208，
    # PRISON_COM1_Ｖ責め.ERB@PRISON_COM1:236–237；兩層dispatcher都需傳遞等待。
    from eragvt.game.prison.event import prison_routine
    prepare_ts(ctx)
    c=ctx.state.target_chara
    c.cflag[20],c.cflag[21],c.cflag[0]=0,2,1
    ctx.state.rng=FixedRng([0]*200)
    gen=prison_routine(ctx,1)
    assert next(gen) is None
    assert trait(ctx,"妊娠") == 1
    pending=ctx.state.rng.snapshot()
    assert gen.send(9) is None
    assert ctx.state.rng.snapshot() == pending
    for answer in (0,1,0):assert gen.send(answer) is None
    with pytest.raises(StopIteration) as end:gen.send(1)
    assert end.value.value == 1
    # TENTACLE_BOSS_2_Ｖ触手.ERB@TENTACLE_BOSS_2_PALAM_HOSEI:117、125先寫RESULT:8=100。
    assert_conversion(ctx,100)


def test_web_ts_input_resume(ctx,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    prepare_ts(ctx)
    c=ctx.state.target_chara
    c.cflag[230]=-1
    ctx.state.rng=FixedRng([20])
    app=create_app(ctx.data,tmp_path,narration=NullNarrationService())
    session=app.state.session
    session.state=ctx.state
    session.globals.mem.global_[275]=1  # 人工前態已取得初始成就，聚焦TS輸入。
    completed=[]
    session._run_gen(ninsin.ninsin_flag(session._ctx()),lambda: completed.append(True))
    with TestClient(app) as client:
        assert client.get("/api/screen").status_code == 200
        assert client.post("/api/input",json={"value":9}).status_code == 200
        assert completed == []
        assert ctx.state.rng.snapshot() == []
        for answer in (0,1,0):
            assert client.post("/api/input",json={"value":answer}).status_code == 200
            assert completed == []
        assert client.post("/api/input",json={"value":1}).status_code == 200
        assert completed == [True]
        assert session._turn is None
    assert_conversion(ctx)
    assert ctx.state.result[0] == 0
