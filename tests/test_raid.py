"""S20：襲撃／救援イベント戦（`eragvt.game.raid`、`turnend.raid_hantei`）。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/ゲーム内_イベント発生/`，行號寫在註解），不從實作輸出反推：
HANTEI = `強制発生イベント/FORCE_襲撃or救援イベント発生.ERB`、RESCUE = `イベントから派生する特殊戦闘/●イベント戦闘_救援共通.ERB`、
ATTACK = `イベントから派生する特殊戦闘/●イベント戦闘_襲撃共通.ERB`、`2:`〜`3004:` = 各イベントファイル。
初期セット『特装戦隊』：紅葉（1）・桃香（2）・蒼美（3）、全員 休憩（CFLAG:100 = 103）・未変身、性耐性 198。
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import raid, shop, turnend
from eragvt.game.action import Ctx, Step
from eragvt.game.battle import train
from eragvt.game.battle.cloth import cloth_hosei
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.session import GameSession, Phase
from eragvt.state import GameRng, GameState
from eragvt.state.savefile import load_from_file
from eragvt.text import NullNarrationService, TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data):
    """DAY = 3、TIME = 0、TARGET = 1、防衛力 5000、FLAG:52 = 0。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.day[0] = 3
    return Ctx(s, data, TextOutput(), NullNarrationService())


class ByN(GameRng):
    """rand(n) は n ごとに用意した値を順に返し、無ければ default（None なら n-1）。呼ばれた n を記録。"""

    def __init__(self, table: dict[int, list[int]] | None = None, default: int | None = None) -> None:
        super().__init__(0)
        self.table = {k: list(v) for k, v in (table or {}).items()}
        self.default = default
        self.calls: list[int] = []

    def rand(self, n: int) -> int:
        if n <= 0:
            raise ValueError(n)
        self.calls.append(n)
        q = self.table.get(n)
        if q:
            return q.pop(0) % n
        return (n - 1) if self.default is None else self.default % n


def T(data, n):
    return data.index_of("TALENT", n)


def B(data, n):
    return data.index_of("BASE", n)


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def drive(gen, inputs=()):
    """INPUT に inputs を順に送り、戻り値を返す。"""
    inputs = list(inputs)
    try:
        next(gen)
        while True:
            gen.send(inputs.pop(0))
    except StopIteration as e:
        return e.value


def rec_gen(store: list, value=None):
    def fake(ctx, *a):
        store.append((ctx.state.target, ctx.state.flag[45]))
        return value
        yield  # pragma: no cover

    return fake


# =====================================================================================================
# RAID_HANTEI（HANTEI:9–105）
# =====================================================================================================


def _day2(st):
    st.day[0] = 2  # :31 DAY < 3


def _f21(st):
    st.flag[21] = 1  # :25 裏ボス


def _f41(st):
    st.flag[41] = 3  # :28 FLAG:41 >= CHARANUM - 1


def _all_out(st):
    for i, plan in ((1, 101), (2, 101), (3, 105)):  # :42 出撃・防衛は数えない
        st.charas[i].cflag[100] = plan


def _all_captured(st):
    for i in (1, 2, 3):
        st.charas[i].cflag[0] = 1


@pytest.mark.parametrize("setup", [_day2, _f21, _f41, _all_out, _all_captured])
def test_raid_hantei_guards(ctx, setup):
    st = ctx.state
    setup(st)
    st.rng = ByN()
    assert drive(turnend.raid_hantei(ctx)) is None
    assert st.rng.calls == []


@pytest.mark.parametrize(
    ("defence", "n"),
    [(999, 6), (1000, 12), (1749, 12), (1750, 24), (2499, 24), (3750, 48), (7499, 60), (9999, 72), (12499, 84),
     (14999, 96), (17499, 112), (19999, 128), (20000, 256)],
)
def test_raid_hantei_defence_rand(ctx, defence, n):
    """:51–75 防衛力に応じた RAND。LOCAL:2 != 0 なら :95／:100 の RAND は引かず（短絡）、:103 RAND:100 のみ。"""
    st = ctx.state
    st.flag[852] = defence
    st.temp.battle_situation = "撤退不可,"
    st.rng = ByN()
    assert drive(turnend.raid_hantei(ctx)) is None
    assert st.rng.calls == [n, 100]
    assert st.temp.battle_situation == ""  # :78 INITBATTLESITUATION


@pytest.mark.parametrize(
    ("time", "f52", "table", "calls", "kind"),
    [
        (0, 0, {60: [0], 2: [0]}, [60, 2], "rescue"),  # 防衛力 5000 → :61 RAND:60。:95 昼・RAND:2 == 0
        (1, 0, {60: [0], 2: [0], 18: [5]}, [60, 2, 18], "attack"),  # 夜：:95 不成立 → :100 RAND:18 != 0
        (0, 0, {60: [0], 2: [1], 18: [0], 100: [0]}, [60, 2, 18, 100], "attack"),  # :103 最低 1%
        (0, 2, {60: [0], 2: [1], 12: [3]}, [60, 2, 12], "attack"),  # :100 RAND:(18 - 2*3)
        (0, 0, {60: [1], 100: [1]}, [60, 100], None),
    ],
)
def test_raid_hantei_dispatch(ctx, monkeypatch, time, f52, table, calls, kind):
    """:95–105 JUMP RAID_RESCUE／RAID_ATTACK。JUMP 先の戻り値（BEGIN 先）がそのまま返る。"""
    st = ctx.state
    st.time = time
    st.flag[52] = f52
    got: list = []
    monkeypatch.setattr(raid, "raid_rescue", rec_gen(got, Step.TRAIN))
    monkeypatch.setattr(raid, "raid_attack", rec_gen(got, Step.SHOP))
    st.rng = ByN(table)
    r = drive(turnend.raid_hantei(ctx))
    assert st.rng.calls == calls
    if kind is None:
        assert r is None and got == []
    else:
        assert len(got) == 1
        assert r == (Step.TRAIN if kind == "rescue" else Step.SHOP)


def test_event_turnend_returns_raid_step(ctx, monkeypatch):
    """SHOP_TURNEND.ERB:131–136：RAID が BEGIN TRAIN したら EVENTTURNEND はそこで終わる。"""

    def fake(ctx):
        ctx.state.flag[45] = 2
        return Step.TRAIN
        yield  # pragma: no cover

    monkeypatch.setattr(turnend, "raid_hantei", fake)
    ctx.state.rng = GameRng(3)
    ctx.state.flag[799] = ctx.state.charanum
    assert drive(turnend.event_turnend(ctx)) == Step.TRAIN


# =====================================================================================================
# RAID_RESCUE（RESCUE:3–216）
# =====================================================================================================


def test_rescue_no_candidate(ctx):
    """:8–20：疲労 50 以上（CFLAG:99）は数えない → 全員なら何もせず RETURN。"""
    st = ctx.state
    for i in (1, 2, 3):
        st.charas[i].cflag[99] = 50
    st.rng = ByN()
    assert drive(raid.raid_rescue(ctx)) is None
    assert st.rng.calls == [] and texts(ctx.out) == []


def test_rescue_target_heal_and_abandon(ctx):
    st = ctx.state
    st.charas[1].cflag[100] = 101  # 出撃 → :31 で再抽選
    c = st.charas[2]
    c.base[0], c.base[1] = 100, 100
    st.rng = ByN({3: [0, 1], 4: [1]})  # :29 RAND:3 + 1 = 1（不可）→ 2、:49 RAND(2, 6) = 1 + 2 = 3
    r = drive(raid.raid_rescue(ctx), [5, 1])  # 5 は :151–163 の GOTO INPUT_LOOP_1（再入力）、1 = 助けに行かない
    assert r is None
    assert st.target == 2
    assert st.flag[43] == 0  # :23
    # :91–95 体力 MAXBASE/10 + 500 = 245 + 500、気力 MAXBASE/100 + 500 = 27 + 500
    assert (c.base[0], c.base[1]) == (845, 627)
    assert st.flag[45] == 0  # :159
    assert st.flag[60] == 100003  # 3:25–27 ABANDON
    t = texts(ctx.out)
    assert t.count("　　　―――――　　　ＥＭＥＲＧＥＮＣＹ　！！　　―――――") == 1  # 演出 30 コマは CLEARLINE で消える
    assert "WARNING" not in t
    assert "息抜きがてらに街に出ていた桃香のもとに、緊急の連絡が入った。" in t  # :98–108（昼・休憩）
    assert "自衛官専用の回線に、救援要請が発信されていた。" in t  # 3:5
    assert t[-3:] == ["不確定要素も多く、万全でもない状態で触手生物と戦うのは危険すぎる。",
                      "状況から判断した結果、桃香は助けに行かないという決断を下した……", ""]  # :158 PRINTW


def test_rescue_accept_begins_train(ctx, data):
    """救援 4（入力なし）：:153 RESCUE_4 → :168–178 初期化 → EXEC_4（ターン上限 40）→ ENCOUNT_BOSS → BEGIN TRAIN。"""
    st = ctx.state
    st.time = 1
    st.charas[2].cflag[100] = 101
    st.charas[3].cflag[100] = 101
    c = st.charas[1]
    boss_exp = c.exp[data.index_of("EXP", "ボス経験")]
    st.rng = ByN({3: [0], 4: [2]})  # :29 → 1、RAND(2, 6) = 4
    st.temp.battle_situation = ""
    r = drive(raid.raid_rescue(ctx), [0])
    assert r == Step.TRAIN
    assert st.flag[45] == 4
    assert st.temp.turn_limit == 40  # 4:44
    assert st.temp.battle_situation == "撤退不可,追撃戦,市民なし,レイプなし,"  # 4:45（ADDBATTLESITUATION は代入）
    assert (st.tflag[0], c.tcvarn[0]) == (-1, 3)  # :168–173
    assert c.exp[data.index_of("EXP", "ボス経験")] == boss_exp + 1  # ENCOUNT.ERB:290
    t = texts(ctx.out)
    assert "自室に居た紅葉のもとに、緊急の連絡が入った。" in t  # :109–124（夜・休憩）
    assert "たとえ危険が伴うとしても、この事態を見過ごすわけにはいかない。" in t
    assert any(x.endswith(" と遭遇した！") for x in t)  # MESSAGE_RAID_BOSS:40–42


def test_rescue_not_found_is_sticky(ctx):
    """:31–39：999 回で見つからなければ「気のせい」。LOCAL:1 は静的で 999 のまま残る → 次回は 1 回目で即終了。"""
    st = ctx.state
    st.charas[2].cflag[100] = 101
    st.charas[3].cflag[100] = 101
    st.rng = ByN({}, default=1)  # :29 RAND:3 = 1 → 常にキャラ 2（出撃中）
    assert drive(raid.raid_rescue(ctx)) is None
    assert st.rng.calls == [3] * 1000  # 999 回の再抽選 + 判定時の 1 回
    assert texts(ctx.out)[-2:] == ["桃香は何か嫌な気配を感じたが、気のせいだったようだ…", ""]  # :37–38
    st.rng = ByN({}, default=0)  # 今度は 1（無事）を引いても
    assert drive(raid.raid_rescue(ctx)) is None
    assert st.rng.calls == [3]
    assert st.flag[45] == 0


# =====================================================================================================
# RAID_ATTACK（ATTACK:3–178）
# =====================================================================================================


@pytest.mark.parametrize(
    ("setup", "time", "expected"),
    [
        (lambda c, d: c.talent.__setitem__(T(d, "繁殖袋"), 1), 0, 3002),  # :45
        (lambda c, d: (c.cflag.__setitem__(100, 104), c.cflag.__setitem__(101, 8)), 0, 3003),  # :48 ライブ公演直後
        (lambda c, d: (c.cflag.__setitem__(100, 108), c.cflag.__setitem__(101, 20)), 1, 3004),  # :51 ナイトプール
        (lambda c, d: (c.cflag.__setitem__(100, 108), c.cflag.__setitem__(101, 20)), 0, 3001),
        (lambda c, d: c.talent.__setitem__(T(d, "夜魔の貴族"), 1), 0, 3002),  # :54
        (lambda c, d: None, 0, 3001),
        (lambda c, d: None, 1, 3002),
    ],
)
def test_attack_event_kind(ctx, data, monkeypatch, setup, time, expected):
    st = ctx.state
    st.time = time
    st.charas[2].cflag[100] = 101
    st.charas[3].cflag[100] = 105
    setup(st.charas[1], data)
    got: list = []
    monkeypatch.setattr(raid, "_exec", rec_gen(got, Step.SHOP))
    st.rng = ByN()
    assert drive(raid.raid_attack(ctx)) == Step.SHOP
    assert got == [(1, expected)]
    assert st.flag[43] == 0  # :6


def test_attack_weights_and_heal(ctx, data, monkeypatch):
    """:20–29 巻き込まれ体質・人外の美貌は各 2 口追加 → 候補 紅葉 5 口 + 桃香 1 口 = RAND:6。:108–112 体力気力回復。"""
    st = ctx.state
    st.charas[3].cflag[100] = 101
    c = st.charas[1]
    c.talent[T(data, "巻き込まれ体質")] = 1
    c.talent[T(data, "人外の美貌")] = 1
    c.base[0] = 0
    monkeypatch.setattr(raid, "_exec", rec_gen([], Step.SHOP))
    st.rng = ByN({6: [0]})
    drive(raid.raid_attack(ctx))
    assert st.rng.calls[0] == 6
    assert st.target == 1
    assert c.base[0] == 2787 // 10 + 500
    t = texts(ctx.out)
    assert t.count("　　　―――――　　　ＷＡＲＮＩＮＧ　！！　　―――――") == 1


def test_attack_ishole_uses_target(ctx, data, monkeypatch):
    """:15 `ISHOLE()` は引数省略 = TARGET（候補の CCOUNT ではない）。男女平等 OFF（FLAG:850 bit5）で TARGET が男なら
    候補 0 → FLAG:45 = 0 で中断（:32–35）。"""
    st = ctx.state
    st.flag[850] |= 1 << 5
    st.charas[1].talent[T(data, "オトコ")] = 1
    st.target = 1
    st.flag[45] = 9
    st.rng = ByN()
    assert drive(raid.raid_attack(ctx)) is None
    assert st.flag[45] == 0


# =====================================================================================================
# 個別イベント EXEC
# =====================================================================================================


def _prep(ctx, n):
    st = ctx.state
    st.target = 1
    st.flag[45] = n
    st.temp.battle_situation = ""
    raid._pre_train_init(ctx)


def test_exec_2(ctx):
    st = ctx.state
    _prep(ctx, 2)
    c = st.charas[1]
    # [2] 知性 100 < 110 → 2:94 MAX(198/10, 10) + RAND:3(2) = 21。:106 RAND:7 = 0（金髪の制服少女）、:134 RAND:2 = 0
    # [1] 助け出す → :218 MAX(177/4, 20) + RAND:6(5) = 49、人気度 +1。:228 RAND:2 = 1（礼拝堂）、PRINTDATAL RAND:2 = 0
    st.rng = ByN({3: [2], 7: [0], 2: [0, 1, 0], 6: [5]})
    assert drive(raid._exec(ctx), [2, 1]) is None
    assert c.base[2] == 198 - 21 - 49
    assert st.flag[853] == 1
    assert st.temp.turn_limit == 15
    assert st.temp.battle_situation == "撤退不可,耐久戦,市民なし,レイプなし,"
    t = texts(ctx.out)
    assert "派手なアクセサリを付けた金髪の制服少女が触手に手足を取り込まれて、" in t
    assert "スカートを捲り上げられ触手が股間に突き立てられ、卑猥な水音を立てている。" in t
    assert "　性耐性が21減少した！" in t and "　性耐性が49減少した！" in t
    assert "見れば多数の気絶した生徒があちこちに倒れている。" in t
    assert "生存者を助けようと紅葉が礼拝堂に踏み込むと、" in t


def test_exec_2_strong(ctx):
    """[0] 攻撃 150 + 防御 130 ≥ 250 → 無傷。[0] 先を急ぐ。"""
    st = ctx.state
    _prep(ctx, 2)
    st.rng = ByN()
    drive(raid._exec(ctx), [0, 0])
    assert st.charas[1].base[2] == 198
    assert st.flag[853] == 0


@pytest.mark.parametrize(("defence", "hp", "pop"), [(130, 2787 - (2787 // 6 + 299), 0), (141, 2787, 2)])
def test_exec_3_front(ctx, data, defence, hp, pop):
    """3:45 防御 > 140 または 攻撃 > 200 なら受け止める（人気度 +2）、それ以外は体力 BASE/6 + RAND:300 減少。"""
    st = ctx.state
    _prep(ctx, 3)
    st.charas[1].base[B(data, "防御")] = defence
    st.rng = ByN()
    drive(raid._exec(ctx), [0])
    assert st.charas[1].base[0] == hp
    assert st.flag[853] == pop
    assert st.temp.turn_limit == 15


def test_exec_4(ctx):
    st = ctx.state
    _prep(ctx, 4)
    st.rng = ByN()
    assert drive(raid._exec(ctx)) is None
    assert st.temp.turn_limit == 40
    assert "新たな獲物を見つけたと言わんばかりに何本もの太い触手が蠢き始める。" in texts(ctx.out)  # 4:31 ISGIRLY


@pytest.mark.parametrize(
    ("first", "second", "setup", "situation", "limit"),
    [
        # 5:86–91 慎重 → ターン上限 25。:196 頭上 → 防御 130 < 200 → 体力 MAX(278, 10) + RAND(300,400)(399) = 677 減 → 2110 > 70%
        (1, 1, {}, "撤退不可,支援無効,耐久戦,市民なし,レイプなし,", 25),
        (1, 1, {"防御": 200}, "撤退不可,支援無効,耐久戦,市民なし,レイプなし,", 25),  # :239 防ぎきった
        (1, 0, {"体力": 1500}, "撤退不可,支援無効,耐久戦,市民なし,レイプなし,強制挿入,", 25),  # 1500-549=951 ≤ 50%
        (1, 0, {"体力": 2200}, "撤退不可,支援無効,耐久戦,市民なし,レイプなし,強制拘束,", 25),  # 2200-619=1581：50〜70%
        (1, 0, {"敏捷": 500}, "撤退不可,支援無効,耐久戦,市民なし,レイプなし,", 25),  # :187 回避
        (1, 2, {}, "撤退不可,支援無効,市民なし,レイプなし,強制全裸,強制発情,強制拘束,", 25),  # 知性不足
        (1, 8, {}, "撤退不可,支援無効,市民なし,レイプなし,", 25),  # :327 表示されなくても 7／8／9 は受け付ける
        (1, 5, {}, "撤退不可,支援無効,市民なし,レイプなし,強制全裸,強制発情,強制拘束,", 25),  # CASEELSE
        (0, 8, {}, "撤退不可,支援無効,市民なし,レイプなし,", 20),  # :57–85 突入 → 20
    ],
)
def test_exec_5(ctx, data, first, second, setup, situation, limit):
    st = ctx.state
    _prep(ctx, 5)
    c = st.charas[1]
    for k, v in setup.items():
        c.base[B(data, k)] = v
    st.rng = ByN()
    assert drive(raid._exec(ctx), [first, second]) is None
    assert st.temp.battle_situation == situation
    assert st.temp.turn_limit == limit


def test_exec_5_bound_resist(ctx):
    """5:312 MAX(198/10, 10) + RAND(15, 30)：RAND:15 + 15。"""
    st = ctx.state
    _prep(ctx, 5)
    st.rng = ByN({15: [3]})
    drive(raid._exec(ctx), [1, 2])
    assert st.charas[1].base[2] == 198 - (19 + 18)
    assert "性耐性が37減少した！" in texts(ctx.out)


def test_exec_3001(ctx):
    st = ctx.state
    _prep(ctx, 3001)
    st.rng = ByN()
    assert drive(raid._exec(ctx)) is None
    assert st.temp.turn_limit == 15
    assert st.temp.battle_situation == "撤退不可,支援無効,市民確定,レイプなし,耐久戦,"
    assert "息抜きがてらに街に出ていた紅葉は、突然響き渡った轟音にはっとした。" in texts(ctx.out)  # 3001:4–21


def test_exec_3002(ctx):
    st = ctx.state
    _prep(ctx, 3002)
    c = st.charas[1]
    c.cflag[100] = 106
    st.rng = ByN()
    assert drive(raid._exec(ctx)) is None
    assert c.cflag[100] == 103  # 3002:72–73
    assert c.tcvarn[0] == 1  # :123 近距離
    assert st.temp.battle_situation == "撤退不可,空中不可,遠距離不可,支援無効,市民なし,レイプなし,耐久戦,"
    assert "戦闘支援を行っていた紅葉は、突然響き渡った轟音にはっとした。" in texts(ctx.out)


def test_exec_3002_breeding_sack_kidnapped(ctx, data):
    """3002:9–56：繁殖袋は戦闘なしで拉致 → CFLAG:0 = 9、苗床化、幽閉経験 +1 → BEGIN TURNEND。"""
    st = ctx.state
    _prep(ctx, 3002)
    c = st.charas[1]
    c.talent[T(data, "繁殖袋")] = 1
    st.rng = ByN()
    assert drive(raid._exec(ctx)) == Step.TURNEND
    assert c.cflag[0] == 9
    assert c.talent[T(data, "苗床化")] == 1
    assert c.exp[data.index_of("EXP", "幽閉経験")] == 1
    t = texts(ctx.out)
    assert "ベッドから動けない紅葉に外の世界に警告する方法はなく、ただ仲間達を待つことしかできない。" in t
    assert "という音と共に現れた触手" in t  # :119–122（繁殖袋なら「に、…」は付かない）
    assert "紅葉は触手生物に拉致されました" in t


def test_exec_3003_costume(ctx):
    st = ctx.state
    _prep(ctx, 3003)
    c = st.charas[1]
    st.rng = ByN()
    drive(raid._exec(ctx))
    assert (c.cflag[40], c.cflag[544], c.cflag[540], c.cflag[541]) == (105, 1, 100, 200)  # 3003:6、特殊シチュ:60–75
    assert st.temp.turn_limit == 30
    assert st.temp.battle_situation == "先制無し,支援無効,身バレ不可,常時撮影,市民確定,レイプなし,耐久戦,,"


def test_exec_3004_costume_and_shower(ctx):
    st = ctx.state
    _prep(ctx, 3004)
    c = st.charas[1]
    c.cflag[270] = 4
    st.rng = ByN({3: [1]})
    drive(raid._exec(ctx))
    # 3004:299 アウター 0、インナー 992（BATTLE_EVENT_CLOTH_STATUS_3004 "INNER" CASE 4：少女用スクール水着 HP35）
    assert (c.cflag[40], c.cflag[41], c.cflag[42]) == (0, 200, 992)
    assert c.cstr[82] == "少女用スクール水着"
    assert c.tcvarn[24] == 35
    assert c.tcvarn[0] == 1
    # :304 MAX(198/5, 20) + RAND:3(1) = 40
    assert c.base[2] == 158
    assert st.temp.battle_situation == "先制無し,支援無効,市民なし,レイプなし,変身不可,"


def test_event_cloth_status_outside_3004(ctx):
    """CLOTHDATA※イベント専用装備.ERB:95–99：FLAG:45 が 3004 以外なら CATCH の既定値（HP80）。:73／:88 の 991 は先に
    定義された :73（HP0）。"""
    st = ctx.state
    st.flag[45] = 0
    assert cloth_hosei(ctx, 1, 992, "HP") == 80
    assert cloth_hosei(ctx, 1, 992, "SEITAISEI") == 95
    assert cloth_hosei(ctx, 1, 991, "HP") == 0


# =====================================================================================================
# ミッション判定・成否・ターン終了
# =====================================================================================================


@pytest.mark.parametrize(
    ("n", "t98", "t21", "expected"),
    [
        (2, 2, 0, 0), (2, 0, 0, 1), (2, 1, 0, 1),
        (4, 0, 0, 0), (4, 1, 0, 1), (4, 2, 0, 0),
        (3001, 2, 0, 0), (3002, 0, 0, 1),
        # 3003:78 `98 == 2 || (98 == 0 && (21 & 3) || (21 & 4) || (21 & 5) || (21 & 6))`：&&／|| 同優先度・左結合
        (3003, 1, 0, 1), (3003, 1, 2, 0), (3003, 0, 1, 0), (3003, 2, 0, 1), (3003, 0, 8, 1), (3004, 2, 1, 0),
    ],
)
def test_mission_checker(ctx, n, t98, t21, expected):
    st = ctx.state
    st.flag[45], st.tflag[98], st.tflag[21] = n, t98, t21
    assert raid._CHECKER[n](ctx) == expected


def test_mission_success_2(ctx):
    st = ctx.state
    st.flag[45] = 2
    money = st.money
    raid.mission_check(ctx, 1)
    assert st.money == money + 5000 and st.flag[853] == 3
    assert st.flag[60] == 110002
    assert "　報酬として政府から$5000入手した！" in texts(ctx.out)


@pytest.mark.parametrize(("t98", "f60"), [(2, 120003), (0, 100003)])
def test_mission_failure_3(ctx, t98, f60):
    """3:163–165 `FLAG:60 = 100000 + (TFLAG:98 == 0 ? 0 # 20000) + FLAG:45`。"""
    st = ctx.state
    st.flag[45], st.tflag[98] = 3, t98
    raid.raid_mission_failure(ctx)
    assert st.flag[60] == f60
    assert texts(ctx.out)[-1] == "　救出ミッションに失敗しました……"


def test_mission_news_not_overwritten(ctx):
    st = ctx.state
    st.flag[45], st.flag[60] = 5, 7
    raid.mission_check(ctx, 1)
    assert st.flag[60] == 7
    assert st.money == 5000 + 7000  # 5:419


@pytest.mark.parametrize(("turn", "v0", "cleared"), [(7, 3, True), (6, 3, False), (9, 0, False)])
def test_turnend_3003(ctx, turn, v0, cleared):
    st = ctx.state
    st.flag[45] = 3003
    st.tflag[0] = turn
    st.charas[1].tcvarn[0] = v0
    st.flag[70], st.flag[71] = 4, 2
    raid.event_battle_turnend(ctx)
    assert (st.flag[70], st.flag[71]) == ((0, 0) if cleared else (4, 2))


def test_turnend_3004_shower(ctx):
    """3004:343 TFLAG:0 % 3 == 0 で白濁シャワー（性耐性 MAX(/7, 15) + RAND:3）。"""
    st = ctx.state
    st.flag[45] = 3004
    st.tflag[0] = 3
    c = st.charas[1]
    c.tcvarn[0] = 0
    st.rng = ByN({3: [0]})
    raid.event_battle_turnend(ctx)
    assert c.base[2] == 198 - 28
    st.tflag[0] = 4
    raid.event_battle_turnend(ctx)
    assert c.base[2] == 170


def test_event_train_keeps_event_setup(ctx):
    """BATTLE_TRAIN.ERB:16–27：FLAG:45 > 0 ならシチュエーション・TCVARn・ターン上限を初期化しない。"""
    st = ctx.state
    _prep(ctx, 3002)
    st.temp.battle_situation = "撤退不可,空中不可,"
    st.temp.turn_limit = 15
    st.charas[1].tcvarn[0] = 1
    st.flag[11] = 1
    st.rng = GameRng(5)
    train.update_in_begin_train(st)
    train.event_train(ctx)
    assert st.temp.battle_situation == "撤退不可,空中不可,"
    assert st.temp.turn_limit == 15
    assert st.charas[1].tcvarn[0] == 1


# =====================================================================================================
# 整合：Web session で救援／襲撃 1 例ずつ走り切り、SHOP に戻って存讀檔
# =====================================================================================================


def _session(data, seed):
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(seed))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』
    s.input(1)  # HEROINE_PRESET [1] 基本セット
    s.state.day[0] = 3
    return s


def _play(s, policy, limit=5000):
    for i in range(1, s.state.charanum):
        s.input(i)
        s.input(103)
    mark = len(s.out.lines)
    s.input(100)
    if s.phase == Phase.ACTION_CONFIRM:
        s.input(9)
    n = 0
    while s.phase != Phase.SHOP:
        assert s.phase != Phase.HALTED, [ln.text for ln in s.out.lines[-5:]]
        new = s.out.lines[mark:]
        buttons = [v for ln in new for (_, v) in ln.buttons]
        mark = len(s.out.lines)
        s.input(policy.choice(buttons) if buttons else 0)
        n += 1
        assert n < limit


@pytest.mark.parametrize(("kind", "seed"), [("rescue", 11), ("attack", 12)])
def test_session_raid_roundtrip(data, monkeypatch, kind, seed):
    seen: list = []

    def forced(ctx):
        ctx.state.temp.battle_situation = ""
        seen.append(kind)
        if kind == "rescue":
            ctx.state.time = 0
            return (yield from raid.raid_rescue(ctx))
        return (yield from raid.raid_attack(ctx))

    monkeypatch.setattr(turnend, "raid_hantei", forced)
    s = _session(data, seed)
    st = s.state
    policy = random.Random(seed)
    # 救援は [0] 助けに行く を選ぶまで（:151）ターンを回す
    for _ in range(20):
        before60 = st.flag[60]
        boss = sum(c.exp[data.index_of("EXP", "ボス経験")] for c in st.charas)
        _play(s, policy)
        fought = sum(c.exp[data.index_of("EXP", "ボス経験")] for c in st.charas) > boss
        if fought:
            break
    assert fought and seen
    assert st.flag[45] == 0  # SHOP_TURNEND.ERB:59–63
    if kind == "rescue":
        assert st.flag[60] != before60 or before60 != 0  # SUCCESS／FAILURE がニュース番号を設定（未設定なら）
    loaded, _ = load_from_file(Path(s.save_dir) / "save99.json")
    assert loaded.flag[45] == 0
    assert [c.base[0] for c in loaded.charas] == [c.base[0] for c in st.charas]
    assert loaded.flag[852] == st.flag[852]
