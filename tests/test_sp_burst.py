"""S16：ＳＰ変身（COM73）・ＳＰバースト（COM70）・ＳＰフルバースト（COM74）・バースト攻撃（COM17、TCVARn:217）。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/ゲーム内_戦闘処理/`、行號寫在註解），不從實作輸出反推。
バースト補正の検証では、S05 で移植・テスト済みの判定値（バーストなしの成功値・DAMAGE）を入力として使い、
バースト分岐の式（COMMON_BATTLE_HANTEI.ERB:367–382 等）だけを手計算で当てる。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.action import Ctx, print_transcallname
from eragvt.game.battle import commands, hantei
from eragvt.game.battle.cloth import cloth_battle_hosei
from eragvt.game.battle.core import (
    KIZETU,
    KOUKOTSU,
    P_GUARD,
    correction_trans,
    get_battle_situation,
    percent_cal,
)
from eragvt.game.era import div, times
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

STYLES = {"連続": 1, "装甲": 2, "撹乱": 3, "重撃": 4, "広範": 5, "全力": 6, "知略": 7, "設置": 8, "使役": 9, "反撃": 10, "通常": 0}


class ZeroRng(FixedRng):
    """RAND は常に 0（回数は記録する）。"""

    def __init__(self) -> None:
        super().__init__([])
        self.calls: list[int] = []

    def rand(self, n: int) -> int:
        self.calls.append(n)
        return 0


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # TARGET=1（紅葉：変身能力 1、性格 勝気）
    s.savestr[13] = "BOSS"
    s.flag[110] = 0
    s.flag[10] = 0  # ボス戦
    s.flag[11] = 3
    s.flag[12] = s.flag[13] = 100000
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def I(data, var, name):  # noqa: E743
    return data.index_of(var, name)


def run_gen(gen):
    try:
        next(gen)
    except StopIteration as e:
        return e.value
    raise AssertionError("INPUT 待ちになった")


def set_style(ctx, style: str, dist: int = 2) -> None:
    c = ctx.state.charas[1]
    c.tcvarn[0] = dist
    c.cdflag[(dist, ctx.data.index_of("CDFLAG2", "戦闘スタイル"))] = STYLES[style]


# --- COMABLE.ERB@COM_ABLE17:425–453、COM_ABLE73:764–798、COM_ABLE74:802–830 ---------------------


@pytest.mark.parametrize(
    "n, setup, expected",
    [
        (17, {"v4": 200, "cflag1": 1}, 1),
        (17, {"v4": 199, "cflag1": 1}, 0),  # :434 ゲージ 200 未満・SP モードでない
        (17, {"v4": 0, "cflag1": 2}, 1),  # :434 SP モード中はゲージ不問
        (17, {"v4": 300, "cflag1": 0}, 0),  # :437 変身前
        (17, {"v4": 300, "cflag1": 1, "cflag99": 50}, 0),  # :440
        (17, {"v4": 300, "cflag1": 1, "v0": 0}, 0),  # :430 拘束中
        (73, {"v4": 150, "v6": 50, "cflag1": 1}, 1),  # :770 TCVARn:4 + TCVARn:6 >= 200
        (73, {"v4": 150, "v6": 49, "cflag1": 1}, 0),
        (73, {"v4": 300, "cflag1": 0}, 0),  # :776 変身前
        (73, {"v4": 300, "cflag1": 2}, 0),  # :779 SP 変身中
        (73, {"v4": 300, "cflag1": 1, "v12": KOUKOTSU}, 0),  # :785
        (73, {"v4": 300, "cflag1": 1, "sit": "EX不可,"}, 0),  # :794
        (73, {"v4": 300, "cflag1": 1, "tr": 0}, 0),  # :773 変身能力なし
        (74, {"v4": 0, "cflag1": 2}, 1),  # :811 変身能力ありならゲージ不問
        (74, {"v4": 500, "cflag1": 1}, 0),  # :814 SP 変身前
        (74, {"v4": 499, "cflag1": 0, "tr": 0}, 0),  # :811 変身能力なしはゲージ 500 必要
        (74, {"v4": 500, "cflag1": 0, "tr": 0}, 1),
        (74, {"v4": 0, "cflag1": 2, "v12": KIZETU}, 0),  # :817
        (74, {"v4": 0, "cflag1": 2, "sit": "EX不可,"}, 0),  # :826
    ],
)
def test_com_able_sp(ctx, data, n, setup, expected):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    v[0] = setup.get("v0", 2)
    v[4] = setup.get("v4", 0)
    v[6] = setup.get("v6", 0)
    v[12] = setup.get("v12", 0)
    v[8] = 10  # SHOW_USERCOM／USERCOM が +10 した状態
    c.cflag[1] = setup.get("cflag1", 0)
    c.cflag[99] = setup.get("cflag99", 0)
    c.talent[I(data, "TALENT", "変身能力")] = setup.get("tr", 1)
    st.temp.battle_situation = setup.get("sit", "")
    assert commands.com_able(ctx, n)[0] == expected


# --- COMF73.ERB@COM73 ＳＰ変身 -------------------------------------------------------------------


@pytest.mark.parametrize(
    "seikaku, shinkyou, word",
    [
        (12, 6, "高揚"),  # 勝気：:38–41 その他
        (15, 2, "怒り"),  # 面倒くさがり：:31–33
        (27, 2, "怒り"),  # 乱暴者
        (10, 4, "冷静"),  # 臆病：:35–37
        (22, 4, "冷静"),  # 無口
    ],
)
def test_com73_sp_transform(ctx, data, seikaku, shinkyou, word):
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    for i in range(10, 29):
        c.talent[i] = 0
    c.talent[seikaku] = 1
    c.cflag[1] = 1
    c.cflag[41] = 200
    v[0], v[4], v[5], v[12], v[1], v[11], v[22], v[23], v[8] = 2, 350, 7, KIZETU, 3, 3, 50, 10, 11
    st.tflag[1] = 0
    st.tflag[99] = 2
    st.rng = FixedRng([])  # RAND なし
    assert run_gen(commands.run_com(ctx, 73)) == 1  # :61
    assert c.cflag[1] == 2  # :12
    assert (v[5], v[4]) == (350, 0)  # :13–14
    assert v[12] == 0  # :20
    assert v[1] == shinkyou and v[11] == 0  # :31–46
    assert v[23] == 50  # :49–50 CFLAG:41 != 0
    assert st.tflag[1] == 1 and st.tflag[99] == 5 and v[8] == 1  # :53、:56、:59
    name = print_transcallname(st, 1)
    t = texts(ctx.out)
    assert f"{name}の状態異常が治った！" in t
    assert f"{name}は {word}状態 になった" in t


def test_com73_no_abnormal_no_outer(ctx):
    """:17 TCVARn:12 == 0 なら文なし、:49 CFLAG:41 == 0 ならアウターは回復しない。"""
    st = ctx.state
    c = st.charas[1]
    v = c.tcvarn
    c.cflag[1] = 1
    c.cflag[41] = 0
    v[0], v[4], v[12], v[22], v[23] = 2, 200, 0, 50, 10
    st.rng = FixedRng([])
    assert run_gen(commands.run_com(ctx, 73)) == 1
    assert v[23] == 10
    assert not any("状態異常が治った" in x for x in texts(ctx.out))


def test_com73_catalog_message(data):
    """MESSAGE_BATTLE_CHARA_SP_TRANSFORMCALL（地の文/MESSAGE_BATTLE.ERB:1020–1039）を catalog で実行：
    CFLAG:1 == 1 の時点で呼ばれるので「再び」、:1031 CFLAG:1 == 1 && CFLAG:41 != 0 → 傷一つない衣装。"""
    from eragvt.narration.service import CatalogNarrationService

    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    svc = CatalogNarrationService(Path(default_csv_dir()).parent / "ERB", data)
    cctx = Ctx(s, data, TextOutput(), svc)
    c = s.charas[1]
    c.cflag[1] = 1
    c.cflag[41] = 200
    c.tcvarn[0], c.tcvarn[4] = 2, 300
    assert run_gen(commands.run_com(cctx, 73)) == 1
    name = print_transcallname(s, 1)
    t = texts(cctx.out)
    assert f"力を開放した{name}の周囲に、再び光が集う…！" in t
    assert f"輝きが散り、その下から傷一つない衣装を纏った{name}が姿を現した！" in t
    assert not any("〈地の文：" in x for x in t)


# --- COMF70.ERB@COM70 ＳＰバースト ---------------------------------------------------------------


def _setup_burst(ctx, data):
    st = ctx.state
    c = st.charas[1]
    b = lambda n: I(data, "BASE", n)  # noqa: E731
    c.maxbase[b("体力")], c.maxbase[b("気力")], c.maxbase[b("性耐性")] = 3000, 2000, 200
    c.maxbase[b("防御")], c.maxbase[b("攻撃")] = 200, 300
    c.base[b("体力")], c.base[b("気力")], c.base[b("性耐性")] = 1500, 1000, 100
    c.ex[99] = 10  # EX:行動ポイント
    c.cflag[1] = 1
    c.cflag[99] = 0
    v = c.tcvarn
    v[0], v[4], v[5], v[6] = 0, 400, 0, 30
    st.temp.prevcom = 0
    st.tflag[99] = 0
    return c, v


@pytest.mark.parametrize(
    "setup, expected",
    [
        # :30 MAX(3000*2+100*3=6300, 480) * POWER(200,2)=40000 * (100+20) / 4800000 = 6300、
        # :39 PERCENT(1500+1000+4000, 3000+2000+8000) = 50 → 6300*75/100 = 4725
        ({}, 4725),
        ({"prevcom": 45}, 5433),  # :33 6300*115/100 = 7245 → 7245*75/100 = 5433
        ({"cflag1": 2}, 6600),  # :30 + 2500 → 8800*75/100
        ({"tr": 0}, 4016),  # :41 4725*85/100
        ({"mob": True}, 9450),  # :36 雑魚 ×2 → 12600*75/100
        ({"v4": 200}, 500),  # POWER(0,2) = 0 → :44 LIMIT 下限 500
    ],
)
def test_sp_burst_damage(ctx, data, setup, expected):
    st = ctx.state
    c, v = _setup_burst(ctx, data)
    st.temp.prevcom = setup.get("prevcom", 0)
    c.cflag[1] = setup.get("cflag1", 1)
    c.talent[I(data, "TALENT", "変身能力")] = setup.get("tr", 1)
    v[4] = setup.get("v4", 400)
    if setup.get("mob"):
        st.flag[10] = 2
    assert commands.sp_burst_damage(ctx) == expected


def test_com70_sp_burst(ctx, data):
    st = ctx.state
    c, v = _setup_burst(ctx, data)
    st.tflag[4] = 3
    st.tflag[1] = 0
    st.rng = FixedRng([])
    assert run_gen(commands.run_com(ctx, 70)) == 1  # :76
    assert v[0] == 2 and st.tflag[4] == 0  # :16–17
    assert v[6] == 30 - 500  # :20
    assert st.flag[13] == 100000 - 4725  # :46
    assert (c.base[0], c.base[1]) == (1500 - 375, 1000 - 250)  # :56–59
    assert st.tflag[99] == 2 + 200 * 10 // 400  # :65 = 7
    assert c.ex[99] == 10 // 2 + 1  # :68–69
    assert st.tflag[1] == 1 and v[8] == 1  # :72、:74
    t = texts(ctx.out)
    assert "SPバースト" in t
    assert any(x.endswith("に4725のダメージを与えた！") for x in t)
    assert "体力を375、気力を250消費した！" in t


def test_com70_fatigue_limit(ctx, data):
    """:9–14 CFLAG:99 >= 100 なら RETURN 0（状態は変わらない）。"""
    st = ctx.state
    c, v = _setup_burst(ctx, data)
    c.cflag[99] = 100
    st.rng = FixedRng([])
    assert run_gen(commands.run_com(ctx, 70)) == 0
    assert v[0] == 0 and v[6] == 30 and st.flag[13] == 100000
    assert "ＳＰバーストは使えない…！" in texts(ctx.out)


# --- COMF74.ERB@COM74 ＳＰフルバースト -----------------------------------------------------------


def test_com74_sp_full_burst(ctx, data):
    st = ctx.state
    c, v = _setup_burst(ctx, data)
    c.cflag[1] = 2
    v[0], v[3], v[5] = 2, 3, 1000
    st.temp.battle_situation = "撤退不可,"
    st.tflag[99] = 4
    st.rng = FixedRng([1])  # :62 RAND:2
    assert run_gen(commands.run_com(ctx, 74)) == 1  # :85
    # :32 MAX(3000 + 3000, 800) * 120 * 6000 / 500000 = 8640、
    # :41 PERCENT(1500+1000+1000, 3000+2000+2000) = 50 → 8640*250/200 = 10800
    assert st.flag[13] == 100000 - 10800
    assert v[6] == -500 and v[3] == 0 and v[0] == 2  # :20–22、:16
    assert st.tflag[99] == 4 + 15 + 1  # :62 MIN(2000*120/10000=24, 15) + RAND:2
    assert (c.base[0], c.base[1]) == (1000, 667)  # :66–69 1500/3=500、1000/3=333
    # :76 ADDBATTLESITUATION は '= で上書き（既存の「撤退不可」は消える）
    assert st.temp.battle_situation == "EX不可,"
    assert get_battle_situation(st, "EX不可") == 1 and get_battle_situation(st, "撤退不可") == 0
    assert "体力を500、気力を333消費した！" in texts(ctx.out)


def test_com74_finishing_blow(ctx, data):
    """:58–59 トドメなら TFLAG:99 = 0、RAND なし、反動なし。"""
    st = ctx.state
    c, v = _setup_burst(ctx, data)
    c.cflag[1] = 2
    v[0], v[5] = 2, 1000
    st.flag[13] = 10800
    st.tflag[99] = 9
    st.rng = FixedRng([])
    assert run_gen(commands.run_com(ctx, 74)) == 1
    assert st.flag[13] == 0 and st.tflag[99] == 0
    assert (c.base[0], c.base[1]) == (1500, 1000)


# --- COMMON_BATTLE_HANTEI.ERB のバースト補正 -------------------------------------------------------


@pytest.mark.parametrize(
    "style, l5, cflag99, expected",
    [
        ("装甲", 60, 0, 80),  # :370 60*125/100+5
        ("重撃", 60, 0, 49),  # :372 60*90/100-5
        ("広範", 13, 0, 100),  # :374
        ("全力", 60, 7, 63),  # :376 60+10-7
        ("使役", 61, 0, 49),  # :378 61*90/100=54 → 49
        ("通常", 61, 0, 81),  # :380 61*125/100=76 → 81
        ("連続", 60, 0, 60),  # 該当 CASE なし
        ("撹乱", 60, 0, 60),
        ("知略", 60, 0, 60),
        ("設置", 60, 0, 60),
        ("反撃", 60, 0, 60),
    ],
)
def test_burst_hit_table(ctx, style, l5, cflag99, expected):
    set_style(ctx, style)
    ctx.state.charas[1].cflag[99] = cflag99
    assert hantei._burst_hit(ctx, l5) == expected


@pytest.mark.parametrize("style", ["装甲", "重撃", "全力", "連続"])
def test_act_hantei_burst_hit(ctx, style):
    """ACT_HANTEI_CHARA_TO_TENTACLE:367–382 → :405 下限 0 → :409 RAND:100 < LOCAL:5。RESULT:1 が補正後の値。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, style)
    c.cflag[1] = 1
    st.rng = FixedRng([99])
    _, base = hantei.act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_MIDDLE")
    c.tcvarn.set_bit(217, 0, True)
    st.rng = FixedRng([99])
    _, burst = hantei.act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_MIDDLE")
    expected = {
        "装甲": div(base * 125, 100) + 5,
        "重撃": div(base * 90, 100) - 5,
        "全力": base + 10 - c.cflag[99],
        "連続": base,
    }[style]
    assert burst == max(expected, 0)


@pytest.mark.parametrize("burst, expected", [(False, 1), (True, 0)])
def test_guard_burst_zenryoku(ctx, burst, expected):
    """ACT_HANTEI_CHARA_TO_TENTACLE_GUARD:545–549 [全力]バーストはカス当たり率 0 → RAND:100 < 0 は偽。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, "全力")
    c.cflag[1] = 1
    c.tcvarn.set_bit(217, 0, burst)
    st.rng = FixedRng([0])
    assert hantei.act_hantei_chara_to_tentacle_guard(ctx, "ATTACK_RANGE_MIDDLE") == expected


@pytest.mark.parametrize("style, burst, expected", [("広範", True, 0), ("全力", True, 0), ("広範", False, 1), ("重撃", True, 1)])
def test_avoid_burst(ctx, style, burst, expected):
    """ACT_HANTEI_TENTACLE_TO_CHARA:1006–1013 [広範]・[全力]バーストは回避率 0（RAND:100 < 0 は偽 → 被弾、
    絶対回避 FEAT は無い）。それ以外は RAND 0 で回避成功。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, style)
    c.cflag[1] = 1
    c.tcvarn[2] = 0
    c.tcvarn.set_bit(217, 0, burst)
    st.tflag[11] = 7  # 全距離に攻撃
    st.rng = ZeroRng()
    assert hantei.act_hantei_tentacle_to_chara(ctx, "AVOID_KOUGEKI") == expected


@pytest.mark.parametrize(
    "style, mul",
    [("連続", 40), ("撹乱", 110), ("重撃", 150), ("全力", 150), ("使役", 300), ("通常", 110), ("装甲", 100), ("広範", 100)],
)
@pytest.mark.parametrize("fullburst", [0, 1])
def test_damage_burst(ctx, data, style, mul, fullburst):
    """DAMAGE:1461–1479 与ダメージ修正（:1477 フルバーストは ×125/100）。後続の補正が恒等になる条件
    （TFLAG:31 = TFLAG:33 = 0、CFLAG:99 = 0、:1520 付近の RAND 50 → ×1.00）で比較する。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, style)
    c.cflag[1] = 1
    c.cflag[99] = 0
    c.talent[I(data, "TALENT", "フルバースト")] = fullburst
    st.tflag[31] = st.tflag[33] = 0
    st.rng = FixedRng([50])
    base = hantei.damage(ctx, "ATTACK_RANGE_MIDDLE")
    c.tcvarn.set_bit(217, 0, True)
    st.rng = FixedRng([50])
    expected = div(base * mul, 100)
    if fullburst:
        expected = div(expected * 125, 100)
    assert hantei.damage(ctx, "ATTACK_RANGE_MIDDLE") == expected


@pytest.mark.parametrize("style, mul", [("全力", 125), ("重撃", 100)])
def test_damage_burst_chara(ctx, style, mul):
    """DAMAGE:1482–1487 被ダメージ修正：[全力]バーストのみ ×125/100（フルバースト FEAT は関係しない）。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, style)
    c.cflag[1] = 1
    c.tcvarn[2] = 0
    st.tflag[32] = 0
    st.rng = FixedRng([50])
    base = hantei.damage(ctx, "CHARA")
    c.tcvarn.set_bit(217, 0, True)
    st.rng = FixedRng([50])
    assert hantei.damage(ctx, "CHARA") == div(base * mul, 100)


def test_fstyle_attack_hangeki_burst(ctx, data):
    """FIGHT_STYLE.ERB@FSTYLE_ATTACK:102–105 [反撃]バーストは 攻撃*0.35 + 防御*0.25。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, "反撃")
    c.cflag[1] = 1
    c.talent[I(data, "TALENT", "小柄")] = c.talent[I(data, "TALENT", "長身")] = 0  # :67–74 の補正を外す
    c.tcvarn.set_bit(217, 0, True)
    l10 = div(c.maxbase[10] * cloth_battle_hosei(ctx, "KOUGEKI", 1), 100)
    l11 = div(c.maxbase[11] * cloth_battle_hosei(ctx, "BOUGYO", 1), 100)
    assert hantei.fstyle_attack(ctx, 1, 2) == div(l10 * 35, 100) + div(l11 * 25, 100)


# --- COM_ATTACK_COMMON.ERB のバースト分岐 ---------------------------------------------------------


def _attack(ctx, style: str):
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, style)
    c.cflag[1] = 1
    c.cflag[99] = 0
    c.tcvarn.set_bit(217, 0, True)
    c.tcvarn[2] = 0
    st.tflag[30] = st.tflag[31] = st.tflag[32] = st.tflag[33] = 0
    st.tflag[99] = 0
    st.tflag[1] = 0
    st.flag[17] = 0
    st.rng = ZeroRng()  # 命中・クリティカル（RAND:100 < 5+補正）・DAMAGE の RAND（0 → ×1.08）
    return commands.com_attack_common(ctx)


def test_attack_burst_normal_critical(ctx):
    """通常：:212 クリティカル → :215–216 倍率 15+5 = 20、:235 LOCAL:1 = DAMAGE*20/10、:383 反動 +1、
    COMBO_ATTACK.ERB:152–193 の表示。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, "通常")
    c.cflag[1] = 1
    c.cflag[99] = 0
    c.tcvarn.set_bit(217, 0, True)
    st.tflag[31] = 1  # :174 で 1 になった時点の DAMAGE
    st.tflag[33] = 0
    st.rng = ZeroRng()
    dmg = hantei.damage(ctx, "ATTACK_RANGE_MIDDLE")
    assert _attack(ctx, "通常") == 1
    assert st.flag[13] == 100000 - div(dmg * 20, 10)
    assert st.tflag[99] == 1
    t = "\n".join(texts(ctx.out))
    assert "＋BURST STRIKE" in t and "バースト攻撃：通常" in t and "与ダメージアップ＋直撃率アップ" in t
    assert "CRITICAL HIT!" in t


def test_attack_burst_renzoku_six_hits(ctx):
    """:15–19 [連続]バースト ATTACK_NUM = 1 + 4 → 6 回攻撃、:319–320 反動 +2。"""
    st = ctx.state
    _attack(ctx, "連続")
    assert sum(1 for x in texts(ctx.out) if x.endswith("のダメージを与えた！")) == 6
    assert st.tflag[99] == 2


def test_attack_burst_shieki_no_extra(ctx):
    """:21–22 [使役]はバースト時に追撃なし（1 回）、:335–336 反動 +3。"""
    st = ctx.state
    _attack(ctx, "使役")
    assert sum(1 for x in texts(ctx.out) if x.endswith("のダメージを与えた！")) == 1
    assert st.tflag[99] == 3


def test_attack_burst_soukou_autoguard(ctx):
    """:321–322 反動 +2、:393–396 オートガード。"""
    st = ctx.state
    _attack(ctx, "装甲")
    assert st.charas[1].tcvarn[2] == P_GUARD and st.tflag[99] == 2
    assert f"{print_transcallname(st, 1)}は防御態勢になった！" in texts(ctx.out)


def test_attack_burst_chiryaku_mikiri(ctx):
    """:331–332 反動 +1、:398–401 見切り（TFLAG:25 = 1）。"""
    st = ctx.state
    st.tflag[25] = 0
    _attack(ctx, "知略")
    assert st.tflag[25] == 1 and st.tflag[99] == 1


def test_attack_burst_secchi_yudan(ctx):
    """直撃時 :279–284 [設置] 300 + バースト 300 → :295 FLAG:17 += 600、:333–334 反動 +1。"""
    st = ctx.state
    _attack(ctx, "設置")
    assert st.flag[17] == 600 and st.tflag[99] == 1
    assert any(x.endswith("の油断度が少し上昇した……（＋６００）") for x in texts(ctx.out))


def test_attack_burst_kakuran_flinch(ctx):
    """:298–303 [撹乱]バースト：クリティカル（HIT_FLAG 2）なら RAND なしで怯み（TFLAG:1 = 1）。"""
    st = ctx.state
    _attack(ctx, "撹乱")
    assert st.tflag[1] == 1 and st.tflag[99] == 2
    assert "うまく相手の体勢を崩した！" in texts(ctx.out)


def test_attack_burst_hotstart_fullburst(ctx, data):
    """:387–390 FEAT による反動増加（通常 1 + 1 + 1）。"""
    c = ctx.state.charas[1]
    c.talent[I(data, "TALENT", "ホットスタート")] = 1
    c.talent[I(data, "TALENT", "フルバースト")] = 1
    _attack(ctx, "通常")
    assert ctx.state.tflag[99] == 3


def test_attack_burst_hangeki_charge(ctx):
    """:240–241 [反撃]バースト：直撃の最終ダメージに TCVARn:205 を加算、:337–341 反動 +3
    （TCVARn:205 <= TCVARn:206 なので過剰蓄積なし）。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, "反撃")
    c.cflag[1] = 1
    c.cflag[99] = 0
    c.tcvarn.set_bit(217, 0, True)
    c.tcvarn[205], c.tcvarn[206] = 400, 1000
    st.tflag[31] = 1
    st.tflag[33] = 0
    st.rng = ZeroRng()
    dmg = hantei.damage(ctx, "ATTACK_RANGE_MIDDLE")
    _attack(ctx, "反撃")
    assert st.flag[13] == 100000 - (div(dmg * 20, 10) + 400)
    assert st.tflag[99] == 3 and c.tcvarn[205] == 400


def test_attack_burst_hangeki_overcharge(ctx):
    """:344–379 過剰蓄積：PERCENT_CAL(205, 206) = 150 → 上限 70、MAXBASE:体力の 70% を受ける、
    :375 FOR 70→5 刻み 14 回 × 3 を加算、TCVARn:205 = 0。"""
    st = ctx.state
    c = st.charas[1]
    c.tcvarn[205], c.tcvarn[206] = 1500, 1000
    c.base[0] = c.maxbase[0]
    _attack(ctx, "反撃")
    l2 = div(c.maxbase[0] * 70, 100)
    assert c.base[0] == c.maxbase[0] - l2
    assert st.tflag[99] == 3 + 14 * 3
    assert c.tcvarn[205] == 0
    assert f"{l2}ダメージを受けた！" in texts(ctx.out)


# --- ＳＰ変身中の補正分岐（既存移植の確認）---------------------------------------------------------


def test_sp_correction_trans(ctx, data):
    """COMMON_BATTLE_FUNC.ERB@CORRECTION_TRANS:43–48：SP 変身中は CFLAG:11（100 未満は 100）倍。"""
    c = ctx.state.charas[1]
    c.cflag[1] = 2
    c.cflag[11] = 80
    assert correction_trans(ctx, 1000) == 1000
    c.cflag[11] = 150
    assert correction_trans(ctx, 1000) == 1500
    c.cflag[1] = 1
    assert correction_trans(ctx, 1000) == 1000  # :44 変身中（CFLAG:1 == 1）は補正なし


def test_sp_breast_weight(ctx, data):
    """COMMON_BATTLE_HANTEI.ERB:608–613／:1209–1213：SP 変身中は胸の重量だけ MAXBASE。"""
    c = ctx.state.charas[1]
    c.base[48], c.maxbase[48], c.base[44] = 1, 9, 49
    c.cflag[1] = 1
    assert hantei.breast_weight_term(ctx, c, 1000) == div(1000 * 2, 50)
    c.cflag[1] = 2
    assert hantei.breast_weight_term(ctx, c, 1000) == div(1000 * 10, 50)


def test_sp_stamina_fixed(ctx, data):
    """ACT_HANTEI_CHARA_TO_TENTACLE:23–24：SP 変身中は消耗度 LOCAL:0 = 100（体力が減っていても成功値が同じ）。"""
    st = ctx.state
    c = st.charas[1]
    set_style(ctx, "通常")
    c.cflag[1] = 2
    st.rng = FixedRng([99])
    _, full = hantei.act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_MIDDLE")
    c.base[0], c.base[1] = 1, 1
    st.rng = FixedRng([99])
    _, low = hantei.act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_MIDDLE")
    assert low == full
    c.cflag[1] = 1
    st.rng = FixedRng([99])
    _, low1 = hantei.act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_MIDDLE")
    assert low1 < full


# --- 整合：出撃 → 変身 → ＳＰ変身 → 攻撃 → 撤退 → 変身解除 ----------------------------------------------


def _buttons(s: GameSession) -> list[int]:
    return [p.button for ln in s.screen()[-30:] for p in ln.parts if p.button is not None]


def test_e2e_sp_transform_then_release(data):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(12))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』
    s.state.flag[47] = s.state.flag[46]  # ENCOUNT.ERB:159 ボス遭遇条件
    s.input(101)
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)
    assert s.phase == Phase.TURN
    st = s.state
    c = st.charas[1]
    seen_sp = attacked_sp = False
    for _ in range(40):
        if s.phase != Phase.TURN:
            break
        v = c.tcvarn
        b = _buttons(s)
        if v[0] == 0:  # 拘束されたら手順をやり直さず撤退優先で抜ける
            x = next((n for n in (8, 40, 10, 11) if n in b), b[0])
        elif c.cflag[1] == 0 and 0 in b:
            x = 0
        elif c.cflag[1] == 1:
            v[4] = 300  # :770 ゲージ条件を満たす
            s.input(810)  # 特殊コマンドの頁（BATTLE_COM.ERB@USERCOM:810）
            assert 73 in _buttons(s)
            x = 73
        elif c.cflag[1] == 2 and not attacked_sp:
            x = 2 if 2 in b else 1
            attacked_sp = True
        elif c.cflag[1] == 2:
            x = 999
        elif b:
            x = b[0]
        else:
            x = 0
        s.input(x)
        if c.cflag[1] == 2:
            seen_sp = True
    assert seen_sp and attacked_sp
    # BATTLE_TRAIN_AFTER.ERB:206 等 `CALL TRANSFORM, 0` → 戦闘後は変身解除
    for _ in range(20):
        if s.phase == Phase.SHOP:
            break
        b = _buttons(s)
        s.input(b[0] if b else 0)
    assert s.phase == Phase.SHOP
    assert c.cflag[1] == 0


@pytest.mark.parametrize(
    "hp, ki, fatigue, expected_pct",
    [
        (3000, 2000, 0, 120),  # 100% → CASEELSE
        (1500, 2000, 0, 100),  # 3500/5000 = 70% → 40 TO 74
        (1000, 900, 0, 80),  # 38% → 0 TO 39
        (1000, 900, 1, 100),  # (1900+150)/5000 = 41%
    ],
)
def test_status_charge_limit(ctx, hp, ki, fatigue, expected_pct):
    """CHARA_STATUS.ERB@STATUS_PRINT_CHARGE:1480–1489：TCVARn:206 = MAXBASE:体力 × 限度(%) / 100。"""
    from eragvt.game.battle.train import status_charge_limit

    c = ctx.state.charas[1]
    c.maxbase[0], c.maxbase[1] = 3000, 2000
    c.base[0], c.base[1] = hp, ki
    c.cflag[99] = fatigue
    assert status_charge_limit(ctx) == 3000 * expected_pct // 100
    assert c.tcvarn[206] == 3000 * expected_pct // 100
