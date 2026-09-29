"""角色（era 的 CHARA 一筆）。"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from ..data.csv_loader import CharaDef
from .sparse import IntArray, StrArray


@dataclass
class Character:
    """era 角色變數。陣列一律稀疏：未設定讀為 0／空字串。

    欄位名稱＝era 變數名小寫。`tcvarn` 是 `ERB/DIM.ERH`:9 的 `#DIM CHARADATA TCVARn`（不存檔）。
    CDFLAG 為 2 維，索引用 `(第一維, 第二維)`。
    """

    no: int
    name: str = ""
    callname: str = ""
    nickname: str = ""
    mastername: str = ""
    base: IntArray = field(default_factory=IntArray)
    maxbase: IntArray = field(default_factory=IntArray)
    abl: IntArray = field(default_factory=IntArray)
    talent: IntArray = field(default_factory=IntArray)
    exp: IntArray = field(default_factory=IntArray)
    mark: IntArray = field(default_factory=IntArray)
    palam: IntArray = field(default_factory=IntArray)
    juel: IntArray = field(default_factory=IntArray)
    ex: IntArray = field(default_factory=IntArray)
    nowex: IntArray = field(default_factory=IntArray)
    stain: IntArray = field(default_factory=IntArray)
    cflag: IntArray = field(default_factory=IntArray)
    cdflag: IntArray = field(default_factory=IntArray)
    equip: IntArray = field(default_factory=IntArray)
    relation: IntArray = field(default_factory=IntArray)
    tcvarn: IntArray = field(default_factory=IntArray)
    cstr: StrArray = field(default_factory=StrArray)

    @classmethod
    def from_def(cls, d: CharaDef) -> Character:
        """對應 era `ADDCHARA 番号`：以角色 CSV 的初期值建立。

        「基礎」同時設定 BASE 與 MAXBASE。RELATION 保持 CSV 原樣（索引 = 對方 CSV 番号）；
        轉成固有番號（CFLAG:240）的處理屬於開局流程（S03，見 unresolved）。
        """
        return cls(
            no=d.no,
            name=d.name,
            callname=d.callname,
            nickname=d.nickname,
            mastername=d.mastername,
            base=IntArray(d.base),
            maxbase=IntArray(d.maxbase),
            abl=IntArray(d.abl),
            talent=IntArray(d.talent),
            exp=IntArray(d.exp),
            mark=IntArray(d.mark),
            juel=IntArray(d.juel),
            cflag=IntArray(d.cflag),
            equip=IntArray(d.equip),
            relation=IntArray(d.relation),
            cstr=StrArray(d.cstr),
        )

    # 不存檔的欄位：TCVARn 是 `#DIM CHARADATA`（無 SAVEDATA），Emuera 不存
    # （GameProc/UserDefinedVariable.cs:26、150–152；文字存檔下 CHARADATA 不能加 SAVEDATA，:315–320）。
    # 讀檔後角色是新建的，TCVARn 為 0（VariableEvaluator.cs@LoadFromStream:2178–2184）。
    NOT_SAVED = frozenset({"tcvarn"})

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(self):
            if f.name in self.NOT_SAVED:
                continue
            value = getattr(self, f.name)
            out[f.name] = value.to_json() if isinstance(value, (IntArray, StrArray)) else value
        return out

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Character:
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            if f.name not in obj or f.name in cls.NOT_SAVED:
                continue  # 舊版存檔缺欄位 → 預設值
            value = obj[f.name]
            if f.name == "cstr":
                value = StrArray.from_json(value)
            elif isinstance(value, dict):
                value = IntArray.from_json(value)
            kwargs[f.name] = value
        return cls(**kwargs)
