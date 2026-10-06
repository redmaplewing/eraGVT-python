"""S50：expected 由引擎詞法與色彩 ERB 推導，未由 Python 輸出反推。

引擎：reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2357–2387、2540–2569；
reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:133–263。
.NET Framework 4 的 Convert／Encoding／double 邊界另以 tmp/s50/probe.cs 實測。
"""
import pytest

from eragvt.game.chara_make import toint
from eragvt.game.colorbar import isnumeric, setcolor_by_str, colorchip
from eragvt.text import TextOutput


@pytest.mark.parametrize("text,valid,expected", [
    ("", False, 0), ("0", True, 0), ("0012", True, 12),
    ("+12", True, 12), ("-12", True, -12), (" 12", False, 0),
    ("12 ", False, 0), ("12\t", False, 0), ("12\n", False, 0),
    ("+", False, 0), ("--1", False, 0), ("+ 1", False, 0),
    ("12.", True, 12), ("-12.99", True, -12), (".5", False, 0),
    ("1.2.3", False, 0), ("1.2e3", False, 0), ("1e2.99", True, 100),
    ("0xFF", True, 255), ("0XfF", True, 255), ("0b101", True, 5),
    ("0B101", True, 5), ("0x+10", True, 16), ("0b+10", True, 2),
    ("+0x10", False, 0), ("-0b10", False, 0), ("0x", True, 0),
    ("0b", True, 0), ("0x.5", True, 0), ("0b.5", True, 0),
    ("0xG", False, 0), ("0bA", False, 0), ("0x1.25", True, 1),
    ("0x1.2A", False, 0), ("1e2", True, 100), ("1E+2", True, 100),
    ("19e-1", True, 1), ("-19e-1", True, -1), ("3p3", True, 24),
    ("3P-1", True, 1), ("0x1e2", True, 482), ("0x1p10", True, 65536),
    ("0b1e10", True, 100), ("0b1p10", True, 4),
    ("1e4294967296", True, 1), ("1p2147483648", True, 0),
    ("1p-2147483648", True, 0), ("1p4294967297", True, 2),
    ("9223372036854775807", True, 9223372036854775807),
    ("-9223372036854775808", True, -9223372036854775808),
    ("0xFFFFFFFFFFFFFFFF", True, -1), ("0x8000000000000000", True, -9223372036854775808),
    ("0b" + "1" * 64, True, -1), ("1p63", True, -9223372036854775808),
    ("-1p63", True, -9223372036854775808),
    ("9223372036854775807p0", True, 9223372036854775807),
    ("9223372036854775807p-1", True, 4611686018427387904),
    ("１２", False, 0), ("1e２", False, 0), ("1字", False, 0),
    ("💫", False, 0), ("1💫", False, 0), ("𝟙", False, 0),
    ("1.١٢", True, 1), ("²", False, 0), ("0x+«", False, 0),
    ("0x+ゔ", False, 0), ("0" * 5000 + "12", True, 12),
])
def test_numeric_formats(text, valid, expected):
    # ReadInt64:141–162 僅字串起首辨識前綴；:178 指數以同進位讀取後轉 Int32。
    # :184–187 先用 double 乘算，再依 .NET Framework unchecked 轉回 Int64。
    assert isnumeric(text) is valid
    assert toint(text) == expected


@pytest.mark.parametrize("text,error", [
    ("1e", ValueError), ("1p+", ValueError), ("0x+", ValueError),
    ("0b+", ValueError), ("0x-1", ValueError), ("0b-1", ValueError),
    ("0b2", ValueError), ("0b102", ValueError), ("0b1p2", ValueError),
    ("0x1p-1", ValueError), ("١٢", ValueError), ("0x١", ValueError),
    ("1e−", ValueError), ("0x+〜", ValueError),
    ("9223372036854775808", OverflowError), ("-9223372036854775809", OverflowError),
    ("0x10000000000000000", OverflowError), ("0b" + "1" * 65, OverflowError),
    ("1e9223372036854775808", OverflowError), ("1p64", OverflowError),
    ("0p2147483647", OverflowError), ("1e2147483647", OverflowError),
    ("9223372036854775808x", OverflowError),
])
def test_numeric_errors_are_not_invalid_zero(text, error):
    # ReadInt64:185–186、readDigits:234–261：錯誤先於後綴有效性判斷，不得改成 0。
    for convert in (isnumeric, toint):
        with pytest.raises(error):
            convert(text)


@pytest.mark.parametrize("text,expected", [
    ("0xFF//0b10000000//25e1", (255, 128, 250)),
    ("0x//0b//1p7", (0, 0, 128)),
    ("255.9//+2//19e-1", (255, 2, 1)),
])
def test_color_code(text, expected):
    # ERB/汎用関数/SETCOLOR_BY_STR.ERB@SETCOLOR_BY_STR:48–55。
    out = TextOutput()
    assert setcolor_by_str(out, text) == 0
    assert out.color == "#" + "".join(f"{v:02x}" for v in expected)
    colorchip(out, text)
    assert out.color == "#" + "".join(f"{v:02x}" for v in expected)


@pytest.mark.parametrize("text,error", [
    ("0x100//0//0", ValueError), ("-1//0//0", ValueError),
    ("1e//0//0", ValueError), ("1p64//0//0", OverflowError),
])
def test_color_errors(text, error):
    # Process.ScriptProc.cs:381–406：SETCOLOR 範圍 0–255，並非自動裁切。
    out = TextOutput()
    out.set_color((1, 2, 3))
    with pytest.raises(error):
        setcolor_by_str(out, text)
    assert out.color == "#010203"


@pytest.mark.parametrize("text", ["1//2", "1//2//3//4", "+0xFF//0//0", "1 //2//3", "abc//1e//0"])
def test_invalid_color_preserves_color_and_short_circuits(text):
    out = TextOutput()
    out.set_color((1, 2, 3))
    assert setcolor_by_str(out, text) == -1
    assert out.color == "#010203"


@pytest.fixture(scope="module")
def data():
    from eragvt.data import default_csv_dir, load_game_data
    return load_game_data(default_csv_dir())


@pytest.mark.parametrize("texts,expected", [
    (("0x20", "0b10010", "2e1"), (32, 18, 20)),
    (("0x", "0", "1p-1"), (-99, 0, -99)),
    (("年齢に合わせる", "0x12", "実年齢に合わせる"), (18, 18, 18)),
    (("1💫", "+0x10", "💫"), (-99, -99, -99)),
])
def test_age_designations_share_numeric_rules(data, texts, expected):
    from eragvt.game.body import chara_make_age_setting
    from eragvt.state import GameState, FixedRng

    # ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING:1408–1444。
    # 只有字串 "0" 指定零歲；其餘非正值走 RANDOM_AGE_F，未知字串 = -99。
    state = GameState.new(data, rng=FixedRng([5]))
    state.add_chara(data, 0)
    chara = state.charas[-1]
    chara.cstr[204], chara.cstr[205], chara.cstr[206] = texts
    state.result[0], state.results[0] = 123, "殘值"
    chara_make_age_setting(state, data, chara)
    assert (chara.base[40], chara.base[41], chara.maxbase[41]) == expected
    assert (state.result[0], state.results[0]) == (123, "殘值")


def test_saved_color_codes_reach_web_status_page(data, tmp_path):
    from fastapi.testclient import TestClient
    from eragvt.web import create_app

    # 現有 P5 顯示入口，並無新增手動色彩選單。
    # ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE5.ERB@SHOW_STATUS_CHARA_APPERANCE:194–195。
    app = create_app(data, tmp_path, narration=None)
    client = TestClient(app)

    def send(value):
        response = client.post("/api/input", json={"value": value})
        assert response.status_code == 200
        return response.json()

    for value in (0,1, 1000, 1,0, 1):
        send(value)
    chara = app.state.session.state.charas[1]
    code = "0xFF//0b10000000//25e1"
    chara.cstr[30] = code
    for value in (200, 0):
        send(value)
    chara.cstr[30] = "赤"
    for value in (300, 0):
        send(value)
    assert app.state.session.state.charas[1].cstr[30] == code
    for value in (110, 5000):
        result = send(value)
    assert result["phase"] != "halted"
    segments = [segment for line in result["lines"] for part in line.get("parts", []) for segment in part.get("segments", [])]
    assert any(segment["text"] == "■" and segment.get("color") == "#ff80fa" for segment in segments)
    assert "#ff80fa" in client.get("/").text
