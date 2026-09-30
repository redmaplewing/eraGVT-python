"""隨機方針模擬（S11 起各階段共用）：`python tools/sim.py --preset default --seeds 0-249`。

每一場：新遊戲（`--preset default` = 標題 [0]→[0] おまかせ；`tokusou` = [0]→[1] 初期セット）→ 每次 SHOP 時
對全員隨機預約 101–103（休憩・鍛錬・出撃）後 [100] 確認；其他畫面從最近輸出的按鈕中隨機選一個（沒有按鈕就送 0）。
遊戲 RNG = `GameRng(seed)`，方針 RNG = `random.Random(seed)`（兩者獨立）。口上／地の文用 catalog（Web 預設）。

停止條件：Web「停止」（未移植 → NotImplementedError 的訊息）、SHOP 次數達 `--max-shop`、輸入步數達 `--max-steps`、
其他例外（記為「例外: 型別」）。

輸出：停止原因頻度、停止前經過的 SHOP 次數（平均／最多）、敗北局數（曾有人幽閉 CFLAG:0 == 1）與敗北後 SHOP 平均。
停止原因以訊息的前 `--key-len` 字歸類。
"""

from __future__ import annotations

import argparse
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eragvt.data import default_csv_dir, load_game_data  # noqa: E402
from eragvt.game.session import GameSession, Phase  # noqa: E402
from eragvt.narration.service import CatalogNarrationService  # noqa: E402
from eragvt.state import GameRng  # noqa: E402

HALT_PREFIX = "（未實作のため停止しました："


def _parse_seeds(text: str) -> list[int]:
    out: list[int] = []
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def run_one(data, narration, seed: int, preset: str, max_shop: int, max_steps: int, save_dir: Path) -> dict:
    policy = random.Random(seed)
    s = GameSession(data, save_dir, rng=GameRng(seed), narration=narration)
    s.input(0)
    s.input(0 if preset == "default" else 1)
    shops = 0
    defeated_at: int | None = None
    reason = "上限"
    steps = 0
    mark = len(s.out.lines)
    while steps < max_steps:
        steps += 1
        if s.phase == Phase.HALTED:
            text = next((ln.text for ln in reversed(s.out.lines) if ln.text.startswith(HALT_PREFIX)), "")
            reason = text[len(HALT_PREFIX):].rstrip("）")
            break
        st = s.state
        if st is not None and defeated_at is None and any(st.charas[i].cflag[0] == 1 for i in range(1, st.charanum)):
            defeated_at = shops
        try:
            if s.phase == Phase.SHOP:
                shops += 1
                if shops > max_shop:
                    reason = "上限"
                    break
                for i in range(1, st.charanum):
                    s.input(i)
                    s.input(policy.choice((101, 102, 103)))
                mark = len(s.out.lines)
                s.input(100)
                continue
            new = s.out.lines[mark:] if len(s.out.lines) >= mark else s.out.lines[-40:]
            buttons = [v for ln in new for (_, v) in ln.buttons]
            if not buttons:
                buttons = [v for ln in s.out.lines[-40:] for (_, v) in ln.buttons]
            mark = len(s.out.lines)
            s.input(policy.choice(buttons) if buttons else 0)
        except Exception as exc:  # noqa: BLE001（例外も停止原因として集計）
            reason = f"例外: {type(exc).__name__}: {exc}"
            break
    else:
        reason = "步數上限"
    return {"seed": seed, "reason": reason, "shops": shops, "defeated_at": defeated_at}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=("default", "tokusou"), default="default")
    p.add_argument("--seeds", default="0-249")
    p.add_argument("--max-shop", type=int, default=200)
    p.add_argument("--max-steps", type=int, default=100000)
    p.add_argument("--key-len", type=int, default=40)
    p.add_argument("--verbose", action="store_true")
    a = p.parse_args(argv)
    data = load_game_data(default_csv_dir())
    narration = CatalogNarrationService(default_csv_dir().parent / "ERB", data)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in _parse_seeds(a.seeds):
            r = run_one(data, narration, seed, a.preset, a.max_shop, a.max_steps, Path(tmp))
            results.append(r)
            if a.verbose:
                print(r, flush=True)
    n = len(results)
    shops = [r["shops"] for r in results]
    lost = [r for r in results if r["defeated_at"] is not None]
    print(f"preset={a.preset} games={n}")
    print(f"SHOP 次數：平均 {sum(shops) / n:.2f}／最多 {max(shops)}")
    after = [r["shops"] - r["defeated_at"] for r in lost]
    print(f"敗北局 {len(lost)}" + (f"／敗北後 SHOP 平均 {sum(after) / len(after):.2f}" if after else ""))
    print("停止原因：")
    for k, v in Counter(r["reason"][: a.key_len] for r in results).most_common():
        print(f"  {v:4d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
