"""コンフィグ（設定画面）とグローバルデータ（GLOBAL）の翻寫。路徑相對 `source/earGVP/ERB/`。

- `config_init`：`SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`:4–61（プリセット 0〜3）。
- `update_global`／`update`：`バージョン間互換処理.ERB@UPDATE_GLOBAL`:12–91、`@UPDATE`:95–128（GLOBAL 部分）。
- `config_gen`：`SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG`:68–513。
- `config_f_gen`／`config_m_gen`／`config_t_gen`：`CONFIG_GLOBAL_MANIAC.ERB@CONFIG_F`:52–205、
  `CONFIG_GLOBAL_MOB.ERB@CONFIG_M`:6–201、`CONFIG_GLOBAL_TRANSFORM.ERB@CONFIG_T`:22–146。
- `heroine_preset_gen`：`ゲーム内_イベント発生/オープニング処理.ERB@HEROINE_PRESET`:617–759。

INPUT 待ちは `value = yield`（session が数値を send する）。グローバル変数は `GlobalStore`
（`eragvt.state.savefile`：メモリ `mem` と SAVEGLOBAL／LOADGLOBAL）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..data.csv_loader import GameData
from ..state import GameState
from ..state.savefile import GlobalStore
from ..text import TextOutput
from .era import div, format_curly, format_percent

Gen = Generator[None, int, None]

# SETCOLOR の値（CONFIG_SYSTEM.ERB 各行）
ON = (120, 255, 255)
OFF = (105, 105, 105)
GRAY = "#808080"  # SETCOLORBYNAME Gray（.NET Color.Gray）
CYAN = "#00ffff"  # SETCOLORBYNAME CYAN（.NET Color.Cyan）

MOB_CATEGORY = 10  # DIM.ERH:168 `#DIM CONST MOB_CATEGORY = 10`
# `@TENTACLE_MOB_{n}`（中身は空）と `@TENTACLE_MOB_{n}_GETNAME` の RESULTS
# （ゲーム内_戦闘処理/触手データ/雑魚敵/TENTACLE_MOB_{n}_*.ERB の GETNAME 行。RESULTS = の右辺そのまま）。
MOB_NAMES: dict[int, str] = {
    1: "触手幼体の群れ",
    2: "ペネトレイトボール ",
    3: "ニップルスラグの群れ",
    101: "ぷるぷるスライム",
    102: "ぷるぷるスライム・アス",
    201: "バイタリティバルブ ",
    301: "クリスターフィッシュ",
    501: "擬態触手・クズ市民",
    601: "発情ウサギ",
    701: "チキチキ蜂 ",
    702: "アナルリーチ",
    801: "カージャッカー ",
    802: "中継ドローン ",
    803: "メカ触手",
    901: "セラプー",
    902: "妖精の群れ",
}
# CONFIG_GLOBAL_MOB.ERB:12–22 `#DIMS 種族,10`
MOB_RACES = ("無形", "スライム", "植物", "水棲系", "---", "ヒト型", "動物系", "虫", "物質", "天使・悪魔系")
# DIM.ERH:283 `#DIMS CONST transnamegenre`
TRANSNAMEGENRE = ("マジカル的な単語", "天体の名前", "色の名前", "果物、野菜など植物の名前", "雑多な英単語", "宝石の名前",
                  "人を示す単語", "武器の名前", "ランダム")


def mob_exists(n: int) -> bool:
    """`TRYCCALLFORM TENTACLE_MOB_{n}` が CATCH に行かないか（関数が存在するか）。"""
    return n in MOB_NAMES


def mob_getname(state: GameState, n: int) -> str:
    """`TRYCALLFORM TENTACLE_MOB_{n}_GETNAME` の RESULTS。901 だけ TFLAG:17 を書き換える
    （TENTACLE_MOB_901_天界（セラプー）.ERB:9–13）。"""
    if n == 901 and state.tflag[17] in (3, 5):
        state.tflag[17] = -1
    return MOB_NAMES[n]


def lb(out: TextOutput) -> None:
    """`CALL LB`（shop.lb。opening → config → shop → opening の循環 import を避けて遅延 import）。"""
    from .shop import lb as shop_lb

    shop_lb(out)


def _invertbit(arr, index: int, bit: int) -> None:
    arr[index] = arr[index] ^ (1 << bit)


# --- CONFIG_INIT ----------------------------------------------------------------

# CONFIG_初期設定.ERB:17–59（FLAG:800〜805）
PRESETS: dict[int, tuple[int, int, int, int, int, int]] = {
    1: (0, 1, 1 + 2 + 4 + 8, 1 + 2 + 4 + 256, 1, 2),
    2: (0, 1 + 8 + 16, 1 + 2 + 4 + 8 + 16, 1 + 2 + 4 + 128 + 256, 1 + 2 + 4 + 16 + 32 + 64 + 128, 1 + 2 + 64),
    3: (0, 1 + 8 + 16, 1 + 2 + 4 + 8 + 16 + 32, 1 + 2 + 4 + 128 + 256, 1 + 2 + 4 + 16 + 32 + 64 + 128 + 1024, 1 + 2 + 64),
}


def config_init(state: GameState, preset: int, store: GlobalStore | None = None) -> None:
    """`CONFIG_INIT(ARG)`:4–61。CASE 0 はメモリ上の GLOBAL:11〜15 を写す（LOADGLOBAL はしない）。
    該当 CASE が無い ARG は何もしない（SELECTCASE に CASEELSE が無い）。"""
    f = state.flag
    if preset == 0:
        g = (store.mem if store is not None else None)
        f[800] = 1
        for i in range(5):
            f[801 + i] = g.global_[11 + i] if g is not None else 0
        return
    if preset not in PRESETS:
        return
    for i, v in enumerate(PRESETS[preset]):
        f[800 + i] = v


# --- UPDATE_GLOBAL / UPDATE -----------------------------------------------------


def update_global(state: GameState, store: GlobalStore, out: TextOutput, version: int) -> None:
    """`バージョン間互換処理.ERB@UPDATE_GLOBAL`:12–91（GLOBAL:3 = グローバルデータのバージョン）。"""
    g = store.mem.global_
    gs = store.mem.globals_
    mg = store.mem.mob_global
    if g[3] < 364:
        g[9] = 0
    if g[3] < 371:
        state.mob_flag[(0, 1)] = 100
        mg[(0, 1)] = 100
    if g[3] < 380:
        g[0] = 0
        g[1] = 0
        g[2] = 0
        g[10] = 0
        g[11] = 4
        g[12] = 31
        g[13] = 88
        g[14] = 5
    if g[3] < 390:
        _invertbit(g, 4, 16)
        _invertbit(g, 4, 17)
    if g[3] < 398:
        g[15] = 0
        g[16] = 0
    if g[3] < 400:
        for i in range(111, 171):  # FOR LOCAL,111,171
            g[i + 100] = g[i]
            g[i] = 0
        g[113] = g[110]
        g[110] = 0
    if g[3] < 404:
        for b in (7, 8, 9, 11, 12, 19, 20):
            _invertbit(g, 4, b)
    if g[3] < 406:
        for i in range(0, 9):  # FOR LOCAL,0,9
            if gs[18] == TRANSNAMEGENRE[i]:
                g[8] = i + 1
                break
        gs[18] = ""
    if g[3] < 408:
        if g[20] == 8:
            g[20] += 1
    if g[3] < version:
        out.printl("【グローバル設定を最新バージョンにアップデートしました】")
        g[3] = version
        store.save()


def update_global_part(state: GameState, store: GlobalStore, out: TextOutput, version: int) -> None:
    """`@UPDATE`:95–128 のグローバルデータ管理（先頭の PRINTL を含む）。LASTLOAD_VERSION 以降（:131–）は呼び出し側。"""
    out.printl()  # :97
    if not store.load():  # :99–100
        return
    update_global(state, store, out, version)  # :102
    g = store.mem.global_
    if state.flag.get_bit(800, 0) > 0:  # :105 CONFIG_CHECK_MAIN_F(0)
        if g[0] + g[1] + g[2] != 0:
            out.printw("【グローバルデータからコンフィグ設定を読み込みました】")
        for i in range(5):
            state.flag[801 + i] = g[11 + i]
    state.flag[850] = g[4]  # :115
    for cat in range(MOB_CATEGORY):  # :117–125
        for j in range(100):
            if mob_exists(cat * 100 + j):
                state.mob_flag[(cat, j)] = store.mem.mob_global[(cat, j)]
            else:
                state.mob_flag[(cat, j)] = 0


def update(state: GameState, store: GlobalStore, out: TextOutput, version: int) -> None:
    """`@UPDATE`:95–846。LASTLOAD_VERSION が -1（新規ゲーム）または現行版（408）のときの経路：
    :131 以降の分岐はすべて不成立（`LASTLOAD_VERSION < n`、n ≦ 408）→ 末尾の PRINTL（:846）だけ。"""
    update_global_part(state, store, out, version)
    llv = state.temp.last_load_version
    if llv != -1 and llv < version:
        raise NotImplementedError("GameBase バージョン 408 以外のセーブの更新処理は未移植")
    out.printl()  # :846


# --- CONFIG（CONFIG_SYSTEM.ERB:68–513）------------------------------------------


def _bit(state: GameState, flag: int, n: int) -> int:
    return state.flag.get_bit(flag, n)


def _item(out: TextOutput, on: int, text: str) -> None:
    """`SETCOLOR 120,255,255` → `SIF 判定 == 0 : SETCOLOR 105,105,105` → `PRINTFORML`。"""
    out.set_color(ON)
    if on == 0:
        out.set_color(OFF)
    out.printl(text)


def _show_config(state: GameState, out: TextOutput, page: int, from_: str) -> None:
    f = state.flag
    lb(out)  # :78 CALL LB
    out.set_bold(True)
    out.set_color((255, 200, 50))
    out.print("Ｃ　Ｏ　Ｎ　Ｆ　Ｉ　Ｇ")
    out.set_bold(False)
    out.reset_color()
    out.print(f"　　　　　　　page({page + 1}/2)")
    out.printl()
    out.drawline()
    sc = lambda n: _bit(state, 801, n)  # noqa: E731
    ev = lambda n: _bit(state, 802, n)  # noqa: E731
    ba = lambda n: _bit(state, 803, n)  # noqa: E731
    pr = lambda n: _bit(state, 804, n)  # noqa: E731
    ot = lambda n: _bit(state, 805, n)  # noqa: E731
    if page == 0:  # :87–212
        out.print("★")
        out.set_color((255, 255, 150))
        out.printl("グローバルフィルタ（全セーブデータ共通、グローバル環境に自動上書き）")
        out.reset_color()
        out.printl("　[1000]性嗜好フィルタ")
        out.printl("　[2000]雑魚敵フィルタ")
        out.printl("　[3000]非戦闘行動時の自動変身")
        out.printl()
        out.drawline()
        out.print("★")
        out.set_color((255, 255, 150))
        out.printl("コンフィグ関係（セーブデータ個別に設定）")
        _item(out, _bit(state, 800, 0), "　[0]グローバル環境のコンフィグ設定を使用する")
        out.reset_color()
        out.printl("　[1]SAVE GLOBAL (グローバル環境に手動でセーブ)")
        out.printl("　[2]LOAD GLOBAL (グローバル環境から手動ロード)")
        out.print("　●")
        out.set_color((255, 120, 60))
        out.printl("画面表示関係")
        _item(out, sc(0), "　[10]素質をカテゴリ分けして表示する")
        _item(out, sc(1), "　[11]戦闘中に調教ステータスの上昇を表示する")
        _item(out, sc(2), "　[12]戦闘中のコマンドをカテゴリ分けして表示する")
        _item(out, sc(3), "　[13]一部ウェイトの削減")
        _item(out, sc(4), "　[14]「未熟」消去後に代替素質を表示する")
        out.reset_color()
        _item(out, sc(5), f"　[15]{'▼' if sc(5) == 0 else '▲'}戦闘画面に調教ステータスの一覧を表示する")
        out.reset_color()
        if sc(5) == 1:
            _item(out, sc(6), "　 ┣[16]表示位置を下部に移動")
            out.reset_color()
            _item(out, sc(7), "　 ┗[17]表示位置を可変にする")
            out.reset_color()
        out.print("　●")
        out.set_color((255, 120, 120))
        out.printl("イベント関連")
        _item(out, ev(0), "　[30]ボス触手の襲撃")
        _item(out, ev(1), "　[31]子触手の夜這い")
        _item(out, ev(2), "　[32]仲間による夜這い")
        _item(out, ev(3), "　[33]クズ市民イベント")
        _item(out, ev(4), "　[34]雑魚敵との戦闘")
        out.reset_color()
        _item(out, ev(5), "　[35]クズ市民との戦闘")
        out.reset_color()
        _item(out, ev(6), "　[36]恋人セックス時のゴム装着")
        out.reset_color()
        out.printl()
        out.printl()
        if sc(5) == 0:
            out.printl()
            out.printl()
    elif page == 1:  # :213–414
        out.print("★")
        out.set_color((255, 255, 150))
        out.printl("コンフィグ関係（続き）")
        out.print("　●")  # 色は 255,255,150 のまま（RESETCOLOR なし）
        out.set_color((120, 60, 255))
        out.printl("ゲームバランス変更")
        _item(out, ba(0), "　[50]捕獲触手遭遇率アップを使用する　　　　難易度：低下")
        _item(out, ba(1), "　[51]索敵ターゲットを使用する　　　　　　　難易度：低下")
        _item(out, ba(2), "　[52]オート振り解き機能を使用する　　　　　難易度：低下")
        _item(out, ba(3), "　[53]搾精強化機能を使用する　　　　　　　　難易度：低下")
        _item(out, ba(4), "　[54]ボス触手撃破で返り血　　　　　　　　　難易度：上昇")
        _item(out, ba(5), "　[55]ラスボス強化機能　　　　　　　　　　　難易度：上昇")
        _item(out, ba(6), "　[56]集中が乱れても変身を維持する　　　　　難易度：低下（大）")
        _item(out, ba(7), "　[57]Ａ感覚が低い時の快Ａ増加　　　　　　　難易度：上昇")
        _item(out, ba(8), "　[58]行動不能のヒロインを敵が正確に狙う　　難易度：上昇")
        out.reset_color()
        out.printl()
        out.print("　●")
        out.set_color((60, 255, 120))
        out.printl("幽閉・悪堕ち関連オプション")
        _item(out, pr(0), "　[60]オトコの敗北時に女体化させる")
        _item(out, pr(1), f"　[61]{'▼' if pr(1) == 0 else '▲'}ヒロイン悪堕ち機能を使用する")
        if pr(1) == 1:
            _item(out, pr(2), "　 ┣[62]ただし苗床化したヒロインは産む機械として取り込む")
            _item(out, pr(3), "　 ┣[63]ただし嬲られ体質を持たない戦闘員だけが悪堕ちする")
            _item(out, pr(4), f"　 ┣[64]{'▼' if pr(4) == 0 else '▲'}悪堕ち時に容姿を変更する")
            out.reset_color()
            if pr(4) == 1:
                for n, text in ((5, "　　 ┣[65]髪型の変更を許可する"), (6, "　　 ┣[66]髪の色の変更を許可する"),
                                (7, "　　 ┣[67]目の色の変更を許可する"), (8, "　　 ┗[68]肌の色の変更を許可する")):
                    _item(out, pr(n), text)
                    out.reset_color()
            _item(out, pr(9), "　 ┗[69]【触手の虜】無しでも洗脳ではなく悪堕ちする")
        _item(out, pr(10), "　[70]クズ市民による幽閉を許可する")
        _item(out, pr(11), "　[71]悪堕ちヒロインを倒しても正気に戻らない")
        out.reset_color()
        out.printl()
        out.print("　●")
        out.set_color((60, 255, 120))
        out.printl("その他オプション")
        _item(out, ot(0), "　[72]触手の子種からも娘を妊娠する可能性がある")
        _item(out, ot(1), "　[73]ギブアップコマンドを使用する")
        _item(out, ot(2), "　[74]┏妊娠出産機能を封印する")
        _item(out, ot(3), "　[75]┗避妊のためにアフターピルを使用する")
        _item(out, ot(4), "　[76]Ａ責め攻撃では常に後ろの穴にのみ挿入する")
        out.reset_color()
        _item(out, ot(5), "　[77]ヒロインが常に聖処女となる（基本的に処女を喪失しない）")
        out.reset_color()
        _item(out, ot(6), "　[78]プロフィール設定時に裏プロフィールも使用する")
        out.reset_color()
        _item(out, ot(7), "　[79]FLASH NEWSにバイラルメディア(有害ブログ)を追加する")
        out.reset_color()
        _item(out, ot(8), "　[80]強制衣装変更イベントでも設定通りの衣装を使う")
        out.reset_color()
        if pr(1) == 0:
            for _ in range(8):
                out.printl()
        elif pr(4) == 0:
            for _ in range(4):
                out.printl()
    out.printl()  # :415
    out.printl("[100]ページ切り替え")
    if from_ != "mainmenu":
        out.print("[999]現在のセーブデータのみに適用して戻る　　")
        out.printl("[9999]グローバル設定に保存して戻る")


def _flags_to_global(state: GameState, store: GlobalStore) -> None:
    for i in range(5):
        store.mem.global_[11 + i] = state.flag[801 + i]


def config_gen(state: GameState, data: GameData, out: TextOutput, store: GlobalStore, from_: str = "") -> Gen:
    """`CONFIG_SYSTEM.ERB@CONFIG(FROM)`:68–513。`[999]`／`[9999]` は FROM が "mainmenu" でも表示しないだけで受け付ける。"""
    f = state.flag
    version = _version(data)
    page = 0
    while True:  # $MASTER_LOOP
        _show_config(state, out, page, from_)
        while True:  # $INPUT_LOOP
            r = yield
            if r == 100:
                page = 1 if page == 0 else 0
                break
            if r == 999:
                return
            if r == 9999:
                _flags_to_global(state, store)
                store.save()
                return
            if r == 0:
                _invertbit(f, 800, 0)
                break
            if r == 1:
                _flags_to_global(state, store)
                store.save()
                out.printl("現在のグローバルコンフィグを保存しました。")
                out.printl("ゲームをロードするたびに自動で適用されます。")
                out.printw()
                break
            if r == 2:
                out.printw("【グローバルコンフィグ設定を読み込みました】")
                for i in range(5):
                    f[801 + i] = store.mem.global_[11 + i]
                update_global(state, store, out, version)
                break
            if r == 1000:
                yield from config_f_gen(state, out, store)
                break
            if r == 2000:
                yield from config_m_gen(state, out, store)
                break
            if r == 3000:
                yield from config_t_gen(state, out, store)
                break
            if 10 <= r <= 17:
                _invertbit(f, 801, r - 10)
                break
            if 30 <= r <= 34:
                _invertbit(f, 802, r - 30)
                if _bit(state, 802, 3) == 0:
                    f.set_bit(802, 5, False)
                break
            if r == 35:
                if _bit(state, 802, 3) == 1:
                    _invertbit(f, 802, r - 30)
                break
            if r == 36:
                _invertbit(f, 802, r - 30)
                break
            if 50 <= r <= 58:
                _invertbit(f, 803, r - 50)
                break
            if 60 <= r <= 71:
                _invertbit(f, 804, r - 60)
                break
            if r in (74, 75):  # 常時避妊／アフターピルは択一（:500–504）
                _invertbit(f, 805, r - 72)
                f.set_bit(805, 2 + (75 - r), False)
                break
            if 72 <= r <= 80:
                _invertbit(f, 805, r - 72)
                break
            out.printl()
            out.printl("正しい値を入力してください")


def _version(data: GameData) -> int:
    """GAMEBASE_VERSION（GameBase.csv バージョン、本作 408）。"""
    from ..state.savefile import GameIdentity

    return GameIdentity.from_data(data).version


# --- CONFIG_F（性嗜好フィルタ）------------------------------------------------------


def config_check_maniac(state: GameState, n: int) -> int:
    """`CONFIG_CHECK_MANIAC,ARG`／`CONFIG_CHECK_MANIAC_F(ARG)`：1 - GETBIT(FLAG:850, ARG)（:32–47）。"""
    return 1 - state.flag.get_bit(850, n)


def _maniac(out: TextOutput, on: int, text: str) -> None:
    out.set_color(ON)
    if on == 0:
        out.set_color(OFF)
    out.printl(text + ("【○】" if on else "【×】"))


def config_f_gen(state: GameState, out: TextOutput, store: GlobalStore) -> Gen:
    """`CONFIG_GLOBAL_MANIAC.ERB@CONFIG_F`:52–205。"""
    start = out.linecount
    m = lambda n: config_check_maniac(state, n)  # noqa: E731
    while True:  # $MASTER_LOOP
        out.printl()
        out.drawline()
        out.printl("性嗜好フィルタ　×にした要素はゲーム中に登場しなくなります")
        out.printl()
        _maniac(out, m(1), "[11]ふたなりの取得　　　　　　　　　")
        _maniac(out, m(2), "[12]母乳体質の取得　　　　　　　　　")
        _maniac(out, m(3), "[13]寄生の取得　　　　　　　　　　　")
        _maniac(out, m(4), "[14]出産時の合いの子(異形)描写　　　")
        out.set_color(ON)
        if m(5) == 0:
            out.set_color(OFF)
        out.printl("[15]男女平等(オトコも犯される)　　　" + ("【○】" if m(5) else "【×】") + "　※♀と男の娘は常に被姦対象です")
        _maniac(out, m(6), f"[16]{'▲' if m(6) == 1 else '▼'}淫紋の取得　　　　　　　　　　")
        if m(6) == 1:
            _maniac(out, m(7), "[17]┣複数個所の取得　　　　　　　　")
            _maniac(out, m(8), "[18]┣複雑化　　　　　　　　　　　　")
            out.set_color(ON)
            if m(9) == 0:
                out.set_color(OFF)
            out.printl("[19]┣救出後も浸食が進む　　　　　　" + ("【○】" if m(9) else "【×】") + "　")
            _maniac(out, m(10), "[20]┣進行が汚染度と連動する　　　　")
            _maniac(out, m(11), "[21]┣対応フォントの使用　　　　　　")
            _maniac(out, m(12), "[22]┗Wingdingsの使用　　 　　　　　")
        _maniac(out, m(13), "[23]寄生陥落キャラによる触手責め　　")
        _maniac(out, m(14), "[24]残酷/ハードな描写 　　　　　　　")
        _maniac(out, m(15), "[25]スカトロ系描写 　 　　　　　　　")
        _maniac(out, m(16), f"[26]{'▲' if m(16) == 1 else '▼'}拡張度の表示　  　　　　　　　")
        if m(16) == 1:
            _maniac(out, m(17), "[27]┣極端な拡張　　　　　　　　　　")
            _maniac(out, m(20), "[30]┗極端な太さの触手　　　　　　　")
        _maniac(out, m(18), f"[28]{'▲' if m(18) == 1 else '▼'}膨乳の取得   　 　　　　　　　")
        if m(18) == 1:
            _maniac(out, m(19), "[29]┗極端な膨乳　　　　　　　　　　")
        out.reset_color()
        out.printl()
        if m(6) == 0:
            for _ in range(6):
                out.printl()
        if m(16) == 0:
            for _ in range(2):
                out.printl()
        if m(18) == 0:
            out.printl()
        out.printl("[200]変更を保存して戻る")
        out.printl()
        while True:  # $INPUT_LOOP
            r = yield
            if 11 <= r <= 31:
                _invertbit(state.flag, 850, r - 10)
                # :193–196（原文どおり：[22] で立てると bit 1（ふたなり）を消す）
                if state.flag.get_bit(850, r - 10) and r == 21:
                    state.flag.set_bit(850, 12, False)
                if state.flag.get_bit(850, r - 10) and r == 22:
                    state.flag.set_bit(850, 1, False)
                out.clearline(out.linecount - start)
                break
            if r == 200:
                store.mem.global_[4] = state.flag[850]
                store.save()
                return


# --- CONFIG_M（雑魚敵フィルタ）------------------------------------------------------


def _set_category(state: GameState, cat: int, value: int) -> None:
    for j in range(100):
        if mob_exists(cat * 100 + j):
            state.mob_flag[(cat, j)] = value


def config_m_gen(state: GameState, out: TextOutput, store: GlobalStore) -> Gen:
    """`CONFIG_GLOBAL_MOB.ERB@CONFIG_M`:6–201。"""
    lcount0 = out.linecount
    while True:  # $MASTER_LOOP
        lb(out)
        out.drawline()
        out.printl("雑魚敵出現フィルタ　カテゴリを選択してください")
        out.printl("※全雑魚0%時は戦闘処理が省略されます")
        out.printl()
        for cat in range(MOB_CATEGORY):
            n = 0
            total = 0
            for j in range(100):
                if mob_exists(cat * 100 + j):
                    n += 1
                    total += state.mob_flag[(cat, j)]
            if n == 0 or div(total, n) == 0:
                out.set_color(GRAY)
            out.printl(f"[{cat}]{format_percent(MOB_RACES[cat], 16, True)}　[{cat + 10}]0％　[{cat + 20}]100％")
            out.reset_color()
        out.printl()
        out.printl("[101]全カテゴリの雑魚出現率を全て0％に設定する")
        out.printl("[102]全カテゴリの雑魚出現率を全て100％に設定する")
        out.printl("[200]変更を保存して戻る")
        while True:  # $INPUT_LOOP
            r = yield
            if 0 <= r <= 9 and r != 4:
                yield from _config_m_category(state, out, r)
                out.clearline(out.linecount - lcount0)
                break
            if 10 <= r <= 19:
                _set_category(state, r - 10, 0)
                out.clearline(out.linecount - lcount0)
                break
            if 20 <= r <= 29:
                _set_category(state, r - 20, 100)
                out.clearline(out.linecount - lcount0)
                break
            if r in (101, 102):
                for cat in range(MOB_CATEGORY):
                    _set_category(state, cat, 0 if r == 101 else 100)
                out.clearline(out.linecount - lcount0)
                break
            if r == 200:
                for cat in range(MOB_CATEGORY):
                    for j in range(100):
                        store.mem.mob_global[(cat, j)] = state.mob_flag[(cat, j)]
                store.save()
                return


def _config_m_category(state: GameState, out: TextOutput, cat: int) -> Gen:
    """CONFIG_M:56–147（カテゴリ内の個別設定。[200] で MASTER_LOOP に戻る）。"""
    page = 1
    lcount1 = out.linecount
    while True:  # $LOOP_0
        out.drawline()
        out.printl(f"雑魚敵出現フィルタ　PAGE({page}/5)　　　　　　　　　　　　　　　　出現率")
        out.printl()
        for i in range(1, 21):
            sel = (page - 1) * 20 + i
            if mob_exists(cat * 100 + sel):
                name = mob_getname(state, cat * 100 + sel)
                out.print(f"[{format_curly(sel, 3)}] {format_percent(name, 56, True)}　{state.mob_flag[(cat, sel)]}％")
            else:
                out.print(" ---")  # `PRINT  ---`：命令直後の 1 文字だけ区切り（GameProc/LogicalLineParser.cs:437）
            out.printl()
        out.printl()
        out.print("このカテゴリの全出現率を ")
        out.print_plain("　　　")
        out.print("[101]0％にする ")
        out.print_plain("　　　　")
        out.print("[102]100％にする")
        out.printl()
        out.print("[200]戻る　　　")
        out.print_plain("　　　　　　　　")
        if page >= 2:
            out.print("[201]前のページ")
        else:
            out.print("　　　　　　　 ")
        out.print_plain("　　　　")
        if page <= 4:
            out.print("[202]次のページ")
        else:
            out.print("　　　　　　　 ")
        out.printl()
        while True:  # $INPUT_LOOP_0
            r = yield
            sel = r
            if sel not in (101, 102, 201, 202, 200) and not mob_exists(cat * 100 + sel):
                sel = -1
            if (page - 1) * 20 + 1 <= sel <= (page - 1) * 20 + 20:
                name = mob_getname(state, cat * 100 + sel)
                out.printl(f"{name}の出現率を入力してください （  0 - 100 ％）")
                while True:  # $INPUT_LOOP_1
                    v = yield
                    if 0 <= v <= 100:
                        state.mob_flag[(cat, sel)] = v
                        break
                out.clearline(out.linecount - lcount1)
                break
            if r in (101, 102):
                _set_category(state, cat, 0 if r == 101 else 100)
                out.clearline(out.linecount - lcount1)
                break
            if r == 200:
                return
            if r == 201 and page >= 2:
                page -= 1
                out.clearline(out.linecount - lcount1)
                break
            if r == 202 and page <= 4:
                page += 1
                out.clearline(out.linecount - lcount1)
                break


# --- CONFIG_T（非戦闘行動時の自動変身）---------------------------------------------

_T_HEADINGS = ((1, "特別活動時の変身設定"), (4, "情報収集時の変身設定"), (7, "息抜きの変身設定"))
_T_KINDS = ("通常の変身の場合　　　　　　    ", "変身時に女体化する場合          ", "変身時に男性化する場合          ")


def config_t_gen(state: GameState, out: TextOutput, store: GlobalStore) -> Gen:
    """`CONFIG_GLOBAL_TRANSFORM.ERB@CONFIG_T`:22–146（GLOBAL:51〜59 は代入値 0／1／2）。"""
    start = out.linecount
    option = [0] * 10
    for i in range(1, 10):
        option[i] = store.mem.global_[i + 50]
    while True:  # $MASTER_LOOP
        out.printl()
        out.drawline()
        out.printl("ここで変身設定を指定しておくことで、変身するかどうかの選択肢を省略することができます。")
        out.printl()
        for first, heading in _T_HEADINGS:
            out.printl(heading)
            out.printl()
            for k in range(3):
                i = first + k
                out.print(f"　[{10 + i}]{_T_KINDS[k]}【")
                if option[i] == 1:
                    out.print("常に変身する")
                elif option[i] == 2:
                    out.print("常に変身しない")
                else:
                    out.print("選択肢を表示する")
                out.printl("】")
            out.printl()
        out.printl("[200]変更を保存して戻る")
        out.printl()
        while True:  # $INPUT_LOOP
            r = yield
            if 10 < r < 20:
                i = r - 10
                option[i] = 2 if option[i] == 1 else 0 if option[i] == 2 else 1
                out.clearline(out.linecount - start)
                break
            if r == 200:
                for i in range(1, 10):
                    store.mem.global_[i + 50] = option[i]
                store.save()
                return


# --- HEROINE_PRESET（オープニング処理.ERB:617–759）---------------------------------


def heroine_preset_gen(state: GameState, data: GameData, out: TextOutput, store: GlobalStore) -> Gen:
    """`@HEROINE_PRESET`:617–759。[0]〜[3] で CONFIG_INIT(選択) して終了。"""
    while True:  # $INPUT_LOOP_CON_HEAD
        out.printl()
        out.printl()
        out.printl()
        out.drawline()
        out.printl()
        out.set_bold(True)
        out.set_color(CYAN)
        out.printl("◆ヒロインデータ確認")
        out.set_bold(False)
        out.reset_color()
        for i in range(1, state.charanum):
            c = state.charas[i]
            alias = f"《{c.cstr[0]}》" if c.cstr[0] != "" and c.cstr[0] != c.callname else ""
            out.printl(f"　[{19 + i}]●{format_percent(c.name, 20, True)} {alias}")
        if state.charanum >= 2:
            out.printl(" [30]ヒロインに相関関係を設定する")
        out.printl(" ")
        out.printl(" ")
        out.set_bold(True)
        out.set_color(CYAN)
        out.printl("◆ゲーム開始　（※コンフィグは開始後も個別変更できます）")
        out.set_bold(False)
        out.reset_color()
        out.printl("　★周回プレイヤー向け")
        out.printl("　[0]グローバルコンフィグを引き継いで開始")
        out.printl("　　┗[10]編集")
        out.printl(" ")
        out.printl("　★新規プレイヤー向けコンフィグセット")
        out.printl("　┣[1]「基本セット」　　で開始　：初期から存在した「少女 vs 触手」に要素を絞り込みます")
        out.printl("　┣[2]「淫獄セット」　　で開始　：雑魚敵との戦闘やヒロイン悪堕ち等の追加オプションがONになります")
        out.printl("　┗[3]「クズ市民セット」で開始　：クズ市民が活性化、治安悪化時の監禁やレイプ戦闘が発生します")
        out.printl(" ")
        while True:  # $INPUT_LOOP_CON
            r = yield
            if r == 10:
                yield from config_gen(state, data, out, store, "mainmenu")
                break
            if 20 <= r <= 29:
                raise NotImplementedError("ヒロインデータ確認（SHOW_STATUS_CHARA_SELECT）は未移植")
            if r == 30 and state.charanum >= 2:
                raise NotImplementedError("相関関係設定（CONVERT_RELATION／SET_RELATION）は未移植")
            if r < 0 or r > 3:
                continue
            config_init(state, r, store)  # :756–758
            return
