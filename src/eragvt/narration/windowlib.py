"""複数ウィンドウ描画ライブラリの Python 移植（S14）。catalog から `CALL WINDOW_*` で呼ばれる。

原作：`汎用関数/WindowDrawer.ERB`（@WINDOW_DISPLAY_EX:50–126、@WINDOW_DISPLAY:129–134、@WINDOW_CREATE:149–168、
@WINDOW_DESTROY:179–194、@WINDOW_SETTEXT:206–222、@WINDOW_MGR:316–409）と `汎用関数/TagSetText.ERB`
（@CUT_TAGSET_TEXT:75–181、@SHAPE_TAGSET_TEXT:196–271、@PRINT_TAGSET_TEXT:287–319、@PRINT_TAGSET_TEXT_MAIN:384–418、
@TAGSET_TEXT_SET_TAGINFO:430–460、@TAGSET_TEXT_CLEATE_TAGINFO_TEXT:474–500、@…_CLOSE_TEXT:515–541）。
呼び出し元は本作では `地の文/MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window` のみ。

catalog の子集合外（SPLIT・ISNUMERIC・TOINT・THROW・REF 引数・ARRAYCOPY・GETCOLOR／GETFONT／CHKFONT・PRINTBUTTON）を
多用するため手で移植した。状態（GameState）への書き込み・RAND は無い（原文を grep で確認）。
ウィンドウ管理の静的配列（@WINDOW_MGR の `#DIMS arrWndText` 等：関数内 #DIM は静的、UserDefinedVariable.cs:27）は
`WindowManager` のインスタンスが持つ。唯一の呼び出し元は終了時（入力 "99"）に全ウィンドウを破棄して RETURN するので、
catalog の 1 回の実行ごとに新しいインスタンスを使っても結果は同じ。

エンジン側の依拠（`reference/emuera-1824/Emuera/`）：
- STRLENS = Shift-JIS のバイト数（`_Library/LangManager.cs`:17–20 → `runtime.cp932_len`）、STRLENSU = `string.Length`
  （`GameData/Function/Creator.Method.cs`:2110–2123）、SUBSTRINGU = 文字単位の部分文字列（同:2167–2220）。
  C# の Length は UTF-16 単位だが、本作の該当文字列はすべて BMP 内なので Python の len と一致する。
- SPLIT：`string.Split(区切り, StringSplitOptions.None)`、RESULT = 分割数、配列長を超えた分は切り捨て
  （`GameProc/Process.ScriptProc.cs`:522–538）。
- PRINTPLAINFORM は按鈕化しない（`GameView/PrintStringBuffer.cs@AppendPlainText`:109）。
"""

from __future__ import annotations

from typing import Any, Optional

from .runtime import ErbRuntimeError, NotSupported, cp932_len

_TAG_SIZE = 5  # `#DIMS arrTagInfo, 5`
_SPLIT_SIZE = 200  # `#DIMS strSplitBuf, 200`
_DISPLAY_WIDTH = 84  # @WINDOW_DISPLAY_EX:54 `#DIM nDisplayWidth = 84`
_DISPLAY_LINES = 200  # `#DIMS arrDisplayText, 200`
_MAX_WINDOWS = 10
_WND_LINES = 100  # `#DIMS arrWndText, 10, 100`


def _split(text: str) -> list[str]:
    parts = text.split("@")
    if len(parts) > _SPLIT_SIZE:
        # SPLIT は配列長で切り捨てるが RESULT は元の数 → FOR で範囲外参照になりエラー
        raise ErbRuntimeError("SPLIT：タグ指定テキストの分割数が 200 を超えています")
    return parts


def _substringu(s: str, start: int, length: int = -1) -> str:
    """SUBSTRINGU（Creator.Method.cs:2195–2220）。"""
    if start >= len(s) or length == 0:
        return ""
    if length < 0 or length > len(s):
        length = len(s)
    if start <= 0:
        if length == len(s):
            return s
        start = 0
    if start + length > len(s):
        length = len(s) - start
    return s[start : start + length]


def set_taginfo(text: str, info: list[str]) -> None:
    """TagSetText.ERB@TAGSET_TEXT_SET_TAGINFO:430–460。"""
    if _substringu(text, 0, 1) == "/":
        typ = _substringu(text, 1, -1)
        val = ""
    else:
        typ = _substringu(text, 0, 1)
        val = _substringu(text, 2, -1)
    if typ == "C":
        info[0] = val
    elif typ == "B":
        info[1] = val
    elif typ == "F":
        info[2] = val


def tag_open_text(info: list[str]) -> str:
    """@TAGSET_TEXT_CLEATE_TAGINFO_TEXT:474–500。"""
    out = ""
    for i, v in enumerate(info[:_TAG_SIZE]):
        if cp932_len(v) <= 0:
            continue
        if i == 0:
            out += f"@C:{v}@"
        elif i == 1:
            out += f"@B:{v}@"
        elif i == 2:
            out += f"@F:{v}@"
    return out


def tag_close_text(info: list[str]) -> str:
    """@TAGSET_TEXT_CLEATE_TAGINFO_CLOSE_TEXT:515–541。"""
    out = ""
    for i, v in enumerate(info[:_TAG_SIZE]):
        if cp932_len(v) <= 0:
            continue
        if i == 0:
            out += "@/C@"
        elif i == 1:
            out += "@/B@"
        elif i == 2:
            out += "@/F@"
    return out


def shape_tagset_text(text: str, size: int) -> list[str]:
    """@SHAPE_TAGSET_TEXT:196–271。戻り値 = RESULTS:0〜（成形後の各行）。size <= 1 なら空（RESULTS はすべて ""）。"""
    if size <= 1:
        return []
    pieces = _split(text)
    shape = [""]
    cnt = 0
    info = [""] * _TAG_SIZE
    checked = 0
    for n, piece in enumerate(pieces):
        if n % 2 == 0:
            buf = piece
            while len(buf) > 0:
                w = cp932_len(buf)
                if checked + w <= size:
                    shape[cnt] += buf
                    checked += w
                    buf = ""
                else:
                    ls = ""
                    k = 0
                    while cp932_len(ls) < size - checked:
                        c1 = _substringu(buf, k, 1)
                        if cp932_len(ls) + cp932_len(c1) <= size - checked:
                            ls += c1
                            k += 1
                        else:
                            break
                    shape[cnt] += ls
                    checked += cp932_len(ls)
                    buf = _substringu(buf, len(ls), -1)
                    shape[cnt] += tag_close_text(info)
                    if size - checked > 0:
                        shape[cnt] += " " * (size - checked)
                    checked = 0
                    cnt += 1
                    shape.append(tag_open_text(info))
        else:
            shape[cnt] += f"@{piece}@"
            set_taginfo(piece, info)
    shape[cnt] += tag_close_text(info)
    if size - checked > 0:
        shape[cnt] += " " * (size - checked)
    return shape


def cut_tagset_text(text: str, size: int, mode: int, padding: int) -> list[str]:
    """@CUT_TAGSET_TEXT:75–181。戻り値 = RESULTS:0（前半）・RESULTS:1（後半）…。"""
    if size <= 0:
        return ["", text]
    if mode not in (0, 1):
        raise NotSupported("CUT_TAGSET_TEXT の nMode は 0／1 のみ（それ以外は原作で無限ループ）")
    pieces = _split(text)
    shape = [""]
    cnt = 0
    info = [""] * _TAG_SIZE
    full = 0
    checked = 0
    for n, piece in enumerate(pieces):
        if n % 2 == 0:
            buf = piece
            while len(buf) > 0:
                w = cp932_len(buf)
                if cnt == 1:
                    shape[cnt] += buf
                    checked += w
                    buf = ""
                elif checked + w <= size:
                    shape[cnt] += buf
                    checked += w
                    buf = ""
                else:
                    ls = ""
                    k = 0
                    while cp932_len(ls) < size - checked:
                        c1 = _substringu(buf, k, 1)
                        if mode == 0:
                            if cp932_len(ls) + cp932_len(c1) <= size - checked:
                                ls += c1
                                k += 1
                            else:
                                break
                        else:
                            if cp932_len(ls) < size - checked:
                                ls += c1
                                k += 1
                            else:
                                break
                    if cp932_len(ls) > size - checked:
                        full = 1
                    shape[cnt] += ls
                    checked += cp932_len(ls)
                    buf = _substringu(buf, len(ls), -1)
                    shape[cnt] += tag_close_text(info)
                    if padding == 1 and size - checked > 0:
                        shape[cnt] += " " * (size - checked)
                    checked = 0
                    cnt += 1
                    shape.append(tag_open_text(info) + " " * full)
        else:
            shape[cnt] += f"@{piece}@"
            set_taginfo(piece, info)
    shape[cnt] += tag_close_text(info)
    if padding == 1 and size - checked > 0:
        shape[cnt] += " " * (size - checked)
    return shape


def _r(results: list[str], i: int) -> str:
    return results[i] if i < len(results) else ""


def print_tagset_text(out: Any, text: str, exflag: int) -> None:
    """@PRINT_TAGSET_TEXT:287–319 ＋ @PRINT_TAGSET_TEXT_MAIN:384–418。

    既定タグ情報は `0x{GETCOLOR():X6}`（呼び出し前の文字色）。ここでは「呼び出し前の色に戻す」として扱う
    （SETCOLOR で同じ色を明示指定するのと表示は同じ）。フォント指定（@F:）は表示のみなので反映しない
    （本作の呼び出し元は @F: を使わない）。"""
    saved = out._color
    default = object()
    info: list[Any] = [""] * _TAG_SIZE
    default_info: list[Any] = [default, "", ""] + [""] * (_TAG_SIZE - 3)

    def main(s: str, tag: list[Any]) -> None:
        c = tag[0]
        if c is default:
            out._color = saved
        elif cp932_len(c) > 0:
            v = _toint(c)
            if v is not None:
                if v >= 0:
                    out.set_color(((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))
                else:
                    out.reset_color()
        if cp932_len(tag[1]) > 0:
            try:
                value = int(tag[1])
            except ValueError as e:
                # DEVIATION: Web の入力は整数のみ（deviations.md「INPUTS 只能輸入整數」）
                raise NotSupported(f"PRINTBUTTON の値が整数でない（{tag[1]}）") from e
            out.button(s, value)
        else:
            out.print_plain(s)

    for n, piece in enumerate(_split(text)):
        if n % 2 == 0:
            main(piece, info)
        else:
            if exflag & 0x02:
                continue
            set_taginfo(piece, info)
            main("", default_info)
    main("", default_info)
    if exflag & 0x01:
        out.printl()


def _toint(s: str) -> Optional[int]:
    """ISNUMERIC＋TOINT（10 進・0x 16 進のみ。それ以外は ISNUMERIC 偽として扱う）。"""
    t = s.strip()
    try:
        if t[:2].lower() == "0x":
            return int(t[2:], 16)
        return int(t)
    except ValueError:
        return None


class WindowManager:
    """@WINDOW_MGR:316–409 の静的配列（arrWndTextPrint・arrWndText・arrWndInfo）。"""

    def __init__(self) -> None:
        self.text_print = [[""] * _WND_LINES for _ in range(_MAX_WINDOWS)]
        self.text = [[""] * _WND_LINES for _ in range(_MAX_WINDOWS)]
        self.info = [[0] * _WND_LINES for _ in range(_MAX_WINDOWS)]

    def _check_id(self, wid: int) -> None:
        if not 0 <= wid < _MAX_WINDOWS:
            raise ErbRuntimeError(f"ウィンドウ ID {wid} が範囲外")

    def exists(self, wid: int) -> int:
        self._check_id(wid)
        return self.info[wid][99]

    def _reset(self, wid: int) -> None:
        self.text_print[wid] = [""] * _WND_LINES
        self.text[wid] = [""] * _WND_LINES
        self.info[wid] = [0] * _WND_LINES

    def create(self, wid: int, x: int, y: int, w: int, h: int, exflag: int) -> None:
        """@WINDOW_CREATE:149–168 → @WINDOW_MGR "CREATE":334–339／351–375。"""
        if self.exists(wid) == 1:
            raise ErbRuntimeError(f"WINDOW_CREATE() : ウィンドウ（nWndId={wid}）は生成済みです")
        border = 1 if exflag & 0x01 else 0
        self._reset(wid)
        self.info[wid][99] = 1
        info = self.info[wid]
        info[0], info[1], info[2], info[3], info[4] = x, y, w, h, border
        tp = self.text_print[wid]
        if border == 1:
            bar = "━" * _trunc_div(w - 4, 2)
            tp[0] = f"┏{bar}┓"
            tp[h - 1] = f"┗{bar}┛"
            for n in range(1, h - 1):
                tp[n] = "┃" + _r(shape_tagset_text(self.text[wid][n - 1], w - 4), 0) + "┃"
        else:
            for n in range(0, h):
                tp[n] = _r(shape_tagset_text(self.text[wid][n], w), 0)

    def destroy(self, wid: int) -> None:
        """@WINDOW_DESTROY:179–194 → "DESTROY":341–347。"""
        self._check_id(wid)
        self._reset(wid)

    def settext(self, wid: int, line: int, s: str) -> None:
        """@WINDOW_SETTEXT:206–222 → "SETTEXT":377–389。"""
        if self.exists(wid) == 0:
            raise ErbRuntimeError(f"WINDOW_SETTEXT() : ウィンドウ（nWndId={wid}）は未生成です")
        if not 0 <= line < _WND_LINES:
            raise ErbRuntimeError("ウィンドウの行位置が範囲外")
        self.text[wid][line] = s
        info = self.info[wid]
        if info[4] == 1:
            if line < info[3] - 2:
                self.text_print[wid][line + 1] = "┃" + _r(shape_tagset_text(s, info[2] - 4), 0) + "┃"
        else:
            self.text_print[wid][line] = _r(shape_tagset_text(s, info[2]), 0)

    def display_ex(self, out: Any, priority: list[int]) -> None:
        """@WINDOW_DISPLAY_EX:50–126。"""
        lines = [""] * _DISPLAY_LINES
        max_line = 0
        for wid in priority:
            if wid < 0:
                continue
            if self.exists(wid) == 0:
                continue
            x, y, w, h, _border = self.info[wid][:5]
            for wl in range(h):
                cl = y + wl
                if cl < 0:
                    continue
                if cl >= _DISPLAY_LINES:
                    raise ErbRuntimeError("arrDisplayText の範囲外")
                if x >= 0:
                    left = _r(cut_tagset_text(lines[cl], x, 0, 1), 0)
                    right = _r(cut_tagset_text(lines[cl], x + w, 1, 0), 1)
                    body = _r(shape_tagset_text(self.text_print[wid][wl], w), 0)
                else:
                    # :96–107（負の X）。本作では使われない
                    raise NotSupported("WINDOW_DISPLAY_EX：負の X 座標")
                lines[cl] = left + body + right
                max_line = max(max_line, cl)
        for cl in range(max_line + 1):
            print_tagset_text(out, _r(shape_tagset_text(lines[cl], _DISPLAY_WIDTH), 0), 0x01)


def _trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def py_functions(wm: WindowManager, out: Any) -> dict:
    """catalog の py_functions に登録する `CALL WINDOW_*`（RETURN → RESULT:0 = 0）。"""

    def _int(args: list, i: int) -> int:
        v = args[i] if i < len(args) and args[i] is not None else 0
        if not isinstance(v, int):
            raise ErbRuntimeError("整数が必要です")
        return v

    def create(it, args):
        wm.create(*(_int(args, i) for i in range(6)))
        it._set_result([0])
        return 0

    def settext(it, args):
        s = args[2] if len(args) > 2 and args[2] is not None else ""
        wm.settext(_int(args, 0), _int(args, 1), s)
        it._set_result([0])
        return 0

    def destroy(it, args):
        wm.destroy(_int(args, 0))
        it._set_result([0])
        return 0

    def display(it, args):
        # @WINDOW_DISPLAY:129–134：nWindowCnt = 10、優先度 0..9
        wm.display_ex(out, list(range(_MAX_WINDOWS)))
        it._set_result([0])
        return 0

    def display_ex(it, args):
        # 第 2 引数は REF 配列（catalog では配列を渡せない）。本作では nTestMode == 0 のため呼ばれない
        raise NotSupported("WINDOW_DISPLAY_EX（REF 配列引数）")

    return {
        "WINDOW_CREATE": create,
        "WINDOW_SETTEXT": settext,
        "WINDOW_DESTROY": destroy,
        "WINDOW_DISPLAY": display,
        "WINDOW_DISPLAY_EX": display_ex,
    }
