"""原作 `CSV/` 的載入器，依 Emuera 1.824 的解析規則實作。

引擎依據（路徑相對 `reference/emuera-1824/Emuera/`）：
- 讀行：`Sub/EraStreamReader.cs@ReadEnabledLine`:62–95（空行略過、行首空白略過，**不處理 `;` 註解**）。
- 名稱表：`GameData/ConstantData.cs@loadDataTo`:1300–1343。
- 角色 CSV：`GameData/ConstantData.cs@loadCharacterData`:952–1062、`@toCharacterTemplate`:1106–1289、
  數值解析 `@tryToInt64`:1064–1104（→ `Sub/LexicalAnalyzer.cs@ReadInt64`:133）。
- `_Replace.csv`：`Config/ConfigData.cs@LoadReplaceFile`:528–563、`Config/ConfigItem.cs@TryParse`:108。
- `GameBase.csv`：`GameData/GameBase.cs@LoadGameBaseCsv`:86。
- `VariableSize.csv`：`GameData/ConstantData.cs@changeVariableSizeData`:224。
細節見 `docs/wiki/era/csv.md`。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 變數名 → 名稱表檔名（`CSV/` 直下）。
NAME_TABLE_FILES: dict[str, str] = {
    "ABL": "Abl.csv",
    "BASE": "Base.csv",
    "TALENT": "Talent.csv",
    "EXP": "Exp.csv",
    "MARK": "Mark.csv",
    "PALAM": "Palam.csv",
    "JUEL": "Juel.csv",
    "EX": "Ex.csv",
    "ITEM": "Item.csv",
    "TRAIN": "Train.csv",
    "CDFLAG1": "Cdflag1.csv",
    "CDFLAG2": "Cdflag2.csv",
}

# 角色 CSV 第一欄（ToUpper 後）→ (變數名, 索引名稱表)。ConstantData.cs:1122–1204
# 名稱表 None = 不接受名稱索引（RELATION）；"" = 本作沒有該名稱表（cflag.csv 等），名稱索引一律失敗。
# JUEL 的名稱索引查的是 palam.csv（:1190 `nameToIntDics[paramIndex]`），不是 Juel.csv。
_CHARA_ARRAY_KEYS: dict[str, tuple[str, str | None]] = {
    "MARK": ("MARK", "MARK"),
    "刻印": ("MARK", "MARK"),
    "EXP": ("EXP", "EXP"),
    "経験": ("EXP", "EXP"),
    "ABL": ("ABL", "ABL"),
    "能力": ("ABL", "ABL"),
    "BASE": ("BASE", "BASE"),
    "基礎": ("BASE", "BASE"),
    "TALENT": ("TALENT", "TALENT"),
    "素質": ("TALENT", "TALENT"),
    "RELATION": ("RELATION", None),
    "相性": ("RELATION", None),
    "CFLAG": ("CFLAG", ""),
    "フラグ": ("CFLAG", ""),
    "EQUIP": ("EQUIP", ""),
    "装着物": ("EQUIP", ""),
    "JUEL": ("JUEL", "PALAM"),
    "珠": ("JUEL", "PALAM"),
}
_CHARA_STR_KEYS = {"NAME": "name", "名前": "name", "CALLNAME": "callname", "呼び名": "callname",
                   "NICKNAME": "nickname", "あだ名": "nickname", "MASTERNAME": "mastername",
                   "主人の呼び方": "mastername"}

# 角色陣列預設長度：ConstantData.cs:168–173（整數 100、TALENT/CFLAG 1000、JUEL 200；CSTR 100），
# 之後被 VariableSize.csv 覆寫。
_CHARA_DEFAULT_LENGTH = {"TALENT": 1000, "CFLAG": 1000, "JUEL": 200, "CSTR": 100}


class CsvFormatError(ValueError):
    """CSV 內容無法依 era 格式解讀（致命錯誤）。"""


# --- 讀行與數值 --------------------------------------------------------------


def read_enabled_lines(path: Path) -> list[tuple[int, str]]:
    """`EraStreamReader.ReadEnabledLine` 的對應：回傳 `(行號, 行首空白略過後的內容)`。

    空行與只有空白的行略過；**`;` 不當註解**（引擎在這一層不處理註解）。
    空白只算半形空白與 tab（`emuera.config`「全角スペースをホワイトスペースに含める:NO」，
    `Sub/LexicalAnalyzer.cs@SkipWhiteSpace`:733–750）。
    """
    # UNVERIFIED: 原版 1.824 對無 BOM 檔以 Shift-JIS 解碼（EraStreamReader.cs:42 + Config.cs:17），
    # 本作有 7 個無 BOM 的 UTF-8 角色檔；這裡一律以 UTF-8 讀（可能是 +v10 差異，見 unresolved）。
    text = path.read_text(encoding="utf-8-sig")
    out: list[tuple[int, str]] = []
    # StreamReader.ReadLine 以 \r\n、\n、\r 分行
    for no, line in enumerate(re.split(r"\r\n|\n|\r", text), start=1):
        stripped = line.lstrip(" \t")
        if stripped == "":
            continue
        if stripped.startswith("{") or stripped.startswith("}"):
            raise CsvFormatError(f"{path}:{no}: 本作 CSV 不應出現行連結記號")
        out.append((no, stripped))
    return out


_DOTNET_WS = "\t\n\v\f\r "
_DOTNET_INT_RE = re.compile(rf"[{_DOTNET_WS}]*([+-]?[0-9]+)[{_DOTNET_WS}]*")


def dotnet_try_parse_int(text: str, bits: int = 64) -> int | None:
    """.NET `Int32/Int64.TryParse(s)`（NumberStyles.Integer）：前後空白與正負號可，其餘失敗。"""
    m = _DOTNET_INT_RE.fullmatch(text)
    if not m:
        return None
    value = int(m.group(1))
    limit = 1 << (bits - 1)
    return value if -limit <= value < limit else None


def emuera_try_to_int64(text: str) -> int | None:
    """`ConstantData.cs@tryToInt64`:1064：開頭（正負號後）須為 ASCII 數字，之後由
    `LexicalAnalyzer.ReadInt64` 讀到非數字為止（`100.` → 100、`1400 ` → 1400）。失敗回 None。"""
    if not text:
        return None
    i, sign = 0, 1
    if text[0] == "+":
        i = 1
    elif text[0] == "-":
        sign, i = -1, 1
    if i >= len(text) or text[i] not in "0123456789":
        return None
    try:
        value, _ = read_int64(text, i)
    except ValueError:
        return None
    return value * sign


def read_int64(s: str, i: int) -> tuple[int, int]:
    """`LexicalAnalyzer.ReadInt64(st, false)`:133–190 的移植（0x／0b 前綴、p/e 指數）。"""
    base = 10
    if s[i] == "0" and i + 1 < len(s) and s[i + 1] in "xXbB":
        base = 16 if s[i + 1] in "xX" else 2
        i += 2
    significand, i = _read_digits(s, i, base)
    exp_base = 0
    if i < len(s) and s[i] in "pP":
        exp_base = 2
    elif i < len(s) and s[i] in "eE":
        exp_base = 10
    if exp_base:
        exponent, i = _read_digits(s, i + 1, base)
        if exponent != 0:
            d = significand * float(exp_base) ** exponent
            if d != d or d in (float("inf"), float("-inf")) or not (-(2**63) <= d <= 2**63 - 1):
                raise ValueError("64 位元範圍外")
            significand = int(d)
    return significand, i


def _read_digits(s: str, i: int, base: int) -> tuple[int, int]:
    """`LexicalAnalyzer.readDigits`:192–250。10 進位用 char.IsDigit（含全形數字）。"""
    start = i
    if i < len(s) and s[i] in "+-":
        i += 1
    digits_start = i
    while i < len(s):
        c = s[i]
        if base == 10 and c.isdecimal():
            i += 1
        elif base == 16 and (c.isdecimal() or c in "abcdefABCDEF"):
            i += 1
        elif base == 2 and c.isdecimal():
            if c not in "01":
                raise ValueError("二進法表記の中で使用できない文字")
            i += 1
        else:
            break
    body = s[digits_start:i]
    if not body:
        return 0, i
    # C# 端以 Convert.ToInt64(…, base) 轉換；全形數字在 10 進位時 Python int() 可直接轉。
    value = int(s[start:i], base)
    return value, i


# --- 名稱表 ------------------------------------------------------------------


def _split_rows(path: Path) -> list[tuple[int, list[str]]]:
    return [(no, line.split(",")) for no, line in read_enabled_lines(path)]


def load_name_table(path: Path) -> dict[int, str]:
    """`loadDataTo`：`tokens[0]` 以 Int32.TryParse 讀番號，名稱 = `tokens[1]` 原樣（不 trim）。
    空名稱（`42,`）等於未定義，不收。"""
    table: dict[int, str] = {}
    for _, tokens in _split_rows(path):
        if len(tokens) < 2:
            continue
        index = dotnet_try_parse_int(tokens[0], 32)
        if index is None or index < 0:
            continue
        if tokens[1] == "":
            table.pop(index, None)
        else:
            table[index] = tokens[1]
    return table


@dataclass(frozen=True)
class ItemDef:
    no: int
    name: str
    price: int


def load_items(path: Path) -> dict[int, ItemDef]:
    """Item.csv：`番號,名稱,價格`；價格 = `Int64.TryParse(tokens[2].TrimEnd())`（ConstantData.cs:1330–1341）。"""
    items: dict[int, ItemDef] = {}
    for _, tokens in _split_rows(path):
        if len(tokens) < 2:
            continue
        no = dotnet_try_parse_int(tokens[0], 32)
        if no is None or no < 0 or tokens[1] == "":
            continue
        price = 0
        if len(tokens) >= 3:
            parsed = dotnet_try_parse_int(tokens[2].rstrip(), 64)
            price = parsed if parsed is not None else 0
        items[no] = ItemDef(no, tokens[1], price)
    return items


def load_str_defaults(path: Path) -> dict[int, str]:
    """Str.csv：STR 陣列的初期值（與名稱表同一個讀法）。"""
    return load_name_table(path)


def load_game_base(path: Path) -> dict[str, str]:
    """GameBase.csv：鍵 = `tokens[0]` 原樣、值 = `tokens[1]`（GameBase.cs:104–145）。"""
    out: dict[str, str] = {}
    for _, tokens in _split_rows(path):
        if len(tokens) >= 2:
            out[tokens[0]] = tokens[1]
    return out


def load_variable_size(path: Path) -> dict[str, tuple[int, ...]]:
    """VariableSize.csv：鍵 trim、長度 int.TryParse（ConstantData.cs:226–260）。"""
    out: dict[str, tuple[int, ...]] = {}
    for _, tokens in _split_rows(path):
        if len(tokens) < 2:
            continue
        key = tokens[0].strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue  # `;TCVAR` 等：變數名無法辨識 → 警告後略過
        dims = [dotnet_try_parse_int(t, 32) for t in tokens[1:3] if t.strip() != ""]
        if not dims or dims[0] is None:
            continue
        out[key.upper()] = tuple(d for d in dims if d is not None)
    return out


def load_replace(path: Path) -> dict[str, str]:
    """_Replace.csv：以 `,` 或 `:` 切鍵，鍵與值都 trim；值 trim 後為空的行略過（→ 保留預設值）。
    例：`BAR文字1, ` 不生效，BAR 字元維持預設 `*`（Config/ConfigData.cs:129、539–551）。"""
    out: dict[str, str] = {}
    for line in re.split(r"\r\n|\n|\r", path.read_text(encoding="utf-8-sig")):
        if line == "" or line[0] == ";":
            continue
        tokens = re.split(r"[,:]", line)
        if len(tokens) < 2:
            continue
        value = line[len(tokens[0]) + 1 :]
        if value.strip() == "":
            continue
        out[tokens[0].strip()] = value.strip()
    return out


# --- 角色 CSV ----------------------------------------------------------------


@dataclass
class CharaDef:
    """角色 CSV 定義的初期值（Emuera 的 CharacterTemplate）。陣列都是稀疏 dict：`{索引: 值}`。

    `base` 是 CSV「基礎」＝ CharacterTemplate.Maxbase；ADDCHARA 時同時寫入 BASE 與 MAXBASE。
    """

    no: int
    csv_no: int = 0  # 檔名 `CHARA` 後的數字（ConstantData.cs:1033–1045）
    name: str = ""
    callname: str = ""
    nickname: str = ""
    mastername: str = ""
    base: dict[int, int] = field(default_factory=dict)
    abl: dict[int, int] = field(default_factory=dict)
    talent: dict[int, int] = field(default_factory=dict)
    exp: dict[int, int] = field(default_factory=dict)
    mark: dict[int, int] = field(default_factory=dict)
    juel: dict[int, int] = field(default_factory=dict)
    cflag: dict[int, int] = field(default_factory=dict)
    equip: dict[int, int] = field(default_factory=dict)
    relation: dict[int, int] = field(default_factory=dict)
    cstr: dict[int, str] = field(default_factory=dict)
    source: Path | None = None
    # 引擎會發出警告並略過的行
    warnings: list[str] = field(default_factory=list)

    @property
    def maxbase(self) -> dict[int, int]:
        return dict(self.base)


def _chara_lengths(variable_size: dict[str, tuple[int, ...]]) -> dict[str, int]:
    lengths = {var: _CHARA_DEFAULT_LENGTH.get(var, 100) for var in
               ("BASE", "ABL", "TALENT", "EXP", "MARK", "JUEL", "CFLAG", "EQUIP", "RELATION", "CSTR")}
    for var in lengths:
        if var in variable_size:
            lengths[var] = variable_size[var][0]
    return lengths


def _reverse(tables: dict[str, dict[int, str]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for var, table in tables.items():
        rev: dict[str, int] = {}
        for no in sorted(table):
            rev.setdefault(table[no], no)
        out[var] = rev
    return out


def _chara_no_from_filename(name: str) -> int:
    upper = name.upper()
    rest = upper[upper.index("CHARA") + 5 :]
    m = re.match(r"\d+", rest)  # char.IsDigit
    return int(m.group(0)) if m else 0


def load_chara(
    path: Path,
    name_tables: dict[str, dict[int, str]],
    variable_size: dict[str, tuple[int, ...]] | None = None,
) -> CharaDef | None:
    """讀取單一角色 CSV（`loadCharacterDataFile`）。沒有 `番号` 行則回傳 None（引擎不建立角色）。"""
    reverse = _reverse(name_tables)
    lengths = _chara_lengths(variable_size or {})
    chara: CharaDef | None = None
    warnings: list[str] = []
    for lineno, tokens in _split_rows(path):
        where = f"{path.name}:{lineno}"
        if len(tokens) < 2:
            warnings.append(f"{where}: \",\"が必要です")
            continue
        if tokens[0] == "":
            warnings.append(f"{where}: \",\"で始まっています")
            continue
        if tokens[0] in ("NO", "番号"):
            if chara is not None:
                warnings.append(f"{where}: 番号が二重に定義されました")
                continue
            no = dotnet_try_parse_int(tokens[1].rstrip(), 64)
            if no is None:
                warnings.append(f"{where}: {tokens[1]}を整数値に変換できません")
                continue
            chara = CharaDef(no=no, csv_no=_chara_no_from_filename(path.name), source=path)
            continue
        if chara is None:
            warnings.append(f"{where}: 番号が定義される前に他のデータが始まりました")
            continue
        try:
            _apply_chara_tokens(chara, tokens, reverse, lengths, where, warnings)
        except CsvFormatError as exc:
            # 例外は loadCharacterDataFile の catch（:1048–1056）で捕まり、ファイルの残りは読まれない。
            # テンプレートは番号行の時点で登録済みなので、それまでの内容で残る。
            warnings.append(str(exc))
            break
    if chara is not None:
        chara.warnings = warnings
    return chara


def _apply_chara_tokens(
    chara: CharaDef,
    tokens: list[str],
    reverse: dict[str, dict[str, int]],
    lengths: dict[str, int],
    where: str,
    warnings: list[str],
) -> None:
    """`toCharacterTemplate`:1106–1289 的移植。"""
    key = tokens[0].upper()
    if key in _CHARA_STR_KEYS:
        setattr(chara, _CHARA_STR_KEYS[key], tokens[1])
        return
    if key == "CSTR":
        var, table = "CSTR", ""
    elif key in _CHARA_ARRAY_KEYS:
        var, table = _CHARA_ARRAY_KEYS[key]
    else:
        warnings.append(f"{where}: \"{tokens[0]}\"は解釈できない識別子です")
        return
    length = lengths[var]
    p1 = emuera_try_to_int64(tokens[1].rstrip())
    if p1 is not None:
        if p1 < 0 or p1 >= length:
            warnings.append(f"{where}: {p1}は配列の範囲外です")
            return
        index = p1
    elif table is not None:
        index = reverse.get(table, {}).get(tokens[1]) if table else None  # 名稱不 trim
        if index is None:
            warnings.append(f"{where}: \"{tokens[1]}\"の定義がありません")
            return
        if index >= length:
            warnings.append(f"{where}: \"{tokens[1]}\"は配列の範囲外です")
            return
    else:
        warnings.append(f"{where}: \"{tokens[1]}\"は解釈できない識別子です")
        return
    if var == "CSTR":
        if len(tokens) < 3:
            warnings.append(f"{where}: 三つ目の識別子がありません")
            # C# 端接著讀 tokens[2] 會丟 IndexOutOfRange → 被外層 catch，整個檔案讀取中止
            raise CsvFormatError(f"{where}: CSTR の値がありません（予期しないエラー）")
        chara.cstr[index] = tokens[2]
        return
    # 值省略或無法解析 → 1（:1276–1277）
    value = emuera_try_to_int64(tokens[2]) if len(tokens) >= 3 else None
    getattr(chara, var.lower())[index] = 1 if value is None else value


def find_chara_files(csv_dir: Path) -> list[Path]:
    """`Config.GetFiles(csvDir, "CHARA*.CSV")`（Config/Config.cs:330–379）：
    子資料夾優先（依名稱不分大小寫排序、遞迴），再列目前資料夾的檔案（同樣排序）。"""

    def walk(d: Path) -> list[Path]:
        out: list[Path] = []
        for sub in sorted((p for p in d.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            out.extend(walk(sub))
        files = [
            p for p in d.iterdir()
            if p.is_file() and p.name.lower().startswith("chara") and p.suffix.lower() == ".csv"
        ]
        out.extend(sorted(files, key=lambda p: p.name.lower()))
        return out

    return walk(csv_dir)


def load_charas(
    csv_dir: Path,
    name_tables: dict[str, dict[int, str]],
    variable_size: dict[str, tuple[int, ...]] | None = None,
) -> tuple[dict[int, CharaDef], list[str]]:
    """讀取全部角色 CSV → `({番号: CharaDef}, 全域警告)`。
    番号重複時保留先讀到的（ConstantData.cs:972–985，只發警告）。"""
    charas: dict[int, CharaDef] = {}
    warnings: list[str] = []
    for path in find_chara_files(csv_dir):
        chara = load_chara(path, name_tables, variable_size)
        if chara is None:
            continue
        if chara.no in charas:
            warnings.append(f"番号{chara.no}のキャラが複数回定義されています：{path}")
            continue
        charas[chara.no] = chara
    return charas, warnings


@dataclass
class GameData:
    """`CSV/` 全部內容的唯讀快照。"""

    names: dict[str, dict[int, str]]
    items: dict[int, ItemDef]
    str_defaults: dict[int, str]
    game_base: dict[str, str]
    variable_size: dict[str, tuple[int, ...]]
    replace: dict[str, str]
    charas: dict[int, CharaDef]
    warnings: list[str] = field(default_factory=list)

    _reverse_cache: dict[str, dict[str, int]] = field(default_factory=dict, repr=False, compare=False)

    def index_of(self, var: str, name: str) -> int:
        """名稱 → 番號，例如 `index_of("TALENT", "処女") == 0`（ERB 的 `TALENT:処女`）。"""
        if var not in self._reverse_cache:
            self._reverse_cache[var] = _reverse({var: self.names[var]})[var]
        try:
            return self._reverse_cache[var][name]
        except KeyError:
            raise KeyError(f"{var} 沒有名稱 {name!r}") from None

    def game_base_int(self, key: str, default: int = 0) -> int:
        value = dotnet_try_parse_int(self.game_base.get(key, ""), 64)
        return default if value is None else value


def load_game_data(csv_dir: Path) -> GameData:
    names = {var: load_name_table(csv_dir / fname) for var, fname in NAME_TABLE_FILES.items()}
    variable_size = load_variable_size(csv_dir / "VariableSize.csv")
    charas, warnings = load_charas(csv_dir, names, variable_size)
    return GameData(
        names=names,
        items=load_items(csv_dir / NAME_TABLE_FILES["ITEM"]),
        str_defaults=load_str_defaults(csv_dir / "Str.csv"),
        game_base=load_game_base(csv_dir / "GameBase.csv"),
        variable_size=variable_size,
        replace=load_replace(csv_dir / "_Replace.csv"),
        charas=charas,
        warnings=warnings,
    )
