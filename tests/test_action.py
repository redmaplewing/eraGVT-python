"""行動実行（`eragvt.game.action`）：ACTION_MAIN／REST／TRAINING。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），不從實作輸出反推。
開局狀態（特装戦隊 301–303）：[1] 紅葉（勝気・回復早い・近距離得意、MAXBASE 体力 2787 気力 2454 性耐性 198、
BASE:体力基礎 2006）、[2] 桃香（楽天家、体力 2454 気力 2787）、[3] 蒼美（真面目、体力 2954）。FLAG:50 = FLAG:51 = 1。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, Step, action_main, rest, training
from eragvt.game.opening import event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1, TIME=0, TARGET=1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def run(gen, inputs=()):
    """ジェネレータを入力列で最後まで回し、戻り値を返す。入力が尽きても待っているなら None。"""
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            if not inputs:
                return None
            gen.send(inputs.pop(0))
    except StopIteration as stop:
        return stop.value


# --- REST（ゲーム内_行動実行処理/ACTION_REST.ERB）------------------------------------


def test_rest_basic_with_fatigue(ctx):
    st = ctx.state
    st.target = 2  # 桃香：回復早い／遅い・FEAT なし
    c = st.charas[2]
    c.base[0], c.base[1], c.base[2] = 1000, 500, 0
    c.cflag[99] = 25
    rest(ctx)
    # :9–10 FLAG:51 == 1 → 30、:52–53 疲労 25（>= 20）→ 30 * 50 / 100 = 15
    # :59–60 2454 * 15 / 100 + 200 = 568 → 1568；:62–63 2787 * 15 / 100 + 200 = 618 → 1118；:65 性耐性 = MAXBASE
    assert (c.base[0], c.base[1], c.base[2]) == (1568, 1118, 198)
    # :78 −2、:94–95 昼 −2 → 21
    assert c.cflag[99] == 21
    assert c.cflag[101] == -1  # :7
    # :69 → :105 → :111 → 最大ではない → :116 PRINTW
    assert texts(ctx.out) == ["桃香は休憩しています…", "桃香の身体から疲労が少し抜けた…", "", ""]
    assert ctx.out.lines[-1].wait


def test_rest_night_facilities(ctx):
    st = ctx.state
    st.rng = FixedRng([1, 0])
    st.time = 1
    st.flag[53] = 16 + 64 + 2  # シャワー設備・大浴場・上質なベッド（DIM.ERH:174–179）
    c = st.charas[1]  # 紅葉：回復早い
    c.cflag[99] = 20
    rest(ctx)
    # 疲労：20 −2(:78) −RAND:2=1(:80) −(RAND:2=0)+1(:82) −4 夜(:89) −2 上質なベッド(:91) = 10
    assert c.cflag[99] == 10
    assert c.base[0] == 2787  # LIMIT で MAXBASE 止まり
    assert "紅葉の身体から疲労が少し抜けた…" in texts(ctx.out)
    assert "紅葉は最大まで回復した！" not in texts(ctx.out)  # :112 CFLAG:99 != 0


def test_rest_full_recovery_message(ctx):
    rest(ctx)  # 紅葉：満タン・疲労 0 → :113
    assert texts(ctx.out) == ["紅葉は休憩しています…", "", "紅葉は最大まで回復した！", ""]


def test_rest_reserve_member_is_silent(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[999] = 0
    c.base[0] = 1000
    rest(ctx)
    # :20–21 回復早い → 35；2787 * 35 / 100 + 200 = 1175
    assert c.base[0] == 2175
    assert texts(ctx.out) == []  # :68、:110 CFLAG:999 == 0 は表示なし


# --- TRAINING（ゲーム内_行動実行処理/ACTION_TRAINING.ERB）-------------------------------


def test_training_kintore(ctx, data):
    st = ctx.state
    # 乱数の順：:23 RAND:(5 + 1*2)、BASEUP_CAL_RANDAM RAND:100、:283 RAND(5)
    st.rng = FixedRng([3, 74, 2])
    c = st.charas[1]
    gen = training(ctx)
    next(gen)
    # :40 消費体力 = TRAINING_DOWNTAIRYOKU：2787*0.10=278 → ×2.00=556 → SYOUHI_KEIGEN：
    # 体力基礎 2006 > 1000 → 556 − 556*1006/2500(=223) = 333
    assert "現在の設備レベル：Lv.1　消費体力：333" in texts(ctx.out)
    assert any(t.startswith("[0] 走りこみ") for t in texts(ctx.out))
    gen.send(99)  # :278–279 不正値 → 再 INPUT
    assert texts(ctx.out)[-1] == "正しい値を入力してください"
    with pytest.raises(StopIteration):
        gen.send(3)
    assert c.cflag[101] == 3  # :74
    assert c.base[0] == 2787 - 333  # :125
    # :17–19 LOCAL:1 = 3 + 1/2 + 2 = 5。BASEUP_CAL_RANDAM：74+5=79 < 80 → 100、回復早い −5 → 95 → 5*95/100 = 4
    # SEIKAKU_HOSEI_F(勝気=12, 攻撃=10)：TIMES 1.20 → 4
    assert c.base[10] == 154
    # LEVELSTATUS：((√220=14)+95)*154 + (5+95)*50 = 21786 / 100
    assert c.maxbase[10] == 217
    assert c.juel[50] == 12  # :283 10 + RAND(5)=2
    assert c.juel[20] == 5  # :23 2 + 3
    t = texts(ctx.out)
    for expected in ("紅葉は筋トレを開始した", "攻撃の基礎値が4上がった", "紅葉は経験値を12％得た", "修練Pを5P手に入れた"):
        assert expected in t


def test_training_short_range_and_sengiup(ctx):
    st = ctx.state
    st.rng = FixedRng([0, 0, 0, 0])
    c = st.charas[1]
    c.exp[5] = 15
    run(training(ctx), [6])
    # :171 TIMES 5, 0.30 → 1。BASEUP_CAL_RANDAM：0+5 → 10 未満 → 10 → 70 −5 = 65 → 1*65/100 = 0 → 表示なし
    assert (c.base[10], c.base[12]) == (150, 160)
    # :186 EXP:近距離戦闘経験 += 7（:21 7 + 1/2）、:187 7 > 3 + 1 → 「少し」なし
    assert c.exp[5] == 22
    t = texts(ctx.out)
    assert "近距離戦闘が上達した（＋7）" in t
    # SENGIUP（コモン関数.ERB:675–）：ABL 0 → 25、近距離得意 && ARG:1 == 0 → TIMES 0.9 → 22。22 >= 22
    assert c.abl[30] == 1
    assert "紅葉の近距離Lvが上がった" in t


def test_training_levelup(ctx, data):
    st = ctx.state
    st.rng = FixedRng([0, 74, 2])
    c = st.charas[1]
    c.juel[50] = 95
    run(training(ctx), [3])
    # GET_EXP 12 → 107 > 100 → CHECK_LEVELUP（コモン関数.ERB:921–936）
    assert c.abl[data.index_of("ABL", "レベル")] == 2
    assert c.juel[50] == 7
    assert "紅葉はレベルが1上がった" in texts(ctx.out)
    # LEVELSTATUS_UP(2006, Lv2, 400+(2006-1000)/5=601)：(√440=20 + 95)*2006 + (TIMES 104,0.1=10 + 95)*601 → /100
    assert c.maxbase[0] == 2937


# --- ACTION_MAIN（ゲーム内_行動実行処理/ACTION.ERB）------------------------------------


def test_action_main_first_chara_rest(ctx):
    st = ctx.state
    assert st.flag[799] == 0
    step = run(action_main(ctx))
    assert step == Step.TURNEND
    assert (st.flag[798], st.flag[799], st.target) == (1, 1, 1)  # :11、:17、:46
    t = texts(ctx.out)
    assert t[:2] == ["", "行動開始！"]  # :12–13
    assert "【紅葉の行動：休憩】" in t  # :62


def test_action_main_all_done_goes_turnend(ctx):
    st = ctx.state
    st.flag[799] = 3
    assert run(action_main(ctx)) == Step.TURNEND  # :17–21 FLAG:799 = 4 >= CHARANUM
    assert st.flag[799] == 4
    assert texts(ctx.out) == []


def test_action_main_incapable_forces_rest(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[100] = 102
    c.base[0] = 400  # 強制休憩体力 500 以下（IS_ACTION_INCAPABLE.ERB:150）
    run(action_main(ctx))
    t = texts(ctx.out)
    assert "【紅葉の行動：鍛錬】" in t
    assert "紅葉は体力が残り少ないため、休憩します" in t  # ACTION_NGREASON:197
    assert c.base[0] == 400 + 1175  # REST（回復早い 35%）


def test_action_main_no_plan_becomes_rest_and_reserve(ctx):
    st = ctx.state
    st.charas[1].cflag[100] = 0
    run(action_main(ctx))
    assert st.charas[1].cflag[100] == 103  # :55–56
    st.charas[2].cflag[999] = 0  # 控え
    out_before = len(ctx.out.lines)
    run(action_main(ctx))
    assert st.target == 2
    assert texts(ctx.out)[out_before:] == []  # :49–52 表示なしで REST


def test_action_main_support_count(ctx):
    st = ctx.state
    st.charas[2].cflag[100] = 106
    st.charas[3].cflag[100] = 106
    run(action_main(ctx))
    assert st.flag[43] == 2  # :24–33（CHARANUM_ACTIVE = 3 なので 0 に戻らない）


def test_action_main_unported_action(ctx):
    ctx.state.charas[1].cflag[100] = 101
    with pytest.raises(NotImplementedError):
        run(action_main(ctx))
