"""S23：[反撃]スタイル（反撃準備・ＥＸ反撃・HANGEKI_TO_TENTACLE・完全防御文）。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`、行號は各テストの docstring）。実装の出力から逆算しない。
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, print_transcallname
from eragvt.game.battle import commands, enemy, hangeki
from eragvt.game.battle.core import BETOBETO, KIZETU, P_EX_HANGEKI, P_GUARD, P_HANGEKI, P_NORMAL
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

HEADER = "********** 自分の行動 **********"  # HANGEKI_STYLE.ERB:61


class ZeroRng(FixedRng):
    """RAND は常に 0。"""

    def __init__(self) -> None:
        super().__init__([])

    def rand(self, n: int) -> int:
        return 0


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(Path(default_csv_dir()).parent / "ERB", data)


def _ctx(data, narration):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # TARGET=1（紅葉：変身能力 1）
    s.savestr[13] = "BOSS"
    s.flag[110] = 0
    s.flag[10] = 0  # ボス戦
    s.flag[11] = 3
    s.flag[12] = s.flag[13] = 100000
    c = s.charas[1]
    c.cflag[1] = 1
    c.tcvarn[0] = 2
    c.cdflag[(2, data.index_of("CDFLAG2", "戦闘スタイル"))] = 10  # [反撃]（FIGHT_STYLE.ERB:30–31）
    return Ctx(s, data, TextOutput(), narration)


@pytest.fixture
def ctx(data):
    return _ctx(data, NullNarrationService())


@pytest.fixture
def cctx(data, svc):
    return _ctx(data, svc)


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def run_gen(gen):
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT 待ちになった")


# --- HANGEKI_STYLE.ERB@HANGEKI_TO_TENTACLE:9–52 の成否 -------------------------------------------


@pytest.mark.parametrize(
    "arg, arg1, v200, air, f11, ok",
    [
        (1, 0, 0, False, 7, True),  # :27–30 攻撃：被弾しても成功
        (1, 1, 0, False, 7, True),
        (2, 0, 0, False, 7, False),  # :33–34 絡みつく：被弾時は失敗
        (2, 1, 0, False, 7, True),
        (3, 0, 0, False, 7, False),  # :38–39 体液
        (3, 0, 1, False, 7, True),  # :19–20 完全防御は条件を飛ばす
        (3, 1, 0, False, 7, True),
        (4, 0, 0, False, 7, False),  # :41–42 距離をとる：確定失敗
        (4, 0, 1, False, 7, True),  # （完全防御なら :19 で SKIP）
        (5, 0, 0, False, 7, False),  # :45–46 押し倒す
        (5, 1, 0, False, 7, True),
        (6, 0, 0, False, 7, False),  # :50–51 波動
        (6, 0, 1, False, 7, True),
        (6, 1, 0, False, 7, True),
        (1, 2, 0, False, 7, False),  # :9–13 範囲外回避：地上なら失敗
        (1, 2, 1, False, 7, False),  # （:9 は完全防御の SKIP より前）
        (1, 2, 0, True, 2, True),  # 空中で自分の距離（中）が攻撃範囲内＝エアストライク回避
        (1, 2, 0, True, 5, False),  # 空中でも範囲外（近・遠）なら失敗
    ],
)
def test_hangeki_conditions(ctx, arg, arg1, v200, air, f11, ok):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[2] = P_HANGEKI
    v[200] = v200
    v[205] = 10
    v.set_bit(216, 1, air)
    st.tflag[11] = f11
    st.tflag[10] = arg
    ex0 = c.ex[99]
    assert hangeki.hangeki_to_tentacle(ctx, arg, arg1, 77) == 0
    if ok:
        assert v[205] == 87  # :67 TCVARn:205 += ARG:2
        assert c.ex[99] == ex0 + 2  # :91
        assert HEADER in texts(ctx.out)
        # :70 COM_ATTACK_COMMON の末尾（COM_ATTACK_COMMON.ERB:419–425）で再び 体勢：反撃
        assert v[2] == P_HANGEKI
    else:
        assert v[205] == 10 and c.ex[99] == ex0 and v[2] == P_HANGEKI
        assert texts(ctx.out) == []


def test_hangeki_sets_ex_hangeki_during_attack(ctx, monkeypatch):
    """:56 反撃成功で TCVARn:2 = 体勢：ＥＸ反撃（301）にしてから COM_ATTACK_COMMON を呼ぶ（体勢：反撃成功 302 ではない）。"""
    seen = []
    monkeypatch.setattr(commands, "com_attack_common", lambda ctx: seen.append(ctx.state.charas[1].tcvarn[2]) or 1)
    ctx.state.charas[1].tcvarn[2] = P_HANGEKI
    hangeki.hangeki_to_tentacle(ctx, 1, 0, 0)
    assert seen == [P_EX_HANGEKI]
    assert ctx.state.charas[1].tcvarn[2] == P_EX_HANGEKI


@pytest.mark.parametrize(
    "henshin, exp_name",
    [(1, "中距離戦闘経験"), (-1, "戦闘基礎経験")],  # :73–88（TCVARn:0 = 2）
)
def test_hangeki_exp(ctx, data, henshin, exp_name):
    st = ctx.state
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "変身能力")] = henshin
    for n in ("中距離戦闘経験", "戦闘基礎経験"):
        c.exp[data.index_of("EXP", n)] = 0
    st.rng = ZeroRng()
    hangeki.hangeki_to_tentacle(ctx, 1, 0, 0)
    assert c.exp[data.index_of("EXP", exp_name)] == 1  # RAND:5 + 1
    other = "戦闘基礎経験" if exp_name == "中距離戦闘経験" else "中距離戦闘経験"
    assert c.exp[data.index_of("EXP", other)] == 0


@pytest.mark.parametrize(
    "v200, tflag10, cured",
    [(1, 1, True), (0, 1, False), (1, 4, False)],  # :94 べとべと && 完全防御 && 距離をとる以外
)
def test_hangeki_betobeto(ctx, v200, tflag10, cured):
    st = ctx.state
    v = st.charas[1].tcvarn
    v[2] = P_EX_HANGEKI
    v[12] |= BETOBETO
    v[200] = v200
    st.tflag[10] = tflag10
    hangeki.hangeki_to_tentacle(ctx, 1, 1, 0)
    assert bool(v[12] & BETOBETO) is (not cured)
    name = print_transcallname(st, 1)
    assert (f"　 {name}は[べとべと]状態から回復した！" in texts(ctx.out)) is cured


# --- COMF4.ERB@COM4:24–30（[反撃]スタイルの防御＝ＥＸ反撃） ---------------------------------------


def test_com4_hangeki_style(cctx):
    st = cctx.state
    c = st.charas[1]
    ex0 = c.ex[99]
    assert run_gen(commands.run_com(cctx, 4)) == 1
    assert c.tcvarn[2] == P_EX_HANGEKI
    assert c.ex[99] == ex0 + 1  # :42
    name = print_transcallname(st, 1)
    # MESSAGE_BATTLE.ERB:586–590（catalog）
    assert f"{name}はその場で姿勢を取り、神経をとがらせて次の攻撃を待った・・・" in texts(cctx.out)


def test_com4_other_style_is_guard(cctx, data):
    c = cctx.state.charas[1]
    c.cdflag[(2, data.index_of("CDFLAG2", "戦闘スタイル"))] = 0
    run_gen(commands.run_com(cctx, 4))
    assert c.tcvarn[2] == P_GUARD


# --- COM_ATTACK_COMMON.ERB:417–426（通常反撃準備） ------------------------------------------------


@pytest.mark.parametrize(
    "style, burst, expected",
    [(10, False, P_HANGEKI), (10, True, P_NORMAL), (0, False, P_NORMAL)],
)
def test_attack_common_hangeki_ready(cctx, data, style, burst, expected):
    st = cctx.state
    c = st.charas[1]
    c.cdflag[(2, data.index_of("CDFLAG2", "戦闘スタイル"))] = style
    c.tcvarn[2] = P_NORMAL
    c.tcvarn.set_bit(217, 0, burst)
    c.tcvarn[206] = 10**6  # 過剰蓄積なし
    commands.com_attack_common(cctx)
    assert c.tcvarn[2] == expected
    name = print_transcallname(st, 1)
    line = f"{name}は素早く相手の攻撃を跳ね返す用意を整えた！"  # MESSAGE_BATTLE.ERB:578
    assert (line in texts(cctx.out)) is (expected == P_HANGEKI)


# --- MESSAGE_BATTLE.ERB:1201–1223 完全防御文（[反撃]スタイルは PRINTDATAL） ------------------------


@pytest.mark.parametrize(
    "r, text",
    [
        (0, "は攻撃を完全に封じ込めた後, すぐに敵のすき間に向かって進んだ！"),  # :1207
        (1, "はすべての攻撃をかわし, その勢いで反撃に乗り出した！"),  # :1208
    ],
)
def test_perfect_guard_hangeki_printdata(ctx, r, text):
    st = ctx.state
    st.rng = FixedRng([r])
    enemy.msg_perfect_guard(ctx)
    lines = texts(ctx.out)
    assert lines[0] == "PERFECT GUARD!"
    assert lines[1] == print_transcallname(st, 1) + text


# --- ENEMY_ACTION.ERB:933–934 の呼び出しと引数（ARG = TFLAG:10、ARG:1 = LOCAL:0、ARG:2 = LOCAL:2） ----


@pytest.fixture
def recorded(monkeypatch):
    calls = []
    monkeypatch.setattr(enemy, "hangeki_to_tentacle", lambda ctx, a, b, d: calls.append((a, b, d)) or 0)
    return calls


@pytest.mark.parametrize(
    "posture, kizetu, called",
    [
        (P_HANGEKI, False, True),
        (P_HANGEKI, True, False),  # `!(気絶) && 反撃 || ＥＸ反撃`（&&・|| 同順位・左結合）
        (P_EX_HANGEKI, True, True),
        (P_GUARD, False, False),
    ],
)
def test_enemy_action_hangeki_call(ctx, recorded, monkeypatch, posture, kizetu, called):
    st = ctx.state
    v = st.charas[1].tcvarn
    v[2] = posture
    if kizetu:
        v[12] |= KIZETU
    st.tflag[10] = 1
    st.tflag[16] = -1
    st.tflag[11] = 7
    st.tflag[12] = 1
    monkeypatch.setattr(enemy, "act_hantei_tentacle_to_chara", lambda ctx, kind: 1)
    run_gen(enemy._enemy_action_once(ctx))
    assert (recorded != []) is called
    if called:
        assert recorded[0][:2] == (1, 1) and recorded[0][2] == 0  # 回避：LOCAL:2 は VARSET LOCAL の 0
    assert v[200] == 0  # :937


def _number_before(lines, suffix):
    for ln in lines:
        if ln.endswith(suffix):
            return int(ln[: -len(suffix)])
    raise AssertionError(suffix)


@pytest.mark.parametrize(
    "action, suffix",
    [
        (1, "のダメージを蓄積した！"),  # :181–182（[反撃]スタイル：LOCAL:2 を表示、完全防御なので減算されない）
        (3, "のダメージが無効化された！"),  # :512–513（体液：完全防御 RAND:100 < 15）
        (6, "のダメージが無効化された！"),  # :880–881（波動：完全防御 RAND:100 < 10）
    ],
)
def test_enemy_action_hangeki_arg2_perfect_guard(ctx, recorded, monkeypatch, action, suffix):
    """ＥＸ反撃中の被弾 → 完全防御（:87 確定、:429／:794 は RAND）→ ARG:2 は表示された LOCAL:2。"""
    st = ctx.state
    v = st.charas[1].tcvarn
    v[2] = P_EX_HANGEKI
    st.tflag[10] = action
    st.tflag[16] = -1
    st.tflag[11] = 7
    st.tflag[12] = 1
    st.rng = ZeroRng()
    monkeypatch.setattr(enemy, "act_hantei_tentacle_to_chara", lambda ctx, kind: 0)
    hp0 = st.charas[1].base[0]
    run_gen(enemy._enemy_action_once(ctx))
    l2 = _number_before(texts(ctx.out), suffix)
    assert recorded == [(action, 0, l2)]
    assert st.charas[1].base[0] == hp0  # 完全防御：体力は減らない


def test_enemy_action_taieki_arg2_hit(ctx, recorded, monkeypatch):
    """:446–525 体液の被弾（反撃中、完全防御 RAND:100 < 7 不成立）：ARG:2 = 実際に減った体力（LOCAL:2）。"""
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[2] = P_HANGEKI
    st.tflag[10] = 3
    st.tflag[16] = -1
    st.tflag[11] = 7
    st.tflag[12] = 1
    st.rng = GameRng(5)
    monkeypatch.setattr(enemy, "act_hantei_tentacle_to_chara", lambda ctx, kind: 0)
    orig = st.rng.rand
    first = []

    def rand(n):
        if not first and n == 100:  # :429 `TCVARn:2 == 体勢：反撃 && RAND:100 < 7` → 99 で不成立
            first.append(n)
            return 99
        return orig(n)

    st.rng.rand = rand
    hp0 = c.base[0]
    run_gen(enemy._enemy_action_once(ctx))
    assert recorded == [(3, 0, hp0 - c.base[0])]


# --- 統合：[反撃]スタイルのキャラがボス戦を最後まで戦う ------------------------------------------------


def test_hangeki_style_boss_battle_integration(data, monkeypatch):
    """初期セット＋全員の全距離を [反撃]（人工的な状態）にし、全員出撃を続けてボス戦を数回こなす：
    停止せず、反撃（HANGEKI_TO_TENTACLE の成功）が起きること。"""
    successes = []
    orig = enemy.hangeki_to_tentacle

    def wrapped(ctx, a, b, d):
        ex0 = ctx.state.target_chara.ex[99]
        r = orig(ctx, a, b, d)
        if ctx.state.target_chara.ex[99] >= ex0 + 2:
            successes.append((a, b, d))
        return r

    monkeypatch.setattr(enemy, "hangeki_to_tentacle", wrapped)
    style = data.index_of("CDFLAG2", "戦闘スタイル")
    with tempfile.TemporaryDirectory() as tmp:
        s = GameSession(data, Path(tmp), rng=GameRng(3), narration=NullNarrationService())
        s.input(0)
        s.input(1)
        s.input(1)  # HEROINE_PRESET [1] 基本セット
        for i in range(1, s.state.charanum):
            for dist in (1, 2, 3):
                s.state.charas[i].cdflag[(dist, style)] = 10
        policy = random.Random(3)
        shops = 0
        for _ in range(20000):
            assert s.phase != Phase.HALTED, [ln.text for ln in s.out.lines[-5:]]
            if s.phase == Phase.SHOP:
                shops += 1
                if shops > 6:
                    break
                for i in range(1, s.state.charanum):
                    s.input(i)
                    s.input(101)  # 出撃する
                s.input(100)
                if s.phase == Phase.ACTION_CONFIRM:
                    s.input(9)  # はい（次から確認しない）：SHOP.ERB の SELECTCASE は CASE 9 のみ
                continue
            # S25：[800] ステータス画面（表示のみ）は除外して S23 と同じ戦闘経路を保つ
            buttons = [v for ln in s.out.lines[-40:] for (_, v) in ln.buttons if v != 800]
            s.input(policy.choice(buttons) if buttons else 0)
    assert shops > 6
    assert successes
