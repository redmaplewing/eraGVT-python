"""開局關係設定。原文：ERB/SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB。

固定顯示文字由原文擷取，選單與狀態規則以 Python 手翻。
"""
from collections.abc import Generator
import re

from .action import Ctx
from .chara_common import is_female, talent
from .era import format_percent
from .input_request import TextInputRequest, input_number
from .relation import get_relation, check_all_relation, toshiue
from .relation_setting_text import RELATION, OPENING
from .shop import lb

Menu = Generator[None | TextInputRequest, int | str, None]
# CHARA_RELATION.ERB@SET_RELATION:361–459；おじおば／甥姪互換。
REVERSE_BITS = ((1,1),(6,6),(20,20),(21,21),(22,22),(23,24),(24,23),(25,25),(32,32),(33,33),(34,34))
# DIM.ERH:219–242；いとこ 25 未顯示，但 :510 接受手動輸入。
OPTIONS = ((1,210),(2,214),(3,218),(4,222),(5,226),(6,230),
           (20,236),(21,240),(22,244),(23,248),(24,252),(30,256),
           (31,260),(32,264),(33,268),(34,272),(40,276),(41,280),(42,284))
BIT_NAMES = ("生き別れ","親しい","疎遠な","愛する","憎悪する","義理の",
             "親子","兄弟姉妹","祖父祖母孫","おじおば","甥姪","友人",
             "片思い","恋人","婚約者","配偶者","主人","従者","奴隷")


def _text(line: int, a: str = "", b: str = "", ai: int = 0, bi: int = 0, relation: str = "") -> str:
    replacements = {
        "%CALLNAME:(ARG:0)%": a,
        "%CALLNAME:(ARG:1)%": b,
        "{ARG:0}": str(ai),
        "{ARG:1}": str(bi),
        "%RESULTS%": relation,
    }
    replacements.update({"{"+name+"}": str(bit) for name, (bit, _) in zip(BIT_NAMES, OPTIONS)})
    # 固定樣板只展開一次，插入的角色名稱不重新解讀。
    # reference/emuera-1824/Emuera/GameData/StrForm.cs:205–216。
    pattern = "|".join(re.escape(token) for token in replacements)
    return re.sub(pattern, lambda match: replacements[match[0]], RELATION[line])



def _number(ctx: Ctx) -> Generator[None, int, int]:
    value = yield from input_number(ctx)
    ctx.out.printl(str(value))
    return value


def convert_relation(ctx: Ctx) -> None:
    """FIRSTSETTING_CONVERTCSV.ERB@CONVERT_RELATION:3–24；每角色快照，正值才覆寫。

    DIM.ERH:23：CHARACSV最大数 = 9999；原作不刪舊 CSV NO 格。
    """
    st = ctx.state
    for who,c in enumerate(st.charas):
        if who == st.MASTER:
            continue
        previous = {i:v for i,v in c.relation.items() if i < 9999}
        for other,target in enumerate(st.charas):
            if other == st.MASTER:
                continue
            if not 0 <= target.no < 9999:
                raise IndexError("CONVERT_RELATION：NO 超出 RELATION_LIST 範圍")
            value = previous.get(target.no,0)
            if value > 0:
                c.relation[other] = value
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    st.result[0] = 0


def set_relation(ctx: Ctx, who: int, other: int) -> Menu:
    """CHARA_RELATION.ERB@SET_RELATION:189–553；取消不回寫，確認後部分雙向化。"""
    st,out = ctx.state,ctx.out
    ca,cb = st.charas[who],st.charas[other]
    selected = {bit for bit in range(64) if (ca.relation[other] >> bit) & 1}
    count = out.linecount
    names = dict(a=ca.callname,b=cb.callname,ai=who,bi=other)
    while True:
        lb(out)
        # CALL LB 的自然終端只清 RESULT:0。
        st.result[0] = 0
        out.printl(_text(204,**names))
        out.drawline()
        out.printl(RELATION[207])
        for bit,line in OPTIONS:
            if bit == 20:
                out.drawline()
                out.printl(RELATION[233])
            if bit in selected:
                out.set_color("#ff3cdc")
            out.printl(_text(line))
            out.reset_color()
        out.drawline()
        blocked = False
        lose = set()
        if not selected.intersection(range(20,26)):
            for bit,line in ((1,292),(6,296)):
                if bit in selected:
                    out.printl(RELATION[line])
                    blocked = True
        # :300–337 實際年齡相同時仍由 CFLAG:240 決定；義理不改素質。
        for bit,lines in ((20,(302,304,310,312)),(22,(321,323,329,331))):
            if bit not in selected or 6 in selected:
                continue
            for index,(a,b,c) in enumerate(((who,other,ca),(other,who,cb))):
                if toshiue(st,a,b) and talent(ctx.data,c,"処女") > 0 and is_female(ctx.data,c):
                    out.printl(_text(lines[index*2],**names))
                    if talent(ctx.data,c,"固有キャラ") == 0:
                        out.printl(_text(lines[index*2+1],**names))
                    else:
                        blocked = True
                    lose.add(a)
                    break
        if blocked:
            out.set_color("#696969")
        out.printl(RELATION[340])
        out.reset_color()
        out.printl(RELATION[342])
        value = yield from _number(ctx)
        if value != 200:
            out.clearline(out.linecount-count)
        if value == 200 and not blocked:
            # :347–350：bit0 丟棄，其餘未列出的位元也保留；SETBIT 的 Int64 符號位。
            # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:546–557。
            mask = sum(1<<bit for bit in selected if bit > 0)
            ca.relation[other] = mask-(1<<64) if mask & (1<<63) else mask
            for a in lose:
                st.charas[a].talent[ctx.data.index_of("TALENT","処女")] = 0
            changed = False
            for forward,reverse in REVERSE_BITS:
                on = forward in selected
                changed |= bool((cb.relation[who]>>reverse)&1) != on
                cb.relation.set_bit(who,reverse,on)
            if 40 in selected:
                # :461 原文是 OR；已有其中一種仍詢問，新增而不清另一種。
                if not cb.relation.get_bit(who,41) or not cb.relation.get_bit(who,42):
                    changed = True
                    for line in (463,464,465):
                        out.printl(_text(line,**names))
                    while True:
                        choice = yield from _number(ctx)
                        if choice in (41,42):
                            cb.relation.set_bit(who,choice)
                            break
            else:
                changed |= cb.relation.get_bit(who,41) or cb.relation.get_bit(who,42)
                cb.relation.set_bit(who,41,False)
                cb.relation.set_bit(who,42,False)
            on = bool(selected.intersection((41,42)))
            changed |= cb.relation.get_bit(who,40) != on
            cb.relation.set_bit(who,40,on)
            if ca.relation[other] > 0:
                st.results[0] = get_relation(ctx,who,other)
                st.result[0] = 0
                out.printl(_text(494,relation=st.results[0],**names))
            else:
                out.printl(_text(496,**names))
            if changed:
                if cb.relation[who] > 0:
                    st.results[0] = get_relation(ctx,other,who)
                    st.result[0] = 0
                    out.printl(_text(501,relation=st.results[0],**names))
                else:
                    out.printl(_text(503,**names))
            out.printl(RELATION[505])
            # PRINTW 等待不寫 RESULT／RESULTS：EmueraConsole.cs:497–508、701–734。
            out.printl("（按 Enter 繼續）")
            yield TextInputRequest()
            out.clearline(1)
            break
        if value == 999:
            break
        if 1 <= value <= 6 or 20 <= value <= 25 or 30 <= value <= 34 or 40 <= value <= 42:
            selected.symmetric_difference_update((value,))
            for group in ((23,24),(31,32,33,34),(40,41,42)):
                if value in group:
                    selected.difference_update(set(group)-{value})
    # RETURN 無引數：Instraction.Child.cs:2008–2012；只清 RESULT:0。
    st.result[0] = 0


def _roster(ctx: Ctx, selected: int | None = None) -> None:
    """オープニング処理.ERB@HEROINE_PRESET:666–695、702–736。"""
    for who,c in enumerate(ctx.state.charas):
        if who == ctx.state.MASTER:
            continue
        if who == selected:
            ctx.out.set_color("#696969")
        if c.callname == "汎用キャラ":
            ctx.out.printl(OPENING[671].replace("{LOCAL}",str(who)))
        else:
            age = f"実年齢:{c.base[40]}" if c.cflag[34] > 0 else ""
            ctx.out.print(format_percent(f"[{who}]{c.name}",38,True)+"　"+format_percent(age,10,True)+"　")
            ctx.out.print(OPENING[678] if is_female(ctx.data,c) else OPENING[680])
            line = {1:683,2:685,3:687,4:689,9:691}.get(c.cflag[0])
            if line:
                ctx.out.print(OPENING[line])
            ctx.out.printl()
        if selected is not None:
            ctx.out.reset_color()


def relation_menu(ctx: Ctx) -> Menu:
    """オープニング処理.ERB@HEROINE_PRESET:659–752。"""
    convert_relation(ctx)
    while True:
        ctx.out.drawline()
        ctx.out.printl(OPENING[664])
        ctx.out.printl(OPENING[665])
        _roster(ctx)
        ctx.out.printl(OPENING[696])
        while True:
            first = yield from _number(ctx)
            # :699／740 原文包含 CHARANUM，手動輸入該值仍在存取時越界。
            if 0 < first <= ctx.state.charanum:
                ctx.out.printl(OPENING[701])
                _roster(ctx,first)
                ctx.out.printl(OPENING[737])
                while True:
                    second = yield from _number(ctx)
                    if 0 < second <= ctx.state.charanum and second != first:
                        yield from set_relation(ctx,first,second)
                        break
                    if second == 99:
                        break
                break
            if first == 99:
                check_all_relation(ctx)
                ctx.state.result[0] = 0
                return
