"""醫療室原生流程：ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB。

文字由原檔抽取；此模組手翻分支，不執行 ERB。列表與輸入判斷刻意分開。
"""
import re

from .body import set_profile
from .chara_common import is_female, charatalent
from .drug_text import TEXT
from .era import div, times, format_percent
from .input_request import input_number
from .shop import lb
from .akuoti import dot_after


def _shortline(out):
    """ERB/汎用関数/PRINT_LINE.ERB@SHORTLINE:3–7。"""
    out.printl('――――――――――――――――――――――――――――')


def _t(ctx,c,name):
    return c.talent[ctx.data.index_of('TALENT',name)]


def _set(ctx,c,name,value):
    c.talent[ctx.data.index_of('TALENT',name)]=value


def _say(ctx,*lines,c=None,values=None):
    """抽取文字的固定欄位插值；沒有命令或條件求值。"""
    st=ctx.state
    replacements={'{FLAG:200}':str(st.flag[200]),'{FLAG:201}':str(st.flag[201]),
                  '{MONEY}':str(st.money),'{MONEY / 125}':str(div(st.money,125))}
    if c is not None:
        for key in ('%CALLNAME%','%CALLNAME:RESULT%','%CALLNAME:LOCAL%','%CALLNAME:CCOUNT%','%PRINT_CALLNAME(TARGET)%'):
            replacements[key]=c.callname
        replacements['%CALLNAME:CCOUNT,24,LEFT%']=format_percent(c.callname,24,True)
        for slot in (222,227,241):
            for var in ('RESULT','LOCAL','CCOUNT'):
                replacements[f'{{CFLAG:{var}:{slot}}}']=str(c.cflag[slot])
        replacements['{FLAG:201 + CFLAG:LOCAL:241}']=str(st.flag[201]+c.cflag[241])
        replacements['{CFLAG:RESULT:222 * 20 / 28}']=str(div(c.cflag[222]*20,28))
    replacements.update(values or {})
    for line in lines:
        command,text=TEXT[line]
        for key,value in replacements.items(): text=text.replace(key,str(value))
        text=re.sub(r'%TALENTNAME:(\d+)%',lambda m:ctx.data.names['TALENT'][int(m[1])],text)
        if command.endswith('W'): ctx.out.printw(text)
        elif command.endswith('L'): ctx.out.printl(text)
        elif command=='PRINTPLAIN': ctx.out.print_plain(text)
        else: ctx.out.print(text)


def _eligible(ctx,c,cmd,*,listing=False):
    """@CHARA_LIST_DRUG:456–590／601–1025：顯示條件不是輸入資格。"""
    t=lambda name:_t(ctx,c,name)
    safe=c.cflag[0]==0
    if cmd in (0,2,3,4):
        value=t({0:'触手の虜',2:'母乳体質',3:'寄生',4:'苗床化'}[cmd])
        return safe and (value>0 if listing else value!=0) and (not listing or cmd!=3 or t('共生')<=0)
    if cmd==1:
        a,b=t('ふたなり'),t('変身時ふたなり')
        return safe and ((a in (1,2) or t('変身能力')>0 and b in (1,2)) if listing else not ((a<1 and b<1) or (a>=3 and b>=3)))
    if cmd==5: return safe and ((c.cflag[37]>0 if listing else c.cflag[37]!=0) or c.cflag[38]!=0)
    if cmd in (10,11): return c.cflag[0] in (0,10,11) and is_female(ctx.data,c)
    if cmd==12: return c.cflag[0] in (0,10) and t('妊娠') in (1,3,5)
    if cmd==14: return safe and (is_female(ctx.data,c) if listing else t('妊娠') not in (1,3,5))
    if cmd==15: return (safe and is_female(ctx.data,c) and t('ロボっ子')>0) if listing else t('ロボっ子')!=0
    if cmd in (20,21): return c.cflag[32]!=0 and (safe if listing else True)
    if cmd==30: return safe and (t('未熟')==1 or (t('性徴停滞')>0 if listing else t('性徴停滞')!=0))
    if cmd==31: return safe and ((0<c.cflag[225]<15 and t('性徴停滞')==0) if listing else c.cflag[225]!=0 and c.cflag[225]<=14 and t('性徴停滞')<=0)
    if cmd==51: return safe and t('四肢欠損')>0 and (t('毀滅倒計時')<1 if listing else True)
    return False


def _inspect(ctx,c):
    """@CHARA_LIST_DRUG:729–814：精密檢查會將未發現的狀態4更新為5。"""
    t=lambda name:_t(ctx,c,name)
    if t('寄生')>0 and t('苗床化')>0: _say(ctx,730,731,c=c)
    elif t('寄生')>0: _say(ctx,733,734,c=c)
    elif t('苗床化')>0: _say(ctx,736,737,c=c)
    elif t('未熟')==2: _say(ctx,739 if t('ロボっ子') else 742,740 if t('ロボっ子') else 743,c=c)
    elif t('未熟')==1: _say(ctx,745,746,c=c)
    else: _say(ctx,748,749,c=c)
    _say(ctx,751)
    p=t('妊娠'); age=c.cflag[222]
    if p>0: _say(ctx,753)
    if p==4:
        _say(ctx,755,c=c); _set(ctx,c,'妊娠',5); p=5
    if p in (1,3):
        _say(ctx,760 if p==1 else 771,c=c)
        _say(ctx,(762 if p==1 else 773) if t('苗床化')>0 else (764 if p==1 else 775) if age<7 else (766 if p==1 else 777) if c.cflag[0]==10 else (768 if p==1 else 779),c=c)
    elif p==5:
        _say(ctx,782,c=c)
        line=next(line for bound,line in ((5,784),(8,787),(11,790),(12,793),(22,796),(36,799),(50,802),(54,805),(10**30,808)) if age<bound)
        _say(ctx,line,line+1,811,c=c)
    else: _say(ctx,813,c=c)


def _maintenance(ctx,c):
    """@CHARA_LIST_DRUG:873–958，原文[2]只顯示，完整維修實際接受[0]。"""
    st,out=ctx.state,ctx.out
    while True:
        lb(out); _say(ctx,875); _shortline(out); _say(ctx,877,c=c)
        for line,blocked in ((880,c.cflag[99]<1 or c.cflag[99]>=20),(884,c.cflag[99]<10 or c.cflag[99]>=30),(888,c.cflag[99]<20)):
            if blocked: out.set_color((128,128,128))
            _say(ctx,line); out.reset_color()
        if is_female(ctx.data,c) and _t(ctx,c,'未熟')>=0: _say(ctx,891 if _t(ctx,c,'未熟')==0 else 893)
        _say(ctx,895)
        while True:
            r=yield from input_number(ctx)
            if r==999: _say(ctx,956); return
            fatigue=c.cflag[99]
            amount=0
            if r==0 and 0<fatigue<20: cost,amount,line=500,5,909
            elif r==1 and 10<fatigue<30: cost,amount,line=1500,20,924
            elif r==0 and fatigue>20: cost,amount,line=5500,fatigue,937
            elif r==3 and is_female(ctx.data,c):
                dot_after(ctx); out.printl()
                old=_t(ctx,c,'未熟'); _set(ctx,c,'未熟',2 if old==0 else 0)
                _say(ctx,945 if old==0 else 949,946 if old==0 else 950,c=c); out.printw(); break
            else: continue
            if st.money<cost: _say(ctx,900); continue
            st.money-=cost; c.cflag[99]=max(0,fatigue-amount)
            dot_after(ctx); out.printl()
            _say(ctx,line,c=c); out.printw(); break


def _choose(ctx,cmd):
    st,out=ctx.state,ctx.out
    _say(ctx,449,450)
    for who,c in enumerate(st.charas):
        if who==st.master or not _eligible(ctx,c,cmd,listing=True): continue
        if cmd==14:
            _say(ctx,552,c=c,values={'{CCOUNT}':who})
        else:
            out.print(f'[{who}] {c.callname}')
            if cmd==1:
                for name,lines in (('ふたなり',(467,469)),('変身時ふたなり',(471,473))):
                    value=_t(ctx,c,name)
                    if value in (1,2) and (name=='ふたなり' or _t(ctx,c,'変身能力')>0): _say(ctx,lines[value-1])
            if cmd==5:
                for form in (0,1):
                    n=next((i for i,name in enumerate(('貧乳','奇乳','魔乳','超乳','爆乳','巨乳')) if charatalent(ctx.data,c,form,name)),6)
                    _say(ctx,(500,502,504,506,508,510,512)[n]+(15 if form else 0))
        out.printl()
    _say(ctx,592)
    while True:
        who=yield from input_number(ctx)
        if who==999: return 999
        if not 1<=who<st.charanum or not _eligible(ctx,st.charas[who],cmd): _say(ctx,598); continue
        c=st.charas[who]; t=lambda name:_t(ctx,c,name)
        if cmd in (0,2,3,4):
            name={0:'触手の虜',2:'母乳体質',3:'寄生',4:'苗床化'}[cmd]
            st.flag[200]-=5 if cmd==0 else 2; _set(ctx,c,name,0)
            if cmd==0:
                c.abl[ctx.data.index_of('ABL','触手中毒')]=0
                for name in ('欲情','屈服'): c.juel[ctx.data.index_of('JUEL',name)]=0
            _say(ctx,*{0:(611,612,613),2:(643,644),3:(653,654),4:(663,664)}[cmd],c=c)
        elif cmd==1:
            st.flag[200]-=2
            if t('ふたなり') in (1,2): _say(ctx,622 if t('ふたなり')==2 else 624,627,c=c); _set(ctx,c,'ふたなり',0)
            if t('変身時ふたなり') in (1,2):
                if t('変身能力')>0: _say(ctx,632,c=c)
                _set(ctx,c,'変身時ふたなり',0)
        elif cmd==5:
            st.flag[200]-=2; _say(ctx,672)
            # reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:953–972：RAND(5,20)不含20。
            if t('膨乳改造値')>0: _set(ctx,c,'膨乳改造値',max(0,t('膨乳改造値')-5-st.rng.rand(15)))
            if c.cflag[37]==0 and c.cflag[38]>0:
                _set(ctx,c,'変身時胸サイズ変動',t('変身時胸サイズ変動')-1); c.cflag[38]-=1; _say(ctx,681)
            elif c.cflag[37]>0:
                if c.cflag[38]<0:
                    _set(ctx,c,'変身時胸サイズ変動',t('変身時胸サイズ変動')+1); c.cflag[38]+=1
                if t('巨乳')-t('貧乳')>0: _set(ctx,c,'巨乳',t('巨乳')-1)
                else: _set(ctx,c,'貧乳',min(t('貧乳')+1,2))
            c.cflag[37]=max(c.cflag[37]-1,0)
            _say(ctx,697 if c.cflag[37]>0 or c.cflag[38]!=0 else 699,c=c)
            set_profile(ctx.data,c,st.result)
        elif cmd==10:
            st.money-=50
            dot_after(ctx,2)
            if t('妊娠')==0 or t('妊娠')==4 and c.cflag[222]<3: _say(ctx,712,713)
            else:
                _say(ctx,715)
                if t('妊娠')==4: _say(ctx,717,c=c); _set(ctx,c,'妊娠',5)
        elif cmd==11: st.money-=250; dot_after(ctx,2); _inspect(ctx,c)
        elif cmd==12:
            st.money-=7000; _set(ctx,c,'妊娠',0)
            for slot in (221,222,226,227,228,230,232,233): c.cflag[slot]=0
            dot_after(ctx,2)
            _say(ctx,832,c=c)
            if c.cflag[0]==10:
                from .party import recover_to_party
                _say(ctx,834,c=c); recover_to_party(ctx,who)
                # RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY:1–23無RETURN，末端RESULT=0。
                # :838仍以RESULT取索引，因此入院者的疲勞實際加在MASTER。
                st.result[0]=0
            st.charas[st.result[0]].cflag[99]+=25
        elif cmd==14:
            _say(ctx,846,847,848,c=c)
            while True:
                count=yield from input_number(ctx)
                if 0<=count<=st.flag[201]+c.cflag[241]:
                    st.flag[201]+=c.cflag[241]-count; c.cflag[241]=count
                    _say(ctx,856 if count==0 else 858,c=c,values={'{RESULT}':count}); break
                if count<0 or count==c.cflag[241]: _say(ctx,861,c=c); break
                _say(ctx,863)
        elif cmd==15: yield from _maintenance(ctx,c)
        elif cmd==20:
            st.flag[200]-=10; c.cflag[30]=c.cflag[32]=0; _say(ctx,969,970,c=c)
        elif cmd==21:
            if c.cflag[32]<500000000000000000: _say(ctx,977,978)
            else:
                st.money-=1250
                for slot in (30,32): c.cflag[slot]=times(c.cflag[slot],'0.10')
                _say(ctx,983,984,c=c)
        elif cmd==30:
            st.flag[200]-=1; _say(ctx,993)
            if t('未熟')==1:
                _say(ctx,998,1002 if is_female(ctx.data,c) else 1000,c=c); _set(ctx,c,'未熟',-1)
            if t('性徴停滞')>0: _say(ctx,1007,c=c); _set(ctx,c,'性徴停滞',0)
        elif cmd==31: st.flag[200]-=1; _set(ctx,c,'性徴停滞',1); _say(ctx,1018,1019,c=c)
        elif cmd==51:
            st.money-=25000; st.flag[200]-=40
            _set(ctx,c,'四肢欠損',0); _set(ctx,c,'共生',1)
            _say(ctx,1031,1032,1033,1034,1035,1036,1037,c=c)
        out.printw()
        return 0


def _join_robot(ctx):
    """@DRUG_PREPARATION:280–435；個別編輯依AGENTS走不改設定直接[99]路徑。"""
    from .opening import chara_make_initialize, chara_make_finalize, decode_weapon_data
    from .chara_common import baseup_cal_shield, syuzoku_check
    from .firstsetting import feat_select_ui, set_feat_default
    from .body import generate_char_size, top_under, cup_size
    st,out,data=ctx.state,ctx.out,ctx.data
    lb(out); _say(ctx,286); _shortline(out); _say(ctx,288,289,290,291,292,293)
    while True:
        sex=yield from input_number(ctx)
        if sex==99: return
        if sex in (0,1): break
    _say(ctx,297); lb(out); dot_after(ctx); _say(ctx,300,301)
    target=st.target; st.money-=50000
    c=st.add_chara(data,0); who=st.charanum-1; st.target=who
    for name,value in (('感情乏しい',1),('未熟',2),('口上設定',1),('初期経験設定不可',1),('ロボっ子',1)):
        _set(ctx,c,name,value)
    if sex==1: _set(ctx,c,'オトコ',1); c.name='汎用キャラ(♂)'
    # FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–34／318–353。
    # DEVIATION: 沿用角色製作UI跳過，狀態走原作[99]預設確認；不提供手動編輯。
    items={i:st.item[i] for i in range(100,700) if i in data.items and data.items[i].name}
    for i in items: st.item[i]=1
    if c.cflag[240]==0: chara_make_initialize(st,data,who)
    for dist in (1,2,3):
        if c.cstr[14+dist]: st.result[0]=decode_weapon_data(data,st,who,dist)
        c.cstr[14+dist]=''
    # :112–122的顯示呼叫仍產生RESULT:1–7／RESULTS殘值。
    sizes=generate_char_size(data,c,0,st.result)
    if sizes[4]>0:
        difference,under=top_under(data,c,0)
        st.result[0],st.result[1]=difference,under
        st.result[0],st.results[0]=cup_size(st.result[0])
    st.result[0]=99
    baseup_cal_shield(data,st,who)
    for i in range(4): st.savestr[i]=''
    for i in range(100,700): st.item[i]=items.get(i,0)
    race=syuzoku_check(c); st.result[0]=race
    _say(ctx,325,326,327,328,c=c)
    while True:
        answer=yield from input_number(ctx)
        if answer==0:
            # 這個入口沒有ADD_CHILD專有的RACE==9預選；實際種族是201以上。
            yield from feat_select_ui(ctx,who,race); break
        if answer==1: _say(ctx,408,409,c=c); break
        if answer==2:
            set_feat_default(ctx,who,race); set_profile(data,c,st.result); _say(ctx,415,416); break
    lb(out); dot_after(ctx); _say(ctx,423,424,425,c=c,values={'{TARGET}':who})
    chara_make_finalize(st,data,who)
    st.result[0]=0  # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    _say(ctx,429); st.target=target


def drug_preparation_gen(ctx):
    """@DRUG_PREPARATION:4–440。ROBO／LOCAL:1於重畫累加，僅進入函式時清零。"""
    st,out=ctx.state,ctx.out
    robo=held=0
    while True:
        robo+=sum(_t(ctx,c,'ロボっ子')>0 for c in st.charas)
        lb(out); _say(ctx,18,19,20)
        _say(ctx,22 if st.rng.rand(4)==0 else 24 if st.rng.rand(3)==0 else 26 if st.rng.rand(2)==0 else 28)
        _say(ctx,30,31,32); out.drawline()
        for line in (34,35,36,37,38,39,40,41,42,43,44,45): _say(ctx,line)
        if robo>0: _say(ctx,47)
        for line in (48,49,50,51,52,53,54): _say(ctx,line)
        from .opening import game_option
        from ..state.constants import GameOption
        join=st.charanum<=29 and not game_option(st,GameOption.SOLO)
        if not join: out.set_color((128,128,128))
        _say(ctx,58); out.reset_color(); _say(ctx,60,61)
        while True:
            cmd=yield from input_number(ctx)
            if cmd==999: st.result[0]=999; return 999
            parts={0:5,1:2,2:2,3:2,4:2,5:2,20:10,30:1,31:1}
            money={10:50,11:500,12:7000,13:125,21:1250}
            if cmd in parts and st.flag[200]<parts[cmd]: _say(ctx,68); break
            if cmd in money and st.money<money[cmd]: _say(ctx,140); break
            if cmd in parts or cmd in (10,11,12,21):
                st.result[0]=yield from _choose(ctx,cmd); break
            if cmd==13:
                _say(ctx,143,144,145,146,147,148)
                count=yield from input_number(ctx)
                if count>0 and count*125<=st.money:
                    _say(ctx,152,153,154,values={'{LOCAL}':count,'{125 * LOCAL}':125*count})
                    while True:
                        answer=yield from input_number(ctx)
                        if answer in (0,1): break
                    if answer==0: st.money-=125*count; st.flag[201]+=count
                elif count>0: _say(ctx,166)
                break
            if cmd==14:
                held+=sum(max(c.cflag[241],0) for i,c in enumerate(st.charas) if i!=st.master)
                if st.flag[201]+held<1: _say(ctx,178)
                else: st.result[0]=yield from _choose(ctx,14)
                break
            if cmd==15 and robo>0: st.result[0]=yield from _choose(ctx,15); break
            if cmd==51:
                if st.flag[54]<5: _say(ctx,221,222); break
                _say(ctx,225,226,227,228,229,230,231)
                # DEVIATION: 已授權修復:232–276的確認死循環；1拒絕手術返回，錯值重讀。
                # :245–266明示替代NPC提案尚未移植，維持停用；不宣稱返回是作者最終設計。
                while True:
                    answer=yield from input_number(ctx)
                    if answer in (0,1): break
                    _say(ctx,275)
                if answer==1: break
                if st.money<25000: _say(ctx,236)
                elif st.flag[200]<40: _say(ctx,239)
                else: st.result[0]=yield from _choose(ctx,51)
                break
            if cmd==100 and join:
                if st.money<50000: _say(ctx,282)
                else: yield from _join_robot(ctx)
                break
            _say(ctx,439)
