"""S88：原生角色編輯COUNT邊界，expected取原文；沿用25歲人工前態。"""
import pytest

from test_body_editor import data, ctx
from eragvt.game.character_editor import character_editor
from eragvt.game.character_name import random_character_name
from eragvt.game.character_personality import personality_setting
from eragvt.game.self_call_setting import selfcall_gen
from eragvt.game.opening import mode_select_gen
from eragvt.state import FixedRng


def test_editor_exit_restores_items_count(ctx):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:345–351，先REPEAT4後FOR100..699。
    ctx.state.count[1] = 71
    g = character_editor(ctx, 1)
    next(g)
    with pytest.raises(StopIteration):
        g.send(99)
    assert ctx.state.count[0] == 700
    assert ctx.state.count[1] == 71


def test_name_repeat_is_shared_and_read_after_input(ctx):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM:827–957、1009–1012。
    ctx.data.str_defaults.update({3000: "人工姓", 12000: "人工名"})
    ctx.state.rng = FixedRng([0] * 40)
    g = random_character_name(ctx, 1)
    next(g)
    g.send(200)
    assert ctx.state.count[0] == 20
    with pytest.raises(StopIteration):
        g.send(0)
    assert ctx.state.count[0] == 20
    assert ctx.state.results[0] == "人工姓人工名"


@pytest.mark.parametrize("choice,expected", [(98, 3), (21, 10)])
def test_selfcall_nested_count_and_break(ctx, choice, expected):
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL:1211–1215，COUNT1終值3；
    # :1228–1240，索引9為空→BREAK仍加1得10；預設類型再跑:1244–1253得3。
    ctx.state.charas[1].callname = "あい"
    g = selfcall_gen(ctx, 1)
    next(g)
    assert (ctx.state.count[0], ctx.state.count[1]) == (3, 3)
    if choice == 98:
        with pytest.raises(StopIteration):
            g.send(choice)
    else:
        g.send(choice)
    assert ctx.state.count[0] == expected
    g.close()


def test_personality_catalog_reads_and_mutates_loop_counter(ctx):
    # FIRSTSETTING_CHARA_SEIKAKU.ERB@RAND_CHOOSE_KOJO_SEIKAKU:462–476。
    # 色函式CALL後讀的是共享COUNT，NEXT也從CALL所留數值加1。
    c = ctx.state.charas[1]
    for i in range(10, 29):
        c.talent[i] = int(i == 10)
    seen = []
    class Colors:
        def run_function(self, call_ctx, name):
            if active[0]:
                seen.append((name, call_ctx.state.count[0]))
                call_ctx.state.count[0] = 18
                return True
            return False
    active = [False]
    ctx.narration = Colors()
    ctx.state.rng = FixedRng([0])
    g = personality_setting(ctx, 1)
    next(g)
    active[0] = True
    # 在第二次主畫面繪製前關掉probe，避免把不使用COUNT的SHOW_KOJO_EXIST混入。
    original = ctx.narration.run_function
    def once(call_ctx, name):
        result = original(call_ctx, name)
        active[0] = False
        return result
    ctx.narration.run_function = once
    g.send(98)
    assert len(seen) == 1 and seen[0][1] == 0
    assert c.talent[28] == 1 and c.talent[10] == 0
    assert ctx.state.count[0] == 19
    g.close()


@pytest.mark.parametrize("inherited", [False, True])
def test_mode_menu_count_through_confirm(ctx, inherited):
    # オープニング処理.ERB@MODE_SELECT:306–351，FOR COUNT,1,8；INPUT及RETURN不改COUNT。
    g = mode_select_gen(ctx, inherited=inherited)
    next(g)
    assert ctx.state.count[0] == 8
    with pytest.raises(StopIteration):
        g.send(1)
    assert ctx.state.count[0] == 8


def test_random_naming_select_shared_repeat(ctx):
    # FIRSTSETTING_RANDOMNAMING.ERB@FIRSTSETTING_RANDOMNAMING_SELECT:314、390–392。
    from eragvt.game.naming import random_naming_select
    ctx.data.str_defaults[500] = "中性詞"
    ctx.state.rng = FixedRng([0] * 20)
    g = random_naming_select(ctx, 0, 1, "前綴")
    next(g)
    assert ctx.state.count[0] == 20
    g.send(801)
    assert ctx.state.count[0] == 20
    with pytest.raises(StopIteration):
        g.send(0)
    assert ctx.state.results[0] == "中性詞前綴"
