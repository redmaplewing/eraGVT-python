"""ERB/ヒロイン関連/TRANS_SEX.ERB 的三種轉換；遊戲邏輯手寫，逐題等待輸入。

INPUT只寫RESULT:0：reference/emuera-1824/Emuera/GameProc/Process.cs:249–252。
RETURN只覆寫提供的格數，尾格保留：reference/emuera-1824/Emuera/GameProc/Function/
Instraction.Child.cs:1997–2023、GameData/Variable/VariableEvaluator.cs:1732–1740。
"""
from .body import generate_char_size
from .chara_common import charatalent, talent
from .colorbar import setcolor_by_str
from .input_request import input_number
from .battle.func import transform
from .battle.cloth import cloth_battle_hosei

_BUST = ('絶壁', '貧乳', '普通', '巨乳', '爆乳', '超乳', '魔乳', '奇乳')
_LOOK = ('普通', '安産型', 'むちむち', 'イカ腹', 'スレンダー', '巨尻', '爆尻')


def _choose(ctx, valid):
    while True:
        value = yield from input_number(ctx)
        if value in valid:
            ctx.out.printl()
            return value


def _ct(ctx, form, name):
    return charatalent(ctx.data, ctx.state.target_chara, form, name)


def _bust(ctx, form):
    # 原文判定順序；普通回傳0，但「合わせる」分支沒有普通的賦值。
    for name, value in (('絶壁', -2), ('貧乳', -1), ('奇乳', 5), ('魔乳', 4),
                        ('超乳', 3), ('爆乳', 2), ('巨乳', 1)):
        if _ct(ctx, form, name):
            return value
    return 0


def _body(ctx, form):
    return -1 if _ct(ctx, form, '小柄') else 1 if _ct(ctx, form, '長身') else 0


def _set(ctx, name, value):
    ctx.state.target_chara.talent[ctx.data.index_of('TALENT', name)] = value


def _t(ctx, name):
    return talent(ctx.data, ctx.state.target_chara, name)


def _set_bust(ctx, value):
    _set(ctx, '貧乳', max(-value, 0))
    _set(ctx, '巨乳', max(value, 0))


def _set_body(ctx, value):
    _set(ctx, '小柄', int(value < 0))
    _set(ctx, '長身', int(value > 0))


def _size(ctx, form):
    c, st = ctx.state.target_chara, ctx.state
    if c.cflag[34] > 0:
        values = generate_char_size(ctx.data, c, form, st.result)
        base = c.maxbase if form else c.base
        for slot, value in zip(range(43, 49), values[2:]):
            base[slot] = value


def _sensitivity(ctx, clear=False):
    for delta, positive, negative in (('変身時濡れやすさ変動', '濡れやすい', '濡れにくい'),
                                     ('変身時Ｖ感覚変動', 'Ｖ敏感', 'Ｖ鈍感')):
        value = _t(ctx, delta)
        if value:
            _set(ctx, positive if value > 0 else negative, 1)
        if clear:
            _set(ctx, delta, 0)


def _look_choice(ctx, normal_slots, transformed_slots, label, destination):
    c, out = ctx.state.target_chara, ctx.out
    if all(c.cstr[a] == c.cstr[b] for a, b in zip(normal_slots, transformed_slots)):
        return
    out.printl(f'【{"通常時" if destination == 0 else "変身後"}】　{label}　を選択してください')
    for value, slots, form in ((0, transformed_slots, '変身後'), (1, normal_slots, '通常時')):
        out.print(f'[{value}] {form}の{"ヘアスタイル" if normal_slots == (13,) else "色"} [')
        for index, slot in enumerate(slots):
            if index:
                out.print('][')
            if slot == 13 or slot == 14:
                out.print(c.cstr[slot])
            else:
                ctx.state.result[0] = setcolor_by_str(out, c.cstr[slot])
                out.print('■')
                out.reset_color()
        out.printl('] を引き継ぐ')
    choice = yield from _choose(ctx, (0, 1))
    if choice == destination:
        dst, src = (normal_slots, transformed_slots) if destination == 0 else (transformed_slots, normal_slots)
        for a, b in zip(dst, src):
            c.cstr[a] = c.cstr[b]


def _colors(ctx, mode):
    yield from _look_choice(ctx, (13,), (14,), 'ヘアスタイル', 0)
    for a, b, label in (((30,), (31,), '髪の色'), ((32,33), (34,35), '瞳の色'), ((36,), (37,), '肌の色')):
        if mode != 'ftom':
            normal_label = '瞳の色選択' if mode == 'normal' and a == (32,33) else label
            yield from _look_choice(ctx, a, b, normal_label, 0)
        if mode == 'ftom' or (mode == 'normal' and _t(ctx, '変身能力') > 0 and _t(ctx, '変身時ＴＳ') == 0):
            yield from _look_choice(ctx, a, b, label, 1)


def _finish(ctx, keep, trans):
    if trans:
        transform(ctx, 1)
    ctx.state.target = keep
    ctx.state.result[0] = 1
    return 1


def ts_mtof(ctx, who):
    """ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF:4–173。"""
    st = ctx.state
    keep, st.target = st.target, who
    c = st.target_chara
    trans = c.cflag[1] > 0
    if not trans:
        st.result[0] = transform(ctx, 1)
    _set(ctx, '変身時体格変動', 0)
    _set(ctx, '変身時胸サイズ変動', 0)
    c.base[41] = c.maxbase[41]
    # :27–42兩次讀取之間沒有改衣裝；保留原判定與呼叫順序。
    airplus = st.result[0] = cloth_battle_hosei(ctx, 'AIRPLUS', who)
    r = st.result[0] = cloth_battle_hosei(ctx, 'AIRPLUS', who)
    if airplus == 0 and r > 0:
        c.maxbase[22] += 1
        c.base[22] = min(c.maxbase[22], 5)
    elif airplus == 1 and r == 0:
        c.maxbase[22] -= 1
        c.base[22] = max(c.maxbase[22], 0)
    c.cflag[1] = 0
    for name, value in (('性別変化',1),('オトコ',0),('男の娘',0)):
        _set(ctx,name,value)
    if _t(ctx,'変身時非処女') == 0:
        _set(ctx,'処女',1)
    _set(ctx,'変身時ＴＳ',-1)
    _set(ctx,'変身時非処女',0)
    _set(ctx,'外見',_t(ctx,'変身時外見'))
    _set(ctx,'ふたなり',_t(ctx,'変身時ふたなり'))
    _sensitivity(ctx, clear=True)
    _size(ctx, 0)
    ctx.out.printl()
    yield from _colors(ctx, 'mtof')
    return _finish(ctx, keep, trans)


def ts_ftom(ctx, who):
    """ERB/ヒロイン関連/TRANS_SEX.ERB@TS_FtoM:179–346。"""
    st = ctx.state
    keep, st.target = st.target, who
    c = st.target_chara
    trans = c.cflag[1] > 0
    if not trans:
        st.result[0] = transform(ctx, 1)
    for name, value in (('性別変化',10),('オトコ',0),('男の娘',0),('変身時ＴＳ',-1)):
        _set(ctx,name,value)
    if _t(ctx,'処女') < -2:
        _set(ctx,'処女',_t(ctx,'処女') + 5)
    c.maxbase[41] = c.base[41]
    value = _bust(ctx, 0)
    if value:
        _set_bust(ctx,value)
    value = _body(ctx, 0)
    if value:
        _set_body(ctx,value)
    for name in ('変身時体格変動','変身時胸サイズ変動'):
        _set(ctx,name,0)
    _set(ctx,'変身時外見',_t(ctx,'外見'))
    _set(ctx,'変身時ふたなり',_t(ctx,'ふたなり'))
    c.cflag[1] = 0
    _size(ctx, 1)
    ctx.out.printl()
    yield from _colors(ctx, 'ftom')
    return _finish(ctx, keep, trans)


def _bust_menu(ctx, form, match=None):
    out = ctx.out
    out.printl(f'【{"変身後" if form else "通常時"}】　胸サイズ　を選択してください')
    if match is not None:
        out.printl(f'[0] {"通常時" if form else "変身後"} [{_BUST[match+2]}] に合わせる')
    # @TS_NORMAL:404–405／548–549：保留選項末尾的兩個全形空白。
    out.printl('[1] 絶壁　　[2] 貧乳　　[3] 普通　　')
    out.printl('[4] 巨乳　　[5] 爆乳　　[6] 超乳　　[7] 魔乳　　[8] 奇乳　　')
    return (yield from _choose(ctx, range(0 if match is not None else 1, 9)))


def _body_menu(ctx, form, match):
    out = ctx.out
    out.printl(f'【{"変身後" if form else "通常時"}】　体格　を選択してください')
    names = {-1:'小柄', 0:'普通', 1:'長身'}
    if match:
        out.printl(f'[0] {"通常時" if form else "変身後"} [{names[_body(ctx,1-form)]}] に合わせる')
    out.printl(f'[1] {"変身後" if form else "通常時"} [{names[_body(ctx,form)]}] のままにする')
    for line in ('[2] 小柄　　', '[3] 普通　　', '[4] 長身　　'):
        out.printl(line)
    return (yield from _choose(ctx, range(0 if match else 1, 5)))


def _appearance(ctx, form, match):
    out = ctx.out
    out.printl(f'【{"変身後" if form else "通常時"}】　外見的特徴　を選択してください')
    value = _t(ctx,'外見' if form else '変身時外見')
    if match:
        out.printl(f'[0] {"通常時" if form else "変身後"} [{_LOOK[value] if 0 <= value < len(_LOOK) else "普通"}] に合わせる')
    # @TS_NORMAL:637–643／677–683：通常時[6]有三格，變身後[6]沒有尾空白。
    labels = ('安産型　　', 'むちむち　', 'イカ腹　　', 'スレンダー', '巨尻　　　',
              '爆尻' if form else '爆尻　　　', '普通　　　')
    for i, name in enumerate(labels, 1):
        out.printl(f'[{i}] {name}')
    choice = yield from _choose(ctx, range(0 if match else 1, 8))
    _set(ctx,'変身時外見' if form else '外見', value if choice == 0 else 0 if choice == 7 else choice)


def ts_normal(ctx, who):
    """ERB/ヒロイン関連/TRANS_SEX.ERB@TS_NORMAL:352–925。"""
    st = ctx.state
    keep, st.target = st.target, who
    c = st.target_chara
    if _ct(ctx,0,'オトコ') == 0:
        # :359–362原作錯誤返回先於TARGET恢復；不能改成finally。
        # DEVIATION: 舊PRINTW只標示等待，未阻塞；見docs/wiki/bridge/deviations.md「WAIT／PRINTW 不阻塞」（W07）。
        ctx.out.printw('　! ERROR ! 通常時の性別が女性なのに通常の女体化シーケンスが呼び出されました')
        st.result[0] = 0
        return 0
    trans = c.cflag[1] > 0
    st.result[0] = transform(ctx, 0)
    has_ts = _t(ctx,'変身時ＴＳ') > 0
    breast = _bust(ctx,1) if has_ts else 0
    choice = yield from _bust_menu(ctx,0,breast if has_ts else None)
    if choice or breast:
        _set_bust(ctx,choice-3 if choice else breast)
    if has_ts:
        _set(ctx,'変身時胸サイズ変動',breast-_t(ctx,'巨乳')+_t(ctx,'貧乳'))
    body = _body(ctx,1) if _t(ctx,'変身能力') > 0 else 0
    choice = yield from _body_menu(ctx,0,has_ts)
    if choice == 0:
        value = _body(ctx,1)
        if value:
            _set_body(ctx,value)
    elif choice != 1:
        _set_body(ctx,choice-3)
    if _t(ctx,'変身能力') > 0:
        _set(ctx,'変身時体格変動',body-_t(ctx,'長身')+_t(ctx,'小柄'))
    if _t(ctx,'変身能力') > 0 and _t(ctx,'変身時ＴＳ') == 0:
        choice = yield from _bust_menu(ctx,1,_bust(ctx,0))
        small,big = _t(ctx,'貧乳'),_t(ctx,'巨乳')
        # :566–587：1／2原式是small+big；不能「修正」成相減。
        delta = 0 if choice == 0 else small+big+choice-3 if choice <= 2 else small-big+choice-3
        _set(ctx,'変身時胸サイズ変動',delta)
        choice = yield from _body_menu(ctx,1,True)
        small,tall = _t(ctx,'小柄'),_t(ctx,'長身')
        if choice != 1:
            delta = 0 if choice == 0 else small+tall+choice-3 if choice <= 3 else small-tall+1
            _set(ctx,'変身時体格変動',delta)
    yield from _appearance(ctx,0,has_ts)
    if _t(ctx,'変身能力') > 0 and _t(ctx,'変身時ＴＳ') == 0:
        yield from _appearance(ctx,1,True)
    _sensitivity(ctx)
    if has_ts:
        _set(ctx,'性別変化',1)
        _set(ctx,'ふたなり',_t(ctx,'変身時ふたなり'))
    else:
        _set(ctx,'性別変化',11 if _t(ctx,'変身能力') > 0 else 1)
    for name in ('オトコ','男の娘','変身時男の娘'):
        _set(ctx,name,0)
    if _t(ctx,'変身時非処女') == 0:
        _set(ctx,'処女',1)
    if _t(ctx,'変身能力') > 0:
        if has_ts:
            _set(ctx,'変身時ＴＳ',-1)
            _set(ctx,'変身時非処女',0)
        _size(ctx,1)
    _size(ctx,0)
    yield from _colors(ctx,'normal')
    return _finish(ctx,keep,trans)
