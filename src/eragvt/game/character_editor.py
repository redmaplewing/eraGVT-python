"""共用角色編輯入口：FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:6–353。"""
from .character_editor_text import TEXT
from .input_request import input_number
from .chara_common import talent, baseup_cal_shield, is_male, is_female, seikaku_check, syuzoku_check, feat_bonus
from .body import generate_char_size, top_under, cup_size
from .opening import chara_make_initialize, decode_weapon_data
from .firstsetting import chara_callname, trans_after_name, trans_after_callname, trans_call, nanori
from .self_call_setting import selfcall_gen
from .clothing import clothing_setting_gen
from .weapon_customize import customize
from .era import div


def _draw(ctx, who, restricted):
    """主入口:37–230；顯示函式依原文次序保留 RESULT/RESULTS。"""
    from .akuoti import self_call
    from .self_call_setting import _reading
    from .status_talent import show_status_talent
    from .battle.core import fstyle_name
    st,out,data=ctx.state,ctx.out,ctx.data
    from .shop import lb
    lb(out)
    c=st.charas[who]; t=lambda n:talent(data,c,n)
    out.printl(TEXT[1131])
    out.printl(f'【プロフィールの設定　キャラクター {who}】')
    out.printl(f'◆[ 1]氏名　　：『{c.name}』')
    out.printl(f'◆[ 2]呼び名　：『{c.callname}』')
    out.printl(f'◆[ 3]一人称　：『{self_call(ctx,who)} <{_reading(ctx,who)}>』')
    if t('固有キャラ') or restricted: out.set_color('#808080')
    race=syuzoku_check(c)
    out.printl('◆[ 4]種族　　：『'+(data.names['TALENT'].get(race,'') if race else TEXT[748])+'』')
    st.result[0]=race
    out.reset_color()
    kojo=t('口上設定')
    kojo='非表示' if kojo<0 else {0:'汎用',1:'ロボ風',2:'あなた',3:'汎用豹変'}.get(kojo,f'専用口上({c.no}番)' if c.no else '')
    out.printl('◆[ 5]口上設定：『'+kojo+'』'+(' + 『主観モード』' if t('主観視点')>0 else ''))
    out.printl();out.printl(TEXT[68]);out.printl(TEXT[69])
    if t('固有キャラ'):out.set_color('#808080')
    out.printl(TEXT[72])
    if t('固有キャラ')>0 or t('初期経験設定不可')>0:out.set_color('#808080')
    out.printl(TEXT[75]);out.reset_color();out.drawline()
    sex='ふたなり' if t('ふたなり')>0 else '男' if is_male(data,c) else '女'
    after=''
    if sex=='ふたなり':
        after='男' if t('変身時ＴＳ')>0 else '女' if t('変身能力')>0 else ''
    elif t('変身時ふたなり')>0:after='ふたなり'
    elif t('変身時ＴＳ')>0:after='女' if sex=='男' else '男'
    out.printl(f'　　性別　　：『{sex}』　'+(f'(変身時:{after})' if after else ''))
    out.printl(f'　　年齢　　：{c.base[data.index_of("BASE","年齢")]}歳')
    sizes=generate_char_size(data,c,0,st.result)
    # CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:239–249：男性也呼叫CUP_SIZE並留下RESULTS:0。
    st.results[0]=cup_size(top_under(data,c,0)[0])[1]
    out.print(f'　　身体　　：{div(sizes[2],10)}cm {div(sizes[3],10)}kg')
    if is_female(data,c):out.print(f'(胸{div(sizes[7],10)}.{sizes[7]%10}kg)')
    if sizes[4]>0:
        b,w,h=sizes[4:7]
        st.result[0],st.result[1]=top_under(data,c,0)
        st.result[0],st.results[0]=cup_size(st.result[0])
        out.printl(f'  Ｂ:{div(b,10)}({st.results[0]}) Ｗ:{div(w,10)} Ｈ:{div(h,10)}')
    person=seikaku_check(data,c)
    out.printl('　　性格　　：『'+(data.names['TALENT'].get(person,'') if person else TEXT[748])+'』')
    st.result[0]=person
    _resist(ctx,who,person)
    show_status_talent(ctx,who,2)
    out.reset_color();out.printl(TEXT[135]);out.print('　　　　　')
    for i in range(99):
        if c.exp[i]>0:out.print(f'　{data.names["EXP"].get(i,"")}({c.exp[i]}) ')
        if i==39:out.printl();out.print('　　　　　')
    st.result[0]=0
    out.printl();out.drawline();out.reset_color()
    if t('固有キャラ'):out.set_color('#808080')
    trans=t('変身能力')
    out.printl('◆[10]戦闘能力・・・・・・・・ '+{1:TEXT[147],-1:TEXT[149]}.get(trans,TEXT[151]))
    out.reset_color()
    if trans==1:
        for choice,flag,slot,label in ((11,2,0,'変身後名'),(12,3,1,'変身後呼び名'),(13,4,2,'変身時かけ声'),(14,5,3,'変身後名乗り口上')):
            out.printl(f'　[{choice}]{label}・・・・・・'+(f'『{c.cstr[slot]}』' if c.cflag[flag]==1 else 'なし'))
    out.printl(TEXT[160])
    for choice,slot,label in ((16,40,'アウター'),(17,41,'アウター（変身後）'),(18,42,'インナー')):
        if choice==17 and trans!=1:continue
        item=data.items.get(c.cflag[slot]); value=item.name if item and c.cflag[slot]>0 else 'なし'
        custom=c.cstr[slot-32] if slot!=42 else ''
        if custom and c.cflag[slot]>0:value=custom+'（'+value+'）'
        out.printl(f'　[{choice}]{label}：'+value)
    if trans!=-1:
        out.printl(TEXT[193])
        for dist,label in enumerate(('近','中','遠'),1):
            out.printl(f'　　{label}距離　戦闘スタイル：<<{fstyle_name(ctx,who,dist)}>>　銘：'+(c.cstr[dist+4] or '無'))
    out.printl(f'◆[23]基礎値ボーナス　（のこり +{div(c.juel[data.index_of("PALAM","修練P")],10)}pts）')
    for i,label in enumerate(('体力','気力','性耐性','攻撃','防御','敏捷','知性')):
        value=c.base[data.index_of('BASE',label)]+c.cflag[50+i]*(10 if i<2 else 1)+feat_bonus(data,c,i)
        out.print(f'　{label}：{value:4}')
        if i in (2,4,6):out.printl()
    out.printl('[99]決定')
    if restricted==0:out.printl('[999]CSVから読み込む')


def _resist(ctx, who, person):
    """ヒロイン関連/CHARA_SEIKAKU.ERB@SHOW_RESISTSEX:1056–1168。"""
    from .battle.core import seikaku_hosei_palam
    c=ctx.state.charas[who];t=lambda n:bool(talent(ctx.data,c,n))
    changes={11:10*t('快楽に弱い')-10*t('恥じらい')+10*t('母性的'),
             13:-10*t('快楽の否定')+10*t('度胸')+10*t('喧嘩上等')-20*t('潔癖症'),
             14:10*t('快楽の否定')+(20 if c.mark[ctx.data.index_of('MARK','屈服刻印')]>=3 else -10)*t('プライド高い')-10*t('争いを好まない')+10*t('小悪魔')-10*t('潔癖症'),
             15:10*t('恥じらい')-10*t('度胸')+10*t('上品')+30*t('潔癖症'),
             16:-10*t('快楽に弱い')+10*t('小心者')+10*t('目立ちたがり'),
             17:10*t('争いを好まない')-10*t('喧嘩上等')+10*t('泣き虫')+20*t('潔癖症')}
    for i,label in ((11,'恭'),(13,'欲'),(14,'屈'),(15,'恥'),(16,'苦'),(17,'恐')):
        value=seikaku_hosei_palam(person,i,100)+(changes[i] if person!=28 else 0)
        mark,color=next((m,col) for limit,m,col in ((90,'◎','#fa3c00'),(100,'○','#fab400'),(110,'－','#808080'),(120,'▽','#7878fa'),(float('inf'),'×','#003cfa')) if value<limit)
        ctx.out.print(label+':');ctx.out.set_color(color);ctx.out.print(mark+'  ');ctx.out.reset_color()
    ctx.out.printl();ctx.state.result[0]=0


def character_editor(ctx, who, bonus=0, restricted=0):
    """ARG:2 只鎖種族/CSV；主選單沒有取消，99完成。TARGET不改。

    bonus只供原文:323的CSV重載追加點數；進入/99不加點，該子選單仍未移植。
    WEAPON_CUSTOMIZE的ARG:1=1於原文:8–80未讀取，沿用共用customize。
    """
    st,data=ctx.state,ctx.data
    c=st.charas[who]
    items={i:st.item[i] for i in range(100,700) if i in data.items and data.items[i].name}
    for i in items:st.item[i]=1
    if c.cflag[240]==0:chara_make_initialize(st,data,who)
    for dist in (1,2,3):
        if c.cstr[14+dist]:st.result[0]=decode_weapon_data(data,st,who,dist)
        c.cstr[14+dist]=''
    while True:
        _draw(ctx,who,restricted)
        while True:
            r=yield from input_number(ctx)
            unique=talent(data,c,'固有キャラ');trans=talent(data,c,'変身能力')
            allowed={1,2,3,5,6,16,18,23,99}
            if not unique:
                allowed.update((0,7,10))
                if not restricted:allowed.add(4)
                if not talent(data,c,'初期経験設定不可'):allowed.add(8)
            if trans==1:
                allowed.update((11,12,13,14))
                if c.cflag[0]!=3:allowed.add(17)
            if trans!=-1:allowed.add(24)
            if not restricted:allowed.add(999)
            if r in allowed:break
        if r==99:
            baseup_cal_shield(data,st,who)
            for i in range(4):st.savestr[i]=''
            for i in range(100,700):st.item[i]=items.get(i,0)
            # reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67：自然終端只寫RESULT:0。
            st.result[0]=0
            ctx.out.clearline(ctx.out.linecount)
            return 0
        if r==1:
            from .character_name import character_name
            yield from character_name(ctx,who)
        elif r in (2,3,11,13,14,24):
            yield from {2:chara_callname,3:selfcall_gen,11:trans_after_name,13:trans_call,14:nanori,24:customize}[r](ctx,who)
        elif r==5:
            yield from kojo_setting(ctx,who)
        elif r==12:
            if c.cflag[2]==1:
                c.cflag[3]=1
                yield from trans_after_callname(ctx,who)
        elif r in (16,17,18):
            yield from clothing_setting_gen(ctx,who,r+24)
            st.result[0]=0
        else:
            names={0:'FIRSTSETTING_CHARA_SEX',4:'FIRSTSETTING_CHARA_SYUZOKU',6:'SIZE_SETTING',7:'FIRSTSETTING_CHARA_SEIKAKU',8:'FIRSTSETTING_CHARA_EXP',10:'FIRSTSETTING_CHARA_TRANSABILITY',23:'FIRSTSETTING_STATUS_BONUS',999:'FIRSTSETTING_CHARA_LOADCSV'}
            raise NotImplementedError(names[r]+' 尚未移植')

def kojo_setting(ctx,who):
    """FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_KOJO:1108–1200。"""
    from .creation_menu import wait
    st,out,data=ctx.state,ctx.out,ctx.data;c=st.charas[who]
    k=data.index_of('TALENT','口上設定');subject=data.index_of('TALENT','主観視点')
    labels={0:'汎用',1:'ロボ風',2:'あなた',3:'汎用豹変',-2:'非表示'}
    out.printl(f'{who}人目のキャラ『{c.callname}』 の口上設定を確認してください')
    out.printl(' 現在の口上：'+labels.get(c.talent[k],f'専用({c.no}番)' if c.no else ''))
    out.printl(' 主観モード：'+('使用する' if c.talent[subject]>0 else '使用しない'))
    out.printl(TEXT[1132]);out.printl(TEXT[1133]);out.printl(TEXT[1134])
    while True:
        r=yield from input_number(ctx)
        if r in (0,1,99):break
    if r==99:st.result[0]=99;return 99
    if r==0:
        out.printl(TEXT[1138])
        for i in range(4):out.printl(f'[{i}]'+labels[i])
        if c.no:out.printl(TEXT[1144])
        out.printl(TEXT[1145])
        while True:
            q=yield from input_number(ctx)
            if q in (0,1,2,3,99) or q==90 and c.no:break
        c.talent[k]=-2 if q==99 else c.no if q==90 else q
        out.printl('口上を 『'+(f'専用口上({c.no}番)' if q==90 else labels[c.talent[k]])+'』 に設定しました')
        if q==2:
            c.talent[subject]=1;out.printl('地の文を主観モードに設定しました')
        yield from wait(ctx,'')
    else:
        old=c.talent[subject]
        if old==1:
            out.printl(TEXT[1174]);out.printl(TEXT[1175]);out.printl(TEXT[1176])
        else:
            out.printl(TEXT[1183]);out.printl(TEXT[1184])
            out.printl(TEXT[1185]);out.printl(TEXT[1186])
        if (yield from input_number(ctx))==1:
            c.talent[subject]=0 if old==1 else 1
            yield from wait(ctx,TEXT[1190])
    out.printl();out.printl();st.result[0]=0;return 0
