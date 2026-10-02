"""ステータス表示画面：`ヒロイン関連/ステータス画面/`（路徑相對 `source/earGVP/ERB/`）。

- `SHOW_STATUS_CHARA_SELECT.ERB`：`@SHOW_STATUS_CHARA_SELECT, ARG`:26–123（メインループ）、`@SHOW_STATUS_CHARA_SELECT_DIRECTBTN`:132–140、
  `@SHOW_STATUS_CHARA_NAMES_LV`:150–155
- `SHOW_STATUS_CHARA_SELECT_PAGE1.ERB`〜`PAGE5.ERB`：各ページの表示（`@SHOW_STATUS_CHARA_SELECT_PAGEn`）と固有コマンド
  （`@CMD_STATUS_CHARA_SELECT_PAGEn`）
- `武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB@SET_FSTYLE_INFO`:118–165（共用 RESULTS:0〜2 に書く）

呼び出し元：SHOP [110]（`インターミッション画面/SHOP.ERB`:247–249）、戦闘中 [800]（`ゲーム内_戦闘処理/BATTLE_COM.ERB`:626–628）、
開局 HEROINE_PRESET [20]〜[29]（`ゲーム内_イベント発生/オープニング処理.ERB`:656–658）。全域 grep で呼び出しはこの 3 か所のみ。

ジェネレータ（INPUT ごとに yield）。戻り値は `RETURN 999`（:123）。SHOW_TRANS_STATUS（`SHOW_STATUS.ERH`:4 の広域変数：
この画面だけが使う、セーブ対象外）は画面ごとのローカル状態で持つ（入口 :31 で毎回代入されるので以前の値は読まれない）。
表示の REDRAW 0／3 は描画ロックのみ（状態に影響なし）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from .action import Ctx, config_check_maniac, config_check_other
from .akuoti import self_call
from .battle.cloth import costume_name, inner_name
from .battle.core import BOSSES, t
from .battle.gaping import printform_gaping_now
from .battle.hantei import fstyle_attack
from .battle.core import fstyle_name
from .battle.ninsin import pregnancy_belly_expand, pregnancy_boob_expand
from .body import AGE, BREAST_WEIGHT, BUST, HEIGHT, HIP, REAL_AGE, WAIST, WEIGHT
from .body import chara_make_age_setting, chara_size_default, cup_size, generate_bodyline, top_under
from .chara_common import charatalent, feat_bonus, is_male, seikaku_check, syuzoku_check
from .colorbar import color_bar, colorchip, colorsentence_bar, percent_cal, setcolor
from .config import CYAN, mob_exists, mob_getname
from .era import div, format_curly, format_percent, limit, mod
from .firstsetting import (
    chara_callname,
    convert_age,
    convert_colorcstr,
    nanori,
    size_setting_default,
    trans_after_callname,
    trans_after_name,
    trans_call,
)
from .relation import KYOUDAI, OIMEI, OJIOBA, OYAKO, SOFUBO, get_relation
from .shop import lb
from .status_talent import show_status_talent, talent_info
from .tattoo import print_tattoo, tattoo_access

Gen = Generator[None, int, int]
Z = "　"  # 全角空白
GRAY = (128, 128, 128)
DIM_GRAY = (105, 105, 105)
DIST_NAMES = ("拘束中", "近距離", "中距離", "遠距離")  # CSV定数定義/TCVARn.ERH:18–23 キャラ一時戦闘距離
GAIKEN_NAMES = ("", "安産型", "むちむち", "イカ腹", "スレンダー", "巨尻", "爆尻")  # CSV定数定義/TALENT.ERH:86–95 素質外見


class _Screen:
    """画面の状態：SHOW_TRANS_STATUS（変身時プロフィールを表示中か）。"""

    def __init__(self, trans: int) -> None:
        self.trans = trans


def _shortline(ctx: Ctx) -> None:
    """`汎用関数/PRINT_LINE.ERB@SHORTLINE`:3–7。"""
    ctx.out.print("――――――――――――――――――――――――――――")
    ctx.out.printl()


def _ix(ctx: Ctx, var: str, name: str) -> int:
    return ctx.data.index_of(var, name)


def _check_chara(st: GameState, arg: int) -> None:
    if not 0 <= arg < st.charanum:
        # NAME:ARG 等のキャラ変数参照が範囲外 → 原作でも CodeEE（reference/emuera-1824/Emuera/GameData/Variable/
        # VariableToken.cs:278「キャラ登録番号の範囲外」）。HEROINE_PRESET の [20]〜[29] は CHARANUM を見ずに呼ぶ（オープニング処理.ERB:656）。
        raise NotImplementedError(f"キャラ番号 {arg} は存在しない（原作でもエラー）")


# --- メインループ（SHOW_STATUS_CHARA_SELECT.ERB）------------------------------------------------------


def show_status_chara_select(ctx: Ctx, arg: int) -> Gen:
    """`@SHOW_STATUS_CHARA_SELECT, ARG`:26–123。"""
    st, out = ctx.state, ctx.out
    _check_chara(st, arg)
    page = 1  # :27–29
    sc = _Screen(1 if st.charas[arg].cflag[1] > 0 else 0)  # :31
    while True:  # :37 DO
        lb(out)
        out.drawline()
        _PAGES[page](ctx, arg, sc)  # :42 CALLFORM SHOW_STATUS_CHARA_SELECT_PAGE{PAGE}
        out.print(" [1][前ページ]" + Z * 2)  # :45
        for cmd, text in ((1000, "戦闘　"), (2000, "素質　"), (3000, "武器　"), (4000, "相関　"), (5000, "個人　")):
            _directbtn(ctx, page, cmd, text)
        out.printl(Z + "[2][次ページ]")  # :52
        out.print(" [999]戻る" + Z * 5)  # :53
        if st.flag[700] > 0:  # :55–56
            setcolor(out, *GRAY)
        out.print(Z + "[100]前のキャラ" + Z * 10)
        out.print("[200]次のキャラ")
        out.printl()
        out.reset_color()
        r = yield  # :63 INPUT
        if r == 999:  # :68–69
            break
        if r == 1:
            page = 5 if page - 1 < 1 else page - 1
        elif r == 2:
            page = 1 if page + 1 > 5 else page + 1
        elif r in (1000, 2000, 3000, 4000, 5000):
            page = r // 1000
        elif r in (100, 200):  # :84–104
            if st.flag[700] == 0:
                if r == 100:
                    arg -= 1
                    if arg == 0:
                        arg = st.charanum - 1
                else:
                    arg += 1
                    if arg == st.charanum:
                        arg = 1
                sc.trans = 1 if st.charas[arg].cflag[1] > 0 else 0
            else:
                out.printl()
                out.printl("正しい値を入力してください")
        else:  # :106–112
            res = yield from _CMDS[page](ctx, arg, r, sc)
            if res == 0:
                out.printl()
                out.printl("正しい値を入力してください")
    return 999  # :123


def _directbtn(ctx: Ctx, page: int, cmd: int, text: str) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_DIRECTBTN, PAGE, CMD_ID, CMD_TEXT`:132–140。"""
    out = ctx.out
    if page * 1000 == cmd:
        out.set_color(CYAN)
    out.print(f"[{cmd}]{text}")
    out.reset_color()


def _names_lv(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_NAMES_LV, ARG`:150–155。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    out.printl(f"氏名　：{c.name}")
    out.printl(f"呼び名：{c.callname}")
    out.printl(f"一人称：{self_call(ctx, arg)}")
    out.printl(f"レベル：Lv.{c.abl[_ix(ctx, 'ABL', 'レベル')]} （{c.juel[_ix(ctx, 'JUEL', '経験値')]}％）")
    out.printl(f"性別　：{'男' if is_male(ctx.data, c) else '女'}")


# --- PAGE1：基本ステータス ----------------------------------------------------------------------


_KOJO_LABELS = {  # PAGE1:45–65（CFLAG:6）
    -2: "[0] 口上設定（現在：非表示）" + Z * 4,
    -1: "[0] 口上設定（未教育）" + Z * 7,
    0: "[0] 口上設定（現在：女性汎用）" + Z * 3,
    1: "[0] 口上設定（現在：オトコ汎用）" + Z * 2,
    2: "[0] 口上設定（現在：ロボ風）" + Z * 4,
    3: "[0] 口上設定（現在：あなた）" + Z * 4,
    4: "[0] 口上設定（現在：汎用豹変）" + Z * 3,
}


def _page1(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_PAGE1, ARG`:5–138。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[arg]
    battle = st.flag[700] > 0
    out.printl(Z * 17 + "基本ステータス情報" + Z * 14 + "PAGE(1/5)")
    out.drawline()
    out.print("氏名　：" + format_percent(c.name, 28, True))  # :16–19
    out.print_plain(Z)
    out.print("[10]主観モードの変更：" + ("使用する" if t(ctx, c, "主観視点") > 0 else "使用しない"))
    out.printl()
    out.print("呼び名：" + format_percent(c.callname, 28, True))  # :22–29
    out.print_plain(Z)
    if battle:
        setcolor(out, *DIM_GRAY)
    out.print("[11]呼び名の変更")
    out.reset_color()
    out.printl()
    out.print("一人称：" + format_percent(self_call(ctx, arg), 28, True))  # :32–39
    out.print_plain(Z)
    if battle:
        setcolor(out, *DIM_GRAY)
    out.print("[12]一人称の変更")
    out.reset_color()
    out.printl()
    out.print("性別　：" + format_percent("男" if is_male(data, c) else "女", 28, True))  # :43–66
    out.print_plain(Z)
    k = c.cflag[6]
    if k in _KOJO_LABELS:
        out.print(_KOJO_LABELS[k])
    elif c.no != 0:  # NO:ARG（CSV 番号）
        out.print("[0] 口上設定（現在：専用）" + Z * 5)
    else:
        setcolor(out, *DIM_GRAY)
        out.print_plain("[0]口上設定（現在：汎用）" + Z * 5)
        out.reset_color()
    out.printl()
    _syuzoku(ctx, arg)  # :69–70
    out.printl()
    _seikaku(ctx, arg)  # :72–73
    out.printl()
    if t(ctx, c, "変身能力") == 1:  # :78–98
        _shortline(ctx)
        out.print("【変身能力あり】")
        out.print_plain(Z * 11)
        if battle:
            setcolor(out, *DIM_GRAY)
        out.print("[13]変身後名/掛け声の設定")
        out.reset_color()
        out.printl()
        if c.cflag[2]:
            out.print(f"{Z}変身後名{Z * 2}：{c.cstr[0]}")
            if c.cflag[3] and c.cstr[0] != c.cstr[1]:
                out.print(f"（{c.cstr[1]}）")
            out.printl()
        if c.cflag[4]:
            out.printl(f"{Z}変身時かけ声：{c.cstr[2]}")
    elif st.target_chara.talent[0]:
        # :100 `ELSEIF TALENT;ARG:変身能力 == 素質変身能力_非戦闘員` は `;` 以降が行中コメント
        # （reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:954–966）なので `ELSEIF TALENT` = TALENT:TARGET:0（処女）
        # （引数省略は TARGET・0：GameData/Variable/VariableParser.cs:107–119）。原作どおり。
        _shortline(ctx)
        out.printl("【非戦闘員】")
    _shortline(ctx)  # :107–108
    _battlestats(ctx, arg)
    _shortline(ctx)  # :112–114
    _basestats(ctx, arg)
    _sengi(ctx, arg)
    if any(t(ctx, c, n) for n in ("Ｃ結界", "Ｖ結界", "Ａ結界", "Ｂ結界", "避妊結界")):  # :118–122
        out.printl()
        _shortline(ctx)
        _shields(ctx, arg)
    if c.cflag[32] > 0:  # :126–130
        out.printl()
        _shortline(ctx)
        _tattoo(ctx, arg)
    out.printl()  # :131
    _shortline(ctx)  # :135–138
    _cloth(ctx, arg)
    out.drawline()
    out.printl()


def _cmd_page1(ctx: Ctx, arg: int, cmd: int, sc: _Screen) -> Gen:
    """`@CMD_STATUS_CHARA_SELECT_PAGE1, ARG, INPUT_CMD`:148–250。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[arg]
    sub = _ix(ctx, "TALENT", "主観視点")
    if cmd == 0:  # :154–171 口上設定の切り替え
        k = c.cflag[6]
        if k == 0:
            c.cflag[6] = 1
        elif k == 1:
            c.cflag[6] = 2
        elif k == 2:
            c.cflag[6] = 3
            c.talent[sub] = 1
        elif k == 3:
            c.cflag[6] = 4
            c.talent[sub] = 0
        elif k == 4:
            c.cflag[6] = -2
        elif k == c.no:
            c.cflag[6] = 0
        else:
            c.cflag[6] = c.no
        return 1
    if cmd == 10:  # :173–193 主観モード
        if c.talent[sub] == 1:
            out.printl("現在『主観モード』を使用中です")
            out.printl("[0]変更しない")
            out.printl("[1]主観モードを終了する")
            r = yield
            if r == 1:
                c.talent[sub] = 0
                out.printw("地の文を変更しました")
        else:
            out.printl("※地の文をより主観的な描写に変更します")
            out.printl("　この設定は個別に適用されます")
            out.printl("[0]使用しない")
            out.printl("[1]使用する")
            r = yield
            if r == 1:
                c.talent[sub] = 1
                out.printw("地の文を変更しました")
        return 1
    if cmd in (11, 12, 13):  # :195–245
        if st.flag[700]:
            return 0
        if cmd == 11:
            yield from chara_callname(ctx, arg)
            return 1
        if cmd == 12:
            raise NotImplementedError("一人称設定画面（FIRSTSETTING_CHARA_SELFCALL）は未移植")
        if t(ctx, c, "変身能力") != 1:
            return 0
        lcount = out.linecount  # :210
        while True:  # $LOOP_12
            out.printl("変更する項目を選択してください")
            _shortline(ctx)
            for n, label in ((0, "変身後名・・・・・・"), (1, "変身後呼び名・・・・"), (2, "変身時かけ声・・・・"),
                             (3, "変身後名乗り口上・・")):
                v = f"・『{c.cstr[n]}』" if c.cflag[2 + n] == 1 else "・ なし"
                out.printl(f"[{n}]{Z}{label}{v}")
            out.printl()
            out.printl("[99] 戻る")
            while True:  # $INPUT_LOOP_12
                r = yield
                if r in (0, 1, 2, 3, 99):
                    break
            if r == 0:
                yield from trans_after_name(ctx, arg)
            elif r == 1:
                if c.cflag[2] == 1:
                    c.cflag[3] = 1
                    yield from trans_after_callname(ctx, arg)
            elif r == 2:
                yield from trans_call(ctx, arg)
            elif r == 3:
                yield from nanori(ctx, arg)
            else:
                return 1
            out.clearline(out.linecount - lcount)  # :243
    return 0


def _syuzoku(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_SYUZOKU, ARG`:260–263（SYUZOKU_CHECK "STRING"：該当なしは「ランダム」）。"""
    c = ctx.state.charas[arg]
    ctx.out.print("種族　：")
    k = syuzoku_check(c)
    name = ctx.data.names["TALENT"].get(k, "") if k else "ランダム"
    ctx.out.print(format_percent(name, 46, True))


def _seikaku(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_SEIKAKU, ARG`:270–273（HTML_PRINT、title に TALENT_INFO）。
    SEIKAKU_CHECK_F が 0（性格なし）なら TALENTNAME:0（処女）と TALENT_INFO(0) になる（原作どおり）。"""
    c = ctx.state.charas[arg]
    k = seikaku_check(ctx.data, c)
    name = ctx.data.names["TALENT"].get(k, "")
    ctx.out.html_print(f"<nobr><nonbutton title='{talent_info(k)}'>性格　：{format_percent(name, 46, True)}"
                       "</nonbutton></nobr>")


def _battlestats(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_BATTLESTATS, ARG`:282–322。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    m = c.maxbase
    a, d, s, i = (_ix(ctx, "BASE", n) for n in ("攻撃", "防御", "敏捷", "知性"))
    out.printl(f"レベル：Lv.{c.abl[_ix(ctx, 'ABL', 'レベル')]} （{c.juel[_ix(ctx, 'JUEL', '経験値')]}％）"
               f"{Z}修練P：{c.juel[_ix(ctx, 'JUEL', '修練P')]}P")
    for name in ("体力", "気力", "性耐性"):
        k = _ix(ctx, "BASE", name)
        colorsentence_bar(out, name, 6, c.base[k], m[k], 20)
        out.printl()
    pa, pd, ps = (div(m[x] * c.cflag[10], 100) for x in (a, d, s))  # :303–305
    raw = f"攻撃：{format_curly(m[a], 4)}  防御：{format_curly(m[d], 4)}  敏捷：{format_curly(m[s], 4)}  知性：{format_curly(m[i], 4)}"
    mod_ = f"攻撃：{format_curly(pa, 4)}  防御：{format_curly(pd, 4)}  敏捷：{format_curly(ps, 4)}  知性：{format_curly(m[i], 4)}"
    kind = t(ctx, c, "変身能力")
    if kind == 0:
        out.print(f"戦闘力{Z * 2}{format_percent(raw, 46, True)}{Z * 2}")
    elif kind == 1:
        out.print(f"変身前{Z * 2}{format_percent(mod_, 46, True)}{Z * 2}")
        out.printl()
        out.print(f"変身後{Z * 2}{format_percent(raw, 46, True)}{Z * 2}")
    elif kind == -1:
        out.print(f"戦闘力{Z * 2}{format_percent(mod_, 46, True)}{Z * 2}")
    out.printl()


def _basestats(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_BASESTATS, ARG`:328–333（基礎値＋FEAT_BONUS_F）。LOCALS への文字列代入は末尾の半角空白が
    trim される（reference/emuera-1824/Emuera/GameProc/Function/ArgumentBuilder.cs:772–774 → Sub/LexicalAnalyzer.cs:1217–1221）。"""
    data, out = ctx.data, ctx.out
    c = ctx.state.charas[arg]
    b = c.base
    fb = lambda w: feat_bonus(data, c, w)  # noqa: E731
    s1 = (f"体力：{b[_ix(ctx, 'BASE', '体力基礎')] + fb(0)}  気力：{b[_ix(ctx, 'BASE', '気力基礎')] + fb(1)}  "
          f"性耐性：{b[_ix(ctx, 'BASE', '性耐性基礎')] + fb(2)}")
    out.printl("◆基礎値  " + format_percent(s1, 46, True))
    s2 = "  ".join(f"{n}：{format_curly(b[_ix(ctx, 'BASE', n)] + fb(w), 4)}"
                   for w, n in ((3, "攻撃"), (4, "防御"), (5, "敏捷"), (6, "知性")))
    out.printl(" " * 10 + format_percent(s2, 46, True))


def _sengi(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_SENGI, ARG`:339–349（改行しない）。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    a = lambda n: c.abl[_ix(ctx, "ABL", n)]  # noqa: E731
    out.print("◆戦技Lv  ")
    if t(ctx, c, "変身能力") != -1:
        out.print(f"近距離Lv.{a('近距離')}  中距離Lv.{a('中距離')}  遠距離Lv.{a('遠距離')}  ")
    else:
        out.print(f"戦闘基礎Lv.{a('戦闘基礎')}  ")
    out.print(f"空中Lv：{c.maxbase[_ix(ctx, 'BASE', '空中ダッシュ')]}")


def _shields(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_SHIELDS, ARG`:360–396。"""
    data, out = ctx.data, ctx.out
    c = ctx.state.charas[arg]
    names = data.names["TALENT"]
    seals = [(_ix(ctx, "TALENT", n), _ix(ctx, "BASE", n + "耐久力")) for n in ("Ｃ結界", "Ｖ結界", "Ａ結界", "Ｂ結界")]
    printed = 0
    if any(c.talent[s] for s, _ in seals):
        out.print("◆結界" + Z * 2)
        for s, d in seals:
            if c.talent[s] == 0:
                continue
            if printed:
                out.printl()
                out.print(Z * 5)
            out.print(names.get(s, ""))
            _shield_durability(ctx, arg, d)
            printed = 1
    if t(ctx, c, "避妊結界"):
        if printed:
            out.printl()
        out.printl(Z * 5 + "避妊結界")


def _shield_durability(ctx: Ctx, arg: int, d: int) -> None:
    """`@SHOW_SHIELD_DURABILITY, ARG, DURABILITY_NUM`:407–439。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    cur, mx = c.base[d], c.maxbase[d]
    if cur > 0:
        p = percent_cal(cur, mx)  # :416
        r = limit(255 - div(p * p * 4, 200), 0, 255)
        g = limit(-215 - div(p * p, 100) + p * 5, 0, 255)
        hue = div(p * 3, 4) - 160
        color_bar(out, cur, mx, 20, r, g, 20, hue, 6, 32, 20, 1, "▮", "▮")
    else:
        setcolor(out, 128, 40, 40)
        out.print(Z * 3 + "崩" + Z + "壊" + Z * 4)
        out.reset_color()
    out.set_bold(True)
    out.print(f" {percent_cal(cur, mx)}％{Z}")
    out.set_bold(False)
    if st.flag[999] == 1:  # :435–439 デバッグ表示
        setcolor(out, 96, 96, 96)
        out.print(f" /* debug */ {cur} / {mx}")
        out.reset_color()


def _tattoo(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_TATTOO, ARG`:446–498（TARGET を一時的に ARG にして TATTOO_ACCESS／PRINT_TATTOO）。"""
    st, out = ctx.state, ctx.out
    keep = st.target
    st.target = arg
    try:
        bits = int(tattoo_access(ctx, "POSITION_BIT"))
        if bits > 0:
            head = "◆淫紋"
            for i in range(4):  # :454 FOR LOCAL, 0, 感覚数
                if (bits >> i) & 1:
                    if head != "◆淫紋":
                        out.printl()
                    out.print(f"{head}{Z * 2}位置：")
                    out.print(("下腹部", "腹部" + Z, "右臀部", "左乳房")[i])
                    out.print(Z * 2 + "状態：")
                    head = Z * 3
                    print_tattoo(ctx, i)
            extra = int(tattoo_access(ctx, "TATTOO_TYPE", 7))  # :473–496
            for i in range(8):
                if (extra >> i) & 1:
                    out.printl()
                    out.print(Z * 5 + "位置：")
                    pos = ("額" + Z * 2, "喉下部", "背中" + Z, "右頬" + Z, "左頬" + Z, "右内股", "左内股")
                    if i < len(pos):
                        out.print(pos[i])
                    out.print(Z * 2 + "状態：")
                    print_tattoo(ctx, 7, i)
    finally:
        st.target = keep  # :498


def _cloth(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_CLOTH, ARG`:504–545。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    out.printl("◆衣装設定")
    out.print("【アウター】")
    if t(ctx, c, "変身能力") == 1:
        out.printl("┏なし" if c.cflag[40] == 0 else costume_name(ctx, arg, 0))  # :511–515（名前のときは ┏ なし：原作どおり）
        out.printl(Z * 6 + "┗" + ("なし" if c.cflag[41] == 0 else costume_name(ctx, arg, 1)))
    else:
        out.printl("なし" if c.cflag[40] == 0 else costume_name(ctx, arg, 0))
    out.print("【インナー】")
    out.printl("なし" if c.cflag[42] == 0 else inner_name(ctx, arg))
    out.print("【その他" + Z + "】")
    items = ctx.data.items
    out.printl("なし" if c.cflag[43] == 0 else (items[c.cflag[43]].name if c.cflag[43] in items else ""))


# --- PAGE2：素質・性成長 ------------------------------------------------------------------------

_ABLS = ("Ｃ感覚", "Ｖ感覚", "Ａ感覚", "Ｂ感覚", "従順", "欲望", "技巧", "奉仕精神", "露出癖", "マゾっ気", "触手中毒", "自慰中毒",
         "精液中毒", "噴乳中毒", "射精中毒")  # PAGE2:75–80
_MARKS = ("快楽刻印", "苦痛刻印", "屈服刻印", "恐怖刻印", "恥辱刻印")  # :140–143
_EXPS = ("戦闘経験", "ボス経験", "ラスボス経験", None, "近距離戦闘経験", "中距離戦闘経験", "遠距離戦闘経験", "戦闘基礎経験", None,
         "被姦経験", "幽閉経験", None, "Ｖ経験", "Ａ経験", None, "絶頂経験", "精液経験", "フェラ経験", None,
         "露出快楽経験", "奉仕快楽経験", "苦痛快楽経験", None, "自慰経験", "近親交配経験", None,
         "異常経験", "Ｖ拡張経験", "Ａ拡張経験", None, "射精経験", "噴乳経験", "放尿経験", None,
         "寄生経験", "出産経験", "魅了経験")  # :196–207（None = -1：改行）
# SHOW_STATUS.ERH:7–17 非性的経験
_NON_SEXUAL = ("戦闘経験", "ボス経験", "ラスボス経験", "近距離戦闘経験", "中距離戦闘経験", "遠距離戦闘経験", "戦闘基礎経験", "魅了経験")
NON_SEXUAL_RANK = -1  # SHOW_STATUS.ERH:19


def get_color_by_rank(ctx: Ctx, rank: int) -> tuple[int, int, int]:
    """`@GET_COLOR_BY_RANK, RANK`（PAGE2:283–305）：`RETURN r, g, b` → 共用 RESULT:0〜2。"""
    rgb = {NON_SEXUAL_RANK: (255, 255, 255), 1: (255, 192, 192), 2: (255, 128, 128), 3: (255, 64, 64),
           4: (255, 94, 255)}.get(rank, (128, 128, 128))
    ctx.state.set_result_x(*rgb)
    return rgb


def _page2(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_PAGE2, ARG`:5–40。"""
    st, out = ctx.state, ctx.out
    out.printl(Z * 18 + "素質・性成長" + Z * 16 + "PAGE(2/5)")
    out.drawline()
    _names_lv(ctx, arg)
    _shortline(ctx)
    show_status_talent(ctx, arg, 0, 1)
    _shortline(ctx)
    _abl(ctx, arg)
    out.printl()
    _shortline(ctx)
    _mark(ctx, arg)
    out.printl()
    _shortline(ctx)
    _exp(ctx, arg)
    if st.flag[999] == 1:  # :31–35
        out.printl()
        _shortline(ctx)
        _juel(ctx, arg)
    out.printl()
    out.drawline()
    out.print_plain(Z)  # :39–40
    out.printl("[0]キャラクターデータの書き出し" + Z * 2)  # PRINTKL


def _cmd_page2(ctx: Ctx, arg: int, cmd: int, sc: _Screen) -> Gen:
    """`@CMD_STATUS_CHARA_SELECT_PAGE2, ARG, INPUT_CMD`:50–59。"""
    if cmd == 0:
        from .export_csv import export_csv

        ctx.state.target = arg  # :54
        yield from export_csv(ctx)
        return 1
    return 0


def _abl(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_ABL, ARG`:73–127。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    names = ctx.data.names["ABL"]
    out.printl("◆開発")
    for n, name in enumerate(_ABLS):
        k = _ix(ctx, "ABL", name)
        v = c.abl[k]
        rank = 0 if v == 0 else 1 if v <= 3 else 2 if v <= 5 else 3 if v <= 9 else 4
        col = get_color_by_rank(ctx, rank)
        setcolor(out, *col)
        out.print(f"{format_percent(names.get(k, ''), 8, True)}：Lv{format_curly(v, 2)}[")
        if v > 10:
            color_bar(out, v - 9, 10, 5, *col, -16, 10, 10, 6, 2, "❤", ">>")
        else:
            color_bar(out, v, 10, 10, *col, -160, 10, 10, 6, 2, ">", ">")
        setcolor(out, *col)
        out.print("]")
        out.reset_color()
        if (n + 1) % 4 == 0:
            out.printl()


def _mark(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_MARK, ARG`:138–183。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    names = ctx.data.names["MARK"]
    out.printl("◆刻印")
    for n, name in enumerate(_MARKS):
        k = _ix(ctx, "MARK", name)
        v = c.mark[k]
        rank = 0 if v == 0 else 1 if v <= 2 else 2 if v <= 3 else 3 if v <= 4 else 4
        col = get_color_by_rank(ctx, rank)
        setcolor(out, *col)
        out.print(f"{names.get(k, '')}：Lv{format_curly(v, 2)}[")
        color_bar(out, v, 5, 5, *col, -160, 10, 10, 6, 2, "❤", "❤")
        setcolor(out, *col)
        out.print("]")
        out.reset_color()
        if (n + 1) % 3 == 0:
            out.printl()


def _exp(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_EXP, ARG`:194–256。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[arg]
    names = data.names["EXP"]
    non_combatant = t(ctx, c, "変身能力") == -1
    out.printl("◆経験")
    for name in _EXPS:
        if name is None:
            out.printl()
            continue
        if name == "放尿経験" and config_check_maniac(st, 15) == 0:  # :224–225
            continue
        if non_combatant:
            if name in ("近距離戦闘経験", "中距離戦闘経験", "遠距離戦闘経験"):
                continue
        elif name == "戦闘基礎経験":
            continue
        k = _ix(ctx, "EXP", name)
        v = c.exp[k]
        if v == 0:
            rank = 0
        elif name in _NON_SEXUAL:  # MATCH(非性的経験, OUTPUT)
            rank = NON_SEXUAL_RANK
        else:
            rank = 1 if v < 30 else 2 if v < 100 else 3 if v < 200 else 4
        setcolor(out, *get_color_by_rank(ctx, rank))
        out.print(f"{format_percent(names.get(k, ''), 14, False)}：{format_curly(v, 8, True)}")
        out.reset_color()


def _juel(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_JUEL, ARG`:263–275（デバッグ表示）。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    names = ctx.data.names["PALAM"]
    out.print("◆珠" + Z)
    for n in range(12):
        k = n + 6 if n > 3 else n
        if n in (4, 8):
            out.print(Z * 3)
        out.print(f"{format_percent(names.get(k, ''), 6, False)} : {format_curly(c.juel[k], 10)}{Z}")
        if n in (3, 7):
            out.printl()


# --- PAGE3：武器カスタマイズ ------------------------------------------------------------------

_FSTYLE_INFO = {  # FIGHT_STYLE.ERB@SET_FSTYLE_INFO:118–165
    "連続": ("威力影響度：攻撃*0.25 + 敏捷*0.20", "追加効果　：攻撃が２回ヒットする", "BURST性能 ：６ヒットする連続攻撃。全て直撃すれば高威力"),
    "装甲": ("威力影響度：攻撃*0.45 + 防御*0.40", "追加効果　：被ダメージ軽減　クリティカルされない", "BURST性能 ：直撃しやすくなる。攻撃後にオートガード"),
    "撹乱": ("威力影響度：攻撃*0.75 + 敏捷*0.35", "追加効果　：クリティカル率ＵＰ　ただし防御力にペナルティ", "BURST性能 ：威力が上がる。確率で相手を怯ませる"),
    "重撃": ("威力影響度：攻撃*0.90 + 防御*0.30", "追加効果　：威力が高い　ただし回避率にペナルティ", "BURST性能 ：直撃しにくいが大振りな一撃"),
    "広範": ("威力影響度：攻撃*1.15", "追加効果　：カス当たりの威力が高い　ただし直撃しにくい", "BURST性能 ：絶対直撃する。ただし反動で回避できなくなる"),
    "全力": ("威力影響度：攻撃*1.50", "追加効果　：反動で疲労蓄積　疲労度に応じて直撃率ダウン", "BURST性能 ：捨て身で放つ、強烈な一撃"),
    "知略": ("威力影響度：攻撃*0.75 + 知性*0.25", "追加効果　：知性に応じて直撃率が上昇", "BURST性能 ：クリティカルしやすくなる。攻撃後に見切り効果"),
    "設置": ("威力影響度：攻撃*0.50 + 知性*0.30", "追加効果　：直撃、カス当たり時に相手の油断度を増加", "BURST性能 ：油断度上昇効果２倍"),
    "使役": ("威力影響度：攻撃*0.25 + 知性*0.20", "追加効果　：攻撃が２回ヒットする", "BURST性能 ：直撃しにくいが大振りな一撃"),
    "反撃": ("威力影響度：攻撃*0.70 + 防御*0.50", "追加効果　：弱攻撃後に反撃体勢、反撃成功時に強力な速攻　「防御」コマンドの効果変更",
           "BURST性能 ：戦闘中に反撃を成功させて蓄積したダメージを一撃に加える"),
    "通常": ("威力影響度：攻撃*1.00", "追加効果　：標準的な性能　直撃率が少し高い", "BURST性能 ：ダメージ効率の良い強攻撃"),
}


def set_fstyle_info(ctx: Ctx, who: int, dist: int) -> None:
    """`@SET_FSTYLE_INFO, ARG, ARG:1`：共用 RESULTS:0〜2 に戦闘スタイルの説明を書く（docs/wiki/python/result.md）。"""
    info = _FSTYLE_INFO[fstyle_name(ctx, who, dist)]
    for i, s in enumerate(info):
        ctx.state.results[i] = s


def _page3(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_PAGE3, ARG`:5–29。"""
    st, out = ctx.state, ctx.out
    out.printl(Z * 17 + "武器カスタマイズ" + Z * 15 + "PAGE(3/5)")
    out.drawline()
    _names_lv(ctx, arg)
    for dist in (1, 2, 3):
        _shortline(ctx)
        _weapon_edit(ctx, arg, dist)
    out.printl()
    out.drawline()
    if st.charas[arg].cflag[0] != 0 or st.flag[700]:  # :21–28
        setcolor(out, *DIM_GRAY)
        out.print_plain("[0]武器カスタマイズ画面に移動" + Z * 3)
        out.reset_color()
    else:
        out.print("[0]武器カスタマイズ画面に移動" + Z * 3)
    out.printl()


def _cmd_page3(ctx: Ctx, arg: int, cmd: int, sc: _Screen) -> Gen:
    """`@CMD_STATUS_CHARA_SELECT_PAGE3, ARG, INPUT_CMD`:39–46。"""
    st = ctx.state
    if cmd == 0 and st.charas[arg].cflag[0] == 0 and st.flag[700] == 0:
        raise NotImplementedError("武器カスタマイズ画面（WEAPON_CUSTOMIZE）は未移植")
    return 0
    yield  # pragma: no cover


def _weapon_edit(ctx: Ctx, arg: int, dist: int) -> None:
    """`@SHOW_WEAPON_EDIT, ARG, RANGE`:56–72。FSTYLE_ATTACK の RETURN（RESULT:0 のみ）は模型化しない。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    out.print(f"◆{DIST_NAMES[dist]}武器")
    if c.cstr[dist + 4] != "":
        out.printl(f"『{c.cstr[dist + 4]}』")
    else:
        out.printl("（武器名が設定されていません）")
    out.printl("│")
    power = fstyle_attack(ctx, arg, dist)
    out.printl(f"└◎戦闘スタイル{Z}<<{fstyle_name(ctx, arg, dist)}>>{Z * 9}威力：【{power}】")
    set_fstyle_info(ctx, arg, dist)
    for i in range(3):
        out.printl(f"{Z}---> {ctx.state.results[i]}")


# --- PAGE4：キャラクター相関 -------------------------------------------------------------------

_BLOOD = ((0, "？？？"), (1, "Ｃ触手"), (2, "Ｖ触手"), (3, "Ａ触手"), (4, "Ｂ触手"), (5, "Ｓ触手"), (6, "Ｐ触手"), (7, "Ｈ触手"))  # DIM.ERH:244–251


def _page4(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_PAGE4, ARG`:5–53。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    out.printl(Z * 17 + "キャラクター相関" + Z * 15 + "PAGE(4/5)")
    out.drawline()
    _names_lv(ctx, arg)
    _shortline(ctx)
    _relations(ctx, arg)
    blood = c.relation[arg]  # RELATION:ARG:ARG
    if blood > 0:
        _shortline(ctx)
        out.print(Z + "血統" + Z + "(")
        for bit, name in _BLOOD:
            if (blood >> bit) & 1:
                out.print(Z + name)
        out.printl(Z + ")")
    else:
        out.printl()
    if c.cflag[7] or c.cflag[9]:
        _shortline(ctx)
        _parents(ctx, arg)
    else:
        out.printl()
    out.drawline()


def _cmd_page4(ctx: Ctx, arg: int, cmd: int, sc: _Screen) -> Gen:
    """`@CMD_STATUS_CHARA_SELECT_PAGE4`:63–65：固有コマンドなし。"""
    return 0
    yield  # pragma: no cover


def _relations(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_RELATIONS, ARG`:79–151。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    lcount = 0
    for i in range(st.charanum):
        if i == GameState.MASTER or i == arg:
            continue
        if c.relation[i]:
            out.printl(f"{Z}({format_curly(i, 2)}){Z}{st.charas[i].name}{Z}→{Z}{get_relation(ctx, arg, i)}")
            lcount += 1
    if lcount == 0:
        out.printl(Z * 3 + "相関関係のあるキャラ：なし")
        lcount += 1
    if c.cflag[120] > 0 or c.cflag[121] > 0 or c.cflag[122] > 0:
        out.printl()
        out.printl(Z * 3 + "コネクション：")
        lcount += 2
    if c.cflag[120] == 1:
        out.printl(Z * 6 + "噂好きな友人")
        lcount += 1
    if c.cflag[121] == 1:
        out.printl(Z * 6 + "警察関係者")
        lcount += 1
    elif c.cflag[121] == 2:
        out.printl(Z * 6 + "警察上層部")
        lcount += 1
    v = c.cflag[122]
    if v > 0:
        b2, b3, b4 = (v >> 2) & 1, (v >> 3) & 1, (v >> 4) & 1
        out.print(Z * 6 + "情報屋(")
        if b2 and b3:
            out.print("無法者")
        elif b2 and b4:
            out.print("お調子者な男")
        elif b3 and b4:
            out.print("老紳士")
        elif b2:
            out.print("下品な男")
        elif b3:
            out.print("上品な男")
        elif b4:
            out.print("探偵風の男")
        else:
            out.print("特徴の無い男")
        out.printl(")")
        lcount += 1
    if c.cflag[123] == 1:
        out.printl(Z * 6 + "裕福な実家")
        lcount += 1
    for _ in range(20 - lcount):  # :149–151（MIN_LINES = 20）
        out.printl()


def _father_name(ctx: Ctx, v: int) -> str:
    """PAGE4:209–222 の TRYCALLFORM TENTACLE_*_GETNAME（RESULTS）。関数が無いと RESULTS は前の値のままなので停止。"""
    st = ctx.state
    if v < 100:
        if v in BOSSES:  # 触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB:7–8
            return BOSSES[v].name
    elif v < 200:
        if v == 101:  # TENTACLE_LASTBOSS_1_Ｋ触手.ERB:7–8
            return "Ｋ触手"
        if v == 102:  # TENTACLE_LASTBOSS_2_天使の樹.ERB:8–15
            return {1: "天使の樹", 2: "楽園の花"}.get(st.flag[21], "堕落の核")
    elif v == 200:
        return "雑魚触手"
    elif mob_exists(v - 200):
        return mob_getname(st, v - 200)
    raise NotImplementedError(f"父親（CFLAG:9 = {v}）の名前関数が無い（TRYCALLFORM 不発で RESULTS が前の値のまま）")


def _parents(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_PARENTS, ARG`:162–242。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    real_age = _ix(ctx, "BASE", "実年齢")
    papa = mama = 0
    if c.cflag[9] <= -100:  # :169–180
        for i in range(st.charanum):
            if i == GameState.MASTER or i == arg:
                continue
            if st.charas[i].cflag[240] == c.cflag[9] * -1 - 100:
                papa = i
    if c.cflag[7] > 0:  # :184–194
        for i in range(st.charanum):
            if i == GameState.MASTER or i == arg:
                continue
            if st.charas[i].cflag[240] == c.cflag[7]:
                mama = i
    if papa > 0:
        p = st.charas[papa]
        out.print(f"{Z}実父{Z}:{Z}{p.name} ")
        if p.cflag[34] > 0:
            out.print(f"({p.base[real_age]})")
        incest = func_check_chara_incest(ctx, papa, mama, 1)
        if incest != "":
            out.print(f"{Z * 2}({incest}との近親相姦)")
    elif c.cflag[9] > 0:
        out.print(f"{Z}実父{Z}:{Z}{_father_name(ctx, c.cflag[9])}")
    elif c.cflag[9] == -100:
        out.print(f"{Z}実父{Z}:{Z}誰とも知れない相手")
    out.printl()
    if mama > 0:
        m = st.charas[mama]
        out.print(f"{Z}実母{Z}:{Z}{m.name} ")
        if m.cflag[34] > 0:
            out.print(f"({m.base[real_age]})")
        incest = func_check_chara_incest(ctx, mama, papa, 0)
        if incest != "":
            out.print(f"{Z * 2}({incest}との近親相姦)")
    out.printl()


def func_check_chara_incest(ctx: Ctx, x: int, y: int, x_is_papa: int) -> str:
    """`@FUNC_CHECK_CHARA_INCEST, PARENT_X, PARENT_Y, X_IS_PAPA`:256–311（#FUNCTIONS）。"""
    st = ctx.state
    cx, cy = st.charas[x], st.charas[y]
    ra = _ix(ctx, "BASE", "実年齢")
    elder = (cx.base[ra] == cy.base[ra] and cx.cflag[240] < cy.cflag[240]) or cx.base[ra] > cy.base[ra]
    rel = cx.relation[y]
    g = lambda bit: (rel >> bit) & 1 == 1  # noqa: E731
    s = ""
    if g(OYAKO):
        s += ("娘" if x_is_papa else "息子") if elder else ("母" if x_is_papa else "父")
        if g(KYOUDAI) or g(SOFUBO) or g(OJIOBA) or g(OIMEI):
            s += "/"
    if g(KYOUDAI):
        s += ("妹" if x_is_papa else "弟") if elder else ("姉" if x_is_papa else "兄")
        if g(SOFUBO) or g(OJIOBA) or g(OIMEI):
            s += "/"
    if g(SOFUBO):
        s += "孫" if elder else ("祖母" if x_is_papa else "祖父")
        if g(OJIOBA) or g(OIMEI):
            s += "/"
    if g(OJIOBA):
        s += "おば" if x_is_papa else "おじ"
    elif g(OIMEI):
        s += "姪" if x_is_papa else "甥"
    return s


# --- PAGE5：キャラクタープロフィール ------------------------------------------------------------


def _page5(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_SELECT_PAGE5, ARG`:5–59。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[arg]
    convert_colorcstr(c)  # :8–9
    convert_age(c)
    out.printl(Z * 14 + "キャラクタープロフィール" + Z * 14 + "PAGE(5/5)")
    out.drawline()
    _names_lv(ctx, arg)
    _shortline(ctx)
    _apperance(ctx, arg, sc)
    if c.cflag[34] == 0:  # :21–39
        if st.flag[700] > 0:
            setcolor(out, *GRAY)
        out.printl(Z * 21 + "[20]" + Z + "設定")
    else:
        if sc.trans:
            out.print(Z * 21 + "[10]" + Z + "通常時")
        elif t(ctx, c, "変身能力") > 0:
            out.print(Z * 21 + "[10]" + Z + "変身時")
        out.printl()
        if st.flag[700] > 0:
            setcolor(out, *GRAY)
        out.printl(Z * 21 + "[20]" + Z + "再設定")
    out.reset_color()
    if config_check_maniac(st, 16) == 1 and c.cflag[34] > 0:  # :43–46
        _shortline(ctx)
        # CALL PRINTFORM_GAPING_NOW, ARG, LOCAL：PAGE5 の LOCAL は代入されないので 0（関数の LOCAL は 0 で始まる）
        printform_gaping_now(ctx, arg, 0)
    _shortline(ctx)
    _personality(ctx, arg)
    _sexual_personality(ctx, arg)
    out.printl()
    out.printl()
    out.drawline()


def _cmd_page5(ctx: Ctx, arg: int, cmd: int, sc: _Screen) -> Gen:
    """`@CMD_STATUS_CHARA_SELECT_PAGE5, ARG, INPUT_CMD`:69–87。"""
    st, data = ctx.state, ctx.data
    c = st.charas[arg]
    if cmd == 10 and t(ctx, c, "変身能力") > 0:
        sc.trans ^= 1  # INVERTBIT SHOW_TRANS_STATUS, 0
    elif cmd == 20 and st.flag[700] == 0:  # :73–79 スリーサイズ等設定
        if c.cflag[34] == 0:
            generate_bodyline(st, data, c)
        chara_make_age_setting(st, data, c)
        chara_size_default(data, c, st.result)
        # DEVIATION（表示のみ）：プロフィール設定画面 SIZE_SETTING（CHARA_SIZE_UI.ERB:2–2145）は未移植のため、
        # 何も変えずに [99]「決定して戻る」を押した場合の状態変化だけ行う（deviations「子供加入時的キャラ設定畫面」と同じ扱い）
        size_setting_default(ctx, arg)
    elif cmd == 30 and st.flag[999] > 0:
        c.cflag[35] = 0
    elif cmd == 31 and st.flag[999] > 0:
        c.cflag[36] = 0
    else:
        return 0
    return 1
    yield  # pragma: no cover


def is_revealed_pregnant(ctx: Ctx, who: int) -> int:
    """`@IS_REVEALED_PREGNANT, ARG`:304–308：妊娠（触手・触手人・人）が発覚済みなら 1。"""
    return 1 if t(ctx, ctx.state.charas[who], "妊娠") in (1, 3, 5) else 0


def _apperance(ctx: Ctx, arg: int, sc: _Screen) -> None:
    """`@SHOW_STATUS_CHARA_APPERANCE, ARG`:102–296。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.charas[arg]
    if c.cflag[34] == 0:  # :119–129
        out.print(Z * 9 + "プロフィール未設定")
        for _ in range(12):
            out.printl()
        if config_check_maniac(st, 16) == 0:
            for _ in range(4):
                out.printl()
        return
    tr = sc.trans
    src = c.maxbase if tr else c.base
    if tr:  # :137–168
        out.printl(Z * 11 + "＜＜変身時＞＞")
        body_talent = t(ctx, c, "変身時外見")
        hair, hair_col, eye_r, eye_l, skin = c.cstr[14], c.cstr[31], c.cstr[34], c.cstr[35], c.cstr[37]
    else:
        out.printl(Z * 11 + "＜＜通常時＞＞")
        body_talent = t(ctx, c, "外見")
        hair, hair_col, eye_r, eye_l, skin = c.cstr[13], c.cstr[30], c.cstr[32], c.cstr[33], c.cstr[36]
    age, height, weight, bw = src[AGE], src[HEIGHT], src[WEIGHT], src[BREAST_WEIGHT]
    bust, waist, hip = src[BUST], src[WAIST], src[HIP]
    real = c.base[REAL_AGE]
    CT = lambda n, tr_=None: charatalent(data, c, tr if tr_ is None else tr_, n)  # noqa: E731
    dec = lambda v, w=0: f"{format_curly(div(v, 10), w) if w else div(v, 10)}.{mod(v, 10)}"  # noqa: E731
    out.print(Z + "ヘアスタイル" + Z * 11)  # :171–181
    out.printl(f"{'実' if age != real else Z}年齢：{format_curly(real, 7)} 歳")
    out.print(f"{Z * 4}前髪：{format_percent('『' + c.cstr[12] + '』', 18, True)}")
    if age != real:
        out.print(f"{Z * 3}外見：{format_curly(age, 7)} 歳")
    out.printl()
    out.printl(f"{Z * 4}後髪：{format_percent('『' + hair + '』', 20, True)}{Z * 2}身長：{dec(height, 5)} cm")  # :184–191
    out.print(f"{Z * 19}体重：{dec(weight, 5)} kg")
    if CT("オトコ") == 0:
        out.printl(f"(胸{dec(bw)} kg)")
    else:
        out.printl()
    out.print(Z * 3 + "髪の色：" + Z)  # :194–196
    colorchip(out, hair_col)
    out.printl()
    size, influence = top_under(data, c, tr)  # :198 RETURN サイズ値, 影響値 → RESULT:0〜1
    st.set_result_x(size, influence)
    boob = pregnancy_boob_expand(ctx, arg)
    cup_value, cup_label = cup_size(size + boob)  # :199 RETURN LOCAL → RESULT:0
    st.result[0] = cup_value
    manly = CT("オトコ") > 0 and CT("男の娘") == 0
    if manly:  # :201–213
        out.printl(f"{Z * 19} Ｂ ：{Z}（―）")
    else:
        b = bust + boob
        out.print(f"{Z * 19} Ｂ ：{dec(b, 5)} cm ")
        if is_revealed_pregnant(ctx, arg):
            out.print(f"(+{dec(boob)} cm) ")
        out.print(f"({cup_label})")
        out.printl()
    out.print(f"{Z * 3}目つき：{format_percent('『' + c.cstr[18] + '』', 20, True)}")  # :216–229
    if manly:
        out.printl(f"{Z * 2} Ｗ ：{Z}（―）")
    else:
        belly = pregnancy_belly_expand(ctx, arg)
        out.print(f"{Z * 2} Ｗ ：{dec(waist + belly, 5)} cm ")
        if is_revealed_pregnant(ctx, arg):
            out.print(f"(+{dec(belly)} cm) ")
        out.printl()
    out.print(Z * 4 + "右目：" + Z)  # :232–239
    colorchip(out, eye_r)
    if manly:
        out.printl(f"{Z * 9} Ｈ ：{Z}（―）")
    else:
        out.printl(f"{Z * 9} Ｈ ：{dec(hip, 5)} cm")
    out.print(Z * 4 + "左目：" + Z)  # :242–244
    colorchip(out, eye_l)
    out.printl()
    out.print(Z * 19)  # :249–290
    for name in ("小柄", "長身", "絶壁", "貧乳", "巨乳", "爆乳", "超乳", "魔乳", "奇乳"):
        if CT(name) > 0:
            out.print(f"[{name}]")
    if tr:
        if CT("オトコ", 1) > 0 and CT("オトコ", 0) > 0:
            out.print("[オトコ]")
        if CT("オトコ", 1) > 0 and CT("オトコ", 0) == 0:
            out.print("[男性化]")
        if CT("オトコ", 1) == 0 and CT("オトコ", 0) > 0:
            out.print("[女体化]")
    elif CT("オトコ") > 0:
        out.print("[オトコ]")
    if CT("男の娘") > 0:
        out.print("[男の娘]")
    if CT("ふたなり") > 0:
        out.print("[ふたなり]")
    if t(ctx, c, "妊娠") == 5 and c.cflag[222] < 11:
        out.print("[着床]")
    elif is_revealed_pregnant(ctx, arg):
        out.print("[妊娠]")
    if body_talent:
        out.print(f"[{GAIKEN_NAMES[body_talent]}]")
    out.printl()
    out.print(Z * 3 + "肌の色：" + Z)  # :293–295
    colorchip(out, skin)
    out.printl()


def _personality(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_PERSONALITY, ARG`:314–326。"""
    out = ctx.out
    c = ctx.state.charas[arg]
    if c.cstr[40] != "" or c.cstr[41] != "" or c.cstr[42] != "":
        out.printl(Z + "＊＊＊" + Z + "パーソナリティ ＊＊＊")
    else:
        out.printl()
    for i in range(3):
        if c.cstr[40 + i] != "":
            out.printl(f"{Z * 2}『{c.cstr[40 + i]}』")
        else:
            out.printl()


def _sexual_personality(ctx: Ctx, arg: int) -> None:
    """`@SHOW_STATUS_CHARA_SEXUAL_PERSONALITY, ARG`:332–354（:340 の SETCOLOR 末尾の `,` は引数 3 個として解釈される：
    reference/emuera-1824/Emuera/GameData/Expression/ExpressionParser.cs@ReduceArguments:63–116）。"""
    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    if config_check_other(st, 6) == 1 and any(c.cstr[45 + i] != "" for i in range(4)):
        _shortline(ctx)
        out.printl(Z + "＊＊＊" + Z + "裏パーソナリティ ＊＊＊")
        n = 0
        for i in range(4):
            if c.cstr[45 + i] != "":
                lv = limit(c.abl[i], 0, 10)
                setcolor(out, 255, 255 - 23 * lv, 255 - 11 * lv)
                out.print(f"{Z * 2}『{c.cstr[45 + i]}")
                out.printl("♥" * limit(div(c.abl[i], 2), 0, 5) + "』")
                out.reset_color()
                n += 1
        for _ in range(4 - n):
            out.printl()
    else:
        for _ in range(6):
            out.printl()


_PAGES = {1: _page1, 2: _page2, 3: _page3, 4: _page4, 5: _page5}
_CMDS = {1: _cmd_page1, 2: _cmd_page2, 3: _cmd_page3, 4: _cmd_page4, 5: _cmd_page5}
