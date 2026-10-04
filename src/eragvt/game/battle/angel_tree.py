"""天使樹手翻。

依據 ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_LASTBOSS_2_天使の樹.ERB。
各函式的原作名稱與行號列於 docstring；只有原作現有資料及判定。
"""
from dataclasses import replace

from ..era import div, times


def access(ctx, key):
    """ERB/ゲーム内_戦闘処理/触手データ/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:198–307。"""
    from .core import tentacle_level, tentacle_status_hosei

    st = ctx.state
    st.results[0] = f"【エラー：{st.savestr[13]}_{st.flag[11]}に対するTENTACLE_ACCESS('{key}')関数失敗】"
    if key in ('NAME','GETNAME'):
        st.results[0] = name(st)
        st.result[0] = 0
        if key == 'NAME':
            ctx.out.print(st.results[0])
            return ''
        return st.results[0]
    if key in ('KOUGEKI','BOUGYO','SAKUSEI'):
        value = stat(ctx,key)
    elif key == 'ATTACK_ROUTINE':
        value = attack(ctx)
    elif key == 'HP':
        value = tentacle_status_hosei(st,10000,2500)
    elif key == 'SYASEI':
        value = 580+tentacle_level(st)*10
    else:
        value = getattr(data(st),key.lower())
        if key in ('BINSYOU','CHISEI'):
            value = tentacle_status_hosei(st,value,100 if key == 'BINSYOU' else 10)
    st.result[0] = value
    return value


def name(st):
    """@TENTACLE_LASTBOSS_2_GETNAME:8–15。"""
    return {1: '天使の樹', 2: '楽園の花'}.get(st.flag[21], '堕落の核')


def data(st):
    """@TENTACLE_LASTBOSS_2_DEFENITION:19 至 @TENTACLE_LASTBOSS_2_PALAM_HOSEI:290。"""
    from .core import LASTBOSSES

    phase = st.flag[21]
    if phase == 1:
        definition = ('（Ｋ触手の死体から生え出してきた巨大な柱状の構造物）',
                      '（中心につぼみが存在し、遠目からはまるで肉で出来た大樹のようにも見える）')
        palam = (150,150,150,150,100,150,150,150,50,50,50,50)
    elif phase == 2:
        definition = ('（天使の樹の中央にある巨大なつぼみが花開いた姿）',
                      '（周囲の広範囲にわたって虹色にきらめく謎の花粉を飛ばしている）')
        palam = (250,250,250,250,100,150,150,150,150,150,150,150)
    else:
        definition = ('（萎れた楽園の花から姿を現した天使の樹の中心核）',
                      '（周囲の地面からは柱状の触手が突き出てビルを薙ぎ倒している）')
        palam = (100,100,100,100,100,50,50,50,200,200,200,200)
    return replace(LASTBOSSES[1], name=name(st), definition=definition,
                   hp=(10000,2500), syasei=(580,10),
                   yudan={1:1500,2:3000}.get(phase,6000),
                   binsyou={1:50,2:200,3:250}.get(phase,100),
                   chisei={1:25,2:999}.get(phase,80),
                   short={1:250,2:150}.get(phase,85),
                   middle={1:240,2:150}.get(phase,85),
                   long={1:230,2:150}.get(phase,85),
                   hold={1:350,2:140}.get(phase,90),
                   palam_hosei=palam, stat_bonus=(10,25,100))


def stat(ctx, key):
    """@TENTACLE_LASTBOSS_2_SAKUSEI:47–53、_KOUGEKI:69–84、_BOUGYO:88–133。"""
    from .core import tc, tentacle_status_hosei, get_local, set_local

    st, c = ctx.state, tc(ctx)
    phase = st.flag[21]
    if key == 'SAKUSEI':
        # LOCAL 依函式保留：reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:24–30、69–70。
        func = 'TENTACLE_LASTBOSS_2_SAKUSEI'
        if phase >= 1:
            set_local(st,func,0,25 if phase >= 3 else 50)
        return get_local(st,func,0)
    if key == 'KOUGEKI':
        defense = c.base[ctx.data.index_of('BASE','防御')]
        divisor, bonus, minimum = (6,80,200) if phase == 1 else (4,160,250) if phase == 2 else (2,200,300)
        return tentacle_status_hosei(st,max(div(defense-100,divisor)+bonus,minimum),10)
    attack = c.base[ctx.data.index_of('BASE','攻撃')]
    divisor, bonus = (1,200) if phase == 1 else (2,50) if phase == 2 else (4,50) if phase == 3 else (4,25)
    value = div(attack-100,divisor)+bonus
    distance = c.tcvarn[0]
    if distance in (1,2,3):
        value = times(value,{1:'1.05',2:'0.85',3:'0.75'}[distance])
        if phase == 1 and not st.tflag[13] & (1 << (distance-1)):
            value = times(value,{1:'1.5',2:'2.5',3:'4.5'}[distance])
    return tentacle_status_hosei(st,value,25)


def attack(ctx):
    """@TENTACLE_LASTBOSS_2_ATTACK_ROUTINE:299–372；保留短路亂數順序。

    引擎：reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–553。
    """
    from .core import tc, percent_cal

    st, c = ctx.state, tc(ctx)
    hp = percent_cal(c.base[0],c.maxbase[0])
    mp = percent_cal(c.base[1],c.maxbase[1])
    phase, rand = st.flag[21], st.rng.rand
    if phase == 1:
        return (1 if hp else 2) if rand(100) < 70 else 3
    if hp and mp:
        if phase >= 3 and rand(4) == 0:
            return 2
        if (hp < mp and hp) or (hp and (rand(4) == 0 or phase >= 3 and rand(3) != 0)):
            roll = rand(100)
            return 1 if roll < 70 else 3 if roll < 80 else 6
        return 3 if rand(100) < 10 else 6
    if hp <= 0 and mp:
        roll = rand(100)
        return 2 if roll < 70 else 3 if roll < 80 else 6
    if mp <= 0 and hp:
        roll = rand(100)
        return 2 if roll < 70 else 1 if roll < 80 else 3
    return 2


def sex_routine(ctx):
    """@TENTACLE_LASTBOSS_2_SEX_ROUTINE:379–551，保留原作候選不足時填至101的寫法。

    FOR 終點一次求值：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1735–1743。
    """
    from .core import tc, t, abl, clear_randchoose, add_randchoose, choicecount, randchoose_f

    st, c = ctx.state, tc(ctx)
    rand = st.rng.rand
    clear_randchoose(st)
    for a,b,offset,strong in [('Ｃ敏感','淫核',0,1000),('Ｖ敏感','淫壷',2,1001),
                               ('Ａ敏感','淫尻',4,1002),('Ｂ敏感','淫乳',6,1003)]:
        if t(ctx,c,a) or t(ctx,c,b):
            for _ in range(10):
                roll = rand(100)
                lo, hi = (70,100) if c.palam[ctx.data.index_of('PALAM','潤滑')] < 2000 else (20,70)
                add_randchoose(st,offset if roll < lo else offset+1 if roll < hi else strong)
    if st.flag[21] == 1:
        for _ in range(abl(ctx,c,'自慰中毒')*3):
            rand(100)  # 原作有消耗但未使用。
            add_randchoose(st,1006)
        bounds = [(9,0),(12,1),(21,2),(24,3),(33,4),(36,5),(45,6),(48,7),(55,10),
                  (65,11),(75,1000),(80,1001),(85,1002),(90,1003),(95,1005),(100,1006)]
        limit = 100
    else:
        bounds = [(8,1),(16,3),(24,5),(32,7),(40,8),(48,9),(52,10),(56,11),(64,12),
                  (68,1000),(72,1001),(76,1002),(80,1003),(92,1004),(96,1005),(100,1007)]
        limit = 200
    if choicecount(st) < limit:
        for _ in range(101-choicecount(st)):
            roll=rand(100)
            add_randchoose(st,next(value for bound,value in bounds if roll < bound))
    st.result[0] = randchoose_f(st) if choicecount(st) else -1
    return st.result[0]


def change_phase(ctx):
    """ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:40–112。

    ELSEIF 每次最多變化一次；不補上原作沒有的最低HP或略過中間形態。
    """
    from .core import percent_cal

    st = ctx.state
    phase = st.flag[21]
    percent = percent_cal(st.flag[13],st.flag[12])
    st.result[0] = percent
    active = (phase == 1 and percent <= 75 or phase == 2 and percent <= 37
              or phase == 3 and percent <= 10 or phase == 4 and st.flag[13] <= 0)
    if not active:
        return
    # 文字片段額外的函式終端不是原作 inline PRINT；保存其前的 RESULT。
    def show(fragment):
        before = st.result[0]
        if not ctx.narration.run_function(ctx,fragment):
            raise NotImplementedError(f"天使樹原文片段不可執行：{fragment}")
        st.result[0] = before

    if phase == 3:
        show('MESSAGE_ANGEL_PHASE_3')
        heal = div(st.flag[12]*70,100)-st.flag[13]
        st.temp.locals[('SOURCE_CHECK',0)] = heal
        st.temp.locals[('MESSAGE_ANGEL_HEAL',0)] = heal
        show('MESSAGE_ANGEL_HEAL')
        st.flag[13] += heal
    else:
        show(f'MESSAGE_ANGEL_PHASE_{phase}')
    st.flag[21] = 0 if phase == 4 else phase+1
