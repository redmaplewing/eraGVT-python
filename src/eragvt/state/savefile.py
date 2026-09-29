"""版本化 JSON 存讀檔。

格式：`{"format": "eragvt-save", "version": 1, "game_code": …, "game_version": …, "comment": …, "state": {…}}`。
輸出為正規化 JSON（鍵排序、固定縮排、UTF-8、LF），同一狀態永遠得到相同位元組。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..data.csv_loader import GameData, dotnet_try_parse_int
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


@dataclass(frozen=True)
class GameIdentity:
    """GameBase.csv 的「コード」「バージョン」「バージョン違い認める」。存檔時寫入、讀檔時檢查
    （VariableEvaluator.cs@SaveToStream:2146–2149、@LoadFromStream:2166–2171；GameBase.cs:40–55）。"""

    code: int = 0
    version: int = 0
    version_defined: bool = False
    compatible_min_version: int = -1

    @classmethod
    def from_data(cls, data: GameData) -> GameIdentity:
        version = dotnet_try_parse_int(data.game_base.get("バージョン", ""), 64)
        min_version = dotnet_try_parse_int(data.game_base.get("バージョン違い認める", ""), 64)
        return cls(
            code=data.game_base_int("コード", 0),
            version=version if version is not None else 0,
            version_defined=version is not None,
            compatible_min_version=min_version if min_version is not None else -1,
        )

    def code_matches(self, saved: int) -> bool:
        return saved == 0 or saved == self.code  # GameBase.cs@UniqueCodeEqualTo:40–46

    def version_ok(self, saved: int) -> bool:  # GameBase.cs@CheckVersion:48–55
        if not self.version_defined and saved != 1000:
            return True
        if self.compatible_min_version <= saved:
            return True
        return self.version == saved


def dump_save(state: GameState, comment: str = "", identity: GameIdentity = GameIdentity()) -> bytes:
    """`comment` 對應 Emuera 的 SAVEDATA_TEXT（存檔時刻 + `@SAVEINFO` 的 PUTFORM 內容）。"""
    return _dump({
        "format": SAVE_FORMAT,
        "version": SAVE_VERSION,
        "game_code": identity.code,
        "game_version": identity.version,
        "comment": comment,
        "state": state.to_json(),
    })


def load_save(
    raw: bytes, rng: GameRng | None = None, identity: GameIdentity | None = None
) -> tuple[GameState, str]:
    """回傳 `(狀態, comment)`。舊版本依 `SAVE_MIGRATIONS` 逐版升級。

    給了 `identity` 時照 Emuera 檢查遊戲代碼與版本；讀入的狀態 `temp.last_load_version`
    設為存檔的遊戲版本（era `LASTLOAD_VERSION`，VariableEvaluator.cs:2174）。
    """
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveFormatError(f"存檔無法解析：{exc}") from exc
    version = _check_header(obj, SAVE_FORMAT, SAVE_VERSION)
    while version < SAVE_VERSION:
        obj = SAVE_MIGRATIONS[version](obj)
        version += 1
    game_code = obj.get("game_code", 0)
    game_version = obj.get("game_version", 0)
    if identity is not None:
        if not identity.code_matches(game_code):
            raise SaveFormatError("異なるゲームのセーブデータです")
        if not identity.version_ok(game_version):
            raise SaveFormatError("セーブデータのバーションが異なります")
    state = GameState.from_json(obj["state"], rng=rng)
    state.temp.last_load_version = game_version
    return state, obj.get("comment", "")


def dump_global(g: GlobalState) -> bytes:
    return _dump({"format": GLOBAL_FORMAT, "version": GLOBAL_VERSION, "global": g.to_json()})


def load_global(raw: bytes) -> GlobalState:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveFormatError(f"全域資料無法解析：{exc}") from exc
    _check_header(obj, GLOBAL_FORMAT, GLOBAL_VERSION)
    return GlobalState.from_json(obj["global"])


def save_to_file(
    path: Path, state: GameState, comment: str = "", identity: GameIdentity = GameIdentity()
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_save(state, comment, identity))


def load_from_file(
    path: Path, rng: GameRng | None = None, identity: GameIdentity | None = None
) -> tuple[GameState, str]:
    return load_save(path.read_bytes(), rng=rng, identity=identity)


def read_save_comment(path: Path) -> str | None:
    """存檔一覽用：只讀 comment；檔案不存在或格式不符回 None。"""
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
        _check_header(obj, SAVE_FORMAT, SAVE_VERSION)
    except (UnicodeDecodeError, json.JSONDecodeError, SaveFormatError):
        return None
    return obj.get("comment", "")


def save_global_file(path: Path, g: GlobalState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_global(g))


def load_global_file(path: Path) -> GlobalState:
    """era `LOADGLOBAL`：檔案不存在時回傳空的全域資料（原作據此判斷「真正的初次啟動」）。"""
    if not path.exists():
        return GlobalState()
    return load_global(path.read_bytes())
