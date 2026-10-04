"""カラーバー等の表示部品：`汎用関数/コモン関数.ERB`（@COLOR_BAR:19–75、@COLORSENTENCE_BAR:79–111、
@COLORSENTENCE_BARCOLOR:192–203、@PERCENT_CAL:216–221、@PERCENT_CAL_F:224–229）と
`汎用関数/SETCOLOR_BY_STR.ERB`（@SETCOLOR_BY_STR:10–55、@COLORCHIP:64–73）。路徑相對 `source/earGVP/ERB/`。

表示のみ（代入は関数の LOCAL だけ、RAND なし）。SETCOLOR の範囲外（0 未満・255 超）は原作では CodeEE
（reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:399–402）なので ValueError にする。
"""

from __future__ import annotations

from ..text import TextOutput
from .era import div, format_curly, format_percent


def setcolor(out: TextOutput, r: int, g: int, b: int) -> None:
    """`SETCOLOR r, g, b`（Process.ScriptProc.cs:381–406：0〜255 以外は CodeEE）。"""
    if min(r, g, b) < 0 or max(r, g, b) > 255:
        raise ValueError(f"SETCOLOR の引数が範囲外：{r},{g},{b}")
    out.set_color((r, g, b))


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def color_bar(out: TextOutput, a1: int, a2: int, a3: int = 20, r: int = 160, g: int = 160, b: int = 160, a7: int = -80,
              a8: int = 0, a9: int = 0, a10: int = 0, a11: int = 1, s1: str = "▂", s2: str = "▁") -> int:
    """`@COLOR_BAR(現在値, 最大値, 長さ, R, G, B, 背景色相差, R加算, G加算, B加算, 変化頻度, ゲージ文字, 背景文字)`:19–75。
    最大値 0 は原作でも 0 除算エラー（ZeroDivisionError）。戻り値は RETURN 1（RESULT:0 のみ：模型化しない）。"""
    l1 = div(a1 * a3, a2)  # :22
    l4, l5, l6 = _clamp(r + a7), _clamp(g + a7), _clamp(b + a7)  # :24–38
    l100 = 0
    l101 = 0
    for i in range(a3):  # :39 FOR LOCAL, 0, ARG:3
        if l1 > i:
            if l100 < a11:
                setcolor(out, r, g, b)
                l100 += 1
            else:
                r, g, b = _clamp(r + a8), _clamp(g + a9), _clamp(b + a10)
                setcolor(out, r, g, b)
                l100 = 0
            out.print(s1)
        else:
            if not l101:
                setcolor(out, l4, l5, l6)
                l101 = 1
            out.print(s2)
    out.reset_color()  # :72
    return 1


def percent_cal(a: int, b: int) -> int:
    """`@PERCENT_CAL`／`@PERCENT_CAL_F`:216–229：どちらかが 0 なら 0、それ以外 a*100/b。"""
    if a == 0 or b == 0:
        return 0
    return div(a * 100, b)


def colorsentence_barcolor(out: TextOutput, cur: int, mx: int) -> None:
    """`@COLORSENTENCE_BARCOLOR, ARG:0, ARG:1`:192–203（50% 以上は色を変えない）。"""
    if cur == 0:
        setcolor(out, 255, 0, 0)
        return
    p = percent_cal(cur, mx)
    if p < 25:
        setcolor(out, 255, 123, 0)
    elif p < 50:
        setcolor(out, 255, 255, 0)


_BAR_COLORS = {"体力": (215, 105, 30), "気力": (60, 75, 215), "性耐性": (255, 90, 120), "射精": (215, 180, 105),
               "噴乳": (255, 220, 205)}


def colorsentence_bar(out: TextOutput, name: str, width: int, cur: int, mx: int, length: int) -> None:
    """`@COLORSENTENCE_BAR, ARGS, ARG:0〜3`:79–111（名前・カラーバー・（現在/最大））。"""
    colored = name not in ("射精", "噴乳")
    if colored:
        colorsentence_barcolor(out, cur, mx)
    out.print(format_percent(name, width, True) + "　  ")  # :84
    r, g, b = _BAR_COLORS.get(name, (0, 0, 0))  # :87–107（該当なしは ARG:4〜6 = 0）
    out.print("₍")
    color_bar(out, cur, mx, length, r, g, b, -160, 10, 18, 6, 2, "▮", "▮")
    if colored:
        colorsentence_barcolor(out, cur, mx)
    out.print("₎")
    out.print(f"（{format_curly(cur, 5)}/{format_curly(mx, 5)}）")
    out.reset_color()


# --- SETCOLOR_BY_STR.ERB -------------------------------------------------------------------

_NAMED_COLORS = (
    (("赤", "レッド"), (255, 8, 8)),
    (("緑", "グリーン"), (8, 255, 125)),
    (("青", "ブルー"), (8, 125, 255)),
    (("黄", "イエロー"), (245, 245, 125)),
    (("金", "ブロンド", "ゴールド"), (255, 255, 8)),
    (("紫", "パープル"), (255, 8, 255)),
    (("橙", "オレンジ"), (255, 125, 8)),
    (("桃", "ピンク"), (255, 8, 125)),
    (("銀", "シルバー"), (200, 200, 255)),
    (("茶", "ブラウン", "ブルネット"), (88, 8, 8)),
    (("黒", "ブラック"), (40, 24, 24)),
    (("肌色",), (255, 200, 180)),
    (("褐色",), (183, 86, 17)),
    (("色白",), (255, 236, 220)),
)


def isnumeric(s: str) -> bool:
    """ISNUMERIC：Creator.Method.cs:2540–2569；與 TOINT 共用相同詞法及錯誤。"""
    from .numeric import read_numeric

    return read_numeric(s) is not None


def setcolor_by_str(out: TextOutput, color: str) -> int:
    """`@SETCOLOR_BY_STR, COLOR_STR`:10–55：色名か "R//G//B"。変更しなかったら -1、した場合は関数終端（0）。"""
    for names, rgb in _NAMED_COLORS:
        if color in names:
            setcolor(out, *rgb)
            return 0
    parts = color.split("//")  # :45 SPLIT（RESULT = 要素数）
    if len(parts) == 3 and all(isnumeric(p) for p in parts):
        from .chara_make import toint

        setcolor(out, toint(parts[0]), toint(parts[1]), toint(parts[2]))
        return 0
    return -1


def colorchip(out: TextOutput, color: str) -> None:
    """`@COLORCHIP, COLOR`:64–73：`[■]`（■ だけ色付き、前後は呼び出し時点の文字色：GETCOLOR／SETCOLOR で復元）。
    GETCOLOR は現在の文字色（既定色なら Config.ForeColor：Creator.Method.cs@GetColorMethod:563–567）を返し、
    SETCOLOR でそれに戻すので、既定色のときは既定色のまま（TextOutput では reset_color）。"""
    original = out.color
    out.print("[")
    setcolor_by_str(out, color)
    out.print("■")
    if original is None:
        out.reset_color()
    else:
        out.set_color(original)
    out.print("]")
