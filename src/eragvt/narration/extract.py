"""抽取器：ERB 檔 → 函式單位的節點樹（`nodes.FuncDef`）。

只支援「文字輸出＋條件分岐」子集（見 `docs/wiki/python/narration.md`）；子集外的敘述留下 `Unsupported`
節點並記入 `FuncDef.unsupported`（原因＋行號），整個函式因此不可執行。**不猜**：無法照引擎語意解析的一律 unsupported。

行的讀法照 `reference/emuera-1824/Emuera/Sub/EraStreamReader.cs@ReadEnabledLine`:62–130（空行略過、`{`〜`}` 以空白連結）、
`GameProc/ErbLoader.cs@loadErb`:283–400（`[SKIPSTART]`〜`[SKIPEND]`、`#` 行只在函式宣言直後有效、`@`／`$` 標籤）、
`GameProc/LogicalLineParser.cs@ParseLine`:386–480（命令判定：命令名の直後は半角空白・タブ・`;` のみ、1 文字読み飛ばして引数；
それ以外は代入文）。
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from . import nodes as N
from .expr import Call, Form, Parser, Resolver, T_COMMA, T_EOL, T_PAREN, Var, form_to_expr, walk
from .lexer import (
    COMMA,
    F_CALLNAME,
    F_EOL,
    OPERATOR,
    ErbSyntaxError,
    Stream,
    analyse,
    analyse_form,
    read_identifier,
    skip_ws,
)
from .symbols import BUILTIN_STR, BUILTIN_VARS, CSV_NAME_TABLE, INSTRUCTIONS, UserVar

_NEWLINES = re.compile(r"\r\n|\r|\n")

# 式中関数（GameData/Function/Creator.Method.cs の methodList）
BUILTIN_METHODS = frozenset(
    """GETCHARA GETSPCHARA CSVNAME CSVCALLNAME CSVNICKNAME CSVMASTERNAME CSVCSTR CSVBASE CSVABL CSVMARK CSVEXP
    CSVRELATION CSVTALENT CSVCFLAG CSVEQUIP CSVJUEL FINDCHARA FINDLASTCHARA EXISTCSV VARSIZE CHKFONT CHKDATA ISSKIP
    MOUSESKIP MESSKIP GETCOLOR GETDEFCOLOR GETFOCUSCOLOR GETBGCOLOR GETDEFBGCOLOR GETSTYLE GETFONT BARSTR
    CURRENTALIGN CURRENTREDRAW COLOR_FROMNAME COLOR_FROMRGB CHKVARDATA CHKCHARADATA CHKGLOBALDATA FIND_VARDATA
    FIND_CHARADATA MONEYSTR PRINTCPERLINE PRINTCLENGTH SAVENOS GETTIME GETTIMES GETMILLISECOND GETSECOND RAND MIN
    MAX ABS POWER SQRT CBRT LOG LOG10 EXPONENT SIGN LIMIT SUMARRAY SUMCARRAY MATCH CMATCH GROUPMATCH NOSAMES
    ALLSAMES MAXARRAY MAXCARRAY MINARRAY MINCARRAY GETBIT GETNUM GETPALAMLV GETEXPLV FINDELEMENT FINDLASTELEMENT
    INRANGE INRANGEARRAY INRANGECARRAY GETNUMB ARRAYMSORT STRLENS STRLENSU SUBSTRING SUBSTRINGU STRFIND STRFINDU
    STRCOUNT TOSTR TOINT TOUPPER TOLOWER TOHALF TOFULL LINEISEMPTY REPLACE UNICODE UNICODEBYTE CONVERT ISNUMERIC
    ESCAPE ENCODETOUNI CHARATU GETLINESTR STRFORM STRJOIN GETCONFIG GETCONFIGS""".split()
)

# --- 行の読み込み --------------------------------------------------------------------


def read_logical_lines(raw: bytes) -> list[tuple[int, str]]:
    """ERB／ERH 1 檔 → `(行號, 文字)`。空白行・註解行・SKIP 區間を除き、`{ }` を連結する。
    BOM 付き UTF-8 前提（BOM なしも UTF-8 として読む：docs/wiki/bridge/unresolved.md の無 BOM 項と同じ扱い）。"""
    text = raw.decode("utf-8-sig", errors="replace")
    rows = _NEWLINES.split(text)
    out: list[tuple[int, str]] = []
    skip = False
    i = 0
    n = len(rows)
    while i < n:
        line = rows[i]
        no = i + 1
        i += 1
        st = line.lstrip(" \t")
        if not st:
            continue
        if st.startswith("{"):
            if st.strip() != "{":
                raise ErbSyntaxError(f"{no}: 行連結始端記号'{{'の行に他の文字")
            buf: list[str] = []
            while i < n:
                seg = rows[i]
                i += 1
                t = seg.lstrip()
                if t.startswith("}"):
                    break
                buf.append(seg)
                buf.append(" ")
            line = "".join(buf)
            st = line.lstrip(" \t")
        if st.startswith("[") and not st.startswith("[["):
            tok = st[1:].split("]")[0].strip().split()
            key = tok[0].upper() if tok else ""
            if key == "SKIPSTART":
                skip = True
            elif key == "SKIPEND":
                skip = False
            elif key == "IF_DEBUG":
                skip = True
            elif key in ("IF_NDEBUG", "ENDIF"):
                skip = False if key == "ENDIF" else skip
            continue
        if skip:
            continue
        if st.startswith(";"):
            continue
        out.append((no, st))
    return out


def scan_labels(lines: list[tuple[int, str]]) -> list[tuple[str, int, int]]:
    """`@NAME` 行の位置：`(大文字名, 開始 index, 終了 index)`（lines の index）。"""
    labels: list[tuple[str, int]] = []
    for k, (_, text) in enumerate(lines):
        if text.startswith("@"):
            st = Stream(text, 1)
            skip_ws(st)
            name = read_identifier(st)
            labels.append((name.upper(), k))
    out = []
    for j, (name, k) in enumerate(labels):
        end = labels[j + 1][1] if j + 1 < len(labels) else len(lines)
        out.append((name, k, end))
    return out


# --- 解析 ------------------------------------------------------------------------------

_PRINT_RE = re.compile(r"^PRINT(SINGLE)?(V|S|FORM|FORMS)?(K)?(D)?(L|W)?$")
_PRINT_C_RE = re.compile(r"^PRINT(FORM)?(L)?C(K|D)?$")
_BLOCK_END = {
    "ELSE", "ELSEIF", "ENDIF", "CASE", "CASEELSE", "ENDSELECT", "NEXT", "WEND", "REND", "LOOP", "ENDDATA",
    "DATA", "DATAFORM", "DATALIST", "ENDLIST", "CATCH", "ENDCATCH", "ENDFUNC",
}
_UNSUPPORTED_INSTR_REASON = {
    "GOTO": "GOTO", "TRYGOTO": "GOTO", "GOTOFORM": "GOTO", "TRYGOTOFORM": "GOTO", "TRYCGOTO": "GOTO",
    "TRYCGOTOFORM": "GOTO", "JUMP": "JUMP", "TRYJUMP": "JUMP", "JUMPFORM": "JUMP", "TRYJUMPFORM": "JUMP",
    "BEGIN": "BEGIN", "INPUT": "INPUT", "INPUTS": "INPUT", "TINPUT": "INPUT", "TINPUTS": "INPUT",
    "ONEINPUT": "INPUT", "ONEINPUTS": "INPUT", "TONEINPUT": "INPUT", "TONEINPUTS": "INPUT",
}


class FuncResolver(Resolver):
    def __init__(self, ctx: "ExtractContext", private: dict[str, bool]) -> None:
        self.ctx = ctx
        self.private = private

    def is_variable(self, name: str) -> bool:
        return name in self.private or name in BUILTIN_VARS or name in self.ctx.user_vars

    def is_function(self, name: str) -> bool:
        return name in BUILTIN_METHODS or self.ctx.is_user_method(name)

    def is_csv_name(self, var: str, name: str) -> bool:
        table = CSV_NAME_TABLE.get(var)
        if var == "CDFLAG":
            return self.ctx.csv_has("CDFLAG1", name) or self.ctx.csv_has("CDFLAG2", name)
        return table is not None and self.ctx.csv_has(table, name)

    def is_str_var(self, name: str) -> bool:
        if name in self.private:
            return self.private[name]
        if name in BUILTIN_STR:
            return True
        uv = self.ctx.user_vars.get(name)
        return bool(uv and uv.is_str)


class ExtractContext:
    """抽取時需要的全域資訊。"""

    def __init__(
        self,
        user_vars: dict[str, UserVar],
        csv_names: dict[str, set[str]],
        is_user_method: Callable[[str], bool],
        hook_matcher: Optional[Callable[[str, int, str], Optional[str]]] = None,
    ) -> None:
        self.user_vars = user_vars
        self.csv_names = csv_names
        self.is_user_method = is_user_method
        self.hook_matcher = hook_matcher

    def csv_has(self, table: str, name: str) -> bool:
        return name in self.csv_names.get(table, ())


class _Unsup(Exception):
    pass


class FuncParser:
    def __init__(self, ctx: ExtractContext, rel: str, lines: list[tuple[int, str]]) -> None:
        self.ctx = ctx
        self.rel = rel
        self.lines = lines
        self.k = 0
        self.fd: N.FuncDef

    # --- entry ---
    def parse(self) -> N.FuncDef:
        no, label = self.lines[0]
        end_line = self.lines[-1][0]
        st = Stream(label, 1)
        skip_ws(st)
        name = read_identifier(st).upper()
        fd = N.FuncDef(name, self.rel, no, end_line)
        self.fd = fd
        private: dict[str, bool] = {"LOCAL": False, "LOCALS": True, "ARG": False, "ARGS": True}
        fd.private = private
        self.res = FuncResolver(self.ctx, private)
        self.k = 1
        # '#' 行（関数宣言直後のみ有効：ErbLoader.cs:345–354）
        while self.k < len(self.lines) and self.lines[self.k][1].startswith("#"):
            sno, text = self.lines[self.k]
            self.k += 1
            word = text[1:].split(None, 1)[0].upper() if text[1:].strip() else ""
            if word == "FUNCTION":
                fd.kind = "int"
            elif word == "FUNCTIONS":
                fd.kind = "str"
            elif word in ("DIM", "DIMS"):
                try:
                    from .symbols import parse_dim

                    uv = parse_dim(text[1:], self.ctx.user_vars)
                except ErbSyntaxError as e:
                    self._unsup(sno, f"#DIM 解析不能：{e}")
                    continue
                if uv.chara or uv.glob or uv.save:
                    self._unsup(sno, f"#DIM {uv.name} の種類（SAVEDATA 等）は未対応")
                if uv.const:
                    if any(v is None for v in uv.values):
                        self._unsup(sno, f"#DIM CONST {uv.name} の値を評価できません")
                    fd.consts[uv.name] = uv.values
                private[uv.name] = uv.is_str
            elif word in ("LOCALSIZE", "LOCALSSIZE", "PRI", "LATER", "SINGLE", "ONLY"):
                if word in ("PRI", "LATER", "SINGLE", "ONLY"):
                    self._unsup(sno, f"イベント関数（#{word}）")
            else:
                self._unsup(sno, f"#{word}")
        # 引数（ErbLoader.cs@setLabelsArg:490–620）
        self._parse_params(no, st)
        body, term = self._block(set())
        if term is not None:
            self._unsup(term[0], f"対応しない {term[1]}")
        fd.body = body
        return fd

    def _parse_params(self, no: int, st: Stream) -> None:
        skip_ws(st)
        if st.eos:
            return
        c = st.cur
        try:
            toks = analyse(st, allow_assign=True)
        except ErbSyntaxError as e:
            self._unsup(no, f"関数宣言の引数：{e}")
            return
        if not toks:
            return
        p = Parser(toks, self.res)
        if p.is_sym(","):
            p.i += 1
            end = T_EOL
        elif p.is_sym("("):
            p.i += 1
            end = T_PAREN
        else:
            self._unsup(no, "関数宣言の引数の書式")
            return
        from .expr import T_ASSIGN

        term_end = (T_COMMA if end == T_EOL else (T_PAREN | T_COMMA)) | T_ASSIGN
        try:
            while not p.eol:
                if p.is_sym(")"):
                    p.i += 1
                    break
                v = p.reduce_term(term_end)
                default = None
                t = p.cur
                if t is not None and t.kind == "op" and t.value == "=":
                    p.i += 1
                    d = p.reduce_term(term_end & ~T_ASSIGN)
                    default = getattr(d, "value", None)
                if not isinstance(v, Var):
                    raise ErbSyntaxError("関数定義の引数には代入可能な変数を指定してください")
                self.fd.params.append((v, default))
                if p.is_sym(","):
                    p.i += 1
        except ErbSyntaxError as e:
            self._unsup(no, f"関数宣言の引数：{e}")

    # --- helpers ---
    def _unsup(self, line: int, reason: str) -> N.Unsupported:
        self.fd.unsupported.append((line, reason))
        return N.Unsupported(line, reason)

    def _expr_line(self, text: str) -> Optional[object]:
        p = Parser(analyse(Stream(text)), self.res)
        e = p.reduce_term(T_EOL)
        if not p.eol:
            raise ErbSyntaxError("式の後に余分な文字")
        return e

    def _args_line(self, text: str) -> list:
        p = Parser(analyse(Stream(text)), self.res)
        return p.reduce_arguments(T_EOL)

    def _note_calls(self, e) -> None:
        def f(x):
            if isinstance(x, Call) and x.name not in BUILTIN_METHODS:
                self.fd.calls.add(x.name)

        walk(e, f)

    # --- block ---
    def _block(self, terms: set[str]):
        """terms のいずれかの命令が来るまで読む。戻り値 (stmts, (line, name, argtext) | None)。"""
        out: list = []
        while self.k < len(self.lines):
            no, text = self.lines[self.k]
            if text.startswith("#"):
                self.k += 1
                out.append(self._unsup(no, "関数宣言直後以外の # 行"))
                continue
            if text.startswith("$"):
                # $ラベル（LogicalLineParser.cs:290–320：識別子を ToUpper、引数があれば警告のみ）
                self.k += 1
                lst = Stream(text, 1)
                try:
                    lname = read_identifier(lst).upper()
                except ErbSyntaxError:
                    out.append(self._unsup(no, "$ラベル名が不正"))
                    continue
                out.append(N.Label(no, lname))
                continue
            name, argtext = self._instr_name(text)
            if name in _BLOCK_END:
                if name in terms:
                    self.k += 1
                    return out, (no, name, argtext)
                self.k += 1
                out.append(self._unsup(no, f"対応しない {name}"))
                continue
            self.k += 1
            stmt = self._stmt(no, text, name, argtext)
            if stmt is not None:
                out.append(stmt)
        return out, None

    def _instr_name(self, text: str) -> tuple[Optional[str], str]:
        """命令なら (命令名, 引数文字列)、代入文なら (None, "")。"""
        if text[0] in "+-":
            return None, ""
        st = Stream(text)
        try:
            ident = read_identifier(st)
        except ErbSyntaxError:
            return None, ""
        up = ident.upper()
        if up in INSTRUCTIONS or up in BUILTIN_METHODS:
            if st.eos:
                return up, ""
            if st.cur in (";", " ", "\t"):
                return up, st.s[st.p + 1 :]
            return "!BAD", text
        return None, ""

    def _stmt(self, no: int, text: str, name: Optional[str], arg: str):
        try:
            return self._stmt_inner(no, text, name, arg)
        except ErbSyntaxError as e:
            return self._unsup(no, f"構文：{e}")
        except _Unsup as e:
            return self._unsup(no, str(e))

    def _stmt_inner(self, no: int, text: str, name: Optional[str], arg: str):
        # hook（狀態變化行を Python 移植で代替：hooks.py）
        if self.ctx.hook_matcher is not None and not getattr(self, "_hooking", False):
            key = self.ctx.hook_matcher(self.fd.name, no, text)
            if key is not None:
                if name in ("IF", "SELECTCASE", "FOR", "WHILE", "REPEAT", "DO", "SIF"):
                    raise _Unsup(f"ブロック命令 {name} は hook にできない")
                self._hooking = True
                try:
                    inner = self._stmt_inner(no, text, name, arg)
                finally:
                    self._hooking = False
                if isinstance(inner, N.CallStmt):
                    from .hooks import HOOK_CALLS

                    if not isinstance(inner.name, str) or inner.name not in HOOK_CALLS:
                        raise _Unsup(f"hook 化できない CALL {inner.name}")
                    self.fd.calls.discard(inner.name)
                elif isinstance(inner, (N.Assign, N.BitOp)):
                    from .hooks import HOOK_WRITABLE

                    if inner.target.name not in HOOK_WRITABLE:
                        raise _Unsup(f"hook 化できない代入先 {inner.target.name}")
                else:
                    raise _Unsup("hook 化できない文")
                h = N.Hook(no, key, text, [inner])
                self.fd.hooks.append(h)
                return h
        if name is None:
            return self._assign(no, text)
        if name == "!BAD":
            raise ErbSyntaxError("命令の直後に半角スペース・タブ以外の文字")
        m = _PRINT_RE.match(name)
        if m and name not in ("PRINT_ABL",):
            return self._print(no, m, arg)
        if name in ("PRINTPLAIN", "PRINTPLAINFORM"):
            a = arg if name == "PRINTPLAIN" else form_to_expr(analyse_form(Stream(arg), F_EOL), self.res)
            self._note_calls(a if not isinstance(a, str) else None)
            return N.Print(no, "raw" if name == "PRINTPLAIN" else "form", a, plain=True)
        if name.startswith("PRINTDATA"):
            return self._printdata(no, name, arg)
        if name in ("IF",):
            return self._if(no, arg)
        if name == "SIF":
            cond = self._expr_line(arg)
            self._note_calls(cond)
            if self.k >= len(self.lines):
                raise _Unsup("SIF の次の行がありません")
            sno, stext = self.lines[self.k]
            sname, sarg = self._instr_name(stext)
            if sname in _BLOCK_END or sname in ("IF", "SELECTCASE", "FOR", "WHILE", "REPEAT", "DO", "SIF") or (
                sname and sname.startswith("PRINTDATA")
            ) or stext.startswith(("#", "$", "@")):
                raise _Unsup("SIF の次の行が単文でない")
            self.k += 1
            body = self._stmt(sno, stext, sname, sarg)
            return N.Sif(no, cond, body)
        if name == "SELECTCASE":
            return self._select(no, arg)
        if name in ("FOR",):
            args = self._args_line(arg)
            if len(args) < 3 or not isinstance(args[0], Var):
                raise ErbSyntaxError("FOR の引数")
            for a in args:
                self._note_calls(a)
            self._check_local_target(args[0])
            body, term = self._block({"NEXT"})
            if term is None:
                raise _Unsup("NEXT がありません")
            return N.For(no, args[0], args[1], args[2], args[3] if len(args) > 3 else None, body)
        if name == "WHILE":
            cond = self._expr_line(arg)
            self._note_calls(cond)
            body, term = self._block({"WEND"})
            if term is None:
                raise _Unsup("WEND がありません")
            return N.While(no, cond, body)
        if name == "REPEAT":
            cnt = self._expr_line(arg)
            body, term = self._block({"REND"})
            if term is None:
                raise _Unsup("REND がありません")
            return N.Repeat(no, cnt, body)
        if name == "DO":
            body, term = self._block({"LOOP"})
            if term is None:
                raise _Unsup("LOOP がありません")
            return N.Loop(no, self._expr_line(term[2]), body)
        if name == "BREAK":
            return N.Break(no)
        if name == "CONTINUE":
            return N.Continue(no)
        if name in ("SETCOLOR",):
            args = self._args_line(arg)
            return N.Style(no, "SETCOLOR", args)
        if name in ("RESETCOLOR", "FONTBOLD", "FONTITALIC", "FONTREGULAR"):
            return N.Style(no, name)
        if name == "SETFONT":
            e = self._expr_line(arg) if arg.strip() else None
            return N.Style(no, "SETFONT", [e])
        if name == "ALIGNMENT":
            return N.Style(no, "ALIGNMENT", [arg.strip().upper()])
        if name == "CLEARLINE":
            return N.ClearLine(no, self._expr_line(arg))
        if name == "DRAWLINE":
            return N.DrawLine(no)
        if name == "DRAWLINEFORM":
            f = form_to_expr(analyse_form(Stream(arg), F_EOL), self.res)
            self._note_calls(f)
            return N.DrawLine(no, f)
        if name == "GOTO":
            # 定数ラベル名のみ（TRYGOTO／GOTOFORM 系は子集合外のまま）。名前は ToUpper（Instraction.Child.cs:2387–2392）
            lst = Stream(arg.strip())
            lname = read_identifier(lst).upper()
            skip_ws(lst)
            if not lst.eos:
                raise _Unsup("GOTO の引数")
            return N.Goto(no, lname)
        if name == "INPUTS":
            if arg.strip():
                raise _Unsup("命令 INPUTS（既定値つき）")
            return N.Input(no, "S")
        if name in ("WAIT", "FORCEWAIT", "WAITANYKEY"):
            return N.Wait(no, name)
        if name == "RETURN":
            vals = self._args_line(arg) if arg.strip() else []
            for v in vals:
                self._note_calls(v)
            return N.Return(no, vals)
        if name == "RETURNF":
            v = self._expr_line(arg) if arg.strip() else None
            self._note_calls(v)
            return N.ReturnF(no, v)
        if name in ("CALL", "TRYCALL", "CALLFORM", "TRYCALLFORM", "TRYCCALL", "TRYCCALLFORM", "CALLF", "CALLFORMF"):
            return self._call(no, name, arg)
        if name in ("SETBIT", "CLEARBIT", "INVERTBIT"):
            args = self._args_line(arg)
            if not args or not isinstance(args[0], Var):
                raise ErbSyntaxError(f"{name} の引数")
            self._check_local_target(args[0])
            return N.BitOp(no, {"SETBIT": 1, "CLEARBIT": 0, "INVERTBIT": -1}[name], args[0], args[1:])
        if name in ("STRLEN", "STRLENU", "STRLENFORM", "STRLENFORMU"):
            if "FORM" in name:
                f = form_to_expr(analyse_form(Stream(arg), F_EOL), self.res)
                self._note_calls(f)
                return N.StrLen(no, "form", f, name.endswith("U"))
            return N.StrLen(no, "raw", arg, name.endswith("U"))
        if name == "VARSET":
            args = self._args_line(arg)
            if not args or not isinstance(args[0], Var):
                raise ErbSyntaxError("VARSET の引数")
            self._check_local_target(args[0])
            for a in args[1:]:
                self._note_calls(a)
            rest = list(args[1:]) + [None] * 3
            return N.VarSet(no, args[0], rest[0], rest[1], rest[2])
        if name in BUILTIN_METHODS:
            args = self._args_line(arg) if arg.strip() else []
            for a in args:
                self._note_calls(a)
            return N.MethodStmt(no, name, args)
        if name in _UNSUPPORTED_INSTR_REASON:
            raise _Unsup(f"命令 {name}（{_UNSUPPORTED_INSTR_REASON[name]}）")
        raise _Unsup(f"命令 {name}")

    # --- PRINT ---
    def _print(self, no: int, m: re.Match, arg: str) -> N.Print:
        single, kind, kflag, dflag, lw = m.groups()
        if kind == "V":
            raise _Unsup("PRINTV 系")
        if kflag:
            raise _Unsup("PRINT K 系（かな変換）")
        if kind is None:
            a: object = arg
            k = "raw"
        elif kind == "S":
            a = self._expr_line(arg)
            k = "expr"
        elif kind == "FORM":
            a = form_to_expr(analyse_form(Stream(arg), F_EOL), self.res)
            k = "form"
        else:  # FORMS
            e = self._expr_line(arg)
            a = e
            k = "forms"
        if not isinstance(a, str):
            self._note_calls(a)
        return N.Print(no, k, a, newline=lw in ("L", "W"), wait=lw == "W", dflag=bool(dflag))

    def _printdata(self, no: int, name: str, arg: str) -> N.PrintData:
        m = re.match(r"^PRINTDATA(K)?(D)?(L|W)?$", name)
        if not m:
            raise _Unsup(f"命令 {name}")
        if m.group(1):
            raise _Unsup("PRINTDATAK")
        # 引数（VAR_INT、省略可）
        var = None
        if arg.strip():
            v = self._expr_line(arg)
            if not isinstance(v, Var):
                raise ErbSyntaxError("PRINTDATA の引数")
            self._check_local_target(v)
            var = v
        items: list = []
        while self.k < len(self.lines):
            lno, text = self.lines[self.k]
            self.k += 1
            iname, iarg = self._instr_name(text)
            if iname == "ENDDATA":
                return N.PrintData(no, var, items, newline=m.group(3) in ("L", "W"), wait=m.group(3) == "W",
                                   dflag=bool(m.group(2)))
            if iname == "DATA":
                items.append([("raw", iarg, lno)])
            elif iname == "DATAFORM":
                f = form_to_expr(analyse_form(Stream(iarg), F_EOL), self.res)
                self._note_calls(f)
                items.append([("form", f, lno)])
            elif iname == "DATALIST":
                group: list = []
                while self.k < len(self.lines):
                    gno, gtext = self.lines[self.k]
                    self.k += 1
                    gname, garg = self._instr_name(gtext)
                    if gname == "ENDLIST":
                        break
                    if gname == "DATA":
                        group.append(("raw", garg, gno))
                    elif gname == "DATAFORM":
                        f = form_to_expr(analyse_form(Stream(garg), F_EOL), self.res)
                        self._note_calls(f)
                        group.append(("form", f, gno))
                    else:
                        raise _Unsup(f"DATALIST 内の {gname or gtext[:10]}")
                items.append(group)
            else:
                raise _Unsup(f"PRINTDATA 内の {iname or text[:10]}")
        raise _Unsup("ENDDATA がありません")

    # --- IF / SELECTCASE ---
    def _if(self, no: int, arg: str) -> N.If:
        branches = []
        cond = self._expr_line(arg)
        self._note_calls(cond)
        orelse = None
        while True:
            body, term = self._block({"ELSEIF", "ELSE", "ENDIF"})
            if term is None:
                raise _Unsup("ENDIF がありません")
            if cond is not None:
                branches.append((cond, body))
            else:
                orelse = body
            tname = term[1]
            if tname == "ENDIF":
                break
            if tname == "ELSEIF":
                if orelse is not None:
                    raise _Unsup("ELSE の後の ELSEIF")
                cond = self._expr_line(term[2])
                self._note_calls(cond)
            else:
                if orelse is not None:
                    raise _Unsup("ELSE が重複")
                cond = None
        return N.If(no, branches, orelse)

    def _select(self, no: int, arg: str) -> N.Select:
        e = self._expr_line(arg)
        self._note_calls(e)
        cases = []
        orelse = None
        # 最初の CASE までの行は無視されない（エラー）が、空であることを確認する
        body, term = self._block({"CASE", "CASEELSE", "ENDSELECT"})
        if body:
            raise _Unsup("SELECTCASE と最初の CASE の間に文")
        while term is not None and term[1] != "ENDSELECT":
            if term[1] == "CASE":
                conds = self._case_conds(term[2])
                body, nterm = self._block({"CASE", "CASEELSE", "ENDSELECT"})
                cases.append((conds, body))
            else:
                body, nterm = self._block({"CASE", "CASEELSE", "ENDSELECT"})
                if orelse is not None:
                    raise _Unsup("CASEELSE が重複")
                orelse = body
            term = nterm
        if term is None:
            raise _Unsup("ENDSELECT がありません")
        return N.Select(no, e, cases, orelse)

    def _case_conds(self, text: str) -> list:
        """`ReduceCaseExpressions`（ExpressionParser.cs:180–190、`reduceCaseExpression`:284–325）。"""
        p = Parser(analyse(Stream(text)), self.res)
        out = []
        while not p.eol:
            t = p.cur
            if t is not None and t.kind == "id" and str(t.value).upper() == "IS":
                p.i += 1
                op = p.cur
                if op is None or op.kind != "op":
                    raise ErbSyntaxError("ISキーワードの後に演算子がありません")
                p.i += 1
                a = p.reduce_term(T_COMMA)
                out.append(N.CaseCond("is", a, op=str(op.value)))
            else:
                a = p.reduce_term(T_COMMA, allow_to=True)
                if a is None:
                    raise ErbSyntaxError("CASEの引数は省略できません")
                t = p.cur
                if t is not None and t.kind == "id" and str(t.value).upper() == "TO":
                    p.i += 1
                    b = p.reduce_term(T_COMMA, allow_to=True)
                    out.append(N.CaseCond("to", a, b))
                else:
                    out.append(N.CaseCond("eq", a))
            self._note_calls(out[-1].a)
            if p.is_sym(","):
                p.i += 1
            elif not p.eol:
                raise ErbSyntaxError("CASE の書式")
        return out

    # --- CALL ---
    def _call(self, no: int, name: str, arg: str) -> N.CallStmt:
        """`SP_CALL_ArgumentBuilder`（ArgumentBuilder.cs:563–630）。"""
        form = "FORM" in name
        st = Stream(arg)
        if form:
            fw = analyse_form(st, F_CALLNAME, trim=True)
            fexpr = form_to_expr(fw, self.res)
            fname: object = fw.strs[0].upper() if not fw.subs else fexpr
            self._note_calls(fexpr)
        else:
            s = _read_call_name(st)
            fname = s.strip(" \t").upper()
        cur = st.cur
        toks = analyse(st)
        args: list = []
        if cur in ("(", ","):
            p = Parser(toks[1:], self.res)
            args = p.reduce_arguments(T_PAREN if cur == "(" else T_EOL)
            if not p.eol:
                raise ErbSyntaxError("CALL の書式が間違っています")
        elif cur == "[":
            raise _Unsup("CALL の [] 引数")
        for a in args:
            self._note_calls(a)
        try_ = name.startswith("TRY")
        catch = None
        success = None
        if name in ("TRYCCALL", "TRYCCALLFORM"):
            body, term = self._block({"CATCH"})
            if term is None:
                raise _Unsup("CATCH がありません")
            success = body or None
            catch, term = self._block({"ENDCATCH"})
            if term is None:
                raise _Unsup("ENDCATCH がありません")
        if isinstance(fname, str):
            self.fd.calls.add(fname)
        else:
            self.fd.dynamic_calls.append(no)
        return N.CallStmt(no, fname, args, try_=try_, catch=catch, success=success if catch is not None else None,
                          callf=name in ("CALLF", "CALLFORMF"))

    # --- 代入 ---
    def _check_local_target(self, v: Var) -> None:
        if getattr(self, "_hooking", False):
            return
        if v.name in self.res.private or v.name in ("RESULT", "RESULTS", "COUNT"):
            return
        uv = self.ctx.user_vars.get(v.name)
        if uv is not None and getattr(uv, "narration_owned", False):
            return
        raise _Unsup(f"非 LOCAL 変数 {v.name} への代入")

    def _assign(self, no: int, text: str) -> N.Assign:
        """LogicalLineParser.cs:386–480 ＋ SP_SET_ArgumentBuilder（ArgumentBuilder.cs:656–830）。"""
        st = Stream(text)
        if text[0] in "+-":
            raise _Unsup("前置インクリメント行")
        left = analyse(st, OPERATOR)
        p = Parser(left, self.res)
        target = p.reduce_term(T_EOL)
        if not isinstance(target, Var) or not p.eol:
            raise ErbSyntaxError("代入文の左辺")
        self._check_local_target(target)
        op = _read_assign_op(st)
        is_str = self.res.is_str_var(target.name)
        if op in ("++", "--"):
            skip_ws(st)
            if not st.eos:
                raise ErbSyntaxError("インクリメント行に余分な文字")
            return N.Assign(no, target, op, [])
        if not is_str:
            if op == "'=":
                raise ErbSyntaxError("整数型への '=")
            p2 = Parser(analyse(st), self.res)
            vals = p2.reduce_arguments(T_EOL)
            if not vals or vals[0] is None:
                raise ErbSyntaxError("代入文の右辺")
            if len(vals) > 1 and op != "=":
                raise ErbSyntaxError("複合代入の右辺に複数の値")
            for v in vals:
                self._note_calls(v)
            return N.Assign(no, target, op, vals)
        if op == "=":
            while st.cur == " ":
                st.p += 1
            f = form_to_expr(analyse_form(st, F_EOL, trim=True), self.res)
            self._note_calls(f)
            return N.Assign(no, target, "=", [f])
        if op in ("*=", "+=", "'="):
            p2 = Parser(analyse(st), self.res)
            vals = p2.reduce_arguments(T_EOL)
            if not vals or vals[0] is None:
                raise ErbSyntaxError("代入文の右辺")
            if len(vals) > 1 and op != "'=":
                raise ErbSyntaxError("代入文の右辺に余分な','")
            for v in vals:
                self._note_calls(v)
            return N.Assign(no, target, op, vals)
        raise ErbSyntaxError(f"文字列変数に使用できない代入演算子 {op}")


def _read_call_name(st: Stream) -> str:
    """`ReadString(st, LeftParenthesis_Bracket_Comma_Semicolon)`（LexicalAnalyzer.cs:442–495）。"""
    buf: list[str] = []
    while True:
        c = st.cur
        if c == "\0" or c in "([,;":
            break
        if c == "\\":
            st.p += 1
            e = st.cur
            if e == "\0":
                raise ErbSyntaxError("エスケープ文字\\の後に文字がありません")
            buf.append({"s": " ", "S": "\u3000", "t": "\t", "n": "\n"}.get(e, e))
            st.p += 1
            continue
        buf.append(c)
        st.p += 1
    return "".join(buf)


def _read_assign_op(st: Stream) -> str:
    """`ReadAssignmentOperator`（LexicalAnalyzer.cs:613–700）。`==` は代入扱い（LogicalLineParser.cs:470–476）。"""
    c = st.cur
    n = st.nxt
    two = c + n
    if two in ("++", "--", "+=", "-=", "*=", "/=", "%=", "|=", "&=", "^=", "'="):
        st.p += 2
        return two
    if two == "==":
        st.p += 2
        return "="
    if st.s.startswith("<<=", st.p) or st.s.startswith(">>=", st.p):
        op = st.s[st.p : st.p + 3]
        st.p += 3
        return op
    if c == "=":
        st.p += 1
        return "="
    raise ErbSyntaxError("解釈できない行です")


def parse_function(ctx: ExtractContext, rel: str, lines: list[tuple[int, str]]) -> N.FuncDef:
    return FuncParser(ctx, rel, lines).parse()
