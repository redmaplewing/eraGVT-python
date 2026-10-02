"""ターン終了（`eragvt.game.turnend`）：EVENTTURNEND／EVENTSHOP 通常分岐と下位関数。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），不從實作輸出反推。
SHOP_TURNEND.ERB は `インターミッション画面/SHOP_TURNEND.ERB`。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop, turnend
from eragvt.game.action import Ctx, Step
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


class MaxRng(GameRng):
    """常に n-1 を返す（RAND:100 < 5 等の確率イベントが起きない側）。"""

    def rand(self, n: int) -> int:
        if n <= 0:
            raise ValueError(n)
        return n - 1


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1, TIME=0, TARGET=1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def play_turn(ctx: Ctx) -> None:
    """全員休憩で 1 ターン：JUMP ACTION_MAIN … BEGIN SHOP → @EVENTSHOP（オートセーブ・SHOW_SHOP は session 側）。"""
    gen = turnend.run_turn(ctx)
    with pytest.raises(StopIteration):
        next(gen)
    shop.event_shop(ctx.state, ctx.data, ctx.out, ctx.narration)


# --- 1 ターン通し（開局状態・全員休憩）---------------------------------------------------


def test_two_turns_all_rest(ctx):
    st = ctx.state
    st.rng = MaxRng()
    play_turn(ctx)
    # 昼 → 夜
    assert (st.day[0], st.time) == (1, 1)  # :172 INVERTBIT、:180 TIME == 0 のときだけ DAY += 1
    assert (st.flag[41], st.flag[43]) == (0, 0)  # :168–169
    assert st.flag[42] == 0  # DAILY_DEFENCE_CHANGE:450–451（FLAG:41 = 1：EVENTFIRST:286）
    assert st.flag[852] == 5000
    assert st.flag[853] == 0  # RAND:100 = 99 → 変動なし
    assert st.money == 5000
    assert st.flag[799] == 3  # PARASITE:9 が CHARANUM-1 まで上書き（SHOW_SHOP:20 で 0 に戻る）
    assert (st.flag[798], st.target) == (1, 1)  # ACTION.ERB:11、EVENTSHOP:209
    assert st.flag[44] == 0  # BIRTH_AUTO_RANDOM：RAND:50 = 49
    assert st.charas[1].cflag[217] == 0  # ESTRUS_CYCLE は TIME == 0 のときだけ（:763）
    t = texts(ctx.out)
    assert t.count("行動開始！") == 1
    assert "【蒼美の行動：休憩】" in t
    assert "夜になりました" in t
    assert "防衛力の変動　　" not in t

    shop.show_shop(st, ctx.data, TextOutput(), ctx.narration)  # SHOW_SHOP:20 FLAG:799 = 0
    ctx.out = TextOutput()
    play_turn(ctx)
    # 夜 → 翌日昼
    assert (st.day[0], st.time) == (2, 0)
    # DAILY_DEFENCE_CHANGE：FLAG:41 == 0 → FLAG:42 = 1、TENTACLE_LEVEL = 撃破 0*3 + 4 + 150*1/11/100(=0) = 4
    # → :418 LOCAL:852 = 4 + 5 = 9
    assert st.flag[42] == 1
    assert st.flag[852] == 4991
    # CALC_INCOME_EXPEND:832–838：40 + 20 * CHARANUM_SAFE(3) = 100
    assert st.money == 4900
    # ESTRUS_CYCLE:64 CFLAG:217 = 1 + RAND:29(=28)
    assert [c.cflag[217] for c in st.charas[1:]] == [29, 29, 29]
    t = texts(ctx.out)
    for expected in (
        "　危険度レベル1：まだ比較的安全です",
        "　防衛力( 5000 )　−　時間経過( 9 )　＝　4991",
        "一日が終了しました",
        "維持費や生活費として資金$100を支払った。",
    ):
        assert expected in t


def test_turnend_loops_back_to_action_main(ctx):
    st = ctx.state
    st.flag[799] = 1
    gen = turnend.event_turnend(ctx)
    with pytest.raises(StopIteration) as e:
        next(gen)
    assert e.value.value == Step.ACTION_MAIN  # :15–16
    assert (st.flag[70], st.flag[71], st.flag[72]) == (0, 0, 0)


# --- RECOVERY_OVER_TIME（SHOP_TURNEND.ERB:591–768）----------------------------------------


def test_recovery_day(ctx):
    st = ctx.state
    st.rng = MaxRng()
    st.time = 0
    k, m = st.charas[1], st.charas[2]
    k.base[0], k.base[1], k.base[2] = 1000, 1000, 100
    m.base[0] = 1000
    turnend.recovery_over_time(ctx)
    # 紅葉：:600 8 + :602 回復早い 4 = 12% → 2787*12/100=334、2454*12/100=294、198*12/100=23
    assert (k.base[0], k.base[1], k.base[2]) == (1334, 1294, 123)
    # 桃香：8% → 2454*8/100 = 196
    assert m.base[0] == 1196


def test_recovery_night_uses_target_yama(ctx, data):
    st = ctx.state
    st.rng = MaxRng()
    st.time = 1
    k = st.charas[1]
    k.base[0] = 1000
    turnend.recovery_over_time(ctx)
    assert k.base[0] == 1000  # :608 夜は 0%
    st.target = 3
    st.charas[3].talent[data.index_of("TALENT", "夜魔の貴族")] = 1
    turnend.recovery_over_time(ctx)
    # :610 `TALENT:夜魔の貴族`（TARGET）で全員 +8 → 2787*8/100 = 222
    assert k.base[0] == 1222


def test_recovery_fatigue_and_misc(ctx, data):
    st = ctx.state
    st.rng = MaxRng()
    st.time = 0
    st.flag[53] = 8  # マッサージチェア
    k = st.charas[1]
    k.base[0] = 1000
    k.cflag[99] = 45
    k.cflag[100] = 102
    k.cflag[241] = 3
    k.cflag[400] = 5
    k.talent[190] = 1
    k.maxbase[30], k.base[30] = 2000, 1000
    turnend.recovery_over_time(ctx)
    assert k.base[0] == 1000  # :630–631 疲労 45 → 12*5/100 = 0
    assert k.cflag[99] == 44  # :672 マッサージチェア +1
    assert "紅葉の身体から疲労が少し抜けた…" in texts(ctx.out)  # :702–706（予定が休憩ではない）
    assert k.base[30] == 1060  # :738–748 無事 3%（休憩ではない）→ 2000*3/100 = 60
    assert (k.cflag[241], k.cflag[400]) == (2, 0)  # :758–761
    assert k.cflag[217] == 29  # ESTRUS_CYCLE:64


def test_estrus_cycle(ctx):
    c = ctx.state.charas[1]
    c.cflag[217] = 29
    turnend.estrus_cycle(ctx, 1)
    assert c.cflag[217] == 30  # ESTRUS_CYCLE.ERB:56–57（29 <= 29 - 0）
    turnend.estrus_cycle(ctx, 1)
    assert c.cflag[217] == 1  # :59–60


# --- CALC_INCOME_EXPEND（SHOP_TURNEND.ERB:771–847）-----------------------------------------


@pytest.mark.parametrize(
    ("day", "gov", "gov_line"),
    [
        (7, 1200, True),  # :796 1000 + 5001/25
        (21, 2000, True),  # :823 +800
        (42, 500, True),  # :825 /4
        (63, 0, False),  # :827 0、:828 表示なし
    ],
)
def test_income(ctx, day, gov, gov_line):
    st = ctx.state
    st.day[0] = day
    st.rng = FixedRng([5])
    turnend.calc_income_expend(ctx)
    # :797 RAND:(5001/10 + 50)=5 + 10 = 15、:805 人気度 0 → 1200、:832 支出 100
    assert st.money == 5000 + gov + 15 + 1200 - 100
    t = texts(ctx.out)
    assert ("政府からの援助金として資金$" + str(gov) + "を得た！" in t) == gov_line
    assert "市民からの義援金として資金$1215を得た！" in t


def test_expense_shortage(ctx):
    st = ctx.state
    st.day[0] = 2
    st.money = 50
    turnend.calc_income_expend(ctx)
    assert st.money == 0  # :842
    assert st.charas[1].base[0] == 2229  # :843–846 TIMES 2787, 0.8
    assert st.charas[0].base[0] == 800  # MASTER も含む（FOR CCOUNT, 0, CHARANUM）


# --- DAILY_DEFENCE_CHANGE／DAILY_POPULARITY_CHANGE -------------------------------------------


def test_defence_drop(ctx):
    st = ctx.state
    st.flag[41] = 0
    st.flag[42] = 2
    turnend.daily_defence_change(ctx)
    assert st.flag[42] == 3  # :389–391
    # :421 FLAG:42 == 3 + FLAG:52 → 5000*4/100 + 4 + 10 = 214
    assert st.flag[852] == 4786
    t = texts(ctx.out)
    assert "　危険度レベル3：触手の活動が活発化しています" in t  # :401
    assert "　防衛力( 5000 )　−　時間経過( 214 )　＝　4786" in t


def test_defence_day_level(ctx):
    st = ctx.state
    st.flag[41] = 0
    st.day[0] = 22
    turnend.daily_defence_change(ctx)
    # TENTACLE_LEVEL：日数レベル 150*22/11/100 = 3 → 7、:416 FLAG:42 = 1 < 2 → 7 + 5
    assert st.flag[852] == 5000 - 12


def test_defence_someone_sortied(ctx):
    st = ctx.state
    st.flag[41] = 2
    st.flag[42] = 5
    turnend.daily_defence_change(ctx)
    assert st.flag[42] == 0  # :450–451
    assert texts(ctx.out) == []


def test_popularity(ctx):
    st = ctx.state
    # 一般評価 2 回（防衛力 5000 < 7500）、処女 3 人、ファン 3 人×1（CFLAG:284 判定）、悪いうわさ 3 回
    st.rng = FixedRng([0, 50, 0, 99, 99, 0, 0, 0, 0, 0, 0])
    turnend.daily_popularity_change(ctx)
    assert st.flag[853] == 2
    assert "　人気度( 0 )　＋　一般評価( 1 )　＋　処女ボーナス( 1 )　＝　2　(↑上昇)" in texts(ctx.out)


# --- ENDING 判定（ゲーム内_イベント発生/エンディング/ENDING.ERB:74–85）------------------------------


@pytest.mark.parametrize(("day", "time", "fires"), [(10, 1, False), (11, 0, False), (11, 1, True)])
def test_ending_time_limit(ctx, day, time, fires):
    from eragvt.game.ending import ending_gen

    st = ctx.state
    st.day[0], st.time = day, time
    # ボス 7 体生存：(7 - 7 + 1) * FLAG:2(11) - DAY + DAY:1 <= 0 && TIME == 1 → ENDING_3（S27：FLAG:999 = -999）
    list(ending_gen(ctx))
    assert (st.flag[999] == -999) is fires
    assert ("時間切れです・・・" in texts(ctx.out)) is fires


def test_ending_clear_condition(ctx):
    from eragvt.game.ending import ending_gen

    ctx.state.flag[100] = 0
    gen = ending_gen(ctx)
    assert next(gen) is None  # :9 ENDING_2 → SCORE →「クリアデータを記録しますか？」の INPUT
    assert "この街に平和が戻りました！！" in texts(ctx.out)
    assert "クリアデータを記録しますか？" in texts(ctx.out)


# --- 夜間イベント：開局状態では起きない／条件が揃うと未移植で止まる ---------------------------------


def test_night_events_not_triggered_in_opening_state(ctx):
    st = ctx.state
    st.time = 1
    st.rng = FixedRng([])  # 乱数を消費しない（消費したら FixedRng が例外）
    turnend.prison(ctx)  # 幽閉中（CFLAG:0 == 1）なし
    list(turnend.birth_hantei(ctx))  # 妊娠なし
    list(turnend.grow_hantei(ctx))  # 育児なし
    turnend.akuoti_attack(ctx)  # 悪堕ちなし
    list(turnend.lovesex_night(ctx))  # 交際相手 0 → :28 CONTINUE（RAND 短絡：OperatorMethod.cs:532–536）
    list(turnend.yobai(ctx))  # 淫核等・感覚 0 → 候補判定の対象外
    st.day[0] = 2
    turnend.raid_hantei(ctx)  # :30 DAY < 3


def test_self_night_rolls_but_zero_chance(ctx):
    st = ctx.state
    st.time = 1
    st.rng = FixedRng([0, 0, 0])  # :47 RAND:100 < 0 は常に偽
    turnend.self_night(ctx)


@pytest.mark.parametrize(
    ("setup", "func"),
    [
        (lambda st, d: st.charas[1].cflag.__setitem__(0, 1), turnend.prison),
    ],
)
def test_night_events_unported(ctx, data, setup, func):
    ctx.state.time = 1
    setup(ctx.state, data)
    with pytest.raises(NotImplementedError):
        func(ctx)


# --- EVENTSHOP の下位関数 --------------------------------------------------------------------


def test_birth_auto_random(ctx):
    st = ctx.state
    st.rng = FixedRng([0, 0, 2, 0])
    turnend.birth_auto_random(ctx)
    # PREGNANT_SOURCE_NINSIN.ERB:618 RAND:(5000/100)=0 → :621–631 昼・RAND:2=0 → DATA 3 番目 → :663 DATA 1 番目
    assert st.flag[44] == 1  # :744–746
    t = texts(ctx.out)
    assert t[-2:] == ["【避けられた悲劇】", "　更衣室で着替えていた少女が襲われ、何匹もの子触手が産み落とされたようだ..."]
    assert ctx.out.lines[-1].wait  # PRINTDATAW


def test_birth_auto_random_contraception_config(ctx):
    ctx.state.flag[805] |= 4  # CONFIG_CHECK_OTHER_F(2)：常時避妊
    ctx.state.rng = FixedRng([])
    turnend.birth_auto_random(ctx)
    assert ctx.state.flag[44] == 0


def test_small_tentacle_not_at_day(ctx):
    st = ctx.state
    st.flag[44] = 1
    st.time = 0
    st.rng = FixedRng([])
    list(turnend.small_tentacle_hantei(ctx))  # FORCE_深夜の子触手襲来.ERB:29–30 夜以外は判定しない（乱数も使わない）
    assert texts(ctx.out) == []


def test_parasite_overwrites_flag799(ctx):
    from eragvt.game.parasite import parasite

    list(parasite(ctx))
    assert ctx.state.flag[799] == 3  # FORCE_深夜の寄生触手暴走.ERB:8–9


def test_set_partymember_pregnant_sortie(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "妊娠")] = 1
    c.cflag[100] = 101
    turnend.set_partymember(ctx)
    assert c.cflag[100] == 103  # SET_PARTYMEMBER.ERB:12–15
    assert "紅葉は妊娠しているため出撃できなくなりました" in texts(ctx.out)


# --- S20 使用者裁決（2026-10-01）：脅迫クールダウン CFLAG:72 の減算（DEVIATION）-----------------------


def test_intimidation_cooldown_decrements_before_hantei(ctx, monkeypatch):
    """原作は CFLAG:72 = 8（FORCE_クズ市民の脅迫.ERB:520／:632）を減らさない。裁決により EVENTTURNEND の
    INTIMIDATION 判定（SHOP_TURNEND.ERB:90–101）の直前で、> 0 なら 1 減らす（0 はそのまま）。"""
    st = ctx.state
    st.rng = MaxRng()
    st.flag[804] |= 1 << 10  # CONFIG_CHECK_PRISON_F(10)：クズ市民による幽閉
    c1, c2 = st.charas[1], st.charas[2]
    c1.cflag[72], c1.cflag[286] = 2, 1
    c2.cflag[72] = 0
    seen: list = []

    def fake(ctx):
        seen.append((ctx.state.target, ctx.state.target_chara.cflag[72]))
        return
        yield  # pragma: no cover

    monkeypatch.setattr(turnend, "intimidation_event", fake)
    play_turn(ctx)
    assert seen == [(1, 1)]  # 判定時点で既に 2 → 1
    assert (c1.cflag[72], c2.cflag[72]) == (1, 0)
