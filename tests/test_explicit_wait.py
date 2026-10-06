"""S85 中性契約：引擎 EmueraConsole.cs:497–508、707–734；原文等待先於寫入。"""
import pytest
from fastapi.testclient import TestClient
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.achievements import unlock
from eragvt.game.action import Ctx
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import GameState, GameRng
from eragvt.web import create_app
from tools.sim_adult import adult_data


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def app(data, tmp_path):
    app = create_app(data, tmp_path / "save", narration=None)
    s = app.state.session
    s.state = GameState.new(data, GameRng(85))
    s.out.drain()
    s.state.result[0], s.state.result[1] = 73, 74
    s.state.results[0], s.state.results[1] = "保留", "其他"
    yield app
    app.state.session.close()


def test_achievement_wait_preserves_results_rng_and_historical_labels(app):
    # SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:15–19：確認後保存；函式流落才寫 RESULT:0=0。
    s = app.state.session
    st = s.state
    rng = st.rng.snapshot()
    def flow():
        s.out.printl("[42]舊戰鬥按鈕")
        unlock(s._ctx(), 220, "中性成就")
        s.out.printl("[7]下一個數字選項")
        yield
    s._run_gen(flow(), s.begin_title)
    with TestClient(app) as client:
        html = client.get("/").text
        assert s.input_kind == "wait"
        assert "舊戰鬥按鈕" in html and 'class="btn"' not in html
        assert 'id="continue"' in html and 'id="value"' not in html
        assert st.result[0] == 73 and st.result[1] == 74
        assert st.results[0] == "保留" and st.results[1] == "其他"
        assert st.rng.snapshot() == rng
        assert s.globals.mem.global_[220] == 0 and not s.globals.exists()
        token = client.get("/api/screen").json()["input_token"]
        client.post("/input", data={"value": "", "input_token": token})
        assert s.input_kind == "number" and s.globals.mem.global_[220] == 1
        assert st.result[0] == 0 and st.result[1] == 74
        assert st.results[0] == "保留" and st.results[1] == "其他"
        assert st.rng.snapshot() == rng
        assert 'value="7"' in client.get("/").text
        client.post("/input", data={"value": "", "input_token": token})
        assert s.input_kind == "number"  # 重送不消耗下一個INPUT。


@pytest.mark.parametrize("answer", ["", "  ", "中性文字"])
def test_catalog_wait_numeric_text_are_not_inferred_from_history(app, tmp_path, answer):
    s = app.state.session
    st = s.state
    source = ("@NEUTRAL\nPRINTW 中性等待\nPRINTL [12]數字\nINPUT\n"
              "WAIT\nPRINTL 文字\nINPUTS\nFORCEWAIT\nRETURN 9\n")
    root = tmp_path / "catalog"
    root.mkdir()
    (root / "neutral.ERB").write_text(source, encoding="utf-8", newline="\n")
    svc = CatalogNarrationService(root, s.data)
    ctx = Ctx(st, s.data, s.out, svc, s.globals)
    rng = st.rng.snapshot()
    s._run_gen(svc.run_event_gen(ctx, "NEUTRAL", waits=True), s.begin_title)
    with TestClient(app) as client:
        assert s.input_kind == "wait" and st.result[0] == 73
        client.post("/input", data={"value": ""})
        assert s.input_kind == "number"
        assert 'value="12"' in client.get("/").text
        client.post("/input", data={"value": ""})
        assert s.input_kind == "number" and st.result[0] == 73
        client.post("/input", data={"value": "12"})
        assert s.input_kind == "wait" and st.result[0] == 12
        assert 'class="btn"' not in client.get("/").text
        client.post("/input", data={"value": ""})
        assert s.input_kind == "text"
        client.post("/input", data={"value": answer})
        assert s.input_kind == "wait" and st.results[0] == answer
        assert st.result[0] == 12 and st.result[1] == 74 and st.results[1] == "其他"
        assert st.rng.snapshot() == rng and not svc.failures
        token = client.get("/api/screen").json()["input_token"]
        client.post("/restart")
        client.post("/input", data={"value": "0", "input_token": token})
        assert app.state.session.phase.value == "title"


@pytest.mark.parametrize("abort", [False, True])
def test_nested_catalog_achievement_keeps_input_and_cleanup(app, tmp_path, abort):
    # 原成就函式由 catalog 呼叫，沿兩層 queue 等待；不可把後續 INPUT 當成確認。
    import threading
    s = app.state.session
    root = tmp_path / "nested"
    root.mkdir()
    (root / "neutral.ERB").write_text(
        '@NEUTRAL\nCALL UNLOCK_ACHIEVEMENT,220,"中性成就"\n'
        'PRINTL [12]數字\nINPUT\nFORCEWAIT\nRETURN 9\n',
        encoding="utf-8", newline="\n")
    svc = CatalogNarrationService(root, s.data)
    s.narration = svc
    s._run_gen(svc.run_event_gen(s._ctx(), "NEUTRAL", waits=True), s.begin_title)
    with TestClient(app) as client:
        assert s.input_kind == "wait" and s.globals.mem.global_[220] == 0
        if not abort:
            client.post("/input", data={"value": ""})
            assert s.input_kind == "number" and s.globals.mem.global_[220] == 1
            client.post("/input", data={"value": "12"})
            assert s.input_kind == "wait" and s.state.result[0] == 12
        client.post("/restart")
        assert not svc.failures and svc.journal.depth == 0
        assert not any(t.name in ("erb-event-NEUTRAL", "eragvt-achievement-wait")
                       for t in threading.enumerate())
        assert s.globals.exists() == (not abort)
