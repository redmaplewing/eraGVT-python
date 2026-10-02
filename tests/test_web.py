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


def test_new_game_default_opening_to_shop_and_save(client):
    """S10：タイトル [0] → [0] おまかせ（原作の既定経路：汎用キャラ 3 名）→ SHOP、存檔・讀檔。"""
    c, app, _ = client
    c.post("/api/input", json={"value": 0})
    c.post("/api/input", json={"value": 0})
    shop = c.post("/api/input", json={"value": 1}).json()  # HEROINE_PRESET [1] 基本セット
    assert shop["phase"] == "shop"
    st = app.state.session.state
    assert [ch.no for ch in st.charas[1:]] == [0, 0, 0]
    names = [ch.callname for ch in st.charas[1:]]
    assert all(n and n != "汎用キャラ" for n in names)
    assert any(names[0] in x for x in texts(shop))
    c.post("/api/input", json={"value": 200})  # SAVEGAME
    c.post("/api/input", json={"value": 0})
    c.post("/api/input", json={"value": 300})  # LOADGAME
    s = c.post("/api/input", json={"value": 0}).json()
    assert s["phase"] == "shop"
    assert [ch.callname for ch in app.state.session.state.charas[1:]] == names


def test_new_game_shop_action_save_load(client):
    c, app, save_dir = client
    title = c.get("/api/screen").json()
    assert title["phase"] == "title"
    assert buttons(title) == [0, 1]

    new_game = c.post("/api/input", json={"value": 0}).json()
    # 2 択（DEVIATION）＋ MODE_SELECT:360–368 の [100]／[200]／[300]
    assert new_game["phase"] == "new_game" and set(buttons(new_game)) == {0, 1, 100, 200, 300}
    assert any("おまかせで開始" in x for x in texts(new_game))
    hp = c.post("/api/input", json={"value": 1}).json()  # 初期セット『特装戦隊』
    assert hp["phase"] == "new_game"  # HEROINE_PRESET（オープニング処理.ERB:617–）
    assert {0, 1, 2, 3, 10, 20, 21, 22, 30}.issubset(buttons(hp))
    shop = c.post("/api/input", json={"value": 1}).json()  # [1]「基本セット」
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
    c.post("/input", data={"value": 1})
    c.post("/input", data={"value": 1})
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
    c.post("/api/input", json={"value": 1})  # 初期セット『特装戦隊』
    c.post("/api/input", json={"value": 1})  # HEROINE_PRESET [1] 基本セット
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
    c.post("/api/input", json={"value": 1})  # 初期セット『特装戦隊』
    c.post("/api/input", json={"value": 1})  # HEROINE_PRESET [1] 基本セット
    c.post("/api/input", json={"value": 102})  # 紅葉 → 鍛錬
    c.post("/api/input", json={"value": 100})
    s = c.post("/api/input", json={"value": 9}).json()
    assert s["phase"] == "turn"  # ACTION_TRAINING.ERB:70 INPUT 待ち
    assert {0, 3, 9}.issubset(buttons(s))
    s = c.post("/api/input", json={"value": 3}).json()  # 筋トレ
    assert s["phase"] == "shop"
    assert app.state.session.state.charas[1].cflag[101] == 3
    c.post("/api/input", json={"value": 104})  # 紅葉 → 活動（特別活動：未移植）
    s = c.post("/api/input", json={"value": 100}).json()
    assert s["phase"] == "halted"
    assert any("未實作" in x for x in texts(s))


def test_sortie_battle_retreat_back_to_shop(client):
    """出撃 → ボス遭遇（探索度をノルマに設定）→ 戦闘画面で攻撃・撤退 → EVENTEND → TURNEND → SHOP → セーブ／ロード。"""
    c, app, save_dir = client
    c.post("/api/input", json={"value": 0})
    c.post("/api/input", json={"value": 1})  # 初期セット『特装戦隊』
    c.post("/api/input", json={"value": 1})  # HEROINE_PRESET [1] 基本セット
    st = app.state.session.state
    st.flag[47] = st.flag[46]  # ENCOUNT.ERB:159 のボス遭遇条件（探索度 >= ノルマ）
    c.post("/api/input", json={"value": 101})  # 紅葉 → 出撃
    c.post("/api/input", json={"value": 100})
    s = c.post("/api/input", json={"value": 9}).json()
    for _ in range(10):  # 遭遇しなかった日はそのまま次のターンへ
        if s["phase"] == "turn":
            break
        assert s["phase"] == "shop"
        st = app.state.session.state
        st.flag[47] = max(st.flag[47], st.flag[46])
        st.flag[49] = 0
        s = c.post("/api/input", json={"value": 100}).json()
    assert s["phase"] == "turn"  # 戦闘の入力待ち（BATTLE_COM.ERB@SHOW_USERCOM）
    assert any("撤退[999]" in x for x in texts(s))
    assert app.state.session.state.flag[700] == 1  # BATTLE_TRAIN.ERB:139 戦闘中フラグ
    st = app.state.session.state
    turn0, pre0 = st.tflag[0], st.tflag[24]
    s = c.post("/api/input", json={"value": 3}).json()  # 遠距離攻撃（COMF3）→ SOURCE_CHECK → EVENTCOMEND
    assert s["phase"] == "turn"
    assert any("自分の行動" in x for x in texts(s)) and any("敵の行動" in x for x in texts(s))
    # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:1313–1318 先制攻撃中は TFLAG:24 を減らし、そうでなければ TFLAG:0 を進める
    assert (st.tflag[0], st.tflag[24]) == ((turn0, pre0 - 1) if pre0 > 0 else (turn0 + 1, 0))
    for _ in range(30):
        s = c.post("/api/input", json={"value": 999}).json()
        if s["phase"] != "turn":
            break
    assert s["phase"] == "shop"
    st = app.state.session.state
    assert st.flag[700] == 0  # BATTLE_TRAIN_AFTER.ERB:7
    c.post("/api/input", json={"value": 200})
    assert c.post("/api/input", json={"value": 3}).json()["phase"] == "shop"
    c.post("/api/input", json={"value": 300})
    assert c.post("/api/input", json={"value": 3}).json()["phase"] == "shop"
    assert app.state.session.state.flag[852] == st.flag[852]


def test_sortie_restraint_battle_save_load(tmp_path, data):
    """S06：出撃 → 被拘束の戦闘（振り解く／引き剥がす）→ 撤退 → SHOP → セーブ → ロードで状態が戻る。"""
    app = create_app(data, tmp_path, rng_factory=lambda: GameRng(12), now=lambda: datetime(2026, 9, 29, 12, 34, 56))
    c = TestClient(app)
    c.post("/api/input", json={"value": 0})
    c.post("/api/input", json={"value": 1})  # 初期セット『特装戦隊』
    c.post("/api/input", json={"value": 1})  # HEROINE_PRESET [1] 基本セット
    app.state.session.state.flag[47] = app.state.session.state.flag[46]  # ENCOUNT.ERB:159
    c.post("/api/input", json={"value": 101})
    s = c.post("/api/input", json={"value": 100}).json()
    if s["phase"] == "action_confirm":
        s = c.post("/api/input", json={"value": 9}).json()
    assert s["phase"] == "turn"
    restrained = False
    used = []
    for _ in range(60):
        if s["phase"] != "turn":
            break
        v = app.state.session.state.charas[1].tcvarn
        b = [p["button"] for ln in s["lines"][-30:] for p in ln["parts"] if p["button"] is not None]
        if v[0] == 0:
            restrained = True
            x = next(n for n in (8, 40, 10, 11) if n in b)
        else:
            x = 999 if restrained else 1
        used.append(x)
        s = c.post("/api/input", json={"value": x}).json()
    assert restrained and 8 in used
    assert s["phase"] == "shop"
    st = app.state.session.state
    snapshot = (st.flag[852], st.charas[1].juel[20])
    c.post("/api/input", json={"value": 200})
    assert c.post("/api/input", json={"value": 4}).json()["phase"] == "shop"
    st.flag[852] = -1  # ロードで戻ることを確認するために壊す
    c.post("/api/input", json={"value": 300})
    assert c.post("/api/input", json={"value": 4}).json()["phase"] == "shop"
    st2 = app.state.session.state
    assert (st2.flag[852], st2.charas[1].juel[20]) == snapshot
    assert st2.flag[700] == 0 and st2.charas[1].tcvarn[0] == 0
