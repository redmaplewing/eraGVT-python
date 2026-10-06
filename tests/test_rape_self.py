"""S15：戦闘後レイプ（`ゲーム内_イベント発生/戦闘イベント.ERB@AFTER_TRAIN_RAPE`:962–1334、
`ゲーム内_イベント発生/CALC_GANGBANG.ERB@CALC_GANGBANG`:3–166）と自慰系
（`ゲーム内_イベント発生/強制発生イベント/FORCE_夜間自慰.ERB`）。

expected は ERB 原文から手計算（路徑相對 `source/earGVP/ERB/`、行號は註解）。
"""

from __future__ import annotations
from _gen_driver import as_generator, run_no_input

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop, turnend
from eragvt.game.action import Ctx, Step
from eragvt.game.battle import after, palam, rape, self_kind, sexcom
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


class RecRng(GameRng):
    """先頭から与えた値を返し（`値 % n`）、尽きたら 0。呼ばれた RAND の上限を記録する。"""

    def __init__(self, values: list[int]) -> None:
        super().__init__(0)
        self.values = list(values)
        self.calls: list[int] = []

    def rand(self, n: int) -> int:
        self.calls.append(n)
        v = self.values.pop(0) if self.values else 0
        return v % n


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


def _state(data) -> GameState:
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1、TIME=0、TARGET=1（紅葉）
    return s


@pytest.fixture
def ctx(data):
    return Ctx(_state(data), data, TextOutput(), NullNarrationService())


@pytest.fixture
def cctx(data, svc):
    return Ctx(_state(data), data, TextOutput(), svc)


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


def _rape_ready(st, data, *, virgin: int = 0) -> None:
    """襲われる確率 = 50（FLAG:852 = 0、FLAG:72 = 1：:977–980）、常時避妊（NINSIN_HANTEI／AFTER_PILL は RAND なしで戻る）。"""
    st.flag[852] = 0
    st.flag[72] = 1
    st.flag.set_bit(805, 2, True)  # CONFIG_CHECK_OTHER_F(2) 常時避妊（CONFIG_CHECK_OTHER_F = GETBIT(FLAG:805, n)）
    st.tflag[98] = 1
    st.charas[1].talent[I(data, "TALENT", "処女")] = virgin


# --- AFTER_TRAIN_RAPE:970–983 発生判定 ---------------------------------------------------------------


def test_rape_not_alive_or_not_hole(ctx, data):
    st = ctx.state
    c = st.charas[1]
    st.rng = RecRng([])
    c.cflag[0] = 1  # :970–971
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    c.cflag[0] = 0
    c.talent[I(data, "TALENT", "オトコ")] = 1  # :973–974 ISHOLE()：男性、CONFIG_CHECK_MANIAC_F(5) == 0
    st.flag.set_bit(850, 5, True)
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    assert st.rng.calls == []


@pytest.mark.parametrize(
    "flag852, cflag285, naburare, flag72, local",
    [
        (0, 0, 0, 1, 50),  # MIN(50, 50)
        (0, 0, 0, 0, 25),  # :979–980 FLAG:72 == 0 → /2
        (4000, 10, 1, 1, 40),  # MIN(10,50) + MIN(20,50) + 10
        (6000, 40, 0, 1, 40),  # MIN(-10,50) + MIN(80,50)
        (4000, 10, 1, 0, 20),  # 40 / 2
    ],
)
def test_rape_probability(ctx, data, flag852, cflag285, naburare, flag72, local):
    st = ctx.state
    c = st.charas[1]
    st.flag[852] = flag852
    st.flag[72] = flag72
    c.cflag[285] = cflag285
    c.talent[I(data, "TALENT", "嬲られ体質")] = naburare
    st.rng = RecRng([local])  # :982 RAND:100 >= LOCAL → RETURN 0
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    assert st.rng.calls == [100]
    assert texts(ctx.out) == []
    st.rng = RecRng([local - 1, 0, 0])  # 発生 → :995 RAND:100 = 0 < 閾値 → 尾けられた
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    assert st.rng.calls[:2] == [100, 100]
    assert "――――――" in texts(ctx.out)


@pytest.mark.parametrize(
    "flag72, rolls, calls, line",
    [
        (0, [0, 0], [100, 100, 2], "どうやら気のせいだったようだ・・・"),  # LOCAL 25 → `LOCAL < 25` 偽 → RAND:2 == 0
        (0, [0, 0, 1], [100, 100, 2], "うまく撒くことができたようだ・・・"),
        (1, [0, 0, 1], [100, 100, 2], "うまく撒くことができたようだ・・・"),
    ],
)
def test_rape_followed(ctx, data, flag72, rolls, calls, line):
    st = ctx.state
    st.flag[852] = 0
    st.flag[72] = flag72
    st.rng = RecRng(rolls)
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    assert st.rng.calls == calls
    t = texts(ctx.out)
    i = t.index("紅葉は誰かに尾けられているような気がしたが、")
    assert t[i + 1] == line


def test_rape_followed_low_local_skips_rand2(ctx):
    st = ctx.state
    st.flag[852] = 4000  # LOCAL = 10 / 2 = 5 < 25 → RAND:2 は評価しない（`||` 短絡）
    st.flag[72] = 0
    st.rng = RecRng([0, 0])
    assert run_gen(rape.after_train_rape(ctx, 0)) == 0
    assert st.rng.calls == [100, 100]
    assert "どうやら気のせいだったようだ・・・" in texts(ctx.out)


@pytest.mark.parametrize(
    "tflag98, time, naburare, roll, outcome",
    [
        # LOCAL:1 = 40：閾値 40*3/4 + 0 - 12(夜) - 12(嬲られ) = 6
        (0, 1, 1, 5, None),
        (0, 1, 1, 6, "不利を悟って何とか撤退した紅葉。"),
        # 勝利・昼：30 + 6 = 36
        (1, 0, 0, 35, None),
        (1, 0, 0, 36, "何とか戦闘に勝利することができた紅葉。"),
    ],
)
def test_rape_escape_threshold(ctx, data, tflag98, time, naburare, roll, outcome):
    st = ctx.state
    c = st.charas[1]
    st.flag[852] = 0
    st.flag[72] = 1
    st.flag.set_bit(805, 2, True)
    st.tflag[98] = tflag98
    st.time = time
    c.talent[I(data, "TALENT", "嬲られ体質")] = naburare
    # :992 PERCENT_CAL(体力 + 気力 + 性耐性*10, MAX体力 + MAX気力 + 性耐性*10) = 400*100/1000 = 40
    c.base[0], c.base[1], c.base[2] = 200, 200, 0
    c.maxbase[0], c.maxbase[1] = 500, 500
    st.rng = RecRng([0, roll])
    r = run_gen(rape.after_train_rape(ctx, 0))
    t = texts(ctx.out)
    if outcome is None:
        assert r == 0 and "紅葉は誰かに尾けられているような気がしたが、" in t
    else:
        assert r == 1 and outcome in t


def _exp(c, data):
    return {n: c.exp[I(data, "EXP", n)] for n in
            ("Ｖ経験", "Ａ経験", "精液経験", "フェラ経験", "苦痛快楽経験", "異常経験", "Ｖ拡張経験", "Ａ拡張経験")}


def test_rape_first_time_virgin(ctx, data):
    """初回（CFLAG:286 == 0）・処女：:1028 初回の文、:1111 RAND なし、:1153 処女、:1236 処女喪失・NAKADASHI = 1。"""
    st = ctx.state
    c = st.charas[1]
    _rape_ready(st, data, virgin=1)
    e0 = _exp(c, data)
    # :982 RAND:100, :995 RAND:100, :1264 RAND:3, :1315 RAND:2,
    # CALC_GANGBANG :36 RAND:30, :71 RAND:5 ×2, :81 RAND:16, :83 RAND:5, :116 RAND:3、以降は COMMON_PRISON 等
    st.rng = RecRng([0, 99, 1, 1, 5, 3, 1, 4, 2, 1])
    assert run_gen(rape.after_train_rape(ctx, 1)) == 1  # :1334
    assert st.rng.calls[:10] == [100, 100, 3, 2, 30, 5, 5, 16, 5, 3]
    assert st.rng.calls[-1] == 100  # :162 悪い噂（最後の RAND）→ 0 < 30
    t = texts(ctx.out)
    assert "大して苦戦することもなく勝利した紅葉。" in t  # :1020–1021（LOCAL:1 = 100）
    assert "射精させれば正気に戻るはずだと覚悟を決めた・・・" in t
    assert "破瓜の痛みと共にまだ男を知らないヴァギナが貫かれ、紅葉の悲鳴が路地に響き渡る・・・" in t  # :1155–1165
    assert "処女喪失" in t
    assert "身勝手なピストンで男が限界に登り詰めて膣内射精を決めると、" in t
    assert "なおも諦めずに止めるよう説得を続ける紅葉を嘲笑うように" in t  # :1292–1302
    assert "絶望に染め上げられた紅葉の瞳が光を失っていく・・・" in t
    assert "男たちのうち一人がハンディカメラでレイプの一部始終を録画しており、" in t  # :1317–1319
    # CALC_GANGBANG
    assert c.talent[I(data, "TALENT", "処女")] == -1  # :38–42
    assert c.cflag[206] == 11
    assert c.cflag[35] == 10 and c.cflag[36] == 10  # :49–52、:75–78
    assert c.cflag[286] == 1  # :105
    assert c.cflag[825] == 1  # :162–163
    e1 = _exp(c, data)
    # :36 LOCAL:120 = 15、:71 LOCAL:121 = 40 - 15 + 3 - 1 = 27、:81 19、:83 14、:116 3、:112 1、:51／:77 2
    assert {k: e1[k] - e0[k] for k in e0} == {"Ｖ経験": 15, "Ａ経験": 27, "精液経験": 19, "フェラ経験": 14,
                                               "苦痛快楽経験": 3, "異常経験": 1, "Ｖ拡張経験": 2, "Ａ拡張経験": 2}
    assert st.temp.locals[("CALC_GANGBANG", 11)] == 10  # :21–22 Ｖ感覚 0 → 10（処女なので ×3 なし）
    assert st.temp.locals[("CALC_GANGBANG", 20)] == 500


def test_rape_second_time(ctx, data):
    """二度目以降・非処女・陥落経験あり：:1034 「お前のせいで」（RAND:8 ≠ 0、RAND:7 == 0 → 母さん）、:1167 二度目以降。"""
    st = ctx.state
    c = st.charas[1]
    _rape_ready(st, data, virgin=0)
    c.cflag[286] = 1
    c.exp[I(data, "EXP", "陥落経験")] = 1
    # :982, :995, :1034 RAND:3=0, RAND:8=1, RAND:7=0, :1111 RAND:2=1, :1264 RAND:3=1, :1284 RAND:2=0, CALC …
    st.rng = RecRng([0, 99, 0, 1, 0, 1, 1, 0])
    assert run_gen(rape.after_train_rape(ctx, 1)) == 1
    assert st.rng.calls[:9] == [100, 100, 3, 8, 7, 2, 3, 2, 30]  # :1315 は CFLAG:286 > 0 で RAND なし
    t = texts(ctx.out)
    assert "男たちは苦々しげに、「お前のせいで母さんが……」と言いながらズボンを下ろし、" in t
    assert "すると男はそのまま紅葉を押し倒し、" in t
    assert "何度も謝罪の言葉を口にする紅葉を平手打ちで黙らせ、" in t
    assert "ヴァギナに挿入して乱暴にピストンし始めた。" in t
    assert "男が限界に登り詰めて当然のように膣内射精を決めると、" in t
    assert "全員に順番が回ると２週目、３週目が始まって休むことも許されず、" in t
    assert "「次も頼むわ」という言葉と共に、男たちは下卑た笑いだけ残して去っていった。" in t
    assert c.cflag[286] == 2
    assert st.temp.locals[("CALC_GANGBANG", 11)] == 30  # :45 非処女 → 10 * 3


@pytest.mark.parametrize("flag852, line", [
    # LOCAL = MIN((5000-4900)/100, 50) = 1：パイズリを選ばなくても :1230 `LOCAL == 1` が真（原作どおり）
    (4900, "男が限界に登り詰めて胸に精液をぶっかけると、"),
    (4800, "男が口にねじ込んだまま喉に精液を放出すると、"),
])
def test_rape_holy_virgin_local_quirk(ctx, data, flag852, line):
    st = ctx.state
    c = st.charas[1]
    _rape_ready(st, data, virgin=2)  # CHECK_HOLYVIRGIN_F：処女 >= 2
    st.flag[852] = flag852
    # :982 RAND:100=0, :995 99, :1137 RAND:2=1（パイズリしない）
    st.rng = RecRng([0, 99, 1])
    assert run_gen(rape.after_train_rape(ctx, 1)) == 1
    t = texts(ctx.out)
    assert "男がペニスで明らかにオトコ慣れしていないアナルに捻り込んで、ピストンし始めた。" not in t
    assert "男が指すら入った事ないアナルをハンドクリームを使って" in t  # :1141 Ａ経験 0、CFLAG:36 0
    assert line in t
    assert c.talent[I(data, "TALENT", "処女")] == 2  # :16 V挿入ブロッカー → NAKADASHI = 0
    assert c.cflag[35] == 0


def test_rape_male(ctx, data):
    """男性（CONFIG_CHECK_MANIAC_F(5) == 1 で ISHOLE）：:1082 の OR は常に真 → 下着の文、:1122 アナル。"""
    st = ctx.state
    c = st.charas[1]
    _rape_ready(st, data)
    c.talent[I(data, "TALENT", "オトコ")] = 1
    st.flag.set_bit(850, 5, False)
    c.cflag[42] = 0
    st.rng = RecRng([0, 99])
    assert run_gen(rape.after_train_rape(ctx, 1)) == 1
    t = texts(ctx.out)
    assert "男が紅葉の服を乱暴に剥ぐと隠すもののないお尻が露わになった。" in t
    assert "メスになりたいなら手伝ってやるよ、と男の下卑た笑い声が響いた。" in t
    assert "オンナモノの下着なんか着けてこうやって犯されるのが夢だったんだろ？と男が嘲笑う。" in t
    assert "男が限界に登り詰めて直腸内に精液を放出すると、" in t
    # CALC_GANGBANG :72–73 ISMALE → LOCAL:121 = TIMES(40 - 0 + 0 - 0, 1.50) = 60
    assert st.temp.locals[("CALC_GANGBANG", 121)] == 60


def test_rape_male_underwear_catalog(cctx, data):
    """:1093–1096 SHITAGI_COLOR／KAIZOU_PANT（PASTIME_改造制服.ERB:134／359）を catalog で実行。"""
    st = cctx.state
    c = st.charas[1]
    _rape_ready(st, data)
    c.talent[I(data, "TALENT", "オトコ")] = 1
    st.flag.set_bit(850, 5, False)
    c.cflag[42] = 301  # かわいい下着：EQUIP:TARGET:301 = 0 → 色 0「白」、形 0「ショーツ」
    st.rng = RecRng([0, 99])
    run_gen(rape.after_train_rape(cctx, 1))
    assert "男が紅葉の服を乱暴に剥ぐと白のかわいいショーツが露わになった。" in texts(cctx.out)


# --- CALC_GANGBANG の静的 LOCAL ----------------------------------------------------------------------


def test_calc_gangbang_static_locals(ctx, data, monkeypatch):
    """LOCAL は VARSET されない（:3–166）：NAKADASHI なしの呼び出しでも前回の LOCAL:120（Ｖ経験）と LOCAL:11 が残る。"""
    st = ctx.state
    c = st.charas[1]
    st.flag.set_bit(805, 2, True)
    c.talent[I(data, "TALENT", "処女")] = 0
    st.rng = RecRng([7])  # :36 RAND:30 = 7 → LOCAL:120 = 17
    run_gen(rape.calc_gangbang(ctx, "戦闘後", 4, 1))
    assert st.temp.locals[("CALC_GANGBANG", 120)] == 17
    v0 = c.exp[I(data, "EXP", "Ｖ経験")]
    ups: list = []
    c.talent[I(data, "TALENT", "処女")] = 2  # 聖処女 → :16 NAKADASHI = 0
    c.abl[I(data, "ABL", "Ａ感覚")] = 0  # 1 回目の _ABLUP で上がった分を戻す（:57–58 → LOCAL:12 = 6）
    st.rng = RecRng([])
    from eragvt.game.prison import commands

    real = commands.common_prison
    monkeypatch.setattr(commands, "common_prison", lambda ctx_, args, arg12=0: (ups.append((list(args), arg12)),
                                                                               real(ctx_, args, arg12)))
    run_gen(rape.calc_gangbang(ctx, "戦闘後", 4, 1))
    # :124 LOCAL:10〜21：快Ｖ（LOCAL:11）は前回の 30、苦痛（LOCAL:20）は 0 のまま
    assert ups == [([0, 30, 6, 0, 0, 0, 100, 0, 500, 0, 0, 500], 1)]
    # :71 LOCAL:121 = 40 - 17（前回の LOCAL:120）+ 0 - 0
    assert st.temp.locals[("CALC_GANGBANG", 121)] == 23
    assert c.exp[I(data, "EXP", "Ｖ経験")] == v0 + 17  # :126–128 前回の LOCAL:120 がまた加算される
    assert c.cflag[286] == 2


# --- EVENTEND:498–504 → DOUGA_RYUSUTU, 1 --------------------------------------------------------------


def test_event_end_rape_then_video(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.cflag[100] = 101
    st.savestr[13] = "BOSS"
    st.flag[11] = 3
    st.flag[12] = 10000
    st.flag[13] = 3000
    st.tflag[98] = 0
    st.tflag[0] = 4
    _rape_ready(st, data, virgin=0)
    st.tflag[98] = 0
    # [:148 RAND:10, :159 RAND:101, :172 RAND:100（FLAG:852 == 0 → 人気度）, :221 RAND:4（探索度）, SELF_CHECK RAND:100,
    #  AFTER_TRAIN_RAPE :982 RAND:100 = 0, :995 RAND:100 = 99, 以降 0]
    st.rng = RecRng([7, 50, 99, 0, 99, 0, 99])
    assert run_gen(after.event_end(ctx)) == Step.TURNEND
    t = texts(ctx.out)
    assert c.cflag[286] == 1
    # DOUGA_RYUSUTU:1465–1477（ARG == 1）：CFLAG:284 += 4 + RAND:5
    assert "男たちは襲われたことを他言しなければ動画を公開しないと言っていたが、" in t
    assert c.cflag[284] == 4


# --- SELF_CHECK:77–178 -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "yokujo, yokubou, roshutsu, onani, inran, roll, expected",
    [
        (0, 5, 5, 5, 1, 99, 0),  # 欲情 0 → 0
        (20000, 3, 3, 0, 0, 50, 1),  # 15 × 1 × 1 × 1.00 = 15
        (20000, 3, 3, 0, 0, 30, 0),  # 15 × 0.90 = 13
        (20000, 3, 3, 0, 0, 70, 1),  # 15 × 1.10 = 16
        (3000, 0, 0, 5, 1, 99, 0),  # 10 × .25 = 2 × .25 = 0 → 0
        (3000, 4, 4, 1, 1, 50, 1),  # 10 × 1.25 = 12 × 1.25 = 15 × 1.25 = 18 × 2 = 36
        (1500, 5, 3, 0, 0, 90, 0),  # 8 × 1.5 = 12 × 1.20 = 14
    ],
)
def test_self_check(ctx, data, yokujo, yokubou, roshutsu, onani, inran, roll, expected):
    c = ctx.state.charas[1]
    c.palam[I(data, "PALAM", "欲情")] = yokujo
    c.abl[I(data, "ABL", "欲望")] = yokubou
    c.abl[I(data, "ABL", "露出癖")] = roshutsu
    c.abl[I(data, "ABL", "自慰中毒")] = onani
    c.talent[I(data, "TALENT", "淫乱")] = inran
    ctx.state.rng = RecRng([roll])
    assert self_kind.self_check(ctx, 1) == expected
    assert ctx.state.rng.calls == [100]


# --- SELF_N／B／A／V：PALAM_CAL に渡す値 -------------------------------------------------------------


@pytest.fixture
def cal(monkeypatch):
    got: list = []
    monkeypatch.setattr(palam, "palam_cal", as_generator(lambda ctx, *a, losebase=0: got.append((list(a), losebase))))
    return got


def _abl(c, data, kw: dict) -> None:
    for k, v in kw.items():
        c.abl[I(data, "ABL", k)] = v


@pytest.mark.parametrize(
    "func, abls, talents, up, lb, dexp",
    [
        # SELF_N :262–406：Ｃ2→2000、Ｂ1→400、非処女・女性 Ｖ3→4000、技巧 3 → ×1.25
        ("n", {"Ｃ感覚": 2, "Ｂ感覚": 1, "Ｖ感覚": 3, "技巧": 3, "露出癖": 1, "自慰中毒": 2}, {"処女": 0},
         [2500, 5000, 0, 500, 0, 0, 800, 2000, 100, 100, 0, 0], 150, {"自慰経験": 1, "Ｖ経験": 1}),
        ("n", {"Ｃ感覚": 5, "Ｂ感覚": 0, "Ｖ感覚": 3, "技巧": 1, "露出癖": 5, "自慰中毒": 0}, {"処女": 1},
         [20000, 0, 0, 200, 0, 0, 200, 0, 2000, 2000, 0, 0], 150, {"自慰経験": 1, "Ｖ経験": 0}),
        # SELF_B :421–525：Ｂ5→10000 × 2.00、恥情 100、欲情 0（自慰中毒 0）
        ("b", {"Ｂ感覚": 5, "技巧": 5, "露出癖": 0, "自慰中毒": 0}, {},
         [0, 0, 0, 20000, 0, 0, 200, 0, 50, 100, 0, 0], 100, {"自慰経験": 1}),
        # SELF_A :541–641：Ａ1 は代入なし、屈服・恥情 200（露出癖 1）
        ("a", {"Ａ感覚": 1, "技巧": 4, "露出癖": 1, "自慰中毒": 3}, {},
         [0, 0, 0, 0, 0, 0, 1000, 5000, 200, 200, 0, 0], 150, {"自慰経験": 1, "Ａ経験": 1}),
        ("a", {"Ａ感覚": 4, "技巧": 2, "露出癖": 4, "自慰中毒": 5}, {},
         [0, 0, 11000, 0, 0, 0, 4000, 20000, 2000, 2000, 0, 0], 150, {"自慰経験": 1, "Ａ経験": 1}),
        # SELF_V :656–811：処女 Ｖ3→2000（経験なし）
        ("v", {"Ｖ感覚": 3, "Ａ感覚": 3, "技巧": 0, "露出癖": 2, "自慰中毒": 1}, {"処女": 1, "淫尻": 0},
         [0, 2000, 0, 0, 0, 0, 400, 1000, 200, 200, 0, 0], 150, {"自慰経験": 1, "Ｖ経験": 0, "Ａ経験": 0}),
        # 淫尻：Ｖ3→3000、Ａ3→3000
        ("v", {"Ｖ感覚": 3, "Ａ感覚": 3, "技巧": 0, "露出癖": 2, "自慰中毒": 1}, {"処女": 0, "淫尻": 1},
         [0, 3000, 3000, 0, 0, 0, 400, 1000, 200, 200, 0, 0], 150, {"自慰経験": 1, "Ｖ経験": 1, "Ａ経験": 1}),
        ("v", {"Ｖ感覚": 3, "Ａ感覚": 3, "技巧": 3, "露出癖": 2, "自慰中毒": 1}, {"処女": 0, "淫尻": 0},
         [0, 5000, 0, 0, 0, 0, 400, 1000, 200, 200, 0, 0], 150, {"自慰経験": 1, "Ｖ経験": 1, "Ａ経験": 0}),
    ],
)
def test_self_parts(ctx, data, cal, func, abls, talents, up, lb, dexp):
    st = ctx.state
    c = st.charas[1]
    _abl(c, data, abls)
    for k, v in talents.items():
        c.talent[I(data, "TALENT", k)] = v
    e0 = {k: c.exp[I(data, "EXP", k)] for k in dexp}
    st.rng = RecRng([])
    run_no_input(getattr(self_kind, f"self_{func}")(ctx, 1, 0))
    assert cal == [(up, lb)]
    assert {k: c.exp[I(data, "EXP", k)] - e0[k] for k in dexp} == dexp
    assert texts(ctx.out)[0] == f"〈地の文：MESSAGE_SELF_{func.upper()}〉"


# --- SELF_KIND:182–247 の分岐 ------------------------------------------------------------------------


@pytest.fixture
def kinds(monkeypatch):
    got: list = []
    for k in "nbav":
        monkeypatch.setattr(self_kind, f"self_{k}", as_generator(lambda ctx, a, a1, k=k: got.append(k.upper())))
    return got


@pytest.mark.parametrize(
    "abls, talents, rolls, calls, expected",
    [
        ({}, {}, [49], [100], ["N"]),  # :211–217 Ｖ自慰可・Ａ自慰可 0
        ({}, {}, [50], [100], ["B"]),
        ({"Ｖ感覚": 1}, {}, [32], [99], ["N"]),  # :218–226
        ({"Ｖ感覚": 1}, {}, [33], [99], ["V"]),
        ({"Ｖ感覚": 1}, {"オトコ": 1}, [33], [99], ["B"]),  # ISFEMALE 偽 → ELSE
        ({"Ｖ感覚": 1}, {}, [66], [99], ["B"]),
        ({"Ａ感覚": 2}, {}, [65], [99], ["B"]),  # :227–235
        ({"Ａ感覚": 2}, {}, [66], [99], ["A"]),
        ({"Ａ感覚": 2, "Ｖ感覚": 1}, {}, [70], [99], ["B"]),  # :236 は到達しない（Ｖ自慰可 == 1 が先）
        ({}, {"淫壷": 1}, [0, 0], [3, 100], ["V", "N"]),  # :192–193
        ({}, {"淫壷": 1, "オトコ": 1}, [0, 0], [3, 100], ["N"]),  # ISFEMALE 偽 → 次の ELSEIF（淫尻 0 なので RAND なし）
        ({}, {"淫壷": 1, "淫尻": 1}, [1, 0, 99], [3, 3, 100], ["A", "B"]),
        ({}, {"淫乳": 1, "淫核": 1}, [1, 0, 0], [3, 3, 100], ["N", "N"]),
    ],
)
def test_self_kind_branch(ctx, data, kinds, abls, talents, rolls, calls, expected):
    c = ctx.state.charas[1]
    _abl(c, data, abls)
    for k, v in talents.items():
        c.talent[I(data, "TALENT", k)] = v
    ctx.state.rng = RecRng(rolls)
    run_no_input(self_kind.self_kind(ctx, 1, 0))
    assert kinds == expected
    assert ctx.state.rng.calls == calls


def test_self_kind_static_flag(ctx, data, kinds):
    """`#DIM Ｖ自慰可` は静的：一度 1 になると Ｖ感覚 0 のキャラでも :218 の分岐（RAND:99）。"""
    st = ctx.state
    st.charas[1].abl[I(data, "ABL", "Ｖ感覚")] = 1
    st.rng = RecRng([0])
    run_no_input(self_kind.self_kind(ctx, 1, 0))
    st.charas[1].abl[I(data, "ABL", "Ｖ感覚")] = 0
    st.rng = RecRng([40])
    run_no_input(self_kind.self_kind(ctx, 1, 0))
    assert st.rng.calls == [99]
    assert kinds == ["N", "V"]
    # 読込（新しい GameState）では 0 に戻る（VariableData.cs@SetDefaultLocalValue:514–520）
    assert _state(data).temp.locals.get(("SELF_KIND#Ｖ自慰可", 0), 0) == 0


# --- 呼び出し点の統合 --------------------------------------------------------------------------------


def test_forced_masturbation_spcom6(cctx, data):
    """SEX_SPCOM6:45 `CALL SELF_KIND, TARGET, 0`（戦闘中の強制自慰）。"""
    st = cctx.state
    c = st.charas[1]
    st.savestr[13] = "BOSS"
    st.flag[11] = 3
    st.rng = GameRng(3)
    e0 = c.exp[I(data, "EXP", "自慰経験")]
    run_no_input(sexcom.sex_spcom6(cctx))
    t = texts(cctx.out)
    assert c.exp[I(data, "EXP", "自慰経験")] == e0 + 1
    assert "強制自慰" in t
    assert t.index("強制自慰") < max(t.index(x) for x in ("自慰", "胸自慰") if x in t)
    assert st.tflag[20] == 1006


def test_battle_end_masturbation(cctx, data):
    """SUBEVENT_BATTLEEND:12–13 → SELF_BATTLEEND:65–72（MESSAGE_SELF_BATTLEEND → SELF_KIND, ARG, 1 → _ABLUP 0）。"""
    st = cctx.state
    c = st.charas[1]
    st.tflag[98] = 1
    c.palam[I(data, "PALAM", "欲情")] = 300000  # 30
    _abl(c, data, {"欲望": 3, "露出癖": 3})
    e0 = c.exp[I(data, "EXP", "自慰経験")]
    st.rng = RecRng([50, 0])  # SELF_CHECK RAND:100、SELF_KIND :212 RAND:100 = 0 → SELF_N
    run_no_input(after.subevent_battleend(cctx))
    t = texts(cctx.out)
    assert "戦闘後自慰（紅葉）" in t
    assert "自慰" in t
    assert c.exp[I(data, "EXP", "自慰経験")] == e0 + 1


def test_battle_end_no_masturbation_on_defeat(ctx):
    st = ctx.state
    st.tflag[98] = 2  # SUBEVENT_BATTLEEND:12 TFLAG:98 == 0 || 1 のときだけ
    st.rng = RecRng([])
    run_no_input(after.subevent_battleend(ctx))
    assert st.rng.calls == []


def test_night_masturbation(cctx, data):
    """SHOP_TURNEND:116 → SELF_NIGHT:5–61：対象 2 人、DRAWLINE は最初の 1 人の前だけ、VARSET PALAM。"""
    st = cctx.state
    st.time = 1
    for i in (1, 2):
        c = st.charas[i]
        _abl(c, data, {"自慰中毒": 5})  # :34–48 LOCAL:1 = 35
        c.palam[I(data, "PALAM", "欲情")] = 1234
    others = [i for i in range(3, st.charanum) if st.charas[i].cflag[999]]
    for i in others:
        st.charas[i].cflag[999] = 0
    st.charas[1].talent[I(data, "TALENT", "交際相手")] = 0
    st.charas[2].talent[I(data, "TALENT", "交際相手")] = 0
    before = st.target
    st.rng = RecRng([34, 0, 34, 0])  # 各キャラ :49 RAND:100 < 35、SELF_KIND :212 RAND:100 < 50 → SELF_N
    run_no_input(turnend.self_night(cctx))
    t = texts(cctx.out)
    assert "夜間自慰（紅葉）" in t
    assert sum(1 for x in t if x.startswith("夜間自慰（")) == 2
    assert sum(1 for ln in cctx.out.lines if ln.kind == "drawline") == 1
    for i in (1, 2):
        assert st.charas[i].palam[I(data, "PALAM", "欲情")] == 0  # :57 VARSET PALAM
    assert st.target == before  # :61
