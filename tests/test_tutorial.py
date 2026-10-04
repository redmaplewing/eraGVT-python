"""S52：expected 來自 オープニング処理.ERB@TUTORIAL:454–581。"""
from pathlib import Path
import runpy
import pytest
from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameState, GameRng
from eragvt.text import TextOutput
from eragvt.game.input_request import TextInputRequest
from eragvt.game.tutorial import tutorial

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "source/earGVP/ERB/ゲーム内_イベント発生/オープニング処理.ERB"

@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())

@pytest.fixture
def env(data):
    st = GameState.new(data, GameRng(42))
    st.result[0], st.result[1] = 123, 456
    st.results[0], st.results[1] = "殘值", "第二格"
    return st, TextOutput()

def expected(lo, hi):
    # 只讀指定原文 PRINTL；不以 Python 產生結果當 expected。
    lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    return [s.strip()[7:] if s.strip().startswith("PRINTL ") else ""
            for s in lines[lo-1:hi] if s.lstrip().startswith("PRINTL")]

def texts(out):
    return [line.text for line in out.lines]

@pytest.mark.parametrize("choice,lo,hi", [(0,469,479),(1,486,500),(2,504,515),(3,519,539)])
@pytest.mark.parametrize("ack", ["", "任意文字", 999])
def test_chapters_wait_return_without_state_change(env, choice, lo, hi, ack):
    st, out = env
    saved, rng = st.to_json(), st.rng.snapshot()
    g = tutorial(st, out)
    assert next(g) is None
    assert texts(out) == expected(456,465)
    assert isinstance(g.send(choice), TextInputRequest)
    assert texts(out)[11:-2] == expected(lo,hi)
    assert st.result[0] == choice
    assert g.send(ack) is None
    assert texts(out)[-10:] == expected(456,465)
    assert st.result[0] == choice  # PRINTW 不寫 RESULT/RESULTS。
    with pytest.raises(StopIteration) as done:
        g.send(999)
    assert done.value.value == 999
    assert st.result[0] == 999 and st.result[1] == 456
    assert (st.results[0], st.results[1]) == ("殘值", "第二格")
    saved["result"]["0"] = 999  # 原文 RETURN 999；僅此結果格改變。
    assert st.to_json() == saved and st.rng.snapshot() == rng

@pytest.mark.parametrize("value", [-1,5,99,300,1000])
def test_invalid_does_not_redraw(env, value):
    st, out = env
    g = tutorial(st,out)
    next(g)
    assert g.send(value) is None
    assert texts(out) == expected(456,465) + [str(value)]
    assert st.result[0] == value

@pytest.mark.parametrize("choice", [1,99])
def test_spoiler_submenu(env, choice):
    st, out = env
    g = tutorial(st,out)
    next(g)
    assert g.send(4) is None
    assert texts(out)[11:] == expected(543,558)
    count=len(out.lines)
    for invalid in (-1,0,2,4,999):
        assert g.send(invalid) is None
        count += 1
        assert len(out.lines) == count
    req=g.send(choice)
    if choice == 1:
        assert isinstance(req,TextInputRequest)
        assert texts(out)[-11:-2] == expected(566,574)
        assert g.send("") is None
        assert st.result[0] == 1
    else:
        assert req is None
        assert st.result[0] == 99
    assert texts(out)[-10:] == expected(456,465)


def test_reentry_and_style_preserved(env):
    st,out=env
    out.set_color("#123456")
    out.set_bold(True)
    for _ in range(2):
        g=tutorial(st,out)
        next(g)
        with pytest.raises(StopIteration): g.send(999)
    assert sum(line.text == "チュートリアルメニュー" for line in out.lines) == 2
    assert all(seg.bold and seg.color == "#123456" for line in out.lines for part in line.parts for seg in part.segments)


def test_extraction_reproducible_and_comments_excluded():
    tool=runpy.run_path(str(ROOT/"tools/extract_tutorial.py"))
    actual=(ROOT/"src/eragvt/game/tutorial_text.py").read_text(encoding="utf-8")
    assert tool["extract"]() == actual
    from eragvt.game.tutorial_text import TEXT
    assert 480 not in TEXT and 481 not in TEXT and 482 not in TEXT
    assert set(TEXT) == {i for i,s in enumerate(SOURCE.read_text(encoding="utf-8-sig").splitlines(),1)
                         if 456 <= i <= 575 and s.lstrip().startswith(("PRINTL", "PRINTW"))}

@pytest.mark.parametrize("preset", [0,1])
def test_web_opening_continue(data,tmp_path,preset):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app
    app=create_app(data,tmp_path,narration=None)
    client=TestClient(app)
    def send(value):
        response=client.post("/api/input",json={"value":value})
        assert response.status_code == 200
        return response.json()
    send(0)
    send(300)
    assert "チュートリアルメニュー" in client.get("/").text
    send(0)
    assert app.state.session.input_kind == "text"
    send("")
    send(4)
    send(1)
    send("")
    send(999)
    assert app.state.session.input_kind == "number"
    send(300)
    send(999)
    send(preset)
    send(1)
    assert app.state.session.phase.name == "SHOP"
