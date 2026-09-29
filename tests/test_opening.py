"""新遊戲最小路徑（`eragvt.game.opening.event_first`）。

expected 由 ERB 原文逐行推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），不從實作輸出反推。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.opening import _CALL_HEAD, _CALL_TAIL, _CALL_TAIL_DEFAULT, event_first
from eragvt.state import GameRng, GameState


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def st(data):
    s = GameState.new(data, rng=GameRng(12345))
    event_first(s, data)
    return s


# --- 全域 --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "value"),
    [
        (0, 0b10),  # MODE_SELECT:376 FLAG:0 = モードオプション:1（NORMAL, DIM.ERH:85）
        (2, 11),  # SET_LIMIT_DAY:430（NORMAL は補正なし、人数 3 なので :445 も 0）
        (3, 7),  # :95–96 GET_BOSS_ERB_NUM（TENTACLE_BOSS_1..7）
        (1, 7 * 11 + 1 * 10),  # SET_LIMIT_DAY:448–450 FLAG:3*FLAG:2 + FLAG:4*10
        (4, 1),  # :99
        (5, 1),  # 初期セット/0_特捜戦隊.ERB:20
        (7, 1),  # :22
        (8, 3),  # EVENTFIRST:121 +3 → KAI で −3 → SELECT_0 で +3
        (41, 1),  # :286
        (46, 12 * 1 // 3 + 24),  # RESEARCH_QUOTA：撃破数 = 7−7+1 = 1、LOCAL=12 → 28、日数補正 SQRT(0)=0
        (47, 0),
        (50, 1),  # :90
        (51, 1),
        (100, 0b1111111),  # :102–104 REPEAT FLAG:3 SETBIT
        (101, 0),
        (800, 0),  # CONFIG_INIT(1)（CONFIG_初期設定.ERB:17–29）
        (801, 1),
        (802, 1 + 2 + 4 + 8),
        (803, 1 + 2 + 4 + 256),
        (804, 1),
        (805, 2),
        (852, 5000),  # :76
    ],
)
def test_flags(st, index, value):
    assert st.flag[index] == value


def test_money_time_day(st):
    assert st.money == 5000  # :49（裕福な実家なし → +2500 なし）
    assert st.time == 1  # :48
    assert st.day[0] == 0


def test_items(st):
    # :53–59 と :269–283（CFLAG:40/41/42 = 100/200/300、CFLAG:43 = 0 → ITEM:0 = 1）
    assert sorted(k for k, _ in st.item.items()) == [0, 100, 200, 201, 202, 299, 300, 401]


def test_savestr(st):
    assert st.savestr[10] == "特装戦隊"  # 0_特捜戦隊.ERB:21
    assert st.savestr[12] == "特命特捜!"  # :23
    assert st.savestr[11] == ""


def test_mob_flag(st):
    # :36–44 初回起動：TENTACLE_MOB_{n} が存在する n の MOB_FLAG:(n/100):(n%100) = 100
    assert st.mob_flag[(0, 1)] == 100
    assert st.mob_flag[(9, 2)] == 100
    assert st.mob_flag[(4, 1)] == 0  # TENTACLE_MOB_401 は存在しない
    assert len(st.mob_flag) == 16


# --- 角色列表 ----------------------------------------------------------------


def test_chara_list(st):
    # :63–64 SWAP/DEL で MASTER=999、:122 の汎用キャラは KAI（SHOKISET.ERB:28–31）で削除
    assert [c.no for c in st.charas] == [999, 301, 302, 303]
    assert st.target == 3  # :257 最後に TARGET = LOCAL（EVENTSHOP で 1 に戻る）


@pytest.mark.parametrize("i", [1, 2, 3])
def test_common_cflags(st, i):
    c = st.charas[i]
    assert c.cflag[6] == 0  # :145–155 口上設定 0 かつ女性 → 0（女性汎用）
    assert c.cflag[100] == 103  # :165 予定_休憩
    assert c.cflag[240] == i  # CHARA_MAKE_DEFAULT.ERB:242–243
    assert c.cflag[999] == 1  # :265–266
    assert (c.cflag[40], c.cflag[41], c.cflag[42]) == (100, 200, 300)  # CSV:25–27
    assert (c.cflag[2], c.cflag[3], c.cflag[4], c.cflag[5]) == (1, 1, 1, 1)  # INITIALIZE:186–210
    assert c.abl[50] == 1  # FIRSTSETTING_CHARA_CSVFIX:1628–1629


# Chara301赤羽 紅葉.csv の 基礎：体力1400 気力1200 性耐性120 攻撃150 防御130 敏捷160 知性100
# CHARA_MAKE_FINALIZE は 2 回実行される（CHARA_MAKE.ERB:210 と オープニング処理.ERB:135）。
# LEVELSTATUS_UP(B, Lv=1, G) = ((14+95)·B + (5+95)·G) / 100（SQRT(220)=14、TIMES 52×0.1=5）
#  1 回目：体力 G=400+(1400−1000)/5=480 → (109·1400+100·480)/100 = 2006
#          気力 G=440 → 1748、性耐性 Lv'=1/3+1=1、G=10+(120−100)/2=20 → 150
#  2 回目（体力基礎 = 1 回目の BASE）：体力 G=400+1006/5=601 → (109·2006+60100)/100 = 2787
#          気力 G=400+748/5=549 → (109·1748+54900)/100 = 2454、性耐性 G=10+50/2=35 → 198
#  攻撃等（BASE は変化しない）：G=50 → 攻撃 (109·150+5000)/100=213、防御 191、敏捷 224、知性 159
@pytest.mark.parametrize(
    ("attr", "index", "value"),
    [
        ("maxbase", 0, 2787),
        ("maxbase", 1, 2454),
        ("maxbase", 2, 198),
        ("maxbase", 10, 213),
        ("maxbase", 11, 191),
        ("maxbase", 12, 224),
        ("maxbase", 13, 159),
        ("base", 0, 2787),  # FINALIZE:373–375 BASE = MAXBASE
        ("base", 1, 2454),
        ("base", 2, 198),
        ("base", 10, 150),  # 攻撃等の BASE は CSV のまま
        ("base", 50, 2006),  # 体力基礎（2 回目の値）
        ("base", 51, 1748),
        ("base", 52, 150),
        ("maxbase", 20, 8000),  # 射精（CSV 8000 ≥ 1 なので補正なし）
        ("maxbase", 22, 2),  # 空中ダッシュ LIMIT(CSVBASE 2, 0, 8)
        ("base", 91, -1),  # 体格基本値：小柄（素質116）
        ("base", 92, 0),
        ("maxbase", 90, 0),
    ],
)
def test_chara_301_status(st, attr, index, value):
    assert getattr(st.charas[1], attr)[index] == value


def test_chara_303_levelstatus(st):
    # Chara303海野 蒼美.csv 体力1500 気力1300：1 回目 G=500 → (109·1500+50000)/100=2135、
    # 2 回目 G=400+1135/5=627 → (109·2135+62700)/100 = 2954
    c = st.charas[3]
    assert (c.base[50], c.maxbase[0]) == (2135, 2954)
    assert c.base[91] == 1  # 長身（素質117）
    assert c.base[92] == 1  # 巨乳（素質111）


def test_transformation_names(st):
    c = st.charas[1]
    # INITIALIZE:169–211：SAVESTR:11 は空、CALLNAME「紅葉」→ 変身後名
    assert (c.cstr[0], c.cstr[1], c.cstr[2]) == ("紅葉", "紅葉", "特命特捜!")
    # CSTR:3 = SAVESTR:10 + CSTR:0 + CHANGINGCALL_DETAIL（勝気 12 はグループ1）
    head_tail = c.cstr[3][len("特装戦隊紅葉") :]
    assert c.cstr[3].startswith("特装戦隊紅葉")
    assert any(head_tail == h + t for h in _CALL_HEAD for t in _CALL_TAIL_DEFAULT)
    # 桃香は楽天家(17) → グループ3
    t3 = dict(_CALL_TAIL)[(13, 17, 19, 23, 25)]
    rest = st.charas[2].cstr[3][len("特装戦隊桃香") :]
    assert any(rest == h + t for h in _CALL_HEAD for t in t3)


def test_weapon_decode(st):
    # Chara301 CSV `CSTR,15,ツラヌキ・ロッド(近)// //通常` → CSTR:5 = 名前、戦闘スタイル 0、CSTR:15 は空に
    c = st.charas[1]
    assert (c.cstr[5], c.cstr[6], c.cstr[7]) == ("ツラヌキ・ロッド(近)", "ツラヌキ・ロッド(中)", "ツラヌキ・ロッド(遠)")
    assert c.cstr[15] == "" and c.cdflag[(1, 500)] == 0


def test_color_conversion(st):
    # CSVFIX:1647–1656：CSTR:36 が空 → 34→36、32→34、33→35、36→37
    c = st.charas[1]
    assert (c.cstr[34], c.cstr[35], c.cstr[36], c.cstr[37]) == ("茶", "茶", "肌色", "肌色")


def test_relation_not_converted(data):
    # CONVERT_RELATION は HEROINE_PRESET の [30] でのみ呼ばれる（オープニング処理.ERB:661）→ 最小路徑では CSV のまま
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data)
    for c in s.charas[1:]:
        assert dict(c.relation.items()) == data.charas[c.no].relation
