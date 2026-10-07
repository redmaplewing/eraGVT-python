"""S89：衣裝／武器COUNT，expected由ERB推導；角色沿用25歲人工資料。

NEXT／BREAK讀共享counter後步進，RETURN不步進：
reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023、2054–2161。
"""
import pytest

from test_body_editor import data, ctx
from eragvt.game import clothing, weapon_words
from eragvt.game.clothing_custom import encode_custom
from eragvt.game.weapon_customize import add_strings
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import dump_save, load_save


# 各CUSTOM_NUM長度、通常／特殊／內衣代表；不逐件重複等價測試。
@pytest.mark.parametrize("cid,expected", [
    (101,5),(102,6),(114,7),(146,8),(196,5),(199,7),
    (301,5),(305,7),(312,6),(313,4),(314,4),
])
def test_custom_menu_repeat_and_return(ctx, cid, expected):
    st = ctx.state
    slot = 42 if cid >= 300 else 40
    st.charas[1].cflag[slot] = cid
    st.count[0], st.count[1] = 73, 74
    before_rng = st.rng.snapshot()
    g = clothing.custom_clothing_gen(ctx, 1, slot)
    next(g)
    assert st.count[0] == expected
    g.send(-123)  # 非法輸入只回INPUT_LOOP，不重跑CUSTOM_NUM。
    assert st.count[0] == expected
    with pytest.raises(StopIteration):
        g.send(99)
    assert (st.count[0], st.count[1]) == (expected, 74)
    assert st.rng.snapshot() == before_rng


def test_missing_custom_function_does_not_touch_count(ctx):
    ctx.state.charas[1].cflag[40] = 118
    ctx.state.count[0] = 73
    g = clothing.custom_clothing_gen(ctx, 1, 40)
    with pytest.raises(StopIteration):
        next(g)
    assert ctx.state.count[0] == 73


@pytest.mark.parametrize("slot", [40, 41])
def test_copy_and_paste_loop_boundaries(ctx, monkeypatch, slot):
    # 共通処理@COPY91:536–547兩分支各REPEAT CUSTOM_NUM；COPY92不寫COUNT。
    st, c = ctx.state, ctx.state.charas[1]
    c.cflag[40] = c.cflag[41] = 101
    c.equip[1] = c.equip[101] = 12345
    seen = []
    original = clothing.figure_split
    def probe(value, digit):
        if digit <= 9:
            seen.append((st.count[0], digit))
        return original(value, digit)
    monkeypatch.setattr(clothing, "figure_split", probe)
    g = clothing.custom_clothing_gen(ctx, 1, slot)
    next(g)
    expected = list(zip(range(5), range(1, 6)))
    assert seen == expected
    seen.clear()
    g.send(91)
    assert seen == expected * 2  # COPY91後SAVE，再次進OPTION。
    seen.clear()
    g.send(92)
    assert seen == expected  # COPY92 RETURN -1，只下次OPTION讀取。
    assert st.count[0] == 5
    g.close()


def test_figure_call_reads_and_overwrites_shared_count(ctx, monkeypatch):
    # OPTION_101:168–170；CALL不保存COUNT，賦值左側及NEXT讀CALL後值。
    # SET先算右側再SetValue：reference/emuera-1824/Emuera/GameProc/Function/
    # Instraction.Child.cs:459–463；探針只檢查時序，原FIGURE_SPLIT使用LOCAL。
    st = ctx.state
    st.charas[1].cflag[40] = 101
    seen = []
    def probe(value, digit):
        if digit <= 9:
            seen.append((st.count[0], digit))
            if st.count[0] == 0:
                st.count[0] = 3
        return 0
    monkeypatch.setattr(clothing, "figure_split", probe)
    g = clothing.custom_clothing_gen(ctx, 1, 40)
    next(g)
    assert seen == [(0,1), (4,5)]
    assert st.count[0] == 5
    g.close()


def test_save_repeat_and_continue(ctx):
    # 共通処理@SAVE:566–572：COUNT0==0 CONTINUE，最後另加refCUSTOM0。
    ctx.state.count[0], ctx.state.count[1] = 73, 74
    assert encode_custom(101, [2,0,0,0,0], state=ctx.state) == 2
    assert (ctx.state.count[0], ctx.state.count[1]) == (5,74)


@pytest.mark.parametrize("used,expected", [(0,1), (1,0), (2,0)])
def test_parts_repeat_remaining_slots_before_performance(ctx, monkeypatch, used, expected):
    # CLOTH_WEAR@CLOTH_CUSTOMIZE_OUTER2:983–989，負上限／零次仍COUNT=0。
    st, c = ctx.state, ctx.state.charas[1]
    c.cflag[41] = 401  # CLOTH_HOSEI_SLOT_401：1槽。
    for i in range(used):
        c.equip[600+i] = 1
    st.count[0], st.count[1] = 73,74
    seen = []
    original = clothing._performance
    def probe(*args, **kwargs):
        seen.append(st.count[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(clothing, "_performance", probe)
    g = clothing.custom_parts_gen(ctx, 1)
    next(g)
    assert seen == [expected]
    assert (st.count[0], st.count[1]) == (expected,74)
    with pytest.raises(StopIteration):
        g.send(999)
    assert st.count[0] == expected


def test_weapon_repeat_break_is_visible_before_rng(ctx):
    # GENERATE_ADD_STR@GENERATE_ADD_STR:159–169：最後LCOUNT54空字串，BREAK後COUNT=1。
    st = ctx.state
    st.count[0], st.count[1] = 73,74
    rng = st.rng
    seen = []
    class ProbeRng:
        def rand(self, upper):
            seen.append(st.count[0])
            return rng.rand(upper)
    st.rng = ProbeRng()
    assert weapon_words.addition(ctx, 1,1,0,1,1,"")
    assert set(seen) == {1}
    assert (st.count[0], st.count[1]) == (1,74)


def test_weapon_ui_and_saved_count(ctx, tmp_path):
    # WEAPON_NAME@WEAPON_ADD_STRS:141–527：外層LOCAL，不覆寫GENERATE_ADD_STR殘值。
    st = ctx.state
    st.charas[1].cstr[5] = "星"
    st.count[0], st.count[1] = 73,74
    g = add_strings(ctx, 1,1)
    next(g)
    assert st.count[0] == 73
    g.send(11)
    g.send(100)
    assert st.count[0] == 1
    with pytest.raises(StopIteration):
        g.send(110)
    saved, _ = load_save(dump_save(st))
    assert (saved.count[0],saved.count[1]) == (1,74)
    (tmp_path / "neutral.ERB").write_text(
        "@COUNT_RESULT\nPRINTFORML {COUNT}:{COUNT:1}\nRETURN\n", encoding="utf-8", newline="\n")
    ctx.narration = CatalogNarrationService(tmp_path, ctx.data)
    ctx.state = saved
    assert ctx.narration.run_function(ctx, "COUNT_RESULT")
    assert ctx.out.lines[-1].text == "1:74"


@pytest.fixture(scope="module")
def svc(data):
    from eragvt.data import default_csv_dir
    return CatalogNarrationService(default_csv_dir().parent / "ERB", data)


@pytest.mark.parametrize("color,expected", [("",73), ("red",73), ("1//2//3",20007), ("1//2//4",21000)])
def test_catalog_color_exact_return_and_fallthrough(ctx, svc, color, expected):
    # GET_COLOR_NAME@GETCOLORNAMESTR:127–156：拒絕參數不跑FOR，命中RETURNF不步進。
    st = ctx.state
    # 僅測本函式，人工色表；不以實作推導近似色輸出。
    original = ctx.data.str_defaults
    ctx.data.str_defaults = {20007: "1//2//3", 21007: "人工色"}
    try:
        st.count[0] = 73
        result = svc._interp(ctx).call("GETCOLORNAMESTR", [color], as_method=True)
        assert st.count[0] == expected
        if color.startswith("1//"):
            assert result == "人工色"
    finally:
        ctx.data.str_defaults = original


@pytest.mark.parametrize("solo,action,result", [(False,103,1), (False,55,-1), (True,103,-1)])
def test_catalog_choose_action_early_return(ctx, svc, solo, action, result):
    # CHOOSE_RAND_1@CHOOSE_ACTION_TOGETHER_F:22–41：solo RETURN亦在REPEAT CHARANUM之後。
    from eragvt.state.constants import GameOption
    st = ctx.state
    st.charas[1].cflag[100] = 103
    if solo:
        st.flag.set_bit(0, int(GameOption.SOLO))
    st.count[0] = 73
    assert svc._interp(ctx).call("CHOOSE_ACTION_TOGETHER_F", [action,-1], as_method=True) == result
    assert st.count[0] == len(st.charas)


@pytest.mark.parametrize("facility,result", [(0,0),(1,1)])
def test_catalog_relaxation_empty_and_selected(ctx, svc, facility, result):
    # CHOOSE_RAND_1@CHOOSE_RELAXATION_FACILITY:54–56、61–64、113–115。
    ctx.state.flag[53] = facility
    assert svc.run_function(ctx, "CHOOSE_RELAXATION_FACILITY", [facility])
    assert (ctx.state.count[0],ctx.state.result[0]) == (15,result)


def test_common_draw_nine_shared_then_catalog_call(ctx, svc):
    # 共通処理@CLOTH_CUSTOMIZE_OPTION_DRAW:174–177後CALL；實際呼叫者為戰鬥衣裝顯示。
    ctx.state.count[0],ctx.state.count[1] = 73,74
    assert svc.run_function(ctx, "CLOTH_CUSTOMIZE_OPTION_DRAW", [101,1])
    assert (ctx.state.count[0],ctx.state.count[1]) == (9,74)
