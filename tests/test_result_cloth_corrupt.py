"""S21：共用 RESULT 陣列（照原作的殘值）＋触手拘束具＋悪堕ち容姿＋防衛力為負的裁決（Part D）。

expected 由 ERB 原文推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），引擎語意附
`reference/emuera-1824/Emuera/` 的行號。不從實作輸出反推。
"""

from __future__ import annotations

import json

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import akuoti, corruption, party, shop, turnend
from eragvt.game.action import Ctx
from eragvt.game.battle import cheers, core, palam, restraint, sexcom, source_check
from eragvt.game.battle.ablup import _abl_up_ex
from eragvt.game.battle.hantei import act_hantei_chara_to_tentacle
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.game.prison import commands, event
from eragvt.game.prison.event_palam import event_palam_hosei
from eragvt.narration import runtime as rt
from eragvt.narration.extract import ExtractContext, parse_function, read_logical_lines
from eragvt.narration.runtime import Env, Frame, Interp
from eragvt.narration.service import CatalogNarrationService
from eragvt.narration.windowlib import WindowManager, py_functions
from eragvt.state import FixedRng, GameRng, GameState, dump_save, load_save
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


@pytest.fixture
def ctx(data):
    """初期セット『特装戦隊』（キャラ 1〜3）、TARGET = 1。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    s.savestr[13] = "BOSS"
    s.flag[110] = 0
    return Ctx(s, data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def T(data, n):
    return data.index_of("TALENT", n)


def A(data, n):
    return data.index_of("ABL", n)


def E(data, n):
    return data.index_of("EXP", n)


def pad(rolls: list[int], n: int = 60) -> FixedRng:
    return FixedRng(list(rolls) + [0] * n)


# =====================================================================================================
# Part A：共用 RESULT（GameState.result）
# =====================================================================================================


@pytest.mark.parametrize(
    ("before", "values", "after"),
    [
        # 多値 RETURN は与えた個数だけ RESULT:0〜 に書き、残りは保留（VariableEvaluator.cs@SetResultX:1732–1740）
        ({0: 9, 1: 8, 5: 55, 11: 77}, (1, 2), {0: 1, 1: 2, 5: 55, 11: 77}),
        ({3: 3, 12: 12}, tuple(range(10, 22)), {i: 10 + i for i in range(12)} | {12: 12}),
        ({0: 5}, (0,), {}),  # 0 を書けば疎配列からは消える（値は 0）
    ],
)
def test_set_result_x_keeps_untouched_slots(data, before, values, after):
    st = GameState.new(data)
    for k, v in before.items():
        st.result[k] = v
    st.set_result_x(*values)
    assert {i: st.result[i] for i in range(30) if st.result[i]} == after


def test_result_saved_and_migrated(data):
    """RESULT（0x0A）は存檔対象（VariableToken.cs:74–77、VariableData.cs@SaveToStream:663–674）→ 存讀檔で保持。
    版本 1 の存檔（RESULT なし）は全 0 で読める。"""
    st = GameState.new(data)
    st.result[3] = 33
    st2, _ = load_save(dump_save(st))
    assert st2.result[3] == 33
    obj = json.loads(dump_save(st))
    assert obj["version"] == 2
    obj["version"] = 1
    del obj["state"]["result"]
    st3, _ = load_save(json.dumps(obj).encode())
    assert st3.result[3] == 0


def _run_fd(svc, ctx, src: str):
    ectx = ExtractContext({}, {}, lambda n: False)
    fd = parse_function(ectx, "t.ERB", read_logical_lines(src.encode("utf-8")))
    it = Interp(svc.catalog, Env(ctx.state, ctx.data, ctx.out, {}, {}, ctx))
    try:
        it.exec_block(fd.body, Frame(fd, "F"))
    except rt._Return:
        pass
    return it


def test_narration_result_is_shared(svc, ctx):
    """口上・地の文 catalog の RESULT も共用：多値 RETURN（Instraction.Child.cs@RETURN_Instruction:2006–2023）、
    `VARSET RESULT`（全要素 0）、代入。"""
    st = ctx.state
    st.result[7] = 70
    _run_fd(svc, ctx, "@F\nRETURN 1, 2, 3\n")
    assert [st.result[i] for i in range(8)] == [1, 2, 3, 0, 0, 0, 0, 70]
    _run_fd(svc, ctx, "@F\nRESULT:4 = 44\n")
    assert st.result[4] == 44 and st.result[7] == 70
    _run_fd(svc, ctx, "@F\nVARSET RESULT\n")
    assert all(st.result[i] == 0 for i in range(10))


def test_narration_function_end_sets_only_result0(svc, ctx):
    """関数終端まで流れ落ちると RESULT:0 = 0 のみ（Process.ScriptProc.cs:61–67）。"""
    st = ctx.state
    st.result[0] = 5
    st.result[1] = 11
    it = Interp(svc.catalog, Env(st, ctx.data, ctx.out, {}, {}, ctx))
    # MESSAGE_STAIN_CORRUPTED_HAIR_COLOR（地の文/MESSAGE_AKUOTI.ERB:73–76）は RETURN なし
    it.call("MESSAGE_STAIN_CORRUPTED_HAIR_COLOR", [1])
    assert st.result[0] == 0 and st.result[1] == 11


def test_window_functions_clear_result(svc, ctx):
    """WINDOW_* は WINDOW_MGR の `VARSET RESULT, 0`（WindowDrawer.ERB:330）を通り RESULT:1 以降は書かない → 全 0。"""
    st = ctx.state
    st.result[1] = 9
    st.result[4] = 4
    it = Interp(svc.catalog, Env(st, ctx.data, ctx.out, {}, {}, ctx))
    py_functions(WindowManager(), ctx.out)["WINDOW_CREATE"](it, [0, 0, 0, 10, 3, 0])
    assert all(st.result[i] == 0 for i in range(10))


@pytest.mark.parametrize("residue", [(5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), (0, 250, 60, 80, 3, 5, 1, 2, 100, 100, 100, 100)])
def test_tentacle_access_prison_akuoti_returns_residue(ctx, residue):
    """COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:314–343 に CFLAG:20 == 2 の分岐はない → 関数終端で RESULT:0 = 0、
    RESULT:1〜11 は前の値（照原作：使用者裁決 2026-10-02）。"""
    st = ctx.state
    c = st.charas[2]
    c.cflag[20] = 2
    st.set_result_x(*residue)
    r = event.tentacle_access_prison(ctx, 2, "PALAM_HOSEI")
    assert r == (0,) + residue[1:]
    assert st.result[0] == 0


def test_prison_akuoti_palam_hosei_reads_previous_prisoner(ctx, data):
    """S20 調査の代表路徑 a)：同じ PRISON ループで先にボス 1 に幽閉されたキャラ A を処理 → 悪堕ちキャラに幽閉された B の
    EVENT_PALAM_HOSEI（EVENT_PALAM_UP.ERB:134–140 `UP:PCOUNT = RESULT:PCOUNT / 100`）が読む RESULT は
    - :8〜11 = A の :136 TENTACLE_ACCESS_PRISON（:327）＝ボス 1 の PALAM_HOSEI（TENTACLE_BOSS_1_Ｃ触手.ERB:100–125：快Ｃ 120、他 100）
    - :2〜7 = A の PRISON_GAPING → SET_TENTACLE_SIZE（GAPING.ERB:1123–1128）→ TENTACLE_BOSS_1_TENTACLE_SIZE（:202–220、
      ARG = -TFLAG:10 = 0 ≠ 3）の 8 値 RETURN の 2〜7：Ａ 60、Ｂ 80、本数 RAND:3+1、RAND:5+1、RAND:5+1、RAND:3+1
    - :0〜1 = PRISON_GAPING の `RETURN ARG:2, ARG:3`（GAPING.ERB:1336）、その後 B の :136 で RESULT:0 = 0。"""
    st = ctx.state
    a, b = st.charas[1], st.charas[2]
    for c in (a, b):
        c.cflag[0] = 1
    a.cflag[20], a.cflag[21] = 0, 1
    b.cflag[20], b.cflag[21] = 2, 3
    st.target = 1
    st.tflag[10] = 0
    st.rng = pad([2, 4, 0, 1])  # 本数：3、5、1、2（以降のサイズ計算・SET_TENTACLE_SIZE_R の RAND は 0）
    event.tentacle_access_prison(ctx, 1, "PALAM_HOSEI")
    assert [st.result[i] for i in range(12)] == [120] + [100] * 11
    commands.prison_gaping(ctx, 0, 0, 7, 250)
    assert [st.result[i] for i in range(12)] == [7, 250, 60, 80, 3, 5, 1, 2, 100, 100, 100, 100]
    st.target = 2
    event_palam_hosei(ctx, 1)
    up = st.temp.up
    # UP:0〜11（PALAM 番号 0〜11、PCOUNT がそのまま添字：prison.md「照原作移植的怪處」）＝ RESULT / 100
    assert [up[i] for i in range(12)] == [0, 2, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
    assert st.result[0] == 0


def test_prison_gaping_akuoti_parasite_writes_abl(ctx, data):
    """路徑 b)：悪堕ちキャラ（寄生持ち）に幽閉されたキャラ自身の PRISON_GAPING：SET_TENTACLE_SIZE（GAPING.ERB:1093–1101）で
    RESULT:0〜3 = 悪堕ちキャラ（ARG:3 = FLAG:111：:1302）の ABL:0〜3 * 10 + 50、RESULT:4〜7 = 1、関数終端で RESULT:0 = 0、
    その後 :1336 `RETURN ARG:2, ARG:3`。"""
    st = ctx.state
    c, e = st.charas[1], st.charas[3]
    c.cflag[20] = 2
    st.flag[111] = 3
    e.talent[T(data, "寄生")] = 1
    for i, v in enumerate((1, 2, 3, 4)):
        e.abl[i] = v
    st.target = 1
    st.rng = pad([])
    commands.prison_gaping(ctx, 0, 0, 5, 6)
    assert [st.result[i] for i in range(8)] == [5, 6, 80, 90, 1, 1, 1, 1]  # ABL:2 = 3、ABL:3 = 4


def test_inmon_recovery_writes_result1(ctx, data):
    """SHOP_TURNEND.ERB:859–860 は RESULT:1 への直接代入（以降 :862 TATTOO_ACCESS は RESULT:0 だけ）。"""
    from eragvt.game.tattoo import PROG_UNIT

    st = ctx.state
    c = st.charas[1]
    st.flag[850] = 0  # CONFIG_CHECK_MANIAC_F(9) = 1 - bit9（基本セットは全て 1）
    c.cflag[0] = 0
    c.talent[T(data, "触手の虜")] = 1
    c.cflag[32] = 50 * PROG_UNIT
    st.rng = pad([3, 0, 0])  # RAND:(LIMIT(SQRT(100 - 50), 1, 8)) = RAND:7 → 3、欲望 0・触手中毒 0 → RAND:1 は 0
    turnend.inmon_recovery(ctx, 1)
    assert st.result[1] == (2 + 3) * 3 // 4  # :859–860 = 3


@pytest.mark.parametrize(
    ("fn", "n"),
    [
        ("sex_comex", 12),  # SEX_COMEX.ERB:338 RETURN L_VAR:0〜11
        ("sex_comex_random", 2),  # SEX_COMEX.ERB:123
        ("hantei", 2),  # COMMON_BATTLE_HANTEI.ERB:410／:412
        ("abl_up_ex", 4),  # ABL_UP_CHECK.ERB:1235
        ("exp_sh", 4),  # COMMON_PRISON.ERB:71
    ],
)
def test_multi_return_writers(ctx, fn, n):
    """移植済みの多値 RETURN は戻り値と同じ値を RESULT:0〜n-1 に書き、RESULT:n 以降は触らない。"""
    st = ctx.state
    st.flag[11] = 1
    st.result[n] = 999
    st.rng = pad([], 200)
    if fn == "sex_comex":
        r = sexcom.sex_comex(ctx, 0, 0, 15)
    elif fn == "sex_comex_random":
        r = sexcom.sex_comex_random(ctx, 0)
    elif fn == "hantei":
        r = act_hantei_chara_to_tentacle(ctx, "ATTACK_RANGE_SHORT")
    elif fn == "abl_up_ex":
        r = _abl_up_ex(ctx, st.charas[1])
    else:
        r = commands.common_prison_exp_sh(ctx, 1, 2, 3, 4)
    assert [st.result[i] for i in range(n)] == list(r)
    assert st.result[n] == 999


def test_tentacle_sakusei_akuoti_uses_result0(ctx, data):
    """悪堕ちキャラ戦の TENTACLE_SAKUSEI（TENTACLE_SYASEI.ERB:585–586）：TENTACLE_BOSS_0_SAKUSEI が無く TRYCALLFORM 不発 →
    `RETURN RESULT` は呼び出し時の RESULT:0。ペニスあり経路では直前の TENTACLE_SYASEI_POINT（:568）の LOCAL:0。"""
    from eragvt.game.battle import syasei

    st = ctx.state
    st.flag[110] = 1
    st.flag[111] = 3
    st.flag[11] = 0
    st.flag[13] = 100000
    st.flag[14] = 1000
    c = st.charas[1]
    c.base[0] = 100
    st.result[0] = 250
    syasei.tentacle_sakusei(ctx, 1000, 250, 0, 0, 0)
    # ARG = (1000 - 500) / 10 + 500 + 技巧*150 = 550（技巧 0）→ 550 * 250 / 100 = 1375
    assert st.flag[13] == 100000 - (550 + 150 * c.abl[A(data, "技巧")]) * 250 // 100
    assert [st.result[i] for i in range(4)] == [250, 0, 0, 0]  # :607 RETURN ARG:1〜4


# =====================================================================================================
# Part B：触手拘束具（CFLAG:42 = 400）
# =====================================================================================================


def _cloth_broken(ctx):
    st = ctx.state
    c = st.charas[1]
    c.cflag[1] = 0
    c.tcvarn[20], c.tcvarn[21] = 100, 0  # アウター耐久 0
    c.tcvarn[24], c.tcvarn[25] = 100, 0  # インナー耐久 0
    st.temp.cloth[2] = 50
    st.temp.cloth[4] = 50
    return c


@pytest.mark.parametrize(
    ("flag45", "roll", "worn"),
    [
        (0, 34, True),  # LOCAL:1 = 35 - 0（SUBEVENT_BATTLEE.ERB:83）、RAND(100) = 34 < 35
        (0, 35, False),
        (1, 22, True),  # イベント戦（FLAG:45 > 0）は 35 - 12 = 23
        (1, 23, False),
    ],
)
def test_settentaclecloth(ctx, flag45, roll, worn):
    """SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_SETTENTACLECLOTH:71–89：衣装が壊れている（耐久 0）とき確率で CFLAG:42 = 400、
    地の文 MESSAGE_SUBEVENT_BATTLE_SETTENTACLECLOTH。"""
    st = ctx.state
    c = _cloth_broken(ctx)
    st.flag[45] = flag45
    st.rng = FixedRng([roll])
    source_check._settentaclecloth(ctx)
    assert (c.cflag[42] == 400) is worn
    assert any("SETTENTACLECLOTH" in x for x in texts(ctx.out)) is worn


def test_settentaclecloth_needs_broken_cloth(ctx):
    """:77–81：アウターが残っていれば（PERCENT_CAL ≥ CLOTH_OUTER_DEF かつ耐久 > 0）LOCAL = 0 → RAND を引かずに何もしない。"""
    st = ctx.state
    c = _cloth_broken(ctx)
    c.tcvarn[21] = 100
    st.rng = FixedRng([])
    source_check._settentaclecloth(ctx)
    assert c.cflag[42] != 400


def test_settentaclecloth_message_catalog(data, svc):
    """地の文/MESSAGE_SUBEVENT.ERB:22–48 を catalog で実行（全裸／半裸の分岐：:24–28）。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    ctx = Ctx(s, data, TextOutput(), svc)
    c = _cloth_broken(ctx)
    s.rng = pad([0])
    source_check._settentaclecloth(ctx)
    t = texts(ctx.out)
    assert c.cflag[42] == 400
    assert t[0:2] == ["あられもない", "全裸の姿で息を切らす" + s.charas[1].callname + "・・・"]  # :23 PRINTL、:25 PRINT、:29


def test_acttentaclecloth(ctx, data, monkeypatch):
    """SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_ACTTENTACLECLOTH:93–156：SEX_COMEX, 0, 0, 15 の RESULT / 2 を補正して
    COMMON_PALAM:LCOUNT に加算（添字は LOCAL の番号のまま：:155）、ISMALE なら LOCAL:1 = 0、被姦経験 +1、NOWEX 全消去。
    補正（POSE・性耐性・素質・性格・触手中毒・RANDOM）：体勢 通常、性耐性 満タン（> 80%）、触手中毒 0 では変化なし、
    素質・性格補正は恒等に差し替えて、PALAM_HOSEI_TALENT／SEIKAKU が LOCAL の番号で呼ばれることだけ確かめる。
    RANDOM は RAND:100 = 50（×1.00）。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[42] = 400
    c.tcvarn[2] = 0
    c.base[2] = c.maxbase[2] = 1000
    c.nowex[0] = 3
    called: dict = {}
    r12 = [100, 200, 0, 7, 40, 50, 60, 70, 80, 90, 2000000, 1]

    def fake_comex(ctx_, a0, a1, a2):
        called["comex"] = (a0, a1, a2)
        ctx_.state.set_result_x(*r12)
        return list(r12)

    talent_ids: list[int] = []
    monkeypatch.setattr(sexcom, "sex_comex", fake_comex)
    monkeypatch.setattr(palam, "palam_hosei_talent", lambda ctx_, pid, v: (talent_ids.append(pid), v)[1])
    monkeypatch.setattr(core, "seikaku_hosei_palam", lambda s, pid, v: v)
    st.rng = pad([50] * 13)
    before = c.exp[E(data, "被姦経験")]
    cp = st.temp.common_palam
    cp.clear()
    source_check._acttentaclecloth(ctx)
    assert called["comex"] == (0, 0, 15)
    half = [v // 2 for v in r12]  # :102–104
    # 0 以下はそのまま加算（0）、正は下限 1（:150–151）、LCOUNT >= 4 は上限 999999（:153–154）
    expected = [h if h <= 0 else min(max(h, 1), 999999) if i >= 4 else max(h, 1) for i, h in enumerate(half)]
    assert [cp[i] for i in range(12)] == expected
    assert cp[12] == 0
    assert talent_ids == [i for i in range(12) if half[i] > 0]
    assert c.exp[E(data, "被姦経験")] == before + 1
    assert c.nowex[0] == 0


def _com103_fail(ctx, data, virgin: int):
    st = ctx.state
    c = st.charas[1]
    c.cflag[42] = 400
    c.base[31] = 0
    c.talent[T(data, "処女")] = virgin
    st.flag[11] = 3
    st.temp.cloth[1] = 0  # CLOTH_OUTER_PER
    st.temp.cloth[3] = 0  # CLOTH_INNER_PER
    st.temp.cloth[4] = 50  # CLOTH_INNER_DEF
    return c


@pytest.mark.parametrize(
    ("rolls", "line"),
    [
        ([99, 0], "拘束されて雌穴をくぱぁと広げられ、"),  # :168 RAND:3 == 0
        ([99, 1, 0], "種付けを受け入れる屈辱的な体勢を無理やり取らされ、"),  # :170 RAND:2 == 0
        ([99, 1, 1], "思わぬタイミングで体勢を崩され、"),
    ],
)
def test_com103_fail_with_tentaclecloth(ctx, data, rolls, line):
    """COMF103.ERB:160–175（非処女）：`%ITEMNAME:400%` の触手に … なし崩し的に挿入を許してしまう。
    REACTION_REF（Ｃ触手 = ボス 3：Ａ触手、ARG 2 → 15）。"""
    st = ctx.state
    _com103_fail(ctx, data, -1)
    st.rng = pad(rolls)
    gen = restraint.com103(ctx)
    with pytest.raises(StopIteration):
        next(gen)
    t = texts(ctx.out)
    i = t.index("触手拘束具の触手に" + line)
    assert t[i - 1].endswith("の行動は失敗した！")
    assert t[i + 1] == "なし崩し的に挿入を許してしまう・・・"
    assert st.tflag[17] == 15


def test_com103_fail_virgin_with_tentaclecloth(ctx, data):
    """COMF103.ERB:125–159（処女）：触手拘束具 → :127–144 の強制開脚文、:156–158 COMMON_PALAM:10 = 10000・処女 = -1・
    CFLAG:206 = 2（LOSTVIRGIN は呼ばない）。"""
    st = ctx.state
    c = _com103_fail(ctx, data, 1)
    st.rng = pad([99, 1, 1])
    gen = restraint.com103(ctx)
    with pytest.raises(StopIteration):
        next(gen)
    t = texts(ctx.out)
    assert "触手拘束具の触手に強制開脚させられてしまう。" in t
    assert "思わぬタイミングで体勢を崩され、" in t
    assert "処女喪失" in t
    assert st.temp.common_palam[10] == 10000
    assert c.talent[T(data, "処女")] == -1
    assert c.cflag[206] == 2


def test_com103_fail_akuoti_reaction_ref_from_result(ctx, data):
    """悪堕ちキャラ戦（FLAG:11 = 0）：COMF103:197 TRYCALLFORM TENTACLE_BOSS_0_REACTION_REF は不発 → RESULT は :5 PRINT_DISTANCE の
    関数終端（RESULT = 0）のまま → :199–200 TFLAG:17 = 0。"""
    st = ctx.state
    c = _com103_fail(ctx, data, -1)
    c.cflag[42] = 0
    st.flag[11] = 0
    st.flag[110] = 1
    st.flag[111] = 3
    st.tflag[17] = 7
    st.result[0] = 5
    st.rng = pad([99])
    gen = restraint.com103(ctx)
    with pytest.raises(StopIteration):
        next(gen)
    assert st.tflag[17] == 0


# =====================================================================================================
# Part C：悪堕ち容姿（ヒロイン関連/悪堕ち/CORRPUTION.ERB、CORRUPTION_RECOVER.ERB）
# =====================================================================================================


def _config(st, *bits):
    for b in bits:
        st.flag.set_bit(804, b)


def test_corrupt_change_looks_main_config_off(ctx):
    """:20–21 CONFIG_CHECK_PRISON_F(4) == 0（基本セット）→ RETURN 1、何もしない。"""
    st = ctx.state
    snap = st.charas[1].cstr.copy()
    st.rng = FixedRng([])
    assert corruption.corrupt_change_looks_main(ctx, 1) == 1
    assert st.charas[1].cstr == snap


def _henshin_chara(ctx, data):
    st = ctx.state
    c = st.charas[1]
    c.talent[T(data, "変身能力")] = 1
    c.cflag[34] = 1
    c.cflag[2] = 1
    c.cflag[80] = 0
    c.cflag[81] = 0
    c.cflag[13] = 0
    st.flag[6] = 0
    for k, v in {0: "ブレイズ・レッド", 1: "レッド", 201: "ブレイズ", 202: "レッド", 12: "目隠れ", 13: "ポニー",
                 14: "三つ編み", 18: "普通", 30: "黒", 31: "赤", 32: "茶", 33: "茶", 34: "185//30//104",
                 35: "185//30//104", 36: "肌色", 37: "色白"}.items():
        c.cstr[k] = v
    for k in range(50, 61):
        c.cstr[k] = ""
    c.exp[E(data, "陥落経験")] = 3
    return c


def test_corrupt_change_looks_main_full(ctx, data):
    """設定 F(4)〜F(8) ON、変身キャラ、陥落経験 3。RAND は記述順：
    CORRUPT_GET_SPNAME（:285 RAND(55)=2 イビル、:349 RAND(30)=0 ダーク、:401 RAND:2=0 → 上の句・下名詞）→
    GET_CORRUPTED_EYES（RAND(8)=1 煽情的な、CSTR:18 普通 → 「煽情的な瞳」）→ GET_CORRUPTED_HAIR（目隠れ → RAND(5)=2 斜めぱっつん、
    ADJ RAND(5)=0 ゆるふわ、三つ編み → RAND(2)=1 ロングヘア）→ 髪色（RAND(12)=1 222//67//53）→ 目色（右：RAND(12)=0 は元と同じ
    で引き直し、2 → 237//81//78；左：REYE == LEYE なので RAND:10 = 5 ≠ 0 → 右と同じ）→ 肌（色白 → RAND(2)=1 183//86//17）。
    その後 CORRUPT_CHANGE_LOOKS（:126–142）で入れ替え、:145–165 変身後名の改竄（CSTR:1 ≠ CSTR:0 なので呼び名は替えない）。"""
    st = ctx.state
    _config(st, 4, 5, 6, 7, 8)
    c = _henshin_chara(ctx, data)
    st.rng = FixedRng([2, 0, 0, 1, 2, 0, 1, 1, 0, 2, 5, 1])
    assert corruption.corrupt_change_looks_main(ctx, 1) == 0
    assert st.rng.snapshot() == []
    cs = c.cstr
    # 入れ替え後：現在の容姿 ＝ 悪堕ち容姿、CSTR:50〜 ＝ 元の容姿
    assert (cs[18], cs[50]) == ("煽情的な瞳", "普通")
    assert (cs[12], cs[57]) == ("斜めぱっつん", "目隠れ")
    assert (cs[14], cs[58]) == ("ゆるふわロングヘア", "三つ編み")
    assert (cs[31], cs[51]) == ("222//67//53", "赤")
    assert (cs[34], cs[52], cs[35], cs[53]) == ("237//81//78", "185//30//104", "237//81//78", "185//30//104")
    assert (cs[37], cs[54]) == ("183//86//17", "色白")
    assert (cs[0], cs[55], cs[56], cs[1]) == ("ブレイズ・イビル", "ブレイズ・レッド", "ブレイズ・イビル", "レッド")
    assert c.cflag[80] == 0b111111  # bit 0〜5（:33／:41／:47／:53／:59／:65）
    assert c.cflag[13] == 1
    t = texts(ctx.out)
    assert f"{c.name}の変身後名が書き換えられてゆく……" in t  # PRINT_TRANSNAME：変身していない → NAME
    assert "　　　　　————ブレイズ・イビル" in t


def test_corrupt_change_looks_main_setbit_goes_to_target(ctx, data):
    """`SETBIT CFLAG:80, n`（:33／:65）は ARG ではなく TARGET のキャラに書かれる（原作どおり）。"""
    st = ctx.state
    _config(st, 4)
    c = st.charas[1]
    c.cflag[34] = 1
    c.cflag[80] = 0
    c.talent[T(data, "変身能力")] = 0
    c.cstr[18] = "ジト目"
    c.cstr[50] = ""
    st.target = 2
    st.charas[2].cflag[80] = 0
    st.rng = FixedRng([3])  # GET_CORRUPTED_EYES RAND(8) = 3 小悪魔的な
    corruption.corrupt_change_looks_main(ctx, 1)
    assert c.cflag[80] == 0
    assert st.charas[2].cflag[80] == 0b101
    assert (c.cstr[18], c.cstr[50]) == ("小悪魔的なジト目", "ジト目")


def test_recover_corruption_stain(ctx, data):
    """CORRUPTION_RECOVER.ERB@RECOVER_CORRUPTION:6–60。陥落経験 2：髪 RAND:100 ≤ 30（:23）、右目・左目・肌 ≤ 15（:29／:35／:41）。
    RAND：髪 10（定着）、右目 50（戻る）、左目 15（定着）、肌 99（戻る）。定着した部分は CSTR:5x を現在（悪堕ち）の値で上書き
    （STAIN_*:64–104）してから CORRUPT_CHANGE_LOOKS で入れ替える → 悪堕ちの値のまま。:58 CLEARBIT CFLAG:80, 2。"""
    st = ctx.state
    _config(st, 4, 5, 6, 7, 8)
    c = st.charas[1]
    c.talent[T(data, "変身能力")] = 0
    c.cflag[34] = 1
    c.cflag[80] = 0b110111  # 0 初回、1 肌、2 悪堕ち中、4 髪色、5 目色（3 髪型なし）
    c.cflag[81] = 0
    c.exp[E(data, "陥落経験")] = 2
    for k, v in {18: "妖艶な瞳", 50: "普通", 30: "222//67//53", 51: "黒", 32: "R悪", 52: "R元", 33: "L悪", 53: "L元",
                 36: "183//86//17", 54: "肌色", 12: "前髪", 13: "髪型"}.items():
        c.cstr[k] = v
    st.rng = FixedRng([10, 50, 15, 99])
    assert corruption.recover_corruption(ctx, 1) == 0
    assert st.rng.snapshot() == []
    cs = c.cstr
    assert (cs[18], cs[50]) == ("普通", "妖艶な瞳")
    assert (cs[30], cs[51]) == ("222//67//53", "222//67//53")
    assert (cs[32], cs[52]) == ("R元", "R悪")
    assert (cs[33], cs[53]) == ("L悪", "L悪")
    assert (cs[36], cs[54]) == ("肌色", "183//86//17")
    assert c.cflag[81] == 0b101
    assert c.cflag[80] == 0b110011


def test_recover_corruption_final_removes_tentaclecloth(ctx, data):
    """陥落経験 11 > 10 → 完堕ち（:47–52：CSTR:50 = CSTR:18、TALENT:完堕ち = 1、CFLAG:81 bit 4）。その後の
    CORRUPT_CHANGE_LOOKS:200–210（変身能力なし）で 衣装 = 触手の花嫁（196）、`CFLAG:42 = 0`（TARGET：触手拘束具も外れる）。
    登録ビットが無いので RAND は引かない。"""
    st = ctx.state
    _config(st, 4)
    c = st.charas[1]
    c.talent[T(data, "変身能力")] = 0
    c.cflag[34] = 1
    c.cflag[80] = 0b101
    c.cflag[81] = 0
    c.cflag[40] = 100
    c.cflag[42] = 400
    c.exp[E(data, "陥落経験")] = 11
    c.cstr[18] = "妖艶な瞳"
    c.cstr[50] = "普通"
    st.rng = FixedRng([])
    corruption.recover_corruption(ctx, 1)
    assert c.talent[T(data, "完堕ち")] == 1
    assert c.cflag[81] == 0b10000
    assert (c.cstr[18], c.cstr[50]) == ("妖艶な瞳", "妖艶な瞳")  # 目つきが戻らない
    assert c.cflag[40] == 196 and c.cflag[42] == 0
    assert c.cflag[80] == 0b001
    assert any("【" + data.names["ITEM"][196] + "】になった！" in x for x in texts(ctx.out))


def test_nanori_final(ctx, data):
    """完堕ち＋変身キャラ：CORRUPT_CHANGE_LOOKS:170–188 名乗りの改竄。CORRUPTTION_GET_THEME（触手の虜 → RAND(13)=0 淫奴、
    RAND(4)=1 便器 → CSTR:60）、CORRUPTTION_GET_NANORI_FINAL（RAND:100 = 50 → :737／:754 の組、RAND(15)=4 戦士失格、
    RAND(10)=3 オナホール、STRMATCH で元の変身後名（CSTR:55）以降「、参上！」→ REPLACE で「、無様に参上❤」＋「❤❤」）。
    :191–198 淫縛の鎖（402）、TARGET の CFLAG:42 = 0。"""
    st = ctx.state
    _config(st, 4)
    c = st.charas[1]
    c.talent[T(data, "変身能力")] = 1
    c.talent[T(data, "完堕ち")] = 1
    c.talent[T(data, "触手の虜")] = 1
    c.cflag[13] = 1  # 変身後名は改竄済み
    c.cflag[80] = 0
    c.cflag[41] = 401
    c.cflag[42] = 400
    st.savestr[10] = "正義の美少女戦士"
    c.cstr[0] = "ブレイズ・イビル"
    c.cstr[55] = "ブレイズ・レッド"
    c.cstr[3] = "正義の美少女戦士ブレイズ・レッド、参上！"
    c.cstr[60] = ""
    st.rng = FixedRng([0, 1, 50, 4, 3])
    corruption.corrupt_change_looks(ctx, 1)
    assert st.rng.snapshot() == []
    assert c.cstr[60] == "淫奴便器"
    assert c.cstr[3] == "戦士失格オナホール❤ 淫奴便器ブレイズ・イビル、無様に参上❤❤❤"
    assert c.cflag[5] == 1
    assert c.cflag[41] == 402 and c.cflag[42] == 0
    t = texts(ctx.out)
    assert "　正義の美少女戦士ブレイズ・レッド、参上！" in t
    assert "　　————戦士失格オナホール❤ 淫奴便器ブレイズ・イビル、無様に参上❤❤❤" in t


def test_after_rescued_calls_recover(ctx, data, monkeypatch):
    """AFTER_RESCUED.ERB:29–30：CFLAG:80 bit 2（悪堕ち中）なら RECOVER_CORRUPTION。"""
    st = ctx.state
    c = st.charas[1]
    c.cflag[80] = 0b100
    called = []
    monkeypatch.setattr(corruption, "recover_corruption", lambda ctx_, who: called.append(who))
    st.rng = pad([])
    party.after_rescued(ctx, 1)
    assert called == [1]


@pytest.mark.parametrize(
    ("func", "setup", "expected"),
    [
        # 地の文/MESSAGE_AKUOTI.ERB:14–51：目の色名は GETCOLORNAME（汎用関数/GET_COLOR_NAME.ERB:67–105）、オッドアイでなければ
        # 「%右目の色名%の%CSTR:18%」
        ("MESSAGE_CORRUPT_CHANGE_LOOKS_EYES", {32: "青", 33: "青", 18: "妖艶な瞳"}, ["{n}の目は青色の妖艶な瞳に変わった。", ""]),
        ("MESSAGE_CORRUPT_CHANGE_LOOKS_EYES", {32: "青", 33: "赤", 18: "ジト目"},
         ["{n}の目は青色と赤色のオッドアイのジト目に変わった。", ""]),
        ("MESSAGE_STAIN_CORRUPTED_SKIN_COLOR", {}, ["{n}の肌の色は戻りませんでした……"]),  # :88–91
    ],
)
def test_corrupt_messages_catalog(data, svc, func, setup, expected):
    """S21 で catalog に SPLIT・ISNUMERIC・TOINT・STRCOUNT・REPLACE・STRFINDU を追加し、MESSAGE_AKUOTI.ERB が実行可能に。"""
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    ctx = Ctx(s, data, TextOutput(), svc)
    c = s.charas[1]
    c.talent[T(data, "変身能力")] = 0
    for k, v in setup.items():
        c.cstr[k] = v
    assert ctx.narration.run_function(ctx, func, [1])
    n = c.callname
    assert texts(ctx.out) == [x.format(n=n) for x in expected]


@pytest.mark.parametrize(
    ("src", "result"),
    [
        # SPLIT（Process.ScriptProc.cs:522–538）：分割数 → RESULT:0、各要素 → 配列
        ('@F\n#DIMS X, 3\nSPLIT "1//2//3//4", "//", X\nRETURN RESULT, TOINT(X:0) + TOINT(X:2)\n', [4, 4]),
        ('@F\nRETURN ISNUMERIC("12"), ISNUMERIC("1.50"), ISNUMERIC("1a"), ISNUMERIC("0\t"), ISNUMERIC("-")\n',
         [1, 1, 0, 0, 0]),  # IsNumericMethod:2540–2568
        ('@F\nRETURN TOINT("-12"), TOINT("3.9"), TOINT("x")\n', [-12, 3, 0]),  # ToIntMethod:2357–2387
        ('@F\nRETURN STRCOUNT("1//2//3", "/"), STRFINDU("ああいう", "い"), STRFINDU("", "")\n', [4, 2, -1]),
    ],
)
def test_catalog_new_builtins(svc, ctx, src, result):
    st = ctx.state
    _run_fd(svc, ctx, src)
    assert [st.result[i] for i in range(len(result))] == result


def test_catalog_replace_statement(svc, ctx):
    """`REPLACE 文字列, 正規表現, 置換`（命令形）→ RESULTS（Instraction.Child.cs:390–409、ReplaceMethod:2452–2474）。"""
    it = _run_fd(svc, ctx, '@F\nREPLACE "参上！？", "[！？♪]", "❤"\n')
    assert ctx.state.results[0] == "参上❤❤"  # S22：共用 RESULTS


# =====================================================================================================
# Part D：防衛力が負（使用者裁決 2026-10-02）
# =====================================================================================================


def test_cheers_negative_defence_sqrt_as_zero(ctx, data, monkeypatch):
    """D3：戦闘イベント.ERB:65 `SQRT(FLAG:852 + 625)` の括弧内が負なら 0 として計算（原作は CodeEE）。
    防衛力 -1000、夜：LOCAL = 25 + (5000 + 1000) / 100 = 85（:19）→ RAND:100 = 0 で発生、FLAG:70 = MIN(-1000/3000, 5) = 0
    + MIN(魅了経験 200 / 100, 5) = 2 → 夜 MAX(2/2, 1) = 1、+= MIN(980 + RAND:40, CFLAG:400 / 10 = 0) = 0。
    :65 LOCAL = 0 → :67 0 - 0 - MIN(被姦経験 / 5, 20) = 0 → RAND:100 < 0 は偽 → FLAG:72 = 1（クズ市民）。"""
    st = ctx.state
    c = st.charas[1]
    st.flag[852] = -1000
    st.time = 1
    st.flag[11] = 1
    for n in ("巻き込まれ体質", "人外の美貌", "嬲られ体質"):
        c.talent[T(data, n)] = 0
    c.exp[E(data, "魅了経験")] = 200
    c.exp[E(data, "被姦経験")] = 0
    c.cflag[284] = c.cflag[285] = 0
    c.cflag[400] = 0
    called = []
    monkeypatch.setattr(cheers, "perform_cheers_first", lambda ctx_: called.append(1))
    st.rng = FixedRng([0, 5, 0])
    cheers.perform_cheers_first_hantei(ctx)
    assert st.rng.snapshot() == []
    assert st.flag[70] == 1 and st.flag[72] == 1
    assert called == [1]
