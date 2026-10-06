"""S64：FIRSTSETTING_CHARA.ERB 原文前態；全新25歲人工模板。"""
from dataclasses import replace

import pytest

from test_body_editor import data, ctx
from eragvt.data.csv_loader import CharaDef
from eragvt.game.character_csv import load_character_csv
from eragvt.game.character_editor import character_editor
from eragvt.game.input_request import WaitInputRequest


SLOTS = (0, 1, 2, 10, 11, 12, 13)


def template(no, *, unique=1, size=333333333333333, callname='人工成年'):
    return CharaDef(no=no, csv_no=no+100, name=f'人工模板{no}', callname=callname,
                    base={**dict.fromkeys(SLOTS, 100), 40:25, 41:25},
                    talent={999:unique, 10:1, 200:1, 201:1},
                    cflag={34:size, 42:300, 240:1, **{60+i:i+1 for i in range(7)}},
                    cstr={204:'25',205:'25',206:'25',32:'1//2//3',33:'4//5//6',34:'7//8//9'})


def install(ctx, *defs):
    ctx.data=replace(ctx.data,charas={d.no:d for d in defs})


def finish(g, value=None):
    with pytest.raises(StopIteration):g.send(value)


def text(ctx):
    return '\n'.join(line.text for line in ctx.out.lines)


@pytest.mark.parametrize('count,maximum', [(0,0),(1,0),(29,0),(30,1),(31,1),(60,2),(61,2)])
def test_page_boundaries_and_empty_last_page(ctx,count,maximum):
    """LOADCSV:1509–1547：最大頁直接整除30，整30筆時仍可到空白末頁。"""
    install(ctx,*(template(i) for i in range(count)),template(999),template(9999),template(-4))
    g=load_character_csv(ctx,1);next(g)
    assert f'Page(0/{maximum})' in text(ctx)
    assert '人工模板999' not in text(ctx)
    for page in range(1,maximum+2):
        ctx.out.clearline(ctx.out.linecount);g.send(-2)
        assert f'Page({min(page,maximum)}/{maximum})' in text(ctx)
    for _ in range(maximum+2):g.send(-1)
    assert f'Page(0/{maximum})' in text(ctx)
    finish(g,99)


@pytest.mark.parametrize('choice', [-3,999,9999,10000,765])
def test_invalid_repaints_without_mutation_or_rng(ctx,choice):
    install(ctx,template(0),template(999),template(9999))
    before=ctx.state.to_json();rng=ctx.state.rng.snapshot()
    ctx.state.result[8]=765;ctx.state.results[0]='字串殘值'
    g=load_character_csv(ctx,1);next(g);g.send(choice)
    assert ctx.state.charas[1].to_json()==before['charas'][1]
    assert ctx.state.rng.snapshot()==rng
    finish(g,99)
    assert ctx.state.result[0]==0 and ctx.state.result[8]==765
    assert ctx.state.results[0]=='字串殘值'


@pytest.mark.parametrize('unique', [0,1])
def test_swap_entire_character_and_reset_base_before_inheritance(ctx,unique):
    """LOADCSV:1561–1606：非固有改NO0再用0的CSV；遺傳只加BASE、不加MAXBASE。"""
    generic=replace(template(0),base={**dict.fromkeys(SLOTS,200),40:25,41:25})
    selected=template(50,unique=unique)
    install(ctx,generic,selected)
    st=ctx.state;old=st.charas[1];master=st.charas[0];other=st.add_chara(ctx.data,0)
    st.target=2;st.assi=1;old.cflag[500]=77;old.juel[0]=88;old.relation[1]=99
    for i in range(5):st.savestr[i]='保留'
    st.result[8]=876;st.results[0]='保留RESULTS'
    rng=st.rng.snapshot()
    g=load_character_csv(ctx,1);next(g)
    assert isinstance(g.send(50),WaitInputRequest)
    c=st.charas[1]
    assert c is not old and c.no==50 and c.abl[0]==0  # PRINTFORMW在CSVFIX之前。
    assert [st.savestr[i] for i in range(5)]==['','','','','保留']
    assert st.result[0]==50
    finish(g)
    assert st.charanum==3 and st.charas[0] is master and st.charas[2] is other
    assert (st.target,st.assi)==(2,1) and c.no==(50 if unique else 0)
    expected=[100]*7 if unique else [200,180,200,200,200,220,240]
    assert [c.maxbase[i] for i in SLOTS]==expected
    assert [c.base[i] for i in SLOTS]==[v+n for n,v in enumerate(expected,1)]
    assert c.cflag[500]==c.juel[0]==c.relation[1]==0
    assert c.abl[ctx.data.index_of('ABL','レベル')]==1
    assert [c.cstr[i] for i in (34,35,36,37)]==['1//2//3','4//5//6','7//8//9','7//8//9']
    assert st.result[0]==0 and st.result[8]==876 and st.results[0]=='保留RESULTS'
    assert st.rng.snapshot()==rng


def test_missing_bases_csvfix_defaults_are_overwritten_by_reset(ctx):
    """CSVFIX:1638–1646的1000/100稍後仍被LOADCSV:1579–1581重設為CSV零。"""
    d=replace(template(20),base={40:25,41:25})
    install(ctx,d)
    g=load_character_csv(ctx,1);next(g);g.send(20);finish(g)
    c=ctx.state.charas[1]
    assert [c.maxbase[i] for i in SLOTS]==[0]*7
    assert [c.base[i] for i in SLOTS]==list(range(1,8))


def test_male_choice_loads_zero_definition_and_can_select_off_page(ctx):
    """LOADCSV:1548–1559：選1必須EXISTCSV(1)，但ADDCHARA的是0。"""
    install(ctx,template(0,unique=0),template(1),template(9998))
    g=load_character_csv(ctx,1);next(g);g.send(1);finish(g)
    c=ctx.state.charas[1]
    assert c.no==0 and c.name=='汎用キャラ(♂)'
    assert c.talent[ctx.data.index_of('TALENT','オトコ')]==1
    g=load_character_csv(ctx,1);next(g);g.send(9998);finish(g)
    assert ctx.state.charas[1].no==9998


def test_cancel_and_reentry_reset_page_preserve_character(ctx):
    install(ctx,*(template(i) for i in range(32)))
    c=ctx.state.charas[1];ctx.state.savestr[0]='保留'
    g=load_character_csv(ctx,1);next(g);g.send(-2);finish(g,99)
    assert ctx.state.charas[1] is c and ctx.state.savestr[0]=='保留'
    ctx.out.clearline(ctx.out.linecount)
    g=load_character_csv(ctx,1);next(g)
    assert 'Page(0/1)' in text(ctx)
    finish(g,99)


def test_template_99_is_listed_but_cancel_takes_precedence(ctx):
    """LOADCSV:1511與1530：清單只排999；即使列99，輸入99仍先取消。"""
    install(ctx,template(99))
    c=ctx.state.charas[1]
    g=load_character_csv(ctx,1);next(g)
    assert '人工模板99' in text(ctx)
    finish(g,99)
    assert ctx.state.charas[1] is c


def test_all_candidates_sorted_by_number_not_csv_filename(ctx):
    install(ctx,*(template(i) for i in reversed(range(61))))
    g=load_character_csv(ctx,1);next(g)
    for page in range(3):
        labels=[part.text for line in ctx.out.lines for part in line.parts
                if part.button is not None and part.button>=0 and '人工模板' in part.text]
        assert len(labels)==(30 if page<2 else 1)
        for label,i in zip(labels,range(30*page,min(61,30*(page+1)))):
            assert f'人工模板{i}' in label
        ctx.out.clearline(ctx.out.linecount)
        if page<2:g.send(-2)
    finish(g,99)


@pytest.mark.parametrize('count,expected',[(2,[[0,1]]),(3,[[0,1],[2]]),(31,[[30]])])
def test_two_columns_odd_tail_and_pagination_buttons(ctx,count,expected):
    """LOADCSV:1516–1528：每兩人一行；翻頁後不足兩人照留，控制鍵值不變。"""
    install(ctx,*(template(i) for i in range(count)))
    g=load_character_csv(ctx,1);next(g)
    if count==31:
        ctx.out.clearline(ctx.out.linecount);g.send(-2)
    rows=[[part.button for part in line.parts if '人工模板' in part.text]
          for line in ctx.out.lines if '人工模板' in line.text]
    assert rows==expected
    buttons=[part.button for line in ctx.out.lines for part in line.parts if part.button is not None]
    assert buttons[-3:]==[-1,-2,99]
    finish(g,99)


@pytest.mark.parametrize('size',[0,333333333333333])
def test_main_named_template_size_default_only_when_missing(ctx,size,monkeypatch):
    """MAIN:326–332：非汎用呼稱只在CFLAG34=0時生成年齡／尺寸，不初始化種族。"""
    d=replace(template(70,size=size),cflag={**template(70,size=size).cflag,240:0})
    install(ctx,template(0),d)
    from eragvt.game import body
    calls=[]
    age,default=body.chara_make_age_setting,body.chara_size_default
    def age_spy(*args):calls.append('age');return age(*args)
    def size_spy(*args):calls.append('size');return default(*args)
    monkeypatch.setattr(body,'chara_make_age_setting',age_spy)
    monkeypatch.setattr(body,'chara_size_default',size_spy)
    g=character_editor(ctx,1);next(g);g.send(999);g.send(70);g.send(None)
    c=ctx.state.charas[1]
    # CHARA_SIZE.ERB:53與CHARA_SIZE_UI.ERB:2158：曲線原值照回寫，0不變成非0。
    assert c.no==70 and c.cflag[34]==size and c.cflag[240]==0
    assert calls==(['age','size'] if size==0 else [])
    assert c.base[40]==c.base[41]==c.maxbase[40]==c.maxbase[41]==25
    assert c.talent[201]==1 and c.cstr[0]==''
    if size:assert c.cflag[34]==size
    finish(g,99)


@pytest.mark.parametrize('distance,style',[(1,'連続'),(2,'7'),(3,'反撃')])
def test_csvfix_decodes_weapon_before_clearing_packed_data(ctx,distance,style):
    """CSVFIX:1659–1670；WEAPON_ARCHIVE.ERB@DECODE_WEAPON_DATA:7–50。"""
    d=template(70)
    d=replace(d,cstr={**d.cstr,14+distance:f'人工裝備////{style}'})
    install(ctx,d)
    g=load_character_csv(ctx,1);next(g);g.send(70);finish(g)
    c=ctx.state.charas[1]
    assert c.cstr[distance+4]=='人工裝備'
    assert c.cdflag[(distance,500)]=={'連続':1,'7':7,'反撃':10}[style]
    assert [c.cstr[i] for i in (15,16,17)]==['','','']


def test_extracted_csv_menu_text_reproducible():
    import runpy
    from pathlib import Path
    root=Path(__file__).parents[1]
    expected=runpy.run_path(str(root/'tools/extract_character_editor.py'))['extract']()
    assert expected==(root/'src/eragvt/game/character_editor_text.py').read_text(encoding='utf-8')


@pytest.mark.parametrize('restricted', [0,1])
def test_main_unique_allowed_medical_restricted_and_bonus_cancel(ctx,restricted):
    """MAIN:321–333：固有仍可999，醫療鎖；每次返回（含取消）加bonus*10。"""
    c=ctx.state.charas[1];c.talent[ctx.data.index_of('TALENT','固有キャラ')]=1
    point=ctx.data.index_of('PALAM','修練P');c.juel[point]=30
    g=character_editor(ctx,1,bonus=3,restricted=restricted);next(g)
    if restricted:
        g.send(999);assert c.juel[point]==30
    else:
        for expected in (60,90):
            g.send(999);g.send(99);assert c.juel[point]==expected
    finish(g,99)


def test_main_reload_bonus_once_and_refresh_character_reference(ctx):
    point=ctx.data.index_of('PALAM','修練P')
    d=replace(template(70),juel={point:50})
    install(ctx,template(0),d)
    g=character_editor(ctx,1,bonus=2);next(g);g.send(999);g.send(70);g.send(None)
    c=ctx.state.charas[1];assert c.no==70 and c.juel[point]==70
    g.send(10)  # 新固有角色必須拒絕，不能沿用舊c的非固有限制。
    finish(g,99)
    assert c.juel[point]==70
    g=character_editor(ctx,1,bonus=2);next(g);finish(g,99)
    assert c.juel[point]==70


@pytest.mark.parametrize('choice',[0,1])
def test_main_generic_load_runs_original_initialize(ctx,choice):
    """MAIN:324–325：CALLNAME汎用キャラ回MASTER_LOOP；不走尺寸捷徑。"""
    g=character_editor(ctx,1);next(g);g.send(999);g.send(choice);g.send(None)
    c=ctx.state.charas[1]
    assert c.callname!='汎用キャラ' and c.cflag[34]!=0
    assert c.base[40]==c.base[41]==25
    assert c.talent[ctx.data.index_of('TALENT','オトコ')]==choice
    finish(g,99)


def test_web_load_wait_cancel_reentry_and_shop(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    from eragvt.web import create_app
    data=replace(data,charas={**data.charas,70:template(70)})
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(64),narration=NullNarrationService())
    client=TestClient(app)
    def send(v):
        r=client.post('/api/input',json={'value':v});assert r.status_code==200
        return r.json()
    for v in (0,0,1,999,-2,-1,70):screen=send(v)
    assert screen['input_kind']=='wait'
    send('');send(999);send(99);send(99);send(1);send(99)
    for v in (1000,1):screen=send(v)
    assert screen['phase']=='shop'
    assert app.state.session.state.charas[1].no==70


def test_recruitment_reads_replaced_character(ctx):
    """TSUIKAYOUSEI_NORMAL:39–40、145–149全都依who讀新角色。"""
    from eragvt.game.recruitment import recruitment_gen
    ctx.data=replace(ctx.data,charas={**ctx.data.charas,70:template(70)})
    count=ctx.state.charanum;target=ctx.state.target
    g=recruitment_gen(ctx);next(g);g.send(0);g.send(999);g.send(70);g.send(None);g.send(99)
    assert ctx.state.result[0]==201
    finish(g,1)
    c=ctx.state.charas[count]
    assert c.no==70 and c.cflag[999]==1 and ctx.state.target==target
