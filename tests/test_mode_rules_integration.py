"""S83實際TRAIN／PALAM_UP／TURNEND與Web共用前態；原文expected見各案例。"""
import pytest

from _mode_rules import prepare
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.session import GameSession, Phase
from eragvt.narration.service import CatalogNarrationService
from tools.sim_adult import adult_data, assert_ages


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService(default_csv_dir().parent / "ERB",data)


@pytest.fixture
def session(data,catalog,tmp_path):
    catalog.failures.clear()
    s=GameSession(data,tmp_path,narration=catalog)
    yield s
    assert catalog.failures == []
    assert_ages(s.state)
    s.close()


def row(s,stage):
    return next(r for r in s.fixture_evidence["events"] if r["stage"] == stage)


@pytest.mark.parametrize("mode",["survival-win","freeplay-win","sandbox-win","normal-win"])
def test_endless_real_battle_and_turnend(session,mode):
    # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:142–165；BATTLE_TRAIN_AFTER.ERB@EVENTEND:311–333。
    # 人工前態day90、總數26、存活7。ENDLESS擊破後總數27，期限扣6+2+1=9。
    s=session
    prepare(s,mode)
    s.input(0)
    s.input(1)
    while s.input_kind == "wait":
        s.input(0)
    final=row(s,"battle-return")
    assert final["outcome"] == 1 and final["battle"] == 0 and final["end"] == 0
    assert (final["total"],final["alive"],final["day"]) == ((26,126,[90,100]) if mode == "normal-win" else (27,127,[90,91]))
    assert s.phase == Phase.SHOP


@pytest.mark.parametrize("mode,count",[("instant-human",5),("instant-transform",2),("instant-sp",2),("instant-hit",5)])
def test_instant_real_turn_wait(session,mode,count):
    # BATTLE_COM.ERB@EVENTCOMEND:981–986 → INSTANT_ARG_DOWN.ERB@INSTANT_ARG_DOWN:1–32。
    s=session
    prepare(s,mode)
    s.input(0)
    s.input(4)
    assert s.input_kind == "wait"
    before=row(s,"instant-wait")
    s.input(0)
    final=row(s,"instant-complete")
    # 從實際RNG輸入按原文映射算expected，非從產品輸出反推。
    draws=final["rng"][len(before["rng"]):]
    assert len(draws) == count and all(bound == 5 for bound,value in draws)
    expected=before["bases"].copy()
    for bound,value in draws:
        expected[3+value if value < 4 else 7] -= 1 if value < 4 else 10
    assert final["bases"] == expected and final["result"] == 0
    if mode == "instant-hit":
        # ENEMY_ACTION.ERB@ENEMY_ACTION:446–540：Lv4→200，防禦/2=100，基礎/2=50。
        assert before["bases"][8] == 50


def test_palam_real_chain(session):
    # PALAM_UP.ERB@PALAM_UP:320–330；KIRYOKUDOWN:1465–1561、SEITAISEIDOWN:1565–1668。
    # 耐性10%→75*0.9=67；衣裝95%兩次合90%→60；Lv4→62；基礎扣31。
    # 服從30000經補正仍>=20000→12；內衣95%→11；Lv4→11；基礎扣5。
    # CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI:99–106、CLOTHDATAインナー.ERB@CLOTH_STATUS_300:35–36。
    s=session
    prepare(s,"instant-palam")
    s.input(0)
    final=row(s,"palam-complete")
    assert final["bases"][1:3] == [438,89]
    assert final["bases"][8:10] == [69,95]
