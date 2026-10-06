"""Web 實體行；TextOutput 保留論理行，CLEARLINE 不依瀏覽器排版計數。

reference/emuera-1824/Emuera/GameView/PrintStringBuffer.cs:176–245、480–536：
760px 原畫布、ButtonWrap=YES、非按鈕可拆行；nobr 不折行。
同檔:397–415／ConsoleButtonString.cs:169–185，各樣式段獨立計量。
"""
from __future__ import annotations

from dataclasses import replace
import json

from .metrics import DRAWABLE_WIDTH, display_font, measure_text
from .output import Line, Part, Segment


def _width(part: Part) -> int:
    if part.space_px is not None:
        return part.space_px
    return sum(measure_text(s.text, s.font, s.bold, s.italic) or 0 for s in part.segments)


def _split(part: Part, available: int) -> tuple[Part | None, Part | None]:
    """依各段字寬找可容納前綴；shape 不可分割。"""
    if part.space_px is not None:
        return None, part
    left: list[Segment] = []
    right: list[Segment] = []
    for i, seg in enumerate(part.segments):
        width = measure_text(seg.text, seg.font, seg.bold, seg.italic)
        if width <= available:
            left.append(seg)
            available -= width
            continue
        low, high = 0, len(seg.text)
        while low < high:
            mid = (low + high + 1) // 2
            if measure_text(seg.text[:mid], seg.font, seg.bold, seg.italic) <= available:
                low = mid
            else:
                high = mid - 1
        if low:
            left.append(replace(seg, text=seg.text[:low]))
        right = [replace(seg, text=seg.text[low:])] + part.segments[i + 1:]
        break
    return (replace(part, segments=left) if left else None, replace(part, segments=right) if right else None)


def _rows(line: Line) -> list[Line]:
    if line.nobr or measure_text(" ") is None:
        return [line]
    rows, parts, used = [], [], 0
    pending = list(line.parts)
    while pending:
        part = pending.pop(0)
        width = _width(part)
        if used + width <= DRAWABLE_WIDTH:
            parts.append(part)
            used += width
            continue
        if part.button is not None and parts:
            rows.append(replace(line, parts=parts, wait=False))
            parts, used = [], 0
            pending.insert(0, part)
            continue
        left, right = _split(part, DRAWABLE_WIDTH - used)
        if left is not None:
            parts.append(left)
        if left is None and not parts:
            # 引擎不能拆分的 shape 允許超過畫布，不無限重排。
            parts.append(part)
            continue
        rows.append(replace(line, parts=parts, wait=False))
        parts, used = [], 0
        if right is not None:
            pending.insert(0, right)
    if parts or not rows:
        rows.append(replace(line, parts=parts))
    elif line.wait:
        rows[-1].wait = True
    return rows


def render_lines(lines: list[Line]) -> list[dict]:
    return [row.to_json() for line in lines for row in _rows(line)]


def segment_style(seg: dict) -> str:
    """字型名使用 CSS 字串跳脫；固定每段 GDI advance，避免瀏覽器字寬累積偏移。"""
    style = []
    if seg["color"]:
        style.append(f"color:{seg['color']}")
    if seg["bold"]:
        style.append("font-weight:bold")
    if seg["italic"]:
        style.append("font-style:italic")
    family = display_font(seg["font"])
    if family:
        style.append("font-family:" + json.dumps(family, ensure_ascii=False))
    width = measure_text(seg["text"], seg["font"], seg["bold"], seg["italic"])
    if width is not None:
        style.extend(("display:inline-block", f"width:{width}px"))
    return ";".join(style)
