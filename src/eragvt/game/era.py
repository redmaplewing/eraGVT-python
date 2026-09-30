"""Emuera 內建命令／運算的語意（與 C# 實作一致的整數運算、字串格式）。

依據路徑相對 `reference/emuera-1824/Emuera/`。
"""

from __future__ import annotations

import math
from decimal import Decimal


def div(a: int, b: int) -> int:
    """整數除法（C# `long / long`：向 0 截斷）。"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def mod(a: int, b: int) -> int:
    """C# `%`：符號跟被除數。"""
    return a - div(a, b) * b


def times(value: int, factor: str) -> int:
    """`TIMES 變數, 小數`：decimal 乘算後截斷（GameProc/Function/Instraction.Child.cs@TIMES_Instruction:893–916，
    config「TIMESの計算をeramakerにあわせる:NO」）。`factor` 以字串給，避免二進位浮點誤差。"""
    return int(Decimal(value) * Decimal(factor))  # int() 對 Decimal 向 0 截斷


def isqrt(value: int) -> int:
    """`SQRT(x)`：`(Int64)Math.Sqrt(x)`（GameData/Function/Creator.Method.cs@SqrtMethod:1074–1080）。"""
    if value < 0:
        raise ValueError("SQRT関数の引数に負の値が指定されました")
    return int(math.sqrt(value))


def power(x: int, y: int) -> int:
    """`POWER(x, y)`：`(long)Math.Pow(x, y)`、非数・無限大・int64 範囲外はエラー
    （GameData/Function/Creator.Method.cs@PowerMethod:1043–1064）。"""
    p = math.pow(x, y)
    if math.isnan(p) or math.isinf(p) or p >= 2**63 or p <= -(2**63):
        raise OverflowError(f"累乗結果({p})が64ビット符号付き整数の範囲外です")
    return int(p)


def limit(value: int, low: int, high: int) -> int:
    """`LIMIT(v, low, high)`（GameData/Function/Creator.Method.cs@GetLimitMethod:1178–1201）。"""
    return max(low, min(high, value))


def cp932_len(text: str) -> int:
    """`LangManager.GetStrlenLang`（_Library/LangManager.cs:17–20，日本語設定 = cp932 のバイト数）。
    エンコードできない文字は `?`（1 バイト）扱い。"""
    return len(text.encode("cp932", errors="replace"))


def format_percent(text: str, width: int, left: bool) -> str:
    """`%文字列,幅,LEFT/RIGHT%`（GameData/StrForm.cs@FormatPercent:248–263）：全角を 2 として幅を詰める。"""
    total = width - (cp932_len(text) - len(text))
    if total < len(text):
        return text
    return text.ljust(total) if left else text.rjust(total)


def format_curly(value: int | str, width: int, left: bool = False) -> str:
    """`{数値,幅,LEFT/RIGHT}`（StrForm.cs@FormatCurlyBrace:233–244）：文字数で PadRight/PadLeft。"""
    s = str(value)
    return s.ljust(width) if left else s.rjust(width)
