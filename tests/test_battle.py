"""戦闘（`eragvt.game.battle`）：遭遇判定・TRAIN の流れ・EVENTCOMEND・EVENTEND・能力上昇。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號寫在註解），不從實作輸出反推。
戦闘 ERB は `ゲーム内_戦闘処理/` 以下。触手の Lv（TENTACLE_LEVEL、S04 で移植・テスト済み）は入力値として使う。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, Step
from eragvt.game.battle import ablup as ablup_mod
from eragvt.game.battle import after, encount, train
from eragvt.game.battle.core import BeginAfterTrain, get_local, set_local, tentacle_level
from eragvt.game.era import div
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


def _drive(gen):
    """入力待ちにならないジェネレータを最後まで実行して戻り値を返す（S15：event_end はジェネレータ）。"""
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("入力待ちになった")


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1、TIME=0、TARGET=1（紅葉）
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def idx(data, var, name):
    return data.index_of(var, name)


# --- 先制攻撃（BATTLE_TRAIN.ERB@EVENTTRAIN:169–207）------------------------------------------


@pytest.mark.parametrize(
    "exp0, chisei_sum, chisei_enemy, flag100, expected",
    [
        # :169 MIN(SQRT(0),20) + MIN(SQRT(0),25) + 5 = 5、:173 FLAG:3(7) == 生存数(7) → +15
        (0, 0, 100, 127, 20),
        # SQRT(100)=10、PERCENT_CAL(40,10)=400 → SQRT=20、+5、+15 = 50
        (100, 40, 10, 127, 50),
        # SQRT(900)=30 → 上限 20、PERCENT_CAL(1000,1)=100000 → SQRT=316 → 上限 25、+5、+15 = 65
        (900, 1000, 1, 127, 65),
        # ボス 1 体撃破済み（FLAG:100 = 126 → 生存 6）：:176 FLAG:3 - 1 == 6 → +15（:173 は不成立）
        (0, 0, 100, 126, 20),
        # 2 体撃破済み（生存 5）：どちらも不成立 → 5
        (0, 0, 100, 124, 5),
    ],
)
def test_initiative_rate(ctx, exp0, chisei_sum, chisei_enemy, flag100, expected):
    st = ctx.state
    st.charas[1].exp[0] = exp0
    st.flag[100] = flag100
    st.flag[10] = 0  # ボス戦（ENEMY_TYPE_CHECK_F("MOB") == 0）
    assert train.initiative_rate(ctx, chisei_sum, chisei_enemy) == expected


@pytest.mark.parametrize(
    "initiative, rolls, tflag24",
    [
        # :202 10 < 40 → TFLAG:24=1、:204 40*3/4=30 → 29 < 30 → 2、30*3/4=22 → 50 < 22 不成立で終了
        (40, [10, 29, 50], 2),
        (40, [40], 0),  # 40 < 40 不成立
        # 1 → 0 < 1 成功、1*3/4 = 0 → :205 SIF INITIATIVE > 0 不成立でループを抜ける（RAND は 1 回だけ）
        (1, [0], 1),
        # 0 でも :202 の RAND:100 は 1 回評価される
        (0, [0], 0),
    ],
)
def test_initiative_loop(ctx, initiative, rolls, tflag24):
    st = ctx.state
    st.rng = FixedRng(rolls)
    train.initiative_loop(ctx, initiative)
    assert st.tflag[24] == tflag24
    assert st.rng._values == []


# --- 遭遇判定（ENCOUNT.ERB）-----------------------------------------------------------------


def test_encount_boss_not_located_consumes_only_enemy_roll(ctx):
    st = ctx.state
    st.charas[1].cflag[100] = 101
    # ENCOUNT_ENEMY:57–64 昼 40 - MIN(5000/500, 40) = 30、:74 RAND:100 = 99 → 遭遇せず
    # ENCOUNT_BOSS:159–160 FLAG:47(0) < FLAG:46(28) → RETURN 0（RAND を引かない）
    st.rng = FixedRng([99])
    assert encount.encount(ctx) == 0
    assert st.rng._values == []
    assert st.charas[1].exp[idx(ctx.data, "EXP", "戦闘経験")] == 1  # ENCOUNT_ENEMY:28
    assert (st.flag[110], st.savestr[13]) == (0, "BOSS")  # ENCOUNT_BOSS:142–144


def test_encount_boss_after_kill_stop_flag(ctx):
    st = ctx.state
    st.flag[47] = st.flag[46]
    st.flag[49] = 1  # 撃破直後ターン：:159 FLAG:49 → RETURN 0
    st.rng = FixedRng([99])
    assert encount.encount(ctx) == 0


def test_encount_boss_hit(ctx):
    st, data = ctx.state, ctx.data
    c = st.charas[1]
    c.cflag[100] = 101
    st.flag[47] = st.flag[46]  # 探索度 = ノルマ
    st.flag[303] = 25000000  # Ａ触手の蓄積ダメージ 25％（×100 で保存）
    # [ENCOUNT_ENEMY:74 の RAND:100, ENCOUNT_BOSS:184 の RAND:100, RANDCHOOSE_F の RAND:7]
    # :152 ENCOUNT_PER = (40 + 7*3) * 28 / 28 = 61 > 60 → 遭遇。候補は生存ボス 1..7（:208–212）、RAND:7 = 2 → 3 番目 = 3
    st.rng = FixedRng([99, 60, 2])
    assert encount.encount(ctx) == 1
    assert st.rng._values == []  # :226–239 捕獲中のキャラがいないので RAND:100 は引かない
    lv = tentacle_level(st)
    assert (st.flag[10], st.flag[11], st.flag[18]) == (0, 3, 3)  # :262–269
    # TENTACLE_BOSS_3_Ａ触手.ERB:19–22 HP = TENTACLE_STATUS_HOSEI(6500, 1500) = (Lv*10+95)*6500/100 + 1500
    assert st.flag[12] == div((lv * 10 + 95) * 6500, 100) + 1500
    # :293 FLAG:13 = FLAG:13 * (1000000 - 25000000/100) / 1000000、:294 %100 == 0
    assert st.flag[13] == div(st.flag[12] * 750000, 1000000)
    assert st.flag[14] == 900 + lv * 25  # _SYASEI:26–29
    assert (st.flag[15], st.flag[16], st.flag[17]) == (0, 1710, 0)  # _YUDAN = 1710
    assert c.exp[idx(data, "EXP", "ボス経験")] == 1
    t = texts(ctx.out)
    # MESSAGE_BATTLE.ERB@MESSAGE_ENCOUNT_BOSS:28–35
    assert t[-5:-1] == [
        f"Ａ触手 Lv.{lv} と遭遇した！",
        "（まるでスライムかアメーバのような不定形の姿をした半透明のボス触手）",
        "（中心に大きな核が透けて見え、その周囲には臓器らしき肉塊が並んでいる）",
        "・・・・・・・・・・・・・・・",
    ]
    assert ctx.out.lines[-1].wait


def test_encount_boss_miss(ctx):
    st = ctx.state
    st.flag[47] = st.flag[46]
    st.rng = FixedRng([99, 61])  # 61 > 61 不成立 → SELECT = 0 → :258 RETURN 0
    assert encount.encount(ctx) == 0
    assert st.rng._values == []
    assert st.flag[11] == 0


def test_mob_tentacle_encount_text_only(ctx):
    """ENCOUNT.ERB@MOB_TENTACLE_ENCOUNT:449–521（FLAG:802 = 15 は bit4 が 0 → 文章のみ）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[100] = 101
    c.juel[50] = 0
    money = st.money
    # [探索度 RAND:4, GET_EXP_BATTLE RAND(15), GET_SYUREN RAND:15, GET_MONEY RAND:11, RAND:5, 防衛力 RAND:50]
    st.rng = FixedRng([2, 7, 3, 5, 1, 20])
    assert encount.mob_tentacle_encount(ctx) == 0
    assert st.rng._values == []
    lv = tentacle_level(st)
    # :453–456 LOCAL = TIMES(2787, 0.35) = 975。SYOUHI_KEIGEN（コモン関数.ERB:947–960）：体力基礎 2006 > 1000
    #   → 975 - 975*1006/2500 = 975 - 392 = 583（975/2 より大）
    assert c.base[0] == 2787 - 583
    # :458–461 TIMES(2454, 0.30) = 736、気力基礎 1748 → 736 - 736*748/2500 = 736 - 220 = 516
    assert c.base[1] == 2454 - 516
    assert st.flag[47] == 8  # :465 6 + 2（出撃中、狩人の勘なし）
    assert c.juel[50] == min(div(8 * (lv + 2), 1) + 7, 75)  # コモン関数.ERB:374
    assert c.juel[20] == 13  # :481 10 + 3
    assert st.money == money + (25 + 5) * (5 + 1)  # :482
    assert st.flag[852] == 5000 + 20 + div(lv, 2) + 25  # :486
    t = texts(ctx.out)
    assert t[:3] == ["ザコ触手 と遭遇した！", "・・・・・・・・・・・・・・・", "ザコ触手 を倒した!"]  # MESSAGE_BATTLE.ERB:5–11
    assert "体力が975減少した" in t and "気力が736減少した" in t  # 表示は軽減前の値（:456、:461）
    assert "探索度が8上昇した" in t
    assert f"防衛力が{20 + div(lv, 2) + 25}上昇した" in t


# --- @USERCOM の表示系コマンド（BATTLE_COM.ERB:626–655）------------------------------------------


def run_gen(gen):
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT 待ちになった")


@pytest.mark.parametrize(
    "value, check",
    [
        (810, lambda st: st.charas[1].tcvarn[8] == 0),  # :630
        (820, lambda st: st.charas[1].tcvarn[8] == 1),  # :632
        (830, lambda st: st.charas[1].tcvarn[8] == 2),  # :634
        (898, lambda st: st.flag.get_bit(801, 8)),  # :637 INVERTBIT FLAG:801, 8
        (899, lambda st: st.flag.get_bit(801, 6)),  # :639
        (400, lambda st: st.flag[999] == 1),  # :643–648
    ],
)
def test_usercom_settings(ctx, value, check):
    st = ctx.state
    st.charas[1].tcvarn[8] = 5
    st.flag[801] = 1
    run_gen(train.usercom(ctx, value))
    assert check(st)


def test_usercom_retreat_not_available_when_restrained(ctx):
    """:573 拘束中（TCVARn:0 == 0）は 999 でも何もしない（:656 RESULT < 400 にも当たらない）。"""
    st = ctx.state
    st.charas[1].tcvarn[0] = 0
    st.rng = FixedRng([])
    run_gen(train.usercom(ctx, 999))
    assert texts(ctx.out) == []


# --- @EVENTCOMEND（BATTLE_COM.ERB:685–986）------------------------------------------------------


def test_event_comend_analysis_and_decay(ctx):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    st.flag[10] = 0
    st.flag[11] = 3
    st.flag[20] = 0
    v[0] = 3
    c.palam[0] = 0
    c.palam[13] = 1000  # 欲情
    c.palam[10] = 500  # 潤滑（減衰しない）
    c.nowex[0] = 2
    st.temp.selectcom = 4
    set_local(st, "EVENTCOMEND", 1, 2)  # 前回 :957–968 で 2 人避難した
    st.rng = FixedRng([3])  # :895 RAND:5（:858 は NOWEX 合計 > 0 だが CFLAG:1 == 0 なので RAND を引かない）
    train.event_comend(ctx)
    assert st.rng._values == []
    lv = tentacle_level(st)
    # :883–898 LOCAL = CALC_CHISEI_SHIEN(2)（支援なし 0）→ RAND:5(3) + 0/4 + LOCAL:1(2) = 5、Lv < 10 → + 10 - Lv/3
    gain = 5 + 10 - div(lv, 3)
    assert st.flag[20] == gain
    assert f"敵の解析度が{gain}％上がった！" in texts(ctx.out)
    # :944 PALAMLV_F は前回の戻り値 LOCAL(0) の PALAM:0 = 0 を見て 0 を返し続ける → AT_VAR = 950
    assert c.palam[13] == 950
    assert c.palam[10] == 500
    assert st.temp.max_palam[13] == 1000 and st.temp.max_palam[10] == 500  # :948–949
    assert c.ex[0] == 2  # :929–931
    assert st.temp.prevcom == 4  # :933
    assert st.tflag[32] == 1  # :728–729 防御の次のターンはカウンター
    assert get_local(st, "EVENTCOMEND", 1) == 0  # :957 LOCAL:1 = 0（避難なし）


def test_battle_report(ctx):
    """REPORT.ERB@BATTLE_REPORT:6–29。絶頂回数はすべて TCREPORT:10（REPORT.ERH:11–13 が同じ 10）。"""
    st = ctx.state
    c = st.charas[1]
    st.tflag[0] = 7
    c.base[0] = 0
    c.ex[1] = 3
    c.tcvarn[21] = 0
    c.tcvarn[23] = 5
    c.tcvarn[25] = 5
    train.battle_report(ctx)
    rep = st.temp.tcreport
    assert (rep[0], rep[10], rep[3], rep[4], rep[1]) == (7, 3, 7, 0, 0)


# --- @EVENTEND（BATTLE_TRAIN_AFTER.ERB）-------------------------------------------------------


def test_event_end_retreat_from_boss(ctx):
    st, data = ctx.state, ctx.data
    c = st.charas[1]
    c.cflag[100] = 101
    c.juel[50] = 0
    st.savestr[13] = "BOSS"
    st.flag[110] = 0
    st.flag[10] = 0
    st.flag[11] = 3
    st.flag[12] = 10000
    st.flag[13] = 3000
    st.flag[20] = 40
    st.flag[46] = 28
    st.flag[47] = 36
    st.flag[700] = 1
    st.tflag[98] = 0  # 撤退
    st.tflag[0] = 4
    c.palam[13] = 40000  # 欲情
    lv = tentacle_level(st)
    # [:148 RAND:10, :159 RAND:101, SELF_CHECK:161 RAND:100, AFTER_TRAIN_RAPE:982 RAND:100]
    st.rng = FixedRng([7, 50, 99, 50])
    assert _drive(after.event_end(ctx)) == Step.TURNEND
    assert st.rng._values == []
    t = texts(ctx.out)
    assert st.flag[700] == 0  # :7
    # :14–15 40000 >= 40000 + 防止 0 → 快楽刻印 1
    assert c.mark[idx(data, "MARK", "快楽刻印")] == 1
    assert "紅葉は快楽刻印1を取得した" in t
    # _ABLUP:19–49 PALAM 40000（< 60000）→ 欲情の珠 2000。ABL_UP_11:944–946 Lv0→1 に 500 消費、Lv1→2 は 2000 必要で不可
    assert c.abl[idx(data, "ABL", "欲望")] == 1
    assert c.juel[idx(data, "JUEL", "欲情")] == 1500
    assert "欲望が1に上がった" in t
    # :146–152 消耗 0％ → LOCAL = (Lv-2)/1*0/2 + 7
    assert c.juel[50] == 7
    # :157–169 POWER(MIN(4-10,0),2) = 36 → 36*(8+Lv) + 50 + MAX(300 - 0, 100)
    loss = 36 * (8 + lv) + 50 + 300
    assert st.flag[852] == 5000 - loss
    assert f"防衛力が{loss}低下した" in t
    assert st.flag[47] == div(36 - 28, 4) + 28  # :217–218
    # :425–431 蓄積ダメージ：3000*1000000/10000 = 300000 → (1000000 - 300000) * 100、余りなし
    assert st.flag[303] == 70000000
    assert st.flag[503] == 40
    assert c.tcvarn[0] == 0 and st.flag[73] == 0  # :516、:524


def test_event_end_boss_victory(ctx):
    st, data = ctx.state, ctx.data
    c = st.charas[1]
    c.cflag[100] = 101
    c.juel[50] = 0
    st.savestr[13] = "BOSS"
    st.flag[110] = 0
    st.flag[10] = 0
    st.flag[11] = 3
    st.flag[100] = 127 - 4  # SOURCE_CHECK の勝利処理で Ａ触手のビットは落ちている
    st.tflag[98] = 1
    c.abl[idx(data, "ABL", "レベル")] = 10  # レベルアップ（CHECK_LEVELUP）が起きない値にする
    money = st.money
    lv = tentacle_level(st)
    # [GET_EXP_BATTLE RAND(15), GET_MONEY RAND:8, RAND:8, 防衛力 RAND:101, SELF_CHECK RAND:100, AFTER_TRAIN_RAPE RAND:100]
    st.rng = FixedRng([5, 3, 4, 60, 99, 99])
    assert _drive(after.event_end(ctx)) == Step.TURNEND
    assert st.rng._values == []
    # コモン関数.ERB:387 50*(Lv+2)/10 + 5 + 25（上限 150）
    assert c.juel[50] == min(div(50 * (lv + 2), 10) + 30, 150)
    assert c.juel[20] == 100  # :268 100 + 0*2
    # :269 (25+3) * (100 + (7 - 6) * (25 + 4))
    assert st.money == money + 28 * (100 + 29)
    assert st.flag[200] == 3  # :270 GET_KAKERA 3
    assert st.flag[852] == 5000 + (lv + 4) * 50 + 400 + 60  # :273
    assert st.flag[853] == 3  # :281–283
    assert st.flag[303] == 0  # :425 勝利時は蓄積ダメージを書かない


# --- 能力上昇（ヒロイン関連/ABL_UP_CHECK.ERB）---------------------------------------------------


def test_ablup_juujun_uses_fear_when_submission_short(ctx):
    """ABL_UP_10:886–893：屈服の珠が足りなければ恐怖の珠で上げる。"""
    st, data = ctx.state, ctx.data
    c = st.charas[1]
    c.palam.clear()
    c.juel[idx(data, "JUEL", "屈服")] = 500
    c.juel[idx(data, "JUEL", "恐怖")] = 1000
    ablup_mod.ablup(ctx, 0)
    assert c.abl[idx(data, "ABL", "従順")] == 1
    assert c.juel[idx(data, "JUEL", "恐怖")] == 0
    assert c.juel[idx(data, "JUEL", "屈服")] == 500
    assert "従順が1に上がった" in texts(ctx.out)


def test_ablup_arg2_only_jewels(ctx):
    """_ABLUP:65–66 ARG == 2 は珠の取得だけ。:15–18 COUNT > 3 は +6（PALAM:10–17）。"""
    st = ctx.state
    c = st.charas[1]
    c.palam.clear()
    c.palam[0] = 150  # 快Ｃ：< 300 → 1
    c.palam[17] = 700  # 恐怖：< 1500 → 10
    before = {i: c.juel[i] for i in (0, 17)}
    ablup_mod.ablup(ctx, 2)
    assert c.juel[0] == before[0] + 1
    assert c.juel[17] == before[17] + 10
    assert c.abl[0] == 0


# --- TRAIN 全体（BEGIN TRAIN → 撤退 → EVENTEND）----------------------------------------------------


def test_run_train_retreat_reaches_turnend(ctx):
    """戦闘開始 → [999] 撤退。撤退に成功するまで繰り返し、BEGIN AFTERTRAIN → EVENTEND → BEGIN TURNEND。"""
    st = ctx.state
    st.charas[1].cflag[100] = 101
    st.flag[47] = st.flag[46]
    st.rng = GameRng(3)
    for _ in range(50):
        if encount.encount(ctx) == 1:
            break
        st.flag[49] = 0
    assert st.flag[11] > 0
    gen = train.run_train(ctx)
    next(gen)  # SHOW_USERCOM 後の入力待ち
    assert st.flag[700] == 1 and st.charas[1].tcvarn[0] == 3 and st.temp.turn_limit == 50  # EVENTTRAIN:16–29、:139
    assert any("撤退[999]" in x for x in texts(ctx.out))
    result = None
    for _ in range(30):
        try:
            gen.send(999)
        except StopIteration as e:
            result = e.value
            break
    assert result == Step.TURNEND
    assert st.flag[700] == 0


def test_begin_after_train_is_exception():
    assert issubclass(BeginAfterTrain, Exception)
