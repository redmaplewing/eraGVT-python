"""S37：expected 由 ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION 推導。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first, PRESET_TOKUSOU
from eragvt.game import succession
from eragvt.state import GameState, GameRng
from eragvt.state.constants import GameMode, MODE_OPTIONS
from eragvt.text import TextOutput, NullNarrationService


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    st = GameState.new(data, rng=GameRng(1))
    event_first(st, data, preset=PRESET_TOKUSOU)
    return Ctx(st, data, TextOutput(), NullNarrationService())


@pytest.mark.parametrize("mode,rank,loops,expected", [
    (GameMode.NORMAL, 1, 1, 5), (GameMode.SOLO, 2, 1, 3),
    (GameMode.HARDCORE, 6, 4, 36), (GameMode.INSTANT, 5, 7, 48),
    (GameMode.SURVIVAL, 4, 1, 5),
])
def test_points(ctx, mode, rank, loops, expected):
    # :31–129：周回數、模式、評價先加總再乘周回倍率。
    ctx.state.flag[0] = MODE_OPTIONS[mode]
    ctx.state.flag[854] = loops
    assert succession.points(ctx, rank) == expected


@pytest.mark.parametrize("kills,bonus", [(7,0),(8,1),(20,2),(30,4),(40,6),(50,8),(60,12)])
def test_global_points(ctx, kills, bonus):
    ctx.state.flag[854] = 4
    g = ctx.globals.mem.global_
    g[114] = kills
    g[211] = 1
    g[220] = g[228] = g[269] = 1
    # :79–268：稱號乘倍率，實績 (10+20+5)/10 截斷後才加。
    assert succession.points(ctx, 1) == (3+5+5+bonus)*2+3
    g[115] = 1000
    assert succession.points(ctx, 1) == 1000


def test_money_refund_quirk(ctx):
    # :674–737：選5扣16，但切到1時退 LOCAL:15*4 (=20)，照原作。
    s = succession.Selection(30)
    s.money_choice(5)
    assert (s.remaining, s.values[15]) == (14,5)
    s.money_choice(1)
    assert (s.remaining, s.values[15]) == (30,1)
    s.money_choice(1)
    assert (s.remaining, s.values[15]) == (34,0)


@pytest.mark.parametrize("first,second,cost", [(22,27,2),(23,28,2),(25,30,2),(27,22,6),(28,23,6),(30,25,8)])
def test_exclusive_options(first,second,cost):
    # :907–1001：相反選項退回原價後購買新選項。
    s = succession.Selection(30)
    s.toggle(first)
    s.toggle(second)
    assert s.remaining == 30-cost
    assert s.values[first] == 0 and s.values[second] == 1


@pytest.mark.parametrize("keep_sex", [0,1])
def test_character_ranges(ctx, keep_sex):
    # :1104–1373：精確半開區間，EXP:58 故意讀 CSVCFLAG_F，保留原文怪處。
    st = ctx.state
    c = st.charas[1]
    c.cflag[0] = 999
    c.cflag[239] = 88
    c.cflag[998] = 77
    c.cflag[999] = 1
    c.exp[58] = 900
    c.exp[59] = 123
    c.palam[0] = 321
    c.abl[0] = 9
    c.mark[90] = 8
    s = succession.Selection(30)
    s.values[11] = keep_sex
    succession.reset_character(ctx, 1, s)
    d = ctx.data.charas[c.no]
    assert c.abl[0] == (9 if keep_sex else d.abl.get(0,0))
    assert c.cflag[239] == 88
    assert c.cflag[998] == (77 if keep_sex else d.cflag.get(998,0))
    assert c.cflag[999] == 0
    assert c.exp[58] == d.cflag.get(58,0)
    assert c.exp[59] == 123 and c.palam[0] == 321
    assert c.mark[90] == d.mark.get(90,0)


def test_reset_globals_and_delete_relations(ctx):
    # :1043–1097, :1387–1422：未選角色相鄰交換後刪末尾；MASTER 的 RELATION 亦參與交換。
    st = ctx.state
    kept = st.charas[2]
    kept.cflag[0] = 999
    for i,c in enumerate(st.charas):
        for j in range(st.charanum):
            c.relation[j] = 100*i+j
    st.day[2] = 91
    st.flag[8] = 23
    st.flag[854] = 3
    st.flag[999] = 71
    st.flag[250] = 99
    st.tflag[77] = 81
    st.results[3] = "保留"
    s = succession.Selection(20)
    s.values[10] = 1
    succession.reset_data(ctx, s)
    assert st.charas[1] is kept and st.charanum == 2
    assert kept.relation[1] == 202
    assert st.charas[0].relation[1] == 2
    assert st.day[2] == 91 and st.flag[8] == 23 and st.flag[854] == 3
    assert st.flag[999] == 71 and st.flag[250] == 0
    assert st.tflag[77] == 81 and st.results[3] == "保留"
    assert (st.money, st.flag[852], st.flag[50], st.flag[51]) == (1000,5000,1,1)


def test_three_pages_invalid_and_confirm(ctx):
    st=ctx.state
    st.flag[854]=1
    gen=succession.succession_gen(ctx,1)  # 5 點。
    next(gen)
    for key in (1234,3,2,8):  # 無效、未解鎖等級、無女兒、無碎片。
        gen.send(key)
        assert "(5pts.)" in ctx.out.lines[-14].text or any("(5pts.)" in ln.text for ln in ctx.out.lines[-30:])
    gen.send(4)  # 戰技需8，拒絕。
    gen.send(200)
    gen.send(11)  # 夜間回復需8，拒絕。
    gen.send(19)  # 妊娠機率3，剩2。
    assert any("(2pts.)" in ln.text for ln in ctx.out.lines[-30:])
    gen.send(200)
    gen.send(21)  # 人氣免費。
    gen.send(0)
    gen.send(200)  # 最後一頁不能再往後。
    assert any("PAGE < 3/3 >" in ln.text for ln in ctx.out.lines[-8:])
    gen.send(100)
    gen.send(0)  # 第二頁全部退點。
    gen.send(100)
    gen.send(999)
    gen.send(77)  # 確認輸入保持等待。
    gen.send(1)  # 否，退回選單。
    assert ctx.out.lines[-1].text=="[999] 引き継ぎ開始"
    gen.send(999)
    gen.send(0)
    gen.send(6)  # SANDBOX 不可選。
    gen.send(100)
    assert st.result[0]==999
    assert ctx.out.lines[-1].text=="[999] 引き継ぎ開始"
    gen.close()


def test_selected_characters_complete_succession(ctx):
    from eragvt.game.action import Step
    st=ctx.state
    st.flag[854]=1
    old=st.charas[2]
    gen=succession.succession_gen(ctx,1)
    next(gen)
    for key in (0,2,999,999,1):  # 選角色2→開始→NORMAL（無GLOBAL通關次數選單）。
        gen.send(key)
    assert any("基本セット" in ln.text for ln in ctx.out.lines[-10:])
    with pytest.raises(StopIteration) as done:
        gen.send(1)
    assert done.value.value==Step.SHOP
    assert st.charas[1] is old and st.charanum==4
    assert st.flag[64]==-1 and st.flag[41]==1
    assert all(c.cflag[999]==1 for c in st.charas[1:])


@pytest.mark.parametrize("choice,money,facilities", [(0,1000,(1,1,0,0)),(1,2625,(1,1,0,0)),(4,7500,(1,1,0,0)),(5,5000,(1,2,0,1))])
def test_money_reset(ctx,choice,money,facilities):
    # :1401–1406，MONEY 已含 ENDING 退款；設施值=2000+500。
    st=ctx.state
    st.money=6500
    st.flag[50],st.flag[51],st.flag[52],st.flag[53]=1,2,0,1
    s=succession.Selection(100)
    s.values[15]=choice
    succession.reset_data(ctx,s)
    assert st.money==money
    assert tuple(st.flag[i] for i in (50,51,52,53))==facilities


def test_preserved_options_and_item_ranges(ctx):
    st=ctx.state
    s=succession.Selection(100)
    s.values[18]=s.values[26]=s.values[31]=1
    s.values[17]=7
    st.flag[200]=123
    st.flag[54]=7
    st.flag[853]=99
    for i in (100,101,199,200,300,301,399,400,401,699,700):
        st.item[i]=8
    succession.reset_data(ctx,s)
    assert (st.flag[200],st.flag[54],st.flag[852],st.flag[853])==(123,7,8500,0)
    assert st.flag[906]==1 and st.flag[0]==66
    assert [st.item[i] for i in (100,200,300,400,700)]==[8]*5
    assert [st.item[i] for i in (101,199,301,399,401,699)]==[0]*6


def test_daughter_cancel_and_solo_restriction(ctx):
    st=ctx.state
    ctx.globals.mem.global_[115]=100
    st.charas[2].cflag[231]=1
    gen=succession.succession_gen(ctx,1)
    next(gen)
    for key in (0,100,999):
        gen.send(key)
    assert st.charas[2].cflag[0]!=999
    for key in (2,0,2,999,2):
        gen.send(key)
    assert st.charas[2].cflag[0]==0
    gen.send(999)
    gen.send(2)  # 已選2人，SOLO 必須留在模式輸入。
    assert st.day[0]==0 and st.charanum==4
    gen.send(100)
    assert ctx.out.lines[-1].text=="[999] 引き継ぎ開始"
    gen.close()


def test_no_personality_relation_swap_bug(ctx):
    # :1383 故意檢查 LOCAL（前一個汎用角色的性格=0），因此後續不交換 RELATION。
    st=ctx.state
    st.charas[1].no=0
    for i in range(10,50):
        st.charas[1].talent[i]=0
    st.charas[1].cflag[0]=999
    st.charas[3].cflag[0]=999
    st.charas[1].relation[2]=12
    st.charas[1].relation[3]=13
    succession.reset_data(ctx,succession.Selection(5))
    assert st.charas[1].relation[2]==12
    assert st.charas[1].relation[3]==0


def test_ts_swap_uses_target(ctx):
    # :1263–1265 的 SWAP 未指定 CCOUNT，必須交換 TARGET 的欄位。
    st=ctx.state
    st.target=2
    ti=lambda n:ctx.data.index_of("TALENT",n)
    st.charas[1].talent[ti("女体受容")]=1
    st.charas[2].talent[ti("男性苦手")]=1
    st.charas[2].talent[ti("女性苦手")]=2
    succession.reset_character(ctx,1,succession.Selection(5))
    assert st.charas[2].talent[ti("男性苦手")]==2
    assert st.charas[2].talent[ti("女性苦手")]==1


def test_negative_character_input_matches_source_error(ctx):
    # SUCCESSION.ERB@SUCCESSION:559 只有上界，負數 CFLAG 索引會觸發引擎範圍錯誤。
    gen=succession.succession_gen(ctx,1)
    next(gen)
    gen.send(0)
    with pytest.raises(NotImplementedError,match="負索引"):
        gen.send(-1)


@pytest.mark.parametrize("keep,expected", [(0,0),(1,150)])
def test_attraction_uses_cflag_csv_or_quarter(ctx,keep,expected):
    # :1304–1309：不保留用 CSVCFLAG_F(58)，保留時100以上只留25%。
    c=ctx.state.charas[1]
    c.exp[58]=300
    s=succession.Selection(30)
    s.values[20]=keep
    succession.reset_character(ctx,1,s)
    assert c.exp[58]==expected


def test_preserve_all_daughter_fields(ctx):
    # :1108、:1341–1352：性成長保留才會保有女兒231；娘能力補正只直接加BASE。
    st=ctx.state
    c=st.charas[1]
    c.cflag[231]=1
    c.cflag[60]=70
    c.abl[50]=30
    c.abl[30]=8
    c.exp[5]=500
    c.equip[600]=1
    c.cflag[40]=c.cflag[41]=c.cflag[42]=0
    s=succession.Selection(100)
    for i in (11,13,14,19):
        s.values[i]=1
    succession.reset_character(ctx,1,s)
    assert (c.abl[50],c.abl[30],c.exp[5],c.equip[600])==(30,8,500,1)
    assert c.cflag[231]==1
    assert c.base[0]==ctx.data.charas[c.no].base.get(0,0)+70
    assert c.maxbase[0]==ctx.data.charas[c.no].base.get(0,0)
    assert [c.cflag[i] for i in (40,41,42)]==[-1]*3
