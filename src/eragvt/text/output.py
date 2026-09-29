"""era PRINT 系列 → 結構化行。

後端把遊戲輸出累積成 `Line` 列表，Web 端只負責渲染；遊戲邏輯不直接產生 HTML。
對應關係：PRINT = `print`、PRINTL = `printl`、PRINTW = `printw`、DRAWLINE = `drawline`、
WAIT = `wait`、SETCOLOR／RESETCOLOR = `set_color`／`reset_color`、FONTBOLD／FONTREGULAR = `set_bold`、
PRINTBUTTON = `button`、CLEARLINE = `clearline`。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# `[n]`（可含空白、負號）→ Emuera 會把這種文字變成可點的按鈕。
_BUTTON_RE = re.compile(r"\[\s*(-?\d+)\s*\]")


@dataclass(frozen=True)
class Segment:
    text: str
    color: str | None = None  # "#rrggbb"；None = 預設色
    bold: bool = False
    button: int | None = None  # 點擊後送出的值


@dataclass
class Line:
    segments: list[Segment] = field(default_factory=list)
    kind: Literal["text", "drawline"] = "text"
    wait: bool = False  # 顯示到此行後等待玩家輸入（PRINTW／WAIT）

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.segments)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _hex_color(color: str | tuple[int, int, int]) -> str:
    if isinstance(color, tuple):
        r, g, b = color
        for c in color:
            if not 0 <= c <= 255:
                raise ValueError(f"顏色分量超出範圍：{color!r}")
        return f"#{r:02x}{g:02x}{b:02x}"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(f"顏色格式應為 #rrggbb：{color!r}")
    return color.lower()


def split_buttons(text: str, color: str | None = None, bold: bool = False) -> list[Segment]:
    """把含 `[n]` 的字串切成段落：每個 `[n]` 到下一個 `[` 按鈕或字串尾為一顆按鈕。

    Emuera 的實際判定更細（見 docs/wiki/python/state.md），這裡取主選單常見寫法
    `[101]出撃する　[102]鍛錬する` 能正確切開的簡化版。
    """
    matches = list(_BUTTON_RE.finditer(text))
    if not matches:
        return [Segment(text, color, bold)] if text else []
    segs: list[Segment] = []
    if matches[0].start() > 0:
        segs.append(Segment(text[: matches[0].start()], color, bold))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segs.append(Segment(text[m.start() : end], color, bold, int(m.group(1))))
    return segs


class TextOutput:
    def __init__(self) -> None:
        self._lines: list[Line] = []
        self._current: list[Segment] = []
        self._color: str | None = None
        self._bold = False

    # --- 樣式 ---------------------------------------------------------------

    def set_color(self, color: str | tuple[int, int, int]) -> None:
        self._color = _hex_color(color)

    def reset_color(self) -> None:
        self._color = None

    def set_bold(self, bold: bool = True) -> None:
        self._bold = bold

    # --- 輸出 ---------------------------------------------------------------

    def print(self, text: str) -> None:
        """PRINT：不換行，`[n]` 自動成為按鈕。"""
        self._current.extend(split_buttons(text, self._color, self._bold))

    def print_plain(self, text: str) -> None:
        """PRINTPLAIN：不做按鈕轉換。"""
        if text:
            self._current.append(Segment(text, self._color, self._bold))

    def button(self, label: str, value: int) -> None:
        """PRINTBUTTON：明確指定按鈕值。"""
        self._current.append(Segment(label, self._color, self._bold, value))

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
        if self._current:
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

    def _newline(self, wait: bool = False) -> None:
        self._lines.append(Line(self._current, wait=wait))
        self._current = []

    def _flush_partial(self) -> None:
        if self._current:
            self._newline()
