"""S22：共用 RESULTS（字串回傳值）陣列，照原作。

expected 由 ERB 原文推導（路徑相對 `source/earGVP/ERB/`，行號寫在註解），引擎語意附
`reference/emuera-1824/Emuera/` 的行號。不從實作輸出反推。
"""

from __future__ import annotations

import json

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import corruption, shop, tattoo
from eragvt.game.action import Ctx
from eragvt.game.battle import source_check
from eragvt.game.opening import PRESET_TOKUSOU, event_first
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
    return Ctx(s, data, TextOutput(), NullNarrationService())


def _run_fd(svc, ctx, src: str):
    ectx = ExtractContext({}, {}, lambda n: False)
    fd = parse_function(ectx, "t.ERB", read_logical_lines(src.encode("utf-8")))
    it = Interp(svc.catalog, Env(ctx.state, ctx.data, ctx.out, {}, {}, ctx))
    try:
        it.exec_block(fd.body, Frame(fd, "F"))
    except rt._Return:
        pass
    return it


def _results(st: GameState, n: int = 4) -> list[str]:
    return [st.results[i] for i in range(n)]


# --- 引擎：不存檔、新遊戲／讀檔時為空 ---------------------------------------------------------


def test_results_not_saved(ctx):
    """RESULTS（0x02）≥ __COUNT_SAVE_STRING_ARRAY__（0x01）且無 __SAVE_EXTENDED__ → 不存檔（VariableCode.cs:104–110、
    VariableData.cs@SaveToStream:663–674）；讀檔時 SetDefaultValue 清空（VariableEvaluator.cs@LoadFromStream:2173）。
    RESULTS 不入存檔；S35 因DA新增升為3。"""
    st = ctx.state
    st.results[0] = "a"
    st.results[2] = "c"
    raw = dump_save(st)
    obj = json.loads(raw)
    assert obj["version"] == 3
    assert "results" not in obj["state"]
    st2, _ = load_save(raw)
    assert _results(st2) == ["", "", "", ""]
    assert st2 == st  # compare=False：RESULTS 不影響存讀檔往返的比較
    assert dump_save(st2) == raw


def test_results_empty_on_new_game(data):
    """ResetData → SetDefaultValue（VariableEvaluator.cs:1132–1139、VariableData.cs:558–574）。"""
    st = GameState.new(data)
    assert len(st.results) == 0


# --- catalog：共用陣列、殘值、VARSET、失敗回復 --------------------------------------------------


def test_catalog_results_shared_and_residual(svc, ctx):
    """catalog の `RESULTS:n =` は共用 RESULTS に書き、Python 側から読める。RESULTS:0 だけを書く後続処理
    （式中関数を命令として：Instraction.Child.cs@METHOD_Instruction:398–404）では RESULTS:1／2 は残る。"""
    st = ctx.state
    _run_fd(svc, ctx, '@F\nRESULTS:0 = a\nRESULTS:1 = b\nRESULTS:2 = c\n')
    assert _results(st) == ["a", "b", "c", ""]
    _run_fd(svc, ctx, '@F\nSUBSTRINGU "xyz", 1, 1\n')
    assert _results(st) == ["y", "b", "c", ""]
    st.results[3] = "py"
    it = _run_fd(svc, ctx, '@F\nLOCALS = %RESULTS:3%\n')
    assert it._get_narr(("F", "LOCALS"), (0,), "") == "py"


def test_catalog_varset_results(svc, ctx):
    """`VARSET RESULTS`：全 100 格を "" に（例 口上/女性汎用口上/KOJO_0_21_ヤンデレ.ERB:38）。"""
    st = ctx.state
    st.results[0] = "a"
    st.results[2] = "c"
    st.results[99] = "z"
    _run_fd(svc, ctx, '@F\nVARSET RESULTS\n')
    assert len(st.results) == 0


def test_catalog_results_index_out_of_range(svc, ctx):
    """RESULTS の大きさは 100（ConstantData.cs:154–155）：RESULTS:100 は範囲外。"""
    with pytest.raises(rt.ErbRuntimeError):
        _run_fd(svc, ctx, '@F\nRESULTS:100 = a\n')


def test_strmatch_catalog(svc, ctx):
    """汎用関数/コモン関数.ERB@STRMATCH:1378–1393 を catalog で実行：成立 → RESULTS:1 前・:2 後・:0 一致文字列、
    不成立 → RESULTS:0／1 だけ空にして RESULTS:2 は前の値のまま。"""
    st = ctx.state
    assert svc.run_function(ctx, "STRMATCH", ["abcdef", "cd"])
    assert _results(st) == ["cd", "ab", "ef", ""]
    assert st.result[0] == 0  # :1393 RETURN
    assert svc.run_function(ctx, "STRMATCH", ["abcdef", "zz"])
    assert _results(st) == ["", "", "ef", ""]


def test_catalog_failure_restores_results(svc, ctx):
    """catalog の実行時失敗の回復（service._Tx：出力・亂數・LOCAL・RESULT）で RESULTS も実行前に戻す。"""
    from eragvt.narration.service import _Tx

    st = ctx.state
    st.results[1] = "keep"
    ctx2 = Ctx(st, ctx.data, ctx.out, svc)

    tx = _Tx(ctx2)
    _run_fd(svc, ctx2, '@F\nRESULTS:1 = changed\n')
    assert st.results[1] == "changed"
    tx.rollback()
    assert ctx2.state.results[1] == "keep"


# --- 名乗り改竄（CORRPUTION.ERB@CORRUPTTION_GET_NANORI_FINAL:733–816） ---------------------------


def _nanori_setup(ctx, data, cstr3: str):
    st = ctx.state
    c = st.charas[1]
    st.savestr[10] = "正義の美少女戦士"
    c.cstr[0] = "ブレイズ・イビル"
    c.cstr[55] = "ブレイズ・レッド"
    c.cstr[3] = cstr3
    c.cstr[60] = ""
    return st, c


def test_nanori_final_hit_writes_results(ctx, data):
    """STRMATCH 成立（:786）：RESULTS:1 = 前、:2 = 後（:1382–1386）、:0 = 一致文字列（:1388）→ REPLACE（命令）で
    RESULTS:0 = 改竄後（:794–807）。RAND:100 = 50 → :737／:754 の組、RAND(15)=4 戦士失格、RAND(10)=3 オナホール。"""
    st, c = _nanori_setup(ctx, data, "正義の美少女戦士ブレイズ・レッド、参上！")
    st.rng = FixedRng([50, 4, 3])
    corruption.corruption_get_nanori_final(ctx, 1)
    assert st.rng.snapshot() == []
    assert c.cstr[3] == "戦士失格オナホール❤ 正義の美少女戦士ブレイズ・イビル、無様に参上❤❤❤"
    assert _results(st) == ["、無様に参上❤", "正義の美少女戦士", "、参上！", ""]
    assert st.result[0] == 0


def test_nanori_final_miss_reads_previous_results2(ctx, data):
    """使用者裁決（2026-10-02）照原作：名乗り（CSTR:3）に変身後名（CSTR:55）が無い → STRMATCH は RESULTS:0／1 だけ空に
    （:1390–1392）→ :787 は前回の RESULTS:2（ここでは「、推参だ！」）→ :794 `[！？♪]`→❤、:797 推参→無様に推参、:809 ❤❤。
    CHANGINGCALL_DETAIL は呼ばれない（RAND は 3 回だけ）。"""
    st, c = _nanori_setup(ctx, data, "正義の美少女戦士ブレイズ・カスタム、行くよ！")
    st.results[0] = "old0"
    st.results[1] = "old1"
    st.results[2] = "、推参だ！"
    st.rng = FixedRng([50, 4, 3])
    corruption.corruption_get_nanori_final(ctx, 1)
    assert st.rng.snapshot() == []
    assert c.cstr[3] == "戦士失格オナホール❤ 正義の美少女戦士ブレイズ・イビル、無様に推参だ❤❤❤"
    assert _results(st) == ["、無様に推参だ❤", "", "、推参だ！", ""]
    assert c.cflag[5] == 1


def test_nanori_final_miss_empty_results2(ctx, data):
    """不成立かつ前回の RESULTS:2 が空 → :790 `FIRSTSETTING_CHANGINGCALL_DETAIL(ARG:0, LOCAL)`（静的 LOCAL = 0 → ELSE の強気系：
    FIRSTSETTING_変身デフォルト口上.ERB:116–130）：RAND(4)=1「、見参」、RAND(6)=4「…負けないわよ！」→ 改竄。"""
    st, c = _nanori_setup(ctx, data, "正義の美少女戦士ブレイズ・カスタム、行くよ！")
    st.rng = FixedRng([50, 4, 3, 1, 4])
    corruption.corruption_get_nanori_final(ctx, 1)
    assert st.rng.snapshot() == []
    assert c.cstr[3] == "戦士失格オナホール❤ 正義の美少女戦士ブレイズ・イビル、無様に見参…イキ果てるわよ❤❤❤"
    assert _results(st) == ["、無様に見参…イキ果てるわよ❤", "", "", ""]


def test_nanori_final_second_call_uses_first_results2(ctx, data):
    """2 人続けて完堕ち：1 人目の STRMATCH 成立で RESULTS:2 =「、参上！」→ 2 人目は不成立なのでその値を使う。"""
    st, c = _nanori_setup(ctx, data, "正義の美少女戦士ブレイズ・レッド、参上！")
    c2 = st.charas[2]
    c2.cstr[0] = "ミスト・イビル"
    c2.cstr[55] = "ミスト・ブルー"
    c2.cstr[3] = "名乗り変更済み"
    c2.cstr[60] = ""
    st.rng = FixedRng([50, 4, 3, 50, 0, 0])
    corruption.corruption_get_nanori_final(ctx, 1)
    corruption.corruption_get_nanori_final(ctx, 2)
    assert st.rng.snapshot() == []
    # :737 RAND(15)=0 お触手様の、:754 RAND(10)=0 性奴隷
    assert c2.cstr[3] == "お触手様の性奴隷❤ 正義の美少女戦士ミスト・イビル、無様に参上❤❤❤"


# --- TagSetText（WINDOW_*）：VARSET RESULTS, "" → ARRAYCOPY ---------------------------------------


class _It:
    def __init__(self, st):
        self.st = st


def test_window_results(data):
    """@WINDOW_CREATE → WINDOW_MGR "CREATE"（WindowDrawer.ERB:351–375）の SHAPE_TAGSET_TEXT（TagSetText.ERB:196–271：
    `VARSET RESULTS, ""` → ARRAYCOPY）。幅 10・高さ 1・枠なし → RESULTS:0 = 空白 10、他は空。SETTEXT（:377–389）→
    「abc」＋空白 7。DESTROY（:341–347）は RESULTS を変えない。DISPLAY（:121–124）の最後の SHAPE（84 桁）が残る。"""
    st = GameState.new(data)
    st.results[2] = "old"
    fns = py_functions(WindowManager(), TextOutput())
    it = _It(st)
    fns["WINDOW_CREATE"](it, [0, 0, 0, 10, 1, 0])
    assert _results(st) == [" " * 10, "", "", ""]
    fns["WINDOW_SETTEXT"](it, [0, 0, "abc"])
    assert _results(st) == ["abc" + " " * 7, "", "", ""]
    fns["WINDOW_DISPLAY"](it, [])
    assert _results(st) == ["abc" + " " * 81, "", "", ""]
    st.results[2] = "keep"
    fns["WINDOW_DESTROY"](it, [0])
    assert _results(st) == ["abc" + " " * 81, "", "keep", ""]


# --- PRINT_TATTOO（佔位）でも RESULTS は原作どおり -----------------------------------------------


def test_print_tattoo_fallback_results(svc, ctx, data):
    """CHARA_TATTOO.ERB@PRINT_TATTOO（catalog 不可：CHKFONT）の佔位時：:245 `VARSET RESULTS` → :373 TATTOO_RANK、:392
    TATTOO_TYPE → :397 `TATTOO_LIB, RESULT + CAL_VAR * 10, LOCAL`（:478–1409）。CFLAG:32 = 2（部位 0 の模様 2、進行度 0）、
    ABL:0 = 50・TALENT:100／101／153 = 0 → TATTOO_LV_CAL(0) = 50、ランク = 50 * 50 / 800 = 3 → TATTOO_LIB(2, 3)：
    ARG:0 == 2 の組（:495–503）、ランク 3 は LEFT_STR:3／RIGHT_STR:3 を空に → RESULTS:0 = L3L2L1L0、:1 = R0R1R2R3。"""
    st = ctx.state
    c = st.charas[st.target]
    c.cflag[32] = 2
    c.abl[0] = 50
    for i in (100, 101, 153):
        c.talent[i] = 0
    st.results[2] = "old"
    ctx2 = Ctx(st, data, TextOutput(), svc)
    tattoo.print_tattoo(ctx2, 0)
    assert _results(st) == ["ཆཤཎ", "སབྷཀ", "", ""]


def test_print_tattoo_fallback_null_narration(ctx):
    """catalog なし（NullNarrationService）でも :245 の VARSET RESULTS は反映（RESULTS:0／1 は TATTOO_LIB が使えず空）。"""
    st = ctx.state
    st.results[2] = "old"
    tattoo.print_tattoo(ctx, 0)
    assert len(st.results) == 0


def test_tattoo_position_str_writes_results0(ctx):
    """TATTOO_ACCESS "POSITION_STR"（CHARA_TATTOO.ERB:209–229）：RESULTS = %LOCALS%（:217／:229）。"""
    st = ctx.state
    st.charas[st.target].cflag[32] = 2  # 部位 0（下腹部）のみ
    st.results[1] = "keep"
    assert tattoo.tattoo_access(ctx, "POSITION_STR") == "下腹部"
    assert _results(st) == ["下腹部", "keep", "", ""]


# --- RESULT:0 の「呼び出し前の値」（deviations「口上 catalog の表示簡化」・S22 確認） --------------------


def test_hatujou_to_hairan_sets_result0(ctx):
    """SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:513–527 の RETURN 0 → RESULT:0 = 0。悪堕ちキャラ戦（FLAG:11 = 0）で
    BATTLE_COM_AFTER.ERB:1157 の TRYCALLFORM が不発のとき :1159 が読む値。"""
    st = ctx.state
    st.result[0] = 7
    source_check._hatujou_to_hairan(ctx)
    assert st.result[0] == 0
