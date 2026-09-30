"""S11：拡張度（`ゲーム内_戦闘処理/GAPING.ERB` の CFLAG:34 ≠ 0 分岐）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/`、行號は註解）。引擎語意は
`reference/emuera-1824/Emuera/` の行號。身長 1581 のとき GAPING_SIZE_01〜08 = 7, 15, 25, 40, 55, 75, 115, 160（:431–500）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.battle import gaping
from eragvt.game.battle.sexmsg import msg_spcom7
from eragvt.game.opening import event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

TALENTS = ("未熟", "Ｖ敏感", "Ｖ鈍感", "淫壷", "Ａ敏感", "Ａ鈍感", "淫尻", "処女", "変身能力")


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    """預設開局（汎用キャラ、CFLAG:34 = 1）の TARGET=1 を、年齢 16・身長 1581・関連素質／経験 0 にそろえる。"""
    s = GameState.new(data, rng=GameRng(3))
    event_first(s, data)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.target = 1
    c = s.charas[1]
    c.base[data.index_of("BASE", "年齢")] = 16
    c.base[data.index_of("BASE", "身長")] = 1581
    c.base[data.index_of("BASE", "腰囲")] = 816
    c.cflag[1] = 0
    for n in TALENTS:
        c.talent[data.index_of("TALENT", n)] = 0
    for n in ("Ｖ拡張経験", "Ａ拡張経験", "出産経験"):
        c.exp[data.index_of("EXP", n)] = 0
    assert c.cflag[34] == 1  # CHARA_MAKE_DEFAULT.ERB:980
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


# --- GAPING_RANK_STR（:150–279）---------------------------------------------------------------


@pytest.mark.parametrize(
    "arg, kind, expected",
    [
        (-2, "NAME", " ― "),
        (-1, "NAME", "処女"),
        (0, "NAME", " Ｅ "),
        (1, "NAME", " Ｅ+"),
        (11, "NAME", " Ｓ+"),
        (16, "NAME", " 狂 "),
        (17, "NAME", " 最狂 "),  # :200–201 ELSE
        (-3, "NAME", " 最狂 "),
        (-2, "TEXT", ""),  # :240–241
        (-1, "TEXT", "未だ純潔を保っている"),  # :242–243
        (0, "TEXT", "繊毛と同程度のモノを受け入れられる"),  # :204–205、:239
        (17, "TEXT", "船の船首ほどの大きさのモノを受け入れられる"),  # :237–238
        (1, "T_TEXT", "繊毛よりは太い程度"),
        (4, "T_TEXT", "一般的な男性器と同程度"),
    ],
)
def test_gaping_rank_str(ctx, arg, kind, expected):
    assert gaping.gaping_rank_str(ctx, arg, kind) == expected


def test_gaping_rank_str_t_text_callname_and_other_args(ctx):
    name = ctx.state.charas[1].callname
    assert gaping.gaping_rank_str(ctx, 2, "T_TEXT") == f"{name}の指と同程度"  # :248–249 PRINT_CALLNAME(TARGET)
    assert gaping.gaping_rank_str(ctx, 99, "T_TEXT") == f"{name}を粉砕しそうなほど太い"  # :276–277
    # SELECTCASE に当たらない ARGS → 静的 LOCALS の前回値（VariableToken.cs:1712–1737）
    assert gaping.gaping_rank_str(ctx, 0, "XXX") == f"{name}を粉砕しそうなほど太い"


@pytest.mark.parametrize("rank, point", [(-1, -5), (0, 0), (8, 155), (11, 335), (17, 1205), (18, 0)])
def test_gaping_rank_to_point(rank, point):
    """`@GAPING_RANK_TO_POINT`:286–332（VARSET LOCAL の後、該当なしは 0）。"""
    assert gaping.gaping_rank_to_point(rank) == point


@pytest.mark.parametrize("arg, rank", [(4, 0), (5, 1), (14, 1), (15, 2), (154, 7), (155, 8), (1204, 16), (1205, 17)])
def test_gaping_rank(arg, rank):
    """`@GAPING_RANK`:81–140（境界は各ランクの下限）。"""
    assert gaping.gaping_rank(arg) == rank


def test_gaping_size_by_hand(ctx):
    """`@GAPING_SIZE`:342–427（身長 1581）：
    21 → D_RANK 2、M0 = (15+25)/2 = 20 < 21 → M1 = (25+40)/2 = 32、(25−15)×1/12 + 15 = 15。
    31 → M0 = 32 ≥ 31 → M1 = 32、M0 = 20、D_RANK 2 → 10×11/12 + 15 = 24。32 → 10×12/12 + 15 = 25。"""
    assert [gaping.gaping_size(ctx, a) for a in (21, 31, 32)] == [15, 24, 25]


# --- GET_V_GAPING_EXP／GET_A_GAPING_EXP（:1004–1059）-----------------------------------------------


def test_get_v_gaping_exp_static_local(ctx, data):
    st = ctx.state
    c = st.charas[1]
    vexp = data.index_of("EXP", "Ｖ拡張経験")
    assert gaping.get_v_gaping_exp(ctx, 6) == 2  # :1018–1019
    assert c.exp[vexp] == 2 and texts(ctx.out)[-1] == "Ｖ拡張経験 + 2"  # :1023–1026
    # ARG < 3 は LOCAL を代入しない → 静的 LOCAL の前回値 2 のまま加算（原作どおり）
    assert gaping.get_v_gaping_exp(ctx, 0) == 2
    assert c.exp[vexp] == 4
    assert gaping.get_v_gaping_exp(ctx, 3) == 1  # :1020–1021
    # OPTION == 1（PRISON_GAPING:1321）→ 加算しないが値は返す
    assert gaping.get_v_gaping_exp(ctx, 6, st.target, 1) == 2
    assert c.exp[vexp] == 5
    c.cflag[0] = 1  # 幽閉中 → 加算しない（:1023）
    assert gaping.get_v_gaping_exp(ctx, 6) == 2 and c.exp[vexp] == 5


def test_get_gaping_exp_cflag34_zero(ctx, data):
    st = ctx.state
    st.charas[1].cflag[34] = 0
    assert gaping.get_v_gaping_exp(ctx, 9) == 0  # :1015–1016
    assert gaping.get_a_gaping_exp(ctx, 9) == 0  # :1044–1045
    assert ctx.out.lines == []


def test_get_a_gaping_exp(ctx, data):
    c = ctx.state.charas[1]
    assert gaping.get_a_gaping_exp(ctx, 7) == 2
    assert c.exp[data.index_of("EXP", "Ａ拡張経験")] == 2
    assert texts(ctx.out)[-1] == "Ａ拡張経験 + 2"


# --- V_GAPING（:851–925）・A_GAPING（:932–998）-------------------------------------------------


@pytest.mark.parametrize(
    "roll, cflag35, ret",
    [
        # 年齢 16：UPRATE = LIMIT(4,0,15)×3+30 = 42。CFLAG:35 = 31：POWER(31,2)/150 = 6、GAPING_RANK(31) = 3 → 300、
        # (306×42)/20 = 642 → 2500 − 642 = 1858（:881）。1858 > RAND → CFLAG:35++（:917–918）
        (1857, 32, 1),  # 戻り値 GAPING_SIZE(32) − GAPING_SIZE(31) = 25 − 24（:924）
        (1858, 31, 0),
    ],
)
def test_v_gaping_one_iteration(ctx, roll, cflag35, ret):
    st = ctx.state
    c = st.charas[1]
    c.cflag[35] = 31
    st.rng = FixedRng([roll])
    assert gaping.v_gaping(ctx, 1) == ret
    assert c.cflag[35] == cflag35
    assert st.rng._values == []


def test_v_gaping_loop_count_and_virgin(ctx, data):
    """FOR LCOUNT, 0, ARG × ARG（:873）：ARG 2 → 4 回。処女 → 戻り値 0（:921–922）。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "処女")] = 1
    c.cflag[35] = 31
    st.rng = FixedRng([0, 0, 0, 0])
    assert gaping.v_gaping(ctx, 2) == 0
    assert c.cflag[35] == 35
    assert st.rng._values == []


def test_v_gaping_early_returns_keep_target(ctx, data):
    """ARG == 0／CFLAG:34 == 0 の RETURN は KEEPTARGET を戻さない（:858–868、TARGET = TAR のまま）。"""
    st = ctx.state
    st.rng = FixedRng([])
    st.target = 2
    assert gaping.v_gaping(ctx, 0, 1) == 0
    assert st.target == 1
    st.target = 2
    st.charas[1].cflag[34] = 0
    assert gaping.a_gaping(ctx, 5, 1) == 0
    assert st.target == 1


def test_v_gaping_suppressed(ctx):
    """CONFIG_CHECK_MANIAC_F(17) == 0（FLAG:850 の bit 17 が立つ）：:909–915。"""
    st = ctx.state
    c = st.charas[1]
    st.flag.set_bit(850, 17)
    c.cflag[35] = 154  # >= GAPING_RANK_TO_POINT(8) − 1 → RETURN 0（RAND なし）
    st.rng = FixedRng([])
    assert gaping.v_gaping(ctx, 3) == 0 and c.cflag[35] == 154
    # 120：UPRATE は代入前の 120 で計算：POWER/150 = 96、RANK 7 → 700、(796×42)/20 = 1671 → 829、/3 = 276。
    # 次に CFLAG:35 = 110、276 > RAND:10000 = 275 → 111
    c.cflag[35] = 120
    st.rng = FixedRng([275])
    gaping.v_gaping(ctx, 1)
    assert c.cflag[35] == 111
    c.cflag[35] = 120
    st.rng = FixedRng([276])
    gaping.v_gaping(ctx, 1)
    assert c.cflag[35] == 110


@pytest.mark.parametrize(
    "talent, cflag36, roll, after",
    [
        # UPRATE = LIMIT(16−10,0,15)×3+30 = 48、31 → (306×48)/20 = 734 → 1766（:960）
        (None, 31, 1765, 32),
        (None, 31, 1766, 31),
        # Ａ敏感：1766 + 1766/8 + 200 = 2186（:962–963）
        ("Ａ敏感", 31, 2185, 32),
        ("Ａ敏感", 31, 2186, 31),
        # 200：POWER/150 = 266、RANK 8 → 800、(1066×48)/20 = 2558 → −58；Ａ鈍感：−58 − (−58/8 + 200) = −251
        # （C# の切り捨て除算：−58/8 = −7）→ LIMIT 下限 500（:982）
        ("Ａ鈍感", 200, 499, 201),
        ("Ａ鈍感", 200, 500, 200),
    ],
)
def test_a_gaping(ctx, data, talent, cflag36, roll, after):
    st = ctx.state
    c = st.charas[1]
    if talent:
        c.talent[data.index_of("TALENT", talent)] = 1
    c.cflag[36] = cflag36
    st.rng = FixedRng([roll])
    r = gaping.a_gaping(ctx, 1)
    assert c.cflag[36] == after
    if cflag36 == 31:
        assert r == after - 31  # GAPING_SIZE(32) − GAPING_SIZE(31) = 1（:997）


def test_v_gaping_arg_bonus(ctx):
    """ARG >= 5 → +500（:903–904）：UPRATE 1858 + 500 = 2358。ARG 5 → 25 回。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[35] = 31
    st.rng = FixedRng([2357] + [9999] * 24)
    gaping.v_gaping(ctx, 5)
    assert c.cflag[35] == 32
    assert st.rng._values == []


# --- 表示：PRINT_TENTACLE_SIZE（:754–783）・PRINTFORM_GAPING_NOW（:789–845）-------------------------------


def test_print_tentacle_size(ctx):
    st = ctx.state
    sz, num = st.temp.tentacle_size, st.temp.tentacle_num
    st.flag[700] = 1
    st.temp.insert = gaping.V_BIT
    sz[(0, 0)], sz[(1, 0)] = 0, 10  # Ｃ：TENTACLE_SIZE:0 == 0 → T_RANK:1 のみ（:765–766）
    sz[(0, 1)], num[(0, 1)], sz[(1, 1)], num[(1, 1)] = 50, 2, 100, 2
    sz[(0, 2)], num[(0, 2)], sz[(1, 2)], num[(1, 2)] = 10, 3, 30, 0  # FLAG:700 == 1 && NUM:1 == 0 → 結界（:772–773）
    sz[(0, 3)], sz[(1, 3)] = 10, 10  # LOCAL:3 − COMMON_PALAM:3 = 0 → 表示しない（:778）
    gaping.print_tentacle_size(ctx, 1, 1, 1, 0)
    lines = ctx.out.lines
    assert [ln.text for ln in lines] == [
        "　Ｃ用触手　[ Ｅ+] 繊毛よりは太い程度",
        "　Ｖ用触手　[ Ｂ ] 一般的な男性器と同程度 2本 （挿入中）",
        # %LOCALS, 50, LEFT%：cp932 42 バイト・25 文字 → 33 文字まで空白（StrForm.cs@FormatPercent:248–263）
        "　Ａ用触手　[ Ｄ+] 繊毛よりは太い程度 3本 " + " " * 8 + " → [ × ] 結界に阻まれている",
        "",
    ]
    # HTML_PRINT の [×] 等は按鈕にならない（HtmlManager.cs@Html2DisplayLine）
    assert all(p.button is None for ln in lines for p in ln.parts)


def test_printform_gaping_now(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "処女")] = 1
    c.cflag[35] = c.cflag[36] = 0
    st.target = 2
    st.rng = FixedRng([])  # ARG == 0 の V_GAPING／A_GAPING は RAND を引かない
    gaping.printform_gaping_now(ctx, 1, 0)
    # :802 LIMIT(16−10,0,15)/3 + 20 = 22、:806 LIMIT(20−16,0,15)/3 + 20 = 21
    assert (c.cflag[35], c.cflag[36]) == (22, 21)
    assert st.target == 1  # V_GAPING の ARG == 0 の RETURN で TARGET = TAR のまま（原作どおり）
    lines = ctx.out.lines
    assert [ln.text for ln in lines] == [
        "　　拡張度",
        "　　　　膣径：　 ―  cm　/　[処女]",  # :828–829、:833–834 LOCAL:2 = −1
        "　　　　肛径：   1.5 cm　/　[ Ｄ ]",  # GAPING_SIZE(21) = 15 → {1,4}.5
    ]
    assert lines[1].parts[-1].title == "未だ純潔を保っている"
    assert lines[2].parts[-1].title == "自身の指と同程度のモノを受け入れられる"


def test_printform_gaping_now_hidden(ctx):
    """CONFIG_CHECK_MANIAC_F(16) == 0 → 何もしない（:798）。"""
    ctx.state.flag.set_bit(850, 16)
    ctx.state.charas[1].cflag[35] = 0
    gaping.printform_gaping_now(ctx, 1, 0)
    assert ctx.out.lines == [] and ctx.state.charas[1].cflag[35] == 0


# --- MESSAGE_SEX_SPCOM7:1229–1293 の INPUTS ---------------------------------------------------------


def _spcom7_ctx(ctx, monkeypatch, seen):
    """FLAG:900 は直後の KOJO_ROOT が 0 に戻す（KOJO_ROOT.ERB:46–90）ので、KOJO_ROOT 呼び出し時の値を記録する。"""
    from eragvt.game.battle import sexmsg

    monkeypatch.setattr(sexmsg, "kojo_root", lambda c, code, *a: seen.append((code, c.state.flag[900])))
    st = ctx.state
    st.flag[70] = st.flag[71] = 0
    st.flag[110] = 0
    st.savestr[13] = "BOSS"
    return ctx


def test_spcom7_inputs_skip(ctx, monkeypatch):
    seen = []
    ctx = _spcom7_ctx(ctx, monkeypatch, seen)
    gen = msg_spcom7(ctx)
    next(gen)  # :1236 INPUTS 待ち
    assert ctx.out.lines[-1].text == "[1]映像を見る"
    with pytest.raises(StopIteration):
        gen.send(0)  # RESULTS = "0" ≠ "1"
    assert seen == [("SEX_SPCOM7", 3)]  # :1293 FLAG:900 = 3 → :1297 KOJO_ROOT
    assert all(ln.text != "[1]映像を見る" for ln in ctx.out.lines)  # :1237 CLEARLINE


def test_spcom7_inputs_video_site_without_catalog(ctx, monkeypatch):
    """S14：動画サイト（:1258 CALL MESSAGE_SEX_VIDEO_SITE_Window）は状態変化なし。catalog が無ければ佔位 1 行で続行。"""
    seen = []
    ctx = _spcom7_ctx(ctx, monkeypatch, seen)
    gen = msg_spcom7(ctx)
    next(gen)
    with pytest.raises(StopIteration):
        gen.send(1)
    assert any(ln.text == "〈地の文：MESSAGE_SEX_VIDEO_SITE_Window〉" for ln in ctx.out.lines)
    assert seen == [("SEX_SPCOM7", 3)]


def test_spcom7_no_input_when_cflag34_zero(ctx, monkeypatch):
    seen = []
    ctx = _spcom7_ctx(ctx, monkeypatch, seen)
    ctx.state.charas[1].cflag[34] = 0
    with pytest.raises(StopIteration):
        next(msg_spcom7(ctx))  # :1239–1240 RESULTS = 0
    assert seen == [("SEX_SPCOM7", 3)]


# --- 整合：預設開局 → 出撃 → 性攻撃で拡張 ----------------------------------------------------------------


def test_e2e_default_opening_gaping_in_battle(data):
    """預設開局（CFLAG:34 = 1）でボス戦 → 拘束中は耐える（10）／なすがまま（11）で性攻撃を受け、
    PALAM_CALC_GAPING（PALAM_UP.ERB:771–800）で拡張度が上がるまで進める（停止しないこと）。"""
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(9))
    s.input(0)
    s.input(0)  # おまかせ（汎用キャラ 3 名）
    s.state.flag[47] = s.state.flag[46]  # ENCOUNT.ERB:159 ボス遭遇条件
    s.input(101)
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)
    for _ in range(200):
        assert s.phase == Phase.TURN
        b = [p.button for ln in s.screen()[-30:] for p in ln.parts if p.button is not None]
        if s.state.target_chara.tcvarn[0] == 0:
            x = next((n for n in (10, 11, 8) if n in b), b[0] if b else 0)
        else:
            x = 1 if 1 in b else (b[0] if b else 0)
        s.input(x)
        if any(s.state.charas[i].cflag[35] for i in range(1, s.state.charanum)):
            break
    t = [ln.text for ln in s.out.lines]
    assert any("用触手" in x for x in t)  # PRINT_TENTACLE_SIZE（:775）
    assert any(x.startswith("Ｖ拡張経験 + ") for x in t)  # GET_V_GAPING_EXP（:780）
    assert any(x.startswith("　膣径：＋") for x in t)  # V_GAPING（:784–788）
