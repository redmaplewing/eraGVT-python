"""S11：いちゃラブセックス（`ゲーム内_イベント発生/強制発生イベント/FORCE_いちゃラブセックス.ERB`）と AFTER_PILL／
NINSIN_HANTEI の一般人分岐（`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB`）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/`、行號は註解）。
"""

from __future__ import annotations
from _gen_driver import as_generator, run_no_input

import re
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import lovesex, shop
from eragvt.game.action import Ctx
from eragvt.game.battle import ninsin
from eragvt.game.opening import event_first
from eragvt.game.session import GameSession, Phase
from eragvt.narration.hooks import LOVESEX_HOOK_LINES
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


def T(data, name):
    return data.index_of("TALENT", name)


def A(data, name):
    return data.index_of("ABL", name)


def E(data, name):
    return data.index_of("EXP", name)


@pytest.fixture
def ctx(data):
    """預設開局。キャラ 1 だけを対象にする（2・3 は CFLAG:999 = 0 → :14–15 CONTINUE）。キャラ 1 は素質・能力を 0 に。"""
    s = GameState.new(data, rng=GameRng(3))
    event_first(s, data)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.time = 1
    s.target = 1
    for i in (2, 3):
        s.charas[i].cflag[999] = 0
    c = s.charas[1]
    c.talent.clear()
    c.abl.clear()
    c.exp.clear()
    c.cflag[99] = 0
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def run_gen(gen):
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT 待ちになった")


# --- LOVESEX_NIGHT の発生条件（:5–96）-------------------------------------------------------------


def _record(monkeypatch):
    calls = []

    def kind(ctx, arg, arg1):
        calls.append(("KIND", arg, arg1))
        return 1
        yield  # noqa: B901（ジェネレータにする）

    monkeypatch.setattr(lovesex, "lovesex_kind", kind)
    monkeypatch.setattr(lovesex, "ablup", lambda ctx, arg: calls.append(("ABLUP", arg)))
    monkeypatch.setattr(lovesex, "message_kataomoi_night", lambda ctx: calls.append(("KATAOMOI",)))
    return calls


@pytest.mark.parametrize(
    "partner, virgin, student, day, yokubou, cflag99, rolls, expected",
    [
        (0, 0, 0, 1, 20, 0, [], []),  # :28 交際相手 0（|| の短絡で RAND:10 は引かない：OperatorMethod.cs:532–536）
        (5, 0, 0, 1, 20, 0, [], []),  # 未亡人
        (2, 0, 0, 1, 20, 30, [], []),  # :24 疲労 30 以上
        (1, 0, 0, 1, 20, 0, [5], []),  # :28 片思い：RAND:10 = 5 > 4 → CONTINUE
        (1, 0, 0, 1, 2, 0, [4, 9], [("KATAOMOI",)]),  # 欲望 2 → LOCAL:1 = 10、RAND:100 = 9 < 10 → 告白（:85）
        (1, 0, 0, 1, 2, 0, [4, 10], []),  # 10 < 10 偽
        (2, 0, 0, 1, 1, 0, [4], [("KIND", 1, 0), ("ABLUP", 0)]),  # :82 4 < 5 → :88–90
        # 処女 × 彼氏持ち：LOCAL:3 = 12（:48–49）、高校生 +4 = 16。DAY 15 < 16 && RAND:4 != 0 → CONTINUE（:63–64）
        (2, 1, 3, 15, 20, 0, [1], []),
        (2, 1, 3, 15, 20, 0, [0, 50], [("KIND", 1, 0), ("ABLUP", 0)]),  # RAND:4 == 0 → 判定へ：欲望 20 → 100
        (2, 1, 3, 16, 20, 0, [99], [("KIND", 1, 0), ("ABLUP", 0)]),  # DAY 16 は制限なし（RAND:4 を引かない）
    ],
)
def test_lovesex_night_conditions(ctx, data, monkeypatch, partner, virgin, student, day, yokubou, cflag99, rolls,
                                  expected):
    st = ctx.state
    c = st.charas[1]
    calls = _record(monkeypatch)
    c.talent[T(data, "交際相手")] = partner
    c.talent[T(data, "処女")] = virgin
    c.talent[T(data, "学生")] = student
    c.abl[A(data, "欲望")] = yokubou
    c.cflag[99] = cflag99
    c.palam[0] = 123
    st.day[0] = day
    st.target = 2
    st.rng = FixedRng(rolls)
    list(lovesex.lovesex_night(ctx))
    assert calls == expected
    assert st.rng._values == []
    assert st.target == 2  # :96
    assert (c.palam[0] == 0) == bool(expected)  # :93 VARSET PALAM（TARGET）


def test_lovesex_night_houshi_and_day_time(ctx, data, monkeypatch):
    """奉仕精神 3 → +25（:75–76）、精液中毒 1 → +2：LOCAL:1 = 27。TIME != 1 → 何もしない（:7–8）。"""
    st = ctx.state
    c = st.charas[1]
    calls = _record(monkeypatch)
    c.talent[T(data, "交際相手")] = 3
    c.abl[A(data, "奉仕精神")] = 3
    c.abl[A(data, "精液中毒")] = 1
    st.rng = FixedRng([27])
    list(lovesex.lovesex_night(ctx))
    assert calls == []
    st.rng = FixedRng([26])
    list(lovesex.lovesex_night(ctx))
    assert calls[0] == ("KIND", 1, 0)
    st.time = 0
    st.rng = FixedRng([])
    list(lovesex.lovesex_night(ctx))


# --- LOVESEX_KIND（:100–147）------------------------------------------------------------------


@pytest.mark.parametrize(
    "setup, rolls, expected",
    [
        ({}, [0], [("V", 0)]),  # Ａ感覚 0 → LOCAL:0 = 0 → SEX_V ARG, 0（:128–133）
        ({"淫壷": 1}, [6], [("V", 0), ("V", 1)]),  # RAND:10 = 6 > 5 → SEX_V 0、SEX_TWICE 1 → SEX_V 1
        ({"淫壷": 1}, [5], [("V", 0)]),
        ({"淫尻": 1}, [0], [("A",), ("V", 0)]),  # :117–118
        ({"Ａ感覚": 2}, [0, 50], [("V", 0)]),  # 女性・非聖処女 → RAND:100 = 50 >= 50 → SEX_V
        ({"Ａ感覚": 2}, [0, 49], [("A",)]),
        ({"Ａ感覚": 2, "処女": 2}, [0], [("A",)]),  # 聖処女（処女 >= 2）→ LOCAL:1 = 0 のまま → SEX_A
    ],
)
def test_lovesex_kind(ctx, data, monkeypatch, setup, rolls, expected):
    st = ctx.state
    c = st.charas[1]
    for k, v in setup.items():
        if k == "Ａ感覚":
            c.abl[A(data, k)] = v
        else:
            c.talent[T(data, k)] = v
    calls = []

    def sex_v(ctx, arg, arg1=0):
        calls.append(("V", arg1))
        return 0
        yield  # noqa: B901

    monkeypatch.setattr(lovesex, "sex_v", sex_v)
    monkeypatch.setattr(lovesex, "sex_a", as_generator(lambda ctx, arg: calls.append(("A",))))
    c.nowex[0] = 3
    st.rng = FixedRng(rolls)
    assert run_gen(lovesex.lovesex_kind(ctx, 1, 0)) == 1
    assert calls == expected
    assert st.rng._values == []
    assert c.nowex[0] == 0  # :110 VARSET NOWEX


# --- SEX_V（:151–337）・SEX_A（:341–447）の PALAM_CAL 引数 ----------------------------------------------


@pytest.fixture
def captured(monkeypatch):
    got = {}
    monkeypatch.setattr(lovesex, "palam_cal", as_generator(lambda ctx, *a, losebase=0: got.update(args=a, losebase=losebase)))
    monkeypatch.setattr(lovesex, "ninsin_hantei", as_generator(lambda ctx, *a: got.update(ninsin=a)))
    return got


def test_sex_v_non_virgin(ctx, data, captured):
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "処女")] = -1
    for name, v in (("Ｃ感覚", 1), ("Ｖ感覚", 2), ("Ｂ感覚", 0), ("技巧", 2), ("露出癖", 0), ("奉仕精神", 1)):
        c.abl[A(data, name)] = v
    st.rng = FixedRng([0])  # MESSAGE_SEX_V:1315 RAND:4（Null → fallback で同じ RAND を引く）
    assert run_gen(lovesex.sex_v(ctx, 1)) == 0
    # 快C 1000・快V 1000・快B 200 → 技巧 2 で TIMES 1.10（:237–239）；屈服・恥情 50（露出癖 0）、欲情 1000・習得 400（奉仕 1）
    assert captured["args"] == (1100, 1100, 0, 220, 0, 0, 400, 1000, 50, 50, 0, 0)
    assert captured["losebase"] == 150  # :322
    assert captured["ninsin"] == (6, 800, -3)  # :336 愛する人（DIM.ERH:256）
    assert c.cflag[218] == 1  # :331
    assert [c.exp[E(data, n)] for n in ("Ｖ経験", "精液経験", "フェラ経験")] == [1, 1, 1]


def test_sex_v_virgin(ctx, data, captured):
    """処女：:220–224 TALENT:処女 = −1、CFLAG:206 = 5、LOCAL:10（苦痛）= 2500。
    地の文 :1301 の TALENT:処女 == 1 は既に −1 なので RAND:4 を引く。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "処女")] = 1
    st.rng = FixedRng([1])
    run_gen(lovesex.sex_v(ctx, 1))
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 5
    assert captured["args"] == (200, 200, 0, 200, 0, 0, 200, 0, 50, 50, 2500, 0)
    assert st.rng._values == []


def test_sex_v_condom_config(ctx, data, captured):
    """CONFIG_CHECK_EVENT_F(6) == 1：SEX_V_CONDOM（初回はイチャックス回数 1 ≤ RAND:3+2 → RETURN 1）→ ゴム有り：
    TIMES 0.95／0.90／0.95（:227–231）、妊娠判定なし（:328–329）。"""
    st = ctx.state
    c = st.charas[1]
    st.flag.set_bit(802, 6)
    st.rng = FixedRng([0, 0])  # SEX_V_CONDOM:465 RAND:3、MESSAGE_SEX_V RAND:4
    assert run_gen(lovesex.sex_v(ctx, 1)) == 0
    assert captured["args"][:4] == (190, 180, 0, 190)
    assert "ninsin" not in captured and c.cflag[218] == 0


def test_sex_v_condom_prompt(ctx, data):
    """イチャックス回数 > LOCAL:1 → 提案（:468–476）。範囲外の入力は再入力（:523–524 GOTO）。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "交際相手")] = 2
    st.temp.locals[("SEX_V_CONDOM", "イチャックス回数")] = 10
    st.rng = FixedRng([0])  # LOCAL:1 = 0 + 2 + 彼氏持ち 1 人 = 3
    gen = lovesex.sex_v_condom(ctx, 1)
    next(gen)
    assert texts(ctx.out)[-4:] == ["彼氏はどうやらゴムを着けずに生でのセックスがしたいようだ・・・", "受け入れますか？",
                                   "[0]はい", "[1]いいえ"]
    assert st.temp.locals[("SEX_V_CONDOM", "イチャックス回数")] == 0  # :474
    n = len(ctx.out.lines)
    gen.send(7)
    assert len(ctx.out.lines) == n
    with pytest.raises(StopIteration) as e:
        gen.send(1)
    assert e.value.value == 1
    # :517 PRINT（改行なし）→ :519 PRINTFORML が同じ行に続く
    assert texts(ctx.out)[-2:] == [f"もどかしさを感じながら、{c.callname}は彼氏のペニスにゴムを装着した・・・", ""]


def test_sex_a(ctx, data, captured):
    st = ctx.state
    c = st.charas[1]
    for name, v in (("Ａ感覚", 3), ("技巧", 3), ("露出癖", 2)):
        c.abl[A(data, name)] = v
    st.rng = FixedRng([0])  # MESSAGE_SEX_A:1419 RAND:2 = 0（CASE 0：RAND:10 なし）
    run_no_input(lovesex.sex_a(ctx, 1))
    # 快A 4000 × 1.25 = 5000、屈服・恥情 500、欲情 0（奉仕 0）・習得 200
    assert captured["args"] == (0, 0, 5000, 0, 0, 0, 200, 0, 500, 500, 0, 0)
    assert [c.exp[E(data, n)] for n in ("精液経験", "Ａ経験", "フェラ経験")] == [1, 1, 1]
    assert st.rng._values == []


# --- AFTER_PILL（:898–957）・NINSIN_HANTEI の一般人（:93–96）--------------------------------------------


def test_after_pill_default_config_returns(ctx):
    ctx.state.rng = FixedRng([])
    assert run_gen(ninsin.after_pill(ctx, 1, 75, -3)) == 0  # CONFIG_CHECK_OTHER_F(3) == 0（FLAG:805 = 2）
    assert ctx.out.lines == []


def test_after_pill_take(ctx, data):
    st = ctx.state
    c = st.charas[1]
    st.flag.set_bit(805, 3)
    st.money = 1000
    c.talent[T(data, "妊娠")] = 4
    st.rng = FixedRng([10, 10])  # :936 RAND:100 < 75、CHECK_HININ_F(1, −3)：CFLAG:241 > 0 && ARG:1 < 0 → 80、10 < 80
    gen = ninsin.after_pill(ctx, 1, 75, -3)
    next(gen)
    n = len(ctx.out.lines)
    gen.send(3)  # :953–956 再入力（CLEARLINE LINECOUNT − LCOUNT）
    assert len(ctx.out.lines) == n
    with pytest.raises(StopIteration):
        gen.send(1)
    assert st.money == 500 and c.cflag[99] == 15 and c.cflag[241] == 1
    assert c.talent[T(data, "妊娠")] == 0  # :938–939
    assert texts(ctx.out)[-2:] == [f"{c.callname}はアフターピルを飲んだ…", "身体の底に疲労が蓄積した……（＋１５）"]


def test_after_pill_no_money(ctx):
    st = ctx.state
    st.flag.set_bit(805, 3)
    st.money = 100
    st.rng = FixedRng([])
    gen = ninsin.after_pill(ctx, 1, 20, -3)
    next(gen)
    assert "時間が経ち過ぎて効果がないかもしれないが、" in texts(ctx.out)[-3]  # ARG:1 < 25
    with pytest.raises(StopIteration):
        gen.send(1)
    assert texts(ctx.out)[-1] == "なんと、所持金が足りない！"


@pytest.mark.parametrize("roll, pregnant", [(148, False), (147, True)])
def test_ninsin_hantei_human_father(ctx, roll, pregnant):
    """ARG:2 = 愛する人（−3）：CHECK_HININ_F は RAND:100 を引く（:26、LOCAL 0 → 不成立）。PAPA_ID = −3、
    CHARAID_F(−97) = 0 → MASTER は寄生ふたなりでない → RAND:4 なし（:62–64）。CFLAG:233 += 6 →
    SQRT(800×6×1/2) = 48（:93–96）、FLAG:700 == 0、幽閉されていない → RAND:1000 < 48 + 100（:140）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[217] = 0
    st.rng = FixedRng([0, roll, 20])
    if pregnant:
        # S13：受精成立 → NINSIN_SUBMIT（出産経験 0：屈服 +2500・恐怖 +1500、:765–766）、:144–148、
        # NINSIN_FLAG（普通の人間・寄生なし → 妊娠 = 4、CFLAG:228 = 266 × (80 + RAND:41) / 100：:214–218、:837–839）
        assert run_no_input(ninsin.ninsin_hantei(ctx, 6, 800, -3)) == 1
        assert c.cflag[233] == 0 and c.cflag[221] == 0 and c.cflag[232] == 0 and c.cflag[230] == -3
        assert c.talent[T(ctx.data, "妊娠")] == 4 and c.cflag[228] == 266
        assert c.juel[ctx.data.index_of("PALAM", "屈服")] == 2500 and c.juel[ctx.data.index_of("PALAM", "恐怖")] == 1500
    else:
        assert run_no_input(ninsin.ninsin_hantei(ctx, 6, 800, -3)) == 0
        assert c.cflag[233] == 6 and c.cflag[221] == 6 and c.cflag[232] == 0


# --- 地の文（catalog）と hook ------------------------------------------------------------------------


def test_lovesex_hook_table_matches_erb(svc):
    cat = svc.catalog
    for (func, line), (text, _) in LOVESEX_HOOK_LINES.items():
        e = cat.index[func]
        assert dict(cat.lines_of(e.rel))[line].strip() == text, (func, line)
    # 4 つの地の文の中の非 LOCAL 代入・状態 CALL はすべて表にある
    e0 = cat.index["MESSAGE_LOVESEX_NIGHT"]
    lines = dict(cat.lines_of(e0.rel))
    for no in range(1264, 1577):
        s = lines.get(no, "").strip()
        if re.match(r"^(FLAG|CFLAG|TALENT|BASE|EXP|ABL|TFLAG|MARK|MONEY)\b[^=]*[-+*/|&]?=(?!=)", s) or s.startswith("CALL "):
            assert ("MESSAGE_KATAOMOI_NIGHT", no) in LOVESEX_HOOK_LINES, (no, s)
    for name in ("MESSAGE_LOVESEX_NIGHT", "MESSAGE_SEX_V", "MESSAGE_SEX_A", "MESSAGE_KATAOMOI_NIGHT"):
        assert cat.unsupported_reason(name) is None, name


@pytest.mark.parametrize("roll, partner, line", [(96, 0, "彼はその告白を断った。"), (70, 1, "すこし考えさせてほしいと言った。"),
                                                 (0, 2, None)])
def test_kataomoi_catalog_hook(ctx, data, svc, roll, partner, line):
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "交際相手")] = 1
    cctx = Ctx(st, data, TextOutput(), svc)
    st.rng = FixedRng([roll])  # :1547 RAND:100
    lovesex.message_kataomoi_night(cctx)
    assert c.talent[T(data, "交際相手")] == partner  # :1559 ／ :1575 hook
    t = texts(cctx.out)
    assert f"告白（{c.callname}）" in t
    if line:
        assert line in t


def test_kataomoi_null_fallback(ctx, data):
    c = ctx.state.charas[1]
    c.talent[T(data, "交際相手")] = 1
    ctx.state.rng = FixedRng([10])
    lovesex.message_kataomoi_night(ctx)
    assert c.talent[T(data, "交際相手")] == 2
    assert texts(ctx.out) == ["〈地の文：MESSAGE_KATAOMOI_NIGHT〉"]


# --- 整合：預設開局 → 夜のいちゃラブ → SHOP -------------------------------------------------------------


def test_e2e_default_opening_lovesex_night(data, svc):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(3), narration=svc)
    s.input(0)
    s.input(1)  # MODE_SELECT NORMAL
    s.input(1000)  # CHARA_MAKE_MAIN 完成
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    s.input(0)  # EVENTFIRST 序章略過
    st = s.state
    c = st.charas[1]
    assert c.talent[T(data, "交際相手")] == 4  # seed 3：柊心美は人妻（CHARA_MAKE_DEFAULT）
    c.abl[A(data, "欲望")] = 20  # LOCAL:1 = 100 → 必ず発生（:82）
    vexp = c.exp[E(data, "Ｖ経験")]
    for _ in range(2):  # 晝 → 夜（TIME 1 の EVENTTURNEND で LOVESEX_NIGHT：SHOP_TURNEND.ERB:112）
        assert s.phase == Phase.SHOP
        for i in range(1, st.charanum):
            s.input(i)
            s.input(103)  # 休憩する
        s.input(100)
        while s.phase == Phase.ACTION_CONFIRM:  # 確認は [9] のみ開始（SHOP.ERB:521–532：[1] は中断＝原作どおり）
            s.input(9)
    assert s.phase == Phase.SHOP
    t = [ln.text for ln in s.out.lines]
    assert f"夜の営み（{c.callname}）" in t  # MESSAGE_LOVESEX_NIGHT:1269
    assert any(x in t for x in ("セックス", "アナルセックス"))  # MESSAGE_SEX_V:1299／MESSAGE_SEX_A:1417
    assert c.exp[E(data, "Ｖ経験")] > vexp or c.exp[E(data, "Ａ経験")] > 0
