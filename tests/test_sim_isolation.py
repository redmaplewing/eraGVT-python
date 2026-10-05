"""模擬輸入與每 seed 全域資料隔離，避免新增成就改變策略抽樣。"""
import importlib.util
import json
import random
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

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
