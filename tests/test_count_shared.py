"""S88：共用 COUNT；中性 catalog 與全新25歲人工角色。

迴圈 expected 依 reference/emuera-1824/Emuera/GameProc/Function/
Instraction.Child.cs:1731–1744、2054–2161：開始值先寫、RETURN不步進、
BREAK／CONTINUE步進；COUNT是全域陣列，不受CALL或巢狀函式保護。
"""
import json

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.shop import game_mode_check, game_mode_check_proc
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import GameState, GameRng, dump_save, load_save
from eragvt.state.character import Character
from eragvt.state.constants import MODE_OPTIONS, GameMode
from eragvt.text import TextOutput


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def ctx(data, tmp_path):
    st = GameState(rng=GameRng(88), target=1)
    for i in range(2):
        c = Character(i, name=f"人工成年{i}", callname=f"人工成年{i}")
        for n in (40, 41):
            c.base[n] = c.maxbase[n] = 25
        st.charas.append(c)
    return Ctx(st, data, TextOutput(), CatalogNarrationService(tmp_path, data))


def install(ctx, tmp_path, source):
    (tmp_path / "neutral.ERB").write_text(source, encoding="utf-8", newline="\n")
    ctx.narration = CatalogNarrationService(tmp_path, ctx.data)
    return ctx.narration


@pytest.mark.parametrize("body,expected", [
    ("REPEAT 0\nREND", 0),
    ("REPEAT 3\nREND", 3),
    ("REPEAT 7\nBREAK\nREND", 1),
    ("REPEAT 3\nCONTINUE\nREND", 3),
    ("REPEAT 8\nRETURN\nREND", 0),
    ("REPEAT 3\nREPEAT 2\nREND\nREND", 3),
    ("FOR COUNT, 5, -1, -2\nNEXT", -1),
    ("FOR COUNT, 5, -1, -2\nBREAK\nNEXT", 3),
    ("FOR LOCAL, 0, 3\nNEXT", 77),
    ("REPEAT COUNT\nREND", 0),
    ("FOR COUNT, 5, COUNT+2\nNEXT", 7),
])
def test_catalog_counter_boundaries(ctx, tmp_path, body, expected):
    svc = install(ctx, tmp_path, "@F\n" + body + "\nRETURN\n")
    ctx.state.count[0] = 77
    assert svc.run_function(ctx, "F")
    assert ctx.state.count[0] == expected


def test_cross_call_and_separate_count_indices(ctx, tmp_path):
    svc = install(ctx, tmp_path, "@F\nFOR COUNT:1, 0, 2\nCALL G\nNEXT\nRETURN\n@G\nREPEAT 3\nREND\nRETURN\n")
    assert svc.run_function(ctx, "F")
    assert [ctx.state.count[i] for i in range(2)] == [3, 2]
    assert not any(key[0] == "COUNT" for key in ctx.state.temp.narr)


def test_call_clobbers_active_repeat_counter(ctx, tmp_path):
    # Process.State.cs:438–483、502–523不還原COUNT；G留下2，F的REND加1即達上限3。
    svc = install(ctx, tmp_path, "@F\nREPEAT 3\nPRINTL outer\nCALL G\nREND\nRETURN\n@G\nREPEAT 2\nREND\nRETURN\n")
    assert svc.run_function(ctx, "F")
    assert ctx.state.count[0] == 3
    assert [line.text for line in ctx.out.lines] == ["outer"]


@pytest.mark.parametrize("version", [1, 2, 3])
def test_count_saved_and_old_json_migrates(ctx, version):
    # VariableCode.cs:45、94；VariableData.cs:663–688：0x0B屬存檔陣列。
    ctx.state.count[0], ctx.state.count[1], ctx.state.count[999] = 20, 3, -7
    raw = dump_save(ctx.state)
    obj = json.loads(raw)
    assert obj["version"] == 4
    restored, _ = load_save(raw)
    assert restored.count == ctx.state.count
    assert dump_save(restored) == raw
    obj["version"] = version
    del obj["state"]["count"]
    if version == 1:
        del obj["state"]["result"]
    if version <= 2:
        del obj["state"]["da"]
    old, _ = load_save(json.dumps(obj).encode())
    assert old.count[0] == old.count[1] == 0


def test_begin_train_does_not_reset_count(ctx):
    # VariableEvaluator.cs:1422–1460的清除清單沒有COUNT；不是每個BEGIN都ResetData。
    from eragvt.game.battle.train import update_in_begin_train
    ctx.state.count[0], ctx.state.count[1] = 7, 3
    update_in_begin_train(ctx.state)
    assert (ctx.state.count[0], ctx.state.count[1]) == (7, 3)
    assert GameState().count[0] == 0


@pytest.mark.parametrize("mode", list(GameMode) + [-1])
@pytest.mark.parametrize("proc", [False, True])
def test_mode_return_preserves_current_count(ctx, mode, proc):
    # ERB/ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB
    # @GAME_MODE_CHECK:124–130／@GAME_MODE_CHECK_F:131–138。
    ctx.state.flag[906] = int(proc)
    ctx.state.flag[0] = MODE_OPTIONS[mode] | (64 if proc else 0) if mode != -1 else -1
    ctx.state.count[0] = 77
    assert (game_mode_check_proc if proc else game_mode_check)(ctx.state) == mode
    assert ctx.state.count[0] == (8 if mode == -1 else mode)


@pytest.mark.parametrize("value", [-1, 1000])
def test_count_bounds(ctx, tmp_path, value):
    # ConstantData.cs:147–148預設1000格，VariableSize.csv未改COUNT。
    svc = install(ctx, tmp_path, f"@F\nCOUNT:{value} = 4\nRETURN\n")
    ctx.state.count[0] = 9
    assert not svc.run_function(ctx, "F")
    assert ctx.state.count[0] == 9
    assert svc.journal.depth == 0


def test_varset_and_failure_restore_shared_count(ctx, tmp_path):
    svc = install(ctx, tmp_path, "@F\nVARSET COUNT\nCOUNT:1 = 5\nRETURN\n@FAIL\nCOUNT:0 = 2\nCALLFORM MISSING_{COUNT}\nRETURN\n")
    ctx.state.count[999] = 4
    assert svc.run_function(ctx, "F")
    assert [ctx.state.count[i] for i in (0, 1, 999)] == [0, 5, 0]
    assert not svc.run_function(ctx, "FAIL")
    assert [ctx.state.count[i] for i in (0, 1, 999)] == [0, 5, 0]
    assert svc.journal.depth == 0


@pytest.mark.parametrize("event", [False, True])
def test_input_resume_keeps_count_once(ctx, tmp_path, event):
    svc = install(ctx, tmp_path, "@F\nREPEAT 2\nPRINTFORML {COUNT}\nINPUT\nREND\nRETURN\n")
    ctx.state.count[0] = 77
    gen = (svc.run_event_gen if event else svc.run_function_gen)(ctx, "F")
    next(gen)
    assert ctx.state.count[0] == 0
    gen.send(9)
    assert ctx.state.count[0] == 1
    with pytest.raises(StopIteration) as stopped:
        gen.send(9)
    assert stopped.value.value is True
    assert ctx.state.count[0] == 2
    assert [line.text for line in ctx.out.lines] == ["0", "1"]
    assert svc.journal.depth == 0


def test_native_hook_failure_keeps_count_and_stops(ctx, monkeypatch):
    # 沿既有hook不可回復契約；COUNT搬出temp.narr不能讓原生hook被重放或例外被吃掉。
    from eragvt.game import kojo_calls
    from eragvt.narration.extract import parse_function, read_logical_lines
    from eragvt.narration.runtime import Frame
    svc = ctx.narration
    calls = []
    def neutral_hook(call_ctx, who):
        calls.append(who)
        call_ctx.state.count[0] = 42
    monkeypatch.setattr(kojo_calls, "hook_levelstatus", neutral_hook)
    fd = parse_function(svc.catalog.ctx, "口上/neutral.ERB", read_logical_lines(
        b"@F\nCOUNT = 3\nCALL LEVELSTATUS, TARGET\nLOCAL = 1 / 0\n"))
    with pytest.raises(NotImplementedError):
        svc._run(ctx, lambda it: it.exec_block(fd.body, Frame(fd, "F")), "F")
    assert calls == [1]
    assert ctx.state.count[0] == 42
    assert svc.journal.depth == 0


def test_nested_transaction_restores_count(ctx):
    from eragvt.narration.service import _Tx
    ctx.state.count[0] = 9
    outer = _Tx(ctx)
    ctx.state.count[0] = 10
    inner = _Tx(ctx)
    ctx.state.count[0] = 11
    inner.commit()
    outer.rollback()
    assert ctx.state.count[0] == 9
    assert ctx.narration.journal.depth == 0
