"""文字輸出層。按鈕判定的 expected 由 reference/emuera-1824/Emuera/GameView/ButtonStringCreator.cs 推導。"""

import pytest

from eragvt.text import NullNarrationService, Segment, TextOutput, split_buttons


def texts(lines):
    return [(l.kind, l.text, l.wait) for l in lines]


def test_print_printl_printw():
    o = TextOutput()
    o.print("A")
    o.print("B")
    assert o.linecount == 0  # 未換行
    o.printl("C")
    o.printw("待つ")
    o.printl()
    assert texts(o.lines) == [("text", "ABC", False), ("text", "待つ", True), ("text", "", False)]


def test_drawline_flushes_partial_line():
    o = TextOutput()
    o.print("x")
    o.drawline()
    assert texts(o.lines) == [("text", "x", False), ("drawline", "", False)]


def test_wait_variants():
    o = TextOutput()
    o.wait()
    assert texts(o.lines) == [("text", "", True)]
    o.printl("a")
    o.wait()
    assert o.lines[-1].wait
    o.print("b")
    o.wait()
    assert texts(o.lines)[-1] == ("text", "b", True)


def test_color_and_bold():
    o = TextOutput()
    o.set_color((0, 255, 150))  # BATTLE_COM.ERB `SETCOLOR 0, 255, 150`
    o.set_bold()
    o.print("撤退")
    o.reset_color()
    o.set_bold(False)
    o.printl("!")
    segs = o.lines[0].parts[0].segments
    assert segs == [Segment("撤退", "#00ff96", True), Segment("!", None, False)]


def test_italic_and_regular():
    """S20（使用者裁決 2026-10-01）：FONTITALIC は現在のスタイルに Italic を加え（太字は保つ）、FONTREGULAR は両方解除
    （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1084–1121）。
    例：FORCE_悪堕ちキャラの淫謀.ERB:810–815 `FONTBOLD / PRINT □ / FONTITALIC / PRINTFORML 文 / FONTREGULAR`。"""
    o = TextOutput()
    o.set_bold(True)
    o.print("□")
    o.set_italic(True)
    o.printl("私はロボットではありません")
    o.set_bold(False)
    o.printl("x")
    segs = o.lines[0].parts[0].segments
    assert segs == [Segment("□", None, True, False), Segment("私はロボットではありません", None, True, True)]
    assert o.lines[1].parts[0].segments == [Segment("x", None, False, False)]
    assert o.lines[0].to_json()["parts"][0]["segments"][1]["italic"] is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # ボタン 0 個 → 1 単位、選択不可
        ("ただの文字列", [("ただの文字列", None)]),
        # 1 個 → 行全体が 1 つのボタン（syn:73–81）
        ("選択：[ 0]いいえ", [("選択：[ 0]いいえ", 0)]),
        # 説明が右だけ → 各 [n] の直前で切る（alignmentRight）
        ("[110]ステータス表示 [111]キャラの強化", [("[110]ステータス表示 ", 110), ("[111]キャラの強化", 111)]),
        # lex の例（ButtonStringCreator.cs:222–224）
        ("[1] あ [2] いうえ ", [("[1] あ ", 1), ("[2] いうえ ", 2)]),
        # 説明が左右両方 → 2 文字以上の空白で区切る（alignmentEtc）
        ("a [1] b  c [2] d", [("a [1] b", 1), ("  c [2] d", 2)]),
        # 説明が左だけ → [n] の直後で切る（alignmentLeft）
        ("はい[0] いいえ[1]", [("はい[0]", 0), (" いいえ[1]", 1)]),
        # 数字でない [] はボタンにならない
        ("[A] [B]", [("[A] [B]", None)]),
        # [ の入れ子 → 解析不能で 1 単位
        ("[[1]]", [("[[1]]", None)]),
    ],
)
def test_split_buttons(text, expected):
    assert split_buttons(text) == expected


def test_buttons_decided_over_whole_line_across_prints_and_colors():
    # PRINT を複数回・色違いで出しても、改行時に行全体で判定（PrintStringBuffer.cs@fromCssToButton:275）
    o = TextOutput()
    o.print("[101]出撃する　")
    o.set_color("#ff0000")
    o.print("[102]鍛錬する")
    o.printl()
    parts = o.lines[0].parts
    assert [(p.text, p.button) for p in parts] == [("[101]出撃する　", 101), ("[102]鍛錬する", 102)]
    assert parts[1].segments[0].color == "#ff0000"


def test_button_boundary_splits_styled_segment():
    o = TextOutput()
    o.print("[1]あ [2]")
    o.set_color("#00ff00")
    o.print("い")
    o.printl()
    parts = o.lines[0].parts
    assert parts[1].segments == [Segment("[2]", None, False), Segment("い", "#00ff00", False)]


def test_print_plain_and_explicit_button():
    o = TextOutput()
    o.print("[5]は押せる")  # PRINTPLAIN の前に確定
    o.print_plain("[1]は押せない")
    o.button("はい", 1)
    o.printl()
    assert o.lines[0].buttons == [("[5]は押せる", 5), ("はい", 1)]
    assert o.lines[0].parts[1].button is None


def test_clearline_and_drain():
    o = TextOutput()
    for t in "abc":
        o.printl(t)
    o.clearline(2)
    o.print("partial")
    drained = o.drain()
    assert [l.text for l in drained] == ["a"]
    assert o.lines == []
    o.printl()
    assert o.lines[0].text == "partial"


def test_line_to_json():
    o = TextOutput()
    o.printl("[1]はい")
    assert o.lines[0].to_json() == {
        "parts": [{"segments": [{"text": "[1]はい", "color": None, "bold": False, "italic": False}], "button": 1, "title": None}],
        "kind": "text",
        "wait": False,
        "align": "left",
    }


def test_null_narration():
    """口上なし＝KOJO_ROOT.ERB:46–90 の「見つからない」路徑：FLAG:62（OTHER_ なら 1）、RESETCOLOR、FLAG:900 = 0、-1。"""
    from types import SimpleNamespace

    from eragvt.state import GameState

    st = GameState()
    st.flag[900] = 3
    out = TextOutput()
    out.set_color((1, 2, 3))
    ctx = SimpleNamespace(state=st, out=out)
    assert NullNarrationService().call_kojo(ctx, 0, "FIRST") == -1
    assert (st.flag[62], st.flag[900], out._color) == (0, 0, None)
    assert NullNarrationService().call_kojo(ctx, 0, "OTHER_X") == -1
    assert st.flag[62] == 1
    assert NullNarrationService().run_function(ctx, "MESSAGE_FIRST") is False


def test_narration_runtime_fontitalic():
    """S20：口上 catalog の FONTITALIC／FONTREGULAR も TextOutput に反映（以前は FONTITALIC を無視していた）。"""
    from eragvt.narration import nodes as N
    from eragvt.narration.runtime import Env, Interp

    o = TextOutput()
    it = Interp(None, Env(state=None, data=None, out=o))
    it._style(N.Style(1, "FONTBOLD"), None)
    it._style(N.Style(1, "FONTITALIC"), None)
    o.print("a")
    it._style(N.Style(1, "FONTREGULAR"), None)
    o.printl("b")
    assert o.lines[0].parts[0].segments == [Segment("a", None, True, True), Segment("b", None, False, False)]
