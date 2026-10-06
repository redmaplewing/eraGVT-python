"""共用模板載入：ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB。"""
from .action import seikaku_hosei
from .chara_common import seikaku_check, talent
from .character_editor_text import TEXT
from .era import format_percent
from .input_request import input_number, WaitInputRequest
from .opening import _csvbase, firstsetting_chara_csvfix


def load_character_csv(ctx, who):
    """@FIRSTSETTING_CHARA_LOADCSV:1496–1620；模板番号，不是檔名或上傳檔案。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    # EXISTCSV/CSVNAME按模板番号；引擎不使用檔名csv_no。
    # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1326–1353。
    candidates = sorted(no for no in data.charas if 0 <= no < 9999 and no != 999)
    page = 0
    while True:
        out.printl()
        out.printl(f'{who}人目のキャラデータを選んでください')
        out.printl(TEXT[1506])
        for ordinal, no in enumerate(candidates[30 * page:30 * (page + 1)], 1):
            out.print_lc(f'[{no:4}] '+format_percent(data.charas[no].name,32,True))
            if ordinal % 2 == 0 and ordinal % 30 != 0:
                out.printl()
        out.printl()
        out.printl(TEXT[1522])
        out.print_lc(TEXT[1523])
        # 原文直接整除；筆數為30倍數時保留可達的空白末頁。
        out.print_lc(f'        Page({page}/{len(candidates) // 30})')
        out.printl(TEXT[1526])
        out.printl(TEXT[1528])
        choice = yield from input_number(ctx)
        if choice == 99:
            st.result[0] = 0
            return
        if choice == -1:
            page = max(0, page - 1)
        elif choice == -2:
            page = min(len(candidates) // 30, page + 1)
        elif choice in candidates:
            break

    # ADDCHARA→SWAPCHARA→DELCHARA：整筆替換，不保留舊角色的欄位；索引變數不變。
    # reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1026–1033、1061–1067、1165–1174。
    c = st.add_chara(data, 0 if choice == 1 else choice)
    st.charas[who], st.charas[-1] = st.charas[-1], st.charas[who]
    st.del_chara(st.charanum - 1)
    if choice == 1:
        c.talent[data.index_of('TALENT', 'オトコ')] = 1
        c.name = '汎用キャラ(♂)'
    # DEVIATION: REPEAT4的COUNT沿既有W07未與catalog共用，不新增全域COUNT模型。
    for i in range(4):
        st.savestr[i] = ''
    out.printw(f'{who}人目のキャラを{c.name}にしました')
    yield WaitInputRequest()
    firstsetting_chara_csvfix(st, data, who)
    if talent(data, c, '固有キャラ') == 0:
        c.no = 0
    slots = (0, 1, 2, 10, 11, 12, 13)
    for slot in slots:
        c.base[slot] = c.maxbase[slot] = _csvbase(data, c.no, slot)
    if c.no == 0:
        person = seikaku_check(data, c)
        for slot in slots:
            c.base[slot] = c.maxbase[slot] = seikaku_hosei(person, slot, c.base[slot])
    for i, slot in enumerate(slots):
        c.base[slot] += c.cflag[60 + i]
    # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67：自然終端只寫RESULT0。
    st.result[0] = 0
