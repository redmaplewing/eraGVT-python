"""S70：TRANS_SEX 原文推導；全新25歲人工兩形態，不經角色年齡生成。"""
import pytest
from pathlib import Path
import re

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game import trans_sex as ts
from eragvt.game.battle.func import transform
from eragvt.state import GameState, FixedRng
from eragvt.text import NullNarrationService, TextOutput
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, FixedRng([]))
    st.charas = st.charas[:1]
    for name in ('人工成年甲', '人工成年乙'):
        c = st.add_chara(data, 0)
        c.name = c.callname = name
        c.talent.clear()
        c.cflag.clear()
        for k in (13, 14, 30, 31, 32, 33, 34, 35, 36, 37):
            c.cstr[k] = '黒' if k >= 30 else '短髮'
    st.target = 2
    st.result[8], st.results[0], st.results[8] = 765, '保留字串', '尾格'
    assert_ages(st)
    return Ctx(st, data, TextOutput(), NullNarrationService())


def put(ctx, **values):
    for name, value in values.items():
        ctx.state.charas[1].talent[ctx.data.index_of('TALENT', name.replace('TS','ＴＳ'))] = value


def get(ctx, name):
    return ctx.state.charas[1].talent[ctx.data.index_of('TALENT', name)]


def drive(gen, answers=()):
    answers = iter(answers)
    try:
        next(gen)
        while True:
            answer = next(answers, None)
            assert answer is not None, '缺少原作INPUT的回答'
            gen.send(answer)
    except StopIteration as exc:
        assert next(answers, None) is None, '產品提前結束，尚有原作INPUT回答'
        return exc.value


@pytest.mark.parametrize('kind,transformed,change', [('mtof', 0, 1), ('mtof', 1, 1), ('ftom', 0, 10), ('ftom', 1, 10)])
def test_ts_conversion_restore_and_appearance(ctx, kind, transformed, change):
    # ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF:4–173、@TS_FtoM:179–346。
    put(ctx, 変身能力=1, 変身時ＴＳ=1, オトコ=int(kind == 'mtof'), 外見=2, 変身時外見=4,
        変身時体格変動=1, 変身時胸サイズ変動=2)
    c = ctx.state.charas[1]
    c.cstr[14] = '長髮'
    c.cstr[31], c.cstr[34], c.cstr[35], c.cstr[37] = '赤', '青', '緑', '褐色'
    if transformed:
        transform(ctx, 1, 1)
    assert drive(getattr(ts, 'ts_' + kind)(ctx, 1), [9, 0, 1, 0, 1]) == 1
    assert (ctx.state.target, c.cflag[1], get(ctx, '性別変化'), get(ctx, '変身時ＴＳ')) == (2, transformed, change, -1)
    assert get(ctx, 'オトコ') == 0
    assert c.cstr[13] == '長髮'
    assert (c.cstr[30], c.cstr[31]) == (('黒', '赤') if kind == 'mtof' else ('黒', '黒'))
    assert (c.cstr[32], c.cstr[34]) == (('青', '青') if kind == 'mtof' else ('黒', '青'))
    assert (c.cstr[36], c.cstr[37]) == (('黒', '褐色') if kind == 'mtof' else ('黒', '黒'))
    assert ctx.state.result[0] == 1 and ctx.state.result[8] == 765
    assert ctx.state.results[0] == '保留字串' and ctx.state.results[8] == '尾格'
    assert_ages(ctx.state)


@pytest.mark.parametrize('bust,expected', [(1,(2,0)),(2,(1,0)),(3,(0,0)),(4,(0,1)),(5,(0,2)),(6,(0,3)),(7,(0,4)),(8,(0,5))])
def test_normal_bust_choices_and_invalid_retry(ctx, bust, expected):
    # @TS_NORMAL:399–458：無TS時0非法，1–8明確設定兩個素質。
    put(ctx, オトコ=1)
    assert drive(ts.ts_normal(ctx, 1), [0, 9, bust, 1, 7]) == 1
    assert (get(ctx,'貧乳'),get(ctx,'巨乳')) == expected
    assert (get(ctx,'性別変化'),get(ctx,'オトコ'),get(ctx,'男の娘')) == (1,0,0)
    assert ctx.state.target == 2 and ctx.state.result[0] == 1
    assert_ages(ctx.state)


@pytest.mark.parametrize('body,expected', [(1,(0,1)),(2,(1,0)),(3,(0,0)),(4,(0,1))])
def test_normal_body_keep_and_choices(ctx, body, expected):
    put(ctx, オトコ=1, 長身=1)
    drive(ts.ts_normal(ctx, 1), [3, 9, body, 0, 4])
    assert (get(ctx,'小柄'),get(ctx,'長身')) == expected
    assert get(ctx,'外見') == 4


def test_normal_two_forms_keep_and_original_unusual_delta(ctx):
    # @TS_NORMAL:566–581及627–632按原式相加，不修成差值。
    put(ctx, オトコ=1, 変身能力=1, 長身=1)
    drive(ts.ts_normal(ctx, 1), [4, 1, 1, 3, 4, 0])
    assert (get(ctx,'巨乳'),get(ctx,'変身時胸サイズ変動')) == (1,-1)
    assert (get(ctx,'長身'),get(ctx,'変身時体格変動')) == (1,1)
    assert (get(ctx,'外見'),get(ctx,'変身時外見'),get(ctx,'性別変化')) == (4,4,11)


def test_normal_menu_preserves_source_column_spaces(ctx):
    # ERB/ヒロイン関連/TRANS_SEX.ERB@TS_NORMAL:404–405、494–496、548–549、
    # 595–597、637–643、677–683；變身後[6]原文特別沒有尾端空白。
    source = Path(__file__).resolve().parents[1] / 'source/earGVP/ERB/ヒロイン関連/TRANS_SEX.ERB'
    lines = source.read_text(encoding='utf-8-sig').splitlines()
    expected = [lines[n - 1].lstrip('\t').removeprefix('PRINTL ')
                for start, end in ((404,405),(494,496),(548,549),(595,597),(637,643),(677,683))
                for n in range(start, end + 1)]
    put(ctx, オトコ=1, 変身能力=1)
    drive(ts.ts_normal(ctx, 1), [3, 1, 0, 1, 7, 0])
    actual = [line.text for line in ctx.out.lines
              if re.match(r'^\[[1-8]\] (?!通常時|変身後)', line.text)]
    assert actual == expected


def test_normal_existing_ts_match_and_restore(ctx):
    put(ctx, オトコ=1, 変身能力=1, 変身時ＴＳ=1, 変身時胸サイズ変動=2,
        変身時体格変動=-1, 変身時外見=5)
    transform(ctx, 1, 1)
    drive(ts.ts_normal(ctx, 1), [0, 0, 0])
    assert (get(ctx,'巨乳'),get(ctx,'小柄'),get(ctx,'外見')) == (2,1,5)
    assert (get(ctx,'変身時胸サイズ変動'),get(ctx,'変身時体格変動')) == (0,0)
    assert (get(ctx,'性別変化'),get(ctx,'変身時ＴＳ'),ctx.state.charas[1].cflag[1]) == (1,-1,1)
    assert_ages(ctx.state)


def test_normal_female_error_retains_target(ctx):
    # @TS_NORMAL:357–362：RETURN 0位於TARGET=KEEP之前，保留原作。
    assert drive(ts.ts_normal(ctx, 1)) == 0
    assert ctx.state.target == 1 and ctx.state.result[0] == 0
    assert ctx.state.result[8] == 765 and ctx.state.results[0] == '保留字串'


@pytest.mark.parametrize('kind,forms', [('mtof',(0,)),('ftom',(1,)),('normal',(1,0))])
def test_profile_sizes_use_real_calculator_and_preserve_tail(ctx, kind, forms):
    # TRANS_SEX各函式的GENERATE_CHAR_SIZE呼叫方向；
    # ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:254–281指定值覆寫。
    put(ctx, オトコ=int(kind != 'ftom'), 変身能力=1, 変身時ＴＳ=int(kind != 'normal'))
    c = ctx.state.charas[1]
    c.cflag[33],c.cflag[34] = 314159,333333333333333
    names = ('身長','体重','胸囲','胴囲','腰囲','胸の重量')
    normal = (1700,600,950,700,960,15)
    altered = (1800,700,1000,750,1000,20)
    for name,a,b in zip(names,normal,altered):
        put(ctx, **{name+'指定':a, '変身時'+name+'指定':b})
    # 身長指定在:254–260同樣覆寫；MAXBASE/BASE未被呼叫的形態保留哨兵。
    for slot in range(43,49):
        c.base[slot],c.maxbase[slot] = 71,72
    drive(getattr(ts,'ts_'+kind)(ctx,1), [3,1,0,1,7,0] if kind == 'normal' else [])
    assert tuple(c.base[i] for i in range(43,49)) == (normal if 0 in forms else (71,)*6)
    assert tuple(c.maxbase[i] for i in range(43,49)) == (altered if 1 in forms else (72,)*6)
    assert tuple(ctx.state.result[i] for i in range(2,8)) == (normal if forms[-1] == 0 else altered)
    assert ctx.state.result[1] == 333333333333333 and ctx.state.result[8] == 765
    assert ctx.state.results[0] == '保留字串'
    assert_ages(ctx.state)


@pytest.mark.parametrize('service', ['null','catalog'])
@pytest.mark.parametrize('kind,expected', [('mtof',1),('ftom',10),('normal',1)])
def test_first_event_real_dispatch_waits_and_resumes(ctx, kind, expected, service):
    # ERB/地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST:82–150。
    from eragvt.game.prison.event import _msg_first
    from eragvt.narration.service import CatalogNarrationService
    put(ctx, オトコ=int(kind != 'ftom'), 変身能力=int(kind != 'normal'), 変身時ＴＳ=int(kind != 'normal'))
    st = ctx.state
    st.target = 1
    c = st.target_chara
    c.cflag[6] = 99999  # 人工資料沒有口上；只驗TS hook，避免附帶其他事件。
    c.cstr[14] = '長髮'
    st.flag[804] |= 1  # CONFIG_CHECK_PRISON_F(0)讀FLAG:804 bit0。
    if kind == 'mtof':
        transform(ctx,1)
    if service == 'catalog':
        ctx.narration = CatalogNarrationService(default_csv_dir().parent/'ERB',ctx.data)
    gen = _msg_first(ctx)
    try:
        assert next(gen) is None
        assert c.cstr[13] == '短髮'
        assert st.target == 1
        assert gen.send(99) is None
        if kind == 'normal':
            gen.send(3)
            gen.send(1)
            gen.send(7)
        with pytest.raises(StopIteration):
            gen.send(0)
        assert c.cstr[13] == '長髮'
        assert get(ctx,'性別変化') == expected
        assert c.cflag[1] == int(kind == 'mtof')
        assert st.result[0] == 0 and st.result[8] == 765
        assert_ages(st)
    finally:
        gen.close()


@pytest.mark.parametrize('choice,delta', [(0,0),(1,0),(2,1),(3,-2),(4,-1),(5,0),(6,1),(7,2),(8,3)])
def test_normal_alternate_bust_all_original_formulas(ctx, choice, delta):
    # @TS_NORMAL:561–587，以通常爆乳2代入；1、2採加法，3–8採減法。
    put(ctx, オトコ=1, 変身能力=1)
    drive(ts.ts_normal(ctx,1),[5,1,choice,1,7,0])
    assert get(ctx,'巨乳') == 2 and get(ctx,'変身時胸サイズ変動') == delta


@pytest.mark.parametrize('choice,delta', [(0,0),(1,0),(2,0),(3,1),(4,0)])
def test_normal_alternate_body_all_original_formulas(ctx, choice, delta):
    # @TS_NORMAL:622–632，通常長身1、原變動0。
    put(ctx, オトコ=1, 変身能力=1, 長身=1)
    drive(ts.ts_normal(ctx,1),[3,1,0,choice,7,0])
    assert get(ctx,'長身') == 1 and get(ctx,'変身時体格変動') == delta


@pytest.mark.parametrize('choice,expected', [(0,4),(1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,0)])
def test_normal_alternate_appearance_all_choices(ctx, choice, expected):
    # @TS_NORMAL:720–730。
    put(ctx, オトコ=1, 変身能力=1)
    drive(ts.ts_normal(ctx,1),[3,1,0,1,4,99,choice])
    assert get(ctx,'外見') == 4 and get(ctx,'変身時外見') == expected


def test_normal_color_second_form_rechecks_after_first_copy(ctx):
    # @TS_NORMAL:826–849、879–906：通常時選0後相等，後一題不出現。
    put(ctx, オトコ=1, 変身能力=1)
    c = ctx.state.charas[1]
    c.cstr[31],c.cstr[34],c.cstr[35],c.cstr[37] = '赤','青','緑','褐色'
    drive(ts.ts_normal(ctx,1),[3,1,0,1,7,0,0,1,1,0])
    assert (c.cstr[30],c.cstr[31]) == ('赤','赤')
    assert (c.cstr[32],c.cstr[33],c.cstr[34],c.cstr[35]) == ('黒','黒','黒','黒')
    assert (c.cstr[36],c.cstr[37]) == ('褐色','褐色')


@pytest.mark.parametrize('kind', ['mtof','ftom','normal'])
def test_equal_appearance_has_no_extra_prompts_and_no_profile_write(ctx, kind):
    put(ctx, オトコ=int(kind != 'ftom'), 変身能力=1, 変身時ＴＳ=int(kind != 'normal'))
    c = ctx.state.charas[1]
    for slot in range(43,49):
        c.base[slot],c.maxbase[slot] = 123,456
    drive(getattr(ts,'ts_'+kind)(ctx,1),[3,1,0,1,7,0] if kind == 'normal' else [])
    assert all(c.base[i] == 123 and c.maxbase[i] == 456 for i in range(43,49))
    assert_ages(ctx.state)


@pytest.mark.parametrize('kind', ['mtof','normal'])
@pytest.mark.parametrize('wet,v', [(1,1),(1,-1),(-1,1),(-1,-1)])
def test_sensitivity_deltas_clear_only_in_mtof(ctx, kind, wet, v):
    # @TS_MtoF:57–69清除變動；@TS_NORMAL:738–748只設正負對應值，保留變動。
    put(ctx, **{'オトコ':1, '変身能力':1, '変身時ＴＳ':1,
                '変身時濡れやすさ変動':wet, '変身時Ｖ感覚変動':v})
    drive(getattr(ts,'ts_'+kind)(ctx,1), [3,1,7] if kind == 'normal' else [])
    assert get(ctx,'濡れやすい' if wet > 0 else '濡れにくい') == 1
    assert get(ctx,'Ｖ敏感' if v > 0 else 'Ｖ鈍感') == 1
    assert (get(ctx,'変身時濡れやすさ変動'),get(ctx,'変身時Ｖ感覚変動')) == ((0,0) if kind == 'mtof' else (wet,v))


@pytest.mark.parametrize('virgin,expected', [(-4,1),(-3,2),(-2,-2),(1,1)])
def test_ftom_restores_stored_virgin_and_copies_appearance(ctx, virgin, expected):
    # @TS_FtoM:202–204、246–250；已變身前態，不額外調用TRANSFORM設置前態。
    put(ctx, **{'オトコ':1,'変身能力':1,'変身時ＴＳ':1,'処女':virgin,
                '外見':3,'変身時外見':5,'ふたなり':1,'変身時ふたなり':0})
    c = ctx.state.charas[1]
    c.cflag[1] = 2  # 原文只記TRANS=1，結尾回到1，不保留特殊變身值2。
    drive(ts.ts_ftom(ctx,1))
    assert (get(ctx,'処女'),get(ctx,'変身時外見'),get(ctx,'変身時ふたなり')) == (expected,3,1)
    assert c.cflag[1] == 1 and ctx.state.target == 2


def test_turnend_prison_real_generator_chain(ctx):
    # ERB/インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND:103
    # →ERB/ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB@PRISON:27、@PRISON_EVENT:64–68。
    from eragvt.game import turnend
    from eragvt.game.action import Step
    from eragvt.state import GameRng
    from eragvt.state.constants import GameMode, MODE_OPTIONS
    put(ctx, オトコ=1)
    st = ctx.state
    st.flag[0] = MODE_OPTIONS[GameMode.NORMAL]
    st.flag[804] |= 1
    st.flag[799] = st.charanum
    st.flag[798] = 2
    st.flag[100] = 1  # 尚有敵方存在，不觸發結局。
    st.flag[2] = 11  # ERB/ゲーム内_イベント発生/オープニング処理.ERB@SET_LIMIT_DAY:432。
    st.charas[1].cflag[0] = 1
    st.charas[1].cflag[21] = 1
    st.charas[1].cflag[6] = 99999
    st.charas[1].cflag[220] = 9
    subject = st.charas[1]
    before = subject.exp[ctx.data.index_of('EXP','被姦経験')]
    # 原作PRISON:98–104結界防止後續妊娠呼叫；保留真實指令與事件後處理。
    for slot in range(30,34):
        subject.base[slot] = 10000
    st.rng = GameRng(70)
    gen = turnend.event_turnend(ctx)
    try:
        assert next(gen) is None
        assert st.target_chara.cflag[220] == 0
        assert st.target_chara.cflag[31] == 0  # 輸入前不執行後續幽閉狀態更新。
        assert '胸サイズ' in '\n'.join(line.text for line in ctx.out.lines)
        assert gen.send(999) is None
        assert st.target_chara.cflag[31] == 0
        gen.send(3)
        gen.send(1)
        with pytest.raises(StopIteration) as stop:
            gen.send(7)
        assert stop.value.value == Step.SHOP
        # PRISON:164–168在TS完成後才更新，不由Python輸出反推expected。
        assert subject.cflag[31] == 1
        assert subject.exp[ctx.data.index_of('EXP','被姦経験')] == before + 1
        assert subject.talent[ctx.data.index_of('TALENT','性別変化')] == 1
        assert_ages(st)
    finally:
        gen.close()
