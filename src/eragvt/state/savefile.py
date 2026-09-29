"""版本化 JSON 存讀檔。

格式：`{"format": "eragvt-save", "version": 1, "comment": ..., "state": {...}}`。
輸出為正規化 JSON（鍵排序、固定縮排、UTF-8、LF），同一狀態永遠得到相同位元組。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .game_state import GameState, GlobalState
from .rng import GameRng

SAVE_FORMAT = "eragvt-save"
GLOBAL_FORMAT = "eragvt-global"
SAVE_VERSION = 1
GLOBAL_VERSION = 1

# 舊版 → 新版的轉換：`{舊版本: fn(payload) -> 下一版 payload}`。版本 1 之前沒有舊資料。
SAVE_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


class SaveFormatError(ValueError):
    """不是本程式的存檔，或版本無法處理。"""


def _dump(obj: dict[str, Any]) -> bytes:
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1)
    return (text + "\n").encode("utf-8")


def _check_header(obj: Any, fmt: str, current: int) -> int:
    if not isinstance(obj, dict) or obj.get("format") != fmt:
        raise SaveFormatError(f"不是 {fmt} 格式")
    version = obj.get("version")
    if type(version) is not int or version < 1:
        raise SaveFormatError(f"版本欄位不合法：{version!r}")
    if version > current:
        raise SaveFormatError(f"存檔版本 {version} 比程式支援的 {current} 新")
    return version


def dump_save(state: GameState, comment: str = "") -> bytes:
    """`comment` 對應 era 的存檔說明（原作 `@SAVEINFO` 產生的文字）。"""
    return _dump({"format": SAVE_FORMAT, "version": SAVE_VERSION, "comment": comment, "state": state.to_json()})


def load_save(raw: bytes, rng: GameRng | None = None) -> tuple[GameState, str]:
    """回傳 `(狀態, comment)`。舊版本依 `SAVE_MIGRATIONS` 逐版升級。"""
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveFormatError(f"存檔無法解析：{exc}") from exc
    version = _check_header(obj, SAVE_FORMAT, SAVE_VERSION)
    while version < SAVE_VERSION:
        obj = SAVE_MIGRATIONS[version](obj)
        version += 1
    return GameState.from_json(obj["state"], rng=rng), obj.get("comment", "")


def dump_global(g: GlobalState) -> bytes:
    return _dump({"format": GLOBAL_FORMAT, "version": GLOBAL_VERSION, "global": g.to_json()})


def load_global(raw: bytes) -> GlobalState:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveFormatError(f"全域資料無法解析：{exc}") from exc
    _check_header(obj, GLOBAL_FORMAT, GLOBAL_VERSION)
    return GlobalState.from_json(obj["global"])


def save_to_file(path: Path, state: GameState, comment: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_save(state, comment))


def load_from_file(path: Path, rng: GameRng | None = None) -> tuple[GameState, str]:
    return load_save(path.read_bytes(), rng=rng)


def save_global_file(path: Path, g: GlobalState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_global(g))


def load_global_file(path: Path) -> GlobalState:
    """era `LOADGLOBAL`：檔案不存在時回傳空的全域資料（原作據此判斷「真正的初次啟動」）。"""
    if not path.exists():
        return GlobalState()
    return load_global(path.read_bytes())
