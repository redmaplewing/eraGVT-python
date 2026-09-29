"""原作 `CSV/` 的載入器。

格式依據見 `docs/wiki/era/csv.md`。本模組只負責「讀出原始定義」，
不做任何遊戲邏輯（初期化、MAXBASE 以外的衍生值等留給 S02 的狀態模型）。
"""

from __future__ import annotations

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

# 角色 CSV 第一欄 → 變數名。日文關鍵字與英文別名都接受。
_CHARA_ARRAY_KEYS: dict[str, str] = {
    "基礎": "BASE",
    "BASE": "BASE",
    "能力": "ABL",
    "ABL": "ABL",
    "素質": "TALENT",
    "TALENT": "TALENT",
    "経験": "EXP",
    "EXP": "EXP",
    "刻印": "MARK",
    "MARK": "MARK",
    "珠": "JUEL",
    "JUEL": "JUEL",
    "フラグ": "CFLAG",
    "CFLAG": "CFLAG",
    "装着物": "EQUIP",
    "EQUIP": "EQUIP",
    "相性": "RELATION",
    "RELATION": "RELATION",
}

# 角色 CSV 的索引若寫成名稱，要查哪一張名稱表。
_INDEX_NAME_TABLE: dict[str, str] = {
    "BASE": "BASE",
    "ABL": "ABL",
    "TALENT": "TALENT",
    "EXP": "EXP",
    "MARK": "MARK",
    "JUEL": "JUEL",
}


class CsvFormatError(ValueError):
    """CSV 內容無法依 era 格式解讀。"""


def read_csv_rows(path: Path) -> list[list[str]]:
    """讀取 era CSV，回傳去除註解與空白後的欄位列表。

    - UTF-8，有無 BOM 皆可；CRLF／LF 皆可。
    - `;` 之後整段視為註解（本作 CSV 的 `;` 只出現在註解）。
    - 每欄去除前後空白；行尾多出的空欄丟掉；全空行略過。
    """
    text = path.read_text(encoding="utf-8-sig")
    rows: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        fields = [f.strip() for f in line.split(",")]
        while fields and fields[-1] == "":
            fields.pop()
        if fields:
            rows.append(fields)
    return rows


def _parse_int(text: str, path: Path, what: str) -> int:
    # 原作 Chara299.CSV 有 `フラグ,40,100.` 這種尾端句點的筆誤，當整數讀
    # （Emuera 實際行為未驗證，見 docs/wiki/bridge/unresolved.md）。
    if text.endswith(".") and text[:-1].lstrip("-").isdigit():
        text = text[:-1]
    try:
        return int(text)
    except ValueError:
        raise CsvFormatError(f"{path}: {what} 不是整數：{text!r}") from None


def load_name_table(path: Path) -> dict[int, str]:
    """讀取 `番號,名稱[,…]` 形式的名稱表 → `{番號: 名稱}`。"""
    table: dict[int, str] = {}
    for fields in read_csv_rows(path):
        if len(fields) < 2:
            continue  # 例：Base.csv 的 `42,`（保留號碼，無名稱）
        table[_parse_int(fields[0], path, "番號")] = fields[1]
    return table


@dataclass(frozen=True)
class ItemDef:
    no: int
    name: str
    price: int


def load_items(path: Path) -> dict[int, ItemDef]:
    """讀取 Item.csv（`番號,名稱,價格`）。"""
    items: dict[int, ItemDef] = {}
    for fields in read_csv_rows(path):
        if len(fields) < 2:
            continue
        no = _parse_int(fields[0], path, "番號")
        price = _parse_int(fields[2], path, "價格") if len(fields) >= 3 else 0
        items[no] = ItemDef(no, fields[1], price)
    return items


def load_str_defaults(path: Path) -> dict[int, str]:
    """讀取 Str.csv：STR 陣列的初期值（不是名稱表）。"""
    return load_name_table(path)


def load_key_values(path: Path) -> dict[str, list[str]]:
    """讀取 `鍵,值[,值…]` 形式（GameBase.csv／VariableSize.csv／_Replace.csv）。"""
    return {fields[0]: fields[1:] for fields in read_csv_rows(path)}


@dataclass
class CharaDef:
    """角色 CSV 定義的初期值。陣列都是稀疏 dict：`{索引: 值}`。"""

    no: int
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
    # 無法解讀而略過的行（原作有範本用佔位符 `xx` 等）。
    warnings: list[str] = field(default_factory=list)

    @property
    def maxbase(self) -> dict[int, int]:
        """era 規則：CSV 的「基礎」同時設定 BASE 與 MAXBASE。"""
        return dict(self.base)


def _resolve_index(
    text: str,
    var: str,
    reverse: dict[str, dict[str, int]],
    path: Path,
) -> int:
    try:
        return int(text)
    except ValueError:
        pass
    table_key = _INDEX_NAME_TABLE.get(var)
    if table_key is not None and text in reverse.get(table_key, {}):
        return reverse[table_key][text]
    raise CsvFormatError(f"{path}: {var} 的索引名稱找不到：{text!r}")


def _reverse(tables: dict[str, dict[int, str]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for var, table in tables.items():
        rev: dict[str, int] = {}
        for no, name in table.items():
            rev.setdefault(name, no)  # 同名時取先出現者
        out[var] = rev
    return out


def _apply_chara_row(
    chara: CharaDef,
    fields: list[str],
    reverse: dict[str, dict[str, int]],
    path: Path,
    no: int | None,
) -> int | None:
    """套用一行角色 CSV；回傳（可能更新後的）番号。"""
    key = fields[0]
    text = fields[1] if len(fields) > 1 else ""
    if key == "番号":
        return _parse_int(text, path, "番号")
    if key == "名前":
        chara.name = text
    elif key == "呼び名":
        chara.callname = text
    elif key == "あだ名":
        chara.nickname = text
    elif key == "主人の呼び方":
        chara.mastername = text
    elif key == "CSTR":
        idx = _parse_int(text, path, "CSTR 索引")
        chara.cstr[idx] = fields[2] if len(fields) > 2 else ""
    elif key in _CHARA_ARRAY_KEYS:
        var = _CHARA_ARRAY_KEYS[key]
        idx = _resolve_index(text, var, reverse, path)
        # 省略值時視為 1（素質常見寫法 `素質,処女`）。
        value = _parse_int(fields[2], path, f"{key} 值") if len(fields) > 2 else 1
        getattr(chara, var.lower())[idx] = value
    else:
        raise CsvFormatError(f"{path}: 未知的角色 CSV 欄位：{key!r}")
    return no


def load_chara(path: Path, name_tables: dict[str, dict[int, str]]) -> CharaDef:
    """讀取單一角色 CSV。`name_tables` 用來把名稱索引（如 `素質,処女`）轉成番號。"""
    reverse = _reverse(name_tables)
    no: int | None = None
    chara = CharaDef(no=-1, source=path)
    for fields in read_csv_rows(path):
        try:
            no = _apply_chara_row(chara, fields, reverse, path, no)
        except CsvFormatError as exc:
            chara.warnings.append(str(exc))
    if no is None:
        raise CsvFormatError(f"{path}: 缺少 番号")
    chara.no = no
    return chara


def find_chara_files(csv_dir: Path) -> list[Path]:
    """遞迴找 `Chara*.csv`（不分大小寫），依路徑排序。

    Emuera 設定「サブディレクトリを検索する:YES」＋「読み込み順をファイル名順にソートする:YES」。
    """
    files = [
        p
        for p in csv_dir.rglob("*")
        if p.is_file() and p.suffix.lower() == ".csv" and p.name.lower().startswith("chara")
    ]
    return sorted(files, key=lambda p: str(p.relative_to(csv_dir)).lower())


def load_charas(csv_dir: Path, name_tables: dict[str, dict[int, str]]) -> dict[int, CharaDef]:
    """讀取全部角色 CSV → `{番号: CharaDef}`。番号重複時報錯。"""
    charas: dict[int, CharaDef] = {}
    for path in find_chara_files(csv_dir):
        chara = load_chara(path, name_tables)
        if chara.no in charas:
            other = charas[chara.no].source
            raise CsvFormatError(f"番号 {chara.no} 重複：{other} 與 {path}")
        charas[chara.no] = chara
    return charas


@dataclass
class GameData:
    """`CSV/` 全部內容的唯讀快照。"""

    names: dict[str, dict[int, str]]
    items: dict[int, ItemDef]
    str_defaults: dict[int, str]
    game_base: dict[str, list[str]]
    variable_size: dict[str, list[str]]
    replace: dict[str, list[str]]
    charas: dict[int, CharaDef]

    def index_of(self, var: str, name: str) -> int:
        """名稱 → 番號，例如 `index_of("TALENT", "処女") == 0`。"""
        for no, n in self.names[var].items():
            if n == name:
                return no
        raise KeyError(f"{var} 沒有名稱 {name!r}")


def load_game_data(csv_dir: Path) -> GameData:
    names = {var: load_name_table(csv_dir / fname) for var, fname in NAME_TABLE_FILES.items()}
    return GameData(
        names=names,
        items=load_items(csv_dir / NAME_TABLE_FILES["ITEM"]),
        str_defaults=load_str_defaults(csv_dir / "Str.csv"),
        game_base=load_key_values(csv_dir / "GameBase.csv"),
        variable_size=load_key_values(csv_dir / "VariableSize.csv"),
        replace=load_key_values(csv_dir / "_Replace.csv"),
        charas=load_charas(csv_dir, names),
    )
