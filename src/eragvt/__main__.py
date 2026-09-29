"""`python -m eragvt`：啟動本機 Web（預設 http://127.0.0.1:8000）。

`--check-data`：只載入原作 CSV、列出摘要，並確認開局狀態能存讀檔。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .data import GameData, default_csv_dir, load_game_data
from .state import GameRng, GameState, dump_save, load_save


def check_data(csv_dir: Path) -> int:
    data = load_game_data(csv_dir)
    print(f"CSV: {csv_dir}")
    for var, table in data.names.items():
        if var == "ITEM":
            continue
        print(f"  {var:<8} {len(table):>5} 筆")
    print(f"  ITEM     {len(data.items):>5} 筆（含價格）")
    print(f"  STR      {len(data.str_defaults):>5} 筆（初期值）")
    print(f"  角色     {len(data.charas):>5} 名")
    # 註解行也會產生引擎警告（Emuera 不處理 `;`），只列數量。
    chara_warnings = sum(len(c.warnings) for c in data.charas.values())
    print(f"  讀取警告：角色 CSV {chara_warnings} 件、全域 {len(data.warnings)} 件")
    return check_state_roundtrip(data)


def check_state_roundtrip(data: GameData) -> int:
    """新遊戲開局（MASTER + 特捜戦隊 301/302/303）後，確認存→讀→存逐位元組一致。"""
    from .game.opening import event_first

    state = GameState.new(data, rng=GameRng(0))
    event_first(state, data)
    raw = dump_save(state)
    ok = dump_save(load_save(raw)[0]) == raw
    print(f"開局狀態存讀檔：{'OK' if ok else '不一致'}（{state.charanum} 名，{len(raw)} bytes）")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    # Windows 主控台預設 cp950，日文路徑/名稱會變亂碼
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="eragvt")
    parser.add_argument("--check-data", action="store_true", help="載入原作 CSV 並列出摘要")
    parser.add_argument("--csv-dir", type=Path, default=None, help="原作 CSV 目錄")
    parser.add_argument("--save-dir", type=Path, default=Path("saves"), help="存檔目錄（預設 ./saves）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    csv_dir = args.csv_dir or default_csv_dir()
    if args.check_data:
        return check_data(csv_dir)

    import uvicorn

    from .web import create_app

    app = create_app(load_game_data(csv_dir), args.save_dir)
    print(f"eraGVT: http://{args.host}:{args.port}/")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
