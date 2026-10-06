"""S67同階段補完；expected取自ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING。

全新25歲人工角色，僅驗證欄位切換、顯示與清理；不建立敘事或經歷生成。
"""
import pytest

from test_body_editor import ctx, data, finish
from test_body_editor_options import buttons, get, put
from eragvt.game.body_editor import size_setting
from tools.sim_adult import assert_ages


PAIRS = [(70, '濡れやすい', '濡れにくい'), (71, 'Ｃ敏感', 'Ｃ鈍感'),
         (72, 'Ｖ敏感', 'Ｖ鈍感'), (73, 'Ａ敏感', 'Ａ鈍感'), (74, 'Ｂ敏感', 'Ｂ鈍感')]


@pytest.mark.parametrize('choice,positive,negative', PAIRS)
@pytest.mark.parametrize('before,expected', [((0, 0), (1, 0)), ((2, 0), (0, 1)),
    ((0, 3), (0, 0)), ((2, 3), (0, 1)), ((-1, -1), (1, 0))])
def test_trait_pair_cycle(ctx, choice, positive, negative, before, expected):
    """@SIZE_SETTING:1904–1978；正值判斷有優先序，非布林XOR。"""
    put(ctx, **{positive: before[0], negative: before[1], 'オトコ': 0})
    g = size_setting(ctx, 1); next(g); g.send(choice)
    assert get(ctx, positive, negative) == expected
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('choice,field', [(70, '変身時濡れやすさ変動'), (72, '変身時Ｖ感覚変動')])
@pytest.mark.parametrize('before,expected', [(0, 1), (1, -1), (-1, 0), (3, -1), (-3, 0)])
def test_transformed_trait_cycle(ctx, choice, field, before, expected):
    """@SIZE_SETTING:1916–1923、1948–1955；男性且TS>0才改變身差值。"""
    put(ctx, **{'オトコ': 1, '変身時ＴＳ': 1, field: before})
    g = size_setting(ctx, 1); next(g); g.send(choice)
    assert get(ctx, field) == (expected,)
    finish(g); assert get(ctx, field) == (expected,)
    assert_ages(ctx.state)


@pytest.mark.parametrize('choice', [70, 72])
def test_male_without_ts_hidden_input_unchanged(ctx, choice):
    """@SIZE_SETTING:482–512、573–604及1905／1916、1937／1948。"""
    put(ctx, オトコ=1, 変身時ＴＳ=0)
    g = size_setting(ctx, 1); next(g)
    before = dict(ctx.state.charas[1].talent.items())
    assert choice not in buttons(ctx)
    g.send(choice)
    assert dict(ctx.state.charas[1].talent.items()) == before
    finish(g)


@pytest.mark.parametrize('choice,field', [(75, 'パイパン'), (80, '初心'),
    (82, '母乳体質'), (83, '苗床化'), (84, '寄生')])
@pytest.mark.parametrize('before,expected', [(0, 1), (1, 0), (-1, 0), (3, 0)])
def test_switches_accept_fixed_hidden_input(ctx, choice, field, before, expected):
    """@SIZE_SETTING:1979–1984、1994–1999、2030–2048，NO／GLOBAL不限制寫入。"""
    c = ctx.state.charas[1]; c.no = 5
    put(ctx, **{field: before, '固有キャラ': 1, '共生': 7, 'オトコ': 1, '変身時ＴＳ': 0})
    g = size_setting(ctx, 1); next(g)
    if choice in (82, 83, 84): assert choice not in buttons(ctx)
    g.send(choice)
    assert get(ctx, field) == (expected,)
    assert get(ctx, '共生') == (0 if choice == 84 and before != 0 else 7,)
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('before,expected', [(0, 1), (1, 2), (2, 0), (3, 0), (-1, 0)])
def test_maturity_flag_cycle(ctx, before, expected):
    """@SIZE_SETTING:1985–1992只循環欄位，沒有年齡條件或經歷生成呼叫。"""
    put(ctx, 未熟=before)
    c = ctx.state.charas[1]; exp = dict(c.exp.items())
    g = size_setting(ctx, 1); next(g); g.send(76)
    assert get(ctx, '未熟') == (expected,)
    assert dict(c.exp.items()) == exp
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('male,ability,ts,normal,other,expected', [
    (0, 1, 0, 0, 0, (3, 3)), (0, 1, 0, 3, 3, (0, 3)),
    (0, 1, 0, 0, 3, (3, 0)), (0, 1, 0, 3, 0, (0, 0)),
    (0, 0, 0, 0, 0, (3, 0)), (0, 2, 0, 0, 0, (3, 0)),
    (0, 1, 1, 0, 0, (3, 0)), (1, 1, 1, 0, 0, (0, 3)),
    (1, 1, 1, 0, 3, (0, 0)), (1, 1, 1, 3, 0, (0, 3)),
    (1, 0, 1, 0, 0, (0, 0)), (1, 1, 0, 0, 0, (0, 0)),
    (0, 0, 0, 0, 3, (3, 0)), (0, 1, 0, 1, 2, (0, 0)),
])
def test_two_form_flag_source_branches(ctx, male, ability, ts, normal, other, expected):
    """@SIZE_SETTING:2000–2028，精確比較0／3及能力1，不用泛化的非零判斷。"""
    put(ctx, **{'オトコ': male, '変身能力': ability, '変身時ＴＳ': ts,
               'ふたなり': normal, '変身時ふたなり': other})
    g = size_setting(ctx, 1); next(g); g.send(81)
    assert get(ctx, 'ふたなり', '変身時ふたなり') == expected
    finish(g); assert_ages(ctx.state)


@pytest.mark.parametrize('unique,locked,expected', [(0, 0, 0), (1, 0, 9), (0, 1, 9), (1, 1, 9)])
def test_two_form_flag_cleanup(ctx, unique, locked, expected):
    """@SIZE_SETTING:2020–2026只有關閉分支、兩鎖均0時清經驗，沒有生成經驗。"""
    put(ctx, **{'オトコ': 0, '変身時ＴＳ': 0, 'ふたなり': 3, '変身時ふたなり': 0,
               '固有キャラ': unique, '初期経験設定不可': locked})
    c = ctx.state.charas[1]; slot = ctx.data.index_of('EXP', '射精経験'); c.exp[slot] = 9
    g = size_setting(ctx, 1); next(g); g.send(81)
    assert c.exp[slot] == expected
    finish(g)


@pytest.mark.parametrize('male,ts,unlocked,visible', [
    (0, 0, False, {70,71,72,73,74,75,76,80}),
    (0, 0, True, {70,71,72,73,74,75,76,80,81,82,83,84}),
    (1, 0, True, {71,73,74,75,76,80,83,84}),
    (1, 1, True, {70,71,72,73,74,75,76,80,81,82,83,84}),
])
def test_trait_buttons_and_numeric_interception(ctx, male, ts, unlocked, visible):
    """@SIZE_SETTING:482–724皆PRINTFORM；數字子頁仍顯按鈕，由1477–1503先攔輸入。"""
    for k in (244, 245, 253, 255): ctx.globals.mem.global_[k] = int(unlocked)
    put(ctx, オトコ=male, 変身時ＴＳ=ts)
    g = size_setting(ctx, 1); next(g)
    assert buttons(ctx) & set(range(70,85)) == visible
    g.send(30); ctx.out.clearline(len(ctx.out.lines)); g.send(1100)
    assert buttons(ctx) & set(range(70,85)) == visible
    before = dict(ctx.state.charas[1].talent.items())
    for choice in visible: g.send(choice)
    assert dict(ctx.state.charas[1].talent.items()) == before
    g.send(-1); g.send(30); finish(g); assert_ages(ctx.state)


def test_cancel_confirm_reentry_preserves_traits_and_other_character(ctx):
    """@SIZE_SETTING:1712–1715非數字子頁取消不回滾，1745–1747清不適用形態差值。"""
    put(ctx, **{'オトコ': 0, 'パイパン': 0, '初心': 0, '未熟': 0,
               '変身時濡れやすさ変動': 1, '変身時Ｖ感覚変動': -1})
    other = ctx.state.charas[0].to_json(); rng = ctx.state.rng.snapshot()
    ctx.state.target = 0; ctx.state.result[10] = 417
    g = size_setting(ctx, 1); next(g); g.send(5)
    for choice in (75, 76, 80): g.send(choice)
    g.send(5); finish(g)
    assert get(ctx, 'パイパン', '未熟', '初心', '変身時濡れやすさ変動', '変身時Ｖ感覚変動') == (1,1,1,0,0)
    g = size_setting(ctx, 1); next(g); finish(g)
    assert get(ctx, 'パイパン', '未熟', '初心') == (1,1,1)
    assert ctx.state.charas[0].to_json() == other and ctx.state.rng.snapshot() == rng
    assert ctx.state.target == 0 and ctx.state.result[0] == 0 and ctx.state.result[10] == 417
    assert_ages(ctx.state)
