"""執行器支援範圍（靜態表）與抽取後的靜態檢查。

- 可讀的變數：狀態模型（`eragvt.state`）有對應欄位者。沒有對應欄位的變數（SOURCE、TEQUIP、PLAYER、GLOBAL…）
  其值在本程式中不會被維護，讀了等於猜 0，所以一律視為 unsupported。
- 已實作的式中関数：`IMPLEMENTED_METHODS`（語意照 `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs`）。
- `PY_FUNCTIONS`：以 Python 實作的 ERB 使用者函式（需要改變狀態、或本身即是派發規則的函式）。
"""

from __future__ import annotations

from . import nodes as N
from .expr import Call, Var, walk

# 角色變數 → Character 的欄位
CHARA_ATTR = {
    "BASE": "base", "MAXBASE": "maxbase", "ABL": "abl", "TALENT": "talent", "EXP": "exp", "MARK": "mark",
    "PALAM": "palam", "JUEL": "juel", "EX": "ex", "NOWEX": "nowex", "STAIN": "stain", "CFLAG": "cflag",
    "EQUIP": "equip", "RELATION": "relation", "TCVARN": "tcvarn",
}
CHARA_STR_ATTR = {"NAME": "name", "CALLNAME": "callname", "NICKNAME": "nickname", "MASTERNAME": "mastername"}
# 全域整數陣列 → GameState 的 IntArray 欄位
GLOBAL_ARRAY_ATTR = {"FLAG": "flag", "TFLAG": "tflag", "ITEM": "item", "DAY": "day"}
# 全域純量（索引 0 のみ）
GLOBAL_SCALAR = {"TIME", "MONEY", "TARGET", "ASSI", "MASTER", "SELECTCOM", "PREVCOM", "NEXTCOM"}
# 非存檔の #DIM（DIM.ERH ほか）→ TempVars の欄位
TEMP_ARRAY_ATTR = {
    "UP": "up", "LOSEBASE": "losebase", "TENTACLE_SIZE": "tentacle_size", "TENTACLE_NUM": "tentacle_num",
    "MAX_PALAM": "max_palam", "COMMON_PALAM": "common_palam", "RANDCHOOSE_NUM": "randchoose", "TCREPORT": "tcreport",
}
TEMP_SCALAR_ATTR = {"EX_COM": "ex_com", "SH_COM": "sh_com", "INSERT": "insert", "ターン上限": "turn_limit"}
CLOTH_INDEX = {"CLOTH_NO_INNER": 0, "CLOTH_OUTER_PER": 1, "CLOTH_OUTER_DEF": 2, "CLOTH_INNER_PER": 3, "CLOTH_INNER_DEF": 4}
STATE_SAVEDATA_ATTR = {"SHIELD": "shield", "MOB_FLAG": "mob_flag"}
NARR_STORE = {"RESULT", "RESULTS", "COUNT"}  # 口上実行中だけ使う一時変数（state.temp.narr に置く）
READ_ONLY_SPECIAL = {"RAND", "CHARANUM", "LINECOUNT", "NO", "STR", "SAVESTR", "CSTR", "特殊戦闘シチュエーション"}
NAME_TABLE_OF = {
    "ABLNAME": "ABL", "TALENTNAME": "TALENT", "EXPNAME": "EXP", "MARKNAME": "MARK", "PALAMNAME": "PALAM",
    "TRAINNAME": "TRAIN", "BASENAME": "BASE", "EXNAME": "EX", "ITEMNAME": "ITEM", "CDFLAGNAME1": "CDFLAG1",
    "CDFLAGNAME2": "CDFLAG2",
}

IMPLEMENTED_METHODS = {
    "GETBIT", "UNICODE", "STRFIND", "RAND", "MIN", "MAX", "ABS", "LIMIT", "GROUPMATCH", "POWER", "INRANGE",
    "STRLENS", "STRLENSU", "SUBSTRING", "SUBSTRINGU", "TOSTR", "SIGN",
}

# Python 實作的使用者函式：名稱 → 說明（實體在 service.py 註冊）
PY_FUNCTIONS = {
    "KOJO_ROOT": "口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT（派發規則、FLAG:62／FLAG:900）",
    # S14：汎用関数/WindowDrawer.ERB（＋TagSetText.ERB）→ `narration.windowlib`
    "WINDOW_CREATE": "汎用関数/WindowDrawer.ERB@WINDOW_CREATE",
    "WINDOW_SETTEXT": "汎用関数/WindowDrawer.ERB@WINDOW_SETTEXT",
    "WINDOW_DESTROY": "汎用関数/WindowDrawer.ERB@WINDOW_DESTROY",
    "WINDOW_DISPLAY": "汎用関数/WindowDrawer.ERB@WINDOW_DISPLAY",
    "WINDOW_DISPLAY_EX": "汎用関数/WindowDrawer.ERB@WINDOW_DISPLAY_EX（REF 配列引数：実行時 unsupported）",
}


def readable_var(name: str, catalog) -> bool:
    if name in CHARA_ATTR or name in CHARA_STR_ATTR or name == "CDFLAG":
        return True
    if name in GLOBAL_ARRAY_ATTR or name in GLOBAL_SCALAR or name in TEMP_ARRAY_ATTR or name in TEMP_SCALAR_ATTR:
        return True
    if name in CLOTH_INDEX or name in STATE_SAVEDATA_ATTR or name in NARR_STORE or name in READ_ONLY_SPECIAL:
        return True
    if name in NAME_TABLE_OF or name.endswith("NAME") and name[:-4] in (
        "FLAG", "TFLAG", "CFLAG", "TCVAR", "CSTR", "STAIN", "SOURCE", "EQUIP", "TEQUIP", "STR", "TSTR", "SAVESTR",
        "GLOBAL", "GLOBALS",
    ):
        return True
    uv = catalog.user_vars.get(name)
    if uv is not None and (uv.const or getattr(uv, "narration_owned", False)):
        return True
    return False


def unsupported_reasons_static(fd: N.FuncDef, catalog) -> list[tuple[int, str]]:
    """抽取後の静的検査：読めない変数・未実装の式中関数・未実装の命令関数。"""
    out: list[tuple[int, str]] = []

    def check_expr(line: int, e) -> None:
        def f(x) -> None:
            if isinstance(x, Var):
                if x.name in fd.private or x.name in ("LOCAL", "LOCALS", "ARG", "ARGS"):
                    return
                if not readable_var(x.name, catalog):
                    out.append((line, f"未対応の変数 {x.name}"))
            elif isinstance(x, Call):
                from .extract import BUILTIN_METHODS

                if x.name in BUILTIN_METHODS and x.name not in IMPLEMENTED_METHODS:
                    out.append((line, f"未実装の式中関数 {x.name}"))

        walk(e, f)

    def visit(stmts) -> None:
        for s in stmts or ():
            visit_stmt(s)

    def visit_stmt(s) -> None:
        if s is None:
            return
        ln = s.line
        if isinstance(s, N.Print):
            if not isinstance(s.arg, str):
                check_expr(ln, s.arg)
        elif isinstance(s, N.PrintData):
            check_expr(ln, s.var)
            for item in s.items:
                for kind, a, lno in item:
                    if kind != "raw":
                        check_expr(lno, a)
        elif isinstance(s, N.If):
            for c, b in s.branches:
                check_expr(ln, c)
                visit(b)
            visit(s.orelse)
        elif isinstance(s, N.Select):
            check_expr(ln, s.expr)
            for conds, b in s.cases:
                for cc in conds:
                    check_expr(ln, cc.a)
                    check_expr(ln, cc.b)
                visit(b)
            visit(s.orelse)
        elif isinstance(s, N.Sif):
            check_expr(ln, s.cond)
            visit_stmt(s.body)
        elif isinstance(s, N.Assign):
            check_expr(ln, s.target)
            for v in s.values:
                check_expr(ln, v)
        elif isinstance(s, N.BitOp):
            check_expr(ln, s.target)
            for v in s.bits:
                check_expr(ln, v)
        elif isinstance(s, N.ClearLine):
            check_expr(ln, s.count)
        elif isinstance(s, N.StrLen):
            if not isinstance(s.arg, str):
                check_expr(ln, s.arg)
        elif isinstance(s, N.VarSet):
            for a in (s.target, s.value, s.start, s.end):
                check_expr(ln, a)
        elif isinstance(s, N.Style):
            for a in s.args:
                if not isinstance(a, str):
                    check_expr(ln, a)
        elif isinstance(s, (N.Return,)):
            for v in s.values:
                check_expr(ln, v)
        elif isinstance(s, N.ReturnF):
            check_expr(ln, s.value)
        elif isinstance(s, N.CallStmt):
            if not isinstance(s.name, str):
                check_expr(ln, s.name)
            for a in s.args:
                check_expr(ln, a)
            visit(s.catch)
            visit(getattr(s, "success", None))
        elif isinstance(s, N.MethodStmt):
            if s.name not in IMPLEMENTED_METHODS and s.name not in METHOD_STMT_ONLY:
                out.append((ln, f"未実装の命令関数 {s.name}"))
            for a in s.args:
                check_expr(ln, a)
        elif isinstance(s, N.For):
            for a in (s.var, s.start, s.end, s.step):
                check_expr(ln, a)
            visit(s.body)
        elif isinstance(s, (N.While, N.Loop)):
            check_expr(ln, s.cond)
            visit(s.body)
        elif isinstance(s, N.Repeat):
            check_expr(ln, s.count)
            visit(s.body)

    visit(fd.body)
    for v, _ in fd.params:
        check_expr(fd.line, v)
    # GOTO：飛び先は関数本体トップレベルの $ラベルのみ対応（runtime.Interp.call）
    top = {s.name for s in fd.body if isinstance(s, N.Label)}
    for s in N.iter_stmts(fd.body):
        if isinstance(s, N.Goto) and s.name not in top:
            out.append((s.line, f"GOTO 先 ${s.name} がトップレベルにない"))
        elif isinstance(s, N.DrawLine) and s.form is not None:
            check_expr(s.line, s.form)
    return out


# 命令としてのみ使う（RESULT/RESULTS に結果）もの：現状なし
METHOD_STMT_ONLY: set[str] = set()
