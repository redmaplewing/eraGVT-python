"""era PRINT 系列 → 結構化行。

後端把遊戲輸出累積成 `Line` 列表，Web 端只負責渲染；遊戲邏輯不直接產生 HTML。
對應關係：PRINT = `print`、PRINTL = `printl`、PRINTW = `printw`、PRINTPLAIN = `print_plain`、
PRINTBUTTON = `button`、DRAWLINE = `drawline`、WAIT = `wait`、SETCOLOR／RESETCOLOR = `set_color`／`reset_color`、
FONTBOLD／FONTREGULAR = `set_bold`、CLEARLINE = `clearline`。

按鈕的切法照 Emuera：一行裡「PRINT 累積、尚未變成按鈕」的文字，在換行或 PRINTBUTTON／PRINTPLAIN 時
整段交給 `split_buttons` 判定（reference/emuera-1824/Emuera/GameView/PrintStringBuffer.cs@fromCssToButton:275、
@createButtons:325；GameView/ButtonStringCreator.cs）。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

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


@dataclass
class Part:
    """一個顯示單位（Emuera 的 ConsoleButtonString）：可點擊時 `button` 為送出的值。"""

    segments: list[Segment]
    button: int | None = None

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.segments)


@dataclass
class Line:
    parts: list[Part] = field(default_factory=list)
    kind: Literal["text", "drawline"] = "text"
    wait: bool = False  # 顯示到此行後等待玩家輸入（PRINTW／WAIT）
    align: Literal["left", "center", "right"] = "left"  # ALIGNMENT

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
                got.append(Segment(seg.text[:need], seg.color, seg.bold))
                queue.insert(0, Segment(seg.text[need:], seg.color, seg.bold))
                need = 0
        parts.append(Part(got, value))
    return parts


# --- 輸出緩衝 ----------------------------------------------------------------


class TextOutput:
    def __init__(self) -> None:
        self._lines: list[Line] = []
        self._parts: list[Part] = []  # 本行已確定的單位
        self._pending: list[Segment] = []  # PRINT 累積、尚未判定按鈕的文字
        self._color: str | None = None
        self._bold = False
        self._align: Literal["left", "center", "right"] = "left"
        # WAIT／PRINTW の累計回数（EVENTCOMEND 後の自動 WAIT 判定用：Process.SystemProc.cs:476、515–517）
        self.wait_count = 0

    # --- 樣式 ---------------------------------------------------------------

    def set_color(self, color: str | tuple[int, int, int]) -> None:
        self._color = _hex_color(color)

    def reset_color(self) -> None:
        self._color = None

    def set_bold(self, bold: bool = True) -> None:
        self._bold = bold

    def set_align(self, align: Literal["left", "center", "right"]) -> None:
        """ALIGNMENT LEFT/CENTER/RIGHT（行単位）。"""
        self._align = align

    # --- 輸出 ---------------------------------------------------------------

    def print(self, text: str) -> None:
        """PRINT：不換行；按鈕在換行時整段判定。"""
        if text:
            self._pending.append(Segment(text, self._color, self._bold))

    def print_plain(self, text: str) -> None:
        """PRINTPLAIN：先結算前面的文字，再加入不可點的單位（PrintStringBuffer.cs@AppendPlainText:109）。"""
        self._resolve_pending()
        if text:
            self._parts.append(Part([Segment(text, self._color, self._bold)]))

    def button(self, label: str, value: int) -> None:
        """PRINTBUTTON：明確指定按鈕值（@AppendButton:100）。"""
        self._resolve_pending()
        self._parts.append(Part([Segment(label, self._color, self._bold)], value))

    def print_lc(self, text: str) -> None:
        """PRINTLC：左寄せ列。`PRINTCの文字数:25`（emuera.config）に対し、cp932 バイト数で 26 まで空白を補う
        （GameView/EmueraConsole.Print.cs@CreateTypeCString:383–425）。改行しない。
        DEVIATION: 原作はさらにフォント幅で末尾空白を削るが、ここでは等幅前提でバイト数のみ（表示のみの差）。"""
        if not text:
            return  # PrintC:364–365
        n = len(text.encode("cp932", errors="replace"))
        if n < 26:
            text += " " * (26 - n)
        self.print(text)

    def printl(self, text: str = "") -> None:
        """PRINTL：輸出後換行。"""
        self.print(text)
        self._newline()

    def printw(self, text: str = "") -> None:
        """PRINTW：輸出、換行並等待輸入。"""
        self.print(text)
        self._newline(wait=True)

    def drawline(self) -> None:
        """DRAWLINE：水平線（字元由前端決定，原作為 `_Replace.csv` 的 `─`）。"""
        self._flush_partial()
        self._lines.append(Line(kind="drawline"))

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
        """CLEARLINE n：刪除最後 n 行（已完成的行）。"""
        if n > 0:
            del self._lines[-n:]

    # --- 取出 ---------------------------------------------------------------

    @property
    def lines(self) -> list[Line]:
        """已完成的行（不含尚未換行的部分）。"""
        return list(self._lines)

    @property
    def linecount(self) -> int:
        """era `LINECOUNT` 的對應（已完成行數）。"""
        return len(self._lines)

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
        self._lines.append(Line(self._parts, wait=wait, align=self._align))
        self._parts = []

    def _flush_partial(self) -> None:
        if self._pending or self._parts:
            self._newline()
