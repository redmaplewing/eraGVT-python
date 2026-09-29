"""`python -m eragvt`：啟動入口。

Web 介面在 S03 才實作；目前只提供 `--check-data` 檢查原作 CSV 能否完整載入、開局狀態能否存讀檔。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .data import default_csv_dir, load_game_data
from .state import GameState, dump_save, load_save


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
    warnings = [w for c in data.charas.values() for w in c.warnings]
    for w in warnings:
        print(f"  警告：{w}")
    return check_state_roundtrip(data)


def check_state_roundtrip(data) -> int:
    """以開局隊伍（MASTER + 特捜戦隊 301/302/303）建狀態，確認存→讀→存逐位元組一致。"""
    state = GameState.new(data)
    for no in (301, 302, 303):
        state.add_chara(data, no)
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
    args = parser.parse_args(argv)
    if args.check_data:
        return check_data(args.csv_dir or default_csv_dir())
    print("Web 介面尚未實作（預定 S03）。可用 --check-data 檢查原作資料。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
