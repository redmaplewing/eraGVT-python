"""S86 原文決策資訊：人工25歲前態；expected 由各函式原文推導。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game import shop
from eragvt.game.battle import train
from eragvt.state import GameState, FixedRng
from eragvt.text import TextOutput, NullNarrationService

@pytest.fixture(scope="module")
def data():
    from tools.sim_adult import adult_data
    return adult_data(load_game_data(default_csv_dir()))

@pytest.fixture
def ctx(data):
    return make_context(data)


def make_context(data):
    st = GameState.new(data, FixedRng([]))
    st.charas=st.charas[:1]
    for _ in range(3):
        c = st.add_chara(data, 0)
        c.talent.clear()
        c.cflag.clear()
        c.name = c.callname = "人工成年"
        c.cflag[999] = 1
        for i in (0,1,2):
            c.base[i] = c.maxbase[i] = 1000
        for i in (10,11,12,13):
            c.base[i] = c.maxbase[i] = 100
    st.target = 1
    st.flag[2]=10
    st.flag[10],st.flag[11] = 0,3
    st.flag[12],st.flag[13],st.flag[14],st.flag[16] = 1000,250,100,100
    st.charas[1].tcvarn[0] = 2
    st.charas[1].tcvarn[20] = st.charas[1].tcvarn[24] = -1
    st.savestr[13] = "BOSS"
    st.result[1],st.results[1] = 74,"尾格"
    return Ctx(st,data,TextOutput(),NullNarrationService())

def text(ctx):
    return "\n".join(line.text for line in ctx.out.lines)

def talent(ctx,name,value):
    ctx.state.target_chara.talent[ctx.data.index_of("TALENT",name)] = value

@pytest.mark.parametrize("day,abnormal,expected",[(1,0,"月経"),(12,0,""),(12,1,"危険日"),(15,3,"危険日"),(19,1,""),(19,2,"排卵日"),(25,3,"排卵日")])
def test_shop_cycle_and_fatigue(ctx,day,abnormal,expected):
    # SHOP_SHOW_STATUS_LIST.ERB@SHOW_SHOP_STATUS_SIGN:162–188；ESTRUS_CYCLE.ERB@PRINT_ESTRUS_CYCLE:7–27。
    c=ctx.state.target_chara
    c.cflag[217],c.cflag[99],c.cflag[15],c.cflag[241]=day,20,1,3
    talent(ctx,"排卵異常",abnormal)
    shop.shop_show_status_target(ctx.state,ctx.data,ctx.out)
    value=text(ctx)
    assert all(x in value for x in ("[疲労 20]","[憂鬱]","[避妊 3]"))
    assert ("["+expected+"]" in value) if expected else not any(x in value for x in ("[危険日]","[排卵日]","[月経]"))
    assert any(p.color == "#289249" and "疲労" in p.text for l in ctx.out.lines for part in l.parts for p in part.segments)
    assert ctx.state.rng._values == []

@pytest.mark.parametrize("reserve",[False,True])
def test_shop_list_minibars_and_signs(ctx,reserve):
    # SHOP_SHOW_STATUS_LIST.ERB@SHOW_SHOP_STATUS_BASE_ONELINE:143–150：長度4，PAD=2*maxdigits-currentdigits-maxdigits。
    c=ctx.state.target_chara
    c.cflag[999]=0 if reserve else 1
    c.base[0],c.maxbase[0],c.cflag[99]=25,100,50
    fn=shop.shop_show_status_reserve_list if reserve else shop.shop_show_status_party_list
    fn(ctx.state,ctx.data,ctx.out)
    value=text(ctx)
    assert "体力₍▂▁▁▁₎(25/100)" in value
    assert "[疲労 50]" in value

@pytest.mark.parametrize("group,dist,commands",[(0,2,[201,202,203]),(1,2,[1,2,3]),(2,2,[6,7,5]),(0,0,[44,45,46]),(1,0,[100,101,102]),(2,0,[8,9,10])])
def test_categories_source_order(ctx,monkeypatch,group,dist,commands):
    # BATTLE_COM.ERB@SHOW_USERCOM:13–363，各組第一排；可用性仍由 PRINT_COMNAME 判斷。
    ctx.state.flag[801]=4
    v=ctx.state.target_chara.tcvarn
    v[8],v[0]=group,dist
    seen=[]
    monkeypatch.setattr(train,"print_comname",lambda c,n:seen.append(n))
    monkeypatch.setattr(train,"com_able",lambda c,n:(1,None))
    train.show_usercom(ctx)
    assert seen[:3]==commands
    assert v[8]==group
    assert all(str(n) in text(ctx) for n in (810,820,830,800))

@pytest.mark.parametrize("known,expected",[(24,"？？？/？？？"),(25,"？？？/ 1000"),(50,"  250/ 1000")])
def test_battle_info_and_enemy_mask(ctx,known,expected):
    # CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:47–67；コモン関数.ERB@COLORSENTENCE_ENEMYBAR:180–188。
    from eragvt.game.battle.core import fstyle_name
    ctx.state.flag[20]=known
    talent(ctx,"近距離得意",1)
    talent(ctx,"中距離苦手",1)
    train.show_status(ctx)
    value=text(ctx)
    assert "[近距離◎] [中距離×] [遠距離○]" in value
    assert all(fstyle_name(ctx,1,n) in value for n in (1,2,3))
    assert expected in value
    assert "【危険予測】" in value and "予測精度" in value
    assert "CHARGE." in value and "AIR." in value
    assert ctx.state.target_chara.tcvarn[206]==1200
    assert ctx.state.result[1]==74 and ctx.state.results[1]=="尾格"
    assert ctx.state.results[0]=="【エラー：BOSS_3に対するTENTACLE_ACCESS('CHISEI')関数失敗】"
    assert ctx.state.rng._values==[]

@pytest.mark.parametrize("trans,mx,cur,pct,expected,color",[(0,-1,0,0,"（─）",None),(0,0,0,0,"（なし）","#7b7b7b"),(0,100,20,20,"（20/100）","#ff7b00"),(1,100,74,74,"（74/100）","#ffff00"),(1,100,75,75,"（75/100）",None),(1,100,100,100,"（100/100）",None),(1,100,0,0,"（0/100）","#ff0000")])
def test_cloth_durability_boundaries(ctx,trans,mx,cur,pct,expected,color):
    # CLOTH_BATTLE.ERB@CLOTH_BATTLE_DISPHP:48–105；DEF=50，中段=75。
    from eragvt.game.battle.status_display import cloth_durability
    c=ctx.state.target_chara;c.cflag[1]=trans
    c.tcvarn[20 if trans==0 else 22]=mx;c.tcvarn[21 if trans==0 else 23]=cur
    ctx.state.temp.cloth[1],ctx.state.temp.cloth[2]=pct,50
    cloth_durability(ctx)
    value=text(ctx)
    assert expected in value
    label=next(seg for l in ctx.out.lines for p in l.parts for seg in p.segments if "アウター無し" in seg.text)
    assert label.color==color

@pytest.mark.parametrize("noair,nofar,air,expected",[(0,0,0,"[中距離]"),(0,0,2,"[中空中]"),(1,1,0,"---"),(0,1,4,"[中着地]")])
def test_distance_window_rng_and_options(ctx,noair,nofar,air,expected):
    # BATTLE_SHOW_STATUS.ERB@SHOW_DISTANCE_WINDOW:526–531,539–635,702–742；FORECAST:259–340。
    from eragvt.game.battle.status_display import show_distance_window
    from eragvt.game.battle.core import add_battle_situation
    ctx.state.temp.battle_situation=("空中不可," if noair else "")+("遠距離不可," if nofar else "")
    ctx.state.target_chara.tcvarn[216]=air
    show_distance_window(ctx)
    assert expected in text(ctx)
    assert "┣╋╋╋╋┫" in text(ctx) if nofar else "┣╋╋╋╋┫" not in text(ctx)
    assert ctx.state.rng._values==[]


def test_ng_red_remains(ctx):
    # SHOP.ERB@SHOP_NG_ACTION_INFO:347–381，函式沒有 RESETCOLOR。
    c=ctx.state.target_chara;c.cflag[100]=101;c.base[0]=0
    shop.shop_ng_action_info(ctx.state,ctx.data,ctx.out)
    assert ctx.out.color=="#ff0000"


def test_clothing_catalog_real_options(ctx):
    # CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_DRAW_101:101–162。
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.game.battle.status_display import cloth_durability
    from pathlib import Path
    ctx.narration=CatalogNarrationService(Path("source/earGVP/ERB"),ctx.data)
    c=ctx.state.target_chara;c.cflag[40]=101;c.equip[1]=1
    cloth_durability(ctx)
    assert "[カラー：黒]" in text(ctx) and "[セーラー服][スカーフ]" in text(ctx)
    assert not ctx.narration.failures
    assert ctx.state.rng._values==[]
    assert ctx.state.result[1]==74 and ctx.state.results[1]=="尾格"


@pytest.mark.parametrize("variant,expected", [
    (0, "[過剰な露出][隠せない果実]"),
    (1, "[過剰な露出][透けかけた布地]"),
    (2, "[過剰な露出][ずり落ちそうな布切れ]"),
    (3, "[過剰な露出][丸見えの尻肉]"),
    (4, ""), (5, ""), (99, ""),
])
def test_event_clothing_catalog_options(ctx, variant, expected):
    # 3004 プール奇襲.ERB@BATTLE_EVENT_CLOTH_STATUS_3004:8–79：
    # option 只改 RESULTS:0，CASE4/5/ELSE 的代入均被註解；人工角色25歲。
    # CLOTHDATA※イベント専用装備.ERB@CLOTH_CUSTOMIZE_OPTION_DRAW_992:115–120。
    # 流程落尾只清 RESULT:0：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.game.battle.status_display import cloth_durability
    ctx.narration = CatalogNarrationService(default_csv_dir().parent / "ERB", ctx.data)
    st, c = ctx.state, ctx.state.target_chara
    st.flag[45] = 3004
    c.cflag[42], c.cflag[270] = 992, variant
    c.cstr[82], st.savestr[0] = "中性衣裝名稱", "原有衣裝資料"
    st.count[0], st.count[1] = 71, 82
    before_rng = st.rng.snapshot()
    cloth_durability(ctx)
    assert not ctx.narration.failures
    assert expected in text(ctx) if expected else "[過剰な露出]" not in text(ctx)
    assert st.results[0] == expected and st.results[1] == "尾格"
    assert st.result[0] == 0 and st.result[1] == 74
    assert c.cstr[82] == "中性衣裝名稱" and st.savestr[0] == "原有衣裝資料"
    assert (st.count[0], st.count[1]) == (9, 82)
    assert st.rng.snapshot() == before_rng and st.target == 1


@pytest.mark.parametrize("mode,parts,ok", [
    ("option", "OUTER", True), ("option", "OUTER_TRANS", True),
    ("option", "OTHER", True), ("info", "INNER", False),
])
def test_event_clothing_option_boundary(ctx, mode, parts, ok):
    # 3004 プール奇襲.ERB@BATTLE_EVENT_CLOTH_STATUS_3004:8–27：外衣兩分支全為註解。
    # info 未開放 catalog；確認失敗保持現有交易回復契約。
    from eragvt.narration.service import CatalogNarrationService
    ctx.narration = CatalogNarrationService(default_csv_dir().parent / "ERB", ctx.data)
    st = ctx.state
    st.result[0], st.results[0], st.count[0] = 31, "入口殘值", 52
    assert ctx.narration.run_function(ctx, "BATTLE_EVENT_CLOTH_STATUS_3004", [mode, parts]) is ok
    assert (st.result[0], st.results[0]) == ((0, "") if ok else (31, "入口殘值"))
    assert st.result[1] == 74 and st.results[1] == "尾格" and st.count[0] == 52
    assert st.rng._values == [] and not ctx.out.lines


def test_event_clothing_option_failure_rolls_back(ctx):
    # 純顯示 adapter 後失敗必須回復；片段 expected 由上述原文 CASE0 推導。
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.narration.extract import parse_function, read_logical_lines
    svc = ctx.narration = CatalogNarrationService(default_csv_dir().parent / "ERB", ctx.data)
    source = '''@NEUTRAL_OPTION_FAILURE
CALL BATTLE_EVENT_CLOTH_STATUS_3004("option", "INNER")
REPEAT 3
REND
PRINTFORML %RESULTS%
LOCAL = 1 / 0
'''
    svc.catalog._parsed["NEUTRAL_OPTION_FAILURE"] = parse_function(
        svc.catalog.ctx, "口上/neutral.ERB", read_logical_lines(source.encode("utf-8")))
    st = ctx.state
    st.result[0], st.results[0], st.count[0] = 31, "入口殘值", 52
    assert not svc.run_function(ctx, "NEUTRAL_OPTION_FAILURE")
    assert (st.result[0], st.results[0], st.count[0]) == (31, "入口殘值", 52)
    assert st.result[1] == 74 and st.results[1] == "尾格"
    assert st.rng._values == [] and not ctx.out.lines


@pytest.mark.parametrize("flags,expected",[(32,1),(96,1),(416,0)])
def test_palam_side_effect_and_charge_once(ctx,monkeypatch,flags,expected):
    # CHARA_STATUS.ERB@SHOW_TRAIN_PALAM_STATUS:1715–1750；BATTLE_SHOW_STATUS:357–362。
    from eragvt.game.battle import gaping
    count={"gaping":0,"charge":0}
    def touch(*args):
        count["gaping"]+=1
    original=train.status_charge_limit
    def charge(cx):
        count["charge"]+=1
        return original(cx)
    monkeypatch.setattr(gaping,"printform_gaping_now",touch)
    monkeypatch.setattr(train,"status_charge_limit",charge)
    ctx.state.flag[801]=flags
    ctx.state.flag[700]=1
    ctx.state.flag[802]=1<<16
    ctx.state.target_chara.cflag[34]=1
    train.show_status(ctx)
    assert count=={"gaping":expected,"charge":1}


@pytest.mark.parametrize("enemy,known,expected",[("BOSS",0,"【エラー：BOSS_3に対するTENTACLE_ACCESS('CHISEI')関数失敗】"),("BOSS",100,"【エラー：BOSS_3に対するTENTACLE_ACCESS('HOLD')関数失敗】"),("AKUOTI",0,"110")])
def test_display_call_register_residue(ctx,enemy,known,expected):
    # BATTLE_SHOW_STATUS:747–755 的支援→敵知性，以及 :300–317 的最後 HOLD。
    # CLOTHDATAアウター_通常.ERB@CLOTH_STATUS_109:1710：CHISEI110；內衣0無資料。
    st=ctx.state
    st.savestr[13],st.flag[20],st.flag[111]=enemy,known,3
    st.flag[110]=int(enemy=="AKUOTI")
    helper=st.charas[2]
    helper.cflag[100]=106
    helper.cflag[40]=109
    helper.cflag[42]=0
    st.result[0],st.results[0],st.savestr[0]=888,"入口殘值","入口衣裝"
    train.show_status(ctx)
    assert st.result[0]==0 and st.result[1]==74
    assert (st.results[0],st.results[1])==(expected,"尾格")
    assert st.savestr[0]=="SLOT-1,HP0,def0,"  # CLOTHDATAアウター_通常.ERB@CLOTH_STATUS_0:73。
    assert st.target==1 and st.rng._values==[]
    # BATTLE_COM.ERB@USERCOM:629–634 只改分類，沒有消費或覆寫 RESULTS。
    list(train.usercom(ctx,830))
    assert st.results[0]==expected and st.target_chara.tcvarn[8]==2


def test_catalog_failure_stops(ctx):
    from eragvt.game.battle.status_display import cloth_durability
    class FailedCatalog:
        def run_function(self,*args):return False
    ctx.narration=FailedCatalog()
    with pytest.raises(NotImplementedError,match="CLOTH_CUSTOMIZE_OPTION_DRAW"):
        cloth_durability(ctx)


def test_category_real_ability_and_switch(ctx):
    # BATTLE_COM.ERB@USERCOM:629–634 分類不推進回合；PRINT_COMNAME沿 COM_ABLE。
    from eragvt.game.battle.commands import com_able
    st=ctx.state
    st.flag[801]=4
    before=st.rng.snapshot()
    list(train.usercom(ctx,820))
    assert st.target_chara.tcvarn[8]==1 and st.tflag[0]==0
    train.show_usercom(ctx)
    assert "[  1]" in text(ctx) or "[1]" in text(ctx)
    assert st.rng.snapshot()==before
    st.target_chara.tcvarn[12]=1  # 気絶；COM_ABLE:1 不能攻擊。
    ctx.out=TextOutput()
    train.show_usercom(ctx)
    assert "[  1]" not in text(ctx) and "[1]" not in text(ctx)
