"""Web API 整合測試（少量代表 case）：開新遊戲 → SHOP → 預約行動 → 存檔 → 讀檔。"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from eragvt.data import default_csv_dir, load_game_data
from eragvt.state import GameRng
from eragvt.web import create_app


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def client(tmp_path, data):
    app = create_app(data, tmp_path, rng_factory=lambda: GameRng(7), now=lambda: datetime(2026, 9, 29, 12, 34, 56))
    return TestClient(app), app, tmp_path


def texts(screen):
    return ["".join(s["text"] for p in l["parts"] for s in p["segments"]) for l in screen["lines"]]


def buttons(screen):
    return [p["button"] for l in screen["lines"] for p in l["parts"] if p["button"] is not None]


def test_new_game_shop_action_save_load(client):
    c, app, save_dir = client
    title = c.get("/api/screen").json()
    assert title["phase"] == "title"
    assert buttons(title) == [0, 1]

    shop = c.post("/api/input", json={"value": 0}).json()
    assert shop["phase"] == "shop"
    t = texts(shop)
    assert any("インターミッション" in x and "1 日目" in x for x in t)
    assert {100, 101, 108, 200, 300}.issubset(buttons(shop))
    # オートセーブ（99 番、SystemProc@beginAutoSave）
    auto = json.loads((save_dir / "save99.json").read_text(encoding="utf-8"))
    assert auto["comment"] == "2026/09/29 12:34:56 NORMALモード     1日目  1体目殲滅中    ver0.408"

    c.post("/api/input", json={"value": 101})  # 紅葉 → 出撃
    c.post("/api/input", json={"value": 2})  # 操作キャラを桃香に
    shop = c.post("/api/input", json={"value": 102}).json()  # 桃香 → 鍛錬
    st = app.state.session.state
    assert (st.charas[1].cflag[100], st.charas[2].cflag[100]) == (101, 102)

    c.post("/api/input", json={"value": 200})  # SAVEGAME
    shop = c.post("/api/input", json={"value": 5}).json()  # 5 番（空き）へ
    assert shop["phase"] == "shop"
    saved = (save_dir / "save05.json").read_bytes()

    c.post("/api/input", json={"value": 103})  # 桃香 → 休憩（セーブ後の変更）
    c.post("/api/input", json={"value": 300})  # LOADGAME
    shop = c.post("/api/input", json={"value": 5}).json()
    assert shop["phase"] == "shop"
    st2 = app.state.session.state
    assert st2.charas[2].cflag[100] == 102  # ロードで戻る
    from eragvt.state import dump_save
    from eragvt.state.savefile import GameIdentity

    assert dump_save(st2, json.loads(saved)["comment"], GameIdentity.from_data(app.state.session.data)) == saved


def test_html_page_renders_buttons(client):
    c, _, _ = client
    c.post("/input", data={"value": 0})
    html = c.get("/").text
    assert 'name="value" value="100"' in html
    assert "インターミッション" in html


def test_load_empty_slot_and_back_to_title(client):
    c, _, _ = client
    c.post("/api/input", json={"value": 1})  # ロードしてはじめる
    s = c.post("/api/input", json={"value": 7}).json()  # データなし
    assert "データがありません" in texts(s)
    s = c.post("/api/input", json={"value": 100}).json()
    assert s["phase"] == "title"


def test_full_turn_rest_back_to_shop(client):
    """開局 → 全員休憩（EVENTFIRST:165 で初期値が 予定_休憩）→ [100][9] → 1 ターン後 SHOP（夜）→ 再度 [100] → 翌日昼。"""
    c, app, save_dir = client
    c.post("/api/input", json={"value": 0})
    s = c.post("/api/input", json={"value": 100}).json()  # USERSHOP_ACTION_CONFIRM の確認
    assert s["phase"] == "action_confirm"
    s = c.post("/api/input", json={"value": 9}).json()  # [9] → FLAG:40 = 2（出撃なし）→ JUMP ACTION_MAIN
    assert s["phase"] == "shop"
    st = app.state.session.state
    assert (st.day[0], st.time) == (1, 1)  # SHOP_TURNEND.ERB:172
    assert st.flag[799] == 0  # SHOW_SHOP:20
    assert any("[🌙夜]" in x for x in texts(s))
    auto = json.loads((save_dir / "save99.json").read_text(encoding="utf-8"))
    assert auto["state"]["time"] == 1  # BEGIN SHOP（Normal から）→ オートセーブ
    s = c.post("/api/input", json={"value": 100}).json()  # FLAG:40 = 2 → 確認なし（SHOP.ERB:503–557）
    assert s["phase"] == "shop"
    assert (st.day[0], st.time, st.money) == (2, 0, 4900)


def test_training_input_and_unported_halt(client):
    c, app, _ = client
    c.post("/api/input", json={"value": 0})
    c.post("/api/input", json={"value": 102})  # 紅葉 → 鍛錬
    c.post("/api/input", json={"value": 100})
    s = c.post("/api/input", json={"value": 9}).json()
    assert s["phase"] == "turn"  # ACTION_TRAINING.ERB:70 INPUT 待ち
    assert {0, 3, 9}.issubset(buttons(s))
    s = c.post("/api/input", json={"value": 3}).json()  # 筋トレ
    assert s["phase"] == "shop"
    assert app.state.session.state.charas[1].cflag[101] == 3
    c.post("/api/input", json={"value": 101})  # 紅葉 → 出撃（S05）
    s = c.post("/api/input", json={"value": 100}).json()
    assert s["phase"] == "halted"
    assert any("未實作" in x for x in texts(s))
