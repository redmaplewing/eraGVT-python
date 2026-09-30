"""S13：妊娠（`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB`）と出産・子供（`PREGNANT_CHILD_BIRTH.ERB`／`_N.ERB`）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/`、行號は註解）。乱数は FixedRng（`值 % n`）。
"""

from __future__ import annotations

import re

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import child, firstsetting, pregnancy, relation, shop, turnend
from eragvt.game.action import Ctx
from eragvt.game.battle import ninsin
from eragvt.game.battle.func import act_limit
from eragvt.game.opening import event_first
from eragvt.game.tentacle import tentacle_bitvalue
from eragvt.narration.hooks import NINSIN_HOOK_LINES
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.state.savefile import dump_save, load_save
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


class ZeroTail(FixedRng):
    """FixedRng の値を使い切ったら 0 を返す（後続の RAND が期待値に影響しない試験用）。"""

    def rand(self, n: int) -> int:
        if not self._values:
            return 0
        return super().rand(n)


def T(data, name):
    return data.index_of("TALENT", name)


def J(data, name):
    return data.index_of("PALAM", name)  # JUEL の名前は Palam.csv


def E(data, name):
    return data.index_of("EXP", name)


@pytest.fixture
def ctx(data):
    """預設開局（汎用キャラ 3 名、CFLAG:240 = 1〜3、全員編成中 CFLAG:999 = 1、所持金 $5000）。"""
    s = GameState.new(data, rng=GameRng(3))
    event_first(s, data)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.target = 1
    # 開局時のランダム素質（STATUS_TALENT 等）が期待値に影響しないよう、種族（201–211）・変身能力（200）・処女以外を 0 に
    keep = set(range(200, 212)) | {data.index_of("TALENT", "処女")}
    for i in (1, 2, 3):
        c = s.charas[i]
        saved = {k: c.talent[k] for k in keep}
        c.talent.clear()
        for k, v in saved.items():
            c.talent[k] = v
        c.cflag[217] = 0  # 危険日でない（ESTRUS_TEXT_F）
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def run_inputs(gen, inputs: list[int]):
    """ジェネレータに INPUT を順に送る。すべて消費して終了すること。"""
    try:
        next(gen)
        for v in inputs:
            gen.send(v)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT がまだ残っている")


# --- NINSIN_HANTEI の父親分岐（:39–97）と受精後（:140–163、NINSIN_FLAG:195–246）-------------------------------


def test_ninsin_prison_tentacle_father(ctx, data):
    """幽閉中（CFLAG:0 = 1、CFLAG:21 = 3 Ａ触手）：PAPA_ID = 3（:39–40）→ CFLAG:232 += 10、
    PREG_PER = SQRT(30 × 10 × 1 / 2) = 12（:72–75）、FLAG:700 = 0・幽閉中なので +100 なし → RAND:1000 = 11 < 12。
    NINSIN_FLAG：触手 → 妊娠 2（:224）→ CFLAG:21 > 0 で即時（:227）→ 育児機能 OFF（FLAG:805 = 2）→ 妊娠 1、
    CFLAG:227 = 1 + RAND:4（出産経験 0：:583–584）、CFLAG:228 = 88 × 227 × (80 + RAND:41) / 100（:833–839）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[0] = 1
    c.cflag[21] = 3
    c.cflag[217] = 0  # 危険日でない
    st.rng = FixedRng([0, 11, 2, 20])  # CHECK_HININ RAND:100、:140 RAND:1000、RAND:4、RAND:41
    assert ninsin.ninsin_hantei(ctx, 10, 30) == 1
    assert c.cflag[230] == 3 and c.cflag[232] == 0 and c.cflag[221] == 0
    assert c.talent[T(data, "妊娠")] == 1
    assert c.cflag[227] == 3 and c.cflag[228] == 88 * 3 * 100 // 100
    assert c.juel[J(data, "屈服")] == 2500 and c.juel[J(data, "恐怖")] == 1500  # NINSIN_SUBMIT:765–766
    assert "〈地の文：MESSAGE_NINNSIN〉" in texts(ctx.out)


def test_ninsin_prison_not_pregnant_keeps_count(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.cflag[0] = 1
    c.cflag[21] = 3
    c.cflag[217] = 0
    st.rng = FixedRng([0, 12])  # 12 < 12 は偽
    assert ninsin.ninsin_hantei(ctx, 10, 30) == 0
    assert c.cflag[232] == 10 and c.cflag[221] == 10 and c.talent[T(data, "妊娠")] == 0


def test_ninsin_battle_boss_father(ctx, data):
    """戦闘中（FLAG:700 = 1）ボス触手（FLAG:11 = 2）：PAPA_ID = 2、PREG_PER = SQRT(15×5/2) = 6 → ×2（:99–100）= 12、
    非幽閉 +100 → RAND:1000 = 111 < 112。妊娠 = 2 のまま（戦闘中は NINSIN_CHECK_AFTER で判明）。H触手でないので :150–162 なし。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[217] = 0
    st.flag[700] = 1
    st.flag[11] = 2
    st.savestr[13] = "BOSS"
    st.rng = FixedRng([0, 111])
    assert ninsin.ninsin_hantei(ctx, 5, 15) == 1
    assert c.talent[T(data, "妊娠")] == 2 and c.cflag[230] == 2 and c.cflag[227] == 0
    # 戦闘後：NINSIN_CHECK_AFTER（:169–190）で 妊娠 1
    st.flag[700] = 0
    st.rng = FixedRng([3, 40])  # NUM_CHILD：1 + RAND:4 = 4、SIZE：88×4×(80+40)/100 = 422
    ninsin.ninsin_check_after(ctx)
    assert c.talent[T(data, "妊娠")] == 1 and c.cflag[227] == 4 and c.cflag[228] == 422


def test_ninsin_h_tentacle_ovulation(ctx, data):
    """Ｈ触手（FLAG:11 = 7）＋排卵（TCVARn:12 & 2 → PREG_PER = 1000：:121–122）：:150–161 で 妊娠 = 1（CFLAG:227／228 は設定しない）。"""
    st = ctx.state
    c = st.charas[1]
    st.flag[700] = 1
    st.flag[11] = 7
    st.savestr[13] = "BOSS"
    c.tcvarn[12] = 2
    st.rng = FixedRng([0, 999])
    assert ninsin.ninsin_hantei(ctx, 5, 15) == 1
    assert c.talent[T(data, "妊娠")] == 1 and c.cflag[227] == 0 and c.cflag[228] == 0
    t = texts(ctx.out)
    assert "成熟した卵子の周りには無数の触手の精子が群がっている。" in t
    assert f"{c.callname}は[妊娠]した" in t


def test_ninsin_akuoti_father(ctx, data):
    """悪堕ちキャラ（FLAG:110 > 0、FLAG:111 = 2）：PAPA_ID = CFLAG:2:240 × −1 − 100 = −102（:44–45）、寄生ふたなりでない。
    :77–91 仲間（寄生なし）→ CFLAG:233 += 5、SQRT(15×5/2) = 6、FLAG:700 = 1 → 12。NINSIN_FLAG:198–212 → 妊娠 4。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[217] = 0
    st.flag[700] = 1
    st.flag[110] = 1
    st.flag[111] = 2
    st.savestr[13] = "BOSS"  # :151 TENTACLE_ACCESS "GETNAME"（悪堕ちキャラ戦は未移植なので仮の敵データ）
    st.flag[11] = 1
    st.rng = FixedRng([99, 111, 0])  # CHECK_HININ（CFLAG:241 = 0 → LOCAL 0）、:140、PREGNANT_RANDOM_SIZE RAND:41
    assert ninsin.ninsin_hantei(ctx, 5, 15) == 1
    assert c.cflag[230] == -102 and c.talent[T(data, "妊娠")] == 4 and c.cflag[228] == 266 * 80 // 100


@pytest.mark.parametrize("parasite, used, preg", [(0, 233, 4), (1, 232, 1)])
def test_ninsin_companion_father(ctx, data, parasite, used, preg):
    """ARG:2 = −102（仲間 CFLAG:240 = 2）：:61–66、:77–91。寄生なら触手扱い（232）。
    NINSIN_FLAG:198–212：父母とも寄生なし → 4（+CFLAG:228）、それ以外 → 2 → 戦闘外なので即時 → 1（:227–242）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[217] = 0
    st.charas[2].talent[T(data, "寄生")] = parasite
    # CHECK_HININ、:65 は寄生ふたなりでない → RAND:4 なし、:140（SQRT(60×10/2) = 17 + 100）、
    # 妊娠 4：RAND:41 ／ 妊娠 1：RAND:4、RAND:41
    st.rng = FixedRng([0, 116, 0, 0])
    assert ninsin.ninsin_hantei(ctx, 10, 60, -102) == 1
    assert c.talent[T(data, "妊娠")] == preg and c.cflag[230] == -102
    assert c.cflag[used] == 0


def test_ninsin_papa_zero_uses_previous_preg_per(ctx, data):
    """PAPA_ID = 0（戦闘外・非幽閉・ARG:2 = 0）は :72–97 のどれにも当たらず、static な PREG_PER の前回値（:14、
    UserDefinedVariable.cs:27）を使う。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[217] = 0
    st.temp.locals[("NINSIN_HANTEI:PREG_PER", 0)] = 50
    # CHECK_HININ、:140（149 < 50 + 100）、NINSIN_FLAG：触手扱い 2 → 戦闘外で即時 1（NUM_CHILD RAND:4、SIZE RAND:41）
    st.rng = FixedRng([0, 149, 0, 0])
    assert ninsin.ninsin_hantei(ctx, 5, 15) == 1
    assert c.cflag[230] == 0 and c.talent[T(data, "妊娠")] == 1 and c.cflag[227] == 1


@pytest.mark.parametrize(
    "toriko, birth, juel",
    [(1, 0, {"恭順": 1000}), (0, 10, {"屈服": 100}), (0, 5, {"屈服": 400, "恐怖": 50}),
     (0, 1, {"屈服": 1000, "恐怖": 300}), (0, 0, {"屈服": 2500, "恐怖": 1500})],
)
def test_ninsin_submit(ctx, data, toriko, birth, juel):
    """`@NINSIN_SUBMIT`:752–767。"""
    c = ctx.state.charas[1]
    c.talent[T(data, "触手の虜")] = toriko
    c.exp[E(data, "出産経験")] = birth
    ninsin.ninsin_submit(ctx)
    for name in ("恭順", "屈服", "恐怖"):
        assert c.juel[J(data, name)] == juel.get(name, 0)


@pytest.mark.parametrize(
    "birth, nae, dead, rolls, expected",
    [(0, 0, False, [3], 4), (9, 0, False, [4], 6), (29, 0, False, [5], 8), (49, 0, False, [6], 10),
     (50, 0, False, [7], 12), (0, 1, False, [0, 1], 3), (0, 1, True, [3, 1], 3)],
)
def test_num_child_tentacle(ctx, data, birth, nae, dead, rolls, expected):
    """`@NUM_CHILD_TENTACLE`:579–601（TARGET の出産経験・苗床化・CFLAG:0 を読む）。死亡なら MAX(n/2, 1)。"""
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "出産経験")] = birth
    c.talent[T(data, "苗床化")] = nae
    c.cflag[0] = 9 if dead else 0
    st.rng = FixedRng(rolls)
    assert ninsin.num_child_tentacle(ctx) == expected


@pytest.mark.parametrize(
    "preg, d, c228, small, belly, boob",
    [(1, 10, 300, False, 300, 20), (3, 10, 300, False, 300, 20), (4, 13, 1000, False, 150 * 5 // 48, 0),
     (5, 30, 1000, False, 800 * 22 // 48, 12), (5, 56, 1000, True, 1000 * 48 // 48 * 85 // 100, 25),
     (0, 30, 1000, False, 0, 0)],
)
def test_pregnancy_expand(ctx, data, preg, d, c228, small, belly, boob):
    """`@PREGNANCY_BELLY_EXPAND`:863–893、`@PREGNANCY_BOOB_EXPAND`:844–859。"""
    c = ctx.state.charas[1]
    c.talent[T(data, "妊娠")] = preg
    c.cflag[222] = d
    c.cflag[228] = c228
    c.talent[T(data, "小さな体躯")] = 1 if small else 0
    c.talent[T(data, "妖精族")] = 0
    assert ninsin.pregnancy_belly_expand(ctx, 1) == belly
    assert ninsin.pregnancy_boob_expand(ctx, 1) == boob


# --- BIRTH_HANTEI（:277–410）---------------------------------------------------------------------------


def _preg(data, c, preg, d, n227=3, c228=264):
    c.talent[T(data, "妊娠")] = preg
    c.cflag[222] = d
    c.cflag[227] = n227
    c.cflag[228] = c228


@pytest.mark.parametrize(
    "d, nae, prison, expected",
    [(0, 0, False, 1), (0, 1, False, 3), (0, 0, True, 3), (0, 1, True, 5)],
)
def test_birth_hantei_tentacle_growth(ctx, data, d, nae, prison, expected):
    """:295–302：1 日（半日）+1、苗床化 +3、幽閉中さらに +2。"""
    c = ctx.state.charas[3]
    _preg(data, c, 1, d)
    c.talent[T(data, "苗床化")] = nae
    if prison:
        c.cflag[0] = 1
    ctx.state.rng = FixedRng([])
    list(pregnancy.birth_hantei(ctx))
    assert c.cflag[222] == expected


def test_birth_hantei_matanity_and_birth(ctx, data):
    """CFLAG:222 = 10 > 9：出産直前（CFLAG:0 = 10、:288–293）→ 11（:298）→ > 10：母乳体質（性嗜好フィルタ既定 ON、:305–311）、
    LOCAL:1 = RAND:(30 − 11)（:316）= 0 → 出産（:318）→ BIRTH_TENTACLES（:416–458）。キャラ 3 は最後尾なので並べ替えなし。"""
    st = ctx.state
    c = st.charas[3]
    _preg(data, c, 1, 10)
    c.cflag[34] = 0  # 拡張度の上昇（:566）を起こさない
    c.base[0] = 3000
    c.cflag[99] = 0
    st.rng = ZeroTail([0])
    list(pregnancy.birth_hantei(ctx))
    assert c.cflag[0] == 0 and c.talent[T(data, "母乳体質")] == 1
    # :418 疲労 45 + BELLY/20（妊娠 1：264 × 11 / 10 = 290 → 14）
    assert c.cflag[99] == 45 + 14
    assert st.flag[200] == 3  # :444 触手の欠片 + CFLAG:227
    assert c.talent[T(data, "妊娠")] == 0 and all(c.cflag[k] == 0 for k in (221, 222, 227, 228, 232, 233))
    assert c.exp[E(data, "出産経験")] == 3  # ABL_UP_BIRTH:557–563
    t = texts(ctx.out)
    assert "〈地の文：MESSAGE_MATANITY〉" in t and "触手の欠片＋3" in t


def test_birth_hantei_set_partymember_reorders(ctx, data):
    """原作どおりの並べ替え：キャラ 1 が出産直前になると SET_PARTYMEMBER（:291）で最後尾へ（SHIFTBACK_CHARA）。
    同じ周回の :295–299 は index 1 に繰り上がったキャラ（元のキャラ 2）に対して行われ、元のキャラ 1 は index 3 で再度処理される。"""
    st = ctx.state
    a, b, cc = st.charas[1], st.charas[2], st.charas[3]
    _preg(data, a, 1, 10)
    a.talent[T(data, "苗床化")] = 0
    st.rng = ZeroTail([5, 5])
    list(pregnancy.birth_hantei(ctx))
    assert st.charas[3] is a and st.charas[1] is b and st.charas[2] is cc
    assert b.cflag[222] == 1  # 繰り上がったキャラが +1
    assert a.cflag[0] == 10 and a.cflag[222] == 11  # index 3 で +1（:298）、RAND:19 = 5 → 出産せず


@pytest.mark.parametrize(
    "d, line, preg",
    [(5, "前回から随分と生理が遅れているようだ…", 4), (8, "時折強い吐き気を感じているようだ…", 4),
     (11, "今まで先延ばしにしてきたが、ちゃんと検査をしておいた方が良いだろう…", 4),
     (19, "もう妊娠していることは誰の目にも明らかだ…", 5)],
)
def test_birth_hantei_human_messages(ctx, data, d, line, preg):
    """:329–370 正常妊娠（無自覚）：+1 後の 6／9／12 で兆候、20 以上で 妊娠 5（自覚）。"""
    c = ctx.state.charas[3]
    _preg(data, c, 4, d)
    ctx.state.rng = FixedRng([0])
    list(pregnancy.birth_hantei(ctx))
    assert line in texts(ctx.out) and c.talent[T(data, "妊娠")] == preg


@pytest.mark.parametrize("d, state0", [(42, 0), (43, 10)])
def test_birth_hantei_human_matanity(ctx, data, d, state0):
    """:374–379 妊娠 5 で CFLAG:222 > 42 なら出産直前。:398–403 RAND:(83 − 222) と 53 以上／56 以上で出産。"""
    c = ctx.state.charas[3]
    _preg(data, c, 5, d)
    ctx.state.rng = FixedRng([1])
    list(pregnancy.birth_hantei(ctx))
    assert c.cflag[0] == state0 and c.cflag[222] == d + 1


def test_act_limit_late_pregnancy(ctx, data):
    """`COMMON_BATTLE_FUNC.ERB@ACT_LIMIT`:256–272：妊娠 4／5 で CFLAG:222 >= 56 → RAND:100 < 3 + SQRT(222/4)。"""
    st = ctx.state
    c = st.charas[1]
    _preg(data, c, 5, 60)
    st.rng = FixedRng([5])  # 5 < 3 + SQRT(15) = 6
    assert act_limit(ctx) == 1
    assert "体が竦んでしまった・・・" in texts(ctx.out)


# --- BIRTH_TENTACLES（幽閉中）・ABL_UP_BIRTH -----------------------------------------------------------------


@pytest.mark.parametrize("roll, msg", [(0, "MESSAGE_BIRTH_AINOKO_PRISON"), (1, "MESSAGE_BIRTH_TENTACLES_PRISON")])
def test_birth_tentacles_prison(ctx, data, roll, msg):
    """:424–439：幽閉中は異形出産フィルタ（既定 ON）で RAND:4 == 0 なら合いの子、CFLAG:223 = 1、CFLAG:220・FLAG:44 += 数。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[0] = 1
    c.cflag[21] = 2
    c.cflag[34] = 0
    _preg(data, c, 1, 12, n227=4)
    st.rng = ZeroTail([roll])
    pregnancy.birth_tentacles(ctx)
    assert f"〈地の文：{msg}〉" in texts(ctx.out)
    assert c.cflag[223] == 1 and c.cflag[220] == 4 and st.flag[44] == 4 and st.flag[200] == 0


def test_abl_up_birth_first(ctx, data):
    """:463–574（従順 3 → ×1.00、触手中毒 0 → ×1.00、出産経験 0 → ×0.50：LOCAL = 50）。"""
    st = ctx.state
    c = st.charas[1]
    for k in list(c.abl):
        c.abl[k] = 0
    for k in list(c.juel):
        c.juel[k] = 0
    for k in list(c.exp):
        c.exp[k] = 0
    c.abl[data.index_of("ABL", "従順")] = 3
    c.cflag[34] = 0
    c.base[0] = 3000
    c.maxbase[0] = 2000
    c.base[50] = 1000
    pregnancy.abl_up_birth(ctx, 2)
    assert c.base[0] == 1000 and c.base[1] == 1  # :468–469（気力は新しい BASE:体力 から）
    assert c.juel[20] == 5  # GET_SYUREN LOCAL/10
    assert c.juel[J(data, "快Ｖ")] == 500 and c.juel[J(data, "快Ｂ")] == 500  # :521–524
    assert c.juel[J(data, "恭順")] == 4 * 100 * 50 and c.juel[J(data, "屈服")] == 4 * 250 * 50
    assert c.juel[J(data, "欲情")] == 1250 and c.juel[J(data, "恥情")] == 1250
    assert c.juel[J(data, "苦痛")] == 300 * 50 and c.juel[J(data, "恐怖")] == 100 * 50
    assert c.exp[E(data, "Ｖ経験")] == 5 and c.exp[E(data, "絶頂経験")] == 1 and c.exp[E(data, "苦痛快楽経験")] == 1
    assert c.exp[E(data, "Ｖ拡張経験")] == 1 and c.exp[E(data, "異常経験")] == 1 and c.exp[E(data, "出産経験")] == 2
    assert c.cflag[204] == 1 and c.maxbase[0] == 2500 and c.base[50] == 1250  # :547–556


# --- 苗床出産（BIRTH_AUTO_RANDOM:671–746）---------------------------------------------------------------


def test_nae_birth_static_losedef(ctx, data):
    """取り込まれ（CFLAG:0 = 9）＋苗床化、RAND:4 == 0。NUM_CHILD_TENTACLE は TARGET（キャラ 1、出産経験 0）を読む：
    1 + RAND:4。LOSEDEF は static（:607）で累積し、母乳体質／膨乳改造値（:729–732）は TARGET に付く（原作どおり）。"""
    st = ctx.state
    st.flag[852] = 20000  # :618 の RAND:200 == 0 を避ける値 → [1]
    c3 = st.charas[3]
    c3.cflag[0] = 9
    c3.talent[T(data, "苗床化")] = 1
    st.target = 1
    # :618 RAND:200、:675 RAND:4、NUM_CHILD RAND:4、PRINTDATA ×4、RAND(2,4)
    st.rng = FixedRng([1, 0, 1, 0, 0, 0, 0, 1])
    turnend.birth_auto_random(ctx)
    assert st.flag[852] == 20000 - 2 * 3 and st.flag[44] == 2
    assert st.charas[1].talent[T(data, "母乳体質")] == 1 and c3.talent[T(data, "母乳体質")] == 0
    assert st.charas[1].talent[T(data, "膨乳改造値")] == 10
    st.rng = FixedRng([1, 0, 1, 0, 0, 0, 0, 0])
    turnend.birth_auto_random(ctx)
    assert st.flag[852] == 20000 - 6 - (6 + 4)  # 2 回目は LOSEDEF = 6 + 2×2


# --- 出産（人間相手：PREGNANT_CHILD_BIRTH_N.ERB）-----------------------------------------------------------


def _human_birth(ctx, data, money, papa=-3):
    st = ctx.state
    c = st.charas[3]
    _preg(data, c, 5, 56, n227=0, c228=266)
    c.cflag[0] = 10
    c.cflag[230] = papa
    c.cflag[34] = 0
    st.money = money
    st.rng = ZeroTail([])
    st.target = 3
    return c


def test_birth_human_hospital_cradle(ctx, data):
    """病院（CFLAG:0 = 10）、所持金 $10000 → INPUT [1]：$10000 を払い育児中（CFLAG:0 = 11、:157–161）。
    疲労 45 + BELLY/20（妊娠 5・222 = 56：266 × 48 / 48 = 266 → 13）。愛する人 → CFLAG:219++（:116–118）。"""
    c = _human_birth(ctx, data, 10000)
    c.cflag[99] = 0
    run_inputs(child.birth_daughter_human_origin(ctx), [7, 1])
    st = ctx.state
    assert st.money == 0 and c.cflag[0] == 11 and c.cflag[219] == 1
    assert c.cflag[99] == 45 + 13 and c.talent[T(data, "妊娠")] == 0 and c.cflag[222] == 0
    t = texts(ctx.out)
    assert "正しい数値を入力してください" in t and "やはり、母親の居ない子供にしてしまうわけにはいかない。" in t


def test_birth_human_hospital_no_money(ctx, data):
    """所持金不足 → 選択肢なし（:177–194）、手放して RECOVER_TO_PARTY。"""
    c = _human_birth(ctx, data, 9999, papa=-4)
    run_inputs(child.birth_daughter_human_origin(ctx), [])
    t = texts(ctx.out)
    assert "（資金不足なので選択肢を省略します）" in t and "熟考の末、子供を施設に預けて忘れることにしました。" in t
    assert c.cflag[0] == 0 and c.cflag[219] == 0


def test_birth_human_hook_sets_child_sex(ctx, data, svc):
    """MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN（catalog）:729–735 の RAND:2 と CFLAG:TARGET:226（hook）。"""
    c = _human_birth(ctx, data, 0)
    cctx = Ctx(ctx.state, data, TextOutput(), svc)
    ctx.state.rng = ZeroTail([1])
    child.message_birth_daughter_human_origin(cctx)
    assert c.cflag[226] == 1
    assert "「頑張りましたねー。はい、元気な男の子ですよー」" in texts(cctx.out)


def test_ninsin_hook_table_matches_erb(svc):
    cat = svc.catalog
    for (func, line), (text, _) in NINSIN_HOOK_LINES.items():
        e = cat.index[func]
        assert dict(cat.lines_of(e.rel))[line].strip() == text, (func, line)
    # 地の文/MESSAGE_NINSIN.ERB の全関数：非 LOCAL 代入は表にある 2 行だけ
    e0 = cat.index["MESSAGE_NINNSIN"]
    for no, s in cat.lines_of(e0.rel):
        s = s.strip()
        if re.match(r"^(FLAG|CFLAG|TALENT|BASE|EXP|ABL|TFLAG|MARK|MONEY|JUEL|CSTR)\b[^=]*[-+*/|&]?=(?!=)", s):
            assert ("MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN", no) in NINSIN_HOOK_LINES, (no, s)
    for name in ("MESSAGE_NINNSIN", "MESSAGE_NINNSIN_TS_FIX", "MESSAGE_MATANITY", "MESSAGE_BIRTH_TENTACLES",
                 "MESSAGE_BIRTH_TENTACLES_PRISON", "MESSAGE_BIRTH_AINOKO_PRISON", "MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN",
                 "MESSAGE_BIRTH_DAUGHTER_HUMAN_ORIGIN_PRISON", "MESSAGE_CHILD_CRADLE", "MESSAGE_CHILD_ASLYM"):
        assert cat.unsupported_reason(name) is None, name


# --- GROW_HANTEI・ADD_CHILD ---------------------------------------------------------------------------


def test_grow_hantei_days(ctx, data):
    """:10–15 育児中 CFLAG:224 += 1、4 以上で RAND:2 == 0 または 10 以上で ADD_CHILD。"""
    st = ctx.state
    c = st.charas[3]
    c.cflag[0] = 11
    c.cflag[224] = 2
    st.rng = FixedRng([])
    list(child.grow_hantei(ctx))
    assert c.cflag[224] == 3 and st.charanum == 4


def _add_child_run(ctx, data, inputs, papa=-3, sex=0):
    st = ctx.state
    m = st.charas[3]
    m.cflag[0] = 11
    m.cflag[224] = 9
    m.cflag[230] = papa
    m.cflag[226] = sex
    m.mark[data.index_of("MARK", "血族補正")] = 2
    m.talent[T(data, "人間")] = 0  # 母親はケモミミ族（209）→ 変身能力は RAND:4 == 0 のときだけ
    st.rng = GameRng(7)
    run_inputs(child.grow_hantei(ctx), inputs)
    return m, st.charas[4]


def test_add_child_full(ctx, data):
    """育児中の母親（キャラ 3）：+1 で 10 → ADD_CHILD（:14）。INPUT：名前 [0] ランダム → [1] 英語 → [1] はい →
    フルネーム [0] 苗字なし → フィート [1] 設定しない（変身能力が付けば変身後名 [0] → かけ声 [0] → 名乗り [0]）。"""
    st = ctx.state
    before8 = st.flag[8]
    m, c = _add_child_run(ctx, data, [0, 1, 1, 0, 1, 0, 0, 0])
    assert st.charanum == 5 and c.no == 0
    assert st.flag[8] == before8 + 1 and c.cflag[240] == st.flag[8]  # :307–308
    assert c.cflag[7] == m.cflag[240] and c.cflag[9] == -3  # :310、:701
    assert c.name == c.callname and c.cstr[10] == ""  # [0] 苗字なし（:470–472）
    assert c.talent[209] == 1 and c.cflag[231] == 209  # 母親依存の種族（:523–532）
    assert c.talent[T(data, "処女")] == 1 and c.talent[T(data, "パイパン")] == 1 and c.talent[T(data, "未熟")] == 1
    assert all(c.talent[101 + 2 * k] == 1 for k in range(4))  # :697–699 鈍感
    # PAPA_POWER 0（一般人：:778–779）→ 基礎値は母親の 6/10（:814–816）
    assert c.base[50] == m.base[50] * 6 // 10 and c.maxbase[50] == c.base[50]
    assert c.cflag[60] == m.base[50] * 6 // 10 - 1000  # :828（性格決定前：SEIKAKU_CHECK_F = 0 → 補正なし、CSVBASE 0:体力 1000）
    assert c.mark[data.index_of("MARK", "血族補正")] == 3  # :919
    # GROW_HANTEI の同じ周回で :16–25 は新キャラに対して行われる：CFLAG:225 = 1 → 2
    assert c.cflag[225] == 2 and m.cflag[225] == 0
    assert c.base[40] == 0 and 6 <= c.base[41] <= 10  # :1042–1046
    assert c.cstr[4] == "私" or c.cflag[8] in (25, 26, 27, 30, 31, 32)  # SELFCALL [99]（:1475）
    assert m.cflag[0] == 0 and m.cflag[224] == 0 and c.cflag[0] == 0  # :1083–1089 RECOVER_TO_PARTY
    # CHECK_ALL_RELATION：CFLAG:7 から親子（:576–588）、双方向
    assert (c.relation[3] >> 20) & 1 and (m.relation[4] >> 20) & 1
    # :576–588 の親子設定は WAITFLAG を増やさないので表示なし、母親の処女消去（:950–958）は母親の周回（CHARA = 3）が
    # 子供（CHARA = 4）より先なので起きない（原作どおり）
    assert not any("』は【" in x for x in texts(ctx.out))
    assert st.target == 1  # :27 で復元
    raw = dump_save(st)  # 存讀檔往返
    assert dump_save(load_save(raw)[0]) == raw


def test_add_child_male_and_surname(ctx, data):
    """CFLAG:ARG:226 > 0 → オトコ（:312–314）、Ｖ系の素質なし（:786–793）。フルネーム [1]：母姓 苗字 名前（:473–475）。"""
    m, c = _add_child_run(ctx, data, [0, 0, 1, 1, 1, 0, 0, 0], sex=1)
    assert c.talent[T(data, "オトコ")] == 1 and c.talent[T(data, "処女")] == 0 and c.talent[T(data, "Ｖ鈍感")] == 0
    assert c.cstr[10] == m.cstr[10] and c.name == f"{m.cstr[10]} {c.callname}"
    assert m.cflag[226] == 0  # :319


def test_add_child_manual_name_stops(ctx, data):
    st = ctx.state
    st.charas[3].cflag[0] = 11
    st.charas[3].cflag[224] = 9
    st.rng = GameRng(7)
    gen = child.grow_hantei(ctx)
    next(gen)
    with pytest.raises(NotImplementedError, match="手入力"):
        gen.send(1)


@pytest.mark.parametrize(
    "papa, power", [(1, 10), (5, 10), (150, 15), (250, 1), (-102, 4), (-3, 0)],
)
def test_add_child_papa_power(ctx, data, papa, power):
    """:704–784 父親別の PAPA_POWER → :796–803 BASE:体力基礎 = 母×6/10 + 15×P + RAND:(40×P)（P = 0 なら加算なし）。"""
    m, c = _add_child_run(ctx, data, [0, 0, 1, 0, 1, 0, 0, 0], papa=papa)
    lo = m.base[50] * 6 // 10 + 15 * power
    assert lo <= c.base[50] < lo + max(40 * power, 1)
    assert ctx.state.temp.locals[("ADD_CHILD:PAPA_POWER", 0)] == power
    if papa == 1:
        assert c.talent[T(data, "Ｃ敏感")] == 1 and c.talent[T(data, "Ｃ鈍感")] == 0 and (c.relation[4] >> 1) & 1


def test_child_grow_1(ctx, data):
    """:1113–1145：未熟を失う、25% でパイパンでなくなる、鈍感は 80% で取れる、年齢 +1〜5 と体格の再計算。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "未熟")] = 1
    c.talent[T(data, "パイパン")] = 1
    for k in range(4):
        c.talent[101 + 2 * k] = 1
    c.cflag[225] = 7
    age = c.base[41]
    st.rng = FixedRng([0, 0, 99, 0, 99, 4])  # RAND:4 == 0、鈍感 C:0<80 V:99 A:0 B:99、年齢 +5
    child.child_grow_1(ctx)
    assert c.talent[T(data, "未熟")] == 0 and c.talent[T(data, "パイパン")] == 0
    assert [c.talent[101 + 2 * k] for k in range(4)] == [0, 1, 0, 1]
    assert c.base[41] == age + 5 and "一次性徴" in texts(ctx.out)


def test_child_grow_2(ctx, data):
    """:1150–1205（女性）。RAND の順：パイパン（RAND:4 != 0）、各部位（左辺 RAND:100 が偽なら ELSEIF で再度 RAND:100）、
    胸・濡れ・回復・体格（RAND:100）、年齢 RAND:5。"""
    st = ctx.state
    c = st.charas[1]
    for name in ("パイパン", "貧乳", "濡れにくい", "回復早い", "小柄"):
        c.talent[T(data, name)] = 1
    for k in range(4):
        c.talent[100 + 2 * k] = 0
        c.talent[101 + 2 * k] = 1
    st.rng = FixedRng([1, 0, 90, 90, 90, 90, 90, 90, 0, 0, 0, 0, 0])
    child.child_grow_2(ctx)
    assert c.talent[T(data, "パイパン")] == 0
    assert c.talent[101] == 0  # C：0 < 80 → 鈍感が取れる
    assert [c.talent[100 + 2 * k] for k in (1, 2, 3)] == [1, 1, 1]  # V・A・B：左辺偽 → RAND:100 = 90 > 80 → 敏感
    assert c.talent[T(data, "貧乳")] == 0 and c.talent[T(data, "濡れにくい")] == 0
    assert c.talent[T(data, "回復早い")] == 0 and c.talent[T(data, "小柄")] == 0


# --- 相関関係・フィート・キャラ設定 ----------------------------------------------------------------------------


def test_check_all_relation_siblings(ctx, data):
    """母親 3 の子供 1・2（CFLAG:7 = 3）：親子（:576–588）→ 同じ親を持つので兄弟姉妹（:596–611）。
    TOSHIUE_F：実年齢が上（同じなら CFLAG:240 が小さい方）。"""
    st = ctx.state
    m, a, b = st.charas[3], st.charas[1], st.charas[2]
    m.base[40], a.base[40], b.base[40] = 40, 10, 8
    a.cflag[7] = b.cflag[7] = m.cflag[240]
    relation.check_all_relation(ctx)
    assert relation.get_relation(ctx, 1, 2) == "妹" and relation.get_relation(ctx, 2, 1) == "姉"
    assert relation.get_relation(ctx, 3, 1) == "娘" and relation.get_relation(ctx, 1, 3) == "母親"
    assert m.talent[T(data, "処女")] == 0


def test_set_feat_default_takes_all_candidates(ctx, data):
    """`SET_FEAT_DEFAULT`:1500–1776（人間）：RAND:8 = 1、RAND:4 = 1 → 枠 3、RAND:4 = 1（!= 0）→ プリセット、
    RAND:4 = 0 → 平凡（枠 2）、RAND:2 = 0 → 枠 1。枠 > 0 なので残りの取得可能フィート 5 個をすべて取得（:1767 の FOR 終端は
    開始時の候補数：Instraction.Child.cs:1731–1743）。"""
    st = ctx.state
    c = st.charas[1]
    for f in range(1100, 1300):
        c.talent[f] = 0
    st.rng = FixedRng([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    firstsetting.set_feat_default(ctx, 1, 201)
    got = sorted(data.names["TALENT"][f] for f in range(1100, 1300) if c.talent[f])
    assert got == sorted(("平凡", "巻き込まれ体質", "秘められし力", "ラッキーチャーム", "祝福", "不屈"))
    assert st.temp.randchoose[0] == 0


def test_feat_select_ui(ctx, data):
    """ADD_CHILD:549–627：[1100]〜 で切り替え、[0] で決定（3 個以下）。"""
    c = ctx.state.charas[1]
    for f in range(1100, 1300):
        c.talent[f] = 1
    run_inputs(firstsetting.feat_select_ui(ctx, 1, 201), [5, 100, 200, 0])
    assert c.talent[1100] == 1 and c.talent[1200] == 1
    assert sum(c.talent[f] for f in range(1100, 1300)) == 2


@pytest.mark.parametrize("c8, call", [(0, "私"), (27, "ボク"), (31, "おれ")])
def test_selfcall_default(ctx, data, c8, call):
    """FIRSTSETTING_CHARA_SELFCALL を [99] で決定：CFLAG:8 は同値、CSTR:4 = SELF_CALL_LIST(CFLAG:8/5%20, CFLAG:8%5)。"""
    c = ctx.state.charas[1]
    c.cflag[8] = c8
    c.cstr[4] = ""
    firstsetting.selfcall_default(ctx, 1)
    assert c.cflag[8] == c8 and c.cstr[4] == call


def test_size_setting_default(ctx, data):
    """SIZE_SETTING を [99] で決定：パーソナリティを前に詰める（:1731–1745）。変身能力なし → MAXBASE:年齢 = −1 のまま。"""
    c = ctx.state.charas[1]
    c.talent[T(data, "変身能力")] = 0
    c.cstr[40], c.cstr[41], c.cstr[42] = "", "", "明るい"
    c.maxbase[41] = -1
    firstsetting.size_setting_default(ctx, 1)
    assert (c.cstr[40], c.cstr[41], c.cstr[42]) == ("明るい", "", "")
    assert c.maxbase[41] == -1


def test_tentacle_bitvalue(ctx):
    st = ctx.state
    assert tentacle_bitvalue(st, 7) == 64
    st.flag[10] = 1  # ラスボス
    assert tentacle_bitvalue(st, 2) == 2
    with pytest.raises(NotImplementedError):
        tentacle_bitvalue(st, 3)


# --- 救出された娘（RESCUE_CHILD:1210–1299）------------------------------------------------------------------


@pytest.mark.parametrize("money, inputs, kept", [(5000, [1], True), (5000, [0], False), (4999, [], False)])
def test_rescue_child(ctx, data, money, inputs, kept):
    st = ctx.state
    st.add_chara(data, 0)
    d = st.charas[4]
    d.callname = "ミク"
    d.cflag[7] = st.charas[1].cflag[240]
    d.cflag[6] = -1
    d.cflag[0] = -1
    st.money = money
    r = run_inputs(child.rescue_child(ctx, 4), inputs)
    assert (st.charanum == 5) == kept and r == (0 if kept else -1)
    if kept:
        assert d.cflag[6] == 0 and d.cflag[0] == 0 and st.money == 0


# --- 整合：受精 → 數回合 → 出産 → SHOP ------------------------------------------------------------------------


def test_integration_pregnancy_to_birth(ctx, data):
    """幽閉されていないキャラ 3 が戦闘外で触手の子を身ごもった（妊娠 1）状態から BIRTH_HANTEI を回し、出産（:318）まで。"""
    st = ctx.state
    c = st.charas[3]
    _preg(data, c, 1, 0, n227=2, c228=176)
    c.cflag[34] = 0
    st.rng = GameRng(11)
    for _ in range(40):
        list(pregnancy.birth_hantei(ctx))
        if c.talent[T(data, "妊娠")] == 0:
            break
    assert c.talent[T(data, "妊娠")] == 0 and c.exp[E(data, "出産経験")] == 2 and c.cflag[0] == 0
    raw = dump_save(st)
    assert dump_save(load_save(raw)[0]) == raw
