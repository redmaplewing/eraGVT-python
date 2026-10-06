"""S79 expected：ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST／MODE_SELECT。

採全新25歲人工資料；模式只驗開局，完整生命週期仍屬W06。
"""
import pytest

from eragvt.data import load_game_data, default_csv_dir
from eragvt.state import GameState, GameRng
from eragvt.state.savefile import GlobalStore
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first_gen, mode_select_gen, prologue_gen
from tools.sim_adult import adult_data


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    return Ctx(GameState.new(data, GameRng(79)), data, TextOutput(), NullNarrationService(), GlobalStore())


@pytest.mark.parametrize('mode,flags,count,days,limit', [
    (1, 2, 3, 11, 87), (2, 10, 1, 12, 94), (3, 4, 3, 13, 101),
    (4, 18, 3, 9, 0), (5, 114, 3, 9, 0),
    (6, 498, 3, 9, 0), (7, 1538, 3, 11, 87),
])
def test_seven_new_game_modes(ctx, mode, flags, count, days, limit):
    # DIM.ERH:83–92；EVENTFIRST:114–122；SET_LIMIT_DAY:430–451。
    st = ctx.state
    g = event_first_gen(st, ctx.data, ctx.out, ctx.globals, ctx.narration)
    next(g)
    g.send(mode)
    assert st.flag[0] == flags
    assert st.charanum == count + 1
    g.send(1000)
    assert st.flag[2] == days and st.flag[1] == limit
    g.send(1)
    assert any('プロローグを表示しますか' in line.text for line in ctx.out.lines)
    with pytest.raises(StopIteration) as done:
        g.send(0)
    assert done.value.value is True
    assert st.target == count
    assert all(c.cflag[999] == 1 for c in st.charas[1:])


def test_mode_invalid_back_reenter(ctx):
    # MODE_SELECT:371／391–392；EVENTFIRST:128–132 返回只刪角色、保留FLAG:8。
    st = ctx.state
    g = event_first_gen(st, ctx.data, ctx.out, ctx.globals, ctx.narration)
    next(g)
    for invalid in (-3, 0, 8, 99):
        g.send(invalid)
        assert st.charanum == 1
        assert any('タイトルに戻る' in line.text for line in ctx.out.lines)
    g.send(1)
    g.send(999)
    assert st.charanum == 1 and st.flag[8] == 3
    g.send(2)
    assert st.charanum == 2 and st.flag[8] == 4
    g.send(999)
    with pytest.raises(StopIteration) as done:
        g.send(100)
    assert done.value.value is False and st.result[0] == 999


@pytest.mark.parametrize('count', [0, 1, 2])
def test_shared_succession_mode_restrictions(ctx, count):
    # MODE_SELECT:309、372：引繼禁止SANDBOX，多人時禁止SOLO。
    g = mode_select_gen(ctx, inherited=True, count=count)
    next(g)
    g.send(6)
    if count > 1:
        g.send(2)
    with pytest.raises(StopIteration) as done:
        g.send(100)
    assert done.value.value == 999


def test_prologue_invalid_and_skip_preserves_other_results(ctx):
    # EVENTFIRST:177–185：INPUT_LOOP_PRO無返回選項；0只印空行。
    ctx.state.result[1] = 73
    ctx.state.results[0] = '保留'
    g = prologue_gen(ctx)
    next(g)
    before = ctx.state.rng.snapshot()
    for value in (-1, 2, 99):
        g.send(value)
        assert ctx.state.result[0] == value
    with pytest.raises(StopIteration):
        g.send(0)
    assert ctx.state.result[0] == 0 and ctx.state.result[1] == 73
    assert ctx.state.results[0] == '保留' and ctx.state.rng.snapshot() == before


def test_prologue_view_explicit_scope_stop(ctx):
    g = prologue_gen(ctx)
    next(g)
    with pytest.raises(NotImplementedError, match='序章'):
        g.send(1)


def test_first_catalog_inputs_and_waits(ctx, tmp_path):
    """中性人工catalog驗接線；非原作敘事內容驗收。

    原呼叫順序EVENTFIRST:257–266；WAIT不寫RESULT(S)：
    reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、707–734。
    """
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.game.input_request import WaitInputRequest, TextInputRequest
    source = ('@KOJO_0_FIRST_12\nCFLAG:280 += 1\nPRINTW 中性開局確認\n'
              'PRINTL 中性文字輸入\nINPUTS\nCSTR:20 = %RESULTS%\n'
              'PRINTL [7]中性數字確認\nINPUT\nCFLAG:281 = RESULT\nFORCEWAIT\n')
    (tmp_path / '口上').mkdir()
    (tmp_path / '口上' / 'neutral.ERB').write_text(source, encoding='utf-8', newline='\n')
    svc = CatalogNarrationService(tmp_path, ctx.data)
    g = event_first_gen(ctx.state, ctx.data, ctx.out, ctx.globals, svc)
    next(g)
    for v in (1, 200, 0, 1, 1000, 1):g.send(v)
    # 套組0第一人的性格12；第二/三人不符人工catalog，走既有找不到分派。
    assert isinstance(g.send(0), WaitInputRequest)
    c = ctx.state.charas[1]
    assert ctx.state.target == 1 and c.cflag[999] == 0 and c.cflag[280] == 1
    before = (ctx.state.result.copy(), ctx.state.results.copy())
    assert isinstance(g.send(''), TextInputRequest)
    assert (ctx.state.result, ctx.state.results) == before
    assert g.send('中性輸入') is None
    assert isinstance(g.send(7), WaitInputRequest)
    assert c.cstr[20] == '中性輸入' and c.cflag[281] == 7 and c.cflag[280] == 1
    with pytest.raises(StopIteration):g.send('')
    assert svc.failures == [] and ctx.state.target == 3
    assert all(c.cflag[999] == 1 for c in ctx.state.charas[1:])


@pytest.mark.parametrize('mode,count', [(1,3),(2,1),(3,3),(4,3),(5,3),(6,3),(7,3)])
def test_seven_mode_session_boundary(data, tmp_path, mode, count):
    from eragvt.game.session import GameSession, Phase
    session = GameSession(data, tmp_path, rng=GameRng(79), narration=NullNarrationService())
    for value in (0, mode, 1000, 1, 0):session.input(value)
    # EVENTFIRST:292 BEGIN SHOP；SystemProc:614–680 EVENTSHOP→自動存檔→SHOP。
    assert session.phase == Phase.SHOP
    assert session.state.charanum == count + 1
    assert (tmp_path/'save99.json').exists()


def test_sim_confirmation_does_not_consume_policy_rng():
    from types import SimpleNamespace
    from tools.sim import _input_choice
    class Policy:
        def choice(self, values):raise AssertionError('確認不能消耗策略亂數')
    seen=[]
    session=SimpleNamespace(input_kind='wait', input=seen.append)
    _input_choice(session, Policy(), [0,1])
    assert seen == ['']
