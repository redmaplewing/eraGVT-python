"""S77 人工25歲連續驗收前態；只組裝入口，不替代待驗遊戲函式。"""
import re

from eragvt.game.action import Step
from eragvt.game.battle.after import event_end
from eragvt.game.battle.func import transform
from eragvt.game.battle.train import run_train
from eragvt.game.character_editor import character_editor
from eragvt.game.opening import chara_make_finalize
from eragvt.game.session import Phase
from eragvt.game.turnend import event_turnend
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.state.constants import GameMode, MODE_OPTIONS
from eragvt.text import TextOutput


class NumericOutput(TextOutput):
    """保留原作選項值；敘事不儲存，另記錄列表的非敘事身分行。"""
    def __init__(self):
        super().__init__()
        self.status_rows = []
        self._status_row = None

    def print(self, text):
        if re.match(r" 人工成年[甲乙丙]：", text):
            self._status_row = ""
        if self._status_row is not None:
            self._status_row += text
            super().print(text)
            return
        for number in re.findall(r"\[\s*([0-9]+)\s*\]", text):
            super().print(f"[{number}] 原作選項　")

    def _newline(self, *args, **kwargs):
        if self._status_row is not None:
            self.status_rows.append(self._status_row)
            self._status_row = None
        super()._newline(*args, **kwargs)

    def print_plain(self, text):
        pass

    def button(self, label, value, **kwargs):
        super().button(f"[{value}] 原作選項", value)

    def html_print(self, html):
        pass


def ages(st):
    values = [[c.base[40], c.base[41], c.maxbase[40], c.maxbase[41]] for c in st.charas]
    assert all(row == [25] * 4 for row in values)
    return values


def install_editor(s, mode):
    """人工共用編輯入口：三位已初始化的角色，沒有出生或自然開局聲明。"""
    assert mode in ("prison", "pregnancy")
    st = s.state = GameState.new(s.data, GameRng(77))
    st.charas = st.charas[:1]
    for i, name in enumerate(("甲", "乙", "丙"), 1):
        c = st.add_chara(s.data, 0)
        for field in (c.talent, c.cflag, c.abl, c.exp, c.equip):
            field.clear()
        c.name = c.callname = f"人工成年{name}"
        for slot, value in {6:99999, 40:100, 41:200, 42:300, 100:103, 240:i, 999:1}.items():
            c.cflag[slot] = value
        for name, value in {"変身能力":1, "オトコ":int(i == 1)}.items():
            c.talent[s.data.index_of("TALENT", name)] = value
        c.abl[s.data.index_of("ABL", "レベル")] = 10
        for slot in (0,1,2):
            c.base[slot] = c.maxbase[slot] = 1000
        for slot in (10,11,12,13):
            c.base[slot] = c.maxbase[slot] = 100
        for j in range(4):
            c.relation[j] = 10 * i + j
        c.cstr[13], c.cstr[14] = "短髮", "長髮"
        for a, b in ((30,31),(32,34),(33,35),(36,37)):
            c.cstr[a], c.cstr[b] = "黒", "青"
    st.target = 1
    for slot, value in {0:MODE_OPTIONS[GameMode.NORMAL], 2:100, 3:7, 4:2,
                        100:127, 798:1, 799:4, 804:1, 805:0}.items():
        st.flag[slot] = value
    st.savestr[13] = "BOSS"
    # 本次不驗重複成就提示；人工GLOBAL已有成就，不改原取得／統計函式。
    for i in range(200,400):
        s.globals.mem.global_[i] = 1
    s.out = NumericOutput()
    ages(st)

    def done():
        chara_make_finalize(st, s.data, 1, ctx=s._ctx())
        begin_lifecycle(s, mode)

    s._run_gen(character_editor(s._ctx(), 1), done)


def begin_lifecycle(s, mode):
    """人工敗北前態；TS設定與外貌沿用剛才編輯，原生TRANSFORM後不再改寫。"""
    st, c = s.state, s.state.charas[1]
    transform(s._ctx(), 1)
    c.cflag[0], c.cflag[20], c.cflag[21] = 1, 0, 3
    c.cflag[220] = 9
    # 結界阻止額外妊娠來源，讓兩路只驗規格指定的狀態。
    for slot in range(30,34):
        c.base[slot] = 10000
    st.flag[10], st.flag[11] = 0, 3
    st.flag[12], st.flag[13] = 10000, 3000
    st.flag[46], st.flag[47] = 28, 36
    st.flag[700] = 1
    st.tflag[98] = 2
    st.rng = FixedRng([0] * 1000)
    if mode == "pregnancy":
        # 已受判定的人工前態；真EVENTEND→NINSIN_CHECK_AFTER→TS等待。
        c.talent[s.data.index_of("TALENT", "妊娠")] = 2

    def chain():
        if mode == "pregnancy":
            assert (yield from event_end(s._ctx())) == Step.TURNEND
        assert (yield from event_turnend(s._ctx())) == Step.SHOP

    s._run_gen(chain(), lambda:s.begin_shop(called_when_normal=True))


def begin_rescue(s):
    """人工已遭遇BOSS、HP=1的戰鬥前態；勝利／救出由run_train處理。"""
    st = s.state
    assert s.phase == Phase.SHOP
    st.target = 1
    st.flag[798], st.flag[799] = 1, st.charanum
    st.flag[10], st.flag[11], st.flag[12], st.flag[13] = 0, 3, 10000, 1
    st.flag[46], st.flag[47], st.flag[100] = 28, 36, 127
    st.savestr[13] = "BOSS"
    st.rng = FixedRng([0] * 1000)

    def chain():
        assert (yield from run_train(s._ctx())) == Step.TURNEND
        # 救援事件收尾前態，原作TURNEND:55–63於隊伍重算後回SHOP；
        # 不走其後出生判定。本次不宣稱自然救援事件遭遇。
        st.flag[45] = 1
        assert (yield from event_turnend(s._ctx())) == Step.SHOP

    s._run_gen(chain(), lambda:s.begin_shop(called_when_normal=True))
