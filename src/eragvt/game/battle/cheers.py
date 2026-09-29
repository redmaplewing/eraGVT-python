"""戦闘中の応援（観衆・クズ市民）：`ゲーム内_イベント発生/戦闘イベント.ERB`。

路徑相對 `source/earGVP/ERB/`。コンフィグ `CONFIG_CHECK_EVENT_F(3)`（基本セットで ON）のとき呼ばれる。
凌辱時の応援（PERFORM_CHEERS_TENTACLE_SEX_HANTEI）は S06。
"""

from __future__ import annotations

from ..action import Ctx, print_transcallname
from ..chara_common import is_female, is_male
from ..tentacle import enemy_type_check
from .cloth import INNER_PER, OUTER_PER, figure_split
from .core import (
    abl,
    add_randchoose,
    choicecount,
    clear_randchoose,
    clear_specific_choose,
    exp,
    get_battle_situation,
    is_manly,
    print_theme,
    randchoose_f,
    shinkyou_check,
    t,
    tc,
)
from ..era import div, isqrt


def _shinkyou_line(ctx: Ctx) -> None:
    st = ctx.state
    ctx.out.print(f"{print_transcallname(st, st.target)}は ")
    shinkyou_check(ctx, "PRINT", 0)
    ctx.out.printl("状態 になった")


def perform_cheers_first_hantei(ctx: Ctx) -> None:
    """`@PERFORM_CHEERS_FIRST_HANTEI`:8–85。"""
    st = ctx.state
    c = tc(ctx)
    if get_battle_situation(st, "市民なし") == 1:
        return
    if enemy_type_check(st, "CITIZEN") == 1:
        return
    local = 25 + max(div(5000 - st.flag[852], 100), 0) + (10 if st.time == 0 else 0)
    local += get_battle_situation(st, "市民確定") * 100
    for name in ("巻き込まれ体質", "人外の美貌", "嬲られ体質"):
        if t(ctx, c, name) > 0:
            local += 15
    if st.flag[999] == 1:
        raise NotImplementedError("デバッグ表示は未移植")
    if st.rng.rand(100) > local:
        return
    st.flag[70] = min(div(st.flag[852], 3000), 5)
    st.flag[70] += min(div(exp(ctx, c, "魅了経験"), 100), 5)
    if t(ctx, c, "巻き込まれ体質") > 0:
        st.flag[70] += 1
    if t(ctx, c, "人外の美貌") > 0:
        st.flag[70] += 1
    if st.time == 0:
        st.flag[70] += st.rng.rand(3)
    if get_battle_situation(st, "市民確定") == 1:
        st.flag[70] += 5
    if st.time == 1 and st.flag[70]:
        st.flag[70] = max(div(st.flag[70], 2), 1)
    st.flag[70] += min(980 + st.rng.rand(40), div(c.cflag[400], 10))
    if enemy_type_check(st, "LASTBOSS") > 0:
        return
    if st.flag[70] == 0:
        return
    local = isqrt(st.flag[852] + 625)
    local = local - (div(c.cflag[284], 4) + c.cflag[285]) * 5 - min(div(exp(ctx, c, "被姦経験"), 5), 20)
    if t(ctx, c, "人外の美貌") > 0:
        local -= 5
    if t(ctx, c, "嬲られ体質") > 0:
        local -= 10
    if st.rng.rand(100) < local:
        st.flag[72] = 0
    else:
        st.flag[72] = 1
        if t(ctx, c, "嬲られ体質") > 0:
            st.flag[70] += st.rng.rand(5)
    if enemy_type_check(st, "MOB") == 1 and st.flag[72] == 0:
        return
    perform_cheers_first(ctx)


_CHEER_HOPE = {
    10: "「{s}だ・・・{s}が来てくれた！！」",
    9: "「そんなやつ、ぶっとばしちゃえ！」",
    7: "「あなたならきっと勝てるわ！」",
    6: "「みんなを、みんなをたすけて！」",
    5: "「頼む、君だけが頼りだ！」",
    4: "「あの子の・・・あの子の仇を取ってくれ！！」",
    3: "「応援してるぞ！　{s}！！」",
    2: "「{s}、負けないで！！」",
    1: "「悪い奴をやっつけて！」",
}
_CHEER_HIDE = {
    10: "「離してくれ、俺たちなんかより{s}の安全が・・・！」",
    9: "「逃げてくれ、触手は{s}を狙ってるんだ！」",
    8: "「{s}、早く逃げて！！」",
    7: "「触手の狙いはあなただ、早く避難を！」",
    6: "「バケモノ、こっちに来やがれ！　{s}には手出しさせないぞ！！」",
    5: "「頼む逃げてくれ、君は俺たちの希望なんだ！」",
    4: "「おいバケモノ、あの子を狙うなんて下劣だぞ！！」",
    3: "「{s}、危ない！！」",
    2: "「{s}、いま助けに・・・うわっ！！」",
    1: "「{s}、悪い奴に負けないで！」",
}


def _crowd_word(st) -> str:
    n = st.flag[70] + st.flag[71]
    return "多くの人々が" if n >= 5 else "数名の一般人が" if n > 1 else "ひとりの一般市民が"


def _cheer_lines(ctx: Ctx, table: dict[int, str], word: str, manly_8: bool = False) -> None:
    st = ctx.state
    clear_randchoose(st)
    for i in range(10):
        add_randchoose(st, i + 1)
    for _ in range(min(st.flag[70] + st.flag[71], 5)):
        if choicecount(st) == 0:
            break
        r = randchoose_f(st)
        if r == 8 and manly_8:
            ctx.out.print("「頑張って、お兄さん！！」" if is_manly(ctx) else "「頑張って、お姉ちゃん！！」")
        elif r in table:
            ctx.out.print(table[r].format(s=word))
        clear_specific_choose(st, r)
        ctx.out.printl()


def perform_cheers_first(ctx: Ctx) -> None:
    """`@PERFORM_CHEERS_FIRST`:90–305。"""
    from ..action import _shortline  # SHORTLINE（S04 移植済み）

    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    name = print_transcallname(st, st.target)
    _shortline(out)
    if st.flag[72] > 0:
        l1 = st.flag[70]
        st.flag[71] = 1
        for _ in range(l1):
            p = 20 + min(div(exp(ctx, c, "魅了経験") - 40, 15), 20) + min(c.cflag[285], 10) - min(div(st.flag[852] - 5000, 100), 10)
            if st.rng.rand(100) < p:
                st.flag[70] -= 1
                st.flag[71] += 1
        st.flag[70] = 0
        out.printl()
        out.print("振り返ると")
        if st.flag[45] == 0 and st.flag[71] > 5:
            out.printl("騒ぎを聞きつけた野次馬が集まり、")
        if st.flag[71] > 100:
            out.print("無数の")
        elif st.flag[71] > 5:
            out.print("大勢の")
        elif st.flag[71]:
            out.print("数名の")
        out.printl("オタクっぽい服装をした男性がこちらにカメラを向けている！")
        if st.flag[71]:
            out.printl("中にはスマホで動画を撮り始める者までいる始末だ。")
        out.printw()
        out.printl("危険を注意しても避難を始める気配がないため、")
        out.print(f"仕方なく{name}は敵に向き合い背後を庇って戦う態勢を取った")
        if t(ctx, c, "感情乏しい"):
            out.printl("・・・")
        elif (t(ctx, c, "触手の虜") or abl(ctx, c, "欲望") >= 3) and t(ctx, c, "初心") < 1:
            out.printl("。")
            out.printl("もしかしたら自分の痴態を見られてしまうかもしれない興奮を感じながら")
            out.printl(f"「予定外の観客」の参加に{name}は心の中で笑みをこぼした・・・")
            out.printw()
            c.tcvarn[1] = 6
        elif get_battle_situation(st, "正体バレ不可"):
            out.printl("。")
            out.printl("決して見せてはいけない姿を撮影されてしまうかもしれない危機を感じながら")
            out.printl(f"命知らずの観客に{name}は心の中で悲鳴を上げた・・・")
            out.printw()
            c.tcvarn[1] = 6
        else:
            out.printl("。")
            out.printl("正義の味方なんだから一般市民を守るのは当然だろうと言わんばかりの態度に")
            out.printl("いったいどちらの味方なのかと怒りが込み上げてくる・・・")
            out.printw()
            c.tcvarn[1] = 2
        _shinkyou_line(ctx)
        out.printw()
    elif st.rng.rand(100) > 50 or get_battle_situation(st, "市民確定") == 1:
        out.printl()
        out.printl("不意に、後ろの方から声がした・・・！")
        out.print("見れば")
        out.print(_crowd_word(st))
        out.print("自分")
        if st.flag[70] + st.flag[71] > 1:
            out.print("たち")
        out.printl("の身の安全も顧みずに")
        if get_battle_situation(st, "正体バレ不可"):
            out.printl(f"{name}から触手の注意を逸らそうと声を張り上げている！")
            out.printw()
            _cheer_lines(ctx, _CHEER_HIDE, name + ("君" if is_male(ctx.data, c) else "ちゃん"))
        else:
            out.printl(f"{name}を応援しようと声を張り上げている！")
            out.printw()
            theme = print_theme(ctx)
            if theme != "":
                word = theme
            elif is_manly(ctx) and t(ctx, c, "変身時ＴＳ") == 0 and t(ctx, c, "変身時男の娘") <= 0:
                word = "魔装少年"
            else:
                word = "魔法少女"
            _cheer_lines(ctx, _CHEER_HOPE, word, manly_8=True)
        out.printw()
        out.printl(f"心の奥が暖かくなるのを感じながら、{name}は市民からの声援で奮起した！")
        out.printl(f"気合を入れなおした{name}は避難を呼びかけながら、")
        out.printl("敵の注意を引き付けるべく前に進み出た・・・")
        out.printl()
        c.tcvarn[1] = 6
        c.tcvarn[4] += 100
        c.base[0] = min(c.base[0] + div(c.maxbase[0] * 12, 100), c.maxbase[0])
        c.base[1] = min(c.base[1] + div(c.maxbase[1] * 24, 100), c.maxbase[1])
        out.printl("体力、気力が回復し、ＥＸゲージが増加した！")
        _shinkyou_line(ctx)
        out.printw()
    else:
        out.printl()
        out.printl("どうやら何人か逃げ遅れて戦闘に巻き込まれてしまった者が居るようだ。")
        out.printl("彼らが無事に避難できるように、時間を稼ぐ必要がある。")
        out.printl(f"{name}は敵の注意を引き付けるべく前に進み出た・・・")
        out.printl()
        c.tcvarn[1] = 4
        c.tcvarn[4] += 200
        out.printl("ＥＸゲージが大きく増加した！")
        _shinkyou_line(ctx)
        out.printw()


def perform_cheers_hate(ctx: Ctx) -> None:
    """`@PERFORM_CHEERS_HATE`:309–387（悪堕ち経験がある場合のみ）。"""
    st = ctx.state
    if st.flag[70] + st.flag[71] == 0:
        return
    if exp(ctx, tc(ctx), "陥落経験") > 0:
        raise NotImplementedError("悪堕ち経験者への罵声（PERFORM_CHEERS_HATE）は未移植")


def _suit_state(ctx: Ctx) -> int:
    """MISS／HIT_HANTEI 冒頭の触手服判定（:402–409）。

    `CFLAG:1 == 0 && CFLAG:40 == 199 || CFLAG:1 > 0 && CFLAG:41 == 199` は Emuera では
    `((A && B) || C) && D` と評価される。
    """
    c = tc(ctx)
    if ((c.cflag[1] == 0 and c.cflag[40] == 199) or c.cflag[1] > 0) and c.cflag[41] == 199:
        if c.tcvarn[41] != 0:
            return 1
        if figure_split(c.equip[99 if c.cflag[1] == 0 else 199], 1) == 0:
            return 2
        return 3
    return 0


def _filming(ctx: Ctx, miss: bool) -> None:
    """FLAG:72（クズ市民観衆）の撮影テキスト（:411–523／:607–715）。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    cl = st.temp.cloth
    name = print_transcallname(st, st.target)
    lewd = (t(ctx, c, "淫乱") or abl(ctx, c, "露出癖") >= 3) and t(ctx, c, "初心") < 1
    l1 = _suit_state(ctx)
    if is_manly(ctx):
        if miss:
            out.printl(f"なんとか攻撃を回避した{name}に向かって")
        else:
            out.printl(f"攻撃を受けた{name}を心配するどころか")
        out.printl("観戦者たちから野次が飛んでくる・・・")
    elif cl[OUTER_PER] > 50:
        if miss:
            out.printl(f"敵の攻撃を回避するために{name}が見せる大胆なアングルを狙って")
            out.printl("野次馬のシャッター音が連続で響く。")
            if lewd:
                out.printl("鬱陶しく思いながらも、ローアングルから激写されることに微かな興奮を覚えてしまう・・・")
            else:
                out.printl("ローアングルを攻めるカメラ小僧が胸や股ばかり撮って非常に鬱陶しい・・・")
        else:
            out.printl(f"攻撃を受けて衣装が破ける{name}を助けようともせず")
            out.printl("観衆は好き勝手な野次を飛ばしている。")
            if lewd:
                out.printl("やられシーンをカメラ小僧に激写されて微かに股間が疼いてしまう・・・")
            else:
                out.printl(f"敵の攻撃を捌くので精いっぱいの{name}は文句を言うこともできない・・・")
    elif cl[INNER_PER] > 50:
        if (c.stain[0] & 4) or (c.stain[1] & 4) or (c.stain[2] & 4):
            out.print("精液で汚され、")
        out.print("着衣の乱れた" if cl[OUTER_PER] else "下着姿のまま戦う")
        if miss:
            out.printl(f"{name}を撮影するべく野次馬のシャッター音が連続で響く。")
        else:
            out.printl(f"{name}を撮影するべく")
            out.printl("野次馬のシャッター音が連続で響く。")
        if lewd:
            if is_male(ctx.data, c):
                out.printl("もう股間の膨らみまではっきりと撮られてしまっている・・・" if miss else "もう膨らみまではっきりと撮られてしまっている・・・")
            else:
                out.printl("もう股間の食い込みまではっきりと撮られてしまっている・・・" if miss else "もう食い込みまではっきりと撮られてしまっている・・・")
        else:
            out.printl("写真を撮らないよう呼び掛けてもカメラ小僧が退く様子はない・・・")
    else:
        tr = c.cflag[1] > 0
        if l1 == 1:
            out.printl("暴走した触手服に犯され、激しい責めに")
            out.print("震える身体")
        elif l1 == 2:
            out.printl("蠢く触手服がぴたりと張り付き、" + ("乳首と股間をさらけ出し" if is_male(ctx.data, c) else "乳房と股間をさらけ出し"))
            out.print("淫らな姿")
        elif c.cflag[41] == 401 and tr:
            out.printl("薄布の前垂れだけが股間を隠し、肌も露わに")
            out.print("扇情的な姿")
        elif c.cflag[41] == 299 and tr:
            out.printl("薄いゴム状のスーツがぴたりと張り付き、カラダの凹凸をさらけ出して")
            out.print("裸も同然")
        else:
            if cl[INNER_PER]:
                out.print("ほとんど")
            out.print("全裸")
        out.printl(f"で戦う{name}を撮影するべく野次馬のシャッター音が連続で響く。")
        if l1 == 1:
            s = "蠢く触手服に陵辱される姿"
        elif l1 == 2 and is_female(ctx.data, c):
            s = "露出した乳房と股間"
        elif l1 == 2:
            s = "露出した乳首と股間"
        elif c.cflag[41] == 401 and tr:
            s = "前垂れから見え隠れする股間"
        elif c.cflag[41] == 299 and tr:
            s = "裸同然の姿"
        else:
            s = "裸体"
        subj = t(ctx, c, "主観視点") > 0
        inran, roshutsu, shoshin = t(ctx, c, "淫乱"), abl(ctx, c, "露出癖") >= 3, t(ctx, c, "初心") < 1
        # `(淫乱 || 露出癖 >= 3 && 主観視点 > 0) && 初心 < 1` は ((淫乱 || 露出癖>=3) && 主観) && 初心
        if ((inran or roshutsu) and subj) and shoshin:
            out.printl(f"{s}を激写されることに{name}は言いようのない興奮を覚えてしまう。")
        elif (inran or roshutsu) and shoshin:
            out.printl(f"{s}を激写されることに{name}は言いようのない興奮を覚えている。")
        elif subj:
            out.printl(f"{name}は見せるつもりもない相手に{s}を激写され、羞恥心と屈辱で顔が真っ赤になってしまう。")
        else:
            out.printl(f"見せるつもりのない相手に{s}を激写され、{name}は羞恥心で顔が真っ赤だ。")
        if l1 == 3:
            pass
        elif c.stain[3] & 4:
            out.printl("股間から中出し精液が溢れ出ている様子をはっきりとフィルムに収められてしまった・・・")
        elif c.stain[4] & 4:
            out.printl("尻穴から中出し精液が溢れ出ている様子をはっきりとフィルムに収められてしまった・・・")
        else:
            out.print("開脚した際に")
            out.print("覗く" if (c.cflag[41] == 401 and tr) else "薄いゴム越しの" if (c.cflag[41] == 299 and tr) else "露出した")
            out.printl("秘茎をはっきりとフィルムに収められてしまった・・・" if is_male(ctx.data, c) else "秘部をはっきりとフィルムに収められてしまった・・・")


def perform_cheers_tentacle_miss_hantei(ctx: Ctx) -> None:
    """`@PERFORM_CHEERS_TENTACLE_MISS_HANTEI`:393–586。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if st.flag[70] + st.flag[71] == 0:
        return
    out.printw()
    name = print_transcallname(st, st.target)
    if st.flag[72]:
        _filming(ctx, miss=True)
    elif st.rng.rand(100) < 35:
        local = 0
        if exp(ctx, c, "陥落経験") > 0:
            raise NotImplementedError("悪堕ち経験者への観衆の反応は未移植")
        if st.rng.rand(3) == 0:
            out.printl(f"{name}は襲われそうになっていた一般人を寸でのところで助け出した・・・")
            if st.rng.rand(100) < 20 and local > 0:  # LOCAL は VARSET で 0（原作では常に不成立）
                pass
        elif st.rng.rand(2) == 0:
            out.print("避難中の一般人")
            if st.flag[70] + st.flag[71] > 1:
                out.print("たち")
            out.printl(f"が{name}の攻防を固唾を飲んで見守っている・・・")
            if st.rng.rand(100) < 5 and local > 0:
                pass
        else:
            out.printl(f"観衆の「危ない！」という声に反応して咄嗟に{name}が身を躱すと、")
            out.printl("敵の攻撃が鼻先を掠めていった・・・")
            local = st.rng.rand(st.flag[70] + st.flag[71])
            if st.rng.rand(100) < 10 and local > 0:
                out.printl()
                st.flag[853] += 1
                out.printl("人気度が1上昇した！")


def perform_cheers_tentacle_hit_hantei(ctx: Ctx) -> None:
    """`@PERFORM_CHEERS_TENTACLE_HIT_HANTEI`:590–757。"""
    st = ctx.state
    c = tc(ctx)
    out = ctx.out
    if st.flag[70] + st.flag[71] == 0:
        return
    out.printw()
    name = print_transcallname(st, st.target)
    if st.flag[72]:
        _filming(ctx, miss=False)
    elif st.rng.rand(100) < 35:
        if exp(ctx, c, "陥落経験") > 0:
            raise NotImplementedError("悪堕ち経験者への観衆の反応は未移植")
        if st.rng.rand(3) == 0:
            out.printl(f"{name}は逃げ遅れた一般人を庇って避けきれなかったようだ・・・")
            local = st.rng.rand(st.flag[70] + st.flag[71])
            if st.rng.rand(100) < 20 and local > 0:
                out.printl()
                st.flag[853] += 1
                out.printl("人気度が1上昇した！")
        elif st.rng.rand(2) == 0:
            out.print("避難中の一般人")
            if st.flag[70] + st.flag[71] > 1:
                out.print("たち")
            out.printl(f"が{name}の攻防を固唾を飲んで見守っている・・・")
        else:
            out.printl(f"{name}が攻撃を避けきれずに食らう様を目の当たりにして")
            out.printl("観衆から悲鳴が上がった・・・")
