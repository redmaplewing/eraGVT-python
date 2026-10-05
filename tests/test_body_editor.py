"""S61：一般身體編輯；expected 直接由 CHARA_SIZE_UI.ERB 分支推導。"""
import pytest

from eragvt.data import load_game_data, default_csv_dir
from eragvt.state import GameState, GameRng
from eragvt.game.action import Ctx
from eragvt.text import TextOutput, NullNarrationService
from tools.sim_adult import adult_data
from eragvt.game.body_editor import size_setting, color_table


@pytest.fixture(scope='module')
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def ctx(data):
    st = GameState.new(data, rng=GameRng(61))
    st.charas = st.charas[:1]
    c = st.add_chara(data, 0)
    c.name = c.callname = '人工成年'
    c.cflag[34] = 333333333333333
    c.cflag[33] = 314159
    c.cflag[240] = 1
    c.base[47] = 900
    c.talent[data.index_of('TALENT', '変身能力')] = 1
    for a in (c.base, c.maxbase):
        a[40] = a[41] = 25
    for k in (30,31,32,33,34,35,36,37):
        c.cstr[k] = '8//8//8'
    return Ctx(st, data, TextOutput(), NullNarrationService())


def finish(gen):
    with pytest.raises(StopIteration):
        gen.send(99)


@pytest.mark.parametrize('mode,slot', [(0,41),(50,40)])
def test_age_invalid_then_25_and_return(ctx, mode, slot):
    """@SIZE_SETTING:1461–1473，超界重試；本次有效資料固定25。"""
    gen=size_setting(ctx,1); next(gen); gen.send(mode)
    gen.send(-1); gen.send(100000); gen.send(25)
    finish(gen)
    assert ctx.state.charas[1].base[slot] == 25
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize('choice,slot,value', [(601,30,'255//8//8'),(654,31,'255//255//8'),(710,32,'40//24//24'),(752,33,'8//255//125'),(803,34,'8//125//255'),(858,35,'205//205//205'),(901,36,'255//200//180'),(952,37,'183//86//17')])
def test_color_presets(ctx, choice,slot,value):
    """@SIZE_SETTING:1769–1790、1814–1823，不要求先開色彩模式。"""
    gen=size_setting(ctx,1); next(gen); gen.send(choice)
    assert ctx.state.charas[1].cstr[slot] == value
    finish(gen)


@pytest.mark.parametrize('mode,choice,slot,key', [(5,108,12,30008),(15,214,13,30114),(25,263,14,30113),(45,313,18,30213)])
def test_hair_and_eyes(ctx,mode,choice,slot,key):
    """@SIZE_SETTING:1752–1759；子頁編輯後再次輸入mode返回。"""
    c=ctx.state.charas[1]
    c.cstr[14]='另一髮型'
    gen=size_setting(ctx,1); next(gen); gen.send(mode); gen.send(choice)
    assert c.cstr[slot] == ctx.data.str_defaults[key]
    gen.send(mode); finish(gen)


def test_default_preserves_target_compacts_and_reentry(ctx):
    """@SIZE_SETTING:1734–1743、2115–2142；99確認，無整頁取消。"""
    c=ctx.state.charas[1]; c.cstr[41]='沉穩'; c.cstr[42]='慎重'
    ctx.state.target=0
    gen=size_setting(ctx,1); next(gen)
    assert ctx.state.target==1
    finish(gen)
    assert ctx.state.target==0
    assert [c.cstr[i] for i in (40,41,42)]==['沉穩','慎重','']
    gen=size_setting(ctx,1);next(gen);finish(gen)
    assert c.base[41]==c.maxbase[41]==25


@pytest.mark.parametrize('starting,expected', [(0,1),(1,2),(2,3),(6,0),(9,1)])
def test_general_appearance_cycle(ctx,starting,expected):
    """@SIZE_SETTING:1653–1670，正常與變身外貌同步。"""
    c=ctx.state.charas[1]
    c.talent[ctx.data.index_of('TALENT','外見')]=starting
    gen=size_setting(ctx,1);next(gen);gen.send(4)
    assert c.talent[ctx.data.index_of('TALENT','外見')]==expected
    assert c.talent[ctx.data.index_of('TALENT','変身時外見')]==expected
    finish(gen)


def test_height_cycle_and_named_character_restriction(ctx):
    """@SIZE_SETTING:1506–1531；NO != 0不能改身高素質。"""
    c=ctx.state.charas[1];long=ctx.data.index_of('TALENT','長身');short=ctx.data.index_of('TALENT','小柄')
    c.talent[long]=c.talent[short]=0
    gen=size_setting(ctx,1);next(gen)
    for expected in ((1,0),(0,1),(0,0)):
        gen.send(1);assert (c.talent[long],c.talent[short])==expected
    c.no=5;gen.send(1);assert c.talent[long]==c.talent[short]==0
    gen.send(30) # :1717，非汎用角色輸入1會進入mode1，30取消。
    finish(gen)


def test_palette_confirm_cancel_and_static_axis(ctx):
    """COLOR_TABLE.ERB@COLOR_TABLE:102–153；10000在軸2得到(8,255,8)。"""
    gen=color_table(ctx);next(gen);gen.send(2);gen.send(10000);gen.send(30016)
    with pytest.raises(StopIteration):gen.send(0)
    assert [ctx.state.result[i] for i in range(4)]==[1,4,127,4]
    gen=color_table(ctx);next(gen)
    # 跨呼叫MODE仍1，選1返回選色；軸仍2、重新選色重置明度32。
    gen.send(1);gen.send(10000)
    assert [ctx.state.result[i] for i in (1,2,3)]==[8,255,8]
    with pytest.raises(StopIteration):gen.send(99)
    assert [ctx.state.result[i] for i in range(4)]==[-1]*4


def test_unported_actions_remain_explicit_stops(ctx):
    gen=size_setting(ctx,1);next(gen)
    with pytest.raises(NotImplementedError,match='SIZE_SETTING'):
        gen.send(70)


def test_display_result_tail_from_top_under(ctx):
    """@SIZE_SETTING:341–342、378–379；顯示覆寫RESULT:1，非GENERATE的成長曲線。"""
    c=ctx.state.charas[1];c.cstr[14]='不同'
    gen=size_setting(ctx,1);next(gen)
    # CHARA_SIZE.ERB@TOP_UNDER:301–322、330–331：年齡min(25,22)，
    # 314159 % (23,7,53)=(2,6,28)，32*(6*2+26-2)/15+28/4+99+8=190。
    assert ctx.state.result[1]==190
    finish(gen)
    assert ctx.state.result[1]==190


@pytest.mark.parametrize('mode,maximum',[(1100,11),(1200,31),(1300,59),(1400,15),(1500,16),(1600,13),(1700,23),(1800,7),(1900,53)])
def test_roller_overrides_boundaries_and_reset(ctx,mode,maximum):
    """@SIZE_SETTING:1477–1503、1825–1834；0也是合法重設。"""
    from eragvt.game.body_editor import RANDOM_FIELDS
    name=RANDOM_FIELDS[(mode-1100)//100];slot=ctx.data.index_of('TALENT',name)
    gen=size_setting(ctx,1);next(gen);gen.send(30);gen.send(mode)
    gen.send(maximum+1)
    assert ctx.state.charas[1].talent[slot]==0
    gen.send(maximum)
    assert ctx.state.charas[1].talent[slot]==maximum
    gen.send(1000)
    assert ctx.state.charas[1].talent[slot]==0
    gen.send(30);finish(gen)


def test_color_cancel_leaves_value_and_palette_is_session_local(ctx,data):
    """COLOR_TABLE:110–117取消、#DIM生命週期見VariableToken.cs:1846–1865。"""
    c=ctx.state.charas[1];before=c.cstr[30]
    gen=size_setting(ctx,1);next(gen);gen.send(600);gen.send(99)
    assert c.cstr[30]==before
    finish(gen)
    assert ('COLOR_TABLE',0) in ctx.state.temp.locals
    assert ('COLOR_TABLE',0) not in GameState.new(data).temp.locals
    assert 'COLOR_TABLE' not in str(ctx.state.to_json())
    fresh=Ctx(GameState.new(data),data,TextOutput(),NullNarrationService())
    gen=color_table(fresh);next(gen);gen.send(10000)
    assert [fresh.state.result[i] for i in (1,2,3)]==[8,8,255]
    with pytest.raises(StopIteration):gen.send(99)


def test_common_editor_real_input_and_reentry(ctx):
    """FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:256–257，SIZE_SETTING返回主編輯。"""
    from eragvt.game.character_editor import character_editor
    c=ctx.state.charas[1]
    gen=character_editor(ctx,1);next(gen);gen.send(6);gen.send(601)
    gen.send(99)
    assert c.cstr[30]=='255//8//8'
    gen.send(6);gen.send(99);finish(gen)


def test_personality_literal_comparison_duplicate_candidates_and_manual(ctx):
    """@SET_PERSONALITY:2241–2247一般引號按字面比較；2272–2277空字重試。"""
    from copy import copy
    from eragvt.game.body_editor import set_personality
    ctx.data=copy(ctx.data);ctx.data.str_defaults=dict(ctx.data.str_defaults)
    ctx.data.str_defaults[30500]='沉穩'
    class Rng:
        def rand(self,n):return 0
    ctx.state.rng=Rng()
    c=ctx.state.charas[1];c.cstr[40]='沉穩'
    gen=set_personality(ctx,1,41);next(gen)
    assert sum(line.text.endswith('沉穩') for line in ctx.out.lines)==20
    gen.send(20);gen.send('');gen.send(20)
    with pytest.raises(StopIteration):gen.send('謹慎')
    assert c.cstr[41]=='謹慎'


def test_personality_lock_clear_and_three_random_draws(ctx):
    """@SIZE_SETTING:1863–1888，鎖定不抽亂數；清除不解除鎖定。"""
    from copy import copy
    ctx.data=copy(ctx.data);ctx.data.str_defaults=dict(ctx.data.str_defaults)
    ctx.data.str_defaults[30500]='沉穩'
    class Rng:
        calls=0
        def rand(self,n):self.calls+=1;return 0
    rng=Rng();ctx.state.rng=rng
    c=ctx.state.charas[1];c.cstr[40]='謹慎'
    gen=size_setting(ctx,1);next(gen);gen.send(160);gen.send(69)
    assert [c.cstr[k] for k in (40,41,42)]==['謹慎','沉穩','沉穩'] and rng.calls==2
    gen.send(260);gen.send(69)
    assert c.cstr[40]=='' and rng.calls==4
    finish(gen)
