"""S14：動画流出（`ゲーム内_イベント発生/戦闘イベント.ERB@DOUGA_RYUSUTU`）と動画サイト表示
（`地の文/MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window`、`汎用関数/WindowDrawer.ERB`、
`汎用関数/TagSetText.ERB`）、catalog の GOTO／INPUTS。

expected は ERB 原文から逐行推導（路徑相對 `source/earGVP/ERB/`、行號は註解）、引擎語意は
`reference/emuera-1824/Emuera/` の行號。実装の出力から逆算しない。
"""

from __future__ import annotations

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import shop, turnend
from eragvt.game.action import Ctx, print_transcallname
from eragvt.game.battle.after import douga_ryusutu
from eragvt.game.battle.sexmsg import msg_spcom7
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.narration import nodes as N
from eragvt.narration import windowlib as W
from eragvt.narration.extract import ExtractContext, parse_function, read_logical_lines
from eragvt.narration.runtime import Env, ErbRuntimeError, Interp, NeedInput, NotSupported
from eragvt.narration.runtime_support import unsupported_reasons_static
from eragvt.narration.service import CatalogNarrationService
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = default_csv_dir().parent / "ERB"
# 汎用関数/PRINT_LINE.ERB@SHORTLINE:4 の PRINT 文字列（:5–6 ARG == 0 で改行）
SHORTLINE = (ERB / "汎用関数/PRINT_LINE.ERB").read_text(encoding="utf-8-sig").splitlines()[3][len("PRINT ") :]


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture(scope="module")
def svc(data):
    return CatalogNarrationService(ERB, data)


def _state(data, seed: int = 1) -> GameState:
    s = GameState.new(data, rng=GameRng(seed))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())  # DAY=1, TIME=0, TARGET=1
    return s


@pytest.fixture
def ctx(data):
    return Ctx(_state(data), data, TextOutput(), NullNarrationService())


def texts(out: TextOutput) -> list[str]:
    return [ln.text for ln in out.lines]


def _set_exp(ctx, name: str, v: int) -> None:
    ctx.state.charas[1].exp[ctx.data.index_of("EXP", name)] = v


def _set_talent(ctx, name: str, v: int) -> None:
    ctx.state.charas[1].talent[ctx.data.index_of("TALENT", name)] = v


# --- DOUGA_RYUSUTU:1338–1478 ------------------------------------------------------------------------
# TFLAG:21 bit：1 動画配信・2 愛撫・4 口・8 挿入・16 膣内射精・32 アナル射精・64 ぶっかけ・128 嬲りもの・256 絶頂
# （●開発者向け資料/●GVTフラグ一覧.txt:480–490）

_HEAD = ["", "どうやら撮影された動画がネットに放流されたようだ。", ""]  # :1344–1346
_FACE = {  # :1444–1462 の各分岐（2 行目が無いものは 1 行）
    "luck": ["幸運なことに顔はしっかりと映っていないが、", "どんなところから身元を特定されてしまうか分かったものではない。"],
    "mosaic": ["不幸中の幸いと言うべきか、顔にはモザイクが掛かっていたが、", "見る人が見れば容易に身元を特定されてしまうだろう。"],
    "blur": ["顔の映りは不鮮明だが、見る人が見れば容易に身元を特定されてしまうだろう。"],
    "clear": ["顔がはっきり映されてしまっており、ネット上で身元を特定されるのも時間の問題だろう。"],
}
# RAND:4 == 0 → luck／RAND:3 == 0 → mosaic／RAND:2 == 0 → blur／else → clear（ELSEIF の RAND は評価順どおり）
_ROLLS = {"luck": [0], "mosaic": [1, 0], "blur": [1, 1, 0], "clear": [1, 1, 1]}
_MOSAIC_LINE = "股間にモザイクも掛けられておらず、結合部が丸見えになっている。"  # :1442–1443（bit 8）


@pytest.mark.parametrize(
    "tflag21, body, face, charm, cflag285",
    [
        # 1 のみ：:1435–1437「あわや…際どい」
        (1, ["あわや犯されそうになっている際どい映像が映し出されていた。"], "luck", 0, 0),
        # 3（1|2）：:1357 TFLAG:21 == 3 →「喘いでいる」／mosaic は魅了経験 >= 150 で +1（:1450–1451）
        (3, ["全身を愛撫されて快楽に喘いでいる映像が映し出されていた。"], "mosaic", 150, 1),
        (3, ["全身を愛撫されて快楽に喘いでいる映像が映し出されていた。"], "mosaic", 149, 0),
        # 31（1|2|4|8|16）：:1385–1386 PRINTL 、→ :1396–1398「挿入までされ」:1401「て」:1406 膣内射精 :1413「ている」
        (
            31,
            ["全身を愛撫されて快楽に喘ぎながら口で奉仕させられ、", "挿入までされて膣内射精を受け止めている映像が映し出されていた。"],
            "blur",
            0,
            1,
        ),
        # 69（1|4|64）：:1365「た上に」:1372 ぶっかけ :1380–1381「ている」／clear +2、魅了経験 +1（:1459–1461）
        (69, ["口で奉仕させられた上に精液をぶっかけられている映像が映し出されていた。"], "clear", 150, 3),
        # 387（1|2|128|256）：:1386–1388「、」「それだけでなく」、:1419–1420「させられた挙句に」、:1428–1432 玩具・「、」
        (
            387,
            [
                "全身を愛撫されて快楽に喘ぎながら、",
                "それだけでなく絶頂させられた挙句に玩具のように嬲られて、",
                "拷問でボロボロになっていく映像が映し出されていた。",
            ],
            "luck",
            0,
            0,
        ),
        # 397（1|4|8|128|256）：:1393–1394 ボロボロに犯され、:1410–1411「、」、:1421–1424「させられている」
        (
            397,
            ["口で奉仕させられた上に、", "ボロボロに犯され、", "絶頂させられている映像が映し出されていた。"],
            "clear",
            0,
            2,
        ),
        # 13（1|4|8）：:1365 の第 2 条件（愛撫なし・挿入あり）が先に真 → :1367 の TFLAG:21 == 13 分岐には来ない
        (13, ["口で奉仕させられた上に、", "挿入までされている映像が映し出されていた。"], "luck", 0, 0),
        # 97（1|32|64）：:1373 65／113 ではない、:1379–1381 は bit 32 で「ている」なし、挿入なしで 32 は表示されない
        (97, ["精液をぶっかけられ映像が映し出されていた。"], "luck", 0, 0),
    ],
)
def test_douga_ryusutu_leak(ctx, tflag21, body, face, charm, cflag285):
    st = ctx.state
    st.tflag[21] = tflag21
    _set_exp(ctx, "魅了経験", charm)
    st.rng = FixedRng(_ROLLS[face])
    douga_ryusutu(ctx, 0)
    name = print_transcallname(st, st.target)
    head = [SHORTLINE, *_HEAD, f"そこには{name}が触手に捕まり、"]  # :1343–1353（ENEMY_TYPE_CHECK_F("AKUOTI") == 0）
    expected = head + body + [""] + ([_MOSAIC_LINE] if tflag21 & 8 else []) + _FACE[face]
    expected += ["動画が削除されるまでの間、再生数は伸び続けた・・・", ""]  # :1463 PRINTFORML、:1464 PRINTW（空行で待つ）
    assert texts(ctx.out) == expected
    assert ctx.out.lines[-1].wait
    assert st.charas[1].cflag[285] == cflag285
    assert st.charas[1].cflag[284] == 0


def test_douga_ryusutu_akuoti(ctx):
    st = ctx.state
    st.tflag[21] = 1
    st.flag[110] = 1  # ENEMY_TYPE_CHECK_F("AKUOTI")：FLAG:110 > 0（コモン関数.ERB:1356–1371）
    st.rng = FixedRng([0])
    douga_ryusutu(ctx, 0)
    assert f"そこには{print_transcallname(st, st.target)}が悪の手先に捕まり、" in texts(ctx.out)  # :1350–1351


@pytest.mark.parametrize("tflag21", [0, 2, 510])
def test_douga_ryusutu_nothing_without_filming(ctx, tflag21):
    st = ctx.state
    st.tflag[21] = tflag21
    st.rng = FixedRng([])  # RAND を引かない
    douga_ryusutu(ctx, 0)
    assert texts(ctx.out) == []


@pytest.mark.parametrize(
    "tflag21, shukan, line",
    [
        (0, 0, "初めから約束を守る気など無かったのか、すぐにレイプ動画をネット上にアップロードした。"),  # :1472
        # :1342 は ARG == 0 が必要 → bit 0 があっても :1465 ELSEIF ARG == 1 へ
        (
            1,
            1,
            "初めから約束を守る気など無かったのか、あの後すぐにレイプの一部始終を捉えた動画をネット上にアップロードしたようだ。",
        ),  # :1469–1470 TALENT:主観視点
    ],
)
def test_douga_ryusutu_rape_video(ctx, tflag21, shukan, line):
    st = ctx.state
    st.tflag[21] = tflag21
    _set_talent(ctx, "主観視点", shukan)
    st.charas[1].cflag[284] = 2
    st.rng = FixedRng([3])
    douga_ryusutu(ctx, 1)
    name = print_transcallname(st, st.target)
    assert texts(ctx.out) == [
        SHORTLINE,
        "",
        "男たちは襲われたことを他言しなければ動画を公開しないと言っていたが、",
        line,
        f"後になって{name}が気付いた時には既に遅く、",
        "動画が多数の人間の目に触れてしまった後だった・・・",
        "",  # :1476 PRINTW
    ]
    assert st.charas[1].cflag[284] == 2 + 4 + 3  # :1477 CFLAG:284 += 4 + RAND:5
    assert st.charas[1].cflag[285] == 0


# --- CFLAG:284／285 の後続（SHOP_TURNEND.ERB）---------------------------------------------------------


class _ConstRng(GameRng):
    def __init__(self, v: int) -> None:
        super().__init__(0)
        self.v = v

    def rand(self, n: int) -> int:
        if n <= 0:
            raise ValueError(n)
        return min(self.v, n - 1)


@pytest.mark.parametrize(
    "cflag284, roll, fan",
    [
        (40, 9, 1),  # :543 RAND:100 < MIN(40 / 4, 10) = 10
        (40, 10, 0),
        (8, 1, 1),  # MIN(8 / 4, 10) = 2
        (8, 2, 0),
        (3, 0, 0),  # 3 / 4 = 0 → 常に偽
    ],
)
def test_popularity_fan_from_leak(ctx, cflag284, roll, fan):
    """`DAILY_POPULARITY_CHANGE`:529–562 のファン人気、CFLAG:284 の判定（:543–544）。
    RAND 順：一般評価 2（:497–505）、処女 3 人（:510–527）、ファン各キャラ（特装戦隊は該当素質なし → :543 のみ）、悪いうわさ 3。"""
    st = ctx.state
    st.charas[1].cflag[284] = cflag284
    st.rng = FixedRng([99, 99, 99, 99, 99, roll, 99, 99, 99, 99, 99])
    turnend.daily_popularity_change(ctx)
    assert st.flag[853] == fan
    assert any(("ファン人気( 1 )" in t) for t in texts(ctx.out)) == bool(fan)


@pytest.mark.parametrize(
    "talent, charm, v, before, after",
    [
        # :751–752 社交的：RAND:100 < 4 + SQRT(魅了経験)
        ("社交的", 9216, 99, 0, 1),  # 4 + 96 = 100 > 99
        ("社交的", 9025, 99, 0, 0),  # 4 + 95 = 99
        # :753–754 小心者：RAND:100 < 8 && CFLAG:285 > 0 で -1
        ("小心者", 0, 7, 2, 1),
        ("小心者", 0, 8, 2, 2),
        ("小心者", 0, 0, 0, 0),
    ],
)
def test_recovery_stalker_flag(ctx, talent, charm, v, before, after):
    st = ctx.state
    c = st.charas[1]
    for n in ("社交的", "小心者"):
        _set_talent(ctx, n, 0)
    _set_talent(ctx, talent, 1)
    _set_exp(ctx, "魅了経験", charm)
    c.cflag[285] = before
    st.rng = _ConstRng(v)
    turnend.recovery_over_time(ctx)
    assert c.cflag[285] == after


# --- windowlib（TagSetText.ERB／WindowDrawer.ERB）--------------------------------------------------


@pytest.mark.parametrize(
    "text, size, expected",
    [
        ("abc", 5, ["abc  "]),  # :264–266 残りを半角空白で埋める
        # 全角は 2 桁（STRLENS＝Shift-JIS バイト数）：「う」は入らず次の行へ（:232–256）
        ("あいう", 5, ["あい ", "う   "]),
        # タグは幅に数えず、折り返しでは閉じタグ → 次の行の先頭で開きタグ（:251–256）
        ("@B:1@abcdef@/B@", 4, ["@B:1@abcd@/B@", "@B:1@ef@/B@  "]),
        ("xyz", 1, []),  # :219–220 nShapeSize <= 1
    ],
)
def test_shape_tagset_text(text, size, expected):
    assert W.shape_tagset_text(text, size) == expected


@pytest.mark.parametrize(
    "text, size, mode, pad, expected",
    [
        ("abcdef", 3, 0, 1, ["abc", "def"]),
        ("あいう", 3, 0, 1, ["あ ", "いう"]),  # mode 0：途中の全角は後半へ、前半を空白埋め（:125–131、:152–155）
        ("あいう", 3, 1, 0, ["あい", " う"]),  # mode 1：前半へ、後半の先頭に空白 1（:133–139、:141–143、:159）
        ("", 5, 0, 1, ["     "]),
        ("x", 0, 0, 1, ["", "x"]),  # :99–104
    ],
)
def test_cut_tagset_text(text, size, mode, pad, expected):
    assert W.cut_tagset_text(text, size, mode, pad) == expected


def test_print_tagset_text_buttons():
    out = TextOutput()
    W.print_tagset_text(out, "@B:0@[ 0] 自己紹介@/B@　@B:99@[99] 再生終了@/B@", 0x01)
    ln = out.lines[-1]
    assert ln.text == "[ 0] 自己紹介　[99] 再生終了"
    assert ln.buttons == [("[ 0] 自己紹介", 0), ("[99] 再生終了", 99)]  # PRINTBUTTON（:409–410）


def test_window_border_and_overlap():
    """@WINDOW_MGR "CREATE":358–370（枠：┏━┓ の ━ は (幅 - 4) / 2 個）、@WINDOW_DISPLAY_EX（後に生成したものが上）。"""
    wm = W.WindowManager()
    wm.create(0, 0, 0, 8, 3, 1)
    wm.settext(0, 0, "ab")
    wm.create(1, 4, 1, 4, 1, 0)
    wm.settext(1, 0, "XY")
    out = TextOutput()
    wm.display_ex(out, list(range(10)))
    pad = lambda s, n: s + " " * (84 - n)  # noqa: E731  最後に 84 桁へ成形（:54、:120–123）
    # 1 行目：ウィンドウ 0 の「┃ab  ┃」の 4 桁目以降をウィンドウ 1 の「XY  」が覆う（CUT_TAGSET_TEXT 前半＋本体＋後半）
    assert texts(out) == [pad("┏━━┓", 8), pad("┃abXY", 6), pad("┗━━┛", 8)]


# --- catalog：GOTO／INPUTS（S14 擴充）----------------------------------------------------------------


class _Cat:
    """合成した関数だけを持つ最小の catalog。"""

    def __init__(self, src: str, real) -> None:
        self.user_vars = real.user_vars
        lines = read_logical_lines(src.encode("utf-8"))
        self.fd = parse_function(ExtractContext({}, {}, lambda n: False), "t.ERB", lines)

    def get(self, name):
        return self.fd if name.upper() == self.fd.name else None

    def exists(self, name):
        return name.upper() == self.fd.name

    def unsupported_reason(self, name):
        return None


def _run(ctx, cat, inputs=None):
    it = Interp(cat, Env(ctx.state, ctx.data, ctx.out, {}, {}, ctx, inputs))
    it.call(cat.fd.name, [])
    return it


def test_goto_top_level_label(ctx, svc):
    src = "@F\nLOCAL = 0\n$LOOP\nLOCAL += 1\nPRINTFORML {LOCAL}\nIF LOCAL < 3\n\tGOTO loop\nENDIF\nPRINTL end\n"
    cat = _Cat(src, svc.catalog)
    assert cat.fd.unsupported == []
    assert unsupported_reasons_static(cat.fd, cat) == []
    _run(ctx, cat)
    assert texts(ctx.out) == ["1", "2", "3", "end"]  # ラベル名は ToUpper（LogicalLineParser.cs:305–307、Instraction.Child.cs:2390–2391）


def test_goto_nested_label_is_unsupported(svc):
    # S28c2 から IF／SELECTCASE の中のラベルは対応（runtime.Interp._exec_body）。ループの中は不可のまま
    cat = _Cat("@F\nFOR LOCAL, 0, 1\n$L\nNEXT\nGOTO L\n", svc.catalog)
    assert any("GOTO 先" in why for _, why in unsupported_reasons_static(cat.fd, cat))


def test_inputs_in_interp(ctx, svc):
    cat = _Cat("@F\nINPUTS\nPRINTFORML [%RESULTS%]\n", svc.catalog)
    assert isinstance(cat.fd.body[0], N.Input)
    with pytest.raises(NotSupported):
        _run(ctx, cat)  # 通常の呼び出し（inputs=None）
    with pytest.raises(NeedInput):
        _run(ctx, cat, [])
    _run(ctx, cat, ["ab"])
    assert texts(ctx.out)[-1] == "[ab]"  # RESULTS = 入力（Process.cs@InputString:257–260）


def test_drawlineform_empty_is_error(ctx, svc):
    cat = _Cat('@F\n#DIMS S\nDRAWLINEFORM %S%\n', svc.catalog)
    with pytest.raises(ErbRuntimeError):
        _run(ctx, cat)  # EmueraConsole.Print.cs@printCustomBar:526–531


# --- MESSAGE_SEX_SPCOM7:1229–1293 ＋ 動画サイト（catalog）----------------------------------------------


@pytest.fixture
def cctx(data, svc):
    """特装戦隊 TARGET=1 紅葉、ボス 1（Ｃ触手）、撮影なし（FLAG:70／71 = 0）→ SPCOM7 の ELSE 分岐。"""
    s = _state(data)
    s.savestr[13] = "BOSS"
    s.flag[110] = 0
    s.flag[11] = 1
    s.flag[70] = s.flag[71] = 0
    s.charas[1].cflag[34] = 1
    s.rng = FixedRng([5] * 5000)
    return Ctx(s, data, TextOutput(), svc)


def test_spcom7_catalog_needs_input(svc):
    assert svc.catalog.needs_input("MESSAGE_SEX_SPCOM7")
    assert svc.catalog.unsupported_reason("MESSAGE_SEX_VIDEO_SITE_WINDOW") is None


def test_spcom7_skip_video(cctx):
    gen = msg_spcom7(cctx)
    next(gen)  # :1237 INPUTS
    assert texts(cctx.out)[-1] == "[1]映像を見る"
    with pytest.raises(StopIteration):
        gen.send(0)
    t = texts(cctx.out)
    assert "[1]映像を見る" not in t  # :1238 CLEARLINE LINECOUNT - LCOUNT
    assert "それは紅葉もよく知る動画配信サイトにアップされた" in t  # :1281


def test_spcom7_video_site(cctx):
    st = cctx.state
    gen = msg_spcom7(cctx)
    next(gen)
    gen.send(1)  # :1242 RESULTS == "1" → :1260 CALL MESSAGE_SEX_VIDEO_SITE_Window → :1343 INPUTS
    t = texts(cctx.out)
    assert "それは、動画にコメントを付けられる機能のある視聴者参加型のサイトだった。" in t  # :1243
    # 画面：:1335 DRAWLINEFORM の後、ウィンドウ 5（コマンド、:1253–1259、y=0）の 0 行目がボタン（PRINT_TAGSET_TEXT）
    first = next(i for i, ln in enumerate(cctx.out.lines) if ln.buttons)
    assert cctx.out.lines[first - 1].kind == "drawline"
    assert cctx.out.lines[first].buttons == [("[ 0] 自己紹介", 0), ("[ 1] 恋愛経験", 1)]
    assert cctx.out.lines[first + 4].buttons == [("[99] 再生終了", 99)]
    # ウィンドウ 1（メニュー、x=1 y=5 幅 80 枠あり）：内側 76 桁 = 72 バイト＋空白 4
    assert t[first + 6] == " ┃ファイル（Ｆ）｜編集（Ｖ）｜お気に入り（Ａ）｜ツール（Ｔ）｜ヘルプ（Ｈ）    ┃   "
    # ウィンドウ 3（x=5 y=28）：再生数 = RAND(2,30) = 2 + 5 % 28 = 7（:24）、抜いた！ = 0（:25）
    assert t[first + 28].startswith(" ┃  再生数：7 ")
    assert t[first + 29].startswith(" ┃  抜いた！：0 ")
    gen.send(0)  # :1352–1372 自己紹介：再生数 += RAND(100000) = 5、抜いた！ += RAND(50000) = 5
    t = texts(cctx.out)
    first = next(i for i, ln in enumerate(cctx.out.lines) if ln.buttons)
    assert first == 1  # :1469 CLEARLINE LINECOUNT で全消去 → :1335 DRAWLINEFORM から描き直し
    assert t[first + 28].startswith(" ┃  再生数：12 ")
    assert t[first + 29].startswith(" ┃  抜いた！：5 ")
    # ウィンドウ 7（x=3 y=12 枠あり）の 3 行目（:136）：特装戦隊は身體資料 0
    assert t[first + 16].startswith(" ┃┃身長は0.0cmで、体重が0.0kgです。")
    assert t[first + 17].startswith(" ┃┃スリーサイズはナ・イ・ショです♪")  # :141
    with pytest.raises(StopIteration):
        gen.send(99)  # :1462–1466 RETURN
    t = texts(cctx.out)
    k = t.index("事細かに晒された紅葉の恥辱のプロフィールが終わり、")  # :1273
    assert t[k + 1 : k + 6] == [
        "今度は紅葉の受けた陵辱のダイジェストが流れ出した。",  # :1274
        "",  # :1275 PRINTL
        "",  # :1276 PRINTW
        "大音量で再生される嬌声、飛び交うコメント、驚異的な速さで増加する「抜いた！」カウンタ",  # :1277
        "その一つ一つが紅葉の羞恥を煽り続けた・・・",  # :1278
    ]
    assert st.charas[1].cflag[284] == 0 and st.charas[1].cflag[285] == 0  # 動画サイトは状態を変えない


def test_spcom7_video_site_invalid_input_advances(cctx):
    """:1346–1347 0〜4・99 以外は strInputResult = nCountMovies（直前に見た番号 + 1。最初は "0"）。"""
    gen = msg_spcom7(cctx)
    next(gen)
    gen.send(1)
    gen.send(7)  # nCountMovies = "0" → 自己紹介
    t = texts(cctx.out)
    assert any(x.startswith(" ┃┃身長は0.0cmで") for x in t)
    gen.send(7)  # nCountMovies = "1" → 恋愛経験（:1373–1393）
    assert not any(x.startswith(" ┃┃身長は0.0cmで") for x in texts(cctx.out))


def test_spcom7_video_site_replay_is_deterministic(data, svc):
    """INPUTS ごとに開始時へ戻して再実行しても、同じ入力列なら同じ出力・同じ亂數状態（service.run_function_gen）。"""

    def play(inputs):
        s = _state(data, seed=5)
        s.savestr[13] = "BOSS"
        s.flag[110] = 0
        s.flag[11] = 1
        s.charas[1].cflag[34] = 1
        c = Ctx(s, data, TextOutput(), svc)
        gen = msg_spcom7(c)
        next(gen)
        try:
            for v in inputs:
                gen.send(v)
        except StopIteration:
            pass
        return texts(c.out), s.rng.rand(1000000)

    a = play([1, 2, 4, 99])
    b = play([1, 2, 4, 99])
    assert a == b
