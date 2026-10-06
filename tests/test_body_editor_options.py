"""S67 一般操作，expected 逐條取自 CHARA_SIZE_UI.ERB@SIZE_SETTING。

所有角色由 fresh-adult-25-v1 建立；沒有修改正式資料的年齡規則。
"""
import pytest

from test_body_editor import ctx, data, finish
from eragvt.game.body_editor import size_setting
from eragvt.state.savefile import GlobalStore
from eragvt.state.constants import GameOption
from tools.sim_adult import assert_ages


def put(ctx, **values):
    c = ctx.state.charas[1]
    for name, value in values.items():
        # Python識別字NFKC正規化；CSV字串key保留全形。
        name = name.replace('TS', 'ＴＳ')
        c.talent[ctx.data.index_of('TALENT', name)] = value


def get(ctx, *names):
    c = ctx.state.charas[1]
    return tuple(c.talent[ctx.data.index_of('TALENT', name)] for name in names)


def buttons(ctx):
    return {v for line in ctx.out.lines for _, v in line.buttons}


@pytest.mark.parametrize('male,girly,ts,expected', [
    (0, 0, 0, (1, 0, 0, 0)), (0, 0, 1, (1, 0, 1, 0)),
    (1, 0, 0, (1, 1, 0, 1)), (1, 0, 1, (1, 1, 1, 0)),
    (1, 1, 0, (0, 0, 0, 0)), (1, 1, 1, (0, 0, 1, 0)),
])
def test_normal_sex_cycle(ctx, male, girly, ts, expected):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1560–1604。"""
    put(ctx, オトコ=male, 男の娘=girly, 変身時ＴＳ=ts)
    g = size_setting(ctx, 1); next(g); g.send(2)
    assert get(ctx, 'オトコ', '男の娘', '変身時ＴＳ', '変身時男の娘') == expected
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('male,ts,girly,expected', [
    (0, 0, 0, (1, 0)), (0, 1, 0, (1, 1)), (0, 1, 1, (0, 0)),
    (1, 0, 0, (0, 1)), (1, 0, 1, (1, 0)), (1, 1, 0, (0, 0)),
])
def test_transformed_sex_cycle_even_hidden(ctx, male, ts, girly, expected):
    """@SIZE_SETTING:1533、1545–1558、1598–1604，手輸12不查變身能力／年齡哨兵。"""
    put(ctx, オトコ=male, 変身時ＴＳ=ts, 変身時男の娘=girly, 変身能力=0)
    g = size_setting(ctx, 1); next(g)
    assert 12 not in buttons(ctx)
    g.send(12)
    assert get(ctx, '変身時ＴＳ', '変身時男の娘') == expected
    finish(g); assert_ages(ctx.state)


def test_sex_resets_barriers_and_preserves_others(ctx):
    """@SIZE_SETTING:1534–1544 每個非零結界退50，190..193與避妊結界分開。"""
    c = ctx.state.charas[1]
    for k, v in zip(range(190, 194), (1, 2, 0, -1)): c.talent[k] = v
    put(ctx, 避妊結界=3)
    point = ctx.data.index_of('JUEL', '修練P'); c.juel[point] = 7
    other = ctx.state.charas[0].to_json(); rng = ctx.state.rng.snapshot()
    ctx.state.target = 0
    g = size_setting(ctx, 1); next(g); g.send(2)
    assert all(c.talent[k] == 0 for k in range(190, 194))
    assert get(ctx, '避妊結界') == (0,) and c.juel[point] == 207
    finish(g)
    assert ctx.state.target == 0 and ctx.state.charas[0].to_json() == other
    assert ctx.state.rng.snapshot() == rng


def test_sex_copies_transformed_shape_in_source_order(ctx):
    """@SIZE_SETTING:1564–1582；依變身形態複製後才清性別，原欄位不是全量重置。"""
    put(ctx, オトコ=1, 男の娘=1, 変身時ＴＳ=1, 変身時胸サイズ変動=3,
        変身時外見=5, 貧乳=0, 巨乳=0, 外見=0)
    g = size_setting(ctx, 1); next(g); g.send(2)
    assert get(ctx, '巨乳', '貧乳', '外見', '変身時外見', '変身時胸サイズ変動') == (3, 0, 5, 0, 0)
    finish(g)


@pytest.mark.parametrize('large,small,expected', [
    (0, 0, (1, 0)), (1, 0, (2, 0)), (2, 0, (3, 0)),
    (3, 0, (4, 0)), (4, 0, (5, 0)), (5, 0, (0, 2)),
    (0, 2, (0, 1)), (0, 1, (0, 0)),
])
def test_normal_shape_cycle(ctx, large, small, expected):
    """@SIZE_SETTING:1632–1649。"""
    put(ctx, 巨乳=large, 貧乳=small, オトコ=0)
    g = size_setting(ctx, 1); next(g); g.send(3)
    assert get(ctx, '巨乳', '貧乳') == expected
    finish(g)


@pytest.mark.parametrize('large,small,delta,expected', [
    (0, 0, -2, -1), (0, 0, -1, 0), (0, 0, 0, 1),
    (0, 0, 1, 2), (0, 0, 4, 5), (0, 0, 5, -2),
    (5, 0, 0, -2),  # :1619 寫絕對-2；原形態+5仍存在，不能「修」成-7。
    (0, 2, 2, 3),
])
def test_transformed_shape_cycle(ctx, large, small, delta, expected):
    """@SIZE_SETTING:1608–1629，迴圈中每一步重查CHARATALENT。"""
    put(ctx, 巨乳=large, 貧乳=small, 変身時胸サイズ変動=delta, オトコ=0)
    g = size_setting(ctx, 1); next(g); g.send(13)
    assert get(ctx, '変身時胸サイズ変動') == (expected,)
    finish(g)


@pytest.mark.parametrize('no,male,choice', [(5, 0, 3), (5, 0, 13), (0, 1, 3), (0, 1, 13)])
def test_shape_restrictions(ctx, no, male, choice):
    """@SIZE_SETTING:1608，固定角色與該形態男性不變更。"""
    c = ctx.state.charas[1]; c.no = no
    put(ctx, オトコ=male, 変身時ＴＳ=0, 巨乳=0, 貧乳=0, 変身時胸サイズ変動=0)
    g = size_setting(ctx, 1); next(g); g.send(choice)
    assert get(ctx, '巨乳', '貧乳', '変身時胸サイズ変動') == (0, 0, 0)
    finish(g)


def test_fixed_character_sex_falls_through_to_input_mode(ctx):
    """@SIZE_SETTING:1533、1717–1718；NO!=0手輸2進實年齡模式，不能改成拒絕。"""
    c = ctx.state.charas[1]; c.no = 5
    g = size_setting(ctx, 1); next(g)
    assert 2 not in buttons(ctx)
    before = get(ctx, 'オトコ', '男の娘')
    g.send(2); g.send(-1); g.send(100000); g.send(25)
    assert get(ctx, 'オトコ', '男の娘') == before
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('starting,expected', [(0, 1), (1, 2), (2, 3), (3, 0), (9, 1)])
def test_accessory_cycle(ctx, starting, expected):
    """@SIZE_SETTING:1891–1902。"""
    put(ctx, アクセサリ=starting, 固有キャラ=0)
    g = size_setting(ctx, 1); next(g); g.send(46)
    assert get(ctx, 'アクセサリ') == (expected,)
    finish(g)


@pytest.mark.parametrize('male,girly,unique,visible,expected', [
    (0, 0, 0, True, 1), (1, 1, 0, True, 1), (1, -1, 0, True, 1),
    (1, 0, 0, False, 0), (0, 0, 1, True, 0),
])
def test_accessory_visibility_and_unique_lock(ctx, male, girly, unique, visible, expected):
    """@SIZE_SETTING:810–828 顯示不查固有，但:1892寫入有檢查；NO!=0不等於固有。"""
    ctx.state.charas[1].no = 5
    put(ctx, オトコ=male, 男の娘=girly, 固有キャラ=unique, アクセサリ=0)
    g = size_setting(ctx, 1); next(g)
    assert (46 in buttons(ctx)) == visible
    g.send(46); assert get(ctx, 'アクセサリ') == (expected,)
    finish(g)


@pytest.mark.parametrize('mode', [5, 1100])
def test_subpage_direct_changes_and_cancel(ctx, mode):
    """@SIZE_SETTING:1464優先攔數字；非數字子頁:1712取消不回滾。"""
    put(ctx, アクセサリ=0)
    g = size_setting(ctx, 1); next(g); g.send(mode); g.send(46)
    assert get(ctx, 'アクセサリ') == ((0,) if mode == 1100 else (1,))
    if mode == 1100: g.send(-1); g.send(30)
    else: g.send(mode)
    finish(g)


@pytest.mark.parametrize('unlocks,solo,sequence', [
    ((), False, [0]), ((258,), False, [1, 0]), ((262,), False, [3, 0]),
    ((278,), False, [4, 0]), ((212,), False, [9, 0]),
    ((258, 262, 278, 212), False, [1, 3, 4, 9, 0]),
    ((258, 262, 278, 212), True, [1, 4, 9, 0]),
])
def test_initial_state_cycle(ctx, unlocks, solo, sequence):
    """@SIZE_SETTING:2053–2102與CHARA_MAKE_MAIN:150–198相同，保留原副作用。"""
    ctx.globals = GlobalStore()
    for k in unlocks: ctx.globals.mem.global_[k] = 1
    ctx.state.flag[0] = int(solo) << GameOption.SOLO
    c = ctx.state.charas[1]; exp = ctx.data.index_of('EXP', '陥落経験')
    c.exp[exp] = 7; c.cflag[41] = 200; c.cflag[71] = 11
    g = size_setting(ctx, 1); next(g)
    assert (86 in buttons(ctx)) == bool(unlocks)
    for state in sequence:
        g.send(86)
        assert c.cflag[0] == state and c.exp[exp] == 7 + (state == 3)
    assert c.cflag[41] == (401 if 262 in unlocks and not solo else 200)
    assert c.cflag[71] == (30 if 278 in unlocks else 11)
    finish(g)


def test_initial_state_hidden_input_and_free_mode(ctx):
    """@SIZE_SETTING:725–748只管顯示，2053手輸仍有效；離開3仍直接減一。"""
    ctx.globals = GlobalStore()
    c = ctx.state.charas[1]; c.cflag[0] = 3
    exp = ctx.data.index_of('EXP', '陥落経験'); c.exp[exp] = 0
    g = size_setting(ctx, 1); next(g)
    assert 86 not in buttons(ctx)
    g.send(86)
    assert c.cflag[0] == 0 and c.exp[exp] == -1
    ctx.state.flag[0] = 1 << GameOption.NO_ACHIEVEMENT_END
    g.send(86); assert c.cflag[0] == 1
    finish(g)


def test_unused_85_noop_confirm_and_reentry(ctx):
    """@SIZE_SETTING:2049–2051明示未使用；一般操作確認寫回且重入保留。"""
    put(ctx, アクセサリ=0)
    g = size_setting(ctx, 1); next(g); g.send(46); g.send(85)
    finish(g)
    assert get(ctx, 'アクセサリ') == (1,)
    g = size_setting(ctx, 1); next(g); finish(g)
    assert get(ctx, 'アクセサリ') == (1,)
    assert_ages(ctx.state)


def test_two_forms_toggle_reentry_and_result_tail(ctx):
    """@SIZE_SETTING:1690–1710、2110–2142；重設另一形態後仍依確認規則寫回。"""
    c = ctx.state.charas[1]; c.cstr[14] = '人工變身髮型'
    put(ctx, 巨乳=0, 貧乳=0, オトコ=0, 変身時ＴＳ=0, 変身時胸サイズ変動=0)
    ctx.state.target = 0
    ctx.state.result[10] = 919; ctx.state.results[2] = '保留'
    g = size_setting(ctx, 1); next(g)
    assert c.maxbase[41] == 25
    g.send(3); g.send(13)
    assert get(ctx, '巨乳', '変身時胸サイズ変動') == (1, 1)
    g.send(20)
    assert c.maxbase[41] == -1 and get(ctx, '変身時胸サイズ変動') == (0,)
    g.send(20); assert c.maxbase[41] == 25
    finish(g)
    assert ctx.state.result[0] == 0 and ctx.state.result[10] == 919
    assert ctx.state.results[2] == '保留' and ctx.state.target == 0
    assert c.base[43] == c.maxbase[43] and c.base[45] == c.maxbase[45]
    g = size_setting(ctx, 1); next(g); finish(g)
    assert get(ctx, '巨乳') == (1,)
    assert_ages(ctx.state)


def test_numeric_mode_buttons_follow_original_print_commands(ctx):
    """@SIZE_SETTING:266／316為PRINTPLAIN，823／747仍PRINTFORM；不另行猜按鈕權限。"""
    ctx.globals.mem.global_[258] = 1
    g = size_setting(ctx, 1); next(g)
    ctx.out.clearline(len(ctx.out.lines)); g.send(50)
    assert 2 not in buttons(ctx) and 3 not in buttons(ctx)
    assert {46, 86} <= buttons(ctx)
    g.send(25); finish(g)
    assert_ages(ctx.state)


@pytest.mark.parametrize('entry', ['editor', 'status'])
def test_real_web_entry_confirm_reentry_and_shop(data, tmp_path, entry):
    """FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:260；狀態PAGE5@CMD:73–79。"""
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    app = create_app(data, tmp_path, rng_factory=lambda: GameRng(67), narration=NullNarrationService())
    session = app.state.session
    client = TestClient(app)
    def send(value):
        response = client.post('/api/input', json={'value': value})
        assert response.status_code == 200
        assert_ages(session.state)
        return response.json()
    for value in ((0, 1, 1) if entry == 'editor' else (0, 1, 1000, 1,0)):
        send(value)
    c = session.state.charas[1]
    for name, value in (('変身能力', 1), ('オトコ', 0), ('変身時ＴＳ', 0), ('アクセサリ', 0), ('固有キャラ', 0)):
        c.talent[data.index_of('TALENT', name)] = value
    c.cstr[14] = '人工變身髮型'
    others = [x.to_json() for i, x in enumerate(session.state.charas) if i != 1]
    if entry == 'status':
        c.cflag[34] = 0
        for value in (110, 5000, 20): send(value)
    else: send(6)
    # @SIZE_SETTING:1904–2048補完操作從真Web邊界確認，再循環回原前態。
    fields = ('濡れやすい', '濡れにくい', 'Ｃ敏感', 'Ｃ鈍感', 'Ｖ敏感', 'Ｖ鈍感',
              'Ａ敏感', 'Ａ鈍感', 'Ｂ敏感', 'Ｂ鈍感', 'パイパン', '未熟', '初心',
              'ふたなり', '変身時ふたなり', '母乳体質', '苗床化', '寄生', '共生')
    for name in fields: c.talent[data.index_of('TALENT', name)] = 0
    for value in (70, 71, 72, 73, 74, 75, 76, 80, 81, 82, 83, 84): send(value)
    assert c.talent[data.index_of('TALENT', '未熟')] == 1
    assert c.talent[data.index_of('TALENT', '変身時ふたなり')] == 3
    for value, count in ((70,2),(71,2),(72,2),(73,2),(74,2),(75,1),(76,2),
                         (80,1),(81,3),(82,1),(83,1),(84,1)):
        for _ in range(count): send(value)
    assert all(c.talent[data.index_of('TALENT', name)] == 0 for name in fields)
    for value in (2, 2, 2, 3, 13, 46, 5, 46, 5, 20, 20, 85, 99): send(value)
    assert c.talent[data.index_of('TALENT', 'アクセサリ')] == 2
    assert [x.to_json() for i, x in enumerate(session.state.charas) if i != 1] == others
    if entry == 'editor':
        for value in (6, 99, 99, 1000, 1,0): send(value)
    else:
        for value in (20, 99, 999): send(value)
    assert session.phase.name == 'SHOP'
