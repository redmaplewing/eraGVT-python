"""スケジュール（S28a）：`ゲーム内_行動実行処理/ACTIONsub_SCHEDULE.ERB` の `@SCHEDULE`（SHOP [160]）と `@RES_SCHEDULE`。

路徑相對 `source/earGVP/ERB/`。CFLAG:110〜113（鍛錬・特別活動・情報収集・自由行動）の符号化：
`|CFLAG| = SC_ACTION * 10^18 + Σ SC_ITEM[k] * 100^k`（k = 0〜8、項目番号は 1 始まり、0 は空き）、負ならスケジュール OFF
（:432–442 で書き、:35–53 で読む）。行動側は CFLAG > 0 のときだけ `RES_SCHEDULE` で「次の項目番号 - 1」を取り出す
（鍛錬 `ACTION_TRAINING.ERB`:66–71、情報収集 `ACTION_GATHER_INFORMATION.ERB`:25–64；特別活動・自由行動は S28b／S28c）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state.character import Character
from .era import div, format_curly, format_percent, mod, power

E18 = 1000000000000000000
_YELLOW = (255, 255, 0)
_BLACK = (0, 0, 0)
_GRAY = (96, 96, 96)
_NBSP = " "
LINENUM = 8  # :24 項目一覧の最大行数


def res_schedule(c: Character, arg: int, arg1: int = -1) -> int:
    """`@RES_SCHEDULE, ARG, ARG:1 = -1`:453–495（CFLAG は TARGET＝`c`）。戻り値 = SC_RES（項目番号 - 1）。

    `STRLENFORM {SC_VAR:1}` は桁数（数字は 1 バイト：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@STRLEN_Instruction`:504–528）、
    `POWER` は `era.power`。ARG:1 を指定すると実行番号を上書きして参照だけ（CFLAG は変えない）。
    """
    v0 = div(c.cflag[arg], E18)  # :463
    v1 = mod(c.cflag[arg], E18)  # :464
    if arg1 != -1:  # :465–467
        v0 = arg1
    n = len(str(v1))  # :469–470
    if n % 2 == 1:  # :472–474
        n += 1
    n = div(n, 2)
    res = mod(div(c.cflag[arg], power(100, v0)), 100) - 1  # :476
    if arg1 == -1:  # :478–480
        c.cflag[arg] = mod(c.cflag[arg], E18)
    v0 += 1  # :481–487
    if v0 > 8:
        v0 = 0
    if v0 > n - 1:
        v0 = 0
    v0 *= E18  # :489
    if arg1 == -1:  # :491–493
        c.cflag[arg] += v0
    return res


def _items(ctx, mode: int, lost: int) -> tuple[int, list[int], list[str]]:
    """:69–227 各モードの ITEM_NUM・IT_FLAG・SC_STR（TARGET の素質等で使用可否）。"""
    from .battle.core import is_hole
    from .chara_common import talent

    st, data = ctx.state, ctx.data
    c = st.target_chara
    t = lambda n: talent(data, c, n)  # noqa: E731
    a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    flags = [0] * 100
    strs = [""] * 100
    if mode == 0:  # :71–110
        strs[:11] = ["走り込み", "精神鍛錬", "瞑想", "筋トレ ", "自衛訓練", "ダッシュ", "近距離戦闘訓練", "中距離戦闘訓練",
                     "遠距離戦闘訓練", "戦術研究", "戦闘基礎訓練"]
        for k in (0, 1, 2, 3, 4, 5, 9):
            flags[k] = 1
        henshin = t("変身能力")
        for k in (6, 7, 8):
            flags[k] = 1 if henshin != -1 else 0
        flags[10] = 1 if henshin == -1 else 0
        return 11, flags, strs
    if mode == 1:  # :113–157
        hole = is_hole(ctx)
        ex = c.exp[data.index_of("EXP", "出産経験")]
        strs[:8] = ["アルバイト", "研究所で検査協力" if (ex > 0 or t("妊娠") in (1, 3)) else "研究所助手", "雑魚触手退治",
                    "援助交際", "AV出演", "公衆便所", "アイドル活動", "枕営業"]
        flags[0] = flags[1] = flags[2] = flags[6] = 1
        if a("欲望") > 0 and hole:
            flags[3] = 1
        if (a("欲望") + a("露出癖") >= 5 or c.cflag[283] >= 10) and hole:
            flags[4] = 1
        if a("欲望") + a("マゾっ気") >= 5 and hole:
            flags[5] = 1
        if c.exp[data.index_of("EXP", "魅了経験")] > 99 and hole:
            flags[7] = 1
        return 9, flags, strs
    if mode == 2:  # :160–178
        strs[:4] = ["噂話の聞き込み", "事件の捜査", "情報を買う", "仲間の捜索"]
        flags[0] = flags[1] = 1
        if c.cflag[122] > 0:
            flags[2] = 1
        if lost > 0:
            flags[3] = 1
        return 4, flags, strs
    # :181–227 自由行動
    strs[:21] = ["学校に通う", "ランダムお出かけ", "ランダム(街)", "ランダム(遠出)", "ランダム(運動)", "街：アミューズメント施設",
                 "街：繁華街", "街：ショッピングモール", "街：公園", "遠：動物園", "遠：水族館", "遠：遊園地", "遠：植物園", "遠：ライブ",
                 "遠：ウォーターパーク", "遠：海辺", "遠：温泉", "運：運動公園", "運：フィットネスクラブ", "運：マッサージサロン", "運：プール"]
    for k in range(21):
        flags[k] = 1
    return 21, flags, strs


def schedule_gen(ctx) -> Generator[None, int, None]:
    """`@SCHEDULE`:3–449（SHOP [160]、TARGET のスケジュールを編集する画面）。

    画面の再描画は原作の `CLEARLINE 24/26 + …`（:400、:447：描いた行数＋入力エコー 1 行）と同じく、`$INPUT_LOOP`（モード変更は
    見出しから）以降に出力した行を消す（Python の出力には入力エコー行が無いので行数で数える）。
    """
    from .gather import lost_count

    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    lost = lost_count(st)  # :29
    out.drawline()  # :31–32（REDRAW 0 は表示の更新抑止のみ）
    sc_flag = [0] * 10
    sc_limit = [0] * 10
    sc_action = [0] * 10
    sc_item = [[0] * 12 for _ in range(10)]
    for m in range(4):  # :35–53
        now = c.cflag[m + 110]
        if now < 0:
            sc_flag[m] = 0
            now = abs(now)
        else:
            sc_flag[m] = 1
        sc_limit[m] = 0
        for k in range(9):
            if mod(now, 100) > 0:
                sc_limit[m] = k
            sc_item[m][k] = mod(now, 100)
            now = div(now, 100)
        if sc_item[m][0] != 0:
            sc_limit[m] += 1
        sc_action[m] = now
    mode = 0  # :55–59
    if c.cflag[100] == 104:
        mode = 1
    if c.cflag[100] == 107:
        mode = 2
    now_input = (sc_limit[mode] + 11) * 10  # :61
    while True:  # $CHANGE_MODE
        item_num, it_flag, sc_str = _items(ctx, mode, lost)
        start = out.linecount
        out.print(f" {c.callname} ")  # :231–240
        out.printl(("の鍛錬スケジュール設定", "の特別活動スケジュール設定", "の情報収集スケジュール設定",
                    "の自由行動スケジュール設定")[mode])
        out.drawline()
        while True:  # $INPUT_LOOP
            loop_start = out.linecount
            # :246–259 正規化
            sc_limit[mode] = min(max(sc_limit[mode], 0), 10)
            now_input = min(max(now_input, 110), 190)
            if sc_action[mode] > sc_limit[mode]:
                sc_action[mode] = sc_limit[mode]
            if sc_item[mode][sc_action[mode]] == 0:
                sc_action[mode] -= 1
            if sc_action[mode] < 0:
                sc_action[mode] = 0
            _draw(ctx, mode, now_input, sc_limit[mode], sc_item[mode], item_num, it_flag, sc_str, sc_flag[mode])
            r = yield  # :394 INPUT
            if 200 <= r < 204:  # :397–401 モード変更
                mode = r - 200
                now_input = (sc_limit[mode] + 11) * 10
                out.clearline(out.linecount - start)
                break
            if r == 99:  # :403–413 項目削除（未設定項目を削除しても SC_LIMIT は減らない）
                base = div(now_input, 10) - 11
                if sc_item[mode][base] != 0:
                    sc_limit[mode] -= 1
                for k in range(21 - div(now_input, 10)):
                    if k > 8:
                        sc_item[mode][base + k] = 0
                    else:
                        sc_item[mode][base + k] = sc_item[mode][base + k + 1]
            elif 0 < r < item_num + 1 and it_flag[r - 1] > 0:  # :415–420 項目入力
                base = div(now_input, 10) - 11
                if sc_item[mode][base] == 0:
                    sc_limit[mode] += 1
                sc_item[mode][base] = r
                now_input += 10
            elif 100 < r < 200 and r % 10 == 0:  # :422–423 入力箇所変更
                now_input = r
            elif r == 997:  # :425–426 INVERTBIT SC_FLAG:SC_MODE, 0
                sc_flag[mode] ^= 1
            elif r == 998:  # :428–429 キャンセル
                return
            elif r == 999:  # :431–443 決定
                for m in range(4):
                    v = 0
                    for k in range(9):
                        v = v * 100 + sc_item[m][8 - k]
                    v += sc_action[m] * E18
                    if sc_flag[m] == 0:
                        v = -v
                    c.cflag[m + 110] = v
                return
            out.clearline(out.linecount - loop_start)  # :447


def _draw(ctx, mode, now_input, limit, items, item_num, it_flag, sc_str, flag) -> None:
    """:261–392 の表示。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    box_top = "┏" + "━" * 12 + "┓"
    box_bottom = "┗" + "━" * 12 + "┛"
    sel = lambda m: "►" if mode == m else _NBSP  # noqa: E731

    def colored(text: str, color) -> None:
        out.set_color(color)
        out.print(text)
        out.reset_color()

    colored("　" * 5 + box_top, _YELLOW if now_input == 110 else _BLACK)  # :261–265
    out.print_plain("　" * 11)
    out.set_color(_YELLOW) if mode == 0 else None
    out.printl(f"{sel(0)} [200] 鍛錬")
    out.reset_color()
    bn = data.names["BASE"]
    mb = c.maxbase
    for k in range(9):  # :273–368
        gray = k > limit
        if gray:
            out.set_color(_GRAY)
        out.print("　[" + ("---" if gray else str((k + 11) * 10)) + "] ")
        out.reset_color()
        cur = now_input == (k + 11) * 10
        colored("　" + ("┃" if cur else "　"), _YELLOW)
        if gray:
            out.set_color(_GRAY)
        out.print(format_percent(sc_str[items[k] - 1], 24, True) if items[k] > 0 else "　―――　　　　　　　　")
        out.reset_color()
        colored(("┃" if cur else "　") + ("◄" if limit == k else _NBSP), _YELLOW)
        if k == 0:
            out.print_plain("　" * 10 + " ")
            out.set_color(_YELLOW) if mode == 1 else None
            out.print(f"{sel(1)} [201] 特別活動")
            out.reset_color()
        if k == 1:
            out.print_plain("　" * 10 + " ")
            out.set_color(_YELLOW) if mode == 3 else None
            out.print(f"{sel(3)} [203] 自由行動")
            out.reset_color()
        out.print_plain("　")
        if k == 3:
            out.print("　" * 10 + " " + format_percent(bn.get(1, ""), 6, True) + "：" + format_curly(mb[1], 6))
        if k == 5:
            out.print("　" * 10 + " " + format_percent(bn.get(11, ""), 6, True) + "：" + format_curly(mb[11], 6))
        if k == 6:
            out.print("　" * 10 + " " + format_percent(bn.get(13, ""), 6, True) + "：" + format_curly(mb[13], 6))
        if k == 8:
            out.print_plain("　  実行できない場合は休憩になります")
        out.printl()
        nxt = now_input == (k + 11) * 10 or now_input == (k + 12) * 10  # :324–328
        colored("　" * 5 + (box_bottom if now_input == (k + 11) * 10 else box_top), _YELLOW if nxt else _BLACK)
        if k == 0:
            out.print_plain("　" * 10 + " ")
            out.set_color(_YELLOW) if mode == 2 else None
            out.print(f"{sel(2)}  [202] 情報収集")
            out.reset_color()
        if k == 2:
            out.print("　" * 12 + format_percent(bn.get(0, ""), 6, True) + "：" + format_curly(mb[0], 6))
        if k == 3:
            out.print("　" * 12 + format_percent(bn.get(2, ""), 6, True) + "：" + format_curly(mb[2], 6))
        if k == 4:
            out.print("　" * 12 + format_percent(bn.get(10, ""), 6, True) + "：" + format_curly(mb[10], 6))
        if k == 5:
            out.print("　" * 12 + format_percent(bn.get(12, ""), 6, True) + "：" + format_curly(mb[12], 6))
        if k == 6:
            a = lambda n: c.abl[data.index_of("ABL", n)]  # noqa: E731
            out.print("　" * 8 + f"近LV：{a('近距離')} 　中LV：{a('中距離')} 　遠LV：{a('遠距離')}")
        if k == 7:
            out.print_plain("　　※ 行動時、上から順に繰り返し実行されます")
        out.printl()
    out.drawline()  # :369
    for k in range(item_num):  # :371–380
        if it_flag[k] == 0:
            out.set_color(_GRAY)
        out.print("[" + (format_curly(k + 1, 2) if it_flag[k] else "―") + "]"
                  + (format_percent(sc_str[k], 20, True) if it_flag[k] else "　――　　　　　　　"))
        out.reset_color()
        out.print_plain(" ")
        if k % 3 == 2 and k > 0:
            out.printl()
    if item_num % 3 != 0:  # :381–382
        out.printl()
    for _ in range(LINENUM - div(item_num + 2, 3)):  # :384–386
        out.printl()
    out.printl("[99]項目削除　　　　　　")
    out.drawline()
    out.print("[999] 決定　[998] キャンセル")  # :390–392
    out.print_plain(" 　　　　　　 　　　　")
    out.printl("[997] スケジュール機能 - " + ("ON" if flag else "OFF"))
