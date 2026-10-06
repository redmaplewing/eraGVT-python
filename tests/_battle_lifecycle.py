"""S82：可重用25歲人工前態；原生戰鬥／行動／事件串接，無產品函式替身。"""
from copy import deepcopy

from _adult_lifecycle import NumericOutput
from test_transformation_parts import make_context
from eragvt.game.action import Step, action_main
from eragvt.game.battle.train import run_train
from eragvt.game.turnend import event_turnend, raid_hantei
from eragvt.state import GameRng
from eragvt.state.constants import GameMode, MODE_OPTIONS
from eragvt.text import TextOutput
from tools.sim_adult import assert_ages


TERMINALS = tuple(f"last{n}-{outcome}" for n in (1, 2)
                  for outcome in ("win", "lose", "retreat", "timeout"))
ENCOUNTERS = ("encounter-boss", "encounter-mob", "encounter-citizen", "encounter-akuoti")
RESCUES = ("rescue-win", "rescue-timeout", "rescue-lose", "rescue-abandon")
MODES = TERMINALS + ENCOUNTERS + RESCUES
SEEDS = {mode: 1 for mode in MODES}
SEEDS.update({"last1-retreat":82, "last2-retreat":0, "encounter-boss":2,
              "encounter-mob":0, "encounter-citizen":0, "encounter-akuoti":1,
              "rescue-win":2, "rescue-timeout":2, "rescue-lose":32, "rescue-abandon":2})


def prepare(s, mode, seed=None):
    assert mode in MODES
    seed = SEEDS[mode] if seed is None else seed
    s.close()
    st = s.state = make_context(s.data, s.narration).state
    s.out = NumericOutput()
    c = st.charas[1]
    for index in (2, 3):
        other = deepcopy(c)
        other.name = other.callname = f"人工成年{index}"
        st.charas.append(other)
    for index, ch in enumerate(st.charas[1:], 1):
        ch.cflag[999], ch.cflag[100], ch.cflag[240] = 1, 103, index
        ch.abl[s.data.index_of("ABL", "レベル")] = 10
        for slot in (0, 1, 2):
            ch.base[slot] = ch.maxbase[slot] = 1000
        for slot in (10, 11, 12, 13):
            ch.base[slot] = ch.maxbase[slot] = 100
    st.flag[0] = MODE_OPTIONS[GameMode.NORMAL]
    for slot, value in {1:100, 2:100, 3:7, 4:2, 46:28, 47:28, 50:1, 51:1, 100:127,
                        798:1, 799:1, 804:1, 805:0, 852:1000}.items():
        st.flag[slot] = value
    st.day[0], st.time = 3, 0
    # 關閉額外隨機事件／返血／失去角色發現，保留本次待驗原生呼叫者。
    st.flag[802] = 0
    st.flag[850] = (1 << 11) | (1 << 14)
    for index in range(200, 400):
        s.globals.mem.global_[index] = 1
    st.rng = GameRng(seed)
    evidence = {"mode": mode, "seed": seed, "stage": "prepared", "events": []}
    s.fixture_evidence = evidence

    def record(stage):
        assert_ages(st)
        row = dict(stage=stage, enemy=[st.flag[10], st.flag[11], st.savestr[13], st.flag[110]],
                   hp=[st.flag[12], st.flag[13]], last_phase=st.flag[21], outcome=st.tflag[98],
                   event=st.flag[45], news=st.flag[60], money=st.money, target=st.target,
                   turn=st.tflag[0], turn_limit=st.temp.turn_limit, battle=st.flag[700],
                   clear=st.flag[64], survived=[st.flag[100],st.flag[101]],
                   situation=st.temp.battle_situation,
                   captives=[[x.cflag[0],x.cflag[20],x.cflag[21]] for x in st.charas[1:]])
        evidence["events"].append(row)
        evidence["stage"] = stage
        return row

    def to_shop(step):
        while step != Step.SHOP:
            if step == Step.TURNEND:
                step = yield from event_turnend(s._ctx())
            elif step == Step.ACTION_MAIN:
                step = yield from action_main(s._ctx())
            elif step == Step.TRAIN:
                step = yield from run_train(s._ctx())
            else:
                raise AssertionError(step)
        record("before-shop")
        return step

    def battle(outcome):
        c = st.target_chara
        gen = run_train(s._ctx())
        first = next(gen)
        # 明示人工「戰鬥第一個輸入前」前態；BEGIN TRAIN清TFLAG後才設定。
        # 不替換COM、SOURCE_CHECK、敵行動、結算或亂數。
        if outcome == "timeout":
            st.tflag[0] = st.temp.turn_limit
        elif outcome == "lose":
            c.base[0] = c.base[1] = c.base[2] = 0
        record("battle-input")
        value = yield first
        while True:
            try:
                request = gen.send(value)
            except StopIteration as stop:
                record("battle-return")
                return stop.value
            value = yield request

    def chain():
        TextOutput.printl(s.out, "[0] fixture：開始已列明的人工前態與原生流程")
        yield None
        if mode.startswith("last"):
            n, outcome = int(mode[4]), mode.split("-")[1]
            st.flag[100], st.flag[101] = 0, 1 << (n-1)
            st.flag[10], st.flag[11] = 1, n
            st.flag[12], st.flag[13] = 10000, (1 if outcome == "win" else 10000)
            st.flag[14], st.flag[16] = 1000, 2000
            st.flag[21] = 4 if n == 2 else 0
            st.savestr[13] = "BOSS"
            c.cflag[100] = 101
            # 攻擊／撤退人工優勢，固定seed仍由原生判定；勝利不能直接設HP0。
            c.base[10] = c.maxbase[10] = 10000
            c.base[12] = c.maxbase[12] = 10000
            step = yield from battle(outcome)
            if outcome == "win":
                assert step == Step.TURNEND
                evidence["stage"] = "ending-boundary"
                return step
            return (yield from to_shop(step))
        if mode.startswith("encounter"):
            kind = mode.split("-")[1]
            st.flag[799] = 0
            c.cflag[100] = 107 if kind == "citizen" else 101
            if kind == "mob":
                st.flag[47] = 0
                st.flag.set_bit(802, 4, True)
                from eragvt.game.battle.mob import STATS
                for number in STATS:
                    st.mob_flag[divmod(number, 100)] = 1
            elif kind == "citizen":
                st.flag[852] = 0
                st.flag.set_bit(802, 5, True)
            elif kind == "akuoti":
                st.charas[2].cflag[0] = 3
                st.flag[852] = 0
            step = yield from action_main(s._ctx())
            record("encounter-return")
            assert step == Step.TRAIN, (mode, seed, step)
            # 抽樣目的為原ACTION_MAIN遭遇→真TRAIN選單；不冒充該戰完整通關。
            gen = run_train(s._ctx())
            request = next(gen)
            record("encounter-train")
            yield request
            gen.close()
            evidence["stage"] = "encounter-complete"
            return step
        outcome = mode.split("-")[1]
        # 正常RAID_HANTEI機率→RAID_RESCUE→事件號抽選，不直接指派FLAG45。
        st.flag[852] = 0
        if outcome == "win":
            for i in range(301, 308):
                st.flag[i] = 100000000
            c.base[10] = c.maxbase[10] = 10000
            c.base[12] = c.maxbase[12] = 10000
        gen = raid_hantei(s._ctx())
        request = next(gen)
        record("rescue-choice")
        value = yield request
        while True:
            try:
                request = gen.send(value)
            except StopIteration as stop:
                step = stop.value
                break
            value = yield request
        record("rescue-return")
        if outcome == "abandon":
            assert step is None
            evidence["stage"] = "rescue-abandoned"
            return Step.SHOP
        assert step == Step.TRAIN and st.flag[45] == 4, (seed, step, st.flag[45])
        step = yield from battle(outcome)
        return (yield from to_shop(step))

    def done():
        if evidence["stage"] in ("ending-boundary", "encounter-complete"):
            TextOutput.printl(s.out, "S82 已到指定驗收邊界，請查看 /fixture/state。")
        else:
            s.begin_shop(called_when_normal=True)
            record("shop")
    s._run_gen(chain(), done)
    return evidence
