"""TOINT／ISNUMERIC 的原生共用轉換，限既有色彩與年齡呼叫者。

依據：reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2357–2387、2540–2569；
reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:133–263。
"""
from __future__ import annotations

import math

_INT64_MIN = -(1 << 63)
_INT64_MAX = (1 << 63) - 1
_UINT64_MAX = (1 << 64) - 1
_HEX = "abcdefABCDEF"
# Config/Config.cs:134、_Library/LangManager.cs:12–20 使用 .NET Encoding(932)。
# Python cp932 與 .NET Framework 4 的 BMP 位元組長度差（全 65,536 字元實測）。
# 這是數值判定的寬字元閘門；不改其他既有 CP932 顯示函式。
_CP932_WIDTH = {"«": 2, "¯": 2, "µ": 2, "·": 2, "¸": 2, "»": 2,
                "‖": 1, "−": 1, "〜": 1, "ゔ": 2}


def _digit(ch: str) -> bool:
    # char.IsDigit 以 UTF-16 char 判斷 Nd，非 BMP 的代理字元各自不是數字。
    # .NET Framework 4 與 Python 3.10 全 BMP 分類實測一致（S50 查證）。
    return len(ch) == 1 and ord(ch) <= 0xFFFF and ch.isdecimal()


def _wide(text: str) -> bool:
    # Creator.Method.cs:2363／2545：str.Length < GetByteCount(str)。
    # 非 BMP 在 .NET 932 為兩個替代位元組，恰等於 UTF-16 長度，不構成寬字元。
    return any(
        ord(ch) <= 0xFFFF
        and _CP932_WIDTH.get(ch, len(ch.encode("cp932", errors="replace"))) > 1
        for ch in text
    )


def _read_digits(text: str, pos: int, base: int) -> tuple[int, int]:
    """LexicalAnalyzer.cs:192–263：掃描後 Convert.ToInt64，保留錯誤順序。"""
    start = pos
    if pos < len(text) and text[pos] in "+-":
        pos += 1
    digits = pos
    while pos < len(text):
        ch = text[pos]
        if _digit(ch):
            if base == 2 and ch not in "01":
                raise ValueError("二進位數值包含無效數字")
        elif base != 16 or ch not in _HEX:
            break
        pos += 1
    negative = text[start:start + 1] == "-"
    if negative and base != 10:
        raise ValueError("非十進位數值不能包含負號")
    if digits == pos:
        raise ValueError("數值缺少數字")
    ceiling = (1 << 63) if negative else _INT64_MAX
    if base != 10:
        ceiling = _UINT64_MAX
    value = 0
    # 原 Convert 限 Int64／UInt64；逐位檢查可接受任意多前導 0，且不建立無界大整數。
    for ch in text[digits:pos]:
        if "0" <= ch <= "9":
            digit = ord(ch) - ord("0")
        elif ch in _HEX:
            digit = ord(ch.lower()) - ord("a") + 10
        else:
            raise ValueError("數值包含無法轉換的數字")
        value = value * base + digit
        if value > ceiling:
            raise OverflowError("數值超出 64 位元整數範圍")
    if negative:
        value = -value
    elif base != 10 and value > _INT64_MAX:
        value -= 1 << 64  # Convert.ToInt64 的二／十六進位採二補數。
    return value, pos


def read_numeric(text: str) -> int | None:
    """合法回 Int64，無效格式回 None；引擎轉換錯誤仍拋例外，不混同數值 0。"""
    if not text or _wide(text):
        return None
    if text[0] in "+-":
        if not _digit(text[1:2]):
            return None
    elif not _digit(text[0]):
        return None

    base, pos = 10, 0
    if text[:2].lower() == "0x":
        base, pos = 16, 2
    elif text[:2].lower() == "0b":
        base, pos = 2, 2
    current = text[pos:pos + 1]
    # :163–169 的 retZero 分支不消耗目前字元；裸前綴可回 0。
    if current not in ("+", "-") and not _digit(current) and not (base == 16 and current and current in _HEX):
        value = 0
    else:
        value, pos = _read_digits(text, pos, base)
        marker = text[pos:pos + 1].lower()
        if marker in ("e", "p"):
            exponent, pos = _read_digits(text, pos + 1, base)
            exponent = ((exponent + (1 << 31)) % (1 << 32)) - (1 << 31)  # :178 unchecked Int32
            if exponent:
                try:
                    factor = math.pow(10 if marker == "e" else 2, exponent)
                except OverflowError:
                    factor = math.inf
                scaled = value * factor
                # :185 比較時 Int64.MaxValue 也先轉成 double（2**63）。
                if not math.isfinite(scaled) or scaled > float(_INT64_MAX) or scaled < _INT64_MIN:
                    raise OverflowError("指數結果超出 64 位元整數範圍")
                # :187 .NET Framework unchecked 的 2**63 邊界轉為 Int64.MinValue。
                value = _INT64_MIN if scaled == float(1 << 63) else int(scaled)
    if pos < len(text):
        if text[pos] != "." or not all(_digit(ch) for ch in text[pos + 1:]):
            return None
    return value
