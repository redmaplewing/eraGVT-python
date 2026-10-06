"""S65：FIRSTSETTING_CHARA_SEX原文前態；全新25歲人工角色。"""
import pytest

from test_body_editor import data, ctx
from eragvt.game.character_editor import character_editor
from eragvt.game.character_sex import sex_setting


def slot(ctx, name):
    return ctx.data.index_of('TALENT', name)


def done(g, value=1):
    with pytest.raises(StopIteration):
        g.send(value)


@pytest.mark.parametrize('trans,choice,male,ts', [(1,0,0,0),(1,1,0,1),(1,2,1,0),(1,3,1,1),(0,0,0,1),(-1,2,1,1)])
def test_choices_confirm_and_profile(ctx,trans,choice,male,ts):
    """SEX:371–375、391–402、442–465；無變身能力不清既有TS。"""
    c=ctx.state.charas[1];c.talent[slot(ctx,'変身能力')]=trans
    c.talent[slot(ctx,'変身時ＴＳ')]=1
    c.talent[slot(ctx,'オトコ')]=1-male
    for name in ('男の娘','変身時男の娘','ふたなり','変身時ふたなり'):
        c.talent[slot(ctx,name)]=1
    old_rng=ctx.state.rng.snapshot();ctx.state.target=0
    g=sex_setting(ctx,1);next(g);g.send(choice)
    assert c.talent[slot(ctx,'オトコ')]==1-male
    done(g)
    assert c.talent[slot(ctx,'オトコ')]==male and c.talent[slot(ctx,'変身時ＴＳ')]==ts
    assert all(c.talent[slot(ctx,n)]==0 for n in ('男の娘','変身時男の娘','ふたなり','変身時ふたなり'))
    assert c.base[40]==c.base[41]==c.maxbase[40]==c.maxbase[41]==25
    assert ctx.state.target==0 and ctx.state.rng.snapshot()==old_rng
    height=ctx.data.index_of('BASE','身長')
    assert ctx.state.result[0]==0 and c.base[height]>0 and c.maxbase[height]>0


@pytest.mark.parametrize('choice,retained', [(0,True),(1,False),(2,False),(3,True)])
def test_shape_change_reset_conditions(ctx,choice,retained):
    """SEX:397–402、461–466：女且TS、男且非TS時清形態差；女性總清兩感度差。"""
    c=ctx.state.charas[1]
    for n in ('変身時胸サイズ変動','変身時外見','変身時濡れやすさ変動','変身時Ｖ感覚変動'):
        c.talent[slot(ctx,n)]=2
    g=sex_setting(ctx,1);next(g);g.send(choice);done(g)
    assert c.talent[slot(ctx,'変身時胸サイズ変動')]==(2 if retained else 0)
    assert c.talent[slot(ctx,'変身時外見')]==(2 if retained else 0)
    for n in ('変身時濡れやすさ変動','変身時Ｖ感覚変動'):
        assert c.talent[slot(ctx,n)]==(2 if choice==3 else 0)


@pytest.mark.parametrize('choice,locked,unique', [(v,l,u) for v in (0,2) for l,u in ((0,0),(1,0),(0,1))])
def test_barrier_refund_and_experience_reset(ctx,choice,locked,unique):
    """SEX:404–416、469–482：每個非零結界還50，193含194不含；鎖定不清EXP。"""
    c=ctx.state.charas[1];point=ctx.data.index_of('PALAM','修練P');c.juel[point]=7
    for i,v in ((190,1),(191,0),(192,-2),(193,3),(194,9)):c.talent[i]=v
    c.talent[slot(ctx,'避妊結界')]=1
    c.talent[slot(ctx,'初期経験設定不可')]=locked;c.talent[slot(ctx,'固有キャラ')]=unique
    keys=[ctx.data.index_of('EXP',n) for n in ('射精経験','Ｖ経験','出産経験')]
    for k in keys:c.exp[k]=17
    g=sex_setting(ctx,1);next(g);g.send(choice);done(g)
    assert c.juel[point]==207 and [c.talent[i] for i in range(190,195)]==[0,0,0,0,9]
    assert c.talent[slot(ctx,'避妊結界')]==0
    expected=([0,17,17] if choice==0 else [17,0,0]) if not locked and not unique else [17]*3
    assert [c.exp[k] for k in keys]==expected
    g=sex_setting(ctx,1);next(g);g.send(choice);done(g)
    assert c.juel[point]==207


@pytest.mark.parametrize('partner,expected', [(0,0),(1,1),(2,0),(3,3),(4,0),(5,0),(6,6)])
def test_male_cleanup_partner_and_traits(ctx,partner,expected):
    c=ctx.state.charas[1];c.talent[slot(ctx,'交際相手')]=partner
    names=('処女','母乳体質','パイパン','Ｖ敏感','Ｖ鈍感','貧乳','巨乳','濡れやすい','濡れにくい','苗床化','アクセサリ','外見')
    for n in names:c.talent[slot(ctx,n)]=1
    g=sex_setting(ctx,1);next(g);g.send(2);done(g)
    assert all(c.talent[slot(ctx,n)]==0 for n in names)
    assert c.talent[slot(ctx,'交際相手')]==expected


def test_cancel_keeps_early_ts_mutation_and_invalid_confirmation(ctx):
    """SEX:371–374早於確認；否只重入，不回滾TS或退出。"""
    c=ctx.state.charas[1];c.talent[slot(ctx,'オトコ')]=0;c.talent[slot(ctx,'変身時ＴＳ')]=0
    before=c.to_json();g=sex_setting(ctx,1);next(g);g.send(3)
    assert c.talent[slot(ctx,'変身時ＴＳ')]==1
    g.send(9);assert c.talent[slot(ctx,'オトコ')]==0
    g.send(0);assert c.talent[slot(ctx,'変身時ＴＳ')]==1
    assert c.base.to_json()==before['base']
    g.send(0);done(g)
    assert c.talent[slot(ctx,'変身時ＴＳ')]==0


@pytest.mark.parametrize('trans', [0,-1,2])
def test_hidden_ts_rejected_without_transform_ability(ctx,trans):
    c=ctx.state.charas[1];c.talent[slot(ctx,'変身能力')]=trans
    g=sex_setting(ctx,1);next(g)
    for bad in (1,3,99,-5):
        before=c.to_json();g.send(bad);assert c.to_json()==before
    g.send(0);done(g)


def test_shared_results_side_effects(ctx):
    """SET_PROFILE保留GENERATE_CHAR_SIZE的RESULT1–7；自然終端只覆寫0。"""
    st=ctx.state;st.result[8]=876;st.results[0]='字串殘值';st.results[1]='保留'
    g=sex_setting(ctx,1);next(g);g.send(2);done(g)
    c=st.charas[1]
    assert st.result[0]==0 and st.result[8]==876 and st.results[0]=='―' and st.results[1]=='保留'
    slots=[ctx.data.index_of('BASE',n) for n in ('身長','体重','胸囲','胴囲','腰囲','胸の重量')]
    assert [st.result[i] for i in range(2,8)]==[c.maxbase[i] for i in slots]


@pytest.mark.parametrize('unique,restricted', [(0,0),(0,1),(1,0),(1,1)])
def test_main_hidden_entry_and_restrictions(ctx,unique,restricted):
    c=ctx.state.charas[1];c.talent[slot(ctx,'固有キャラ')]=unique
    g=character_editor(ctx,1,restricted=restricted);next(g);g.send(0)
    if not unique:
        g.send(2);g.send(1);assert c.talent[slot(ctx,'オトコ')]==1
        g.send(0);g.send(0);g.send(1);assert c.talent[slot(ctx,'オトコ')]==0
    done(g,99)


def test_web_hidden_entry_cancel_reentry_and_shop(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.state import GameRng
    from eragvt.text import NullNarrationService
    from eragvt.web import create_app
    app=create_app(data,tmp_path,rng_factory=lambda:GameRng(65),narration=NullNarrationService())
    client=TestClient(app)
    def send(v):
        response=client.post('/api/input',json={'value':v});assert response.status_code==200
        return response.json()
    for v in (0,0,1,0,3,0,2,1,0,0,1,99,1,99,1000,1):screen=send(v)
    assert screen['phase']=='shop'
