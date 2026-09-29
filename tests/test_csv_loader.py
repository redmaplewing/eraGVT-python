"""CSV 載入器測試。

expected 值全部直接從 `source/earGVP/CSV/` 原文手抄（行號附在註解），不從載入器輸出反推。
解析規則的 expected 由 Emuera 1.824 原始碼推導（`reference/emuera-1824/Emuera/...`，行號附在註解）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.data.csv_loader import (
    dotnet_try_parse_int,
    emuera_try_to_int64,
    load_chara,
    load_charas,
    load_replace,
    read_enabled_lines,
)

CSV_DIR = default_csv_dir()


@pytest.fixture(scope="module")
def data():
    return load_game_data(CSV_DIR)


# --- 通用解析規則（合成輸入） ------------------------------------------


def test_read_enabled_lines_keeps_semicolons(tmp_path: Path):
    # EraStreamReader.cs@ReadEnabledLine:62–95：空行・空白行を飛ばし、行頭空白を除く。`;` は処理しない。
    p = tmp_path / "x.csv"
    p.write_bytes("\ufeff0,Ｃ感覚,\r\n\r\n  \t\r\n;註解行\r\n\t50,レベル,;コメント\n".encode("utf-8"))
    assert read_enabled_lines(p) == [(1, "0,Ｃ感覚,"), (4, ";註解行"), (5, "50,レベル,;コメント")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1400", 1400),
        ("100.;私服", 100),  # ReadInt64 は数字以外で止まる（LexicalAnalyzer.cs:192–216）
        ("-1", -1),
        ("+5", 5),
        (";処女", None),  # 先頭が数字でない → 失敗（ConstantData.cs:1082–1098）
        ("xx", None),
        (" 5", None),  # 空白始まりも失敗
        ("0x10", 16),
        ("1e3", 1000),
        ("", None),
    ],
)
def test_emuera_try_to_int64(text, expected):
    assert emuera_try_to_int64(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [(" 42 ", 42), ("-3", -3), ("4x", None), ("", None), ("2147483648", None)],
)
def test_dotnet_int32_parse(text, expected):
    assert dotnet_try_parse_int(text, 32) == expected


# --- 名稱表 ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("var", "index", "name"),
    [
        ("ABL", 0, "Ｃ感覚"),  # Abl.csv:1
        ("ABL", 50, "レベル"),  # Abl.csv:24
        ("BASE", 22, "空中ダッシュ"),  # Base.csv:13
        ("BASE", 50, "体力基礎"),  # Base.csv:30
        ("TALENT", 0, "処女"),  # Talent.csv:2
        ("TALENT", 200, "変身能力"),  # Talent.csv:85
        ("TALENT", 999, "固有キャラ"),  # Talent.csv:230
        ("TALENT", 1218, "エアマスター"),  # Talent.csv:264
        ("EXP", 20, "Ｖ経験"),  # Exp.csv:14
        ("MARK", 0, "快楽刻印"),
        ("PALAM", 10, "潤滑"),
        ("JUEL", 20, "修練P"),  # Juel.csv:15
        ("EX", 99, "行動ポイント"),  # Ex.csv（最終行無換行）
        ("TRAIN", 0, "変身する"),  # Train.csv:2
        ("TRAIN", 101, "フェラ攻撃"),  # Train.csv:40
        ("CDFLAG1", 1, "近距離"),
        ("CDFLAG2", 0, "武器ＩＤ"),
    ],
)
def test_name_tables(data, var, index, name):
    assert data.names[var][index] == name


def test_base_reserved_index_without_name_is_absent(data):
    # Base.csv 的 `42,` 沒有名稱
    assert 42 not in data.names["BASE"]


def test_index_of(data):
    assert data.index_of("TALENT", "固有キャラ") == 999
    assert data.index_of("ABL", "レベル") == 50


def test_items_have_price(data):
    item = data.items[101]  # Item.csv:3 `101,セーラー服,2000,`
    assert (item.name, item.price) == ("セーラー服", 2000)
    assert data.items[100].price == 0  # `100,私服,0,`


def test_str_defaults(data):
    assert data.str_defaults[2500] == "触手"  # Str.csv `2500,触手,;総称`
    assert data.str_defaults[2501] == "ザコ触手"


def test_key_value_files(data):
    assert data.game_base["最初からいるキャラ"] == "999"
    assert data.game_base_int("バージョン") == 408
    assert data.game_base_int("コード") == 891216222
    assert data.variable_size["CDFLAG"] == (100, 1000)
    assert data.variable_size["TALENT"] == (1300,)
    assert data.variable_size["STR"] == (32000,)  # `STR, 32000`
    assert "TCVAR" not in data.variable_size  # `;TCVAR, 300` は変数名として認識できない


def test_replace_csv_trim_and_empty(data):
    # ConfigData.cs@LoadReplaceFile:539–551：キーと値を Trim、値が空白だけの行は無視（既定値のまま）
    assert data.replace == {"販売アイテム数": "0", "DRAWLINE文字": "─"}


def test_replace_csv_colon_separator(tmp_path: Path):
    p = tmp_path / "_Replace.csv"
    p.write_text(";comment\nBAR文字1:#\n販売アイテム数 , 12 \n", encoding="utf-8")
    assert load_replace(p) == {"BAR文字1": "#", "販売アイテム数": "12"}


# --- 角色 CSV -------------------------------------------------------------


def test_all_charas_loaded(data):
    # CSV/ 下遞迴共 77 個 Chara*.csv（含 _ADD/、Chara3000 AssaultLily/、大寫 CHARA*）
    assert len(data.charas) == 77
    for no in (0, 1, 121, 160, 301, 998, 999, 1805, 3083):
        assert no in data.charas


@pytest.mark.parametrize(
    ("no", "name", "callname"),
    [
        (301, "赤羽 紅葉", "紅葉"),
        (999, "ダミー", "ダミー"),
        (160, "錦木千束", "千束"),  # _ADD/，無 BOM、CRLF
        (1805, "島村 卯月", "卯月"),  # CHARA 大寫檔名，LF
        (3080, "船田 純", "純"),  # 資料夾名含空白
    ],
)
def test_chara_names(data, no, name, callname):
    c = data.charas[no]
    assert (c.no, c.name, c.callname) == (no, name, callname)


# Chara/Chara300~400_Shokiset/Chara301赤羽 紅葉.csv
@pytest.mark.parametrize(
    ("attr", "index", "value"),
    [
        ("base", 0, 1400),  # 基礎,0,1400,;体力
        ("base", 13, 100),  # 基礎,13,100,;知性
        ("base", 22, 2),  # 基礎,22,2,;空中ダッシュ
        ("talent", 0, 1),  # 素質,0,;処女（省略值 = 1）
        ("talent", 200, 1),  # 素質,200,;変身能力あり
        ("talent", 999, 1),  # 素質,固有キャラ,1,（名稱索引）
        ("exp", 40, 5),  # 経験,40,5,;自慰経験
        ("cflag", 10, 25),
        ("cflag", 11, 120),
        ("cflag", 42, 300),
        ("cstr", 10, "赤羽"),
        ("cstr", 30, "橙"),
        ("cstr", 15, "ツラヌキ・ロッド(近)// //通常"),
    ],
)
def test_chara_301_fields(data, attr, index, value):
    assert getattr(data.charas[301], attr)[index] == value


def test_chara_301_maxbase_equals_base(data):
    assert data.charas[301].maxbase[0] == 1400


def test_chara_301_has_no_other_talents(data):
    # 素質 0,12,114,104,116,180,200,201,固有キャラ(999) の 9 個
    assert sorted(data.charas[301].talent) == [0, 12, 104, 114, 116, 180, 200, 201, 999]


# _ADD/Chara160錦木千束.csv：索引以名稱書寫
@pytest.mark.parametrize(
    ("attr", "index", "value"),
    [
        ("base", 0, 1100),  # 基礎,体力,1100
        ("base", 2, 70),  # 基礎,性耐性,70
        ("base", 10, 155),  # 基礎,攻撃,155
        ("abl", 50, 1),  # 能力,レベル,1
        ("cstr", 204, "17"),
        ("cstr", 205, "実年齢に合わせる"),
    ],
)
def test_chara_160_name_indexed(data, attr, index, value):
    assert getattr(data.charas[160], attr)[index] == value


def test_relation_large_bitset(data):
    # Chara361_髙橋舞.csv:127 `相性,362,2199023255552,;左鬼は従者`（bit 41 = 従者）
    assert data.charas[361].relation[362] == 2199023255552
    assert data.charas[361].relation[365] == 1073741828  # :130


def test_exp_by_name(data):
    # Chara365_アンネリース シュミット.csv:59 `経験,Ｖ経験,10`
    assert data.charas[365].exp[20] == 10


def test_juel(data):
    # Chara000汎用キャラ(女性).CSV:14 `珠,20,200,;修練Ｐ`
    assert data.charas[0].juel[20] == 200


def test_trailing_period_integer(data):
    # Chara299.CSV:17 `フラグ,40,100.;私服`（原作筆誤）
    assert data.charas[299].cflag[40] == 100
    assert data.charas[299].cflag[42] == 300


def test_unparsable_value_becomes_1(data):
    # ConstantData.cs:1276–1277：値が省略または解釈不能なら 1
    c = data.charas[998]  # Chara998_AA表示.CSV
    assert c.base[40] == 1  # `基礎,40,xx,;実年齢`
    assert c.base[41] == 1  # `基礎,41,xx,;見た目年齢`
    assert c.talent[200] == 1  # `素質,200,変身能力`
    assert c.base[0] == 1000  # `基礎,0,1000,;体力`


def test_cstr_value_is_not_trimmed_nor_comment_stripped(data):
    # tokens[2] をそのまま代入（ConstantData.cs:1266–1271）
    assert data.charas[998].cstr[9] == "バリアジャケットD;変身時アウターの表示名"
    # Chara1505茜島 蘭牙.csv `CSTR,40, 負けず嫌い` → 先頭の空白も残る
    assert data.charas[1505].cstr[40] == " 負けず嫌い"


def test_comment_lines_warn_but_do_not_change_data(tmp_path: Path, data):
    p = tmp_path / "Chara9.csv"
    p.write_text(";前置き\n番号,9\n;素質,0,処女\n素質,処女,2\n", encoding="utf-8")
    c = load_chara(p, data.names)
    assert c.talent == {0: 2}
    assert len(c.warnings) == 2  # 番号より前のデータ／解釈できない識別子


def test_duplicate_chara_number_keeps_first(tmp_path: Path, data):
    # ConstantData.cs:972–985：警告のみ、先に読んだテンプレートを使う。サブフォルダが先（Config.cs:349–358）
    (tmp_path / "Chara1.csv").write_text("番号,5\n名前,A\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "Chara2.csv").write_text("番号,5\n名前,B\n", encoding="utf-8")
    charas, warnings = load_charas(tmp_path, data.names)
    assert charas[5].name == "B"
    assert len(warnings) == 1


def test_unknown_name_index_is_warning(tmp_path: Path, data):
    p = tmp_path / "Chara9.csv"
    p.write_text("番号,9\n素質,存在しない素質\n素質,処女,2\n素質, 処女,3\n", encoding="utf-8")
    c = load_chara(p, data.names)
    assert c.talent == {0: 2}  # 名前は Trim しない（:1219）→ ` 処女` は未定義
    assert len(c.warnings) == 2


def test_juel_name_index_uses_palam_table(tmp_path: Path, data):
    # 珠 の名前索引は palam.csv（ConstantData.cs:1186–1191）
    p = tmp_path / "Chara9.csv"
    p.write_text("番号,9\n珠,修練P,50\n", encoding="utf-8")
    assert load_chara(p, data.names).juel == {20: 50}


def test_csv_no_from_filename(data):
    # ConstantData.cs:1033–1045：ファイル名 CHARA の直後の数字
    assert data.charas[999].csv_no == 999
    assert data.charas[0].csv_no == 0  # Chara000汎用キャラ(女性).CSV
