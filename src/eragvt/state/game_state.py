"""遊戲狀態：存檔變數（GameState）與跨存檔的全域資料（GlobalState）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..data.csv_loader import GameData
from .character import Character
from .rng import GameRng
from .sparse import IntArray, StrArray

# GameBase.csv `最初からいるキャラ,999`
DEFAULT_MASTER_NO = 999


@dataclass
class TempVars:
    """不存檔的 `#DIM` 變數（Emuera 只存 SAVEDATA／CHARADATA）。ERB/DIM.ERH"""

    turn_limit: int = 0  # ターン上限（:280）
    max_palam: IntArray = field(default_factory=IntArray)  # MAX_PALAM（:138）
    common_palam: IntArray = field(default_factory=IntArray)  # COMMON_PALAM（:16）
    battle_situation: str = ""  # 特殊戦闘シチュエーション（イベントから派生する特殊戦闘/DIM.ERH:3）


@dataclass
class GameState:
    """一份存檔的內容。欄位名＝era 變數名小寫。

    存檔範圍：era 內建存檔變數 + `SHIELD`（DIM.ERH:155 SAVEDATA）+ `MOB_FLAG`（:169 SAVEDATA，
    2 維，索引 `(分類, 番號)`）。`temp` 與 `rng` 不存。
    """

    day: int = 0
    time: int = 0  # 0 = 晝、1 = 夜
    money: int = 0
    target: int = 0
    assi: int = -1
    flag: IntArray = field(default_factory=IntArray)
    tflag: IntArray = field(default_factory=IntArray)
    item: IntArray = field(default_factory=IntArray)  # 本作 = 衣裝持有
    savestr: StrArray = field(default_factory=StrArray)
    shield: IntArray = field(default_factory=IntArray)
    mob_flag: IntArray = field(default_factory=IntArray)
    charas: list[Character] = field(default_factory=list)
    temp: TempVars = field(default_factory=TempVars, compare=False)
    rng: GameRng = field(default_factory=GameRng, compare=False, repr=False)

    # --- 角色列表（index 0 = MASTER） -------------------------------------

    MASTER = 0

    @classmethod
    def new(cls, data: GameData, rng: GameRng | None = None) -> GameState:
        """新遊戲的初始狀態：角色列表只有 MASTER（Chara999 ダミー）。

        原作 `@EVENTFIRST` 以 `SWAPCHARA 0, 1` / `DELCHARA 1` 達成同樣結果
        （`ゲーム内_イベント発生/オープニング処理.ERB`:63–64）。
        """
        master_no = int(data.game_base.get("最初からいるキャラ", [DEFAULT_MASTER_NO])[0])
        state = cls(rng=rng or GameRng())
        state.add_chara(data, master_no)
        return state

    @property
    def charanum(self) -> int:
        """era `CHARANUM`。"""
        return len(self.charas)

    @property
    def master(self) -> Character:
        return self.charas[self.MASTER]

    @property
    def target_chara(self) -> Character:
        return self.charas[self.target]

    def add_chara(self, data: GameData, no: int) -> Character:
        """era `ADDCHARA 番号`：加到列表尾端。"""
        if no not in data.charas:
            raise KeyError(f"沒有番号 {no} 的角色 CSV")
        chara = Character.from_def(data.charas[no])
        self.charas.append(chara)
        return chara

    def del_chara(self, index: int) -> None:
        """era `DELCHARA index`：後面的角色往前補。TARGET／ASSI 不自動調整（與 era 相同，呼叫端負責）。"""
        if index == self.MASTER:
            raise ValueError("不能刪除 MASTER")
        del self.charas[index]

    def swap_chara(self, a: int, b: int) -> None:
        """era `SWAPCHARA a, b`。"""
        self.charas[a], self.charas[b] = self.charas[b], self.charas[a]

    # --- 序列化 -------------------------------------------------------------

    def to_json(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "time": self.time,
            "money": self.money,
            "target": self.target,
            "assi": self.assi,
            "flag": self.flag.to_json(),
            "tflag": self.tflag.to_json(),
            "item": self.item.to_json(),
            "savestr": self.savestr.to_json(),
            "shield": self.shield.to_json(),
            "mob_flag": self.mob_flag.to_json(),
            "charas": [c.to_json() for c in self.charas],
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any], rng: GameRng | None = None) -> GameState:
        return cls(
            day=obj["day"],
            time=obj["time"],
            money=obj["money"],
            target=obj["target"],
            assi=obj["assi"],
            flag=IntArray.from_json(obj["flag"]),
            tflag=IntArray.from_json(obj["tflag"]),
            item=IntArray.from_json(obj["item"]),
            savestr=StrArray.from_json(obj["savestr"]),
            shield=IntArray.from_json(obj["shield"]),
            mob_flag=IntArray.from_json(obj["mob_flag"]),
            charas=[Character.from_json(c) for c in obj["charas"]],
            rng=rng or GameRng(),
        )


@dataclass
class GlobalState:
    """跨存檔資料（era `SAVEGLOBAL`／`LOADGLOBAL`）：GLOBAL、GLOBALS、MOB_GLOBAL（DIM.ERH:170）。"""

    global_: IntArray = field(default_factory=IntArray)
    globals_: StrArray = field(default_factory=StrArray)
    mob_global: IntArray = field(default_factory=IntArray)

    def to_json(self) -> dict[str, Any]:
        return {
            "global": self.global_.to_json(),
            "globals": self.globals_.to_json(),
            "mob_global": self.mob_global.to_json(),
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> GlobalState:
        return cls(
            global_=IntArray.from_json(obj["global"]),
            globals_=StrArray.from_json(obj["globals"]),
            mob_global=IntArray.from_json(obj["mob_global"]),
        )
