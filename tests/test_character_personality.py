"""S62：FIRSTSETTING_CHARA_SEIKAKU.ERB 原文推導；人工資料均25歲。"""
import pytest

from test_body_editor import data, ctx
from eragvt.state.rng import FixedRng
from eragvt.game.character_personality import personality_setting, random_mental_traits


def prepare(ctx, person=10):
    c=ctx.state.charas[1]
    for i in range(10,29): c.talent[i]=int(i==person)
    for i in range(600,700): c.talent[i]=0
    return c


def finish(gen):
    with pytest.raises(StopIteration): gen.send(200)


@pytest.mark.parametrize('choice',range(19))
def test_all_personalities(ctx,choice):
    """主函式:232–244：清19格後只設選項+10。"""
    c=prepare(ctx);g=personality_setting(ctx,1);next(g);g.send(choice)
    assert [c.talent[i] for i in range(10,29)]==[int(i==choice+10) for i in range(10,29)]
    finish(g)


@pytest.mark.parametrize('choice,slots',[(100,(600,601)),(101,(602,603)),(102,(604,605)),(103,(606,607)),(104,(608,609)),(105,(610,611)),(106,(612,613)),(107,(614,615,625)),(108,(616,617,618,619)),(109,(620,621,622,623,624))])
def test_all_trait_cycles(ctx,choice,slots):
    """主函式:245–414：無→各格→無；互斥群組由原文列出。"""
    c=prepare(ctx);g=personality_setting(ctx,1);next(g)
    for selected in (*slots,None):
        g.send(choice)
        assert [c.talent[i] for i in slots]==[int(i==selected) for i in slots]
    finish(g)


def test_emotionless_clears_and_blocks_traits(ctx):
    """主函式:239–244、245–414；28清600–699，十按鍵皆拒絕。"""
    c=prepare(ctx);c.talent[699]=1
    g=personality_setting(ctx,1);next(g);g.send(18)
    for choice in range(100,110):g.send(choice)
    assert all(c.talent[i]==0 for i in range(600,700))
    finish(g)


def test_limit_reset_invalid_and_reentry(ctx):
    """主函式:192–204、221–225、415–416；計數含未命名699。"""
    c=prepare(ctx)
    for i in (600,602,604,606,699):c.talent[i]=1
    g=personality_setting(ctx,1);next(g);g.send(200);g.send(-1);g.send(300)
    assert all(c.talent[i]==0 for i in range(600,700))
    for q in (100,101,102,103):g.send(q)
    finish(g)
    g=personality_setting(ctx,1);next(g);finish(g)
    assert [c.talent[i] for i in (600,602,604,606)]==[1]*4


def test_csv_reset_and_confirmation_not_compounding(ctx):
    """主函式:14–20、419–444；性格10只改氣力/敏捷/知性。"""
    c=prepare(ctx);slots=(0,1,2,10,11,12,13)
    expected=[ctx.data.charas[c.no].base.get(i,0) for i in slots]
    for i in slots:c.base[i]=c.maxbase[i]=99999
    ctx.state.result[1]=731;ctx.state.results[0]='殘值';ctx.state.target=0
    g=personality_setting(ctx,1);next(g)
    assert [c.base[i] for i in slots]==expected
    finish(g)
    # 原文 SEIKAKU_HOSEI_F:67–83，TIMES先截斷。
    expected[1]=expected[1]*90//100;expected[5]=expected[5]*110//100;expected[6]=expected[6]*120//100
    assert [c.base[i] for i in slots]==expected
    assert [c.maxbase[i] for i in slots]==expected
    assert ctx.state.target==0 and ctx.state.result[0]==0 and ctx.state.result[1]==731
    assert ctx.state.results[0]=='殘值'
    g=personality_setting(ctx,1);next(g);finish(g)
    assert [c.base[i] for i in slots]==expected


@pytest.mark.parametrize('person,male,custom,before,after',[(24,0,'',3,20),(25,0,'',3,11),(10,0,'',20,20),(24,1,'',3,3),(24,0,'私',3,3)])
def test_self_call_rules(ctx,person,male,custom,before,after):
    """主函式:435–441，僅女性空自訂一人稱；其他性格不重置。"""
    c=prepare(ctx,person);c.talent[ctx.data.index_of('TALENT','オトコ')]=male
    c.cstr[4]=custom;c.cflag[8]=before
    g=personality_setting(ctx,1);next(g);finish(g)
    assert c.cflag[8]==after


def test_random_none_and_unrestricted(ctx):
    """主函式:23–31、208–220：進頁19擇，99亦19擇含28。"""
    c=prepare(ctx,0);ctx.state.rng=FixedRng([2,18]);c.talent[600]=1
    g=personality_setting(ctx,1);next(g);assert c.talent[12]==1
    g.send(99);assert c.talent[28]==1 and c.talent[600]==0
    finish(g);assert ctx.state.rng.snapshot()==[]


def test_random_mental_rng_and_shared_pool(ctx):
    """DEFAULT@CHARA_MAKE_STATUS_TALENT_SEIKAKU:1248–1331：8二擇、4擇、6擇、移除。"""
    c=prepare(ctx);ctx.state.rng=FixedRng([0]*13)
    random_mental_traits(ctx,1,3)
    assert [i for i in range(600,700) if c.talent[i]]==[600,602,604]
    assert ctx.state.temp.randchoose[0]==7
    assert ctx.state.rng.snapshot()==[]


def test_random_button_emotionless_still_draws_count(ctx):
    """主函式:226–231先RAND:3；DEFAULT:1240立即返回。"""
    c=prepare(ctx,28);ctx.state.rng=FixedRng([2])
    g=personality_setting(ctx,1);next(g);g.send(999);finish(g)
    assert ctx.state.rng.snapshot()==[]
    assert all(c.talent[i]==0 for i in range(600,700))


class Colors:
    def __init__(self):self.calls=[]
    def run_function(self,ctx,name):
        self.calls.append(name)
        if name.endswith(('_12','_15')):ctx.state.result[0]=0;return True
        return False


def test_kojo_choice_executes_and_excludes_current(ctx):
    """@RAND_CHOOSE_KOJO_SEIKAKU:462–476：實呼叫色函式，排除既有性格。"""
    c=prepare(ctx,12);c.talent[ctx.data.index_of('TALENT','オトコ')]=1
    ctx.narration=Colors();ctx.state.rng=FixedRng([0])
    g=personality_setting(ctx,1);next(g);g.send(98)
    assert c.talent[15]==1 and c.talent[12]==0
    assert ctx.narration.calls==[f'KOJO_1_COLOR_{i}' for i in range(10,29)]*3
    finish(g)


def test_editor_dispatch(ctx):
    """FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:259–263共用真入口。"""
    from eragvt.game.character_editor import character_editor
    prepare(ctx)
    g=character_editor(ctx,1);next(g);g.send(7);g.send(3);g.send(200)
    assert ctx.state.charas[1].talent[13]==1
    with pytest.raises(StopIteration):g.send(99)


def test_trait_buttons_preserve_title_and_disabled_color(ctx):
    """主函式:64–189，HTML按鈕的數值／tooltip／灰色仍可點擊。"""
    from eragvt.game.status_talent import talent_info
    c=prepare(ctx);c.talent[600]=1
    g=personality_setting(ctx,1);next(g)
    part=next(p for line in ctx.out.lines for p in line.parts if p.button==100)
    assert part.title==talent_info(600)
    g.send(18)
    part=next(p for line in ctx.out.lines for p in line.parts if p.button==100)
    assert part.segments[0].color=='#808080'
    finish(g)


@pytest.mark.parametrize('current_only',[False,True])
def test_kojo_empty_candidates_is_engine_rand_error(ctx,current_only):
    """@RAND_CHOOSE_KOJO_SEIKAKU:464、472；Creator.Method.cs:960–970拒RAND:0。"""
    class NoChoice:
        def run_function(self,ctx,name):return current_only and name.endswith('_10')
    prepare(ctx);ctx.narration=NoChoice()
    g=personality_setting(ctx,1);next(g)
    with pytest.raises(ValueError,match='RAND'):g.send(98)


def test_existing_color_execution_failure_not_missing(ctx):
    """TRYCCALLFORM只對缺函式走CATCH；Instraction.Child.cs:2297–2332。"""
    class Broken:
        catalog=None
        def exists(self,name):return True
        def run_function(self,ctx,name):return False
    prepare(ctx);ctx.narration=Broken();ctx.narration.catalog=ctx.narration
    with pytest.raises(RuntimeError,match='存在但無法執行'):next(personality_setting(ctx,1))


def test_random_mental_last_branch_and_count_cap(ctx):
    """DEFAULT:1242、1296–1318；count封頂10，分支逐次抽數。"""
    c=prepare(ctx);ctx.state.rng=FixedRng([1]*16+[0]*10)
    random_mental_traits(ctx,1,99)
    assert [i for i in range(600,700) if c.talent[i]]==[601,603,605,607,609,611,613,615,619,625]
    assert ctx.state.temp.randchoose[0]==0 and ctx.state.rng.snapshot()==[]


@pytest.mark.parametrize('person,count',[(10,0),(28,3)])
def test_random_mental_early_return_keeps_pool(ctx,person,count):
    prepare(ctx,person);ctx.state.rng=FixedRng([]);ctx.state.temp.randchoose[0]=2
    random_mental_traits(ctx,1,count)
    assert ctx.state.temp.randchoose[0]==2


def test_random_button_draw_order(ctx):
    """主函式:230先RAND:3再呼叫，抽3項；不是讓共用生成函式自己抽數。"""
    c=prepare(ctx);c.talent[699]=1;ctx.state.rng=FixedRng([2]+[0]*13)
    g=personality_setting(ctx,1);next(g);g.send(999);finish(g)
    assert [i for i in range(600,700) if c.talent[i]]==[600,602,604]
    assert ctx.state.rng.snapshot()==[]


def test_first_active_trait_wins_and_normalizes_group(ctx):
    """主函式:246–255，前態同時有兩項仍按第一個IF分支。"""
    c=prepare(ctx);c.talent[600]=c.talent[601]=2
    g=personality_setting(ctx,1);next(g);g.send(100)
    assert (c.talent[600],c.talent[601])==(0,1)
    finish(g)


def test_web_editor_tooltip_confirm_reenter_shop(data,tmp_path):
    """主入口:259–263、子頁:198–244，真GameSession與HTML邊界。"""
    from fastapi.testclient import TestClient
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(62),narration=NullNarrationService())
    client=TestClient(app)
    def send(value):
        response=client.post('/api/input',json={'value':value});assert response.status_code==200
        return response.json()
    for value in (0,1,1,7,0,300,100):send(value)
    html=client.get('/').text
    from eragvt.game.status_talent import talent_info
    assert 'value="100" title="'+talent_info(600)+'"' in html
    send(200);send(7)
    c=app.state.session.state.charas[1]
    assert c.talent[10]==c.talent[600]==1 and c.base[40]==c.base[41]==25
    for value in (200,99,1000,1,0):screen=send(value)
    assert screen['phase']=='shop'


def test_real_color_catalog_side_effect_and_rng(ctx):
    """S54已查KOJO_0_COLOR_16:24–34會清原有文字變數；S62每次繪頁實呼叫。"""
    from eragvt.narration.service import CatalogNarrationService
    from eragvt.data import default_csv_dir
    c=prepare(ctx);c.talent[ctx.data.index_of('TALENT','オトコ')]=0
    ctx.narration=CatalogNarrationService.from_csv_dir(default_csv_dir(),ctx.data)
    key=('真面目_フラグ_シチュ',(0,));ctx.state.temp.narr[key]='殘值'
    before=ctx.state.rng.snapshot()
    g=personality_setting(ctx,1);next(g)
    assert ctx.state.temp.narr[key]=='' and ctx.narration.failures==[]
    assert ctx.state.rng.snapshot()==before
    finish(g)


def test_confirmation_recalculates_shields(ctx):
    """主函式:444→コモン関数.ERB@BASEUP_CAL_SHIELD:638–648、@CAL_SHIELD_F:653–656。"""
    from math import isqrt
    c=prepare(ctx);c.talent[190]=1;c.maxbase[30]=1;c.base[30]=1
    c.abl[ctx.data.index_of('ABL','レベル')]=1
    g=personality_setting(ctx,1);next(g);finish(g)
    b=ctx.data.charas[c.no].base
    expected=isqrt((b.get(1,0)*90//100)*b.get(2,0)*b.get(11,0)**2//160)//2+2500
    assert c.base[30]==c.maxbase[30]==expected
