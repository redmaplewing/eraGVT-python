"""隨機方針模擬（S11 起各階段共用）：`python tools/sim.py --preset default --seeds 0-249`。

每一場：新遊戲（`--preset default` = 標題 [0]→[0] おまかせ；`tokusou` = [0]→[1] 初期セット）→ 每次 SHOP 時
對全員隨機預約 101–103（休憩・鍛錬・出撃）後 [100] 確認；其他畫面從最近輸出的按鈕中隨機選一個（沒有按鈕就送 0）。
遊戲 RNG = `GameRng(seed)`，方針 RNG = `random.Random(seed)`（兩者獨立）。口上／地の文用 catalog（Web 預設）。

停止條件：Web「停止」（未移植 → NotImplementedError 的訊息）、SHOP 次數達 `--max-shop`、輸入步數達 `--max-steps`、
其他例外（記為「例外: 型別」）。

輸出：停止原因頻度、停止前經過的 SHOP 次數（平均／最多）、敗北局數（曾有人幽閉 CFLAG:0 == 1）與敗北後 SHOP 平均、
ゲームオーバーモード（FLAG:0 == 0，S12）進入局數與進入後 SHOP 平均（＝再走幾回合）及其停止原因。
停止原因以訊息的前 `--key-len` 字歸類。

S18：各強制發生事件的實際觸發次數（`install_event_counters`：包裝模組函式計數，不改變遊戲行為）。
`--enable-intimidation` 在開局後把 FLAG:804 bit10（`CONFIG_CHECK_PRISON_F(10)`「クズ市民による幽閉」）打開
（基本セットは OFF：脅迫イベントは起きない）。

S19：`--enable-akuoti` は開局後に FLAG:804 bit1（`CONFIG_CHECK_PRISON_F(1)`：陥落時に洗脳／悪堕ち）と bit9
（`CONFIG_CHECK_PRISON_F(9)`：洗脳ではなく悪堕ち）を打開（PRISON.ERB:335–357；基本セットは FLAG:804 = 1 で両方 OFF、
陥落しても悪堕ちキャラは生まれない）。悪堕ちキャラの淫謀・洗脳／悪堕ちキャラ戦の次数も数える。
"""

from __future__ import annotations

import argparse
import json
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


def install_event_counters() -> Counter:
    """S18：強制發生事件的函式呼叫／狀態變化を数える（モジュール属性を包む。呼び出しは全てモジュールの大域名経由）。"""
    from eragvt.game import intimidation, small_tentacle, turnend, yobai

    counts: Counter = Counter()

    def wrap(mod, name, before=None, after=None):
        orig = getattr(mod, name)

        def w(ctx, *a, **k):
            snap = before(ctx, *a) if before else None
            r = yield from orig(ctx, *a, **k)
            if after:
                after(ctx, snap, *a)
            return r

        setattr(mod, name, w)

    def intim_before(ctx):
        c = ctx.state.target_chara
        return (c.cflag[290], c.cflag[0])

    def intim_after(ctx, snap):
        c = ctx.state.target_chara
        if c.cflag[290] != snap[0]:
            counts["脅迫（発生）"] += 1
        if c.cflag[0] == 4 and snap[1] != 4:
            counts["脅迫→拉致監禁"] += 1

    def kid_after(ctx, snap):
        counts["拉致監禁（KIDNAPPING 呼出）"] += 1
        if ctx.state.charas[snap].cflag[0] != 4:
            counts["拉致監禁→救出／解放"] += 1

    wrap(turnend, "intimidation_event", intim_before, intim_after)
    wrap(turnend, "kidnapping", lambda ctx: ctx.state.target, kid_after)
    wrap(yobai, "yobai_event", after=lambda ctx, snap: counts.update(["夜這い（YOBAI_EVENT）"]))
    wrap(yobai, "yobai_action", after=lambda ctx, snap, arg, *a: counts.update([f"夜這い実行 ARG={arg}"]))
    wrap(small_tentacle, "small_tentacle_attack", after=lambda ctx, snap: counts.update(["子触手襲来（ATTACK）"]))
    wrap(small_tentacle, "small_prison_event", after=lambda ctx, snap: counts.update(["子触手襲来（成功）"]))
    wrap(small_tentacle, "small_prison_com", after=lambda ctx, snap, arg: counts.update([f"子触手 SMALL_PRISON_COM {arg}"]))

    # S19：悪堕ちキャラ関連（いずれも通常の関数）
    from eragvt.game import akuoti
    from eragvt.game.battle import encount, source_check

    def wrap_plain(mod, name, after):
        orig = getattr(mod, name)

        def w(ctx, *a, **k):
            r = orig(ctx, *a, **k)
            after(ctx, r)
            return r

        setattr(mod, name, w)

    def enc_after(ctx, r):
        if r:
            kind = {2: "洗脳", 3: "悪堕ち"}.get(ctx.state.charas[ctx.state.flag[111]].cflag[0], "?")
            counts[f"{kind}キャラ戦（ENCOUNT_ENEMY）"] += 1

    wrap_plain(akuoti, "akuoti_event", lambda ctx, r: counts.update(["悪堕ちキャラの淫謀（AKUOTI_EVENT）"]))
    wrap_plain(encount, "encount_enemy", enc_after)
    wrap_plain(source_check, "_victory_akuoti", lambda ctx, r: counts.update(["洗脳／悪堕ちキャラ戦 勝利"]))
    orig_lose = source_check._battle_lose

    def lose(ctx, *a, **k):
        if ctx.state.flag[110] > 0:  # 敗北処理は BEGIN AFTERTRAIN（例外）で抜けるので先に数える
            counts["洗脳／悪堕ちキャラ戦 敗北"] += 1
        return orig_lose(ctx, *a, **k)

    source_check._battle_lose = lose
    return counts


def _corrupt(state, data, who: int) -> None:
    """`--corrupt N`（テスト用の初期状態）：キャラ N を開局時点で悪堕ち（CFLAG:0 = 3）にする。支配者はボス 1
    （CFLAG:20 = 0〔ボス〕、CFLAG:21 = 1：PRISON.ERB:335–388 の陥落と同じ持ち方）、陥落経験 +1、CFLAG:23 = 0。
    口上・容姿変更・経験値付与などの陥落時演出は通さない（原作の途中経過ではない人工的な状態）。"""
    c = state.charas[who]
    c.cflag[0] = 3
    c.cflag[20] = 0
    c.cflag[21] = 1
    c.cflag[23] = 0
    c.exp[data.index_of("EXP", "陥落経験")] += 1


def run_one(data, narration, seed: int, preset: str, max_shop: int, max_steps: int, save_dir: Path,
            enable_intimidation: bool = False, setup=None, enable_akuoti: bool = False, corrupt: int = 0) -> dict:
    """`setup(state)`：開局直後に状態を変える（テスト用）。"""
    policy = random.Random(seed)
    s = GameSession(data, save_dir, rng=GameRng(seed), narration=narration)
    s.input(0)
    s.input(0 if preset == "default" else 1)
    if enable_intimidation:
        s.state.flag[804] |= 1 << 10
    if enable_akuoti:
        s.state.flag[804] |= (1 << 1) | (1 << 9)
    if corrupt:
        _corrupt(s.state, data, corrupt)
    if setup is not None:
        setup(s.state)
    shops = 0
    defeated_at: int | None = None
    gameover_at: int | None = None
    reason = "上限"
    steps = 0
    mark = len(s.out.lines)
    while steps < max_steps:
        steps += 1
        st = s.state
        if st is not None and defeated_at is None and any(st.charas[i].cflag[0] == 1 for i in range(1, st.charanum)):
            defeated_at = shops
        if st is not None and gameover_at is None and st.flag[0] == 0:  # CHANGE_GAMEOVER_MODE 後
            gameover_at = shops
        if s.phase == Phase.HALTED:
            text = next((ln.text for ln in reversed(s.out.lines) if ln.text.startswith(HALT_PREFIX)), "")
            reason = text[len(HALT_PREFIX):].rstrip("）")
            break
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
    return {"seed": seed, "reason": reason, "shops": shops, "defeated_at": defeated_at, "gameover_at": gameover_at}


def summarize(results: list[dict], preset: str, key_len: int = 40) -> None:
    """停止原因・SHOP 次數・事件次數の集計を表示（`--load` で分割実行の結果を合算するときも使う）。"""
    counts: Counter = Counter()
    games_with: Counter = Counter()
    for r in results:
        counts.update(r.get("events", {}))
        games_with.update(r.get("events", {}).keys())
    n = len(results)
    shops = [r["shops"] for r in results]
    lost = [r for r in results if r["defeated_at"] is not None]
    print(f"preset={preset} games={n}")
    print(f"SHOP 次數：平均 {sum(shops) / n:.2f}／最多 {max(shops)}")
    after = [r["shops"] - r["defeated_at"] for r in lost]
    print(f"敗北局 {len(lost)}" + (f"／敗北後 SHOP 平均 {sum(after) / len(after):.2f}" if after else ""))
    go = [r for r in results if r["gameover_at"] is not None]
    go_after = [r["shops"] - r["gameover_at"] for r in go]
    print(f"ゲームオーバーモード進入 {len(go)}" + (f"／進入後 SHOP 平均 {sum(go_after) / len(go_after):.2f}／最多 {max(go_after)}" if go else ""))
    print("停止原因：")
    for k, v in Counter(r["reason"][: key_len] for r in results).most_common():
        print(f"  {v:4d}  {k}")
    print("強制發生事件（總次數／發生局數）：" if counts else "強制發生事件：なし")
    for k in sorted(counts):
        print(f"  {counts[k]:5d}／{games_with[k]:3d}  {k}")
    if go:
        print("停止原因（ゲームオーバーモード進入局）：")
        for k, v in Counter(r["reason"][: key_len] for r in go).most_common():
            print(f"  {v:4d}  {k}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=("default", "tokusou"), default="default")
    p.add_argument("--seeds", default="0-249")
    p.add_argument("--max-shop", type=int, default=200)
    p.add_argument("--max-steps", type=int, default=100000)
    p.add_argument("--key-len", type=int, default=40)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--enable-intimidation", action="store_true")
    p.add_argument("--enable-akuoti", action="store_true")
    p.add_argument("--dump", help="各局の結果を JSON Lines で書き出す（分割実行用）")
    p.add_argument("--load", nargs="+", help="--dump の出力を読んで合算表示だけする")
    p.add_argument("--corrupt", type=int, default=0, help="開局時に悪堕ちにするキャラ番号（テスト用）")
    a = p.parse_args(argv)
    if a.load:
        results = []
        for path in a.load:
            with open(path, encoding="utf-8") as fp:
                results.extend(json.loads(line) for line in fp if line.strip())
        summarize(results, a.preset, a.key_len)
        return 0
    counts = install_event_counters()
    games_with: Counter = Counter()
    data = load_game_data(default_csv_dir())
    narration = CatalogNarrationService(default_csv_dir().parent / "ERB", data)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in _parse_seeds(a.seeds):
            before = Counter(counts)
            r = run_one(data, narration, seed, a.preset, a.max_shop, a.max_steps, Path(tmp), a.enable_intimidation,
                        enable_akuoti=a.enable_akuoti, corrupt=a.corrupt)
            r["events"] = dict(counts - before)
            games_with.update(r["events"].keys())
            results.append(r)
            if a.verbose:
                print(r, flush=True)
    if a.dump:
        with open(a.dump, "w", encoding="utf-8", newline="\n") as fp:
            for r in results:
                fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    summarize(results, a.preset, a.key_len)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
