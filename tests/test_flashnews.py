"""FLASHNEWS（S26）。expected は `source/earGVP/ERB/インターミッション画面/SHOP_FLASHNEWS.ERB` から推導（行番号は註解）。

FixedRng の値は ERB の RAND 呼出順（短絡評価込み）に並べる。STRDATA は `RAND:(DATA 数)` を 1 回（コメント行は数えない）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from eragvt.data import default_csv_dir, load_game_data
from eragvt.game import flashnews as fn
from eragvt.game import shop
from eragvt.game.opening import PRESET_TOKUSOU, event_first
from eragvt.state import FixedRng, GameRng, GameState
from eragvt.text import NullNarrationService, TextOutput

ERB = Path(__file__).resolve().parents[1] / "source/earGVP/ERB/インターミッション画面/SHOP_FLASHNEWS.ERB"


@pytest.fixture(scope="module")
def data():
    return load_game_data(default_csv_dir())


@pytest.fixture
def st(data):
    s = GameState.new(data, rng=GameRng(1))
    event_first(s, data, preset=PRESET_TOKUSOU)
    shop.event_shop(s, data, TextOutput(), NullNarrationService())
    # 既定：どの優先ニュースにも当たらない状態（DAY 21 夜・防衛 6000・人気 0・ボス 7 体生存・経験 0）
    s.savestr[20] = ""
    s.flag[60] = 0
    s.day[0], s.time = 21, 1
    s.flag[852], s.flag[853] = 6000, 0
    for c in s.charas:
        for name in ("被姦経験", "戦闘経験", "ボス経験", "ラスボス経験", "魅了経験"):
            c.exp[data.index_of("EXP", name)] = 0
        c.abl[data.index_of("ABL", "露出癖")] = 0
    return s


def _run(st, data, rng):
    st.rng = FixedRng(rng)
    out = TextOutput()
    fn.flashnews(st, data, out)
    assert st.rng._values == []  # 乱数の消費数も ERB どおり
    return [ln.text for ln in out.lines]


def _erb_lines():
    return ERB.read_text(encoding="utf-8-sig").splitlines()


# --- 文字列表と原文の照合 ---------------------------------------------------------------------------------

_REP = [("%CALLNAME:(LOCAL:2)%", "{c}"), ("%NAME:(LOCAL:2)%", "{n}"), ("%LOCALS:2%", "{s2}"), ("%LOCALS:3%", "{s3}"),
        ("%LOCALS%", "{s}"), ("%SAVESTR:(RESULT:1)%", "{v}"), ("%ITEMNAME:399%", "{item}"),
        ('%CONFIG_CHECK_MANIAC_F(14) && RAND:4 ? "四肢切断され肉壁と一体化" # "子宮に触手幼体が多数寄生"%', "{x}")]


def test_tables_match_erb():
    lines = _erb_lines()
    blocks = {}
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("STRDATA"):
            start, items = i + 1, []
            i += 1
            while lines[i].strip() != "ENDDATA":
                t = lines[i].lstrip(" \t")
                if t.startswith("DATAFORM "):  # 命令の後の 1 文字（半角空白）の次から（LogicalLineParser.cs:429–438）
                    body = t[len("DATAFORM "):]
                    for a, b in _REP:
                        body = body.replace(a, b)
                    items.append((i + 1, body))
                i += 1
            blocks[start] = tuple(items)
        i += 1
    assert fn._STRDATA == blocks
    assert len(blocks) == 42
    for no, text in fn._TEXT.items():
        assert re.fullmatch(r"\s*LOCALS = (.*)", lines[no - 1]).group(1) == text, no


# --- 抽選済み・固定ニュース -------------------------------------------------------------------------------


def test_already_drawn(st, data):
    # :27–31 SAVESTR:20 があれば《》付きで再表示、FLAG:60 = 0、乱数なし
    st.savestr[20] = "既出"
    st.flag[60] = 110002
    assert _run(st, data, []) == ["FLASH NEWS：《既出》"]
    assert st.flag[60] == 0


@pytest.mark.parametrize(("day", "line"), [(1, 193), (3, 191), (6, 189), (15, 187), (63, 171)])
def test_day_fixed_news(st, data, day, line):
    # :168–203 昼（TIME 0）の日付固定ニュース：乱数なし、SAVESTR:20 に保存
    st.day[0], st.time = day, 0
    text = _erb_lines()[line - 1].strip()[len("LOCALS = "):]
    assert _run(st, data, []) == [f"FLASH NEWS：《{text}》"]
    assert st.savestr[20] == text and st.flag[60] == 0


def test_day_fixed_news_only_daytime(st, data):
    # 夜は :168 に入らない → 通常の抽選（:318 露出 RAND → :432 RAND → ランダム :527 → コモン STRDATA 52 件）
    st.day[0], st.time = 1, 1
    st.flag[852] = 6000
    # DAY 1 < 20 かつ 防衛 >= 5000 → :334 の RAND:100 も引く
    lines = _run(st, data, [99, 99, 99, 30, 0])
    assert lines == ["FLASH NEWS：《繊毛1本まで高精細に撮れる。超高速ズーム搭載 TENTAX SK 新発売》"]  # :671


# --- ゲームオーバー・裏ボス・イベント戦 ----------------------------------------------------------------------


@pytest.mark.parametrize(("turns", "line"), [(1, 101), (5, 109), (9, 117)])
def test_gameover_h_tentacle(st, data, turns, line):
    # :91–117：FLAG:11 = 7、LOCAL = (DAY*2+TIME) - DAY:2
    st.flag[60], st.flag[11] = 10001, 7
    st.day[0], st.time = 30, 1
    st.day[2] = 61 - turns
    text = _erb_lines()[line - 1].strip()[len("LOCALS = "):]
    assert _run(st, data, []) == [f"FLASH NEWS：《{text}》"]


def test_gameover_other_boss(st, data):
    st.flag[60], st.flag[11] = 10001, 1  # :152–153
    assert _run(st, data, []) == ["FLASH NEWS：《街は壊滅状態に。魔法少女はいったい何処へ…》"]


def test_gameover_choose_heroine(st, data):
    # :123–146：CFLAG:0 != 0 の女性（変身時ＴＳ 0）→ 候補 20／21。RAND:2 = 0 → 20（変身前）→ NAME:2
    st.flag[60], st.flag[11] = 10001, 7
    st.day[0], st.time, st.day[2] = 30, 0, 50  # LOCAL = 10
    st.charas[2].cflag[0] = 1
    lines = _run(st, data, [0, 3, 1])  # 選択・STRDATA(6)→:138・STRDATA(3)→:144
    assert lines == ["FLASH NEWS：《『触孕姫誕生 ～花園 桃香～』大人気販売中！》"]
    # CHOOSEHEROINE の RETURN LOCAL:1, LOCAL（:920）で RESULT:0 = 2、RESULT:1 = 0。その後 :205 RETURN が RESULT:0 = 0
    assert (st.result[0], st.result[1]) == (0, 0)


def test_gameover_choose_heroine_transformed(st, data):
    # 変身後（RESULT:1 == 1）→ PRINT_TRANSCALLNAME（変身中なら CSTR:1）、CALLNAME と同じなら NAME（:126–130）
    st.flag[60], st.flag[11] = 10001, 7
    st.day[0], st.time, st.day[2] = 30, 0, 50
    c = st.charas[2]
    c.cflag[0] = 1
    assert _run(st, data, [1, 0, 0]) == ["FLASH NEWS：《『触手絶頂少女 ～花園 桃香～』好評発売中！》"]
    assert (st.result[0], st.result[1]) == (0, 1)  # RESULT:1 = 変身後フラグ（:920）、RESULT:0 は :205 RETURN で 0
    st.savestr[20] = ""
    st.flag[60] = 10001
    c.cflag[3], c.cflag[1], c.cstr[1] = 1, 1, "ピーチ"
    assert _run(st, data, [1, 0, 0]) == ["FLASH NEWS：《『触手絶頂少女 ～ピーチ～』好評発売中！》"]


def test_gameover_no_heroine(st, data):
    st.flag[60], st.flag[11] = 10001, 7
    st.day[0], st.time, st.day[2] = 30, 0, 50
    assert _run(st, data, []) == ["FLASH NEWS：《街は壊滅状態に。魔法少女はいったい何処へ…》"]  # :148
    assert (st.result[0], st.result[1]) == (0, 0)  # RETURN 0,0（:922）


def test_lastboss_news(st, data):
    st.flag[60], st.flag[21] = 10000, 2  # :157–165
    assert _run(st, data, []) == ["FLASH NEWS：《開花に至った\"楽園の花\"、花粉を浴びた若い女性の子宮に触手が固着か》"]


@pytest.mark.parametrize(
    ("f60", "text"),
    [
        (110002, "お手柄！ 女子高襲う触手生物を撃退、可憐な魔法少女に女生徒ら感謝の声"),  # 2:307–308
        (100004, "大型触手生物が市街地を襲来、複数の女性が行方不明に"),  # 4:106–107
        (120002, "女子高が触手生物の襲撃で壊滅、女生徒ら多数残されたまま汚染区域に認定へ…"),  # -1 は "" → 0 に戻る（:85–87）
        (120004, "大型触手生物が市街地を襲来、女性ら多数行方不明。中には魔法少女の姿も？"),  # 4:109–110
        (103001, "前回の値"),  # 3001 は本体がコメント → 前回の RESULTS:0（:75）
        (100005 + 20000, "市街地に突如大穴、触巣出現で集団下校中の女子生徒ら犠牲に"),  # 5 の -1 は書かない → 前回値 "" → 0
    ],
)
def test_event_battle_news(st, data, f60, text):
    st.flag[60] = f60
    st.results[0] = "前回の値" if f60 == 103001 else ""
    assert _run(st, data, []) == [f"FLASH NEWS：《{text}》"]
    assert st.flag[60] == 0 and st.savestr[20] == text


def test_event_battle_news_3003_uses_target_name(st, data):
    st.flag[60] = 113003
    st.target = 3
    assert _run(st, data, []) == ["FLASH NEWS：《客を魅了、触手を翻弄！　アイドル「海野 蒼美」が囮となり避難の時間を稼ぐ》"]


def test_event_battle_news_empty_falls_through(st, data):
    # 前回の RESULTS:0 が "" なら :196 に入らず通常の抽選へ（FLAG:60 は :749 で 0）
    st.flag[60] = 103002
    st.results[0] = ""
    lines = _run(st, data, [99, 99, 30, 1])
    assert lines == ["FLASH NEWS：《各地で人語を話す白い獣の目撃例相次ぐ。魔法少女への勧誘も》"]  # :672
    assert st.flag[60] == 0


# --- 通常の抽選 -------------------------------------------------------------------------------------------


def test_danger_news(st, data):
    # :213 防衛 < 4000 かつ RAND:12 == 0 → :221 防衛 < 2000 かつ RAND:100 < 60 → STRDATA(8) → :226
    st.flag[852] = 1000
    assert _run(st, data, [0, 59, 3]) == ["FLASH NEWS：《市内の女子高が触手生物に占拠され自衛隊が駆けつけるも、行方不明者多数》"]


def test_danger_news_second_chance(st, data):
    # RAND:12 != 0 でも 防衛 < 1250 かつ RAND:3 == 0 → :221 RAND:100 = 60 → ELSE STRDATA(6) → :236
    st.flag[852] = 1000
    assert _run(st, data, [1, 0, 60, 0]) == ["FLASH NEWS：《深刻化する触手被害、政府は女性単独での外出自粛を要請》"]


def test_viral_media_static_flag(st, data):
    # [79] 有害ブログ（FLAG:805 bit 7）→ バイラルメディアフラグ = 0 → :216 RAND:2 == 0 → FLASH_VIRALMEDIA("通常")（21 件）
    st.flag.set_bit(805, 7, True)
    st.flag[852] = 1000
    assert _run(st, data, [0, 0, 20]) == ["FLASH NEWS：【悲報】女子小学生の●割が触手レイプで処女膜貫通済みだった模様ｗｗｗｗ"]
    assert st.temp.flashnews_viral == 1
    # 設定を切っても static #DIM は 1 のまま（:19–21）→ 《》なしで表示される
    st.flag.set_bit(805, 7, False)
    st.savestr[20] = ""
    st.day[0], st.time = 1, 0
    assert _run(st, data, []) == ["FLASH NEWS：街の噂・触手生物と戦う「魔法少女」気になるその正体は…？"]


def test_idol_news_video_leak(st, data):
    # :246 アイドル：紅葉 魅了経験 240（→ 240/12 = 20 件）、CFLAG:284 = 8（→ (8/4+1)^2+10 = 19、売れっ子 ×2 = 38 件）
    c = st.charas[1]
    c.exp[data.index_of("EXP", "魅了経験")] = 240
    c.cflag[284] = 8
    # RAND:100 = 5 → 標的 RAND:20 → 内容 RAND:88 = 60（51 番目以降は 2）→ 動画流出・売れっ子 STRDATA(5) → :279
    lines = _run(st, data, [5, 0, 60, 1])
    assert lines == ["FLASH NEWS：《やはり『紅葉』は魔法少女か？陵辱動画に映る特徴が完全に一致》"]
    assert (st.result[0], st.result[1]) == (0, 38)  # RESULT:1 は :978 の ×2 後、RESULT:0 は関数終端で 0


def test_idol_news_viral(st, data):
    # :254 バイラル（防衛 <= 5000、RAND:2 == 0）→ TARGET の変身能力 1 → "魔法少女"、genre 0 → :801 STRDATA(3)
    st.flag.set_bit(805, 7, True)
    st.flag[852] = 5000
    c = st.charas[1]
    c.exp[data.index_of("EXP", "魅了経験")] = 150  # 150/18 = 8 件、新人
    st.target = 1
    tc = st.charas[1]
    tc.talent[data.index_of("TALENT", "変身能力")] = 1
    for n in fn._TSUYOKI:
        tc.talent[data.index_of("TALENT", n)] = 0
    # 防衛 5000 は :213 の 4000 未満でない。RAND:100 → 標的 RAND:8 → 内容 RAND:50 → RAND:2 → STRDATA(3)
    lines = _run(st, data, [0, 0, 0, 0, 0])
    assert lines == ["FLASH NEWS：【朗報】新人魔法少女の赤羽 紅葉ちゃん、セクシーすぎる衣装をお披露目"]


def test_exposure_boom(st, data):
    # :318 露出ブーム浸透 = -4 + 6 = 2 → RAND:100 < 4 → CASE IS <= 4 → :321
    st.charas[1].abl[data.index_of("ABL", "露出癖")] = 6
    assert _run(st, data, [3]) == ["FLASH NEWS：《服が破けても戦い続ける魔法少女をPTAが批難。「娘が裸族になった」》"]


def test_boss_news(st, data):
    # :432 RAND:100 < 4、ボス 7/7 生存 → 生存率 100 → CASEELSE :454
    assert _run(st, data, [99, 3, 0]) == ["FLASH NEWS：《触手生物の目撃情報多数、危険な状態と専門家ら警告》"]


def test_defence_damage_news(st, data):
    # :458 防衛 4000 → RAND:100 < 3 + 1000/100 = 13 → STRDATA(7) → :466
    st.flag[852] = 4000
    assert _run(st, data, [99, 99, 12, 6]) == ["FLASH NEWS：《ナイトプールが触手汚染の被害に？　女性利用客ら触手を妊娠か》"]


def test_unpopular_news_skips_comment_lines(st, data):
    # 人気度 -60：:492 RAND(30) != 0 → :504 RAND(20) == 0 → STRDATA(5)（:508–509 はコメント）→ 3 件目 :510
    st.flag[853] = -60
    lines = _run(st, data, [99, 99, 1, 0, 2])
    assert lines == ["FLASH NEWS：《魔法少女、即ち戦士に扮した肉便器！ 容赦の無い新語辞典が話題に》"]


@pytest.mark.parametrize(("maniac_bit", "rng", "frag"), [
    (False, [0], "子宮に触手幼体が多数寄生"),  # MANIAC(14) = 1、RAND:4 = 0 → 偽
    (False, [1], "四肢切断され肉壁と一体化"),
    (True, [], "子宮に触手幼体が多数寄生"),  # MANIAC(14) = 0 → RAND:4 は引かない
])
def test_ending_b_ternary(st, data, maniac_bit, rng, frag):
    # :389 末路Ｂ（DAY > 21、防衛 < 2500、RAND:100 < 4）→ STRDATA(22) の 19 件目 = :423
    st.day[0] = 22
    st.flag[852] = 2000
    st.flag.set_bit(850, 14, maniac_bit)
    lines = _run(st, data, [1, 99, 50, 0, 18] + rng)  # :213 RAND:12・:318・:383・:389・STRDATA
    assert lines == [f"FLASH NEWS：《友人庇い行方不明の女子中学生を触巣深部にて発見。{frag}、回収を断念》"]


# --- $NEWSLOOP ---------------------------------------------------------------------------------------------


def test_random_loop_retry_counts_static(st, data):
    # :529 LOCAL < 8 で SAVESTR:21〜25 が空 → 失敗 → NOWLOOPNUM++ → 再抽選 → LOCAL 20（防衛 >= 5000）→ STRDATA(5) :662
    lines = _run(st, data, [99, 99, 5, 20, 3])
    assert lines == ["FLASH NEWS：《「駆逐してやる…　一匹残らず！」触手に恋人を攫われた男性、決意語る》"]
    assert st.temp.flashnews_loopnum == 1


def test_random_loop_exhausted(st, data):
    # NOWLOOPNUM は呼出間で持ち越す static：30 に達していれば再抽選しない → :741、SAVESTR:20 は空のまま
    st.temp.flashnews_loopnum = 30
    assert _run(st, data, [99, 99, 5]) == ["特にめぼしいニュースは無いようです。"]
    assert st.savestr[20] == "" and st.flag[60] == 0


def test_random_av_titles(st, data):
    # :533 FOR LOCAL,21,26 は SAVESTR:21〜25（26 は含まない）
    st.savestr[23] = "『写真集Ｘ』"
    st.savestr[26] = "『対象外』"
    lines = _run(st, data, [99, 99, 5, 0, 1])
    assert lines == ["FLASH NEWS：《『写真集Ｘ』好評発売中！》"]
    assert st.result[1] == 23


@pytest.mark.parametrize(("hikan", "sentou", "rng", "text"), [
    (0, 3, [0, 1], "魔法少女に憧れる少女が急増「小さな希望を広げたい」"),  # 候補 6 → :640
    (0, 6, [0], "アンケート結果  魔法少女を応援している 60％  頑張ってほしい 20％"),  # 候補 5 → :635
    (15, 0, [0, 2], "魔法少女のファンアートがSNS上で激増、過激な構図に非難の声も"),  # 候補 4 → :630
    (45, 0, [0], "アンケート結果  抜いた 30％  犯したい 10％  触手を応援している 35％"),  # 候補 1 → :611
    (70, 0, [1], "アンケート結果  気持ち良かった 90％  また使いたい 85％"),  # :566 被姦度 > 60 → :569
])
def test_random_heroine_reputation(st, data, hikan, sentou, rng, text):
    c = st.charas[1]
    c.exp[data.index_of("EXP", "被姦経験")] = hikan
    c.exp[data.index_of("EXP", "戦闘経験")] = sentou
    assert _run(st, data, [99, 99, 10] + rng) == [f"FLASH NEWS：《{text}》"]


def test_random_heroine_reputation_no_candidate_retries(st, data):
    # 被姦・戦闘とも 0 → 候補なし → 失敗 → 再抽選（:731–733）
    lines = _run(st, data, [99, 99, 10, 30, 2])
    assert lines == ["FLASH NEWS：《世界を一変させる官能的な装着感　ルクタンテ・ショーツ新発売》"]  # :673 ITEMNAME:399
    assert st.temp.flashnews_loopnum == 1


def test_show_shop_prints_news_once(st, data):
    # SHOP.ERB:40：再描画しても SAVESTR:20 のニュースが繰り返される（乱数は最初の 1 回だけ）
    st.rng = GameRng(5)
    out = TextOutput()
    shop.show_shop(st, data, out, NullNarrationService())
    first = st.savestr[20]
    assert first and f"FLASH NEWS：《{first}》" in [ln.text for ln in out.lines]
    out = TextOutput()
    shop.show_shop(st, data, out, NullNarrationService())
    assert st.savestr[20] == first
