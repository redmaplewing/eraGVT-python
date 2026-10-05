"""原作共用成就；GLOBAL 保存沿用 GlobalStore。"""
from ..state.constants import GameOption
from .opening import game_option
from .achievements_data import NAMES, PAGES, GET_STATE_ABLUP, GET_STATE_EXPUP


def update_status_record(ctx, who):
    """ERB/インターミッション画面/SHOP_TURNEND.ERB@UPDATE_STATUS_RECORD:263–348。

    GLOBAL:110 同時是魅了經驗及 SCORE 總評；保留原作共用欄位。
    """
    from .era import format_percent
    c, g = ctx.state.charas[who], ctx.globals.mem
    rows = [("maxbase", "BASE", name, 103+i, slot, "") for i,(name,slot) in enumerate(
        (("体力",0),("気力",1),("性耐性",2),("攻撃",10),("防御",11),("敏捷",12),("知性",13)))]
    rows.append(("exp","EXP","魅了経験",110,14,""))
    rows.extend(("exp","EXP",name,120+i,20+i,"回") for i,name in enumerate(
        ("Ｖ経験","Ａ経験","自慰経験","フェラ経験","精液経験","絶頂経験","出産経験","近親交配経験","射精経験","噴乳経験","放尿経験","寄生経験")))
    for array, kind, name, number, slot, suffix in rows:
        value = getattr(c,array)[ctx.data.index_of(kind,name)]
        if value > g.global_[number]:
            g.global_[number] = value
            g.globals_[slot] = f"{format_percent(c.name,40,True)}（Lv{c.abl[ctx.data.index_of('ABL','レベル')]}）　{value}{suffix}"
    ctx.globals.save()
    # 自然回傳：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    ctx.state.result[0] = 0


def _thresholds(ctx, who, rows):
    c = ctx.state.charas[who]
    for array,name,threshold,num in rows:
        if getattr(c,array.lower())[ctx.data.index_of(array,name)] >= threshold:
            unlock(ctx,num,NAMES[num])


def get_state_ablup(ctx, who):
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_ABLUP:443–502。"""
    c = ctx.state.charas[who]
    value = sum(c.abl[ctx.data.index_of("ABL",name)] for name in ("Ｃ感覚","Ｖ感覚","Ａ感覚","Ｂ感覚"))
    for threshold,num in ((5,240),(10,241),(15,242),(20,243)):
        if value >= threshold:
            unlock(ctx,num,NAMES[num])
    _thresholds(ctx,who,GET_STATE_ABLUP)
    for num,name in ((262,"触手の虜"),(279,"完堕ち"),(280,"四肢欠損")):
        if ctx.globals.mem.global_[num] == 0 and sum(c.talent[ctx.data.index_of("TALENT",name)] > 0 for c in ctx.state.charas[1:]) >= 3:
            unlock(ctx,num,NAMES[num])
    ctx.state.result[0] = 0


def get_state_expup(ctx, who):
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_EXPUP:506–534。"""
    _thresholds(ctx,who,GET_STATE_EXPUP)
    c = ctx.state.charas[who]
    if c.talent[ctx.data.index_of("TALENT","処女")] > 0 and c.exp[ctx.data.index_of("EXP","Ａ経験")] >= 10:
        unlock(ctx,264,NAMES[264])
    ctx.state.result[0] = 0


def get_state_trophy(ctx, who):
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_TROPHY:398–441。"""
    c = ctx.state.charas[who]
    for name, low in (("攻撃",220),("防御",222),("敏捷",224),("知性",226)):
        value = c.maxbase[ctx.data.index_of("BASE", name)]
        for threshold, num in ((500,low),(1000,low+1)):
            if value >= threshold:
                unlock(ctx,num,NAMES[num])
    for name, threshold, num in (("体力",10000,228),("気力",10000,229),("性耐性",1000,230)):
        if c.maxbase[ctx.data.index_of("BASE",name)] >= threshold:
            unlock(ctx,num,NAMES[num])
    for name,num in (("近距離",231),("中距離",232),("遠距離",233)):
        if c.abl[ctx.data.index_of("ABL",name)] >= 9:
            unlock(ctx,num,NAMES[num])
    ctx.state.result[0] = 0


def show_trophy(ctx):
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@SHOW_TROPHY:23–353。"""
    from .shop import lb
    from .action import _shortline
    from .era import format_percent
    # MODE 是預設靜態 DIM；重入只重設 LOCAL 頁碼。
    # reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27；
    # GameData/Variable/VariableData.cs:451–473、1012–1013（讀檔重設靜態變數）。
    mode = ctx.state.temp.locals.get(("SHOW_TROPHY_MODE", 0), 0)
    page = 1
    out, st, g = ctx.out, ctx.state, ctx.globals.mem
    while True:
        lb(out)
        out.printl("☆☆☆実績＆トロフィーの確認☆☆☆")
        out.drawline()
        maximum = 4 if mode else 2
        if mode:
            start, rows = PAGES[page-1]
            out.printl("実績名　　　　　　　　　　　　内容　　　　　　　　　　　　　　　　周回ボーナス")
            _shortline(out)
            for display, (num,name,hint,bonus,desc,extra,limit) in enumerate(rows,start):
                if g.global_[num]:
                    out.printl(f"　{display:02} {format_percent(name,28,True)}{format_percent(desc,36,True)}+{bonus}")
                    out.printl("　　　　　　　　　　　　　　　　" + format_percent(extra,36,False))
                else:
                    out.set_color((105,105,105))
                    out.printl(f"　{display:02} ？？？　　　　　　　　　　　{format_percent(hint,36,True)}？")
                    out.reset_color()
                    out.printl("　　　　　　　　　　　　　　　　" + format_percent(limit,36,False))
        elif page == 1:
            out.printl(" プレイの記録")
            _shortline(out)
            rank = g.global_[110]
            out.printl("　　総合ランク最高記録　　　　　　　　　" + ("ＥＤＣＢＡＳ"[rank-1]+"ランク" if 1 <= rank <= 6 else "なし"))
            out.printl(f"　　周回数累計　　　　　　　　　　　　　 {st.flag[854]} 回")
            if g.global_[114] > 0:
                out.printl(f"　　ENDLESS撃破記録 　　　　　　　　　　 {g.global_[114]} 体　")
            out.printl()
            out.printl("　　現在の共通設定")
            for label, flag, index in (("主題",5,10),("冠名",6,11),("かけ声",7,12)):
                spacing = "　　　　　　　　　　　　　　" if flag == 7 else "　　　　　　　　　　　　　　　"
                out.printl(f"　　　{label}{spacing}『{st.savestr[index] if st.flag[flag] == 1 else 'なし'}』")
            out.printl(" ")
            _shortline(out)
            out.printl(" ＨＡＬＬ　ＯＦ　ＦＡＭＥ　〜　歴代記録保持者　〜")
            _shortline(out)
            out.printl()
            for label,index in (("体力",0),("気力",1),("性耐性",2),("攻撃",10),("防御",11),("敏捷",12),("知性",13),("魅了",14)):
                out.printl("　　" + label + ("　　" if index == 2 else "　　　") + (g.globals_[index] or 'なし'))
                out.printl()
        else:
            out.printl(" ")
            out.set_color("#ff69b4")
            _shortline(out)
            out.printl(" ＨＯＬＥ　ＯＦ　ＳＨＡＭＥ　〜　歴代恥辱保持者　〜")
            _shortline(out)
            out.printl()
            for index,label in enumerate(("膣穴","尻穴","自慰","フェラ","精液","絶頂","出産","交配","射精","噴乳","放尿","寄生"),20):
                out.printl("　　" + label + ("　　" if index == 23 else "　　　") + (g.globals_[index] or 'なし'))
                out.printl()
            out.reset_color()
        out.drawline()
        out.print("[100]前のページへ　　　　　")
        out.print_plain(f"PAGE < {page}/{maximum} >　　　　")
        out.printl("[200]次のページへ")
        out.printl()
        out.printl("\t　　　　　　　　　[1000]実績を表示" if mode == 0 else "\t　　　　　　　　　[1000]トロフィーを表示")
        out.print("[999]戻る　")
        # INPUT 後回到等待狀態會提交未換行輸出：
        # reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:685–695。
        out._flush_partial()
        while True:
            value = yield
            st.result[0] = value
            if value in (100,200,1000,999):
                break
        if value == 999:
            st.result[0] = 0
            return
        if value == 1000:
            mode, page = 1-mode, 1
            st.temp.locals[("SHOW_TROPHY_MODE", 0)] = mode
        else:
            page = ((page-1 + (1 if value == 200 else -1)) % maximum)+1


def unlock(ctx, num, name):
    """ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20。

    PRINTW 的等待先於 GLOBAL 寫入與 SAVEGLOBAL。
    reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1279–1281
    SAVEGLOBAL 不修改 RESULT；函式 RETURN／流落才設 RESULT:0=0。
    """
    if not game_option(ctx.state, GameOption.NO_ACHIEVEMENT_END) and ctx.globals.mem.global_[num] == 0:
        ctx.out.printl(f"【実績：{name}】を達成しました！")
        ctx.out.printw()
        wait = getattr(ctx.out, "achievement_wait", None)
        if wait is not None:
            wait(None)
        ctx.globals.mem.global_[num] = 1
        ctx.globals.save()
    ctx.state.result[0] = 0
