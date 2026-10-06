"""S82成年人工連續鏈；expected來自原作分支，固定seed僅選可重現路徑。

本階段無產品修改，既有行為的新增整合驗收直接應為綠；不製造假紅。
原作路徑相對source/earGVP/；邊界／隔離詳_battle_lifecycle.py及battle-lifecycle.md。
"""
import pytest

from _battle_lifecycle import prepare
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Step
from eragvt.game.session import GameSession, Phase
from eragvt.narration.service import CatalogNarrationService
from eragvt.state.savefile import load_from_file
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService(default_csv_dir().parent / "ERB", data)


@pytest.fixture
def session(data, catalog, tmp_path):
    catalog.failures.clear()
    s = GameSession(data, tmp_path, narration=catalog)
    yield s
    assert_ages(s.state)
    assert catalog.failures == []
    s.close()


def row(s, stage):
    return next(r for r in s.fixture_evidence["events"] if r["stage"] == stage)


def feed(s, value):
    """真輸入一路保留；若新增等待不得靜默當成同一次命令。"""
    assert s.input_kind == "number"
    s.input(value)
    assert s.phase != Phase.HALTED


@pytest.mark.parametrize("number", [1, 2])
@pytest.mark.parametrize("outcome,commands,result", [
    ("win", [1], 1), ("lose", [4], 2),
    ("retreat", [999], 0), ("timeout", [4], 0),
])
def test_lastboss_train_terminal_chain(session, number, outcome, commands, result):
    """ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:
    117–193、279–306勝利；973、1031–1043敗北；1104–1130時間切れ。
    ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@USERCOM:573–625撤退。
    ERB/インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND:15–19、52–136續行。
    """
    s = session
    prepare(s, f"last{number}-{outcome}")
    feed(s, 0)
    initial = row(s, "battle-input")
    assert initial["hp"] == [10000, 1 if outcome == "win" else 10000]
    assert initial["turn_limit"] == 50
    for command in commands + ([999] if number == 1 and outcome == "retreat" else []):
        feed(s, command)
    final = row(s, "battle-return")
    assert final["outcome"] == result
    if outcome == "win":
        # 原作末王完全殲滅跳過EVENTEND；天使樹4→0後走末王勝利共通。
        # 同檔@SOURCE_CHECK:40–112、279–306；不虛造勝利後直接SHOP。
        assert final["hp"][1] <= 0
        assert final["survived"] == [0, 0]
        assert final["clear"] == -1 and final["battle"] == 1
        assert s._gen_result == Step.TURNEND
        assert s.fixture_evidence["stage"] == "ending-boundary"
        assert final["last_phase"] == 0
    else:
        # ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:7、432–439。
        assert final["battle"] == 0 and final["clear"] == 0
        assert final["survived"] == [0, 1 << (number - 1)]
        assert s.phase == Phase.SHOP
        assert s.state.flag[45] == 0
        if outcome == "lose":
            assert final["captives"][0] == [1, 1, number]
            # 原生SET_PARTYMEMBER會移動幽閉角色，依身分核對而非固定索引。
            ch = next(c for c in s.state.charas if c.cflag[240] == 1)
            assert [ch.cflag[i] for i in (0, 20, 21)] == [1, 1, number]
        else:
            assert all(c.cflag[0] == 0 for c in s.state.charas[1:])
        if outcome == "timeout":
            assert final["turn"] >= 50
        saved, _ = load_from_file(s.save_dir / "save99.json")
        assert_ages(saved)
        assert saved.flag[101] == 1 << (number - 1)
        assert sorted((c.cflag[240], c.cflag[0], c.cflag[20], c.cflag[21]) for c in saved.charas) == sorted(
            (c.cflag[240], c.cflag[0], c.cflag[20], c.cflag[21]) for c in s.state.charas)


@pytest.mark.parametrize("kind,inputs,enemy_type,category,corrupt,event", [
    ("boss", [], 0, "BOSS", 0, 0),
    ("mob", [], 2, "MOB", 0, 0),
    ("citizen", [1, 1], 2, "CITIZEN", 0, 6002),
    ("akuoti", [], 0, "BOSS", 1, 0),
])
def test_action_main_naturally_draws_encounter(session, kind, inputs, enemy_type, category, corrupt, event):
    """ERB/ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN:75–96、145–155。
    ERB/ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT_ENEMY:74–129、@ENCOUNT_BOSS:262–297、
    @MOB_TENTACLE_BATTLE:533–600；ERB/ゲーム内_行動実行処理/ACTION_GATHER_INFORMATION.ERB
    @MESSAGE_GATHER_INFORMATION:344–416→ENCOUNT_CITIZEN(6002)。
    不固定敵號、不替換遭遇判定，人工條件與固定seed詳fixture。
    """
    s = session
    prepare(s, f"encounter-{kind}")
    feed(s, 0)
    for command in inputs:
        feed(s, command)
    encountered = row(s, "encounter-return")
    assert encountered["enemy"][0] == enemy_type
    assert encountered["enemy"][2:] == [category, corrupt]
    assert encountered["event"] == event
    assert encountered["hp"][0] == encountered["hp"][1] > 0
    started = row(s, "encounter-train")
    assert started["battle"] == 1
    assert started["turn_limit"] == (15 if enemy_type == 2 else 50)
    assert s.fixture_evidence["stage"] == "encounter-train"


@pytest.mark.parametrize("outcome,command,result,news", [
    ("win", 1, 1, 110004), ("timeout", 4, 0, 100004), ("lose", 4, 2, 120004),
])
def test_rescue4_natural_offer_battle_mission_shop(session, outcome, command, result, news):
    """ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB
    @RAID_HANTEI:95–105→救援共通@RAID_RESCUE:42–50、149–216。
    ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/4 攫われた女性.ERB
    @EVENT_BATTLE_EXEC_4:44–45上限40／撤退不可；@EVENT_BATTLE_MISSION_CHECKER_4:73–80
    只有勝利成功；@EVENT_BATTLE_SUCCESS_4:66–71／@EVENT_BATTLE_FAILURE_4:98–99新聞。
    """
    s = session
    prepare(s, f"rescue-{outcome}")
    feed(s, 0)
    assert row(s, "rescue-choice")["event"] == 4
    feed(s, 0)
    initial = row(s, "battle-input")
    assert initial["event"] == 4 and initial["turn_limit"] == 40
    assert initial["situation"] == "撤退不可,追撃戦,市民なし,レイプなし,"
    if outcome == "timeout":
        # ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@USERCOM:573，禁止時手輸999也不結束。
        turn = s.state.tflag[0]
        feed(s, 999)
        assert s.state.tflag[0] == turn and s.state.flag[700] == 1
        assert s.state.flag[45] == 4 and s.fixture_evidence["stage"] == "battle-input"
    feed(s, command)
    final = row(s, "battle-return")
    assert (final["outcome"], final["news"], final["battle"]) == (result, news, 0)
    if outcome == "win":
        assert final["money"] >= 5000
    if outcome == "lose":
        assert final["captives"][0] == [1, 0, final["enemy"][1]]
    # SHOP_TURNEND.ERB@EVENTTURNEND:56–61清事件；SHOP_FLASHNEWS.ERB@FLASHNEWS:69–88、204清新聞。
    assert s.phase == Phase.SHOP
    assert s.state.flag[45] == s.state.flag[60] == 0
    saved, _ = load_from_file(s.save_dir / "save99.json")
    assert saved.flag[45] == 0 and saved.flag[60] == news
    assert_ages(saved)


def test_rescue4_abandon_returns_to_shop(session):
    """救援共通@RAID_RESCUE:149–163；4 攫われた女性.ERB@EVENT_BATTLE_ABANDON_4:18–25。
    拒絕清FLAG45、無戰鬥／報酬／事件新聞；不把「未抽中事件」當拒絕。
    """
    s = session
    prepare(s, "rescue-abandon")
    feed(s, 0)
    assert row(s, "rescue-choice")["event"] == 4
    feed(s, 1)
    assert s.phase == Phase.SHOP
    assert s.state.flag[45] == s.state.flag[60] == s.state.flag[700] == 0
    assert s.state.money == 0
    assert not any(e["stage"] == "battle-input" for e in s.fixture_evidence["events"])
