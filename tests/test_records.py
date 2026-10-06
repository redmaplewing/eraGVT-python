"""S58：預期依 SHOP_TURNEND@UPDATE_STATUS_RECORD、SCORE@SCORE、ENDING@ENDING_1。"""
import pytest
from eragvt.game.input_request import WaitInputRequest
from test_clothing_menu import data, ctx
from eragvt.game import achievements, ending
from eragvt.state.constants import GameMode, MODE_OPTIONS
from eragvt.game.battle.source_check import _all_bosses_cleared, _rescue_captives
from eragvt.game.battle.core import BeginTurnend


@pytest.mark.parametrize("old,value,expected", [(9,8,9),(9,9,9),(9,10,10)])
def test_status_record(ctx,old,value,expected):
    c=ctx.state.charas[1]
    c.name="記録者"
    c.abl[ctx.data.index_of("ABL","レベル")]=7
    c.maxbase[ctx.data.index_of("BASE","体力")]=value
    ctx.globals.mem.global_[103]=old
    ctx.globals.mem.globals_[0]="以前"
    achievements.update_status_record(ctx,1)
    assert ctx.globals.mem.global_[103]==expected
    assert (ctx.globals.mem.globals_[0]=="以前")== (value<=old)
    if value>old:
        assert ctx.globals.mem.globals_[0].endswith("（Lv7）　10")
    assert ctx.globals.exists()  # 無新紀錄也 SAVEGLOBAL
    assert ctx.state.result[0]==0


@pytest.mark.parametrize("mode,slot", [(GameMode.NORMAL,101),(GameMode.SOLO,100),(GameMode.HARDCORE,102),(GameMode.SURVIVAL,None),(GameMode.FREEPLAY,None),(GameMode.SANDBOX,None),(GameMode.INSTANT,None)])
def test_score_counts(ctx,monkeypatch,mode,slot):
    # SCORE:695–750，模式需完整等於 MODE_OPTIONS；總評3，不觸發E/S成就。
    monkeypatch.setattr(ending,"score_values",lambda ctx:(3,3,3,3,3,3,3))
    ctx.state.temp.last_load_version=408
    ctx.state.flag[0]=MODE_OPTIONS[mode]
    old=ctx.state.flag[854]
    assert ending.score(ctx)==3
    assert ctx.globals.mem.global_[113]==3
    assert [ctx.globals.mem.global_[i] for i in (100,101,102)]==[int(i==slot) for i in (100,101,102)]
    assert ctx.globals.exists()
    assert ctx.state.flag[854]==old+1


@pytest.mark.parametrize("old,expected", [(8,9),(9,9),(10,10)])
def test_endless_load_before_record(ctx,old,expected):
    # ENDING:269–277：磁碟舊紀錄覆蓋記憶體後，比較嚴格大於。
    ctx.globals.mem.global_[114]=old
    ctx.globals.save()
    ctx.globals.mem.global_[114]=999
    ctx.state.flag[3]=9
    ctx.state.flag[100]=0
    assert ending._endless_record(ctx)
    assert ctx.globals.mem.global_[114]==expected
    ctx.globals.load()
    assert ctx.globals.mem.global_[114]==expected


@pytest.mark.parametrize("state,owner,expected", [(1,1,271),(2,1,273),(1,2,None),(0,1,None)])
def test_rescue_achievements(ctx,state,owner,expected):
    # SOURCE_CHECK:209–210／240–241，救援變更狀態之前取得。
    c=ctx.state.charas[1]
    c.cflag[0],c.cflag[20],c.cflag[21]=state,owner,3
    ctx.state.flag[10],ctx.state.flag[11]=1,3
    _rescue_captives(ctx)
    assert [ctx.globals.mem.global_[i] for i in (271,273)]==[int(i==expected) for i in (271,273)]


@pytest.mark.parametrize("solo,sensitive,prison,juel,daughters,expected", [
    (True,True,1,1000,3,(259,260,261,265)),
    (False,True,1,1000,3,(259,265)),
    (True,False,0,999,2,()),
])
def test_clear_achievements(ctx,solo,sensitive,prison,juel,daughters,expected):
    # SOURCE_CHECK:283–304：259取最大JUEL而非合計；265原文未檢查solo。
    from copy import deepcopy
    ctx.state.flag[0]=MODE_OPTIONS[GameMode.SOLO if solo else GameMode.NORMAL]
    ctx.state.flag[64]=-1
    c=ctx.state.charas[1]
    for name in ("Ｃ敏感","Ｖ敏感","Ａ敏感","Ｂ敏感"):
        c.talent[ctx.data.index_of("TALENT",name)]=int(sensitive)
    c.exp[ctx.data.index_of("EXP","幽閉経験")]=prison
    c.juel[ctx.data.index_of("JUEL","修練P")]=juel
    while len(ctx.state.charas)<4:
        ctx.state.charas.append(deepcopy(c))
    for i,ch in enumerate(ctx.state.charas[1:]):
        ch.cflag[231]=int(i<daughters)
    with pytest.raises(BeginTurnend):
        _all_bosses_cleared(ctx)
    assert tuple(i for i in (259,260,261,265) if ctx.globals.mem.global_[i])==expected


@pytest.mark.parametrize("kind,name,slot,textslot,suffix", [
    ("BASE","体力",103,0,""),("BASE","気力",104,1,""),("BASE","性耐性",105,2,""),
    ("BASE","攻撃",106,10,""),("BASE","防御",107,11,""),("BASE","敏捷",108,12,""),("BASE","知性",109,13,""),
    ("EXP","魅了経験",110,14,""),
    *[("EXP",name,120+i,20+i,"回") for i,name in enumerate(("Ｖ経験","Ａ経験","自慰経験","フェラ経験","精液経験","絶頂経験","出産経験","近親交配経験","射精経験","噴乳経験","放尿経験","寄生経験"))],
])
def test_each_record_field(ctx,kind,name,slot,textslot,suffix):
    c=ctx.state.charas[1]
    c.maxbase.clear();c.exp.clear()
    getattr(c,"maxbase" if kind=="BASE" else "exp")[ctx.data.index_of(kind,name)]=987
    ctx.globals.mem.global_[88]=654
    ctx.globals.mem.mob_global[9]=321
    ctx.state.result[1]=77
    before=ctx.state.rng.snapshot()
    achievements.update_status_record(ctx,1)
    assert ctx.globals.mem.global_[slot]==987
    assert ctx.globals.mem.globals_[textslot].endswith("　987"+suffix)
    assert ctx.globals.mem.global_[88]==654
    assert ctx.globals.mem.mob_global[9]==321
    assert ctx.state.result[1]==77
    assert ctx.state.rng.snapshot()==before


@pytest.mark.parametrize("old,expected", [(2,3),(3,3),(5,5)])
def test_rank_charm_independent(ctx,monkeypatch,old,expected):
    # S59已裁決：SCORE與SHOW_TROPHY改用113；魅了仍110，不猜回填。
    ctx.globals.mem.global_[113]=old
    ctx.state.charas[1].exp[ctx.data.index_of("EXP","魅了経験")]=77
    achievements.update_status_record(ctx,1)
    monkeypatch.setattr(ending,"score_values",lambda ctx:(3,3,3,3,3,3,3))
    ending.score(ctx)
    assert ctx.globals.mem.global_[110]==77
    assert ctx.globals.mem.global_[113]==expected
    gen=achievements.show_trophy(ctx)
    next(gen)
    assert any("総合ランク最高記録" in line.text and "ＥＤＣＢＡＳ"[expected-1]+"ランク" in line.text for line in ctx.out.lines)
    gen.close()
    assert ctx.globals.mem.globals_[14].endswith("　77")


def test_new_record_wait_before_save(ctx):
    from eragvt.game.wait_bridge import with_achievement_wait
    ctx.state.flag[3]=9;ctx.state.flag[100]=0
    def run():
        ending._endless_record(ctx)
        yield "done"
    ctx.state.result[0],ctx.state.result[1]=73,74
    ctx.state.results[0],ctx.state.results[1]="kept","other"
    rng=ctx.state.rng.snapshot()
    def assert_unchanged():
        assert (ctx.state.result[0],ctx.state.result[1])==(0,74)  # ENDING_1:270 LOADGLOBAL失敗寫RESULT:0=0，WAIT本身保留。
        assert (ctx.state.results[0],ctx.state.results[1])==("kept","other")
        assert ctx.state.rng.snapshot()==rng
    gen=with_achievement_wait(run(),ctx.out)
    assert isinstance(next(gen), WaitInputRequest)
    assert ctx.globals.mem.global_[114]==0
    assert not ctx.globals.exists()
    assert_unchanged()
    assert gen.send(0)=="done"
    assert_unchanged()
    assert ctx.globals.mem.global_[114]==9
    gen.close()


def test_record_reaches_existing_count_unlock(ctx,monkeypatch):
    from eragvt.game.creation_menu import _can_count
    ctx.state.temp.last_load_version=408
    assert not _can_count(ctx)
    monkeypatch.setattr(ending,"score_values",lambda ctx:(3,3,3,3,3,3,3))
    ending.score(ctx)
    assert _can_count(ctx)


def test_score_confirm_before_writes(ctx,monkeypatch):
    from eragvt.game.wait_bridge import with_achievement_wait
    monkeypatch.setattr(ending,"score_values",lambda ctx:(3,3,3,3,3,3,3))
    ctx.state.temp.last_load_version=408
    def run():
        ending.score(ctx)
        yield "done"
    ctx.state.result[0],ctx.state.result[1]=73,74
    ctx.state.results[0],ctx.state.results[1]="kept","other"
    rng=ctx.state.rng.snapshot()
    def assert_unchanged():
        assert (ctx.state.result[0],ctx.state.result[1])==(73,74)
        assert (ctx.state.results[0],ctx.state.results[1])==("kept","other")
        assert ctx.state.rng.snapshot()==rng
    gen=with_achievement_wait(run(),ctx.out)
    assert isinstance(next(gen), WaitInputRequest)  # SCORE:694 PRINTW
    assert not ctx.globals.exists()
    assert_unchanged()
    assert isinstance(gen.send(0), WaitInputRequest)  # SCORE:738 PRINTW
    assert ctx.globals.mem.global_[113]==3
    assert_unchanged()
    assert ctx.globals.mem.global_[101]==0
    assert gen.send(0)=="done"
    assert_unchanged()
    assert ctx.globals.mem.global_[101]==1
    gen.close()
