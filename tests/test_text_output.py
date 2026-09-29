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
    segs = o.lines[0].segments
    assert segs[0] == Segment("撤退", "#00ff96", True)
    assert segs[1] == Segment("!", None, False)


def test_auto_buttons_shop_menu():
    # インターミッション画面/SHOP.ERB:154 `PRINT [110]ステータス表示 `
    segs = split_buttons("[110]ステータス表示 [111]キャラの強化")
    assert [(s.text, s.button) for s in segs] == [("[110]ステータス表示 ", 110), ("[111]キャラの強化", 111)]


def test_auto_button_with_prefix_and_spaces():
    segs = split_buttons("選択：[ 0]いいえ")
    assert [(s.text, s.button) for s in segs] == [("選択：", None), ("[ 0]いいえ", 0)]


def test_print_plain_and_explicit_button():
    o = TextOutput()
    o.print_plain("[1]は押せない")
    o.button("はい", 1)
    o.printl()
    segs = o.lines[0].segments
    assert segs[0].button is None and segs[1].button == 1


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
        "segments": [{"text": "[1]はい", "color": None, "bold": False, "button": 1}],
        "kind": "text",
        "wait": False,
    }


def test_null_narration():
    assert NullNarrationService().narrate(0, "FIRST", 12) is None
