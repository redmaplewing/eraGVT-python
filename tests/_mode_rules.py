"""S83真瀏覽器與少量整合案例共用的人工25歲前態，完整catalog。"""
from copy import deepcopy

from _adult_lifecycle import NumericOutput
from test_mode_remaining_rules import context
from eragvt.game.action import Step, action_main
from eragvt.game.battle import palam, train
from eragvt.game.battle.cloth import OUTER_PER, INNER_PER
from eragvt.game.input_request import WaitInputRequest
from eragvt.game.turnend import event_turnend
from eragvt.state import GameRng
from eragvt.state.constants import GameMode
from eragvt.text import TextOutput
from tools.sim_adult import assert_ages

MODES = ("survival-win", "freeplay-win", "sandbox-win", "normal-win",
         "instant-human", "instant-transform", "instant-sp", "instant-hit", "instant-palam")


class RecordedRng(GameRng):
    def __init__(self, seed):
        super().__init__(seed)
        self.draws = []

    def rand(self, n):
        value = super().rand(n)
        self.draws.append([n,value])
        return value


def prepare(s, mode):
    assert mode in MODES
    s.close()
    game_mode = {"survival":GameMode.SURVIVAL,"freeplay":GameMode.FREEPLAY,
                 "sandbox":GameMode.SANDBOX,"normal":GameMode.NORMAL}.get(mode.split("-")[0],GameMode.INSTANT)
    st = s.state = context(s.data,game_mode).state
    s.out = NumericOutput()
    c = st.target_chara
    for n in (2,3):
        other = deepcopy(c)
        other.name = other.callname = f"人工成年{n}"
        st.charas.append(other)
    for n,ch in enumerate(st.charas[1:],1):
        ch.cflag[999],ch.cflag[100],ch.cflag[240]=1,103,n
        ch.abl[s.data.index_of("ABL","レベル")]=10
    for key,value in {1:1000,2:100,3:26,4:1,46:28,47:28,50:1,51:1,798:1,799:1,
                      804:1,805:0,850:(1<<11)|(1<<14),852:1000,12:10000,13:10000,14:1000,16:2000}.items():
        st.flag[key]=value
    st.day[0],st.day[1],st.time=90,100,0
    st.rng=RecordedRng(83)
    for n in range(200,400):
        s.globals.mem.global_[n]=1
    evidence={"mode":mode,"seed":83,"stage":"prepared","events":[]}
    s.fixture_evidence=evidence

    def record(stage):
        assert_ages(st)
        evidence["stage"]=stage
        evidence["events"].append(dict(stage=stage,day=[st.day[0],st.day[1]],
            total=st.flag[3],alive=st.flag[100],target_boss=st.flag[18],end=st.flag[64],
            outcome=st.tflag[98],battle=st.flag[700],transform=c.cflag[1],
            bases=[c.base[n] for n in (0,1,2,10,11,12,13,50,51,52)],
            rng=list(st.rng.draws),result=st.result[0]))

    def chain():
        TextOutput.printl(s.out,"[0] fixture：開始已列明的人工前態與原生流程")
        yield None
        if mode == "instant-palam":
            # 直接進既有PALAM_UP呼叫鏈；無敵回合／非自然遭遇的聲明。
            st.flag[3],st.day[0]=7,0
            st.flag[700]=1
            c.base[2],c.maxbase[2]=100,1000
            st.temp.up[11]=30000
            c.tcvarn[0]=0
            for n in (20,21,24,25):
                c.tcvarn[n]=100
            st.temp.cloth[OUTER_PER]=st.temp.cloth[INNER_PER]=100
            record("palam-before")
            yield from palam.palam_up(s._ctx())
            record("palam-complete")
            return
        if mode.endswith("-win"):
            c.cflag[100]=101
            c.base[10]=c.maxbase[10]=10000
            st.flag[13]=1
        else:
            st.flag[3],st.day[0]=7,0
            c.cflag[1]=2 if mode == "instant-sp" else 1 if mode == "instant-transform" else 0
        gen=train.run_train(s._ctx())
        request=next(gen)
        if mode.startswith("instant"):
            # 在BEGIN TRAIN完成後建立人工下一敵行動；未替換任何判定／戰鬥函式。
            st.tflag[24]=0
            st.tflag[10]=st.tflag[16]=3 if mode == "instant-hit" else 4
            st.tflag[11]=7
            c.tcvarn[5]=100
            st.flag[13]=5000
            # 命中案讓回避率低，仍實抽判定；衣裝耐久0使TAIRYOKU/KIRYOKU/LIQUID=100%。
            if mode == "instant-hit":
                c.base[12]=c.maxbase[12]=1
                for n in (21,23,25):
                    c.tcvarn[n]=0
        record("battle-input")
        value=yield request
        waiting=False
        while True:
            try:
                request=gen.send(value)
            except StopIteration as stop:
                record("battle-return")
                step=stop.value
                break
            if mode.startswith("instant") and isinstance(request,WaitInputRequest):
                record("instant-wait")
                waiting=True
            elif mode.startswith("instant") and waiting:
                record("instant-complete")
                gen.close()
                return
            value=yield request
        assert step == Step.TURNEND
        while step != Step.SHOP:
            if step == Step.TURNEND:
                step=yield from event_turnend(s._ctx())
            elif step == Step.ACTION_MAIN:
                step=yield from action_main(s._ctx())
            else:
                raise AssertionError(step)
        record("before-shop")
        return step

    def done():
        if mode.endswith("-win"):
            s.begin_shop(called_when_normal=True)
            record("shop")
        else:
            TextOutput.printl(s.out,"S83指定規則驗收邊界，請查看 /fixture/state。")
    s._run_gen(chain(),done)
    return evidence
