"""S84補驗原作ENDLESS全滅八體門檻；FREEPLAY也沒有額外引繼守衛。"""
import pytest

from _mode_lifecycle import start_new, drive_until
from test_mode_lifecycle import data, session  # noqa: F401 共用人工25歲fixture。
from eragvt.game.action import Step
from eragvt.game.battle.after import event_end
from eragvt.game.turnend import event_turnend


@pytest.mark.parametrize("mode,flags", [(4,18),(5,114)])
def test_endless_annihilation_eight_enters_score(session,mode,flags):
    # ENDING.ERB@ENDING_1:263–293、@ENDING:86–87：FREEPLAY同樣由
    # ENDLESS全滅>=8進評分；OPTION_引継ぎ無し在全ERB／ERH僅定義1處。
    # BATTLE_TRAIN_AFTER.ERB@EVENTEND:527–528實際呼叫者，不直接CALL ENDING_1。
    s = session
    start_new(s,mode)
    st = s.state
    st.target = 1
    st.flag[3],st.flag[100],st.flag[802] = 15,127,0
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
    assert (st.flag[0],st.flag[999]) == (flags,-997)
    st.flag[799] = st.charanum
    s._run_gen(event_turnend(s._ctx()),lambda:None)
    drive_until(s,lambda x:x.out.prompt == "clear-save")
    assert st.flag[64] > 0 and st.flag[999] == 0 and s.globals.mem.global_[114] == 8
