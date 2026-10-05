"""中性輸入前態；expected 依 EmueraConsole.cs:497–508、709–733。"""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.input_request import WaitInputRequest, inputs, input_number
from eragvt.web import create_app

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

@pytest.fixture
def neutral(tmp_path, data):
    app = create_app(data, tmp_path, narration=None)
    session = app.state.session
    state = SimpleNamespace(result={0: 73}, results={0: "kept"})
    ctx = SimpleNamespace(state=state, out=session.out)
    events = []
    def flow():
        try:
            session.out.printw("中性確認一")
            yield WaitInputRequest()
            events.append("first")
            session.out.wait()
            yield WaitInputRequest()
            events.append("second")
            yield from input_number(ctx)
            yield from inputs(ctx)
        finally:
            events.append("closed")
    session._run_gen(flow(), session.begin_title)
    with TestClient(app) as client:
        yield client, app, state, events
    app.state.session.close()

@pytest.mark.parametrize("value", ["", "anything", 0])
def test_wait_does_not_write_results(neutral, value):
    c, app, state, events = neutral
    assert c.get("/api/screen").json()["input_kind"] == "wait"
    c.post("/api/input", json={"value": value})
    assert events == ["first"]
    assert state.result == {0:73} and state.results == {0:"kept"}

@pytest.mark.parametrize("value", ["", " ", "bad"])
def test_number_rejects_empty_and_invalid(neutral, value):
    c, app, state, events = neutral
    for _ in range(2): c.post("/api/input", json={"value":""})
    assert app.state.session.input_kind == "number"
    c.post("/api/input", json={"value":value})
    assert state.result == {0:73} and app.state.session.input_kind == "number"

@pytest.mark.parametrize("value", ["", "  ", "中性文字"])
def test_text_keeps_empty_and_spaces(neutral, value):
    c, app, state, events = neutral
    for answer in ("", "", 12): c.post("/api/input", json={"value":answer})
    assert app.state.session.input_kind == "text"
    c.post("/api/input", json={"value":value})
    assert state.result == {0:12} and state.results == {0:value}
    assert events == ["first", "second", "closed"]

def test_wait_form_and_duplicate_submission(neutral):
    c, app, state, events = neutral
    token = c.get("/api/screen").json()["input_token"]
    html = c.get("/").text
    assert 'id="continue"' in html and 'id="value"' not in html
    for _ in range(2):
        c.post("/input", data={"value":"", "input_token":token})
    assert events == ["first"]
    assert app.state.session.input_kind == "wait"

def test_api_duplicate_and_legacy_clients(neutral):
    c, app, state, events = neutral
    token = c.get("/api/screen").json()["input_token"]
    for _ in range(2):
        c.post("/api/input", json={"value":"", "input_token":token})
    assert events == ["first"]
    c.post("/api/input", json={"value":""})
    assert events == ["first", "second"]

def test_restart_closes_generator_and_rejects_old_page(neutral):
    c, app, state, events = neutral
    token = c.get("/api/screen").json()["input_token"]
    c.post("/restart")
    assert events == ["closed"]
    c.post("/input", data={"value":"0", "input_token":token})
    assert app.state.session.phase.value == "title"


def test_number_and_text_form_constraints(neutral):
    c, app, state, events = neutral
    for _ in range(2): c.post("/input", data={"value":""})
    html = c.get("/").text
    assert 'type="number" name="value" id="value" autofocus autocomplete="off" required' in html
    c.post("/input", data={"value":"12"})
    html = c.get("/").text
    assert 'type="text" name="value" id="value" autofocus autocomplete="off">' in html
    c.post("/input", data={"value":""})
    assert state.results == {0:""}
