"""原作 WINAPI 文字計量；只使用 Windows 既有 GDI／GDI+，不安裝字型。

source/earGVP/emuera.config:11–22 指定 WINAPI、760px、ＭＳ ゴシック、14px。
reference/emuera-1824/Emuera/Config/Config.cs:186–208 建立 Pixel Font；
GameView/StringMeasure.cs:43–72 → _Library/GDI.cs:331–347：ToHfont 後
GetTabbedTextExtentW，保留 UTF-16 長度及預設 tab stop。
"""
from __future__ import annotations

import ctypes as C
import sys
from functools import lru_cache
from threading import RLock

DEFAULT_FONT = "ＭＳ ゴシック"
FONT_SIZE = 14
DRAWABLE_WIDTH = 760
_lock = RLock()
_api = None


class _LogFont(C.Structure):
    _fields_ = [(n, C.c_int32) for n in ("height", "width", "escapement", "orientation", "weight")] + [
        (n, C.c_ubyte) for n in ("italic", "underline", "strikeout", "charset", "outprecision", "clipprecision", "quality", "pitch")
    ] + [("face", C.c_wchar * 32)]


def _libraries():
    global _api
    if _api is not None:
        return _api
    gp, gdi, user = C.WinDLL("gdiplus"), C.WinDLL("gdi32"), C.WinDLL("user32")
    ptr, integer = C.c_void_p, C.c_int
    signatures = [
        (gp, "GdiplusStartup", [C.POINTER(C.c_size_t), ptr, ptr], integer),
        (gp, "GdipCreateFontFamilyFromName", [C.c_wchar_p, ptr, C.POINTER(ptr)], integer),
        (gp, "GdipGetGenericFontFamilySansSerif", [C.POINTER(ptr)], integer),
        (gp, "GdipGetFamilyName", [ptr, C.c_wchar_p, integer], integer),
        (gp, "GdipCreateFont", [ptr, C.c_float, integer, integer, C.POINTER(ptr)], integer),
        (gp, "GdipCreateFromHDC", [ptr, C.POINTER(ptr)], integer),
        (gp, "GdipGetLogFontW", [ptr, ptr, C.POINTER(_LogFont)], integer),
        (gp, "GdipDeleteFont", [ptr], integer),
        (gp, "GdipDeleteFontFamily", [ptr], integer),
        (gp, "GdipDeleteGraphics", [ptr], integer),
        (gdi, "CreateCompatibleDC", [ptr], ptr),
        (gdi, "CreateFontIndirectW", [C.POINTER(_LogFont)], ptr),
        (gdi, "SelectObject", [ptr, ptr], ptr),
        (gdi, "DeleteObject", [ptr], integer),
        (gdi, "DeleteDC", [ptr], integer),
        (user, "GetTabbedTextExtentW", [ptr, C.c_wchar_p, integer, integer, C.POINTER(integer)], C.c_uint32),
    ]
    for lib, name, args, result in signatures:
        fn = getattr(lib, name)
        fn.argtypes, fn.restype = args, result
    class Startup(C.Structure):
        _fields_ = [("version", C.c_uint32), ("debug", ptr), ("thread", integer), ("codecs", integer)]
    token = C.c_size_t()
    _check(gp.GdiplusStartup(C.byref(token), C.byref(Startup(1, None, 0, 0)), None))
    _api = gp, gdi, user, token  # GDI+ 活到程序結束；每次使用的字型與 DC 皆另行釋放。
    return _api


def _check(status):
    if status:
        raise RuntimeError(f"GDI+ 字型計量失敗：{status}")


@lru_cache(maxsize=256)
def _font(font: str, bold: bool, italic: bool) -> tuple[bytes, str, bool]:
    gp, gdi, _, _ = _libraries()
    family, native, graphics = C.c_void_p(), C.c_void_p(), C.c_void_p()
    dc = gdi.CreateCompatibleDC(None)
    if not dc:
        raise RuntimeError("無法建立 GDI 文字計量 DC")
    try:
        available = gp.GdipCreateFontFamilyFromName(font, None, C.byref(family)) == 0
        if not available:
            # System.Drawing.Font(name, ...) 的缺字型回落：GenericSansSerif。
            _check(gp.GdipGetGenericFontFamilySansSerif(C.byref(family)))
        _check(gp.GdipCreateFont(family, FONT_SIZE, int(bold) | (int(italic) << 1), 2, C.byref(native)))
        _check(gp.GdipCreateFromHDC(dc, C.byref(graphics)))
        logfont = _LogFont()
        _check(gp.GdipGetLogFontW(native, graphics, C.byref(logfont)))
        name = C.create_unicode_buffer(32)
        _check(gp.GdipGetFamilyName(family, name, 0))
        return bytes(logfont), name.value, available
    finally:
        if graphics: gp.GdipDeleteGraphics(graphics)
        if native: gp.GdipDeleteFont(native)
        if family: gp.GdipDeleteFontFamily(family)
        gdi.DeleteDC(dc)


def installed_font(font: str) -> bool:
    if sys.platform != "win32":
        return False
    with _lock:
        return _font(font, False, False)[2]


def display_font(font: str | None) -> str | None:
    if sys.platform != "win32":
        return font
    with _lock:
        _, resolved, available = _font(font or DEFAULT_FONT, False, False)
        return (font or DEFAULT_FONT) if available else resolved


@lru_cache(maxsize=8192)
def measure_text(text: str, font: str | None = None, bold: bool = False, italic: bool = False) -> int | None:
    if sys.platform != "win32":
        # DEVIATION：非 Windows 沿用既有欄寬近似；不冒充 GDI 等價。
        return None
    if not text:
        return 0
    with _lock:
        _, gdi, user, _ = _libraries()
        raw, _, _ = _font(font or DEFAULT_FONT, bold, italic)
        logfont = _LogFont.from_buffer_copy(raw)
        dc = gdi.CreateCompatibleDC(None)
        native = gdi.CreateFontIndirectW(C.byref(logfont))
        if not dc or not native:
            if native: gdi.DeleteObject(native)
            if dc: gdi.DeleteDC(dc)
            raise RuntimeError("無法建立 GDI 文字計量字型")
        previous = gdi.SelectObject(dc, native)
        try:
            # Windows wchar_t = UTF-16；Python len 對補充平面字元只有一個碼點。
            count = len(text.encode("utf-16-le", errors="surrogatepass")) // 2
            return user.GetTabbedTextExtentW(dc, text, count, 0, None) & 0xffff
        finally:
            gdi.SelectObject(dc, previous)
            gdi.DeleteObject(native)
            gdi.DeleteDC(dc)
