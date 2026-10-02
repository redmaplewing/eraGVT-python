"""S17：寄生系統（`ゲーム内_イベント発生/強制発生イベント/FORCE_深夜の寄生触手暴走.ERB`、`COMMON_BATTLE_FUNC.ERB@ACT_LIMIT`:226–255、
`ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP`:407–422）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/`、行號は註解。FORCE = FORCE_深夜の寄生触手暴走.ERB）。
乱数は FixedRng（`值 % n`）、ZeroTail は使い切ったあと 0。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import parasite as P
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.battle.ablup import ablup
from eragvt.game.battle.func import act_limit
from eragvt.game.battle.sexcom import check_holyvirgin
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.relation import ITOKO, KOIBITO, OYAKO, SHITASHII, YUUJIN
from eragvt.game.session import GameSession, Phase
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


class ZeroTail(FixedRng):
    def rand(self, n: int) -> int:
        if not self._values:
            return 0
        return super().rand(n)


@pytest.fixture
def ctx(data):
    """初期セット『特装戦隊』（CHARANUM = 4、キャラ 1〜3 編成中）、夜（TIME = 1）。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.time = 1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def T(data, n):
    return data.index_of("TALENT", n)


def E(data, n):
    return data.index_of("EXP", n)


def A(data, n):
    return data.index_of("ABL", n)


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def drive(gen, inputs):
    """ジェネレータに入力列を与えて最後まで実行。残った入力数を返す（全部使えば 0）。"""
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            gen.send(inputs.pop(0))
    except StopIteration:
        return len(inputs)


def _parasitize(data, c, kyousei=0):
    c.talent[T(data, "寄生")] = 1
    c.talent[T(data, "共生")] = kyousei


# --- PARASITE（FORCE:3–68）--------------------------------------------------------------------


@pytest.mark.parametrize(
    "c82, c83, c84, get_event",
    [
        (49, 0, 0, True),  # :20–21 で 50 → :36 LOCAL:3 = 50 → :38 成立
        (48, 0, 0, False),  # 49 < 50
        (19, 1, 0, True),  # :32–34 CFLAG:83 > 0 → 20
        (49, 0, 1, False),  # :38 CFLAG:84 != 0（次から確認しない）
    ],
)
def test_parasite_synbiosis_get_condition(ctx, data, c82, c83, c84, get_event):
    st = ctx.state
    c = st.charas[2]
    _parasitize(data, c)
    c.cflag[82], c.cflag[83], c.cflag[84] = c82, c83, c84
    st.rng = FixedRng([9999])  # 共生取得が無いときの :48 RAND:10000（≥ 200 なので暴走しない）
    gen = P.parasite(ctx)
    if get_event:
        next(gen)  # :331 INPUT 待ち
        assert "寄生触手との共生（" + c.callname + "）" in texts(ctx.out)
        with pytest.raises(StopIteration):
            gen.send(1)
    else:
        assert list(gen) == []
        assert not any("寄生触手との共生" in x for x in texts(ctx.out))
    assert c.exp[E(data, "寄生経験")] == 1  # :17


@pytest.mark.parametrize(
    "answer, kyousei, c82, c83, c84, line",
    [
        (0, 1, 0, 50 + 7, 0, "は 共生 を得た"),  # :337–347 CFLAG:83 += CFLAG:82、CFLAG:82 = 0
        (1, 0, 50, 7, 0, "但し一時しのぎにしかならず、時間が経てばまた同じことが起こるだろう、と。"),
        (9, 0, 50, 7, 1, "但し、この薬では体内の触手の除去までは出来ない"),  # :333–334
        (5, 0, 50, 7, 0, "但し、この薬では体内の触手の除去までは出来ない"),  # 値を検査しない：0／1／9 以外も ELSE
    ],
)
def test_synbiosis_get_event_answers(ctx, data, answer, kyousei, c82, c83, c84, line):
    st = ctx.state
    c = st.charas[2]
    _parasitize(data, c)
    c.cflag[82], c.cflag[83] = 49, 7
    st.rng = FixedRng([])
    # CFLAG:83 > 0 → 閾値 20、49 + 1 = 50 ≥ 20
    assert drive(P.parasite(ctx), [answer]) == 0
    assert c.talent[T(data, "共生")] == kyousei
    assert (c.cflag[82], c.cflag[83], c.cflag[84]) == (c82, c83, c84)
    assert any(line in x for x in texts(ctx.out))


def test_parasite_day_and_kyousei_no_adapt(ctx, data):
    """:20–21 共生なら CFLAG:82 は増えない、:28–29 昼は判定なし（RAND なし）。"""
    st = ctx.state
    c = st.charas[3]
    _parasitize(data, c, kyousei=1)
    st.time = 0
    st.rng = FixedRng([])
    assert list(P.parasite(ctx)) == []
    assert c.cflag[82] == 0 and c.exp[E(data, "寄生経験")] == 1
    assert st.flag[799] == 3  # :9 CHARANUM-1 まで上書き


# --- PARASITE_EVENT／PARASITE_ACTION（FORCE:72–283）-----------------------------------------------


@pytest.mark.parametrize(
    "rolls, target, self_attack",
    [
        ([199, 0], 2, True),  # :48 199 < 200、:78 RAND:4 == 0 → 自分
        ([199, 1, 0], 1, False),  # RAND:4 = 1 → RAND:3 + 1 = 1
        ([199, 1, 2], 3, False),  # RAND:3 = 2 → 3
    ],
)
def test_parasite_event_target(ctx, data, rolls, target, self_attack):
    st = ctx.state
    c = st.charas[2]
    _parasitize(data, c)
    st.rng = ZeroTail(rolls)
    assert list(P.parasite(ctx)) == []
    assert st.target == target  # :88
    out = texts(ctx.out)
    assert "寄生触手の暴走" in out
    if self_attack:
        assert f"{c.callname}は自身に寄生する触手を抑えきれずに、暴走を許してしまった！" in out
    else:
        assert any(f"隣室の{st.charas[target].callname}に襲いかかった！" in x for x in out)


def test_parasite_event_skips_unavailable(ctx, data):
    """:85–86 CFLAG:0 != 0 のキャラは GOTO LOOP で選び直し。"""
    st = ctx.state
    _parasitize(data, st.charas[2])
    st.charas[1].cflag[0] = 1
    st.rng = ZeroTail([199, 1, 0, 1, 2])  # 1 回目 → キャラ 1（幽閉中）→ やり直し → 3
    list(P.parasite(ctx))
    assert st.target == 3


def test_parasite_action_state(ctx, data):
    """:111–236：ABL C0／V2／A1／B0 の女性・処女 → LOCAL:120 = 8、:121 = 5、処女 = -1・CFLAG:206 = 4（:193–200）、
    :231–234 は両方 LOCAL:123（精液経験）→ 2、フェラ経験は増えない、:236 異常経験 +1。"""
    st = ctx.state
    c = st.charas[2]
    _parasitize(data, c)
    for n, v in (("Ｃ感覚", 0), ("Ｖ感覚", 2), ("Ａ感覚", 1), ("Ｂ感覚", 0)):
        c.abl[A(data, n)] = v
    c.talent[T(data, "処女")] = 1
    c.talent[T(data, "オトコ")] = 0
    st.target = 2
    assert check_holyvirgin(ctx) == 0
    before = {n: c.exp[E(data, n)] for n in ("Ｖ経験", "Ａ経験", "精液経験", "フェラ経験", "異常経験")}
    st.rng = ZeroTail([199, 0])
    list(P.parasite(ctx))
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 4
    got = {n: c.exp[E(data, n)] - before[n] for n in before}
    assert got == {"Ｖ経験": 8, "Ａ経験": 5, "精液経験": 2, "フェラ経験": 0, "異常経験": 1}
    out = texts(ctx.out)
    assert "処女喪失" in out
    # :247–250 `CHECK_HOLYVIRGIN_F()==0 && ISFEMALE(TARGET)` → 「ヴァギナと」
    assert "完全に独立した意志を見せる触手がヴァギナと尻穴に潜り込み、" in out


def test_parasite_drawline_only_first(ctx, data):
    """:50–52 静的 LOCAL:2：DRAWLINE は最初の 1 回だけ。"""
    st = ctx.state
    _parasitize(data, st.charas[2])
    st.rng = ZeroTail([199, 0])
    list(P.parasite(ctx))
    n1 = sum(1 for ln in ctx.out.lines if ln.kind == "drawline")
    st.rng = ZeroTail([199, 0])
    list(P.parasite(ctx))
    n2 = sum(1 for ln in ctx.out.lines if ln.kind == "drawline")
    assert st.temp.locals[("PARASITE", 2)] == 1
    assert n2 - n1 == 0 and n1 >= 1


# --- SYNBIOSIS_EVENT／SOLO／YOBAI（FORCE:367–760）---------------------------------------------------


def _kyousei_night(ctx, data, me=2):
    st = ctx.state
    _parasitize(data, st.charas[me], kyousei=1)
    return st.charas[me]


def test_synbiosis_event_solo(ctx, data):
    """:54–56 共生なら慰み者 → [0] 自分自身（:399、:431 TARGET = FLAG:799 → SYNBIOSIS_ABL_UP, 0：異常経験 +1）。"""
    st = ctx.state
    c = _kyousei_night(ctx, data)
    st.target = 1
    before = c.exp[E(data, "異常経験")]
    st.rng = ZeroTail([199])
    assert drive(P.parasite(ctx), [0]) == 0
    assert st.target == 2
    assert c.exp[E(data, "異常経験")] == before + 1
    out = texts(ctx.out)
    assert f"寄生触手の慰み者（{c.callname}）" in out
    assert "[1]仲間の元へ向かう" in out  # :388–389 対象あり
    assert "深い眠りについた。" in out


def test_synbiosis_event_invalid_then_gaman(ctx, data):
    """:421–423 不正値 → 「正しい値を入力してください」→ INPUT し直し、[999] 我慢（状態変化なし）。"""
    st = ctx.state
    c = _kyousei_night(ctx, data)
    st.rng = ZeroTail([199])
    before = c.exp[E(data, "異常経験")]
    assert drive(P.parasite(ctx), [5, 999]) == 0
    out = texts(ctx.out)
    assert "正しい値を入力してください" in out
    assert "これではまるで、自分が触手となってしまったようじゃないか" in out
    assert c.exp[E(data, "異常経験")] == before


def test_synbiosis_event_no_yobai_target(ctx, data):
    """:383–389 対象なし（他全員 繁殖袋）→ [1] は表示されず、入力 1 は不正値扱い（:400 `RESULT == 1 && Y_RESULT == 0`）。"""
    st = ctx.state
    _kyousei_night(ctx, data)
    for i in (1, 3):
        st.charas[i].talent[T(data, "繁殖袋")] = 1
    st.flag[799] = 2
    assert P.check_synbiosis_yobai_target(ctx) == -999
    st.rng = ZeroTail([199])
    assert drive(P.parasite(ctx), [1, 999]) == 0
    out = texts(ctx.out)
    assert "[1]仲間の元へ向かう" not in out
    assert "正しい値を入力してください" in out


def test_synbiosis_yobai_action(ctx, data):
    """:400–402 → SYNBIOSIS_YOBAI_EVENT：[3] → TARGET = 3（:656）→ SYNBIOSIS_ABL_UP, 1 は TARGET（キャラ 3）に入る。"""
    st = ctx.state
    me = _kyousei_night(ctx, data)
    o = st.charas[3]
    b_me, b_o = me.exp[E(data, "異常経験")], o.exp[E(data, "異常経験")]
    st.rng = ZeroTail([199])
    assert drive(P.parasite(ctx), [1, 3]) == 0
    assert st.target == 3
    assert o.exp[E(data, "異常経験")] == b_o + 1 and me.exp[E(data, "異常経験")] == b_me
    out = texts(ctx.out)
    assert "誰の部屋に行きますか？" in out and "[999]夜這いは行わない" in out
    assert f"{me.callname}は無意識の内に、{o.callname}の部屋の前まで足を運んでいた。" in out


def test_synbiosis_yobai_cancel(ctx, data):
    """:653–654 RETURN 999 → :404–408 やめる。不正値（0、CHARANUM 以上）はやり直し（:660–662）。"""
    st = ctx.state
    _kyousei_night(ctx, data)
    st.rng = ZeroTail([199])
    assert drive(P.parasite(ctx), [1, 0, 4, 999]) == 0
    out = texts(ctx.out)
    assert out.count("正しい値を入力してください") == 2
    assert "やはり止めよう、仲間を傷付けるわけにはいかない。" in out


@pytest.mark.parametrize(
    "setup, expected",
    [
        ({}, [1, 3]),
        ({3: "繁殖袋"}, [1]),  # :607–608
        ({1: "四肢欠損"}, [3]),
        ({"me": "女性苦手"}, []),  # :615–616（初期セットは全員女性）
        ({"me": ("女性苦手", "両刀")}, [1, 3]),
    ],
)
def test_yobai_candidates(ctx, data, setup, expected):
    st = ctx.state
    st.flag[799] = 2
    for k, v in setup.items():
        c = st.charas[2] if k == "me" else st.charas[k]
        for n in (v if isinstance(v, tuple) else (v,)):
            c.talent[T(data, n)] = 1
    assert P._yobai_candidates(ctx, False) == expected
    assert P.check_synbiosis_yobai_target(ctx) == (0 if expected else -999)


@pytest.mark.parametrize(
    "bits, text",
    [
        ((), ""),
        ((SHITASHII,), "親しい間柄"),  # :797–798（血縁・関係なし）
        ((YUUJIN, SHITASHII), "親友"),  # :813 友人なら「親しい」を付けない、:904–905
        ((OYAKO, KOIBITO), "(実の母親かつ恋人)"),  # TOSHIUE_F(TARGET=2, 3)：同年齢なら CFLAG:240 で判定
        ((ITOKO,), "(実のいとこ"),  # :931 閉じ括弧の条件に いとこ が無い（原作どおり）
    ],
)
def test_print_chara_list_relation(ctx, data, bits, text):
    st = ctx.state
    st.flag[799] = 2
    st.target = 2
    o = st.charas[3]
    o.base[40] = st.charas[2].base[40] = 20
    st.charas[2].cflag[240], o.cflag[240] = 5, 1  # キャラ 2 は年下 → 親子なら相手は 母親
    rel = 0
    for b in bits:
        rel |= 1 << b
    assert P._relation_text(ctx, rel, 3) == text


def test_print_chara_list_format(ctx, data):
    """:936–945 `[n] (♀) 名前(24 桁)　関係(24 桁)`。"""
    st = ctx.state
    st.flag[799] = 2
    P.print_chara_list(ctx, [3])
    o = st.charas[3]
    line = texts(ctx.out)[0]
    assert line.startswith(f"[3] (♀) {o.callname}")
    assert line.endswith("　" + " " * 24)


# --- ACT_LIMIT（COMMON_BATTLE_FUNC.ERB:226–255）--------------------------------------------------


@pytest.mark.parametrize(
    "kyousei, roll, result",
    [
        (0, 5, 1),  # RAND:100 = 5 < 6
        (0, 6, 0),
        (0, 102, 1),  # RAND:100 = 2
        (1, 5, 1),  # 共生：RAND:200（:228–230）
        (1, 102, 0),  # RAND:200 = 102
    ],
)
def test_act_limit_parasite(ctx, data, svc, kyousei, roll, result):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    _parasitize(data, c, kyousei)
    c.mark.clear()
    ctx = Ctx(st, data, TextOutput(), svc)
    st.rng = ZeroTail([roll])
    assert act_limit(ctx) == result
    if result:
        out = texts(ctx.out)
        assert f"{c.callname}の様子がおかしい・・・" in out
        assert f"{c.callname}は体内に寄生する触手が不意に暴れだそうとして" in out


# --- _ABLUP 寄生ふたなり（ABL_UP_CHECK.ERB:407–422）--------------------------------------------


@pytest.mark.parametrize(
    "futa, henshin, emit_abl, emit_exp, c39, after, msg",
    [
        (2, 0, 5, 0, 0, (4, 0), "神経の奥深くまで寄生ふたなりが癒着してしまい"),  # :408–414 定着
        (0, 2, 5, 0, 0, (0, 4), "神経の奥深くまで寄生ふたなりが癒着してしまい"),
        (2, 0, 0, 13, 3, (0, 0), "精液を出しきり、萎び落ちていった・・・"),  # :416–422 13 - 3 ≥ 10
        (2, 0, 0, 12, 3, (2, 0), None),
        (2, 0, 5, 20, 0, (4, 0), "神経の奥深くまで寄生ふたなりが癒着してしまい"),  # 定着後は 4 なので消失しない
    ],
)
def test_ablup_parasite_futanari(ctx, data, svc, futa, henshin, emit_abl, emit_exp, c39, after, msg):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.talent[T(data, "ふたなり")] = futa
    c.talent[T(data, "変身時ふたなり")] = henshin
    c.abl[A(data, "射精中毒")] = emit_abl
    c.exp[E(data, "射精経験")] = emit_exp
    c.cflag[39] = c39
    ctx = Ctx(st, data, TextOutput(), svc)
    ablup(ctx, 1)
    assert (c.talent[T(data, "ふたなり")], c.talent[T(data, "変身時ふたなり")]) == after
    out = texts(ctx.out)
    if msg:
        assert msg in out
    else:
        assert not any("寄生ふたなり" in x or "萎び落ち" in x for x in out)


# --- Web（session）：@EVENTSHOP の INPUT ---------------------------------------------------------


def test_session_eventshop_input(data):
    """@EVENTSHOP（SHOP_TURNEND.ERB:161）の共生取得 INPUT を Phase.TURN で受け、終了後にオートセーブ → SHOP。"""
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(1))
    s.input(0)
    s.input(1)
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    st = s.state
    c = st.charas[2]
    _parasitize(data, c)
    c.cflag[82] = 49
    st.time = 1
    st.rng = ZeroTail([])
    s.begin_shop(called_when_normal=True)
    assert s.phase == Phase.TURN
    s.input(0)
    assert s.phase == Phase.SHOP
    assert c.talent[T(data, "共生")] == 1
    assert (Path(s.save_dir) / "save99.json").exists()


def test_tokusou_act_limit_parasite_no_longer_halts(data, svc, monkeypatch):
    """S16 模擬で唯一停止した経路（初期セット seed 101：PRISON_COM301 で寄生されたキャラが救出後の戦闘で
    寄生の行動制限 COMMON_BATTLE_FUNC.ERB:226–255 を引く）。S18 で乱数の消費が変わり seed 101 では到達しなくなったので、
    開局直後にキャラ 1〜3 へ 寄生 を付けて同じ経路を通す（S20 で襲撃／救援が起きるようになり乱数の消費が変わったので seed 6）。
    停止せず SHOP 上限まで進む。"""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import sim
    from eragvt.game.battle import core, func

    hits = []
    orig = core.run_chinobun

    def rc(ctx, fn, *a, **k):
        if fn == "MESSAGE_BATTLE_DISACTION_PARASITE":
            hits.append(ctx.state.target)
        return orig(ctx, fn, *a, **k)

    monkeypatch.setattr(func, "run_chinobun", rc)
    def setup(st):
        for i in (1, 2, 3):
            _parasitize(data, st.charas[i])

    r = sim.run_one(data, svc, 6, "tokusou", 30, 100000, Path(tempfile.mkdtemp()), setup=setup)
    assert r["reason"] == "上限"
    assert hits
