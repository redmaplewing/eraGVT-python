"""S27：ラスボス（Ｋ触手）と結局（ENDING_2／3／6・SCORE）。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`、行號は註解）。触手 Lv（TENTACLE_LEVEL）は入力値として使う。
"""

from __future__ import annotations
from _gen_driver import run_no_input
from eragvt.game.prison.event import prison_routine

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import ending, shop
from eragvt.game.action import Ctx, Step, config_check_maniac
from eragvt.game.battle import encount, gaping, source_check, train
from eragvt.game.battle.core import BeginAfterTrain, BeginTurnend, lastboss_attack_routine, tentacle_access, tentacle_level
from eragvt.game.battle.sexcom import lastboss_reaction_ref, lastboss_sex_routine
from eragvt.game.era import div, isqrt
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.prison.event import tentacle_access_prison
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.state.savefile import load_from_file
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1、TIME=0、TARGET=1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def _lastboss_battle(st) -> None:
    """全ボス撃破済み・Ｋ触手と戦闘中（ENCOUNT.ERB:372–384 後の FLAG）。"""
    st.flag[100] = 0
    st.flag[101] = 1
    st.flag[10] = 1
    st.flag[11] = 1
    st.flag[110] = 0
    st.flag[73] = 0
    st.savestr[13] = "BOSS"


# --- データ（TENTACLE_LASTBOSS_1_Ｋ触手.ERB）---------------------------------------------------------


def test_k_tentacle_data(ctx):
    st = ctx.state
    _lastboss_battle(st)
    lv = tentacle_level(st)
    h = lambda v, b=100: div((lv * 10 + 95) * v, 100) + b  # noqa: E731  TENTACLE_STATUS_HOSEI（COMMON_TENTACLE_DATA.ERB:348–352）
    assert tentacle_access(ctx, "GETNAME") == "Ｋ触手"  # :7–8
    assert tentacle_access(ctx, "HP") == h(30000, 2000)  # :18–21
    assert tentacle_access(ctx, "SYASEI") == 1250 + lv * 25  # :25–28
    assert tentacle_access(ctx, "YUDAN") == 2260
    assert tentacle_access(ctx, "KOUGEKI") == h(300)  # :44–47
    assert tentacle_access(ctx, "BOUGYO") == h(200, 50)  # :51–54
    assert tentacle_access(ctx, "BINSYOU") == h(100, 50)  # :58–61
    assert tentacle_access(ctx, "CHISEI") == h(65, 10)  # :65–68
    assert [tentacle_access(ctx, k) for k in ("SHORT", "MIDDLE", "LONG", "HOLD")] == [150, 150, 150, 200]


def test_lastboss_access_ignores_flag10(ctx):
    """COMMON_TENTACLE_DATA.ERB:202：ラスボス出現後（FLAG:101 = 1）は FLAG:10 に関わらずラスボス側。FLAG:11 = 0
    （悪堕ちキャラ戦）は TENTACLE_LASTBOSS_0_GETNAME が無く、:200 のエラー文字列のまま。"""
    st = ctx.state
    _lastboss_battle(st)
    st.flag[10] = 0
    st.flag[11] = 0
    assert tentacle_access(ctx, "GETNAME") == "【エラー：BOSS_0に対するTENTACLE_ACCESS('GETNAME')関数失敗】"


@pytest.mark.parametrize(
    ("roll", "bougyo", "yudan", "expected"),
    [
        (34, 100, True, 4),  # :134–135 油断（FLAG:17 >= FLAG:16）かつ RAND < 35
        (35, 100, True, 1),  # 35 は不成立 → :145 < 50 → 1
        (4, 300, False, 1),  # :137 LOCAL:2 = 100、4 < 50 → :138 < 5 → 1
        (20, 300, False, 3),  # :140 < 35 → 3
        (40, 300, False, 2),  # :142 ELSE → 2
        (60, 300, False, 2),  # 60 < 50 不成立 → :147 < 74 → 2
        (80, 100, False, 3),  # LOCAL:2 = -100（< -50 不成立）→ :149 < 98 → 3
        (98, 100, False, 4),  # :151 ELSE → 4
    ],
)
def test_k_attack_routine(ctx, roll, bougyo, yudan, expected):
    st = ctx.state
    _lastboss_battle(st)
    st.charas[1].base[ctx.data.index_of("BASE", "防御")] = bougyo
    st.flag[16], st.flag[17] = (100, 100) if yudan else (100, 0)
    st.rng = FixedRng([roll])
    assert lastboss_attack_routine(ctx) == expected


@pytest.mark.parametrize(("roll", "expected"), [(0, 1000), (9, 1001), (39, 1007), (40, 1015), (49, 1015), (50, -1)])
def test_k_sex_routine(ctx, roll, expected):
    ctx.state.rng = FixedRng([roll])
    assert lastboss_sex_routine(ctx, 1) == expected  # :158–180


@pytest.mark.parametrize(("arg", "rolls", "expected"), [(1, [1], 3), (1, [3], 5), (1, [4], 1001), (1, [5], 1002),
                                                        (2, [], 15), (3, [], 11), (0, [], -1)])
def test_k_reaction_ref(ctx, arg, rolls, expected):
    ctx.state.rng = FixedRng(rolls)
    assert lastboss_reaction_ref(ctx, 1, arg) == expected  # :187–204


def test_set_tentacle_size_lastboss(ctx):
    """GAPING.ERB:1131–1135（LOCAL = SQRT((Lv*6+35)*150)、極端サイズ OFF で SQRT(LOCAL*75)）＋Ｋ触手 :244–257、:1159–1169。"""
    st = ctx.state
    _lastboss_battle(st)
    lv = tentacle_level(st)
    # [C 本数 RAND:5, V RAND:3, A RAND:3, B RAND:5, C 幅 RAND:161, V RAND:21, A RAND:21, B RAND:91]
    st.rng = FixedRng([4, 2, 0, 1, 0, 20, 0, 90])
    gaping.set_tentacle_size(ctx, 1, 1, 0, 0, 3)
    assert st.rng.snapshot() == []
    # 初期セットは CONFIG_CHECK_MANIAC_F(20)（極端なサイズ）ON → :1076–1077 RESULT*10、:1133–1134 の抑制なし
    assert config_check_maniac(st, 20) == 1
    local = isqrt((lv * 10 * 6 + 35) * 150)
    sz, num = st.temp.tentacle_size, st.temp.tentacle_num
    assert [sz[(0, i)] for i in range(4)] == [div(local * 90, 520) + 2, div(local * 120, 110), div(local * 120, 90),
                                              div(local * 90, 345) + 5]
    assert [num[(0, i)] for i in range(4)] == [5, 3, 1, 2]
    assert [st.result[i] for i in range(1, 8)] == [120, 120, 90, 5, 3, 1, 2]  # 8 値 RETURN（RESULT:0 は終端で 0）


# --- 遭遇（ENCOUNT.ERB@ENCOUNT_BOSS:309–421）-------------------------------------------------------


def _ready_lastboss(st):
    st.flag[100] = 0
    st.flag[101] = 1
    st.flag[47] = st.flag[46]
    st.charas[1].cflag[100] = 101


def test_encount_lastboss_hit(ctx):
    st, data = ctx.state, ctx.data
    _ready_lastboss(st)
    st.flag[401] = 25000000  # 蓄積ダメージ 25％
    # [ENCOUNT_ENEMY:74 RAND:100, :333 RAND:100（昼 70*28/28 = 70 > 69）, RANDCHOOSE_F RAND:1]
    st.rng = FixedRng([99, 69, 0])
    assert encount.encount(ctx) == 1
    assert st.rng.snapshot() == []
    lv = tentacle_level(st)
    assert (st.flag[10], st.flag[11], st.savestr[13]) == (1, 1, "BOSS")  # :306、:372、:384
    hp = div((lv * 10 + 95) * 30000, 100) + 2000
    assert st.flag[12] == hp  # LASTBOSS_KYOUKA_F = 1（FLAG:803 bit5 OFF）
    assert st.flag[13] == div(hp * 750000, 1000000)  # :394
    assert (st.flag[14], st.flag[16], st.flag[22]) == (1250 + lv * 25, 2260 + lv * 10, 0)  # :400–410
    assert st.charas[1].exp[data.index_of("EXP", "ラスボス経験")] == 1
    t = texts(ctx.out)
    assert t[-5:-1] == [f"Ｋ触手 Lv.{lv} と遭遇した！", "（数十メートルはある巨大な図体をしたラスボス触手）",
                        "（その禍々しい威容はまさしく触手たちの王を名乗るにふさわしい）", "・・・・・・・・・・・・・・・"]


def test_encount_lastboss_miss_and_kyouka(ctx):
    st = ctx.state
    _ready_lastboss(st)
    st.rng = FixedRng([99, 70])  # 70 > 70 不成立 → SELECT = 0 → :365–366 RETURN 0
    assert encount.encount(ctx) == 0
    st.flag.set_bit(803, 5, True)  # [55] ラスボス強化（LASTBOSS_POWERUP.ERB:5–13）→ HP 5 倍
    st.rng = FixedRng([99, 0, 0])
    assert encount.encount(ctx) == 1
    lv = tentacle_level(st)
    assert st.flag[12] == (div((lv * 10 + 95) * 30000, 100) + 2000) * 5


# --- 勝利（BATTLE_COM_AFTER.ERB@SOURCE_CHECK:117–308）---------------------------------------------


def test_victory_lastboss_perfect(ctx):
    """Ｋ触手撃破：:173 蓄積ダメージ 0、:186–188 FLAG:64 = -1、:192–193 FLAG:101 のビット 0 を落とす → :279–306 完全殲滅 →
    BEGIN TURNEND（@EVENTEND を通らない）。:204–262 Ｋ触手（CFLAG:20 = 1、CFLAG:21 = 1）に捕らわれたキャラは救出。"""
    st = ctx.state
    _lastboss_battle(st)
    st.flag[13] = 0
    st.flag[401] = 5000
    st.flag[18] = 1
    st.flag[700] = 1
    cap = st.charas[2]
    cap.cflag[0], cap.cflag[20], cap.cflag[21] = 1, 1, 1
    with pytest.raises(BeginTurnend):
        source_check._victory(ctx)
    assert (st.flag[64], st.flag[101], st.flag[401], st.flag[18], st.flag[49]) == (-1, 0, 0, 0, 1)
    assert st.tflag[98] == 1 and st.flag[700] == 1
    assert cap.cflag[0] == -1
    t = texts(ctx.out)
    assert "Ｋ触手の殲滅完了！" in "".join(t)
    s2500 = ctx.data.str_defaults.get(2500, "")
    assert f"全ての{s2500}を完全殲滅しました！！" in t  # MESSAGE_BATTLE.ERB:1673–1679


def test_victory_last_boss_tentacle_makes_lastboss_appear(ctx):
    """最後のボス（Ｃ触手）撃破：:266–276 FLAG:101 = 1、MESSAGE_BATTLE_END_LASTBOSSAPPEAR → BEGIN AFTERTRAIN。"""
    st, data = ctx.state, ctx.data
    st.flag[100] = 1
    st.flag[101] = 0
    st.flag[10], st.flag[11], st.flag[13] = 0, 1, 0
    st.savestr[13] = "BOSS"
    with pytest.raises(BeginAfterTrain):
        source_check._victory(ctx)
    assert (st.flag[100], st.flag[101], st.flag[64]) == (0, 1, 0)
    t = texts(ctx.out)
    assert f"全ての{data.str_defaults.get(2502, '')}を殲滅しました！" in t
    assert f"{data.str_defaults.get(2503, '')}が出現しました！" in t


def test_victory_lastboss_hardcore_second_cycle(ctx):
    """:176–180 周回（FLAG:854 > 0）＆HARDCORE でＫ触手撃破 → FLAG:4 += 1、FLAG:1 += 5、FLAG:21 = 1 → :270–272 裏ボス出現
    （ENEMY_TYPE_CHECK_F("LASTBOSS") = 1 + FLAG:21 = 2）。"""
    from eragvt.state.constants import GameOption

    st = ctx.state
    _lastboss_battle(st)
    st.flag[13] = 0
    st.flag[854] = 1
    st.flag.set_bit(0, GameOption.HARDCORE, True)
    f1, f4 = st.flag[1], st.flag[4]
    with pytest.raises(BeginAfterTrain):
        source_check._victory(ctx)
    assert (st.flag[4], st.flag[1], st.flag[21], st.flag[101], st.flag[64]) == (f4 + 1, f1 + 5, 1, 2, 0)
    assert "なにやら様子がおかしい……" in texts(ctx.out)


def test_integration_lastboss_battle_to_turnend(ctx):
    """FLAG:401 = 100%（ENCOUNT.ERB:394–398 で FLAG:13 = 1）→ 最初の攻撃で撃破 → run_train は Step.TURNEND。"""
    st = ctx.state
    _ready_lastboss(st)
    st.flag[401] = 100000000
    st.rng = FixedRng([99, 0, 0])
    assert encount.encount(ctx) == 1
    assert st.flag[13] == 1
    st.rng = GameRng(1)  # 先制攻撃が命中する系列（命中しないと Lv.22 のＫ触手に一撃で気絶させられる）
    gen = train.run_train(ctx)
    next(gen)
    with pytest.raises(StopIteration) as ex:
        gen.send(1)
    assert ex.value.value == Step.TURNEND
    assert st.flag[700] == 1  # @EVENTEND（:7 FLAG:700 = 0）を通らない
    assert st.flag[64] == -1 and st.flag[101] == 0


# --- 幽閉（COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:329–342）--------------------------------


def test_prison_by_k_tentacle(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[20], c.cflag[21] = 1, 1
    assert tentacle_access_prison(ctx, 1, "GETNAME") == "Ｋ触手"
    # :338–339 は TENTACLE_BOSS_{CFLAG:21}_PALAM_HOSEI（Ｃ触手：TENTACLE_BOSS_1_Ｃ触手.ERB:96–125）
    assert tentacle_access_prison(ctx, 1, "PALAM_HOSEI") == (120, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100)
    st.rng = FixedRng([85])  # TENTACLE_LASTBOSS_1_Ｋ触手.ERB:237–238 ELSE → RETURN 0
    assert run_no_input(prison_routine(ctx, 1)) == 0


# --- SHOP 表示 -----------------------------------------------------------------------------------


def test_shop_boss_info_lastboss(ctx):
    """SHOP_SHOW_BOSS_INFO.ERB:104–152：REPEAT FLAG:4、索敵なし → [Ｋ触手]、FLAG:11 は戻す（:153）。"""
    st = ctx.state
    st.flag[100] = 0
    st.flag[101] = 1
    st.flag[11] = 0
    out = TextOutput()
    shop.shop_show_boss_info(st, ctx.data, out)
    joined = "".join(ln.text for ln in out.lines)
    assert "[Ｋ触手]" in joined
    assert st.flag[11] == 0


def test_situation_list_lastboss(ctx):
    """SHOP_SHOW_SITUATION_LIST.ERB:26–38：現在活動中の %STR:2503%、[Ｋ触手]、FLAG:11 は戻さない。"""
    st, data = ctx.state, ctx.data
    _lastboss_battle(st)
    st.flag[11] = 0
    shop.shop_show_situation_list(st, data, ctx.out, NullNarrationService())
    t = texts(ctx.out)
    assert f"現在活動中の{data.str_defaults.get(2503, '')}" in t
    assert "[Ｋ触手]" in t
    assert st.flag[11] == 1


# --- 結局 -----------------------------------------------------------------------------------------


def test_score_values(ctx):
    """SCORE.ERB：生存（全員無事 → 100 → S=6）、日数（(FLAG:1 - DAY) * 100 / FLAG:2）、純潔、性成長、人気、資産。"""
    st, data = ctx.state, ctx.data
    st.day[0] = 30
    f1, f2 = st.flag[1], st.flag[2]
    l1, l2, l3, l4, l5, l6, total = ending.score_values(ctx)
    assert l1 == 6
    d = div((f1 - 30) * 100, f2)
    assert l2 == (1 if d < 30 else 2 if d < 70 else 3 if d < 110 else 4 if d < 150 else 5 if d < 190 else 6)
    assert total == div(l1 + l2 + max(l3, l4) + l5 + div(l6, 2) + 3, 5)  # :441–447
    # 1 人が幽閉中：LOCAL = 100 - 60 / (CHARANUM - 1)（:36–37）
    st.charas[2].cflag[0] = 1
    n = st.charanum - 1
    local = 100 - div(60, n)
    assert ending.score_values(ctx)[0] == (1 if local < 40 else 2 if local < 55 else 3 if local < 70 else 4 if local < 85
                                           else 5 if local < 100 else 6)


def test_score_hikan_and_popularity(ctx):
    st, data = ctx.state, ctx.data
    e = data.index_of("EXP", "被姦経験")
    for i in range(1, st.charanum):
        st.charas[i].exp[e] = 0
    st.flag[853] = 45  # :378 非ソロ LOCAL < 50 → 5
    r = ending.score_values(ctx)
    # :119–125：処女かつ清純派のキャラ数だけ -1 → 0 以下 → S（6）
    assert r[2] == 6
    assert r[4] == 5
    st.charas[1].exp[e] = 10  # 処女・清純派でなければ ×2
    st.flag[853] = -10
    r = ending.score_values(ctx)
    assert r[4] == 1


def test_start_succession_refund_then_menu(ctx):
    """ENDING.ERB:29–69：施設 Lv（FLAG:50／51：REPEAT の COUNT 1 から）と FLAG:52・FLAG:53 を資金に還元して JUMP SUCCESSION（等待選單）。"""
    st = ctx.state
    st.flag[50], st.flag[51], st.flag[52], st.flag[53] = 3, 2, 1, 1 | 2048
    money = st.money
    gen = ending.start_succession(ctx)
    next(gen)
    assert any("データ引き継ぎ" in ln.text for ln in ctx.out.lines)
    gen.close()
    assert st.money == money + (10000 + 15000) + 2000 + 10000 + 500 + 100000


def test_ending_2_text(ctx):
    st = ctx.state
    st.charas[2].cflag[0] = 2  # 洗脳中 → :355–365
    st.rng = FixedRng([0])  # PRINTDATAL RAND:6
    ending.ending_2(ctx)
    t = texts(ctx.out)
    assert f"洗脳されていた{st.charas[2].callname}もまた、自分を取り戻すことができた。" in t
    assert "南極に突如出現した\"超空間通路\"から、謎の敵が飛来し都市を襲い始めたのだ。" in t
    assert "お疲れ様でした" in t


def test_ending_6_dead_code_text(ctx):
    st = ctx.state
    ending.ending_6(ctx)
    assert (st.flag[0], st.flag[999]) == (0, -998)  # :745–747
    assert "全滅した・・・" in texts(ctx.out)


# --- 整合（GameSession）---------------------------------------------------------------------------


def _session(data, tmp, seed=3):
    s = GameSession(data, Path(tmp), rng=GameRng(seed))
    s.input(0)
    s.input(1)  # MODE_SELECT NORMAL
    for value in (200, 0, 1): s.input(value)  # CHARA_MAKE_MAIN 套組0確認
    s.input(1000)  # CHARA_MAKE_MAIN 完成
    s.input(1)  # HEROINE_PRESET 基本セット
    s.input(0)  # EVENTFIRST 序章略過
    assert s.phase == Phase.SHOP
    return s


def test_session_ending_3_returns_to_title(data):
    """11 日目夜（ボス 7 体生存：(7-7+1)*11 - 11 + 0 <= 0 && TIME == 1）→ ENDING_3 → FLAG:999 = -999 →
    SHOP_TURNEND.ERB:44–47 CLEARLINE・RESETDATA・BEGIN TITLE。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _session(data, tmp)
        st = s.state
        st.day[0], st.time = 11, 1
        for i in range(1, st.charanum):
            st.charas[i].cflag[100] = 103  # 休憩
        s.input(100)
        if s.phase == Phase.ACTION_CONFIRM:
            s.input(9)  # はい（次から確認しない）：[1] は原作どおり中断（SHOP.ERB:521–532）
        for _ in range(200):
            if s.phase in (Phase.TITLE, Phase.HALTED):
                break
            s.input(0)
        assert s.phase == Phase.TITLE and s.state is None
        assert "[0] 最初からはじめる" in [ln.text for ln in s.out.lines]


def test_session_lastboss_clear_score_savegame(data):
    """全ボス撃破済み（人工）→ Ｋ触手（蓄積ダメージ 100％ → FLAG:13 = 1）を撃破 → 完全殲滅 → BEGIN TURNEND →
    ENDING_2 → SCORE → [0]はい → SAVEGAME（5 番）→ 施設資金還元 → 引き継ぎ選單→SHOP。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _session(data, tmp, seed=4)  # 遭遇判定（:333）が成立し先制攻撃が命中する系列
        st = s.state
        st.flag[100] = 0
        st.flag[101] = 1
        st.flag[47] = st.flag[46]
        st.flag[401] = 100000000
        st.charas[1].cflag[100] = 101
        for i in range(2, st.charanum):
            st.charas[i].cflag[100] = 103
        s.input(100)
        if s.phase == Phase.ACTION_CONFIRM:
            s.input(9)
        saved = False
        for _ in range(3000):
            if any("データ引き継ぎ" in ln.text for ln in s.out.lines[-30:]):
                break
            lines = [ln.text for ln in s.out.lines[-6:]]
            if s.phase == Phase.SAVE_SELECT:
                s.input(5)
                saved = True
                continue
            if "[1]いいえ" in lines:
                s.input(0)
                continue
            btn = [v for ln in s.out.lines[-30:] for (_, v) in ln.buttons]
            s.input(1 if 1 in btn else 0)
        assert saved and s.phase == Phase.TURN
        t = [ln.text for ln in s.out.lines]
        assert "*** クリアスコア ***" in t
        assert any("データ引き継ぎ" in x for x in t)
        st2, _ = load_from_file(Path(tmp) / "save05.json")
        assert 1 <= st2.flag[64] <= 6 and st2.flag[854] == 1
        assert st2.flag[101] == 0 and st2.flag[100] == 0
        # オープニング処理.ERB@EVENTLOAD:13–14：FLAG:64 > 0 のデータをロード → JUMP ENDING → :4–5 $START_SUCCESSION → 繼承選單
        s2 = GameSession(data, Path(tmp), rng=GameRng(0))
        s2.input(1)
        s2.input(5)
        assert s2.phase == Phase.TURN
        assert any("データ引き継ぎ" in ln.text for ln in s2.out.lines[-30:])
        # 人工配置的末王致死傷害經實際通關／存檔入口，再走零角色預設繼承。
        s2.input(999)
        s2.input(0)
        s2.input(1)  # NORMAL
        s2.input(0)  # 周回人數預設
        # SUCCESSION.ERB@SUCCESSION:1560 → CHARA_MAKE.ERB@CHARA_MAKE_MAIN:207–210。
        s2.input(1000)  # 保留預設角色設定，明確完成角色製作。
        s2.input(1)  # HEROINE_PRESET 基本設定
        assert s2.phase == Phase.SHOP
        assert (s2.state.flag[64], s2.state.day[0], s2.state.time) == (0, 1, 0)  # EVENTSHOP 清除繼承標記。
        s2.close()
        s.close()
