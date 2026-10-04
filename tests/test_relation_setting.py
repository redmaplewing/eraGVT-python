"""S51 expected：CHARA_RELATION.ERB@SET_RELATION:189–553；開局:659–752。"""
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first
from eragvt.state import GameState, GameRng
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game import relation_setting as rs

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

@pytest.fixture
def ctx(data):
    st = GameState.new(data, GameRng(3))
    event_first(st, data)
    for i, c in enumerate(st.charas):
        c.relation.clear()
        c.base[40] = 20 + i
        c.cflag[240] = i + 1
        c.talent[data.index_of("TALENT", "処女")] = 0
    return Ctx(st, data, TextOutput(), NullNarrationService())

def drive(g, values):
    next(g)
    for value in values:
        try:
            g.send(value)
        except StopIteration as e:
            return e.value
    raise AssertionError("仍等待輸入")

@pytest.mark.parametrize("bit,reverse", [(2,0),(3,0),(4,0),(5,0),(20,20),(21,21),(22,22),(23,24),(24,23),(25,25),(30,0),(31,0),(32,32),(33,33),(34,34),(41,40),(42,40)])
def test_bit_direction(ctx, bit, reverse):
    drive(rs.set_relation(ctx, 1, 2), [bit, 200, ""])
    assert ctx.state.charas[1].relation[2] == 1 << bit
    assert ctx.state.charas[2].relation[1] == (1 << reverse if reverse else 0)
    assert ctx.state.result[0] == 0

@pytest.mark.parametrize("bit", [1,6])
def test_family_requirement(ctx, bit):
    g = rs.set_relation(ctx, 1, 2)
    next(g); g.send(bit); g.send(200)
    assert ctx.state.charas[1].relation[2] == 0
    g.send(25); g.send(200)
    with pytest.raises(StopIteration): g.send("")
    assert ctx.state.charas[2].relation[1] == (1 << 25) | (1 << bit)

@pytest.mark.parametrize("group", [(23,24),(31,32,33,34),(40,41,42)])
def test_exclusion(ctx, group):
    # :516–550 即使把所選位元關閉，也會清其他互斥位元。
    for chosen in group:
        ctx.state.charas[1].relation[2] = sum(1 << b for b in group)
        drive(rs.set_relation(ctx, 1, 2), [chosen, 200, ""])
        assert ctx.state.charas[1].relation[2] == 0

@pytest.mark.parametrize("reverse,choice,expected", [(0,41,1<<41),(1<<41,42,(1<<41)|(1<<42)),(1<<42,41,(1<<41)|(1<<42))])
def test_master_reverse_or_preserved(ctx, reverse, choice, expected):
    ctx.state.charas[2].relation[1] = reverse
    drive(rs.set_relation(ctx, 1, 2), [40,200,0,99,choice,""])
    assert ctx.state.charas[2].relation[1] == expected


def test_master_both_reverse_skips_input(ctx):
    ctx.state.charas[2].relation[1] = (1<<41)|(1<<42)
    drive(rs.set_relation(ctx, 1, 2), [40,200,""])


def test_cancel_and_reentry(ctx):
    ctx.state.charas[1].relation[2] = 1<<30
    drive(rs.set_relation(ctx,1,2), [32,-1,0,7,19,26,35,43,998,999])
    assert ctx.state.charas[1].relation[2] == 1<<30
    drive(rs.set_relation(ctx,1,2), [200,""])
    assert ctx.state.charas[1].relation[2] == 1<<30

@pytest.mark.parametrize("older", [1,2])
@pytest.mark.parametrize("bit", [20,22])
@pytest.mark.parametrize("unique", [0,1])
def test_parent_virgin_validation(ctx, older, bit, unique):
    c = ctx.state.charas[older]
    c.base[40] = 50
    c.talent[ctx.data.index_of("TALENT","オトコ")] = 0
    c.talent[ctx.data.index_of("TALENT","処女")] = 1
    c.talent[ctx.data.index_of("TALENT","固有キャラ")] = unique
    g = rs.set_relation(ctx,1,2)
    next(g); g.send(bit); g.send(200)
    if unique:
        assert ctx.state.charas[1].relation[2] == 0
        with pytest.raises(StopIteration): g.send(999)
    else:
        with pytest.raises(StopIteration): g.send("")
    assert c.talent[ctx.data.index_of("TALENT","処女")] == unique


def test_conversion_snapshot_positive_only(ctx):
    st=ctx.state
    st.charas[1].no=2; st.charas[2].no=1; st.charas[3].no=8
    st.charas[1].relation[1]=4; st.charas[1].relation[2]=8
    st.charas[1].relation[3]=16; st.charas[1].relation[8]=-9
    st.charas[0].relation[1]=19
    rs.convert_relation(ctx)
    assert [st.charas[1].relation[i] for i in (1,2,3,8)] == [8,4,16,-9]
    assert st.charas[0].relation[1] == 19


def test_preserve_unknown_bits_clear_bit_zero(ctx):
    ctx.state.charas[1].relation[2] = -(1<<63) | (1<<60) | 1
    drive(rs.set_relation(ctx,1,2), [200,""])
    assert ctx.state.charas[1].relation[2] == -(1<<63) | (1<<60)


def texts(out):
    return "\n".join("".join(s.text for part in line.parts for s in part.segments) for line in out.lines)


def test_menu_invalid_return_and_finish(ctx):
    g=rs.relation_menu(ctx)
    next(g)
    for value in (-1,0,98,1000):
        g.send(value)
    g.send(1)
    for value in (-1,0,1,98,1000):
        g.send(value)
    g.send(99)
    assert texts(ctx.out).count("相関関係設定") == 2
    with pytest.raises(StopIteration): g.send(99)
    assert ctx.state.result[0] == 0

@pytest.mark.parametrize("first,second", [(4,1),(1,4)])
def test_menu_original_inclusive_bound_error(ctx,first,second):
    # オープニング処理.ERB:699、740 原文 <= CHARANUM。
    g=rs.relation_menu(ctx)
    next(g); g.send(first)
    with pytest.raises(IndexError): g.send(second)


def test_cancel_linecount_and_results(ctx):
    ctx.out.printl("先前內容")
    ctx.state.result[1]=77
    ctx.state.results[0]="保留"
    ctx.state.results[1]="尾格"
    before=ctx.out.linecount
    g=rs.set_relation(ctx,1,2)
    next(g)
    count=ctx.out.linecount
    g.send(30)
    assert ctx.out.linecount == count
    with pytest.raises(StopIteration): g.send(999)
    assert ctx.out.linecount == before
    assert texts(ctx.out) == "先前內容"
    assert (ctx.state.result[0],ctx.state.result[1],ctx.state.results[0],ctx.state.results[1]) == (0,77,"保留","尾格")

@pytest.mark.parametrize("initial,values,expected", [(0,[200,""],"保留"),(0,[30,200,""],"友人"),(1<<32,[32,200,""],"保留")])
def test_commit_result_residue(ctx,initial,values,expected):
    ctx.state.charas[1].relation[2]=initial
    ctx.state.charas[2].relation[1]=initial
    ctx.state.results[0]="保留"
    ctx.state.results[1]="尾格"
    ctx.state.result[1]=77
    drive(rs.set_relation(ctx,1,2),values)
    assert (ctx.state.result[0],ctx.state.result[1],ctx.state.results[0],ctx.state.results[1]) == (0,77,expected,"尾格")

@pytest.mark.parametrize("male,giri", [(0,1),(1,0),(1,1)])
def test_parent_exemptions(ctx,male,giri):
    c=ctx.state.charas[1]
    c.base[40]=50
    for name,value in (("オトコ",male),("処女",1),("固有キャラ",1)):
        c.talent[ctx.data.index_of("TALENT",name)]=value
    drive(rs.set_relation(ctx,1,2), [20]+([6] if giri else [])+[200,""])
    assert c.talent[ctx.data.index_of("TALENT","処女")] == 1

@pytest.mark.parametrize("bit,reverse", rs.REVERSE_BITS)
def test_removal_preserves_unilateral_reverse(ctx,bit,reverse):
    # :361–459 已有的反向關係亦可清除；印象／友人等殘留。
    ctx.state.charas[2].relation[1]=(1<<reverse)|(1<<4)|(1<<30)|(1<<31)|(1<<58)
    drive(rs.set_relation(ctx,1,2),[200,""])
    assert ctx.state.charas[2].relation[1] == (1<<4)|(1<<30)|(1<<31)|(1<<58)


def test_check_all_relation_results_and_parent_ids(ctx):
    # CHARA_RELATION.ERB@CHECK_ALL_RELATION:930–949、967–977。
    from eragvt.game.relation import check_all_relation
    st=ctx.state
    st.charas[1].base[40]=50
    st.charas[2].base[40]=20
    st.charas[1].talent[ctx.data.index_of("TALENT","オトコ")]=0
    st.charas[1].relation[2]=1<<20
    st.results[0]="舊值"; st.results[1]="尾格"; st.result[1]=77
    check_all_relation(ctx)
    assert st.charas[2].cflag[7] == st.charas[1].cflag[240]
    assert st.results[0] == "母親"
    assert st.results[1] == "尾格" and st.result[1] == 77
    assert st.result[0] == 0


def test_selection_then_check_all_and_reentry(ctx):
    st=ctx.state
    st.charas[1].base[40]=50
    st.charas[2].base[40]=20
    st.charas[1].talent[ctx.data.index_of("TALENT","オトコ")]=0
    g=rs.relation_menu(ctx)
    next(g)
    for value in (1,2,20,200,""): g.send(value)
    assert st.charas[2].cflag[7] == 0
    with pytest.raises(StopIteration): g.send(99)
    assert st.charas[2].cflag[7] == st.charas[1].cflag[240]
    drive(rs.relation_menu(ctx),[99])
    assert st.charas[1].relation[2] == 1<<20


def test_web_and_save(data,tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,narration=None)
    client=TestClient(app)
    def send(value):
        return client.post("/api/input",json={"value":value}).json()
    for value in (0,0,30,1,2,30,200,""):
        send(value)
    st=app.state.session.state
    assert st.charas[1].relation[2] & (1<<30)
    send(99); send(1)
    for value in (110,4000):send(value)
    assert "友人" in client.get("/").text
    for value in (999,200,0):send(value)
    saved=st.charas[1].relation[2]
    st.charas[1].relation[2]=0
    for value in (300,0):send(value)
    assert app.state.session.state.charas[1].relation[2] == saved


def test_extracted_text_matches_source():
    from pathlib import Path
    import runpy
    script=Path(__file__).parents[1]/"tools/extract_relation_setting.py"
    module=runpy.run_path(str(script))
    assert module["extract"]() == (script.parents[1]/"src/eragvt/game/relation_setting_text.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("token", ["{ARG:0}", "{ARG:1}", "%CALLNAME:(ARG:0)%", "%CALLNAME:(ARG:1)%", "%RESULTS%", "{主人}"])
def test_display_does_not_reinterpret_names(token):
    # PRINTFORM 僅展開原樣板，不再次展開插入的 CALLNAME／RESULTS 字串。
    # reference/emuera-1824/Emuera/GameData/StrForm.cs:205–216。
    assert rs._text(494, a=token, b=token, ai=1, bi=2, relation=token) == f"『{token}』にとって『{token}』は【{token}】です。"
