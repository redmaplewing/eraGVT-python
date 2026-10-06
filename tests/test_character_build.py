"""S63：三個 FIRSTSETTING 函式的原文前態／expected；人工25歲資料。"""
from dataclasses import replace
import pytest

from test_body_editor import data, ctx
from eragvt.state.rng import FixedRng
from eragvt.game.character_build import race_setting, transformation_setting, status_bonus
from eragvt.game.character_editor import character_editor
from eragvt.game.input_request import WaitInputRequest


def end(g, value, expected=0):
    with pytest.raises(StopIteration) as stop:g.send(value)
    assert stop.value.value==expected


def clear(ctx):
    c=ctx.state.charas[1]
    for i in range(190,250):c.talent[i]=0
    for i in range(1100,1300):c.talent[i]=0
    return c


@pytest.mark.parametrize('race', range(12))
def test_race_choices_and_hidden_11(ctx,race):
    """SYUZOKU:36–43、115–120；接受11，但只清201–211。"""
    c=clear(ctx);c.talent[201]=1;c.talent[212]=1
    c.talent[ctx.data.index_of('TALENT','オトコ')]=1
    c.talent[ctx.data.index_of('TALENT','口上設定')]=1
    g=race_setting(ctx,1);next(g);g.send(-1);g.send(12);g.send(race)
    end(g,0)
    assert [c.talent[i] for i in range(201,212)]==[int(i==race+201) for i in range(201,212)]
    assert c.talent[212]==1
    assert c.talent[1110]==int(race==9)
    assert ctx.state.result[0]==0


def test_race_cancel_limit_fixed_and_incompatible_feats(ctx):
    """SYUZOKU:16–21、44–60、92–111、151–160。取消重讀角色原有feat。"""
    c=clear(ctx);c.talent[201]=1;c.talent[1100]=1
    g=race_setting(ctx,1);next(g);g.send(0);g.send(100);g.send(1)
    assert c.talent[1100]==1
    g.send(9);g.send(110)  # 固定feat無法關閉。
    for q in (203,204,216):g.send(q)
    g.send(0)  # 四項不能確定。
    assert c.talent[201]==1
    g.send(216);end(g,0)
    assert c.talent[1100]==0 and c.talent[1110]==1
    assert sum(c.talent[i]>0 for i in range(1100,1300))==3


@pytest.mark.parametrize('preg,kojo',[(0,0),(0,1),(1,0),(1,1)])
def test_robot_followups(ctx,preg,kojo):
    """SYUZOKU:122–149：兩個獨立輸入；口上1直接略過第二題。"""
    c=clear(ctx);c.talent[ctx.data.index_of('TALENT','オトコ')]=0
    k=ctx.data.index_of('TALENT','口上設定');c.talent[k]=0
    g=race_setting(ctx,1);next(g);g.send(3);g.send(0);g.send(9);g.send(preg);end(g,kojo)
    assert c.talent[ctx.data.index_of('TALENT','未熟')]==preg*2
    assert c.talent[k]==int(kojo==0)


def test_robot_invalid_kojo_returns_to_pregnancy_input(ctx):
    """SYUZOKU:149原作跳INPUT_LOOP_1，不自行修成INPUT_LOOP_2。"""
    c=clear(ctx);c.talent[ctx.data.index_of('TALENT','オトコ')]=0
    c.talent[ctx.data.index_of('TALENT','口上設定')]=0
    g=race_setting(ctx,1);next(g);g.send(3);g.send(0);g.send(0);g.send(9);g.send(1);end(g,1)
    assert c.talent[ctx.data.index_of('TALENT','未熟')]==2


@pytest.mark.parametrize('choice,csv,expected',[(0,-2,0),(0,8,5),(1,3,3),(2,3,2),(2,0,0)])
def test_transformation_csv_dash_and_wait(ctx,choice,csv,expected):
    """TRANSFORMATION:11–65：直接CSV值、清TS在尺寸生成後；PRINTW不寫RESULTS。"""
    c=ctx.state.charas[1];d=ctx.data.charas[c.no]
    ctx.data=replace(ctx.data,charas={**ctx.data.charas,c.no:replace(d,base={**d.base,22:csv})})
    ts=ctx.data.index_of('TALENT','変身時ＴＳ');c.talent[ts]=1
    c.base[22]=c.maxbase[22]=99;ctx.state.result[8]=321;ctx.state.results[1]='tail'
    g=transformation_setting(ctx,1);next(g);g.send(-1);g.send(3)
    assert isinstance(g.send(choice),WaitInputRequest)
    assert c.talent[200]==(1,0,-1)[choice]
    assert c.base[22]==c.maxbase[22]==expected
    assert c.talent[ts]==int(choice==0)
    before=ctx.state.results[0];end(g,None)
    assert ctx.state.results[0]==before and ctx.state.results[1]=='tail'
    assert ctx.state.result[0]==0 and ctx.state.result[8]==321


@pytest.mark.parametrize('slot',range(7))
@pytest.mark.parametrize('choice,expected',[(0,-5),(1,-1),(2,1),(3,5)])
def test_seven_bonus_controls(ctx,slot,choice,expected):
    """STATUS_BONUS:602–626：只在200儲存CFLAG，不直接改BASE。"""
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P');c.juel[p]=1000
    before=c.base.copy();g=status_bonus(ctx,1);next(g);g.send(slot*10+choice)
    assert c.cflag[50+slot]==0 and c.juel[p]==1000-expected*10
    end(g,200,1)
    assert c.cflag[50+slot]==expected and c.base.copy()==before


@pytest.mark.parametrize('child,start,points,choice,expected,left',[
    (0,39,100,3,40,90),(1,19,100,3,20,90),(0,-19,0,0,-20,10),
    (0,0,29,3,2,9),(0,0,-20,2,-2,0),(0,42,0,2,40,20),
])
def test_bonus_clamps_in_original_order(ctx,child,start,points,choice,expected,left):
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P')
    c.cflag[231]=child;c.cflag[50]=start;c.juel[p]=points
    g=status_bonus(ctx,1);next(g);g.send(choice);end(g,200,1)
    assert c.cflag[50]==expected and c.juel[p]==left


@pytest.mark.parametrize('group,good,bad',[(70,'近距離得意','近距離苦手'),(80,'中距離得意','中距離苦手'),(90,'遠距離得意','遠距離苦手'),(100,'空中得意','空中苦手'),(110,'回復早い','回復遅い')])
def test_trait_purchase_refund_cycles(ctx,group,good,bad):
    """STATUS_BONUS:627–820；差額 -5/0/15、資金不足不改。"""
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P');c.juel[p]=149
    good,bad=(ctx.data.index_of('TALENT',s) for s in (good,bad))
    c.talent[good]=c.talent[bad]=0
    g=status_bonus(ctx,1);next(g);g.send(group+2)
    assert c.juel[p]==149 and c.talent[good]==0
    g.send(group);assert c.juel[p]==199 and c.talent[bad]==1
    g.send(group+1);assert c.juel[p]==149 and c.talent[bad]==0
    c.juel[p]=150;g.send(group+2);assert c.juel[p]==0 and c.talent[good]==1
    g.send(group);assert c.juel[p]==200 and c.talent[bad]==1 and c.talent[good]==0
    g.send(group+2);g.send(group+1);assert c.juel[p]==150 and c.talent[good]==0
    end(g,200,1)


@pytest.mark.parametrize('group,name,prices',[(120,'噂好きの友人',(0,50)),(130,'警察関係者',(0,100,200)),(140,'情報屋',(0,150)),(150,'裕福な実家',(0,100))])
def test_connection_all_levels(ctx,group,name,prices):
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P');t=ctx.data.index_of('TALENT',name)
    c.talent[t]=0;c.juel[p]=prices[-1]-1
    g=status_bonus(ctx,1);next(g);g.send(group+len(prices)-1)
    assert c.talent[t]==0
    c.juel[p]=300
    for value in (*range(len(prices)),*reversed(range(len(prices)))):
        g.send(group+value);assert c.talent[t]==value and c.juel[p]==300-prices[value]
    end(g,200,1)


@pytest.mark.parametrize('name,level,expected,buttons',[
    ('噂好きの友人',0,'噂好きの友人（+ 0）',('[120] なし','[121] ＋１')),
    ('噂好きの友人',1,'噂好きの友人（+ 5）',('[120] なし','[121] ＋１')),
    ('警察関係者',0,'警察関係者　（+ 0）',('[130] なし','[131] ＋１','[132] ＋２')),
    ('警察関係者',1,'警察関係者　（+10）',('[130] なし','[131] ＋１','[132] ＋２')),
    ('警察関係者',2,'警察上層部　（+20）',('[130] なし','[131] ＋１','[132] ＋２')),
    ('情報屋',0,'情報屋　　　（+ 0）',('[140] なし','[141] ＋１')),
    ('情報屋',1,'情報屋　　　（+15）',('[140] なし','[141] ＋１')),
    ('裕福な実家',0,'裕福な実家　（+ 0）',('[150] なし','[151] ＋１')),
    ('裕福な実家',1,'裕福な実家　（+10）',('[150] なし','[151] ＋１')),
])
def test_connection_display_original_names_costs_and_digits(ctx,name,level,expected,buttons):
    """ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_STATUS_BONUS.ERB@FIRSTSETTING_STATUS_BONUS:379–474。"""
    c=ctx.state.charas[1];c.talent[ctx.data.index_of('TALENT',name)]=level
    g=status_bonus(ctx,1);next(g)
    text=''.join(part.text for line in ctx.out.lines for part in line.parts)
    assert expected in text
    assert all(button in text for button in buttons)
    end(g,200,1)


@pytest.mark.parametrize('male,ts,limit',[(0,0,3),(1,0,2),(0,1,2),(1,1,2)])
def test_shield_limit_and_exclusion(ctx,male,ts,limit):
    """STATUS_BONUS:584–601／DIM.ERH:154：上限3或2、V與避妊互斥。"""
    c=clear(ctx);p=ctx.data.index_of('PALAM','修練P');c.juel[p]=500
    c.talent[200]=1;c.talent[ctx.data.index_of('TALENT','オトコ')]=male
    c.talent[ctx.data.index_of('TALENT','変身時ＴＳ')]=ts
    birth=ctx.data.index_of('TALENT','避妊結界')
    g=status_bonus(ctx,1);next(g);g.send(304);g.send(301)
    assert c.talent[birth]==1 and c.talent[191]==0
    for q in (300,302,303):g.send(q)
    assert sum(c.talent[i] for i in (190,191,192,193,birth))==limit
    g.send(304);g.send(301);g.send(304)
    assert c.talent[birth]==0 and c.talent[191]==1
    end(g,200,1)


def test_reset_preserves_birth_shield_random_exceeds_cap_and_reentry(ctx):
    """STATUS_BONUS:501–583不清避妊結界；末段999不套上下限且FOR終值只讀一次。"""
    c=clear(ctx);p=ctx.data.index_of('PALAM','修練P');birth=ctx.data.index_of('TALENT','避妊結界')
    c.talent[birth]=1;c.talent[190]=1;c.cflag[50]=-5;c.juel[p]=19
    g=status_bonus(ctx,1);next(g);g.send(201)
    assert c.juel[p]==19 and c.talent[birth]==1 and c.talent[190]==0
    c.juel[p]=419;ctx.state.rng=FixedRng([0]*41);g.send(999);end(g,200,1)
    assert c.cflag[50]==41 and c.juel[p]==9 and ctx.state.rng.snapshot()==[]
    g=status_bonus(ctx,1);next(g);g.send(-1);g.send(4);end(g,200,1)
    assert c.cflag[50]==41 and c.juel[p]==9


@pytest.mark.parametrize('restricted', [0,1])
def test_editor_bonus_and_gates(ctx,restricted):
    """MAIN:249、271、310：獎勵參數只給999讀CSV用，23不再加；限制只擋種族。"""
    c=clear(ctx);p=ctx.data.index_of('PALAM','修練P');c.juel[p]=123
    c.talent[ctx.data.index_of('TALENT','固有キャラ')]=0
    g=character_editor(ctx,1,bonus=99,restricted=restricted);next(g)
    if restricted:g.send(4)
    else:g.send(4);g.send(0);g.send(0)
    g.send(10);g.send(1);g.send(None)
    g.send(23);g.send(2);g.send(200);end(g,99)
    assert c.juel[p]==113 and c.cflag[50]==1


def test_missing_csv_is_error(ctx):
    """CSVBASE_F:966–969→reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1383–1418。"""
    c=ctx.state.charas[1];c.no=999999
    g=transformation_setting(ctx,1);next(g)
    with pytest.raises((KeyError,NotImplementedError)):g.send(0)


def test_missing_dash_field_is_zero(ctx):
    c=ctx.state.charas[1];definition=ctx.data.charas[c.no]
    ctx.data=replace(ctx.data,charas={**ctx.data.charas,c.no:replace(definition,base={k:v for k,v in definition.base.items() if k!=22})})
    g=transformation_setting(ctx,1);next(g);g.send(0);end(g,None)
    assert c.base[22]==c.maxbase[22]==0


def test_transformation_generates_size_before_clearing_ts(ctx):
    """TRANSFORMATION:32–39：女性有TS，產生男性尺寸後才清TS；不重新生成。"""
    c=ctx.state.charas[1];c.talent[ctx.data.index_of('TALENT','オトコ')]=0
    c.talent[ctx.data.index_of('TALENT','変身時ＴＳ')]=1
    c.talent[ctx.data.index_of('TALENT','変身時男の娘')]=0
    g=transformation_setting(ctx,1);next(g);g.send(1)
    assert [c.maxbase[i] for i in (45,46,47)]==[-1,-1,-1]
    assert c.talent[ctx.data.index_of('TALENT','変身時ＴＳ')]==0
    end(g,None)


def test_random_accumulates_on_existing_bonus(ctx):
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P')
    c.cflag[50]=40;c.cflag[51]=-2;c.juel[p]=37;ctx.state.rng=FixedRng([0,1,6])
    g=status_bonus(ctx,1);next(g);g.send(999);end(g,200,1)
    assert [c.cflag[50+i] for i in range(7)]==[41,-1,0,0,0,0,1]
    assert c.juel[p]==7 and ctx.state.rng.snapshot()==[]


def test_shield_insufficient_points_and_no_bonus_redraw_accumulation(ctx):
    c=clear(ctx);p=ctx.data.index_of('PALAM','修練P');c.juel[p]=49
    g=status_bonus(ctx,1);next(g);count=ctx.out.linecount
    for q in (300,301,302,303,304,305,-1):
        g.send(q);assert ctx.out.linecount==count
    assert all(c.talent[i]==0 for i in (190,191,192,193,303)) and c.juel[p]==49
    end(g,200,1)


@pytest.mark.parametrize('race,feats',[
    (0,(100,101,200,201,209,210)),(1,(102,200,202,207,214,215)),
    (2,(103,201,205,208,212,213)),(3,(104,203,205,207,208,211)),
    (4,(105,204,205,209,213,217)),(5,(106,204,202,210,214,217)),
    (6,(107,202,203,210,211,212)),(7,(108,206,212,213,215,216)),
    (8,(109,206,211,214,215,218)),(9,(110,203,204,216,217,218)),
    (10,(104,203,205,207,208,211)),
])
def test_all_available_feats_toggle_and_exclude_others(ctx,race,feats):
    """CHARA_SYUZOKU.ERB@FEAT_ABLE_F:92–239逐種六項；全部可關再開（固定110例外）。"""
    c=clear(ctx);c.talent[ctx.data.index_of('TALENT','オトコ')]=1
    c.talent[ctx.data.index_of('TALENT','口上設定')]=1
    for feat in feats:
        for i in range(1100,1300):c.talent[i]=0
        g=race_setting(ctx,1);next(g);g.send(race)
        for q in (99,300,-1,999):g.send(q)
        for _ in range(3):g.send(feat)
        end(g,0)
        assert {i-1000 for i in range(1100,1300) if c.talent[i]}=={feat}|({110} if race==9 else set())


def test_bonus_reset_all_fields_and_preserve_base_target_results(ctx):
    """STATUS_BONUS:501–583：同時有得意／苦手仍各自扣還；RESULT其他格不變。"""
    c=clear(ctx);p=ctx.data.index_of('PALAM','修練P')
    names=('近距離得意','近距離苦手','中距離得意','中距離苦手','遠距離得意','遠距離苦手','空中得意','空中苦手','回復早い','回復遅い','噂好きの友人','警察関係者','情報屋','裕福な実家')
    for n in names:c.talent[ctx.data.index_of('TALENT',n)]=2 if n=='警察関係者' else 1
    c.juel[p]=0
    for i in range(7):c.cflag[50+i]=i-3
    st=ctx.state;st.result[1]=888;st.results[0]='keep';st.target=0
    before=c.base.copy();g=status_bonus(ctx,1);next(g);g.send(201);end(g,200,1)
    assert c.juel[p]==1000 and all(c.cflag[50+i]==0 for i in range(7))
    assert all(c.talent[ctx.data.index_of('TALENT',n)]==0 for n in names)
    assert c.base==before and st.target==0 and st.result[1]==888 and st.results[0]=='keep'


def test_no_edit_bonus_preserves_stored_values_and_rng(ctx):
    c=ctx.state.charas[1];p=ctx.data.index_of('PALAM','修練P');c.juel[p]=777
    c.cflag[50]=-4;c.cflag[51]=9;ctx.state.rng=FixedRng([])
    g=status_bonus(ctx,1);next(g);end(g,200,1)
    assert c.cflag[50]==-4 and c.cflag[51]==9 and c.juel[p]==777


def test_debug_reads_target_not_editor_subject(ctx):
    """STATUS_BONUS:33–91：每個TIMES截斷；三個得意同時套補正。"""
    ctx.state.flag[999]=1;ctx.state.target=0;c=ctx.state.charas[0]
    for n in ('近距離得意','中距離得意','遠距離得意'):c.talent[ctx.data.index_of('TALENT',n)]=1
    for n in ('近距離苦手','中距離苦手','遠距離苦手'):c.talent[ctx.data.index_of('TALENT',n)]=0
    g=status_bonus(ctx,1);next(g)
    text=''.join(p.text for line in ctx.out.lines for p in line.parts)
    assert '近距離性能：250' in text and '中距離性能：245' in text and '遠距離性能：240' in text
    end(g,200,1)


def test_real_race_catalog_and_failure_is_not_null_fallback(ctx):
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.data import default_csv_dir
    c=clear(ctx);ctx.narration=CatalogNarrationService.from_csv_dir(default_csv_dir(),ctx.data)
    before=ctx.state.rng.snapshot()
    g=race_setting(ctx,1);next(g);g.send(0);g.send(100);end(g,0)
    assert ctx.narration.failures==[] and ctx.state.rng.snapshot()==before
    class Missing:
        def run_function(self,*a):return False
        def exists(self,*a):return False
    ctx.narration=Missing();ctx.narration.catalog=ctx.narration
    g=race_setting(ctx,1);next(g)
    with pytest.raises(RuntimeError,match='SYUZOKU_INFO'):g.send(0)


def test_unique_character_still_has_bonus_but_not_race_or_ability(ctx):
    c=ctx.state.charas[1];c.talent[ctx.data.index_of('TALENT','固有キャラ')]=1
    p=ctx.data.index_of('PALAM','修練P');c.juel[p]=10
    g=character_editor(ctx,1);next(g);count=ctx.out.linecount
    g.send(4);g.send(10);assert ctx.out.linecount==count
    g.send(23);g.send(2);g.send(200);end(g,99)
    assert c.cflag[50]==1 and c.juel[p]==0


def test_web_three_menus_wait_reentry_and_shop(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(63),narration=NullNarrationService())
    client=TestClient(app)
    def send(value):
        r=client.post('/api/input',json={'value':value});assert r.status_code==200
        return r.json()
    for v in (0,0,1,4,11,0,4,0,100,0,10,2):screen=send(v)
    assert screen['input_kind']=='wait'
    send('');send(23);send(201);send(0);send(200)
    c=app.state.session.state.charas[1]
    assert c.talent[201]==1 and c.talent[1100]==1 and c.talent[200]==-1 and c.cflag[50]==-5
    send(23);send(200);send(10);send(0);send('')
    for v in (99,1000,1):screen=send(v)
    assert screen['phase']=='shop' and c.base[40]==c.base[41]==25


def test_extract_build_text_reproducible():
    import runpy
    from pathlib import Path
    root=Path(__file__).parents[1]
    assert runpy.run_path(str(root/'tools/extract_character_build.py'))['extract']()==(root/'src/eragvt/game/character_build_text.py').read_text(encoding='utf-8')
