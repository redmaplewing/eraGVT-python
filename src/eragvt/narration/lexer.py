"""ERB 的字句解析（式・FORM 文字列）。

照 `reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs` 移植（行號見各函式）。只做本 catalog 需要的部分；
引擎本身會報錯的寫法一律丟 `ErbSyntaxError`（呼叫端把該函式標為 unsupported）。
emuera.config：「全角スペースをホワイトスペースに含める:NO」「FORM中の三連記号を展開しない:YES」
（`source/earGVP/emuera.config`），所以全形空白是錯誤、`***` 等照字面。
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ErbSyntaxError(Exception):
    """引擎在載入或執行時會視為錯誤的語法（CodeEE 相當）。"""


# --- Token ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Tok:
    kind: str  # "int" "str" "form" "id" "op" "sym"
    value: object


# --- FORM 文字列 -------------------------------------------------------------------


@dataclass(slots=True)
class FormSub:
    """`%式,幅,LEFT%`（kind="%"）／`{式,幅,LEFT}`（kind="{"）／`\\@式?左#右\\@`（kind="@"）。"""

    kind: str
    tokens: list[Tok] = field(default_factory=list)  # 式の部分（未解析のトークン列）
    left: FormWord | None = None  # \@ の真側
    right: FormWord | None = None  # \@ の偽側（# がない場合 None）


@dataclass(slots=True)
class FormWord:
    """`LexicalAnalyzer.AnalyseFormattedString` の結果：strs[0] sub[0] strs[1] sub[1] … strs[n]。"""

    strs: list[str]
    subs: list[FormSub]


class Stream:
    """`Sub/StringStream.cs` 相當（'\\0' = EOS）。"""

    __slots__ = ("s", "p")

    def __init__(self, s: str, p: int = 0) -> None:
        self.s = s
        self.p = p

    @property
    def cur(self) -> str:
        return self.s[self.p] if self.p < len(self.s) else "\0"

    @property
    def nxt(self) -> str:
        return self.s[self.p + 1] if self.p + 1 < len(self.s) else "\0"

    @property
    def eos(self) -> bool:
        return self.p >= len(self.s)

    def rest(self) -> str:
        return self.s[self.p :]


_ID_END = set(" \t+-*/%=!<>|&^~?#)}],:({[$\\'\"@.;")


def read_identifier(st: Stream) -> str:
    """`ReadSingleIdentifier`:381–434。全形空白は SystemAllowFullSpace=NO なのでエラー。"""
    start = st.p
    while not st.eos:
        c = st.cur
        if c in _ID_END:
            break
        if c == "　":
            raise ErbSyntaxError("予期しない全角スペース")
        st.p += 1
    return st.s[start : st.p]


def skip_ws(st: Stream) -> None:
    """`SkipWhiteSpace`：半角空白・タブ（全角は含めない）。"""
    while st.cur in (" ", "\t"):
        st.p += 1


def _read_digits(st: Stream, base: int) -> str:
    start = st.p
    if st.cur in "+-":
        st.p += 1
    while not st.eos:
        c = st.cur
        if base == 10 and c.isdigit():
            st.p += 1
        elif base == 16 and (c.isdigit() or c in "abcdefABCDEF"):
            st.p += 1
        elif base == 2 and c.isdigit():
            if c not in "01":
                raise ErbSyntaxError("二進法表記の中で使用できない文字")
            st.p += 1
        else:
            break
    return st.s[start : st.p]


def read_int(st: Stream) -> int:
    """`ReadInt64`:133–185（0x／0b、p／e の指数）。"""
    base = 10
    if st.cur == "0" and st.nxt in "xX":
        base = 16
        st.p += 2
    elif st.cur == "0" and st.nxt in "bB":
        base = 2
        st.p += 2
    digits = _read_digits(st, base)
    try:
        value = int(digits, base)
    except ValueError as e:
        raise ErbSyntaxError(f"数値として解釈できない：{digits}") from e
    exp_base = 2 if st.cur in "pP" else 10 if st.cur in "eE" else 0
    if exp_base:
        st.p += 1
        exp = int(_read_digits(st, base) or "0", base)
        if exp:
            value = int(value * (exp_base**exp))
    return value


def read_string(st: Stream, end: str) -> str:
    """`ReadString`:442–495（`"..."` の中身など）。end: '"' または "," または "(" 系。"""
    buf: list[str] = []
    while True:
        c = st.cur
        if c == "\0":
            break
        if end == '"' and c == '"':
            break
        if end == "," and c == ",":
            break
        if c == "\\":
            st.p += 1
            e = st.cur
            if e == "\0":
                raise ErbSyntaxError("エスケープ文字\\の後に文字がありません")
            buf.append({"s": " ", "S": "　", "t": "\t", "n": "\n"}.get(e, e))
            st.p += 1
            continue
        buf.append(c)
        st.p += 1
    return "".join(buf)


def read_operator(st: Stream, allow_assign: bool = False) -> str:
    """`ReadOperator`:498–605。"""
    c = st.cur
    st.p += 1
    n = st.cur
    two = {
        ("+", "+"): "++", ("-", "-"): "--", ("=", "="): "==", ("!", "="): "!=", ("!", "&"): "!&",
        ("!", "|"): "!|", ("<", "="): "<=", ("<", "<"): "<<", (">", "="): ">=", (">", ">"): ">>",
        ("|", "|"): "||", ("&", "&"): "&&", ("^", "^"): "^^",
    }.get((c, n))
    if two:
        st.p += 1
        return two
    if c == "=":
        if allow_assign:
            return "="
        raise ErbSyntaxError("予期しない代入演算子'='")
    if c in "+-*/%!<>|&^~?#":
        return c
    raise ErbSyntaxError(f"'{c}'は演算子として認識できません")


# LexEndWith
EOL, PERCENT, CURLY, QUESTION, COMMA, OPERATOR = "eol", "%", "}", "?", ",", "op"


def analyse(st: Stream, end: str = EOL, allow_assign: bool = False) -> list[Tok]:
    """`Analyse`:789–990。`end` で止まったとき `st.cur` はその終端文字。"""
    out: list[Tok] = []
    nest_s = nest_l = 0
    while True:
        c = st.cur
        if c in ("\n", "\0"):
            break
        if c in (" ", "\t"):
            st.p += 1
            continue
        if c == "　":
            raise ErbSyntaxError("予期しない全角スペース")
        if "0" <= c <= "9":
            out.append(Tok("int", read_int(st)))
            continue
        if c in "+-*/%=!<>|&^~?#":
            if nest_s == 0 and nest_l == 0:
                if end == OPERATOR:
                    break
                if end == PERCENT and c == "%":
                    break
                if end == QUESTION and c == "?":
                    break
            out.append(Tok("op", read_operator(st, allow_assign)))
            continue
        if c == ")":
            out.append(Tok("sym", ")"))
            nest_s -= 1
        elif c == "]":
            out.append(Tok("sym", "]"))
            nest_l -= 1
        elif c == "(":
            out.append(Tok("sym", "("))
            nest_s += 1
        elif c == "[":
            if st.nxt == "[":
                raise ErbSyntaxError("予期しない文字'[['")
            out.append(Tok("sym", "["))
            nest_l += 1
        elif c == ":":
            out.append(Tok("sym", ":"))
        elif c == ",":
            if end == COMMA and nest_s == 0:
                break
            out.append(Tok("sym", ","))
        elif c == "'":
            # 代入文の左辺探索中の `'=`（:895–900）のみ許可
            if end == OPERATOR and nest_s == 0 and nest_l == 0 and st.nxt == "=":
                break
            raise ErbSyntaxError("予期しない文字'''")
        elif c == "}":
            if end == CURLY:
                break
            raise ErbSyntaxError("予期しない文字'}'")
        elif c == '"':
            st.p += 1
            out.append(Tok("str", read_string(st, '"')))
            if st.cur != '"':
                raise ErbSyntaxError('"が閉じられていません')
        elif c == "@":
            if st.nxt != '"':
                out.append(Tok("sym", "@"))
            else:
                st.p += 2
                out.append(Tok("form", analyse_form(st, '"')))
                if st.cur != '"':
                    raise ErbSyntaxError('"が閉じられていません')
        elif c == "\\":
            if st.nxt != "@":
                raise ErbSyntaxError("予期しない文字'\\'")
            st.p += 2
            out.append(Tok("form", FormWord(["", ""], [analyse_yen_at(st)])))
            continue
        elif c in "{$":
            raise ErbSyntaxError(f"予期しない文字'{c}'")
        elif c == ";":
            # 行中コメント（:954–966）。;!; は読み飛ばし（;#; はデバッグモードのみ）
            if st.s.startswith(";!;", st.p):
                st.p += 3
                continue
            st.p = len(st.s)
            break
        elif c == ".":
            out.append(Tok("sym", "."))
        else:
            out.append(Tok("id", read_identifier(st)))
            continue
        st.p += 1
    if nest_s or nest_l:
        raise ErbSyntaxError("括弧の対応が取れていません")
    return out


# FormStrEndWith
F_EOL, F_DQ, F_SHARP, F_YENAT, F_CALLNAME = "eol", '"', "#", "@", "call"


def analyse_form(st: Stream, end: str = F_EOL, trim: bool = False) -> FormWord:
    """`AnalyseFormattedString`:1108–1222。F_CALLNAME = LeftParenthesis_Bracket_Comma_Semicolon。"""
    strs: list[str] = []
    subs: list[FormSub] = []
    buf: list[str] = []
    while True:
        c = st.cur
        if c in ("\n", "\0"):
            break
        if c == '"' and end == F_DQ:
            break
        if c == "#" and end == F_SHARP:
            break
        if c == "," and end == F_CALLNAME:
            break
        if c in "([;" and end == F_CALLNAME:
            break
        if c == "%":
            strs.append("".join(buf))
            buf = []
            st.p += 1
            subs.append(FormSub("%", analyse(st, PERCENT)))
            if st.cur != "%":
                raise ErbSyntaxError("'%'に対応する'%'が見つかりません")
        elif c == "{":
            strs.append("".join(buf))
            buf = []
            st.p += 1
            subs.append(FormSub("{", analyse(st, CURLY)))
            if st.cur != "}":
                raise ErbSyntaxError("'{'に対応する'}'が見つかりません")
        elif c == "\\":
            st.p += 1
            e = st.cur
            if e == "\0":
                raise ErbSyntaxError("エスケープ文字\\の後に文字がありません")
            if e == "@":
                if end in (F_YENAT, F_SHARP):
                    break
                strs.append("".join(buf))
                buf = []
                st.p += 1
                subs.append(analyse_yen_at(st))
                continue
            if e == "\n":
                pass
            else:
                buf.append({"s": " ", "S": "　", "t": "\t", "n": "\n"}.get(e, e))
                if e not in "sStn":
                    st.p += 1
                    continue
        else:
            # 三連記号（*** など）は「FORM中の三連記号を展開しない:YES」なので字面どおり（:1159–1174）
            buf.append(c)
        st.p += 1
    strs.append("".join(buf))
    if trim and strs:
        strs[0] = strs[0].lstrip(" \t")
        strs[-1] = strs[-1].rstrip(" \t")
    return FormWord(strs, subs)


def analyse_yen_at(st: Stream) -> FormSub:
    """`AnalyseYenAt`:1231–1257：`\\@` の直後から。"""
    cond = analyse(st, QUESTION)
    if st.cur != "?":
        raise ErbSyntaxError("'\\@'に対応する'?'が見つかりません")
    st.p += 1
    left = analyse_form(st, F_SHARP, trim=True)
    if st.cur != "#":
        if st.cur != "@":
            raise ErbSyntaxError("'\\@','?'に対応する'#'が見つかりません")
        st.p += 1
        return FormSub("@", cond, left, None)
    st.p += 1
    right = analyse_form(st, F_YENAT, trim=True)
    if st.cur != "@":
        raise ErbSyntaxError("'\\@'が閉じられていません")
    st.p += 1
    return FormSub("@", cond, left, right)
