"""S32：預期條件、文字分支及狀態更新由 ERB 原文推導。

原作路徑相對 source/earGVP/ERB/；文字直接讀取原文指定行，不由 Python 輸出反推。
"""

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.battle.source_check import _hatujou_to_hairan
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration import nodes as N
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState, IntArray
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"
SOURCE = "ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB"
TEXT = "MESSAGE_HATUJOU_TO_HAIRAN"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data, svc):
    st = GameState.new(data, rng=GameRng(1))
    event_first(st, data, preset=PRESET_TOKUSOU)
    shop.event_shop(st, data, TextOutput(), NullNarrationService())
    c = st.target_chara
    c.talent = IntArray()
    c.abl = IntArray()
    c.mark = IntArray()
    c.cflag[0] = c.cflag[1] = c.cflag[3] = c.cflag[6] = 0
    st.flag[700] = 0  # MESSAGE_BRANCH.ERB@BRANCH_PALAM_F:45–371：基本 FAITH_S=10，無戰鬥修正。
    c.tcvarn[12] = 12  # DIM.ERH:130–132：發情 4、麻痺 8。
    c.talent[data.index_of("TALENT", "ケモミミ族")] = 1
    st.result[0], st.result[1], st.result[2] = 7, 8, 9
    return Ctx(st, data, TextOutput(), svc)


@pytest.mark.parametrize(
    "species,male,pregnant,state,roll,draws,result,expected_state",
    [
        (0, 0, 0, 12, 0, 0, 0, 12),
        (1, 1, 0, 12, 0, 0, 0, 12),
        (1, 0, 1, 12, 0, 0, 0, 12),
        (1, 0, 4, 12, 0, 0, 0, 12),
        (1, 0, 0, 14, 0, 0, 0, 14),
        (1, 0, 0, 8, 0, 0, 0, 8),
        (1, 0, 0, 12, 0, 1, 1, 14),
        (1, 0, 0, 12, 9, 1, 1, 14),
        (1, 0, 0, 12, 10, 1, 0, 12),
        (1, 0, 0, 12, 99, 1, 0, 12),
        (-1, 0, 0, 12, 0, 1, 1, 14),  # 原作 :514 是 ==0，不是 <=0。
    ],
)
def test_gates_rng_and_state(ctx, species, male, pregnant, state, roll, draws, result, expected_state):
    """SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:514–526、583–585。

    RETURN 只覆寫提供的 RESULT 元素：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2024；
    reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740。
    位元 OR：reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:623–635。
    RAND:100 為 0–99：reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1451–1463；
    reference/emuera-1824/Emuera/_Library/SFMT.cs:60–65。
    """
    st, c = ctx.state, ctx.state.target_chara
    for name, value in (("ケモミミ族", species), ("オトコ", male), ("妊娠", pregnant)):
        c.talent[ctx.data.index_of("TALENT", name)] = value
    c.tcvarn[12] = state
    st.rng = FixedRng([roll, 71])
    _hatujou_to_hairan(ctx)
    assert c.tcvarn[12] == expected_state
    assert [st.result[i] for i in range(3)] == [result, 8, 9]
    assert st.rng.snapshot() == ([71] if draws else [roll, 71])
    assert bool(ctx.out.lines) == bool(result)
    if result:
        before = ctx.out.linecount
        _hatujou_to_hairan(ctx)  # 已有旗標時不再抽亂數或輸出。
        assert st.result[0] == 0
        assert st.rng.snapshot() == [71]
        assert ctx.out.linecount == before


# 手工由 :528–582 的條件挑出各列應輸出的原文行，涵蓋主觀、用語、數量與狀態分支。
TEXT_CASES = [
    ((0, 0, 0, 0, 0, 0, 0), [531, 533, 541, 545, 547, 549, 553, 557, 559, 563]),
    ((0, 0, 0, 20, 1, 0, 1), [531, 533, 539, 541, 545, 547, 549, 551, 553, 557, 561, 563]),
    ((1, 1, 0, 0, 0, 0, 0), [529, 533, 541, 543, 547, 549, 553, 555]),
    ((1, 0, 0, 20, 0, 1, 1), [529, 533, 539, 541, 545, 547, 551, 553, 555]),
    ((0, 1, 1, 20, 0, 0, 0), [531, 533, 537, 541, 545, 547, 549, 566, 570, 571]),
    ((1, 1, 2, 20, 1, 0, 1), [529, 533, 536, 537, 541, 543, 547, 549, 566, 568]),
    ((0, 0, 2, 0, 1, 1, 0), [531, 533, 536, 537, 541, 545, 547, 566, 570, 571]),
    ((1, 0, 1, 0, 0, 0, 0), [529, 533, 537, 541, 545, 547, 549, 566, 568]),
]


@pytest.mark.parametrize("settings,printed_lines", TEXT_CASES)
def test_original_text_and_style(ctx, settings, printed_lines):
    """SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:528–582；ESTRUS_CYCLE.ERB@ESTRUS_TEXT_F:30–46。"""
    subjective, pure, quantity, births, wording, daraku, danger = settings
    st, c = ctx.state, ctx.state.target_chara
    for name, value in (("主観視点", subjective), ("清純派", pure), ("触手の虜", daraku)):
        c.talent[ctx.data.index_of("TALENT", name)] = value
    c.exp[ctx.data.index_of("EXP", "出産経験")] = births
    c.cflag[217] = 13 if danger else 0
    st.tflag[7], st.flag[96] = quantity, wording
    st.rng = FixedRng([0])
    source = (ERB / SOURCE).read_text(encoding="utf-8-sig").splitlines()
    expected, pending = [], ""
    for number in printed_lines + [574, 575, 578, 581, 582]:
        command, text = source[number - 1].lstrip().split(" ", 1)
        text = text.replace("%PRINT_CALLNAME(TARGET)%", c.callname)
        text = text.replace("%PRINT_TRANSCALLNAME(TARGET)%", c.callname)
        text = text.replace('%ESTRUS_TEXT_F(TARGET,"の")%', "危険日の" if danger else "")
        pending += text
        if command.endswith(("L", "W")):
            expected.append(pending)
            pending = ""
    _hatujou_to_hairan(ctx)
    assert [line.text for line in ctx.out.lines] == expected
    assert sum(line.wait for line in ctx.out.lines) == 2
    segments = [s for line in ctx.out.lines for p in line.parts for s in p.segments]
    label = next(s for s in segments if s.text == "[排卵]")
    assert (label.color, label.bold) == ("#9600fa", True)
    assert segments[-1].color is None and not segments[-1].bold
    assert st.rng.snapshot() == []


def test_catalog_fragment_excludes_game_logic(ctx):
    """只抽取 SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:528–582，不能直接執行整段遊戲規則。"""
    cat = ctx.narration.catalog
    assert cat.exists(TEXT)
    fd = cat.get(TEXT)
    assert fd.file == SOURCE
    assert all(528 <= node.line <= 582 for node in N.iter_stmts(fd.body))
    assert not any(isinstance(node, (N.Assign, N.Return)) for node in N.iter_stmts(fd.body))
    assert cat.unsupported_reason("HATUJOU_TO_HAIRAN") is not None


def test_no_catalog_stops_before_state_update(ctx):
    ctx.narration = NullNarrationService()
    ctx.state.rng = FixedRng([0])
    with pytest.raises(NotImplementedError):
        _hatujou_to_hairan(ctx)
    assert ctx.state.target_chara.tcvarn[12] == 12
    assert ctx.state.result[0] == 7


def test_text_precedes_flag_and_return(ctx):
    """ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:528–585：先輸出，後寫旗標及 RETURN。"""
    class RecordingNarration(NullNarrationService):
        def run_function(self, context, name, args=None, hooks=None):
            assert name == TEXT
            assert context.state.target_chara.tcvarn[12] == 12
            assert context.state.result[0] == 7
            return True

    ctx.narration = RecordingNarration()
    ctx.state.rng = FixedRng([0])
    _hatujou_to_hairan(ctx)
    assert ctx.state.target_chara.tcvarn[12] == 14
    assert ctx.state.result[0] == 1
