"""S28c1：自由行動（ACTION_PASTIME・自由行動中イベント）。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`、`自由/` = `ゲーム内_イベント発生/自由行動中イベント/`；行號は註解）。
開局（特装戦隊）：[1] 紅葉（MAXBASE 体力 2787／気力 2454／性耐性 198、学生 0、巨乳 0、処女 1、変身能力 1、CFLAG:40 = 100、CFLAG:42 = 300）。
FLAG:852 = 5000、DAY = 1、TIME = 0。GLOBAL:57 = 2（気晴らしの変身設定「常に変身しない」：ACTIONsub_TRANSFORMATION_SELECT.ERB:42–48）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import gather, pastime as pt, pastime_school as pts, shop
from eragvt.game.action import Ctx, Step, action_main
from eragvt.game.battle import ablup as ablup_mod
from eragvt.game.battle import ninsin as ninsin_mod
from eragvt.game.schedule import E18
from eragvt.game.session import GameSession, Phase
from eragvt.narration.hooks import PASTIME_HOOK_LINES
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.state.constants import ActionPlan
from eragvt.text import NullNarrationService, TextOutput
from eragvt.game.opening import PRESET_TOKUSOU, event_first

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
    c.globals.mem.global_[57] = 2
    s.target = 1
    return c


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


def T(data, n):
    return data.index_of("TALENT", n)


def E(data, n):
    return data.index_of("EXP", n)


def A(data, n):
    return data.index_of("ABL", n)


def B(data, n):
    return data.index_of("BASE", n)


_NANPA_TALENTS = ("学生", "巨乳", "小柄", "女体受容", "男の娘", "社交的", "母性的", "小悪魔", "目立ちたがり", "上品", "泣き虫", "清純派",
                  "変身時外見", "外見", "巻き込まれ体質", "人外の美貌", "小さな体躯", "嬲られ体質")


def _clear(ctx, names=_NANPA_TALENTS):
    c = ctx.state.target_chara
    for k in names:
        c.talent[T(ctx.data, k)] = 0


def _gen(record, name):
    def g(ctx, *a, **k):
        record.append((name,) + a)
        return 0
        yield  # pragma: no cover

    return g


# --- catalog（本文中心の関数）と hook -----------------------------------------------------------


def test_pastime_hook_table_matches_erb(svc):
    cat = svc.catalog
    for (func, line), (text, _) in PASTIME_HOOK_LINES.items():
        e = cat.index[func]
        assert dict(cat.lines_of(e.rel))[line].strip() == text, (func, line)
    for name in ("PASTIME_FASHION", "MESSAGE_PASTIME_FITNESSCLUB", "MESSAGE_PASTIME_MASSAGESALON", "MESSAGE_PASTIME_POOL",
                 "MESSAGE_PASTIME_ZOO", "MESSAGE_PASTIME_AQUARIUM", "MESSAGE_PASTIME_AMUSEMENTPARK", "MESSAGE_PASTIME_BOTANICALGARDEN",
                 "MESSAGE_PASTIME_LIVESHOW", "MESSAGE_PASTIME_WATERPARK", "MESSAGE_PASTIME_BEACHSIDE", "MESSAGE_PASTIME_SPA",
                 "PASTIME_AKUOTI_EVENT", "KAIZOU_SEIFUKU", "KAIZOU_PANT", "KAIZOU_BRA", "SHITAGI_COLOR", "MESSAGE_SCHOOL_CLASSWORK",
                 "MESSAGE_SCHOOL_CLASSWORK_CL", "MESSAGE_SCHOOL_CLASSWORK_PE", "MESSAGE_SCHOOL_LUNCHBREAK",
                 "MESSAGE_SCHOOL_CLUBACTIVITIES", "SCHOOL_CLUBSTRING", "PASTIME_TOHYO", "PASTIME_SHASHIN"):
        assert cat.unsupported_reason(name) is None, name  # 表外の代入があれば unsupported
        assert not cat.needs_input(name), name


def test_catalog_classwork_cl_masturbation_hooks(ctx, data, svc):
    """Message_School_Classwork_CL:432–569：LOCAL ≥ 100（自慰中毒 * 5）かつ欲望 > 0 → 自慰経験・絶頂経験 +1（hook）。"""
    st = ctx.state
    c = st.target_chara
    c.abl[A(data, "欲望")] = 1
    c.abl[A(data, "自慰中毒")] = 20
    cctx = Ctx(st, data, TextOutput(), svc)
    st.rng = GameRng(3)
    e0 = (c.exp[E(data, "自慰経験")], c.exp[E(data, "絶頂経験")])
    assert svc.run_function(cctx, "Message_School_Classwork_CL", [])
    assert (c.exp[E(data, "自慰経験")], c.exp[E(data, "絶頂経験")]) == (e0[0] + 1, e0[1] + 1)
    assert "自慰経験：＋1" in texts(cctx.out)


def test_catalog_pool_swimsuit_hook(ctx, data, svc):
    """MESSAGE_PASTIME_Pool:443–460：淫乱・初心なし・ISGIRLY → CFLAG:270 は 0〜3、:644 CFLAG:342 += 1。"""
    st = ctx.state
    c = st.target_chara
    c.talent[T(data, "淫乱")] = 1
    cctx = Ctx(st, data, TextOutput(), svc)
    assert svc.run_function(cctx, "MESSAGE_PASTIME_Pool", [])
    assert c.cflag[270] in (0, 1, 2, 3) and c.cflag[342] == 1


def test_pool_fallback_plain(ctx, data):
    """Null（catalog 不可）：淫乱なし → :469–470 競泳（CFLAG:270 = 5）、:644。淫乱の分岐は乱数依存 → 停止。"""
    c = ctx.state.target_chara
    pt._chinobun(ctx, "MESSAGE_PASTIME_Pool")
    assert (c.cflag[270], c.cflag[342]) == (5, 1)
    c.talent[T(data, "淫乱")] = 1
    with pytest.raises(NotImplementedError):
        pt._chinobun(ctx, "MESSAGE_PASTIME_Pool")


@pytest.mark.parametrize("use_svc", [False, True])
def test_fitness_eroevent_static(ctx, data, svc, use_svc):
    """MESSAGE_PASTIME_FitnessClub:314／:347：`#DIM EROEVENT = 0` は静的で初回訪問で 1 になり戻らない → 2 回目も RESULT 1。"""
    st = ctx.state
    c = st.target_chara
    if use_svc:
        ctx = Ctx(st, data, TextOutput(), svc)
    for k in (1, 2):
        pt._chinobun(ctx, "MESSAGE_PASTIME_FitnessClub")
        assert st.result[0] == 1 and c.cflag[334] == k


# --- @PASTIME（ACTION_PASTIME.ERB） ----------------------------------------------------------------


@pytest.fixture
def dispatch(monkeypatch):
    rec: list = []
    monkeypatch.setattr(pt, "machi", _gen(rec, "machi"))
    monkeypatch.setattr(pt, "toode", _gen(rec, "toode"))
    monkeypatch.setattr(pt, "undou", _gen(rec, "undou"))
    monkeypatch.setattr(pts, "pastime_school", _gen(rec, "school"))
    monkeypatch.setattr(pt, "pastime_rest", lambda ctx: None)
    monkeypatch.setattr(gather, "calc_charm_feat_other", lambda ctx, who: 0)
    monkeypatch.setattr(ablup_mod, "ablup", lambda ctx, arg: None)
    return rec


@pytest.mark.parametrize("item,time,rands,expected", [
    (1, 0, [], ("school", 0)),  # :45–46 RESULT 0 → 学校（ARG = RESULT）
    (3, 0, [3], ("machi", 3)),  # :69–70
    (4, 0, [5], ("toode", 5)),
    (5, 1, [2], ("undou", 2)),
    (6, 0, [], ("machi", 0)),  # :75–76 RESULT 5〜8 → 街(RESULT-5)
    (9, 0, [], ("machi", 3)),
    (10, 0, [], ("toode", 0)),
    (17, 0, [], ("toode", 7)),
    (18, 0, [], ("undou", 0)),
    (21, 1, [], ("undou", 3)),
    (2, 0, [0], ("school", -1)),  # :48–58 昼のランダム
    (2, 0, [1, 2], ("machi", 2)),
    (2, 0, [2, 7], ("toode", 7)),
    (2, 0, [3, 1], ("undou", 1)),
    (2, 1, [0, 3], ("machi", 3)),  # :60–67 夜は 1+RAND:3
    (2, 1, [1, 4], ("toode", 4)),
    (2, 1, [2, 0], ("undou", 0)),
])
def test_schedule_dispatch(ctx, dispatch, item, time, rands, expected):
    st = ctx.state
    st.time = time
    st.target_chara.cflag[113] = item  # 項目 1 つ（実行番号 0）
    st.rng = FixedRng(rands)
    assert run(pt.pastime(ctx)) is None
    assert dispatch == [expected]


def test_schedule_out_of_range_does_nothing(ctx, dispatch):
    """RES_SCHEDULE が 21 以上（項目 22）→ :45–81 どれにも当たらない。"""
    ctx.state.target_chara.cflag[113] = 22
    run(pt.pastime(ctx))
    assert dispatch == []


def test_schedule_night_school_skips_to_next(ctx, dispatch):
    """:33–43：夜に通学 → 次の項目（ランダム(街) = 項目 3）を探す。"""
    st = ctx.state
    st.time = 1
    st.target_chara.cflag[113] = 1 + 3 * 100
    st.rng = FixedRng([2])
    run(pt.pastime(ctx))
    assert dispatch == [("machi", 2)]


@pytest.mark.parametrize("items", [1, 2, 9])
def test_schedule_night_all_school(ctx, dispatch, items):
    """:36 `FOR LOCAL,1,NUM_SCHEDULE_F(113)+1`：全部通学なら NUM_SCHEDULE_F 回 RES_SCHEDULE して RESULT 0 → 夜でも学校(0)。
    実行番号は最初の 1 回 + n 回進む（項目数で巡回：ACTIONsub_SCHEDULE.ERB:481–493）。"""
    st = ctx.state
    st.time = 1
    n = sum(100**k for k in range(items))
    st.target_chara.cflag[113] = n
    run(pt.pastime(ctx))
    assert dispatch == [("school", 0)]
    assert st.target_chara.cflag[113] == ((1 + n) % items) * E18 + n


def test_manual_menu_invalid_inputs(ctx, dispatch, data):
    """:97–131：範囲外 → 正しい値…、[3] で学生でない → 正しい値…、学生でも夜 → 昼のみ。"""
    st = ctx.state
    assert run(pt.pastime(ctx), [5, 3, 0]) is None
    assert texts(ctx.out).count("正しい値を入力してください") == 2
    assert dispatch == [("machi", -1)]
    dispatch.clear()
    st.target_chara.talent[T(data, "学生")] = 3
    st.time = 1
    assert run(pt.pastime(ctx), [3, 2]) is None
    assert "学校に行けるのは昼のみです" in texts(ctx.out)
    assert any("[3]学校に行く" in t for t in texts(ctx.out))
    assert dispatch == [("undou", -1)]


def test_pastime_rest(ctx, data):
    """PASTIME_REST:164–212：体力 10%+200、気力 30%+200、性耐性 1/2、回復遅いは体力 -5・気力 +5（:170–172）、疲労 -10。"""
    c = ctx.state.target_chara
    _clear(ctx, ("回復早い", "回復遅い", "魔力貯蔵", "不老長寿", "溢れる生命力"))
    hp, mp, sei = B(data, "体力"), B(data, "気力"), B(data, "性耐性")
    for k in (hp, mp, sei):
        c.base[k] = 0
    c.cflag[99] = 15
    pt.pastime_rest(ctx)
    assert (c.base[hp], c.base[mp], c.base[sei]) == (2787 * 10 // 100 + 200, 2454 * 30 // 100 + 200, 198 // 2)
    assert c.cflag[99] == 5 and "紅葉の身体から疲労が少し抜けた…" in texts(ctx.out)
    for k in (hp, mp):
        c.base[k] = 0
    c.talent[T(data, "回復遅い")] = 1
    pt.pastime_rest(ctx)
    assert (c.base[hp], c.base[mp]) == (2787 * 5 // 100 + 200, 2454 * 35 // 100 + 200)


def test_action_main_free_and_flag73(ctx, dispatch):
    """ACTION.ERB:157–163：PASTIME の後 FLAG:73 > 0 なら TRAIN、それ以外 TURNEND。"""
    st = ctx.state
    st.flag[799] = 0
    st.charas[1].cflag[100] = ActionPlan.FREE
    assert run(action_main(ctx), [1]) == Step.TURNEND
    assert dispatch == [("toode", -1)]


# --- 判定 -----------------------------------------------------------------------------------


@pytest.mark.parametrize("roll,naki,nanpa,sake", [(25, 0, 1, 1), (26, 0, 0, 0), (28, 1, 1, 1), (29, 1, 0, 1), (31, 1, 0, 0)])
def test_nanpa_judgement(ctx, data, roll, naki, nanpa, sake):
    """PASTIME_NANPA:12–68／SAKE_NANPA:13–69：10 + RAND:10（4）＋高校生 3＋巨乳 3＋巻き込まれ体質 5（＋泣き虫 3／5）、RAND:100 <= 値。"""
    _clear(ctx)
    c = ctx.state.target_chara
    for k, v in (("学生", 3), ("巨乳", 1), ("巻き込まれ体質", 1), ("泣き虫", naki)):
        c.talent[T(data, k)] = v
    ctx.state.rng = FixedRng([4, roll])
    assert pt.pastime_nanpa(ctx) == nanpa and ctx.state.result[0] == nanpa
    ctx.state.rng = FixedRng([4, roll])
    assert pt.pastime_sake_nanpa(ctx) == sake


def test_chikan_seated_no_event(ctx):
    """PASTIME_CHIKAN：混雑度 RAND:95=10 +5（朝）= 15 → まばら・着席（STAND_POS -1）→ :222 不成立、:462–465 DOT_AFTER、RETURN 0。"""
    _clear(ctx)
    ctx.state.rng = FixedRng([10, 0, 0, 0])
    assert run(pt.pastime_chikan(ctx, -1)) == 0
    tx = texts(ctx.out)
    assert "車内にはまばらに人がいるが座席に座れない事もなさそうだ。" in tx
    assert "座席を確保できた紅葉は座って一息ついた・・・" in tx


def test_chikan_triggered_stops(ctx):
    """混雑 65 → ドア前（STAND_POS 1）、RAND:80 = 0 <= 判定 → 痴漢；[1]抵抗で RAND:100 = 0 < 失敗率 → 本編（S28c2）で停止。"""
    _clear(ctx)
    ctx.state.rng = FixedRng([60, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0])
    with pytest.raises(NotImplementedError, match="MESSAGE_PASTIME_CHIKAN"):
        run(pt.pastime_chikan(ctx, -1), [1])
    tx = texts(ctx.out)
    assert "紅葉がドアの前に立って景色を眺めていると" in tx
    assert "口を開いた瞬間、脂ぎった中年オヤジに口を抑えられ声を発することができなかった・・・" in tx


def test_chikan_buzzer(ctx):
    """[3]防犯ブザー → TEIKOU 0 → 本編に入らず RETURN 0。"""
    _clear(ctx)
    ctx.state.rng = FixedRng([60, 0, 0, 0, 0, 0, 1, 0])
    assert run(pt.pastime_chikan(ctx, -1), [9, 3]) == 0
    assert "脂ぎった中年オヤジは即座に離れていった・・・" in texts(ctx.out)


# --- 各イベント -----------------------------------------------------------------------------


@pytest.fixture
def no_nanpa(monkeypatch):
    monkeypatch.setattr(pt, "pastime_nanpa", lambda ctx: 0)
    monkeypatch.setattr(pt, "pastime_sake_nanpa", lambda ctx: 0)


@pytest.mark.parametrize("arg,dest", [(0, "ショッピングモール"), (2, "繁華街"), (3, "公園")])
def test_machi_destination(ctx, no_nanpa, arg, dest):
    """街に出る:43 CFLAG:101 = 行き先 + 5、:49 の RESULT は DOT_AFTER（RETURN RESULT）を通っても行き先のまま、:427。"""
    assert run(pt.machi(ctx, arg)) is None
    assert ctx.state.target_chara.cflag[101] == 5 + arg
    assert texts(ctx.out)[-1] == f"紅葉は、{dest}を満喫してきたようだ。"


def test_machi_invalid_then_nanpa_stop(ctx, monkeypatch):
    monkeypatch.setattr(pt, "pastime_nanpa", lambda ctx: 1)
    with pytest.raises(NotImplementedError, match="MESSAGE_PASTIME_NANPA"):
        run(pt.machi(ctx, -1), [4, 3])
    assert "正しい値を入力してください" in texts(ctx.out)
    assert ctx.state.target_chara.cflag[101] == 8


@pytest.mark.parametrize("time,stop", [(0, False), (1, True)])
def test_machi_sake_nanpa_only_at_night(ctx, monkeypatch, time, stop):
    """街に出る:327–331：酒ナンパは `RESULT > 0 && TIME > 0` のときだけ本編。"""
    monkeypatch.setattr(pt, "pastime_sake_nanpa", lambda ctx: 1)
    monkeypatch.setattr(pt, "pastime_nanpa", lambda ctx: 0)
    ctx.state.time = time
    if stop:
        with pytest.raises(NotImplementedError, match="SAKE_NANPA"):
            run(pt.machi(ctx, 2))
    else:
        run(pt.machi(ctx, 2))
        assert texts(ctx.out)[-1] == "紅葉は、繁華街を満喫してきたようだ。"


@pytest.mark.parametrize("roll,ink", [(51, True), (50, False)])
def test_toode_inkioukyu_by_defense(ctx, monkeypatch, no_nanpa, roll, ink):
    """遠出する:61 CFLAG:101 = 行き先 + 9、:102 `RAND:100 > FLAG:852 / 100`（5000 → 50）で淫気応急。"""
    rec: list = []
    monkeypatch.setattr(pt, "pastime_chikan", _gen(rec, "chikan"))
    monkeypatch.setattr(pt, "inkioukyu", _gen(rec, "ink"))
    ctx.state.rng = FixedRng([roll])
    run(pt.toode(ctx, 4))
    assert ctx.state.target_chara.cflag[101] == 13
    assert rec[0] == ("chikan", 4)
    assert (("ink", 0) in rec) is ink
    if not ink:
        assert "紅葉は、ライブを楽しんできたようだ。" in texts(ctx.out)


def test_undou_fitness_eroevent_blocks_nanpa(ctx, monkeypatch):
    """運動する:58–59／:70：フィットネス初回の EROEVENT 1 でナンパ本編に入らない。マッサージ（EROEVENT 0）は本編 → 停止。"""
    monkeypatch.setattr(pt, "pastime_nanpa", lambda ctx: 1)
    run(pt.undou(ctx, 1))
    assert texts(ctx.out)[-1] == "紅葉は、フィットネスクラブで身体を存分に動かしたようだ。"
    assert ctx.state.target_chara.cflag[101] == 18
    with pytest.raises(NotImplementedError, match="MESSAGE_PASTIME_NANPA"):
        run(pt.undou(ctx, 2))


def test_sports_park_count_and_kokurare(ctx, data, no_nanpa):
    """SportsPark:303–307 CFLAG:330 += 1；交際相手 0 で KOKURARE（330 = 15 → 告白、[1] → 交際相手 2：告られ:70）。"""
    c = ctx.state.target_chara
    c.cflag[330] = 15
    assert run(pt.undou(ctx, 0), [1]) is None
    assert c.talent[T(data, "交際相手")] == 2 and c.cflag[330] == 16
    assert "[1]付き合う" in texts(ctx.out)


def test_kokurare_small_talk(ctx):
    """告られ:75–76：CFLAG:330 == 13 → 連絡先交換（INPUT なし）。"""
    ctx.state.target_chara.cflag[330] = 13
    assert run(pt.kokurare(ctx)) is None
    assert any("友人のランナーと連絡先を交換した。" in t for t in texts(ctx.out))


def test_select_school(ctx, data):
    """学校途中編入:26–45：範囲外 → 正しい値…、[3] → TALENT:学生 = 3。"""
    assert run(pt.select_school(ctx), [7, 3]) is None
    assert ctx.state.target_chara.talent[T(data, "学生")] == 3
    assert "紅葉は高校に編入することにした。" in texts(ctx.out)


def test_pastime_select_school_on_day30(ctx, data, dispatch):
    """ACTION_PASTIME:8–10：学生 0 かつ DAY % 30 == 0 かつ DAY > 29 で編入の機会。"""
    ctx.state.day[0] = 30
    run(pt.pastime(ctx), [4, 0])
    assert ctx.state.target_chara.talent[T(data, "学生")] == 4
    assert dispatch == [("machi", -1)]


@pytest.mark.parametrize("gakusei,inp,cf,label", [(2, 1, 11, "運動部"), (1, 2, 2, "図書委員"), (4, 0, 20, "所属しない")])
def test_select_club(ctx, data, gakusei, inp, cf, label):
    """SelectClub:1518–1576：大学 20+、小学 そのまま、他 10+ を CFLAG:352（変身中は 353）。"""
    c = ctx.state.target_chara
    c.talent[T(data, "学生")] = gakusei
    run(pts.select_club(ctx), [inp])
    assert c.cflag[352] == cf and label in texts(ctx.out)
    if inp == 0:
        assert "紅葉はどこにも入部しないことにした。" in texts(ctx.out)


def test_akuoti_encounter_negative_defense(ctx, data):
    """悪堕ち遭遇:19：DEVIATION D4 — FLAG:852 < 0 の SQRT を 0 → RAND:(0/2+20)；候補 1 人 → FLAG:111。"""
    st = ctx.state
    st.flag[852] = -100
    st.charas[2].cflag[0] = 3
    bounds = []

    class Rec(FixedRng):
        def rand(self, n):
            bounds.append(n)
            return super().rand(n)

    st.rng = Rec([5, 0])
    pt.akuoti_encounter(ctx)
    assert bounds[0] == 20 and st.flag[111] == 2
    assert "〈地の文：PASTIME_AKUOTI_EVENT〉" in texts(ctx.out)


def test_inkioukyu_sumata_exp(ctx, data, monkeypatch):
    """淫気応急：下着越し素股（:49–51）→ 通常処理、CFLAG:42 = 300 → :288–293 と :304 S_膣内精液 += 2+RAND:3。
    CALC_INKIOKYU：S_回数 12、フェラ経験 = 12 - (0 + 0 + 4 + RAND:6=0) = 8（:532）、処女なので妊娠判定なし。"""
    monkeypatch.setattr(ablup_mod, "ablup", lambda ctx, arg: None)
    c = ctx.state.target_chara
    c.abl[A(data, "Ｃ感覚")] = 0
    before = list(c.exp[i] for i in range(100))
    ctx.state.rng = FixedRng([1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0])
    run(pt.inkioukyu(ctx))
    diff = {i: c.exp[i] - before[i] for i in range(100) if c.exp[i] != before[i]}
    assert diff == {E(data, "精液経験"): 15, E(data, "フェラ経験"): 8}
    assert c.talent[T(data, "処女")] == 1


def test_inkioukyu_rape_loses_virgin(ctx, data, monkeypatch):
    """暴走レイプ（:176 RAND:5 == 0）→ 秘裂（:182 RAND:2 = 1）→ 処女喪失 TALENT:処女 = -1・CFLAG:206 = 11（:203–205）。
    CALC：Ｖ経験・被姦経験・絶頂経験 +1、精液経験 15（RAND:16 = 0）、膣内精液 = MIN(1 + 10 + 0, 15) = 11 で NINSIN_HANTEI(11, 100, -4)。"""
    monkeypatch.setattr(ablup_mod, "ablup", lambda ctx, arg: None)
    monkeypatch.setattr(pt, "_holyvirgin", lambda ctx: 0)
    calls = []
    monkeypatch.setattr(ninsin_mod, "ninsin_hantei", lambda ctx, a, b, d=0: calls.append((a, b, d)) or 0)

    def pill(ctx, who, a, b):
        calls.append(("pill", a, b))
        return None
        yield  # pragma: no cover

    monkeypatch.setattr(ninsin_mod, "after_pill", pill)
    c = ctx.state.target_chara
    c.abl[A(data, "Ｃ感覚")] = 0
    ctx.state.rng = FixedRng([1, 0] + [1, 0, 1] + [0, 0, 0, 0, 0, 0])
    run(pt.inkioukyu(ctx))
    assert c.talent[T(data, "処女")] == -1 and c.cflag[206] == 11
    assert calls == [(11, 100, -4), ("pill", 20, -4)]
    for k, v in (("Ｖ経験", 1), ("被姦経験", 1), ("精液経験", 15)):
        assert c.exp[E(data, k)] >= v


def test_school_full_day_catalog(ctx, data, svc, monkeypatch):
    """学校に行く（catalog）：高校生、通学の痴漢なし → 授業・昼休み・放課後（帰宅部 CFLAG:350 == 0 → 部活選択 [1] → 運動部 11）、
    :359–362 CFLAG:350／357 += 1。"""
    st = ctx.state
    c = st.target_chara
    c.talent[T(data, "学生")] = 3
    monkeypatch.setattr(pts, "pastime_chikan", _gen([], "chikan"))
    monkeypatch.setattr(pts, "pastime_nanpa", lambda ctx: 0)
    cctx = Ctx(st, data, TextOutput(), svc)
    st.rng = GameRng(11)
    assert run(pts.pastime_school(cctx, -1), [1]) is None
    tx = texts(cctx.out)
    assert "【午前】" in tx and "【昼休み】" in tx and "【放課後】" in tx
    assert not any("〈地の文" in t for t in tx)
    assert (c.cflag[352], c.cflag[350], c.cflag[357]) == (11, 1, 1)
    assert "紅葉は、学業を果たしてきたようだ。" in tx


def test_school_kaizou_static(ctx, data, monkeypatch):
    """学校:9–10 `#DIM 改造制服` は静的：一度セーラー服で登校すると、その後 CFLAG:40 を変えても 1 のまま（KAIZOU_SEIFUKU を呼ぶ）。"""
    st = ctx.state
    c = st.target_chara
    c.talent[T(data, "学生")] = 3
    monkeypatch.setattr(pts, "pastime_chikan", lambda ctx, a: (yield from iter(())) or 1)
    calls = []
    orig = pts._chinobun
    monkeypatch.setattr(pts, "_chinobun", lambda ctx, f, *a, **k: calls.append(f) or orig(ctx, f, *a, **k))
    c.cflag[40] = 101
    run(pts.pastime_school(ctx, -1))
    c.cflag[40] = 100
    run(pts.pastime_school(ctx, -1))
    assert calls == ["KAIZOU_SEIFUKU", "KAIZOU_SEIFUKU"]


# --- 整合：SHOP → 自由行動 → TURNEND → SHOP --------------------------------------------------


def test_shop_pastime_turnend(data):
    with tempfile.TemporaryDirectory() as tmp:
        s = GameSession(data, Path(tmp), rng=GameRng(7), narration=CatalogNarrationService(ERB, data))
        s.input(0)
        s.input(1)  # 初期セット『特装戦隊』
        s.input(1)  # 基本セット
        assert s.phase == Phase.SHOP
        st = s.state
        day = st.day[0]
        st.charas[1].cflag[113] = 19  # スケジュール：運：マッサージサロン（RESULT 18 → 運動(1)…:79–80 は 17〜20 → 運動(RESULT-17)）
        for i, p in {1: 108, 2: 103, 3: 103}.items():
            s.input(i)
            s.input(p)
        s.input(100)
        for v in (9, 1):  # 確認 [9] → 変身しない
            if s.phase == Phase.SHOP:
                break
            s.input(v)
        for _ in range(40):
            if s.phase == Phase.SHOP or s.phase == Phase.HALTED:
                break
            s.input(0)
        st = s.state
        c = st.charas[1]
        if s.phase == Phase.HALTED:  # ナンパ本編（S28c2）に当たったら停止画面
            assert any("ナンパ" in ln.text for ln in s.out.lines)
            return
        assert s.phase == Phase.SHOP
        assert (st.day[0], st.time) == (day, 1)
        assert c.cflag[101] == 18 and c.cflag[334] == 1
        assert any("【紅葉の行動：自由行動】" in ln.text for ln in s.out.lines)
