"""S10：既定の開局（汎用キャラ 3 名のおまかせ生成、`eragvt.game.chara_make`）。

expected は ERB 原文から手で導出（路徑相對 `source/earGVP/ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB`、
以下「DEFAULT」、行號は註解）。`&&`／`||` は短絡（reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–555）。
実装の出力から逆算しない。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.battle.hantei import breast_weight_term
from eragvt.game.body import chara_make_age_setting
from eragvt.game.chara_make import (
    PERSONALITIES,
    _random_name_and_looks,
    base_profile_generic,
    chara_make_status_talent,
    chara_make_status_talent_flavor,
    initialize_personality,
    initialize_race,
    random_age_f,
    toint,
)
from eragvt.game.chara_common import seikaku_check, syuzoku_check
from eragvt.game.era import div
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


def ti(data, name):
    return data.index_of("TALENT", name)


def fresh(data, rolls=None, **talents):
    """ADDCHARA 0（Chara000 汎用キャラ・女性、素質なし）1 名。"""
    st = GameState.new(data, rng=FixedRng(rolls) if rolls is not None else GameRng(0))
    st.add_chara(data, 0)
    c = st.charas[-1]
    for name, v in talents.items():
        c.talent[ti(data, name)] = v
    return st, c, len(st.charas) - 1


def talents_of(data, c):
    return {data.names["TALENT"][i]: c.talent[i] for i in range(1300) if c.talent[i]}


# --- 種族（DEFAULT:8–72）-------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rolls, expected",
    [
        ([0], {"人間": 1}),  # RAND:24 = 0 → 201
        ([3], {"ロボっ子": 1}),  # 204
        ([10], {"ポリニアン": 1}),  # 211
        ([9, 0], {"ヴァンパイア": 1, "夜魔の貴族": 1}),  # 210 && RAND:2 == 0（:58）
        ([9, 1], {"人間": 1}),  # 210 だが RAND:2 != 0 → ELSE 人間
        ([23], {"人間": 1}),  # 224 → ELSE（RAND:2 は短絡で引かない。FixedRng が 1 個で足りる）
    ],
)
def test_initialize_race_random(data, rolls, expected):
    st, c, sel = fresh(data, rolls)
    initialize_race(st, data, sel)
    assert talents_of(data, c) == expected


def test_initialize_race_setting_and_feat(data):
    """FLAG:823 = 10 → ヴァンパイア＋夜魔の貴族（:30–32、乱数なし）。FLAG:824 == 1 的自動分配見 S54 測試。"""
    st, c, sel = fresh(data, [])
    st.flag[823] = 10
    initialize_race(st, data, sel)
    assert talents_of(data, c) == {"ヴァンパイア": 1, "夜魔の貴族": 1}



# --- 性格ガチャ・性格補正・一人称（DEFAULT:74–164、ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_F）---------


@pytest.mark.parametrize(
    "roll, name, bases, cflag8",
    [
        # 古風（24）：性耐性 ×0.80、攻撃・防御 ×1.10（CHARA_SEIKAKU.ERB の 24 の分岐）→ 一人称 20（:157–158）
        (14, "古風", (1000, 1000, 80, 110, 110, 100, 100), 20),
        # かるい性格（25）：体力 ×0.80、気力 ×0.90、性耐性・攻撃・敏捷 ×1.10 → 一人称 11（:159–160）
        (15, "かるい性格", (800, 900, 110, 110, 100, 110, 100), 11),
        # 臆病（10）：気力 ×0.90、敏捷 ×1.10、知性 ×1.20 → 一人称 0
        (0, "臆病", (1000, 900, 100, 100, 100, 110, 120), 0),
    ],
)
def test_initialize_personality(data, roll, name, bases, cflag8):
    st, c, sel = fresh(data, [roll])
    initialize_personality(st, data, sel)
    assert PERSONALITIES[roll] == name and ti(data, name) == 10 + roll  # Talent.csv:10–27
    assert seikaku_check(data, c) == 10 + roll
    keys = (0, 1, 2, 10, 11, 12, 13)
    assert tuple(c.base[k] for k in keys) == bases  # Chara000：体力・気力 1000、他 100
    assert tuple(c.maxbase[k] for k in keys) == bases
    assert c.cflag[8] == cflag8




# --- CHARA_MAKE_STATUS_TALENT（DEFAULT:985–1058）---------------------------------------------------


def test_status_talent_female(data):
    # 処女判定 10 < 20 → 非処女・Ｖ経験 1+RAND:4(2)=3／清純派 69 < 20+0 偽／パイパン 5／C 1 → 敏感／V 97 → 鈍感／
    # A 50／B 50／乳 20（どちらでもない）／体型 80 → 長身／濡れ 95 → 濡れにくい
    st, c, sel = fresh(data, [10, 2, 69, 5, 1, 97, 50, 50, 20, 80, 95])
    chara_make_status_talent(st, data, sel)
    assert talents_of(data, c) == {"パイパン": 1, "Ｃ敏感": 1, "Ｖ鈍感": 1, "長身": 1, "濡れにくい": 1}
    assert c.exp[data.index_of("EXP", "Ｖ経験")] == 3


def test_status_talent_male(data):
    # 男性：処女判定なし（ISFEMALE && …）。清純派 10 < 20／パイパン 50／C 1 → 敏感／V 1 → 女性限定なので無し／
    # A 97 → 鈍感／B 50／乳 0 → 女性限定で無し／体型 0 → 小柄／濡れ 0 → 女性限定で無し
    st, c, sel = fresh(data, [10, 50, 1, 1, 97, 50, 0, 0, 0], オトコ=1)
    chara_make_status_talent(st, data, sel)
    assert talents_of(data, c) == {"オトコ": 1, "清純派": 1, "Ｃ敏感": 1, "Ａ鈍感": 1, "小柄": 1}


# --- CHARA_MAKE_STATUS_TALENT_FLAVOR（DEFAULT:1063–1229）---------------------------------------------


def test_flavor_female_elementary(data):
    # 年齢 8 → 学生 1／交際 5：<4 偽、<8 かつ女性 → 2／家族 3：<2 偽、<4 → 2／アクセサリ 13 < 18 → 3／
    # 外見 9 < 12 → 3／イカ腹 10 < 12・学生 1・女性 → 外見 3／パイパン 80 ≥ 75 → 無し
    st, c, sel = fresh(data, [5, 3, 13, 9, 10, 80])
    c.base[41] = 8
    chara_make_status_talent_flavor(st, data, sel)
    assert talents_of(data, c) == {"学生": 1, "交際相手": 2, "家族関係": 2, "アクセサリ": 3, "外見": 3, "変身時外見": 3}


def test_flavor_male_highschool(data):
    # 年齢 16 → 学生 3／交際 5：<8 は女性限定 → <10 → 3（婚約者）／家族 0 → 1／アクセサリ・外見は女性限定／
    # イカ腹は学生 1 でない／パイパン 10 < 75 → 1
    st, c, sel = fresh(data, [5, 0, 0, 0, 0, 10], オトコ=1)
    c.base[41] = 16
    chara_make_status_talent_flavor(st, data, sel)
    assert talents_of(data, c) == {"オトコ": 1, "学生": 3, "交際相手": 3, "家族関係": 1, "パイパン": 1}


def test_flavor_ikabara_tall_and_small(data):
    """DEFAULT:1216–1224：長身は +12（10+12=22 ≥ 12 → イカ腹なし）、小柄は /2（23/2=11 < 12 → イカ腹）。"""
    st, c, sel = fresh(data, [99, 99, 99, 99, 10, 99], 長身=1)
    c.base[41] = 7
    chara_make_status_talent_flavor(st, data, sel)
    assert c.talent[ti(data, "外見")] == 0
    st, c, sel = fresh(data, [99, 99, 99, 99, 23, 99], 小柄=1)
    c.base[41] = 7
    chara_make_status_talent_flavor(st, data, sel)
    assert c.talent[ti(data, "外見")] == 3


# --- 年齢指定（DEFAULT:1408–1444、@RANDOM_AGE_F:1448–1497）-------------------------------------------


@pytest.mark.parametrize(
    "s, expected",
    [("", 0), ("12", 12), ("+5", 5), ("-3", -3), ("12.50", 12), ("12a", 0), ("1.2.3", 0), ("-", 0),
     ("１２", 0), ("少女", 0), ("abc", 0)],
)
def test_toint(s, expected):
    """Creator.Method.cs@ToIntMethod:2357–2387。全角を含むと 0（:2363）、数字の後は '.'＋数字のみ許す（:2371–2385）。"""
    assert toint(s) == expected


@pytest.mark.parametrize(
    "s, roll, expected",
    [("赤子", 3, 3), ("少女", 8, 15), ("壮年", 25, 60), ("大学生", 0, 19), ("年齢に合わせる", None, -99)],
)
def test_random_age_f(data, s, roll, expected):
    st = GameState.new(data, rng=FixedRng([] if roll is None else [roll]))
    assert random_age_f(st, s) == expected


def test_age_setting_designations(data):
    """RAND:11=5 → 15（変身能力なしで RAND:4 は引かない）→ :1404–1406 で 年齢・MAXBASE:年齢 15、実年齢 15。
    CSTR:204「年齢に合わせる」→ TOINT 0 → RANDOM_AGE_F = -99（乱数なし）→ 最後に :1436 で 実年齢 = 年齢。
    CSTR:205「少女」→ RAND:9(3)+7 = 10。CSTR:206「25」→ 25。"""
    st, c, _ = fresh(data, [5, 3])
    c.cstr[204], c.cstr[205], c.cstr[206] = "年齢に合わせる", "少女", "25"
    chara_make_age_setting(st, data, c)
    assert (c.base[40], c.base[41], c.maxbase[41]) == (10, 10, 25)
    st, c, _ = fresh(data, [5])
    c.cstr[204], c.cstr[206] = "0", "実年齢に合わせる"
    chara_make_age_setting(st, data, c)
    assert (c.base[40], c.base[41], c.maxbase[41]) == (0, 15, 0)  # 206 は RANDOM_AGE_F で -99 → :1442 で 実年齢 0


# --- 名前と外見（DEFAULT:546–900）----------------------------------------------------------------------


def test_random_name_japanese(data):
    # RAND:4=1（≠0 → 日本語苗字）／苗字 3000+0 = STR:3000「佐藤」／名前 12000+1 = STR:12001「陽菜」／
    # RAND:8=1 → ELSEIF RAND:3=0 → 黒髪／瞳 黒／RAND:4=1 → 肌色／RAND:15=1 アルビノなし／変身後の髪 RAND:4=1 なし／
    # RAND:50=1、RAND:4=1 → 瞳の変化なし
    st, c, _ = fresh(data, [1, 0, 1, 1, 0, 1, 1, 1, 1, 1])
    assert _random_name_and_looks(st, data, c) == (3000, "佐藤", "陽菜")
    assert [c.cstr[k] for k in range(30, 38)] == ["黒", "黒", "黒", "黒", "黒", "黒", "肌色", "肌色"]


def test_random_name_foreign_and_eye_change(data):
    # RAND:4=0 → 外国苗字：RAND:8500(0)+3500 = STR:3500「アボット」、名前 RAND:3500(0)+12500 = STR:12500「アビー」／
    # 髪 RAND:6=0 → 銀／瞳 RAND:12=0 → 赤／肌 RAND:20=0 → 銀／特殊 RAND:6=0 → 褐色娘（銀髪・褐色）／
    # 変身後の髪 RAND:4=0 → RAND:8=0 → 赤／RAND:50=0 → オッドアイ：RAND:8=1、RAND:7=0 → 緑、代入先 34+RAND:2(1) = 35
    st, c, _ = fresh(data, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1])
    assert _random_name_and_looks(st, data, c) == (3500, "アボット", "アビー")
    assert [c.cstr[k] for k in range(30, 38)] == ["銀", "赤", "赤", "赤", "赤", "緑", "褐色", "褐色"]


# --- 既定の開局（オープニング処理.ERB@EVENTFIRST:111–166、CHARA_MAKE.ERB:206–209）--------------------------


@pytest.fixture(scope="module")
def default_state(data):
    st = GameState.new(data, rng=GameRng(5))
    event_first(st, data)
    return st


def test_default_opening_charas(data, default_state):
    st = default_state
    assert st.charanum == 4 and st.flag[8] == 3  # MASTER（999）＋ ADDCHARA 0 ×3（:115–122）
    assert st.charas[0].no == 999
    kojo = ti(data, "口上設定")
    for i, c in enumerate(st.charas[1:], start=1):
        assert c.no == 0  # CharacterData.cs:99 NO = tmpl.No
        assert c.callname not in ("", "汎用キャラ") and c.cstr[200] == c.callname  # :911–916
        assert c.name.endswith(c.callname) or c.name.startswith(c.callname)
        assert 10 <= seikaku_check(data, c) <= 27  # RAND:18+10
        assert sum(1 for k in range(10, 28) if c.talent[k]) == 1
        assert 201 <= syuzoku_check(c) <= 211
        assert c.talent[kojo] == 0 and c.cflag[6] == 0  # 女性汎用：:147 NO:0 → 0、:154–155 口上設定 0 → 0
        assert c.cflag[34] == 1  # :980
        assert c.cflag[240] == i
        assert c.cflag[100] == 103  # 予定_休憩（:165）
        # 身体データ（CHARA_SIZE_DEFAULT）：年齢 10〜20（RAND:11+10、学生の再抽選なし：学生は AGE_SETTING の後で決まる）
        assert 10 <= c.base[41] <= 20 and c.base[40] >= c.base[41] or c.talent[ti(data, "ロボっ子")]
        assert all(c.base[k] > 0 for k in (43, 44, 45, 46, 47))
        assert c.maxbase[41] == -1  # CHARA_SIZE_DEFAULT:2152–2153 は変身能力の付与（:531–534）より前
        assert c.cflag[40] == 100 and c.cflag[41] == 200 and c.cflag[42] == 300  # Chara000 CSV
        if c.talent[ti(data, "人間")]:
            assert c.talent[ti(data, "変身能力")] == 1 and c.cstr[0] == c.callname and c.cflag[2] == 1


def test_default_opening_battle_breast_term_normal(data, default_state):
    """COMMON_BATTLE_HANTEI.ERB:606–614：value*(1+胸の重量)/(1+体重)。体重が生成されるので値は小さい（敏捷はほぼそのまま）。"""
    st = default_state
    ctx = Ctx(st, data, TextOutput(), NullNarrationService())
    for c in st.charas[1:]:
        w, b = c.base[44], c.base[48]
        assert w > 100  # 10.0kg 超
        assert breast_weight_term(ctx, c, 160) == div(160 * (1 + b), 1 + w) < 16


def test_default_opening_shop(data):
    st = GameState.new(data, rng=GameRng(11))
    event_first(st, data)
    shop.event_shop(st, data, TextOutput(), NullNarrationService())
    assert st.day[0] == 1 and st.target == 1


def test_preset_option_still_tokusou(data):
    st = GameState.new(data, rng=GameRng(3))
    event_first(st, data, preset=PRESET_TOKUSOU)
    assert [c.no for c in st.charas[1:]] == [301, 302, 303]


def test_session_default_opening_reaches_shop(data):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(2))
    s.input(0)
    assert s.phase == Phase.NEW_GAME
    s.input(0)  # おまかせで開始
    assert s.phase == Phase.NEW_GAME  # HEROINE_PRESET の入力待ち（S24）
    s.input(1)  # [1]「基本セット」
    assert s.phase == Phase.SHOP
    assert all(c.no == 0 for c in s.state.charas[1:])
