"""W02：種族、變身能力、基礎點選單；原文路徑見各函式。"""
from .body import generate_char_size, set_profile, top_under, cup_size
from .chara_common import talent, is_female, feat_bonus, charatalent
from .character_build_text import TEXT
from .era import div, mod, times, limit, format_percent
from .firstsetting import feat_able
from .input_request import input_number, WaitInputRequest


def _lines(ctx,key,*numbers):
    for n in numbers:ctx.out.printl(TEXT[key,n])


def _info(ctx,name,number):
    # 真catalog缺函式／執行失敗都停止；只有Null fixture顯示函式名。
    ok=ctx.narration.run_function(ctx,name,[number])
    if not ok:
        from ..text import NullNarrationService
        catalog=getattr(ctx.narration,'catalog',None)
        if catalog is not None or not isinstance(ctx.narration,NullNarrationService):
            raise RuntimeError(f'{name} catalog 缺少函式或無法執行')
        ctx.out.printl(f'〈{name} {number}〉')
    ctx.state.result[0]=0


def _size_results(ctx,c,transformed):
    # CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:239–249：CUP_SIZE留下RESULTS:0。
    values=generate_char_size(ctx.data,c,transformed,ctx.state.result)
    ctx.state.results[0]=cup_size(top_under(ctx.data,c,transformed)[0])[1]
    return values


def race_setting(ctx,who):
    """ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SYUZOKU.ERB@FIRSTSETTING_CHARA_SYUZOKU:4–165。"""
    from .shop import lb
    st,out,data=ctx.state,ctx.out,ctx.data;c=st.charas[who];names=data.names['TALENT']
    while True:
        selected={i for i in range(100,300) if c.talent[1000+i]>0}
        lb(out);_lines(ctx,'R',24,25,26)
        out.printl(f'{who}人目のキャラ 『{c.callname}』 の種族を設定してください')
        for race in range(11):
            if c.talent[201+race]>0:out.set_color('#8080ff')
            out.printl(f'[{race}]'+names.get(201+race,''));out.reset_color()
        while True:
            race=yield from input_number(ctx)
            if 0<=race<=11:break  # :40原作接受未顯示的11。
        selected={i for i in selected if feat_able(ctx,race+201,i+1000)}
        lb(out)
        while True:
            if race==9:selected.add(110)
            out.printl(names.get(race+201,''));out.drawline()
            _info(ctx,'SYUZOKU_INFO',race+201);_lines(ctx,'R',63)
            for i in range(100,300):
                if not feat_able(ctx,race+201,i+1000):continue
                mark='◎ 固定取得' if i==110 and i in selected else '○' if i in selected else '×'
                out.printl(('　★' if i<200 else '　☆')+format_percent(names.get(i+1000,''),22,True)+f' [{i}] {mark}')
            out.printl(f'選択したフィート({len(selected)}/3)')
            if len(selected)>3:out.set_color('#808080')
            _lines(ctx,'R',91);out.reset_color();_lines(ctx,'R',93)
            while True:
                r=yield from input_number(ctx)
                if r==0 and len(selected)<=3 or r==1:break
                if 100<=r<=300 and feat_able(ctx,race+201,r+1000):
                    lb(out);_info(ctx,'FEAT_INFO',r+1000);out.printl()
                    selected.symmetric_difference_update({r});break
            if r in (0,1):break
        if r==1:continue
        break
    for i in range(201,212):c.talent[i]=0
    c.talent[201+race]=1
    out.printl('種族を 『'+names.get(201+race,'')+'』 に設定しました')
    if race==3:
        female=is_female(data,c);k=data.index_of('TALENT','口上設定')
        if female:
            out.printl(f'人工子宮を内蔵させることにより、{c.callname}を妊娠可能にすることができます')
            _lines(ctx,'R',123,124)
        pregnancy_input=female
        while True:
            if pregnancy_input:
                while True:
                    r=yield from input_number(ctx)
                    if r in (0,1):break
                c.talent[data.index_of('TALENT','未熟')]=r*2
                out.printl(f'{c.callname}は妊娠可能になります' if r==0 else f'{c.callname}に妊娠機能を付けません')
            if c.talent[k]==1:break
            _lines(ctx,'R',138,139,140)
            r=yield from input_number(ctx)
            if r==0:c.talent[k]=1;_lines(ctx,'R',144);break
            if r==1:_lines(ctx,'R',147);break
            # :149的GOTO INPUT_LOOP_1，連男性非法值也進此輸入；保留原作。
            pregnancy_input=True
    for i in range(100,300):c.talent[1000+i]=int(i in selected)
    set_profile(data,c,st.result)
    st.results[0]=cup_size(top_under(data,c,1)[0])[1]
    out.printl();out.printl();st.result[0]=0
    return 0


def transformation_setting(ctx,who):
    """ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_CHARA_TRANSABILITY:4–60。"""
    st,out,data=ctx.state,ctx.out,ctx.data;c=st.charas[who]
    out.printl(f'{who}人目のキャラ 『{c.callname}』 の戦闘能力を設定してください')
    _lines(ctx,'T',6,7,8,9)
    while True:
        choice=yield from input_number(ctx)
        if choice in (0,1,2):break
    c.talent[data.index_of('TALENT','変身能力')]=(1,0,-1)[choice]
    from .export_csv import csvbase
    dash=limit(csvbase(ctx,c.no,22)-int(choice==2),0,5)
    c.base[22]=c.maxbase[22]=dash
    values=_size_results(ctx,c,1)
    for slot,value in zip((43,44,45,46,47,48),values[2:]):c.maxbase[slot]=value
    if choice!=0:c.talent[data.index_of('TALENT','変身時ＴＳ')]=0
    _lines(ctx,'T',(25,40,55)[choice])
    out.printw('');yield WaitInputRequest()
    out.printl();st.result[0]=0
    return 0


_GROUPS=((70,'近距離','近距離得意','近距離苦手'),(80,'中距離','中距離得意','中距離苦手'),
         (90,'遠距離','遠距離得意','遠距離苦手'),(100,'空中','空中得意','空中苦手'),
         (110,'回復','回復早い','回復遅い'))
_CONNECTIONS=((120,'噂好きの友人',(0,5)),(130,'警察関係者',(0,10,20)),
              (140,'情報屋',(0,15)),(150,'裕福な実家',(0,10)))
_SHIELDS=('Ｃ結界','Ｖ結界','Ａ結界','Ｂ結界','避妊結界')


def _debug_performance(ctx):
    """STATUS_BONUS:33–91刻意讀TARGET、不是ARG；沿已查TIMES語意。"""
    c=ctx.state.charas[ctx.state.target];t=lambda n:talent(ctx.data,c,n)
    coeffs=(('1.20','0.60','0.85','1.15','0.85','1.10','1.16'),
            ('0.90','1.20','1.25','0.70','0.90','1.10','1.085'),
            ('0.95','1.20','0.95','1.10','1.30','0.80','1.0275'))
    ctx.out.set_color('#696969')
    for n,(value,coeff) in enumerate(zip((250,225,200),coeffs)):
        for j,(_,_,good,bad) in enumerate(_GROUPS[:3]):
            if t(good):value=times(value,coeff[j*2])
            if t(bad):value=times(value,coeff[j*2+1])
        if all(t(good) for _,_,good,_ in _GROUPS[:3]):value=times(value,coeff[6])
        ctx.out.print(f'{_GROUPS[n][1]}性能：{value}　')
    ctx.out.reset_color();ctx.out.printl()


def _bonus_draw(ctx,who,bonuses,high):
    st,out,data=ctx.state,ctx.out,ctx.data;c=st.charas[who]
    t=lambda n:talent(data,c,n);points=div(c.juel[data.index_of('PALAM','修練P')],10)
    out.printl();out.printl(f'{who}人目のキャラ 『{c.callname}』 の基礎値にボーナスを振ってください')
    _lines(ctx,'B',32)
    if st.flag[999]==1:_debug_performance(ctx)
    out.printl(f'ボーナス値　のこり『 +{points} pts』')
    for i,slot in enumerate((0,1,2,10,11,12,13)):
        value=c.base[slot]+feat_bonus(data,c,i)
        out.print(f'{data.names["BASE"][slot]}：{value} → {value+bonuses[i]*(10 if i<2 else 1)}（{bonuses[i]:+}） ')
        for q,delta in enumerate((-5,-1,1,5)):
            if delta<0 and bonuses[i]<=-20 or delta>0 and (bonuses[i]>=high or c.juel[data.index_of('PALAM','修練P')]<=0):out.set_color('#808080')
            out.print(f'[{i*10+q}] {delta:+}　');out.reset_color()
        out.printl()
    for group,label,good,bad in _GROUPS:
        old=2 if t(good) else 0 if t(bad) else 1
        labels=('遅い','普通','早い') if group==110 else ('苦手','普通','得意')
        out.print(f'{label}：{labels[old]} ({(-5,0,15)[old]:+})　')
        for q,s in enumerate(labels):
            if q==old:out.set_color('#ffff00')
            elif (-5,0,15)[q]-(-5,0,15)[old]>points:out.set_color('#808080')
            out.print(f'[{group+q}] {s}　');out.reset_color()
        out.printl()
    count=sum(t(n) for n in _SHIELDS)
    cap=3-int(any(charatalent(data,c,h,'オトコ')>0 for h in (0,1)))
    out.print(f'結界：{count} / {cap} (+{count*5})　')
    for i,n in enumerate(_SHIELDS):
        # :331–370顯示用硬編碼3，實際判定依cap；保留差異。
        if count>2 or points<5 or i==1 and t(_SHIELDS[4])>0 or i==4 and t(_SHIELDS[1])>0:out.set_color('#808080')
        if t(n):out.set_color('#ffff00')
        out.print(f'[{300+i}] {n}　');out.reset_color()
    out.printl();_lines(ctx,'B',375,376)
    for group,n,prices in _CONNECTIONS:
        value=t(n);old=value if group==130 and value in (1,2) else int(bool(value)) if group!=130 else 0
        # STATUS_BONUS:379–474：等級2原名、成本欄寬與按鈕全形數字。
        name='警察上層部' if group==130 and old==2 else n
        padding={120:'',130:'　',140:'　　　',150:'　'}[group]
        out.print(f'{name}{padding}（+{prices[old]:2}）　')
        for q,cost in enumerate(prices):
            if q==old:out.set_color('#ffff00')
            elif cost-prices[old]>points:out.set_color('#808080')
            out.print(f'[{group+q}] '+('なし','＋１','＋２')[q]+'　');out.reset_color()
        out.printl()
    _lines(ctx,'B',479,480,481,482)


def status_bonus(ctx,who):
    """ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_STATUS_BONUS.ERB@FIRSTSETTING_STATUS_BONUS:4–926。

    七格暫存在本次呼叫；JUEL/TALENT即時修改。只有200提交CFLAG，沒有取消。
    """
    st,out,data=ctx.state,ctx.out,ctx.data;c=st.charas[who]
    p=data.index_of('PALAM','修練P');idx=lambda n:data.index_of('TALENT',n)
    t=lambda n:c.talent[idx(n)]
    b=[c.cflag[50+i] for i in range(7)];high=20 if c.cflag[231] else 40
    line=out.linecount
    while True:
        _bonus_draw(ctx,who,b,high)
        r=yield from input_number(ctx)
        if r==200:
            for i in range(7):c.cflag[50+i]=b[i]
            out.printl();out.printl();st.result[0]=1
            return 1
        out.clearline(out.linecount-line)
        obj,change=div(r,10),mod(r,10)
        if r==201:
            c.juel[p]+=sum(b)*10;b=[0]*7
            for _,_,good,bad in _GROUPS:
                for name,refund in ((good,150),(bad,-50)):
                    if t(name):c.talent[idx(name)]=0;c.juel[p]+=refund
            # :547–562刻意只清四種；避妊結界沒有清除或退款。
            for name in _SHIELDS[:4]:
                if t(name):c.talent[idx(name)]=0;c.juel[p]+=50
            for group,name,prices in _CONNECTIONS:
                old=t(name)
                if group==130:
                    if old not in (1,2):continue
                else:old=int(bool(old))
                if old:c.talent[idx(name)]=0;c.juel[p]+=prices[old]*10
        elif 300<=r<=304:
            name=_SHIELDS[r-300]
            if r==301 and t(_SHIELDS[4])>0 or r==304 and t(_SHIELDS[1])>0:continue
            if t(name):c.talent[idx(name)]=0;c.juel[p]+=50
            else:
                cap=3-int(any(charatalent(data,c,h,'オトコ')>0 for h in (0,1)))
                if c.juel[p]>=50 and sum(t(n) for n in _SHIELDS)<cap:
                    c.talent[idx(name)]=1;c.juel[p]-=50
        elif 0<=obj<=6 and 0<=change<=3:
            delta=min((-5,-1,1,5)[change],div(c.juel[p],10))
            if b[obj]+delta>high:delta=high-b[obj]
            if b[obj]+delta<-20:delta=-20-b[obj]
            b[obj]+=delta;c.juel[p]-=delta*10
        elif 7<=obj<=11 and 0<=change<=2:
            _,_,good,bad=_GROUPS[obj-7]
            old=15 if t(good) else -5 if t(bad) else 0
            cost=((-5,0,15)[change]-old)*10
            if c.juel[p]>=cost:
                c.talent[idx(good)]=int(change==2);c.talent[idx(bad)]=int(change==0);c.juel[p]-=cost
        elif 12<=obj<=15:
            group,name,prices=_CONNECTIONS[obj-12]
            if change not in range(len(prices)):continue
            value=t(name);old=value if group==130 and value in (1,2) else int(bool(value)) if group!=130 else 0
            cost=(prices[change]-prices[old])*10
            if c.juel[p]>=cost:c.talent[idx(name)]=change;c.juel[p]-=cost
        elif r==999:
            # FOR終值只在開始求值：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1731–1743。
            # 原文無上限檢查、無reset，原有b之上累加，尾數保留。
            for _ in range(max(0,div(c.juel[p],10))):b[st.rng.rand(7)]+=1;c.juel[p]-=10
