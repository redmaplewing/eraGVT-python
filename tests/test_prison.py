"""S08：幽閉（`eragvt.game.prison`／`party`／`tattoo`／`ending`）。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號は註解）、引擎の語意は
`reference/emuera-1824/Emuera/` の行號を附す。実装の出力から逆算しない。
他の関数（S05／S06 で移植・テスト済みの SEIKAKU_HOSEI_PALAM_F・PERCENT_CAL・TENTACLE_LEVEL 等）の値は入力として使う。
PRISON.ERB = `ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB`。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import party, shop, turnend
from eragvt.game.action import Ctx
from eragvt.game.battle import source_check
from eragvt.game.battle.core import seikaku_hosei_palam, set_local
from eragvt.game.battle.restraint import kyushutu_success
from eragvt.game.chara_common import seikaku_check
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.prison import commands, event
from eragvt.game.prison.event_palam import got_event_sex_mark_check
from eragvt.game.session import GameSession, Phase
from eragvt.game.tattoo import PROG_UNIT, save_tattoo, tattoo_access, tattoo_lv_cal, tattoo_position
from eragvt.narration.hooks import PRISON_HOOK_LINES
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # TARGET=1（紅葉）
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def ti(data, name):
    return data.index_of("TALENT", name)


def ei(data, name):
    return data.index_of("EXP", name)


def imprison(st, who: int, boss: int = 1) -> None:
    """敗北直後の状態（BATTLE_COM_AFTER.ERB:1031–1034：CFLAG:0 = 1、CFLAG:20 = FLAG:10、CFLAG:21 = FLAG:11）。"""
    c = st.charas[who]
    c.cflag[0] = 1
    c.cflag[20] = 0
    c.cflag[21] = boss


# --- SET_PARTYMEMBER.ERB@SHIFTBACK_CHARA:32–44／@SET_PARTYMEMBER:1–28 ----------------------------


@pytest.mark.parametrize("arg", [1, 2, 3, 4])
def test_shiftback_chara(ctx, data, arg):
    st = ctx.state
    st.add_chara(data, 301)  # 4 人目（CHARANUM = 5）
    for i, c in enumerate(st.charas):
        for k in range(5):
            c.relation[k] = 10 * i + k
    before = list(st.charas)
    rel_before = [[c.relation[k] for k in range(5)] for c in before]
    st.target = 2
    party.shiftback_chara(ctx, arg)
    # :34 FOR LOCAL, ARG, CHARANUM - 1：LOCAL と LOCAL+1 を順に SWAPCHARA → ARG 番目が最後尾、以降は 1 つ前へ
    assert st.charas == before[:arg] + before[arg + 1 :] + [before[arg]]
    # :38–42 各キャラ（MASTER 除く）の RELATION:x:LOCAL ↔ :LOCAL+1 → 列 ARG 以降が左に 1 つ回転
    for i, c in enumerate(before):
        r = rel_before[i]
        exp = r if i == 0 else r[:arg] + r[arg + 1 :] + [r[arg]] if arg < 4 else r
        assert [c.relation[k] for k in range(5)] == exp, i
    # SWAPCHARA は TARGET を動かさない（VariableEvaluator.cs@SwapChara:1165–1174）
    assert st.target == 2


@pytest.mark.parametrize(
    "prisoned, expected_order, party_flags",
    [
        # :22–24 1 番が離脱 → 最後尾へ、CFLAG:999 = 0
        ((1,), (2, 3, 1), (1, 1, 0)),
        # 1・2 番が離脱：1 番を送った後 FOR は 2 に進むので、繰り上がった旧 2 番（位置 1）は判定されない（原作どおり）
        ((1, 2), (2, 3, 1), (1, 1, 0)),
        # :25–26 最後尾（CCOUNT == CHARANUM - 1）なら CFLAG:999 = 0 だけ
        ((3,), (1, 2, 3), (1, 1, 0)),
    ],
)
def test_set_partymember_shift(ctx, prisoned, expected_order, party_flags):
    st = ctx.state
    orig = list(st.charas)
    for i in prisoned:
        imprison(st, i)
    party.set_partymember(ctx)
    assert [orig.index(c) for c in st.charas[1:]] == list(expected_order)
    assert tuple(c.cflag[999] for c in st.charas[1:]) == party_flags


# --- PRISON.ERB@CHECK_CONTAMINATION:430–443 ------------------------------------------------------------


@pytest.mark.parametrize(
    "seitaisei, abls, naedoko, cfg3, flag904, expected",
    [
        (150, {}, 0, 0, 0, 260 + 30 * 4),  # :433 SQRT(90*10)=30
        (60, {}, 0, 0, 0, 260),
        (1000, {}, 0, 0, 0, 260 + 340),  # MIN(SQRT(9400)*4=384, 340)
        (150, {"触手中毒": 5, "従順": 5, "欲望": 5}, 0, 0, 0, 220),  # 380-80-40-40=220（下限 160 以上）
        (60, {"触手中毒": 5, "従順": 5}, 0, 0, 0, 160),  # 260-120=140 → :435–436 160
        (150, {}, 1, 1, 0, 380 + 80),  # :438–439
        (150, {}, 0, 0, 1, 380 * 3 // 4),  # :441–442
    ],
)
def test_check_contamination(ctx, data, seitaisei, abls, naedoko, cfg3, flag904, expected):
    st = ctx.state
    c = st.charas[1]
    c.base[data.index_of("BASE", "性耐性基礎")] = seitaisei
    for k, v in abls.items():
        c.abl[data.index_of("ABL", k)] = v
    c.talent[ti(data, "苗床化")] = naedoko
    st.flag.set_bit(804, 3, bool(cfg3))
    st.flag[904] = flag904
    assert event.check_contamination(ctx) == expected


# --- PRISON_COMABLE.ERB@PRISON_COMABLE:93–348 ------------------------------------------------------


@pytest.fixture
def calls(monkeypatch):
    rec = []
    for n in (0, 1, 2, 3, 4, 5, 6, 7, 100, 101, 102, 103, 104, 105, 200, 201, 300, 301):
        monkeypatch.setattr(commands, f"prison_com{n}", lambda ctx, n=n: rec.append(n))
    return rec


@pytest.mark.parametrize(
    "arg, setup, rng, expected",
    [
        (0, {}, [], 0),
        (1, {}, [], 1),
        (1, {"talent": {"男の娘": 1}}, [], 2),  # :136–137
        (1, {"talent": {"オトコ": 1}}, [], 0),  # :139–140 ISMALE
        (6, {"talent": {"感情乏しい": 1}}, [], 4),  # :162–163
        (6, {}, [], 6),
        (7, {}, [], 7),
        # :170–171 SHIELD:1 → GOTO SHIELDED（:99）：結界の無い部位（BASE:30〜33 < 1）から RAND:LCOUNT
        (7, {"shield": (0, 1, 0, 0), "base": (0, 500, 0, 0)}, [1], 2),
        # 全部位に結界 → :115 RAND:感覚数
        (7, {"shield": (0, 1, 0, 0), "base": (5, 5, 5, 5)}, [3], 3),
        (100, {}, [], 100),
        (100, {"maniac_off": 1}, [], 0),  # :190 CONFIG_CHECK_MANIAC_F(1) == 0
        (101, {}, [], 1),  # :216 Ｖ経験 < 20
        (101, {"exp": {"Ｖ経験": 20}}, [], 101),
        (101, {"talent": {"処女": 2}}, [], 5),  # :213 CHECK_HOLYVIRGIN_F
        (102, {"exp": {"Ａ経験": 19}}, [], 2),
        (102, {"exp": {"Ａ経験": 20}}, [], 102),
        (103, {}, [], 103),
        (104, {}, [], 1),  # :261–264 Ｖ感覚 < 5 && Ｖ拡張経験 < 10 → Ｖ経験 < 20
        (104, {"exp": {"Ｖ経験": 20}}, [], 101),
        (104, {"abl": {"Ｖ感覚": 5}}, [], 104),
        (200, {}, [], 101),  # :316–317 Ｖ拡張経験 <= 3
        (200, {"exp": {"Ｖ拡張経験": 4}}, [], 200),
        (200, {"talent": {"男の娘": 1}, "exp": {"Ａ拡張経験": 4}}, [], 201),
        (201, {}, [], 102),
        (201, {"exp": {"Ａ拡張経験": 4}}, [], 201),
        (300, {}, [], 300),
        (301, {}, [], 301),
        (301, {"talent": {"寄生": 1}}, [2], 300),  # :336–343 SELECTCASE RAND:3
    ],
)
def test_prison_comable(ctx, data, calls, arg, setup, rng, expected):
    st = ctx.state
    c = st.charas[1]
    for k, v in setup.get("talent", {}).items():
        c.talent[ti(data, k)] = v
    for k, v in setup.get("exp", {}).items():
        c.exp[ei(data, k)] = v
    for k, v in setup.get("abl", {}).items():
        c.abl[data.index_of("ABL", k)] = v
    for i, v in enumerate(setup.get("shield", (0, 0, 0, 0))):
        st.shield[i] = v
    for i, v in enumerate(setup.get("base", (0, 0, 0, 0))):
        c.base[30 + i] = v
    if setup.get("maniac_off"):
        st.flag.set_bit(850, 1, True)
    st.rng = FixedRng(list(rng))
    commands.prison_comable(ctx, arg)
    assert calls == [expected]


# --- PRISON.ERB@PRISON_EVENT:38–427 -----------------------------------------------------------------


@pytest.fixture
def comable(monkeypatch):
    rec = []
    monkeypatch.setattr(commands, "prison_comable", lambda ctx, arg: rec.append(arg))
    return rec


def test_prison_event_first(ctx, data, comable):
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1, boss=1)
    c.exp[ei(data, "幽閉経験")] = 1  # 敗北時に +1 済み（BATTLE_COM_AFTER.ERB:1090）
    c.base[31] = 300  # Ｖ結界だけ残っている
    st.flag[110] = 5
    st.rng = FixedRng([99, 50, 2])
    event.prison(ctx)
    t = texts(ctx.out)
    assert "Ｃ触手幽閉：紅葉" in t  # :43–44（NAME は改行なし）
    assert t.count("・・・・・・・・・") == 1  # PRISON:18–24
    # :116–117 TENTACLE_BOSS_1_PRISON_ROUTINE（RAND 99 ≥ 40 → 0）→ :122 RAND 50 → :141–142 Sな攻め（4）
    assert comable == [4]
    assert st.flag[110] == 0  # :49–51
    assert [st.shield[i] for i in range(4)] == [0, 1, 0, 0]  # :98–104
    assert c.exp[ei(data, "被姦経験")] == 1  # :164
    assert c.cflag[31] == 1  # :165
    assert c.cflag[30] == 3 + 2  # :167
    assert c.cflag[0] == 1


@pytest.mark.parametrize(
    "boss, rng, expected",
    [
        (1, [10, 0], 0),  # TENTACLE_BOSS_1_Ｃ触手.ERB:188–191
        (1, [35, 0], 100),
        (2, [35, 0], 101),  # TENTACLE_BOSS_2_Ｖ触手.ERB:197–199
        (2, [45, 0], 200),
        (2, [55, 0], 104),
        (2, [65, 90, 0], 300),  # 60 以上 → RETURN 0 → PRISON:152–154（89 ≤ 90 < 94）
        (3, [50, 0], 102),  # TENTACLE_BOSS_3_Ａ触手.ERB:204–206
        (3, [80, 10, 0], 4),  # :210–214 2 回目の RAND
        (3, [80, 90, 0], 301),
        (4, [45, 0], 105),
        (5, [35, 0], 300),
        (6, [32, 0], 101),  # 聖処女でない → :210–212
        (7, [37, 0], 201),
        (1, [99, 20, 0], 1),  # 汎用ルーチン :126–133（聖処女でない → V 中心）
        (1, [99, 99, 0], 301),
    ],
)
def test_prison_event_routine(ctx, data, comable, boss, rng, expected):
    st = ctx.state
    imprison(st, 1, boss=boss)
    st.charas[1].cflag[31] = 3
    st.rng = FixedRng(rng)
    event.prison_event(ctx)
    assert comable == [expected]


def test_prison_event_child_tentacle(ctx, comable):
    st = ctx.state
    imprison(st, 1)
    st.charas[1].cflag[31] = 3
    st.charas[1].cflag[220] = 2  # 出産した子触手
    st.rng = FixedRng([29, 0])  # :111 RAND:100 < 30
    event.prison_event(ctx)
    assert comable == [7]


def test_prison_event_brainwash(ctx, data, comable):
    """末路１（:335–388）：洗脳（触手の虜なし）。オプション CONFIG_CHECK_PRISON_F(1)（FLAG:804 bit1）を ON。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1)
    c.cflag[31] = 3
    c.cflag[30] = 1000  # > CHECK_CONTAMINATION 380
    c.cflag[23] = 5
    st.flag.set_bit(804, 1, True)
    st.rng = FixedRng([99, 0, 0, 7])  # ルーチン 0 → C 中心、汚染 +3、:378 RAND:25 = 7
    event.prison_event(ctx)
    assert c.cflag[0] == 2  # :341
    assert "紅葉は経験値を127％得た" in texts(ctx.out)  # :378 20 * (5 + Lv1) + 7
    assert c.cflag[23] == 0  # :386


def test_prison_event_corruption(ctx, data, comable):
    """末路１：触手の虜 → 悪堕ち（:348–364）。淫紋（:198–277）→ SAVE_TATTOO（CHARA_TATTOO.ERB:44–71）。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1)
    c.cflag[31] = 3
    c.cflag[30] = 1000
    c.talent[ti(data, "触手の虜")] = 1
    st.flag.set_bit(804, 1, True)
    # ルーチン 0、C 中心、汚染 RAND:4、SAVE_TATTOO の RAND:19 = 4、:380 RAND:50 = 0
    st.rng = FixedRng([99, 0, 0, 4, 0])
    event.prison_event(ctx)
    assert c.cflag[0] == 3
    assert c.exp[ei(data, "陥落経験")] == 1
    assert c.cflag[41] == 401  # :353–354 変身能力 == 1
    # PERCENT_CAL(1003, 380) = 263 → LIMIT 100、淫〜素質なし → TATTOO_POSITION（全感覚 0 → :21–22 で 1）
    assert c.cflag[32] == 100 * PROG_UNIT + (1 * (4 + 1) + 1) * 100**1
    assert "紅葉は経験値を240％得た" in texts(ctx.out)  # :380 40 * 6 + 0


def test_prison_event_lost(ctx, data, comable):
    """末路２（:397–424）：洗脳／悪堕ちオプション OFF（基本セット）で 20 回目の被姦 → 取り込まれ。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1)
    c.cflag[31] = 19
    st.rng = FixedRng([99, 0, 0])
    event.prison_event(ctx)
    assert c.cflag[31] == 20
    assert c.cflag[0] == 9
    assert c.talent[ti(data, "苗床化")] == 1
    # :408–411 CONFIG_CHECK_MANIAC_F(14)（FLAG:850 bit14 が 0 → 1）
    assert c.talent[ti(data, "四肢欠損")] == 1 and c.talent[ti(data, "繁殖袋")] == 1


def test_prison_event_escape(ctx, data, comable):
    """:295–327 サンドボックス（OPTION_ゲームオ－バー無し）で 5 日超 → RAND:4 == 0 で脱出 → AFTER_RESCUED。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1)
    c.cflag[999] = 0  # SET_PARTYMEMBER で外れている
    c.cflag[31] = 11
    c.cflag[30] = 50
    c.cflag[220] = 1
    st.flag.set_bit(0, 8, True)
    st.rng = FixedRng([99, 0, 0, 0])
    event.prison_event(ctx)
    t = texts(ctx.out)
    assert "最後の力を温存していた紅葉はこの機を逃さず、" in t
    assert [c.base[i] for i in range(3)] == [0, 0, 0]  # :314–316
    assert [c.cflag[k] for k in (20, 21, 23, 30, 31, 220)] == [0] * 6
    assert c.cflag[0] == 0  # AFTER_RESCUED.ERB:58 → RECOVER_TO_PARTY.ERB:3
    assert c.cflag[100] == 103  # AFTER_RESCUED.ERB:16 予定_休憩
    assert c.cflag[999] == 1 and "紅葉がパーティメンバーに加わりました" in t  # RECOVER_TO_PARTY.ERB:5–15


def test_prison_event_not_hole_uses_previous_fall_flag(ctx, data, comable):
    """ISHOLE() == 0 → GOTO SKIP（:106–107）。静的な `今回陥落するフラグ` は前回の値（ここでは 1）のまま末路１へ。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1)
    c.talent[ti(data, "オトコ")] = 1
    st.flag.set_bit(850, 5, True)  # ISHOLE の男女平等（CONFIG_CHECK_MANIAC_F(5)）を OFF
    st.flag.set_bit(804, 0, False)  # TS オプション OFF
    st.flag.set_bit(804, 1, True)
    set_local(st, "PRISON_EVENT", "今回陥落するフラグ", 1)  # type: ignore[arg-type]
    st.rng = FixedRng([3])  # :378 RAND:25
    event.prison_event(ctx)
    assert comable == []
    assert c.cflag[31] == 0  # :164–165 は飛ばされる
    assert c.cflag[0] == 2


def test_prison_loop_targets(ctx, comable):
    st = ctx.state
    for i in (1, 3):
        imprison(st, i)
        st.charas[i].cflag[31] = 3
    st.rng = FixedRng([10, 0, 10, 0])
    event.prison(ctx)
    assert comable == [0, 0]
    assert st.target == 3  # PRISON:17 TARGET は戻さない
    assert texts(ctx.out).count("・・・・・・・・・") == 1  # :18–24 は最初の 1 人だけ


# --- EVENT_PALAM_UP.ERB -----------------------------------------------------------------------------


def test_event_palam_up_in_prison(ctx, data):
    """COMMON_PRISON（COMMON_PRISON.ERB:21–38）→ EVENT_PALAM_UP（:10–105）。幽閉中は :134–140 で UP:0〜11 が
    触手補正 ÷ 100（Ｃ触手：120,100,…→ 1）に**置き換わり**、UP:12〜17 は ×9 も補正も受けない（:19–21 のループは 0〜11）。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1, boss=1)
    st.rng = FixedRng([0] * 12)  # :20 RAND:(UP+1)
    j0 = {i: c.juel[i] for i in range(18)}
    commands.common_prison(ctx, [1, 2, 3, 4, 0, 5, 6, 7, 8, 9, 10, 11])
    sk = seikaku_check(data, c)
    f = lambda pid, v: seikaku_hosei_palam(sk, pid, v)  # noqa: E731  :126–131
    tijou = f(15, 9) + 200  # :34 快計 1+2+2+1 = 6 < 1000 → 200
    yoku = f(13, 7) + 100 + 0 + 100  # :307–323 100、:339–362 露出癖 0 → ×0、:365–375 苦痛 10 → 100
    exp = {0: 1, 1: 1, 2: 1, 3: 1, 10: 0, 11: 1, 12: 6, 13: yoku, 14: f(14, 8), 15: tijou, 16: f(16, 10), 17: f(17, 11)}
    for pid, v in exp.items():
        assert c.juel[pid] - j0[pid] == v, pid
    assert all(st.temp.up[i] == 0 for i in range(18))  # :105 VARSET UP


@pytest.mark.parametrize(
    "mark_id, level, prevent, up, days, expected",
    [
        (0, 0, 0, 600, 65535, 1),  # 快楽刻印 基礎値 600（EVENT_PALAM_UP.ERH:15–21）
        (0, 0, 0, 599, 65535, 0),
        (1, 1, 2, 1500 + 2 * 150, 0, 2),  # 苦痛刻印 1500 + 防止 2 × 150（:32–45）、幽閉日数しきい値（添字省略 = 0）
        (1, 1, 2, 1799, 0, 1),
        (2, 5, 0, 10**9, 99, 5),  # :417 MARK >= VARSIZE（5）で打ち切り
    ],
)
def test_got_event_sex_mark_check(ctx, mark_id, level, prevent, up, days, expected):
    c = ctx.state.charas[1]
    imprison(ctx.state, 1)
    c.mark[mark_id] = level
    got_event_sex_mark_check(ctx, mark_id, up, prevent, days)
    assert c.mark[mark_id] == expected


@pytest.mark.parametrize(
    "shield, rng, expected",
    [
        # :44–48 ARG:0／1 を ×9 + RAND:(ARG+1)、20 超は 20 + (超過)/4：2→18+2=20、5→45+5=50→27
        ((0, 0, 0, 0), [2, 5], (20, 27, 1, 1)),
        # 18、45→26。:50–56 SHIELD:1 > 0 && SHIELD:2 <= 0 → ARG:1 += ARG:0、ARG:3 += ARG:2、ARG:0 = ARG:2 = 0
        ((0, 1, 0, 0), [0, 0], (0, 44, 0, 2)),
        ((0, 0, 1, 0), [0, 0], (44, 0, 2, 0)),  # :57–63
        ((0, 1, 1, 0), [0, 0], (0, 0, 0, 0)),  # :64–68
    ],
)
def test_common_prison_exp_sh(ctx, shield, rng, expected):
    st = ctx.state
    for i, v in enumerate(shield):
        st.shield[i] = v
    st.rng = FixedRng(rng)
    assert commands.common_prison_exp_sh(ctx, 2, 5, 1, 1) == expected


def test_prison_com200_doubles_kakuchou_exp(ctx, data):
    """PRISON_COM200：:51–53 Ｖ感覚 0 → LOCAL:151 = 1、:188–189 PRISON_GAPING の RESULT:0 は ARG:2（=1）＋拡張経験（CFLAG:34 = 0 → 0）
    なので LOCAL:151 = 2（原作どおりの 2 重加算）。:172–175 初回 → CFLAG:204 = 1・異常経験 +1。"""
    st = ctx.state
    c = st.charas[1]
    imprison(st, 1, boss=2)
    st.flag.set_bit(805, 2, True)  # 常時避妊（NINSIN_HANTEI:23–24 で打ち切り）
    before = {k: c.exp[ei(data, k)] for k in ("Ｖ拡張経験", "異常経験", "Ｖ経験")}
    st.rng = GameRng(3)
    commands.prison_com200(ctx)
    assert c.exp[ei(data, "Ｖ拡張経験")] - before["Ｖ拡張経験"] == 2
    assert c.exp[ei(data, "異常経験")] - before["異常経験"] == 1
    assert c.cflag[204] == 1
    # LOCAL:120 = 5 → ×9 + RAND:6 ∈ [45, 50] → 20 + (x - 20) / 4 ∈ {26, 27}（COMMON_PRISON.ERB:44–48）
    assert c.exp[ei(data, "Ｖ経験")] - before["Ｖ経験"] in (26, 27)
    assert st.tflag[10] == 200


# --- CHARA_TATTOO.ERB ------------------------------------------------------------------------------------


def test_tattoo_lv_cal_and_position(ctx, data):
    c = ctx.state.charas[1]
    c.abl[0], c.abl[1], c.abl[2], c.abl[3] = 3, 3, 4, 2
    c.talent[100] = 1  # Ｃ敏感
    c.talent[155] = 1  # 淫尻
    # :35 ABL * (敏感 + 5) / 5 * (5 - 鈍感) / 5 * (淫〜 + 2) / 2
    assert tattoo_lv_cal(ctx, 0) == ((3 * 6 // 5) * 5 // 5) * 2 // 2  # 3
    assert tattoo_lv_cal(ctx, 2) == ((4 * 5 // 5) * 5 // 5) * 3 // 2  # 6
    assert tattoo_position(ctx) == 2


def test_tattoo_access_and_save(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.talent[ti(data, "触手の虜")] = 1
    c.cflag[32] = 40 * PROG_UNIT + 7 * 100**2
    assert tattoo_access(ctx, "PROGRESS_VAR") == 40
    assert tattoo_access(ctx, "POSITION_BIT") == 4  # Ａ
    assert tattoo_access(ctx, "POSITION_STR") == "右臀部"
    save_tattoo(ctx, 55)  # :72–74 進行度だけ入れ替え（淫〜素質なし → 追加部位なし）
    assert c.cflag[32] == 55 * PROG_UNIT + 7 * 100**2


# --- AFTER_RESCUED.ERB／SHOP_TURNEND.ERB@RECALC_PARTYMEMBER／@INMON_RECOVERY ----------------------------


@pytest.mark.parametrize(
    "toriko, kanochi, prog, exp_cflag32, exp_flag32",
    [
        (1, 0, 50, 35 * PROG_UNIT + 2, None),  # :19–21 ×7/10 → :25 SAVE_TATTOO（進行度だけ入れ替え）
        (0, 0, 50, 50 * PROG_UNIT + 2, None),  # 触手の虜なし → SAVE_TATTOO:47–48 で何もしない
        (1, 1, 50, 50 * PROG_UNIT + 2, None),  # 完堕ち → 低下なし
        (1, 0, 1, 1 * PROG_UNIT + 2, 0),  # 1 × 7 / 10 = 0 → :23 `FLAG:32 = 0`（CFLAG ではない：原作どおり）
    ],
)
def test_after_rescued(ctx, data, toriko, kanochi, prog, exp_cflag32, exp_flag32):
    st = ctx.state
    c = st.charas[3]
    c.cflag[0] = -1
    c.cflag[999] = 0
    c.cflag[32] = prog * PROG_UNIT + 2
    c.talent[ti(data, "触手の虜")] = toriko
    c.talent[ti(data, "完堕ち")] = kanochi
    st.flag[32] = 9
    st.target = 1
    party.after_rescued(ctx, 3)
    assert c.cflag[32] == exp_cflag32
    assert st.flag[32] == (9 if exp_flag32 is None else exp_flag32)
    assert c.cflag[0] == (0)
    assert c.cflag[100] == 103
    assert st.target == 1  # :61
    t = texts(ctx.out)
    if kanochi:
        assert "妙な事を言ったり、奇妙な名前を名乗ったりしています" in t
    else:
        assert "幸い命に別条はないようです・・・" in t


def test_recalc_partymember_rescued(ctx):
    st = ctx.state
    c = st.charas[2]
    c.cflag[0] = -1
    c.cflag[999] = 0
    list(turnend.recalc_partymember(ctx))
    assert c.cflag[0] == 0 and c.cflag[999] == 1  # SHOP_TURNEND.ERB:235–244 → AFTER_RESCUED


@pytest.mark.parametrize("rng, gain", [([0, 0, 0], 1), ([7, 4, 4], 12)])
def test_inmon_recovery_progress(ctx, data, rng, gain):
    """:859–863 RESULT:1 = (2 + RAND:(LIMIT(SQRT(100 - 進行度),1,8)) + RAND:(MIN(欲望+1,5)) + RAND:(MIN(触手中毒+1,5))) * 3 / 4。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[ti(data, "触手の虜")] = 1
    c.abl[data.index_of("ABL", "欲望")] = 4
    c.abl[data.index_of("ABL", "触手中毒")] = 4
    c.cflag[32] = 10 * PROG_UNIT + 1
    st.rng = FixedRng(rng)
    turnend.inmon_recovery(ctx, 1)
    assert gain == (2 + sum(rng)) * 3 // 4
    assert c.cflag[32] == (10 + gain) * PROG_UNIT + 1
    assert f"紅葉の淫紋が{gain}％進行した・・・（{10 + gain}％）" in texts(ctx.out)


def test_inmon_recovery_fall_to_corruption(ctx, data):
    """:870–941 進行度 100 → 生存ボスから支配者（RANDCHOOSE）、変身能力 >= 0 → 悪堕ち。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[ti(data, "触手の虜")] = 1
    c.cflag[32] = 99 * PROG_UNIT + 1
    st.flag[100] = 0b0000101  # 生存：Ｃ触手（1）・Ａ触手（3）
    st.flag[10] = 0
    # 進行 RAND 3 個（2+1+0+0)*3/4=2 → 100、RANDCHOOSE RAND:2 = 1 → 2 番目（Ａ触手）、:935 RAND:50 = 0
    st.rng = FixedRng([1, 0, 0, 1, 0])
    turnend.inmon_recovery(ctx, 1)
    assert c.cflag[0] == 3
    assert (c.cflag[20], c.cflag[21]) == (0, 3)
    assert c.cflag[41] == 401
    assert c.exp[ei(data, "陥落経験")] == 1


def test_inmon_recovery_decay(ctx, data):
    """:984–995 CONFIG_CHECK_MANIAC_F(9) == 0：進行度 ×9/10。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[ti(data, "触手の虜")] = 1
    st.flag.set_bit(850, 9, True)
    c.cflag[32] = 30 * PROG_UNIT + 5
    turnend.inmon_recovery(ctx, 1)
    assert c.cflag[32] == 27 * PROG_UNIT + 5


# --- 救出（BATTLE_COM_AFTER.ERB@SOURCE_CHECK:203–262、COMF15.ERB@KYUSHUTU_SUCCESS:77–97）-------------------


def test_rescue_captives_on_boss_kill(ctx):
    st = ctx.state
    st.flag[10], st.flag[11] = 0, 3
    imprison(st, 2, boss=3)
    imprison(st, 3, boss=5)
    st.charas[2].cflag[30] = 70
    st.charas[2].cflag[31] = 6
    source_check._rescue_captives(ctx)
    c = st.charas[2]
    assert c.cflag[0] == -1 and [c.cflag[k] for k in (20, 21, 30, 31, 220)] == [0] * 5
    assert [c.base[i] for i in range(3)] == [1, 1, 1]
    assert st.charas[3].cflag[0] == 1  # 別のボスに捕らわれている


def test_kyushutu_success(ctx):
    st = ctx.state
    st.flag[11] = 2
    imprison(st, 3, boss=2)
    kyushutu_success(ctx)
    c = st.charas[3]
    assert c.cflag[0] == -1 and c.cflag[21] == 0 and c.base[0] == 1
    assert st.target == 1  # :84–88 で戻す


# --- 地の文 hook 表（narration/hooks.py PRISON_HOOK_LINES）-----------------------------------------------


def test_prison_hook_table_matches_erb(data):
    svc = CatalogNarrationService(ERB, data)
    cat = svc.catalog
    funcs = set()
    for (func, line), (text, _) in PRISON_HOOK_LINES.items():
        funcs.add(func)
        e = cat.index[func]
        assert dict(cat.lines_of(e.rel))[line].strip() == text, (func, line)
    # MESSAGE_PRISON.ERB の全関数：非 LOCAL の代入・状態 CALL は表にある
    e0 = cat.index["MESSAGE_PRISON_COM_0"]
    for no, t in cat.lines_of(e0.rel):
        s = t.strip()
        if re.match(r"^(FLAG|CFLAG|TALENT|BASE|EXP|ABL|TFLAG|MARK)\b[^=]*[-+*/|&]?=(?!=)", s) or re.match(r"^CALL (TS_|UNLOCK)", s):
            assert any(line == no for (_, line) in PRISON_HOOK_LINES), (no, s)
    for name in ("MESSAGE_PRISON_COM_1", "MESSAGE_PRISON_COM_105", "MESSAGE_PRISON_PRISENTENCE_FIRST", "MESSAGE_PRISON_DEAD"):
        assert cat.unsupported_reason(name) is None, name


def test_prison_messages_run_with_catalog(data):
    """catalog で MESSAGE_PRISON_COM_1 を実行：FLAG:900 は hook で書かれ、KOJO_ROOT が 0 に戻す（KOJO_ROOT.ERB:46–90）。"""
    svc = CatalogNarrationService(ERB, data)
    s = GameState.new(data, rng=GameRng(5))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    ctx = Ctx(s, data, TextOutput(), svc)
    imprison(s, 1, boss=2)
    assert svc.run_function(ctx, "MESSAGE_PRISON_COM_1", [])
    t = texts(ctx.out)
    assert "Ｖ中心攻め" in t
    assert s.flag[900] == 0


# --- 状況の確認（SHOP_SHOW_SITUATION_LIST.ERB）／E2E -------------------------------------------------------


def test_situation_list(ctx):
    st = ctx.state
    imprison(st, 2, boss=3)
    st.charas[2].cflag[31] = 5
    st.charas[3].cflag[0] = 9
    st.charas[3].talent[508] = 1  # 繁殖袋
    shop.shop_show_situation_list(st, ctx.data, ctx.out, ctx.narration)
    t = texts(ctx.out)
    assert " 桃香：Ａ触手によって幽閉中 2日目　" in t  # :86–99 CFLAG:31 / 2
    assert " 蒼美：苗床化" in t  # :180–189
    assert st.savestr[13] == "BOSS"  # :14


def _buttons(s: GameSession) -> list[int]:
    return [p.button for ln in s.screen()[-40:] for p in ln.parts if p.button is not None]


def test_e2e_defeat_prison_shop_save_load(data):
    """紅葉だけ出撃（ボス遭遇を強制）→ 敗北 → TURNEND：SET_PARTYMEMBER で最後尾へ・PRISON 1 回 → SHOP。幽閉中に存読檔。"""
    tmp = Path(tempfile.mkdtemp())
    s = GameSession(data, tmp, rng=GameRng(0))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』で開始
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    for _ in range(400):
        st = s.state
        if s.phase == Phase.SHOP and any(c.cflag[0] == 1 for c in st.charas[1:]):
            break
        if s.phase == Phase.SHOP:
            st.flag[47] = max(st.flag[47], st.flag[46])  # ENCOUNT.ERB:159 ボス遭遇条件
            for i in range(1, st.charanum):
                c = st.charas[i]
                if c.cflag[999] == 1 and c.cflag[0] == 0:
                    s.input(i)
                    s.input(101 if c.callname == "紅葉" else 103)
            s.input(100)
            if s.phase == Phase.ACTION_CONFIRM:
                s.input(9)
        else:
            assert s.phase == Phase.TURN, s.phase
            b = _buttons(s)
            s.input(next(n for n in (11, 10, 1) if n in b))
    st = s.state
    assert [c.callname for c in st.charas[1:]] == ["桃香", "蒼美", "紅葉"]  # SHIFTBACK_CHARA
    k = st.charas[3]
    assert (k.cflag[0], k.cflag[999], k.cflag[31]) == (1, 0, 1)  # 幽閉・編成外・PRISON_EVENT 1 回
    assert any("幽閉：紅葉" in ln.text for ln in s.out.lines)
    # 幽閉中のキャラは操作キャラに選べない（SHOP.ERB:199 `CFLAG:RESULT:0 == 状態_無事`）
    s.input(3)
    assert st.target != 3
    # [130] 状況の確認
    s.input(130)
    assert any("紅葉：" in ln.text and "によって幽閉中 0日目" in ln.text for ln in s.out.lines)
    # 幽閉中の存読檔
    snap = st.to_json()
    s.input(200)
    s.input(1)
    s.input(300)
    s.input(1)
    assert s.phase == Phase.SHOP
    assert s.state.to_json() == snap
    # 全員休憩でもう 1 ターン → 2 回目の PRISON_EVENT
    for i in (1, 2):
        s.input(i)
        s.input(103)
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)
    for _ in range(50):
        if s.phase != Phase.TURN:
            break
        s.input(_buttons(s)[0] if _buttons(s) else 0)
    assert s.phase == Phase.SHOP, [ln.text for ln in s.out.lines[-5:]]
    assert s.state.charas[3].cflag[31] == 2


@pytest.mark.parametrize(
    "time, cflag82, rng",
    [
        (0, 0, []),  # :28–29 昼は暴走判定をしない（RAND なし）
        (1, 0, [200]),  # :46 MIN(1*1*200/1, 2500) = 200、RAND 200 は < 200 でない
    ],
)
def test_parasite_after_rescue(ctx, data, time, cflag82, rng):
    """`強制発生イベント/FORCE_深夜の寄生触手暴走.ERB@PARASITE`:3–68：PRISON_COM301 で寄生された救出後のキャラ。
    暴走・共生取得の本体は S17（tests/test_parasite.py）。"""
    from eragvt.game.parasite import parasite

    st = ctx.state
    c = st.charas[2]
    c.talent[ti(data, "寄生")] = 1
    c.cflag[82] = cflag82
    st.time = time
    st.rng = FixedRng(rng)
    assert list(parasite(ctx)) == []
    assert c.exp[ei(data, "寄生経験")] == 1  # :17
    assert c.cflag[82] == cflag82 + 1  # :20–21


def test_session_halts_on_eventshop_stop(data, monkeypatch):
    """@EVENTSHOP 内の未移植イベントは例外で落とさず「停止」にする。"""
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(1))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』で開始
    s.input(1)  # HEROINE_PRESET [1] 基本セット

    def boom(*a, **k):
        raise NotImplementedError("テスト用")

    monkeypatch.setattr(shop, "event_shop_gen", boom)
    s.begin_shop(called_when_normal=True)
    assert s.phase == Phase.HALTED
    assert "（未實作のため停止しました：テスト用）" in texts(s.out)


@pytest.mark.parametrize("roll, ok", [(9, 1), (10, 0)])
def test_act_hantei_kyuushutu_floor(ctx, data, roll, ok):
    """COMF15.ERB@ACT_HANTEI_CHARA_TO_TENTACLE_KYUUSHUTU:102–174：敏捷 0 → PERCENT_CAL_F(0, …) = 0 →
    CORRECTION_BINSYOU_F(0) = 0 → LOCAL:5 = 0 → :156–157 最低値 10 → RAND:100 < 10。"""
    from eragvt.game.battle.restraint import act_hantei_kyuushutu

    st = ctx.state
    st.savestr[13] = "BOSS"
    st.flag[11] = 2
    st.flag[12], st.flag[13] = 1000, 1000
    c = st.charas[1]
    c.maxbase[data.index_of("BASE", "敏捷")] = 0
    st.rng = FixedRng([roll])
    assert act_hantei_kyuushutu(ctx) == ok
