"""武器自訂；原文路徑皆相對 ERB/武器と衣装/武器カスタマイズ関連/。

WEAPON_CUSTOMIZE.ERB 與 WEAPON_NAME.ERB 手翻。
"""

from .input_request import TextInputRequest, input_number, inputs
from .era import cp932_len, format_percent
from .weapon_customize_text import TEXT
from . import weapon_words
from .action import Ctx
from collections.abc import Generator

Menu = Generator[None | TextInputRequest, int | str, int]


def _byte_len(text: str) -> int:
    # LangManager.cs:17–20；.NET CP932 每個不可編碼 UTF-16 單元各回落一個 '?'。
    raw = text.encode("utf-16-le", errors="surrogatepass")
    return sum(
        cp932_len(raw[i : i + 2].decode("utf-16-le", errors="surrogatepass"))
        for i in range(0, len(raw), 2)
    )


def _number(ctx):
    value = yield from input_number(ctx)
    ctx.out.printl(str(value))
    return value


def _wait(ctx):
    # reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734。
    ctx.out.printl("（按 Enter 繼續）")
    yield TextInputRequest()
    ctx.out.clearline(1)


def _return(ctx, value=0):
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023。
    ctx.state.result[0] = value
    return value


def customize(ctx: Ctx, who: int) -> Menu:
    """WEAPON_CUSTOMIZE.ERB@WEAPON_CUSTOMIZE:8–80。"""
    from .status_screen import set_fstyle_info, _shortline
    from .shop import lb
    from .battle.core import fstyle_name
    from .battle.hantei import fstyle_attack

    st, out = ctx.state, ctx.out
    c = st.charas[who]
    while True:
        lb(out)
        out.printl(TEXT[14][1])
        out.printl()
        out.printl(c.name + "　の現在の装備")
        for dist in range(1, 4):
            _shortline(ctx)
            out.printl("◆" + ("近", "中", "遠")[dist - 1] + "距離武器")
            out.printl(
                f"├[{dist*10}]武器名 "
                + (
                    "『" + c.cstr[dist + 4] + "』"
                    if c.cstr[dist + 4]
                    else "（設定されていません）"
                )
            )
            out.reset_color()
            power = fstyle_attack(ctx, who, dist, 1)
            st.result[0] = power
            out.printl(
                f"└[{dist*10+2}]戦闘スタイル　<<{fstyle_name(ctx,who,dist)}>>"
                + " " * 20
            )
            set_fstyle_info(ctx, who, dist)
            st.result[0] = 0  # SET_FSTYLE_INFO:164 RETURN。
            out.printl(f"　　　　　---> 威力　　　：【{power}】（ {st.results[0]} ）")
            for i in (1, 2):
                out.printl("　　　　　---> " + st.results[i])
        out.drawline()
        out.printl(" [999]戻る")
        r = yield from _number(ctx)
        if r == 999:
            return _return(ctx)
        if r in (10, 20, 30):
            yield from setting_weapon_name(ctx, who, r // 10)
        elif r in (12, 22, 32):
            yield from setting_fstyle(ctx, who, r // 10)


def setting_fstyle(ctx: Ctx, who: int, dist: int) -> Menu:
    """WEAPON_CUSTOMIZE.ERB@SETTING_FSTYLE:209–259；即時寫入、無資源消耗。"""
    from .battle.core import fstyle_name

    out = ctx.out
    out.printl(("近", "中", "遠")[dist - 1] + "距離武器の戦闘スタイルを選んでください")
    out.printl("現在のスタイル：<<" + fstyle_name(ctx, who, dist) + ">>")
    for line, (command, text) in TEXT.items():
        if 219 <= line <= 242:
            out.printl(text)
    while True:
        r = yield from _number(ctx)
        if 0 <= r <= 10:
            out.clearline(1)
            ctx.state.charas[who].cdflag[
                dist, ctx.data.index_of("CDFLAG2", "戦闘スタイル")
            ] = r
            return _return(ctx)
        if r == 999:
            return _return(ctx)


def setting_weapon_name(ctx: Ctx, who: int, dist: int) -> Menu:
    """WEAPON_CUSTOMIZE.ERB@SETTING_WEAPON_NAME:85–206。"""
    st, out = ctx.state, ctx.out
    c = st.charas[who]
    while True:
        out.printl(("近", "中", "遠")[dist - 1] + "距離武器の名前を決めてください")
        out.printl(
            "現在の武器名："
            + (
                "『" + c.cstr[dist + 4] + "』"
                if c.cstr[dist + 4]
                else "（武器名が設定されていません）"
            )
        )
        out.printl()
        out.printl(" [0]自分で入力する")
        out.printl(" [1]ランダム生成機能を使う")
        if not c.cstr[dist + 4]:
            out.set_color((96, 96, 96))
        out.printl(" [" + ("2" if c.cstr[dist + 4] else "-") + "]追加文字列の設定")
        out.reset_color()
        out.printl(" [3]消去する")
        for source in range(1, 4):
            if source != dist and c.cstr[source + 4]:
                out.printl(
                    f" [{source+3}]"
                    + ("近", "中", "遠")[source - 1]
                    + "距離と同じ銘　『"
                    + c.cstr[source + 4]
                    + "』"
                )
        out.printl(" [999]戻る")
        while True:
            r = yield from _number(ctx)
            if (
                r in (0, 1, 3, 999)
                or r == 2
                and c.cstr[dist + 4]
                or 4 <= r <= 6
                and r - 3 != dist
                and c.cstr[r + 1]
            ):
                break
        if r == 999:
            return _return(ctx)
        if 4 <= r <= 6:
            c.cstr[dist + 4] = c.cstr[r + 1]
            c.cdflag[dist, 300] = c.cdflag[r - 3, 300]
            return _return(ctx)
        out.clearline(1)
        if r == 0:
            from .status_screen import _shortline

            out.printl()
            _shortline(ctx)
            out.printl(
                ("近", "中", "遠")[dist - 1]
                + "距離武器に設定する名前を入力してください："
            )
            c.cstr[dist + 4] = yield from inputs(ctx)
            c.cdflag[dist, 300] = 0
        elif r == 1:
            if (yield from generate_names(ctx, 20)):
                c.cstr[dist + 4] = st.results[0]
            c.cdflag[dist, 300] = 0  # 取消也清除，原作 :150。
        elif r == 2:
            value = yield from add_strings(ctx, who, dist)
            if value:
                c.cstr[dist + 4] = st.results[0]
                c.cdflag[dist, 300] = value
        else:
            c.cstr[dist + 4] = ""
            c.cdflag[dist, 300] = 0
            out.printl("武器名を消去しました")
            out.printl()
            yield from _wait(ctx)


def generate_names(ctx: Ctx, count: int = 20) -> Menu:
    """WEAPON_NAME.ERB@GENERATE_WEAPON_STRS:4–139；keep 為 static，重入保留。"""
    st, out = ctx.state, ctx.out
    count = max(1, min(50, count))
    key = "GENERATE_WEAPON_STRS:"
    mem = st.temp.locals
    keep = [mem.get((key + "KEEP_STR", i), "") for i in range(10)]
    kept = mem.get((key + "KEEP_VAR", 0), 0)
    mode = "kana"
    refresh = True
    names = []
    out.printl("　　　　　生成文字列　　　　　　　　　　　　　　キープ")
    while True:
        if refresh:
            names = []
            for _ in range(count):
                st.results.clear()
                if mode == "kana" or mode == "random" and st.rng.rand(2):
                    weapon_words.kana(ctx)
                else:
                    weapon_words.japanese(ctx)
                names.append(
                    st.results[0]
                    + (" <" + st.results[1] + ">" if st.results[1] else "")
                )
        for i in range(max(count, 10)):
            out.print(
                (
                    f"　[{i:2}] " + format_percent(names[i], 32, True) + " "
                    if i < count
                    else " " * 40
                )
            )
            if i < count:
                out.button("→ ", i + 300)
            if i < 10:
                out.print(
                    f"[{i+50}] " + format_percent(keep[i], 32, True) + f" [{i+60}] 削除"
                    if keep[i]
                    else "[--]　―――"
                )
            if i == count - 3:
                out.print(" [110]カナ名　　" + ("☑" if mode == "kana" else "☐"))
            if i == count - 2:
                out.print(" [120]和名　　　" + ("☑" if mode == "japanese" else "☐"))
            if i == count - 1:
                out.print(" [130]ランダム　" + ("☑" if mode == "random" else "☐"))
            out.printl()
        out.printl()
        out.printl(" [100]再生成")
        out.drawline()
        out.printl(" [999]戻る")
        r = yield from _number(ctx)
        refresh = False
        if r == 999:
            st.results[0] = ""
            return _return(ctx)
        if r in (100, 110, 120, 130):
            if r != 100:
                mode = {110: "kana", 120: "japanese", 130: "random"}[r]
            refresh = True
        elif 0 <= r < count or 50 <= r < 60:
            chosen = names[r] if r < count else keep[r - 50]
            out.printl()
            out.printl(chosen)
            out.printl("　")
            yield from _wait(ctx)
            st.results[0] = chosen
            out.clearline(3)
            return _return(ctx, 1)
        elif 300 <= r < count + 300:
            if kept < 10:
                keep[kept] = names[r - 300]
                kept += 1
            else:
                keep = keep[1:] + [names[r - 300]]
        elif 60 <= r < kept + 60:
            keep = keep[: r % 10] + keep[r % 10 + 1 :] + [""]
            kept -= 1
        for i, v in enumerate(keep):
            mem[key + "KEEP_STR", i] = v
        mem[key + "KEEP_VAR", 0] = kept
        out.clearline(max(count, 10) + 5)


def _substring(text: str, start: int, length: int) -> str:
    # reference/emuera-1824/Emuera/_Library/LangManager.cs:40–85：CP932 位移向右取整。
    if start >= _byte_len(text) or length == 0:
        return ""
    if length < 0 or length > _byte_len(text):
        length = _byte_len(text)
    raw = text.encode("utf-16-le", errors="surrogatepass")
    units = [
        raw[i : i + 2].decode("utf-16-le", errors="surrogatepass")
        for i in range(0, len(raw), 2)
    ]
    i = 0
    used = 0
    while i < len(units) and used < start:
        used += cp932_len(units[i])
        i += 1
    result = ""
    used = 0
    while i < len(units) and used < length:
        result += units[i]
        used += cp932_len(units[i])
        i += 1
    return result.encode("utf-16-le", errors="surrogatepass").decode(
        "utf-16-le", errors="surrogatepass"
    )


def add_strings(ctx: Ctx, who: int, dist: int) -> Menu:
    """WEAPON_NAME.ERB@WEAPON_ADD_STRS:141–527；設定暫存跨呼叫保留。"""
    from .battle.core import fstyle_name

    st, out = ctx.state, ctx.out
    c = st.charas[who]
    key = "WEAPON_ADD_STRS:"
    mem = st.temp.locals
    options = [mem.get((key + "INS_VAR", i), 0) for i in range(7)]
    custom = mem.get((key + "SELF_CL", 0), "")
    original = c.cstr[dist + 4]
    code = c.cdflag[dist, 300]
    if code:
        original = _substring(original, code // 100, code % 100)
        st.results[0] = original
    parts = original.split(" <")
    st.result[0] = len(parts)
    # Process.ScriptProc.cs:522–536：RESULT 寫完整筆數，輸出陣列只保留容量內項目。
    base = parts[0]
    reading = (" <" + parts[1]) if len(parts) > 1 and parts[1] else ""
    out.printl()
    out.printl(
        f"　　武器名：{base}{reading}　　　　戦闘スタイル：{fstyle_name(ctx,who,dist)}"
    )
    labels = [
        ["あり", "なし"],
        ["なし", "接頭語", "接尾語"],
        ["なし", "半角( )", "全角(　)", "中黒(・)"],
        ["なし", '""', "「」"],
        ["なし", "火", "氷", "雷", "水", "風", "地", "毒", "光", "闇"],
        [
            "なし",
            "剣",
            "刀",
            "槍",
            "斧",
            "槌",
            "拳",
            "爪",
            "棍",
            "杖",
            "鎌",
            "鞭",
            "鋼糸",
            "鎖鋸",
            "杭槍",
            "弓",
            "銃",
            "砲",
            "符",
            "珠",
            "自由入力",
        ],
        ["斬", "打", "突", "射", "術"],
    ]
    headings = ["読み", "追加文字列", "区切り", "強調", "属性", "武器種", "攻撃属性"]
    generated = False
    # LOCAL／LOCALS 按函式保留（VariableData.cs:328–333、514–520）。
    # 入口僅覆寫 LOCALS:0；不合法但被原作接受的選項可能讀到其他格殘值。
    prefix = original
    sep, left, right, suffix = [
        mem.get((key + name, 0), "") for name in ("sep", "left", "right", "suffix")
    ]
    while True:
        if not generated:
            for row, items in enumerate(labels):
                out.printl("<<" + headings[row] + ">>")
                for i, label in enumerate(items):
                    chosen = (
                        bool(options[6] & (1 << i)) if row == 6 else options[row] == i
                    )
                    if chosen:
                        out.set_color((128, 255, 128))
                    if (
                        row == 0
                        and not reading
                        or row in (2, 3)
                        and options[1] != 1
                        or row in (4, 5, 6)
                        and options[1] == 0
                    ):
                        out.set_color((128, 128, 128))
                    out.print(
                        f"[{row*10+(20 if row==6 else 0)+i:2}]"
                        + label
                        + ("☑" if chosen else "☐")
                        + (
                            "（" + custom + "）"
                            if row == 5 and i == 20 and custom
                            else ""
                        )
                        + "　"
                    )
                    out.reset_color()
                    if i % 4 == 3:
                        out.printl()
                out.printl()
            out.printl(" [100]生成　 [200]リセット")
            out.drawline()
            out.printl(" [999]戻る")
            r = yield from _number(ctx)
            if r == 70:
                options[5] = 20
                out.printl(
                    "武器の種類を入力してください（１〜２文字程度のものにすることを推奨します）"
                )
                custom = yield from inputs(ctx)
                if not custom:
                    options[5] = 0
                out.clearline(1)
            elif 0 <= r < 60:
                options[r // 10] = r % 10
            elif 60 <= r < 70:
                options[5] = r - 50
            elif 80 <= r < 85:
                options[6] ^= 1 << (r - 80)
            elif r == 100:
                generated = True
            elif r == 200:
                options = [0] * 7
            elif r == 999:
                return _return(ctx)
            if 50 <= r <= 70:
                options[6] = [
                    0,
                    1,
                    1,
                    4,
                    3,
                    2,
                    6,
                    3,
                    2,
                    18,
                    17,
                    2,
                    1,
                    1,
                    6,
                    8,
                    8,
                    10,
                    16,
                    16,
                    0,
                ][options[5]]
            for i, v in enumerate(options):
                mem[key + "INS_VAR", i] = v
            mem[key + "SELF_CL", 0] = custom
            if not generated:
                out.clearline(27)
                continue
        names = []
        codes = []
        for _ in range(10):
            # 無效選項保留 LOCALS 先前值；有效選項依原作覆寫。
            if 0 <= options[2] <= 3:
                sep = ["", " ", "　", "・"][options[2]]
            if 0 <= options[3] <= 2:
                left, right = [("", ""), ('"', '"'), ("「", "」")][options[3]]
            word = weapon_words.addition(
                ctx,
                c.cdflag[dist, ctx.data.index_of("CDFLAG2", "戦闘スタイル")],
                options[1],
                options[4],
                options[5],
                options[6],
                custom,
            )
            if options[1] == 0:
                prefix = suffix = ""
            elif options[1] == 1:
                prefix = word
                suffix = ""
            elif options[1] == 2:
                prefix = sep = left = right = ""
                suffix = "の" + word
            lead = prefix + sep + left
            middle = base + (reading if options[0] == 0 else "")
            tail = right + suffix
            codes.append(_byte_len(lead) * 100 + _byte_len(middle))
            names.append(lead + middle + tail)
            st.result[0] = _byte_len(tail)
            for name, value in (
                ("sep", sep),
                ("left", left),
                ("right", right),
                ("suffix", suffix),
            ):
                mem[key + name, 0] = value
            out.printl(f"　 [{109+len(names)}] " + names[-1])
        out.printl()
        out.printl(" [100]再生成　　[200]設定変更")
        out.drawline()
        out.printl(" [999]戻る")
        r = yield from _number(ctx)
        if r == 200:
            generated = False
            out.clearline(42)
        elif 110 <= r < 120:
            st.results[0] = names[r - 110]
            return _return(ctx, codes[r - 110])
        elif r == 999:
            return _return(ctx)
        else:
            out.clearline(15)
