"""氏名編輯：FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME:496–686／NAME_RANDOM:690–1021。"""
from .character_editor_text import TEXT
from .input_request import input_number, inputs
from .creation_menu import wait
from .weapon_customize import _byte_len, _substring


def character_name(ctx, who):
    st,out=ctx.state,ctx.out;c=st.charas[who];default=ctx.data.charas[c.no]
    family_input=''
    # @FIRSTSETTING_CHARA_NAME:506、636、671：只清除此函式入口後的行。
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–500。
    entry_line=out.linecount
    while True:
        out.printl(f'{who}人目のキャラの氏名を設定してください')
        out.printl(TEXT[509])
        out.printl(TEXT[510])
        out.printl(TEXT[512]);out.printl(TEXT[1078])
        if default.callname!='汎用キャラ':out.printl(f'[2]デフォルト名を使う（{default.name}）')
        if c.cstr[10]:out.printl(TEXT[517])
        if st.charanum>=3:out.printl(TEXT[519])
        out.printl(TEXT[1134])
        while True:
            r=yield from input_number(ctx)
            if r in (0,1,3,99) or r==2 and default.callname!='汎用キャラ' or r==4 and st.charanum>=3:break
        if r==99:st.result[0]=99;return 99
        if r==0:
            while True:
                yield from random_character_name(ctx,who)
                out.printl(f'キャラの氏名を 『{st.results[0]}』 とします。よろしいですか？')
                out.printl(TEXT[530]);out.printl(TEXT[531])
                if c.callname!='汎用キャラ':out.printl(f'[2]変更しない（{c.name}）')
                while True:
                    q=yield from input_number(ctx)
                    if q in (0,1,2):break
                if q==0:continue
                if q==1:
                    c.name=st.results[0];c.cstr[200]=st.results[1];c.cstr[10]=st.results[2]
                    out.printl(f'キャラの氏名を 『{c.name}』 に設定しました')
                else:c.cstr[200]=c.callname
                break
        elif r==1:
            out.printl(TEXT[552])
            given=c.cstr[200] or c.callname; family=''
            # reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2095–2107、2222–2279。
            # UNVERIFIED: .NET CurrentCulture IndexOf 的少見等價字比對沿既有W08字串相容性項。
            index=c.name.find(c.callname) if c.name else -1
            st.result[0]=_byte_len(c.name[:index]) if index>0 else index
            if index!=-1 and _byte_len(c.name)!=_byte_len(c.callname):
                family=_substring(c.name,_byte_len(c.callname)+1,_byte_len(c.name)) if index==0 else _substring(c.name,0,_byte_len(c.name)-_byte_len(c.callname)-1)
                st.results[0]=family
                out.printl(f'[999]変更しない（{family}）')
            value=yield from inputs(ctx)
            if not value:yield from wait(ctx,TEXT[577])
            elif value=='999':family_input=family
            else:family_input=value
            out.printl();out.printl(TEXT[584])
            if given:out.printl(f'[999]変更しない（{c.callname}）')
            while True:
                value=yield from inputs(ctx)
                if value:break
                yield from wait(ctx,TEXT[592])
                out.clearline(1)  # @FIRSTSETTING_CHARA_NAME:593
            given=c.callname if value=='999' else value
            c.cstr[200]=given;c.cstr[10]=family_input;c.name=family_input+given
            out.printl(f'キャラの氏名を 『{c.name}』 に設定しました')
        elif r==2:
            c.name=default.name;c.callname=default.callname
            c.cstr[10]=default.cstr.get(10,'');c.cstr[200]=default.callname
            out.printl(f'キャラの氏名を 『{default.name}』 に設定しました')
        elif r==3:
            out.printl('[0]苗字　→　名前の順番にする　『'+c.cstr[10]+c.callname+'』')
            out.printl('[1]名前　→　苗字の順番にする　『'+c.callname+'・'+c.cstr[10]+'』')
            out.printl(TEXT[622])
            while True:
                q=yield from input_number(ctx)
                if q in (0,1,99):break
            if q!=99:
                c.name=c.cstr[10]+c.callname if q==0 else c.callname+'・'+c.cstr[10]
                yield from wait(ctx,f'『{c.name}』に変更しました')
            else:yield from wait(ctx,TEXT[667])
            out.clearline(out.linecount-entry_line)
            continue
        elif r==4:
            out.drawline();out.printl(TEXT[640])
            for i,other in enumerate(st.charas):
                if i!=st.MASTER and i!=who and other.cstr[10] and other.cstr[10]!=c.cstr[10]:out.printl(f' [{i}]'+other.cstr[10])
            out.printl(TEXT[1134])
            while True:
                q=yield from input_number(ctx)
                if q==99:
                    yield from wait(ctx,TEXT[667]);break
                # :656 <=CHARANUM 是原作越界條件，不把它悄悄改成 <。
                if q==st.charanum:raise NotImplementedError('FIRSTSETTING_CHARA_NAME 原作角色索引CHARANUM越界')
                if 0<q<st.charanum and st.charas[q].cstr[10] and st.charas[q].cstr[10]!=c.cstr[10]:
                    other=st.charas[q];c.cstr[10]=other.cstr[10]
                    c.name=c.cstr[10]+c.callname if other.name==other.cstr[10]+other.callname else c.callname+'・'+c.cstr[10]
                    out.printl(f'{who}人目のキャラの名前を{c.name}にしました')
                    yield from wait(ctx,'');break
            out.clearline(out.linecount-entry_line)
            continue
        if c.cstr[200]:
            if c.callname==c.cstr[1]:c.cstr[1]=c.cstr[200]
            c.callname=c.cstr[200]
        out.printl();out.printl();st.result[0]=0;return 0


def random_character_name(ctx, who):
    """保留LOCAL重疊、中文第二字覆寫、共用COUNT索引及回傳忽略固定順序。"""
    st,out=ctx.state,ctx.out
    local=[0]*100;local[0]=2
    word=lambda i:ctx.data.str_defaults.get(i,'')
    family_ranges={0:(500,3000),1:(2000,3500),2:(2000,5500),3:(1500,7500),4:(2000,9000),5:(1000,11000),6:(500,16000),7:(200,19000),99:(9000,3000)}
    given_ranges={0:(500,12000),1:(1000,12500),2:(500,13500),3:(500,14000),4:(500,15000),5:(500,15500),7:(500,19200),10:(500,18000),99:(4000,12000)}
    languages=('日本語','英語',TEXT[734],TEXT[736],TEXT[738],TEXT[740],'中国語','韓国語')
    def draw(width,base,retry=None):
        index=st.rng.rand(width)+base
        while not word(index):index=st.rng.rand(retry or width)+base
        return index
    def composed(i,order=True,check=None):
        family,given=word(local[10+i]),word(local[30+i])
        if order and local[3]:return family+given if local[3]==1 else given+'・'+family
        test=local[10+i] if check is None else check
        if local[1] in (0,6) or local[1]==99 and (test<3500 or 16000<=test<16500):return family+given
        if local[1]==7 or local[1]==99 and 19000<=test<19700:return family+'・'+given
        return given+'・'+family
    configure=True
    while True:
        if configure:
            while True:
                config_line=out.linecount
                out.printl('苗字：'+(languages[local[1]] if 0<=local[1]<=7 else TEXT[748]))
                out.printl('名前：'+(languages[local[2]] if 0<=local[2]<=7 else TEXT[746] if local[2]==10 else TEXT[748]))
                out.printl(('苗字' if local[0]==1 else '名前')+TEXT[758])
                for i,label in enumerate(languages):out.printl(f'[{i}]'+label)
                if local[0]==2:out.printl('[10]日本語(中性)')
                out.printl(TEXT[772]);out.printl('[100]'+('名前' if local[0]==1 else '苗字')+'を変更')
                out.printl('[200]生成');out.printl('[800]順序を固定しない [801]「苗字 名前」の順に固定 [802]「名前 苗字」の順に固定')
                while True:
                    r=yield from input_number(ctx)
                    if r==10 and local[0]==1:continue
                    if r<100:local[local[0]]=r
                    elif r==100:local[0]=3-local[0]
                    elif r==200:break
                    elif r in (800,801,802):local[3]=r-800
                    else:continue
                    break
                if r==200:break
                # DEVIATION: 沿既有W07顯示簡化，本頁合併了原文空白行／按鈕列；
                # @FIRSTSETTING_CHARA_NAME_RANDOM:823，
                # 依實際輸出行數清除同一選單，避免固定16誤刪呼叫者的行。
                # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–500。
                out.clearline(out.linecount-config_line)
        for i in range(20):
            st.count[0]=i  # @FIRSTSETTING_CHARA_NAME_RANDOM:827 REPEAT20。
            if local[1] in family_ranges:
                if local[1]==6:local[3]=1
                local[10+i]=draw(*family_ranges[local[1]])
            if local[2]==6:
                local[3]=1
                # :913–920 兩次WHILE都檢查姓而非名；有姓時不重抽空名字。
                # DEVIATION: 空姓原作無窮重抽改為停止；見docs/wiki/bridge/deviations.md的S60／W08姓名安全網待裁決項。
                if not word(local[10+i]):raise NotImplementedError('FIRSTSETTING_CHARA_NAME_RANDOM 原作中文空姓無窮重抽')
                local[30+i]=st.rng.rand(1000)+16500
                local[31+i]=st.rng.rand(1000)+16500
            elif local[2] in given_ranges:
                local[30+i]=draw(*given_ranges[local[2]],7000 if local[2]==99 else None)
        st.count[0]=20
        configure=False
        while True:
            candidates_line=out.linecount
            for i in range(20):
                st.count[0]=i  # :943–957，REND後留下20供:1009／1012使用。
                out.printl(f'[{i:2}]'+composed(i))
            st.count[0]=20
            out.printl('[100]構成から選びなおす [200]再生成')
            out.printl('[800]順序を固定しない [801]「苗字 名前」の順に固定 [802]「名前 苗字」の順に固定')
            while True:
                r=yield from input_number(ctx)
                if 0<=r<20 or r in (100,200,800,801,802):break
            if 0<=r<20:
                st.results[0]=composed(r,False,local[10+st.count[0]])
                st.results[1]=word(local[30+r]);st.results[2]=word(local[10+r])
                st.result[0],st.result[1]=local[1],local[2]
                return local[1]
            if r==100:local[0]=1;configure=True;break
            # @FIRSTSETTING_CHARA_NAME_RANDOM:990、993、997、1001：重抽／換排列清候選頁。
            out.clearline(out.linecount-candidates_line)
            if r==200:break
            local[3]=r-800
