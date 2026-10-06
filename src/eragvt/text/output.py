"""era PRINT 系列 → 結構化行。

後端把遊戲輸出累積成 `Line` 列表，Web 端只負責渲染；遊戲邏輯不直接產生 HTML。
對應關係：PRINT = `print`、PRINTL = `printl`、PRINTW = `printw`、PRINTPLAIN = `print_plain`、
PRINTBUTTON = `button`、DRAWLINE = `drawline`、WAIT = `wait`、SETCOLOR／RESETCOLOR = `set_color`／`reset_color`、
FONTBOLD = `set_bold(True)`、FONTITALIC = `set_italic(True)`、FONTREGULAR = `set_bold(False)`（太字・斜体とも解除）、
CLEARLINE = `clearline`。

按鈕的切法照 Emuera：一行裡「PRINT 累積、尚未變成按鈕」的文字，在換行或 PRINTBUTTON／PRINTPLAIN 時
整段交給 `split_buttons` 判定（reference/emuera-1824/Emuera/GameView/PrintStringBuffer.cs@fromCssToButton:275、
@createButtons:325；GameView/ButtonStringCreator.cs）。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .metrics import DRAWABLE_WIDTH, FONT_SIZE, measure_text

from ..data.csv_loader import read_int64  # LexicalAnalyzer.ReadInt64 的移植

# LexicalAnalyzer.IsWhiteSpace / SkipAllSpace（Sub/LexicalAnalyzer.cs:707–728）
_WS = " \t　"
# ButtonStringCreator.cs:169（.NET 的 \s 與 Python 的 \s 都含全形空白）
_NUM_REG = re.compile(r"\[\s*([0][xXbB])?[+-]?[0-9]+([eEpP][0-9]+)?\s*\]")


@dataclass(frozen=True)
class Segment:
    text: str
    color: str | None = None  # "#rrggbb"；None = 預設色
    bold: bool = False
    italic: bool = False  # FONTITALIC（S20）
    font: str | None = None  # SETFONT；None回到Web預設字型。


@dataclass
class Part:
    """一個顯示單位（Emuera 的 ConsoleButtonString）：可點擊時 `button` 為送出的值。"""

    segments: list[Segment]
    button: int | None = None
    title: str | None = None  # HTML_PRINT の <nonbutton title='…'>（ツールチップ）

    space_px: int | None = None  # HTML shape(space) 的整數像素寬。

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.segments)


@dataclass
class Line:
    parts: list[Part] = field(default_factory=list)
    kind: Literal["text", "drawline"] = "text"
    wait: bool = False  # 顯示到此行後等待玩家輸入（PRINTW／WAIT）
    align: Literal["left", "center", "right"] = "left"  # ALIGNMENT

    logical_start: bool = True  # HTML 的 br 只分實體行，整次 HTML_PRINT 是一個論理行。
    nobr: bool = False  # HTML nobr 禁止折行。
    temporary: bool = False  # 下一個已完成行取代本行。

    @property
    def text(self) -> str:
        return "".join(p.text for p in self.parts)

    @property
    def buttons(self) -> list[tuple[str, int]]:
        return [(p.text, p.button) for p in self.parts if p.button is not None]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _hex_color(color: str | tuple[int, int, int]) -> str:
    if isinstance(color, tuple):
        for c in color:
            if not 0 <= c <= 255:
                raise ValueError(f"顏色分量超出範圍：{color!r}")
        r, g, b = color
        return f"#{r:02x}{g:02x}{b:02x}"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(f"顏色格式應為 #rrggbb：{color!r}")
    return color.lower()


# --- ButtonStringCreator 移植 ------------------------------------------------


def _lex(s: str) -> list[str] | None:
    """`ButtonStringCreator.lex`:227–275："[1] あ [2] いうえ " → ["[1]"," ","あ"," ","[2]"," ","いうえ"," "]。
    `[` 巢狀或多餘的 `]` → None（整行不做按鈕）。"""
    strs: list[str] = []
    state = 0
    start = 0
    i = 0

    def reduce() -> None:
        nonlocal start
        if i == start:
            return
        strs.append(s[start:i])
        start = i

    while i < len(s):
        c = s[i]
        if c == "[":
            if state == 1:
                return None
            reduce()
            state = 1
            i += 1
        elif c == "]":
            if state != 1:
                return None
            i += 1
            reduce()
            state = 0
        elif state == 0 and c in _WS:
            reduce()
            while i < len(s) and s[i] in _WS:
                i += 1
            reduce()
        else:
            i += 1
    reduce()
    return strs


def _button_core(word: str) -> int | None:
    """`isButtonCore`:176–204：`[數字]` 形式則回傳數值。"""
    if len(word) < 3 or word[0] != "[" or word[-1] != "]":
        return None
    if not _NUM_REG.search(word):
        return None
    inner = word[1:-1].lstrip(_WS)
    try:
        value, _ = read_int64(inner, 0) if inner else (0, 0)
    except (ValueError, IndexError):
        return None
    return value


def split_buttons(text: str) -> list[tuple[str, int | None]]:
    """`ButtonStringCreator.syn`:35–167：把一段待輸出文字切成 `(字串, 按鈕值或 None)`。

    - 沒有 `[數字]` 或只有一個：整段是一個單位（有一個時整段都可點，值為該數字）。
    - 兩個以上：依說明文字在按鈕左側／右側／兩側決定切法；兩側都有時以 2 個以上空白分隔。
    """
    if text == "":
        return [("", None)]
    if "[" not in text or "]" not in text:
        return [(text, None)]
    strs = _lex(text)
    if strs is None:
        return [(text, None)]
    before_button = False
    after_button = False
    button_count = 0
    inp = 0
    for w in strs:
        if w == "":
            continue
        if w[0] in _WS:
            continue
        v = _button_core(w)
        if v is not None:
            button_count += 1
            inp = v
            after_button = False
        else:
            after_button = True
            if button_count == 0:
                before_button = True
    if button_count <= 1:
        return [(text, inp if button_count >= 1 else None)]

    align_right = not before_button and after_button
    align_left = before_button and not after_button
    align_etc = not align_right and not align_left
    ret: list[tuple[str, int | None]] = []
    buffer: list[str] = []
    can_select = False
    value = 0
    state = 0

    def reduce() -> None:
        nonlocal can_select, value
        if not buffer:
            return
        ret.append(("".join(buffer), value if can_select else None))
        buffer.clear()
        can_select = False
        value = 0

    for w in strs:
        if w == "":
            continue
        if w[0] in _WS:
            if (state & 3) == 3 and align_etc and len(w) >= 2:
                reduce()
                buffer.append(w)
                state = 0
            else:
                buffer.append(w)
            continue
        v = _button_core(w)
        if v is not None:
            if (state & 1) == 1 or align_right:
                reduce()
                buffer.append(w)
                value, can_select, state = v, True, 1
            elif align_left:
                buffer.append(w)
                value, can_select = v, True
                reduce()
                state = 0
            else:
                buffer.append(w)
                value, can_select, state = v, True, 1
            continue
        buffer.append(w)
        state |= 2
    reduce()
    return ret


def _divide(segments: list[Segment], pieces: list[tuple[str, int | None]]) -> list[Part]:
    """`createButtons`:325–388：把樣式段落依按鈕邊界切開。"""
    parts: list[Part] = []
    queue = list(segments)
    for text, value in pieces:
        need = len(text)
        got: list[Segment] = []
        while need > 0 and queue:
            seg = queue.pop(0)
            if len(seg.text) <= need:
                got.append(seg)
                need -= len(seg.text)
            else:
                got.append(Segment(seg.text[:need], seg.color, seg.bold, seg.italic, seg.font))
                queue.insert(0, Segment(seg.text[need:], seg.color, seg.bold, seg.italic, seg.font))
                need = 0
        parts.append(Part(got, value))
    return parts


# --- 輸出緩衝 ----------------------------------------------------------------


_HTML_TAG = re.compile(r"<(/?)([A-Za-z]+)((?:\s+[A-Za-z]+\s*=\s*'[^']*')*)\s*>")
_HTML_ATTR = re.compile(r"([A-Za-z]+)\s*=\s*'([^']*)'")
_HTML_ENT = {"nbsp": " ", "amp": "&", "gt": ">", "lt": "<", "quot": '"', "apos": "'"}


def _html_unescape(text: str) -> str:
    """`HtmlManager.Unescape`:398–455：`&名前;` と `&#10進;`／`&#x16進;`。"""

    def rep(m: re.Match) -> str:
        w = m.group(1).lower()
        if w in _HTML_ENT:
            return _HTML_ENT[w]
        if w.startswith("#x"):
            return chr(int(w[2:], 16))
        if w.startswith("#"):
            return chr(int(w[1:]))
        raise NotImplementedError(f"HTML_PRINT：不明な文字参照 &{w};")

    return re.sub(r"&([^;&]+);", rep, text)


def _parse_html(html: str) -> list[list[Part]]:
    """HTML → 表示行のリスト（`<br>` で改行：HtmlManager.cs@Html2DisplayLine:326–331、PrintStringBuffer.cs@ButtonsToDisplayLines:
    189–196／:242–245：`<br>` ごとにそこまでを 1 行（空でも）にし、残りが空でなければ最後の 1 行）。"""
    lines: list[list[Part]] = []
    parts: list[Part] = []
    colors: list[str | None] = [None]
    title: str | None = None
    pos = 0
    button: int | None = None
    fraction = 0.5

    def add(text: str) -> None:
        if text:
            parts.append(Part([Segment(_html_unescape(text), colors[-1])], button=button, title=title))

    for m in _HTML_TAG.finditer(html):
        add(html[pos : m.start()])
        pos = m.end()
        close, tag, attrs = m.group(1) == "/", m.group(2).lower(), dict(_HTML_ATTR.findall(m.group(3)))
        if tag == "font":
            if close:
                colors.pop()
            else:
                colors.append(_hex_color(attrs["color"]) if "color" in attrs else colors[-1])
        elif tag in ("nonbutton", "button"):
            # HtmlManager.cs:853–916：原作實用的數字按鈕與說明。
            title = None if close else _html_unescape(attrs.get("title", "")) or None
            button = None if close or tag == "nonbutton" else int(_html_unescape(attrs["value"]))
        elif tag == "br" and not close:  # HtmlManager.cs@tagAnalyze:672–676
            lines.append(parts)
            parts = []
        elif tag == "nobr":  # :677–685（行の折り返し禁止。Web 側は折り返さないので表示上の違いなし）
            pass
        elif tag == "shape" and not close and attrs.get("type") == "space" and attrs.get("param", "").isdigit():
            # :784–851 → ConsoleShapePart.cs:40–53：幅 param% × フォントサイズの空白。
            # ConsoleSpacePart.SetWidth:169–173：截整後的餘數傳給下一個 part。
            width = fraction + int(attrs["param"]) * FONT_SIZE / 100
            pixels = int(width)
            fraction = width - pixels
            parts.append(Part([], button=button, title=title, space_px=pixels))
        else:
            raise NotImplementedError(f"HTML_PRINT：未対応のタグ <{m.group(0)}>")
    add(html[pos:])
    if parts:
        lines.append(parts)
    return lines


class TextOutput:
    def __init__(self) -> None:
        self._lines: list[Line] = []
        self._parts: list[Part] = []  # 本行已確定的單位
        self._pending: list[Segment] = []  # PRINT 累積、尚未判定按鈕的文字
        self._color: str | None = None
        self._bgcolor = "#000000"  # emuera.config:25；EmueraConsole.Print.cs:18。
        self._bold = False
        self._italic = False
        self._font: str | None = None
        self._align: Literal["left", "center", "right"] = "left"
        # WAIT／PRINTW の累計回数（EVENTCOMEND 後の自動 WAIT 判定用：Process.SystemProc.cs:476、515–517）
        self.wait_count = 0

    # --- 樣式 ---------------------------------------------------------------

    def set_color(self, color: str | tuple[int, int, int]) -> None:
        self._color = _hex_color(color)

    def reset_color(self) -> None:
        self._color = None

    def set_bgcolor(self, color: str | tuple[int, int, int]) -> None:
        """Console 背景色：reference/emuera-1824/Emuera/GameView/EmueraConsole.Print.cs:78–81。"""
        self._bgcolor = _hex_color(color)

    def reset_bgcolor(self) -> None:
        """RESETBGCOLOR：Instraction.Child.cs:1070–1081；本作 Config 背景為黑色。"""
        self._bgcolor = "#000000"

    @property
    def bgcolor(self) -> str:
        return self._bgcolor

    @property
    def color(self) -> str | None:
        """現在の文字色（"#rrggbb"、既定色なら None）。GETCOLOR の代わり。"""
        return self._color

    def set_bold(self, bold: bool = True) -> None:
        """FONTBOLD（True）／FONTREGULAR（False）。FONTREGULAR は FontStyle.Regular にするので斜体も解除する
        （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@FONTREGULAR_Instruction:1110–1121）。"""
        self._bold = bold
        if not bold:
            self._italic = False

    def set_italic(self, italic: bool = True) -> None:
        """FONTITALIC：現在のスタイルに Italic を加える（Instraction.Child.cs@FONTITALIC_Instruction:1097–1108、太字は保つ）。"""
        self._italic = italic

    def set_font(self, font: str | None = None) -> None:
        """SETFONT：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:486–492；
        Emuera/GameView/EmueraConsole.Print.cs:60：空字串／省略恢復設定字型。"""
        self._font = font or None

    def set_align(self, align: Literal["left", "center", "right"]) -> None:
        """ALIGNMENT LEFT/CENTER/RIGHT（行単位）。"""
        self._align = align

    # --- 輸出 ---------------------------------------------------------------

    def print(self, text: str) -> None:
        """PRINT：不換行；按鈕在換行時整段判定。"""
        if text:
            self._pending.append(Segment(text, self._color, self._bold, self._italic, self._font))

    def print_plain(self, text: str) -> None:
        """PRINTPLAIN：先結算前面的文字，再加入不可點的單位（PrintStringBuffer.cs@AppendPlainText:109）。"""
        self._resolve_pending()
        if text:
            self._parts.append(Part([Segment(text, self._color, self._bold, self._italic, self._font)]))

    def button(self, label: str, value: int, *, title: str | None = None) -> None:
        """PRINTBUTTON：明確指定按鈕值（@AppendButton:100）。

        手翻HTML選單可直接傳title：reference/emuera-1824/Emuera/GameView/HtmlManager.cs:853–916。
        """
        self._resolve_pending()
        self._parts.append(Part([Segment(label, self._color, self._bold, self._italic, self._font)], value, title))

    def print_lc(self, text: str) -> None:
        """PRINTLC：EmueraConsole.Print.cs:363–425；每欄為獨立按鈕判定邊界。"""
        if not text:
            return
        n = len(text.encode("cp932", errors="replace"))
        if n < 26:
            text += " " * (26 - n)
            limit = measure_text(" " * 26)
            if limit is not None:
                while measure_text(text, self._font, self._bold, self._italic) > limit and text.endswith(" "):
                    text = text[:-1]
            # DEVIATION：非 Windows 的既有 cp932 補白近似保留，見 metrics.py。
        # PrintStringBuffer.cs:63–89，force_button 在欄位前後各結算一次。
        self._resolve_pending()
        self.print(text)
        self._resolve_pending()

    def html_print(self, html: str) -> None:
        """HTML_PRINT（GameProc/Function/Instraction.Child.cs:239–257 → GameView/EmueraConsole.Print.cs@PrintHtml:344–357）：
        空文字なら何もしない；未換行の PRINT 文字列を先に 1 行として確定し、HTML を独立した行として追加する。
        HTML 内の `[数字]` は按鈕化されない（按鈕は `<button>` タグのみ：GameView/HtmlManager.cs@Html2DisplayLine:266–）。
        文字は Unescape（HtmlManager.cs@Unescape:398–）以外そのまま（空白を詰めない）。色は HTML 側の既定（SETCOLOR は効かない）。
        対応タグは原作で使う `<font color='#rrggbb'>`・`<nonbutton title='…'>`・`<br>`（行を分ける）・`<nobr>`・
        `<shape type='space' param='n'>` 與數字 `<button>`（其他標記停止）。"""
        if not html:
            return
        self._flush_partial()
        # 實用子集；未知標記停止，不能靜默丟棄。
        for i, parts in enumerate(_parse_html(html)):
            self._append_line(Line(parts, logical_start=(i == 0), nobr=bool(re.search(r"<nobr\s*>", html, re.I))))

    def printl(self, text: str = "") -> None:
        """PRINTL：輸出後換行。"""
        self.print(text)
        self._newline()

    def printw(self, text: str = "") -> None:
        """PRINTW：輸出、換行並等待輸入。"""
        self.print(text)
        self._newline(wait=True)

    def drawline(self, pattern: str = "─") -> None:
        """DRAWLINEFORM：EmueraConsole.Print.cs:513–560；在既有緩衝後加入線再換行。"""
        if not pattern:
            raise ValueError("空文字列によるDRAWLINEが行われました")
        width = measure_text(pattern)
        if width is None:
            # DEVIATION：非 Windows 沿用既有分隔線；未取得 GDI 計量不偽造字串數。
            self._flush_partial()
            self._append_line(Line(kind="drawline"))
            return
        bar, width = pattern, 0
        while width < DRAWABLE_WIDTH:
            bar += pattern
            width = measure_text(bar)
        while width > DRAWABLE_WIDTH:
            bar = bar[:-1]
            width = measure_text(bar)
        bold, italic = self._bold, self._italic
        self._bold = self._italic = False
        self.print(bar)
        self._bold, self._italic = bold, italic
        self._newline()
        self._lines[-1].kind = "drawline"

    def print_temporary(self, text: str) -> None:
        """PrintTemporaryLine：EmueraConsole.Print.cs:201–204、295–308。"""
        if not text:
            return
        self._flush_partial()
        self.print(text)
        self._newline()
        self._lines[-1].temporary = True

    def wait(self) -> None:
        """WAIT：在目前位置等待輸入。"""
        self.wait_count += 1
        if self._pending or self._parts:
            self._newline(wait=True)
        elif self._lines:
            self._lines[-1].wait = True
        else:
            self._lines.append(Line(wait=True))

    def clearline(self, n: int) -> None:
        """CLEARLINE：Instraction.Child.cs:488–500 直接 deleteLine、不 Flush。
        EmueraConsole.Print.cs:156–176 刪論理行；尚未換行的緩衝原本就不刪。
        """
        while n > 0 and self._lines:
            if self._lines.pop().logical_start:
                n -= 1

    # --- 取出 ---------------------------------------------------------------

    @property
    def lines(self) -> list[Line]:
        """已完成的行（不含尚未換行的部分）。"""
        return list(self._lines)

    @property
    def linecount(self) -> int:
        """LINECOUNT：VariableToken.cs:1537 → EmueraConsole.Print.cs:103、140–141。
        回傳論理行數，不是實體折行數。
        """
        return sum(line.logical_start for line in self._lines)

    def drain(self) -> list[Line]:
        """取出並清空已完成的行，交給前端。未換行的部分留著。"""
        out, self._lines = self._lines, []
        return out

    def _resolve_pending(self) -> None:
        if not self._pending:
            return
        text = "".join(s.text for s in self._pending)
        self._parts.extend(_divide(self._pending, split_buttons(text)))
        self._pending = []

    def _newline(self, wait: bool = False) -> None:
        if wait:
            self.wait_count += 1
        self._resolve_pending()
        self._append_line(Line(self._parts, wait=wait, align=self._align))
        self._parts = []

    def _append_line(self, line: Line) -> None:
        # EmueraConsole.Print.cs:110–114；PRINT 本身不會刪暫時行，只有完成行會。
        if self._lines and self._lines[-1].temporary:
            self.clearline(1)
        self._lines.append(line)

    def _flush_partial(self) -> None:
        if self._pending or self._parts:
            self._newline()
