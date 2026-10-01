"""S12：ゲームオーバーモード（全滅／ソロの洗脳・取り込まれ結局の後も続行する）。

expected は ERB 原文から推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解）。
- GAMEMODE.ERB = `ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB`
- ENDING.ERB = `ゲーム内_イベント発生/エンディング/ENDING.ERB`、PRISON.ERB = `ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB`
- SHOP.ERB／SHOP_TURNEND.ERB = `インターミッション画面/`、定数 = `DIM.ERH`:40–92
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import ending, party, shop, turnend
from eragvt.game.action import Ctx
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.prison import commands, event
from eragvt.game.session import GameSession, Phase
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"

# DIM.ERH:83–92 モードオプション
NORMAL = 0b00000000010
SOLO = 0b00000001010


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def catalog(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1, TIME=0, TARGET=1（紅葉）
    return Ctx(s, data, TextOutput(), NullNarrationService())


@pytest.fixture
def comable(monkeypatch):
    rec = []
    monkeypatch.setattr(commands, "prison_comable", lambda ctx, arg: rec.append(arg))
    return rec


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def imprison(st: GameState, who: int, boss: int = 1) -> None:
    """敗北直後（BATTLE_COM_AFTER.ERB:1031–1034：CFLAG:0 = 1、CFLAG:20 = FLAG:10、CFLAG:21 = FLAG:11）。"""
    c = st.charas[who]
    c.cflag[0] = 1
    c.cflag[20] = 0
    c.cflag[21] = boss


# --- CHANGE_GAMEOVER_MODE／CHECK_GAMEOVER_F／GAME_MODE_CHECK(_F)（GAMEMODE.ERB:112–137）------------------


@pytest.mark.parametrize(
    ("flag0", "day", "time", "day2"),
    [
        (NORMAL, 7, 1, 15),  # :113 FLAG:0 = 0、:114 DAY:2 = DAY*2+TIME
        (SOLO, 12, 0, 24),
        (0b1110010, 1, 1, 3),  # FREEPLAY
    ],
)
def test_change_gameover_mode(ctx, flag0, day, time, day2):
    st = ctx.state
    st.flag[0], st.day[0], st.time = flag0, day, time
    st.day[1] = 5
    shop.change_gameover_mode(st)
    assert st.flag[0] == 0
    assert st.day[2] == day2
    assert (st.day[0], st.day[1], st.time) == (day, 5, time)  # 他は変えない
    assert shop.check_gameover(st)


@pytest.mark.parametrize(
    ("flag0", "mode_f", "gameover"),
    [
        (0, 0, True),  # MODE_GAMEOVER = 0（DIM.ERH:40）、モードオプション:0 = 0
        (0b10, 1, False),  # NORMAL
        (0b1010, 2, False),  # SOLO
        (0b100, 3, False),  # HARDCORE
        (0b10010, 4, False),  # SURVIVAL
        (0b1110010, 5, False),  # FREEPLAY
        (0b111110010, 6, False),  # SANDBOX
        (0b11000000010, 7, False),  # INSTANT
        (0b11, -1, False),  # カスタム（一致なし → :137 RETURNF -1）
        (64, -1, False),  # GAME_MODE_CHECK_F は FLAG:906 を見ない
    ],
)
def test_game_mode_check_f(ctx, flag0, mode_f, gameover):
    st = ctx.state
    st.flag[0] = flag0
    assert shop.game_mode_check(st) == mode_f  # :131–137
    assert shop.check_gameover(st) is gameover  # :116–118


@pytest.mark.parametrize(
    ("flag0", "flag906", "mode"),
    [
        (0, 0, 0),
        (0, 1, -1),  # :127 FLAG:906 ≠ 0 なら各モードに | 64 → 0 はどれとも一致しない
        (64, 1, 0),
        (0b10 | 64, 1, 1),
        (0b10, 1, -1),
        (0b10 | 64, 0, -1),
    ],
)
def test_game_mode_check_proc(ctx, flag0, flag906, mode):
    st = ctx.state
    st.flag[0], st.flag[906] = flag0, flag906
    assert shop.game_mode_check_proc(st) == mode  # :124–130


def test_save_info_gameover(ctx):
    """@SAVEINFO（オープニング処理.ERB:583–614）は CALL GAME_MODE_CHECK（:586）→ モードネーム:0 = "GAMEOVER"（DIM.ERH:51）。"""
    st = ctx.state
    shop.change_gameover_mode(st)
    assert shop.save_info(st, ctx.data).startswith("GAMEOVERモード ")
    st.flag[906] = 1
    assert shop.save_info(st, ctx.data).startswith("☆カスタムモード")  # :590–591 CASEELSE


# --- ENDING_1／4／5 の後はゲームオーバーモードへ（ENDING.ERB:295–302、:553–563、:645–654）-----------------


def test_ending_1_enters_gameover_mode(ctx):
    st = ctx.state
    for i in (1, 2, 3):
        imprison(st, i)
    st.target = 1
    st.day[0], st.time = 9, 1
    ending.ending_1(ctx)  # 例外なしで呼び出し元へ戻る
    t = texts(ctx.out)
    i = t.index("　　ゲームオーバーモードに移行します。")  # :295
    assert t[i + 1] == "　（全キャラが凌辱され続け、終わりはありません。飽きたら終了しましょう）"  # :296 PRINTW
    assert st.flag[0] == 0 and st.day[2] == 19  # :299 CHANGE_GAMEOVER_MODE
    assert st.flag[999] == -998  # :300
    assert ctx.out.lines[-1].wait  # :302 FORCEWAIT


def test_prison_solo_brainwash_ending_4_breaks_loop(ctx, comable):
    """ソロで洗脳（PRISON.ERB:335–371）→ ENDING_4 → DRAWLINE・RETURN（:368–370）→ FLAG:999 == -998 で PRISON のループを抜ける（:32–33）。"""
    st = ctx.state
    st.flag[0] = SOLO
    st.flag.set_bit(804, 1, True)  # CONFIG_CHECK_PRISON_F(1) 洗脳／悪堕ち ON
    for i in (1, 2):
        imprison(st, i)
    c = st.charas[1]
    c.cflag[31] = 3
    c.cflag[30] = 1000  # > CHECK_CONTAMINATION
    c.cflag[23] = 5
    st.rng = FixedRng([99, 0, 0] + [0] * 10)
    event.prison(ctx)
    t = texts(ctx.out)
    assert c.cflag[0] == 2  # :341
    assert "　　ＧＡＭＥ　ＯＶＥＲ" in t
    assert (st.flag[0], st.flag[999], st.day[2]) == (0, -998, 2)  # DAY 1・昼 → 1*2+0
    assert c.cflag[23] == 5  # :386 には来ない（:370 RETURN）
    assert not any("の尖兵となった" in x for x in t)  # :373 には来ない
    assert st.charas[2].cflag[31] == 0  # :32–33 BREAK：2 人目の PRISON_EVENT は無い
    assert comable == [0]


def test_prison_solo_lost_ending_5(ctx, comable):
    """ソロで取り込まれ（:397–421）→ ENDING_5 → RETURN（CFLAG:23 は戻さない）。"""
    st = ctx.state
    st.flag[0] = SOLO
    imprison(st, 1)
    c = st.charas[1]
    c.cflag[31] = 19
    c.cflag[23] = 5
    st.rng = FixedRng([99, 0, 0, 1])  # :295 ソロ・5 日超の脱出判定 RAND:4 = 1（脱出しない）
    event.prison(ctx)
    assert c.cflag[0] == 9
    assert "　　ＧＡＭＥ　ＯＶＥＲ" in texts(ctx.out)
    assert (st.flag[0], st.flag[999]) == (0, -998)
    assert c.cflag[23] == 5  # :422 には来ない


# --- @PRISON（PRISON.ERB:3–34）：ゲームオーバーモードでは全キャラが対象 ---------------------------------


@pytest.mark.parametrize(
    ("flag0", "flag999", "states", "processed", "flag999_after"),
    [
        (0, -998, (1, 2, 9), (1, 2, 3), 0),  # :5–8 で 0 に戻し、:13 CHECK_GAMEOVER_F() == 1 → 全員
        (0, 0, (2, 3, 9), (1, 2, 3), 0),
        (NORMAL, -998, (1, 2, 9), (1,), 0),  # 通常モード：CFLAG:0 == 1 のみ
        (NORMAL, 0, (0, 1, 1), (2, 3), 0),
    ],
)
def test_prison_targets_in_gameover_mode(ctx, comable, flag0, flag999, states, processed, flag999_after):
    st = ctx.state
    st.flag[0], st.flag[999] = flag0, flag999
    for i, s in zip((1, 2, 3), states):
        imprison(st, i)
        st.charas[i].cflag[0] = s
    st.rng = FixedRng([10, 0] * 3)  # :116 ルーチン → RAND:100 = 10（<12 → C 中心）、汚染 +3
    event.prison(ctx)
    assert st.flag[999] == flag999_after
    assert tuple(i for i in (1, 2, 3) if st.charas[i].cflag[31] == 1) == processed  # :165
    assert [st.charas[i].cflag[0] for i in (1, 2, 3)] == list(states)  # 陥落判定は CFLAG:0 == 1 のみ（:187）
    assert texts(ctx.out).count("・・・・・・・・・") == 1


@pytest.mark.parametrize(
    ("cflag0", "gameover", "present", "absent"),
    [
        # 地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE:225–240
        (2, True, "洗脳され、逆らうことを許されない紅葉は", None),
        (3, True, "自ら触手の孕み妻となった紅葉は期待に瞳を潤わせながら、", None),
        (9, True, "触手の奥深くに取り込まれ、肉壁に同化しつつある紅葉は", None),
        (2, False, None, "洗脳され、逆らうことを許されない紅葉は"),
        (9, False, None, "触手の奥深くに取り込まれ、肉壁に同化しつつある紅葉は"),
        # :247 `CFLAG:31 < 6 && CHECK_GAMEOVER_F() == 0` は通常モードのみ
        (1, False, "まだ完全に脱出を諦めていない・・・", None),
        (1, True, None, "まだ完全に脱出を諦めていない・・・"),
    ],
)
def test_message_prison_prisentence_gameover_branches(data, catalog, cflag0, gameover, present, absent):
    s = GameState.new(data, rng=GameRng(5))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    c = s.charas[1]
    imprison(s, 1)
    c.cflag[0] = cflag0
    c.cflag[31] = 3
    if gameover:
        shop.change_gameover_mode(s)
    ctx = Ctx(s, data, TextOutput(), catalog)
    assert catalog.run_function(ctx, "MESSAGE_PRISON_PRISENTENCE", [])
    t = texts(ctx.out)
    assert t[0] == "薄暗い闇の中───"
    if present:
        assert present in t
    if absent:
        assert absent not in t
    assert c.cflag[0] == cflag0


# --- SHOP.ERB：ゲームオーバーモードの画面と入力 ------------------------------------------------------


def _buttons(out: TextOutput) -> list[int]:
    return [b for ln in out.lines for _, b in ln.buttons]


@pytest.mark.parametrize(
    ("gameover", "shown", "hidden"),
    [
        (False, (100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 120, 130, 150, 160, 200, 300, 700, 800), ()),
        # :133–151 行動選択、:155–161 強化・衣装・メディカル・購入、:163–171 施設・スケジュールを隠す
        (True, (100, 110, 130, 200, 300, 700, 800), (101, 102, 103, 104, 105, 106, 107, 108, 111, 112, 113, 120, 150, 160)),
    ],
)
def test_show_shop_menu_gameover(ctx, gameover, shown, hidden):
    st = ctx.state
    if gameover:
        shop.change_gameover_mode(st)
    out = TextOutput()
    shop.show_shop(st, ctx.data, out, NullNarrationService())
    btns = _buttons(out)
    for v in shown:
        assert v in btns, v
    for v in hidden:
        assert v not in btns, v
    header = [ln.text for ln in out.lines if "インターミッション" in ln.text][0]
    if gameover:
        assert header == "インターミッション [☀昼]  1 日目(月)"  # :405–406 何も表示しない（PRINTL）
    else:
        assert "殲滅猶予" in header


@pytest.mark.parametrize(
    ("value", "gameover", "flag63", "calls"),
    [
        (111, False, 0, True),  # :252–254 CHECK_GAMEOVER_F() == 0 && CHARANUM_ACTIVE()
        (111, True, 0, False),
        (112, True, 0, False),  # :257–259
        (113, False, 1, False),  # :262–264 FLAG:63 == 0
        (113, True, 0, False),
        (120, False, 0, True),  # :267–269
        (120, True, 0, False),
        (150, False, 0, True),  # :276–278
        (150, True, 0, False),
        (110, True, 0, True),  # :247–249 は無条件
    ],
)
def test_usershop_submenu_guard(ctx, value, gameover, flag63, calls):
    st = ctx.state
    st.flag[63] = flag63
    if gameover:
        shop.change_gameover_mode(st)
    assert shop.usershop_calls_submenu(st, value) is calls


def test_usershop_status_limits_target(ctx):
    st = ctx.state
    st.target = 0  # MASTER
    assert shop.usershop_calls_submenu(st, 110)
    assert st.target == 1  # :248 LIMIT(TARGET, 1, CHARANUM-1)


def test_usershop_set_action_and_confirm_in_gameover(ctx):
    """USERSHOP_SET_ACTION:617 は何もしない。USERSHOP_ACTION_CONFIRM:504／:534 の確認は出さず JUMP ACTION_MAIN（:557）。"""
    st = ctx.state
    shop.change_gameover_mode(st)
    before = st.charas[1].cflag[100]
    out = TextOutput()
    shop.usershop_set_action(st, ctx.data, out, 101, 0)
    assert st.charas[1].cflag[100] == before and out.lines == []
    for f40 in (0, 1, 2):
        st.flag[40] = f40
        assert shop.action_confirm_prompt(st, ctx.data, TextOutput()) == "begin"


# --- SHOP_TURNEND.ERB：:186、:199、:380、:461 ／ SET_PARTYMEMBER.ERB:10 ／ ENDING.ERB:9・:74 ---------------------


@pytest.mark.parametrize(("gameover", "income"), [(False, True), (True, False)])
def test_event_shop_income_and_news(ctx, monkeypatch, gameover, income):
    st = ctx.state
    rec = []
    monkeypatch.setattr(turnend, "calc_income_expend", lambda c: rec.append(1))
    st.time = 1  # :172 INVERTBIT で昼になり DAY 1 → 2
    st.flag[60] = 0
    if gameover:
        shop.change_gameover_mode(st)
    list(turnend.event_shop_normal(ctx))
    assert st.day[0] == 2
    assert bool(rec) is income  # :186–188
    assert st.flag[60] == (10001 if gameover else 0)  # :199–200（FLAG:101 = 0）


def test_daily_defence_and_popularity_in_gameover(ctx):
    st = ctx.state
    shop.change_gameover_mode(st)
    st.flag[852] = 4000
    st.flag[853] = 150
    st.rng = FixedRng([])  # 乱数を引かない
    turnend.daily_defence_change(ctx)
    assert st.flag[852] == 0  # :380–383
    turnend.daily_popularity_change(ctx)
    assert st.flag[853] == 100  # :459 LIMIT のみ、:461–462 RETURN
    assert texts(ctx.out) == []


def test_set_partymember_no_pregnant_message_in_gameover(ctx, monkeypatch):
    st = ctx.state
    monkeypatch.setattr(party, "check_pregnant", lambda data, st, i: True)
    st.charas[1].cflag[100] = 101
    shop.change_gameover_mode(st)
    party.set_partymember(ctx)
    assert st.charas[1].cflag[100] == 101  # :10–11 何もしない（:12–15 に行かない）
    assert texts(ctx.out) == []


def test_ending_checks_skip_in_gameover(ctx):
    """ENDING.ERB:9 ゲームクリア判定・:74 日数制限判定はゲームオーバーモードでは通らない。"""
    st = ctx.state
    shop.change_gameover_mode(st)
    st.flag[100] = 0
    st.flag[101] = 0
    st.day[0], st.time = 99, 1
    turnend.ending(ctx)  # 例外なし


@pytest.mark.parametrize(
    ("time", "flag852", "states", "rng", "fires"),
    [
        # FORCE_悪堕ちキャラの淫謀.ERB@AKUOTI_ATTACK:5–29
        (0, 0, (3, 1, 1), [19], True),  # 昼 LOCAL 40：MIN(RAND:(SQRT(0)/2+20), 100) = 19 < 40
        (1, 0, (3, 1, 1), [19], True),  # 夜 LOCAL 20：19 < 20（ゲームオーバーモードの防衛力 0 では必ず発生）
        (1, 3600, (3, 1, 1), [20], False),  # SQRT(3600)/2 + 20 = 50 → RAND:50 = 20 は < 20 でない
        (1, 0, (2, 1, 9), [], False),  # 候補なし：RAND を引かない（&& の短絡）
        (0, 3600, (3, 3, 0), [45, 45], False),  # 2 人とも 45 ≥ 40
    ],
)
def test_akuoti_attack_candidates(ctx, monkeypatch, time, flag852, states, rng, fires):
    """候補が 1 人なら RANDCHOOSE_F は RAND:1（= 0）を 1 回引いてその 1 人（:28）→ AKUOTI_EVENT（:29）。"""
    from eragvt.game import akuoti

    st = ctx.state
    st.time = time
    st.flag[852] = flag852
    for i, s in zip((1, 2, 3), states):
        st.charas[i].cflag[0] = s
    called = []
    monkeypatch.setattr(akuoti, "akuoti_event", lambda c: called.append(c.state.flag[111]))
    st.rng = FixedRng(rng + ([0] if fires else []))
    turnend.akuoti_attack(ctx)
    assert called == ([1] if fires else [])
    assert st.rng.snapshot() == []  # 与えた乱数をちょうど使い切る


# --- 整合：全滅 → ENDING_1 → ゲームオーバーモード → TURNEND → SHOP ×2、存讀檔 -------------------------------


def _screen_buttons(s: GameSession) -> list[int]:
    return [p.button for ln in s.screen()[-40:] for p in ln.parts if p.button is not None]


def test_e2e_annihilation_to_gameover_mode(data):
    """桃香・蒼美は取り込まれ済み（CFLAG:0 = 9）、紅葉だけ出撃してギブアップ（BATTLE_COM.ERB:967–975）→ 敗北 →
    BATTLE_TRAIN_AFTER.ERB:527–528 全滅 → ENDING_1 → BEGIN TURNEND → PRISON（全員）→ SHOP。
    常時避妊（CONFIG_CHECK_OTHER_F(2) = FLAG:805 bit2）で受精・苗床出産（未移植）を避ける。"""
    tmp = Path(tempfile.mkdtemp())
    s = GameSession(data, tmp, rng=GameRng(0))
    s.input(0)
    s.input(1)  # 初期セット『特装戦隊』
    st = s.state
    st.flag.set_bit(805, 2, True)
    for i in (2, 3):
        st.charas[i].cflag[0] = 9
        st.charas[i].cflag[21] = 1
    for _ in range(600):
        if s.phase == Phase.SHOP and st.flag[0] == 0:
            break
        if s.phase == Phase.SHOP:
            st.flag[47] = max(st.flag[47], st.flag[46])  # ENCOUNT.ERB:159 ボス遭遇条件
            s.input(1)
            s.input(101)
            s.input(100)
            if s.phase == Phase.ACTION_CONFIRM:
                s.input(9)
        else:
            assert s.phase == Phase.TURN, [ln.text for ln in s.out.lines[-5:]]
            b = _screen_buttons(s)
            s.input(99 if 99 in b else (b[0] if b else 0))
    assert s.phase == Phase.SHOP
    t = [ln.text for ln in s.out.lines]
    assert "全滅しました・・・" in t
    assert "　　ゲームオーバーモードに移行します。" in t
    assert st.flag[0] == 0 and st.flag[999] == 0  # PRISON.ERB:5–8 で -998 → 0
    k = next(c for c in st.charas[1:] if c.callname == "紅葉")
    assert k.cflag[0] == 1 and k.cflag[31] == 1
    lost = [c for c in st.charas[1:] if c.callname != "紅葉"]
    assert all(c.cflag[31] == 1 for c in lost)  # :13 CHECK_GAMEOVER_F() == 1 → CFLAG:0 = 9 も PRISON_EVENT
    assert st.flag[60] == 10001 or st.savestr[20] != ""  # SHOP_TURNEND.ERB:199–200
    assert 101 not in _screen_buttons(s) and 100 in _screen_buttons(s)
    day2 = st.day[2]
    assert day2 > 0
    # 存讀檔往返（FLAG:0・DAY:2 は SAVEDATA）
    snap = st.to_json()
    s.input(200)
    s.input(1)
    s.input(300)
    s.input(1)
    assert s.phase == Phase.SHOP
    assert s.state.to_json() == snap
    st = s.state
    # さらに 2 ターン：[100] → 確認なし（SHOP.ERB:504／:534）→ 全員操作不能 → TURNEND → PRISON → SHOP
    for n in (2, 3):
        s.input(100)
        for _ in range(50):
            if s.phase != Phase.TURN:
                break
            b = _screen_buttons(s)
            s.input(b[0] if b else 0)
        assert s.phase == Phase.SHOP, [ln.text for ln in s.out.lines[-5:]]
        assert all(c.cflag[31] == n for c in st.charas[1:])
        assert st.flag[0] == 0 and st.day[2] == day2
