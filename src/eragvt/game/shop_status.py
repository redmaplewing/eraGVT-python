"""SHOP 共用標記。原作 ERB/インターミッション画面/SHOP_SHOW_STATUS_LIST.ERB。"""
from .opening import talent, is_female
from .era import cp932_len
from .colorbar import colorsentence_minibar


def print_estrus_cycle(state, data, out, who):
    """ERB/ヒロイン関連/ESTRUS_CYCLE.ERB@PRINT_ESTRUS_CYCLE:4–27；不初始化週期。"""
    from .shop import check_pregnant
    c=state.charas[who]
    if talent(data,c,"未熟")>0 or not is_female(data,c) or check_pregnant(data,state,who):
        state.result[0]=0
        return
    day,abnormal=c.cflag[217],talent(data,c,"排卵異常")
    if 13-abnormal<=day<=15:
        out.set_color((250,50,50));out.print("[危険日]")
    elif abnormal>=3 or 16<=day<=(19 if abnormal==2 else 18):
        out.set_color((250,30,200));out.print("[排卵日]")
    elif day==1:
        out.set_color((50,120,230));out.print("[月経]")
    out.reset_color()
    state.result[0]=0


def show_shop_status_sign(state,data,out,who):
    """SHOP_SHOW_STATUS_LIST.ERB@SHOW_SHOP_STATUS_SIGN:158–188；CPRINT.ERB:15–23 保存色彩。"""
    from .shop import check_pregnant
    c=state.charas[who]
    print_estrus_cycle(state,data,out,who)
    if c.cflag[15]>0:
        out.print("[憂鬱]")
    fatigue=c.cflag[99]
    signs=((fatigue,f"[疲労 {fatigue}]",(50,255,90) if fatigue<20 else (40,146,73) if fatigue<50 else (30,102,36)),
           (c.cflag[241],f"[避妊 {c.cflag[241]}]",(255,60,255)),
           (check_pregnant(data,state,who),"[妊娠]",(205,60,60)),
           (talent(data,c,"繁殖袋")>0,"[繁殖袋]",(139,0,0)),
           (talent(data,c,"四肢欠損")>0,"[四肢欠損]",(170,0,0)))
    for active,label,color in signs:
        if active:
            old=out.color
            out.set_color(color);out.print(label)
            out.reset_color() if old is None else out.set_color(old)
    state.result[0]=0  # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。


def list_widths(state,reserve):
    """SHOP_SHOW_STATUS_LIST.ERB@SHOP_SHOW_STATUS_COUNT_MAXLEN:100–124。

    INTLEN 為 コモン関数.ERB@INTLEN:208–212 的 TOSTR 後字數，負號亦計入。
    原文寬度納入出產／育兒中；出場實際列印只含無事，兩者不可混用。
    """
    widths=[0]*5
    for i,c in enumerate(state.charas):
        if i==state.MASTER or c.cflag[999]==int(reserve) or c.cflag[0] not in (0,10,11):
            continue
        values=[cp932_len(c.name),cp932_len(c.callname),*(len(str(c.maxbase[n])) for n in (0,1,2))]
        widths=[max(a,b) for a,b in zip(widths,values)]
    return widths


def show_base_oneline(state,data,out,who,widths):
    """SHOP_SHOW_STATUS_LIST.ERB@SHOW_SHOP_STATUS_BASE_ONELINE:133–150。"""
    c=state.charas[who]
    for n,width in zip((0,1,2),widths):
        pad=2*width-len(str(c.base[n]))-len(str(c.maxbase[n]))
        colorsentence_minibar(out,data.names["BASE"][n],c.base[n],c.maxbase[n],4,pad)
    state.result[0]=0
