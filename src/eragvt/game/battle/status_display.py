"""S86 戰鬥決策資訊；所有狀態規則為原生 Python，衣裝標籤讀既有 catalog。"""
from ..action import config_check_event, print_transname, print_transcallname
from ..opening import is_female
from ..era import div, mod, limit, format_curly, format_percent, cp932_len
from ..colorbar import color_bar, colorsentence_bar, colorsentence_barcolor, percent_cal
from ..shop_status import print_estrus_cycle
from ..tentacle import enemy_type_check
from .core import tc,t,get_battle_situation,tentacle_access,print_distance
from .cloth import costume_name,inner_name,NO_INNER,OUTER_PER,OUTER_DEF,INNER_PER,INNER_DEF
from .func import calc_chisei_shien


def display_enemy_access(ctx,key):
    """COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:198–309 的本畫面 CALL 邊界。

    :201 每一個 key 先寫診斷字串；數值 key 成功也不把 RESULTS 清空。
    NAME 內層呼叫 GETNAME，故錯誤 key 亦為 GETNAME。只同步本畫面，不改其他呼叫者。
    """
    st=ctx.state
    original_key="GETNAME" if key=="NAME" else key
    st.results[0]=f"【エラー：{st.savestr[13]}_{st.flag[11]}に対するTENTACLE_ACCESS('{original_key}')関数失敗】"
    result=tentacle_access(ctx,"GETNAME" if key=="NAME" else key)
    if key in ("NAME","GETNAME"):
        st.results[0]=str(result)
        if key=="NAME":ctx.out.print(str(result))
        st.result[0]=0
    else:st.result[0]=int(result)
    return result


def _regular(out):
    out.set_bold(False);out.set_italic(False)


def status_feat(ctx):
    """ERB/ヒロイン関連/CHARA_STATUS.ERB@STATUS_PRINT_FEAT:1529–1713。"""
    st,out,c=ctx.state,ctx.out,tc(ctx)
    has=lambda name:t(ctx,c,name)>0
    low=percent_cal(c.base[0]+c.base[1],c.maxbase[0]+c.maxbase[1])<=25
    for n in range(201,250):
        if c.talent[n]>0:out.print(f" 種族:{ctx.data.names['TALENT'].get(n,'')}    ")
    out.print("FEAT:")
    found=False
    for n in range(1100,1300):
        name=ctx.data.names['TALENT'].get(n,'')
        if name=="超反応" and st.tflag[80]>0 or name=="秘められし力" and not low:
            out.set_color((128,128,128))
        if c.talent[n]>0:
            out.print(f"[{name}]");found=True
        out.reset_color()
    if not found:
        out.printl("─");return
    out.printl();out.print("   ");out.set_color((200,255,200))
    hit=6*has("攻勢構築")+12*(has("秘められし力") and low)+3*has("心眼")+2*has("共生")
    crt=6*has("獣性の証")+12*(has("秘められし力") and low)+3*has("心眼")+2*has("共生")
    wrap=has("攻勢構築")
    if hit:out.print(f"直撃率+{hit}%  ")
    if crt:out.print(f"CRT率+{crt}%  ")
    if has("超反応") and st.tflag[80]==0:out.print("絶対回避  ")
    benefits=(("闘争本能","恍惚耐性",False),("溢れる生命力","回復量アップ",False),
        ("生粋の戦士","気絶耐性  被CRT防止",False),("剛腕","振り解き率アップ",True),
        ("エアマスター","空中性能強化",True),("有翼","空中ダッシュゲージ+1",True),
        ("空中浮遊","空中ダッシュ疲労軽減",True),("小さな体躯","着地ペナルティ無効",True),
        ("ホットスタート","常にバースト攻撃可能",True),("フルバースト","バースト攻撃の威力アップ",True),
        ("祝福","状態異常耐性",True),("不屈","消耗ペナルティ軽減",True),("スタミナ","持久力アップ",True),
        ("平凡","油断させやすい",False),("背徳の烙印","搾精ダメージアップ",False))
    for name,label,newline in benefits:
        if has(name):out.print(label+"  ");wrap|=newline
    if wrap:out.printl()
    out.print("   ");out.set_color((255,200,255))
    for name,label in (("攻勢構築","油断させにくい"),("剛腕","振り解くと疲労+1"),
        ("エアマスター","空中ダッシュで疲労+1"),("有翼","着地時に疲労+1"),
        ("空中浮遊","移動系コマンドで疲労+1"),("小さな体躯","振り解き率ダウン")):
        if has(name):out.print(label+"  ")
    recoil=int(has("ホットスタート"))+int(has("フルバースト"))
    if recoil:out.print(f"バースト攻撃の反動+{recoil}  ")
    if has("祝福"):out.print("粘液,波動ダメージ増大  ")
    if has("不屈") or has("スタミナ"):out.print("EXゲージが上昇しにくい  ")
    out.reset_color()


def cloth_durability(ctx):
    """ERB/武器と衣装/衣装関連/CLOTH_BATTLE.ERB@CLOTH_BATTLE_DISPHP:31–192。

    BAR 0,1,n：reference/emuera-1824/Emuera/GameData/Expression/ExpressionMediator.cs:121–144；
    預設空格字元為點 Config/ConfigData.cs:130。只讀 REFRESH_CLOTH_DATA 已算的狀態，不重算耐久。
    """
    st,out,c=ctx.state,ctx.out,tc(ctx);v=c.tcvarn;cl=st.temp.cloth
    outer_id=c.cflag[40 if c.cflag[1]==0 else 41]
    outer="◆"+costume_name(ctx,st.target) if costume_name(ctx,st.target) else "◆アウター無し"
    inner="◇（下着兼用）" if cl[NO_INNER] and v[24]>=0 else "◆"+inner_name(ctx,st.target) if c.cflag[42] else "◆インナー無し"
    width=max(cp932_len(outer),cp932_len(inner))+2
    out.printl()
    for inside,label,mx,cur,pct,threshold,cid in ((False,outer,v[20 if c.cflag[1]==0 else 22],v[21 if c.cflag[1]==0 else 23],cl[OUTER_PER],cl[OUTER_DEF],outer_id),
        (True,inner,v[24],v[25],cl[INNER_PER],cl[INNER_DEF],c.cflag[42])):
        warning=(255,123,0) if pct<threshold else (255,255,0) if pct<threshold+div(100-threshold,2) else None
        out.reset_color()
        if mx<0:
            if inside and cid==400 or not inside and v[41] and cid==199:out.set_color((255,128,192))
            out.print(format_percent(label,width,True)+"[.....]（─）"+(" " if not inside else ""))
        elif inside and cl[NO_INNER]:
            if v[41] and outer_id==199:out.set_color((255,128,192))
            elif v[20 if c.cflag[1]==0 else 22]>=0:
                if v[21 if c.cflag[1]==0 else 23]==0:out.set_color((255,0,0))
                elif cl[OUTER_PER]<cl[OUTER_DEF]:out.set_color((255,123,0))
                elif cl[OUTER_PER]<cl[OUTER_DEF]+div(100-cl[OUTER_DEF],2):out.set_color((255,255,0))
            out.print(format_percent(label,width,True))
        elif mx==0:
            # :62 與 :64 原文外衣分支仍看 CFLAG40，即使已變身。
            exists=c.cflag[42 if inside else 40]!=0
            out.set_color((255,0,0) if exists else (123,123,123))
            out.print(format_percent(label,width,True)+"[...............]（なし）")
        else:
            if cur<=0:warning=(255,0,0)
            if warning:out.set_color(warning)
            out.print(format_percent(label,width,True)+"₍")
            rgb=(244,0,0) if inside and cur<=0 else warning or (40,70,210)
            color_bar(out,0 if inside and cur<=0 else cur,mx,15,*rgb,-160,10,18,6,2,"▮","▮")
            if warning:out.set_color(warning)
            out.print("₎")
            out.print(f"（{format_curly(max(cur,0),3)}/{format_curly(mx,3)}）" if inside else f"（{max(cur,0)}/{mx}）")
        out.printl();out.print("　")
        # 純衣裝標籤由既有 catalog 讀原文；測試 NullNarration 不產生標籤。
        from ...text import NullNarrationService
        run = getattr(ctx.narration,"run_function",None)
        if not run or not run(ctx,"CLOTH_CUSTOMIZE_OPTION_DRAW",[cid,st.target]):
            if not isinstance(ctx.narration,NullNarrationService):
                raise NotImplementedError(f"CLOTH_CUSTOMIZE_OPTION_DRAW({cid}) 顯示無法執行")
            out.printl()
        if not inside:out.reset_color()
    st.result[0]=0


def _ex_stock(ctx,mode):
    """CHARA_STATUS.ERB@STATUS_PRINT_EX:1156–1343，五格與消費預告。"""
    out,c=ctx.out,tc(ctx);v=c.tcvarn
    out.set_bold();out.set_italic()
    value=v[5] if mode==1 else v[4]
    count=div(value,100)
    if mode==2:out.set_color((64,64,64));out.print("□□□□□ ")
    elif mode==1 or 0<=count<=5:
        for i in range(min(max(count,0),5)):
            threshold=(-500+i*100) if mode==1 else -(count-i)*100
            shade=(210+i*10,210+i*10,80+i*10) if mode==1 else ((160,170,180,200,220)[i],)*3
            out.set_color((255,255,0) if v[6]<=threshold and c.cflag[1]!=2 else shade);out.print("■")
        out.set_color((128,128,128));out.print("□"*max(0,5-count)+" ")
    out.reset_color();_regular(out)


def status_gauges(ctx):
    """CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:110–205；AIR:1347–1472；CHARGE:1477–1525。"""
    from .train import status_charge_limit
    st,out,c=ctx.state,ctx.out,tc(ctx);v=c.tcvarn
    if c.cflag[1]==2:
        out.print("S.P.　");_ex_stock(ctx,1);out.print("　₍")
        a=div(24*(500+(500-v[5])*4),500);b=div(15*(500+(500-v[5])*4),500)
        color_bar(out,v[5],500,20,128,128,180,-100,a,a,b,1,"▮","▮");out.print("₎　")
    else:
        out.print("E.X.　")
        broken=get_battle_situation(st,"EX不可")==1
        _ex_stock(ctx,2 if broken else 0);out.print("　₍")
        if broken:
            for token in ("▮▮▮","B","▮▮","R","▮▮","E","▮▮","A","▮▮","K","▮▮▮▮"):
                out.set_color((64,64,64) if "▮" in token else (192,64,64));out.print(token)
            out.reset_color()
        else:
            part=mod(v[4],100) if v[4]<500 else 100
            a=div(15*(100+(100-part)*3),100);b=div(14*(100+(100-part)*3),100)
            color_bar(out,part,100,20,64,64,80,-100+80*(v[4]>=100),a,a,b,1,"▮","▮")
        out.print("₎　")
    out.print("　")
    for bit,label,colors in ((0,"攻",((255,180,0),(255,120,30),(255,60,60))),(1,"防",((0,180,255),(30,120,255),(60,60,255)))):
        if v.get_bit(3,bit):
            out.set_bold()
            for token,rgb in zip(("E","X",label+"　"),colors):
                if token==label+"　":out.set_italic()
                out.set_color(rgb);out.print(token)
            out.reset_color();_regular(out)
    if c.cflag[1]==2 and v[3]&3:out.print("ＳＰ変身時間"+"↓"*int(v.get_bit(3,0))+"↓"*int(v.get_bit(3,1)))
    out.printl();out.set_bold();out.print("AIR. ");out.set_italic()
    slot=ctx.data.index_of("BASE","空中ダッシュ")
    for i in range(8):
        if c.maxbase[slot]>i:
            empty=c.base[slot]<i+1
            rgb=(128,128,128) if empty else (255,255,0) if c.base[slot]-int(v.get_bit(216,0))==i else (220,220,220)
            out.set_color(rgb);out.print("□" if empty else "■");out.reset_color()
        else:out.print("　")
    _regular(out)
    # 恰一次計算，維持 PALAM／衣裝顯示後的原呼叫次序。
    status_charge_limit(ctx)
    p=percent_cal(c.base[0]+c.base[1]+c.cflag[99]*150,c.maxbase[0]+c.maxbase[1])
    threshold=80 if 0<=p<=39 else 100 if 40<=p<=74 else 120
    charged=percent_cal(v[205],v[206])
    rgb=(60,75,215) if charged<=threshold else (255,255,0) if charged<=threshold+20 else (255,123,0) if charged<=threshold+40 else (255,0,0)
    if charged>threshold:out.set_color(rgb)
    out.set_bold();out.print("CHARGE.");out.set_italic();out.print("₍")
    color_bar(out,v[205],v[206],20,*rgb,-160,10,18,6,2,"▮","▮")
    if charged>threshold:out.set_color(rgb)
    out.print("₎");_regular(out);out.print(f"（{format_curly(v[205],5)}/{format_curly(v[206],5)}）");out.reset_color()


def show_base(ctx):
    """CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:18–205。"""
    from .palam_display import show_train_palam_status
    from .core import fstyle_name
    st,out,c=ctx.state,ctx.out,tc(ctx)
    out.drawline();out.printl()
    name=c.name if c.cflag[1]==0 else print_transname(st,st.target)
    head=f"{name} Lv.{format_curly(c.abl[ctx.data.index_of('ABL','レベル')],4,True)}"
    width=cp932_len(head)
    head+="性別："+("男性" if not is_female(ctx.data,c) else "❤" if t(ctx,c,"触手の虜") else "女性")+" "
    if t(ctx,c,"変身能力")==1 and c.cflag[1]==0:
        if t(ctx,c,"変身時ＴＳ")<1 or get_battle_situation(st,"奇襲")==0:head+="　<<未変身>>"
        else:head+="　<<未変身・"+("準備中" if st.tflag[0]<5 else "準備完了")+">>"
    out.printl(format_percent(head,46,True));out.print(format_percent(" ",width,True));status_feat(ctx)
    show_train_palam_status(ctx,"上部");out.printl()
    good=[t(ctx,c,n+"距離得意") for n in ("近","中","遠")]
    bad=[t(ctx,c,n+"距離苦手") for n in ("近","中","遠")]
    scores=[3*good[i]-2*bad[i]-sum(good) for i in range(3)]
    signs=["◎" if x>=1 else "×" if x< -2 else "△" if x< -1 else "○" for x in scores]
    out.printl(format_percent("　",46,True)+"　距離適性："+" ".join(f"[{n}距離{mark}]" for n,mark in zip(("近","中","遠"),signs)))
    colorsentence_bar(out,"体力",6,c.base[0],c.maxbase[0],20)
    out.print_plain(" スタイル：")
    for d in (1,2,3):out.print(f"<< {fstyle_name(ctx,st.target,d)} >> ")
    out.printl();colorsentence_bar(out,"気力",6,c.base[1],c.maxbase[1],20)
    support=calc_chisei_shien(ctx,0,registers=True)
    enemy=st.charas[st.flag[111]].maxbase[13] if enemy_type_check(st,"AKUOTI") else int(display_enemy_access(ctx,"CHISEI"))
    ratio=div(100*support,enemy)
    if get_battle_situation(st,"支援無効"):
        out.set_color((255,0,0));out.print(" 戦闘支援効果：支援不可");out.reset_color()
    elif st.flag[43]:out.print(f" 戦闘支援効果：(+ {ratio}％)")
    out.printl();colorsentence_bar(out,"性耐性",6,c.base[2],c.maxbase[2],20);out.printl()
    if t(ctx,c,"ふたなり")>0 or not is_female(ctx.data,c) and t(ctx,c,"未熟")!=1:
        colorsentence_bar(out,ctx.data.names['BASE'][20],6,c.base[20],c.maxbase[20],10);out.printl()
    if t(ctx,c,"母乳体質")>0:
        colorsentence_bar(out,ctx.data.names['BASE'][21],6,c.base[21],c.maxbase[21],10);out.printl()
    cloth_durability(ctx);out.reset_color();status_gauges(ctx)
    st.result[0]=0


def enemy_bar(ctx,name,cur,mx):
    """ERB/汎用関数/コモン関数.ERB@COLORSENTENCE_ENEMYBAR:146–190。"""
    st,out=ctx.state,ctx.out
    akuoti=enemy_type_check(st,"AKUOTI")
    if name=="敵体力":
        colorsentence_barcolor(out,mx,20)
        if st.flag[73]>0:out.reset_color();out.print("人数")
        else:out.print("敵体力" if akuoti else ctx.data.str_defaults.get(2500,"")+"体力")
    rgb={"敵体力":(215,105,30),"敵射精":(215,180,105),"敵絶頂":(250,120,250)}[name]
    out.print("₍");color_bar(out,cur,mx,20,*rgb,-160,10,18,6,2,"▮","▮");out.print("₎")
    known_cur=st.flag[999]==1 or st.flag[20]>=50 or akuoti
    known_max=st.flag[999]==1 or st.flag[20]>=25 or akuoti
    out.print("（"+(format_curly(cur,5) if known_cur else "？？？")+"/"+(format_curly(mx,5) if known_max else "？？？")+"）")
    out.reset_color();st.result[0]=0


def _forecast_number(ctx,value):
    """ERB/ゲーム内_戦闘処理/FORECAST.ERB@FORECAST_OUTPUT_NUM:325–342。"""
    from .train import _forecast_color
    v,out=tc(ctx).tcvarn,ctx.out
    if v[0]==0:value=-1
    out.set_color((48,48,48) if value==-1 else _forecast_color(value))
    out.print(" ―" if v[0]==0 else " ？" if value==-1 else format_curly(value,3));out.reset_color()


def show_distance_window(ctx):
    """ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_DISTANCE_WINDOW:510–759；無 RAND。"""
    st,out,c=ctx.state,ctx.out,tc(ctx);v=c.tcvarn
    dist={0:0,1:3,2:9,3:21}.get(v[0],0)
    if v[0] and mod(st.day[0]+st.tflag[0],4)==0:dist-=1
    elif v[0] and mod(st.day[0]+st.tflag[0],4)==1:dist+=1
    noair=get_battle_situation(st,"空中不可");nofar=get_battle_situation(st,"遠距離不可")
    airgood=t(ctx,c,"空中得意")
    def mark():
        out.set_color("#ff69b4" if is_female(ctx.data,c) else "#0000ff")
        out.print("♀" if is_female(ctx.data,c) else "♂");out.reset_color()
    if v[0]==0:out.set_color("#ff69b4")
    if noair:
        out.printl("┏"+"┳"*20+"┓");out.printl("┣"+"╋"*20+"┫【危険予測】")
        out.print("┣┻┻┻┻┻┻┻┻┻┻╋╋╋╋╋╋┻┻┻┻┫" if nofar else "┣"+"┻"*20+"┫")
    else:
        out.printl("┏"+"━"*20+"┓")
        if not airgood:out.printl("┃"+"　"*20+"┃【危険予測】")
        out.print("┃"+" "*max(dist+7,0))
        if v.get_bit(216,1):mark()
        else:out.print("　")
        out.print(" "*max(31-dist,0)+"┃")
        if v[0]==0:out.set_color("#ff69b4")
        if airgood:
            out.printl("【危険予測】")
            out.print("┃　　　　　　　　　　┣╋╋╋╋┻┻┻┻┻┫" if nofar else "┃"+"　"*20+"┃")
    out.reset_color();out.print(" 空:")
    if noair:out.set_color((128,128,128));out.print("---");out.reset_color()
    else:_forecast_number(ctx,0 if v[0]==0 else v[33])
    out.printl(" %")
    if v[0]==0:out.set_color("#ff69b4")
    out.print("┃ ");out.set_color("#ff69b4" if v[0]>0 else "#ffa500");out.print("≪")
    if enemy_type_check(st,"AKUOTI")==0:
        name=str(display_enemy_access(ctx,"GETNAME"))
    else:name=print_transcallname(st,st.flag[111])
    # SUBSTRING(0,1) 包含跨過第1byte的整字：reference/emuera-1824/Emuera/_Library/LangManager.cs:40–82。
    out.print(name[:1])
    if v[0]==0:
        out.reset_color();mark();out.set_color("#ffa500")
    out.print("≫");out.reset_color()
    out.print("".join("_" if n%2==0 else "-" for n in range(max(dist,0))))
    out.set_color("#ff69b4")
    if v[0]==0:out.reset_color()
    elif not v.get_bit(216,1):mark()
    else:out.print("-_" if dist%2 else "_-")
    out.reset_color()
    out.print("".join("_" if n%2 else "-" for n in range(max((11 if nofar else 22)-dist,0))))
    if nofar:
        if v[0]==0:out.set_color("#ff69b4")
        out.print("┣╋╋╋╋┫")
    else:out.print(" ")
    print_distance(ctx)
    if v[0]==0:out.set_color("#ff69b4")
    out.print("┃");out.print_plain(" ");out.reset_color()
    for label,k in (("近:",30),(" 中:",31),(" 遠:",32)):
        out.print(label);_forecast_number(ctx,0 if v[0]==0 else v[k]);out.print(" %")
    support=calc_chisei_shien(ctx,0,registers=True)
    enemy=st.charas[st.flag[111]].maxbase[13] if enemy_type_check(st,"AKUOTI") else int(display_enemy_access(ctx,"CHISEI"))
    accuracy=div(160*(c.maxbase[13]+support),c.maxbase[13]+support+enemy)+96
    rank,rgb=("－",(105,105,105)) if v[0]==0 else next((label,color) for low,label,color in ((220,"Ｓ",(250,250,0)),(200,"Ａ",(250,90,0)),(160,"Ｂ",(0,120,250)),(120,"Ｃ",(0,250,120)),(80,"Ｄ",(250,0,250)),(-10**20,"Ｅ",(120,120,120))) if accuracy>=low)
    out.print("　予測精度：");out.set_bold();out.set_color(rgb);out.print(rank);_regular(out);out.reset_color();out.printl()
    if v[0]==0:out.set_color("#ff69b4")
    out.printl("┗"+"━"*20+"┛");out.reset_color();st.result[0]=0


def status_signs(ctx):
    """ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS:18–132。"""
    from .core import KIZETU,HATUJOU,MAHI,BETOBETO,KOSHIKUDAKE,KOUKOTSU,HAIRAN,KYOUKOUSOKU
    st,out,c=ctx.state,ctx.out,tc(ctx);v=c.tcvarn
    out.print("状態　　　")
    def item(active,label,rgb):
        out.set_color(rgb)
        if active:out.print(label)
    if not is_female(ctx.data,c):
        item(True,"[オトコ]",(0,180,205));item(t(ctx,c,"男の娘")>0,"[男の娘]",(255,180,180))
    else:
        virgin=t(ctx,c,"処女")
        item(virgin>=-1,"[聖処女]" if virgin>1 else "[処女]" if virgin>0 else "[非処女]",(255,0,255) if virgin>0 else (120,0,120) if virgin==0 else (120,120,120))
        item(any(c.stain[i]&4 for i in (0,1,2)),"[精液まみれ]",(255,255,255))
        item(t(ctx,c,"ふたなり")>0,"[ふたなり]",(255,180,120))
    item(c.cflag[1] in (1,2),"[SP変身]" if c.cflag[1]==2 else "[変身]",(80,80,255))
    item(v[40]>0,"[絶頂禁止]",(255,128,255))
    fatigue=c.cflag[99]
    item(fatigue,f"[疲労 {fatigue}]",(50,255,90) if fatigue<20 else (40,146,73) if fatigue<50 else (30,102,36))
    item(st.flag[70],f"[観衆 {st.flag[70]}人]",(75,150,250))
    item(get_battle_situation(st,"常時撮影"),"[配信中]" if get_battle_situation(st,"配信") else "[撮影中]",(150,75,250))
    item(st.flag[71],f"[動画撮影者 {st.flag[71]}人]",(150,75,250))
    if get_battle_situation(st,"撤退不可")==1 or st.flag[70]+st.flag[71]>0 and config_check_event(st,3)>0:
        item(True,"[撤退不能]",(250,75,15))
    elif st.tflag[0]<8 and config_check_event(st,3)==0 and percent_cal(c.base[0],c.maxbase[0])>50 and percent_cal(c.base[1],c.maxbase[1])>50 and st.flag[45]==0:
        item(True,f"[撤退可能まで {8-st.tflag[0]}ターン]",(250,75,15))
    if v[12]==0:item(True,"[正常]",(150,150,250))
    else:
        for bit,label,rgb in ((KIZETU,"気絶",(250,180,50)),(HATUJOU,"発情",(250,0,150)),(MAHI,"麻痺",(250,250,0)),(BETOBETO,"べとべと",(0,250,150))):
            item(v[12]&bit,f"[{label}]",rgb)
    print_estrus_cycle(st,ctx.data,out,st.target)
    if v[12]:
        for bit,label,rgb in ((KOSHIKUDAKE,"腰くだけ",(150,0,250)),(KOUKOTSU,"恍惚",(255,182,193)),(HAIRAN,"強制排卵",(150,0,250)),(KYOUKOUSOKU,"強拘束",(200,50,50))):
            item(v[12]&bit,f"[{label}]",rgb)
    if t(ctx,c,"避妊結界")>0 and c.base[2]>0:item(True,"[避妊結界]",(200,200,80))
    out.reset_color();out.printl()
