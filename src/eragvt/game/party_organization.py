"""ERB/インターミッション画面/SHOP_ORGANIZE_PARTY.ERB@SHOP_ORGANIZE_PARTY:3–167。"""
from collections.abc import Generator

from . import shop
from .action import Ctx
from .input_request import input_number
from .party_organization_text import TEXT
from ..state.constants import PARTY_MAX, ActionPlan


def _show(ctx: Ctx) -> None:
    st, data, out = ctx.state, ctx.data, ctx.out
    shop.lb(out)
    out.drawline()
    shop.shop_show_boss_info(st, data, out)
    out.drawline()
    out.printl()
    count_text = TEXT[14].replace('{CHARANUM_PARTYCHECK(1)}', str(shop.charanum_partycheck(st)))
    out.printl(count_text.replace('{パーティ人数最大値}', str(PARTY_MAX)))
    shop.shop_show_status_party_list(st, data, out, True)
    if shop.charanum_reserve(st):
        shop.shop_show_status_reserve_list(st, data, out, True)
    out.print_plain(TEXT[20])
    if st.target:
        c = st.charas[st.target]
        if c.cflag[999] == 0:
            if shop.charanum_active(st) >= PARTY_MAX:
                line = 28
            elif c.cflag[0] == 10:
                line = 30
            elif c.cflag[0] == 11:
                line = 32
            else:
                line = 34
            out.print(TEXT[line])
        else:
            out.print(TEXT[38])
    else:
        out.print(TEXT[41])
    # ERB/汎用関数/CPRINT.ERB@CPRINTL:27–31、@CPRINTPLAIN:43–51：恢復呼叫前顏色。
    color = out.color
    out.set_bold()
    out.set_color('#fab432')
    out.printl('[50] パーティ編成を完了する　')  # 原作 :46，CALL 字串。
    out.set_color(color) if color is not None else out.reset_color()
    out.set_bold(False)
    shop.shop_ng_action_info(st, data, out)
    out.drawline()
    for _ in range(4):
        out.printl()
    shop.shop_intermission_header(st, data, out)
    if st.target:
        out.print(TEXT[64])
        color = out.color
        out.set_color('#fab432')
        out.print_plain(f'[{st.target}]{st.charas[st.target].callname}')  # :68
        out.set_color(color) if color is not None else out.reset_color()
        for line in (69, 70, 71):
            out.printl(TEXT[line])
    else:
        for line in (73, 74, 75):
            out.printl(TEXT[line])
    if st.target and st.charas[st.target].cflag[999] == 0:
        out.printl()
        # 原作 :80 確實為 <；與 :27 的 >= 相反，保留原判斷及文字。
        if shop.charanum_active(st) < PARTY_MAX:
            line = 81
        elif st.charas[st.target].cflag[0] == 10:
            line = 83
        elif st.charas[st.target].cflag[0] == 11:
            line = 85
        else:
            line = 87
        out.printl(TEXT[line])
    else:
        out.printl()
        out.printl()
    for _ in range(3):
        out.printl()
    # 最後 CALL（表頭／CPRINTPLAIN）的自然結束，只清 RESULT:0。
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    st.result[0] = 0


def party_organization_gen(ctx: Ctx) -> Generator[None, int, None]:
    """原作 :98–167；RESTART 重畫，INPUT 才等待，沒有新增等待／選項。"""
    st, out = ctx.state, ctx.out
    while True:
        _show(ctx)
        value = yield from input_number(ctx)
        if value == 50:
            out.printl(TEXT[103])
            if st.target == st.MASTER:
                st.target = st.rng.rand(st.charanum - 1) + 1
            if shop.charanum_reserve(st) == 0:
                st.flag[61] = 0
            st.result[0] = 0  # :109 RETURN 0；其餘格保留。
            return
        if value == 100:
            if st.target == 0 or st.charas[st.target].cflag[0] != 0:
                continue
            c = st.charas[st.target]
            if c.cflag[999] == 0 and shop.charanum_active(st) < PARTY_MAX:
                c.cflag[999] = 1
            elif c.cflag[999]:
                c.cflag[999] = 0
                c.cflag[100] = ActionPlan.REST
            st.target = 0
        elif 1 <= value < st.charanum:
            if st.charas[value].cflag[0] in (1, 2, 3, 9):
                continue
            if st.charas[st.target].cflag[0] in (10, 11) or st.charas[value].cflag[0] in (10, 11):
                for who, token in ((st.target, '%CALLNAME:TARGET%'), (value, '%CALLNAME:RESULT%')):
                    c = st.charas[who]
                    if c.cflag[0] in (10, 11):
                        line = (134 if c.cflag[0] == 10 else 136) + (4 if token == '%CALLNAME:RESULT%' else 0)
                        out.printl(TEXT[line].replace(token, c.callname))
                st.target = 0
                continue
            if st.target == 0:
                st.target = value
            elif st.target == value:
                st.target = 0
            else:
                a, b = st.target, value
                for i, c in enumerate(st.charas):
                    if i != st.MASTER:
                        c.relation[a], c.relation[b] = c.relation[b], c.relation[a]
                first, second = st.charas[a], st.charas[b]
                first.cflag[999], second.cflag[999] = second.cflag[999], first.cflag[999]
                # :158；引擎僅交換角色，不修正 TARGET／ASSI／MASTER。
                # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1165–1174。
                st.swap_chara(a, b)
                for i in (a, b):
                    if st.charas[i].cflag[999] == 0:
                        st.charas[i].cflag[100] = ActionPlan.REST
                st.target = 0
