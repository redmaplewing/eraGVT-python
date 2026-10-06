"""情報収集（S28a）：`ゲーム内_行動実行処理/ACTION_GATHER_INFORMATION.ERB` と補助関数。

路徑相對 `source/earGVP/ERB/`。
- `@GATHER_INFORMATION`:3–88、`@MESSAGE_GATHER_INFORMATION`:91–1074（4 種：噂話・事件の捜査・情報を買う・仲間の捜索）。
- `ACTIONsub_TRANSFORMATION_SELECT.ERB@ACTION_TRANSFORMATION_SELECT`:3–136（GLOBAL:54〜56 の変身設定）。
- `特別活動/CALC_CHARM_FEAT.ERB@CALC_CHARM_FEAT_OTHER`:22–59、`汎用関数/コモン関数.ERB@CHARA_LIST`:303–355、
  `汎用関数/CHARANUM.ERB@CHARANUM_PRISON`:50–57。

S36：市民遭遇接到 battle.citizen；事件調查由 FLAG:802 bit5 控制，救援遭遇依原作不檢查此設定。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState
from ..state.constants import CharaState
from .action import Ctx, _wait_or_line, config_check_event, print_transcallname
from .chara_common import charatalent, is_female, is_male, talent
from .era import div, format_percent, isqrt

InputGen = Generator[None, int, None]

_FN = "MESSAGE_GATHER_INFORMATION"
_KEY_LOCALS = (_FN + ":LOCALS", 0)  # 関数の LOCALS（静的：VariableData.cs@SetDefaultLocalValue:514–520）
_KEY_NAKADASHI = (_FN + ":NAKADASHI", 0)  # `#DIM NAKADASHI`（静的・初期化なし：GameProc/UserDefinedVariable.cs:27 Static = true）
_KEY_TF_LOCAL = ("ACTION_TRANSFORMATION_SELECT", 0)  # 同関数の LOCAL（静的）


def charanum_prison(st: GameState) -> int:
    """`@CHARANUM_PRISON`（CHARANUM.ERB:50–57）：CFLAG:0 が 1／2／3 の人数。"""
    return sum(1 for i in range(1, st.charanum) if st.charas[i].cflag[0] in (1, 2, 3))


def charanum_enslaved(st: GameState) -> int:
    """`@CHARANUM_ENSLAVED`（CHARANUM.ERB:70–77）：CFLAG:0 == 4 の人数。"""
    return sum(1 for i in range(1, st.charanum) if st.charas[i].cflag[0] == CharaState.KIDNAPPED)


def lost_count(st: GameState) -> int:
    """GATHER_INFORMATION:9／SCHEDULE:29 の `LOST = CHARANUM_PRISON() + CHARANUM_ENSLAVED()`。"""
    return charanum_prison(st) + charanum_enslaved(st)


def _pd(ctx: Ctx, items: tuple[str, ...]) -> str:
    """PRINTDATA／PRINTDATAL：DATAFORM から 1 件を乱数で選ぶ。"""
    return items[ctx.state.rng.rand(len(items))]


# --- @GATHER_INFORMATION ------------------------------------------------------------


def gather_information(ctx: Ctx) -> InputGen:
    """`@GATHER_INFORMATION`:3–88（TARGET が対象）。:88 の BEGIN TURNEND は呼び出し元（ACTION_MAIN:151–155）が上書きする。"""
    from .battle.ablup import ablup
    from .battle.func import transform
    from .schedule import res_schedule

    st, out = ctx.state, ctx.out
    c = st.target_chara
    lost = lost_count(st)  # :9
    yield from action_transformation_select(ctx, st.target, "情報収集")  # :12
    out.print("[0]噂話の聞き込み　　　")  # :15–23
    out.print("[1]事件の捜査　　　　　")
    if c.cflag[122] > 0:
        out.print("[2]情報を買う　　　　　")
    if lost > 0:
        out.print("[3]仲間の捜索　　　　　")
    out.printl()
    out.printl()
    out.drawline()
    if c.cflag[112] > 0:  # :25–60
        result = res_schedule(c, 112)
        if result in (0, 1, 2):
            out.printl()
            out.print("スケジュール：" + ("噂話の聞き込み", "事件の捜査", "情報を買う")[result])
            out.printl()
        elif result == 3:
            out.printl()
            out.print("スケジュール：仲間の捜索")
            if lost == 0:
                out.print("（実行不能）")
                out.printl("代わりに事件の捜査を行います")  # 原作は RESULT = 0（噂話の聞き込み）にする
                result = 0
    else:
        result = yield  # :62–63 $INPUT_LOOP
    while True:  # :66–78
        out.printl()
        if result in (0, 1) or (result == 2 and c.cflag[122] > 0) or (result == 3 and lost > 0):
            action = result
            break
        out.printl("正しい値を入力してください")
        result = yield  # GOTO INPUT_LOOP（ELSE 内の INPUT）
    c.cflag[101] = result  # :80
    yield from message_gather_information(ctx, action)  # :82
    ablup(ctx, 1)  # :83
    if c.cflag[1] > 0 and st.flag[73] == 0:  # :85–86
        transform(ctx, 0)


def message_gather_information(ctx: Ctx, arg: int) -> InputGen:
    """`@MESSAGE_GATHER_INFORMATION, ARG`:91–1074。"""
    st, out = ctx.state, ctx.out
    out.drawline()  # :96
    if arg == 0:
        yield from _rumor(ctx)
    elif arg == 1:
        yield from _investigate(ctx)
    elif arg == 2:
        yield from _buy(ctx)
    elif arg == 3:
        yield from _search(ctx)
    if arg in (1,3) and st.flag[73] > 0:
        st.result[0] = 0  # @MESSAGE_GATHER_INFORMATION:416/1046 RETURN，略過尾端 PRINTW。
        return
    out.printw()  # :1074


def _set_locals(st: GameState, value: str) -> str:
    st.temp.locals[_KEY_LOCALS] = value  # type: ignore[assignment]
    return value


def _t(ctx: Ctx, name: str) -> int:
    return talent(ctx.data, ctx.state.target_chara, name)


def _abl(ctx: Ctx, name: str) -> int:
    return ctx.state.target_chara.abl[ctx.data.index_of("ABL", name)]


def _exp_idx(ctx: Ctx, name: str) -> int:
    return ctx.data.index_of("EXP", name)


def _rumor(ctx: Ctx) -> InputGen:
    """CASE 0 噂話の聞き込み（:99–232）。"""
    from .akuoti import dot_after
    from .battle.encount import research_progress

    st, out = ctx.state, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    name = print_transcallname(st, st.target)
    out.printl("噂話の聞き込み")
    out.printl()
    miryo = _exp_idx(ctx, "魅了経験")
    hantei = rand(85) + isqrt(c.exp[miryo]) * 2  # :103
    if _t(ctx, "内向的") > 0:
        hantei -= 15
    if _t(ctx, "社交的") > 0:
        hantei += 15
    if _t(ctx, "ラッキーチャーム") > 0:
        hantei += 20
    if c.cflag[120] > 0 and rand(2) == 0 and c.cflag[1] == 0:  # :115–140
        out.printl(f"{name}は噂好きの友人に目ぼしい話がないか聞いてみた。")
        hantei += rand(25) + rand(25) + 25
    elif rand(4) != 0 and _t(ctx, "学生") > 0 and st.time == 0 and c.cflag[1] == 0:
        school = {1: "小学校", 2: "中学校", 3: "高校", 4: "大学"}.get(_t(ctx, "学生"))
        if school is not None:
            _set_locals(st, school)
        locals_ = st.temp.locals.get(_KEY_LOCALS, "")  # 学生 5 以上なら前回の LOCALS のまま（静的）
        out.printl(f"{name}は自分が通う{locals_}で妙な噂話が無いか聞いて回った。")
    elif rand(2) == 0 and c.cflag[1] == 0:
        out.printl(f"{name}は日常生活の中で出来る限り情報を集めた。")
    else:
        out.printl(f"{name}は周囲の人々からさりげなく情報を集めた。")
    # :142 平和だと噂が減る
    # DEVIATION: 防衛力（FLAG:852）が負のとき SQRT を 0 として計算（原作は SQRT の引数が負で CodeEE：
    # reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@SqrtMethod:1074–1080）。使用者裁決 2026-10-02（D4）。
    hantei = hantei - div(isqrt(max(st.flag[852], 0)), 10)
    if hantei < 10:  # :145–161
        out.printl("しかしあまり情報は集まらなかった・・・")
        gather = 2 + rand(3)
    elif hantei < 50:
        out.printl(_pd(ctx, ("思ったより情報が集まったのは良いが、曖昧な話が多すぎる・・・",
                             "他愛ない噂話ばかりだったが、その背後に触手が関わっている可能性は高い・・・",
                             "一見すると無関係な話題の中に、ひとつ気になる情報が混じっていた・・・")))
        gather = 4 + rand(3)
    elif hantei < 75:
        out.printl("その結果、敵の居場所のヒントになりそうな話を聞くことができた！")
        gather = 8 + rand(3)
    else:
        out.printl("その結果、かなり信憑性の高い目撃情報を手に入れることができた！")
        gather = 12 + rand(3)
    _wait_or_line(ctx)
    out.printl(f"{name}による調査の結果、探索度が{gather}上昇しました。")
    research_progress(ctx, gather)  # :168
    local = calc_charm_feat_other(ctx, st.target)  # :170–174
    if local > 0:
        c.exp[miryo] += local
        out.printl(f"魅了経験が{local}上がった")
    if c.cflag[120] == 0 and hantei >= 50 and rand(4) == 0 and c.cflag[1] == 0:  # :176–180
        out.printl()
        dot_after(ctx, 2)
        out.printl(f"なんと、{name}は『コネ：噂好きの友人』を獲得した！")
        c.cflag[120] = 1
    elif c.cflag[122] == 0 and rand(12) == 0:  # :182–231
        yield from _informant(ctx, name, plain_else=False)


def _informant(ctx: Ctx, name: str, plain_else: bool) -> InputGen:
    """情報屋とのコネ獲得（:183–231／:433–484。後者だけ「特徴なし」の ELSE がある）。"""
    from .akuoti import dot_after

    st, out = ctx.state, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    hantei = 0
    out.printl()
    dot_after(ctx, 2)
    out.printl(f"事件を調べていた{name}の前に報酬次第で情報提供をしてもいいと言う者が現れた。")
    hantei |= 2 if c.cflag[1] > 0 else 1  # SETBIT HANTEI, 1／0
    if rand(7) == 0:
        out.printl("小太りでいかにも下品な雰囲気が漂う男だが・・・")
        hantei |= 4
    elif rand(6) == 0:
        out.printl("丁寧で上品な振る舞いの男だが、目つきに何か鋭いものを感じる・・・")
        hantei |= 8
    elif rand(5) == 0:
        out.printl("本人は探偵を名乗っているが、微妙に胡散臭い・・・")
        hantei |= 16
    elif rand(4) == 0:
        out.printl("危険な気配を感じる。おそらくカタギの人間ではないだろう・・・")
        hantei |= 4 | 8
    elif rand(3) == 0:
        out.printl("どうにも軽口の多いお調子者といった感じの男だが・・・")
        hantei |= 4 | 16
    elif rand(2) == 0:
        out.printl("落ち付いた雰囲気の老紳士といった風情だが・・・")
        hantei |= 8 | 16
    elif plain_else:
        out.printl("特に特徴のない普通の男に見えるが・・・")
    out.printl("[0]連絡先を聞く")
    out.printl("[1]無視する")
    while True:
        r = yield
        if r == 0:
            out.printl(f"{name}は『コネ：情報屋』を獲得した！")
            c.cflag[122] = hantei
            return
        if r == 1:
            out.printl(f"{name}は協力の申し出を断った・・・")
            return


def _investigate(ctx: Ctx) -> InputGen:
    """CASE 1 事件の捜査（:234–485）。"""
    from .akuoti import dot_after
    from .battle.encount import research_progress

    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    name = print_transcallname(st, st.target)
    chisei = data.index_of("BASE", "知性")
    out.printl("事件の捜査")
    out.printl()
    hantei = isqrt(max(c.base[chisei] - 50, 0)) * 4 + rand(isqrt(max(c.base[chisei], 0)) + 5)  # :238
    if _t(ctx, "内向的") > 0:
        hantei -= 5
    if _t(ctx, "社交的") > 0:
        hantei += 5
    if _t(ctx, "ラッキーチャーム") > 0:
        hantei += 10
    out.print(f"{name}は")  # :249–253
    if c.cflag[121] > 0:
        out.print("コネを駆使して")
        hantei = hantei + c.cflag[121] * 20
    if rand(3) == 0:  # :254–271
        local = rand(3) + 1
        if rand(4) == 0:
            local += rand(3) + 1
        if rand(4) == 0:
            local += rand(3) + 1
        who = _set_locals(st, "少女" if rand(2) == 0 else "女性")
        if local >= 3:
            out.print("一晩に")
        out.print(f"{local}人")
        if local >= 5:
            out.print("も")
        out.print(f"の{who}が性的被害に遭ったという")
        kind = _set_locals(st, "")
    elif rand(2) == 0:  # :272–289
        local = rand(3) + 1
        if local >= 2 and rand(3) == 0:
            who = "若者たち"
        elif local >= 2 and rand(2) == 0:
            who = "男女"
        elif rand(2) == 0:
            who = "女性"
        else:
            who = "男性"
        _set_locals(st, who)
        out.print(f"{local}人の" if local >= 2 else "とある")
        out.print(f"{who}が行方不明になったという")
        kind = _set_locals(st, "謎の失踪")
    else:  # :290–292
        out.print(f"{rand(4) + 1}人の死者を出したという")
        kind = _set_locals(st, "猟奇殺人")
    out.printl()
    if rand(4) == 0:  # :295–303
        out.printl(f"つい最近起きた{kind}事件について調べてみることにした。")
    elif rand(3) == 0:
        out.printl("迷宮入り事件についてもう一度調べ直してみることにした。")
    elif rand(2) == 0:
        out.printl(f"いま各種メディアを騒がせている{kind}事件について調べてみることにした。")
    else:
        out.printl(f"世間には公表されていない{kind}事件について調べてみることにした。")
    for bound, text, base in (  # :305–320
        (40, "残念ながら、まったく手がかりを掴むことができなかった・・・", None),
        (50, "捜査の結果、僅かながら触手生物の手掛かりを発見することができた・・・", 5),
        (60, "捜査の結果、触手生物の痕跡を見つけることができた！", 10),
        (70, "捜査の結果、触手生物の足取りを掴むことに成功した！", 15),
        (None, "捜査の結果、重大な手掛かりを発見することに成功した！", 20),
    ):
        if bound is None or hantei < bound:
            out.printl(text)
            gather = 0 if base is None else base + rand(5)
            break
    l1 = 0  # :325–332 知性の上昇量
    if talent(data, c, "変身能力") == -1 and rand(4) == 0:
        l1 = 3
    elif rand(3) == 0:
        l1 = 2
    elif rand(3) < 2:
        l1 = 1
    if gather > 0 or l1 > 0:  # :333–347
        _wait_or_line(ctx)
        if gather > 0:
            out.printl(f"{name}による調査の結果、探索度が{gather}上昇しました。")
            research_progress(ctx, gather)
        if l1 > 0:
            c.base[chisei] += l1
            out.printl(f"知性の基礎値が{l1}上がった")
    # :350–417 クズ市民エンカウント（`&&` は短絡：GameData/Expression/OperatorMethod.cs:524–555）
    from .battle.core import is_hole

    if config_check_event(st, 5) == 1 and rand(10000) > st.flag[852] * 2 + 500 and is_hole(ctx):
        from .battle.citizen import encount_citizen

        supplement = _citizen_encount_text(ctx, name)
        encount_citizen(ctx,6002,supplement)
        if rand(100) < 30:  # ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:414–416。
            c.cflag[825] += 1
        return
    if c.cflag[121] == 0 and hantei >= 40 and rand(max(10 - div(hantei, 10), 2)) == 0:  # :421–425
        out.printl()
        dot_after(ctx, 2)
        out.printl(f"なんと、{name}は『コネ：警察関係者』を獲得した！")
        c.cflag[121] = 1
    elif c.cflag[121] == 1 and hantei >= 70 and rand(max(10 - div(hantei, 12), 2)) == 0:  # :426–430
        out.printl()
        dot_after(ctx, 2)
        out.printl(f"なんと、{name}は『コネ：警察上層部』を獲得した！")
        c.cflag[121] = 2
    elif c.cflag[122] == 0 and rand(6) == 0:  # :432–484
        yield from _informant(ctx, name, plain_else=True)


def _citizen_encount_text(ctx: Ctx, name: str) -> str:
    """:351–411（ENCOUNT_CITIZEN の直前まで）。"""
    st, out = ctx.state, ctx.out
    c = st.target_chara
    out.printl()
    out.printl("・")
    out.printl("・・")
    out.printl("・・・")
    out.print(f"{name}が")
    out.print(_pd(ctx, ("人気の無い廃ビル", "薄暗い路地裏", "封鎖された地下道", "廃棄された下水道", "見通しの悪い公園")))
    out.printl("へ調査に向かうと、")
    out.printl(f"どこからか小汚い風体の男たちが現れ{name}を取り囲んできた。")
    out.printl(f"男たちは「獲物」を見つけたと考えているらしく、にやついた顔付きで無遠慮に{name}の肢体を眺め回す。")
    out.printl(f"抗議しようと{name}が口を開いた瞬間、")
    local = st.rng.rand(3)  # :369
    if st.flag[999] == 1:  # :370–375
        raise NotImplementedError("デバッグモードの戦闘シチュエーション入力は未移植")
    if local == 0:
        out.printl("男たちは素早く取り出したスプレーを噴き付けてきた。")
        out.printl(f"咄嗟に反応できず吸い込んでしまった{name}……")
        out.printl("その喉からは、発すべき抗議の言葉ではなく鼻に掛かった艶めかしい喘ぎ声が漏れ出してしまう。")
        out.print("噴き付けられたのは触手由来の媚薬だったらしく、")
    elif local == 1:
        out.printl("男の一人が突然スタンロッドを振り上げ胸元目掛けて突いてきた。")
        out.printl(f"予想外の行為に反応が一瞬遅れてしまった{name}……")
        out.printl("その喉から出たのは抗議の言葉ではなく、艶めかしくも悲痛な叫び声だった。")
        out.printl()
        out.set_bold(True)
        out.printl(f"{min(div(c.base[0], 3) + 200, c.base[0])}のダメージを受けた！")  # :389（BASE は減らさない：原作どおり）
        out.set_bold(False)
        out.printl()
        out.print("全身を高圧電流が駆け巡り、")
    else:
        out.printl(f"背後の男が突然{name}の腕を掴んできた！")
        out.printl(f"意識が逸れた次の瞬間、今度は前方の男が{name}の鳩尾に膝蹴りを入れる……")
        out.printl("喉から出たのは発されるはずだった抗議の言葉ではなく、嘔吐同然の呼気と苦悶の叫びだった。")
        out.printl()
        out.set_bold(True)
        dmg = min(div(c.base[0], 4) + 200, c.base[0])
        out.printl(f"{dmg}のダメージを受けた！")
        out.set_bold(False)
        out.printl()
        c.base[0] -= dmg  # :405
        out.print("たった一撃で失神寸前に陥らされる手慣れた「狩り」に、")
    out.printl(f"{name}の全身からたちまち力が抜けてゆく……")
    out.printw(f"……どうやら{name}は危険な場所に足を踏み入れ過ぎていたようだ。")
    # ACTION_GATHER_INFORMATION.ERB:368 先清空 LOCALS；CASE2 保留空字串。
    return _set_locals(st,{0:"強制発情",1:"強制麻痺"}.get(local,""))


def _buy(ctx: Ctx) -> InputGen:
    """CASE 2 情報を買う（:487–942）。"""
    from .akuoti import dot_after
    from .battle.core import is_girly
    from .battle.encount import research_progress

    st, out = ctx.state, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    gb = lambda k: int(c.cflag.get_bit(122, k))  # noqa: E731（CFLAG:122 は途中で変わるので都度読む）
    name = print_transcallname(st, st.target)
    out.printl("情報を買う")
    out.printl()
    hantei = 0
    if gb(2) and gb(3):  # :492–506
        man = "無法者"
    elif gb(2) and gb(4):
        man = "お調子者な男"
    elif gb(3) and gb(4):
        man = "老紳士"
    elif gb(2):
        man = "下品な男"
    elif gb(3):
        man = "上品な男"
    elif gb(4):
        man = "探偵風の男"
    else:
        man = "特徴のない男"
    _set_locals(st, man)
    known = 1 if (c.cflag[1] > 0 and gb(1)) or gb(0) else 0  # :507–513
    out.print(f"{name}は情報屋({man})と連絡を取った")
    if known == 0:  # :516–528
        out.printl(f"。【所持金：{st.money}】")
        out.print("変身")
        out.print("した" if c.cflag[1] > 0 else "していない")
        out.printl("状態では面識が無かったはずだが、おそらく商売できれば関係無いのだろう。")
        out.printl("相手は深くは詮索せずに商談を開始した・・・")
    else:
        out.printl(f"・・・【所持金：{st.money}】")
    _wait_or_line(ctx)
    out.clearline(1)  # :534
    local = rand(25) * 25 + 500  # :536–561 値段
    local1 = rand(50) * 50 + 5000
    if gb(2) and gb(4) == 0 and is_girly(ctx):
        local = div(local * 150, 100)
        local1 = div(local1 * 150, 100)
    if gb(3):
        local = div(local * 150, 100)
        local1 = div(local1 * 150, 100)
    if gb(4) > 0 or gb(5) == 0:
        local = div(local * 110, 100)
        local1 = div(local1 * 110, 100)
    if _t(ctx, "内向的") > 0 and gb(3) == 0:
        local2 = 110
    elif _t(ctx, "社交的") > 0 and gb(3) == 0:
        local2 = 90
    else:
        local2 = 100
    price = lambda: div(local * local2, 100)  # noqa: E731
    price1 = lambda: div(local1 * local2, 100)  # noqa: E731
    gray = (105, 105, 105)
    if st.money < price():  # :562–573
        out.set_color(gray)
    out.printl(f" [0]情報を買う({price()})")
    out.reset_color()
    if (gb(4) == 0 and gb(5) == 0) or st.money < price1():
        out.set_color(gray)
    out.printl(f" [1]とっておきの情報を買う({price1()})")
    out.reset_color()
    body_ok = lambda: (_t(ctx, "淫乱") > 0 or gb(6)) and (gb(2) or gb(4) == 0) and is_girly(ctx)  # noqa: E731
    if body_ok():
        out.printl(" [2]カラダで情報を買う")
    out.printl("[99]情報を買わずに立ち去る")
    out.printl("[-1]縁を切る")
    while True:  # $INPUT_2
        r = yield
        if r == 0 and st.money >= price():  # :576–584
            st.money -= price()
            if local >= 1000:
                hantei = 1
            if gb(2) and gb(4) == 0 and is_girly(ctx):
                local = div(local, 2)
            if gb(4) == 0 or gb(5) > 0:
                local = div(local * 100, 120)
            gather = div(isqrt(local), 3) + 5
        elif r == 1 and st.money >= price1() and (gb(4) or gb(5)):  # :585–591
            st.money -= price1()
            if gb(2) and gb(4) == 0 and is_girly(ctx):
                local1 = div(local1, 2)
            if gb(4) == 0 or gb(5) > 0:
                local1 = div(local1 * 100, 120)
            gather = div(isqrt(local1), 4)
        elif r == 2 and body_ok():  # :592–904
            gather, hantei = yield from _buy_body(ctx, name, man, gb, hantei)
        elif r == 99:
            out.printl(f"{name}は情報を買わずに立ち去った・・・")
            gather = 0
        elif r == -1:
            out.printl(f"{name}は情報屋({man})との縁を切って立ち去った・・・")
            gather = 0
            c.cflag[122] = 0
        else:
            continue
        break
    if gather > 0:  # :915–920
        out.printl(f"情報提供の結果、探索度が{gather}上昇しました。")
        research_progress(ctx, gather)
    if hantei > 0 and gb(4) == 0 and gb(5) == 0 and rand(4) != 0:  # :922–928 上客
        out.printl()
        dot_after(ctx, 2)
        out.printl(f"男は{name}を上客だと判断した様子だ。")
        out.printl("これからは出し惜しみせずに協力してくれることだろう・・・")
        c.cflag.set_bit(122, 5)
    if gather == 0 and gb(2) and gb(6) == 0 and is_girly(ctx) and rand(4) != 0:  # :930–942 肉体関係
        out.printl()
        dot_after(ctx, 2)
        # :933 は "お調子者の男" と比べているが LOCALS は "お調子者な男"（:495）なので常に ELSE（原作どおり）
        if man == "お調子者の男":
            out.printl(f"そのまま帰ろうとする{name}に男は冗談めかした態度で")
            out.printl("もし金が無いのなら別の方法で報酬を支払ってもらっても構わない、と言ってきた。")
            out.printl("本気かどうかよく分からないが・・・")
        else:
            out.printl(f"男は{name}のカラダを見てニヤニヤしている。")
            out.printl("もし金が無いのなら別の方法で報酬を支払ってもらっても構わない、とのことだが・・・")
        c.cflag.set_bit(122, 6)


def _cum_text(ctx: Ctx, name: str) -> None:
    """口・胸での奉仕の射精文（:621–634／:680–693 同文）。"""
    out = ctx.out
    if _t(ctx, "淫乱") > 0 and _t(ctx, "初心") < 1:
        out.printl("積極的な奉仕に男がたまらず射精すると、")
        out.printl(f"{name}は蟲惑的な表情で")
        if ctx.state.rng.rand(2) == 0:
            out.printl("口を大きく開けて舌に溜めた精子を見せつけ、")
            out.printl("わざとらしく音を立てながら咀嚼した後")
        else:
            out.printl("口の中の精子を両手の平にのせて見せ、それを再び舐め、すすり上げ")
        out.printl("精液を飲み下して見せた・・・")
    else:
        out.printl(f"男は{name}を見下ろし情報を小出しにしつつ、")
        out.printl("肝心なところは伏せたまま口内に射精してしまった・・・")


def _buy_body(ctx: Ctx, name: str, man: str, gb, hantei: int) -> Generator[None, int, tuple[int, int]]:
    """カラダで情報を買う（:593–904）。戻り値 = (GATHER, HANTEI)。"""
    from .battle.ninsin import after_pill, estrus_text, ninsin_hantei

    st, data, out = ctx.state, ctx.data, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    male = lambda: is_male(data, c)  # noqa: E731
    exp = lambda n: c.exp[_exp_idx(ctx, n)]  # noqa: E731
    out.printl("どのような「交渉」を持ち掛けますか？")
    out.printl(" [0]口で奉仕する")
    if _t(ctx, "巨乳") > 0:
        out.printl(" [1]胸で奉仕する")
    out.printl(" [2]素股")
    if _t(ctx, "男の娘") > 0:
        out.print(" [3]アナル本番")
    if is_female(data, c):
        out.print(" [3]本番")
    if _t(ctx, "処女") > 0:
        out.print("(処女)")
    out.printl()
    dirty = man == "下品な男"
    while True:  # $INPUT_2_2
        r = yield
        gather = 0  # :607
        if r in (0, 1):  # :608–709（入力の可否は巨乳を見ない：原作どおり）
            if r == 0:
                out.printl(f"{name}は上目づかいで膝立ちになり、男に口で奉仕を始めた・・・")
            else:
                out.printl(f"{name}は上目づかいで膝立ちになり、男に胸で奉仕を始めた・・・")
            _wait_or_line(ctx)
            out.print("ろくに洗ってもいない不潔な" if dirty else "ガチガチに勃起した")
            if r == 0:
                out.printl("ペニスを頬張り、舌で刺激を与えていく。")
            else:
                out.printl("ペニスに唾液をたっぷり垂らし、")
                big = _t(ctx, "巨乳")
                if big > 2:
                    out.print("ダイナミックな大きさの")
                elif big > 1:
                    out.print("たわわに実った")
                elif big > 0:
                    out.print("豊満な")
                out.printl("胸で刺激を与えていく。")
                out.printl(f"{name}の胸に埋もれるペニスを見て、男は優越感に浸ったような満足気な笑みを浮かべている。")
                out.printl(f"牝の本能か理性的な策略か、{name}は目の前に飛び出している亀頭に舌で刺激を与えた。")
            _cum_text(ctx, name)
            if rand(2) == 0 and _abl(ctx, "精液中毒") > 2 and _t(ctx, "初心") < 1:
                if r == 0 and male():  # :636–642（胸の方は ISMALE の分岐なし：:694–697）
                    out.printl(f"精液の匂いが{name}のお尻の奥を疼かせ、")
                else:
                    out.printl(f"精液の匂いが{name}の{estrus_text(ctx, st.target)}子宮を疼かせ、")
                out.printl("このまま勢いで本番まで許してしまいそうなのを寸でのところでこらえた。")
            out.printw()
            gather += 6 + rand(5) + div(exp("魅了経験"), 100) + div(_abl(ctx, "技巧"), 2)
            if gb(5):
                gather += 2
            if _t(ctx, "内向的") > 0:
                gather -= 2
            if _t(ctx, "社交的") > 0:
                gather += 2
            c.exp[_exp_idx(ctx, "フェラ経験")] += 1
            c.exp[_exp_idx(ctx, "精液経験")] += 1
            return gather, hantei
        if r == 2:  # :711–833 素股
            _sumata(ctx, name, dirty)
            out.printw()
            out.printl("行為を終えると、男は約束の情報を渡してきた・・・")
            gather = _honban_reward(ctx, gather, gb)
            if st.temp.locals.get(_KEY_NAKADASHI, 0) > 0:  # :825–831（NAKADASHI は静的で 0 に戻らない：原作どおり）
                yield from after_pill(ctx, st.target, 35, -1)
                if is_female(data, c):
                    yield from ninsin_hantei(ctx, 2, 800, -1)
            out.printw()
            return gather, 1
        if r == 3:  # :834–901 本番
            out.printl(f"{name}は股を開き、男の挿入を受け入れた・・・")
            _wait_or_line(ctx)
            ti = data.index_of("TALENT", "処女")
            if c.talent[ti] > 0:
                c.talent[ti] *= -1
                c.cflag[206] = 12
                out.printl("処女喪失")
                out.printw()
                gather += 5
            if dirty:
                out.printl(f"男は{name}を種付けするような姿勢で")
                out.printl("でっぷりとした腹を揺らしながらピストンしている。")
            else:
                out.printl(f"{name}は自ら腰を振って男に奉仕している。")
            hole = "腸内" if male() else "膣内"
            if _t(ctx, "淫乱") > 0 and _t(ctx, "初心") < 1:
                out.printl(f"やがて男が限界に近づくと{name}は無意識に相手の腰に脚を巻きつけ、")
                out.printl(f"口づけを交わしながら{hole}射精を受け入れた。")
            else:
                out.printl(f"やがて男が限界に達すると{name}を押さえつけ、")
                out.printl(f"まるでそうするのが当然のように{hole}に精液を注ぎ込んだ。")
            out.printw()
            out.printl("行為を終えると、男は約束の情報を渡してきた・・・")
            gather = _honban_reward(ctx, gather, gb)
            yield from after_pill(ctx, st.target, 35, -1)  # :896
            if is_female(data, c):
                yield from ninsin_hantei(ctx, 2, 800, -1)
            out.printw()
            return gather, 1
        # :902–903 GOTO INPUT_2_2


def _honban_reward(ctx: Ctx, gather: int, gb) -> int:
    """:805–824／:875–894（素股・本番共通）。"""
    st, data = ctx.state, ctx.data
    c = st.target_chara
    gather += 10 + st.rng.rand(5) + div(c.exp[_exp_idx(ctx, "魅了経験")], 50) + div(_abl(ctx, "技巧"), 2)
    if gb(5):
        gather += 5
    if _t(ctx, "内向的") > 0:
        gather -= 4
    if _t(ctx, "社交的") > 0:
        gather += 4
    c.juel[data.index_of("JUEL", "習得")] += 200
    if is_male(data, c):
        c.exp[_exp_idx(ctx, "Ａ経験")] += 2
        c.juel[data.index_of("JUEL", "快Ａ")] += 10 * _abl(ctx, "Ａ感覚")
    else:
        c.exp[_exp_idx(ctx, "Ｖ経験")] += 2
        c.juel[data.index_of("JUEL", "快Ｖ")] += 10 * _abl(ctx, "Ｖ感覚")
    c.exp[_exp_idx(ctx, "精液経験")] += 2
    return gather


def _sumata(ctx: Ctx, name: str, dirty: bool) -> None:
    """素股の本文（:712–802）。中出しになったら静的 NAKADASHI = 1。"""
    st, out = ctx.state, ctx.out
    rand = st.rng.rand

    def nakadashi() -> None:
        st.temp.locals[_KEY_NAKADASHI] = 1

    otoko = _t(ctx, "男の娘") > 0
    if otoko:
        out.printl(f"{name}は股を閉じ、")
        out.printl("自分のモノを押し退けられるように、股間の逆三角形の隙間でペニスを挟み込んだ・・・")
        out.printl(f"男は{name}が実は女の子ではないと知っていても、まるで気にしていない・・・")
    else:
        out.printl(f"{name}は股を閉じ、股間の逆三角形の隙間でペニスを挟み込んだ・・・")
    _wait_or_line(ctx)
    if dirty:
        out.printl(f"男は{name}を壁に押し付けするような姿勢で")
        out.printl("でっぷりとした腹を揺らしながらピストンしている。")
    else:
        out.printl(f"{name}は騎乗位で自ら腰を前後に滑らせ奉仕している。")
    hole, inside = ("アナル", "腸内") if otoko else ("膣内", "膣内")
    refuse = _abl(ctx, "Ａ感覚") < 2 if otoko else _t(ctx, "処女") > 0

    def refused() -> None:
        out.printl("それだけは許してください、と涙ながらに請い、")
        out.printl(f"{name}の股間から頭を覗かせている汁まみれの亀頭を両手の平で撫でまわし")
        out.printl("熱いザーメンの奔流を受け止めた。")

    if rand(3) == 0 and _t(ctx, "淫乱") > 0 and _t(ctx, "初心") < 1:
        out.printl(f"やがて男が限界に近づくと{name}は腰をくねらせ、{hole}にペニスを招き入れた。")
        out.printl(f"口づけを交わしながら相手の腰に脚を巻きつけ、{inside}射精を受け入れた。")
        nakadashi()
    elif rand(2) == 0:
        out.printl(f"やがて男が限界に近づくと{inside}に出して良いならとっておきの情報を教えるぞと言ってきた。")
        out.printl(f"{name}は一瞬だけ躊躇ったが、")
        if refuse:
            refused()
        else:
            out.printl(f"{inside}に出してと甘く媚びた声で繰り返した。")
            out.printl(f"男は腰の角度を変え{name}に生挿入すると、")
            out.printl(f"激しいピストンで一気に{inside}射精した。")
            nakadashi()
    else:
        out.printl(f"やがて男が限界に近づくとピストンが早くなり、事故か故意か{name}の{inside}に生挿入しそうになった。"
                   if not otoko else
                   f"やがて男が限界に近づくとピストンが早くなり、事故か故意か{name}のアナルに生挿入しそうになった。")
        if refuse:
            refused()
        else:
            out.printl("一瞬のハプニングに胸を撫でおろしたのも束の間、同じようなことが何度も繰り返され")
            out.printl(f"{name}が気が付いた時にはしっかりと奥まで挿入されていた。")
            out.printl("気付いても止められないのか、男はラストスパートに入り")
            out.printl(f"快楽に流された{name}も気付かないフリをしたまま{inside}射精を受け入れた。")
            nakadashi()


def _search(ctx: Ctx) -> InputGen:
    """CASE 3 仲間の捜索（:944–1071）。"""
    from .battle.core import add_battle_situation, is_hole
    from .battle.encount import research_progress

    st, out = ctx.state, ctx.out
    c = st.target_chara
    rand = st.rng.rand
    name = print_transcallname(st, st.target)
    out.printl("仲間の捜索")
    out.printl()
    out.printl("行方を捜したい相手を選んでください")
    hantei = yield from chara_list(ctx, 3, 1, 1)  # :948–949
    h = st.charas[hantei]
    out.printl(f"{name}は{h.callname}の行方について情報を集めた。")
    gather = rand(30) + 1  # :952–963
    if _t(ctx, "内向的") > 0:
        gather -= 5
    if _t(ctx, "社交的") > 0:
        gather += 5
    if _t(ctx, "ラッキーチャーム") > 0:
        gather += 10
    if gather < 0:
        gather = 1
    if h.cflag[0] == CharaState.IMPRISONED:  # :966–980
        gather = div(gather, 2)
        if gather < 5:
            out.printl("しかし、あまり情報は集まらなかった・・・")
        else:
            out.printl(f"その結果、{h.callname}を幽閉している触手の居場所のヒントを得ることができた！")
            gather += 5
        _wait_or_line(ctx)
        out.printl(f"{name}による調査の結果、探索度が{gather}上昇しました。")
        research_progress(ctx, gather)
    elif h.cflag[0] == CharaState.KIDNAPPED:  # :982–1050
        gather = div(gather, 2)
        if gather < 5:
            out.printl("しかし、あまり情報は集まらなかった・・・")
        else:
            out.print("その結果、")
            out.printl(_pd(ctx, (f"{h.callname}が行方不明になった夜の目撃情報を得ることができた！",
                                 f"{h.callname}らしき少女が連れ去られる瞬間を目撃した証言を得られた！")))
            gather += 5
        _wait_or_line(ctx)
        local = h.cflag[71] - gather  # :1004 残り必要ポイント
        if h.cflag[71] > 20 and 0 < local <= 20:
            h.cflag[71] -= gather
            out.printl()
            out.printl(f"{name}による調査の結果、{h.callname}が最後に目撃された場所が判明した！")
        elif h.cflag[71] > 10 and 0 < local <= 10:
            h.cflag[71] -= gather
            out.printl()
            out.printl(f"{name}による調査の結果、{h.callname}が何者かの手で監禁されている事実が判明した！")
        elif h.cflag[71] > 0 and local <= 0:
            h.cflag[71] -= gather
            out.printl()
            out.printl(f"{name}による調査の結果、{h.callname}が監禁されている場所が特定された！")
            if is_hole(ctx):  # :1022–1047
                out.printl()
                out.printl("・・・")
                out.print(f"{name}が")
                out.print(_pd(ctx, ("特定した廃ビルの近辺", "廃ビルに隣接する裏路地", "廃ビルへと続く地下道", "廃ビルの地下を通る下水道")))
                out.printl("へ調査に向かうと、")
                out.printl(f"どこからか小汚い風体の男たちが現れ{name}を取り囲んできた。")
                out.printl(f"男たちは「新たな獲物」が迷い込んだと考えたのか、にやついた顔付きで無遠慮に{name}の身体を眺め回す。")
                out.printl(f"{h.callname}の行方を問いただそうと{name}が口を開いた瞬間、男たちは素早く取り出したスプレーを噴き付けてきた。")
                out.printl(f"咄嗟に反応できず吸い込んでしまった{name}……")
                out.printl("その喉からは、発すべき抗議の言葉ではなく鼻に掛かった艶めかしい喘ぎ声が漏れ出してしまう。")
                out.printl(f"噴き付けられたのは触手由来の媚薬だったらしく、{name}の全身からたちまち力が抜けてゆく……")
                out.printw(f"……どうやら{h.callname}を助ける以前に、{name}自身が身を守らねばならないようだ。")
                add_battle_situation(st, "強制発情,")  # :1040
                h.cflag[71] = -1  # :1041
                from .battle.citizen import encount_citizen

                encount_citizen(ctx,6002)
                if st.rng.rand(100) < 30:  # ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:1044–1046。
                    c.cflag[825] += 1
                return
            # ISHOLE でなければ CFLAG:71 <= 0 のまま → 次の夜の KIDNAPPING:447 で救出（intimidation.kidnapping）
        else:
            # :1048–1049 探索度の表示だけで RESEARCH_PROGRESS も CFLAG:71 の減少も無い（原作どおり）
            out.printl(f"{name}による調査の結果、探索度が{gather}上昇しました。")
    else:  # :1053–1071 洗脳／悪堕ち
        if gather < 5:
            out.printl("しかし、あまり情報は集まらなかった・・・")
        elif gather < 15:
            out.printl(f"その結果、{h.callname}の行方を断片的に知ることができた・・・")
        else:
            out.printl(f"その結果、{h.callname}らしき人物の目撃情報をキャッチすることに成功した！")
            gather += 5
        _wait_or_line(ctx)
        out.printl(f"{name}による調査の結果、{h.callname}との遭遇率が{gather}上昇しました。")
        h.cflag[23] += gather
        if h.cflag[23] >= 90:
            h.cflag[23] = 90


# --- 補助関数 -------------------------------------------------------------------------


def chara_list(ctx: Ctx, arg: int, arg1: int, arg2: int = 0) -> Generator[None, int, int]:
    """`汎用関数/コモン関数.ERB@CHARA_LIST, ARG, ARG:1, ARG:2 = 0`:303–355。戻り値 = RESULT（選んだキャラ、999 = やめる）。

    ARG = 1：CFLAG:0 == 0 のみ選択可、2：全キャラ、3：一時離脱（CFLAG:0 が 1〜4）のみ表示。ARG:1 = 1 生存状態、2 修練Ｐ。
    ARG:2 = 1 でキャンセル不可。
    """
    st, data, out = ctx.state, ctx.data, ctx.out
    away = (1, 2, 3, 4)
    out.printl("誰を選びますか？")
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        ch = st.charas[i]
        if arg not in (2, 3) and ch.cflag[999] == 0:
            continue
        if arg == 3 and ch.cflag[0] not in away:
            continue
        if (arg == 0 and ch.cflag[0] != 9) or ch.cflag[0] == 0 or arg in (2, 3):
            out.print(f"[{i}] {format_percent(ch.name, 28, True)}")
            if arg1 == 1:
                for k, label in ((1, "（幽閉中）"), (2, "（洗脳）"), (3, "（悪堕ち）"), (4, "（誘拐監禁中）"), (9, "（取り込まれ）"),
                                 (10, "（出産に備えて入院中）"), (11, "（育児中）")):
                    if ch.cflag[0] == k:
                        out.print(label)
            if arg1 == 2:
                out.print(f"（修練Ｐ：{ch.juel[data.index_of('JUEL', '修練P')]}）")
            out.printl()
    if arg2 == 0:
        out.printl("[999]キャラ選択をやめる")
    while True:  # $INPUT_LOOP_CHARA_LIST（|| は短絡：範囲外なら CFLAG:RESULT は評価しない）
        r = yield
        if r == 999 and arg2 == 0:
            return 999
        bad = r < 1 or r >= st.charanum
        if not bad:
            ch = st.charas[r]
            bad = ((arg == 0 and ch.cflag[0] == 9) or (arg == 1 and ch.cflag[0] != 0)
                   or (arg not in (2, 3) and ch.cflag[999] == 0) or (arg == 3 and ch.cflag[0] not in away))
        if bad:
            out.printl("正しい値を入力してください")
            continue
        return r


def calc_charm_feat_other(ctx: Ctx, who: int) -> int:
    """`特別活動/CALC_CHARM_FEAT.ERB@CALC_CHARM_FEAT_OTHER(対象)`:22–59（RANDOM(n) = RAND:n：`汎用関数/RANDOM.ERB`:11–25 の非デバッグ時）。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    rand = st.rng.rand
    t = lambda n: talent(data, c, n)  # noqa: E731
    e = c.exp[data.index_of("EXP", "魅了経験")]
    local = 0
    if rand(2) == 0 and e >= 30 and e != 99:  # :26–31
        local += 1
        if t("平凡") > 0 and rand(4) == 0:
            local -= 1
        if t("人外の美貌") > 0 and rand(4) == 0:
            local += 1
    elif rand(3) == 0 and e < 28:  # :32–37
        local += 2
        if talent(data, st.target_chara, "平凡") > 0 and rand(4) != 0:  # :34 は TALENT:平凡（TARGET）：原作どおり
            local -= 1
        if t("人外の美貌") > 0 and rand(4) != 0:
            local += 1
    elif e < 29:  # :38–43
        local += 1
        if t("平凡") > 0 and rand(4) == 0:
            local -= 1
        if t("人外の美貌") > 0 and rand(4) != 0:
            local += 1
    if e < 30 and e + local >= 30:  # :46–58
        local = 29 - e
    elif 30 <= e <= 99:
        if e + local < 30:
            local = 30 - e
        elif e + local >= 100:
            local = 99 - e
    elif e >= 100 and e + local < 100:
        local = 100 - e
    return local


_TF_CONFIG = {"特別活動": 51, "情報収集": 54, "気晴らし": 57}  # :11–29 GLOBAL の先頭番号（通常／女体化／男性化）
_TF_NAMES = {
    "特別活動": ("変身した状態で特別活動に行きますか？", "変身せずにそのまま特別活動に行きます。"),
    "情報収集": ("変身した状態で情報収集を行いますか？", "変身せずにそのまま情報収集を行います。"),
    "気晴らし": ("変身した状態で気晴らしに行きますか？", "変身せずにそのまま気晴らしに行きます。"),
}


def _sex_mark(ctx: Ctx, who: int) -> str:
    """:85–93 等：(男の娘)／(♂)／(ふたなり)／(♀)。"""
    c = ctx.state.charas[who]
    if talent(ctx.data, c, "男の娘") > 0:
        return "(男の娘)"
    if is_male(ctx.data, c):
        return "(♂)"
    if talent(ctx.data, c, "ふたなり"):
        return "(ふたなり)"
    return "(♀)"


def action_transformation_select(ctx: Ctx, arg: int, args: str) -> InputGen:
    """`ACTIONsub_TRANSFORMATION_SELECT.ERB@ACTION_TRANSFORMATION_SELECT, ARG, ARGS`:3–136。

    GLOBAL:51〜59（SHOP [700] → 変身設定 `config.config_t_gen` で設定、0 毎回選択・1 常に変身・2 常に変身しない）。
    [9]／[10] はメモリ上の GLOBAL だけ書き換える（SAVEGLOBAL はしない：原作どおり）。
    """
    from .battle.func import transform
    from .battle.ninsin import check_pregnant

    st, data, out = ctx.state, ctx.data, ctx.out
    g = ctx.globals.mem.global_
    c = st.charas[arg]
    base = _TF_CONFIG.get(args)
    name0, name1 = _TF_NAMES.get(args, ("", ""))
    tf_normal, tf_girl, tf_boy = (g[base], g[base + 1], g[base + 2]) if base else (0, 0, 0)
    t = lambda n: talent(data, c, n)  # noqa: E731
    otoko = lambda k: charatalent(data, c, k, "オトコ")  # noqa: E731
    if t("変身能力") > 0 and (is_female(data, c) and t("変身時ＴＳ") == 1 and check_pregnant(ctx, arg) > 0):  # :33–34
        out.printw(f"{c.callname}は妊娠中のため、変身で男性化できません。{name1}")
        return
    if not t("変身能力") > 0:
        return
    c.cflag[1] = 1  # :37–39 変身後名チェック（CFLAG:1 は 0 に戻す：元の値に関係なく）
    ptc = print_transcallname(st, arg)
    locals_ = ptc if ptc != "あなた" and ptc != c.callname else ""
    c.cflag[1] = 0
    if otoko(0) > 0 and otoko(1) == 0 and tf_girl != 0:  # :42–48
        result = tf_girl - 1
    elif otoko(0) == 0 and otoko(1) > 0 and tf_boy != 0:
        result = tf_boy - 1
    elif tf_normal != 0:
        result = tf_normal - 1
    else:  # :49–65
        if otoko(0) > 0 and otoko(1) == 0:
            st.temp.locals[_KEY_TF_LOCAL] = 2
            out.print(f"{c.callname}は{locals_ + 'への' if locals_ else ''}変身で女体化できます。{name0}")
        elif otoko(0) == 0 and otoko(1) > 0:
            st.temp.locals[_KEY_TF_LOCAL] = 3
            out.print(f"{c.callname}は{locals_ + 'への' if locals_ else ''}変身で男性化できます。{name0}")
        else:
            st.temp.locals[_KEY_TF_LOCAL] = 1
            out.print(f"{c.callname}は{locals_ + 'に' if locals_ else ''}変身できます。{name0}")
        out.printl()
        out.printl(f"　[0]{format_percent('はい', 27, True)}\t[1] いいえ")
        out.printl()
        out.printl("　[9]はい　 (次から確認しない)\t[10]いいえ(次から確認しない)")
        result = yield
    while True:
        if result in (9, 10):  # :68–77（LOCAL は静的：設定値経由で 9／10 にはならない）
            if base:
                g[base - 1 + st.temp.locals.get(_KEY_TF_LOCAL, 0)] = 1 if result == 9 else 2
            result = 0 if result == 9 else 1
        if result == 0:  # :79–119
            if otoko(0) == 0 and otoko(1) > 0 and t("妊娠") > 0:
                out.printl(f"しかし、{locals_ + 'への' if locals_ else c.callname + 'の'}変身は失敗した！")
                out.printl("いつものように変身しようとした筈なのに、なぜか何も起こらない…")
                out.print(f"仕方ないので、{c.callname}は{name1}")
                out.print(_sex_mark(ctx, arg))
            else:
                out.print(f"{c.callname}は{locals_ + 'に' if locals_ else ''}変身した！")
                if otoko(0) != otoko(1):
                    out.print(_sex_mark(ctx, arg) + "→")
                transform(ctx, 1)  # :108 CALL TRANSFORM, 1（ARG:1 省略 → TARGET）
                out.print(_sex_mark(ctx, arg))
            out.printl()
            break
        if result == 1:  # :120–131
            out.print(name1)
            out.print(_sex_mark(ctx, arg))
            out.printl()
            break
        result = yield  # :133 GOTO INPUT_LOOP_0_0
    out.drawline()  # :135
