"""S34 狀態顯示；路徑相對 source/earGVP/ERB/。"""
from ..action import Ctx, config_check_screen, config_check_maniac
from ..colorbar import color_bar, percent_cal
from ..era import div, format_curly, limit
from .core import tc


def show_train_palam_status(ctx: Ctx, where: str) -> None:
    """ヒロイン関連/CHARA_STATUS.ERB@SHOW_TRAIN_PALAM_STATUS:1715–1750。"""
    st, out = ctx.state, ctx.out
    if config_check_screen(st, 5) != 1 or config_check_screen(st, 6) != (0 if where == "上部" else 1):
        st.result[0] = 0  # 一般函式終端：Process.ScriptProc.cs:61–67。
        return
    if config_check_screen(st, 7) == 0:
        show_status_palam(ctx)
        st.result[0] = 0
        return
    if where == "上部":
        out.print("　" * 24)
    if config_check_screen(st, 8) == 1:
        out.button("[898] 調教ステータスを表示", 898)
        out.printl()
    else:
        out.button("[898] 調教ステータスを閉じる", 898)
        if where in ("上部", "下部"):
            out.button("[899] " + ("下側" if where == "上部" else "上側") + "に移動", 899)
        out.printl()
        show_status_palam(ctx)
    st.result[0] = 0


def show_status_palam(ctx: Ctx) -> None:
    """ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS_PALAM:353–426。"""
    from .gaping import printform_gaping_now
    st, out, c = ctx.state, ctx.out, tc(ctx)
    if c.cflag[34] > 0 and config_check_maniac(st, 16) == 1:
        printform_gaping_now(ctx, st.target, c.cflag[1])
    else:
        out.printl()
    for count in range(12):
        pid = count if count < 4 else count + 6
        shield = count < 4 and c.base[count + 30] > 0
        if shield:
            result = percent_cal(c.base[count + 30], c.maxbase[count + 30])
            st.result[0] = result  # CALL PERCENT_CAL；其後 COLOR_BAR RETURN 1。
            red = limit(255 - div(result * result * 4, 200), 0, 255)
            green = limit(-215 - div(result * result, 100) + result * 5, 0, 255)
            out.print(ctx.data.names["TALENT"].get(count + 190, "") + "　₍")
            st.result[0] = color_bar(out, c.base[count + 30], c.maxbase[count + 30], 13,
                red, green, 20, -160, 6, 32, 20, 1, "▮", "▮")
            out.print("₎ ")
        else:
            out.print(ctx.data.names["PALAM"].get(pid, "") + format_curly(c.palam[pid], 8))
            thresholds = (100, 300, 600, 1500, 3000, 6000, 10000, 30000, 60000, 150000, 300000)
            level = next((i for i, bound in enumerate(thresholds) if c.palam[pid] < bound), 11)
            out.print("  -  [Lv." + str(level) + "] " if level < 10 else
                "  - [Lv.10] " if level == 10 else "  - [LvMAX] ")
        if count in (2, 5, 8):
            out.printl()
    out.printl()
    st.result[0] = 0  # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。


def palam_up_display_calculation(ctx: Ctx, before: list[int], ecs_flag: int) -> None:
    """ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_UP_DISPLAY_CALCULATION:1338–1399。

    :1356 的 PALAM:LCOUNT 與 :1375 的 PALAM:調教PALAM:LCOUNT 索引不同，照原作。
    STRLENFORM 更新 RESULT：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:504–526。
    """
    st, out, c = ctx.state, ctx.out, tc(ctx)
    up = st.temp.up
    ids = (0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17)
    padding_u = padding_p = 4
    for count, pid in enumerate(ids):
        disp = before[count] if count < 4 else c.palam[count]
        st.result[0] = len(str(up[pid]))
        padding_u = max(padding_u, st.result[0])
        st.result[0] = len(str(disp + up[pid]))
        padding_p = max(padding_p, st.result[0])
    for count, pid in enumerate(ids):
        if up[pid] <= 0:
            continue
        disp = before[count] if count < 4 else c.palam[pid]
        out.print(f"{ctx.data.names['PALAM'].get(pid, '')}：{format_curly(disp, padding_p)} + {format_curly(up[pid], padding_u)} ")
        if count < 4:
            if c.nowex[count] > 0 and ecs_flag < 1:
                minus = disp + up[pid] - 10000 + 1 if c.nowex[count] > 1 else 10000
                # 地の文/MESSAGE_SEX.ERB@ECSTASY_RANK:188–214。
                rank = ("", "", "強", "超", "超強", "最強", "凄", "極", "獄", "狂", "最狂")[c.nowex[count]]
                out.printl(f"- {format_curly(minus, padding_p)} = {format_curly(c.palam[count], padding_p)}　{rank}絶頂")
            else:
                suffix = "　（" + ctx.data.names["TALENT"].get(count + 190, "") + "） " if c.base[count + 30] > 0 and st.flag[700] else " "
                out.printl(f"= {format_curly(c.palam[pid], padding_p)}" + suffix)
        elif disp + up[pid] > 999999:
            out.printl(f"- {format_curly(disp + up[pid] - 999999, padding_p)} = 999999　限界")
        else:
            out.printl(f"= {format_curly(disp + up[pid], padding_p)}")
    st.result[0] = 0  # 一般函式無 RETURN 的終端，STRLENFORM 的暫值不洩漏至呼叫端。
