"""S31：原作設定選單的等待與續行，預期值由註明的 ERB 推導。"""

import threading

import pytest
from fastapi.testclient import TestClient

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import action, shop, turnend
from eragvt.game.action import Ctx
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import Phase
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput
from eragvt.web import create_app


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    st = GameState.new(data, rng=GameRng(1))
    event_first(st, data, preset=PRESET_TOKUSOU)
    shop.event_shop(st, data, TextOutput(), NullNarrationService())
    svc = CatalogNarrationService(default_csv_dir().parent / "ERB", data)
    return Ctx(st, data, TextOutput(), svc)


def yandere(ctx):
    c = ctx.state.target_chara
    c.cflag[6] = 0
    c.cflag[279] = 0
    for i in range(10, 50):
        c.talent[i] = int(i == 21)


@pytest.mark.parametrize("invalid", [0, 1, -1, 100])
def test_turnend_selection_retries_without_replay(ctx, invalid):
    """口上/女性汎用口上/KOJO_0_21_ヤンデレ.ERB@YANDERE_FIRST_SETTING:34–57、@KOJO_0_TURNEND_21:109–121。

    INPUT 等待及 RESULT：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:616–640；
    reference/emuera-1824/Emuera/GameProc/Process.cs:249–252。
    """
    yandere(ctx)
    gen = action.kojo_root_gen(ctx, "TURNEND")
    try:
        assert next(gen) is None
        before = ctx.out.linecount
        assert ctx.state.target_chara.cflag[279] == 0
        assert gen.send(invalid) is None
        assert ctx.out.linecount == before  # GOTO INPUT_LOOP 不重新印出選單。
        with pytest.raises(StopIteration):
            gen.send(2)
        assert ctx.state.target_chara.cflag[279] == 2
        assert ctx.state.target_chara.cstr[20] == ctx.state.charas[2].callname
        assert ctx.narration.failures == []
    finally:
        gen.close()


def test_random_choice_retries_self(ctx):
    """口上/女性汎用口上/KOJO_0_21_ヤンデレ.ERB@YANDERE_FIRST_SETTING:47–57。"""
    yandere(ctx)
    ctx.state.target_chara.cflag[240] = 1
    ctx.state.rng = FixedRng([0, 1])  # 第一次抽到自己（1），再次抽到隊員 2。
    gen = action.kojo_root_gen(ctx, "TURNEND")
    try:
        assert next(gen) is None
        with pytest.raises(StopIteration):
            gen.send(99)
        assert ctx.state.target_chara.cflag[279] == 2
        assert ctx.state.target_chara.cstr[20] == ctx.state.charas[2].callname
        assert ctx.state.rng.snapshot() == []
    finally:
        gen.close()


def test_shop_setting_keeps_edits_until_confirmed(ctx, tmp_path):
    """口上/KOJO_4_汎用豹変.ERB@KOJO_4_FIRST:149–150、220–244；@KOJO_4_HITOKUTI_SHOP:283–285。"""
    c = ctx.state.target_chara
    c.cflag[6] = 4
    c.cflag[277] = c.cflag[278] = 0
    c.cflag[100] = 0
    app = create_app(ctx.data, tmp_path, narration=ctx.narration)
    client = TestClient(app)
    session = app.state.session
    session.state = ctx.state
    try:
        session._show_shop()
        assert session.phase == Phase.TURN
        assert client.post("/api/input", json={"value": 11}).json()["phase"] == "turn"
        assert c.cflag[278] % 1000 == 11
        client.post("/api/input", json={"value": -1})
        assert session.phase == Phase.TURN
        assert c.cflag[278] % 1000 == 11
        assert client.post("/api/input", json={"value": 100}).json()["phase"] == "shop"
        assert session.phase == Phase.SHOP
        assert c.cflag[278] % 1000 == 11
        assert c.cflag[100] == 0  # 選單的 100 不得被當成 SHOP 行動開始。
        assert ctx.narration.failures == []
    finally:
        if session._turn is not None:
            session._turn.close()


def test_restart_closes_pending_menu(ctx, tmp_path):
    """Web 放棄選單後須結束等待，避免舊 session 保留共用 catalog 的交易區間。"""
    ctx.state.target_chara.cflag[6] = 4
    ctx.state.target_chara.cflag[277] = ctx.state.target_chara.cflag[278] = 0
    app = create_app(ctx.data, tmp_path, narration=ctx.narration)
    client = TestClient(app)
    old = app.state.session
    old.state = ctx.state
    before = set(threading.enumerate())
    try:
        old._show_shop()
        workers = set(threading.enumerate()) - before
        assert any(t.name.startswith("erb-event-") for t in workers)
        assert client.post("/restart").status_code == 200
        assert all(not t.is_alive() for t in workers)
        assert app.state.session.phase == Phase.TITLE
    finally:
        if old._turn is not None:
            old._turn.close()


def test_event_turnend_suspends_before_later_effects(ctx):
    """インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND:79–85 先逐人執行口上。"""
    yandere(ctx)
    st = ctx.state
    st.flag[799] = st.charanum
    st.flag[798] = 1
    st.charas[1].cflag[72] = 8
    gen = turnend.event_turnend(ctx)
    try:
        assert next(gen) is None
        assert st.target == 1
        assert st.charas[1].cflag[72] == 8
        assert any("思い人" in line.text for line in ctx.out.lines)
    finally:
        gen.close()


@pytest.mark.parametrize("service", ["null", "catalog"])
def test_missing_kojo_return(ctx, service):
    """口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT:54–58。"""
    if service == "null":
        ctx.narration = NullNarrationService()
    ctx.state.flag[900] = 5
    gen = action.kojo_root_gen(ctx, "NO_SUCH_EVENT_S31")
    with pytest.raises(StopIteration) as stop:
        next(gen)
    assert stop.value.value == -1
    assert ctx.state.flag[900] == 0


@pytest.mark.parametrize("nested", [False, True])
def test_wait_preserves_state_rng_and_special_return(ctx, tmp_path, nested):
    """口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT:88–97：重設旗標並保留 999；INPUT 不重跑先前指令。

    引擎 INPUT：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:616–640。
    """
    root = tmp_path / "口上"
    root.mkdir()
    entry = 'CALL KOJO_ROOT(700, "SETTING")' if nested else "CALL KOJO_700_SETTING"
    (root / "test.ERB").write_text(
        f"@KOJO_700_TURNEND\n{entry}\nRETURN RESULT\n"
        "@KOJO_700_SETTING\nCFLAG:278 += 1\nLOCAL = RAND:100\n"
        "PRINTL [7]確認\nINPUT\nRETURN 999\n",
        encoding="utf-8", newline="\n",
    )
    ctx.narration = CatalogNarrationService(tmp_path, ctx.data)
    ctx.state.target_chara.cflag[6] = 700
    ctx.state.target_chara.cflag[278] = 0
    gen = action.kojo_root_gen(ctx, "TURNEND")
    try:
        assert next(gen) is None
        snapshot = ctx.state.rng.snapshot()
        assert ctx.state.target_chara.cflag[278] == 1
        with pytest.raises(StopIteration) as stop:
            gen.send(7)
        assert stop.value.value == 999
        assert ctx.state.target_chara.cflag[278] == 1
        assert ctx.state.rng.snapshot() == snapshot
        assert ctx.state.flag[900] == 0
    finally:
        gen.close()


def test_error_after_input_stops_without_rolling_back(ctx, tmp_path):
    """輸入後的動態呼叫若失敗，不能撤回玩家已選定的狀態。

    除零拋出 CodeEE：reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:298–313。
    """
    root = tmp_path / "口上"
    root.mkdir()
    (root / "test.ERB").write_text(
        '@KOJO_700_TURNEND\nPRINTL [7]確認\nINPUT\nCFLAG:278 = RESULT\n'
        'CALL KOJO_ROOT(701, "SETTING")\nRETURN 999\n'
        '@KOJO_701_SETTING\nLOCAL = 1 / 0\n',
        encoding="utf-8", newline="\n",
    )
    ctx.narration = CatalogNarrationService(tmp_path, ctx.data)
    ctx.state.target_chara.cflag[6] = 700
    gen = action.kojo_root_gen(ctx, "TURNEND")
    try:
        assert next(gen) is None
        with pytest.raises(NotImplementedError):
            gen.send(7)
        assert ctx.state.target_chara.cflag[278] == 7
    finally:
        gen.close()
