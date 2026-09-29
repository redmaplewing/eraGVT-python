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
class Style(Stmt):
    """SETCOLOR（args）／RESETCOLOR／FONTBOLD／FONTITALIC／FONTREGULAR／ALIGNMENT／SETFONT。"""

    what: str
    args: list = field(default_factory=list)


@dataclass(slots=True)
class DrawLine(Stmt):
    pass


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
    body: list = field(default_factory=list)
    unsupported: list = field(default_factory=list)  # list[tuple[int, str]]
    calls: set = field(default_factory=set)  # 静的に決まる CALL 先・式中関数
    dynamic_calls: list = field(default_factory=list)  # CALLFORM の行
    hooks: list = field(default_factory=list)  # list[Hook]
