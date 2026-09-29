"""ERB 式的 AST 與剖析器。

照 `reference/emuera-1824/Emuera/GameData/Expression/ExpressionParser.cs` 的 `reduceTerm`／`TermStack`
（:327–439、:444–637）移植成同樣的 shift-reduce：
- 優先順位（`OperatorCode.cs`:13–47）：単項 > `* / %`(0x90) > `+ -`(0x80) > `<< >>`(0x70) > 大小比較(0x65)
  > `== !=`(0x60) > `& | ^`(0x50) > `&& || ^^ !& !|`(0x40) > `#`(0x10) > `?`(0x05)；
  直前の演算子の優先度が「同じか高い」なら還元する（:497–501）＝同順位は左結合。
- 単項 `+ - ~` は被演算子の後で還元待ち、`!`・前置 `++ --` は即還元（:458–470、:520–531）。
- 三項 `a ? b # c` は `#` の還元時に `?` と組になる（:596–625）。
- 変数の `:` 引数は 1 トークン（識別子・リテラル・括弧式）だけを読む（`while (!varArg)`:437）。
  変数の引数位置で「変数でも関数でもない識別子」は CSV 名として文字列リテラルになる（:264–272）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .lexer import ErbSyntaxError, FormSub, FormWord, Stream, Tok, analyse

# --- AST ---------------------------------------------------------------------------


class Expr:
    __slots__ = ()


@dataclass(slots=True)
class Lit(Expr):
    value: object  # int | str


@dataclass(slots=True)
class Var(Expr):
    name: str  # 大文字化済み（ICVariable=YES：Config.cs:28–38）
    args: list  # list[Expr]（0〜3 個、書かれた順）


@dataclass(slots=True)
class Call(Expr):
    name: str
    args: list  # list[Expr | None]


@dataclass(slots=True)
class Unary(Expr):
    op: str
    x: Expr


@dataclass(slots=True)
class Binary(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass(slots=True)
class Ternary(Expr):
    cond: Expr
    yes: Expr
    no: Expr


@dataclass(slots=True)
class FormPart:
    kind: str  # "%" "{" "@"
    expr: Optional[Expr]
    width: Optional[Expr] = None
    left: bool = False
    yes: Optional["Form"] = None
    no: Optional["Form"] = None


@dataclass(slots=True)
class Form(Expr):
    strs: list  # list[str]
    parts: list  # list[FormPart]


PRIORITY = {
    "*": 0x90, "/": 0x90, "%": 0x90,
    "+": 0x80, "-": 0x80,
    "<<": 0x70, ">>": 0x70,
    ">": 0x65, "<": 0x65, ">=": 0x65, "<=": 0x65,
    "==": 0x60, "!=": 0x60,
    "&": 0x50, "|": 0x50, "^": 0x50,
    "&&": 0x40, "||": 0x40, "^^": 0x40, "!&": 0x40, "!|": 0x40,
    "#": 0x10, "?": 0x05,
}
UNARY_OPS = {"+", "-", "~", "!", "++", "--"}


class Resolver:
    """識別子の種類の判定（呼び出し側が実装）。"""

    def is_variable(self, name: str) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def is_function(self, name: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def is_csv_name(self, var: str, name: str) -> bool:  # pragma: no cover
        raise NotImplementedError


class _TermStack:
    """`TermStack`:444–637。"""

    def __init__(self) -> None:
        self.state = 0
        self.wait_after = False
        self.stack: list = []

    def add_op(self, op: str) -> None:
        if self.state in (2, 3):
            raise ErbSyntaxError("式が異常です")
        if self.state == 0:
            if op not in UNARY_OPS:
                raise ErbSyntaxError("式が異常です")
            self.stack.append(("op", op))
            self.state = 2 if op in ("+", "-", "~") else 3
            return
        if op in ("++", "--"):
            raise ErbSyntaxError("後置インクリメント／デクリメントは未対応")
        if op not in PRIORITY:
            raise ErbSyntaxError("式が異常です")
        if self.wait_after:
            self._reduce_unary()
            self.wait_after = False
        pri = PRIORITY[op]
        while self._last_priority() >= pri:
            self._reduce_last_three()
        self.stack.append(("op", op))
        self.state = 0

    def add_term(self, term: Expr) -> None:
        if self.state == 1:
            raise ErbSyntaxError("式が異常です")
        self.stack.append(term)
        if self.state == 2:
            self.wait_after = True
        if self.state == 3:
            self._reduce_unary()
        self.state = 1

    def _last_priority(self) -> int:
        if len(self.stack) < 3:
            return -1
        top = self.stack[-2]
        return PRIORITY[top[1]] if isinstance(top, tuple) else -1

    def reduce_all(self) -> Optional[Expr]:
        if not self.stack:
            return None
        if self.state != 1:
            raise ErbSyntaxError("式が異常です")
        if self.wait_after:
            self._reduce_unary()
        self.wait_after = False
        while len(self.stack) > 1:
            self._reduce_last_three()
        return self.stack.pop()

    def _reduce_unary(self) -> None:
        operand = self.stack.pop()
        _, op = self.stack.pop()
        if op in ("++", "--"):
            raise ErbSyntaxError("前置インクリメント／デクリメントは未対応")
        self.stack.append(Unary(op, operand))

    def _reduce_last_three(self) -> None:
        right = self.stack.pop()
        _, op = self.stack.pop()
        left = self.stack.pop()
        if op in ("?", "#"):
            if op == "#" and len(self.stack) > 1:
                _, q = self.stack.pop()
                cond = self.stack.pop()
                if q != "?":
                    raise ErbSyntaxError("三項演算子が異常です")
                self.stack.append(Ternary(cond, left, right))
                return
            raise ErbSyntaxError("式の数が不足しています")
        self.stack.append(Binary(op, left, right))


# TermEndWith
T_EOL, T_COMMA, T_PAREN, T_ASSIGN = 1, 2, 4, 16


class Parser:
    """トークン列 → Expr。"""

    def __init__(self, toks: list[Tok], resolver: Resolver) -> None:
        self.toks = toks
        self.i = 0
        self.r = resolver

    @property
    def cur(self) -> Tok | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    @property
    def eol(self) -> bool:
        return self.i >= len(self.toks)

    def is_sym(self, s: str) -> bool:
        t = self.cur
        return t is not None and t.kind == "sym" and t.value == s

    def reduce_term(self, end: int = T_EOL, var_arg_of: str | None = None, allow_to: bool = False) -> Optional[Expr]:
        """`reduceTerm`:327–439。"""
        ts = _TermStack()
        ternary = 0
        while True:
            t = self.cur
            if t is None:
                break
            if t.kind == "str" or t.kind == "int":
                ts.add_term(Lit(t.value))
                self.i += 1
            elif t.kind == "form":
                ts.add_term(form_to_expr(t.value, self.r))
                self.i += 1
            elif t.kind == "id":
                name = str(t.value)
                up = name.upper()
                if up == "TO":
                    if allow_to:
                        break
                    raise ErbSyntaxError("TOキーワードはここでは使用できません")
                if up == "IS":
                    raise ErbSyntaxError("ISキーワードはここでは使用できません")
                ts.add_term(self._identifier(name, var_arg_of))
                if var_arg_of is not None:
                    break
                continue
            elif t.kind == "op":
                if var_arg_of is not None:
                    raise ErbSyntaxError("変数の引数の読み取り中に予期しない演算子")
                op = str(t.value)
                if op == "=":
                    if end & T_ASSIGN:
                        break
                    raise ErbSyntaxError("式中で代入演算子'='が使われています")
                ts.add_op(op)
                if op == "?":
                    ternary += 1
                elif op == "#":
                    if ternary <= 0:
                        raise ErbSyntaxError("対応する'?'のない'#'です")
                    ternary -= 1
                self.i += 1
            elif t.kind == "sym":
                s = t.value
                if s == "(":
                    self.i += 1
                    inner = self.reduce_term(T_PAREN)
                    if inner is None:
                        raise ErbSyntaxError("かっこの中に式が含まれていません")
                    ts.add_term(inner)
                    if not self.is_sym(")"):
                        raise ErbSyntaxError("対応する')'のない'('です")
                    self.i += 1
                    if var_arg_of is not None:
                        break
                    continue
                if s == ")" and end & T_PAREN:
                    break
                if s == "," and end & T_COMMA:
                    break
                raise ErbSyntaxError(f"予期しない記号'{s}'")
            else:  # pragma: no cover
                raise ErbSyntaxError("不明なトークン")
            if var_arg_of is not None:
                break
        if ternary > 0:
            raise ErbSyntaxError("'?'と'#'の数が正しく対応していません")
        return ts.reduce_all()

    def _identifier(self, name: str, var_arg_of: str | None) -> Expr:
        """`reduceIdentifier`:227–277。"""
        self.i += 1
        up = name.upper()
        if self.is_sym("(") or self.is_sym("["):
            if self.is_sym("["):
                raise ErbSyntaxError("[]を使った機能は未実装")
            self.i += 1
            args = self.reduce_arguments(T_PAREN)
            if not self.r.is_function(up):
                raise ErbSyntaxError(f"関数 {name} が見つかりません")
            return Call(up, args)
        if self.is_sym("."):
            raise ErbSyntaxError("名前空間は未実装")
        if self.is_sym("@"):
            raise ErbSyntaxError("@付き変数参照は未対応")
        if self.r.is_variable(up):
            if var_arg_of is not None:
                return Var(up, [])
            args: list[Expr] = []
            while self.is_sym(":"):
                if len(args) >= 3:
                    raise ErbSyntaxError(f"{name}の引数が多すぎます")
                self.i += 1
                a = self.reduce_term(T_EOL, var_arg_of=up)
                if a is None:
                    raise ErbSyntaxError("変数の:の後に引数がありません")
                args.append(a)
            return Var(up, args)
        if self.r.is_function(up):
            raise ErbSyntaxError(f"関数 {name} を括弧なしで参照")
        if var_arg_of is not None and self.r.is_csv_name(var_arg_of, name):
            return Lit(name)
        raise ErbSyntaxError(f"識別子 {name} を解釈できません")

    def reduce_arguments(self, end: int) -> list:
        """`ReduceArguments`:44–120（isDefine=false）。end: T_EOL（`,` 区切り、行末まで）／T_PAREN。"""
        term_end = T_COMMA if end == T_EOL else (T_PAREN | T_COMMA)
        out: list = []
        while True:
            t = self.cur
            if t is None:
                if end == T_PAREN:
                    raise ErbSyntaxError("'('に対応する')'が見つかりません")
                break
            if t.kind == "sym" and t.value == ")":
                if end == T_PAREN:
                    self.i += 1
                    break
                raise ErbSyntaxError("予期しない')'")
            out.append(self.reduce_term(term_end))
            if self.is_sym(","):
                self.i += 1
        return out


def form_to_expr(fw: FormWord, r: Resolver) -> Form:
    """`StrForm.FromWordToken`（StrForm.cs:51–142）：`%` は文字列式、`{}` は整数式。"""
    parts: list[FormPart] = []
    for sub in fw.subs:
        parts.append(_form_part(sub, r))
    return Form(list(fw.strs), parts)


def _form_part(sub: FormSub, r: Resolver) -> FormPart:
    if sub.kind == "@":
        cond = Parser(sub.tokens, r).reduce_term(T_EOL) if sub.tokens else Lit(0)
        yes = form_to_expr(sub.left, r) if sub.left else Form([""], [])
        no = form_to_expr(sub.right, r) if sub.right else Form([""], [])
        return FormPart("@", cond, yes=yes, no=no)
    p = Parser(sub.tokens, r)
    e = p.reduce_term(T_COMMA)
    if e is None:
        raise ErbSyntaxError("%%や{}の中に式が存在しません")
    width = None
    left = False
    if p.is_sym(","):
        p.i += 1
        width = p.reduce_term(T_COMMA)
        if p.is_sym(","):
            p.i += 1
            t = p.cur
            if t is None or t.kind != "id":
                raise ErbSyntaxError("','の後にRIGHT又はLEFTがありません")
            if str(t.value).upper() == "LEFT":
                left = True
            elif str(t.value).upper() != "RIGHT":
                raise ErbSyntaxError("','の後にRIGHT又はLEFT以外の単語")
            p.i += 1
    if not p.eol:
        raise ErbSyntaxError("書式の後に余分な文字")
    return FormPart(sub.kind, e, width, left)


def parse_expr(text: str, r: Resolver) -> Optional[Expr]:
    """単体テスト・補助用：1 つの式を最後まで読む。"""
    toks = analyse(Stream(text))
    p = Parser(toks, r)
    e = p.reduce_term(T_EOL)
    if not p.eol:
        raise ErbSyntaxError("式の後に余分な文字")
    return e


def walk(e, fn: Callable[[Expr], None]) -> None:
    """式木を前順で辿る（静的検査用）。"""
    if e is None:
        return
    fn(e)
    if isinstance(e, Var):
        for a in e.args:
            walk(a, fn)
    elif isinstance(e, Call):
        for a in e.args:
            walk(a, fn)
    elif isinstance(e, Unary):
        walk(e.x, fn)
    elif isinstance(e, Binary):
        walk(e.left, fn)
        walk(e.right, fn)
    elif isinstance(e, Ternary):
        walk(e.cond, fn)
        walk(e.yes, fn)
        walk(e.no, fn)
    elif isinstance(e, Form):
        for p in e.parts:
            walk(p.expr, fn)
            walk(p.width, fn)
            walk(p.yes, fn)
            walk(p.no, fn)
