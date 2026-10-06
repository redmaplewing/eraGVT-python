"""S28a：拠点防衛・戦闘支援・情報収集・スケジュール・戦闘基礎 Lv5・拉致監禁表示・ACTION_MAIN の終端。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），不從實作輸出反推。
開局（特装戦隊）：[1] 紅葉（MAXBASE 体力 2787／気力 2454、BASE:体力基礎 2006／気力基礎 1748、Lv1、BASE:知性 100、変身能力 1、
CSTR:1 = CALLNAME）、[2] 桃香（巨乳 1）、[3] 蒼美。FLAG:852 = 5000、MONEY = 5000、FLAG:46 = 28、FLAG:47 = 0。
"""

from __future__ import annotations
from _gen_driver import as_generator

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import gather, schedule, shop
from eragvt.game.action import Ctx, Step, action_main, guard, print_transcallname, sengiup, support, training
from eragvt.game.battle import encount as encount_mod
from eragvt.game.era import div, isqrt, times
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.game.turnend import tentacle_level
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

E18 = 10**18


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    c = Ctx(s, data, TextOutput(), NullNarrationService())
    c.globals.mem.global_[54] = 2  # 情報収集の変身設定「常に変身しない」（選択肢を省略）
    return c


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def run(gen, inputs=()):
    """ジェネレータを入力列で最後まで回して戻り値を返す。入力が尽きても待っているなら "WAIT"。"""
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            if not inputs:
                return "WAIT"
            gen.send(inputs.pop(0))
    except StopIteration as stop:
        return stop.value


def keigen(data, c, amount: int, base: int) -> int:
    """`汎用関数/コモン関数.ERB@SYOUHI_KEIGEN`:947–960 の式（期待値の計算用）。"""
    b = c.base[base + 50]
    th = 1000 if base in (0, 1) else 100
    if b > th:
        return max(amount - div(amount * (b - th), 2500), div(amount, 2))
    return amount


# --- ACTION_GUARD.ERB@GUARD:3–30／ACTION.ERB:114–130 -----------------------------------------


def test_guard_no_encount(ctx, monkeypatch):
    st, data = ctx.state, ctx.data
    called = []
    monkeypatch.setattr(encount_mod, "encount", lambda ctx: 0)
    monkeypatch.setattr(encount_mod, "mob_tentacle_encount", lambda ctx: called.append(1) or 0)
    c = st.charas[1]
    c.cflag[100] = 105
    st.flag[799] = 0
    st.rng = FixedRng([10])  # :25 RAND:26
    hp, mp, d, f41 = c.base[0], c.base[1], st.flag[852], st.flag[41]
    step = run(action_main(ctx))
    assert step == Step.TURNEND
    assert st.flag[41] == f41 + 1  # :116
    assert called == [1]  # :12–13（ENCOUNT_BOSS:144 で FLAG:110 = 0）
    assert c.cflag[101] == -1  # :4
    # :17–23：MAXBASE × 0.12 を SYOUHI_KEIGEN（体力基礎 2006・気力基礎 1748 > 1000）
    assert c.base[0] == hp - keigen(data, c, times(2787, "0.12"), 0)
    assert c.base[1] == mp - keigen(data, c, times(2454, "0.12"), 1)
    assert st.flag[852] == d + 125 + 1 * 2 + 10  # :25–26
    assert "防衛力が137上昇した" in texts(ctx.out)  # :27 PRINTFORM ＋ ACTION.ERB:123 PRINTL
    assert "紅葉はパトロールを行っている……" in texts(ctx.out)


def test_guard_flag110_skips_mob(ctx, monkeypatch):
    st = ctx.state
    called = []
    monkeypatch.setattr(encount_mod, "encount", lambda ctx: 0)
    monkeypatch.setattr(encount_mod, "mob_tentacle_encount", lambda ctx: called.append(1) or 0)
    st.flag[110] = 1  # :12 `!RESULT && !FLAG:110`
    st.target = 1
    st.rng = FixedRng([0])
    assert guard(ctx) == 0
    assert called == []


@pytest.mark.parametrize("r", [1, -1])
def test_guard_encount_begins_train(ctx, monkeypatch, r):
    """ACTION.ERB:122–130：RESULT が 0 以外（遭遇 > 0、雑魚戦の候補なし < 0 も）は BEGIN TRAIN、体力等は減らない。"""
    st = ctx.state
    monkeypatch.setattr(encount_mod, "encount", lambda ctx: r)
    c = st.charas[1]
    c.cflag[100] = 105
    st.flag[799] = 0
    hp, d = c.base[0], st.flag[852]
    assert run(action_main(ctx)) == Step.TRAIN
    assert (c.base[0], st.flag[852]) == (hp, d)


# --- ACTION_SUPPORT.ERB@SUPPORT:3–47 ------------------------------------------------------


@pytest.mark.parametrize("f43, factor", [(1, "0.24"), (2, "0.18"), (3, None)])
@pytest.mark.parametrize("kenshin", [0, 1])
def test_support(ctx, f43, factor, kenshin):
    st, data = ctx.state, ctx.data
    st.target = 1
    st.flag[43] = f43
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "献身的")] = kenshin
    hp, mp, syu, exp0, chisei = c.base[0], c.base[1], c.juel[20], c.juel[50], c.base[13]
    st.rng = FixedRng([7, 3, 0])  # :60 RAND:11、:62 RAND:5、:65 RAND:3 == 0
    support(ctx)
    for idx, mx, cur in ((0, 2787, hp), (1, 2454, mp)):
        local = mx if factor is None else times(mx, factor)  # :38–43（FLAG:43 が 1／2 以外は TIMES なし）
        if kenshin:
            local = times(local, "1.10")  # :45–46
        assert c.base[idx] == cur - keigen(data, c, local, idx)
    assert c.juel[20] == syu + 15 + 7  # :60 GET_SYUREN
    gain = min(div(tentacle_level(st) - 3, 1) * 10 + 3, 150)  # :61–63（Lv1）
    assert c.juel[50] == exp0 + gain
    assert c.base[13] == chisei + 2  # :65–67
    assert c.cflag[101] == -1
    assert "紅葉はオペレーション業務に専念している……" in texts(ctx.out)


def test_support_chisei_plus1_and_none(ctx):
    st = ctx.state
    st.target = 1
    st.flag[43] = 1
    c = st.charas[1]
    st.rng = FixedRng([0, 0, 1, 1])  # :65 RAND:3 = 1 → :68 RAND:3 = 1 < 2 → +1
    support(ctx)
    assert c.base[13] == 101
    st.rng = FixedRng([0, 0, 1, 2])  # :68 RAND:3 = 2 → 上昇なし
    support(ctx)
    assert c.base[13] == 101


def test_support_without_frontline_rests(ctx):
    """ACTION.ERB:133–140：出撃・防衛の予約が無く FLAG:41 == 0 なら休憩し FLAG:43 -= 1。"""
    st = ctx.state
    for i in (1, 2, 3):
        st.charas[i].cflag[100] = 106
    st.flag[799] = 0
    st.flag[41] = 0  # 開局直後は オープニング処理.ERB:286 で 1（TURNEND で 0 に戻る）
    st.rng = GameRng(0)
    assert run(action_main(ctx)) == Step.TURNEND
    assert st.charas[1].cflag[101] == -1  # REST:7
    assert "戦闘を行うメンバーが居ないため、休憩にします" in texts(ctx.out)


# --- ACTION_GATHER_INFORMATION.ERB ---------------------------------------------------------


def _gather(ctx, rng, inputs):
    ctx.state.target = 1
    ctx.state.rng = FixedRng(rng)
    return run(gather.gather_information(ctx), inputs)


def test_gather_rumor(ctx, data):
    st = ctx.state
    c = st.charas[1]
    r = _gather(ctx, [60, 0, 0, 1, 1, 0, 1, 5], [0])
    assert r is None
    # :103 RAND:85 = 60、:119 RAND:4 = 0 → :135 RAND:2 = 0「日常生活」、:142 60 - SQRT(5000)/10 = 53
    # → :155–157 GATHER = 8 + RAND:3(1)；:170 CALC_CHARM_FEAT_OTHER：RANDOM(2)=1 → RANDOM(3)=0・魅了 0 < 28 → 2
    # → :176 RAND:4 = 1、:182 RAND:12 = 5（コネなし）
    assert st.flag[47] == 9
    assert c.exp[data.index_of("EXP", "魅了経験")] == 2
    assert c.cflag[101] == 0  # :80
    t = texts(ctx.out)
    assert "紅葉は日常生活の中で出来る限り情報を集めた。" in t
    assert "その結果、敵の居場所のヒントになりそうな話を聞くことができた！" in t
    assert "紅葉による調査の結果、探索度が9上昇しました。" in t
    assert "魅了経験が2上がった" in t
    assert "変身せずにそのまま情報収集を行います。(♀)" in t  # TRANSFORMATION_SELECT:44–48、:120–131（GLOBAL:54 = 2）


def test_gather_rumor_negative_defense_deviation(ctx):
    """DEVIATION D4（使用者裁決 2026-10-02）：:142 の SQRT(FLAG:852) は防衛力が負なら 0。"""
    st = ctx.state
    st.flag[852] = -300
    _gather(ctx, [60, 0, 0, 1, 1, 0, 1, 5], [0])
    assert st.flag[47] == 9  # HANTEI = 60 → < 75 のまま


def test_gather_rumor_informant(ctx):
    st = ctx.state
    c = st.charas[1]
    # HANTEI 5 → < 10：GATHER 2 + RAND:3(0)、CALC：RANDOM(2)=1、RANDOM(3)=1、魅了 0 < 29 → 1、平凡・人外なし
    # :176 は HANTEI < 50 なので RAND を引かず、:182 RAND:12 = 0 → 情報屋（:193 RAND:7 = 0 小太り）→ [0]
    r = _gather(ctx, [5, 0, 1, 0, 1, 1, 0, 0], [0, 0])
    assert r is None
    assert c.cflag[122] == 1 | 4  # SETBIT 0（変身していない）、SETBIT 2
    assert "紅葉は『コネ：情報屋』を獲得した！" in texts(ctx.out)


def test_gather_investigate(ctx):
    st = ctx.state
    c = st.charas[1]
    # :238 SQRT(100-50)*4 + RAND:(SQRT(100)+5) = 28 + 14 = 42；:254 RAND:3=2、:272 RAND:2=1 → :291 RAND:4+1 = 3人の死者
    # :295 RAND:4 = 0；42 < 50 → GATHER 5 + RAND:5(3) = 8；:326 変身能力 1 なので短絡、:328 RAND:3=1、:330 RAND:3=2 → 知性 0
    # :421 CFLAG:121 == 0 && 42 >= 40 && RAND:(MAX(10 - 4, 2)) = 0 → コネ：警察関係者
    r = _gather(ctx, [14, 2, 1, 2, 0, 3, 1, 2, 0], [1])
    assert r is None
    assert st.flag[47] == 8
    assert c.cflag[121] == 1
    assert c.base[13] == 100
    t = texts(ctx.out)
    assert "紅葉は3人の死者を出したという" in t
    assert "つい最近起きた猟奇殺人事件について調べてみることにした。" in t
    assert "なんと、紅葉は『コネ：警察関係者』を獲得した！" in t


def test_gather_investigate_citizen_encounter(ctx):
    """ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:350–416：S36 接通遭遇。"""
    st = ctx.state
    st.flag.set_bit(802, 5)
    # HANTEI28、知性+1 → 遭遇、CASE0、825判定29 < 30。
    st.flag[852] = 0
    _gather(ctx, [0, 2, 1, 2, 0, 1, 0, 9999, 0, 0, 29], [1])
    assert st.flag[45] == 6002 and st.flag[73] == 5
    assert st.charas[1].cflag[825] == 1


def test_gather_buy_money(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[122] = 0b100001  # 面識あり（bit0）・上客（bit5）・特徴のない男
    # :536–537 RAND:25 = 4 → 600、RAND:50 = 10 → 5500；bit4 = 0・bit5 = 1 → :549 ×1.1 なし；LOCAL:2 = 100
    r = _gather(ctx, [4, 10], [2, 1, 0])
    assert r is None
    # [1]（所持金 5000 < 5500）は :585 不成立 → GOTO INPUT_2；[0]：MONEY -= 600、:582 600*100/120 = 500 → SQRT(500)/3 + 5 = 12
    assert st.money == 5000 - 600
    assert st.flag[47] == 12
    t = texts(ctx.out)
    assert "紅葉は情報屋(特徴のない男)と連絡を取った・・・【所持金：5000】" in t
    assert " [1]とっておきの情報を買う(5500)" in t
    assert "情報提供の結果、探索度が12上昇しました。" in t


def test_gather_buy_cut(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[122] = 1
    _gather(ctx, [0, 0], [2, -1])
    assert c.cflag[122] == 0  # :911
    assert st.flag[47] == 0


def test_gather_buy_body_honban(ctx, data, monkeypatch):
    from eragvt.game.battle import ninsin

    st = ctx.state
    c = st.charas[1]
    c.cflag[122] = 1  # 面識あり、bit4 = 0 → カラダで買える（:570 淫乱）
    c.talent[data.index_of("TALENT", "淫乱")] = 1
    calls = []
    monkeypatch.setattr(ninsin, "ninsin_hantei", as_generator(lambda ctx, a, b, f=0: calls.append((a, b, f)) or 0))
    juel_v = c.juel[data.index_of("JUEL", "快Ｖ")]
    giko = c.abl[data.index_of("ABL", "技巧")]
    # 値段 RAND 0／0、本番：RAND:5 = 2、上客判定 RAND:4 = 1（!= 0 → SETBIT 5）
    r = _gather(ctx, [0, 0, 2, 1], [2, 2, 3])  # 情報を買う → [2]カラダで → [3]本番
    assert r is None
    assert c.talent[data.index_of("TALENT", "処女")] == -1  # :841–846
    assert c.cflag[206] == 12
    gather_v = 5 + 10 + 2 + 0 + div(giko, 2)  # :846、:875
    assert st.flag[47] == gather_v
    assert c.juel[data.index_of("JUEL", "習得")] >= 200
    assert c.exp[data.index_of("EXP", "Ｖ経験")] == 2
    assert c.exp[data.index_of("EXP", "精液経験")] == 2
    assert c.juel[data.index_of("JUEL", "快Ｖ")] == juel_v + 10 * c.abl[data.index_of("ABL", "Ｖ感覚")]
    assert calls == [(2, 800, -1)]  # :898–899 NINSIN_HANTEI, 2, 800, 誰とも知れない相手（DIM.ERH:254 = -1）
    assert c.cflag.get_bit(122, 5)  # :922–927 上客
    assert "口づけを交わしながら膣内射精を受け入れた。" in texts(ctx.out)


def _kidnapped(st, who=2, n71=30):
    st.charas[who].cflag[0] = 4
    st.charas[who].cflag[71] = n71


@pytest.mark.parametrize(
    "n71, rng, after, text",
    [
        (30, [19, 0], 15, "最後に目撃された場所が判明した！"),  # 20/2 = 10 → +5 = 15、30-15 = 15（:1008）
        (12, [9, 0], 2, "何者かの手で監禁されている事実が判明した！"),  # 10/2 = 5 → 10、12-10 = 2（:1012）
        (15, [1], 15, None),  # 2/2 = 1（< 5）、15-1 = 14：どの分岐でもない（:1048–1049 表示のみ）
    ],
)
def test_gather_search_kidnapped(ctx, n71, rng, after, text):
    st = ctx.state
    _kidnapped(st, n71=n71)
    r = _gather(ctx, rng, [3, 2])
    assert r is None
    assert st.charas[2].cflag[71] == after
    assert st.flag[47] == 0  # 拉致監禁の捜索は RESEARCH_PROGRESS を呼ばない
    if text:
        assert f"紅葉による調査の結果、桃香が{text}" in texts(ctx.out)


def test_gather_search_kidnapped_found_citizen_encounter(ctx):
    """ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:1016–1046：位置特定後遭遇。"""
    st = ctx.state
    _kidnapped(st, n71=15)
    _gather(ctx, [19, 0, 1, 30], [3, 2])
    assert st.charas[2].cflag[71] == -1
    # 特殊シチュエーション.ERB@ADDBATTLESITUATION:43–44 是覆寫，不是附加。
    assert st.temp.battle_situation == "先制無し,支援無効,レイプなし,,,"
    assert st.flag[45] == 6002 and st.flag[73] == 5


def test_gather_search_list_and_invalid(ctx):
    st = ctx.state
    _kidnapped(st, n71=30)
    st.charas[3].cflag[0] = 1  # 幽閉中
    r = _gather(ctx, [19, 0], [3, 1, 999, 2])  # CHARA_LIST 3：1（無事）・999（ARG:2 = 1 でキャンセル不可）は不可
    assert r is None
    t = texts(ctx.out)
    assert any(x.startswith("[2] ") and x.endswith("（誘拐監禁中）") for x in t)
    assert any(x.startswith("[3] ") and x.endswith("（幽閉中）") for x in t)
    assert t.count("正しい値を入力してください") == 2


def test_gather_search_imprisoned_and_corrupted(ctx):
    st = ctx.state
    st.charas[2].cflag[0] = 1
    _gather(ctx, [19], [3, 2])  # 20/2 = 10 → +5（:971–972）
    assert st.flag[47] == 15
    st.charas[3].cflag[0] = 3
    st.charas[3].cflag[23] = 80
    _gather(ctx, [19], [3, 3])  # 20 ≥ 15 → +5 = 25；80 + 25 → 90 で頭打ち（:1068–1070）
    assert st.charas[3].cflag[23] == 90


def test_gather_menu_invalid_choice(ctx):
    """:71–78：情報屋のコネなしの [2]、行方不明者なしの [3] は「正しい値を入力してください」。"""
    st = ctx.state
    r = _gather(ctx, [60, 0, 0, 1, 1, 0, 1, 5], [2, 3, 0])
    assert r is None
    assert texts(ctx.out).count("正しい値を入力してください") == 2


def test_gather_schedule(ctx):
    """:25–60：CFLAG:112 > 0 → RES_SCHEDULE（INPUT なし）。項目 4（仲間の捜索）で行方不明者なし → RESULT = 0（噂話）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[112] = 4 + 2 * 100  # [仲間の捜索, 事件の捜査]
    r = _gather(ctx, [60, 0, 0, 1, 1, 0, 1, 5], [])
    assert r is None
    assert c.cflag[101] == 0
    assert c.cflag[112] == E18 + 204
    assert "スケジュール：仲間の捜索（実行不能）代わりに事件の捜査を行います" in texts(ctx.out)


# --- ACTIONsub_TRANSFORMATION_SELECT.ERB -----------------------------------------------------


@pytest.mark.parametrize(
    "g54, inputs, transformed, g_after",
    [
        (1, [], 1, 1),  # :47–48 常に変身 → RESULT 0
        (0, [0], 1, 0),
        (0, [1], 0, 0),
        (0, [9], 1, 1),  # :68–76 GLOBAL:(53 + LOCAL 1) = 1
        (0, [10], 0, 2),
        (0, [5, 0], 1, 0),  # 不正値 → GOTO INPUT_LOOP_0_0
    ],
)
def test_transformation_select(ctx, g54, inputs, transformed, g_after):
    st = ctx.state
    ctx.globals.mem.global_[54] = g54
    st.target = 1
    r = run(gather.action_transformation_select(ctx, 1, "情報収集"), inputs)
    assert r is None
    assert st.charas[1].cflag[1] == transformed
    assert ctx.globals.mem.global_[54] == g_after
    t = texts(ctx.out)
    if transformed:
        assert "紅葉は変身した！(♀)" in t  # :96、:109–117（オトコの変化なし → 「→」なし）
    if g54 == 0:
        assert "紅葉は変身できます。変身した状態で情報収集を行いますか？" in t  # :57–58（変身後呼び名 = CALLNAME → LOCALS ""）


def test_gather_transform_released_after(ctx):
    """GATHER_INFORMATION:85–86：変身して行動しても FLAG:73 == 0 なら TRANSFORM 0。"""
    st = ctx.state
    ctx.globals.mem.global_[54] = 1
    _gather(ctx, [60, 0, 0, 1, 1, 0, 1, 5], [0])
    assert st.charas[1].cflag[1] == 0


# --- CALC_CHARM_FEAT.ERB@CALC_CHARM_FEAT_OTHER:22–59 -----------------------------------------


@pytest.mark.parametrize(
    "e, rng, expected",
    [
        (0, [1, 0], 2),  # :32–33
        (27, [1, 0], 2),  # 29 → :46 の上限 29 以内
        (28, [0, 0], 1),  # :26 RANDOM(2)=0 だが 28 < 30、:32 RANDOM(3)=0 だが 28 >= 28 → :38 +1
        (29, [1, 1], 0),
        (30, [0], 1),
        (98, [0], 1),
        (99, [0, 1], 0),  # :26 は 99 を除外 → :49–54 で 99 のまま
        (100, [1, 1], 0),
    ],
)
def test_calc_charm_feat_other(ctx, data, e, rng, expected):
    st = ctx.state
    st.target = 1
    st.charas[1].exp[data.index_of("EXP", "魅了経験")] = e
    st.rng = FixedRng(rng)
    assert gather.calc_charm_feat_other(ctx, 1) == expected


# --- ACTIONsub_SCHEDULE.ERB@RES_SCHEDULE:453–495 ---------------------------------------------


def test_res_schedule_cycle(ctx):
    c = ctx.state.charas[1]
    c.cflag[110] = 3 + 5 * 100 + 1 * 10000  # 項目 [3, 5, 1]
    got = []
    for _ in range(4):
        got.append(schedule.res_schedule(c, 110))
    assert got == [2, 4, 0, 2]  # 項目番号 - 1 を順に、3 個（STRLENFORM 5 桁 → 3）で 0 に戻る
    assert c.cflag[110] == E18 + 10503
    assert schedule.res_schedule(c, 110, 2) == 0  # ARG:1 指定：参照のみ
    assert c.cflag[110] == E18 + 10503


def test_res_schedule_nine_items_wraps(ctx):
    c = ctx.state.charas[1]
    c.cflag[110] = 8 * E18 + sum(1 * 100**k for k in range(9))
    assert schedule.res_schedule(c, 110) == 0
    assert c.cflag[110] // E18 == 0  # :483–484 SC_VAR > 8 → 0


def test_training_with_schedule(ctx):
    """ACTION_TRAINING.ERB:66–74：CFLAG:110 > 0 なら INPUT なしで RES_SCHEDULE の値。"""
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[110] = 1 + 4 * 100  # [走り込み, 筋トレ]
    assert run(training(ctx)) is None
    assert c.cflag[101] == 0
    assert c.cflag[110] == E18 + 401


def test_training_schedule_invalid_waits_input(ctx, data):
    """:273–279：非戦闘員に「近距離戦闘訓練」（項目 7）→ CFLAG:111 <= 0 なら「正しい値」→ INPUT。"""
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "変身能力")] = -1
    c.cflag[110] = 7
    assert run(training(ctx)) == "WAIT"
    assert "正しい値を入力してください" in texts(ctx.out)


# --- ACTIONsub_SCHEDULE.ERB@SCHEDULE（SHOP [160]） ------------------------------------------


@pytest.mark.parametrize(
    "start, inputs, cflag",
    [
        (0, [1, 4, 999], {110: 1 + 4 * 100}),  # 項目入力（:415–420）→ 決定（:431–442）
        (0, [1, 997, 999], {110: -1}),  # ON/OFF（:425–426）
        (1 + 3 * 100, [110, 99, 999], {110: 3}),  # 項目削除（:403–413）
        (2 * E18 + 1 + 3 * 100, [999], {110: E18 + 301}),  # :254–259 実行番号の正規化（項目 2 は空 → 1）
        (301, [1, 998], {110: 301}),  # キャンセル
        (0, [202, 3, 1, 999], {112: 1}),  # モード変更（:397–401）、仲間の捜索は行方不明者なしで不可
    ],
)
def test_schedule_screen(ctx, start, inputs, cflag):
    st = ctx.state
    st.target = 1
    c = st.charas[1]
    c.cflag[100] = 102
    c.cflag[110] = start
    assert run(schedule.schedule_gen(ctx), inputs) is None
    for k, v in cflag.items():
        assert c.cflag[k] == v
    assert any("スケジュール設定" in x for x in texts(ctx.out))


# --- コモン関数.ERB@SENGIUP:737–790 ------------------------------------------------------------


def _lv5_ready(st, data, who=1, gain=0):
    c = st.charas[who]
    c.talent[data.index_of("TALENT", "変身能力")] = -1
    c.talent[data.index_of("TALENT", "変身時ＴＳ")] = 1
    c.talent[data.index_of("TALENT", "変身能力獲得")] = gain
    c.abl[33] = 4
    c.exp[8] = 1000
    return c


@pytest.mark.parametrize(
    "gain, inputs, henshin, ts",
    [
        (0, [1, 0], 1, 1),  # :746–751 確認 → [1] → 変身能力 1 → 変身後名 [0]
        (0, [0], 0, 0),  # :752–756
        (0, [7, 0], 0, 0),  # 不正値 → GOTO INPUT_LOOP_0
        (1, [0], 1, 1),  # :740–742 変身能力獲得 > 0 → 確認なし（変身後名の確認だけ）
        (-1, [], 0, 0),  # :743–745
    ],
)
def test_sengiup_lv5(ctx, data, gain, inputs, henshin, ts):
    st = ctx.state
    st.target = 1
    c = _lv5_ready(st, data, gain=gain)
    assert run(sengiup(ctx, 1, 3), inputs) is None
    assert c.abl[33] == 5
    assert c.talent[data.index_of("TALENT", "変身能力")] == henshin
    assert c.talent[data.index_of("TALENT", "変身時ＴＳ")] == ts
    assert "紅葉は戦闘の基礎を完全にマスターした！" in texts(ctx.out)


def test_sengiup_lv5_transafter_name_continues(ctx, data):
    st = ctx.state
    st.target = 1
    _lv5_ready(st, data)
    run(sengiup(ctx, 1, 3), [1, 1, 1, "星光", 1])
    assert st.charas[1].cstr[0] == st.charas[1].cstr[1] == "星光"


def test_sengiup_lv5_profile_size(ctx, data):
    """:761–768：TARGET の CFLAG:34（成長曲線）≠ 0 なら変身時サイズ（MAXBASE:身長〜腰囲）を生成。"""
    from eragvt.game.body import BUST, HEIGHT, HIP, WAIST, WEIGHT, generate_char_size

    st = ctx.state
    st.target = 1
    c = _lv5_ready(st, data)
    c.cflag[34] = 1
    c.cflag[33] = 50
    expected = generate_char_size(data, c, 1)[2:7]
    run(sengiup(ctx, 1, 3), [1, 0])
    assert tuple(c.maxbase[s] for s in (HEIGHT, WEIGHT, BUST, WAIST, HIP)) == tuple(expected)


# --- SHOP_SHOW_SITUATION_LIST.ERB:113–138 拉致監禁中 -------------------------------------------


def test_situation_list_kidnapped_uses_result(ctx):
    """:126 PRINT_TRANSCALLNAME(RESULT)：ボスのループ後 RESULT = 0（MASTER の呼び名）。"""
    st, data = ctx.state, ctx.data
    _kidnapped(st)
    st.charas[2].cflag[70] = 7
    out = TextOutput()
    shop.shop_show_situation_list(st, data, out, NullNarrationService())
    assert f"{print_transcallname(st, 0)}：廃ビルに拉致監禁中 3日目　" in texts(out)


def test_situation_list_kidnapped_after_akuoti_prison(ctx):
    """:87–95 悪堕ちキャラによる幽閉の表示が RESULT = 支配者の番号を残す → :126 はその名前。"""
    st, data = ctx.state, ctx.data
    _kidnapped(st)
    st.charas[3].cflag[0] = 1
    st.charas[3].cflag[20] = 2
    st.charas[3].cflag[21] = st.charas[1].cflag[240]
    out = TextOutput()
    shop.shop_show_situation_list(st, data, out, NullNarrationService())
    assert "紅葉：廃ビルに拉致監禁中 0日目　" in texts(out)


def test_situation_list_kidnapped_result130_error(ctx):
    """ボスでもラスボスでもない（FLAG:110 = 1：悪堕ちキャラ戦の後）→ RESULT は入力値 130 のまま → 原作も添字範囲外。"""
    st, data = ctx.state, ctx.data
    _kidnapped(st)
    st.flag[110] = 1
    with pytest.raises(NotImplementedError, match="130"):
        shop.shop_show_situation_list(st, data, TextOutput(), NullNarrationService())


# --- Web セッション：ACTION_MAIN の終端・統合 --------------------------------------------------


def _session(data, tmp, seed=3):
    s = GameSession(data, Path(tmp), rng=GameRng(seed), narration=NullNarrationService())
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』
    s.input(1000)  # CHARA_MAKE_MAIN 完成
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    assert s.phase == Phase.SHOP
    return s


def _reserve(s, plans):
    for i, p in plans.items():
        s.input(i)
        s.input(p)


def test_fallthrough_from_usershop_back_to_shop(data, monkeypatch):
    """ACTION.ERB:86–96 で RESULT < 0（雑魚戦の候補なし）→ ACTION_MAIN 終端 → @USERSHOP 終了 → @SHOW_SHOP（EVENTSHOP なし）。"""
    monkeypatch.setattr(encount_mod, "encount", lambda ctx: 0)
    monkeypatch.setattr(encount_mod, "mob_tentacle_encount", lambda ctx: -1)
    with tempfile.TemporaryDirectory() as tmp:
        s = _session(data, tmp)
        day = s.state.day
        _reserve(s, {1: 101})
        s.input(100)
        s.input(9)
        assert s.phase == Phase.SHOP
        assert s.state.day == day  # EVENTSHOP を通らない
        # 2 人目以降は行動していない（SHOW_SHOP:20 で FLAG:799 = 0）
        assert sum(1 for ln in s.out.lines if "の行動：" in ln.text) == 1


def test_fallthrough_from_turnend_halts(data, monkeypatch):
    monkeypatch.setattr(encount_mod, "encount", lambda ctx: 0)
    monkeypatch.setattr(encount_mod, "mob_tentacle_encount", lambda ctx: -1)
    with tempfile.TemporaryDirectory() as tmp:
        s = _session(data, tmp)
        _reserve(s, {1: 103, 2: 101})
        s.input(100)
        s.input(9)
        assert s.phase == Phase.HALTED
        assert any("スクリプト終端" in ln.text for ln in s.out.lines)


def test_integration_guard_support_gather_turn(data):
    """SHOP で 防衛・支援・情報収集を予約 → 行動 → TURNEND → EVENTSHOP → SHOP。"""
    with tempfile.TemporaryDirectory() as tmp:
        s = _session(data, tmp)
        st = s.state
        d0, t0 = st.flag[852], st.time
        _reserve(s, {1: 105, 2: 106, 3: 107})
        s.input(100)
        s.input(9)
        for _ in range(50):  # 変身の確認（[1] いいえ）、情報収集の選択 [0]、情報屋が出たら [0] …
            if s.phase != Phase.TURN:
                break
            s.input(1 if any("情報収集を行いますか？" in ln.text for ln in s.out.lines[-6:]) else 0)
        assert s.phase == Phase.SHOP
        st = s.state
        assert st.time != t0  # EVENTSHOP で昼夜切り替え
        assert st.charas[1].cflag[101] == -1  # GUARD:4
        assert st.charas[2].cflag[101] == -1  # SUPPORT:4
        assert st.charas[3].cflag[101] == 0  # GATHER:80（噂話）
        t = [ln.text for ln in s.out.lines]
        assert "紅葉はパトロールを行っている……" in t
        assert "桃香はオペレーション業務に専念している……" in t
        assert "噂話の聞き込み" in t
        assert st.flag[852] != d0
