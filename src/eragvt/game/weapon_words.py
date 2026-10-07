"""武器命名演算法手翻；原文路徑皆相對 ERB/武器と衣装/武器カスタマイズ関連/。

固定詞表見 weapon_customize_text（每列附原文行號）。
"""

from .weapon_customize_text import KANA, JAPANESE, ADD_WORDS
from .action import Ctx


def kana(ctx: Ctx) -> str:
    """GENERATE_WEAPON_STR.ERB@GENERATE_WEAPON_STR:31–2089。"""
    st = ctx.state
    rand = st.rng.rand
    length = rand(2) + 2
    selected = [0] * 3
    name = ""
    now = 0
    key = ("GENERATE_WEAPON_STR:PRO_VAR", 0)
    pro = st.temp.locals.get(key, 0)  # 入口沒有清除 PRO_VAR。
    counted_key = ("GENERATE_WEAPON_STR:COUNTED", 0)
    if not st.temp.locals.get(counted_key, 0) or st.flag[999]:
        pro = 0  # 首次／偵錯重數詞條的空轉輪會清除 PRO_VAR。
    st.temp.locals[counted_key] = 1
    while now < length:
        permit = 4 if now == 0 else 1 if now == length - 1 else 2
        previous = pro
        pro = 0
        for index, (mask, words, ban, zero) in enumerate(KANA):
            number = len(KANA) - index
            # 原作 RAND 在 SELECTED_NO 檢查之前，即使本輪已選中仍消耗亂數。
            if (
                permit & mask
                and not previous & ban
                and rand(number) == 0
                and not selected[now]
                and number not in selected
            ):
                if len(words) == 1:
                    add = words[0]
                elif len(words) == 2:
                    r = rand(2)
                    add = words[0 if (r == 0 if zero else r != 0) else 1]
                else:
                    for n in range(6, 1, -1):
                        r = rand(n)
                        if r == 0 if n > 2 else r != 0:
                            add = words[6 - n]
                            break
                    else:
                        add = words[-1]
                selected[now] = number
        if not selected[now]:
            continue
        for char, bit, n in [("ー", 1, 3), ("ッ", 2, 4), ("ン", 4, 2), ("ヴ", 8, 3)]:
            st.result[0] = add.find(char)
            if st.result[0] >= 0 and rand(n):
                pro |= bit
        if pro & previous:
            selected[now] = 0
            continue
        st.result[0] = len(add)
        if length > 2 and len(add) > sum(rand(10) == 0 for _ in range(3)) + 2:
            selected[now] = 0
            continue
        end = add[-1:]
        add = add[:-1]
        if rand(5) == 0 and now > 0 and end in ("ン", "ー"):
            end = add[-1:]
            add = add[:-1]
        first = name[:1]
        name = name[1:]
        if end == first or end == "ン" and first == "ム":
            first = ""
        elif end in ("ッ", "ン") and first in ("ッ", "ン"):
            end = "ン" if rand(2) else "ッ"
            first = ""
        elif end in ("ッ", "ー") and first in ("ッ", "ー"):
            end = "ー" if rand(2) else "ッ"
            first = ""
        elif end == "ン" and first == "ー":
            end = "ー" if rand(2) else "ン"
            first = ""
        elif end in ("ア", "イ", "ウ", "エ", "オ") and first == "ー":
            if rand(2):
                end = ""
            else:
                first = ""
        name = add + end + first + name
        now += 1
    st.temp.locals[key] = pro
    st.results[0] = name
    st.result[0] = 0
    return name


def _jp_forms(row, now, rand):
    """原作詞條的濁音／數詞特例；只選取抽取的固定文字，不執行 ERB。"""
    ns, ks, os = row[3:6]
    name = ns[0]
    kun = ks[-1]
    on = os[-1]
    voiced = {
        "狐",
        "鴉",
        "鶴",
        "蜘蛛",
        "蜂",
        "蛍",
        "桜",
        "霞",
        "霧",
        "鎖",
        "祟り",
        "駆",
        "咬",
        "払",
    }
    if name in voiced:
        kun = ks[0] if now == 1 and rand(2) else ks[-1]
    elif name in ("桔梗", "髪"):
        kun = ks[0] if now == 1 and rand(4) else ks[-1]
    elif name == "獅子":
        on = os[0] if now == 1 and rand(2) else os[-1]
    elif name == "竜":
        name = ns[0] if rand(2) == 0 else ns[1]
    elif name in ("熾", "光", "夜", "雷"):
        kun = ks[0] if rand(2) else ks[1]
    elif name == "月":
        if now == 1:
            rand(2)  # 原作接著無條件覆寫 KUN_STR=つき。
        on = os[0] if now == 1 and rand(2) else os[-1]
    elif name == "雨":
        kun = ks[0] if rand(2) == 0 else ks[1] if now == 0 else ks[2]
    elif name == "風":
        kun = ks[0] if now == 0 and rand(2) else ks[1]
    elif name == "氷":
        on = os[0] if now == 0 and rand(2) else os[1]
    elif name == "火":
        kun = ks[0] if rand(2) and now == 0 else ks[1]
    elif name in ("一", "二", "三", "四", "五", "六"):
        on = os[0]
        if name == "六":
            on = os[0] if now == 0 and rand(2) else os[1]
        if now == 0 and rand(2):
            kun = ks[0]
        else:
            kun = ks[1]
            if rand(2) == 0:
                name = ns[1]
                on = ""
    elif name in ("七", "八", "九"):
        on = os[0]
        if rand(2) == 0:
            kun = ks[0]
        else:
            if rand(2) == 0:
                name = ns[1]
                on = ""
            kun = ks[1]
    elif name == "天":
        kun = ks[0] if now == 0 else ks[1]
    elif name == "詩":
        for n in range(5, 1, -1):
            if rand(n) == 0:
                name = ns[5 - n]
                break
        else:
            name = ns[-1]
    elif name == "鉄":
        kun = ks[0] if rand(2) else ks[1]
        on = os[0] if now == 0 and rand(2) else os[1]
    elif name == "神":
        kun = (
            ks[0] if now == 1 and rand(2) else ks[1] if now == 0 and rand(2) else ks[2]
        )
    elif name == "巫":
        name = ns[0] if rand(2) else ns[1]
    elif name == "終":
        name = ns[1] if rand(2) == 0 else ns[0]
    elif name in ("飛", "流"):
        on = os[0] if now == 1 else os[1]
    return name, kun, on


def japanese(ctx: Ctx) -> str:
    """GENERATE_WEAPON_STR_JP.ERB@GENERATE_WEAPON_STR_JP:57–3566。"""
    st = ctx.state
    rand = st.rng.rand
    now = rand(2)
    count = 0
    names = ["", ""]
    kun = ["", ""]
    on = ["", ""]
    selected = 0
    previous = 0
    # PRE_NO/CAT_VAR 是 static；初次計數輪把 PRE_NO 設 0，保留 CAT_VAR。
    prev_no = st.temp.locals.get(("GENERATE_WEAPON_STR_JP:PRE_NO", 0), 0)
    category = st.temp.locals.get(("GENERATE_WEAPON_STR_JP:CAT_VAR", 0), 0)
    if not st.temp.locals.get(("GENERATE_WEAPON_STR_JP:COUNTED", 0), 0):
        prev_no = 0
        previous = category
    while count < 2:
        names[now] = kun[now] = on[now] = ""
        for i, row in enumerate(JAPANESE):
            mask, bit, chance = row[:3]
            number = len(JAPANESE) - i
            if chance and rand(chance) != 0:
                mask -= bit
            if (
                mask & (1 if now == 0 else 2)
                and rand(number) == 0
                and prev_no != number
            ):
                names[now], kun[now], on[now] = _jp_forms(row, now, rand)
                category = row[6]
                selected = number
                break
        if selected > 0:
            # 原作 OR 條件恆成立，包含純名詞／熟語也不得同類。
            if category == previous:
                continue
            if count > 0:
                if not kun[0]:
                    if not kun[1]:
                        reading = on[0] + on[1]
                    else:
                        if rand(4):
                            continue
                        reading = on[0] + kun[1]
                elif not on[0]:
                    if not kun[1]:
                        if rand(4):
                            continue
                        reading = kun[0] + on[1]
                    else:
                        reading = kun[0] + kun[1]
                elif not kun[1]:
                    reading = (on[0] if rand(6) else kun[0]) + on[1]
                elif not on[1]:
                    reading = (kun[0] if rand(6) else on[0]) + kun[1]
                elif rand(8) == 0:
                    reading = kun[0] + on[1]
                elif rand(7) == 0:
                    reading = on[0] + kun[1]
                elif rand(2) == 0:
                    reading = kun[0] + kun[1]
                else:
                    reading = on[0] + on[1]
                st.results[1] = reading
            count += 1
            now ^= 1
        prev_no = selected
        previous = category
    for k, v in [("PRE_NO", prev_no), ("CAT_VAR", category), ("COUNTED", 1)]:
        st.temp.locals["GENERATE_WEAPON_STR_JP:" + k, 0] = v
    st.results[0] = "".join(names)
    st.result[0] = 0
    return st.results[0]


def addition(
    ctx: Ctx,
    style: int,
    position: int,
    element: int,
    kind: int,
    attack: int,
    custom: str,
) -> str:
    """GENERATE_ADD_STR.ERB@GENERATE_ADD_STR:7–364；保留原作權重與重試順序。"""
    st = ctx.state
    rand = st.rng.rand
    # SPLIT 空字串仍有一項空值（Creator.Method.cs／SPLIT 命令）。
    counts = {}
    words_by_group = {}
    # GENERATE_ADD_STR.ERB@GENERATE_ADD_STR:159–169：LCOUNT不碰COUNT，
    # 每組REPEAT100複製字詞，遇空字串BREAK仍步進一次。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023。
    for i in range(55):
        words = ADD_WORDS.get(i, [""])
        counts[i] = len(words)
        copied = [""] * len(words)
        st.count[0] = 0
        while st.count[0] < 100:
            index = st.count[0]
            if index >= len(words) or not words[index]:
                st.count[0] += 1
                break
            copied[index] = words[index]
            st.count[0] += 1
        words_by_group[i] = copied
    total = 1 + sum(n for i, n in counts.items() if not 11 <= i < 20)
    at_total = 1 + sum(counts[i] for i in range(11, 20))
    length = max(2, min(3, rand(4) + int(bool(kind) and position != 2)))
    now = rand(2)
    count = 0
    flags = 0
    chars = ["", "", ""]

    def group(index):
        return words_by_group.get(index, [""])

    while count < length:
        number = total
        at = at_total
        hit = False
        for i in range(11, 20):
            if element != i - 10:
                continue
            for word in group(i):
                at -= 1
                if not flags & 2 and rand(at) == 0:
                    chars[now] = word
                    flags |= 3
                    hit = True
                    break
            if hit:
                break
        if not hit:
            for word in group(51):
                number -= 1
                if rand(number + 16) == 0:
                    chars[now] = word
                    flags |= 1
                    hit = True
                    break
        groups = [(i, style == i and not flags & 4, 4) for i in range(1, 10)]
        groups += [
            (26, bool(attack & 1 and attack & 2) and not flags & 8, 8),
            (27, bool(attack & 2 and attack & 4) and not flags & 8, 8),
            (28, bool(attack & 4 and attack & 1) and not flags & 8, 8),
        ]
        groups += [
            (i, bool(attack & (1 << (i - 21))) and not flags & 8, 8)
            for i in range(21, 29)
        ]
        groups += [(i, kind == i - 30 and now == length - 1, 16) for i in range(30, 50)]
        if not hit:
            for i, allowed, bit in groups:
                for word in group(i):
                    number -= 1
                    if allowed and rand(number) == 0:
                        chars[now] = word
                        flags |= 1 | bit
                        hit = True
                        break
                if hit:
                    break
        if not hit and kind == 20 and now == length - 1:
            chars[now] = custom
            flags |= 17
        if flags & 1:
            flags &= ~1
            if any(
                chars[a] and chars[a] == chars[b] for a, b in [(0, 1), (1, 2), (2, 0)]
            ):
                continue
            if now == length - 1:
                if not flags & 16 and (
                    (length == 3 and rand(8)) or (length == 2 and rand(6))
                ):
                    continue
                if position == 2 and not flags & 16 and rand(8):
                    continue
                units = len(chars[now].encode("utf-16-le", errors="surrogatepass")) // 2
                st.result[0] = units
                if units > 1 and length > 2 and rand(3):
                    continue
                if length == 2 and units > 1 and rand(3) == 0:
                    chars[0] = ""
            now = now ^ 1 if count == 0 else 2
            count += 1
    st.results[0] = "".join(chars)
    st.result[0] = 0  # 函式末尾隱含 RETURN 0。
    return st.results[0]
