"""SHOP（インターミッション）の翻寫。expected は ERB 原文から推導（行號附在註解）。"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def st(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    return s


def test_event_shop_first_day(st):
    # SHOP_TURNEND.ERB:147–155
    assert (st.day[0], st.time, st.flag[64], st.flag[799], st.target) == (1, 0, 0, 0, 1)
    # SHOP_SHOW_BOSS_INFO.ERB:55
    assert st.savestr[13] == "BOSS"
    assert st.flag[11] == 0  # :46 で退避・:154 で復元


def test_save_info(st, data):
    # オープニング処理.ERB@SAVEINFO:583–614：%LOCALS,14,LEFT% %LOCALS:3,7,RIGHT% %LOCALS:1,6,RIGHT%殲滅中    ver%LOCALS:2%
    assert shop.save_info(st, data) == "NORMALモード     1日目  1体目殲滅中    ver0.408"


def test_select_target(st):
    out = TextOutput()
    shop.select_target(st, out, 3)
    assert st.target == 3
    assert "操作キャラを蒼美に変更しました" in [l.text for l in out.lines]


@pytest.mark.parametrize("value", [0, 1, 2, 5])
def test_action_confirm_only_9_starts(st, data, value):
    # SHOP.ERB:521–532：CASE 9 以外は CASEELSE → RETURN 0（[1]はい でも中断する）
    out = TextOutput()
    assert shop.action_confirm_prompt(st, data, out) == "input"
    assert shop.action_confirm_answer(st, data, "input", value) is False
    assert st.flag[40] == 0


def test_action_confirm_9_sets_flag40(st, data):
    # 出撃・防衛予定なし → FLAG:40 = 2（:525–528）
    assert shop.action_confirm_answer(st, data, "input", 9) is True
    assert st.flag[40] == 2
    # FLAG:40 == 2 なら確認なしで行動開始（:504、:534）
    assert shop.action_confirm_prompt(st, data, TextOutput()) == "begin"


def test_set_action_and_hp_constraint(st, data):
    out = TextOutput()
    shop.usershop_set_action(st, data, out, 101, 0)
    assert st.charas[1].cflag[100] == 101
    assert "紅葉は出撃することにしました" in [l.text for l in out.lines]
    # IS_ACTION_INCAPABLE.ERB:24–25：体力 <= 強制休憩体力(500) なら出撃不可
    st.charas[1].base[0] = 500
    out = TextOutput()
    shop.usershop_set_action(st, data, out, 104, 0)
    assert st.charas[1].cflag[100] == 101  # 変更されない
    assert "紅葉は特別活動に必要な体力がありません" in [l.text for l in out.lines]
    assert out.lines[-1].wait  # HAS_INCAPABLE → WAIT（:662–663）


def test_training_hp_constraint(st, data):
    # TRAINING_DOWNTAIRYOKU：MAXBASE:体力 2787 → TIMES 0.10 → 278 → FLAG:50=1 で TIMES 2.00 → 556、
    # SYOUHI_KEIGEN(TARGET=1)：体力基礎 2006 > 1000 → 556 − 556·1006/2500 = 556 − 223 = 333（≧ 556/2）
    assert shop.training_downtairyoku(data, st, 1) == 333
    st.charas[1].base[0] = 600  # > 500 だが 600 >= 333 なので鍛錬は可能
    assert shop.is_action_incapable(data, st, 102, 1) == 0


def test_multi_set_picks_random_target_only_from_master(data):
    s = GameState.new(data, rng=FixedRng([0] * 50))
    event_first(s, data, preset=PRESET_TOKUSOU)
    s.target = 0
    shop.multi_set(s, TextOutput())
    assert s.target == 1  # RAND:(CHARANUM-1)+1 = 0+1
    assert s.flag[9] == 1


def test_show_shop_menu_buttons(st, data):
    out = TextOutput()
    shop.show_shop(st, data, out, NullNarrationService())
    btns = [b for l in out.lines for _, b in l.buttons]
    for v in (90, 50, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 120, 130, 150, 160, 200, 300, 700, 800):
        assert v in btns
    header = [l.text for l in out.lines if "インターミッション" in l.text][0]
    # SHOP_INTERMISSON_HEADER：猶予 = (7−7+1)·11 − 1 + 0 = 10、完全殲滅まで 87 − 1 = 86
    assert header == "インターミッション [☀昼]  1 日目(月)（1体目殲滅猶予 10 日/完全殲滅まで86日）"
