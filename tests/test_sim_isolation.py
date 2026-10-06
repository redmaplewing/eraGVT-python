"""模擬輸入與每 seed 全域資料隔離，避免新增成就改變策略抽樣。"""
import importlib.util
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("sim_isolation_driver", Path(__file__).parents[1] / "tools/sim.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)


def test_achievement_confirmation_preserves_policy_rng():
    policy = random.Random(7)
    before = policy.getstate()
    inputs = []
    session = SimpleNamespace(out=SimpleNamespace(achievement_wait=lambda _: None), input=inputs.append)
    sim._input_choice(session, policy, [9, 10, 30])
    assert inputs == [0]
    assert policy.getstate() == before
    session.out.achievement_wait = None
    sim._input_choice(session, policy, [9, 10, 30])
    assert inputs[-1] == random.Random(7).choice([9, 10, 30])
    assert policy.getstate() != before


def test_batch_seeds_have_independent_global_files(monkeypatch, tmp_path):
    monkeypatch.setattr(sim, "install_event_counters", Counter)
    monkeypatch.setattr(sim, "load_game_data", lambda _: None)
    monkeypatch.setattr(sim, "CatalogNarrationService", lambda *_: SimpleNamespace(failures=[]))
    monkeypatch.setattr(sim, "summarize", lambda *_: None)
    def fake_run(data, narration, seed, preset, max_shop, max_steps, save_dir, *args, **kwargs):
        save_dir.mkdir(parents=True, exist_ok=True)
        global_path = save_dir / "global.json"
        prior = global_path.read_text() if global_path.exists() else None
        global_path.write_text(str(seed))
        return {"seed": seed, "prior_global": prior}
    monkeypatch.setattr(sim, "run_one", fake_run)
    results = []
    for i, seeds in enumerate(("0-1", "1,0", "1")):
        dest = tmp_path / f"{i}.jsonl"
        sim.main(["--seeds", seeds, "--dump", str(dest)])
        results.append({r["seed"]:r for line in dest.read_text().splitlines() if (r := json.loads(line))})
    assert results[0] == results[1]
    assert results[0][1] == results[2][1]
    assert all(r["prior_global"] is None for r in results[0].values())


@pytest.mark.parametrize("result", [0, 1])
def test_pregnancy_counter_waits_for_generator_return(result):
    """計數器須等 RETURN 0／1；不能把 generator 物件當成功。

    對應 ERB/ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_HANTEI:163–165。
    隔離全域 instrumentation，避免污染其他遊戲測試。
    """
    script = r'''
import sys
from eragvt.game import seisan
from tools.sim import install_event_counters

result = int(sys.argv[1])
received = []
def probe(ctx, *args):
    assert ctx == "context" and args == (3, 800, -1)
    received.append((yield None))
    return result

seisan._ninsin = probe
counts = install_event_counters()
gen = seisan._ninsin("context", 3, 800, -1)
assert not counts
assert next(gen) is None
assert not counts
try:
    gen.send(7)
except StopIteration as done:
    assert done.value == result
else:
    raise AssertionError("generator did not finish")
assert received == [7]
key = "特別活動 妊娠判定" + ("→受精" if result else "")
assert dict(counts) == {key: 1}
'''
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script, str(result)],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
