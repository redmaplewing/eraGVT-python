"""受精判定：`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_HANTEI`:11–165 と `@CHECK_HININ_F`:774–808、
`ヒロイン関連/ESTRUS_CYCLE.ERB@ESTRUS_TEXT_F`:30–46。

S13：受精成立後の `@NINSIN_SUBMIT`:752–767、`@NINSIN_FLAG`:195–257、`@NINSIN_TS_FIX`:262–271、
`@NINSIN_CHECK_AFTER`:169–190、`@NUM_CHILD_TENTACLE`:579–601、`@PREGNANT_RANDOM_SIZE`:826–840、
`@PREGNANCY_BOOB_EXPAND`／`@PREGNANCY_BELLY_EXPAND`:844–893 もここ。妊娠の進行・出産は `eragvt.game.pregnancy`、
子供は `eragvt.game.child`（狀態機：`docs/wiki/era/pregnancy.md`）。路徑相對 `source/earGVP/ERB/`。
S71：TS轉換依 `ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF` 等待外貌輸入，完成後續行。
"""

from __future__ import annotations
from collections.abc import Generator

from ...state import GameState
from ..action import Ctx, config_check_other, print_callname, print_transcallname
from ..chara_common import is_female, is_male
from ..era import div, isqrt
from ..tentacle import enemy_type_check
from .core import HAIRAN, HATUJOU, exp, t, tc, tentacle_access


def check_pregnant(ctx: Ctx, who: int) -> int:
    """`@CHECK_PREGNANT_F(ARG)`:813–820。"""
    c = ctx.state.charas[who]
    p = t(ctx, c, "妊娠")
    return 1 if p in (1, 3) or (p == 5 and c.cflag[222] >= 11) else 0


def estrus_text(ctx: Ctx, who: int) -> str:
    """`@ESTRUS_TEXT_F(ARG, footertext="")`（ESTRUS_CYCLE.ERB:30–46）。"""
    c = ctx.state.charas[who]
    if t(ctx, c, "未熟") > 0 or is_male(ctx.data, c) or check_pregnant(ctx, who) > 0:
        return ""
    ab = t(ctx, c, "排卵異常")
    d = c.cflag[217]
    if 13 - ab <= d <= 15:
        return "危険日"
    if ab >= 3 or (16 <= d <= (19 if ab == 2 else 18)):
        return "危険日"
    return ""


def check_hinin(ctx: Ctx, who: int, arg1: int) -> int:
    """`@CHECK_HININ_F(ARG, ARG:1)`:774–808。"""
    st = ctx.state
    c = st.charas[who]
    local = 0
    if st.flag[700] > 0:
        # :780 `CFLAG:ARG:41 == 299 && CFLAG:1 > 0`（後半の CFLAG:1 は TARGET のもの：原作どおり）
        if c.cflag[41] == 299 and st.target_chara.cflag[1] > 0:
            local = 100
        elif c.cflag[241] > 0 and enemy_type_check(st, "AKUOTI") > 0:
            local = 80
        elif c.cflag[241] > 0:
            local = 5
        if t(ctx, c, "避妊結界") > 0 and c.base[2] > 0:
            local = 100
    else:
        if c.cflag[241] > 0 and arg1 < 0:
            local = 80
        elif c.cflag[241] > 0:
            local = 5
        if t(ctx, c, "避妊結界") > 0 and c.base[2] > 0 and arg1 > 0:
            local = 100
    return 1 if st.rng.rand(100) < local else 0


def charaid(ctx: Ctx, arg: int) -> int:
    """`汎用関数/コモン関数.ERB@CHARAID_F, ARG`:1062–1070：CFLAG:240（固有番号）== ARG のキャラ番号、無ければ 0。"""
    st = ctx.state
    for i in range(st.charanum):
        if i == 0:  # MASTER
            continue
        if st.charas[i].cflag[240] == arg:
            return i
    return 0


def _set_t(ctx: Ctx, c, name: str, value: int) -> None:
    c.talent[ctx.data.index_of("TALENT", name)] = value


def _juel_add(ctx: Ctx, c, name: str, value: int) -> None:
    """`JUEL:名 += 値`（JUEL の名前は Palam.csv で引く：`data.csv_loader`）。"""
    c.juel[ctx.data.index_of("PALAM", name)] += value


# #DIM PREG_PER（関数内 #DIM は static：reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27、
# VariableData.cs@SetDefaultLocalValue:514–520 で ResetData／読込時のみ 0）。父親 ID が 0 や仲間キャラが見つからない
# 場合（:72–97 のどれにも代入されない）は前回の値が使われる。
_PREG_PER = ("NINSIN_HANTEI:PREG_PER", 0)


def ninsin_hantei(ctx: Ctx, arg0: int, arg1: int, arg2: int = 0) -> Generator[None, int, int]:
    """`@NINSIN_HANTEI, ARG:0（射精量）, ARG:1（係数）, ARG:2 = 0（父親）`:11–165。受精したら 1。"""
    # RETURN 0/1：reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023。
    st = ctx.state
    c = tc(ctx)
    if is_male(ctx.data, c):  # :16–21
        st.result[0] = 0
        return 0
    if t(ctx, c, "未熟") > 0:
        st.result[0] = 0
        return 0
    if t(ctx, c, "妊娠") > 0:
        st.result[0] = 0
        return 0
    if config_check_other(st, 2) > 0:  # :23–24 常時避妊モード
        st.result[0] = 0
        return 0
    if check_hinin(ctx, st.target, arg2) == 1:  # :26–36
        if st.flag[700] > 0:
            st.tflag[6] += arg0
        st.result[0] = 0
        return 0
    if st.flag[700] > 0:
        arg0 += st.tflag[6]
    st.tflag[6] = 0
    # :39–67 父親の ID
    if c.cflag[0] in (1, 2, 3, 9) and arg2 == 0:
        papa = c.cflag[21] + (c.cflag[20] == 1) * 100
    elif st.flag[700] > 0 and arg2 == 0:
        if enemy_type_check(st, "AKUOTI") > 0:  # :44–48 洗脳／悪堕ちキャラ
            e = st.charas[st.flag[111]]
            papa = e.cflag[240] * -1 - 100
            if (t(ctx, e, "ふたなり") == 2 or t(ctx, e, "変身時ふたなり") == 2) and st.rng.rand(4) != 0:
                papa = 200
        else:
            papa = st.flag[11]
            if enemy_type_check(st, "LASTBOSS") >= 1:
                papa += 100
            elif enemy_type_check(st, "MOB") == 1 or enemy_type_check(st, "CITIZEN") == 1:
                papa += 200
    else:  # :61–66（ARG:2 == 0 でもここに来る：PAPA_ID = 0）
        papa = arg2
        o = st.charas[charaid(ctx, -arg2 - 100)]
        if (t(ctx, o, "ふたなり") == 2 or t(ctx, o, "変身時ふたなり") == 2) and st.rng.rand(4) != 0:
            papa = 200
    c.cflag[221] += arg0  # :69
    birth = exp(ctx, c, "出産経験")
    pper = st.temp.locals.get(_PREG_PER, 0)
    if papa > 0:  # :72–75 触手
        c.cflag[232] += arg0
        pper = isqrt(div(arg1 * c.cflag[232] * (birth + 1), 2))
    elif papa <= -100:  # :77–91 仲間キャラ（寄生されていれば触手扱い）
        for i in range(st.charanum):
            if i == GameState.MASTER:
                continue
            o = st.charas[i]
            if o.cflag[240] == papa * -1 - 100 and t(ctx, o, "寄生") > 0:
                c.cflag[232] += arg0
                pper = isqrt(div(arg1 * c.cflag[232] * (birth + 1), 2))
            elif o.cflag[240] == papa * -1 - 100:
                c.cflag[233] += arg0
                pper = isqrt(div(arg1 * c.cflag[233] * (birth + 1), 2))
    elif papa <= -1:  # :93–96 一般人（いちゃラブセックスの `愛する人` = -3：DIM.ERH:256）
        c.cflag[233] += arg0
        pper = isqrt(div(arg1 * c.cflag[233] * (birth + 1), 2))
    # PAPA_ID == 0 は :72–97 のどれにも当たらず PREG_PER は前回値のまま
    if st.flag[700] == 1:  # :99–121
        pper *= 2
    if t(ctx, c, "苗床化"):
        pper *= 4
    if st.flag[909]:
        pper *= 2
    if t(ctx, c, "避妊結界") > 0 and papa > 0:
        pper *= 2
    if t(ctx, c, "獣性の証") > 0:
        pper = div(pper * 125, 100)
    if t(ctx, c, "祝福") > 0:
        pper = div(pper * 150, 100)
    if t(ctx, c, "不老長寿") > 0:
        pper = div(pper * 75, 100)
    if c.tcvarn[12] & HATUJOU:
        pper *= 2
    if estrus_text(ctx, st.target) != "":
        pper = div(pper * 3, 2)
    if c.tcvarn[12] & HAIRAN:
        pper = 1000
    st.temp.locals[_PREG_PER] = pper
    if st.flag[999] == 1:  # :125–138
        raise NotImplementedError("デバッグモードの妊娠確率入力は未移植")
    # :140 `RAND:1000 < … && TALENT:妊娠 == 0`（RAND を先に引く）
    if st.rng.rand(1000) < pper + 100 * (c.cflag[0] == 0) and t(ctx, c, "妊娠") == 0:
        ninsin_submit(ctx)  # :142
        c.cflag[221] = 0  # :144–146
        c.cflag[232] = 0
        c.cflag[233] = 0
        c.cflag[230] = papa  # :148
        yield from ninsin_flag(ctx)  # :149
        if st.flag[700] == 1:  # :150–162
            if str(tentacle_access(ctx, "GETNAME")) == "Ｈ触手" and (c.tcvarn[12] & HAIRAN):
                out = ctx.out
                name = print_transcallname(st, st.target)
                out.printl(f"Ｈ触手が広げた薄膜のモニターには{name}の胎内の様子が映し出されており、")
                out.printl("成熟した卵子の周りには無数の触手の精子が群がっている。")
                out.printl("そのうちの一匹が表皮を突き破って悲願を達成し、爆発的な細胞の増殖が始まった。")
                out.printl(f"{name}は目の前で異種間受精の瞬間を見せつけられてしまった・・・")
                out.printw()
                _set_t(ctx, c, "妊娠", 1)
                out.printw(f"{name}は[妊娠]した")
                yield from ninsin_ts_fix(ctx)
        st.result[0] = 1
        return 1
    st.result[0] = 0
    return 0


def ninsin_submit(ctx: Ctx) -> None:
    """`@NINSIN_SUBMIT`:752–767：妊娠時の屈服増加（TARGET の JUEL）。"""
    c = tc(ctx)
    birth = exp(ctx, c, "出産経験")
    if t(ctx, c, "触手の虜"):
        _juel_add(ctx, c, "恭順", 1000)
    elif birth >= 10:
        _juel_add(ctx, c, "屈服", 100)
    elif birth >= 5:
        _juel_add(ctx, c, "屈服", 400)
        _juel_add(ctx, c, "恐怖", 50)
    elif birth >= 1:
        _juel_add(ctx, c, "屈服", 1000)
        _juel_add(ctx, c, "恐怖", 300)
    else:
        _juel_add(ctx, c, "屈服", 2500)
        _juel_add(ctx, c, "恐怖", 1500)


def _tentacle_or_other(ctx: Ctx, cond_tentacle: bool) -> None:
    """:228–242／:172–186 共通：育児機能（CONFIG_CHECK_OTHER_F(0)）が ON なら触手／娘の抽選、OFF なら触手。"""
    c = tc(ctx)
    if cond_tentacle:
        _set_t(ctx, c, "妊娠", 1)
        c.cflag[227] = num_child_tentacle(ctx)
        c.cflag[228] = pregnant_random_size(ctx, ctx.state.target)
    else:
        _set_t(ctx, c, "妊娠", 3)
        c.cflag[228] = pregnant_random_size(ctx, ctx.state.target)


def ninsin_flag(ctx: Ctx) -> Generator[None, int, None]:
    """`@NINSIN_FLAG`:195–257：妊娠フラグ（素質 妊娠）を立てて地の文。

    妊娠 = 1 触手の幼体、2 触手（戦闘中：判明は戦闘後）、3 触手の子種による娘（育児機能 ON）、4 人間の子（無自覚）、
    5 人間の子（自覚済み）。
    """
    st = ctx.state
    c = tc(ctx)
    papa = c.cflag[230]
    if papa <= -100:  # :198–212 仲間が父親
        for i in range(st.charanum):
            if i == GameState.MASTER:
                continue
            o = st.charas[i]
            if o.cflag[240] == papa * -1 - 100:
                if t(ctx, o, "寄生") == 0 and t(ctx, c, "寄生") == 0:
                    _set_t(ctx, c, "妊娠", 4)
                    c.cflag[228] = pregnant_random_size(ctx, st.target)
                else:
                    _set_t(ctx, c, "妊娠", 2)
    elif papa <= -1:  # :214–221 普通の人間
        if t(ctx, c, "寄生") == 0:
            _set_t(ctx, c, "妊娠", 4)
            c.cflag[228] = pregnant_random_size(ctx, st.target)
        else:
            _set_t(ctx, c, "妊娠", 2)
    else:  # :223–225
        _set_t(ctx, c, "妊娠", 2)
    # :227–246 幽閉中（CFLAG:21 > 0）または戦闘外なら即時に妊娠
    if c.cflag[21] > 0 or (st.flag[700] == 0 and t(ctx, c, "妊娠") == 2):
        if config_check_other(st, 0) > 0:
            # :230 `((RAND:100 < …) || CFLAG:22 != 0) && CFLAG:0 == 1`（RAND を先に引く）
            r = st.rng.rand(100) < 50 + (t(ctx, c, "苗床化") > 0) * 25
            _tentacle_or_other(ctx, (r or c.cflag[22] != 0) and c.cflag[0] == 1)
        else:
            _tentacle_or_other(ctx, True)
        ctx.out.printl()
        _message_ninnsin(ctx)
        yield from ninsin_ts_fix(ctx)
    # :248–257 ＴＳ変身時の正常妊娠
    if is_female(ctx.data, c) and t(ctx, c, "変身時ＴＳ") > 0 and c.cflag[1] > 0 and t(ctx, c, "妊娠") == 4:
        out = ctx.out
        out.printw()
        out.printl(f"{print_callname(st, st.target, 1)}の様子がおかしい…")
        out.printl("なぜか分からないが、身体の奥底に何か違和感を感じる…")
        out.printl()
        out.printl(f"{print_callname(st, st.target, 1)}は[オトコ]に戻れなくなった")
        out.printw()
        from ..trans_sex import ts_mtof

        yield from ts_mtof(ctx, st.target)
    # 原作自然終端：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    ctx.state.result[0] = 0


def _message_ninnsin(ctx: Ctx) -> None:
    """`地の文/MESSAGE_NINSIN.ERB@MESSAGE_NINNSIN`:5–25（本文のみ・状態変化なし）。"""
    from .core import run_chinobun

    run_chinobun(ctx, "MESSAGE_NINNSIN")


def ninsin_ts_fix(ctx: Ctx) -> Generator[None, int, None]:
    """`@NINSIN_TS_FIX`:262–271：ＴＳ魔法少女が妊娠すると男に戻れない／変身できない。"""
    from .core import run_chinobun

    c = tc(ctx)
    if is_female(ctx.data, c) and t(ctx, c, "変身時ＴＳ") > 0 and c.cflag[1] > 0:
        run_chinobun(ctx, "MESSAGE_NINNSIN_TS_FIX")
        from ..trans_sex import ts_mtof

        yield from ts_mtof(ctx, ctx.state.target)
    elif is_female(ctx.data, c) and t(ctx, c, "変身時ＴＳ") > 0 and c.cflag[1] == 0:
        run_chinobun(ctx, "MESSAGE_NINNSIN_TS_FIX")
    # 原作自然終端：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    ctx.state.result[0] = 0


def ninsin_check_after(ctx: Ctx) -> Generator[None, int, None]:
    """`@NINSIN_CHECK_AFTER`:169–190：戦闘中に受精した（妊娠 = 2）なら戦闘後に判明。"""
    st = ctx.state
    c = tc(ctx)
    if t(ctx, c, "妊娠") == 2 and is_female(ctx.data, c):
        if config_check_other(st, 0) > 0:
            _tentacle_or_other(ctx, st.rng.rand(100) < 50 + (t(ctx, c, "苗床化") > 0) * 25)
        else:
            _tentacle_or_other(ctx, True)
        ctx.out.printl()
        _message_ninnsin(ctx)
        yield from ninsin_ts_fix(ctx)
    # 原作自然終端：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67。
    ctx.state.result[0] = 0


def num_child_tentacle(ctx: Ctx) -> int:
    """`@NUM_CHILD_TENTACLE(ARG)`:579–601：産む触手の数。

    本体は ARG を使わず `EXP:出産経験`・`TALENT:苗床化`・`CFLAG:0` をすべて **TARGET** から読む（原作どおり）。"""
    st = ctx.state
    c = tc(ctx)
    rand = st.rng.rand
    b = exp(ctx, c, "出産経験")
    if b < 1:
        n = 1 + rand(4)
    elif b < 10:
        n = 2 + rand(5)
    elif b < 30:
        n = 3 + rand(6)
    elif b < 50:
        n = 4 + rand(7)
    else:
        n = 5 + rand(8)
    if t(ctx, c, "苗床化"):
        n += 1 + rand(2)
    if c.cflag[0] == 9:
        n = max(div(n, 2), 1)
    return n


def pregnant_random_size(ctx: Ctx, who: int) -> int:
    """`@PREGNANT_RANDOM_SIZE(ARG)`:826–840：妊娠時の腹囲最大サイズ（mm）。"""
    c = ctx.state.charas[who]
    p = t(ctx, c, "妊娠")
    if p == 0:
        return 0
    if p == 1:
        local = 88 * max(c.cflag[227], 0)  # FOR LOCAL:1, 0, CFLAG:227 → 88 を CFLAG:227 回
    else:
        local = 266
    return div(local * (80 + ctx.state.rng.rand(41)), 100)


def pregnancy_boob_expand(ctx: Ctx, who: int) -> int:
    """`@PREGNANCY_BOOB_EXPAND(ARG)`:844–859：妊娠時のバストの増分（mm）。"""
    c = ctx.state.charas[who]
    p = t(ctx, c, "妊娠")
    if p in (1, 3):
        return div(20 * c.cflag[222], 10)
    if p == 5:
        return div(20 * (c.cflag[222] - 6), 40)
    return 0


def pregnancy_belly_expand(ctx: Ctx, who: int) -> int:
    """`@PREGNANCY_BELLY_EXPAND(ARG)`:863–893：妊娠時の腹囲の増分（mm）。"""
    c = ctx.state.charas[who]
    p = t(ctx, c, "妊娠")
    if p == 0:
        return 0
    local = 0
    d = c.cflag[222]
    if p == 1:
        local = div(c.cflag[228] * d, 10)
    elif p == 3:
        local = div(c.cflag[228] * (d + 5), 15)
    elif p in (4, 5):
        if d < 14:
            local = div(c.cflag[228] * 15, 100)
        elif d < 22:
            local = div(c.cflag[228] * 30, 100)
        elif d < 42:
            local = div(c.cflag[228] * 80, 100)
        else:
            local = c.cflag[228]
        local = div(local * max(d - 8, 0), 48)
    if t(ctx, c, "小さな体躯") > 0:
        local = div(local * 85, 100)
        if t(ctx, c, "妖精族") > 0:
            local = div(local * 70, 100)
    return local


def _dot_after(ctx: Ctx) -> None:
    """`汎用関数/PRINT_LINE.ERB@DOT_AFTER, 1`:34–43。"""
    from ..action import config_check_screen

    out = ctx.out
    if config_check_screen(ctx.state, 3) == 0:
        out.printw("・・")
        out.printw("・・・・")
    else:
        out.printl("・・")
        out.printl("・・・・")
    out.printw("・・・・・・")


def after_pill(ctx: Ctx, arg: int, arg1: int, arg2: int):
    """`@AFTER_PILL, ARG, ARG:1, ARG:2`:898–957（ジェネレータ：INPUT）。ARG:1 = 成功率、ARG:2 = CHECK_HININ_F へ渡す父親。

    既定コンフィグ（FLAG:805 = 2：オープニング処理.ERB の初期設定）では CONFIG_CHECK_OTHER_F(3) == 0 で即 RETURN。"""
    from ..action import print_callname

    st, out = ctx.state, ctx.out
    c = st.charas[arg]
    if config_check_other(st, 3) == 0:
        return 0
    if is_male(ctx.data, c):
        return 0
    if t(ctx, c, "未熟") > 0:
        return 0
    if t(ctx, c, "妊娠") in (1, 3, 5):
        return 0
    if c.cflag[241] > 0:
        return 0
    if config_check_other(st, 2) > 0:  # :911–912 常時避妊モード
        return 0
    out.printl()
    _dot_after(ctx)
    out.printl()
    out.printl(f"{print_callname(st, arg, 1)}は膣内射精されたことを自覚している…")
    out.print("時間が経ち過ぎて効果がないかもしれないが、" if arg1 < 25 else "このままでは妊娠してしまうかもしれないが、")
    out.printl("$500支払って緊急用アフターピルを飲んでおくべきだろうか？")
    out.printl("[0]アフターピルは飲まない")
    out.printl(f"[1]アフターピルを飲んで避妊する（所持金:${st.money}）")
    lcount = out.linecount  # :925
    while True:  # :926–957
        r = yield
        if r == 0:
            out.printl(f"{print_callname(st, arg)}はアフターピルを飲まないことにした…")
            return 0
        if r == 1:
            if st.money >= 500:
                st.money -= 500
                out.printl(f"{print_callname(st, arg)}はアフターピルを飲んだ…")
                out.printl("身体の底に疲労が蓄積した……（＋１５）")
                c.cflag[99] += 15
                if st.rng.rand(100) < arg1:  # :936–940（:938 は CHECK_HININ_F（RAND を引く）が && の左辺）
                    c.cflag[241] = 1
                    if check_hinin(ctx, arg, arg2) > 0 and c.cflag[222] == 0:
                        c.talent[ctx.data.index_of("TALENT", "妊娠")] = 0
                if st.flag[999] == 1:  # :941–948
                    raise NotImplementedError("デバッグ表示（AFTER_PILL:943–950）は未移植")
            else:
                out.printl("なんと、所持金が足りない！")
            return 0
        out.printl("妊娠の可能性に慌ててしまう気持ちも分かるが、ここは冷静になるべきだろう…")
        out.printw()
        out.clearline(out.linecount - lcount)
