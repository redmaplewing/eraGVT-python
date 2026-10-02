"""S25：ステータス画面（SHOW_STATUS_CHARA_SELECT と PAGE1〜5）、カラーバー、素質一覧、EXPORT_CSV。

expected は ERB 原文から（路徑相對 `source/earGVP/ERB/`）：
- `ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT.ERB`:26–155、`…_PAGE1.ERB`〜`…_PAGE5.ERB`
- `汎用関数/コモン関数.ERB@COLOR_BAR`:19–75・`@COLORSENTENCE_BAR`:79–111・`@COLORSENTENCE_BARCOLOR`:192–203
- `汎用関数/SETCOLOR_BY_STR.ERB`:10–73、`ヒロイン関連/TALENT_INFO.ERB`、`ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_TALENT`:251–953
- `武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB@SET_FSTYLE_INFO`:118–165、`SYSTEM/キャラメイキング関連/EXPORT_CSV.ERB`
- 呼出：`インターミッション画面/SHOP.ERB`:247–249、`ゲーム内_戦闘処理/BATTLE_COM.ERB`:626–628、`オープニング処理.ERB`:656–658
引擎：`<br>`（reference/emuera-1824/Emuera/GameView/HtmlManager.cs:672–676、PrintStringBuffer.cs:189–196／242–245）、
`<shape type='space'>`（ConsoleShapePart.cs:40–53）、行中コメント `;`（Sub/LexicalAnalyzer.cs:954–966）。
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game.action import Ctx
from eragvt.game.colorbar import color_bar, colorchip, colorsentence_bar, percent_cal
from eragvt.game.config import heroine_preset_gen
from eragvt.game.opening import event_first_gen
from eragvt.game.session import GameSession, Phase
from eragvt.game.status_screen import func_check_chara_incest, set_fstyle_info, show_status_chara_select
from eragvt.game.status_talent import show_status_talent, talent_info
from eragvt.state import GameRng, GameState
from eragvt.state.savefile import GlobalStore
from eragvt.text import NullNarrationService, TextOutput

Z = "　"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


def _session(data, preset=0, seed=0):
    """標題 [0] → 開局（0 = 汎用キャラおまかせ、1 = 初期セット）→ HEROINE_PRESET [1] → SHOP。"""
    s = GameSession(data, Path(tempfile.mkdtemp()), rng=GameRng(seed), narration=NullNarrationService())
    s.input(0)
    s.input(preset)
    s.input(1)
    assert s.phase == Phase.SHOP
    return s


def _texts(lines) -> list[str]:
    return [ln.text for ln in lines]


def _open(data, preset=0, arg=1):
    """SHOP 状態の GameState で画面ジェネレータを直接開く。"""
    s = _session(data, preset)
    out = TextOutput()
    ctx = Ctx(s.state, data, out, NullNarrationService())
    gen = show_status_chara_select(ctx, arg)
    next(gen)
    return s.state, out, ctx, gen


def _send(gen, *values):
    for v in values:
        gen.send(v)


def _last_page(out: TextOutput) -> list[str]:
    """最後の LB（空行 50）以降。"""
    lines = out.lines
    run = start = 0
    for i, ln in enumerate(lines):
        if ln.kind == "text" and ln.text == "":
            run += 1
            if run >= 50:
                start = i + 1
        else:
            run = 0
    return [ln.text for ln in lines[start:] if ln.kind != "drawline"]


# --- カラーバー（コモン関数.ERB）--------------------------------------------------------------


def test_percent_cal():
    assert [percent_cal(0, 5), percent_cal(5, 0), percent_cal(1, 3), percent_cal(150, 100)] == [0, 0, 33, 150]


def test_color_bar_gradient_and_background():
    """:22 LOCAL:1 = 5*10/10 = 5 マス；ARG:11 = 2 なので 2 マス同色→3 マス目で加算（:42–60）；背景は ARG:4〜6 + ARG:7 を
    0〜255 に収めた色（:24–38、:63–66）。最後に RESETCOLOR。"""
    out = TextOutput()
    out.set_color((1, 2, 3))
    color_bar(out, 5, 10, 10, 100, 100, 100, -160, 10, 20, 30, 2, "#", ".")
    out.printl()
    segs = out.lines[0].parts[0].segments if len(out.lines[0].parts) == 1 else [s for p in out.lines[0].parts for s in p.segments]
    text = "".join(s.text for s in segs)
    assert text == "#####....."
    colors = [s.color for s in segs for _ in s.text]
    assert colors[:5] == ["#646464", "#646464", "#6e7882", "#6e7882", "#6e7882"]
    assert colors[5:] == ["#000000"] * 5
    assert out.color is None


@pytest.mark.parametrize("cur, mx, color", [(0, 100, "#ff0000"), (20, 100, "#ff7b00"), (40, 100, "#ffff00"), (50, 100, None)])
def test_colorsentence_bar(cur, mx, color):
    """:84 `%ARGS,6,LEFT%　  `、:93 `₍`、20 マスの ▮、:97 `₎`、:98 `（{cur,5}/{max,5}）`。名前の色は BARCOLOR（:192–203）。"""
    out = TextOutput()
    colorsentence_bar(out, "体力", 6, cur, mx, 20)
    out.printl()
    ln = out.lines[0]
    assert ln.text == "体力  　  ₍" + "▮" * 20 + f"₎（{cur:>5}/{mx:>5}）"
    assert ln.parts[0].segments[0].color == color
    assert out.color is None


def test_colorchip():
    """:64–73：[ ] は呼び出し時の色、■ だけ SETCOLOR_BY_STR の色。名前に無く R//G//B でもなければ色を変えない（RETURN -1）。"""
    for name, col in (("赤", "#ff0808"), ("ブルネット", "#580808"), ("10//20//30", "#0a141e"), ("白", None)):
        out = TextOutput()
        colorchip(out, name)
        out.printl()
        segs = [s for p in out.lines[0].parts for s in p.segments]
        assert "".join(s.text for s in segs) == "[■]"
        sq = next(s for s in segs if "■" in s.text)
        assert sq.color == col
        assert out.color is None


# --- HTML_PRINT の拡張 -------------------------------------------------------------------------


def test_html_br_nobr_shape():
    out = TextOutput()
    out.html_print("A<br>B<br>")
    out.html_print("<br>")
    out.html_print("<nobr>C<shape type='space' param='150'>D</nobr>")
    assert _texts(out.lines) == ["A", "B", "", "C   D"]


# --- TALENT_INFO / SHOW_STATUS_TALENT -----------------------------------------------------------


def test_talent_info():
    assert talent_info(0) == "乙女の証。清純度が好評価になるが、失った場合は苦痛が伴う"  # :38–40
    assert talent_info(192) == "対応する部位への性的な接触を防ぐ結界"  # :216–218 CASE 190 TO 193
    assert talent_info(-10) == "出産に備えて入院中"
    assert talent_info(999) == "原作ありキャラの判定用"
    assert talent_info(1999) == ""  # 該当なし


def _ctx(data):
    st = GameState.new(data, rng=GameRng(0))
    st.add_chara(data, 0)
    out = TextOutput()
    return st, out, Ctx(st, data, out, NullNarrationService())


def _talent(data, c, name, v):
    c.talent[data.index_of("TALENT", name)] = v


def test_show_status_talent_category_mode(data):
    """FLAG:801 bit0 = 1：カテゴリ表示（:642–953）。基本は HTML_PRINT、各カテゴリは 6 個ごとに改行（:1143–1151）。"""
    st, out, ctx = _ctx(data)
    st.add_chara(data, 0)
    c = st.charas[1]
    st.flag[801] = 1
    _talent(data, c, "処女", 1)
    _talent(data, c, "巨乳", 3)
    _talent(data, c, "清純派", 1)
    c.cflag[0] = 1  # 幽閉
    show_status_talent(ctx, 1, 0, 1)
    t = _texts(out.lines)
    assert t[0] == "◆素質"
    assert t[1].startswith("　基本：[女][処女]") and t[1].endswith("[ランダム]")
    assert "　精神：[清純派]" in t
    assert "　肉体：[超乳]" in t
    assert "　状態：[幽閉中]" in t
    # title（説明）付き
    part = next(p for p in out.lines[t.index("　肉体：[超乳]")].parts if p.text == "[超乳]")
    assert part.title == talent_info(111)


def test_show_status_talent_list_mode(data):
    """FLAG:801 bit0 = 0：HTML で 1 行目「◆素質」、2 行目に状態タグと素質（:255–641）。"""
    st, out, ctx = _ctx(data)
    st.add_chara(data, 0)
    c = st.charas[1]
    st.flag[801] = 0
    c.cflag[0] = 4  # クズ監禁：HTML 版は [誘拐中]（:301）
    _talent(data, c, "貧乳", 2)
    _talent(data, c, "学生", 2)
    show_status_talent(ctx, 1, 0, 1)
    t = _texts(out.lines)
    assert t[0] == "◆素質"
    assert t[1] == "[誘拐中][絶壁]"
    assert t[2] == "   [中学生]"  # shape space 150 → 半角 3、800 番台の nonbutton 群
    assert t[3] == ""


def test_training_screen_shows_talents(data):
    """鍛錬画面 `SHOW_STATUS_BASE_TRAINING`:224 `CALL SHOW_STATUS_TALENT, TARGET, 1, 1`（S25 で接続）。"""
    from eragvt.game.action import show_status_base_training

    s = _session(data)
    st = s.state
    st.target = 1
    st.flag[801] = 1
    out = TextOutput()
    show_status_base_training(Ctx(st, data, out, NullNarrationService()), 1)
    t = _texts(out.lines)
    assert "素質" in t
    assert any(x.startswith("基本：[") for x in t)


# --- 画面のメインループ -------------------------------------------------------------------------


def test_navigation_and_return(data):
    st, out, ctx, gen = _open(data)
    p = _last_page(out)
    assert p[0] == Z * 17 + "基本ステータス情報" + Z * 14 + "PAGE(1/5)"
    assert " [1][前ページ]　　[1000]戦闘　[2000]素質　[3000]武器　[4000]相関　[5000]個人　　[2][次ページ]" in p
    # 現在ページのボタンだけ水色（DIRECTBTN:137–138）
    ln = next(x for x in out.lines[::-1] if "[1000]戦闘" in x.text)
    assert next(pt for pt in ln.parts if pt.text.startswith("[1000]")).segments[0].color == "#00ffff"
    assert next(pt for pt in ln.parts if pt.text.startswith("[2000]")).segments[0].color is None
    gen.send(1)  # 前ページ：1 → 5
    assert _last_page(out)[0].endswith("PAGE(5/5)")
    gen.send(2)  # 5 → 1
    assert _last_page(out)[0].endswith("PAGE(1/5)")
    gen.send(4000)
    assert _last_page(out)[0].endswith("PAGE(4/5)")
    gen.send(12345)  # どのページの固有コマンドでもない
    assert out.lines[-1].text == "正しい値を入力してください" or "正しい値を入力してください" in _texts(out.lines)
    with pytest.raises(StopIteration) as stop:
        gen.send(999)
    assert stop.value.value == 999


def test_chara_cycle(data):
    """[100]／[200]：0 と CHARANUM を飛ばして循環（:84–99）。戦闘中（FLAG:700）は「正しい値を入力してください」。"""
    st, out, ctx, gen = _open(data, arg=1)
    n = st.charanum
    gen.send(100)
    assert _last_page(out)[1].startswith(f"氏名　：{st.charas[n - 1].name}")
    gen.send(200)
    assert _last_page(out)[1].startswith(f"氏名　：{st.charas[1].name}")
    st.flag[700] = 1
    k = len(out.lines)
    gen.send(200)
    assert "正しい値を入力してください" in _texts(out.lines[k:])
    assert _last_page(out)[1].startswith(f"氏名　：{st.charas[1].name}")


def test_page1_kojo_cycle_and_subjective(data):
    """[0]：CFLAG:6 0→1→2→3（主観視点=1）→4（主観視点=0）→-2→NO→0（:154–171）。[10]：主観モード（:173–193）。"""
    st, out, ctx, gen = _open(data)
    c = st.charas[1]
    sub = data.index_of("TALENT", "主観視点")
    seq = []
    for _ in range(7):
        gen.send(0)
        seq.append((c.cflag[6], c.talent[sub]))
    assert [v for v, _ in seq[:5]] == [1, 2, 3, 4, -2]
    assert seq[2][1] == 1 and seq[3][1] == 0
    assert seq[5][0] == c.no and seq[6][0] == 0 if c.no != 0 else seq[5][0] == 0
    gen.send(10)
    assert "[1]使用する" in _texts(out.lines)
    gen.send(1)
    assert c.talent[sub] == 1
    assert out.lines[-1].text.startswith(" [999]") and any(ln.wait and ln.text == "地の文を変更しました" for ln in out.lines)


def test_page1_rename_and_battle_lock(data):
    """[11]：FIRSTSETTING_CHARA_CALLNAME（[0] で CSTR:200 を呼び名に）。戦闘中は RETURN 0（:197–198）。[12] は一人称設定画面で停止。"""
    st, out, ctx, gen = _open(data)
    c = st.charas[1]
    c.cstr[200] = "テスト名"
    gen.send(11)
    assert "[0]名前を呼び名に設定（名前：テスト名）" in _texts(out.lines)
    gen.send(0)
    assert c.callname == "テスト名"
    st.flag[700] = 1
    k = len(out.lines)
    gen.send(11)
    assert "正しい値を入力してください" in _texts(out.lines[k:])
    st.flag[700] = 0
    with pytest.raises(NotImplementedError, match="一人称設定画面"):
        gen.send(12)


def test_page1_noncombatant_quirk(data):
    """:100 `ELSEIF TALENT;ARG:…` は `;` 以降コメント → TALENT:TARGET:0（処女）で【非戦闘員】を出す（原作どおり）。"""
    st, out, ctx, gen = _open(data)
    c = st.charas[1]
    c.talent[data.index_of("TALENT", "変身能力")] = 0
    st.target = 1
    c.talent[0] = 1
    gen.send(1000)
    assert "【非戦闘員】" in _last_page(out)
    c.talent[0] = 0
    c.talent[data.index_of("TALENT", "変身能力")] = -1
    gen.send(1000)
    assert "【非戦闘員】" not in _last_page(out)


def test_page1_stats_shields(data):
    """戦闘力（:303–321：変身前は MAXBASE*CFLAG:10/100）、結界（:360–439）。"""
    st, out, ctx, gen = _open(data)
    c = st.charas[1]
    m = c.maxbase
    _talent(data, c, "Ｖ結界", 1)
    c.base[data.index_of("BASE", "Ｖ結界耐久力")] = 0
    c.maxbase[data.index_of("BASE", "Ｖ結界耐久力")] = 100
    _talent(data, c, "避妊結界", 1)
    gen.send(1000)
    p = _last_page(out)
    assert any(x.startswith(f"変身前{Z * 2}攻撃：{m[10] * c.cflag[10] // 100:>4}") for x in p)
    assert any(x.startswith(f"変身後{Z * 2}攻撃：{m[10]:>4}") for x in p)
    assert f"◆結界{Z * 2}Ｖ結界{Z * 3}崩{Z}壊{Z * 4} 0％{Z}" in p
    assert Z * 5 + "避妊結界" in p


def test_page2_get_color_by_rank_writes_result(data):
    """GET_COLOR_BY_RANK の `RETURN r, g, b` は共用 RESULT:0〜2（docs/wiki/python/result.md）。経験は最後の 魅了経験 = 0 → 灰色。"""
    st, out, ctx, gen = _open(data)
    st.flag[801] = 1
    gen.send(2000)
    assert [st.result[i] for i in range(3)] == [128, 128, 128]
    p = _last_page(out)
    assert "Ｃ感覚  ：Lv 0[>>>>>>>>>>]Ｖ感覚  ：Lv 0[>>>>>>>>>>]Ａ感覚  ：Lv 0[>>>>>>>>>>]Ｂ感覚  ：Lv 0[>>>>>>>>>>]" in p
    assert "　[0]キャラクターデータの書き出し　　" in p


def test_page2_abl_heart_bar(data):
    """ABL > 10 は ❤ 5 マス（ABL-9 / 10 × 5）＋ >> 背景（:113–114）、色は段階 4（255,94,255）。"""
    st, out, ctx, gen = _open(data)
    st.charas[1].abl[0] = 13
    gen.send(2000)
    p = _last_page(out)
    assert any(x.startswith("Ｃ感覚  ：Lv13[❤❤>>>>>>]") for x in p)


def test_page3_fstyle_results(data):
    """SET_FSTYLE_INFO は共用 RESULTS:0〜2 に書く（最後に表示した遠距離のスタイル）。"""
    st, out, ctx, gen = _open(data)
    style = data.index_of("CDFLAG2", "戦闘スタイル")
    st.charas[1].cdflag[(3, style)] = 10
    gen.send(3000)
    p = _last_page(out)
    assert any(x.startswith(f"└◎戦闘スタイル{Z}<<反撃>>") for x in p)
    assert st.results[0] == "威力影響度：攻撃*0.70 + 防御*0.50"
    assert st.results[2] == "BURST性能 ：戦闘中に反撃を成功させて蓄積したダメージを一撃に加える"
    set_fstyle_info(ctx, 1, 1)
    assert st.results[0] == "威力影響度：攻撃*1.00"
    with pytest.raises(NotImplementedError, match="WEAPON_CUSTOMIZE"):
        gen.send(0)


def test_page4_relations_parents(data):
    st, out, ctx, gen = _open(data)
    c1, c2 = st.charas[1], st.charas[2]
    c1.relation[1] = (1 << 1) | (1 << 3)  # 血統 Ｃ触手・Ａ触手
    c1.cflag[9] = 2  # ボス 2 の子
    c1.cflag[121] = 2
    gen.send(4000)
    p = _last_page(out)
    assert f"{Z}血統{Z}({Z}Ｃ触手{Z}Ａ触手{Z})" in p
    assert f"{Z}実父{Z}:{Z}Ｖ触手" in p
    assert Z * 6 + "警察上層部" in p
    c1.cflag[9] = 150  # TENTACLE_LASTBOSS_50 は無い → TRYCALLFORM 不発
    with pytest.raises(NotImplementedError):
        gen.send(4000)


def test_func_check_chara_incest(data):
    """:256–311：X が年上なら X にとって Y は子（父なら娘）。複数の関係は "/" で繋ぐ。"""
    st, out, ctx = _ctx(data)
    for _ in range(2):
        st.add_chara(data, 0)
    a, b = st.charas[1], st.charas[2]
    ra = data.index_of("BASE", "実年齢")
    a.base[ra], b.base[ra] = 40, 20
    a.relation[2] = (1 << 20) | (1 << 21)  # 親子・兄弟姉妹
    assert func_check_chara_incest(ctx, 1, 2, 1) == "娘/妹"
    assert func_check_chara_incest(ctx, 1, 2, 0) == "息子/弟"
    b.relation[1] = 1 << 23  # おじおば
    assert func_check_chara_incest(ctx, 2, 1, 1) == "おば"


def test_page5_profile_setting_sets_gaping(data):
    """初期セット（身体資料なし CFLAG:34 = 0）：「プロフィール未設定」と [20]　設定。[20] で GENERATE_BODYLINE〜CHARA_SIZE_DEFAULT
    （＋SIZE_SETTING は [99] 相当）→ CFLAG:34 > 0、再表示で PRINTFORM_GAPING_NOW が拡張度の初期値を設定（S11 裁決）。"""
    st, out, ctx, gen = _open(data, preset=1)
    c = st.charas[1]
    assert c.cflag[34] == 0
    gen.send(5000)
    p = _last_page(out)
    assert Z * 9 + "プロフィール未設定" in p
    assert Z * 21 + "[20]" + Z + "設定" in p
    assert c.cflag[35] == 0 and c.cflag[36] == 0
    gen.send(20)
    assert c.cflag[34] > 0
    p = _last_page(out)
    assert Z * 11 + "＜＜通常時＞＞" in p
    assert "　　拡張度" in p
    assert c.cflag[35] > 0 and c.cflag[36] > 0


def test_page5_transform_toggle(data):
    """[10]（変身能力 > 0）：INVERTBIT SHOW_TRANS_STATUS → ＜＜変身時＞＞、ボタンは「通常時」に。"""
    st, out, ctx, gen = _open(data)
    gen.send(5000)
    assert Z * 11 + "＜＜通常時＞＞" in _last_page(out)
    gen.send(10)
    p = _last_page(out)
    assert Z * 11 + "＜＜変身時＞＞" in p
    assert Z * 21 + "[10]" + Z + "通常時" in p


def test_export_csv(data):
    """PAGE2 [0]：TARGET = ARG → EXPORT_CSV。[1] 保存範囲の切替、[0] でログ全消去して CSV 書式を印字（:72–）。"""
    st, out, ctx, gen = _open(data, arg=2)
    gen.send(2000)
    gen.send(0)
    assert st.target == 2
    assert "[999] やめる" in _texts(out.lines)
    gen.send(1)
    assert _texts(out.lines)[-3].endswith("現在の設定：感度・経験のみ保存")
    gen.send(0)
    t = _texts(out.lines)
    assert t[0].startswith("番号,")
    assert t[1] == f"名前,{st.charas[2].name},"
    assert ";-------経験--------------------" in t
    assert ";生成終了" + "=" * 77 in t
    assert next(ln for ln in out.lines if ln.text.startswith(";生成終了")).wait  # :581 WAIT → 画面に戻って再描画


# --- 呼出元 ---------------------------------------------------------------------------------


def test_shop_110_integration(data):
    """SHOP [110]：TARGET = LIMIT(TARGET, 1, CHARANUM-1) → 画面 → [2] 次ページ → [999] → SHOP 再表示。"""
    s = _session(data)
    s.state.target = 0
    s.input(110)
    assert s.phase == Phase.TURN
    assert s.state.target == 1
    assert any(t.endswith("PAGE(1/5)") for t in _texts(s.screen()))
    s.input(2)
    assert any(t.endswith("PAGE(2/5)") for t in _texts(s.screen()))
    s.input(999)
    assert s.phase == Phase.SHOP


def test_heroine_preset_status(data):
    """HEROINE_PRESET [20]〜[29]：CALL SHOW_STATUS_CHARA_SELECT(RESULT-19) → GOTO INPUT_LOOP_CON_HEAD（:656–658）。"""
    st = GameState.new(data, rng=GameRng(3))
    out = TextOutput()
    gen = event_first_gen(st, data, out, GlobalStore())
    next(gen)
    gen.send(1)  # 初期セット → HEROINE_PRESET
    gen.send(21)
    assert any(t.endswith("PAGE(1/5)") for t in _texts(out.lines))
    gen.send(999)
    assert _texts(out.lines)[-1] == " "
    assert "◆ヒロインデータ確認" in _texts(out.lines)[-20:]
    with pytest.raises(NotImplementedError, match="存在しない"):
        gen.send(29)


def test_battle_800_opens_status(data):
    """戦闘中 [800]：DRAWLINE → SHOW_STATUS_CHARA_SELECT, TARGET（BATTLE_COM.ERB:626–628）。[100] は灰色、[999] で戦闘に戻る。"""
    s = _session(data, preset=1, seed=1)
    policy = random.Random(1)
    found = False
    for _ in range(3000):
        if s.phase == Phase.SHOP:
            for i in range(1, s.state.charanum):
                s.input(i)
                s.input(103)
            s.input(100)
            continue
        buttons = [v for ln in s.screen()[-40:] for (_, v) in ln.buttons]
        if s.state.flag[700] and 800 in buttons:
            found = True
            break
        s.input(policy.choice([b for b in buttons if b != 800]) if buttons else 0)
    assert found
    s.input(800)
    t = _texts(s.screen())
    assert any(x.endswith("PAGE(1/5)") for x in t)
    ln = next(x for x in s.screen() if "[100]前のキャラ" in x.text)
    assert next(p for p in ln.parts if p.text.startswith("[100]")).segments[0].color == "#808080"
    s.input(999)
    assert s.phase == Phase.TURN and s.state.flag[700] == 1
