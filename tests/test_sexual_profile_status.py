"""S34：預期值由 SEXUAL_PROFILE／ABL_UP_CHECK／BATTLE_SHOW_STATUS／PALAM_UP 原文推導。"""
from _gen_driver import run_no_input
import pytest
from test_gaping import ctx, data
from eragvt.game import sexual_profile as profile
from eragvt.game.battle import ablup, train
from eragvt.game.battle.palam_display import show_train_palam_status, palam_up_display_calculation


class Rolls:
    def __init__(self, values):
        self.values = iter(values)
        self.bounds = []
    def rand(self, bound):
        self.bounds.append(bound)
        value = next(self.values)
        assert 0 <= value < bound
        return value


@pytest.mark.parametrize("level,bounds,indices", [
    (0,[4,5,8],[0,0,0]), (2,[4,5,8],[0,0,0]),
    (3,[4,5,8],[0,0,0]), (4,[4,5,8],[0,0,0]),
    (5,[23,5,8],[0,0,0]), (6,[23,5,8],[0,0,0]),
    (7,[23,5,20,8],[0,0,0,0]),
    (8,[23,8,5,20,8],[0,0,0,0,0]),
    (9,[23,8,5,14,8],[0,0,0,0,0]),
    (10,[23,8,23,23,5,14,8],[0,0,0,1,0,0,0]),
    (11,[8,23,25,5,14,8],[0,0,0,0,0,0]),
    (20,[8,23,25,5,14,8],[0,0,0,0,0,0]),
])
def test_profile_rng_boundaries(ctx,level,bounds,indices):
    # @MAKESEXUALPROFILE:25–108；Lv10 重抽重複形容詞，Lv11 不抽 Adj:1。
    ctx.state.rng = Rolls(indices)
    assert profile.make_sexual_profile(ctx,"C",level)
    assert ctx.state.rng.bounds == bounds


@pytest.mark.parametrize("part,level,bounds", [
    ("B",1,[4,8]),("P",1,[4,3,8]),("V",1,[4,4,13]),("A",1,[4,5,12]),
    ("V",3,[5,4,13]),("A",3,[5,5,12]),("V",5,[28,16,33]),("A",5,[28,14,27]),
    ("V",11,[13,28,25,16,14,33]),("A",11,[13,28,25,14,14,27]),
])
def test_part_tables(ctx,part,level,bounds):
    ctx.state.rng=Rolls([0]*len(bounds))
    profile.make_sexual_profile(ctx,part,level)
    assert ctx.state.rng.bounds==bounds


@pytest.mark.parametrize("flag,expected_bounds", [(0,[23,23,8]),(1,[23,8]),(2,[23,23,8])])
def test_unavailable_title_rerolls(ctx,flag,expected_bounds):
    # MAKE_ADJ_BC:160–166 僅 FLAG:6 == 1 允許替換。
    ctx.state.flag[6]=flag
    ctx.state.savestr[11]="TITLE"
    ctx.state.rng=Rolls([22,0,0] if flag!=1 else [22,0])
    result=profile.make_sexual_profile(ctx,"B",5)
    assert ("TITLE" in result)==(flag==1)
    assert ctx.state.rng.bounds==expected_bounds


@pytest.mark.parametrize("part,index,bound", [("V",32,33),("A",26,27)])
@pytest.mark.parametrize("flag", [0,1,2])
def test_slogan_rerolls(ctx,part,index,bound,flag):
    ctx.state.flag[7]=flag
    ctx.state.savestr[12]="SLOGAN"
    ctx.state.rng=Rolls([0,0,index]+([] if flag==1 else [0]))
    result=profile.make_sexual_profile(ctx,part,5)
    assert ("SLOGAN" in result)==(flag==1)
    assert ctx.state.rng.bounds==[28,16 if part=="V" else 14,bound]+([] if flag==1 else [bound])


@pytest.mark.parametrize("idx,part", [(0,"C"),(1,"V"),(2,"A"),(3,"B")])
def test_ability_write_only_on_increase(ctx,monkeypatch,idx,part):
    c=ctx.state.target_chara
    c.abl[idx]=0
    ctx.state.flag[805]|=1<<6
    calls=[]
    monkeypatch.setattr(profile,"make_sexual_profile",lambda ct,p,lv: calls.append((p,lv)) or "PROFILE")
    ablup._raise(ctx,c,ctx.data.names["ABL"][idx],3)
    assert c.cstr[45+idx]=="PROFILE"
    ablup._raise(ctx,c,ctx.data.names["ABL"][idx],3)
    assert calls==[(part,3)]
    ctx.state.flag[805]=0
    ablup._raise(ctx,c,ctx.data.names["ABL"][idx],4)
    assert c.cstr[45+idx]=="PROFILE" and len(calls)==1


@pytest.mark.parametrize("flags,where,visible,buttons", [
    (0,"上部",False,[]),(32,"上部",True,[]),(32,"下部",False,[]),
    (96,"下部",True,[]),(160,"上部",True,[898,899]),
    (416,"上部",False,[898]),(480,"下部",False,[898]),
    (288,"上部",True,[]),
])
def test_screen_switches(ctx,flags,where,visible,buttons):
    ctx.state.flag[801]=flags
    ctx.state.target_chara.cflag[34]=0
    ctx.state.set_result_x(77,88)
    show_train_palam_status(ctx,where)
    assert (ctx.state.result[0],ctx.state.result[1]) == (0,88)
    text="\n".join(l.text for l in ctx.out.lines)
    assert ("Lv.0" in text)==visible
    assert [v for l in ctx.out.lines for _,v in l.buttons]==buttons


@pytest.mark.parametrize("amount,expected", [(99,"Lv.0"),(100,"Lv.1"),(300,"Lv.2"),
    (600,"Lv.3"),(1500,"Lv.4"),(3000,"Lv.5"),(6000,"Lv.6"),(10000,"Lv.7"),
    (30000,"Lv.8"),(60000,"Lv.9"),(150000,"Lv.10"),(300000,"LvMAX")])
def test_palam_display_levels(ctx,amount,expected):
    ctx.state.flag[801]=32
    ctx.state.target_chara.cflag[34]=0
    ctx.state.target_chara.palam[0]=amount
    show_train_palam_status(ctx,"上部")
    assert expected in ctx.out.lines[1].text


def test_calculation_preserves_original_padding_index_quirk(ctx):
    # @PALAM_UP_DISPLAY_CALCULATION:1356 是 PALAM:LCOUNT，輸出 :1375 才是 PALAM:調教PALAM:LCOUNT。
    c=ctx.state.target_chara
    c.palam.clear()
    c.palam[17]=999990
    ctx.state.temp.up[17]=20
    palam_up_display_calculation(ctx,[0,0,0,0],0)
    # :1378 結尾 1 空白；:1395 直接以減號起始（PRINTFORM 相接）。
    assert ctx.out.lines[0].text=="恐怖：999990 +   20 -   11 = 999999　限界"
    assert ctx.state.result[0]==0  # STRLENFORM 暫值2，函式終端歸0（Process.ScriptProc.cs:61–67）。


def test_extracted_tables_match_source():
    from tools.extract_profile_text import extract
    assert profile.TABLES == extract()


def test_profile_composition_order(ctx,monkeypatch):
    # @MAKESEXUALPROFILE:107 Adj:3+2+1+0、部位、Adv:1+0、動詞。
    seen=[]
    def pick(ct,name,group=0):
        seen.append(name)
        return name + str(len(seen))
    monkeypatch.setattr(profile,"_pick",pick)
    assert profile.make_sexual_profile(ctx,"V",10)==(
        "MAKE_ADJ_VA3MAKE_ADJ_VA1MAKE_ONOMATOPE_VA2MAKE_V_NAME4をMAKE_ADV_25MAKE_VERB_V6のが好き")
    seen.clear()
    assert profile.make_sexual_profile(ctx,"V",11)==(
        "MAKE_BAD_REPUTATION3MAKE_ADJ_VA2MAKE_ONOMATOPE_VA1MAKE_V_NAME4をMAKE_ADV_25MAKE_VERB_V6のが好き")


@pytest.mark.parametrize("male,futa", [(1,0),(0,1)])
def test_profile_p_route_and_saved_cstr(ctx,monkeypatch,male,futa):
    from eragvt.state.savefile import dump_save, load_save
    c=ctx.state.target_chara
    c.talent[ctx.data.index_of("TALENT","オトコ")]=male
    c.talent[ctx.data.index_of("TALENT","ふたなり")]=futa
    c.abl[0]=0
    ctx.state.flag[805]|=1<<6
    seen=[]
    monkeypatch.setattr(profile,"make_sexual_profile",lambda ct,p,lv: seen.append((p,lv)) or "PROFILE")
    ablup._raise(ctx,c,"Ｃ感覚",11)
    assert seen==[("P",11)]
    assert any(p.color=="#ff1991" for l in ctx.out.lines for part in l.parts for p in part.segments if p.text=="PROFILE")
    loaded,_=load_save(dump_save(ctx.state))
    assert loaded.target_chara.cstr[45]=="PROFILE"


def test_ablup_normal_and_ex_updates_in_order(ctx,monkeypatch):
    # @_ABLUP:1021–1058 Lv4→5 20000、:1195–1235 Lv5→6 20000/2*5=50000。
    c=ctx.state.target_chara
    c.abl.clear()
    c.juel.clear()
    c.abl[0]=4
    c.juel[0]=70000
    ctx.state.flag[805]|=1<<6
    calls=[]
    monkeypatch.setattr(profile,"make_sexual_profile",lambda ct,p,lv: calls.append((p,lv)) or str(lv))
    ablup.ablup(ctx,1)
    assert calls==[("C",5),("C",6)]
    assert c.cstr[45]=="6" and c.abl[0]==6 and c.juel[0]==0


@pytest.mark.parametrize("flags,roll_count", [(32,200),(160,200),(416,0),(96,200)])
def test_display_gaping_initialization_once(ctx,flags,roll_count):
    # GAPING.ERB@PRINTFORM_GAPING_NOW:800–808：初始值年齡25→25/20；EXP各1→100抽，9999皆不增加。
    c=ctx.state.target_chara
    c.base[ctx.data.index_of("BASE","年齢")]=25
    c.cflag[35]=c.cflag[36]=0
    c.exp[ctx.data.index_of("EXP","Ｖ拡張経験")]=1
    c.exp[ctx.data.index_of("EXP","Ａ拡張経験")]=1
    ctx.state.flag[801]=flags
    ctx.state.flag[850]&=~(1<<16)  # CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F:43–47；反轉bit。
    from eragvt.game.action import config_check_maniac
    assert config_check_maniac(ctx.state,16)==1
    ctx.state.rng=Rolls([9999]*roll_count)
    for _ in range(2):
        show_train_palam_status(ctx,"上部")
        show_train_palam_status(ctx,"下部")
    assert len(ctx.state.rng.bounds)==roll_count
    assert (c.cflag[35],c.cflag[36])==((25,20) if roll_count else (0,0))


def test_shield_bar_and_shared_result(ctx):
    c=ctx.state.target_chara
    c.cflag[34]=0
    c.base[30],c.maxbase[30]=50,100
    ctx.state.flag[801]=32
    show_train_palam_status(ctx,"上部")
    assert "▮"*13 in ctx.out.lines[1].text
    assert ctx.data.names["TALENT"][190] in ctx.out.lines[1].text
    assert ctx.state.result[0]==0  # COLOR_BAR RETURN 1，其後 SHOW_STATUS_PALAM 終端歸0。


@pytest.mark.parametrize("rank,flag,expected", [
    (0,0,"=    50 "),(1,0,"- 10000 =    50　絶頂"),
    (2,0,"- 10051 =    50　強絶頂"),(2,1,"=    50 "),
])
def test_calculation_ecstasy_and_suppression(ctx,rank,flag,expected):
    c=ctx.state.target_chara
    c.palam.clear()
    c.palam[0]=50
    c.nowex[0]=rank
    ctx.state.temp.up[0]=10000 if rank!=2 else 20000
    palam_up_display_calculation(ctx,[50,0,0,0],flag)
    # padding_P 依加算前+UP = 10050/20050，寬5；值50左側3空白，等號後原文另有1空白。
    assert ctx.out.lines[0].text.endswith(expected)


def test_battle_status_top_bottom_and_controls(data):
    # S86 完整畫面用全新25歲人工角色與完整敵資源，不沿用局部PALAM前態。
    from test_decision_display import make_context
    from tools.sim_adult import adult_data
    ctx=make_context(adult_data(data))
    c=ctx.state.target_chara
    c.cflag[34]=0
    ctx.state.flag[801]=160
    ctx.state.flag[13]=100
    train.show_status(ctx)
    lines=[l.text for l in ctx.out.lines]
    assert next(i for i,l in enumerate(lines) if "Lv.0" in l)<next(i for i,l in enumerate(lines) if "[中距離]" in l)
    list(train.usercom(ctx,899))
    assert ctx.state.flag[801]==224
    from eragvt.text import TextOutput
    ctx.out=TextOutput()
    train.show_status(ctx)
    lines=[l.text for l in ctx.out.lines]
    assert next(i for i,l in enumerate(lines) if "Lv.0" in l)>next(i for i,l in enumerate(lines) if "[中距離]" in l)
    list(train.usercom(ctx,898))
    assert ctx.state.flag[801]==480


def test_palam_up_actual_display_and_static_before(ctx):
    from eragvt.game.battle.palam import palam_up
    from eragvt.game.battle.core import get_local
    from eragvt.state import GameRng
    c=ctx.state.target_chara
    c.cflag[34]=0
    c.palam.clear()
    c.palam[0]=123
    ctx.state.flag[801]=2
    ctx.state.flag[700]=0
    ctx.state.rng=GameRng(3)
    ctx.state.temp.up[0]=1
    run_no_input(palam_up(ctx))
    assert get_local(ctx.state,"PALAM_UP.BEFORE_PALAM_CVAB",0)==123
    assert any("快Ｃ：" in l.text and "123" in l.text for l in ctx.out.lines)
    assert ctx.out.wait_count>0
    c.palam[0]=777
    run_no_input(palam_up(ctx))  # UP:0 == 0，保留 #DIM 的前次值。
    assert get_local(ctx.state,"PALAM_UP.BEFORE_PALAM_CVAB",0)==123
