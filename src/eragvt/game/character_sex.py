"""性別設定：ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SEX:360–492。"""
from .body import set_profile, cup_size, top_under
from .character_editor_text import TEXT
from .input_request import input_number


def sex_setting(ctx, who):
    """確認前即寫TS；否返回選單，確認後清相依特徵並重算兩形態。"""
    st,data,out=ctx.state,ctx.data,ctx.out
    c=st.charas[who]
    key=lambda name:data.index_of('TALENT',name)
    t=lambda name:c.talent[key(name)]
    while True:
        out.printl(f'{who}人目のキャラの性別を設定してください')
        out.printl(TEXT[363]);out.printl(TEXT[364])
        if t('変身能力')==1:out.printl(TEXT[366])
        out.printl(TEXT[367])
        if t('変身能力')==1:out.printl(TEXT[369])
        choice=yield from input_number(ctx)
        if choice not in (0,2) and not (choice in (1,3) and t('変身能力')==1):
            continue
        # :371–374：不可延到確認後，取消也保留本次TS變更。
        if t('変身能力')==1:c.talent[key('変身時ＴＳ')]=choice%2
        male=choice>=2
        label='オトコ' if male else '女'
        if t('変身時ＴＳ')>0:label+='/'+('女' if male else 'オトコ')
        elif t('変身能力')==1:label+='/'+('オトコ' if male else '女')
        if male:
            for n in (430,431,432):out.printl(TEXT[n])
            out.printl()
        out.printl(f'キャラを {label} にします。よろしいですか？')
        out.printl(TEXT[384]);out.printl(TEXT[385])
        while True:
            answer=yield from input_number(ctx)
            if answer in (0,1):break
        if answer==0:continue
        c.talent[key('オトコ')]=int(male)
        clear=['男の娘','変身時男の娘','ふたなり','変身時ふたなり']
        if male:
            clear+=['処女','母乳体質','パイパン','Ｖ敏感','Ｖ鈍感','貧乳','巨乳',
                    '濡れやすい','濡れにくい','苗床化','アクセサリ','外見']
            if t('交際相手') in (2,4,5):c.talent[key('交際相手')]=0
            if t('変身時ＴＳ')==0:
                clear+=['変身時胸サイズ変動','変身時外見','変身時濡れやすさ変動','変身時Ｖ感覚変動']
        else:
            if t('変身時ＴＳ')>0:clear+=['変身時胸サイズ変動','変身時外見']
            clear+=['変身時濡れやすさ変動','変身時Ｖ感覚変動']
        for name in clear:c.talent[key(name)]=0
        out.printl('キャラを '+('オトコ' if male else '女')+' に設定しました。')
        # :404–413、469–478；FOR終點不含，194不清。
        # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1733–1743。
        point=data.index_of('PALAM','修練P')
        for i in (*range(190,194),key('避妊結界')):
            if c.talent[i]:
                c.talent[i]=0
                c.juel[point]+=50
        if t('固有キャラ')==0 and t('初期経験設定不可')==0:
            for name in (('Ｖ経験','出産経験') if male else ('射精経験',)):
                c.exp[data.index_of('EXP',name)]=0
        set_profile(data,c,st.result)
        # SET_PROFILE最後是變身形態；CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:239–249
        # 呼叫CUP_SIZE，原作亦留下RESULTS:0（男性也呼叫）。
        st.results[0]=cup_size(top_under(data,c,1)[0])[1]
        # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
        st.result[0]=0
        return 0
