"""悪堕ちキャラ（S19）：淫謀イベント・悪堕ちキャラ戦（遭遇／行動選択／性コマンド選択／説得／勝利／敗北）・罵声。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號寫在註解），不從實作輸出反推。
淫謀 = `ゲーム内_イベント発生/強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB`（以下 AKUOTI）。
"""

from __future__ import annotations
from _gen_driver import as_generator, run_no_input

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import akuoti, shop, turnend
from eragvt.game.action import Ctx, Step
from eragvt.game.battle import cheers, encount, enemy, restraint, sexcom, source_check, train
from eragvt.game.battle.core import BeginAfterTrain
from eragvt.game.era import div, times
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ENEMY = 3  # 悪堕ちキャラ（初期セット『特装戦隊』の 3 番）


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    """初期セット『特装戦隊』（キャラ 1〜3：女性・処女）、DAY=1、TIME=0、TARGET=1、防衛力 5000。キャラ 3 を悪堕ちにする
    （CFLAG:0 = 3、支配者はボス 1：CFLAG:20 = 0、CFLAG:21 = 1）。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    e = s.charas[ENEMY]
    e.cflag[0] = 3
    e.cflag[20] = 0
    e.cflag[21] = 1
    return Ctx(s, data, TextOutput(), NullNarrationService())


def T(data, n):
    return data.index_of("TALENT", n)


def A(data, n):
    return data.index_of("ABL", n)


def E(data, n):
    return data.index_of("EXP", n)


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def drive(gen):
    """入力待ちにならないジェネレータを最後まで実行して戻り値を返す。"""
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("入力待ちになった")


# =====================================================================================================
# AKUOTI_EVENT（:33–1711）の分岐選択と防衛力ダメージ
# =====================================================================================================


@pytest.fixture
def branches(monkeypatch):
    """末端の分岐関数を記録だけするものに差し替える（分岐の中身は別テスト）。"""
    called: list[str] = []

    def rec(name, ret=None):
        def f(ctx, *a):
            called.append(name)
            return ret

        return f

    for name in ("_bus", "_woman", "_girl", "_couple", "_drug_shop", "_video", "_pet_shop", "_trained"):
        monkeypatch.setattr(akuoti, name, as_generator(rec(name)) if name == "_trained" else rec(name))
    monkeypatch.setattr(akuoti, "_hunt", rec("_hunt", True))  # 狩りは TIMES DAMAGE, 1.50（:243 相当）を行う側
    monkeypatch.setattr(akuoti, "_water", rec("_water"))
    monkeypatch.setattr(akuoti, "_kidnap_woman", rec("_kidnap_woman", 0))
    monkeypatch.setattr(akuoti, "_kidnap_man", rec("_kidnap_man", 0))
    monkeypatch.setattr(akuoti, "_apply", as_generator(rec("_apply")))
    return called


# 防衛力 2500：SQRT = 50。昼 SELECT_N:0 = MIN(80 - 50, 40) = 30、SELECT_N:1 = MIN(80, 80) = 80（:41–43）
#   夜 SELECT_N:0 = 30 / 2 = 15、SELECT_N:1 = MIN(45, 60) = 45（:44–46）
# 市街地 DAMAGE = 50 * 20 + 2500 * 5 / 100 = 1125（:58）、暗躍 DAMAGE = 50 + 2500 * 10 / 100 = 300（:465）
@pytest.mark.parametrize(
    ("time", "rolls", "expected", "damage"),
    [
        (0, [29, 0], ["_bus", "_apply"], 1125),  # :66 RAND:6 == 0 && TIME == 0
        (0, [29, 1, 0], ["_hunt", "_apply"], times(1125, "1.50")),  # :123 RAND:4
        (0, [29, 1, 1, 0], ["_woman", "_apply"], 1125),  # :248 RAND:2
        (0, [29, 1, 1, 1, 0], ["_girl", "_apply"], 1125),  # :362 RAND:2
        (0, [29, 1, 1, 1, 1], ["_couple", "_apply"], 1125),  # :385 ELSE
        (1, [14, 0, 0], ["_hunt", "_apply"], times(1125, "1.50")),  # 夜：RAND:6 == 0 でも TIME != 0 で幼稚園バスなし
        (0, [30, 0], ["_drug_shop", "_apply"], 300),  # :464 30 ≥ SELECT_N:0 → 暗躍、:473 RAND:3
        (0, [79, 1, 0], ["_video", "_apply"], 300),  # :697 RAND:3
        (0, [79, 1, 1, 0], ["_water", "_apply"], times(300, "1.50")),  # :1058 RAND:10（TIMES DAMAGE, 1.50）
        (0, [79, 1, 1, 1, 0], ["_pet_shop", "_apply"], 300),  # :1096 RAND:2
        (0, [79, 1, 1, 1, 1, 0], ["_kidnap_woman", "_apply"], 300),  # :1230 RAND:4
        (0, [79, 1, 1, 1, 1, 1], ["_kidnap_man", "_apply"], 300),  # :1318 ELSE
        (1, [15, 0], ["_drug_shop", "_apply"], 300),  # 夜は 15 から暗躍
        (0, [80], ["_trained"], 0),  # :1609 SELECT ≥ SELECT_N:1 → 被調教系（防衛力ダメージなし）
        (1, [45], ["_trained"], 0),
    ],
)
def test_akuoti_event_branch(ctx, branches, time, rolls, expected, damage):
    st = ctx.state
    st.time = time
    st.flag[852] = 2500
    st.flag[111] = ENEMY
    st.rng = FixedRng(rolls)
    run_no_input(akuoti.akuoti_event(ctx))
    assert st.rng.snapshot() == []
    assert branches == expected
    assert st.flag[852] == 2500 - damage  # :456–462／:1602–1607
    t = texts(ctx.out)
    if damage:
        assert t[-1] == f"防衛力が{damage}低下した！"
    if expected[0] != "_trained":
        # :59／:466 霧の文。:60–61 CSTR:0 != CSTR:1 なら《CSTR:0》を前置
        assert any("不穏な影を落とす。" in x for x in t)


def test_akuoti_event_gameover_mode_has_no_trained_branch(ctx, branches):
    """:1609 `ELSEIF CHECK_GAMEOVER_F() == 0`：ゲームオーバーモード（FLAG:0 = 0）では被調教系に入らず何もしない。"""
    st = ctx.state
    shop.change_gameover_mode(st)
    st.flag[852] = 0
    st.flag[111] = ENEMY
    # 防衛力 0：昼 SELECT_N:0 = 40、SELECT_N:1 = 80
    st.rng = FixedRng([80])
    run_no_input(akuoti.akuoti_event(ctx))
    assert branches == []
    assert texts(ctx.out) == []


def test_akuoti_event_zero_defense_no_damage_line(ctx, branches):
    """防衛力 0 → DAMAGE = 0（:58）→ :456 `IF DAMAGE` 不成立で「防衛力が…低下した！」は出ない。"""
    st = ctx.state
    st.flag[852] = 0
    st.flag[111] = ENEMY
    st.rng = FixedRng([39, 1, 1, 0])  # 39 < 40 → 市街地、一般女性
    run_no_input(akuoti.akuoti_event(ctx))
    assert branches == ["_woman", "_apply"]
    assert not any("防衛力が" in x for x in texts(ctx.out))
    assert st.flag[852] == 0


# --- 男を攫って快楽攻め（:1318–1580）：`(処女 < 1 || ISMALE) && RAND:n == 0` は短絡 ---------------------------


@pytest.mark.parametrize(
    ("virgin", "rolls", "loc", "v_sex"),
    [
        # 処女の女性：:1362／:1440 の括弧内が偽 → RAND:3／RAND:2 を引かずに :1543 フェラ
        #   [LOCALS RAND:3, 声 RAND:3, LOCAL:124 RAND:5, LOCAL:123 RAND:3, LOCAL:131 RAND:2]
        (1, [0, 0, 2, 1, 1], {124: 6, 123: 7, 131: 2}, 0),
        # 非処女：:1362 RAND:3 == 0 → 逆レイプで触手化。女性なので :1428–1433 Ｖ経験 2 + RAND:3、精液 Ｖ*2 + RAND:3、V_SEX = 精液
        (-1, [0, 0, 0, 2, 1], {120: 4, 123: 9}, 9),
        # 非処女：RAND:3 = 1 → :1440 RAND:2 == 0 → 正常位。Ｖ経験 1 + RAND:3、精液 Ｖ + RAND:3、絶頂経験 1（:1530–1542）
        (-1, [0, 0, 1, 0, 1, 2], {120: 2, 123: 4, 122: 1}, 4),
        # 非処女：RAND:3 = 1、RAND:2 = 1 → :1543 フェラ
        (-1, [0, 0, 1, 1, 4, 0, 0], {124: 8, 123: 8, 131: 1}, 0),
    ],
)
def test_kidnap_man(ctx, data, virgin, rolls, loc, v_sex):
    st = ctx.state
    st.flag[111] = ENEMY
    st.charas[ENEMY].talent[T(data, "処女")] = virgin
    st.rng = FixedRng(rolls)
    got: dict[int, int] = {}
    assert akuoti._kidnap_man(ctx, got) == v_sex
    assert st.rng.snapshot() == []
    assert got == loc
    assert ctx.out.lines[-1].wait  # :1580 PRINTW


def test_kidnap_woman_has_no_state_change(ctx):
    """:1274 `IF 1;RAND:3 == 0` は常に真。LOCAL・V_SEX の設定は無い（:1230–1316）。RAND は LOCALS と声の 2 回だけ。"""
    st = ctx.state
    st.flag[111] = ENEMY
    st.rng = FixedRng([1, 1, 1, 1])  # :1231 RAND:3、:1236 RAND:2 → 少女、:1250／:1252 → 「特別に見逃してあげる」
    assert akuoti._kidnap_woman(ctx) == 0
    assert st.rng.snapshot() == []
    t = texts(ctx.out)
    assert t[0] == "意識の戻った少女は、自身が半裸の状態で触手に拘束されている事実に気が付いた。"
    assert t[-1] == "完全に正気を失い触手の孕み苗床と化した雌穴――愛しい彼女の姿だった・・・"


def test_apply_runs_ninsin_with_tentacle_father(ctx, monkeypatch):
    """:1582–1599：TARGET を悪堕ちキャラにして COMMON_PRISON・経験加算、V_SEX があれば NINSIN_HANTEI, V_SEX, 20, 200。"""
    from eragvt.game.battle import ninsin
    from eragvt.game.prison import commands as pc

    st = ctx.state
    st.flag[111] = ENEMY
    st.target = 1
    calls = []
    monkeypatch.setattr(pc, "common_prison", lambda c, up: calls.append(("prison", c.state.target, tuple(up))))
    monkeypatch.setattr(pc, "common_prison_exp", lambda c, n, v: v and calls.append(("exp", c.state.target, n, v)))
    monkeypatch.setattr(ninsin, "ninsin_hantei", as_generator(lambda c, *a: calls.append(("ninsin", c.state.target, a))))
    run_no_input(akuoti._apply(ctx, {120: 4, 123: 9}, 9))
    assert calls == [
        ("prison", ENEMY, (0,) * 12),
        ("exp", ENEMY, 120, 4),
        ("exp", ENEMY, 123, 9),
        ("ninsin", ENEMY, (9, 20, 200)),
    ]
    assert st.target == 1  # :1599 TARGET = SELECT


# --- 被調教系（:1609–1710）-----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cflag20", "cflag21", "flag110", "flag111"),
    [
        (0, 1, 0, 0),  # :1624–1626 CFLAG:20 < 2 → FLAG:110 = FLAG:111 = 0
        (2, 7, 1, 7),  # :1627–1629 CFLAG:20 == 2 → FLAG:110 = 1、FLAG:111 = CFLAG:21（固有番号のまま入れる）
    ],
)
def test_trained(ctx, data, monkeypatch, cflag20, cflag21, flag110, flag111):
    from eragvt.game.prison import commands as pc
    from eragvt.game.prison import event as pe

    st = ctx.state
    e = st.charas[ENEMY]
    e.cflag[20] = cflag20
    e.cflag[21] = cflag21
    e.cflag[30] = 10
    e.cflag[31] = 2
    e.cflag[220] = 0
    e.base[30] = 5  # 結界（:1636–1642）
    for k in range(31, 34):
        e.base[k] = 0
    st.flag[111] = ENEMY
    st.target = 1
    mode = st.flag[0]
    seen = []
    monkeypatch.setattr(pe, "_msg", lambda c, name, code: seen.append(("msg", name, c.state.target, c.state.flag[0])))
    monkeypatch.setattr(pe, "tentacle_access_prison", lambda c, who, key: seen.append(("routine", who, key)) or 0)
    monkeypatch.setattr(pc, "prison_comable", as_generator(lambda c, n: seen.append(("com", n))))
    before = e.exp[E(data, "被姦経験")]
    # CFLAG:220 == 0 → :1646 の RAND:100 は引かない（&& 短絡）。[:1657 RAND:100 = 50 → < 60 → PRISON_COMABLE 4、:1697 RAND:4]
    st.rng = FixedRng([50, 2])
    run_no_input(akuoti._trained(ctx))
    assert st.rng.snapshot() == []
    assert seen == [
        ("msg", "MESSAGE_PRISON_PRISENTENCE", ENEMY, 0),  # :1615–1616 TARGET = 悪堕ちキャラ、FLAG:0 = 0
        ("routine", ENEMY, "PRISON_ROUTINE"),
        ("com", 4),
    ]
    assert texts(ctx.out)[0] == f"陥落奉仕：{e.callname}"  # :1619
    assert (st.flag[110], st.flag[111]) == (flag110, flag111)
    assert [st.shield[i] for i in range(4)] == [1, 0, 0, 0]
    assert e.exp[E(data, "被姦経験")] == before + 1  # :1694
    assert e.cflag[31] == 3  # :1695
    assert e.cflag[30] == 10 + 3 + 2  # :1697
    assert st.target == 1 and st.flag[0] == mode  # :1707–1709


# =====================================================================================================
# 悪堕ちキャラ戦
# =====================================================================================================


def test_encount_enemy_akuoti(ctx, data, monkeypatch):
    """ENCOUNT.ERB@ENCOUNT_ENEMY:19–131。昼 40 + 遭遇率アップ 0 - MIN(5000/500, 40) = 30（:57–64）。"""
    st = ctx.state
    c = st.charas[1]
    e = st.charas[ENEMY]
    transformed = []
    from eragvt.game.battle import func

    monkeypatch.setattr(func, "transform", lambda cx, arg, who=-999: transformed.append((arg, who)))
    # [:74 RAND:100 = 29 < 30、:77–79 RAND:(候補 1 人) = 0]
    st.rng = FixedRng([29, 0])
    assert encount.encount_enemy(ctx) == 1
    assert st.rng.snapshot() == []
    assert (st.flag[110], st.flag[111], st.savestr[13]) == (1, ENEMY, "BOSS")  # :22–24、:79
    assert c.exp[E(data, "戦闘経験")] == 1  # :28
    lv = e.abl[A(data, "レベル")]
    assert st.flag[12] == e.maxbase[0] + div(e.maxbase[11] * (15 + lv), 2)  # :115
    assert st.flag[13] == st.flag[12]
    assert (st.flag[14], st.flag[15], st.flag[16], st.flag[17], st.flag[22]) == (1000, 0, 760 + lv * 10, 0, -1)
    # :126–127 変身能力持ちで未変身なら TRANSFORM 1, FLAG:111
    assert transformed == ([(1, ENEMY)] if e.talent[T(data, "変身能力")] > 0 else [])


def test_encount_enemy_miss_and_encount_up_redirect(ctx):
    st = ctx.state
    st.rng = FixedRng([30])  # 30 < 30 不成立
    assert encount.encount_enemy(ctx) == 0
    assert st.flag[110] == 1  # 遭遇しなくても 1 のまま（ENCOUNT_BOSS:144 で 0 に戻す）
    # :81–86 CFLAG:23（遭遇率アップ）が最大のキャラに置き換わる（幽閉中 CFLAG:0 = 1 でも）
    st.charas[2].cflag[0] = 1
    st.charas[2].cflag[23] = 40
    st.charas[ENEMY].cflag[23] = 30  # 候補の遭遇率アップは :50 で加算 → 30 + 30 - 10 = 50
    st.rng = FixedRng([49, 0])
    assert encount.encount_enemy(ctx) == 1
    assert st.flag[111] == 2
    assert st.charas[2].cflag[23] == 0  # :87–89 40 / 2 = 20 < 25 → 0


@pytest.mark.parametrize(
    ("rolls", "kisei", "base", "f13", "f902", "f907", "expected"),
    [
        ([54], 0, (100, 100), 100, 0, 0, 1),  # :1086–1088 < 55 攻撃
        ([55], 0, (100, 100), 100, 0, 0, 6),  # < 70 邪悪な波動
        ([70], 1, (100, 100), 100, 0, 0, 2),  # < 85 絡みつく（寄生あり）
        ([70], 0, (100, 100), 100, 0, 0, 5),  # :1149–1150 寄生なしなら押し倒す
        ([85], 1, (100, 100), 100, 0, 0, 3),  # < 95 体液を吐く
        ([85], 0, (100, 100), 100, 0, 0, 1),  # :1153–1154 寄生なしなら攻撃
        ([95], 0, (100, 100), 100, 0, 0, 1),  # :1121–1122 距離を取る → 残り体力 90％以上なら攻撃
        ([95], 0, (100, 100), 89, 0, 0, 4),
        ([70, 14], 1, (100, 100), 100, 1, 0, 1),  # :1104–1114 FLAG:902 絡みつき率ダウン
        ([70, 40], 1, (100, 100), 100, 1, 0, 2),
        ([54, 19], 1, (100, 100), 100, 0, 1, 2),  # :1116–1117 FLAG:907 絡みつき率アップ
        ([54, 20], 1, (100, 100), 100, 0, 1, 1),
        ([54, 39], 0, (0, 100), 100, 0, 0, 6),  # :1125–1133 体力のみ 0
        ([54, 79], 0, (0, 100), 100, 0, 0, 5),  # 絡みつく → 寄生なし → 押し倒す
        ([54, 39], 0, (100, 0), 100, 0, 0, 1),  # :1135–1143 気力のみ 0
        ([54], 1, (0, 0), 100, 0, 0, 2),  # :1145–1146 両方 0
    ],
)
def test_select_enemy_action(ctx, data, monkeypatch, rolls, kisei, base, f13, f902, f907, expected):
    st = ctx.state
    c = st.charas[1]
    st.flag[110] = 1
    st.flag[111] = ENEMY
    st.charas[ENEMY].talent[T(data, "寄生")] = kisei
    c.base[0], c.base[1] = base
    st.flag[12], st.flag[13] = 100, f13
    st.flag[902], st.flag[907] = f902, f907
    st.tflag[11] = st.tflag[12] = 7
    monkeypatch.setattr(enemy, "attack_place_decision", lambda cx: None)
    st.rng = FixedRng(rolls)
    enemy.select_enemy_action(ctx)
    assert st.rng.snapshot() == []
    assert st.tflag[10] == expected
    assert (st.tflag[11], st.tflag[12]) == (0, 0)  # :1075–1076


# --- ENEMY_ACTION_SEX_ROUTINE の悪堕ちキャラ分（ENEMY_ACTION.ERB:1172–1343）--------------------------------
# 敵の ABL が全て 0 なら区間は C[0,5] V[5,20] A[25,35] B[60,70] 苦痛[130,135] 奉仕[265,275] 羞恥[540,545]
# （LOCAL:1x は累積の上限を足しこむので広がる：:1178–1215）。LOCAL:99 = RAND:100 なので苦痛系以降は区間からは選ばれない
# （予約 TFLAG:17 のときだけ）。


@pytest.mark.parametrize(
    ("futanari", "tflag17", "rolls", "expected"),
    [
        (0, -1, [3, 50], 0),  # C：欲望 < 3 で SP 条件は RAND 前に偽、:1233 `RAND:100 < 40 && LOCAL:101` は RAND を引く
        (0, -1, [21, 22, 99, 3, 0], 0),  # どの区間でもない → :1340–1342 再抽選
        (0, -1, [30, 99, 99], 4),  # A：:1276 RAND、:1279 RAND → 弱
        (1, -1, [30, 10, 10], 5),  # ふたなり → LOCAL:101 = 1、A 強
        (1, -1, [65, 0, 0], 7),  # B：:1290 欲望 < 3 で SP 不成立（RAND は先に引く）→ B 強
        (0, 8, [99, 0, 0], 8),  # 予約（TFLAG:17 = 8）：LOCAL:99 を引いた上で苦痛系
    ],
)
def test_akuoti_sex_routine(ctx, data, futanari, tflag17, rolls, expected):
    st = ctx.state
    st.flag[110] = 1
    st.flag[111] = ENEMY
    e = st.charas[ENEMY]
    for n in ("Ｃ感覚", "Ｖ感覚", "Ａ感覚", "Ｂ感覚", "マゾっ気", "従順", "奉仕精神", "露出癖", "欲望"):
        e.abl[A(data, n)] = 0
    e.talent[T(data, "ふたなり")] = futanari
    e.talent[T(data, "寄生")] = 0
    st.charas[1].tcvarn[0] = 0
    st.tflag[17] = tflag17
    st.tflag[10] = 2
    st.rng = FixedRng(rolls)
    assert sexcom.enemy_action_sex_routine(ctx) == expected
    assert st.rng.snapshot() == []


# --- COM47 説得する（戦闘コマンド(ヒロイン)/COMF47.ERB）---------------------------------------------------


@pytest.mark.parametrize(
    ("chisei", "rolls", "tflag3", "line"),
    [
        # 知性 300 / 敵 100 → PERCENT_CAL = 300（:39）。:40 RAND:360 + 90 = 299 < 300 → 650 + RAND:300 / 2
        (300, [209, 101], 5 + 650 + 50, "迫真の言葉に相手は動揺している！"),
        # :47 RAND:240 + 60 = 299 < 300 → 400 + RAND:300 / 2
        (300, [210, 239, 99], 5 + 400 + 49, "相手を少し動揺させることができたようだ・・・"),
        # 知性 250 → 250。:40 359 + 90、:47 239 + 60 は不成立、:54 RAND:180 + 30 = 209 < 250 → 250 + RAND:250 / 4
        (250, [359, 239, 179, 7], 5 + 250 + 1, "相手の瞳の奥に微かな変化があったようにも見える・・・"),
        # 知性 100 → 100：どれも不成立
        (100, [359, 239, 179], 5, "相手は聞く耳を持たない様子だ・・・"),
    ],
)
def test_com47_persuade(ctx, data, monkeypatch, chisei, rolls, tflag3, line):
    st = ctx.state
    c = st.charas[1]
    st.flag[110] = 1
    st.flag[111] = ENEMY
    c.maxbase[data.index_of("BASE", "知性")] = chisei
    st.charas[ENEMY].maxbase[data.index_of("BASE", "知性")] = 100  # :32–33 MAXBASE:(FLAG:111):知性
    monkeypatch.setattr(restraint, "cloth_battle_hosei", lambda cx, kind, *a: 100)
    monkeypatch.setattr(restraint, "shinkyou_check", lambda cx, kind, v: v)
    c.tcvarn[1] = 0
    c.tcvarn[11] = 3
    st.tflag[3] = 0
    ex = c.ex[99]
    st.rng = FixedRng(rolls)  # :69 TCVARn:1 == 0 → RAND:100 は引かない
    assert drive(restraint.com47(ctx)) == 1
    assert st.rng.snapshot() == []
    assert st.tflag[3] == tflag3  # :9 +5 と成否
    assert c.tcvarn[2] == restraint.P_SETTOKU  # :12
    assert line in texts(ctx.out)
    assert c.ex[99] == ex + 1  # :67 行動ポイント
    assert c.tcvarn[11] == 4  # :76 TCVARn:11 ++


def test_com47_shinkyou_change(ctx, data, monkeypatch):
    """:69–72 `TCVARn:1 > 0 && RAND:100 < TCVARn:11 * 10` → 心境 = 6（TCVARn:11 は増えない）。"""
    st = ctx.state
    c = st.charas[1]
    st.flag[110] = 1
    st.flag[111] = ENEMY
    monkeypatch.setattr(restraint, "cloth_battle_hosei", lambda cx, kind, *a: 100)
    monkeypatch.setattr(restraint, "shinkyou_check", lambda cx, kind, v: v)
    c.maxbase[data.index_of("BASE", "知性")] = 100
    st.charas[ENEMY].maxbase[data.index_of("BASE", "知性")] = 100
    c.tcvarn[1] = 2
    c.tcvarn[11] = 3
    st.rng = FixedRng([359, 239, 179, 29])
    drive(restraint.com47(ctx))
    assert st.rng.snapshot() == []
    assert (c.tcvarn[1], c.tcvarn[11]) == (6, 3)


@pytest.mark.parametrize(
    ("akuoti_battle", "prevcom", "tflag20", "guard", "able"),
    [
        (1, 0, 0, 10, 1),
        (0, 0, 0, 10, 0),  # COMABLE.ERB:624–625 相手が触手
        (1, 1, 0, 10, 0),  # :627 攻撃した後
        (1, 47, 0, 10, 0),  # :642 連続使用
        (1, 0, 12, 10, 0),  # :633 イラマチオ直後
        (1, 0, 0, 9, 0),  # :650 TCVARn:8 < 10
    ],
)
def test_com_able47(ctx, akuoti_battle, prevcom, tflag20, guard, able):
    st = ctx.state
    c = st.charas[1]
    st.flag[110] = akuoti_battle
    st.flag[111] = ENEMY
    st.temp.prevcom = prevcom
    st.tflag[20] = tflag20
    c.tcvarn[8] = guard
    c.tcvarn[12] = 0
    assert restraint.com_able_restraint(ctx, 47)[0] == able


# --- 勝利（SOURCE_CHECK.ERB:312–405）-----------------------------------------------------------------------


def test_victory_akuoti_rescues_enemy_and_its_captives(ctx, data):
    st = ctx.state
    e = st.charas[ENEMY]
    st.flag[110] = 1
    st.flag[111] = ENEMY
    e.cflag[240] = 33
    for k in (20, 21, 30, 31):
        e.cflag[k] = 5
    captive = st.charas[2]  # 悪堕ちキャラに幽閉されていた（CFLAG:20 = 2、CFLAG:21 = 固有番号）
    captive.cflag[0] = 1
    captive.cflag[20] = 2
    captive.cflag[21] = 33
    captive.cflag[220] = 2
    source_check._victory_akuoti(ctx)
    assert st.flag[110] == 0  # :314
    assert e.cflag[0] == -1  # :336 救出直後
    assert [e.cflag[k] for k in (20, 21, 30, 31)] == [0, 0, 0, 0]
    assert (e.base[0], e.base[1], e.base[2]) == (1, 1, 1)
    # :384–404 連鎖救出
    assert captive.cflag[0] == -1 and captive.cflag[100] == 103 and captive.cflag[220] == 0
    assert [captive.cflag[k] for k in (20, 21, 30, 31)] == [0, 0, 0, 0]


def test_victory_akuoti_no_rescue_option(ctx):
    """:333–334 CONFIG_CHECK_PRISON_F(11)（悪堕ちキャラが正気に戻らない）なら連れ去られて終わり。"""
    st = ctx.state
    st.flag[110] = 1
    st.flag[111] = ENEMY
    st.flag.set_bit(804, 11, True)
    source_check._victory_akuoti(ctx)
    assert st.flag[110] == 0
    assert st.charas[ENEMY].cflag[0] == 3
    assert any("連れ去ってしまった" in x for x in texts(ctx.out))  # MESSAGE_OTHER.ERB:714–721


# --- 敗北（SOURCE_CHECK.ERB:969–1095）---------------------------------------------------------------------


def _lose_setup(ctx, data):
    st = ctx.state
    c = st.charas[1]
    st.flag[110] = 1
    st.flag[111] = ENEMY
    st.flag[799] = 3
    c.cflag[0] = 0
    return st, c, st.charas[ENEMY]


def test_lose_to_corrupted_is_raped_not_imprisoned(ctx, data, monkeypatch):
    """:1064–1086 悪堕ちキャラ（寄生なし）に敗北 → SUBEVENT_BATTLE_RAPED_ENEMY（SUBEVENT_BATTLEE.ERB:24–51）。"""
    st, c, e = _lose_setup(ctx, data)
    e.talent[T(data, "寄生")] = 0
    got = []
    monkeypatch.setattr(source_check, "palam_cal", as_generator(lambda cx, *a: got.append(a)))
    before = c.exp[E(data, "被姦経験")]
    with pytest.raises(BeginAfterTrain):
        run_no_input(source_check._battle_lose(ctx))
    assert got == [(0, 0, 0, 0, 0, 0, 0, 0, 2000, 2000, 0, 0)]  # LOCAL:8 屈服・LOCAL:9 恥情 = 2000
    assert c.exp[E(data, "被姦経験")] == before + 1
    assert c.cflag[0] == 0 and st.flag[799] == 3  # 幽閉されない
    assert st.flag[110] == 1  # 勝利時以外は戻らない
    assert f"戦闘結果：敗北 -{e.callname}の解放失敗" in texts(ctx.out)  # :980–981


@pytest.mark.parametrize(
    ("enemy_state", "kisei", "maniac13", "cflag20", "cflag21"),
    [
        (2, 0, 0, "e20", "e21"),  # :1046–1062 洗脳キャラ：ご主人様（洗脳した触手）が幽閉
        (3, 1, 1, 2, "e240"),  # :1066–1072 寄生持ち悪堕ちキャラ＋悪堕ち触手アリ：悪堕ちキャラが幽閉
    ],
)
def test_lose_to_akuoti_imprisoned(ctx, data, enemy_state, kisei, maniac13, cflag20, cflag21):
    st, c, e = _lose_setup(ctx, data)
    e.cflag[0] = enemy_state
    e.cflag[20] = 0
    e.cflag[21] = 4
    e.cflag[240] = 33
    e.talent[T(data, "寄生")] = kisei
    st.flag.set_bit(850, 13, not maniac13)  # CONFIG_CHECK_MANIAC_F(13) = 1 - GETBIT(FLAG:850, 13)
    with pytest.raises(BeginAfterTrain):
        run_no_input(source_check._battle_lose(ctx))
    assert c.cflag[0] == 1
    assert c.cflag[20] == {"e20": 0}.get(cflag20, cflag20)
    assert c.cflag[21] == {"e21": 4, "e240": 33}[cflag21]
    assert c.exp[E(data, "幽閉経験")] == 1 and c.exp[E(data, "異常経験")] >= 1
    assert st.flag[799] == 2  # :1091–1092


# --- 統合：遭遇 → 戦闘 → 勝利／敗北（BEGIN TRAIN → … → BEGIN TURNEND）-----------------------------------------


def _battle(ctx, seed):
    st = ctx.state
    st.charas[1].cflag[100] = 101
    st.rng = FixedRng([0, 0])  # ENCOUNT_ENEMY:74 RAND:100、:78 RAND:1
    assert encount.encount(ctx) == 1
    assert st.flag[110] == 1 and st.flag[111] == ENEMY
    st.rng = GameRng(seed)
    gen = train.run_train(ctx)
    next(gen)
    for _ in range(200):
        btn = [v for ln in ctx.out.lines[-40:] for (_, v) in ln.buttons]
        try:
            gen.send(1 if 1 in btn else (btn[0] if btn else 0))  # 近距離攻撃 [1]
        except StopIteration as ex:
            return ex.value
    raise AssertionError("戦闘が終わらない")


def test_integration_akuoti_battle_victory(ctx):
    """敵体力 1：最初の攻撃で FLAG:13 <= 0 → 勝利（:117–）→ 悪堕ちキャラ救出 → EVENTEND → TURNEND。"""
    st = ctx.state
    e = st.charas[ENEMY]
    st.charas[1].cflag[100] = 101
    st.rng = FixedRng([0, 0])
    assert encount.encount(ctx) == 1
    st.flag[13] = 1
    st.rng = GameRng(0)
    gen = train.run_train(ctx)
    next(gen)
    with pytest.raises(StopIteration) as ex:
        gen.send(1)
    assert ex.value.value == Step.TURNEND
    assert st.flag[110] == 0 and e.cflag[0] == -1
    assert any("ダメージを与えた" in x for x in texts(ctx.out))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_integration_akuoti_battle_defeat(ctx, data, seed):
    """体力・気力・性耐性 1 で出撃 → 敵の行動（SELECT_ENEMY_ACTION）で 0 → 悪堕ちキャラ（寄生なし）への敗北は
    犯されるだけ（幽閉されない）→ TURNEND。FLAG:110 は 1 のまま。"""
    st = ctx.state
    c = st.charas[1]
    c.base[0] = c.base[1] = c.base[2] = 1
    before = c.exp[E(data, "被姦経験")]
    assert _battle(ctx, seed) == Step.TURNEND
    assert st.flag[110] == 1
    assert c.cflag[0] == 0
    assert c.exp[E(data, "被姦経験")] >= before + 1  # 戦闘中の挿入でも増えうる。敗北時の SUBEVENT で必ず +1
    t = texts(ctx.out)
    assert f"戦闘結果：敗北 -{st.charas[ENEMY].callname}の解放失敗" in t
    assert "〈地の文：MESSAGE_SUBEVENT_BATTLE_RAPED_ENEMY〉" in t  # SUBEVENT_BATTLEE.ERB:38


# =====================================================================================================
# 戦闘イベント.ERB：悪堕ち経験者（EXP:陥落経験 > 0）への観衆
# =====================================================================================================


def test_perform_cheers_hate(ctx, data):
    """:309–387。観戦 3 人 → 罵声 3 回（候補 1〜10、RANDCHOOSE_F → CLEARSPECIFICCHOOSE）、心境 = 消沈（7）。"""
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "陥落経験")] = 1
    c.cstr[60] = ""
    st.savestr[10] = ""
    st.flag[70], st.flag[71] = 2, 1
    # RANDCHOOSE_F（コモン関数.ERB:39–47）：RAND:10 = 9 → 10、RAND:9 = 0 → 1、RAND:8 = 0 → 2
    st.rng = FixedRng([9, 0, 0])
    cheers.perform_cheers_hate(ctx)
    assert st.rng.snapshot() == []
    t = texts(ctx.out)
    assert "見れば数名の一般人が自分たちの身の安全も顧みずに" in t  # :319–330
    assert t[t.index("見れば数名の一般人が自分たちの身の安全も顧みずに") + 1:][:1] == [f"{c.callname}に怨嗟の声を張り上げている！"]
    assert "「魔法少女だ・・・裏切り者の魔法少女だ！！」" in t  # :335–341 女性 → 魔法少女
    assert "「正義の味方のフリかよ！」" in t
    assert "「魔法少女、負けてしまえ！！」" in t
    assert c.tcvarn[1] == 7  # :381


def test_perform_cheers_hate_no_corruption(ctx):
    st = ctx.state
    st.flag[70] = 3
    st.rng = FixedRng([])
    cheers.perform_cheers_hate(ctx)
    assert texts(ctx.out) == []


@pytest.mark.parametrize(
    ("fn", "rolls", "line", "pop"),
    [
        # MISS :520–551（RAND:100 < 35 → 陥落経験 → RAND:3 == 0、:524 RAND:100 は LOCAL = 0 で不成立）
        ("miss", [0, 0, 0], "一般人は悲鳴を上げながら飛び退いた・・・", 0),
        # MISS :542–550：RAND:(観戦 3) = 2 > 0 かつ RAND:100 < 10 → 人気度 -1
        ("miss", [0, 1, 1, 2, 9], "観衆の落胆の声が聞こえる・・・", -1),
        # HIT :717–726：RAND:3 == 0、RAND:3 = 1、RAND:100 = 19 < 20 → 人気度 -1
        ("hit", [0, 0, 1, 19], "一般人から歓声が上がった。", -1),
        ("hit", [0, 1, 1], "観衆から歓声が上がった・・・", 0),  # :732–734
    ],
)
def test_cheers_tentacle_corrupted(ctx, data, fn, rolls, line, pop):
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "陥落経験")] = 1
    c.cflag[40] = c.cflag[41] = 0
    st.flag[70], st.flag[71], st.flag[72] = 2, 1, 0
    st.flag[853] = 10
    st.rng = FixedRng(rolls)
    f = cheers.perform_cheers_tentacle_miss_hantei if fn == "miss" else cheers.perform_cheers_tentacle_hit_hantei
    f(ctx)
    assert st.rng.snapshot() == []
    assert line in texts(ctx.out)
    assert st.flag[853] == 10 + pop


# =====================================================================================================
# S20 使用者裁決（2026-10-01）：防衛力が負のときの SQRT（DEVIATION）
# =====================================================================================================


def test_akuoti_attack_negative_defence_sqrt_as_zero(ctx, monkeypatch):
    """原作 AKUOTI_ATTACK:20 `SQRT(FLAG:852)` は負數で CodeEE。裁決により 0 として RAND:(0 / 2 + 20) = RAND:20。"""
    st = ctx.state
    st.flag[852] = -100
    st.time = 0  # LOCAL = 40（:7–13）
    called: list = []
    monkeypatch.setattr(akuoti, "akuoti_event", as_generator(lambda ctx: called.append(ctx.state.flag[111])))
    st.rng = FixedRng([19, 0])  # RAND:20 → 19 < 40、:28 RANDCHOOSE_F（候補 1 人）
    run_no_input(turnend.akuoti_attack(ctx))
    assert called == [ENEMY]
    assert st.rng.snapshot() == []


@pytest.mark.parametrize(
    ("rolls", "expected"),
    [
        ([39, 0], ["_bus", "_apply"]),  # :48 SELECT = 39 < 40 → 市街地（:58）、:66 RAND:6 = 0 → 幼稚園バス
        ([40, 0], ["_drug_shop", "_apply"]),  # 40 ≥ SELECT_N:0 → 暗躍（:465）、:473 RAND:3 = 0
    ],
)
def test_akuoti_event_negative_defence_sqrt_as_zero(ctx, branches, rolls, expected):
    """同じ裁決を AKUOTI_EVENT の SQRT（:42／:58／:465）にも適用：SELECT_N:0 = MIN(80 - 0, 40) = 40、SELECT_N:1 = 80。
    D2（使用者裁決 2026-10-02）：損失式の防衛力の項も 0 → DAMAGE = 0（原作どおりなら :58 は 0 + (-100) * 5 / 100 = -5、
    :465 は -10 で、:458 `FLAG:852 -= DAMAGE` により防衛力が増える）→ :456 `IF DAMAGE` 不成立：防衛力は変わらず文も出ない。"""
    st = ctx.state
    st.flag[852] = -100
    st.flag[111] = ENEMY
    st.time = 0
    st.rng = FixedRng(rolls)
    run_no_input(akuoti.akuoti_event(ctx))
    assert branches == expected
    assert st.rng.snapshot() == []
    assert st.flag[852] == -100
    assert not any("防衛力が" in x for x in texts(ctx.out))
