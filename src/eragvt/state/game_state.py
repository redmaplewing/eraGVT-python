"""遊戲狀態：存檔變數（GameState）與跨存檔的全域資料（GlobalState）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..data.csv_loader import GameData
from .character import Character
from .rng import GameRng
from .sparse import IntArray, StrArray


@dataclass
class TempVars:
    """不存檔的 `#DIM` 變數（Emuera 只存 SAVEDATA／CHARADATA）。ERB/DIM.ERH"""

    turn_limit: int = 0  # ターン上限（:280）
    max_palam: IntArray = field(default_factory=IntArray)  # MAX_PALAM（:138）
    common_palam: IntArray = field(default_factory=IntArray)  # COMMON_PALAM（:16）
    common_exp: IntArray = field(default_factory=IntArray)  # COMMON_EXP（:18、COMMON_PRISON の経験受け渡し）
    battle_situation: str = ""  # 特殊戦闘シチュエーション（イベントから派生する特殊戦闘/DIM.ERH:3）
    # era LASTLOAD_VERSION：新遊戲 -1、讀檔後 = 存檔的遊戲版本（VariableData.cs:48、653；VariableEvaluator.cs:2174）
    last_load_version: int = -1
    # --- 戰鬥（S05）用的非存檔變數 ---
    # 內建 UP／LOSEBASE（非角色陣列；VariableCode.cs 中不屬 __SAVE__，UpdateAfterShowUsercom 清零）
    up: IntArray = field(default_factory=IntArray)
    losebase: IntArray = field(default_factory=IntArray)
    # 內建 SELECTCOM／PREVCOM／NEXTCOM（VariableEvaluator.cs@UpdateInBeginTrain:1425–1426）
    selectcom: int = 0
    prevcom: int = -1
    nextcom: int = -1
    # DIM.ERH:139–143 CLOTH_NO_INNER／CLOTH_OUTER_PER／CLOTH_OUTER_DEF／CLOTH_INNER_PER／CLOTH_INNER_DEF
    cloth: IntArray = field(default_factory=IntArray)
    # DIM.ERH:159–164 TENTACLE_SIZE／TENTACLE_NUM（2 維，索引 (i, j)）、EX_COM、SH_COM、INSERT
    tentacle_size: IntArray = field(default_factory=IntArray)
    tentacle_num: IntArray = field(default_factory=IntArray)
    ex_com: int = 0
    sh_com: int = 0
    insert: int = 0
    # DIM.ERH:13 RANDCHOOSE_NUM（稀疏：index → 值）
    randchoose: IntArray = field(default_factory=IntArray)
    # ゲーム内_戦闘処理/REPORT.ERH:2 TCREPORT
    tcreport: IntArray = field(default_factory=IntArray)
    # 函式的 LOCAL 是「每個函式各一份、呼叫間保留」的靜態變數，只在 ResetData／讀檔時歸零
    # （reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs@SetDefaultLocalValue:514–520）。
    # 原作有幾處依賴「上次呼叫留下的值」（例：DAMAGE の LOCAL:7、PALAMLV_F の LOCAL），以 (函式名, 索引) 保存。
    locals: dict[tuple[str, int], int] = field(default_factory=dict)
    # インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS の関数内 static #DIM（:7 `NOWLOOPNUM=0`、:19 `バイラルメディアフラグ=-1`）。
    # 初期値は宣言の値（GameData/Variable/VariableToken.cs@StaticInt1DVariableToken.SetDefault:1861–1865）。
    flashnews_loopnum: int = 0
    flashnews_viral: int = -1
    # 口上／地の文 catalog 執行器（eragvt.narration）用：LOCALS・ARG・ARGS・函式內 #DIM（靜態）、RESULT／RESULTS／COUNT、
    # 口上專用的非 SAVEDATA #DIM（真面目_フラグ_シチュ 等）。鍵 = (變數, 索引)。不存檔（與 Emuera 的非 SAVEDATA 相同）。
    narr: dict = field(default_factory=dict)


@dataclass
class GameState:
    """一份存檔的內容。欄位名＝era 變數名小寫。

    存檔範圍（reference/emuera-1824/Emuera/GameData/Variable/VariableCode.cs:31–118、
    VariableData.cs@SaveToStream:663 / @SaveToStreamExtended:689）：內建整數陣列中 0x00–0x3B 的存檔區
    （DAY MONEY ITEM FLAG TFLAG … TARGET ASSI … TIME …）+ SAVESTR + SAVEDATA 的 `#DIM`
    （`SHIELD`：DIM.ERH:155、`MOB_FLAG`：:169，2 維索引 `(分類, 番號)`）+ 全部角色。
    本類別只建模本作用得到的存檔變數；未建模的存檔變數一律是 0，存不存結果相同。
    `temp`（非 SAVEDATA 的 `#DIM`）與 `rng` 不存；讀檔時 Emuera 會把它們重設為預設值
    （VariableEvaluator.cs@LoadFromStream:2172–2173 → VariableData.cs@SetDefaultLocalValue:514）。
    """

    # DAY は配列：DAY:0 = 日数、DAY:1 = 殲滅猶予の延長日数、DAY:2 = 半日単位の通算
    # （インターミッション画面/SHOP.ERB:411、ゲーム内_イベント発生/エンディング/ENDING.ERB:747 など）
    day: IntArray = field(default_factory=IntArray)
    time: int = 0  # 0 = 晝、1 = 夜
    money: int = 0
    # ResetData 後 TARGET=1、ASSI=-1（VariableData.cs@SetDefaultValue:644–647）
    target: int = 1
    assi: int = -1
    flag: IntArray = field(default_factory=IntArray)
    tflag: IntArray = field(default_factory=IntArray)
    item: IntArray = field(default_factory=IntArray)  # 本作 = 衣裝持有
    savestr: StrArray = field(default_factory=StrArray)
    shield: IntArray = field(default_factory=IntArray)
    mob_flag: IntArray = field(default_factory=IntArray)
    # 內建 RESULT（整數 1 維、大小 1000：reference/emuera-1824/Emuera/GameData/Variable/VariableCode.cs:44 0x0A、
    # GameData/ConstantData.cs@setDefaultArrayLength:147–148）。0x0A < __COUNT_SAVE_INTEGER_ARRAY__（0x3C）→ 存檔對象
    # （GameData/Variable/VariableToken.cs:74–77、VariableData.cs@SaveToStream:663–674），讀檔時以存檔值覆寫；
    # 新遊戲 ResetData 清零（VariableData.cs@SetDefaultValue:538–）；BEGIN TRAIN 不清（VariableEvaluator.cs@UpdateInBeginTrain:1422–）。
    # 跨函式共用：原作有讀「前一次 RESULT」的地方（EVENT_PALAM_HOSEI 的悪堕ち分岐等）。寫入來源一覽：docs/wiki/python/result.md。
    result: IntArray = field(default_factory=IntArray)
    # 內建 RESULTS（字串 1 維、大小 100：VariableCode.cs:110 0x02、ConstantData.cs@setDefaultArrayLength:154–155；
    # 本作 CSV/VariableSize.csv 未指定）。0x02 ≥ __COUNT_SAVE_STRING_ARRAY__（0x01，:105）且無 __SAVE_EXTENDED__ → **不存檔**
    # （VariableData.cs@SaveToStream:663–674、VariableIdentifier.cs:248–256）；新遊戲 ResetData 與讀檔時 SetDefaultValue 清為空
    # （VariableEvaluator.cs@ResetData:1132–1139、@LoadFromStream:2173／@LoadFromStreamBinary:2339 → VariableData.cs:558–574）；
    # BEGIN TRAIN 不清（VariableEvaluator.cs@UpdateInBeginTrain:1422–1460 只清 TSTR）。
    # 跨函式共用（S22）：CORRPUTION.ERB@CORRUPTTION_GET_NANORI_FINAL:787 讀前一次的 RESULTS:2。寫入來源：docs/wiki/python/result.md。
    # 不存檔 → to_json／from_json 不含；compare=False（存讀檔往返的比較不看它）。
    results: StrArray = field(default_factory=StrArray, compare=False)
    charas: list[Character] = field(default_factory=list)
    temp: TempVars = field(default_factory=TempVars, compare=False)
    rng: GameRng = field(default_factory=GameRng, compare=False, repr=False)

    # --- 角色列表（index 0 = MASTER） -------------------------------------

    MASTER = 0

    @classmethod
    def new(cls, data: GameData, rng: GameRng | None = None) -> GameState:
        """標題選「最初からはじめる」後、呼叫 `@EVENTFIRST` 前的狀態
        （Process.SystemProc.cs@endOpenning:197–209）：`ResetData` 後依檔名番號加入角色 0，
        再加入 GameBase.csv「最初からいるキャラ」（本作 999）。

        原作 `@EVENTFIRST` 接著 `SWAPCHARA 0, 1`／`DELCHARA 1` 只留下 999（見 `eragvt.game.opening`）。
        """
        state = cls(rng=rng or GameRng())
        state.add_chara_from_csv_no(data, 0)
        default_chara = data.game_base_int("最初からいるキャラ", 0)
        if default_chara > 0:
            state.add_chara_from_csv_no(data, default_chara)
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
        """era `ADDCHARA 番号`：加到列表尾端（VariableEvaluator.cs@AddCharacter:1026）。"""
        if no not in data.charas:
            raise KeyError(f"沒有番号 {no} 的角色 CSV")
        chara = Character.from_def(data.charas[no])
        self.charas.append(chara)
        return chara

    def add_chara_from_csv_no(self, data: GameData, csv_no: int) -> Character:
        """依檔名番號加入角色；找不到時加入空角色（VariableEvaluator.cs@AddCharacterFromCsvNo:1044–1052）。"""
        for d in data.charas.values():
            if d.csv_no == csv_no:
                chara = Character.from_def(d)
                break
        else:
            chara = Character(no=0)
        self.charas.append(chara)
        return chara

    def del_chara(self, index: int) -> None:
        """era `DELCHARA index`：後面的角色往前補。TARGET／ASSI 不自動調整（與 era 相同，呼叫端負責）。"""
        if index == self.MASTER:
            raise ValueError("不能刪除 MASTER")
        del self.charas[index]

    def set_result_x(self, *values: int) -> None:
        """多值 `RETURN a, b, …`：RESULT:0〜 依序寫入給定個數，其餘格子保留
        （GameProc/Function/Instraction.Child.cs@RETURN_Instruction:2006–2023 → VariableEvaluator.cs@SetResultX:1732–1740）。"""
        for i, v in enumerate(values):
            if i >= 1000:
                return
            self.result[i] = int(v)

    RESULTS_SIZE = 100

    def set_results_array(self, values: list[str]) -> None:
        """`VARSET RESULTS, ""` → `ARRAYCOPY "src", "RESULTS"`（TagSetText.ERB:178–179／:270–271）：全消去後、先頭から
        RESULTS の長さ（100）まで写す（VariableEvaluator.cs@CopyArray:764–775 は短い方の長さ）。"""
        self.results.clear()
        for i, v in enumerate(values[: self.RESULTS_SIZE]):
            self.results[i] = v

    def swap_chara(self, a: int, b: int) -> None:
        """era `SWAPCHARA a, b`。"""
        self.charas[a], self.charas[b] = self.charas[b], self.charas[a]

    # --- 序列化 -------------------------------------------------------------

    def to_json(self) -> dict[str, Any]:
        return {
            "day": self.day.to_json(),
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
            "result": self.result.to_json(),
            "charas": [c.to_json() for c in self.charas],
        }

    @classmethod
    def from_json(cls, obj: dict[str, Any], rng: GameRng | None = None) -> GameState:
        return cls(
            day=IntArray.from_json(obj["day"]),
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
            result=IntArray.from_json(obj["result"]),
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
