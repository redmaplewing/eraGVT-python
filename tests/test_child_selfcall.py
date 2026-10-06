"""S68：ADD_CHILD 的一般文字邊界；全新25歲人工資料，停在feat提示。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.child import add_child
from eragvt.game.input_request import TextInputRequest
from eragvt.state import FixedRng, GameState
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, FixedRng([1]))
    st.charas = st.charas[:1]
    parent = st.add_chara(data, 0)
    parent.name = parent.callname = '人工成年親'
    parent.cstr[10] = parent.cstr[11] = ''
    parent.talent.clear()
    parent.talent[209] = 1
    parent.cflag[240] = 123
    st.target = 1
    return Ctx(st, data, TextOutput(), NullNarrationService())


def text(ctx):
    return '\n'.join(line.text for line in ctx.out.lines)


def enter(ctx):
    """ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:322–515。

    真實命名入口→手輸→確認；未執行之後的成長／身體生成。
    """
    gen = add_child(ctx, 1)
    assert next(gen) is None
    assert isinstance(gen.send(1), TextInputRequest)
    assert gen.send('人工成年') is None
    assert gen.send(1) is None
    assert '一人称' in text(ctx)
    assert 'フィートを設定しますか？' not in text(ctx)
    assert ctx.state.target == 2
    assert ctx.state.charas[2].cflag[231] == 0
    assert_ages(ctx.state)
    return gen


def at_feat(ctx):
    """ADD_CHILD:523–545；SYUZOKU_CHECK:5–24 的 RETURN 留下209。"""
    assert 'フィートを設定しますか？' in text(ctx)
    assert '種族は『ケモミミ族』です' in text(ctx)
    st = ctx.state
    assert st.target == 2 and st.charas[2].cflag[231] == 209
    assert st.result[0] == 209
    assert st.result[8] == 678 and st.results[8] == '尾格'
    assert st.rng.snapshot() == []
    assert_ages(st)


@pytest.mark.parametrize('male,draws,code,display', [
    (0, [1], 0, '私'), (0, [0, 0, 2], 27, 'ボク'),
    (0, [0, 1, 0], 30, '俺'), (1, [1, 0, 1], 26, 'ぼく'),
    (1, [1, 1, 2], 32, 'オレ'),
])
def test_original_default_waits_and_confirms(ctx, male, draws, code, display):
    # ADD_CHILD:508–515：RAND20先抽；男性仍抽，只有條件成立才再抽2、3。
    st = ctx.state
    st.charas[1].cflag[226] = male
    st.rng = FixedRng(draws)
    gen = enter(ctx)
    c = st.charas[2]
    assert (c.cflag[8], c.cstr[4]) == (code, '')
    st.result[8], st.results[8] = 678, '尾格'
    gen.send(99)
    assert (c.cflag[8], c.cstr[4]) == (code, display)
    at_feat(ctx)
    gen.close()


@pytest.mark.parametrize('values,code,display', [
    ([6, 32, 99], 32, 'オレ'),
    ([22, 'キャ', 99], 12698, 'キャ'),
    ([22, '星', 'ほし', 99], 2205599, '星'),
    ([21, 'ほし', 99], 2205599, '人工成年'),
    ([6, 98], 0, ''),
    ([22, '星', 'ほし', 98], 0, ''),
])
def test_edit_or_cancel_then_original_next_prompt(ctx, values, code, display):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL:1291–1491。
    # :1460–1461取消不提交；ADD_CHILD:515沒有檢查回傳值，98也續行。
    gen = enter(ctx)
    ctx.state.result[8], ctx.state.results[8] = 678, '尾格'
    for value in values:
        gen.send(value)
    c = ctx.state.charas[2]
    assert (c.cflag[8], c.cstr[4]) == (code, display)
    at_feat(ctx)
    gen.close()


@pytest.mark.parametrize('cancel', ['', '99'])
@pytest.mark.parametrize('field', ['display', 'reading'])
def test_text_cancel_stays_in_selfcall(ctx, field, cancel):
    gen = enter(ctx)
    assert isinstance(gen.send(22), TextInputRequest)
    if field == 'reading':
        assert isinstance(gen.send('星'), TextInputRequest)
    assert isinstance(gen.send(cancel), TextInputRequest)
    gen.send('')  # 既有PRINTW等待
    assert 'フィートを設定しますか？' not in text(ctx)
    c = ctx.state.charas[2]
    assert (c.cflag[8], c.cstr[4], c.cflag[231]) == (0, '', 0)
    if field == 'reading':
        gen.send(99)  # 缺讀音，99不可越過
        assert 'フィートを設定しますか？' not in text(ctx)
        gen.send(0)
    ctx.state.result[8], ctx.state.results[8] = 678, '尾格'
    gen.send(99)
    at_feat(ctx)
    gen.close()


@pytest.mark.parametrize('invalid', [-1, 9, 999])
def test_invalid_menu_preserves_input_results_and_waits(ctx, invalid):
    # 原文:1488–1490跳讀音INPUTS；不是忽略，也不離開此流程。
    # reference/emuera-1824/Emuera/GameProc/Process.cs:249–260：INPUT(S)各只寫0格。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023：RETURN只寫指定格。
    gen = enter(ctx)
    st = ctx.state
    st.result[8], st.results[8] = 678, '尾格'
    assert isinstance(gen.send(invalid), TextInputRequest)
    assert st.result[0] == invalid
    assert isinstance(gen.send('99'), TextInputRequest)
    assert st.result[0] == invalid and st.results[0] == '99'
    gen.send('')
    assert 'フィートを設定しますか？' not in text(ctx)
    gen.send(99)
    at_feat(ctx)
    gen.close()


def test_web_child_text_and_confirmation(data, tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app

    app = create_app(data, tmp_path, narration=NullNarrationService())
    session = app.state.session
    session.state = GameState.new(data, FixedRng([1]))
    session.state.charas = session.state.charas[:1]
    parent = session.state.add_chara(data, 0)
    parent.cstr[10] = parent.cstr[11] = ''
    parent.talent.clear()
    parent.talent[209] = 1
    session._run_gen(add_child(session._ctx(), 1), lambda: None)
    client = TestClient(app)
    for value in (1, '人工成年', 1, 22, '星'):
        screen = client.post('/api/input', json={'value': value}).json()
    assert screen['input_kind'] == 'text'
    assert 'input' in client.get('/').text
    screen = client.post('/api/input', json={'value': 'ほし'}).json()
    assert screen['input_kind'] == 'number'
    token = screen['input_token']
    screen = client.post('/api/input', json={'value': 99, 'input_token': token}).json()
    assert 'フィートを設定しますか？' in client.get('/').text
    before = session.state.charas[2].to_json()
    client.post('/api/input', json={'value': 99, 'input_token': token})
    assert session.state.charas[2].to_json() == before
    assert before['cstr']['4'] == '星'
    assert_ages(session.state)
    session.close()
