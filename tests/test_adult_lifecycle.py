"""S77：兩條人工成年鏈，只驗一般狀態、列表、隊列及Web存讀邊界。

Expected由ERB推導，非fixture輸出快照：
SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1533–1606；
ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB@PRISON_EVENT:64–104、164–168；
ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_CHECK_AFTER:171–189；
ヒロイン関連/SET_PARTYMEMBER.ERB@SET_PARTYMEMBER:22–26、@SHIFTBACK_CHARA:34–43；
ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:240–259；
ヒロイン関連/AFTER_RESCUED.ERB@AFTER_RESCUED:14–16、32–36、58–61；
ヒロイン関連/RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY:3–6。

引擎依據：reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1165–1174
（SWAPCHARA不追蹤TARGET）；同目錄VariableData.cs:663–686、CharacterData.cs:289–312
（變數／角色存讀）；reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:757–780
（EVENTLOAD後SHOW_SHOP，非重跑EVENTSHOP）。JSON是既定移植規格，不聲稱.sav相容。
"""
import pytest
from fastapi.testclient import TestClient

from _adult_lifecycle import NumericOutput, ages, begin_rescue, install_editor
from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.session import Phase
from eragvt.text import NullNarrationService
from eragvt.web import create_app
from tools.sim_adult import adult_data


@pytest.fixture(scope="module")
def data():
    return adult_data(load_game_data(default_csv_dir()))


def subject(s):
    return next(c for c in s.state.charas if c.callname == "人工成年甲")


def status(s):
    st, c = s.state, subject(s)
    return {
        "order":[c.callname for c in st.charas[1:]],
        "target":st.target,
        "members":[c.cflag[999] for c in st.charas[1:]],
        "state":c.cflag[0], "form":c.cflag[1],
        "ts":[c.talent[s.data.index_of("TALENT", n)] for n in ("オトコ","変身時ＴＳ","性別変化","妊娠")],
        "prison":[c.cflag[i] for i in (20,21,30,31,220)],
        "plan":c.cflag[100], "ages":ages(st),
    }


@pytest.mark.parametrize("mode,final_state,member,preg", [
    ("prison",0,1,0), ("pregnancy",10,0,1),
])
def test_editor_prison_rescue_list_restart_load(data,tmp_path,mode,final_state,member,preg):
    app = create_app(data,tmp_path,narration=NullNarrationService())
    s = app.state.session
    install_editor(s,mode)
    with TestClient(app) as client:
        def press(value):
            assert client.post("/api/input",json={"value":value}).status_code == 200
            if app.state.session.state is not None:
                ages(app.state.session.state)

        # 男性另一形態：第一次12選外貌，第二次12才切TS；真共用UI確認。
        for value in (6,12,12,99):
            press(value)
        c = subject(s)
        assert c.talent[data.index_of("TALENT","変身時ＴＳ")] == 1
        press(99)
        # TS外貌問答尚未完成時，後續幽閉回數不可提前增加。
        assert c.cflag[31] == 0
        assert s.state.target == (3 if mode == "prison" else 1)
        assert c.cflag[220] == (0 if mode == "prison" else 9)
        assert c.talent[data.index_of("TALENT","妊娠")] == preg
        pending = s.state.to_json()
        rng = s.state.rng.snapshot()
        press(9)
        # INPUT只覆寫RESULT:0；reference/emuera-1824/Emuera/GameProc/Process.cs:249–252。
        pending["result"]["0"] = 9
        assert s.state.to_json() == pending
        assert s.state.rng.snapshot() == rng
        for value in (0,1,0,1):
            press(value)
        assert s.phase == Phase.SHOP
        assert [x.callname for x in s.state.charas[1:]] == ["人工成年乙","人工成年丙","人工成年甲"]
        assert [[x.relation[j] for j in range(4)] for x in s.state.charas[1:]] == [
            [20,22,23,21],[30,32,33,31],[10,12,13,11]]
        assert (c.cflag[0],c.cflag[999],c.cflag[31]) == (1,0,1)
        assert (c.talent[data.index_of("TALENT","性別変化")], c.talent[data.index_of("TALENT","変身時ＴＳ")]) == (1,-1)
        press(3)
        assert s.state.target == 1  # SHOP.ERB@USERSHOP:199，只能選SAFE。
        press(130)
        assert any("人工成年甲：" in row and "幽閉中 0日目" in row for row in s.out.status_rows)

        begin_rescue(s)
        pending, rng = s.state.to_json(),s.state.rng.snapshot()
        press(998)
        assert s.state.to_json() == pending and s.state.rng.snapshot() == rng
        press(1)  # 真戰鬥攻擊→SOURCE_CHECK勝利／救出→EVENTEND→TURNEND。
        assert s.phase == Phase.SHOP
        expected = dict(order=["人工成年乙","人工成年丙","人工成年甲"],target=1,
            members=[1,1,member],state=final_state,form=0,ts=[0,-1,1,preg],
            prison=[0]*5,plan=103,ages=[[25]*4]*4)
        assert status(s) == expected
        s.out.status_rows.clear()
        press(130)
        rows = [row for row in s.out.status_rows if "人工成年甲：" in row]
        assert not any("幽閉中" in row for row in rows)
        assert any("特別病棟に入院" in row for row in rows) == bool(preg)
        # 保存／新session讀回是原生端點；不在讀回後重灌角色或相依欄位。
        press(200)
        press(1)
        assert (tmp_path/"save01.json").is_file()
        before = status(s)
        saved_characters = s.state.to_json()["charas"]
        assert client.post("/restart").status_code == 200
        loaded = app.state.session
        assert loaded is not s and loaded._turn is None
        loaded.out = NumericOutput()
        press(1)  # 標題LOAD
        press(1)  # 手動槽1
        assert loaded.phase == Phase.SHOP
        assert status(loaded) == before
        assert loaded.state.to_json()["charas"] == saved_characters
        press(3)
        assert loaded.state.target == (1 if preg else 3)
        press(2)
        press(103)
        assert loaded.phase == Phase.SHOP and loaded.state.target == 2
        assert loaded.state.charas[2].cflag[100] == 103
        press(130)
        assert status(loaded) == {**before,"target":2}
    s.close()
    app.state.session.close()
