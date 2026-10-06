"""S84原文expected：七模式生命週期；日期／規則表不由實作輸出反推。"""
import pytest

from _mode_lifecycle import (new_session, start_new, input_checked, apply_shop_prestate,
                             drive_until, snapshot)
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.achievements import unlock
from eragvt.game.recruitment import recruitment_allowed
from eragvt.game.retirement import retirement_allowed
from eragvt.game.session import Phase
from eragvt.state.savefile import load_from_file
from tools.sim_adult import adult_data, AdultCatalog


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


@pytest.fixture
def session(data, tmp_path):
    catalog = AdultCatalog(default_csv_dir().parent / "ERB", data)
    s = new_session(data, tmp_path, catalog)
    yield s
    assert catalog.failures == []
    s.close()


@pytest.mark.parametrize("mode,period,total,join,achievement", [
    (1,11,87,False,True),(2,12,94,False,True),(3,13,101,False,True),
    (4,9,0,False,True),(5,9,0,False,True),(6,9,0,False,False),
    (7,11,87,True,True),
])
def test_mode_days_and_permissions(session, mode, period, total, join, achievement):
    # オープニング処理.ERB@SET_LIMIT_DAY:430–451；SHOP_TURNEND.ERB@EVENTSHOP:168–180。
    # SHOP.ERB@USERSHOP:290–308；SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20。
    s = session
    start_new(s, mode)
    st = s.state
    assert (st.flag[2], st.flag[1]) == (period, total)
    assert recruitment_allowed(st) is join
    assert retirement_allowed(st, 169) is join
    # 原生UNLOCK寫入／禁止，不預填此欄，也不Null替代成就函式。
    unlock(s._ctx(), 200, "人工模式驗證")
    assert s.globals.mem.global_[200] == int(achievement)
    apply_shop_prestate(s, "rest")
    for expected in ((1,1), (2,0)):
        input_checked(s, 100)
        drive_until(s, lambda x:x.phase == Phase.SHOP)
        assert (st.day[0], st.time) == expected


@pytest.mark.parametrize("mode,scenario,terminal,record", [
    (1,"deadline","title",0),(2,"deadline","title",0),
    (3,"deadline","title",0),(7,"deadline","title",0),
    (4,"record7","title",7),(4,"record8","score",8),
    (5,"record8","shop",0),(6,"record8","shop",0),
])
def test_mode_deadline_through_shop_action(session, mode, scenario, terminal, record):
    # ENDING.ERB@ENDING:74–87／@ENDING_3:460–498：ENDLESS>=8才評分；
    # NO_TIME_LIMIT整段跳過。正常新局→人工日期→全員休憩→真TURNEND。
    s = session
    start_new(s, mode)
    apply_shop_prestate(s, scenario)
    input_checked(s, 100)
    drive_until(s, lambda x:x.phase in (Phase.TITLE,Phase.SHOP) or x.out.prompt == "clear-save")
    if terminal == "score":
        assert s.out.prompt == "clear-save" and s.state.flag[64] > 0
        assert s.state.flag[100] == 127  # SURVIVAL非有限模式的BOSS全滅。
    else:
        assert s.phase.value == terminal
        if terminal == "shop":
            assert s.state.flag[64] == 0 and s.state.flag[100] == 127
    assert s.globals.mem.global_[114] == record


@pytest.mark.parametrize("mode,next_mode,period,total,count,global_slot", [
    (1,1,11,87,3,101),(2,2,12,94,1,100),(3,3,13,101,3,102),
    (7,7,11,87,3,None),(1,4,9,0,3,101),(1,5,9,0,3,101),
])
def test_new_game_action_clear_save_reload_succession(session, mode, next_mode, period, total, count, global_slot):
    # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:176–193／266–281→
    # ENDING.ERB@ENDING:9–69→オープニング処理.ERB@EVENTLOAD:13–14→
    # SUCCESSION.ERB@SUCCESSION:1444–1622→SHOP_TURNEND.ERB@EVENTSHOP:156–180。
    s = session
    start_new(s, mode)
    apply_shop_prestate(s, "clear")
    input_checked(s, 100)
    drive_until(s, lambda x:x.out.prompt == "clear-save")
    assert s.state.flag[100] == s.state.flag[101] == 0
    assert s.state.flag[854] == 1
    if global_slot is not None:
        assert s.globals.mem.global_[global_slot] == 1
    else:
        assert all(s.globals.mem.global_[i] == 0 for i in (100,101,102))
    input_checked(s, 0)
    assert s.phase == Phase.SAVE_SELECT
    input_checked(s, 5)
    assert s.out.prompt == "succession"
    saved, _ = load_from_file(s.save_dir / "save05.json")
    assert saved.flag[64] > 0 and saved.flag[854] == 1
    loaded = new_session(s.data, s.save_dir, s.narration)
    try:
        input_checked(loaded, 1)
        input_checked(loaded, 5)
        assert loaded.out.prompt == "succession"
        if global_slot is not None:
            assert loaded.globals.mem.global_[global_slot] == 1
        for value in (999,0,next_mode):
            input_checked(loaded,value)
        if loaded.out.prompt == "count":
            input_checked(loaded,0)
        for value in (1000,1):
            input_checked(loaded,value)
        drive_until(loaded, lambda x:x.phase == Phase.SHOP)
        st = loaded.state
        assert (st.day[0],st.time,st.flag[64],st.flag[854]) == (1,0,0,1)
        assert (st.flag[100],st.flag[101],st.flag[2],st.flag[1]) == (127,0,period,total)
        assert st.charanum == count + 1
        auto,_ = load_from_file(s.save_dir / "save99.json")
        assert (auto.day[0],auto.time,auto.flag[64],auto.flag[854]) == (1,0,0,1)
    finally:
        loaded.close()


@pytest.mark.parametrize("mode,period,total", [(1,11,87),(2,12,94),(3,13,106),(7,11,87)])
def test_k_victory_reinforcement_in_next_cycle(session, mode, period, total):
    # BATTLE_COM_AFTER.ERB@SOURCE_CHECK:176–180／270–275：
    # 只有周回HARDCORE的K勝利令FLAG4+1、FLAG1+5、FLAG21=1，生成天使樹。
    s = session
    start_new(s, mode)
    apply_shop_prestate(s, "clear")
    s.state.flag[854] = 1
    input_checked(s,100)
    drive_until(s, lambda x:x.phase == Phase.SHOP or x.out.prompt == "clear-save")
    st = s.state
    assert (st.flag[2],st.flag[1]) == (period,total)
    if mode == 3:
        assert s.phase == Phase.SHOP and (st.flag[4],st.flag[101],st.flag[21],st.flag[64]) == (2,2,1,0)
    else:
        assert s.out.prompt == "clear-save" and st.flag[101] == 0 and st.flag[64] > 0


@pytest.mark.parametrize("mode,expected_mode,expected_marker", [
    (1,0,-998),(2,10,0),(3,0,-998),(4,0,-998),
    (5,0,-998),(6,498,0),(7,0,-998),
])
def test_postbattle_annihilation_mode_guard(session,mode,expected_mode,expected_marker):
    # BATTLE_TRAIN_AFTER.ERB@EVENTEND:527–528：SOLO由自身PRISON結局，
    # SANDBOX禁止全滅結局；其餘轉GAMEOVER並保留原呼叫者TURNEND。
    from eragvt.game.battle.after import event_end
    from eragvt.game.action import Step
    s = session
    start_new(s,mode)
    st = s.state
    st.target = 1
    st.flag[802] = 0
    st.flag[10],st.flag[11],st.flag[12],st.flag[13] = 0,1,10000,10000
    st.tflag[98] = 2
    for c in st.charas[1:]:
        c.cflag[0],c.cflag[20],c.cflag[21] = 1,0,1
        # 人工成年男性前態走ISMANLY省略END1敘事；不影響模式守衛。
        c.talent[s.data.index_of("TALENT","オトコ")] = 1
        c.talent[s.data.index_of("TALENT","男の娘")] = 0
        c.talent[s.data.index_of("TALENT","ふたなり")] = 0
    s._run_gen(event_end(s._ctx()),lambda:None)
    drive_until(s,lambda x:x._turn is None)
    assert s._gen_result == Step.TURNEND
    assert (st.flag[0],st.flag[999]) == (expected_mode,expected_marker)
