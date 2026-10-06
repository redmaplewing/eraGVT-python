"""S84：完整 catalog 的人工25歲新局／終局驗收工具，不替換產品流程。"""
from _adult_lifecycle import NumericOutput
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng
from tools.sim_adult import assert_ages


class LifecycleOutput(NumericOutput):
    """只保留非敘事選單標籤與數字；所有 catalog 仍照常執行。"""
    def __init__(self):
        super().__init__()
        self.prompt = "title"

    def print(self, text):
        markers = {
            "◆ゲームモードの選択": "mode",
            "クリアデータを記録しますか？": "clear-save",
            "[999] 引き継ぎ開始": "succession",
            "現在の引き継ぎ人数が 0人になっています。": "inherit-confirm",
            "周回クリアボーナス：ゲーム開始時の人数を増減できます": "count",
        }
        if text in markers:
            self.prompt = markers[text]
        if "[1000]" in text:
            self.prompt = "creation"
        if "基本セット" in text:
            self.prompt = "settings"
        if "プロローグを表示しますか" in text:
            self.prompt = "prologue"
        super().print(text)


def new_session(data, save_dir, narration, seed=4):
    s = GameSession(data, save_dir, rng=GameRng(seed), narration=narration)
    s.out = LifecycleOutput()
    s.begin_title()
    return s


def input_checked(s, value):
    assert_ages(s.state)
    s.input(value)
    assert_ages(s.state)
    assert s.phase != Phase.HALTED


def start_new(s, mode):
    # オープニング処理.ERB@EVENTFIRST:114–292：原預設三人（SOLO一人），
    # 完成製作→基本設定→略過序章；不使用套組捷徑或自動代按。
    for value in (0, mode, 1000, 1, 0):
        input_checked(s, value)
    for _ in range(100):
        if s.phase == Phase.SHOP:
            return
        assert s.input_kind == "wait", (s.phase, s.out.prompt)
        input_checked(s, "")
    raise AssertionError("FIRST未結束")


def apply_shop_prestate(s, scenario):
    """只在已完成真新局的SHOP施加可見人工前態，不直接呼叫結局。"""
    assert s.phase == Phase.SHOP
    st = s.state
    st.flag[802] = 0  # 設定關閉無關隨機事件；完整TURNEND仍執行。
    for c in st.charas[1:]:
        c.cflag[100] = 103
    if scenario == "clear":
        # S37原文前態：七普通BOSS已擊破，K傷害累積使其遭遇HP=1。
        st.flag[100], st.flag[101] = 0, 1
        st.flag[47] = st.flag[46]
        st.flag[401] = 100000000
        st.target = 1
        st.charas[1].cflag[100] = 101
        # 不改RNG實作；人工攻擊／敏捷優勢縮短真TRAIN。
        st.charas[1].base[10] = st.charas[1].maxbase[10] = 10000
        st.charas[1].base[12] = st.charas[1].maxbase[12] = 10000
        st.rng = GameRng(4)
    elif scenario in ("deadline", "record7", "record8"):
        kills = {"deadline": 0, "record7": 7, "record8": 8}[scenario]
        st.flag[3], st.flag[100] = 7 + kills, 127
        st.flag[10], st.flag[11], st.flag[110], st.flag[73] = 0, 1, 0, 0
        st.day[0], st.day[1], st.time = (kills + 1) * st.flag[2], 0, 1
    elif scenario != "rest":
        raise ValueError(scenario)
    assert_ages(st)


def snapshot(s):
    st = s.state
    result = dict(phase=s.phase.value, input_kind=s.input_kind, prompt=s.out.prompt,
                  global_values={str(i): s.globals.mem.global_[i] for i in (100,101,102,113,114,200,270)},
                  saved=(s.save_dir / "save05.json").exists())
    if st is not None:
        assert_ages(st)
        result.update(day=[st.day[0],st.day[1],st.time], mode=st.flag[0],
                      flags={str(i):st.flag[i] for i in (1,2,3,4,10,11,21,64,100,101,401,854,999)},
                      count=st.charanum-1,
                      ages=[[c.base[40],c.base[41],c.maxbase[40],c.maxbase[41]] for c in st.charas])
    return result


def drive_until(s, predicate, maximum=300):
    """測試用實際輸入驅動；瀏覽器不呼叫此函式。"""
    for _ in range(maximum):
        if predicate(s):
            return
        if s.input_kind == "wait":
            value = ""
        elif s.phase == Phase.ACTION_CONFIRM:
            value = 9
        else:
            # TRAIN攻擊1；一般確認0。終局前必須由predicate截住。
            buttons = {v for line in s.screen() for _,v in line.buttons}
            value = 1 if 1 in buttons else 0
        input_checked(s, value)
    raise AssertionError(snapshot(s))
