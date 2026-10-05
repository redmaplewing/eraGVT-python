"""S18：強制発生イベント（クズ市民の脅迫・夜這い・深夜の子触手襲来）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/ゲーム内_イベント発生/強制発生イベント/`、行號は註解：
KYOU = FORCE_クズ市民の脅迫.ERB、YOBAI = FORCE_夜這い.ERB、SMALL = FORCE_深夜の子触手襲来.ERB）。実装の出力から逆算しない。
乱数：FixedRng（`值 % n`、使い切ると例外）、ZeroTail（使い切ったら 0）、ByN（上限 n ごとの値の列、無ければ n-1 または既定値）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import intimidation as I
from eragvt.game import shop
from eragvt.game import small_tentacle as S
from eragvt.game import yobai as Y
from eragvt.game.action import Ctx, print_transcallname
from eragvt.game.relation import KOIBITO
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.state.savefile import load_from_file
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    """初期セット『特装戦隊』（CHARANUM = 4、キャラ 1〜3：女性・処女・編成中）、夜（TIME = 1）、防衛力 5000。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.time = 1
    return Ctx(s, data, TextOutput(), NullNarrationService())


class ZeroTail(FixedRng):
    def rand(self, n: int) -> int:
        if not self._values:
            return 0
        return super().rand(n)


class ByN(GameRng):
    """rand(n) は n ごとに用意した値を順に返し、無ければ default（None なら n-1）。"""

    def __init__(self, table: dict[int, list[int]] | None = None, default: int | None = None) -> None:
        super().__init__(0)
        self.table = {k: list(v) for k, v in (table or {}).items()}
        self.default = default
        self.calls: list[int] = []

    def rand(self, n: int) -> int:
        if n <= 0:
            raise ValueError(n)
        self.calls.append(n)
        q = self.table.get(n)
        if q:
            return q.pop(0) % n
        return (n - 1) if self.default is None else self.default % n


def T(data, n):
    return data.index_of("TALENT", n)


def A(data, n):
    return data.index_of("ABL", n)


def E(data, n):
    return data.index_of("EXP", n)


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def drive(gen, inputs=()):
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            gen.send(inputs.pop(0))
    except StopIteration as e:
        return e.value


def gen_recorder(store: list, value=0):
    def fake(*args, **kwargs):
        store.append(args[1:])
        return value
        yield  # pragma: no cover

    return fake


# =====================================================================================================
# 深夜の子触手襲来（SMALL）
# =====================================================================================================


def test_small_hantei_conditions_without_rand(ctx):
    st = ctx.state
    st.rng = FixedRng([])
    st.flag[44] = 0
    list(S.small_tentacle_hantei(ctx))  # :37–38 育児済みの子触手（FLAG:44 − CFLAG:220 合計）< 1
    st.flag[44] = 2
    st.charas[1].cflag[220] = 2
    list(S.small_tentacle_hantei(ctx))
    st.charas[1].cflag[220] = 0
    st.time = 0
    list(S.small_tentacle_hantei(ctx))  # :29–30
    assert texts(ctx.out) == []


@pytest.mark.parametrize(
    "f44, f852, rolls, attack",
    [
        (1, 5000, [0, 1], True),  # :45 5000 < 5000 + 50 → RAND:8 = 0、:56 RAND:12 = 1 != 0
        (1, 5000, [0, 0, 10], True),  # :56 RAND:12 = 0 → :59 RAND:20 == 10（最低 5%）
        (1, 5000, [1, 3, 0], False),  # LOCAL:2 != 0、RAND:20 != 10、:63 RAND:1 = 0 < 9
        (1, 1500, [0, 1], True),  # :43 1500 < 2500 + 50 → RAND:4
        (1, 20050, [0, 1], True),  # :53 ELSE → RAND:128
    ],
)
def test_small_hantei_rolls(ctx, monkeypatch, f44, f852, rolls, attack):
    st = ctx.state
    st.flag[44], st.flag[852] = f44, f852
    st.rng = FixedRng(rolls)
    called: list = []
    monkeypatch.setattr(S, "small_tentacle_attack", gen_recorder(called))
    st.target = 2
    list(S.small_tentacle_hantei(ctx))
    assert bool(called) == attack
    assert st.target == 2  # :39／:76 TARGET を戻す
    assert st.flag[44] == f44


@pytest.mark.parametrize(
    "f52, rolls, line",
    [
        (0, [1, 0, 9, 0], "子触手は何かの動物に襲われた..."),  # :63 RAND:10 ≥ 9、:68 RAND:2 = 0
        (0, [1, 0, 9, 1], "子触手は迷子になった..."),
        (1, [1, 0, 9, 0], "子触手は防衛システムに引っかかって黒焦げにされた..."),  # :66 FLAG:52 && (RAND:1 != 0 || LOCAL:2 != 0)
    ],
)
def test_small_hantei_decrease(ctx, f52, rolls, line):
    st = ctx.state
    st.flag[44], st.flag[52] = 10, f52
    # 5000 < 5000 + 10*50 → RAND:8（FLAG:52 = 1 でも防衛力の閾値は同じ）。:56 RAND:(12 - FLAG:52*2)
    st.rng = FixedRng(rolls)
    list(S.small_tentacle_hantei(ctx))
    assert st.flag[44] == 9
    assert texts(ctx.out)[-1] == line


def test_small_attack_failed(ctx):
    st = ctx.state
    st.flag[44] = 3
    st.rng = FixedRng([24])  # :86 RAND:100 < 25 → 見つかって処分
    list(S.small_tentacle_attack(ctx))
    assert st.flag[44] == 2
    assert "〈地の文：MESSAGE_SMALL_ATTACK_FAILED〉" in texts(ctx.out)


def test_small_attack_target_selection(ctx, monkeypatch):
    st = ctx.state
    st.charas[1].cflag[0] = 1  # :103 CFLAG:0 != 0 → 再抽選
    st.rng = FixedRng([25, 0, 1])  # :99 RAND:3 + 1 → 1（不可）→ 2
    called: list = []
    monkeypatch.setattr(S, "small_prison_event", gen_recorder(called))
    st.target = 3
    list(S.small_tentacle_attack(ctx))
    assert called == [()]
    assert st.target == 2  # :108（呼び出し元 HANTEI が :76 で戻す）


def test_small_attack_success_decrements_ruling(ctx, monkeypatch):
    """DEVIATION（使用者裁決 2026-10-01）：襲来成功（:108–109）でも FLAG:44 を 1 減らす（失敗 :88／:95 と同じ減法）。
    原作は成功時に減らさない。"""
    st = ctx.state
    st.flag[44] = 3
    st.rng = FixedRng([25, 1])  # :86 RAND:100 = 25（≥ 25）→ :99 RAND:3 + 1 = 2
    called: list = []
    monkeypatch.setattr(S, "small_prison_event", gen_recorder(called))
    list(S.small_tentacle_attack(ctx))
    assert called == [()]
    assert st.flag[44] == 2


def test_small_attack_lost_after_99_tries(ctx, monkeypatch):
    st = ctx.state
    st.flag[44] = 1
    for i in (1, 2, 3):
        st.charas[i].cflag[999] = 0
    st.rng = ByN({100: [50]}, default=0)  # :82 RAND:100 = 50 ≥ 25
    called: list = []
    monkeypatch.setattr(S, "small_prison_event", gen_recorder(called))
    list(S.small_tentacle_attack(ctx))
    assert called == []
    assert st.rng.calls == [100] + [3] * 99  # :93 LOCAL:1 >= 99 で中断
    assert st.flag[44] == 0
    assert "子触手は迷子になった..." in texts(ctx.out)


@pytest.mark.parametrize(
    "setup, rolls, kind",
    [
        ({}, [2], 2),  # :128 RAND:7（処女・ふたなりなし・母乳なし → 追加の RAND なし）
        ({"処女": -1}, [2, 0], 1),  # :133 処女 < 1 && RAND:11 == 0 → Ｖ
        ({"処女": -1}, [2, 1], 2),
        ({"母乳体質": 1}, [0, 0], 3),  # :136
        ({"ふたなり": 1}, [5, 0], 0),  # :130
        ({"オトコ": 1}, [1], 0),  # :143–146 男で Ｖ → ISMANLY → Ｃ
        ({"オトコ": 1, "男の娘": 1}, [1], 2),  # :147–149 男の娘 → Ａ
        ({"処女": 2}, [1, 4], 4),  # :158 聖処女は Ｖ 以外になるまで繰り返す
    ],
)
def test_small_prison_event_kind(ctx, data, monkeypatch, setup, rolls, kind):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    for k, v in setup.items():
        c.talent[T(data, k)] = v
    st.rng = FixedRng(rolls)
    called: list = []
    monkeypatch.setattr(S, "small_prison_com", gen_recorder(called))
    list(S.small_prison_event(ctx))
    assert called == [(kind,)]
    out = texts(ctx.out)
    assert "〈地の文：MESSAGE_SMALL_ATTACK〉" in out and "〈地の文：MESSAGE_SMALL_ATTACK_SUCCESS〉" in out


def test_small_prison_event_female_c_to_v_when_futanari_off(ctx, monkeypatch):
    st = ctx.state
    st.target = 1
    st.flag[850] |= 1 << 1  # CONFIG_CHECK_MANIAC_F(1) == 0（ふたなり×）
    st.rng = FixedRng([0])
    called: list = []
    monkeypatch.setattr(S, "small_prison_com", gen_recorder(called))
    list(S.small_prison_event(ctx))
    assert called == [(1,)]  # :139–140


@pytest.fixture
def com_stubs(monkeypatch):
    """SMALL_PRISON_COM の下位（COMMON_PRISON 等）を記録に置き換える。"""
    from eragvt.game.battle import ablup, ninsin, sexcom
    from eragvt.game import body
    from eragvt.game.prison import commands

    rec = {"prison": [], "exp": {}, "ablup": [], "pill": [], "ninsin": [], "profile": 0, "est": []}
    monkeypatch.setattr(commands, "common_prison", lambda ctx, args, arg12=0: rec["prison"].append((list(args), arg12)))
    monkeypatch.setattr(commands, "common_prison_exp", lambda ctx, cc, v: rec["exp"].__setitem__(cc, v) if v else None)
    monkeypatch.setattr(ablup, "ablup", lambda ctx, arg: rec["ablup"].append(arg))
    monkeypatch.setattr(sexcom, "palam_vabc_estimate", lambda ctx, L, *p: rec["est"].append(p))

    def pill(ctx, who, a1, a2):
        rec["pill"].append((who, a1, a2))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(ninsin, "after_pill", pill)
    monkeypatch.setattr(ninsin, "ninsin_hantei", lambda ctx, a, b, c=0: rec["ninsin"].append((a, b, c)))

    def prof(data, c, result=None):
        rec["profile"] += 1

    monkeypatch.setattr(body, "set_profile", prof)
    return rec


def _L(values: dict[int, int]) -> list[int]:
    L = [0] * 12
    for k, v in values.items():
        L[k] = v
    return L


@pytest.mark.parametrize(
    "kind, abl, tal, base, rolls, L, exp, after_tal",
    [
        # Ｃ：Ｃ感覚 2 → 200（:179）。女・ふたなりなし・Ｃ結界なし → 寄生ふたなり（:201–205）
        (0, {"Ｃ感覚": 2}, {}, {}, [], {0: 200}, {}, {"ふたなり": 2, "変身時ふたなり": 2}),
        (0, {"Ｃ感覚": 2}, {"ふたなり": 1}, {}, [], {0: 600}, {153: 5}, {"ふたなり": 1}),  # :206–210
        (0, {"Ｃ感覚": 9}, {}, {30: 100}, [], {0: 1200}, {}, {"ふたなり": 0}),  # :185 ELSE、:197 結界あり
        # Ｖ：処女 → :251–255（LOCAL:120 = 1、苦痛 500）、Ｖ感覚 0 → 10（×3 しない）
        (1, {}, {}, {}, [3], {1: 10, 10: 500}, {120: 1}, {"処女": -1}),
        (1, {"Ｖ感覚": 3}, {"処女": -1}, {}, [2, 5, 1], {1: 300}, {120: 6, 123: 20, 124: 2}, {}),  # :241–257
        (1, {"Ｖ感覚": 3}, {}, {31: 5}, [], {1: 100}, {}, {"処女": 1}),  # :237 Ｖ結界
        (2, {"Ａ感覚": 1}, {}, {}, [0, 0], {2: 50}, {121: 4, 123: 15}, {}),  # :273、:296–299
        (3, {}, {}, {}, [4], {3: 6}, {123: 9}, {"母乳体質": 1}),  # :331、:336–337
        (3, {"Ｂ感覚": 4}, {"母乳体質": 1, "巨乳": 5}, {}, [0], {3: 2700}, {123: 5, 154: 5}, {}),  # :339 巨乳 < 5 不成立 → :357
        (4, {}, {}, {}, [0, 0], {8: 50, 10: 5000, 11: 1000}, {123: 30, 124: 5, 132: 1}, {}),  # :369–419
        (4, {"従順": 3, "マゾっ気": 3}, {}, {}, [1, 1], {8: 500, 10: 5000, 11: 100}, {123: 31, 124: 6, 132: 8}, {}),
        (5, {"技巧": 5, "奉仕精神": 5}, {}, {}, [0, 0], {5: 1200, 6: 4200, 8: 100}, {123: 10, 124: 5, 131: 1}, {}),
        (6, {"露出癖": 2}, {}, {}, [0], {7: 200, 9: 500}, {123: 5, 130: 5, 140: 5}, {}),  # :530 POWER 2^2 + 1
    ],
)
def test_small_prison_com(ctx, data, com_stubs, kind, abl, tal, base, rolls, L, exp, after_tal):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    for k, v in abl.items():
        c.abl[A(data, k)] = v
    for k, v in tal.items():
        c.talent[T(data, k)] = v
    for k, v in base.items():
        c.base[k] = v
    c.exp[E(data, "射精経験")] = 7
    st.rng = FixedRng(rolls)
    list(S.small_prison_com(ctx, kind))
    assert com_stubs["prison"] == [(_L(L), 0)]  # :546（ARG:12 省略）
    assert com_stubs["exp"] == exp
    assert com_stubs["ablup"] == [1]  # :556
    for k, v in after_tal.items():
        assert c.talent[T(data, k)] == v, k
    if kind == 0 and after_tal.get("ふたなり") == 2:
        assert c.cflag[39] == 7  # :205 CFLAG:39 = EXP:射精経験
    if kind == 1 and not base:
        assert com_stubs["pill"] == [(1, 35, 200)]  # :261（処女喪失直後も :259 処女 < 1 が成立）
        assert com_stubs["ninsin"] == [(exp.get(123, 0), 30, 200)]
        if "処女" not in tal:
            assert c.cflag[206] == 1  # :253


def test_small_prison_com_bust_up(ctx, data, com_stubs):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.talent[T(data, "母乳体質")] = 1
    c.talent[T(data, "巨乳")] = 1
    st.rng = FixedRng([0])
    list(S.small_prison_com(ctx, 3))
    # :339 CONFIG_CHECK_MANIAC_F(18) == 1（既定）かつ 巨乳 < 2 → :343 1 + 0 > 5 でも (F(19)==0 && …) でもない
    assert c.talent[T(data, "巨乳")] == 2  # :352
    assert c.talent[T(data, "変身時胸サイズ変動")] == 0
    assert (c.cflag[37], c.cflag[38]) == (1, 0)  # :354
    assert com_stubs["profile"] == 1  # :356 SET_PROFILE


def test_small_prison_com_real_integration(ctx, data):
    """下位を置き換えずに Ａ襲来を 1 回（COMMON_PRISON → 経験 → _ABLUP）。"""
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    st.rng = ZeroTail([])
    list(S.small_prison_com(ctx, 2))
    assert c.exp[E(data, "Ａ経験")] == 4  # :296 4 + RAND:5
    assert c.exp[E(data, "精液経験")] == 15  # :299
    assert "Ａ経験：＋4" in texts(ctx.out)


# =====================================================================================================
# クズ市民の脅迫（KYOU）
# =====================================================================================================


@pytest.fixture
def gb(monkeypatch):
    from eragvt.game.battle import rape

    calls: list = []

    def fake(ctx, situation, sao, nakadashi):
        calls.append((situation, sao, nakadashi))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(rape, "calc_gangbang", fake)
    return calls


@pytest.mark.parametrize(
    "setup",
    [
        lambda st: setattr(st, "time", 0),  # :9
        lambda st: st.charas[1].cflag.__setitem__(72, 1),  # :13 クールダウン
        lambda st: st.flag.__setitem__(802, st.flag[802] & ~8),  # :15 CONFIG_CHECK_EVENT_F(3)
        lambda st: st.flag.__setitem__(852, 5001),  # :19
        lambda st: st.charas[1].cflag.__setitem__(286, 0),  # :23
    ],
)
def test_intimidation_conditions(ctx, gb, setup):
    st = ctx.state
    st.target = 1
    st.charas[1].cflag[286] = 30
    setup(st)
    st.rng = FixedRng([])  # 乱数を引かない
    assert drive(I.intimidation_event(ctx)) == 0
    assert gb == [] and texts(ctx.out) == []


@pytest.mark.parametrize("roll, happens", [(7, False), (6, True)])
def test_intimidation_probability(ctx, data, gb, roll, happens):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[286], c.cflag[284], c.cflag[290] = 2, 1, 1
    c.talent[T(data, "巻き込まれ体質")] = 1
    # :27–52 LOCAL = 2 + 1 + 1*2 + 1 = 6、:54 LOCAL < RAND:30 なら発生しない
    st.rng = ZeroTail([roll])
    drive(I.intimidation_event(ctx))
    assert bool(gb) == happens
    assert c.cflag[290] == (2 if happens else 1)


def test_intimidation_first_time_kidnapped(ctx, data, gb):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[286] = 30
    st.rng = ZeroTail([])
    drive(I.intimidation_event(ctx))
    out = texts(ctx.out)
    name = print_transcallname(st, 1)
    assert f"クズ市民の脅迫:{name}" in out  # :60
    assert "夜――" in out  # :63–64 初回
    assert f"「エンジェル・ダスト」を嗅がされ意識を失った{name}は、男達に廃ビルの中へ担ぎ込まれてしまった…" in out
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 11  # :296–301
    assert c.cflag[290] == 1  # :352
    # :365 CHARANUM_ENSLAVED() == 0 && RAND:100 = 0 < 20 + 20 → 拉致監禁
    assert (c.cflag[0], c.cflag[71]) == (4, 30)
    assert "〈地の文：MESSAGE_CITIZEN_HIACED〉" in out
    assert gb == [("脅迫", 5, 2)]  # :385 NAKADASHI *= 2


def test_intimidation_normal_end(ctx, data, gb):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[286] = 30
    st.rng = ByN()  # すべて n-1：:54 30 < 29 は偽、:365 RAND:100 = 99 ≥ 40、:388 99 ≥ 36
    drive(I.intimidation_event(ctx))
    out = texts(ctx.out)
    assert c.cflag[0] == 0 and c.cflag[290] == 1
    assert "「次も頼むわ」という呪いの言葉と共に、嘲笑だけを残して去っていく男達。" in out
    assert gb == [("脅迫", 5, 1)]


def test_intimidation_willing_slave(ctx, data, gb):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[286], c.cflag[290] = 30, 1
    c.talent[T(data, "淫乱")] = 1
    st.rng = ByN({100: [99, 0]})  # :365 RAND:100 = 99 → :388 RAND:100 = 0 < 36、淫乱
    drive(I.intimidation_event(ctx))
    assert (c.cflag[0], c.cflag[71], c.cflag[290]) == (4, 40, 2)
    assert "日が落ちる頃に、" + c.callname + "を脅迫している男から再び呼び出しの電話がかかってきた。" in texts(ctx.out)
    assert gb == [("脅迫", 5, 1)]  # :423 の分岐は NAKADASHI を 2 倍にしない


def test_intimidation_no_second_slave(ctx, data, gb):
    st = ctx.state
    st.target = 1
    st.charas[1].cflag[286] = 30
    st.charas[2].cflag[0] = 4  # CHARANUM_ENSLAVED() = 1
    st.rng = ZeroTail([])
    drive(I.intimidation_event(ctx))
    assert st.charas[1].cflag[0] == 0
    assert gb == [("脅迫", 5, 1)]


@pytest.fixture
def rescued(monkeypatch):
    from eragvt.game import party

    calls: list = []
    monkeypatch.setattr(party, "after_rescued", lambda ctx, who: calls.append(who))
    return calls


def test_kidnapping_rescue(ctx, gb, rescued):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[0], c.cflag[71], c.cflag[290] = 4, 0, 3
    st.rng = FixedRng([])
    drive(I.kidnapping(ctx))
    assert (c.cflag[0], c.cflag[71], c.cflag[72], c.cflag[290]) == (-1, 0, 8, 0)  # :518–521
    assert rescued == [1] and gb == []
    assert "拉致監禁・救出" in texts(ctx.out)


@pytest.mark.parametrize(
    "c70, roll, release",
    [
        (7, 1, True),  # :523 RAND:10 < 2 + MIN(2, 0)
        (7, 2, False),
        (10, 3, True),  # 2 + MIN(2, 4/2) = 4
        (10, 4, False),
        (6, None, False),  # CFLAG:70 > 6 でなければ RAND:10 を引かない
    ],
)
def test_kidnapping_release_or_continue(ctx, data, gb, rescued, c70, roll, release):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[0], c.cflag[71], c.cflag[70] = 4, 30, c70
    st.rng = ZeroTail([] if roll is None else [roll])
    drive(I.kidnapping(ctx))
    out = texts(ctx.out)
    assert gb == [("監禁", 5, 2)]  # :629／:786
    if release:
        assert (c.cflag[0], c.cflag[70], c.cflag[72]) == (-1, 0, 8)
        assert rescued == [1]
        assert "拉致監禁・廃棄" in out
    else:
        assert c.cflag[0] == 4 and rescued == []
        assert f"拉致監禁：{print_transcallname(st, 1)}" in out
        # :656 RAND(35)、:719 PRINTDATA RAND:5、:670 RAND(20,40) = 20 + RAND:20 → 50 + 20 + 0
        assert c.juel[data.index_of("JUEL", "修練P")] == 70
        assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 12  # :711–712 INTIMIDATION_RAPE の処女喪失


# =====================================================================================================
# 夜這い（YOBAI）
# =====================================================================================================


@pytest.mark.parametrize(
    "abl, tal, threshold",
    [
        ({"Ｃ感覚": 3}, {}, 3000),  # :53–56 (1*2 + 22) * 125
        ({"Ｃ感覚": 3}, {"交際相手": 2}, 1500),  # :57–58 TIMES 0.5
        ({"Ｃ感覚": 3}, {"清純派": 1}, 1500),
        ({"Ｃ感覚": 3}, {"人間不信": 1}, 750),
        ({"Ｃ感覚": 3}, {"淫乱": 1}, 3500),  # LOCAL:1 = 2 + 1
        ({"Ｃ感覚": 3, "欲望": 2}, {}, 3480),  # (24) * (125 + 2*10)
        ({"Ｖ感覚": 3, "Ｂ感覚": 3}, {}, 3250),  # LOCAL:1 = 2 → 26 * 125
    ],
)
def test_yobai_candidate_probability(ctx, data, monkeypatch, abl, tal, threshold):
    st = ctx.state
    c = st.charas[1]
    for k, v in abl.items():
        c.abl[A(data, k)] = v
    for k, v in tal.items():
        c.talent[T(data, k)] = v
    called: list = []

    def fake(ctx):
        called.append(ctx.state.target)
        return 999
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "yobai_event", fake)
    st.rng = FixedRng([threshold - 1, 0])  # :68 RAND:10000 < LOCAL、:77 RANDCHOOSE_F = RAND:1
    list(Y.yobai(ctx))
    assert called == [1]
    called.clear()
    st.rng = FixedRng([threshold])
    list(Y.yobai(ctx))
    assert called == []


def test_yobai_reroll(ctx, data, monkeypatch):
    st = ctx.state
    for i in (1, 2):
        st.charas[i].abl[A(data, "Ｃ感覚")] = 3
    results = [-999, 0]
    called: list = []

    def fake(ctx):
        called.append(ctx.state.target)
        return results.pop(0)
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "yobai_event", fake)
    # 候補 1, 2 → RAND:2 = 0 → 1（-999）→ :80 CLEARSPECIFICCHOOSE → RAND:1 = 0 → 2
    st.rng = FixedRng([0, 0, 0, 0])
    list(Y.yobai(ctx))
    assert called == [1, 2]


def test_yobai_skips_non_safe_and_day(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.abl[A(data, "Ｃ感覚")] = 3
    c.cflag[0] = 1  # :50 生存していない（幽閉）キャラは判定しない
    st.rng = FixedRng([])
    list(Y.yobai(ctx))
    c.cflag[0] = 0
    st.time = 0  # :11
    list(Y.yobai(ctx))


def test_yobai_event_breast_only_ruling(ctx, data):
    """DEVIATION（使用者裁決 2026-10-01）：YOBAI_EVENT の淫乳条件（:160–177）を `TALENT:淫乳 * 3 + ABL:Ｂ感覚` にした。
    Ｂ感覚だけ 3 のキャラは YOBAI の候補（:48）であり、YOBAI_EVENT も成立して対象選択の INPUT（:504）まで進む。
    （原作の `+ ABL:Ｃ感覚` では全組み合わせが 0 → RETURN -999（:225–226）だった。）"""
    st = ctx.state
    st.target = 1
    st.charas[1].abl[A(data, "Ｂ感覚")] = 3
    st.rng = ZeroTail([])
    gen = Y.yobai_event(ctx)
    next(gen)  # -999 で StopIteration にならない
    assert "（夜這い対象選択）" in texts(ctx.out)


def test_yobai_event_list_and_input(ctx, data, monkeypatch):
    st = ctx.state
    st.target = 1
    st.charas[1].abl[A(data, "Ｃ感覚")] = 3
    called: list = []

    def fake(ctx, arg, arg1=0):
        called.append((ctx.state.flag[799], arg, arg1))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "yobai_action", fake)
    st.rng = ZeroTail([])
    gen = Y.yobai_event(ctx)
    next(gen)  # :504 INPUT
    out = texts(ctx.out)
    assert "（夜這い対象選択）" in out
    assert "紅葉は眠れぬ夜を過ごしている・・・" in out
    rows = [x for x in out if x.startswith("[")]
    # :578–584 Ｃ系のみ → GFLAG:100+n = 1。対象は 2・3（MASTER・本人を除く）
    assert [r[:4] for r in rows] == ["[2] ", "[3] ", "[999"]
    assert rows[0].startswith("[2] (♀) 桃香")
    gen.send(5)  # :524
    assert texts(ctx.out)[-1] == "正しい値を入力してください"
    with pytest.raises(StopIteration) as e:
        gen.send(3)
    assert e.value.value == 0
    assert called == [(3, 1, 0)]  # :508–513 FLAG:799 = 3、YOBAI_ACTION, GFLAG:103
    assert all(st.charas[i].cflag[1] == 0 for i in range(4))  # :629–634 変身解除


@pytest.fixture
def act(monkeypatch):
    """YOBAI_ACTION の COMMON_PRISON・_ABLUP・NINSIN・AFTER_PILL を記録に置き換える。"""
    rec: list = []
    monkeypatch.setattr(Y, "_prison", lambda ctx, L: rec.append(("prison", ctx.state.target, {i: v for i, v in enumerate(L[:200]) if v})))
    monkeypatch.setattr(Y, "_ablup1", lambda ctx: rec.append(("ablup", ctx.state.target)))
    monkeypatch.setattr(Y, "_ninsin", lambda ctx, l123, father: rec.append(("ninsin", ctx.state.target, l123, father)))

    def pill(ctx, who, father):
        rec.append(("pill", who, father))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "_after_pill", pill)
    return rec


def _male_partner(st, data, who=2, desire=4):
    c = st.charas[who]
    c.talent[T(data, "オトコ")] = 1
    c.abl[A(data, "欲望")] = desire
    st.flag[799] = who


V_LOST_EXEC = {1: 50, 10: 50, 120: 2, 122: 1, 123: 1}  # YOBAI:1573–1583
TARGET_C = {0: 50, 122: 1, 153: 1}  # :1610–1619


def test_yobai_action_v_virgin(ctx, data, act):
    st = ctx.state
    st.target = 1
    _male_partner(st, data)
    st.rng = ByN()  # n-1：:667 0 > 29 偽、:672 99 < 20 偽 → 通常。:1372 欲望 4 < 2 + 2 偽 → :1437 処女
    drive(Y.yobai_action(ctx, 2))
    c = st.charas[1]
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 6  # :1588–1594（恋人でない）
    assert act == [
        ("prison", 1, V_LOST_EXEC), ("ablup", 1),
        ("prison", 2, TARGET_C), ("ablup", 2),
        ("ablup", 2),  # :2645
    ]
    out = texts(ctx.out)
    assert "夜這い（紅葉）→（桃香）" in out
    assert "処女喪失" in out
    assert "【夜這い対象：桃香】" in out


def test_yobai_action_c_goto_v_lostvirgin(ctx, data, act):
    """CASE 1 スマタから :1195 GOTO V_LOSTVERGIN_SEX → CASE 2 の :1518 以降を実行して ENDSELECT へ。"""
    st = ctx.state
    st.target = 1
    _male_partner(st, data)
    st.rng = ByN()  # :987 4 < 4 偽 → :1066 相手が男 → :1171 4 + RAND:4(3) ≥ 6
    drive(Y.yobai_action(ctx, 1))
    assert act[0] == ("prison", 1, V_LOST_EXEC)
    assert st.charas[1].talent[T(data, "処女")] == -1
    assert "つぅと破瓜の血が流れ出す・・・" in texts(ctx.out)
    assert [x[0] for x in act] == ["prison", "ablup", "prison", "ablup", "ablup"]


def test_yobai_action_sumata_no_insert(ctx, data, act):
    st = ctx.state
    st.target = 1
    _male_partner(st, data, desire=4)
    st.rng = ByN({4: [0]})  # :1171 4 + 0 < 6 → 挿入なし（:1218–）
    drive(Y.yobai_action(ctx, 1))
    assert act[0] == ("prison", 1, {0: 50, 122: 1})  # :1239、:1268（LCOUNT = 0）
    assert act[2] == ("prison", 2, TARGET_C)
    assert st.charas[1].talent[T(data, "処女")] == 1


def test_yobai_action_executor_falls_asleep(ctx, data, act):
    st = ctx.state
    st.target = 1
    _male_partner(st, data)
    st.charas[1].cflag[99] = 40
    st.rng = ByN()  # :925 40 > RAND:30(29)
    drive(Y.yobai_action(ctx, 2))
    assert act == []  # :949 RETURN（:2645 _ABLUP も無し）
    assert any("そのまま寝入ってしまった。" in x for x in texts(ctx.out))


def test_yobai_action_lover_nakadashi(ctx, data, act):
    st = ctx.state
    st.target = 1
    _male_partner(st, data)
    st.charas[1].talent[T(data, "処女")] = -1
    st.charas[2].relation[1] = 1 << KOIBITO  # LOVER_F(FLAG:799, TARGET)
    st.rng = ByN()
    drive(Y.yobai_action(ctx, 2))
    out = texts(ctx.out)
    assert "「これは性交ではなく、仲間の悩みに応えているだけ」" in out  # :1664 LOVER_F(TARGET, FLAG:799) は 0
    father = -st.charas[2].cflag[240] - 100
    assert act == [
        ("prison", 1, {1: 50, 120: 2, 122: 1, 123: 1}), ("ablup", 1),
        ("ninsin", 1, 1, 2),  # :1750–1751
        ("prison", 2, TARGET_C), ("ablup", 2),
        ("pill", 1, 2),  # :1774–1776 AFTER_PILL, LCOUNT, 75, CFLAG:(TARGET):240 * -1 - 100
        ("ablup", 2),
    ]
    assert father == -102


def test_yobai_action_married_virgin_callname_bug(ctx, data, act):
    st = ctx.state
    st.target = 1
    _male_partner(st, data)
    c = st.charas[1]
    c.talent[800] = 4  # 交際相手 = 人妻
    c.talent[T(data, "淫乱")] = 1
    st.rng = ByN()
    drive(Y.yobai_action(ctx, 2))
    # :1450 %CALLNAME:ARG%（ARG = 2）と %CALLNAME:MASTER%
    assert f"ずぷ、と、{st.charas[2].callname}の膣内へと{st.charas[0].callname}の一物が挿入された。" in texts(ctx.out)


def test_yobai_houshi_4_virgin(ctx, data, act):
    st = ctx.state
    st.target = 1
    st.flag[799] = 2
    st.charas[1].talent[T(data, "淫乱")] = 1
    st.rng = ByN()
    drive(Y.yobai_houshi_4(ctx, 0, 0, 0))
    t2 = st.charas[2]
    assert t2.talent[T(data, "処女")] == -1  # :3086（TARGET = 対象）
    # DEVIATION（使用者裁決 2026-10-01）：処女を失った対象（FLAG:799 = 2）の CFLAG:206 に書く（原作 :3088–3092 は LCOUNT = 1）
    assert t2.cflag[206] == 6 and st.charas[1].cflag[206] == 0
    assert act == [
        ("prison", 1, {0: 100, 122: 1, 153: 2}), ("ablup", 1),
        ("prison", 2, {1: 100, 10: 50, 120: 2, 122: 1, 123: 2}),
        ("ninsin", 2, 2, 1),  # :3100–3101 TALENT:LCOUNT:淫乱
        ("ablup", 2),
        ("pill", 2, 1),  # :3103–3105 NAKADASHI（:3021）
    ]


def test_yobai_houshi_4_fellatio_ruling(ctx, data, act):
    """DEVIATION（使用者裁決 2026-10-01）：:3177 で LOCAL:324 = 1（口内射精）。原作は :3226 VARSET LOCAL の後の
    :3237 `LOCAL:124 = LOCAL:324` が 0 になるが、VARSET 前の値を保持してフェラ経験 +1（:1738／:2063 と同じ）。"""
    st = ctx.state
    st.target = 1
    st.flag[799] = 2
    st.charas[2].talent[T(data, "処女")] = -1
    st.rng = ByN()
    drive(Y.yobai_houshi_4(ctx, 0, 0, 0))
    assert act[2] == ("prison", 2, {1: 100, 120: 2, 122: 1, 123: 2, 124: 1})
    assert ("pill", 2, 1) not in act


def test_yobai_houshi_5_fellatio_ruling(ctx, data, act):
    """DEVIATION（使用者裁決 2026-10-01）：HOUSHI_5 の Ａ感覚 2 以上・淫乱／恋人でない分岐（:3562 LOCAL:324 = 1）。
    原作 :3622 `LOCAL:124 = LOCAL:324` は VARSET LOCAL 後で 0 → VARSET 前の値を使いフェラ経験 +1。"""
    st = ctx.state
    st.target = 1
    st.flag[799] = 2
    st.charas[2].talent[T(data, "男の娘")] = 1
    st.charas[2].abl[A(data, "Ａ感覚")] = 2
    st.rng = ByN()
    Y.yobai_houshi_5(ctx, 0, 0, 0)
    assert act[2] == ("prison", 2, {2: 100, 121: 2, 122: 1, 123: 2, 124: 1})


def test_yobai_houshi_1_hand(ctx, data, act):
    st = ctx.state
    st.target = 1
    st.flag[799] = 2
    st.rng = ByN()
    Y.yobai_houshi_1(ctx, 0, 0, 0)
    assert act == [
        ("prison", 1, {0: 100, 122: 1, 153: 2}), ("ablup", 1),
        ("prison", 2, {123: 2}), ("ablup", 2),
    ]


# =====================================================================================================
# 整合（Web session・存讀檔）
# =====================================================================================================


def _new_session(data, rng):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(1))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』
    s.input(1000)  # CHARA_MAKE_MAIN 完成
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    s.state.rng = rng
    return s


def _turn_all_rest(s, answers=(), limit=200):
    """全員休憩で 1 ターン。INPUT には answers を順に、尽きたら 0 を送る。"""
    answers = list(answers)
    for i in range(1, s.state.charanum):
        s.input(i)
        s.input(103)  # 休憩
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)  # はい（次から確認しない）：[1] は原作どおり中断（shop.action_confirm_answer）
    n = 0
    while s.phase != Phase.SHOP:
        assert s.phase != Phase.HALTED, s.out.lines[-1].text
        s.input(answers.pop(0) if answers else 0)
        n += 1
        assert n < limit


def test_session_intimidation_and_save(data):
    s = _new_session(data, ZeroTail([]))
    st = s.state
    st.flag[804] |= 1 << 10  # CONFIG_CHECK_PRISON_F(10)：クズ市民による幽閉
    st.time = 1
    c = st.charas[1]
    c.cflag[286] = 30
    _turn_all_rest(s)
    assert c.cflag[290] == 1 and c.cflag[0] == 4  # 脅迫 → 拉致監禁（ZeroTail：:365 RAND:100 = 0）
    assert c.cflag[70] == 0  # CALC_GANGBANG "脅迫" は CFLAG:286 を +1（:108）
    assert c.cflag[286] == 31
    loaded, _ = load_from_file(Path(s.save_dir) / "save99.json")
    assert (loaded.charas[1].cflag[0], loaded.charas[1].cflag[71], loaded.charas[1].cflag[290]) == (4, 30, 1)
    # 次のターン：昼でも KIDNAPPING（SHOP_TURNEND.ERB:97–100）→ 監禁継続（CFLAG:70 は CALC_GANGBANG "監禁" で +1）
    _turn_all_rest(s)
    assert c.cflag[0] == 4 and c.cflag[70] == 1


def test_session_yobai(data):
    s = _new_session(data, ZeroTail([]))
    st = s.state
    st.time = 1
    c = st.charas[1]
    c.abl[A(data, "Ｃ感覚")] = 3
    _turn_all_rest(s, answers=[2])  # YOBAI_EVENT の相手選択 [2]
    out = [ln.text for ln in s.out.lines]
    assert "（夜這い対象選択）" in out and "夜這い（紅葉）→（桃香）" in out and "【夜這い対象：桃香】" in out
    # ZeroTail：:987 欲望 0 < 2 + RAND:3 → 愛撫（:1039–1041 快C 50・絶頂経験 1）
    assert c.exp[E(data, "絶頂経験")] == 1
    loaded, _ = load_from_file(Path(s.save_dir) / "save99.json")
    assert loaded.charas[1].exp[E(data, "絶頂経験")] == c.exp[E(data, "絶頂経験")]


def test_session_small_tentacle(data):
    # :56 RAND:12 = 1、SMALL_TENTACLE_ATTACK :82 RAND:100 = 50、:99 RAND:3 = 0 → キャラ 1、:128 RAND:7 = 0 → Ｃ襲来
    s = _new_session(data, ByN({12: [1], 100: [50]}, default=0))
    st = s.state
    st.time = 1
    st.flag[44] = 1
    s.begin_shop(called_when_normal=True)
    assert s.phase == Phase.SHOP
    c = st.charas[1]
    assert c.talent[T(data, "ふたなり")] == 2  # :201–205 寄生ふたなり
    loaded, _ = load_from_file(Path(s.save_dir) / "save99.json")
    assert loaded.charas[1].talent[T(data, "ふたなり")] == 2


# --- 網羅（全 CASE・導入・奉仕の分岐を例外なく通ること。状態の期待値は上の個別テスト）--------------------------
# 1 ケースごとに新しい状態を作り、内部でループする（テスト数を水増ししない）。

_EXEC = {
    "female": {},
    "lewd_married": {"淫乱": 1, 800: 4},
    "otokonoko": {"オトコ": 1, "男の娘": 1, "処女": 0},
    "futa": {"ふたなり": 1, "処女": -1},
    "male": {"オトコ": 1, "処女": 0},
    "ts_female": {"変身時ＴＳ": 1, "性別変化": 1},
    "immature_boy": {"オトコ": 1, "処女": 0, "未熟": 1},
}
_PARTNER = {
    "female": {},
    "male": {"オトコ": 1, "処女": 0},
    "otokonoko": {"オトコ": 1, "男の娘": 1, "処女": 0, "変身時男の娘": -1},
    "nonvirgin": {"処女": -1, "巨乳": 1, "母乳体質": 1},
    "holy": {"処女": 2, "ふたなり": 1, "未熟": 1},
    "immature_boy": {"オトコ": 1, "処女": 0, "未熟": 1, "変身時ＴＳ": 1},
}
# 対象の欲望（:746／:852／:899）・自慰（:672 SELF）・熟睡（:667）・近親（:749）・恋人・実行者の疲労（:922–973）・変身
_VARIANTS = {
    "zero": {},
    "max": {"rng": "max"},
    "desire0": {"desire": 0},
    "desire3": {"desire": 3, "rng": "max"},
    "desire5": {"desire": 5, "rng": "max"},
    "self": {"self": True},
    "asleep": {"asleep": True},
    "incest_old": {"incest": "old", "desire": 1, "rng": "max"},
    "incest_young": {"incest": "young", "desire": 1, "rng": "max"},
    "incest_young_t": {"incest": "young", "desire": 1, "transformed": True},
    "self_max": {"self": True, "rng": "max", "desire": 4},
    "anal": {"anal": True, "rng": "one"},
    "anal_lover": {"anal": True, "lover": True, "desire": 5},
    "lover": {"lover": True, "rng": "max"},
    "tired": {"tired": 3, "rng": "max"},
    "tired_asleep": {"tired": 40, "asleep": True, "rng": "max"},
    "transformed": {"transformed": True},
}


def _fresh(data) -> Ctx:
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.time = 1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def _setup_pair(data, ctx, ex, pa, v):
    from eragvt.game.relation import OYAKO

    st = ctx.state
    st.target, st.flag[799] = 1, 2
    me, f = st.charas[1], st.charas[2]
    for k, val in _EXEC[ex].items():
        me.talent[k if isinstance(k, int) else T(data, k)] = val
    for k, val in _PARTNER[pa].items():
        f.talent[T(data, k)] = val
    f.abl[A(data, "欲望")] = v.get("desire", 3)
    f.abl[A(data, "精液中毒")] = 5
    f.abl[A(data, "自慰中毒")] = 5 if v.get("self") else 0
    f.abl[A(data, "Ａ感覚")] = 3 if v.get("anal") else 0
    me.abl[A(data, "Ａ感覚")] = 2
    me.talent[T(data, "淫尻")] = me.talent[T(data, "淫壷")] = 1
    if v.get("asleep"):
        f.cflag[99] = 100
    if v.get("incest"):
        me.relation[2] = f.relation[1] = 1 << OYAKO
        me.base[40], f.base[40] = (40, 10) if v["incest"] == "old" else (10, 40)
    if v.get("lover"):
        me.relation[2] = f.relation[1] = 1 << KOIBITO
    me.cflag[99] = v.get("tired", 0)
    if v.get("transformed"):
        me.cflag[1] = f.cflag[1] = 1
    st.rng = {"max": ByN(), "one": ByN(default=1)}.get(v.get("rng", ""), ByN(default=0))


def _run_action(ctx, arg, arg1):
    try:
        drive(Y.yobai_action(ctx, arg, arg1))
    except NotImplementedError as e:  # :1450／:1796 %CALLNAME:ARG%（ARG = 4、CHARANUM = 4）は原作でもエラー
        assert arg == 4 and "CALLNAME:4" in str(e)


@pytest.mark.parametrize("variant", list(_VARIANTS))
def test_yobai_action_all_paths_run(data, monkeypatch, variant):
    v = _VARIANTS[variant]
    for arg in (1, 2, 4, 8, 16, 32):
        for ex in _EXEC:
            for pa in _PARTNER:
                for arg1 in (0, 1):
                    ctx = _fresh(data)
                    rec: list = []
                    monkeypatch.setattr(Y, "_prison", lambda ctx, L: rec.append("p"))
                    monkeypatch.setattr(Y, "_ablup1", lambda ctx: rec.append("a"))
                    monkeypatch.setattr(Y, "_ninsin", lambda *a: rec.append("n"))
                    monkeypatch.setattr(Y, "_after_pill", gen_recorder(rec))
                    _setup_pair(data, ctx, ex, pa, v)
                    _run_action(ctx, arg, arg1)
                    assert rec == [] or rec[-1] == "a" or isinstance(rec[-1], tuple)


@pytest.mark.parametrize("houshi", [1, 2, 3, 4, 5])
def test_yobai_houshi_all_paths_run(data, monkeypatch, houshi):
    for suimin in (0, 1):
        for ex in _EXEC:
            for pa in _PARTNER:
                for variant in ("zero", "max", "lover", "transformed", "incest_old", "anal", "anal_lover", "self_max"):
                    ctx = _fresh(data)
                    monkeypatch.setattr(Y, "_prison", lambda ctx, L: None)
                    monkeypatch.setattr(Y, "_ablup1", lambda ctx: None)
                    monkeypatch.setattr(Y, "_ninsin", lambda *a: None)
                    monkeypatch.setattr(Y, "_after_pill", gen_recorder([]))
                    _setup_pair(data, ctx, ex, pa, _VARIANTS[variant])
                    r = getattr(Y, f"yobai_houshi_{houshi}")(ctx, suimin, 0, 1 if ex == "ts_female" else 0)
                    if r is not None:
                        drive(r)
                    assert ctx.state.target == 2  # 対象側の処理で TARGET = FLAG:799


def test_yobai_event_ts_prompt_executor_only(ctx, data, monkeypatch):
    """実行者が変身しないと対象がいない（:251–276）：オトコ・変身時ＴＳ・女体受容、Ｃ感覚 0 でも Ｖ感覚 3。"""
    st = ctx.state
    st.target = 1
    me = st.charas[1]
    for k in ("オトコ", "変身時ＴＳ", "女体受容"):
        me.talent[T(data, k)] = 1
    me.talent[T(data, "処女")] = 0
    me.abl[A(data, "Ｖ感覚")] = 3
    called: list = []

    def fake(ctx, arg, arg1=0):
        called.append((ctx.state.flag[799], arg, arg1, ctx.state.target_chara.cflag[1]))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "yobai_action", fake)
    st.rng = ZeroTail([])
    gen = Y.yobai_event(ctx)
    next(gen)
    name = print_transcallname(st, 1)
    assert f"{name}は変身で女体化できます。変身した状態で夜這いを行いますか？" in texts(ctx.out)
    assert texts(ctx.out)[-1] == " [0]はい　[1]夜這いを行わずに終了する"
    gen.send(7)  # :271 GOTO INPUT_LOOP_0_0（メッセージなし）
    gen.send(0)  # :261–264 変身
    assert me.cflag[1] == 1
    with pytest.raises(StopIteration):
        gen.send(2)
    # :510–511 CFLAG:1 > 0 → GFLAG:300+2。SELECT_PLAY, 10（:533–534 実行者を変身＝女体化）で使えるのは
    # :586–595 Ｖ系のみ（淫壷 0・Ｖ感覚 3、ISFEMALE、相手は女性で ×2 なし）→ 値 2
    assert called == [(2, 2, 0, 1)]


def test_yobai_event_ts_prompt_decline(ctx, data):
    st = ctx.state
    st.target = 1
    me = st.charas[1]
    for k in ("オトコ", "変身時ＴＳ", "女体受容"):
        me.talent[T(data, k)] = 1
    me.talent[T(data, "処女")] = 0
    me.abl[A(data, "Ｖ感覚")] = 3
    st.rng = ZeroTail([])
    gen = Y.yobai_event(ctx)
    next(gen)
    with pytest.raises(StopIteration) as e:
        gen.send(1)
    assert e.value.value == -1  # :265–269
    assert texts(ctx.out)[-2:] == ["夜這いを終了します。", ""]  # :266–267 PRINTFORML ／ PRINTW（空）


def test_yobai_event_ts_prompt_optional(ctx, data, monkeypatch):
    """対象は変身なしでも居る（:278–303）：女性・変身時ＴＳ → 「男性化できます」、[1] で変身せずに続行。"""
    st = ctx.state
    st.target = 1
    me = st.charas[1]
    me.talent[T(data, "変身時ＴＳ")] = 1
    me.abl[A(data, "Ｃ感覚")] = 3
    called: list = []

    def fake(ctx, arg, arg1=0):
        called.append((ctx.state.flag[799], arg, arg1))
        return 0
        yield  # pragma: no cover

    monkeypatch.setattr(Y, "yobai_action", fake)
    st.rng = ZeroTail([])
    gen = Y.yobai_event(ctx)
    next(gen)
    name = print_transcallname(st, 1)
    assert f"{name}は変身で男性化できます。変身した状態で夜這いを行いますか？" in texts(ctx.out)
    gen.send(1)
    assert texts(ctx.out)[-1] != "変身せずにそのまま夜這いを行います。"  # 一覧の表示が続く
    assert "変身せずにそのまま夜這いを行います。" in texts(ctx.out)
    with pytest.raises(StopIteration):
        gen.send(3)
    assert called == [(3, 1, 0)]


_KYOU_TAL = {
    "plain": {},
    "male": {"オトコ": 1, "処女": 0},
    "holy": {"処女": 2},
    "lewd": {"淫乱": 1, "マゾ気質": 1, "主観視点": 1, "交際相手": 3},
    "timid": {"臆病": 1, "交際相手": 1, "主観視点": 1},
    "nonvirgin": {"処女": -1, "貧乳": 1, "四肢欠損": 1},
}


@pytest.mark.parametrize("tal", list(_KYOU_TAL))
def test_intimidation_and_kidnapping_all_paths_run(data, monkeypatch, tal):
    from eragvt.game import party
    from eragvt.game.battle import rape

    monkeypatch.setattr(rape, "calc_gangbang", gen_recorder([]))
    monkeypatch.setattr(party, "after_rescued", lambda ctx, who: None)
    for rng in (lambda: ZeroTail([]), lambda: ByN(), lambda: ByN(default=1), lambda: ByN({100: [99, 0]})):
        for c290 in (0, 1, 3, 7):
            for desire in (0, 3):
                ctx = _fresh(data)
                st = ctx.state
                st.target = 1
                c = st.charas[1]
                for k, v in _KYOU_TAL[tal].items():
                    c.talent[T(data, k)] = v
                c.cflag[286], c.cflag[284], c.cflag[290] = 30, 1, c290
                c.abl[A(data, "欲望")] = c.abl[A(data, "従順")] = desire
                st.rng = rng()
                drive(I.intimidation_event(ctx))
                assert c.cflag[290] == c290 + 1
                c.cflag[0], c.cflag[70], c.cflag[71] = 4, c290 + 5, c290 % 2 * 30
                drive(I.kidnapping(ctx))
