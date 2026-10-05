"""S35：預期由 FIRSTSETTING_CHARA_TRANSFORMATION／RANDOMNAMING 原文推導。"""
import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import child, firstsetting
from eragvt.game.action import Ctx
from eragvt.game.opening import event_first
from eragvt.state import GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    st = GameState.new(data, GameRng(3))
    event_first(st, data)
    return Ctx(st, data, TextOutput(), NullNarrationService())


@pytest.mark.parametrize("old,value,expected", [("舊名", "999", "舊名"), ("", "999", "999"),
                                                ("舊名", "  星光  ", "  星光  ")])
def test_manual_trans_name(ctx, old, value, expected):
    # @FIRSTSETTING_CHARA_TRANSAFTERNAME:101–118；INPUTS 不 trim、不改 RESULT。
    c = ctx.state.charas[1]
    c.cstr[0] = old
    ctx.state.result[2] = 73
    ctx.state.results[2] = "殘值"
    g = firstsetting.trans_after_name(ctx, 1)
    next(g)
    request = g.send(1)
    assert request is not None
    assert g.send("") is not None
    with pytest.raises(StopIteration):
        g.send(value)
    assert (c.cstr[0], c.cstr[1], c.cflag[2], c.cflag[3]) == (expected, expected, 1, 1)
    assert ctx.state.result[0] == 0 and ctx.state.result[2] == 73
    assert ctx.state.results[0] == value and ctx.state.results[2] == "殘值"


@pytest.mark.parametrize("add", [False, True])
def test_child_manual_empty_and_spaces(ctx, add):
    # PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:419–429／@BIRTH_DAUGHTER_TENTACLE_ORIGIN:235–245
    g = child._ask_random_name(ctx, add, None)
    next(g)
    assert g.send(1) is not None
    assert g.send("") is not None
    with pytest.raises(StopIteration) as e:
        g.send("  小星  ")
    assert e.value.value == "  小星  "
    assert ctx.state.results[0] == "  小星  "


def test_random_all_cancel(ctx):
    # @FIRSTSETTING_CHARA_TRANSAFTERNAME:120–124：RETURN（非 RETURN 99），清201/202但不改舊名。
    c = ctx.state.charas[1]
    c.cstr[0], c.cstr[201], c.cstr[202] = "舊名", "上", "下"
    g = firstsetting.trans_after_name(ctx, 1)
    next(g)
    g.send(2)
    g.send(100)
    with pytest.raises(StopIteration):
        g.send(99)
    assert c.cstr[0] == "舊名" and c.cstr[201] == c.cstr[202] == ""
    assert ctx.state.result[0] == 0


def test_combination_genre_cancel_keeps_results(ctx):
    # :144–166：genre99回傳99,0；呼叫端仍確認空RESULTS，不替玩家取消。
    c = ctx.state.charas[1]
    g = firstsetting.trans_after_name(ctx, 1)
    next(g)
    g.send(3)
    g.send(99)
    with pytest.raises(StopIteration):
        g.send(1)
    assert c.cstr[0] == "" and c.cflag[2] == c.cflag[3] == 1
    assert ctx.state.result[1] == 0


class TraceRng:
    def __init__(self, values=()):
        self.values = iter(values)
        self.calls = []

    def rand(self, n):
        self.calls.append(n)
        return next(self.values, 0) % n


def drive(g, values):
    next(g)
    for value in values:
        try:
            g.send(value)
        except StopIteration as stop:
            return stop.value
    raise AssertionError("輸入後仍未結束")


@pytest.mark.parametrize("genre", range(9))
def test_genre_rng_retry(ctx, monkeypatch, genre):
    from eragvt.game.naming import _draw
    # ALL:154–214：random genre只抽一次，空字串只重抽50格詞。
    chosen = 3 if genre == 8 else genre
    base = 500 + chosen * 100
    monkeypatch.setattr(ctx.data, "str_defaults", {base + 2: "詞"})
    rng = TraceRng(([3] if genre == 8 else []) + [1, 2])
    ctx.state.rng = rng
    assert _draw(ctx, genre) == base + 2
    assert rng.calls == ([8] if genre == 8 else []) + [50, 50]


def test_all_keep_reverse_regenerate_static_and_save(ctx, monkeypatch):
    import json
    from eragvt.game.naming import random_naming_all
    from eragvt.state.savefile import dump_save, load_save
    # ALL:129–145先列後上下句；:246–272 keep列不反轉/不重抽；static跨呼叫。
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "上", 600: "下"})
    ctx.state.rng = rng = TraceRng([0, 0, 1, 0] * 20)
    g = random_naming_all(ctx)
    next(g)
    assert len(rng.calls) == 80
    assert ctx.state.da[0, 0] == 500 and ctx.state.da[1, 0] == 600
    g.send(1000)
    g.send(300)
    assert ctx.state.da[0, 0] == 500 and ctx.state.da[1, 0] == 600
    assert ctx.state.da[0, 1] == 600 and ctx.state.da[1, 1] == 500
    g.send(200)
    assert len(rng.calls) == 80 + 19 * 4
    with pytest.raises(StopIteration):
        g.send(0)
    next_g = random_naming_all(ctx)
    next(next_g)
    assert len(rng.calls) == 80 + 19 * 8
    next_g.close()
    raw = dump_save(ctx.state)
    loaded, _ = load_save(raw)
    assert loaded.da == ctx.state.da
    assert not loaded.temp.locals  # static #DIM 不存檔
    assert loaded.results[0] == ""
    obj = json.loads(raw)
    assert obj["version"] == 3
    obj["version"] = 2
    del obj["state"]["da"]
    assert len(load_save(json.dumps(obj).encode())[0].da) == 0


@pytest.mark.parametrize("side,command", [(0, 2000), (1, 3000)])
def test_all_fixed_persists(ctx, monkeypatch, side, command):
    from eragvt.game.naming import random_naming_all
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "上", 600: "下"})
    ctx.state.rng = rng = TraceRng([0, 0, 1, 0] * 20)
    g = random_naming_all(ctx)
    next(g)
    selected = ctx.state.da[side, 0]
    g.send(command)
    assert all(ctx.state.da[side, i] == selected for i in range(20))
    assert len(rng.calls) == 80 + 40  # 固定的那半不抽亂數
    with pytest.raises(StopIteration):
        g.send(0)
    g = random_naming_all(ctx)
    next(g)
    assert len(rng.calls) == 160  # 固定編號static，入口不清
    g.close()


def test_all_genres_and_hidden_invalid_inputs(ctx, monkeypatch):
    from eragvt.game.naming import random_naming_all
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "上", 600: "下"})
    ctx.state.rng = rng = TraceRng()
    g = random_naming_all(ctx)
    next(g)
    g.send(99)  # 候選畫面99無效，只ジャンル畫面接受
    assert len(rng.calls) == 80
    g.send(100)
    g.send(0)
    g.send(100)
    g.send(1)
    g.send(200)
    assert all(ctx.state.da[0, i] == 500 and ctx.state.da[1, i] == 600 for i in range(20))
    assert len(rng.calls) == 120  # 指定genre不抽RAND8
    g.close()


def test_all_display_width_and_trailing_spaces(ctx, monkeypatch):
    from eragvt.game.naming import random_naming_all
    # RANDOMNAMING_ALL:214–232：CP932「上」2bytes，合計26欄，再全形空白。
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "上", 600: "下"})
    ctx.state.rng = TraceRng([0, 0, 1, 0] * 20)
    g = random_naming_all(ctx)
    next(g)
    row = next(line.text for line in ctx.out.lines if line.text.startswith("[ 0]"))
    assert row == "[ 0] 上下" + " " * 22 + "　[1000] ☆キープ 　[2000] 上の句統一 　[3000] 下の句統一 "
    g.close()


@pytest.mark.parametrize("command,prefix,expected", [(800, "名", "名詞"), (801, "名", "詞名"), (801, "", "詞")])
def test_single_order_and_result_tail(ctx, monkeypatch, command, prefix, expected):
    from eragvt.game.naming import random_naming
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "詞"})
    ctx.state.rng = rng = TraceRng()
    ctx.state.result[2] = 81
    drive(random_naming(ctx, 1, prefix), [0, command, 0])
    assert ctx.state.results[0] == expected and ctx.state.charas[1].cstr[202] == "詞"
    assert [ctx.state.result[i] for i in range(3)] == [0, 0, 81]
    assert rng.calls == [50] * 20


def test_single_order_survives_genre_reselect_and_second_call(ctx, monkeypatch):
    from eragvt.game.naming import random_naming
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "詞"})
    ctx.state.rng = TraceRng()
    drive(random_naming(ctx, 1, "甲"), [0, 801, 100])
    assert ctx.state.result[1] == 1
    drive(random_naming(ctx, 1, "乙"), [0, 0])
    assert ctx.state.results[0] == "詞乙"  # LOCAL:21未初始化，保留801設定


def test_combination_reject_restore_old_parts(ctx, monkeypatch):
    # TRANSAFTERNAME:155–158：拒絕後恢復舊parts；再選只寫202，201仍是舊值。
    c = ctx.state.charas[1]
    c.cstr[201], c.cstr[202] = "舊上", "舊下"
    monkeypatch.setattr(ctx.data, "str_defaults", {500: "詞"})
    ctx.state.rng = TraceRng()
    drive(firstsetting.trans_after_name(ctx, 1), [3, 0, 0, 0, 0, 0, 1])
    assert c.cstr[201] == "舊上" and c.cstr[202] == "詞"
    assert c.cstr[0] == c.callname + "詞"


@pytest.mark.parametrize("parts,old", [(False, ""), (False, "舊稱"), (True, "舊稱")])
def test_callname_999_always_keeps_old(ctx, parts, old):
    c = ctx.state.charas[1]
    c.cstr[1] = old
    c.cstr[201] = "上" if parts else ""
    drive(firstsetting.trans_after_callname(ctx, 1), [2 if parts else 0, "", "999"])
    assert c.cstr[1] == old
    assert ctx.state.result[0] == 0


@pytest.mark.parametrize("function,choice,slot", [("chara_callname", 1, None), ("trans_call", 2, 2), ("nanori", 1, 3)])
def test_related_manual_fields(ctx, function, choice, slot):
    c = ctx.state.charas[1]
    c.cflag[2] = 0
    drive(getattr(firstsetting, function)(ctx, 1), [choice, "", " 星光 "])
    assert (c.callname if slot is None else c.cstr[slot]) == " 星光 "


def test_web_text_wait_save_and_escape(data, tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app = create_app(data, tmp_path, narration=None)
    client = TestClient(app)
    for v in (0, 0, 1000, 1):
        client.post("/api/input", json={"value": v})
    session = app.state.session
    session._run_gen(firstsetting.trans_after_name(session._ctx(), 1), session._show_shop)
    response = client.post("/api/input", json={"value": 1}).json()
    assert response["input_kind"] == "text"
    assert 'type="text" name="value"' in client.get("/").text
    assert client.post("/api/input", json={"value": ""}).json()["input_kind"] == "text"
    client.post("/input", data={"value": "  <星光>  "})
    assert session.state.charas[1].cstr[0] == "  <星光>  "

    assert session.input_kind == "number"
    assert "&lt;星光&gt;" in client.get("/").text
    for v in (200, 0, 300, 0):
        client.post("/api/input", json={"value": v})
    assert session.state.charas[1].cstr[0] == "  <星光>  "


def test_catalog_text_marker_uses_existing_nested_channel(ctx, tmp_path):
    from eragvt.game.input_request import TextInputRequest
    from eragvt.narration.service import CatalogNarrationService
    # 最小INPUTS fixture只測引擎通道，不新增原作遊戲內容。
    (tmp_path / "input.ERB").write_text("@TEST_PARENT\nCALL TEST_CHILD\n@TEST_CHILD\nINPUTS\n", encoding="utf-8", newline="\n")
    service = CatalogNarrationService(tmp_path, ctx.data)
    ctx.state.result[0] = 73
    for run in (service.run_event_gen, service.run_function_gen):
        g = run(ctx, "TEST_PARENT")
        assert isinstance(next(g), TextInputRequest)
        with pytest.raises(StopIteration) as stop:
            g.send("  名稱  ")
        assert stop.value.value is True
        assert ctx.state.results[0] == "  名稱  "
        assert service.failures == []


@pytest.mark.parametrize("via_form", [False, True])
def test_web_real_status_entry_numeric_name(data, tmp_path, via_form):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app = create_app(data, tmp_path, narration=None)
    client = TestClient(app)
    def send(v):
        return client.post("/input", data={"value": str(v)}) if via_form else client.post("/api/input", json={"value": v})
    for v in (0, 0, 1000, 1):
        send(v)
    session = app.state.session
    session.state.charas[1].talent[data.index_of("TALENT", "変身能力")] = 1
    for v in (1, 110, 13, 0, 1):
        send(v)
    assert session.input_kind == "text"
    send("")
    assert session.input_kind == "text"
    send("0007")
    assert session.state.charas[1].cstr[0] == "0007"
    assert session.input_kind == "number"
    send("99")  # 數字選單依舊轉int，離開變身名子畫面
    assert session.phase.value != "halted"
