"""遊戲狀態、角色、存讀檔與亂數。設計說明見 `docs/wiki/python/state.md`。"""

from .character import Character
from .game_state import GameState, GlobalState, TempVars
from .rng import FixedRng, GameRng
from .savefile import SaveFormatError, dump_save, load_save
from .sparse import IntArray, StrArray

__all__ = [
    "Character",
    "FixedRng",
    "GameRng",
    "GameState",
    "GlobalState",
    "IntArray",
    "SaveFormatError",
    "StrArray",
    "TempVars",
    "dump_save",
    "load_save",
]
