"""已實作的式中関数（語意照 `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs`，行號見各函式）。

引數一律由左至右求值（C# の引数評価順）。未列出的式中関数由 `runtime_support.unsupported_reasons_static` 擋下。
"""

from __future__ import annotations

from typing import Any

from .runtime import ErbRuntimeError, NotSupported, cp932_len


def _ev(it, e, fr) -> Any:
    return it.eval(e, fr) if e is not None else None


def _int(it, e, fr) -> int:
    v = _ev(it, e, fr)
    if not isinstance(v, int):
        raise ErbRuntimeError("整数が必要です")
    return v


def m_getbit(it, a, fr) -> int:
    """`GetbitMethod`:1595–1625。"""
    n = _int(it, a[0], fr)
    m = _int(it, a[1], fr)
    if m < 0 or m > 63:
        raise ErbRuntimeError("GETBIT の第2引数が範囲外")
    return (n >> m) & 1


def m_unicode(it, a, fr) -> str:
    """`UnicodeMethod`:2476–2490。"""
    i = _int(it, a[0], fr)
    if i < 0 or i > 0xFFFF:
        raise ErbRuntimeError("UNICODE の値が範囲外")
    return chr(i)


def _uft_index(s: str, lang_index: int) -> int:
    """`LangManager.GetUFTIndex`（_Library/LangManager.cs:21–38）。"""
    if lang_index <= 0:
        return 0
    if lang_index >= cp932_len(s):
        return len(s)
    jis = 0
    k = 0
    for ch in s:
        jis += cp932_len(ch)
        k += 1
        if jis >= lang_index:
            break
    return k


def m_strfind(it, a, fr) -> int:
    """`StrfindMethod`:2222–2280（STRFIND は cp932 バイト位置）。"""
    target = _ev(it, a[0], fr)
    word = _ev(it, a[1], fr)
    start = 0
    if len(a) >= 3 and a[2] is not None:
        start = _uft_index(target, _int(it, a[2], fr))
    if start < 0 or start >= len(target):
        return -1
    idx = target.find(word, start)
    if idx > 0:
        idx = cp932_len(target[:idx])
    return idx


def m_rand(it, a, fr) -> int:
    """`RandMethod`:922–974：RAND(max) または RAND(min, max)。"""
    if len(a) == 1:
        lo, hi = 0, _int(it, a[0], fr)
    else:
        lo = _int(it, a[0], fr) if a[0] is not None else 0
        hi = _int(it, a[1], fr)
    if hi <= lo:
        raise ErbRuntimeError("RAND の最大値が最小値以下")
    return it.st.rng.rand(hi - lo) + lo


def m_max(it, a, fr) -> int:
    """`MaxMethod`:976–1026。"""
    vals = [_int(it, x, fr) for x in a]
    return max(vals)


def m_min(it, a, fr) -> int:
    vals = [_int(it, x, fr) for x in a]
    return min(vals)


def m_abs(it, a, fr) -> int:
    return abs(_int(it, a[0], fr))


def m_sign(it, a, fr) -> int:
    v = _int(it, a[0], fr)
    return (v > 0) - (v < 0)


def m_limit(it, a, fr) -> int:
    """`LimitMethod`：LIMIT(値, 最小, 最大)。"""
    v, lo, hi = (_int(it, x, fr) for x in a[:3])
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def m_power(it, a, fr) -> int:
    """`PowerMethod`:1043–1063（double で計算して long へ）。"""
    x = _int(it, a[0], fr)
    y = _int(it, a[1], fr)
    try:
        p = float(x) ** y
    except (OverflowError, ZeroDivisionError) as e:
        raise ErbRuntimeError("累乗結果が範囲外") from e
    if isinstance(p, complex) or p != p:
        raise ErbRuntimeError("累乗結果が非数値")
    if p >= 2**63 or p <= -(2**63):
        raise ErbRuntimeError("累乗結果が範囲外")
    return int(p)


def m_groupmatch(it, a, fr) -> int:
    """`GroupMatchMethod`:1369–1416。"""
    base = _ev(it, a[0], fr)
    return sum(1 for x in a[1:] if _ev(it, x, fr) == base)


def m_inrange(it, a, fr) -> int:
    """`InRangeMethod`:1853–1867。"""
    v, lo, hi = (_int(it, x, fr) for x in a[:3])
    return 1 if lo <= v <= hi else 0


def m_strlens(it, a, fr) -> int:
    """`StrlenMethod`:2095–2107（cp932 バイト数）。"""
    return cp932_len(_ev(it, a[0], fr))


def m_strlensu(it, a, fr) -> int:
    return len(_ev(it, a[0], fr))


def m_substring(it, a, fr) -> str:
    """`SubstringMethod`:2125–2160 → `LangManager.GetSubStringLang`（LangManager.cs:40–82）。"""
    s = _ev(it, a[0], fr)
    start = _int(it, a[1], fr) if len(a) >= 2 and a[1] is not None else 0
    length = _int(it, a[2], fr) if len(a) >= 3 and a[2] is not None else -1
    total = cp932_len(s)
    if start >= total or length == 0:
        return ""
    if length < 0 or length > total:
        length = total
    k = 0
    if start <= 0:
        if length == total:
            return s
    else:
        jis = 0
        for ch in s:
            jis += cp932_len(ch)
            k += 1
            if jis >= start:
                break
        if k >= len(s):
            return ""
    out = []
    jis = 0
    while True:
        out.append(s[k])
        jis += cp932_len(s[k])
        k += 1
        if jis >= length or k >= len(s):
            break
    return "".join(out)


def m_substringu(it, a, fr) -> str:
    """`SubstringuMethod`:2162–2220。"""
    s = _ev(it, a[0], fr)
    start = _int(it, a[1], fr) if len(a) >= 2 and a[1] is not None else 0
    length = _int(it, a[2], fr) if len(a) >= 3 and a[2] is not None else -1
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


def m_tostr(it, a, fr) -> str:
    """`ToStrMethod`:2305–2346（書式指定は未対応）。"""
    v = _int(it, a[0], fr)
    if len(a) >= 2 and a[1] is not None:
        raise NotSupported("TOSTR の書式指定は未対応")
    return str(v)


def m_strfindu(it, a, fr) -> int:
    """`StrfindMethod(unicode: true)`:2222–2280（S21）：開始位置・戻り値とも文字（UTF-16）単位。
    `target.IndexOf(word, start)`（:2273）。空の target は start >= Length で -1。"""
    target = _ev(it, a[0], fr)
    word = _ev(it, a[1], fr)
    start = _int(it, a[2], fr) if len(a) >= 3 and a[2] is not None else 0
    if start < 0 or start >= len(target):
        return -1
    # UNVERIFIED: .NET の IndexOf(string, int) は文化依存比較。序数比較（str.find）で代用（unresolved.md S21）
    return target.find(word, start)


def _dotnet_regex(pattern: str):
    """`new Regex(pattern)`。本作で使われる文字クラス・リテラルのみ（.NET と Python re で同じ意味のもの）を受け付ける。"""
    import re

    if any(ch in pattern for ch in "\\(){}?*+|^$"):
        raise NotSupported(f"正規表現 {pattern!r}（.NET と Python の差を確認していない構文）")
    try:
        return re.compile(pattern)
    except re.error as e:
        raise ErbRuntimeError(f"第２引数が正規表現として不正です：{e}") from e


def m_strcount(it, a, fr) -> int:
    """`StrCountMethod`:2282–2302（S21）：`new Regex(第2引数).Matches(第1引数).Count`。"""
    target = _ev(it, a[0], fr)
    return len(_dotnet_regex(_ev(it, a[1], fr)).findall(target))


def m_replace(it, a, fr) -> str:
    """`ReplaceMethod`:2452–2474（S21）：`new Regex(第2引数).Replace(第1引数, 第3引数)`（置換文字列に `$` は不可）。"""
    base = _ev(it, a[0], fr)
    reg = _dotnet_regex(_ev(it, a[1], fr))
    rep = _ev(it, a[2], fr)
    if "$" in rep:
        raise NotSupported("REPLACE の置換文字列に $（.NET の置換パターン）")
    return reg.sub(lambda m: rep, base)


def _read_int_like(s: str) -> int | None:
    """TOINT／ISNUMERIC 共通（ToIntMethod:2357–2387、IsNumericMethod:2532–2569、Sub/LexicalAnalyzer.cs@ReadInt64:133–190）。
    数値でなければ None。10 進のみ（0x／0b／指数 e・p は本作の到達経路に無いので NotSupported）。"""
    if s == "":
        return None
    try:
        if cp932_len(s) > len(s):  # 全角文字（cp932 で 2 バイト）を含む
            return None
    except UnicodeEncodeError:
        raise NotSupported("cp932 にない文字を含む数値判定") from None
    i = 0
    if s[0] in "+-":
        if len(s) < 2 or not s[1].isdigit():
            return None
        i = 1
    elif not s[0].isdigit():
        return None
    if s[i:i + 2].lower() in ("0x", "0b"):
        raise NotSupported("16／2 進表記の数値判定")
    j = i
    while j < len(s) and s[j].isdigit():
        j += 1
    if j < len(s) and s[j] in "eEpP":
        raise NotSupported("指数表記の数値判定")
    value = int(s[i:j]) * (-1 if s[0] == "-" else 1)
    if j < len(s):
        if s[j] != ".":
            return None
        if not all(ch.isdigit() for ch in s[j + 1:]):
            return None
    return value


def m_isnumeric(it, a, fr) -> int:
    """`IsNumericMethod`:2532–2569（S21）。"""
    return 0 if _read_int_like(_ev(it, a[0], fr)) is None else 1


def m_toint(it, a, fr) -> int:
    """`ToIntMethod`:2357–2387（S21）。"""
    v = _read_int_like(_ev(it, a[0], fr))
    return 0 if v is None else v


BUILTINS = {
    "STRFINDU": m_strfindu, "STRCOUNT": m_strcount, "REPLACE": m_replace, "ISNUMERIC": m_isnumeric, "TOINT": m_toint,
    "GETBIT": m_getbit, "UNICODE": m_unicode, "STRFIND": m_strfind, "RAND": m_rand, "MAX": m_max,
    "MIN": m_min, "ABS": m_abs, "SIGN": m_sign, "LIMIT": m_limit, "POWER": m_power, "GROUPMATCH": m_groupmatch,
    "INRANGE": m_inrange, "STRLENS": m_strlens, "STRLENSU": m_strlensu, "SUBSTRING": m_substring,
    "SUBSTRINGU": m_substringu, "TOSTR": m_tostr,
}
