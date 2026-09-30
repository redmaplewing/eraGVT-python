"""S09：身體資料（`eragvt.game.body`）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/SYSTEM/キャラメイキング関連/`、行號は註解）。
整数の `/` は C# long 除算（向 0 截斷）、BREAK はカウンタを進めてから抜ける
（reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2054–2077）。実装の出力から逆算しない。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx
from eragvt.game.battle.hantei import breast_weight_term
from eragvt.game.body import (
    calc_breast_weight,
    chara_make_age_setting,
    cup_size,
    generate_bodyline,
    generate_char_size,
    set_profile,
    top_under,
)
from eragvt.game.chara_common import charatalent
from eragvt.game.opening import PRESET_TOKUSOU, chara_make_base_profile, event_first
from eragvt.game.prison import commands
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


def ti(data, name):
    return data.index_of("TALENT", name)


def blank(data, **talents):
    """Chara000（汎用キャラ・女性、NO = 0）をもとに、素質を空にしたキャラ。"""
    st = GameState.new(data, rng=GameRng(0))
    st.add_chara(data, 0)
    c = st.charas[-1]
    for i in range(1300):
        c.talent[i] = 0
    for name, v in talents.items():
        c.talent[ti(data, name)] = v
    return st, c


# --- GENERATE_CHAR_SIZE:25–284（TOP_UNDER:287–380、CUP_SIZE:386–456、CALC_BREAST_WEIGHT:554–670）-----------
# 手計算の過程（抜粋）
# (a) 女・素質なし・乱数値 0・成長曲線 0・年齢 0：身長 10940*95/100=10393 → 0 歳 *605/1000=6287 → *(25+260)/3000=597。
#     BMI (20+180)*100/120=166。体重:0=166*597*597/1e6=59、体重:1=597e6/9345768=63 → 63*875822962/1e9=55、
#     CAL_VAR=1000 → 55。胴囲 597*3294/1e4=196、腰囲 597*5022/1e4=299、アンダー 597*4155/1e4=248。
#     TOP_UNDER：影響値 10*26/15=17、ELSE 表 (0,100,174) → 最小 25・最大 99、サイズ 17 → 25。体重 += (-18600*17/50)/1000=-6 → 49。
#     胸囲 273。CUP_SIZE(25)=2 → CALC_BREAST_WEIGHT(273,248,2)：半球 20、カップ 10、R 11、底 8、√57=7、高さ 4、
#     体積 485、重量 0 → (60+0)/11=5 → /100=0。
# (b) 女・巨乳 1・乱数値 1000000・成長曲線 0・年齢 16：乱数値:1..6 = 1,2,9,10,0,1、TOP 側 6,1,49。
#     身長 10502 → 5〜12 歳 +3010、13 歳 +100/2 → 13562 → *287/3000=1297。BMI 200*116/120=193。
#     体重:0=324、体重:1=268 → 273、CAL_VAR=812 → (324*188+273*812)/1000+9=291。胴囲 1297*3837/1e4=497、
#     腰囲 1297*5211/1e4=675、アンダー 1297*4295/1e4=557。影響値 26*22/15+49/4=50 → +99+2=151、
#     巨乳 (25,175,249)：25*99/50+151=200。体重 += -56 → 235。胸囲 757、CUP_SIZE(200)=7、
#     CALC(757,557,7)：半球 46、カップ 80、R 52、底 39、√1183=34、高さ 86、体積 541880、重量 942 → (758+9420)/11=925 → 9。体重 244。
# (c) 男（オトコ 1）・乱数値 0・成長曲線 0・年齢 20：身長 10393+3110 (+0) → 13503*285/3000=1282 → *1085/1000=1390。
#     BMI 200。体重 (386*560+346*440)/1000=368、TOP_UNDER は -1（影響値 157）→ 368-58=310。胸の重量 CALC(600,601,1)→(18+0)/11=1 → 0。
#     男性は胸囲・胴囲・腰囲 -1（:255–258）。
@pytest.mark.parametrize(
    "talents, r0, age, expected",
    [
        ({}, 0, 0, (0, 0, 597, 49, 273, 196, 299, 0)),
        ({"巨乳": 1}, 1000000, 16, (1000000, 0, 1297, 244, 757, 497, 675, 9)),
        ({"オトコ": 1}, 0, 20, (0, 0, 1390, 310, -1, -1, -1, 0)),
    ],
)
def test_generate_char_size(data, talents, r0, age, expected):
    _, c = blank(data, **talents)
    c.cflag[33] = r0
    c.cflag[34] = 0
    c.base[41] = age
    assert generate_char_size(data, c, 0) == expected


def test_generate_char_size_overrides(data):
    """:182–185・:262–281：指定素質（>0）は計算値を上書きする（変身値 0 は通常時の指定のみ）。"""
    _, c = blank(data, 身長指定=1500, 体重指定=450, 胸囲指定=800, 胴囲指定=560, 腰囲指定=820, 胸の重量指定=7)
    c.talent[ti(data, "変身時身長指定")] = 1700
    r = generate_char_size(data, c, 0)
    assert r[2:] == (1500, 450, 800, 560, 820, 7)
    assert generate_char_size(data, c, 1)[2] == 1700


@pytest.mark.parametrize(
    "arg, expected",
    [(-1, (1, "―")), (24, (1, "―")), (25, (2, "AAA")), (74, (2, "AAA")), (75, (2, "AA")), (100, (3, "A")),
     (200, (7, "E")), (224, (7, "E")), (725, (28, "Z")), (900, (35, "Z"))],
)
def test_cup_size(arg, expected):
    """CUP_SIZE:386–456：RESULTS は <25 ―、<75 AAA、以後 25 刻み、≥750 も Z。RESULT は <25 → 1、他 MAX(2,(ARG-25)/25)。"""
    assert cup_size(arg) == expected


@pytest.mark.parametrize(
    "tb, ub, cup, expected",
    [
        (273, 248, 2, 5),  # (a) の胸
        (757, 557, 7, 925),  # (b) の胸
        # :601–602 POWER(R,2)-POWER(底,2) < 0 → 0：ub=0、tb=-100 → カップ -40、R=-18、底=-18-15=-33 → 324-1089<0
        (-100, 0, 1, 0),
    ],
)
def test_calc_breast_weight(tb, ub, cup, expected):
    assert calc_breast_weight(tb, ub, cup) == expected


def test_top_under_male_and_youth(data):
    """TOP_UNDER:367–378：15 歳未満は最小・最大を 75*(15-年齢)/15 下げる。男性（男の娘でない）は -1。"""
    _, c = blank(data)
    c.cflag[33] = 0
    c.base[41] = 0
    assert top_under(data, c, 0) == (25, 17)  # (a)
    _, m = blank(data, オトコ=1)
    m.cflag[33] = 0
    m.base[41] = 20
    assert top_under(data, m, 0) == (-1, 157)


# --- GENERATE_BODYLINE:460–544 ----------------------------------------------------------------


def test_generate_bodyline(data):
    """乱数値 = RAND:535627332240、成長値に RAND:726 で 60 回配分（上限 9、超えたら引き直し）。
    累積境界：83／163／238／321／434／542（_DEV_VAR）。0×9 → 年 0 が 9、10 回目の 0 は引き直し、
    以後 83・163・238・321・434 を各 9 回、542 を 6 回 → 成長値 = [9,9,9,9,9,9,6,0,…] → 成長曲線 6999999。"""
    st, c = blank(data)
    rolls = [123456789] + [0] * 10 + [83] * 9 + [163] * 9 + [238] * 9 + [321] * 9 + [434] * 9 + [542] * 6
    st.rng = FixedRng(rolls)
    generate_bodyline(st, data, c)
    assert (c.cflag[33], c.cflag[34]) == (123456789, 6999999)
    with pytest.raises(RuntimeError):  # 62 回ちょうど消費
        st.rng.rand(2)


def test_generate_bodyline_talent_override(data):
    """:488–489・:535–536：体型乱数値指定／体型成長曲線指定 > 0 なら上書き（乱数は引く）。"""
    st, c = blank(data, 体型乱数値指定=77, 体型成長曲線指定=123)
    st.rng = FixedRng([5] + [0] * 9 + [83] * 9 + [163] * 9 + [238] * 9 + [321] * 9 + [434] * 9 + [542] * 6)
    generate_bodyline(st, data, c)
    assert (c.cflag[33], c.cflag[34]) == (77, 123)


# --- CHARA_MAKE_AGE_SETTING:1336–1444 ----------------------------------------------------------


@pytest.mark.parametrize(
    "talents, rolls, expected",
    [
        # RAND:11=5 → 15、変身能力あり・MAXBASE:年齢 0 <= 18・RAND:4=0 → 15+RAND:6(2)=17、学生なし → :1404–1406 で上書き
        ({"変身能力": 1}, [5, 0, 2], (15, 15, 15)),
        # 高校生：RAND:4=1（≠0）→ ELSEIF、AGE = RAND:5(3)+15 = 18
        ({"変身能力": 1, "学生": 3}, [5, 1, 3], (18, 18, 18)),
        # 変身能力なし：&& の短絡で RAND:4 を引かない（OperatorMethod.cs:524–538）。人妻（交際相手 4）・学生なし → 4*5+RAND:11(7)=27
        ({"交際相手": 4}, [3, 7], (27, 27, 27)),
        # 天使：実年齢 += RAND:1000（RAND:2=0 のとき）、RAND:10=0 → += RAND:10000
        ({"天使": 1}, [0, 0, 400, 0, 5000], (10, 10, 5410)),
    ],
)
def test_chara_make_age_setting(data, talents, rolls, expected):
    st, c = blank(data, **talents)
    st.rng = FixedRng(rolls)
    chara_make_age_setting(st, data, c)
    assert (c.base[41], c.maxbase[41], c.base[40]) == expected


# --- SET_PROFILE（FIRSTSETTING_CHARA_TALENT.ERB:4–19）と膨乳化 --------------------------------------
# 紅葉（Chara301：小柄・変身能力、年齢 0、CFLAG:33 = 34 = 0）の手計算：
#   身長 6287*260/3000=544、BMI (20+20+180)*100/120=183、体重 54、胴囲 544*3447/1e4=187、腰囲 544*5141/1e4=279、
#   アンダー 544*4240/1e4=230。影響値 17 → 体重 54-6=48。
#   巨乳 0：ELSE 表 → サイズ 25、胸囲 255、胸の重量 (60+0)/11/100=0。
#   巨乳 1：(25,175,249) → 最小 100・最大 174、25+17=42 → 100、胸囲 330、CALC(330,230,3)：半球 19、カップ 40、
#   R 24、底 16、√320=17、高さ 41、体積 54542、重量 94 → (100+940)/11=94 → 0。
#   変身時（CFLAG:1 = 0、変身時体格変動・胸サイズ変動 0）の CHARATALENT_F は通常時と同じ素質 → MAXBASE も同値（MAXBASE:年齢 0）。


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # TARGET=1（紅葉）
    return Ctx(s, data, TextOutput(), NullNarrationService())


def _sizes(store):
    return tuple(store[k] for k in (43, 44, 45, 46, 47, 48))


def test_set_profile_momiji(ctx, data):
    c = ctx.state.charas[1]
    set_profile(data, c)
    assert _sizes(c.base) == (544, 48, 255, 187, 279, 0)
    assert _sizes(c.maxbase) == (544, 48, 255, 187, 279, 0)
    assert (c.cflag[33], c.cflag[34]) == (0, 0)  # SET_PROFILE は CFLAG:33／34 を書かない


def test_prison_com105_calls_set_profile(ctx, data):
    """PRISON_COM105_膨乳化.ERB:46–79：膨乳の余地あり → 巨乳 +1、CFLAG:37 +1、SET_PROFILE、恐怖 800、地の文。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[0] = 1
    c.cflag[21] = 1
    commands.prison_com105(ctx)
    assert c.talent[ti(data, "巨乳")] == 1
    assert c.cflag[37] == 1
    assert _sizes(c.base) == (544, 48, 330, 187, 279, 0)
    assert _sizes(c.maxbase) == (544, 48, 330, 187, 279, 0)


# --- 開局（CHARA_MAKE_BASE_PROFILE:493–505）--------------------------------------------------------


def test_new_game_preset_has_no_profile(data):
    """初期セットのキャラは NO = CSV 番号（CharacterData.cs:99）≠ 0 なので :498 の条件が偽 → 何も生成せず :505 で RETURN。
    BASE:40–48 は 0、CFLAG:33／34 も 0（プロフィール未設定）のまま（原作どおり）。"""
    st = GameState.new(data, rng=GameRng(3))
    event_first(st, data, preset=PRESET_TOKUSOU)
    for i in (1, 2, 3):
        c = st.charas[i]
        assert c.no in (301, 302, 303)
        assert all(c.base[k] == 0 for k in range(40, 49))
        assert (c.cflag[33], c.cflag[34]) == (0, 0)


def test_base_profile_no_zero_branch(data):
    """NO == 0 かつ呼び名が「汎用キャラ」以外・CFLAG:34 == 0 → GENERATE_BODYLINE → AGE_SETTING → CHARA_SIZE_DEFAULT（:498–503）。"""
    st, c = blank(data)
    c.callname = "テスト"
    c.talent[ti(data, "変身能力")] = 0
    st.rng = FixedRng([0] + [0] * 9 + [83] * 9 + [163] * 9 + [238] * 9 + [321] * 9 + [434] * 9 + [542] * 6 + [5])
    chara_make_base_profile(st, data, st.charas.index(c))
    assert c.cflag[34] == 6999999
    assert (c.base[41], c.base[40]) == (15, 15)  # RAND:11 = 5 → 15（変身能力なしなので RAND:4 は引かない）
    assert c.maxbase[41] == -1  # AGE_SETTING :1405 で 15 → CHARA_SIZE_DEFAULT :2153–2154（変身能力 < 1）で -1
    assert c.base[43] > 0 and c.base[44] > 0


# --- CHARATALENT_F 変身中分岐（コモン関数.ERB:1083–1206）-------------------------------------------


@pytest.mark.parametrize(
    "talents, transformed, name, expected",
    [
        # 変身中・変身時の問い（:1084–1130）：現在の TALENT をそのまま
        ({"巨乳": 2}, 1, "爆乳", 1),
        ({"変身時外見": 2}, 1, "むちむち", 1),
        # 変身中・通常時の問い（:1131–1205）：巨乳 2 - 貧乳 0 - 変身時胸サイズ変動 1 = 1 → 巨乳
        ({"巨乳": 2, "変身時胸サイズ変動": 1}, 0, "巨乳", 1),
        # 差 0 で変動も 0 → TALENT から（小柄）
        ({"小柄": 1}, 0, "小柄", 1),
        # 長身 0 - 小柄 0 - 変身時体格変動(-1) = 1 → 長身
        ({"変身時体格変動": -1}, 0, "長身", 1),
        # 女性・変身時ＴＳ 1 → 通常時はオトコ
        ({"変身時ＴＳ": 1}, 0, "オトコ", 1),
        ({"外見": 3}, 0, "イカ腹", 1),
    ],
)
def test_charatalent_transformed(data, talents, transformed, name, expected):
    _, c = blank(data, **talents)
    c.cflag[1] = 1
    assert charatalent(data, c, transformed, name) == expected


# --- 戦闘：胸部重量ペナルティ（COMMON_BATTLE_HANTEI.ERB:606–614、:1097–1105、:1207–1214）--------------


@pytest.mark.parametrize(
    "weight, breast, value, expected",
    [
        (0, 0, 160, 160),  # 未生成：160*(1+0)/(1+0) = 160 → 敏捷 0（原作どおり）
        (480, 5, 160, 1),  # 48.0kg・0.5kg：160*6/481 = 1 → 敏捷 159
        (244, 9, 150, 6),  # (b) の体：150*10/245 = 6
    ],
)
def test_breast_weight_term(ctx, weight, breast, value, expected):
    c = ctx.state.charas[1]
    c.base[44] = weight
    c.base[48] = breast
    assert breast_weight_term(ctx, c, value) == expected


def test_breast_weight_term_sp_and_male(ctx, data):
    c = ctx.state.charas[1]
    c.base[44], c.base[48], c.maxbase[48] = 480, 5, 47
    c.cflag[1] = 2  # SP変身中 → 胸の重量は MAXBASE、体重は BASE（:608–609）
    assert breast_weight_term(ctx, c, 160) == 15  # 160*48/481
    c.cflag[1] = 0
    c.talent[ti(data, "オトコ")] = 1
    assert breast_weight_term(ctx, c, 160) == 0
