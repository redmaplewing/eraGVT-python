"""S30：catalog の残りの不可執行原因（ループ内 $ラベルへの GOTO・STRDATA・SETCOLORBYNAME・FINDCHARA・GETCOLOR・
RANDCHOOSE 系・UNLOCK_ACHIEVEMENT・口上の CORRUPTTION_GET_* hook）。

expected は引擎（`reference/emuera-1824/Emuera/`）の命令の意味と ERB 原文から推導（行番号は各テストの docstring）。
開局は特装戦隊（[1] 紅葉、TARGET = 1）。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration import nodes as N
from eragvt.narration.extract import parse_function, read_logical_lines
from eragvt.narration.hooks import KOJO_CALL_HOOKS
from eragvt.narration.runtime import Env, ErbRuntimeError, Frame, Interp, NotSupported, _Return
from eragvt.narration.runtime_support import unsupported_reasons_static
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
    s.target = 1
    return Ctx(s, data, TextOutput(), svc)


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def _fd(svc, src: str, rel: str = "口上/t.ERB"):
    return parse_function(svc.catalog.ctx, rel, read_logical_lines(src.encode("utf-8")))


def _run(svc, ctx, src: str, rel: str = "口上/t.ERB"):
    fd = _fd(svc, src, rel)
    assert fd.unsupported == [], fd.unsupported
    assert unsupported_reasons_static(fd, svc.catalog) == []
    it = Interp(svc.catalog, svc._interp(ctx).env)
    try:
        it._exec_body(fd, Frame(fd, "F"))
    except _Return:
        pass
    return it


def _static(svc, src: str) -> list[str]:
    fd = _fd(svc, src)
    return [why for _, why in fd.unsupported] + [why for _, why in unsupported_reasons_static(fd, svc.catalog)]


# --- GOTO：ループの中の $ラベル（Instraction.Child.cs） -----------------------------------------------------------

GOTO_CASES = [
    # (1) KOJO_AEGI と同じ形：FOR の中の SELECTCASE の別の CASE へ。CASE は ENDSELECT へ飛ぶだけ（ELSEIF_Instruction:1805–1821、
    #     FunctionIdentifier.cs:235）なので L2 の後は ENDSELECT の次 → 「末」→ NEXT（REND_Instruction:2135–2161：カウンタ +1、
    #     まだ残っていれば FOR の次の行へ）。
    (
        "@F\nFOR LOCAL, 0, 3\n\tPRINTFORML 周{LOCAL}\n\tSELECTCASE LOCAL\n\t\tCASE 0\n\t\t\tPRINTL A\n\t\tCASE 1\n"
        "\t\t\tGOTO L2\n\t\tCASE 2\n\t\t\t$L2\n\t\t\tPRINTL B\n\tENDSELECT\n\tPRINTL 末\nNEXT\nPRINTFORML 後{LOCAL}\n",
        ["周0", "A", "末", "周1", "B", "末", "周2", "B", "末", "後3"],
    ),
    # (2) 内側の FOR から外側の FOR の本体のラベルへ：内側ループは捨てられ（線形ジャンプ）、外側は同じ周回を続ける。
    #     内側の FOR は再び FOR 行を通るので最初から（REPEAT_Instruction:1731–1744）。
    (
        "@F\nLOCAL:2 = 0\nFOR LOCAL, 0, 2\n\t$TOP\n\tPRINTFORML o{LOCAL}\n\tFOR LOCAL:1, 0, 3\n\t\tPRINTFORML i{LOCAL:1}\n"
        "\t\tIF LOCAL:1 == 1 && LOCAL:2 == 0\n\t\t\tLOCAL:2 = 1\n\t\t\tGOTO TOP\n\t\tENDIF\n\tNEXT\nNEXT\nPRINTFORML 後{LOCAL},{LOCAL:1}\n",
        ["o0", "i0", "i1", "o0", "i0", "i1", "i2", "o1", "i0", "i1", "i2", "後2,3"],
    ),
    # (3) 外から WHILE の本体へ：WEND は WHILE の条件を再評価するだけ（WEND_Instruction:2163–2176）→ 状態なしで正確。
    (
        "@F\nLOCAL = 0\nGOTO IN\nWHILE LOCAL < 3\n\tPRINTL w\n\t$IN\n\tPRINTFORML x{LOCAL}\n\tLOCAL += 1\nWEND\nPRINTL 後\n",
        ["x0", "w", "x1", "w", "x2", "後"],
    ),
    # (4) 外から DO の本体へ：LOOP は条件が真なら DO の次へ（LOOP_Instruction:2178–2192）。
    (
        "@F\nLOCAL = 10\nGOTO IN\nDO\n\tPRINTL never\n\t$IN\n\tPRINTFORML d{LOCAL}\n\tLOCAL += 1\nLOOP LOCAL < 12\nPRINTL 後\n",
        ["d10", "never", "d11", "後"],
    ),
    # (5) DO 内の CONTINUE は LOOP の条件で判定（CONTINUE_Instruction:2118–2129）。
    (
        "@F\nLOCAL = 0\nDO\n\tLOCAL += 1\n\tSIF LOCAL == 2\n\t\tCONTINUE\n\tPRINTFORML d{LOCAL}\nLOOP LOCAL < 4\nPRINTL 後\n",
        ["d1", "d3", "d4", "後"],
    ),
    # (6) BREAK は FOR／REPEAT のカウンタを 1 歩進めてから抜ける（BREAK_Instruction:2054–2077「eramakerではBREAK時にCOUNTが回る」）。
    (
        "@F\nFOR LOCAL, 0, 10\n\tSIF LOCAL == 3\n\t\tBREAK\nNEXT\nREPEAT 10\n\tSIF COUNT == 5\n\t\tBREAK\nREND\n"
        "FOR LOCAL:1, 0, 3\n\tCONTINUE\nNEXT\nPRINTFORML {LOCAL},{COUNT},{LOCAL:1}\n",
        ["4,6,3"],
    ),
    # (7) WHILE の BREAK はカウンタなし。ラベルの中で BREAK（GOTO で入った周回でも同じループの BREAK）。
    (
        "@F\nLOCAL = 0\nFOR LOCAL:1, 0, 5\n\tSIF LOCAL:1 == 1\n\t\tGOTO M\n\tPRINTFORML a{LOCAL:1}\n\tIF 0\n\t\t$M\n"
        "\t\tPRINTFORML m{LOCAL:1}\n\t\tSIF LOCAL:1 == 3\n\t\t\tBREAK\n\tENDIF\nNEXT\nPRINTFORML 後{LOCAL:1}\n",
        ["a0", "m1", "a2", "a3", "a4", "後5"],
    ),
]


@pytest.mark.parametrize("src,expected", GOTO_CASES)
def test_goto_into_loops(svc, ctx, src, expected):
    _run(svc, ctx, src)
    assert texts(ctx.out) == expected


def test_goto_into_inactive_for_is_unsupported(svc, ctx):
    """実行中でない FOR／REPEAT の中へ：NEXT／REND は FOR 行に前回記録された値で回る（REND_Instruction:2135–2161）。
    その値は持っていないので静的にも実行時にも unsupported（既存の test_goto_into_loop_is_unsupported と同じ形も含む）。"""
    srcs = [
        "@F\nFOR LOCAL, 0, 2\n\t$L\n\tPRINTL a\nNEXT\nGOTO L\n",
        "@F\nREPEAT 2\n\t$L\nREND\nGOTO L\n",
        # 実行中の FOR の中でも、ラベルが別の（実行中でない）内側 FOR の中
        "@F\nFOR LOCAL, 0, 2\n\tFOR LOCAL:1, 0, 2\n\t\t$L\n\tNEXT\n\tGOTO L\nNEXT\n",
    ]
    for src in srcs:
        assert any("実行中でない FOR／REPEAT" in w for w in _static(svc, src)), src
    fd = _fd(svc, srcs[0])
    it = Interp(svc.catalog, svc._interp(ctx).env)
    with pytest.raises(NotSupported):
        it._exec_body(fd, Frame(fd, "F"))
    assert any("関数内にない" in w for w in _static(svc, "@F\nGOTO NOWHERE\n"))


# --- KOJO_AEGI.ERB@渧泣（GOTO ＭＡＸ２／ＭＡＸ１） ----------------------------------------------------------------

AEGI = "口上/口上システム関係/KOJO_AEGI.ERB"
# 4033 の分岐（FLAG:111 が霊夢・魔理沙・早苗でない → ELSE の SELECTCASE RAND:3）の 3 文（:4044–4051、:4117–4124、:4186–4193）
MAX3_0 = ("殺意のこもる視線で、{p}を弄る触手をにらみつける{c}", "歯を食いしばり、触手に与えられる悦楽を堪える{c}",
          "体中に力を込めて、{p}から来る快楽をやり過ごす{c}")
MAX2_0 = ("{p}を嬲る触手の動きに声を漏らしながらも、{c}の戦意は衰えない", "触手が{p}を責める動きを早め、{c}は火照る体を静めきれない",
          "{p}に叩きつけられる快楽に、{c}は必死で抗っている")
MAX1 = ("触手に{p}を嬲られる快感に、{c}は怒りと悔しさを隠せない", "{c}の抵抗を無視して、触手は{p}を責め続けている",
        "強い快感を身悶えしながら我慢する{c}に、触手の責めは激しさを増していく")


@pytest.mark.parametrize(
    "rng,maxn,lines",
    [
        # RAND 順：:63 `SIF !RAND:2`（C、ふたなりでない：0 なら 秘豆）→ :101 ループＭＡＸ = RAND:3 + 1 → 各周の SELECTCASE RAND:3。
        # ループＭＡＸ = 3：周 0 は CASE 3/CASE 0、周 1 は GOTO ＭＡＸ２（:4055 → :4062）、周 2 は GOTO ＭＡＸ１（:4057 → :4131）。
        ([1, 2, 0, 1, 2], 3, [MAX3_0[0], MAX2_0[1], MAX1[2]]),
        # ループＭＡＸ = 2：周 0 は CASE 2/CASE 0（ラベル ＭＡＸ２ を素通り）、周 1 は GOTO ＭＡＸ１（:4128 → :4131）。
        ([0, 1, 2, 0], 2, [MAX2_0[2], MAX1[0]]),
        ([1, 0, 1], 1, [MAX1[1]]),
    ],
)
def test_aegi_goto_max_paths(svc, ctx, data, rng, maxn, lines):
    """`@渧泣("C")`：非気絶（TCVARn:12 bit 0 = 0）・ARGS ≠ M／MA・堕落／性抵抗の分岐に入らない（FLAG:110 = 0 だが
    ABL:触手中毒 = 0、FLAG:111 = 0 のキャラは霊夢等でない）→ 各周は :104「「」+ :3332 ELSE（TARGET が霊夢等でない → 何も出ない）
    + :3983「」」、続いて :3985 の地の文。RETURN 1（:4199）。"""
    st = ctx.state
    c = st.charas[1]
    assert c.tcvarn[12] & 1 == 0 and st.flag[110] == 0 and c.abl[data.index_of("ABL", "触手中毒")] == 0
    assert c.talent[data.index_of("TALENT", "ふたなり")] == 0
    assert st.charas[st.flag[111]].name not in ("霧雨 魔理沙", "東風谷 早苗", "博麗 霊夢")
    assert svc.catalog.unsupported_reason("渧泣") is None
    st.rng = FixedRng(rng)
    part = "秘豆" if rng[0] % 2 == 0 else "クリトリス"  # :61–64
    it = Interp(svc.catalog, svc._interp(ctx).env)
    assert it.call("渧泣", ["C"]) == 1
    expected = []
    for line in lines:
        expected += ["「」", line.format(p=part, c=c.callname)]
    assert texts(ctx.out) == expected
    assert st.result[0] == 1
    assert maxn == len(lines)


# --- STRDATA（Process.ScriptProc.cs:730–760） -------------------------------------------------------------------

STRDATA_SRC = (
    "@F\nSTRDATA LOCALS\n\tDATA あ\n\tDATAFORM {1+1}い\n\tDATALIST\n\t\tDATA う\n\t\tDATAFORM え{LOCAL}\n\tENDLIST\nENDDATA\n"
    "PRINTFORML [%LOCALS%]\n"
)


@pytest.mark.parametrize(
    "r,expected",
    [
        (0, ["[あ]"]),
        (4, ["[2い]"]),  # GetNextRand(3)：FixedRng は 値 % n
        (2, ["[う", "え0]"]),  # DATALIST は行を "\n" で連結した 1 つの文字列（:747–750）。PRINT で改行される
    ],
)
def test_strdata_choice(svc, ctx, r, expected):
    ctx.state.rng = FixedRng([r])
    _run(svc, ctx, STRDATA_SRC)
    assert texts(ctx.out) == expected
    assert ctx.state.rng.snapshot() == []  # RAND は 1 回だけ


def test_strdata_default_results_and_empty(svc, ctx):
    """引数省略 → RESULTS:0（ArgumentBuilder.cs@VAR_STR_ArgumentBuilder:1276–1283）。データが空なら何もしない（RAND も引かない：:732–736）。"""
    ctx.state.rng = FixedRng([1])
    ctx.state.results[0] = "前"
    _run(svc, ctx, "@F\nSTRDATA LOCALS:1\nENDDATA\nSTRDATA\n\tDATA x\n\tDATA y\nENDDATA\nPRINTFORML [%LOCALS:1%]\n")
    assert ctx.state.results[0] == "y"
    assert texts(ctx.out) == ["[]"]
    assert any("STRDATA 内の" in w for w in _static(svc, "@F\nSTRDATA LOCALS\n\tPRINTL a\nENDDATA\n"))


def test_strdata_functions_now_executable(svc):
    """`★真面目関数.ERB@AEGI`:149–235、`kojo_121／131_ホムラ.ERB@KOJO_1x1_BATTLE_CHARA_NANORI`（STRDATA の後に CALL する
    CORRUPTTION_GET_THEME／NANORI_FINAL は口上の名前 hook：Python 移植 `eragvt.game.corruption`）。"""
    cat = svc.catalog
    for name in ("AEGI", "KOJO_0_SEX_COM0_16", "KOJO_121_BATTLE_CHARA_NANORI", "KOJO_131_BATTLE_CHARA_NANORI"):
        assert cat.unsupported_reason(name) is None, name
    assert {"CORRUPTTION_GET_THEME", "CORRUPTTION_GET_NANORI_FINAL"} <= set(KOJO_CALL_HOOKS)
    fd = cat.get("KOJO_121_BATTLE_CHARA_NANORI")
    assert sorted(h.args[0].name for h in fd.hooks) == ["CORRUPTTION_GET_NANORI_FINAL", "CORRUPTTION_GET_THEME"]


def test_nanori_hooks_write_like_python(svc, ctx, data):
    """`kojo_121_ホムラ.ERB`:286–290：TALENT:完堕ち なら CALL CORRUPTTION_GET_THEME, TARGET → CALL CORRUPTTION_GET_NANORI_FINAL(TARGET)
    （hook → `game.corruption` の移植）。結果は Python 移植を同じ亂數で直接呼んだものと同じ（CSTR:60・CSTR:3・CFLAG:5）。"""
    from copy import deepcopy

    from eragvt.game.corruption import corruption_get_nanori_final, corruption_get_theme

    st = ctx.state
    st.charas[1].cstr[3] = "紅葉、参上！"
    st.charas[1].cstr[55] = "紅葉"
    twin = Ctx(deepcopy(st), data, TextOutput(), svc)
    _run(svc, ctx, "@F\nCALL CORRUPTTION_GET_THEME, TARGET\nCALL CORRUPTTION_GET_NANORI_FINAL(TARGET)\n")
    corruption_get_theme(twin, 1)
    corruption_get_nanori_final(twin, 1)
    for k in (60, 3):
        assert st.charas[1].cstr[k] == twin.state.charas[1].cstr[k] != ""
    assert st.charas[1].cflag[5] == 1 and st.result[0] == 0


# --- SETCOLORBYNAME・GETCOLOR・FINDCHARA ------------------------------------------------------------------------


def test_setcolorbyname(svc, ctx):
    """`Color.FromName`（ArgumentBuilder.cs:364–373、Process.ScriptProc.cs:408–420）→ SETCOLOR と同じ。HotPink = #FF69B4、Fuchsia = #FF00FF。"""
    _run(svc, ctx, "@F\nSETCOLORBYNAME HOTPINK\nPRINTL a\nSETCOLORBYNAME Fuchsia\nPRINTL b\n")
    segs = [line.parts[0].segments[0].color for line in ctx.out.lines]
    assert segs == ["#ff69b4", "#ff00ff"]
    assert any("SETCOLORBYNAME" in w for w in _static(svc, "@F\nSETCOLORBYNAME NoSuchColor\n"))
    cat = svc.catalog
    for name in ("MESSAGE_BATTLE_CHARA_TRANSRELEASE_ECS", "MESSAGE_OTHER_BATTLE_END_AKUOTI_NO_RESCUE"):
        assert cat.unsupported_reason(name) is None, name


def test_getcolor(svc, ctx):
    """`GetColorMethod`:553–568：現在の文字色。既定（RESETCOLOR 後）は Config.ForeColor（emuera.config:24 文字色:192,192,192）。
    命令として書くと RESULT:0（METHOD_Instruction:398–404）。"""
    _run(svc, ctx, "@F\nLOCAL = GETCOLOR()\nSETCOLOR 0x123456\nGETCOLOR\nLOCAL:1 = RESULT\nRESETCOLOR\n"
                   "PRINTFORML {LOCAL},{LOCAL:1},{GETCOLOR()}\n")
    assert texts(ctx.out) == [f"{0xC0C0C0},{0x123456},{0xC0C0C0}"]


def test_findchara(svc, ctx):
    """`FindcharaMethod`:222–292／`VariableEvaluator.FindChara`:1228–1293：[開始, 終端) で値が等しい最初（LAST は最後）のキャラ番号、
    無ければ -1。`CFLAG:100` はキャラ添字省略（要素 100）。開始 ≥ 終端 → -1。"""
    st = ctx.state
    for i, v in enumerate([0, 5, 7, 5]):
        st.charas[i].cflag[100] = v
    _run(svc, ctx, "@F\nPRINTFORML {FINDCHARA(CFLAG:100, 5)},{FINDCHARA(CFLAG:100, 5, 2)},{FINDLASTCHARA(CFLAG:100, 5)},"
                   "{FINDCHARA(CFLAG:100, 9)},{FINDCHARA(CFLAG:0:100, 7)},{FINDCHARA(CFLAG:100, 5, 1, 1)},"
                   "{FINDCHARA(NAME, \"花園 桃香\")},{FINDLASTCHARA(CFLAG:100, 5, 0, 3)}\n")
    assert texts(ctx.out) == ["1,3,3,-1,2,-1,2,1"]
    for bad in ("FINDCHARA(CFLAG:100, 5, 4)", "FINDCHARA(CFLAG:100, 5, 0, 5)", "FINDCHARA(CFLAG:100, 5, -1)"):
        fd = _fd(svc, f"@F\nLOCAL = {bad}\n")
        with pytest.raises(ErbRuntimeError):
            Interp(svc.catalog, svc._interp(ctx).env)._exec_body(fd, Frame(fd, "F"))


def test_choose_action_together(svc, ctx):
    """`汎用関数/CHOOSE_RAND_1.ERB@CHOOSE_ACTION_TOGETHER_F, ARG:0, ARG:1 = -1`:13–41：CFLAG:100 == ARG:0 のキャラ（ARG:1 を除く）を
    FINDCHARA で集め、RAND:(個数) で 1 人。いなければ -1。"""
    st = ctx.state
    for i, v in enumerate([0, 103, 7, 103]):
        st.charas[i].cflag[100] = v
    st.rng = FixedRng([1])
    it = Interp(svc.catalog, svc._interp(ctx).env)
    assert it.call("CHOOSE_ACTION_TOGETHER_F", [103, 1], as_method=True) == 3  # 候補 [3] → RAND:1
    st.rng = FixedRng([1])
    assert it.call("CHOOSE_ACTION_TOGETHER_F", [103, -1], as_method=True) == 3  # 候補 [1, 3] → RAND:2 = 1
    assert it.call("CHOOSE_ACTION_TOGETHER_F", [55, -1], as_method=True) == -1
    assert svc.catalog.unsupported_reason("KOJO_0_REST_27") is None


# --- RANDCHOOSE 系・UNLOCK_ACHIEVEMENT（narration.pyfuncs） ----------------------------------------------------


def test_randchoose_py_functions(svc, ctx):
    """`汎用関数/RANDCHOOSE.ERB`：CLEARRANDCHOOSE（:52–61 VARSET）→ ADDRANDCHOOSE 2 回（:3–21）→ CHOICECOUNT_F（:78–81）・
    RANDCHOOSE_F（:39–47：RAND:(個数) + 1 番目 - 1）。負の候補はエラー表示して RETURN（:5–9）。"""
    ctx.state.temp.randchoose[0] = 9
    ctx.state.rng = FixedRng([1])
    _run(svc, ctx, "@F\nCALL CLEARRANDCHOOSE\nCALL ADDRANDCHOOSE, 4\nCALL ADDRANDCHOOSE, 0\nCALL ADDRANDCHOOSE, -1\n"
                   "PRINTFORML {CHOICECOUNT_F()},{RANDCHOOSE_F()},{RESULT}\n")
    assert texts(ctx.out) == ["ERROR 候補に負の数を指定することはできません", "2,0,0"]
    rc = ctx.state.temp.randchoose
    assert (rc[0], rc[1], rc[2]) == (2, 5, 1)


def test_randchoose_rolled_back_on_failure(svc, ctx):
    """catalog の実行が途中で失敗したら RANDCHOOSE_NUM の書き込みもジャーナルで戻る（S29 の失敗回復）。"""
    st = ctx.state
    st.temp.randchoose[0] = 1
    st.temp.randchoose[1] = 8
    fd = _fd(svc, "@F\nCALL CLEARRANDCHOOSE\nCALL ADDRANDCHOOSE, 3\nLOCAL = 1 / 0\n", "地の文/t.ERB")
    ok, _ = svc._run(ctx, lambda it: it._exec_body(fd, Frame(fd, "F")), "t")
    assert not ok
    assert (st.temp.randchoose[0], st.temp.randchoose[1]) == (1, 8)


def test_unlock_achievement_does_nothing(svc, ctx):
    """`SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT`:6–20 は GLOBAL のみ（deviations「全域資料」）→ 何もしない、RESULT = 0。"""
    ctx.state.result[0] = 7
    _run(svc, ctx, "@F\nCALL UNLOCK_ACHIEVEMENT(276,\"絶体絶命ヒロイン\")\nPRINTFORML {RESULT}\n", "地の文/t.ERB")
    assert texts(ctx.out) == ["0"]
    assert svc.catalog.unsupported_reason("MESSAGE_BATTLE_CHARA_TRANSRELEASE") is None


def test_rescue_deadnum_catalog(svc, ctx, data):
    """`地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_RESCUE_DEADNUM`:1739–1810（`source_check._rescue_deadnum` から）：
    CFLAG:0 == 9 かつ 苗床化 のキャラを ADDRANDCHOOSE、RANDCHOOSE_F → FLAG:112、回収後の値（:1785–1809）。"""
    from eragvt.game.battle.source_check import _rescue_deadnum

    st = ctx.state
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    bi = lambda n: data.index_of("BASE", n)  # noqa: E731
    c = st.charas[3]
    c.cflag[0] = 9
    c.talent[ti("苗床化")] = 2
    c.talent[ti("貧乳")] = 1
    c.talent[ti("母乳体質")] = 0
    c.cflag[35] = 10
    _rescue_deadnum(ctx)
    assert st.flag[112] == 3
    assert (c.cflag[0], c.cflag[20], c.cflag[21], c.cflag[30], c.cflag[31], c.cflag[100], c.cflag[220]) == (-1, 0, 0, 0, 0, 103, 0)
    assert (c.base[bi("体力")], c.base[bi("気力")], c.base[bi("性耐性")]) == (1, 1, 1)
    assert [c.talent[ti(n)] for n in ("四肢欠損", "繁殖袋", "母乳体質", "苗床化", "貧乳", "巨乳", "淫乳", "淫核", "淫壷", "淫尻")] == [
        1, 1, 1, 2, 0, 5, 1, 1, 1, 1]
    assert c.cflag[35] == 310 and c.cflag[36] == 300
    assert any("【肉体回収】" in line for line in texts(ctx.out))


def test_rescue_deadnum_no_candidate(svc, ctx):
    """候補なし → CHOICECOUNT_F() == 0 で RETURN（:1747–1748）：何も出さない。"""
    from eragvt.game.battle.source_check import _rescue_deadnum

    _rescue_deadnum(ctx)
    assert texts(ctx.out) == []


# --- 覆蓋率回歸 -------------------------------------------------------------------------------------------------


def test_coverage_remaining(svc):
    """S30 後：13,384 中 13,383。残りは `地の文/スラング/T_SHAPE（触手の形状）.ERB@COLOR_T_SHAPE` の 1 函式だけで、原因は
    呼び出し先 `汎用関数/PRINT_RGBTEXT（色名、文字列）.ERB`:106 の GETBGCOLOR（背景色は TextOutput で模型化していない）。"""
    r = svc.catalog.report()
    assert r["total"] == 13384 and r["ok"] == 13383
    assert r["reasons"] == [("未実装の命令関数 GETBGCOLOR", 1)]
    assert svc.catalog.unsupported_reason("COLOR_T_SHAPE").startswith("PRINT_RGBTEXT:106 ")
    # GOTO の静的判定に引っかかる口上／地の文は無い
    for name in svc.catalog.narration_functions():
        fd = svc.catalog.get(name)
        assert not any("GOTO" in why for _, why in unsupported_reasons_static(fd, svc.catalog)), name
    assert isinstance(N.label_path([], "X"), type(None))
