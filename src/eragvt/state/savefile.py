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
SAVE_VERSION = 3
GLOBAL_VERSION = 1


def _migrate_1_to_2(obj: dict[str, Any]) -> dict[str, Any]:
    """版本 2（S21）：存檔加入內建 RESULT（`GameState.result`）。舊存檔沒有 → 全 0。"""
    obj = dict(obj)
    obj["state"] = dict(obj["state"])
    obj["state"].setdefault("result", {})
    obj["version"] = 2
    return obj


# 舊版 → 新版的轉換：`{舊版本: fn(payload) -> 下一版 payload}`。
def _migrate_2_to_3(obj: dict[str, Any]) -> dict[str, Any]:
    """S35：既有未建模的 DA 均為0，補空稀疏陣列。"""
    obj["state"].setdefault("da", {})
    obj["version"] = 3
    return obj


SAVE_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {1: _migrate_1_to_2, 2: _migrate_2_to_3}


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


def dump_global(g: GlobalState, identity: GameIdentity = GameIdentity()) -> bytes:
    """era `SAVEGLOBAL` 的檔案內容：遊戲代碼・版本（`VariableEvaluator.cs@SaveGlobal`:2200–2233 寫
    ScriptUniqueCode／ScriptVersion）＋ GLOBAL・GLOBALS・`#DIM GLOBAL SAVEDATA`（MOB_GLOBAL）的全部內容
    （`VariableData.cs@SaveGlobalToStream`:904–908、`@SaveGlobalToStream1808`:916–935）。"""
    return _dump({
        "format": GLOBAL_FORMAT,
        "version": GLOBAL_VERSION,
        "game_code": identity.code,
        "game_version": identity.version,
        "global": g.to_json(),
    })


def load_global(raw: bytes, identity: GameIdentity | None = None) -> GlobalState:
    """給了 `identity` 時照 `VariableEvaluator.cs@LoadGlobal`:2256–2296 檢查遊戲代碼（UniqueCodeEqualTo）與版本（CheckVersion），
    不符 → `SaveFormatError`（LOADGLOBAL 失敗）。"""
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveFormatError(f"全域資料無法解析：{exc}") from exc
    _check_header(obj, GLOBAL_FORMAT, GLOBAL_VERSION)
    if identity is not None:
        if not identity.code_matches(obj.get("game_code", 0)):
            raise SaveFormatError("異なるゲームの全域資料です")
        if not identity.version_ok(obj.get("game_version", 0)):
            raise SaveFormatError("全域資料のバージョンが異なります")
    try:
        return GlobalState.from_json(obj["global"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveFormatError(f"全域資料の内容が不正：{exc}") from exc


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


GLOBAL_FILE_NAME = "global.json"  # Emuera は `Config.SavDir + "global.sav"`（VariableEvaluator.cs:1745）


class GlobalStore:
    """Emuera のグローバル変数（メモリ）と global.sav（ファイル）の組。

    - メモリ `mem`：GLOBAL・GLOBALS・MOB_GLOBAL。ResetData（新規ゲーム・RESETDATA）でもロードでも初期化されない
      （`VariableEvaluator.cs@ResetData`:1132–1141「グローバルは初期化しない」、`@LoadFromStream`:2173–2174 は
      SetDefaultValue／SetDefaultLocalValue のみ）。初期化はプロセス起動時と RESETGLOBAL（本作 0 件）だけ。
    - `save()` = SAVEGLOBAL：メモリの全内容をファイルへ（`@SaveGlobal`:2200–2252）。
    - `load()` = LOADGLOBAL：ファイルが無い／代碼・版本不符／読めない → False でメモリは変えない；成功 → メモリを
      ファイルの内容で置き換えて True（`@LoadGlobal`:2256–2310。配列は保存値の後ろを 0 で埋める：
      `Sub/EraDataStream.cs@ReadInt64Array`:77–102 → 全置換と同じ）。
    `path=None` のときはファイルの代わりにメモリ上のバイト列を使う（テスト・模擬用）。
    """

    def __init__(self, path: Path | None = None, identity: GameIdentity = GameIdentity()) -> None:
        self.mem = GlobalState()
        self.path = path
        self.identity = identity
        self._bytes: bytes | None = None
        # DEVIATION: S59 使用者批准，僅全新資料初始化現行遊戲版本。
        # ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:29–44 未設版本，
        # 會令下一次 ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53 覆寫新成就；既有（含損毀）檔不改。
        if not self.exists():
            self.mem.global_[3] = identity.version

    @classmethod
    def in_dir(cls, save_dir: Path, identity: GameIdentity = GameIdentity()) -> GlobalStore:
        return cls(save_dir / GLOBAL_FILE_NAME, identity)

    def exists(self) -> bool:
        return self.path.exists() if self.path is not None else self._bytes is not None

    def save(self) -> None:
        raw = dump_global(self.mem, self.identity)
        if self.path is None:
            self._bytes = raw
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_bytes(raw)

    def load(self) -> bool:
        try:
            if self.path is None:
                if self._bytes is None:
                    return False
                raw = self._bytes
            else:
                if not self.path.exists():
                    return False
                raw = self.path.read_bytes()
            self.mem = load_global(raw, self.identity)
        except (OSError, SaveFormatError):  # LoadGlobal:2297–2300 catch → false
            return False
        return True
