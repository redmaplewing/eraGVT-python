"""S69：ADD_CHILD尾段函式邊界；全新25歲人工前態，非完整出生流程。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import child, party, relation
from eragvt.game.action import Ctx
from eragvt.game.input_request import TextInputRequest
from eragvt.state import FixedRng, GameState
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, FixedRng([]))
    st.charas = st.charas[:1]
    for i, name in enumerate(('人工成年親', '人工成年隊員'), 1):
        c = st.add_chara(data, 0)
        c.name = c.callname = name
        c.talent.clear()
        c.cflag[240] = i
        c.cflag[33], c.cflag[34] = 314159, 333333333333333
        c.base[47] = c.maxbase[47] = 900  # 非舊欄位配置，CONVERT_AGE不搬移。
        c.talent[data.index_of('TALENT', '変身能力')] = 1
        for k in (30, 31, 32, 33, 34, 35, 36, 37):
            c.cstr[k] = '8//8//8'
    st.charas[1].cflag[224] = 9
    st.charas[2].cflag[7] = 1
    st.charas[2].cflag[0] = 11
    st.target = 2  # ADD_CHILD:309已令TARGET指向新角色；尾段不還原為親。
    st.result[8], st.results[8] = 678, '尾格'
    assert_ages(st)
    return Ctx(st, data, TextOutput(), NullNarrationService())


def finish(gen):
    with pytest.raises(StopIteration):
        gen.send(99)


@pytest.mark.parametrize('childcare', [False, True])
def test_wait_then_original_return_and_recovery_order(ctx, monkeypatch, childcare):
    """ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1075–1107。

    :1083–1092必須先恢復親→清224→恢復隊員→全關係；一般分支不執行。
    """
    st = ctx.state
    parent, c = st.charas[1:]
    parent.cflag[0] = 11 if childcare else 0
    c.cstr[40], c.cstr[41], c.cstr[42] = '', '', '沉穩'
    calls = []
    recover, check = party.recover_to_party, relation.check_all_relation

    def recorded_recover(inner, who):
        calls.append(('recover', who, parent.cflag[224], st.target))
        recover(inner, who)

    def recorded_check(inner):
        calls.append(('relation', parent.cflag[0], c.cflag[0], parent.cflag[224]))
        check(inner)

    monkeypatch.setattr(child, 'recover_to_party', recorded_recover)
    monkeypatch.setattr(relation, 'check_all_relation', recorded_check)
    gen = child.add_child_finish(ctx, 1)
    assert next(gen) is None
    assert calls == [] and parent.cflag[224] == 9 and c.cflag[0] == 11
    assert '[99]決定して戻る' in '\n'.join(line.text for line in ctx.out.lines)
    assert st.target == 2
    # CHARA_SIZE_UI.ERB@SIZE_SETTING:341–344：TOP_UNDER影響值190；
    # :1378–1380性格無指定時RESULTS:0為「未設定」。
    assert st.result[1] == 190 and st.results[0] == '未設定'
    finish(gen)
    assert calls == ([('recover', 1, 9, 2), ('recover', 2, 0, 2), ('relation', 0, 0, 0)] if childcare else [])
    assert (parent.cflag[224], c.cflag[0]) == ((0, 0) if childcare else (9, 11))
    assert (parent.cflag[999], c.cflag[999]) == ((1, 1) if childcare else (0, 0))
    assert (parent.relation[2], c.relation[1]) == ((1 << 20, 1 << 20) if childcare else (0, 0))
    assert [c.cstr[k] for k in (40, 41, 42)] == ['沉穩', '', '']
    # SIZE_SETTING:2141恢復進入時TARGET；ADD_CHILD:1107 RETURN不清其他格。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023。
    assert st.target == 2 and st.result[0] == 0 and st.result[1] == 190
    assert st.result[8] == 678 and st.results[8] == '尾格' and st.results[0] == '未設定'
    assert st.rng.snapshot() == []
    assert_ages(st)


@pytest.mark.parametrize('choice,slot,value', [(601, 30, '255//8//8'), (901, 36, '255//200//180')])
def test_general_color_edits_and_confirmation(ctx, choice, slot, value):
    # ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1769–1790。
    gen = child.add_child_finish(ctx, 1)
    next(gen)
    gen.send(choice)
    assert ctx.state.charas[2].cstr[slot] == value
    finish(gen)
    assert ctx.state.charas[1].cstr[slot] == '8//8//8'
    assert_ages(ctx.state)


@pytest.mark.parametrize('starting,expected', [(0, 1), (1, 2), (6, 0)])
def test_general_appearance_cycle(ctx, starting, expected):
    # ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1653–1670。
    slot = ctx.data.index_of('TALENT', '外見')
    ctx.state.charas[2].talent[slot] = starting
    gen = child.add_child_finish(ctx, 1)
    next(gen)
    gen.send(4)
    finish(gen)
    assert ctx.state.charas[2].talent[slot] == expected
    assert ctx.state.charas[1].talent[slot] == 0
    assert_ages(ctx.state)


@pytest.mark.parametrize('cancel', [True, False])
def test_personality_text_waits_and_returns_to_body(ctx, cancel):
    # ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SET_PERSONALITY:2238–2277。
    # 20個候選先抽；空字返回候選頁，未提交人格，不另抽候選。
    candidate = next(k - 30500 for k, v in ctx.data.str_defaults.items() if 30500 <= k < 31000 and v)
    ctx.state.rng = FixedRng([candidate] * 20)
    gen = child.add_child_finish(ctx, 1)
    next(gen)
    gen.send(60)
    assert isinstance(gen.send(20), TextInputRequest)
    if cancel:
        assert gen.send('') is None
        assert ctx.state.charas[2].cstr[40] == ''
        assert isinstance(gen.send(20), TextInputRequest)
    assert gen.send('沉穩') is None
    assert ctx.state.charas[2].cstr[40] == '沉穩'
    finish(gen)
    assert ctx.state.rng.snapshot() == []
    assert_ages(ctx.state)


@pytest.mark.parametrize('curve', [0, 333333333333333])
def test_generate_bodyline_only_when_unset_with_original_rng_order(ctx, curve):
    # ADD_CHILD:1076–1078；CHARA_SIZE.ERB@GENERATE_BODYLINE:475–540。
    # 每個累積下界抽4次，15位皆4；先抽亂數值，再抽60次RAND726。
    bounds = [0, 83, 163, 238, 321, 434, 542, 592, 632, 662, 682, 692, 702, 712, 720]
    rolls = [314159] + [x for x in bounds for _ in range(4)] if curve == 0 else []
    class RecordingRng(FixedRng):
        def __init__(self, values):
            super().__init__(values)
            self.bounds = []

        def rand(self, n):
            self.bounds.append(n)
            return super().rand(n)

    ctx.state.rng = RecordingRng(rolls)
    c = ctx.state.charas[2]
    c.cflag[34] = curve
    gen = child.add_child_finish(ctx, 1)
    next(gen)
    assert c.cflag[34] == (444444444444444 if curve == 0 else curve)
    assert c.cflag[33] == 314159
    assert ctx.state.rng.bounds == ([535627332240] + [726] * 60 if curve == 0 else [])
    finish(gen)
    assert ctx.state.rng.snapshot() == []
    assert_ages(ctx.state)


@pytest.mark.parametrize('parent_state,expected', [
    (0, (1, 0, '', 0, -1, 0, 0)),
    (11, (0, 7, '保留欄位', 0, 0, 1, 1)),
])
def test_existing_alternate_cleanup_and_childcare_priority(ctx, parent_state, expected):
    # ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1083–1106。
    # 全新25歲人工資料，只驗原有IF／ELSEIF優先序與數值清理，不檢查敘事。
    parent, c = ctx.state.charas[1:]
    parent.cflag[0] = parent_state
    parent.cflag[22] = 7
    parent.cstr[11] = '保留欄位'
    gen = child.add_child_finish(ctx, 1)
    next(gen)
    assert parent.cflag[22] == 7 and parent.cflag[224] == 9
    finish(gen)
    assert (c.cflag[0], parent.cflag[22], parent.cstr[11], parent.cflag[224],
            c.cflag[6], parent.cflag[999], c.cflag[999]) == expected
    assert (parent.relation[2], c.relation[1]) == (1 << 20, 1 << 20)
    assert ctx.state.target == 2 and ctx.state.result[0] == 0
    assert ctx.state.result[8] == 678 and ctx.state.results[8] == '尾格'
    assert ctx.state.rng.snapshot() == []
    assert_ages(ctx.state)


def test_web_tail_text_confirmation_and_replayed_token(ctx, tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app

    app = create_app(ctx.data, tmp_path, narration=NullNarrationService())
    session = app.state.session
    session.state = ctx.state
    candidate = next(k - 30500 for k, v in ctx.data.str_defaults.items() if 30500 <= k < 31000 and v)
    ctx.state.rng = FixedRng([candidate] * 20)
    done = []
    session._run_gen(child.add_child_finish(session._ctx(), 1), lambda: done.append(True))
    client = TestClient(app)
    assert '決定して戻る' in client.get('/').text
    screen = client.post('/api/input', json={'value': 601}).json()
    client.post('/api/input', json={'value': 60})
    screen = client.post('/api/input', json={'value': 20}).json()
    assert screen['input_kind'] == 'text'
    screen = client.post('/api/input', json={'value': '沉穩'}).json()
    assert screen['input_kind'] == 'number'
    token = screen['input_token']
    assert not done and ctx.state.charas[2].cstr[30] == '255//8//8'
    client.post('/api/input', json={'value': 99, 'input_token': token})
    assert done == [True]
    client.post('/api/input', json={'value': 99, 'input_token': token})
    assert done == [True] and ctx.state.target == 2
    assert ctx.state.charas[2].cstr[40] == '沉穩'
    assert_ages(ctx.state)
    session.close()
