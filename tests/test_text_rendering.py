"""S87：expected 依原引擎輸出規則推導，不由 Python 回填。"""
import pytest
import sys

native_windows = pytest.mark.skipif(sys.platform != "win32", reason="本機 Windows GDI 驗收；其他平台沿既有偏離")
from eragvt.text import TextOutput


def test_printlc_is_a_button_boundary(monkeypatch):
    # EmueraConsole.Print.cs:363–369、PrintStringBuffer.cs:63–89。
    o = TextOutput()
    o.print("前文")
    o.print_lc("[1]選項")
    o.printl("後文")
    assert [(p.text.strip(), p.button) for p in o.lines[0].parts] == [("前文", None), ("[1]選項", 1), ("後文", None)]


@pytest.mark.parametrize("count, expected", [(0, ["舊一", "舊二", "尚未換行"]), (1, ["舊一", "尚未換行"]), (9, ["尚未換行"])])
def test_clearline_keeps_pending(count, expected):
    # CLEARLINE_Instruction:488–500 直接 deleteLine；沒有 PrintFlush。
    # EmueraConsole.Print.cs:156–176 按 logical line 刪除，未輸出緩衝不動。
    o = TextOutput()
    o.printl("舊一")
    o.printl("舊二")
    o.print("尚未換行")
    o.clearline(count)
    o.printl()
    assert [line.text for line in o.lines] == expected


def test_temporary_line_replaced_only_when_next_line_is_added():
    # EmueraConsole.Print.cs:201–204、295–308、110–114。
    o = TextOutput()
    o.printl("[1]選項")
    o.print_temporary("無効な値です")
    o.print("尚未換行")
    assert [x.text for x in o.lines] == ["[1]選項", "無効な値です"]
    o.printl()
    assert [x.text for x in o.lines] == ["[1]選項", "尚未換行"]
    o.print_temporary("第一次")
    o.print_temporary("第二次")
    assert [x.text for x in o.lines] == ["[1]選項", "尚未換行", "第二次"]


def test_html_shape_space_is_geometry_not_text():
    # ConsoleShapePart.cs:40–53：14px × 75 / 100 = 10.5，再依 :169–173 先加 0.5 再截整為 11px（PrintStringBuffer.cs:400）。
    o = TextOutput()
    o.html_print("<nobr>A<shape type='space' param='75'>B</nobr>")
    assert o.lines[0].text == "AB"
    assert o.lines[0].parts[1].space_px == 11


def test_catalog_setfont_applies_and_resets():
    from eragvt.narration import nodes as N
    from eragvt.narration.runtime import Env, Interp
    from eragvt.narration.expr import Lit
    o = TextOutput()
    it = Interp(None, Env(state=None, data=None, out=o))
    it._style(N.Style(1, "SETFONT", [Lit("ＭＳ Ｐゴシック")]), None)
    o.print("指定")
    it._style(N.Style(1, "SETFONT"), None)
    o.printl("預設")
    assert [s.font for s in o.lines[0].parts[0].segments] == ["ＭＳ Ｐゴシック", None]


@pytest.mark.parametrize("style, expected", [("plain", 182), ("bold", 182), ("italic", 182)])
@native_windows
def test_printlc_uses_native_font_width(style, expected):
    # EmueraConsole.Print.cs:371–425；原 config 為 MS Gothic 14px，26 空白 = 182px。
    from eragvt.text.metrics import measure_text
    o = TextOutput()
    o.set_bold(style == "bold")
    o.set_italic(style == "italic")
    o.set_font("Arial")
    o.print_lc("WWWWWWWWWWWWWWWWWWWW")
    o.printl()
    text = o.lines[0].text
    # 超寬時只能刪尾空白，不能截斷原字串。
    assert text == "WWWWWWWWWWWWWWWWWWWW"
    assert measure_text(" " * 26) == expected


@native_windows
def test_drawlineform_uses_requested_pattern_and_keeps_style():
    # getStBar:543–560；Process.ScriptProc.cs:154–172 不先 Flush，線只取消粗斜體。
    o = TextOutput()
    o.set_bold()
    o.set_italic()
    o.set_color("#ff0000")
    o.print("前")
    o.drawline("―")
    assert len(o.lines) == 1
    assert o.lines[0].text == "前" + "―" * 54  # MS Gothic 14px × 54 = 756 <= 760。
    assert o.lines[0].parts[0].segments[-1].bold is False
    assert o.lines[0].parts[0].segments[-1].italic is False
    o.printl("後")
    assert o.lines[-1].parts[0].segments[0].bold


def test_html_explicit_button_and_inherited_font_color():
    # FIRSTSETTING_CHARA_SEIKAKU.ERB@FIRSTSETTING_CHARA_SEIKAKU:66–85。
    # HtmlManager.cs:853–916，按鈕只能由 button 標記產生。
    o = TextOutput()
    o.html_print("<font color='#808080'><button value='100' title='說明'>[100]選項</button></font>[2]文字")
    assert o.lines[0].buttons == [("[100]選項", 100)]
    assert o.lines[0].parts[0].title == "說明"
    assert o.lines[0].parts[0].segments[0].color == "#808080"
    assert o.lines[0].parts[-1].button is None


@native_windows
def test_web_wrap_keeps_logical_clearline():
    # PrintStringBuffer.cs:176–245：可點按鈕放不下時整顆換行；長文字分割。
    from eragvt.text.layout import render_lines
    o = TextOutput()
    o.print_plain("A" * 100)  # 700px
    o.button("[1]選項文字", 1)  # 超過剩餘60px，整顆移到下一個實體行。
    o.printl()
    rows = render_lines(o.lines)
    assert len(rows) == 2
    assert rows[0]["parts"][0]["segments"][0]["text"] == "A" * 100
    assert rows[1]["parts"][0]["button"] == 1
    assert o.linecount == 1
    o.clearline(1)
    assert render_lines(o.lines) == []


def test_temporary_invalid_system_input_preserves_menu(tmp_path):
    from eragvt.data import default_csv_dir, load_game_data
    from eragvt.game.session import GameSession
    s = GameSession(load_game_data(default_csv_dir()), tmp_path, narration=None)
    initial = [(p.text, p.button) for l in s.screen() for p in l.parts if p.button is not None]
    for _ in range(2):
        s.input(404)
        assert [(p.text, p.button) for l in s.screen() for p in l.parts if p.button is not None] == initial
        assert sum(l.text == "無効な値です" for l in s.screen()) == 1
    s.input(" 001 ")
    assert any(l.text == " 001 " for l in s.screen())  # 回顯原字串，解析仍為1。
    assert not any(l.text == "無効な値です" for l in s.screen())
    s.close()


def test_html_br_clearline_removes_whole_logical_output():
    # PrintStringBuffer.cs:187–196、242–245：HTML 的第一個實體行為 logical，其餘不是。
    o = TextOutput()
    o.printl("歷史")
    o.html_print("A<br>B<br>C")
    assert o.linecount == 2
    o.clearline(1)
    assert [l.text for l in o.lines] == ["歷史"]


@native_windows
def test_window_font_tag_and_restore():
    from eragvt.narration.windowlib import print_tagset_text
    o = TextOutput()
    o.set_font("Arial")
    print_tagset_text(o, "A@F:ＭＳ Ｐゴシック@B@/F@C", 1)
    assert [s.font for p in o.lines[0].parts for s in p.segments] == ["Arial", "ＭＳ Ｐゴシック", "Arial"]
    assert o._font == "Arial"


def test_catalog_transaction_restores_font_and_temporary_output():
    # 既有 S29 交易契約：輸出字型／未換行緩衝／暫時行一起回復。
    from types import SimpleNamespace
    from eragvt.narration.service import _Tx
    from eragvt.state import GameState, GameRng
    o = TextOutput()
    o.set_font("Arial")
    o.print_temporary("原暫時行")
    o.print("原緩衝")
    st = GameState()
    st.rng = GameRng(87)
    ctx = SimpleNamespace(state=st, out=o)
    before = st.rng.snapshot()
    tx = _Tx(ctx)
    o.set_font("ＭＳ Ｐゴシック")
    o.printl("新行")
    st.result[0] = 42
    st.rng.rand(3)
    tx.rollback()
    assert o._font == "Arial"
    assert [line.text for line in o.lines] == ["原暫時行"]
    assert st.result[0] == 0 and st.rng.snapshot() == before
    o.printl()
    assert [line.text for line in o.lines] == ["原緩衝"]


@native_windows
def test_web_native_segment_width_and_space(tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.data import load_game_data, default_csv_dir
    from eragvt.web import create_app
    app = create_app(load_game_data(default_csv_dir()), tmp_path, narration=None)
    s = app.state.session
    s.out.drain()
    s.out.html_print("<nobr>A<shape type='space' param='150'><button value='2' title='說明'>[2]B<shape type='space' param='100'></button></nobr>")
    with TestClient(app) as client:
        page = client.get("/").text
        assert 'width: 21px' in page
        assert 'width:7px' in page
        assert 'value="2" title="說明"' in page
        from html.parser import HTMLParser
        class Check(HTMLParser):
            def __init__(self): super().__init__(); self.in_button = False; self.found = False
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "button": self.in_button = attrs.get("value") == "2"
                if attrs.get("class") == "shape-space" and "14px" in attrs.get("style", ""):
                    self.found = self.in_button
            def handle_endtag(self, tag):
                if tag == "button": self.in_button = False
        check = Check(); check.feed(page)
        assert check.found
    s.close()
