"""原作資料（`source/earGVP/CSV`）的載入。"""

from pathlib import Path

from .csv_loader import CharaDef, CsvFormatError, GameData, ItemDef, load_game_data

__all__ = [
    "CharaDef",
    "CsvFormatError",
    "GameData",
    "ItemDef",
    "default_csv_dir",
    "load_game_data",
]


def default_csv_dir() -> Path:
    """repo 內原作 CSV 的位置（`source/earGVP/CSV`，唯讀）。"""
    return Path(__file__).resolve().parents[3] / "source" / "earGVP" / "CSV"
