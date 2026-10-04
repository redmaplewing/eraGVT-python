"""S49 預期由 WEAPON_CUSTOMIZE.ERB@SETTING_FSTYLE:209–259 推導。"""

import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first
from eragvt.state import GameState, GameRng
from eragvt.text import TextOutput, NullNarrationService
from eragvt.game import weapon_customize as wc


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    st = GameState.new(data, GameRng(3))
    event_first(st, data)
    return Ctx(st, data, TextOutput(), NullNarrationService())


def drive(g, values):
    next(g)
    for value in values:
        try:
            g.send(value)
        except StopIteration as e:
            return e.value
    raise AssertionError("仍等待輸入")


@pytest.mark.parametrize("dist", [1, 2, 3])
@pytest.mark.parametrize("style", range(11))
def test_styles(ctx, dist, style):
    money = ctx.state.money
    drive(wc.setting_fstyle(ctx, 1, dist), [-1, 11, 998, style])
    assert ctx.state.charas[1].cdflag[dist, 500] == style
    assert ctx.state.money == money
    assert ctx.state.result[0] == 0  # RETURN 無引數


@pytest.mark.parametrize("dist", [1, 2, 3])
def test_manual_and_delete(ctx, dist):
    drive(wc.setting_weapon_name(ctx, 1, dist), [0, "星劍", 999])
    assert ctx.state.charas[1].cstr[dist + 4] == "星劍"
    drive(wc.setting_weapon_name(ctx, 1, dist), [3, "", 999])
    assert ctx.state.charas[1].cstr[dist + 4] == ""


@pytest.mark.parametrize(
    "dist,source", [(a, b) for a in range(1, 4) for b in range(1, 4) if a != b]
)
def test_copy_metadata(ctx, dist, source):
    # WEAPON_CUSTOMIZE.ERB:166–193：名稱與元位置一起複製並直接返回。
    c = ctx.state.charas[1]
    c.cstr[source + 4] = "名字"
    c.cdflag[source, 300] = 204
    drive(wc.setting_weapon_name(ctx, 1, dist), [source + 3])
    assert (c.cstr[dist + 4], c.cdflag[dist, 300]) == ("名字", 204)


@pytest.mark.parametrize("value", ["", "  星  ", "<script>"])
def test_input_exact_and_result_residue(ctx, value):
    ctx.state.result[1] = 77
    ctx.state.results[1] = "保留"
    drive(wc.setting_weapon_name(ctx, 1, 1), [0, value, 999])
    assert ctx.state.charas[1].cstr[5] == value
    assert (
        ctx.state.result[0],
        ctx.state.result[1],
        ctx.state.results[0],
        ctx.state.results[1],
    ) == (0, 77, value, "保留")


def test_random_cancel_clears_metadata(ctx):
    c = ctx.state.charas[1]
    c.cstr[5] = "名字"
    c.cdflag[1, 300] = 204
    drive(wc.setting_weapon_name(ctx, 1, 1), [1, 999, 999])
    assert (c.cstr[5], c.cdflag[1, 300]) == ("名字", 0)


def test_generator_keep_static_and_empty_selection(ctx, monkeypatch):
    # WEAPON_NAME.ERB:120–149、126–144：保留10格，溢出左移；空格50也可選。
    def gen(ctx):
        ctx.state.results[0] = "星"
        ctx.state.result[0] = 0

    monkeypatch.setattr(wc.weapon_words, "kana", gen)
    assert drive(wc.generate_names(ctx), [50, ""]) == 1
    assert ctx.state.results[0] == ""
    assert drive(wc.generate_names(ctx), [300] * 11 + [60, 50, ""]) == 1
    assert ctx.state.results[0] == "星"
    assert ctx.state.temp.locals["GENERATE_WEAPON_STRS:KEEP_VAR", 0] == 9
    assert drive(wc.generate_names(ctx), [50, ""]) == 1
    assert ctx.state.results[0] == "星"


def test_generator_modes_and_result_clear(ctx, monkeypatch):
    calls = []

    def kana(ctx):
        calls.append("k")
        ctx.state.results[0] = "カナ"

    def jp(ctx):
        calls.append("j")
        ctx.state.results[0] = "和名"
        ctx.state.results[1] = "よみ"

    monkeypatch.setattr(wc.weapon_words, "kana", kana)
    monkeypatch.setattr(wc.weapon_words, "japanese", jp)
    drive(wc.generate_names(ctx, 3), [120, 0, ""])
    assert calls == ["k"] * 3 + ["j"] * 3
    assert ctx.state.results[0] == "和名 <よみ>"
    calls.clear()
    ctx.state.results[9] = "殘值"
    drive(wc.generate_names(ctx, 3), [120, 110, 130, 999])
    assert calls[:9] == ["k"] * 3 + ["j"] * 3 + ["k"] * 3
    assert ctx.state.results[9] == "" and ctx.state.results[0] == ""


@pytest.mark.parametrize(
    "commands,expected,code",
    [
        ([100, 110], "星 <ほし>", 9),
        ([1, 100, 110], "星", 2),
        ([11, 21, 31, 100, 110], '炎剣 "星 <ほし>"', 609),
        ([12, 100, 110], "星 <ほし>の炎剣", 9),
        ([11, 23, 32, 1, 100, 110], "炎剣・「星」", 802),
    ],
)
def test_add_format(ctx, monkeypatch, commands, expected, code):
    # WEAPON_NAME.ERB@WEAPON_ADD_STRS:487–499：STRLENS 使用CP932，元位置=前綴長*100+主體長。
    ctx.state.charas[1].cstr[5] = "星 <ほし>"
    monkeypatch.setattr(wc.weapon_words, "addition", lambda *args: "炎剣")
    assert drive(wc.add_strings(ctx, 1, 1), commands) == code
    assert ctx.state.results[0] == expected


@pytest.mark.parametrize(
    "kind,attack",
    list(
        enumerate([0, 1, 1, 4, 3, 2, 6, 3, 2, 18, 17, 2, 1, 1, 6, 8, 8, 10, 16, 16, 0])
    ),
)
def test_weapon_kind_defaults(ctx, monkeypatch, kind, attack):
    calls = []

    def addition(*args):
        calls.append(args[1:])
        return "炎剣"

    monkeypatch.setattr(wc.weapon_words, "addition", addition)
    c = ctx.state.charas[1]
    c.cstr[5] = "星"
    c.cdflag[1, 500] = 10
    commands = [11, 40 + 3, 50 + kind] + (["錨"] if kind == 20 else []) + [100, 110]
    drive(wc.add_strings(ctx, 1, 1), commands)
    assert calls == [(10, 1, 3, kind, attack, "錨" if kind == 20 else "")] * 10


def test_add_cancel_reset_and_reentry(ctx, monkeypatch):
    c = ctx.state.charas[1]
    c.cstr[5] = "炎剣「星」"
    c.cdflag[1, 300] = 602
    monkeypatch.setattr(wc.weapon_words, "addition", lambda *args: "炎剣")
    assert drive(wc.add_strings(ctx, 1, 1), [11, 999]) == 0
    assert c.cstr[5] == "炎剣「星」" and c.cdflag[1, 300] == 602
    assert drive(wc.add_strings(ctx, 1, 1), [200, 100, 110]) == 2
    assert ctx.state.results[0] == "星"


@pytest.mark.parametrize("state,battle", [(0, 0), (1, 0), (0, 1)])
def test_entry_gate(ctx, state, battle):
    from eragvt.game.status_screen import _cmd_page3, _Screen

    ctx.state.charas[1].cflag[0] = state
    ctx.state.flag[700] = battle
    g = _cmd_page3(ctx, 1, 0, _Screen(0))
    if state or battle:
        with pytest.raises(StopIteration) as e:
            next(g)
        assert e.value.value == 0
    else:
        assert drive(g, [999]) == 1


@pytest.mark.parametrize(
    "style,normal,making",
    [
        (0, 100, 110),
        (1, 85, 93),
        (2, 125, 137),
        (3, 180, 197),
        (4, 150, 165),
        (5, 115, 126),
        (6, 150, 165),
        (7, 175, 192),
        (8, 170, 187),
        (9, 105, 115),
        (10, 170, 187),
    ],
)
def test_battle_vs_customize_bonus(ctx, style, normal, making):
    from eragvt.game.battle.hantei import fstyle_attack

    # FIGHT_STYLE.ERB:47–111，分量100/200/300/400；未結算10/20/30/40。
    c = ctx.state.charas[1]
    ctx.state.target = 1
    c.cflag[0] = 0
    for name in ("小柄", "長身"):
        c.talent[ctx.data.index_of("TALENT", name)] = 0
    for i in range(4):
        c.maxbase[10 + i] = (i + 1) * 100
        c.cflag[53 + i] = (i + 1) * 10
    c.cdflag[1, 500] = style
    c.tcvarn[0] = 0
    assert fstyle_attack(ctx, 1, 1) == normal
    assert fstyle_attack(ctx, 1, 1, 1) == making


def test_web_and_save(data, tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app

    app = create_app(data, tmp_path, narration=None)
    client = TestClient(app)

    def send(v):
        return client.post("/api/input", json={"value": v}).json()

    for v in (0, 0, 1, 1, 110, 3000, 0):
        send(v)
    assert "ＷＥＡＰＯＮ" in client.get("/").text
    for v in (10, 0, "<星>", 999, 12, 10, 999):
        send(v)
    assert "&lt;星&gt;" in client.get("/").text
    for v in (999, 200, 0, 300, 0):
        send(v)
    c = app.state.session.state.charas[1]
    assert (c.cstr[5], c.cdflag[1, 500]) == ("<星>", 10)


@pytest.mark.parametrize(
    "text,start,length,expected",
    [
        ("a星b", 1, 1, "星"),
        ("a星b", 2, 1, "b"),
        ("a星b", 0, 2, "a星"),
        ("星月", -1, 1, "星"),
        ("星月", 0, 0, ""),
        ("星月", 9, 2, ""),
        ("星月", 0, -1, "星月"),
        ("😀星", 0, 2, "😀"),
        ("😀星", 2, 1, "星"),
        ("😀星", 1, 1, "\ude00"),
    ],
)
def test_substring_cp932_utf16(text, start, length, expected):
    # LangManager.cs:40–85；遇半個全形 byte 向右取整，UTF-16 代理字元分別計數。
    assert wc._substring(text, start, length) == expected


def test_surrogate_count_and_split_capacity(ctx, monkeypatch):
    ctx.state.charas[1].cstr[5] = "😀 <a> <b>"
    monkeypatch.setattr(wc.weapon_words, "addition", lambda *args: "炎剣")
    g = wc.add_strings(ctx, 1, 1)
    next(g)
    assert ctx.state.result[0] == 3  # SPLIT:完整筆數，僅前兩格寫入 OR_STR。
    g.send(100)
    with pytest.raises(StopIteration) as e:
        g.send(110)
    assert e.value.value == 6
    assert ctx.state.results[0] == "😀 <a>"


class ZeroRng:
    def __init__(self):
        self.bounds = []

    def rand(self, n):
        self.bounds.append(n)
        return 0


def test_kana_rng_order(ctx, monkeypatch):
    from eragvt.game import weapon_words as words

    # 原作 :38 兩音，語尾→語頭，選中後仍遍歷表；:2028 每次先 RAND:5。
    monkeypatch.setattr(words, "KANA", [(1, ["ア"], 0, False), (4, ["ル"], 0, False)])
    ctx.state.rng = ZeroRng()
    assert words.kana(ctx) == "アル"
    assert ctx.state.rng.bounds == [2, 1, 5, 2, 5]
    assert ctx.state.result[0] == 0


def test_japanese_rng_order(ctx, monkeypatch):
    from eragvt.game import weapon_words as words

    # 原作 :93 先從語頭開始，兩語不同類別，音讀＋音讀。
    monkeypatch.setattr(
        words,
        "JAPANESE",
        [
            (1, 0, 0, ["星"], [""], ["せい"], 513),
            (2, 0, 0, ["炎"], [""], ["えん"], 2049),
        ],
    )
    ctx.state.rng = ZeroRng()
    assert words.japanese(ctx) == "星炎"
    assert ctx.state.results[1] == "せいえん"
    assert ctx.state.rng.bounds == [2, 2, 1]


@pytest.mark.parametrize(
    "name,now,expected",
    [
        ("狐", 1, ("狐", "きつね", "こ")),
        ("獅子", 1, ("獅子", "", "しし")),
        ("竜", 0, ("竜", "たつ", "りゅう")),
        ("月", 1, ("月", "つき", "げつ")),
        ("雨", 1, ("雨", "あめ", "う")),
        ("氷", 0, ("氷", "こおり", "ひょう")),
        ("火", 1, ("火", "ひ", "か")),
        ("一", 1, ("一ツ", "ひとつ", "")),
        ("六", 0, ("六ツ", "むつ", "")),
        ("七", 1, ("七", "なな", "しち")),
        ("九", 1, ("九", "ここの", "")),
        ("天", 1, ("天", "", "てん")),
        ("詩", 0, ("詩", "うた", "")),
        ("鉄", 0, ("鉄", "くろがね", "てつ")),
        ("神", 0, ("神", "かみ", "しん")),
        ("巫", 0, ("覡", "かんなぎ", "")),
        ("終", 0, ("終ノ", "ついの", "")),
        ("飛", 1, ("飛", "とび", "ひ")),
        ("流", 0, ("流", "ながれ", "る")),
    ],
)
def test_japanese_word_variants(name, now, expected):
    from eragvt.game import weapon_words as words

    row = next(row for row in words.JAPANESE if row[3][0] == name)
    assert words._jp_forms(row, now, lambda n: 0) == expected


@pytest.mark.parametrize("seed", range(5))
def test_generation_seed_reproducible(ctx, seed):
    from eragvt.game import weapon_words as words
    from eragvt.state import GameRng

    ctx.state.rng = GameRng(seed)
    first = [
        words.kana(ctx),
        words.japanese(ctx),
        words.addition(ctx, 10, 1, 3, 20, 31, "錨"),
    ]
    ctx.state.temp.locals.clear()
    ctx.state.rng = GameRng(seed)
    second = [
        words.kana(ctx),
        words.japanese(ctx),
        words.addition(ctx, 10, 1, 3, 20, 31, "錨"),
    ]
    assert first == second and all(first)


def test_addition_duplicate_retry_rng_order(ctx, monkeypatch):
    from eragvt.game import weapon_words as words

    # GENERATE_ADD_STR.ERB@GENERATE_ADD_STR:169–190：空詞群零項，計數=1+全般1+武器1=3。
    # :219–229 先抽全般（RAND:(3-1+16)）；:330–362 重複時重試。
    # 第一次尾字又選「炎」而重試，再跳過全般、選無指定武器「器」（RAND:1）。
    table = {i: [] for i in range(55)}
    table[51] = ["炎"]
    table[30] = ["器"]
    monkeypatch.setattr(words, "ADD_WORDS", table)

    class Rng:
        def __init__(self):
            self.values = iter([0, 0, 0, 0, 1, 0])
            self.bounds = []

        def rand(self, n):
            self.bounds.append(n)
            value = next(self.values)
            assert 0 <= value < n
            return value

    ctx.state.rng = Rng()
    assert words.addition(ctx, 0, 1, 0, 0, 0, "") == "炎器"
    assert ctx.state.rng.bounds == [4, 2, 18, 18, 18, 1]
    assert ctx.state.result[0] == 0


def test_addition_clearline_boundaries(ctx, monkeypatch):
    # WEAPON_NAME.ERB@WEAPON_ADD_STRS:447、515：設定27行，生成15行，換設定清42行。
    ctx.state.charas[1].cstr[5] = "星"
    monkeypatch.setattr(wc.weapon_words, "addition", lambda *args: "炎剣")
    ctx.out.printl("前一畫面")
    g = wc.add_strings(ctx, 1, 1)
    next(g)
    initial = len(ctx.out.lines)
    g.send(11)
    assert len(ctx.out.lines) == initial
    g.send(100)
    assert len(ctx.out.lines) == initial + 15
    g.send(200)
    assert len(ctx.out.lines) == initial
