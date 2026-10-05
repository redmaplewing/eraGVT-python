"""S55：SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN 手翻 UI。"""
from .creation_text import TEXT, ARRAYS, PRESETS, CALLS, UNPORTED_DESCRIPTIONS
from .input_request import input_number, inputs, TextInputRequest
from .naming import random_naming
from .chara_common import is_male, seikaku_check, syuzoku_check, talent
from .era import format_percent
from ..state.constants import GameOption

MAIN='CHARA_MAKE.ERB'
TITLE='FIRSTSETTING_TITLE.ERB'
CROWN='FIRSTSETTING_CROWNNAME.ERB'
CALL='FIRSTSETTING_CHARA_TRANSFORMATION.ERB'
MAPPING=((5,5),(6,6),(7,7),(820,8),(821,9),(822,20),(823,21),(824,22),(825,23))

def lines(ctx,name,first,last):
    for n in range(first,last+1):
        if (name,n) in TEXT:ctx.out.printl(TEXT[name,n])

def number(ctx):
    r=yield from input_number(ctx)
    ctx.out.printl(str(r))
    return r

def wait(ctx,text):
    # PRINTW：Instraction.Child.cs:89–93、144–145；不寫 RESULT(S)。
    ctx.out.printw(text)
    ctx.out.printl('（按 Enter 繼續）')
    yield TextInputRequest()
    ctx.out.clearline(1)

def load_common(ctx):
    # LOADGLOBAL：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1293–1299。
    ctx.state.result[0]=int(ctx.globals.load())
    for f,g in MAPPING:ctx.state.flag[f]=ctx.globals.mem.global_[g]
    for f in (10,11,12):ctx.state.savestr[f]=ctx.globals.mem.globals_[f+5]

def common_setting(ctx,choice):
    """各 FIRSTSETTING 函式；自然終端 RETURN 0（reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。"""
    st,out=ctx.state,ctx.out
    if choice in (1005,1006):
        key=821 if choice==1005 else 822
        lo,hi=(1026,1035) if choice==1005 else (1047,1057)
        while True:
            lines(ctx,'FIRSTSETTING_CHARA.ERB',lo,hi)
            current=ARRAYS['namelang'][st.flag[key]-1] if st.flag[key]>0 else ''
            out.printl('[99]変更せずに戻る'+(('（' + ('現在：' if choice==1006 else '')+current+'）') if current else '（ランダム）'))
            r=yield from number(ctx)
            if 0<=r<=(8 if choice==1005 else 9):st.flag[key]=r;break
            if r==99:break
    elif choice==1007:
        # FIRSTSETTING_CHARA_SYUZOKU.ERB@FIRSTSETTING_racegenre:168–182：10 不顯示但接受。
        while True:
            for i,name in enumerate(ARRAYS['racegenre'][:10]):out.printl(f'[{i}]{name}')
            out.printl('[99]ランダム')
            r=yield from number(ctx)
            if 0<=r<=10:st.flag[823]=r+1;break
            if r==99:st.flag[823]=0;break
    elif choice==1003:
        # FIRSTSETTING_CROWNNAME.ERB@FIRSTSETTING_transnamegenre:76–136。
        lines(ctx,CROWN,78,81);out.drawline();lines(ctx,CROWN,83,85)
        r=yield from number(ctx)
        if r==0:
            st.flag[820]=0;lines(ctx,CROWN,90,90)
        elif r==1:
            while True:
                lines(ctx,CROWN,94,105)
                genre=yield from number(ctx)
                if genre==99:break
                if not 0<=genre<=8:continue
                name=ARRAYS['transnamegenre'][genre]
                out.printl(f'デフォルトジャンルを 『{name}』 とします。よろしいですか？')
                lines(ctx,CROWN,117,118)
                if st.savestr[11]:out.printl(f'[2]変更しない（{name}）')
                while True:
                    r=yield from number(ctx)
                    if 0<=r<=2:break
                if r==0:continue
                if r==1:
                    st.flag[820]=genre+1
                    out.printl(f'デフォルトジャンルを 『{name}』 に設定しました')
                break
        # 原文沒有最外層 ELSE/GOTO：99 與其他數值都自然返回。
    elif choice in (1001,1002,1004):
        key,slot,name,file,first,last={1001:(5,10,'主題',TITLE,4,10),1002:(6,11,'冠名',CROWN,4,13),1004:(7,12,'かけ声',CALL,454,459)}[choice]
        # DRAWLINE 在說明與選項之間。
        draw={1001:6,1002:9,1004:455}[choice]
        lines(ctx,file,first,draw-1);out.drawline();lines(ctx,file,draw+1,last)
        while True:
            r=yield from number(ctx)
            if r in (0,1,2,99):break
        if r==99:st.result[0]=99;return 99
        if r==0:
            st.flag[key]=0;out.printl(f'{name}を設定しませんでした')
        elif r==2:
            st.flag[key]=1
            out.printl(f'{name}を入力してください'+('。' if choice==1001 else ''))
            if choice!=1004 and st.savestr[slot]:out.printl(f'[999]変更しない（{st.savestr[slot]}）')
            while True:
                value=yield from inputs(ctx)
                if value:break
            if choice==1004 or value!='999':
                st.savestr[slot]=value
                out.printl(f'{name}を 『{value}』 に設定しました')
        else:
            st.flag[key]=1
            while True:
                if choice==1004:
                    # FIRSTSETTING_変身デフォルト口上.ERB@FIRSTSETTING_CHANGINGCALL_RANDOM:3–26。
                    st.savestr[slot]=CALLS[st.rng.rand(len(CALLS))]
                    candidate=st.savestr[slot]
                elif choice==1001:
                    lines(ctx,TITLE,72,75)
                    r=yield from number(ctx)
                    st.results[0]=''
                    # :83–85 RESULTS=""；WHILE RESULTS!="" 不執行，連非法編號也自然回空字。
                    if r==99:st.result[0]=99
                    else:out.printl();st.result[0]=0
                    candidate=''
                else:
                    yield from random_naming(ctx,0,'')
                    if st.result[1]==1:continue
                    candidate=st.results[0]
                none=(choice==1001 and not candidate) or (choice==1002 and st.result[0]==99)
                out.printl(f'{name}を設定しません。よろしいですか？' if none else f'{name}を 『{candidate}』 とします。よろしいですか？')
                out.printl('[0]いいえ' if choice==1002 else '[0]もう一度選びなおす')
                out.printl('[1]はい')
                if choice!=1004 and st.savestr[slot]:out.printl(f'[2]変更しない（{st.savestr[slot]}）')
                while True:
                    r=yield from number(ctx)
                    if r in (0,1) or (r==2 and choice!=1004 and (choice==1002 or st.savestr[slot])):break
                if r==0:
                    if choice==1002:st.flag[key]=0
                    continue
                if r==1:
                    st.savestr[slot]=candidate
                    if not candidate:
                        st.flag[key]=0;st.results[0]='';out.printl(f'{name}を設定しませんでした')
                    else:out.printl(f'{name}を 『{candidate}』 に設定しました')
                break
        out.printl()
    else:raise ValueError(choice)
    st.result[0]=0
    return 0

def _settings(ctx,global_values=False):
    st,out=ctx.state,ctx.out
    flag=lambda k:ctx.globals.mem.global_[dict(MAPPING)[k]] if global_values else st.flag[k]
    string=lambda k:ctx.globals.mem.globals_[k+5] if global_values else st.savestr[k]
    values=[('『'+string(10)+'』') if flag(5)==1 else 'なし',
            ('『'+string(11)+'』') if flag(6)==1 else 'なし',
            ('『'+ARRAYS['transnamegenre'][flag(820)-1]+'』') if flag(820)>0 else 'なし',
            ('『'+string(12)+'』') if flag(7)==1 else 'なし',
            ARRAYS['namelang'][flag(821)-1] if flag(821)>0 else 'デフォルト',
            ARRAYS['namelang'][flag(822)-1] if flag(822)>0 else 'デフォルト',
            ARRAYS['racegenre'][flag(823)-1] if flag(823)>0 else 'ランダム',
            'あり' if (flag(824)>0 if global_values else flag(824)==1) else 'なし',
            '口上有りのみ' if (flag(825)>0 if global_values else flag(825)==1) else '完全ランダム']
    if global_values:
        out.printl('現在保存されているグローバル')
        for i,label in enumerate(('主題・・・・','冠名・・・・','変身名・・・','かけ声・・・','苗字言語・・','名前言語・・','種族・・・・','フィート・・','性格・・')):
            value=values[i]
            if i<7:
                f=(5,6,820,7,821,822,823)[i]
                enabled=flag(f)==1 if f in (5,6,7) else flag(f)>0
                value=('あり '+(value if value.startswith('『') else '『'+value+'』')) if enabled else 'なし'
            out.printl('　'+label+value)
    else:
        for i,label in enumerate(('ユニットの主題・・・・・・','変身名（上の句）・・・・・','変身名（下の句）ジャンル・','変身時のかけ声・・・・・・','苗字の言語・・・・・・・・','名前の言語・・・・・・・・','種族・・・・・・・・・・・','フィート自動割り当て・・・','性格・・・・・・・・・・・')):
            out.printl(f'[{1001+i}]'+label+values[i])

def _main(ctx):
    st,out=ctx.state,ctx.out
    from .opening import game_option
    out.drawline();out.set_bold(True);out.set_color('#00ffff');out.printl('◆デフォルト共通設定');out.set_bold(False);out.reset_color()
    _settings(ctx)
    out.printl('[170]グローバルに保存　　　　　　[180]グローバルから読み込み　　　[190]初期化　　　')
    out.drawline();out.printl();out.set_bold(True);out.set_color('#00ffff');out.printl('◆個別キャラメイキング');out.set_bold(False);out.reset_color()
    st.result[0]=0
    for i,c in enumerate(st.charas[1:],1):
        if c.callname=='汎用キャラ':
            out.print(f'[{i}]キャラ作成'+format_percent('♀',6,True)+f'[{i+100}]キャラ作成'+format_percent('♂',4,True)+'　')
        else:out.print(f'[{i}]'+format_percent(c.callname,35,True)+'　')
        status={1:'幽閉',2:'洗脳',3:'悪堕ち',4:'監禁',9:'死亡'}.get(c.cflag[0],' ― ')
        out.button(f'[{i+500}][{status}]',i+500);out.print('  ')
        if c.callname!='汎用キャラ':
            out.print('♂ / ' if is_male(ctx.data,c) else '♀ / ')
            race=syuzoku_check(c);person=seikaku_check(ctx.data,c)
            race=ctx.data.names['TALENT'].get(race,'') if race else 'ランダム'
            st.results[0]=ctx.data.names['TALENT'].get(person,'') if person else 'ランダム'
            st.result[0]=person
            trans=talent(ctx.data,c,'変身能力')
            out.print(f'[{race}] [{st.results[0]}] ['+('非戦闘員' if trans==-1 else '変身なし' if trans==0 else '変身あり')+'] ')
        out.printl()
    out.printl()
    st.result[0]=sum(c.callname=='汎用キャラ' for c in st.charas)
    if not game_option(st,GameOption.SOLO):lines(ctx,MAIN,127,127)
    # :130 成就或自由模式才顯示；尚未手翻人数編輯。
    if _can_count(ctx):out.printl('[300]人数を変更する')
    out.printl();out.printl();out.printl()
    out.print('[1000]★キャラメイクを完了する'+format_percent(' （未設定のキャラはおまかせ） ' if st.result[0] else '  ',32,True))
    out.printl('[999]モード選択に戻る')

def _can_count(ctx):
    from .opening import game_option
    return game_option(ctx.state,GameOption.NO_ACHIEVEMENT_END) or (sum(ctx.globals.mem.global_[i] for i in (100,101,102))>0 and not game_option(ctx.state,GameOption.SOLO))

def preset_menu(ctx):
    """SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:5–45。"""
    st,out=ctx.state,ctx.out
    out.printl()
    while True:
        out.printl('ロードする初期セットを選んでください')
        for i in range(99):
            for text in PRESETS.get(('NAME',i),()):out.printl(text)
        out.printl('[99]読み込まずに戻る')
        r=yield from number(ctx)
        if r==99:st.result[0]=-1;return -1
        if r in UNPORTED_DESCRIPTIONS:
            # 初期セット/6_リリカルハンターAs.ERB@SHOKISET_SETUMEI_6:8–157；
            # 7_リリカルハンターStS.ERB@SHOKISET_SETUMEI_7:8–160；8_リリカルハンターViVid.ERB@SHOKISET_SETUMEI_8:8–173。
            raise NotImplementedError(f'SHOKISET_SETUMEI_{r} 隨機 AA 說明尚未移植')
        if not 0<=r<99 or ('SETUMEI',r) not in PRESETS:continue
        for text in PRESETS['SETUMEI',r]:out.printl(text)
        out.printl('よろしいですか？');out.printl('[0]いいえ');out.printl('[1]はい')
        while True:
            confirm=yield from number(ctx)
            if confirm in (0,1):break
        if confirm==0:continue
        if r!=0:
            # @CHARA_MAKE_FINALIZE_KAI:31–35：呼叫未移植套組前已移除舊角色。
            for _ in range(st.charanum-1):st.del_chara(1);st.flag[8]-=1
            raise NotImplementedError(f'SHOKISET_SELECT_{r} 尚未移植')
        _preset_zero(ctx)
        st.result[0]=0
        return 0

def _preset_zero(ctx):
    from .opening import shokiset_select_0,shokiset_csvfix
    for _ in range(ctx.state.charanum-1):
        ctx.state.del_chara(1);ctx.state.flag[8]-=1
    shokiset_select_0(ctx.state,ctx.data)
    shokiset_csvfix(ctx.state,ctx.data)

def creation_menu(ctx,initial_preset=None,bonus=0):
    """CHARA_MAKE.ERB@CHARA_MAKE_MAIN:5–363；[1000] 完成後 EVENTFIRST 再 FINALIZE 一次。"""
    from .opening import chara_make_finalize,game_option
    from .character_editor import character_editor
    st,out=ctx.state,ctx.out
    load_common(ctx)
    if initial_preset is not None:_preset_zero(ctx)
    while True:
        _main(ctx)
        while True:
            r=yield from number(ctx)
            if 100<r<st.charanum+100 and st.charas[r-100].callname=='汎用キャラ':
                # @CHARA_MAKE_MAIN:142–145。
                c=st.charas[r-100]
                c.talent[ctx.data.index_of('TALENT','オトコ')]=1
                c.name='汎用キャラ(♂)'
                yield from character_editor(ctx,r-100,bonus)
                break
            if 0<r<st.charanum:
                yield from character_editor(ctx,r,bonus)
                break
            if 500<r<st.charanum+500:raise NotImplementedError('CHARA_MAKE_MAIN 初始角色狀態切換尚未移植')
            if r==300 and _can_count(ctx):raise NotImplementedError('CHARA_MAKE_MAIN 人數變更尚未移植')
            if r==1000:
                out.printl('キャラメイクを終了します')
                chara_make_finalize(st,ctx.data,ctx=ctx);st.result[0]=0
                return 0
            if r==999:st.result[0]=-1;return -1
            if 1001<=r<=1007:yield from common_setting(ctx,r);break
            if r in (1008,1009):st.flag[824+r-1008]=int(not st.flag[824+r-1008]);break
            if r==190:
                for f,_ in MAPPING:st.flag[f]=0
                for f in (10,11,12):st.savestr[f]=''
                break
            if r==180:load_common(ctx);break
            if r==170:
                _settings(ctx,True);lines(ctx,MAIN,252,256)
                while True:
                    confirm=yield from number(ctx)
                    if confirm in (0,99):break
                if confirm==0:
                    for f,g in MAPPING:ctx.globals.mem.global_[g]=st.flag[f]
                    for f in (10,11,12):ctx.globals.mem.globals_[f+5]=st.savestr[f]
                    ctx.globals.save() # SAVEGLOBAL 保留 RESULT，Instraction.Child.cs:1279–1281。
                    yield from wait(ctx,'グローバルとして保存しました。')
                break
            if r==200 and not game_option(st,GameOption.SOLO):yield from preset_menu(ctx);break
