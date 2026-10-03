"""S28b：特別活動（ACTION_SEISAN・特別活動/）。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`、`特別活動/` = `ゲーム内_行動実行処理/特別活動/`；行號は註解）。
開局（特装戦隊）：[1] 紅葉（MAXBASE 体力 2787／気力 2454／性耐性 198、BASE:体力基礎 2006／気力基礎 1748、Lv1、MAXBASE:知性 159、
処女 1、変身能力 1、CFLAG:42 = 300）。FLAG:805 = 2（CONFIG_CHECK_OTHER_F(3) = 0 → AFTER_PILL は即 RETURN 0）。MONEY = 5000、DAY = 1。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import flashnews, seisan, shop
from eragvt.game.action import Ctx, Step, action_main
from eragvt.game.battle import ninsin as ninsin_mod
from eragvt.game.era import div
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.narration.hooks import SEISAN_HOOK_LINES
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    c = Ctx(s, data, TextOutput(), NullNarrationService())
    c.globals.mem.global_[51] = 2  # 特別活動の変身設定「常に変身しない」（ACTIONsub_TRANSFORMATION_SELECT.ERB:42–48）
    s.target = 1
    return c


@pytest.fixture
def ninsin_calls(monkeypatch):
    calls = []

    def fake(ctx, a0, a1, a2=0):
        calls.append((a0, a1, a2))
        return 0

    monkeypatch.setattr(ninsin_mod, "ninsin_hantei", fake)
    return calls


def texts(out: TextOutput) -> list[str]:
    return [line.text for line in out.lines]


def run(gen, inputs=()):
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            if not inputs:
                return "WAIT"
            gen.send(inputs.pop(0))
    except StopIteration as stop:
        return stop.value


def keigen(c, amount: int, base: int) -> int:
    """`汎用関数/コモン関数.ERB@SYOUHI_KEIGEN`:947–960。"""
    b = c.base[base + 50]
    th = 1000 if base in (0, 1) else 100
    if b > th:
        return max(amount - div(amount * (b - th), 2500), div(amount, 2))
    return amount


def E(data, n):
    return data.index_of("EXP", n)


def T(data, n):
    return data.index_of("TALENT", n)


def A(data, n):
    return data.index_of("ABL", n)


def J(data, n):
    return data.index_of("PALAM", n)


# --- CALC_SEISAN.ERB ------------------------------------------------------------------------


def test_calc_seisan_part_time_success(ctx):
    """CALC_SEISAN:23–137（アルバイト成功：係数 20,10,0,1000,10,200）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([3, 1, 2])  # :36 RANDOM(7)、:37 RANDOM(4)、（性耐性係数 0 → :38 なし）、:128 RANDOM(4)
    hp, mp, sei, money = c.base[0], c.base[1], c.base[2], st.money
    lb0 = keigen(c, div(2787 * (20 + 3), 100), 0)
    lb1 = keigen(c, div(2454 * (10 + 1), 100), 1)
    earn = div(100 * lb0, 1000) + 1 * 10 + 2 + 200
    assert seisan.calc_seisan(ctx, seisan.ARUBAITO, seisan.SEIKOU) == (lb0, earn)
    assert (c.base[0], c.base[1], c.base[2]) == (hp - lb0, mp - lb1, sei)
    assert st.money == money + earn
    assert (st.result[0], st.result[1]) == (lb0, earn)  # :137 RETURN CUSTOMER_NUM, EARN
    assert (st.temp.losebase[0], st.temp.losebase[1]) == (0, 0)  # :136 VARSET LOSEBASE


def test_calc_seisan_part_time_failure_uses_success_coef(ctx):
    """SEISAN_INIT.ERB:8：アルバイト「失敗」の係数は `特活報酬_アルバイト_成功`（`_失敗` 40,50,30,2000,5,100 は使われない）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0, 0, 0])  # 性耐性係数 0 なので RANDOM は 3 回
    lb0 = keigen(c, div(2787 * 20, 100), 0)
    assert seisan.calc_seisan(ctx, seisan.ARUBAITO, seisan.SHIPPAI) == (lb0, div(100 * lb0, 1000) + 10 + 200)
    assert c.base[2] == 198


def test_calc_seisan_toilet_order_and_exp(ctx, data):
    """CALC_SEISAN:80–85 公衆便所：客数 ×(6+RANDOM(3))/100 → CALC_SEISAN_SEXUAL_EXP（:198–226 の RANDOM 順）→ 稼ぎ 1+100*RANDOM(50)/100。"""
    st = ctx.state
    c = st.charas[1]
    seq = [6, 3, 2, 2] + [2, 2, 2, 1, 1, 1, 2, 2, 2, 2] + [37]
    st.rng = FixedRng(seq)
    lb0 = keigen(c, div(2787 * (7 + 6), 100), 0)
    lbs = div(198 * (7 + 2), 100)
    cust = div(lb0 * (6 + 2), 100)
    before = {n: c.exp[E(data, n)] for n in ("被姦経験", "Ｖ経験", "Ａ経験", "絶頂経験", "露出快楽経験", "自慰経験", "射精経験")}
    money = st.money
    r = seisan.calc_seisan(ctx, seisan.TOILET, seisan.BENKI_NIKU)
    assert r == (cust, 1 + div(100 * 37, 100))
    assert st.money == money + 38
    assert c.base[2] == 198 - lbs
    assert c.exp[E(data, "被姦経験")] - before["被姦経験"] == div(cust * (2 + 2), 100)
    assert c.exp[E(data, "Ｖ経験")] - before["Ｖ経験"] == div(cust * (1 + 2), 100)
    assert c.exp[E(data, "露出快楽経験")] - before["露出快楽経験"] == div(cust * (2 + 2), 100)
    assert c.exp[E(data, "射精経験")] == before["射精経験"]  # ISPENIS 偽


@pytest.mark.parametrize("charm, lv", [(0, 0), (29, 0), (30, 1), (99, 1), (100, 2), (149, 2), (150, 3), (250, 5),
                                       (499, 7), (500, 8), (10**9, 8)])
def test_idol_lv(ctx, data, charm, lv):
    """SEISAN_6_IDOL_ACTIVITY.ERB@IDOL_LV:196–204 ＋ SEISAN_IDOL.ERH:6（末尾 __INT_MAX__）。"""
    ctx.state.charas[1].exp[E(data, "魅了経験")] = charm
    assert seisan.idol_lv(ctx, 1) == lv


# --- ACTION_SEISAN.ERB --------------------------------------------------------------------


def _patch_acts(monkeypatch):
    called = []
    for name in ("part_time", "research", "idol_activity", "idol_live"):
        monkeypatch.setattr(seisan, name, lambda ctx, _n=name: called.append(_n))
    for name in ("pest_control", "prostitution", "porn_video", "toilet", "idol_prostitution"):
        def g(ctx, _n=name):
            called.append(_n)
            yield from ()
        monkeypatch.setattr(seisan, name, g)
    return called


def test_seisan_menu_and_invalid_input(ctx, monkeypatch):
    """:14–45 メニュー（欲望 0：援助交際等なし）、:148–150 実行不可の番号は再入力、:152 CFLAG:101、:187–191。"""
    called = _patch_acts(monkeypatch)
    st = ctx.state
    c = st.charas[1]
    c.cflag[100] = 104
    st.flag[799] = 0
    assert run(action_main(ctx), [3, 9, 0]) == Step.TURNEND
    t = texts(ctx.out)
    assert "[0]アルバイト　　　　[1]研究所助手　　　　[2]雑魚触手退治　　　" in t
    assert "[6]アイドル活動　　　" in t
    assert t.count("正しい値を入力してください") == 2
    assert called == ["part_time"]
    assert c.cflag[101] == 0


def test_seisan_menu_unlocks(ctx, data, monkeypatch):
    """:23–42：欲望・露出癖・マゾっ気・魅了経験による解放、出産経験で「研究所で検査協力」。"""
    _patch_acts(monkeypatch)
    c = ctx.state.charas[1]
    c.abl[A(data, "欲望")] = 3
    c.abl[A(data, "露出癖")] = 2
    c.abl[A(data, "マゾっ気")] = 1
    c.exp[E(data, "魅了経験")] = 100
    c.exp[E(data, "出産経験")] = 1
    assert run(seisan.seisan(ctx), [7]) is None
    t = texts(ctx.out)
    assert "[0]アルバイト　　　　[1]研究所で検査協力　[2]雑魚触手退治　　　" in t
    assert "[3]援助交際　　　　　[4]AV出演　　　　　　" in t  # 公衆便所は 3+1 < 5
    assert "[6]アイドル活動　　　[7]枕営業　　　　　　" in t
    assert c.cflag[101] == 7


@pytest.mark.parametrize("day, inp, act", [(6, 6, 8), (7, 8, 8), (5, 6, 6)])
def test_seisan_weekend_live(ctx, data, monkeypatch, day, inp, act):
    """:33–39 デビュー後の週末は★ライブ公演、:138–140 入力 6 は 8 に読み替え（DAY % 7 が 0 か 6）。"""
    called = _patch_acts(monkeypatch)
    st = ctx.state
    st.day[0] = day
    st.charas[1].exp[E(data, "魅了経験")] = 100
    run(seisan.seisan(ctx), [inp])
    assert st.charas[1].cflag[101] == act
    assert called == ["idol_live" if act == 8 else "idol_activity"]
    assert any(x.startswith("[8]★ライブ公演　　　") for x in texts(ctx.out)) == (act == 8)


def test_seisan_live_not_weekend_rejected(ctx, data, monkeypatch):
    _patch_acts(monkeypatch)
    st = ctx.state
    st.day[0] = 5
    st.charas[1].exp[E(data, "魅了経験")] = 100
    assert run(seisan.seisan(ctx), [8]) == "WAIT"  # :148 `(… DAY % 7 != 0 && != 6) && RESULT == 8`
    assert "正しい値を入力してください" in texts(ctx.out)


def test_seisan_schedule(ctx, monkeypatch):
    """:49–64 CFLAG:111 > 0：RES_SCHEDULE の項目番号 - 1（2 → 研究）。入力なしで実行。"""
    called = _patch_acts(monkeypatch)
    c = ctx.state.charas[1]
    c.cflag[111] = 2
    assert run(seisan.seisan(ctx)) is None
    t = texts(ctx.out)
    assert "　" in t  # :57 PRINTL
    assert "スケジュール：研究所助手　　　　" in t
    assert called == ["research"] and c.cflag[101] == 1


def test_seisan_schedule_unavailable(ctx, monkeypatch):
    """:70–78 援助交際（欲望 0）→（実行不能）→ GOTO INPUT_LOOP で手入力。"""
    called = _patch_acts(monkeypatch)
    c = ctx.state.charas[1]
    c.cflag[111] = 4
    assert run(seisan.seisan(ctx), [2]) is None
    t = texts(ctx.out)
    assert "スケジュール：援助交際（実行不能）" in t
    assert "手動で行動を選択してください" in t
    assert called[-1] == "pest_control"


# --- SEISAN_0_PART_TIME.ERB --------------------------------------------------------------------


def test_part_time_shinbun_normal(ctx):
    """:29–33 RANDOM(4)=0 → 新聞配達、SHINBUN:133／:144／:150 すべて外れ → NORMAL、:97 PROCESSED（人数加算値 10）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0, 1, 1, 1, 0, 0, 0, 3])
    lb0 = keigen(c, div(2787 * 20, 100), 0)
    pay = div(100 * lb0, 1000) + 10 + 0 + 200
    seisan.part_time(ctx)
    processed = div(lb0, 100) + 3 % (div(lb0, 500) + 6) + 10
    assert f"紅葉は{processed}軒に新聞配達し、{pay}＄の報酬を得ました。" in texts(ctx.out)
    assert st.result[0] == lb0  # 直前の CALC_SEISAN の RETURN
    assert st.flag[853] == 0


def test_part_time_hero_korobi(ctx, data):
    """HERO:198–204 転んで失敗（恥情 +25）、:52–57 「夢と性の芽生えを与え」（ISHOLE）、:63 人数加算値 = Lv、:66 魅了経験（CALC_CHARM_FEAT_OTHER）、
    :69–72 人気度、CALC はアルバイト失敗（＝成功の係数）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([1, 0, 0, 0, 5, 99, 0, 0, 0, 2])
    shame = c.juel[J(data, "恥情")]
    lb0 = keigen(c, div(2787 * 20, 100), 0)
    pay = div(100 * lb0, 1000) + 10 + 0 + 200
    seisan.part_time(ctx)
    processed = div(lb0, 250) + 2 % (div(lb0, 250) + 6) + 1
    t = texts(ctx.out)
    assert f"紅葉は{processed}人のちびっこに夢と性の芽生えを与え、{pay}＄の報酬を得ました。" in t
    assert "魅了経験が2上がった" in t and "人気度が1上がった" in t
    assert c.exp[E(data, "魅了経験")] == 2 and st.flag[853] == 1
    assert c.juel[J(data, "恥情")] == shame + 25


def test_part_time_acmecycle(ctx, data):
    """SHINBUN:133–141：処女なので RANDOM(2) も必要、:135 RANDOM(5)=0 で CFLAG:42 = 400（触手拘束具）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0, 0, 0, 0, 0, 0, 0, 0])
    seisan.part_time(ctx)
    assert c.cflag[42] == 400
    assert c.juel[J(data, "習得")] >= 75


# --- SEISAN_1_RESEARCH.ERB -------------------------------------------------------------------


def test_research_assistant(ctx, data):
    """:49–69 助手：表示額は RESULT:1 × MAXBASE:知性 / 100（MONEY は CALC_SEISAN の稼ぎ）、:63 知性 +2。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0, 0, 1, 0])
    lb0 = keigen(c, div(2787 * 10, 100), 0)
    earn = div(100 * lb0, 8000) + 8 + 1 + 150
    money, chisei = st.money, c.base[13]
    seisan.research(ctx)
    assert st.money == money + earn
    assert f"紅葉はアルバイトの報酬として{div(earn * 159, 100)}＄を得ました" in texts(ctx.out)
    assert c.base[13] == chisei + 2 and "知性の基礎値が2上がった" in texts(ctx.out)


def test_research_uterus_shaves(ctx, data):
    """:12–29 妊娠中（TALENT:妊娠 1）→ 子宮検査、パイパン 0 なら 1 に。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "妊娠")] = 1
    st.rng = FixedRng([0, 0, 0, 0])
    seisan.research(ctx)
    assert c.talent[T(data, "パイパン")] == 1
    assert c.exp[E(data, "露出快楽経験")] == 1
    assert "研究所で検査協力（子宮）" in texts(ctx.out)


# --- SEISAN_2_PEST_CONTROL.ERB ---------------------------------------------------------------


def test_pest_control_toriko_defeat(ctx, data, ninsin_calls):
    """:17–71 触手の虜：処女喪失（CFLAG:206 = 2）、退治失敗（稼ぎ 0）、:70 NINSIN_HANTEI(RESULT:0/10+2 = 2, 50, 200)
    （RESULT:0 は AFTER_PILL の 0）。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "触手の虜")] = 1
    c.base[31] = c.base[32] = 0  # Ｖ／Ａ結界耐久力
    st.rng = FixedRng([0] * 30)
    money = st.money
    lb0 = keigen(c, div(2787 * 80, 100), 0)
    tent = div(lb0 * 50, 100)  # :63
    battle = c.exp[E(data, "戦闘経験")]
    run(seisan.pest_control(ctx))
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 2
    assert st.money == money
    assert f"仲間が助けに来るまでの間、紅葉は{tent}匹の触手に陵辱されてしまった。" in texts(ctx.out)
    assert c.exp[E(data, "戦闘経験")] == battle + div(tent * 10, 100)
    assert c.juel[J(data, "欲情")] >= 200
    assert ninsin_calls == [(2, 50, 200)]


def test_pest_control_normal(ctx, data):
    """:74–82 普通は楽勝：戦闘経験 += RESULT:0 × (1 + RANDOM(5)) / 100。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0, 0, 0, 0, 4])
    lb0 = keigen(c, div(2787 * 30, 100), 0)
    earn = div(100 * lb0, 800) + 5 + 0 + 100
    run(seisan.pest_control(ctx))
    assert f"紅葉は{lb0}匹の触手を駆除し、{earn}＄の報酬を得ました。" in texts(ctx.out)
    assert c.exp[E(data, "戦闘経験")] == div(lb0 * 5, 100)


# --- SEISAN_3_PROSTITUTION.ERB --------------------------------------------------------------


def test_prostitution_normal_creampie_ok(ctx, data, ninsin_calls):
    """NORMAL:140–298：非処女 → 生ハメのお願い → [3] 中出しＯＫ（RETURN 2）→ 同意中出し +500、NINSIN_HANTEI(3, 800, -1)。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "処女")] = -1
    c.abl[A(data, "欲望")] = 1
    st.rng = FixedRng([1] + [0] * 4 + [0] * 10 + [0] + [99, 99, 99])
    money = st.money
    assert run(seisan.prostitution(ctx), [5, 3]) is None  # 5 は想定外（:313–334 黙って再入力）
    lb0 = keigen(c, div(2787 * 3, 100), 0)
    cust = div(lb0 * 7, 100)
    earn = div(100 * cust, 33) + 0 + 0 + 250
    t = texts(ctx.out)
    assert "[1]やんわりと断る（交渉失敗率15％）" in t
    assert "中出ししても良いと伝えると、男の目が興奮の色に変わった…" in t
    assert f"紅葉は街で声をかけてきた男に{earn + 500}＄のお小遣いをもらった" in t
    assert st.money == money + earn + 500
    assert ninsin_calls == [(3, 800, -1)]
    assert c.exp[E(data, "Ｖ経験")] >= 3


def test_prostitution_virgin_no_request(ctx, data, ninsin_calls):
    """:153–173 処女は生挿入なし（NAMAHAME 0：入力なし）で処女喪失（CFLAG:206 = 8、TALENT:処女 *= -1）、
    :260–287 コンドームに射精（+0）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([1] + [0] * 15 + [1] + [99, 99, 99])
    assert run(seisan.prostitution(ctx)) is None
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 8
    assert ninsin_calls == []


# --- SEISAN_4_PORN_VIDEO.ERB ------------------------------------------------------------------


def test_porn_video_maid(ctx, data):
    """:17–19 先に CALC、:40–42 メイドもの（CFLAG:282 = 11）、:96–113 [9] で CFLAG:281 = 1、:122 SAVESTR:(20+TARGET)、:123 CFLAG:285。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([0] * 4 + [0] + [0] * 10 + [0] + [0] + [0])
    assert run(seisan.porn_video(ctx), [9]) is None
    title = "『おしおきされてイキまくるドジっ娘メイド 赤羽 紅葉』"
    assert c.cflag[282] == 11 and c.cflag[281] == 1 and c.cflag[285] == 1
    assert st.savestr[21] == title
    assert any(x.startswith(title + "は") and x.endswith("＄の報酬を得ました。") for x in texts(ctx.out))
    # 2 回目は確認なし（:104 CFLAG:281 == 1 → 9）
    st.rng = FixedRng([0] * 30)
    assert run(seisan.porn_video(ctx)) is None
    assert "……ちょっとだけ見てみよう。" in texts(ctx.out)


def test_porn_video_title_henshin(ctx, data):
    """:44–46 サド系：`\\@TALENT:変身能力 == 1?#すぷらったー☆\\@` は変身能力 1 なら空（原作どおり）。"""
    st = ctx.state
    st.rng = FixedRng([0] * 16 + [1, 0] + [99])
    assert run(seisan.porn_video(ctx), [1]) is None
    assert st.savestr[21] == "『サディスティック魔法少女 紅葉』"
    assert st.charas[1].cflag[281] == 0


# --- SEISAN_5_TOILET.ERB ----------------------------------------------------------------------


def test_toilet_back_alley_reads_result_after_pill(ctx, data, ninsin_calls):
    """:34–57 路地裏放置：処女喪失（CFLAG:206 = 9・異常経験 +1）、:56–57 NINSIN_HANTEI((RESULT:0 = AFTER_PILL の 0)/2+2, 100, -1)、
    :79–91 の経験も RESULT:0（NINSIN_HANTEI の戻り値 0）で計算（原作どおり）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([1, 0] + [0] * 4 + [0] * 10 + [0] + [0] + [99])
    v0, a0 = c.exp[E(data, "Ｖ経験")], c.exp[E(data, "Ａ経験")]
    run(seisan.toilet(ctx))
    lb0 = keigen(c, div(2787 * 7, 100), 0)
    cust = div(lb0 * 6, 100)
    assert c.cflag[206] == 9 and c.talent[T(data, "処女")] == -1 and c.exp[E(data, "異常経験")] == 1
    assert ninsin_calls == [(2, 100, -1)]
    assert f"肉便器紅葉は{div(cust, 10) + 1}人に使われたが、使用料は{1}＄しか入っていなかった…" in texts(ctx.out)
    assert c.exp[E(data, "Ｖ経験")] - v0 == div(cust * 1, 100) + 2  # 性的経験（:209）＋ :222 の 0/2+2
    assert c.exp[E(data, "Ａ経験")] - a0 == div(cust * 1, 100) + 1
    assert c.cflag[285] == 1


def test_toilet_dog(ctx, data):
    """:59–74 野良犬：表示は「１＄たりとも得られなかった」だが、CALC_SEISAN:80–85 の公衆便所固有の稼ぎ（1 + 100×RANDOM(50)/100）は
    活動結果に関係なく MONEY に入る（IS_PROFITABLE は共通式を止めるだけ：:127–128。原作どおり）。"""
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "処女")] = -1
    st.rng = FixedRng([1, 1] + [0] * 4 + [0] * 10 + [10] + [2] + [99])
    money = st.money
    run(seisan.toilet(ctx))
    lb0 = keigen(c, div(2787 * 7, 100), 0)
    cust = div(lb0 * 6, 100)
    assert st.money == money + 1 + 10  # CALC_SEISAN:85（公衆便所の固有計算は結果に関係なく行われる）
    assert f"肉便器紅葉は{div(cust, 20) + 2 + 1}匹の野良犬に使われたが、当然使用料は１＄たりとも得られなかった…" in texts(ctx.out)


# --- SEISAN_6_IDOL_ACTIVITY.ERB -------------------------------------------------------------


def test_idol_budding(ctx, data):
    """:21–32 レベル 0・DAY < 14：SEISAN_IDOL_CHARMUP(30, 5, 5, 30)。CALC_CHARM_FEAT_IDOL:2–19（RANDOM(4) ≠ 0、平凡・美貌なし → 0）。"""
    st = ctx.state
    c = st.charas[1]
    st.rng = FixedRng([1, 2])
    seisan.idol_activity(ctx)
    assert c.exp[E(data, "魅了経験")] == 32
    assert "魅了経験が32上がった" in texts(ctx.out)
    assert st.result[0] == 0  # 直後の MESSAGE_SEISAN_IDOL_DEBUT（RETURN 0／終端）


def test_idol_budding_late_minimum(ctx, data):
    """:33–39 DAY ≥ 14：CHARMUP(25 + MIN(DAY, 28), 5, 5, 35)。"""
    st = ctx.state
    st.day[0] = 40
    st.rng = FixedRng([0, 4])  # RANDOM(4) == 0 → 0
    seisan.idol_activity(ctx)
    assert st.charas[1].exp[E(data, "魅了経験")] == 25 + 28 + 4


def test_idol_gravure_savestr(ctx, data, monkeypatch):
    """:83–108 グラビア撮影：写真集タイトル（REF）→ SAVESTR:(23+TARGET)、CHARMUP(4, 2, 4)。catalog なし → タイトル選択の fallback。"""
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "魅了経験")] = 100
    st.rng = FixedRng([0, 1] + [1, 0] + [0, 0, 0] + [0] + [0, 0] + [99, 99])
    seisan.idol_activity(ctx)
    assert st.savestr[24] == "『マジかるエン★ジェル 赤羽 紅葉』"
    assert c.exp[E(data, "魅了経験")] == 104


def test_idol_gravure_catalog_ref(ctx, data, svc):
    """catalog で MESSAGE_SEISAN_IDOL_GRAVURE_PHOTOSHOOT を実行し、`#DIMS REF BOOK_TITLE` の結果を受け取る。"""
    st = ctx.state
    st.charas[1].exp[E(data, "魅了経験")] = 100
    cctx = Ctx(st, data, TextOutput(), svc)
    st.rng = GameRng(3)
    for _ in range(40):
        st.savestr[24] = ""
        seisan.idol_activity(cctx)
        if st.savestr[24]:
            break
    assert re.fullmatch(r"『(ピュエアリーＫＩＳＳ 赤羽 紅葉|マジかるエン★ジェル 赤羽 紅葉|純情ＨＥＡＲＴ 赤羽 紅葉|"
                        r"赤羽 紅葉 ゆうわくビーチ|ガールズ＆スタイルズ 赤羽 紅葉)』", st.savestr[24])
    assert "〈地の文" not in "".join(texts(cctx.out))


# --- SEISAN_7／8 -------------------------------------------------------------------------------


def test_idol_prostitution_virgin_blowjob(ctx, data):
    """SEISAN_7:11–29 処女 → RANDOM(4) ≠ 0 でＰにフェラ：CFLAG:283 += 1、CHARMUP(8, 4, 4)、:234 CFLAG:285。"""
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "魅了経験")] = 100
    st.rng = FixedRng([1] + [0, 0] + [2] + [1, 0] + [0])  # CALC は RANDOM(7)・RANDOM(4) のみ（性耐性係数 0・稼ぎなし）
    run(seisan.idol_prostitution(ctx))
    assert c.cflag[283] == 1 and c.cflag[285] == 1
    assert c.exp[E(data, "フェラ経験")] == 3 + 2
    assert c.exp[E(data, "魅了経験")] == 108


def test_idol_live_static_charm(ctx, data):
    """SEISAN_8:9–100：成功で CHARM_BASE 等（静的）＝ 8,4,2、CFLAG:400 = 来場者、:96–97 魅了経験は最低 100。
    次の失敗では CHARM_BASE が前回のまま → 魅了経験が上がる（原作どおり）。"""
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "魅了経験")] = 100
    st.rng = FixedRng([1, 1] + [0, 0, 0] + [1, 0] + [99, 99, 99])
    seisan.idol_live(ctx)
    assert c.cflag[400] == keigen(c, div(2787 * 80, 100), 0) + 100 * 4  # CALC_SEISAN:114（ライブ観客係数 Lv2 = 4）
    assert c.exp[E(data, "魅了経験")] == 108
    st.rng = FixedRng([0] + [0, 0, 0, 0] + [0, 0] + [99, 99, 99])  # :29 RANDOM(2 + 108/20) == 0 → 失敗
    seisan.idol_live(ctx)
    assert c.exp[E(data, "魅了経験")] == 116


def test_idol_live_first_failure_no_charm(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.exp[E(data, "魅了経験")] = 100
    st.temp.locals.clear()
    st.rng = FixedRng([0] + [0, 0, 0, 0] + [99, 99, 99])
    seisan.idol_live(ctx)
    assert c.exp[E(data, "魅了経験")] == 100


# --- 地の文 catalog ----------------------------------------------------------------------------


def test_seisan_hook_table_matches_erb(svc):
    cat = svc.catalog
    for (func, line), (text, _) in SEISAN_HOOK_LINES.items():
        e = cat.index[func]
        assert dict(cat.lines_of(e.rel))[line].strip() == text, (func, line)
    names = [n for n in cat.index if n.startswith("MESSAGE_SEISAN_")]
    assert len(names) == 58
    for name in names + ["MESSAGE_CITIZEN_TRAIN_KANCHO", "MESSAGE_CITIZEN_TRAIN_PIG", "MESSAGE_CITIZEN_TRAIN_DOG", "IDOL_LV"]:
        assert cat.unsupported_reason(name) is None, name  # 表外の代入があれば unsupported になる


def test_catalog_idol_lv_varsize(ctx, data, svc):
    """IDOL_LV（catalog）：`VARSIZE("アイドルレベル条件")` = 9（初期値の個数：UserDefinedVariable.cs:287–288）、__INT_MAX__。"""
    from eragvt.narration.runtime import Env, Interp

    st = ctx.state
    for charm, lv in ((0, 0), (150, 3), (10**12, 8)):
        st.charas[1].exp[E(data, "魅了経験")] = charm
        it = Interp(svc.catalog, Env(st, data, TextOutput(), {}, {}, ctx))
        assert it.call("IDOL_LV", [1], as_method=True) == lv


def test_mainplay_hook_sets_flag900(ctx, data, svc):
    """MESSAGE_SEISAN_PROSTITUTION_MAINPLAY:127–145 の FLAG:900（hook）→ KOJO_ROOT が 0 に戻す。"""
    st = ctx.state
    cctx = Ctx(st, data, TextOutput(), svc)
    st.rng = GameRng(5)
    assert svc.run_function(cctx, "MESSAGE_SEISAN_PROSTITUTION_MAINPLAY", [1, 0, 1])
    assert st.flag[900] == 0
    assert "処女喪失" in texts(cctx.out)


# --- 整合：SHOP → 特別活動 → TURNEND → SHOP（ニュース） ----------------------------------------


def test_shop_seisan_turnend_news(data):
    with tempfile.TemporaryDirectory() as tmp:
        s = GameSession(data, Path(tmp), rng=GameRng(7), narration=NullNarrationService())
        s.input(0)
        s.input(1)  # 初期セット『特装戦隊』
        s.input(1)  # HEROINE_PRESET [1] 基本セット
        assert s.phase == Phase.SHOP
        st = s.state
        c = st.charas[1]
        c.abl[A(data, "欲望")] = 3
        c.abl[A(data, "露出癖")] = 2
        day = st.day[0]
        for i, p in {1: 104, 2: 103, 3: 103}.items():
            s.input(i)
            s.input(p)
        s.input(100)
        for v in (9, 1, 4, 10):  # 確認 [9]（SHOP.ERB の確認は CASE 9 のみ）→ 変身しない → [4]AV出演 → サンプルは見ない（次から確認しない）
            if s.phase == Phase.SHOP:
                break
            s.input(v)
        for _ in range(20):
            if s.phase == Phase.SHOP:
                break
            s.input(0)
        assert s.phase == Phase.SHOP
        st = s.state
        c = st.charas[1]
        assert (st.day[0], st.time) == (day, 1)  # EVENTSHOP の昼→夜
        assert c.cflag[101] == 4 and c.cflag[281] == 2
        assert st.savestr[21].startswith("『")
        assert any("【紅葉の行動：特別活動】" in ln.text for ln in s.out.lines)
        # SHOP_FLASHNEWS.ERB:529–547：SAVESTR:21〜25 の作品が新聞に出る
        st.rng = FixedRng([0] * 10)
        news = flashnews._random_news(st, data, 0, 0, 0)
        assert news.startswith(st.savestr[21])
