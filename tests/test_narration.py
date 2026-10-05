"""S07：口上／地の文 catalog（`eragvt.narration`）。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號は註解）、引擎の語意は
`reference/emuera-1824/Emuera/` の行號を附す。実装の出力から逆算しない。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, kojo_root
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration import nodes as N
from eragvt.narration.expr import Binary, Lit, Resolver, Ternary, Unary, Var, parse_expr
from eragvt.narration.extract import ExtractContext, parse_function, read_logical_lines
from eragvt.narration.hooks import HOOK_LINES
from eragvt.narration.runtime import Env, Frame, Interp
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data, svc):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.target = 1  # 赤羽 紅葉（勝気 12）
    s.savestr[13] = "BOSS"
    s.flag[110] = 0
    s.flag[11] = 1  # TENTACLE_BOSS_1_GETNAME → Ｃ触手（触手データ/ボス触手/TENTACLE_BOSS_1_Ｃ触手.ERB:7–8）
    return Ctx(s, data, TextOutput(), svc)


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


# --- 式の剖析（ExpressionParser.cs／OperatorCode.cs）------------------------------------------


class _R(Resolver):
    def is_variable(self, name):
        return name in ("A", "B", "C", "FLAG", "LOCAL", "BASE", "TALENT")

    def is_function(self, name):
        return name in ("MAX", "RAND")

    def is_csv_name(self, var, name):
        return var == "BASE" and name == "体力"


@pytest.mark.parametrize(
    "text,expected",
    [
        # 同優先順位は左結合、&& と || は同じ 0x40（OperatorCode.cs:33–34、ExpressionParser.cs:497–501）
        ("A && B || C", Binary("||", Binary("&&", Var("A", []), Var("B", [])), Var("C", []))),
        ("A || B && C", Binary("&&", Binary("||", Var("A", []), Var("B", [])), Var("C", []))),
        # * は + より強い（0x90 > 0x80）
        ("1 + 2 * 3", Binary("+", Lit(1), Binary("*", Lit(2), Lit(3)))),
        # & は == より弱い（0x50 < 0x60）
        ("A & 2 == 0", Binary("&", Var("A", []), Binary("==", Lit(2), Lit(0)))),
        # 単項 - は被演算子に即付く
        ("-A * 2", Binary("*", Unary("-", Var("A", [])), Lit(2))),
        ("!A && B", Binary("&&", Unary("!", Var("A", [])), Var("B", []))),
        # 三項は `?` 0x05 < `#` 0x10：a ? b # c ? d # e は左結合（ExpressionParser.cs:596–625）
        ("A ? 1 # 2", Ternary(Var("A", []), Lit(1), Lit(2))),
        # 変数の `:` 引数は 1 トークンだけ（:437）：FLAG:10 + 1 は (FLAG:10) + 1
        ("FLAG:10 + 1", Binary("+", Var("FLAG", [Lit(10)]), Lit(1))),
        ("FLAG:(A + 1)", Var("FLAG", [Binary("+", Var("A", []), Lit(1))])),
        # CSV 名は変数の引数位置でだけ文字列になる（:264–272）
        ("BASE:体力", Var("BASE", [Lit("体力")])),
    ],
)
def test_parse_expr(text, expected):
    assert parse_expr(text, _R()) == expected


def test_parse_expr_errors():
    from eragvt.narration.lexer import ErbSyntaxError

    for bad in ("A = 1", "未定義", "BASE:未定義", "1 ? 2", "FLAG:-1"):
        with pytest.raises(ErbSyntaxError):
            parse_expr(bad, _R())


# --- 抽取器（節點樹）------------------------------------------------------------------


def _fd(src: str, name: str = "F"):
    ctx = ExtractContext({}, {}, lambda n: False)
    lines = read_logical_lines(src.encode("utf-8"))
    return parse_function(ctx, "t.ERB", lines)


def test_extract_if_select_printdata():
    fd = _fd(
        "@F\n"
        "IF LOCAL == 1\n\tPRINTL a\nELSEIF LOCAL\n\tPRINT b\nELSE\n\tPRINTFORML %CALLNAME%{LOCAL,3,LEFT}\nENDIF\n"
        "SELECTCASE RAND:3\n\tCASE 0, 2 TO 4\n\t\tPRINTW x\n\tCASE IS > 5\n\tCASEELSE\n\t\tPRINTDL y\nENDSELECT\n"
        "PRINTDATAL\n\tDATA d1\n\tDATALIST\n\t\tDATAFORM e%CALLNAME%\n\t\tDATA e2\n\tENDLIST\nENDDATA\n"
    )
    assert fd.unsupported == []
    if_, sel, pd = fd.body
    assert isinstance(if_, N.If) and len(if_.branches) == 2 and if_.orelse is not None
    p = if_.orelse[0]
    assert isinstance(p, N.Print) and p.kind == "form" and p.newline
    assert p.arg.strs == ["", "", ""] and p.arg.parts[1].kind == "{" and p.arg.parts[1].left
    assert isinstance(sel, N.Select) and [c.kind for c in sel.cases[0][0]] == ["eq", "to"]
    assert sel.cases[1][0][0].kind == "is" and sel.cases[1][0][0].op == ">"
    assert sel.orelse[0].dflag and sel.orelse[0].newline
    assert isinstance(pd, N.PrintData) and pd.newline and len(pd.items) == 2 and len(pd.items[1]) == 2


def test_extract_form_yen_at_and_raw_print():
    fd = _fd("@F\nPRINTFORML x\\@ LOCAL ? 甲 # 乙 \\@y\nPRINTL  そのまま ;注釈ではない\n")
    f = fd.body[0].arg
    assert f.strs == ["x", "y"] and f.parts[0].kind == "@"
    assert f.parts[0].yes.strs == ["甲"] and f.parts[0].no.strs == ["乙"]  # 左右は trim（LexicalAnalyzer.cs:1216–1220）
    # PRINT の引数は命令直後の 1 文字を飛ばした残り全部（LogicalLineParser.cs:436、ArgumentBuilder.cs:348–359）
    assert fd.body[1].arg == " そのまま ;注釈ではない"


@pytest.mark.parametrize(
    "src,reason",
    [
        ("@F\nFLAG:900 = 1\n", "非 LOCAL 変数 FLAG への代入"),
        ("@F\nTRYGOTO L\n$L\n", "命令 TRYGOTO"),  # S14：GOTO（定数ラベル）のみ対応
        ("@F\nINPUT 0\n", "INPUT（既定値つき）"),
        ("@F\nINPUTS 既定\n", "INPUTS（既定値つき）"),
        ("@F\nIF 1\nPRINTL a\n", "ENDIF がありません"),
    ],
)
def test_extract_unsupported(src, reason):
    fd = _fd(src)
    assert fd.unsupported and reason in fd.unsupported[0][1]


def test_extract_local_assign_supported():
    fd = _fd("@F\n#DIMS S\nLOCAL = 1\nLOCALS = abc %CALLNAME%\nS '= \"x\" + \"y\"\nSETBIT LOCAL, 3\n")
    assert fd.unsupported == []
    assert [type(s).__name__ for s in fd.body] == ["Assign", "Assign", "Assign", "BitOp"]


# --- 執行器：真實函式 ---------------------------------------------------------------------


def test_kojo_hitokuti_shop_13(ctx, data):
    """`口上/女性汎用口上/KOJO_0_13_元気っ子.ERB@KOJO_0_HITOKUTI_SHOP_13`:20–100 ＋ KOJO_ROOT.ERB:46–90。"""
    st = ctx.state
    c = st.target_chara
    c.talent[12] = 0
    c.talent[13] = 1  # SEIKAKU_CHECK_F = 13（CHARA_SEIKAKU.ERB:41–56）
    st.flag[900] = 7
    # :22 体力 > 500 → :32 TALENT:触手の虜 == 0 なので && 短絡で RAND:3 は引かない（OperatorMethod.cs:532–536）
    # :42 MARK:快楽刻印(0) > RAND:5 → 偽、:59 (0+0)/2 > RAND:4 → 偽、:81 SELECTCASE RAND:8 → CASE 3（:91–93）
    st.rng = FixedRng([0, 0, 3])
    # RETURN LINECOUNT - BEFORE_LINECOUNT（KOJO_ROOT.ERB:46、:93）：:92–93 の 2 行＋:108 PRINTFORML（空行）
    assert kojo_root(ctx, "HITOKUTI_SHOP") == 3
    assert texts(ctx.out) == ["「今日は何しようかな？」", " 紅葉は居ても立っても居られないといった様子だ。", ""]
    # KOJO_0_COLOR_13（:15–16）SETCOLOR 220,200,180 → 本文の色、最後に RESETCOLOR（KOJO_ROOT.ERB:87）
    assert ctx.out.lines[0].parts[0].segments[0].color == "#dcc8b4"
    assert ctx.out._color is None
    assert (st.flag[62], st.flag[900]) == (0, 0)


def test_message_sex_com9(ctx):
    """`地の文/MESSAGE_SEX_COM.ERB@MESSAGE_SEX_COM9`:2771–2824（hook：:2794 FLAG:900、:2823 SETBIT TFLAG:21,7）。"""
    st = ctx.state
    c = st.target_chara
    c.cflag[6] = 99  # KOJO_99_* は無い → KOJO_ROOT は -1（:54–58）で本文に影響しない
    c.cflag[3] = 0
    st.flag[71] = 1  # :2821 撮影中
    st.rng = FixedRng([0])  # :2791 RAND:2 == 0（PRINT_SWOON は気絶でなければ RAND を引かない：MESSAGE.ERB:194–）
    assert ctx.narration.run_function(ctx, "MESSAGE_SEX_COM9", []) is True
    assert texts(ctx.out) == [
        "針刺し",  # :2772–2774（太字）
        # :2777 TENTACLE_ACCESS "NAME"（COMMON_TENTACLE_DATA.ERB:204–206）→ Ｃ触手、:2784、:2787、:2792、:2804
        "Ｃ触手は先端を尖らせた細い触手で紅葉の敏感な部分を刺した。",
        "あまりの痛みに紅葉は泣き叫ぶが、",  # :2813
        "手足はがっちりと拘束されており逃れることはできない・・・",  # :2814
        "",  # :2819
    ]
    assert ctx.out.lines[0].parts[0].segments[0].bold is True
    # :2794 FLAG:900 = 1 の後 :2818 KOJO_ROOT が FLAG:900 = 0（KOJO_ROOT.ERB:57）、FLAG:62 = 0（:76）
    assert (st.flag[900], st.flag[62]) == (0, 0)
    assert st.tflag.get_bit(21, 7)  # :2823


def test_message_battle_end_loss(ctx):
    """`地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_LOSS`:1815–1861（丸飲み後 TFLAG:23 == -1 の分岐、RAND なし）。"""
    st = ctx.state
    st.target_chara.cflag[6] = 99
    st.target_chara.cflag[3] = 0
    st.tflag[23] = -1
    st.rng = FixedRng([])
    assert ctx.narration.run_function(ctx, "MESSAGE_BATTLE_END_LOSS", []) is True
    assert texts(ctx.out) == [
        "精液溜まりに顔まで浸かった魔法少女の姿に満足したのか、",  # :1823–1827（女性）
        "Ｃ触手は腔内の膨れ上がった触手を一斉に揺らし、獲物の頭付近を目掛けて殺到させた。",  # :1828–1829
        "トドメとばかり濃い精液を吐き出し続けるＣ触手の触手群が、少女を絶望の白濁へと沈めてゆく。",  # :1830–1837
        "ごぼりと気泡が浮き上がったのを最後に紅葉の反応が消えると、",  # :1838
        "周囲に甚大な被害を出した丸飲み触手はその巨体に見合わぬ素早さで何処かへと去ってゆき…",  # :1839
        "",
        "",
        "その日、街から「赤羽 紅葉」の姿は忽然と消え去ったのだった・・・",  # :1842
        "",  # :1857
    ]
    assert ctx.out.lines[-1].wait  # :1861 FORCEWAIT


# --- KOJO_ROOT -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "setup,code,force,result,flag62",
    [
        (lambda c: c.tcvarn.__setitem__(12, 1), "HITOKUTI_SHOP", 0, 0, 5),  # :17–21 気絶 → 0、FLAG:62 は触らない
        (lambda c: c.base.__setitem__(30, 1), "SEX_COM10", 0, 0, 5),  # :23–27 Ｃ結界（STRFIND 部分一致）
        (lambda c: c.cflag.__setitem__(6, 99), "HITOKUTI_SHOP", 0, -1, 0),  # :80–86 見つからない → -1
        (lambda c: None, "NO_SUCH_CODE", 0, -1, 0),  # 汎用口上 :52–58
        (lambda c: None, "OTHER_NO_SUCH", 0, -1, 1),  # :60–68 OTHER_ → FLAG:62 = 1
    ],
)
def test_kojo_root_paths(ctx, setup, code, force, result, flag62):
    st = ctx.state
    st.flag[62] = 5
    st.flag[900] = 9
    setup(st.target_chara)
    assert kojo_root(ctx, code, force) == result
    assert (st.flag[62], st.flag[900]) == (flag62, 0)
    assert texts(ctx.out) == []


def test_kojo_generic_dispatch_uses_seikaku(ctx):
    """汎用口上：`KOJO_0_HITOKUTI_SHOP_{SEIKAKU_CHECK_F(TARGET)}`（KOJO_ROOT.ERB:52–53）。紅葉 = 勝気 12。
    KOJO_0_12_勝気.ERB@KOJO_0_HITOKUTI_SHOP_12 は 体力 > 強制休憩体力 なら :23–24 の 2 行（RAND なし）。"""
    st = ctx.state
    st.rng = FixedRng([])
    assert kojo_root(ctx, "HITOKUTI_SHOP") == 2
    assert texts(ctx.out) == ["「さて、何をしようかしら？」", ""]


def test_runtime_rollback_on_unsupported(ctx, svc):
    """実行時に不可執行と判明したら出力・亂數を戻して False（DEVIATION：引擎なら停止）。"""
    st = ctx.state
    st.rng = FixedRng([1, 2, 3])
    ctx.out.print("前")
    it = Interp(svc.catalog, Env(st, ctx.data, ctx.out, {}, {}, ctx))
    fd = _fd("@F\nPRINTFORML x{RAND:5}\nPRINTFORML {1/0}\n")
    ok, _ = svc._run(ctx, lambda it: it.exec_block(fd.body, Frame(fd, "F")), "F")
    assert ok is False
    assert st.rng.snapshot() == [1, 2, 3]
    assert texts(ctx.out) == [] and ctx.out._pending[0].text == "前"
    del it


def test_division_evaluates_right_first(ctx, svc):
    """`/`・`%` は右辺→左辺（OperatorMethod.cs:306–311、323–328）、C# の切り捨て除算。"""
    st = ctx.state
    st.rng = FixedRng([7, 2])
    fd = _fd("@F\nLOCAL = RAND:10 / RAND:10\nLOCAL:1 = -7 / 2\nLOCAL:2 = -7 % 2\n")
    it = Interp(svc.catalog, Env(st, ctx.data, ctx.out, {}, {}, ctx))
    it.exec_block(fd.body, Frame(fd, "F"))
    # 右の RAND:10 が先に 7、左が 2 → 2 / 7 = 0（左→右なら 7 / 2 = 3）
    assert st.temp.locals.get(("F", 0), 0) == 0
    assert st.temp.locals[("F", 1)] == -3 and st.temp.locals[("F", 2)] == -1


# --- hook 表と sexmsg の対照 ------------------------------------------------------------------------


def test_hook_table_matches_sexmsg(svc):
    """hooks.HOOK_LINES：(1) 原文が ERB と一致、(2) 引用が sexmsg の対応関数に書かれている、
    (3) 対象関数中の「非 LOCAL 代入／状態 CALL」はすべて表にある（黙って捨てない）。"""
    cat = svc.catalog
    src = Path(__file__).parents[1].joinpath("src/eragvt/game/battle/sexmsg.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.split("\n")
    bodies = {n.name: "\n".join(lines[n.lineno - 1 : n.end_lineno]) for n in tree.body if isinstance(n, ast.FunctionDef)}
    funcs = set()
    for (func, line), (text, py, cover) in HOOK_LINES.items():
        funcs.add(func)
        e = cat.index[func]
        erb = dict(cat.lines_of(e.rel))
        assert erb[line].strip() == text, (func, line)
        assert cover in bodies[py], (func, line, py, cover)
    state_calls = {"SET_TENTACLE_SIZE_BY_MESSAGE", "TENTACLE_SYASEI_UP", "NINSIN_HANTEI", "LOSTVIRGIN"}
    for func in funcs:
        e = cat.index[func]
        for no, t in cat.lines_of(e.rel)[e.start + 1 : e.end]:
            s = t.strip()
            m = re.match(r"^(CALL\s+(\w+)|SETBIT\s+(\w+)|([^\s=:]+)(:[^=]*)?\s*([-+*/|&]?=)(?!=))", s)
            if not m:
                continue
            if m.group(2) and m.group(2) not in state_calls:
                continue
            target = (m.group(3) or m.group(4) or "").upper()
            if not m.group(2) and target in ("LOCAL", "LOCALS", "RESULTS", "LCOUNT"):
                continue
            if s.startswith(("PRINT", "IF", "ELSEIF", "SIF", "CASE", "SELECTCASE", "DATA")):
                continue
            assert (func, no) in HOOK_LINES or func == "MESSAGE_SEX_SPCOM7" and no in (1235, 1240), (func, no, s)


# --- 覆蓋率・Web --------------------------------------------------------------------------------------


def test_coverage_report(svc):
    r = svc.catalog.report()
    assert r["total"] > 13000 and r["ok"] / r["total"] > 0.9
    assert all(n > 0 for _, n in r["reasons"])


def test_web_shop_shows_hitokuti(data, tmp_path):
    """新遊戲 → SHOP：一口メッセージ（KOJO_0_HITOKUTI_SHOP_12、紅葉は勝気）の本文が出る（SHOP.ERB:112–117）。"""
    from datetime import datetime

    from fastapi.testclient import TestClient

    from eragvt.web import create_app

    app = create_app(data, tmp_path, rng_factory=lambda: GameRng(7), now=lambda: datetime(2026, 9, 29))
    client = TestClient(app)
    client.post("/api/input", json={"value": 0})
    client.post("/api/input", json={"value": 1})  # 初期セット『特装戦隊』
    client.post("/api/input", json={"value": 1000})  # CHARA_MAKE_MAIN 完成
    client.post("/api/input", json={"value": 1})  # HEROINE_PRESET [1] 基本セット
    lines = [ln["parts"] for ln in client.get("/api/screen").json()["lines"]]
    text = ["".join(s["text"] for p in parts for s in p["segments"]) for parts in lines]
    # KOJO_0_12_勝気.ERB の HITOKUTI_SHOP_12 の本文のどれか 1 行（ERB から候補を取る）
    e = app.state.session.narration.catalog.index["KOJO_0_HITOKUTI_SHOP_12"]
    cand = {
        t.split(None, 1)[1] for _, t in app.state.session.narration.catalog.lines_of(e.rel)[e.start : e.end]
        if t.startswith("PRINTL ") and len(t.split(None, 1)) > 1
    }
    assert any(t in cand for t in text)
