"""一般身體／外貌編輯：CHARA_SIZE_UI.ERB@SIZE_SETTING:2–2142。

手寫原生狀態機。整頁只有99確認，
子頁取消保留已經寫入的設定（:1712–1715）。TARGET在正常返回恢復。
"""
from .body import generate_char_size, generate_bodyline, top_under, cup_size
from .body_editor_text import TEXT, LABELS
from .chara_common import talent, charatalent, is_female, is_male, seikaku_check
from .firstsetting import convert_age, convert_colorcstr, _talent_change
from .input_request import input_number, inputs
from .era import div, mod, limit, cp932_len
from .colorbar import setcolor, setcolor_by_str
from .opening import game_option
from ..state.constants import GameOption

SLOTS=(43,44,45,46,47,48)
RANDOM_FIELDS=('身長成長率乱数','身長補正乱数','体重乱数','胴囲乱数','腰囲乱数','アンダー乱数','胸の張り乱数','胸成長率乱数','胸サイズ補正乱数')
MODULI=(11,31,59,15,16,13,23,7,53)
COLORS=('255//8//8','8//255//125','8//125//255','255//255//8','255//8//255','255//125//8','255//8//125','205//205//205','88//8//8','40//24//24')
SKIN=('255//236//220','255//200//180','183//86//17','40//24//24')
MATCH_COLORS={649:(30,31),699:(31,30),748:(32,33),749:(32,34),798:(33,32),799:(33,35),848:(34,35),849:(34,32),898:(35,34),899:(35,33)}


def _cycle_sex(ctx, c, form):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1533–1606。"""
    data = ctx.data
    t = lambda name: talent(data, c, name)
    ct = lambda name: charatalent(data, c, 1, name)
    def put(name, value):
        c.talent[data.index_of('TALENT', name)] = value

    for slot in range(190, 194):
        if c.talent[slot]:
            c.talent[slot] = 0
            c.juel[data.index_of('JUEL', '修練P')] += 50
    if t('避妊結界'):
        put('避妊結界', 0)
        c.juel[data.index_of('JUEL', '修練P')] += 50
    if form:
        if ((is_male(data, c) and t('変身時ＴＳ') == 0)
                or (is_female(data, c) and t('変身時ＴＳ') == 1)) and t('変身時男の娘') == 0:
            put('変身時男の娘', 1)
        else:
            if ct('オトコ'):
                put('変身時外見', t('外見'))
                put('変身時男の娘', 1)
            put('変身時ＴＳ', 0 if t('変身時ＴＳ') > 0 else 1)
    elif is_male(data, c) and t('男の娘') == 0:
        put('男の娘', 1)
        put('変身時男の娘', 1)
    elif is_male(data, c):
        # :1564–1577 各SIF依序讀更新後的值，不提前快照或全面清零。
        for name, field, value in (('絶壁', '貧乳', 2), ('貧乳', '貧乳', 1),
                                    ('奇乳', '巨乳', 5), ('魔乳', '巨乳', 4),
                                    ('超乳', '巨乳', 3), ('爆乳', '巨乳', 2), ('巨乳', '巨乳', 1)):
            if ct(name): put(field, value)
        if not ct('オトコ'): put('外見', t('変身時外見'))
        for name in ('オトコ', '男の娘', '変身時男の娘'): put(name, 0)
    else:
        put('オトコ', 1)
        if not ct('オトコ'):
            put('変身時胸サイズ変動', t('巨乳') - t('貧乳'))
            put('変身時外見', t('外見'))
        for name in ('処女', '変身時非処女', '貧乳', '巨乳', '外見', 'ふたなり', 'アクセサリ'):
            put(name, 0)
    if ct('オトコ'):
        for name in ('変身時胸サイズ変動', '変身時外見', '変身時ふたなり'): put(name, 0)
    else:
        put('変身時男の娘', 0)


def _cycle_shape(ctx, c, form):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1608–1651。"""
    data = ctx.data
    t = lambda name: talent(data, c, name)
    ct = lambda name: charatalent(data, c, form, name)
    def put(name, value):
        c.talent[data.index_of('TALENT', name)] = value

    if form:
        field = '変身時胸サイズ変動'
        if any(ct(name) for name in ('巨乳', '爆乳', '超乳', '魔乳', '絶壁', '貧乳')):
            put(field, t(field) + 1)
        elif ct('奇乳'):
            put(field, -2)  # :1619 絕對-2，原作未扣通常形態數值。
        else:
            put(field, t(field) + 1)
            for _ in range(2):
                if not ct('巨乳'): put(field, t(field) + 1)
    else:
        for name, value in (('巨乳', 2), ('爆乳', 3), ('超乳', 4), ('魔乳', 5)):
            if ct(name):
                put('巨乳', value)
                return
        if ct('奇乳'):
            put('巨乳', 0); put('貧乳', 2)
        elif ct('絶壁'): put('貧乳', 1)
        elif ct('貧乳'): put('貧乳', 0)
        else: put('巨乳', 1)


def _cycle_body_trait(ctx, c, choice):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:1904–2048。

    只寫欄位與清理既有經驗；原文沒有年齡、NO、GLOBAL輸入限制。
    """
    data = ctx.data
    t = lambda name: talent(data, c, name)
    def put(name, value): c.talent[data.index_of('TALENT', name)] = value

    pairs = {70: ('濡れやすい', '濡れにくい'), 71: ('Ｃ敏感', 'Ｃ鈍感'),
             72: ('Ｖ敏感', 'Ｖ鈍感'), 73: ('Ａ敏感', 'Ａ鈍感'), 74: ('Ｂ敏感', 'Ｂ鈍感')}
    if choice in pairs:
        if choice in (70, 72) and is_male(data, c):
            if t('変身時ＴＳ') > 0:
                field = '変身時濡れやすさ変動' if choice == 70 else '変身時Ｖ感覚変動'
                put(field, -1 if t(field) > 0 else 0 if t(field) < 0 else 1)
        else:
            positive, negative = pairs[choice]
            values = (0, 1) if t(positive) > 0 else (0, 0) if t(negative) > 0 else (1, 0)
            put(positive, values[0]); put(negative, values[1])
    elif choice == 76:
        put('未熟', 1 if t('未熟') == 0 else 2 if t('未熟') == 1 else 0)
    elif choice == 81:
        female = is_female(data, c)
        normal, other, ability, ts = (t(n) for n in ('ふたなり', '変身時ふたなり', '変身能力', '変身時ＴＳ'))
        if normal == 0 and other == 0:
            if female:
                put('ふたなり', 3)
                if ability == 1 and ts == 0: put('変身時ふたなり', 3)
            elif ability == 1 and ts > 0: put('変身時ふたなり', 3)
        elif ability == 1 and ((female and ts == 0 and normal == 3 and other == 3)
                              or (not female and ts > 0 and other == 0)):
            put('ふたなり', 0); put('変身時ふたなり', 3)
        elif female and ts == 0 and normal == 0 and other == 3:
            put('ふたなり', 3); put('変身時ふたなり', 0)
        else:
            put('ふたなり', 0)
            if t('固有キャラ') == 0 and t('初期経験設定不可') == 0:
                c.exp[data.index_of('EXP', '射精経験')] = 0
            put('変身時ふたなり', 0)
    else:
        field = {75: 'パイパン', 80: '初心', 82: '母乳体質', 83: '苗床化', 84: '寄生'}[choice]
        before = t(field)
        put(field, int(before == 0))
        if choice == 84 and before != 0: put('共生', 0)


def _draw_body_traits(ctx, c):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:480–724。

    原文均為PRINTFORM，數字模式仍有按鈕；GLOBAL僅決定顯示。
    """
    out, data = ctx.out, ctx.data
    t = lambda name: talent(data, c, name)
    label = lambda line: LABELS[line].strip()
    female = is_female(data, c)
    eligible = female or t('変身時ＴＳ') > 0
    def row(title, value, choice, enabled=True):
        text = f'{label(title)}　{value}'
        if enabled: out.printl(f'{text} [{choice}]')
        else: out.print_plain(text); out.printl()

    for choice, title, transformed_title, positive, negative, high, low, delta in (
        (70, 483, 496, '濡れやすい', '濡れにくい', 487, 489, '変身時濡れやすさ変動'),
        (71, 531, 531, 'Ｃ敏感', 'Ｃ鈍感', 535, 537, None),
        (72, 574, 587, 'Ｖ敏感', 'Ｖ鈍感', 578, 580, '変身時Ｖ感覚変動'),
        (73, 630, 630, 'Ａ敏感', 'Ａ鈍感', 634, 636, None),
        (74, 660, 660, 'Ｂ敏感', 'Ｂ鈍感', 664, 666, None),
    ):
        if delta and not female:
            value = label(high) if t(delta) > 0 else label(low) if t(delta) < 0 else '―'
            row(transformed_title, value if eligible else '―', choice, eligible)
        else:
            value = label(high) if t(positive) > 0 else label(low) if t(negative) > 0 else '―'
            row(title, value, choice)
    row(690, label(697 if female else 695) if t('パイパン') > 0 else '―', 75)
    maturity = label(713) if t('未熟') == 1 else label(715) if t('未熟') == 2 else label(717) if t('ロボっ子') > 0 and female else '―'
    row(709, maturity, 76)
    row(517, label(521) if t('初心') > 0 else '―', 80)
    if ctx.globals.mem.global_[244]:
        normal, other = t('ふたなり') == 3, t('変身時ふたなり') == 3
        value = label(553 if normal and other else 555 if other else 557) if normal or other else '―'
        row(548, value if eligible else '―', 81, eligible)
    for key, choice, title, field in ((245, 82, 615, '母乳体質'), (253, 83, 645, '苗床化'), (255, 84, 675, '寄生')):
        if ctx.globals.mem.global_[key]:
            enabled = choice != 82 or eligible
            row(title, field if t(field) > 0 and enabled else '―', choice, enabled)


def _generated(ctx,c,form):
    """CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:249、283留下RESULTS及8格RESULT。"""
    ctx.state.results[0]=cup_size(top_under(ctx.data,c,form)[0])[1]
    return list(generate_char_size(ctx.data,c,form,ctx.state.result)[2:])


def _chip(out, color, value):
    setcolor_by_str(out,color)
    out.button('■',value)
    out.reset_color()


def _draw(ctx,c,ages,values,mode,locks):
    # DEVIATION: 沿用W07精簡列；兩形態依序顯示、一般數值與可選項保留，
    # 原文固定欄寬／字型留W07，見bridge/deviations.md「口上catalog的顯示簡化」。
    out,st,data=ctx.out,ctx.state,ctx.data
    editable=mod(mode,10)!=0 and mode!=2
    def mainline(text, enabled=True):
        if editable and enabled:out.printl(text)
        else:out.print_plain(text);out.printl()
    out.drawline()
    out.printl(f'{c.name} / {c.base[40]} 歳')
    mainline(TEXT[73]+'　'+TEXT[74])
    mainline(f'{TEXT[151]} [{0}] {ages[0]} 歳')
    if ages[1]>=0:mainline(f'[10] {ages[1]} 歳')
    if talent(data,c,'変身能力')==1:mainline('[20] 変化しない' if ages[1]>=0 else '[20] 変化する')
    for form in (0,1):
        if form and ages[1]<0:continue
        out.printl(TEXT[143] if form else TEXT[138])
        stature='小柄' if charatalent(data,c,form,'小柄') else '長身' if charatalent(data,c,form,'長身') else '―'
        mainline(f'{TEXT[187]} {div(values[form][0],10)}.{mod(values[form][0],10)} cm [{1+form*10}] {stature}', c.no==0)
        out.printl(f'{TEXT[236]} {div(values[form][1],10)}.{mod(values[form][1],10)} kg')
        male = charatalent(data,c,form,'オトコ')
        girly = talent(data,c,'変身時男の娘' if form else '男の娘')
        mainline(f'[{2+form*10}] '+LABELS[273 if male and girly else 275 if male else 278], c.no==0)
        shape = next((name for name in ('絶壁','貧乳','奇乳','魔乳','超乳','爆乳','巨乳') if charatalent(data,c,form,name)), '―')
        # :316、353只查NO，男性仍顯示按鈕；:1608另查性別，手輸不變更。
        mainline(f'[{3+form*10}] {shape}', c.no==0)
        looks='―'
        for name in ('安産型','むちむち','イカ腹','スレンダー','巨尻','爆尻'):
            if charatalent(data,c,form,name):looks=name
        mainline(f'[{4+form*10}] {looks}', c.no==0 and (not charatalent(data,c,form,'オトコ') or charatalent(data,c,form,'男の娘')))
        for label,value in zip(('Ｂ','Ｗ','Ｈ'),values[form][2:5]):
            out.printl(f'{label} '+(f'{div(value,10)}.{mod(value,10)} cm' if value>0 else '― cm'))
        # :341–344／378–380，純數值顯示仍須保留共用RESULT/RESULTS副作用。
        value,influence=top_under(data,c,form)
        st.result[1]=influence
        st.result[0],label=cup_size(value)
        st.results[0]=f'({label})'
    _draw_body_traits(ctx,c)
    mainline(f'{TEXT[763]} [5] {c.cstr[12]}')
    mainline(f'{TEXT[773]} [15] {c.cstr[13]}'+(f' [25] {c.cstr[14]}' if ages[1]>=0 else '')+' [35] ランダム')
    mainline(f'{TEXT[800]} [45] {c.cstr[18]}')
    # :810–828 顯示不查固有角色；:1892寫入才檢查。一般外觀判斷同
    # ERB/汎用関数/SEX_GENDER.ERB@ISGIRLY:28–37，不讀另一形態。
    girly = is_female(data,c) or talent(data,c,'男の娘') != 0
    accessory = {1:LABELS[815],2:LABELS[817],3:LABELS[819]}.get(talent(data,c,'アクセサリ'),'―')
    if girly:
        # :823 PRINTFORM始終產生按鈕，數字輸入模式只改顏色，按46仍作該模式數值。
        out.printl(f'{LABELS[811]} {accessory} [46]')
    else:out.print_plain(LABELS[811]+' ―');out.printl()
    if any(ctx.globals.mem.global_[k] for k in (212,258,262,278)) or game_option(st,GameOption.NO_ACHIEVEMENT_END):
        status={1:LABELS[735],2:LABELS[737],3:LABELS[739],4:LABELS[741],9:LABELS[743]}.get(c.cflag[0],'―')
        # :726 ARG:1為本函式未寫入／未宣告參數的0格，不是呼叫端共用ARG。
        # reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:330–331；
        # reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:23–29、36–70；
        # reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1726–1738。
        # 正常呼叫沒有「鎖初期狀態」參數。
        out.printl(f'{LABELS[730]} {status} [86]')
    for label,numbers in ((835,(6,16)),(868,(7,8,17,18)),(927,(9,19))):
        out.print(TEXT[label])
        for n in numbers:
            if n>=10 and ages[1]<0:continue
            k={6:30,16:31,7:32,8:33,17:34,18:35,9:36,19:37}[n]
            if editable:_chip(out,c.cstr[k],n)
            else:out.print_plain(f'[{n}] ■')
        out.printl()
    mainline('[30] オートローラー [40] 再生成')
    if mode in (0,10,2):
        out.printl(TEXT[992] if mode==2 else TEXT[971])
        for start in range(10,30,5):
            out.printl(' '.join(f'[{n}] {n} 歳' for n in range(start,start+5)))
        out.printl(TEXT[1450])
    elif mode in (5,15,25,45):
        count,base,value,title={5:(9,30000,100,1005),15:(15,30100,200,1023),25:(15,30100,250,1023),45:(14,30200,300,1041)}[mode]
        out.printl(TEXT[title])
        for i in range(count):out.printl(f'[{value+i}] {data.str_defaults.get(base+i,"")}')
    elif mod(mode,10) in (6,7,8):
        bases=(600,650) if mode in (6,16) else (700,750) if mode in (7,8) else (800,850)
        for base in bases:
            if base==650 and ages[1]<0:continue
            out.button('パレット',base)
            for i,color in enumerate(COLORS,1):_chip(out,color,base+i)
            for n,(to,source) in MATCH_COLORS.items():
                if div(n,50)*50==base and not (ages[1]<0 and (to in (31,34,35) or source in (31,34,35))):
                    _chip(out,c.cstr[source],n)
            out.printl()
    elif mod(mode,10)==9:
        out.printl(TEXT[1250])
        for base in ((900,950) if ages[1]>=0 else (900,)):
            for i,color in enumerate(SKIN):_chip(out,color,base+i)
            out.printl()
    elif mode==1:
        out.printl(TEXT[1300]+TEXT[1301])
        for i,(name,m) in enumerate(zip(RANDOM_FIELDS,MODULI)):
            out.printl(f'[{1100+i*100}] {name} {mod(c.cflag[33],m)} ({talent(data,c,name)})')
    elif 1100<=mode<2000:
        if mode%100==0:
            i=(mode-1100)//100
            out.printl(TEXT[1346+i*3]);out.printl(TEXT[1347+i*3])
        out.printl(TEXT[1375])
    else:
        # @SEIKAKU_CHECK("STRING"):19–20返回RESULT並寫字串，:1378–1380改未設定字樣。
        k=seikaku_check(data,c)
        st.result[0]=k
        st.results[0]=data.names['TALENT'].get(k,'') if k else '未設定'
        out.printl(f'パーソナリティ（性格：{st.results[0]}）')
        for i in range(3):
            out.printl(f'[{60+i}] {c.cstr[40+i]} [{160+i}] ロック {locks[i]} [{260+i}] 消去')
        out.printl('[69] オートローラー')
    cancel=-1 if 1100<=mode<2000 else 30 if mode==1 else ages[mode//10] if mode in (0,10) else c.base[40] if mode==2 else 99 if mode<0 else mode
    cancel_text=f'[{cancel:2d}]キャンセル'
    if 1100<=mode<2000 or mode==1 or mode in (0,10,2):cancel_text=f'[{cancel:2d}] キャンセル'
    elif mode<0:cancel_text='[99]決定して戻る'
    out.printl(cancel_text)
    # :1449 STRLENS；reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2095–2107
    # → _Library/LangManager.cs:17–20（本作日文設定為cp932位元組）。
    st.result[0]=cp932_len(cancel_text)


def size_setting(ctx,who):
    """ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:21–2142。"""
    st,data,out=ctx.state,ctx.data,ctx.out;c=st.charas[who]
    keep=st.target;st.target=who;line=out.linecount
    convert_colorcstr(c);convert_age(c)
    ages=[c.base[41],c.maxbase[41]];real=c.base[40]
    values=[[a[s] for s in SLOTS] for a in (c.base,c.maxbase)]
    T=lambda n:talent(data,c,n)
    CT=lambda f,n:charatalent(data,c,f,n)
    def put(name,value):c.talent[data.index_of('TALENT',name)]=value
    def colors_equal():return all(c.cstr[a]==c.cstr[b] for a,b in ((30,31),(32,34),(33,35),(36,37)))
    display=3
    if T('変身能力')<1:ages[1]=-1;display&=~2
    if ages[0]==ages[1] and _talent_change(ctx,c)==0 and values[0][:5]==values[1][:5] and c.cstr[13]==c.cstr[14] and colors_equal():ages[1]=-1
    locks=[0,0,0];mode=-1
    while True:
        c.base[40]=real;c.base[41]=ages[0];c.maxbase[41]=ages[1]
        for form in (0,1):
            if display&(1<<form) and (not form or ages[1]>=0):values[form]=_generated(ctx,c,form)
        # DISPLAY_FLAG=-1 (:1458)含bit3；CAL_VAR各範圍從未有非零寫入，
        # 所以:97–130首輪僅驗0..9999，負數體型仍需原作5000輪。
        if display&8:
            for attempt in range(5000):
                if c.cflag[34]==0:generate_bodyline(st,data,c)
                check=_generated(ctx,c,0)
                if all(0<=v<=9999 for v in check[:5]):
                    values[0]=check
                    if ages[1]>=0:values[1]=_generated(ctx,c,1)
                    break
        _draw(ctx,c,ages,values,mode,locks)
        r=yield from input_number(ctx);display=-1
        if mode==2:
            if 0<=r<=99999:real=r;mode=-1
        elif mod(mode,10)==0:
            if mode<1000:
                if 0<=r<=99999:ages[div(mode,10)]=r;mode=-1
            elif r<0:mode=1
            elif mode%100==0 and 1100<=mode<=1900:
                i=(mode-1100)//100
                if 0<=r<=MODULI[i]:put(RANDOM_FIELDS[i],r);mode=1
        elif mod(r,10)==1 and 0<=r<20 and c.no==0:
            form=div(r,10)
            if form:
                if CT(1,'長身'):
                    put('変身時体格変動',T('変身時体格変動')-1)
                    if not CT(1,'小柄'):put('変身時体格変動',T('変身時体格変動')-1)
                elif CT(1,'小柄'):
                    put('変身時体格変動',T('変身時体格変動')+1)
                    if CT(1,'小柄'):put('変身時体格変動',T('変身時体格変動')+1)
                else:
                    put('変身時体格変動',T('変身時体格変動')+1)
                    if not CT(1,'長身'):put('変身時体格変動',T('変身時体格変動')+1)
            elif CT(0,'長身'):put('長身',0);put('小柄',1)
            elif CT(0,'小柄'):put('小柄',0)
            else:put('長身',1)
        elif r in (2,12) and c.no==0:
            _cycle_sex(ctx,c,div(r,10))
        elif r in (3,13) and not CT(div(r,10),'オトコ') and c.no==0:
            _cycle_shape(ctx,c,div(r,10))
        elif r in (4,14) and c.no==0 and (not CT(div(r,10),'オトコ') or CT(div(r,10),'男の娘')):
            field='外見' if r==4 else '変身時外見'
            put(field,T(field)+1 if 1<=T(field)<=5 else 0 if T(field)==6 else 1)
            if r==4 and not CT(1,'オトコ'):put('変身時外見',T('外見'))
        elif r==20 and T('変身能力')==1:
            for field in ('変身時ＴＳ','変身時体格変動','変身時胸サイズ変動'):put(field,0)
            put('変身時外見',T('外見'));values[1][:5]=values[0][:5]
            for a,b in ((14,13),(31,30),(34,32),(35,33),(37,36)):c.cstr[a]=c.cstr[b]
            ages[1]=ages[0] if ages[1]<0 else -1;mode=-2
        elif r==30 and mode==1:mode=-1
        elif r==mode and mode!=-1:mode=-1
        elif (r<10 or r==15 or (r<=25 and ages[1]>=0) or r==45) and mod(r,10) not in (3,4):mode=r
        elif r==40:generate_bodyline(st,data,c);display=3
        elif r==35:
            for slot,base,n in ((12,30000,9),(13,30100,15),(14,30100,15)):c.cstr[slot]=data.str_defaults.get(base+st.rng.rand(n),'')
            if mode in (5,15,25):mode=-1
        elif r==99 and mode<0:
            compact=[c.cstr[k] for k in (40,41,42) if c.cstr[k]]
            for k,value in enumerate(compact+['']*(3-len(compact)),40):c.cstr[k]=value
            if is_female(data,c) or not T('変身時ＴＳ'):
                put('変身時濡れやすさ変動',0);put('変身時Ｖ感覚変動',0)
            break
        elif 100<=r<109 and mode==5:c.cstr[12]=data.str_defaults.get(29900+r,'')
        elif (200<=r<215 or 250<=r<265) and mode in (15,25):c.cstr[13+div(r-200,50)]=data.str_defaults.get(30100+r%50,'')
        elif 300<=r<314 and mode==45:c.cstr[18]=data.str_defaults.get(29900+r,'')
        elif 600<=r<900 and r%50==0:
            slot=30+div(r-600,50)
            yield from color_table(ctx)
            if st.result[0]>0:c.cstr[slot]='//'.join(str(st.result[i]) for i in (1,2,3))
            display|=4
        elif 600<=r<900 and 1<=r%50<11:c.cstr[div(r,50)+18]=COLORS[r%50-1]
        elif r in MATCH_COLORS:
            dst,src=MATCH_COLORS[r];c.cstr[dst]=c.cstr[src]
        elif 900<=r<1000:
            if r%10<4:c.cstr[div(r,50)+18]=SKIN[r%10]
        elif r==1000:
            for field in RANDOM_FIELDS:put(field,0)
        elif 1100<=r<2000 and r%100 in (0,10):mode=r
        elif r in (1020,1120,1220,1320,1420):pass # :1837–1851，未設過的CAL_VAR範圍清零。
        elif r==30:mode=1
        elif r==50:mode=2
        elif r==51:real=ages[0];c.base[40]=real
        elif 60<=r<=62 and mode<0:yield from set_personality(ctx,who,r-20)
        elif 160<=r<=162 and mode<0:locks[r-160]^=1
        elif 260<=r<=262 and mode<0:c.cstr[r-220]=''
        elif r==69 and mode<0 and not all(locks):
            # :1874–1888比較的是字面字串，不擅自修成去重。
            for i in range(3):
                if locks[i]:continue
                while True:
                    v=data.str_defaults.get(30500+st.rng.rand(500),'');c.cstr[40+i]=v
                    rejected=(not v or v in (('CSTR:ARG:41','CSTR:ARG:42') if i==0 else ('CSTR:ARG:40','CSTR:ARG:41') if i==2 else ('CSTR:ARG:40',)) or (i==1 and c.cstr[40]=='CSTR:ARG:42'))
                    if not rejected:break
        elif r==46:
            if (is_female(data,c) or T('男の娘')) and T('固有キャラ')==0:
                put('アクセサリ',T('アクセサリ')+1 if T('アクセサリ') in (1,2) else 0 if T('アクセサリ')==3 else 1)
        elif 70<=r<=76 or 80<=r<=84:
            _cycle_body_trait(ctx,c,r)
        elif r==85:pass  # ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:2049–2051 未使用。
        elif r==86:
            # @SIZE_SETTING:2053–2102與CHARA_MAKE.ERB@CHARA_MAKE_MAIN:150–198逐條相同。
            from .creation_menu import _cycle_initial_state
            _cycle_initial_state(ctx,who)
        # :2106，-1含bit2，因此一般操作不清舊頁；保持原文。
        if not display&4:out.clearline(out.linecount-line)
    if ages[1]==ages[0] and not _talent_change(ctx,c) and values[0][0]==values[1][0] and values[0][2]==values[1][2] and colors_equal():ages[1]=-1
    c.base[40]=real;c.base[41]=ages[0]
    for slot,value in zip(SLOTS,values[0]):c.base[slot]=value
    if ages[1]>=0 or T('変身能力')==1:
        form=1 if ages[1]>=0 else 0;c.maxbase[41]=ages[form]
        for slot,value in zip(SLOTS,values[form]):c.maxbase[slot]=value
    st.target=keep
    # reference/.../GameProc/Process.ScriptProc.cs:61–67自然終端只改RESULT:0。
    st.result[0]=0


def set_personality(ctx,who,slot):
    """CHARA_SIZE_UI.ERB@SET_PERSONALITY:2230–2282。"""
    st,data,out=ctx.state,ctx.data,ctx.out;c=st.charas[who]
    line=out.linecount
    names=['']*20
    while True:
        for i in range(20):
            while True:
                value=data.str_defaults.get(30500+st.rng.rand(500),'')
                # :2241、2244是一般引號，不插值；不擅自修成候選去重。
                # reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:917–936。
                if value and value not in ('%CSTR:ARG:40%','%CSTR:ARG:41%','%CSTR:ARG:42%','%LOCALS:(LOCAL:1)%'):break
            names[i]=value
        while True:
            for i,value in enumerate(names):out.printl(f'[{i}] {value}')
            for n in (2258,2260,2261):out.printl(TEXT[n])
            r=yield from input_number(ctx)
            if r==999:st.result[0]=0;return
            if 0<=r<20:c.cstr[slot]=names[r];st.result[0]=0;return
            if r==20:
                value=yield from inputs(ctx)
                if value:c.cstr[slot]=value;st.result[0]=0;return
            out.clearline(out.linecount-line)
            if r==200:break


def color_table(ctx):
    """ERB/汎用関数/COLOR_TABLE.ERB@COLOR_TABLE:2–158，32×32色盤。

    #DIM為static：reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1846–1853。
    軸／MODE／選色／明度跨呼叫保留；僅軸色在入口重設8。
    """
    st,out=ctx.state,ctx.out
    local=st.temp.locals
    v=[local.get(('COLOR_TABLE',i),0) for i in range(6)]
    axis,mode,red,green,blue,bright=v;axiscolor=8
    start=out.linecount
    while True:
        for row in range(32):
            for col in range(32):
                rgb=(limit((axis==0)*axiscolor+(axis==1)*(256-(row+1)*8)+(axis==2)*(col+1)*8,0,255),limit((axis==1)*axiscolor+(axis==2)*(256-(row+1)*8)+(axis==0)*(col+1)*8,0,255),limit((axis==2)*axiscolor+(axis==0)*(256-(row+1)*8)+(axis==1)*(col+1)*8,0,255))
                setcolor(out,*rgb);out.button('■',10000+col*100+row)
            setcolor(out,*[limit(256-row*8,0,255) if i==axis else 0 for i in range(3)])
            out.button('■',20000+row)
            out.reset_color()
            out.print_plain('◄' if row==32-div(axiscolor,8) else ' ')
            if mode==1:
                setcolor(out,*[div(v*(32-row),32) for v in (red,green,blue)])
                out.button('■',30000+row)
                out.reset_color();out.print_plain(f' 明度 {div(100*(32-row),32)}％')
            out.reset_color();out.printl()
        if mode==0:out.printl('軸の色を変更 [0] 赤 [1] 緑 [2] 青')
        else:
            for i,v in enumerate((red,green,blue),1):st.result[i]=limit(div(v*bright,32),0,255)
            out.printl(f'この色でよろしいですか？（{st.result[1]}, {st.result[2]}, {st.result[3]}, 明度選択：{div(100*bright,32)}％） [0] はい [1] いいえ')
            if st.result[0]==0:break # 原作:86–88，在INPUT之前檢查共用殘值。
        out.printl('[99] 戻る')
        r=yield from input_number(ctx)
        if 0<=r<3:
            if mode==0:axis=r
            elif r==0:st.result[0]=1;break
            else:mode=0
        elif r==99:
            for i in range(4):st.result[i]=-1
            break
        elif 10000<=r<13232:
            high=limit(256-r%100*8,0,255);low=limit((div(r,100)%100+1)*8,0,255)
            if axis==0:red,green,blue=limit(axiscolor,0,255),low,high
            elif axis==1:red,green,blue=high,limit(axiscolor,0,255),limit(((div(r,100)+1)%100)*8,0,255)
            else:red,green,blue=low,high,limit(axiscolor,0,255)
            bright=32;mode=1
        elif 20000<=r<20032:axiscolor=(32-r%100)*8
        elif 30000<=r<30032:bright=30032-r
        else:break
        # DEVIATION: 沿W07實際輸出行數清除，對應COLOR_TABLE.ERB:156固定40行。
        out.clearline(out.linecount-start)
    for i,value in enumerate((axis,mode,red,green,blue,bright)):local[('COLOR_TABLE',i)]=value
