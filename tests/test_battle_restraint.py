"""S06：拘束後の敵行動・拘束中コマンド・絶頂／射精・敗北（`eragvt.game.battle`）。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號寫在註解），不從實作輸出反推。
他の関数（S05 で移植・テスト済みの TENTACLE_ACCESS／CLOTH_BATTLE_HOSEI／TENTACLE_LEVEL）の値は入力として使う。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, Step, kojo_root
from eragvt.game.battle import after, commands, train
from eragvt.game.battle.cloth import cloth_battle_hosei
from eragvt.game.battle.core import KIZETU, KYOUKOUSOKU, P_HOUSHI, P_NASUGAMAMA, percent_cal, tentacle_access, tentacle_level
from eragvt.game.battle.palam import calc_ecstasy
from eragvt.game.battle.restraint import com_able_restraint
from eragvt.game.battle.sexcom import sex_comable
from eragvt.game.battle.syasei import tentacle_syasei_check, tentacle_syasei_up
from eragvt.game.era import div, times
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # TARGET=1（紅葉）
    s.savestr[13] = "BOSS"  # ENEMY_TYPE_CHECK_F("BOSS") == 1
    s.flag[110] = 0  # 悪堕ちキャラ戦ではない
    s.flag[11] = 3
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def idx(data, var, name):
    return data.index_of(var, name)


def run_gen(gen):
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT 待ちになった")


# --- TENTACLE_SYASEI.ERB@TENTACLE_SYASEI_UP:4–84 ---------------------------------------------


@pytest.mark.parametrize(
    "gikou, insert, vsense, tf4, bust, roll, posture, expected",
    [
        # :11 技巧 2 → TIMES 1.20 = 120、:20 膣挿入 Ｖ感覚 3 → :28 TIMES 1.25 = 150、:72 RAND 50（< 60）→ 変化なし
        (2, 2, 3, 0, 0, 50, 0, 150),
        # 技巧 0 → 100、:52 胸 & 巨乳 2 → :60 TIMES 1.25 = 125、:69 RAND 10 → TIMES 0.90 = 112、
        # :79 なすがまま → TIMES 0.50 = 56
        (0, 0, 0, 8, 2, 10, P_NASUGAMAMA, 56),
        # 技巧 6：:6–18 のどれにも当たらず 100、:76 RAND 99 → TIMES 1.10 = 110、:82 奉仕する → TIMES 1.20 = 132
        (6, 0, 0, 0, 0, 99, P_HOUSHI, 132),
    ],
)
def test_tentacle_syasei_up(ctx, data, gikou, insert, vsense, tf4, bust, roll, posture, expected):
    st = ctx.state
    c = st.charas[1]
    c.abl[idx(data, "ABL", "技巧")] = gikou
    c.abl[idx(data, "ABL", "Ｖ感覚")] = vsense
    c.talent[idx(data, "TALENT", "巨乳")] = bust
    c.tcvarn[2] = posture
    st.temp.insert = insert
    st.tflag[4] = tf4
    st.flag[15] = 7
    st.rng = FixedRng([roll])
    tentacle_syasei_up(ctx, 100)
    assert st.flag[15] == 7 + expected  # :84 FLAG:15 += ARG
    assert st.rng._values == []


def test_tentacle_syasei_check_below_threshold(ctx):
    """:195 FLAG:15 < FLAG:14 かつ TFLAG:4 != 0 → :213–215 TFLAG:5 = 0、RETURN 0,0,0,0（RAND なし）。"""
    st = ctx.state
    st.flag[14], st.flag[15] = 800, 799
    st.tflag[4] = 2
    st.tflag[5] = 99
    st.rng = FixedRng([])
    assert tentacle_syasei_check(ctx) == (0, 0, 0, 0)
    assert st.tflag[5] == 0


def test_tentacle_syasei_check_gaman(ctx, data):
    """:151 TFLAG:4 == 0 かつ FLAG:15 >= FLAG:14 だが 2 倍未満・暴発なし → :172 我慢、:174 SYASEI_UP 50。"""
    st = ctx.state
    c = st.charas[1]
    c.abl[idx(data, "ABL", "技巧")] = 0
    c.tcvarn[2] = 0
    st.temp.insert = 0
    st.flag[14], st.flag[15] = 800, 800
    st.tflag[4] = 0
    st.tflag[20] = 0
    st.rng = FixedRng([50])  # SYASEI_UP:67 RAND:100（50 → 変化なし）
    assert tentacle_syasei_check(ctx) == (0, 0, 0, 0)
    assert st.flag[15] == 850


# --- PALAM_UP.ERB@PALAM_CALC_ECSTASY:826–851（しきい値 PALAM_UP.ERH:11–22）--------------------


@pytest.mark.parametrize(
    "palam, forbid, count, after_palam",
    [
        (9999, 0, 0, 9999),  # どのしきい値にも届かない → 関数終端で RESULT 0、PALAM そのまま
        (10000, 0, 1, 0),  # :839 しきい値:0 → :842 −10000
        (20000, 0, 2, 9999),  # しきい値:1 → −10000 = 10000 → :845–846 しきい値:0 − 1
        (1000000, 0, 10, 9999),  # しきい値:9
        (50000, 1, 0, 50000),  # :833 IS_FORBID_EX > 0 → RETURN 0
    ],
)
def test_calc_ecstasy(ctx, palam, forbid, count, after_palam):
    c = ctx.state.charas[1]
    c.palam[1] = palam
    assert calc_ecstasy(ctx, 1, forbid) == count
    assert c.palam[1] == after_palam


# --- KOJO_ROOT.ERB@KOJO_ROOT:17–39（気絶・結界による口上なし）-------------------------------------


@pytest.mark.parametrize(
    "kizetu, force, shield, code, result, flag62",
    [
        (True, 0, None, "SEX_COM2", 0, 7),  # :17–21 気絶 → FLAG:900 = 0、RETURN 0（FLAG:62 は触らない）
        (True, 1, None, "SEX_COM2", -1, 0),  # FORCEPRINT → 通常処理（口上なし → -1）
        (False, 0, "Ｃ結界耐久力", "SEX_COM12", 0, 7),  # :23 STRFIND は部分一致："SEX_COM1" が "SEX_COM12" に一致
        (False, 0, "Ｃ結界耐久力", "SEX_COM2", -1, 0),  # Ｃ結界は SEX_COM2 を防がない
        (False, 0, "Ｂ結界耐久力", "SEX_SPCOM5", 0, 7),  # :35 SPCOM5
    ],
)
def test_kojo_root_guard(ctx, data, kizetu, force, shield, code, result, flag62):
    st = ctx.state
    c = st.charas[1]
    c.tcvarn[12] = KIZETU if kizetu else 0
    for n in ("Ｃ結界耐久力", "Ｖ結界耐久力", "Ａ結界耐久力", "Ｂ結界耐久力"):
        c.base[idx(data, "BASE", n)] = 0
    if shield:
        c.base[idx(data, "BASE", shield)] = 10
    st.flag[900] = 5
    st.flag[62] = 7
    assert kojo_root(ctx, code, force) == result
    assert st.flag[900] == 0
    assert st.flag[62] == flag62


# --- COMABLE.ERB（拘束中専用コマンド）-----------------------------------------------------------


@pytest.mark.parametrize(
    "n, setup, expected",
    [
        (8, {}, 1),  # :190–206 すべて通過
        (8, {"v12": KYOUKOUSOKU}, 0),  # :196
        (8, {"v8": 0}, 0),  # :201 TCVARn:8 < 10
        (8, {"flag73": 1, "tflag0": 4}, 0),  # :204
        (8, {"v0": 1}, 0),  # :193
        (9, {}, 0),  # :228 変身能力 1 && CFLAG:1 == 0
        (9, {"cflag1": 1}, 1),
        (11, {}, 0),  # :293 苦痛刻印 + 恐怖刻印 < 4
        (11, {"v12": KIZETU}, 1),  # :277
        (11, {"flag73": 1}, 1),  # :290
        (11, {"marks": 4}, 1),  # :293–295
        (40, {}, 0),  # :466 強拘束でない
        (40, {"v12": KYOUKOUSOKU}, 1),
        (40, {"v12": KYOUKOUSOKU | KIZETU}, 0),  # :472
    ],
)
def test_com_able_restraint(ctx, data, n, setup, expected):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[0] = setup.get("v0", 0)
    v[12] = setup.get("v12", 0)
    v[8] = setup.get("v8", 10)  # SHOW_USERCOM／USERCOM が +10 した状態
    c.cflag[1] = setup.get("cflag1", 0)
    st.flag[73] = setup.get("flag73", 0)
    st.tflag[0] = setup.get("tflag0", 10)
    c.mark[idx(data, "MARK", "苦痛刻印")] = setup.get("marks", 0)
    assert com_able_restraint(ctx, n)[0] == expected


# --- SEX_COMABLE.ERB:174–181（衣装破壊：RAND は短絡評価）------------------------------------------


@pytest.mark.parametrize(
    "outer, inner, rolls",
    [
        (0, 0, []),  # :175・:177 とも前半が偽 → RAND を引かずに :180 RETURN 0
        (95, 0, [70, 15]),  # :175 RAND 70（>= 70）→ :177 RAND 15（>= 15）→ RETURN 0
    ],
)
def test_sex_comable_14_fail(ctx, outer, inner, rolls):
    st = ctx.state
    st.temp.cloth[1] = outer  # CLOTH_OUTER_PER
    st.temp.cloth[3] = inner  # CLOTH_INNER_PER
    st.temp.cloth[4] = 50  # CLOTH_INNER_DEF
    st.rng = FixedRng(rolls)
    assert run_gen(sex_comable(ctx, 14)) == 0
    assert st.tflag[10] == 14  # :34
    assert st.rng._values == []


# --- COMF71／72（ＥＸゲージ）、COMF16／17（切り替え）--------------------------------------------


@pytest.mark.parametrize(
    "n, cflag1, burst, bit_on, gauge_after, bit_after",
    [
        (71, 0, 0, False, 400, True),  # COMF71:4–13 bit 0 オフ・未変身 → −100、:26 INVERTBIT
        (71, 0, 0, True, 600, False),  # :14–24 オン → +100
        (72, 2, 0, False, 466, True),  # COMF72 ＳＰ変身中 → −34
        (72, 2, 1, True, 568, False),  # ＳＰ変身中・バースト → +68
    ],
)
def test_com_ex_gauge(ctx, n, cflag1, burst, bit_on, gauge_after, bit_after):
    c = ctx.state.charas[1]
    v = c.tcvarn
    c.cflag[1] = cflag1
    v[217] = burst
    v[6] = 500
    bit = 0 if n == 71 else 1
    v.set_bit(3, bit, bit_on)
    assert run_gen(commands.run_com(ctx, n)) == 0  # RETURN 0：ターンを消費しない
    assert v[6] == gauge_after
    assert v.get_bit(3, bit) == bit_after


@pytest.mark.parametrize("n, key", [(16, 216), (17, 217)])
def test_com16_17_toggle(ctx, n, key):
    v = ctx.state.charas[1].tcvarn
    v[key] = 0
    assert run_gen(commands.run_com(ctx, n)) == 0
    assert v.get_bit(key, 0)
    assert run_gen(commands.run_com(ctx, n)) == 0
    assert not v.get_bit(key, 0)


def test_com69_kizetu(ctx):
    """COMF69:5–20：滞空中なら着地（TCVARn:216 = 4）、体勢＝何もしない、気絶中の文。"""
    st = ctx.state
    v = st.charas[1].tcvarn
    v[216] = 2
    v[12] = KIZETU
    v[0] = 2
    st.rng = FixedRng([])
    assert run_gen(commands.run_com(ctx, 69)) == 1
    assert v[216] == 4
    assert v[2] == -1  # 体勢：何もしない（DIM.ERH）
    assert "紅葉は意識を失っている…" in texts(ctx.out)


def test_com6_second_branch(ctx, data):
    """COMF6：ゲージ（:27–33）、距離＝近（:36）、成否判定（:54–97）の 2 段目。"""
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[0], v[12], v[1], v[11], v[6] = 2, 0, 4, 0, 0  # 心境：冷静（知性 ×1.20：CHARA_SHINKYOU.ERB）
    c.cflag[99] = 0
    st.tflag[10] = 0
    st.tflag[3] = 0
    st.tflag[99] = 0
    l1 = int(tentacle_access(ctx, "CHISEI"))
    hosei = cloth_battle_hosei(ctx, "CHISEI")
    c.maxbase[idx(data, "BASE", "知性")] = l1 * 2
    l0 = div(l1 * 2 * hosei, 100)  # :54–58
    l0 = times(l0, "1.20")  # :61 SHINKYOU_CHECK（冷静は CHISEI ×1.20）
    result = percent_cal(l0, l1)
    assert 60 < result <= 449  # 前提：1 段目は RAND:360 = 359 で不成立、2 段目は RAND:240 = 0 で成立
    # [:28 RAND:16, :73 RAND:360, :81 RAND:240, :82 RAND:RESULT, :100 RAND:100]
    st.rng = FixedRng([5, 359, 0, 41, 0])
    assert run_gen(commands.run_com(ctx, 6)) == 1
    assert st.rng._values == []
    assert v[6] == 35  # 30 + 5
    assert v[0] == 1
    assert st.tflag[99] == 1  # :42
    local = 250 + div(41 % result, 2)  # :82 `RAND:RESULT / 2` は (RAND:RESULT) / 2
    assert st.tflag[3] == local
    assert st.tflag[1] == 0
    t = texts(ctx.out)
    full = str(local).translate(str.maketrans("0123456789", "０１２３４５６７８９"))
    assert "うまく相手を翻弄することができた！" in t
    assert f"油断度＋（{full}）" in t
    assert "EXゲージが大きく溜まった！" in t
    # :100 RAND 0 < 0*0 は偽、TCVARn:1 = 4 → :104 TCVARn:11 ++
    assert v[11] == 1


# --- BATTLE_COM.ERB@SHOW_USERCOM:382–441（拘束中の表示）---------------------------------------------


def test_show_usercom_restraint_layout(ctx):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[0] = 0
    v[12] = KYOUKOUSOKU
    v[8] = 0
    st.flag[73] = 0
    st.rng = GameRng(3)
    train.show_usercom(ctx)
    lines = [ln for ln in ctx.out.lines if ln.kind == "text"]
    t = [ln.text for ln in lines]
    assert v[8] == 0  # :380 +10、:554 −10
    # :386–393 1 行目は COM11 だけ（苦痛＋恐怖刻印 0 → 非表示で空欄）、空行、強拘束なので 40 → 9 → 10
    row = next(x for x in t if "[ 40]" in x)
    assert row.index("引き剥がす(") < row.index("[ 10]")
    assert "振り解く" not in "".join(t)
    # 通常時のコマンド（:444–）は出ない
    assert not any("近距離攻撃[  1]" in x for x in t)
    assert any("ステータス表示[800]" in x for x in t)


# --- BATTLE_TRAIN_AFTER.ERB@EVENTEND:335–422（敗北）--------------------------------------------------


def _defeat_setup(st, c, data):
    c.cflag[0] = 1  # BATTLE_COM_AFTER.ERB@BATTLE_LOSE で 状態_幽閉
    c.cflag[100] = 101
    c.cflag[23] = 5
    c.ex[99] = 2
    c.abl[idx(data, "ABL", "レベル")] = 50
    st.flag[10] = 0
    st.flag[12] = 10000
    st.flag[13] = 3000
    st.flag[20] = 40
    st.flag[46] = 28
    st.flag[47] = 36
    st.flag[52] = 0
    st.flag[852] = 50000
    st.flag[853] = 0
    st.tflag[98] = 2
    st.tflag[0] = 30


def test_event_end_defeat(ctx, data):
    st = ctx.state
    c = st.charas[1]
    _defeat_setup(st, c, data)
    st.flag[73] = 0
    lv = tentacle_level(st)
    juel50 = c.juel[50]
    st.rng = FixedRng([7, 20])  # [:339 RAND:10, :348 RAND:51]
    assert run_gen(after.event_end(ctx)) == Step.TURNEND
    assert st.rng._values == []
    t = texts(ctx.out)
    assert "修練Pを48P手に入れた" in t  # :337 40 + 2 * 4
    exp = min(div(250 * lv, 52) + 7, 750)  # :339–344
    assert c.juel[50] == juel50 + exp
    loss = (lv + 65 - 0) * (30 - 50) - 200 - 20  # :348
    assert st.flag[852] == 50000 + loss
    assert f"防衛力が{abs(loss)}低下した" in t  # :352 ABS LOCAL → RESULT、:366–368
    assert st.flag[853] == -3 and "人気度が3低下した" in t  # :374–376
    assert st.flag[47] == div(36 - 28, 4) + 28  # :418–419
    assert c.cflag[23] == 0  # :421
    assert st.flag[303] == 70000000  # :425–431（S05 と同じ計算）


def test_event_end_defeat_citizen_battle(ctx, data):
    """:355–363 FLAG:73 > 0：RESULT /= 8、FOR LOCAL,1,CHARANUM の後 LOCAL = CHARANUM なので「上昇した」と表示。"""
    st = ctx.state
    c = st.charas[1]
    _defeat_setup(st, c, data)
    st.flag[73] = 1
    st.charas[2].cflag[71] = -1
    lv = tentacle_level(st)
    st.rng = FixedRng([7, 20])
    assert run_gen(after.event_end(ctx)) == Step.TURNEND
    t = texts(ctx.out)
    loss = (lv + 65) * (30 - 50) - 200 - 20
    assert st.flag[852] == 50000 + loss
    assert f"防衛力が{div(abs(loss), 8)}上昇した" in t
    assert st.charas[2].cflag[71] == 1  # :360–363


# --- SUBEVENT_BATTLEE.ERB@SUBEVENT_RELEASE_ECSTASY:163–226 ------------------------------------------


@pytest.mark.parametrize("tflag98, shown", [(0, True), (2, False)])
def test_subevent_release_ecstasy(ctx, data, tflag98, shown):
    st = ctx.state
    c = st.charas[1]
    c.tcvarn[40] = 1
    st.tflag[98] = tflag98
    c.palam[0], c.palam[1], c.palam[2], c.palam[3] = 20000, 5000, 10000, 0
    zecchou = idx(data, "EXP", "絶頂経験")
    roshutsu = idx(data, "EXP", "露出快楽経験")
    e0, r0 = c.exp[zecchou], c.exp[roshutsu]
    j0, j2 = c.juel[0], c.juel[2]
    after.subevent_release_ecstasy(ctx)
    # :170–173 NOWEX = [2, 0, 1, 0]、:176–180 LOCAL = 2
    assert [c.nowex[i] for i in range(4)] == [2, 0, 1, 0]
    assert c.exp[zecchou] == e0 + 2 * 2 + 1 * 2  # :181–188
    assert c.juel[0] == j0 + 1000 * 2 * 2
    assert c.juel[2] == j2 + 1000 * 1 * 2
    assert c.exp[roshutsu] == r0 + 2  # :190
    assert ("絶頂解放" in texts(ctx.out)) == shown  # :194–195 TFLAG:98 != 2 のときだけ
    assert c.tcvarn[40] == 0  # :224


# --- E2E：出撃 → 戦闘（被拘束 → 振り解く／引き剥がす → 撤退）→ SHOP -------------------------------------


def _current_buttons(s: GameSession) -> list[int]:
    return [p.button for ln in s.screen()[-30:] for p in ln.parts if p.button is not None]


def _play_restraint_battle(s: GameSession) -> list[int]:
    """固定方針：拘束中は 振り解く(8)＞引き剥がす(40)＞耐える(10)＞なすがまま(11)、拘束後は撤退(999)、それまでは近距離攻撃。"""
    log = []
    restrained = False
    for _ in range(60):
        if s.phase != Phase.TURN:
            break
        v = s.state.charas[1].tcvarn
        b = _current_buttons(s)
        if v[0] == 0:
            restrained = True
            x = next(n for n in (8, 40, 10, 11) if n in b)
        elif restrained:
            x = 999
        else:
            x = 1
        log.append(x)
        s.input(x)
    return log


def test_e2e_sortie_restraint_back_to_shop(data):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(12))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』で開始
    s.input(1000)  # CHARA_MAKE_MAIN 完成
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    s.state.flag[47] = s.state.flag[46]  # ENCOUNT.ERB:159 ボス遭遇条件
    s.input(101)
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)
    assert s.phase == Phase.TURN
    log = _play_restraint_battle(s)
    assert 8 in log and 40 in log  # 拘束（:969– ENEMY_ACTION 拘束分岐）→ 強拘束（引き剥がす）を経由
    assert s.phase == Phase.SHOP
    st = s.state
    assert st.flag[700] == 0  # BATTLE_TRAIN_AFTER.ERB:7
    assert st.charas[1].cflag[0] == 0  # 敗北していない
    assert any("〈地の文：" in ln.text for ln in s.out.lines)  # 性攻撃の地の文（DEVIATION：表示のみ）
