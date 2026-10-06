"""手翻 SYSTEM/キャラメイキング関連/FIRSTSETTING_RANDOMNAMING.ERB。

候選詞直接讀既有 CSV STR，不另手寫詞庫。所有 RAND 順序與原文一致。
"""
from .input_request import input_number
from .era import cp932_len, format_percent


GENRES = ("マジカル的な単語", "天体の名前", "色の名前", "果物、野菜など植物の名前",
          "雑多な英単語", "宝石の名前", "人を示す単語", "武器の名前", "ランダム")


def _word(ctx, index):
    return ctx.data.str_defaults.get(index, "")


def _draw(ctx, genre):
    # @FIRSTSETTING_RANDOMNAMING_ALL:154–214／@FIRSTSETTING_RANDOMNAMING_SELECT:315–382
    if genre == 8:
        genre = ctx.state.rng.rand(8)
    while True:
        index = 500 + genre * 100 + ctx.state.rng.rand(50)
        if _word(ctx, index):
            return index


def _genres(out):
    for i, name in enumerate(GENRES):
        out.printl(f"[{i:2}] {name}")
    out.printl("[99] もどる")


def random_naming_all(ctx):
    """@FIRSTSETTING_RANDOMNAMING_ALL:3–273：20組、keep、統一、反轉與ジャンル。

    #DIM 預設static：reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27。
    函式開頭只重設兩個genre；keep及固定編號跨呼叫保留，DA為共用存檔陣列。
    """
    st, out = ctx.state, ctx.out
    mem = st.temp.locals
    def key(name, index=0):
        return ("FIRSTSETTING_RANDOMNAMING_ALL:" + name, index)
    def get(name, index=0):
        return mem.get(key(name, index), 0)
    def put(name, value, index=0):
        mem[key(name, index)] = value
    for _ in range(50):
        out.printl()
    # PRINT_LINE.ERB@LB:18 RETURN RESULT，保留原值。
    line = len(out.lines)
    genres = [8, 8]
    regenerate = True
    while True:
        if regenerate:
            for i in range(20):
                if get("keep", i) == 1:
                    continue
                for side in range(2):
                    fixed = get("fixed", side)
                    st.da[side, i] = fixed if fixed > 0 else _draw(ctx, genres[side])
        for i in range(20):
            upper, lower = _word(ctx, st.da[0, i]), _word(ctx, st.da[1, i])
            out.print(f"[{i:2}] " + upper + format_percent(lower, 26 - cp932_len(upper), True) + "　")
            if get("keep", i) == 1:
                out.set_color((255, 255, 8))
                out.print(f"[{i + 1000}] ★キープ ")
                out.reset_color()
                st.result[0] = 0  # SETCOLOR_BY_STR 終端
            else:
                out.print(f"[{i + 1000}] ☆キープ ")
            out.print(f"　[{i + 2000}] 上の句統一 ")
            out.printl(f"　[{i + 3000}] 下の句統一 ")
        out.printl()
        out.printl("[100]ジャンルを絞り込む　　　　　[300] 上の句・下の句の反転")
        out.printl("[200]再生成")
        while True:
            r = yield from input_number(ctx)
            if 0 <= r < 20:
                return r
            if r in (100, 200, 300) or 1000 <= r <= 1019 or 2000 <= r <= 2019 or 3000 <= r <= 3019:
                break
        out.clearline(len(out.lines) - line)
        regenerate = False
        if r in (100, 200):
            put("fixed", 0, 0)
            put("fixed", 0, 1)
            regenerate = True
            if r == 100:
                side = 0
                while True:
                    out.set_bold(side == 0)
                    out.printl("　上の句：" + GENRES[genres[0]])
                    out.set_bold(side == 1)
                    out.printl("　下の句：" + GENRES[genres[1]])
                    out.set_bold(False)
                    out.printl(("上" if side == 0 else "下") + "の句のジャンルを選択してください")
                    _genres(out)
                    out.printl()
                    out.printl("[100] " + ("下" if side == 0 else "上") + "の句変更")
                    out.printl("[200] 生成")
                    while True:
                        r = yield from input_number(ctx)
                        if 0 <= r <= 8 or r in (99, 100, 200):
                            break
                    if r == 99:
                        return 99
                    out.clearline(len(out.lines) - line)
                    if r == 200:
                        break
                    if r == 100:
                        side = 1 - side
                    else:
                        genres[side] = r
        elif r == 300:
            for i in range(20):
                if not get("keep", i):
                    st.da[0, i], st.da[1, i] = st.da[1, i], st.da[0, i]
        elif 1000 <= r <= 1019:
            put("keep", 1 - get("keep", r - 1000), r - 1000)
        else:
            side = 0 if r < 3000 else 1
            put("fixed", st.da[side, r - (2000 if side == 0 else 3000)], side)
            put("fixed", 0, 1 - side)
            regenerate = True


def random_naming(ctx, who, prefix):
    """@FIRSTSETTING_RANDOMNAMING:278–303：RETURN genre,select-result 或 99,0。"""
    out, st = ctx.out, ctx.state
    out.printl("ジャンルを選択してください")
    _genres(out)
    while True:
        genre = yield from input_number(ctx)
        if genre == 99:
            st.result[0], st.result[1] = 99, 0
            return
        if 0 <= genre <= 8:
            break
    result = yield from random_naming_select(ctx, genre, who, prefix)
    st.result[0], st.result[1] = genre, result


def random_naming_select(ctx, genre, who, prefix):
    """@FIRSTSETTING_RANDOMNAMING_SELECT:310–463；800/801只改順序，不重抽。"""
    out, st = ctx.out, ctx.state
    out.printl()
    # LOCAL保留跨呼叫值：VariableToken.cs:1712–1737；Process.State.cs:456–483不清LOCAL。
    side_key = ("FIRSTSETTING_RANDOMNAMING_SELECT:LOCAL", 21)
    side = st.temp.locals.get(side_key, 0)
    regenerate = True
    while True:
        if regenerate:
            words = []
            # @FIRSTSETTING_RANDOMNAMING_SELECT:314–384，REPEAT20。
            for i in range(20):
                st.count[0] = i
                words.append(_draw(ctx, genre))
            st.count[0] = 20
        for i, index in enumerate(words):
            st.count[0] = i  # :390–400，顯示同樣以共用COUNT跑20次。
            word = _word(ctx, index)
            out.printl(f"[{i:2}] " + (prefix + word if side == 0 else word + prefix))
        st.count[0] = 20
        out.printl()
        out.print("[100] ジャンルから選びなおす")
        if prefix:
            out.print("　　　　　[800] ")
            out.set_bold(side == 0)
            out.print(f" {prefix} ＋ 単語 の順")
            out.set_bold(False)
        out.printl()
        out.print("[200] 再生成")
        if prefix:
            out.print("　　　　　　　　　　　　　[801] ")
            out.set_bold(side == 1)
            out.print(f" 単語 ＋ {prefix} の順")
            out.set_bold(False)
        out.printl()
        while True:
            r = yield from input_number(ctx)
            if 0 <= r < 20:
                word = _word(ctx, words[r])
                st.results[0] = prefix + word if side == 0 else word + prefix
                st.charas[who].cstr[202] = word
                st.result[0] = 0
                return 0
            if r == 100:
                st.result[0] = 1
                return 1
            if r in (200, 800, 801):
                break
        out.clearline(24)
        regenerate = r == 200
        if not regenerate:
            side = r - 800
            st.temp.locals[side_key] = side
