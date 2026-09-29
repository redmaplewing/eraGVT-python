"""變數・命令名的符號表。

- 內建變數：`reference/emuera-1824/Emuera/GameData/Variable/VariableCode.cs`（種類・是否角色變數・文字列）。
- CSV 名稱索引：`GameData/ConstantData.cs@GetKeywordDictionary`:707–860（哪個變數查哪個 CSV）。
- ERH 的 `#DIM`／`#DIMS`：`GameProc/HeaderFileLoader.cs`、`GameProc/UserDefinedVariable.cs`
  （CONST 以外預設 STATIC、非 SAVEDATA 不存檔：:27、:150–152）。
- 命令名：`GameProc/Function/BuiltInFunctionCode.cs` 的 enum。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .lexer import ErbSyntaxError, Stream, analyse
from .expr import Lit, Parser, Resolver, T_COMMA, T_EOL

# --- 命令名（BuiltInFunctionCode.cs:9–359）-------------------------------------------
INSTRUCTIONS = frozenset(
    """SET PRINT PRINTL PRINTW PRINTV PRINTVL PRINTVW PRINTS PRINTSL PRINTSW PRINTFORM PRINTFORML PRINTFORMW
    PRINTFORMS PRINTFORMSL PRINTFORMSW PRINTC CLEARLINE REUSELASTLINE WAIT INPUT INPUTS TINPUT TINPUTS TWAIT
    WAITANYKEY FORCEWAIT ONEINPUT ONEINPUTS TONEINPUT TONEINPUTS AWAIT DRAWLINE BAR BARL TIMES PRINT_ABL
    PRINT_TALENT PRINT_MARK PRINT_EXP PRINT_PALAM PRINT_ITEM PRINT_SHOPITEM UPCHECK CUPCHECK ADDCHARA ADDSPCHARA
    ADDDEFCHARA ADDVOIDCHARA DELCHARA PUTFORM QUIT OUTPUTLOG BEGIN SAVEGAME LOADGAME SIF IF ELSE ELSEIF ENDIF
    REPEAT REND CONTINUE BREAK GOTO JUMP CALL CALLEVENT RETURN RETURNFORM RETURNF RESTART STRLEN STRLENFORM
    STRLENU STRLENFORMU PRINTLC PRINTFORMC PRINTFORMLC SWAPCHARA COPYCHARA ADDCOPYCHARA VARSIZE SPLIT
    PRINTSINGLE PRINTSINGLEV PRINTSINGLES PRINTSINGLEFORM PRINTSINGLEFORMS PRINTBUTTON PRINTBUTTONC
    PRINTBUTTONLC PRINTPLAIN PRINTPLAINFORM SAVEDATA LOADDATA DELDATA GETTIME TRYJUMP TRYCALL TRYGOTO JUMPFORM
    CALLFORM GOTOFORM TRYJUMPFORM TRYCALLFORM TRYGOTOFORM CALLTRAIN STOPCALLTRAIN CATCH ENDCATCH TRYCJUMP
    TRYCCALL TRYCGOTO TRYCJUMPFORM TRYCCALLFORM TRYCGOTOFORM TRYCALLLIST TRYJUMPLIST TRYGOTOLIST FUNC ENDFUNC
    CALLF CALLFORMF SETCOLOR SETCOLORBYNAME RESETCOLOR SETBGCOLOR SETBGCOLORBYNAME RESETBGCOLOR FONTBOLD
    FONTITALIC FONTREGULAR SORTCHARA FONTSTYLE ALIGNMENT CUSTOMDRAWLINE DRAWLINEFORM CLEARTEXTBOX SETFONT FOR
    NEXT WHILE WEND POWER SAVEGLOBAL LOADGLOBAL SWAP RESETDATA RESETGLOBAL RANDOMIZE DUMPRAND INITRAND REDRAW
    DOTRAIN SELECTCASE CASE CASEELSE ENDSELECT DO LOOP PRINTDATA PRINTDATAL PRINTDATAW DATA DATAFORM ENDDATA
    DATALIST ENDLIST STRDATA PRINTCPERLINE SETBIT CLEARBIT INVERTBIT DELALLCHARA PICKUPCHARA VARSET CVARSET
    RESET_STAIN SAVENOS FORCEKANA SKIPDISP NOSKIP ENDNOSKIP ARRAYSHIFT ARRAYREMOVE ARRAYSORT ARRAYCOPY
    ENCODETOUNI DEBUGPRINT DEBUGPRINTL DEBUGPRINTFORM DEBUGPRINTFORML DEBUGCLEAR ASSERT THROW SAVEVAR LOADVAR
    SAVECHARA LOADCHARA REF REFBYNAME PRINTK PRINTKL PRINTKW PRINTVK PRINTVKL PRINTVKW PRINTSK PRINTSKL
    PRINTSKW PRINTFORMK PRINTFORMKL PRINTFORMKW PRINTFORMSK PRINTFORMSKL PRINTFORMSKW PRINTCK PRINTLCK
    PRINTFORMCK PRINTFORMLCK PRINTSINGLEK PRINTSINGLEVK PRINTSINGLESK PRINTSINGLEFORMK PRINTSINGLEFORMSK
    PRINTDATAK PRINTDATAKL PRINTDATAKW PRINTD PRINTDL PRINTDW PRINTVD PRINTVDL PRINTVDW PRINTSD PRINTSDL
    PRINTSDW PRINTFORMD PRINTFORMDL PRINTFORMDW PRINTFORMSD PRINTFORMSDL PRINTFORMSDW PRINTCD PRINTLCD
    PRINTFORMCD PRINTFORMLCD PRINTSINGLED PRINTSINGLEVD PRINTSINGLESD PRINTSINGLEFORMD PRINTSINGLEFORMSD
    PRINTDATAD PRINTDATADL PRINTDATADW HTML_PRINT HTML_TAGSPLIT TOOLTIP_SETCOLOR TOOLTIP_SETDELAY
    TOOLTIP_SETDURATION PRINT_IMG PRINT_RECT PRINT_SPACE INPUTMOUSEKEY""".split()
)

# --- 內建變數（VariableCode.cs）--------------------------------------------------------
# 角色整數陣列（1 次元）
CHARA_INT_ARRAYS = frozenset(
    "BASE MAXBASE DOWNBASE ABL TALENT EXP MARK PALAM SOURCE EX NOWEX CFLAG JUEL GOTJUEL CUP CDOWN EQUIP TEQUIP "
    "STAIN RELATION TCVAR".split()
)
CHARA_INT_ARRAYS_2D = frozenset({"CDFLAG"})
CHARA_INT_SCALARS = frozenset({"NO", "ISASSI"})
CHARA_STR_SCALARS = frozenset({"NAME", "CALLNAME", "NICKNAME", "MASTERNAME"})
CHARA_STR_ARRAYS = frozenset({"CSTR"})
GLOBAL_INT_ARRAYS = frozenset(
    "DAY MONEY ITEM FLAG TFLAG UP PALAMLV EXPLV EJAC DOWN RESULT COUNT TARGET ASSI MASTER NOITEM LOSEBASE SELECTCOM "
    "ASSIPLAY PREVCOM TIME ITEMSALES PLAYER NEXTCOM PBAND BOUGHT A B C D E F G H I J K L M N O P Q R S T U V W X Y Z "
    "GLOBAL RANDDATA LOCAL ARG".split()
)
GLOBAL_STR_ARRAYS = frozenset("SAVESTR STR RESULTS TSTR GLOBALS LOCALS ARGS".split())
GLOBAL_PSEUDO = frozenset("RAND CHARANUM LINECOUNT ISTIMEOUT __INT_MAX__ __INT_MIN__ GAMEBASE_CODE".split())
NAME_ARRAYS = frozenset(
    "ABLNAME TALENTNAME EXPNAME MARKNAME PALAMNAME TRAINNAME BASENAME SOURCENAME EXNAME EQUIPNAME TEQUIPNAME "
    "FLAGNAME TFLAGNAME CFLAGNAME TCVARNAME CSTRNAME STAINNAME ITEMNAME STRNAME TSTRNAME SAVESTRNAME GLOBALNAME "
    "GLOBALSNAME CDFLAGNAME1 CDFLAGNAME2 ITEMPRICE".split()
)
BUILTIN_STR = GLOBAL_STR_ARRAYS | CHARA_STR_SCALARS | CHARA_STR_ARRAYS | (NAME_ARRAYS - {"ITEMPRICE"})
BUILTIN_VARS = (
    CHARA_INT_ARRAYS | CHARA_INT_ARRAYS_2D | CHARA_INT_SCALARS | CHARA_STR_SCALARS | CHARA_STR_ARRAYS
    | GLOBAL_INT_ARRAYS | GLOBAL_STR_ARRAYS | GLOBAL_PSEUDO | NAME_ARRAYS
)
CHARA_VARS = CHARA_INT_ARRAYS | CHARA_INT_ARRAYS_2D | CHARA_INT_SCALARS | CHARA_STR_SCALARS | CHARA_STR_ARRAYS

# 名稱索引 → GameData.names 的鍵（ConstantData.cs:707–860；本作沒有 flag.csv 等，那些變數不接受名稱）
CSV_NAME_TABLE = {
    "ABL": "ABL", "EXP": "EXP", "TALENT": "TALENT", "UP": "PALAM", "DOWN": "PALAM", "PALAM": "PALAM",
    "JUEL": "PALAM", "GOTJUEL": "PALAM", "CUP": "PALAM", "CDOWN": "PALAM", "MARK": "MARK", "ITEM": "ITEM",
    "ITEMSALES": "ITEM", "ITEMPRICE": "ITEM", "LOSEBASE": "BASE", "BASE": "BASE", "MAXBASE": "BASE",
    "DOWNBASE": "BASE", "EX": "EX", "NOWEX": "EX", "TRAINNAME": "TRAIN",
}


# --- ERH ------------------------------------------------------------------------------


@dataclass
class UserVar:
    name: str
    is_str: bool
    const: bool
    chara: bool = False
    save: bool = False
    glob: bool = False
    dims: tuple = ()
    values: list = field(default_factory=list)  # CONST の値（1 次元に並べたもの）
    source: str = ""  # 定義された ERH（ERB からの相対パス）
    line: int = 0


class _ConstResolver(Resolver):
    def __init__(self, table: dict[str, UserVar]) -> None:
        self.table = table

    def is_variable(self, name: str) -> bool:
        return name in self.table

    def is_function(self, name: str) -> bool:
        return name in ("STRLENS",)

    def is_csv_name(self, var: str, name: str) -> bool:
        return False


def _const_eval(e, table: dict[str, UserVar]):
    """CONST 初期値の評価（定数・四則・STRLENS のみ）。"""
    from .expr import Binary, Call, Unary, Var

    if isinstance(e, Lit):
        return e.value
    if isinstance(e, Var):
        uv = table[e.name]
        idx = _const_eval(e.args[0], table) if e.args else 0
        return uv.values[idx]
    if isinstance(e, Unary) and e.op == "-":
        return -_const_eval(e.x, table)
    if isinstance(e, Binary):
        a, b = _const_eval(e.left, table), _const_eval(e.right, table)
        return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                "|": lambda: a | b, "<<": lambda: a << b}[e.op]()
    if isinstance(e, Call) and e.name == "STRLENS":
        s = _const_eval(e.args[0], table)
        return len(s.encode("cp932", errors="replace"))
    raise ErbSyntaxError("CONST の初期値を評価できません")


def parse_dim(text: str, table: dict[str, UserVar], private: bool = False) -> UserVar:
    """`#DIM`／`#DIMS` 1 行（先頭の # 除く）→ UserVar（UserDefinedVariable.cs:40–200 の簡略版）。"""
    st = Stream(text)
    word = st.s.split(None, 1)[0].upper()
    is_str = word == "DIMS"
    st.p = len(st.s.split(None, 1)[0])
    toks = analyse(st, allow_assign=True)
    kw = {"CONST", "SAVEDATA", "CHARADATA", "GLOBAL", "DYNAMIC", "STATIC", "REF"}
    flags = set()
    i = 0
    while i < len(toks) and toks[i].kind == "id" and str(toks[i].value).upper() in kw:
        flags.add(str(toks[i].value).upper())
        i += 1
    if i >= len(toks) or toks[i].kind != "id":
        raise ErbSyntaxError("#DIM の変数名がありません")
    name = str(toks[i].value).upper()
    i += 1
    # サイズ（"," 区切り）と "=" 以降の初期値
    rest = toks[i:]
    eq = next((k for k, t in enumerate(rest) if t.kind == "op" and t.value == "="), None)
    size_toks = rest[: eq] if eq is not None else rest
    init_toks = rest[eq + 1 :] if eq is not None else []
    res = _ConstResolver(table)
    dims: list = []
    if size_toks:
        p = Parser(size_toks, res)
        if p.is_sym(","):
            p.i += 1
        for e in p.reduce_arguments(T_EOL):
            try:
                dims.append(_const_eval(e, table) if e is not None else None)
            except (ErbSyntaxError, KeyError, IndexError):
                dims.append(None)
    values: list = []
    if init_toks:
        p = Parser(init_toks, res)
        for e in p.reduce_arguments(T_EOL):
            try:
                values.append(_const_eval(e, table))
            except (ErbSyntaxError, KeyError, IndexError):
                values.append(None)
    return UserVar(
        name, is_str, "CONST" in flags, chara="CHARADATA" in flags, save="SAVEDATA" in flags,
        glob="GLOBAL" in flags, dims=tuple(dims), values=values,
    )


def load_erh(files: list[tuple[str, list[tuple[int, str]]]]) -> dict[str, UserVar]:
    """全 ERH の `#DIM` を読む（`{ … }` 連結済みの論理行を受け取る）。"""
    table: dict[str, UserVar] = {}
    pending: list[tuple[str, int, str]] = []
    for rel, lines in files:
        for no, text in lines:
            t = text.strip()
            if t.startswith("#DIM"):
                pending.append((rel, no, t[1:]))
    # CONST が後ろの定義を参照することがあるので、解決できるまで繰り返す
    for _ in range(5):
        left = []
        for rel, no, t in pending:
            try:
                uv = parse_dim(t, table)
            except (ErbSyntaxError, KeyError):
                left.append((rel, no, t))
                continue
            if uv.const and any(v is None for v in uv.values):
                left.append((rel, no, t))
                continue
            uv.source, uv.line = rel, no
            table.setdefault(uv.name, uv)
        if not left:
            break
        pending = left
    return table
