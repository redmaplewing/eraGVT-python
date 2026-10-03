"""catalog 的節點格式（文字輸出＋條件分岐的受限子集）。說明見 `docs/wiki/python/narration.md`。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .expr import Expr, Form, Var


@dataclass(slots=True)
class Stmt:
    line: int


@dataclass(slots=True)
class Print(Stmt):
    """PRINT 系。arg: raw=str／form=Form／expr=Expr。flags: L=改行 W=改行+待機 D=SETCOLOR 無視 K=かな変換
    PLAIN=PRINTPLAIN。"""

    kind: str
    arg: object
    newline: bool = False
    wait: bool = False
    dflag: bool = False
    plain: bool = False


@dataclass(slots=True)
class PrintData(Stmt):
    """PRINTDATA…ENDDATA。items[i] = 1 選択肢の行（DATA=str／DATAFORM=Form）のリスト。"""

    var: Optional[Var]
    items: list
    newline: bool = False
    wait: bool = False
    dflag: bool = False


@dataclass(slots=True)
class If(Stmt):
    branches: list  # list[tuple[Expr, list[Stmt]]]
    orelse: Optional[list] = None


@dataclass(slots=True)
class CaseCond:
    kind: str  # "eq" "to" "is"
    a: Expr
    b: Optional[Expr] = None
    op: str = ""


@dataclass(slots=True)
class Select(Stmt):
    expr: Expr
    cases: list  # list[tuple[list[CaseCond], list[Stmt]]]
    orelse: Optional[list] = None


@dataclass(slots=True)
class Sif(Stmt):
    cond: Expr
    body: Optional[Stmt]


@dataclass(slots=True)
class Assign(Stmt):
    target: Var
    op: str  # "=" "+=" … "++" "--" "'="
    values: list  # list[Expr]（配列一括代入のとき複数）


@dataclass(slots=True)
class BitOp(Stmt):
    """SETBIT／CLEARBIT／INVERTBIT 変数, ビット…"""

    mode: int  # 1=SET 0=CLEAR -1=INVERT
    target: Var
    bits: list


@dataclass(slots=True)
class StrLen(Stmt):
    """STRLEN／STRLENFORM／STRLENU／STRLENFORMU → RESULT（Instraction.Child.cs:504–528）。"""

    kind: str  # raw / form
    arg: object
    unicode: bool = False


@dataclass(slots=True)
class VarSet(Stmt):
    """VARSET 変数[, 値[, 開始[, 終了]]]（Instraction.Child.cs:1124–1166）。"""

    target: Var
    value: Optional[Expr]
    start: Optional[Expr] = None
    end: Optional[Expr] = None


@dataclass(slots=True)
class Times(Stmt):
    """TIMES 変数, 実数（S29：Instraction.Child.cs@TIMES_Instruction:893–916、引数 ArgumentBuilder.cs@SP_TIMES_ArgumentBuilder:249–283）。
    factor は実数リテラルの原文（decimal で計算するため文字列のまま持つ）。"""

    target: Var
    factor: str


@dataclass(slots=True)
class Split(Stmt):
    """SPLIT 文字列, 区切り, 文字列配列[, 個数変数]（S21：Process.ScriptProc.cs:522–538、引数 ArgumentBuilder.cs:1494–1514）。"""

    src: Expr
    sep: Expr
    target: Var
    num: Optional[Var] = None


@dataclass(slots=True)
class Style(Stmt):
    """SETCOLOR（args）／RESETCOLOR／FONTBOLD／FONTITALIC／FONTREGULAR／ALIGNMENT／SETFONT。"""

    what: str
    args: list = field(default_factory=list)


@dataclass(slots=True)
class DrawLine(Stmt):
    """DRAWLINE／DRAWLINEFORM（form = 線の文字列の FORM 式：GameProc/Process.ScriptProc.cs:154–172）。"""

    form: object = None


@dataclass(slots=True)
class Label(Stmt):
    """`$ラベル`（GOTO 先。名前は ToUpper：GameProc/LogicalLineParser.cs:305–320）。"""

    name: str


@dataclass(slots=True)
class Goto(Stmt):
    """GOTO ラベル（定数名のみ：Instraction.Child.cs@GOTO_Instruction:2366–2406）。"""

    name: str


@dataclass(slots=True)
class Input(Stmt):
    """INPUTS（kind "S"：Instraction.Child.cs@INPUTS_Instruction:642–667；入力文字列 → RESULTS:0）／
    INPUT（kind "I"：S28c2、入力整数 → RESULT:0：GameProc/Process.cs@InputInteger:249–252）。
    ジェネレータ呼び出し（`CatalogNarrationService.run_function_gen`／`run_event_gen`）でのみ実行できる。"""

    kind: str = "S"


@dataclass(slots=True)
class ClearLine(Stmt):
    """CLEARLINE n（論理行を n 行消す：GameView/EmueraConsole.Print.cs@deleteLine:156–178）。"""

    count: Expr


@dataclass(slots=True)
class Wait(Stmt):
    kind: str = "WAIT"


@dataclass(slots=True)
class Return(Stmt):
    values: list  # list[Expr]（RETURN）


@dataclass(slots=True)
class ReturnF(Stmt):
    value: Optional[Expr]


@dataclass(slots=True)
class CallStmt(Stmt):
    """CALL／TRYCALL／CALLFORM／TRYCALLFORM／TRYCCALL(FORM)＋CATCH。name は str（定数）か Form。"""

    name: object
    args: list
    try_: bool = False
    catch: Optional[list] = None  # TRYCCALL 系の CATCH ブロック（関数が無いとき実行）
    success: Optional[list] = None  # TRYCCALL 系：呼び出しから戻った後 CATCH までの文
    callf: bool = False  # CALLF（式中関数を命令として呼ぶ：戻り値は捨てる）


@dataclass(slots=True)
class MethodStmt(Stmt):
    """式中関数を命令として書いたもの（例 `STRFIND st,"x"`）：結果は RESULT／RESULTS へ
    （reference/…/GameProc/Function/Instraction.Child.cs:390–409 の METHOD 命令）。"""

    name: str
    args: list


@dataclass(slots=True)
class For(Stmt):
    var: Var
    start: Expr
    end: Expr
    step: Optional[Expr]
    body: list


@dataclass(slots=True)
class While(Stmt):
    cond: Expr
    body: list


@dataclass(slots=True)
class Repeat(Stmt):
    count: Expr
    body: list


@dataclass(slots=True)
class Loop(Stmt):
    """DO … LOOP 条件。"""

    cond: Expr
    body: list


@dataclass(slots=True)
class Break(Stmt):
    pass


@dataclass(slots=True)
class Continue(Stmt):
    pass


@dataclass(slots=True)
class Hook(Stmt):
    """狀態變化行：由 Python 已移植的處理代替（見 `narration.hooks`）。text = 原文。"""

    key: str
    text: str
    args: list = field(default_factory=list)


@dataclass(slots=True)
class Unsupported(Stmt):
    reason: str


@dataclass
class FuncDef:
    name: str
    file: str
    line: int
    end_line: int
    params: list = field(default_factory=list)  # list[tuple[Var, object default]]
    kind: str = "proc"  # proc / int(#FUNCTION) / str(#FUNCTIONS)
    private: dict = field(default_factory=dict)  # name -> is_str
    consts: dict = field(default_factory=dict)  # 関数内 #DIM CONST：name -> values
    sizes: dict = field(default_factory=dict)  # S21：1 次元文字列配列の要素数（関数内 #DIMS、#LOCALSSIZE）：SPLIT の切り捨て用
    body: list = field(default_factory=list)
    unsupported: list = field(default_factory=list)  # list[tuple[int, str]]
    calls: set = field(default_factory=set)  # 静的に決まる CALL 先・式中関数
    dynamic_calls: list = field(default_factory=list)  # CALLFORM の行
    hooks: list = field(default_factory=list)  # list[Hook]


def iter_stmts(stmts):
    """文リストを入れ子まで含めて前順に列挙する。"""
    for s in stmts or ():
        if s is None:
            continue
        yield s
        t = type(s)
        if t is If:
            for _, b in s.branches:
                yield from iter_stmts(b)
            yield from iter_stmts(s.orelse)
        elif t is Select:
            for _, b in s.cases:
                yield from iter_stmts(b)
            yield from iter_stmts(s.orelse)
        elif t is Sif:
            yield from iter_stmts([s.body])
        elif t is CallStmt:
            yield from iter_stmts(s.catch)
            yield from iter_stmts(s.success)
        elif t in (For, While, Repeat, Loop):
            yield from iter_stmts(s.body)


def label_path(body: list, name: str) -> Optional[list]:
    """`$name` までの経路 [(文リスト, その中の位置), …]（外側から。最後がラベル自身）。経路は IF／SELECTCASE の枝だけを通る
    （ループの中・見つからない → None）。S28c2：入れ子の中のラベルへの GOTO（runtime.Interp._exec_body）。"""

    def find(stmts: list) -> Optional[list]:
        for i, s in enumerate(stmts or ()):
            t = type(s)
            if t is Label and s.name == name:
                return [(stmts, i)]
            subs: list = []
            if t is If:
                subs = [b for _, b in s.branches] + [s.orelse]
            elif t is Select:
                subs = [b for _, b in s.cases] + [s.orelse]
            for b in subs:
                r = find(b)
                if r is not None:
                    return [(stmts, i)] + r
        return None

    return find(body)
