"""幽閉本體：`ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB`（@PRISON／@PRISON_EVENT／@CHECK_CONTAMINATION）と
`ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON`:314–343、ボス触手の `_PRISON_ROUTINE`。
路徑相對 `source/earGVP/ERB/`。CFLAG の意味は `CSV定数定義/CFLAG.ERH` と PRISON.ERB の註解による（docs/wiki/era/prison.md）。

- `#DIM 今回陥落するフラグ=0` は静的（呼び出し間で保持：`TempVars.locals`）。`GOTO SKIP`（:106–107）で :109–283 を
  飛ばした場合は前回（別キャラを含む）の値のまま :287 以降の判定に使われる（原作どおり）。
- LOCAL も静的。:175 の `LOCAL:2` はこの時点で未代入なので前回の :240〜248 の値（原作どおり）。
"""

from __future__ import annotations

from ...state import GameState
from ...state.constants import GameOption
from ..action import (
    Ctx,
    config_check_maniac,
    config_check_prison,
    get_exp,
    get_syuren,
    kojo_root,
    print_callname,
    print_transcallname,
)
from ..battle.core import (
    BOSSES,
    LASTBOSSES,
    KANKAKU_NUM,
    abl,
    config_check_balance,
    exp,
    get_local,
    is_hole,
    percent_cal,
    run_chinobun,
    set_local,
    t,
    tc,
)
from ..chara_common import charatalent
from ..era import div, isqrt
from ..opening import game_option
from ..shop import check_gameover

FN = "PRISON_EVENT"
_FALL = ("PRISON_EVENT", "今回陥落するフラグ")


# --- TENTACLE_ACCESS_PRISON ------------------------------------------------------------------------


def _boss_prison_routine(ctx: Ctx, n: int) -> int:
    """`触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB@TENTACLE_BOSS_{n}_PRISON_ROUTINE`。"""
    from ..battle.sexcom import check_holyvirgin
    from .commands import prison_comable

    rand = ctx.state.rng.rand
    r = rand(100)
    table: tuple[tuple[int, int], ...]
    if n == 1:  # TENTACLE_BOSS_1_Ｃ触手.ERB:187–197
        table = ((30, 0), (40, 100))
    elif n == 2:  # TENTACLE_BOSS_2_Ｖ触手.ERB:192–208
        table = ((30, 1), (40, 101), (50, 200), (60, 104))
    elif n == 3:  # TENTACLE_BOSS_3_Ａ触手.ERB:199–225
        for bound, com in ((45, 2), (60, 102), (75, 201)):
            if r < bound:
                prison_comable(ctx, com)
                return 1
        r = rand(100)
        for bound, com in ((35, 4), (70, 6), (85, 300)):
            if r < bound:
                prison_comable(ctx, com)
                return 1
        prison_comable(ctx, 301)
        return 1
    elif n == 4:  # TENTACLE_BOSS_4_Ｂ触手.ERB:195–208
        table = ((30, 3), (40, 103), (50, 105))
    elif n == 5:  # TENTACLE_BOSS_5_Ｓ触手.ERB:195–205
        table = ((30, 4), (40, 300))
    elif n == 6:  # TENTACLE_BOSS_6_Ｐ触手.ERB:204–232
        if check_holyvirgin(ctx) == 0:
            table = ((30, 5), (35, 101), (40, 200))
        else:
            table = ((30, 5), (35, 102), (40, 201))
    elif n == 7:  # TENTACLE_BOSS_7_Ｈ触手.ERB:201–214
        table = ((30, 6), (35, 102), (40, 201))
    else:
        raise NotImplementedError(f"TENTACLE_BOSS_{n}_PRISON_ROUTINE は存在しない（TRYCALLFORM の不発は未対応）")
    for bound, com in table:
        if r < bound:
            prison_comable(ctx, com)
            return 1
    return 0


def _lastboss_prison_routine(ctx: Ctx, n: int = 1) -> int:
    """`TENTACLE_LASTBOSS_1_PRISON_ROUTINE`（TENTACLE_LASTBOSS_1_Ｋ触手.ERB:208–239）。"""
    from .commands import prison_comable

    r = ctx.state.rng.rand(100)
    # TENTACLE_LASTBOSS_2_天使の樹.ERB@TENTACLE_LASTBOSS_2_PRISON_ROUTINE:579–613。
    bounds = (((5,100),(10,101),(15,102),(20,103),(28,200),(36,201),(44,300),(52,301),(60,104),(68,105))
              if n == 2 else ((10,100),(20,101),(30,102),(40,103),(50,200),(60,201),(70,300),(75,104),(85,105)))
    for bound, com in bounds:
        if r < bound:
            prison_comable(ctx, com)
            return 1
    return 0


def tentacle_access_prison(ctx: Ctx, who: int, key: str):
    """`@TENTACLE_ACCESS_PRISON, ARG, ARGS`:314–343（CFLAG:ARG:20 == 0 のボス触手のみ移植）。

    "NAME" は名前を PRINTFORM、"GETNAME" は名前、"PRISON_ROUTINE" は 0／1、"PALAM_HOSEI" は 12 個の補正 %。
    CFLAG:20 == 2（悪堕ちキャラによる幽閉）はどの分岐にも入らない（NAME は何も出さず、ルーチンは関数終端で RESULT = 0：
    reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。
    """
    st = ctx.state
    c = st.charas[who]
    if c.cflag[20] == 0:
        n = c.cflag[21]
        if n not in BOSSES:
            raise NotImplementedError(f"TENTACLE_BOSS_{n} のデータは存在しない")
        b = BOSSES[n]
        if key == "NAME":
            ctx.out.print(b.name)
            return ""
        if key == "GETNAME":
            return b.name
        if key == "PRISON_ROUTINE":
            return _boss_prison_routine(ctx, n)
        if key == "PALAM_HOSEI":
            # TENTACLE_BOSS_6_Ｐ触手.ERB:124–127 `IF TFLAG:23` なら全て /4（TFLAG は前回戦闘の値のまま）
            r = tuple(div(v, 4) for v in b.palam_hosei) if n == 6 and st.tflag[23] else b.palam_hosei
            # ボスの PALAM_HOSEI（例 TENTACLE_BOSS_1_Ｃ触手.ERB:125）と :327 の 12 値 RETURN → 共用 RESULT:0〜11
            st.set_result_x(*r)
            return r
        raise KeyError(key)
    if c.cflag[20] == 1:  # :329–342 ラスボス（S27）
        n = c.cflag[21]
        if n not in (1,2):
            raise NotImplementedError(f"TENTACLE_LASTBOSS_{n} による幽閉は未移植")
        from ..battle.angel_tree import name as angel_name
        name = angel_name(st) if n == 2 else LASTBOSSES[n].name
        if key == "NAME":
            ctx.out.print(name)
            return ""
        if key == "GETNAME":
            return name
        if key == "PRISON_ROUTINE":
            return _lastboss_prison_routine(ctx,n)
        if key == "PALAM_HOSEI":
            # :338–339 は TENTACLE_**BOSS**_{CFLAG:ARG:21}_PALAM_HOSEI を呼ぶ（原作どおり：Ｋ触手の幽閉はＣ触手の補正値）
            b = BOSSES[n]
            st.set_result_x(*b.palam_hosei)
            return b.palam_hosei
        raise KeyError(key)
    # CFLAG:20 == 2（悪堕ちキャラによる幽閉）：:314–343 にこの分岐は無い → 関数終端で RESULT:0 = 0 だけ
    # （reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。RESULT:1〜11 は直前までの値のまま
    # （共用 RESULT＝GameState.result の殘值、照原作：使用者裁決 2026-10-02）。
    st.result[0] = 0
    if key == "PALAM_HOSEI":
        return tuple(st.result[i] for i in range(12))
    return 0 if key == "PRISON_ROUTINE" else ""


# --- @CHECK_CONTAMINATION -------------------------------------------------------------------------


def check_contamination(ctx: Ctx) -> int:
    """`@CHECK_CONTAMINATION`:430–443：陥落の閾値（汚染度 CFLAG:30 と比べる）。"""
    st = ctx.state
    c = tc(ctx)
    a = lambda n: abl(ctx, c, n)  # noqa: E731
    l1 = 260 + min(isqrt(max(c.base[ctx.data.index_of("BASE", "性耐性基礎")] - 60, 0) * 10) * 4, 340)
    l1 -= (a("触手中毒") * 16 + a("従順") * 8 + a("欲望") * 8 + a("奉仕精神") * 8 + a("露出癖") * 2 + a("マゾっ気") * 2
           + a("精液中毒") * 4 + a("噴乳中毒") * 4 + a("射精中毒") * 4)
    if l1 < 160:
        l1 = 160
    if config_check_prison(st, 3) > 0:
        l1 += t(ctx, c, "苗床化") * 80
    if st.flag[904]:
        l1 = div(l1 * 3, 4)
    return l1


# --- @PRISON ------------------------------------------------------------------------------------------


def prison(ctx: Ctx) -> None:
    """`@PRISON`:3–34：幽閉中（CFLAG:0 == 1）のキャラごとに TARGET を移して PRISON_EVENT。TARGET は戻さない。"""
    st, out = ctx.state, ctx.out
    local = 0
    if st.flag[999] == -998:  # PRISON.ERB@PRISON:5–8。
        st.flag[999] = 0
        out.reset_bgcolor()
    for i in range(st.charanum):  # :10 FOR LOCAL:999, 0, CHARANUM
        if i == GameState.MASTER:
            continue
        if st.charas[i].cflag[0] == 1 or check_gameover(st):
            if local == 0:
                out.drawline()
            st.target = i
            if local == 0:
                out.printl()
                out.printl("・・・")
                out.printl("・・・・・・")
                out.printl("・・・・・・・・・")
                out.printl()
            local = 1
            prison_event(ctx)
            local += 1
        if st.flag[999] == -998:
            break


def _msg(ctx: Ctx, name: str, code: str) -> None:
    run_chinobun(ctx, name, fallback=lambda: kojo_root(ctx, code))


def _msg_first(ctx: Ctx) -> None:
    """`地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST`:7–187。

    catalog で実行できない場合の代わり：:65–134／:135–162 の TS 分岐（TS_MtoF／TS_NORMAL／TS_FtoM による性別変化）は
    状態を変えるので停止、それ以外は末尾の KOJO_ROOT のみ。:9 UNLOCK_ACHIEVEMENT は実績（GLOBAL）のみ。
    """
    st, data = ctx.state, ctx.data
    c = tc(ctx)

    def fallback() -> None:
        from ..achievements import unlock
        unlock(ctx, 275, "女性の宿命")
        if c.cflag[6] == -1:
            return  # :12–64 娘キャラの地の文（口上呼び出しなし）
        if (charatalent(data, c, 0, "オトコ") > 0 or charatalent(data, c, 1, "オトコ") > 0) and config_check_prison(st, 0) > 0:
            raise NotImplementedError("幽閉時の TS 処理（TS_MtoF／TS_NORMAL／TS_FtoM）は未移植")
        kojo_root(ctx, "PRISON_PRISENTENCE_FIRST")

    run_chinobun(ctx, "MESSAGE_PRISON_PRISENTENCE_FIRST", fallback=fallback)


def ts_change(ctx: Ctx, *args) -> None:
    """地の文中の `CALL TS_MtoF／TS_NORMAL／TS_FtoM, TARGET`（hook）：性別変化は未移植。"""
    raise NotImplementedError("幽閉時の TS 処理（TS_MtoF／TS_NORMAL／TS_FtoM）は未移植")


def prison_event(ctx: Ctx) -> None:
    """`@PRISON_EVENT`:38–427。"""
    from ..battle.func import transform
    from ..battle.sexcom import check_holyvirgin
    from ..party import after_rescued, charanum_hope
    from .commands import prison_comable

    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    rand = st.rng.rand
    ti = lambda n: data.index_of("TALENT", n)  # noqa: E731
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    name = print_callname(st, st.target)
    # :42–46
    out.set_bold(True)
    tentacle_access_prison(ctx, st.target, "NAME")
    out.printl(f"幽閉：{print_callname(st, st.target, 1)}")
    out.set_bold(False)
    out.printl()
    # :49–60
    if c.cflag[20] < 2:
        st.flag[110] = 0
        st.flag[111] = 0
    elif c.cflag[20] == 2:
        st.flag[110] = 1
        for cc in range(st.charanum):
            if cc == GameState.MASTER:
                continue
            if st.charas[cc].cflag[240] == c.cflag[21]:
                st.flag[111] = cc
    # :64–91
    if (charatalent(data, c, 0, "オトコ") > 0 or charatalent(data, c, 1, "オトコ") > 0) and config_check_prison(st, 0) > 0:
        c.cflag[220] = 0
        _msg_first(ctx)
    elif c.cflag[31] == 0:
        c.cflag[220] = 0
        if exp(ctx, c, "幽閉経験") <= 1:
            _msg_first(ctx)
        else:
            _msg(ctx, "MESSAGE_PRISON_PRISENTENCE_START", "PRISON_PRISENTENCE_START")
    else:
        _msg(ctx, "MESSAGE_PRISON_PRISENTENCE", "PRISON_PRISENTENCE")
    if c.cflag[20] == 2:  # :94–95
        run_chinobun(ctx, "MESSAGE_OTHER_PRISON_PRISENTENCE")
    # :98–104 結界判定を更新
    for i in range(KANKAKU_NUM):
        st.shield[i] = 1 if c.base[i + 30] > 0 else 0
    local0 = KANKAKU_NUM  # FOR LOCAL,0,感覚数 の後の LOCAL
    fall = get_local(st, *_FALL)  # type: ignore[arg-type]
    if is_hole(ctx):  # :106–107 `SIF ISHOLE() == 0 / GOTO SKIP`
        # :111–161 幽閉コマンドの選択
        if c.cflag[220] > 0 and rand(100) < 30:
            prison_comable(ctx, 7)
        else:
            local0 = int(tentacle_access_prison(ctx, st.target, "PRISON_ROUTINE"))  # :116–117
            if local0 == 0:  # :120–159
                l1 = rand(100)
                if l1 < 12:
                    prison_comable(ctx, 0)
                elif l1 < 24:
                    prison_comable(ctx, 3 if check_holyvirgin(ctx) == 1 else 1)
                else:
                    for bound, com in ((36, 2), (48, 3), (60, 4), (72, 5), (84, 6), (89, 104), (94, 300)):
                        if l1 < bound:
                            prison_comable(ctx, com)
                            break
                    else:
                        prison_comable(ctx, 301)
            out.printl()  # :160
        # :164–172 被姦経験・汚染度
        c.exp[data.index_of("EXP", "被姦経験")] += 1
        c.cflag[31] += 1
        c.cflag[30] += 3 + rand(4)
        if tl("神器の担い手") > 0:
            c.cflag[30] += 3
        if tl("闘争本能") > 0:
            c.cflag[30] += 6
        # :175–179 搾精強化機能
        if config_check_balance(st, 3) > 0 and get_local(st, FN, 2) > 0:
            out.printl(f"{print_transcallname(st, st.target)}は触手の精液からエネルギーを吸収した！")
            get_syuren(ctx, rand(5) + rand(5) + 6)
            out.printl()
        # :182–194
        l1 = check_contamination(ctx)
        fall = 0
        if c.cflag[0] == 1 and (c.cflag[30] > l1 or tl("完堕ち") == 1):
            fall = 1
        if st.flag[999] == 1:
            out.set_color((105, 105, 105))
            out.printl()
            out.printl(f"　DEBUG　汚染値 = {c.cflag[30]}/{l1}")
            out.reset_color()
        # :198–277 淫紋
        if tl("触手の虜") and config_check_maniac(st, 6) == 1:
            _inmon(ctx, fall, l1)
        # :281–282（★変身が強制解除されないオプションを参照：原作の註解どおり）
        if config_check_balance(st, 6) == 0:
            transform(ctx, 0)
    # $SKIP :284
    set_local(st, *_FALL, fall)  # type: ignore[arg-type]
    if game_option(st, GameOption.NO_GAMEOVER) and charanum_hope(st) == 1:  # :288–290
        fall = 0
        set_local(st, *_FALL, fall)  # type: ignore[arg-type]
    solo = game_option(st, GameOption.SOLO)
    # :295–327 5 日以上の幽閉時（ソロ／サンドボックス）の脱出判定（RAND:4 は前の条件が真のときだけ引く）
    if (
        c.cflag[31] > 10
        and ((solo and fall == 0) or game_option(st, GameOption.NO_GAMEOVER))
        and c.cflag[6] != -1
        and rand(4) == 0
    ):
        out.printl("　　　　　　")
        out.printl("そのとき、触手の拘束が僅かに緩んだ！")
        if tl("触手の虜"):
            out.printl(f"まだ辛うじて理性が残っていた{name}は使命を思い出し、")
            if c.cflag[220]:
                out.print("我が子")
                if c.cflag[220] >= 2:
                    out.print("たち")
                out.printl("に別れを告げて外部へと脱出した・・・")
            else:
                out.printl("刹那の逡巡を捨て去って外部へと脱出した・・・")
        else:
            out.printl(f"最後の力を温存していた{name}はこの機を逃さず、")
            out.printl("決死の脱出劇を演じた末に、何とか外部へと逃れることができた・・・")
        out.printw()
        out.drawline()
        c.base[0] = 0  # 体力
        c.base[1] = 0  # 気力
        c.base[2] = 0  # 性耐性
        for k in (20, 21, 23, 30, 31, 220):
            c.cflag[k] = 0
        after_rescued(ctx, st.target)
        out.printw()
        out.drawline()
        return
    str2500 = data.str_defaults.get(2500, "")
    # :335–388 末路１ 洗脳／悪堕ち
    if fall == 1 and config_check_prison(st, 1) == 1 and (
        config_check_prison(st, 3) == 0 or (tl("変身能力") >= 0 and tl("嬲られ体質") < 1)
    ):
        out.printl()
        out.drawline()
        if tl("触手の虜") == 0 and config_check_prison(st, 9) == 0:
            c.cflag[0] = 2
            _msg(ctx, "MESSAGE_PRISON_SENNOU", "PRISON_SENNOU")
            if c.cflag[20] == 2:
                run_chinobun(ctx, "MESSAGE_OTHER_PRISON_SENNOU")
        elif tl("触手の虜") == 1 or config_check_prison(st, 9) == 1:
            from ..tattoo import save_tattoo_additional

            c.cflag[0] = 3
            c.exp[data.index_of("EXP", "陥落経験")] += 1
            if tl("変身能力") == 1:
                c.cflag[41] = 401
            save_tattoo_additional(ctx)
            _msg(ctx, "MESSAGE_PRISON_AKUOTI", "PRISON_AKUOTI")
            corrupt_change_looks_main(ctx, st.target)
            if c.cflag[20] == 2:
                run_chinobun(ctx, "MESSAGE_OTHER_PRISON_AKUOTI")
        if solo:  # :367–371
            from ..ending import ending_4

            ending_4(ctx)
            out.drawline()
            return
        out.printl(f"{str2500}の尖兵となった{name}に邪悪な力が流れ込む・・・")
        out.printl()
        lv = c.abl[data.index_of("ABL", "レベル")]
        if c.cflag[0] == 2:  # :377–381（CALL TENTACLE_LEVEL の RESULT は使われない）
            local0 = 20 * (5 + lv) + rand(25)
        elif c.cflag[0] == 3:
            local0 = 40 * (5 + lv) + rand(50)
        if local0 < 50:
            local0 = 50
        get_exp(ctx, min(local0, 750))
        c.cflag[23] = 0
        out.printw()
    # :397–424 末路２ 取り込まれロスト
    elif (
        c.cflag[0] == 1
        and c.cflag[31] > 19
        and (
            config_check_prison(st, 1) == 0
            or (config_check_prison(st, 2) == 1 and tl("苗床化") > 0)
            or tl("嬲られ体質") >= 1
        )
        and not game_option(st, GameOption.NO_GAMEOVER)
    ):
        out.printl()
        out.drawline()
        c.cflag[0] = 9
        _msg(ctx, "MESSAGE_PRISON_DEAD", "PRISON_DEAD")
        c.talent[ti("苗床化")] = 1
        if config_check_maniac(st, 14):
            c.talent[ti("四肢欠損")] = 1
            c.talent[ti("繁殖袋")] = 1
        if c.cflag[20] == 2:
            run_chinobun(ctx, "MESSAGE_OTHER_PRISON_DEAD")
        if solo:  # :417–421
            from ..ending import ending_5

            ending_5(ctx)
            out.drawline()
            return
        c.cflag[23] = 0
    out.drawline()  # :426–427
    out.printw()


def _inmon(ctx: Ctx, fall: int, l1: int) -> None:
    """PRISON_EVENT :198–277 触手の虜の淫紋。"""
    from ..tattoo import print_tattoo, save_tattoo, tattoo_access, tattoo_position

    st, out = ctx.state, ctx.out
    c = tc(ctx)
    tl = lambda n: t(ctx, c, n)  # noqa: E731
    pc = print_callname(st, st.target)
    inn = tl("淫核") + tl("淫壷") + tl("淫尻") + tl("淫乳")
    if c.cflag[32] == 0:  # :200–237
        out.printl()
        if config_check_maniac(st, 7) == 1 and inn > 0:
            out.print(f"激しい責めを受け続ける{pc}の")
            if tl("淫核") > 0 or tl("淫壷") > 0 or tl("淫尻") > 0 or tl("淫乳") > 0:
                if tl("淫尻") == 0 and tl("淫乳") == 0:
                    out.print("腹部")
                elif tl("淫乳") == 0:
                    out.print("下半身")
                else:
                    out.print("体中")
            elif tl("淫核") > 0:
                out.print("下腹部")
            elif tl("淫壷") > 0:
                out.print("腹部")
            elif tl("淫尻") > 0:
                out.print("右臀部")
            elif tl("淫乳") > 0:
                out.print("左乳房")
            out.printl("に、奇妙な紋様が浮かびつつある・・・")
        elif config_check_maniac(st, 7) == 1 and inn == 0:
            pass
        else:
            out.print(f"激しい責めを受け続ける{pc}の")
            r = tattoo_position(ctx)
            out.print({0: "下腹部", 1: "下腹部", 2: "右臀部", 3: "左乳房"}.get(r, ""))
            out.printl("に、奇妙な紋様が浮かびつつある・・・")
    elif fall == 0:  # :239–267
        local2 = 0
        if config_check_maniac(st, 7) == 1:
            local2 = 0
            bits = int(tattoo_access(ctx, "POSITION_BIT"))
            for i in range(KANKAKU_NUM):
                if (bits >> i) & 1 == 0 and c.talent[i + 153]:
                    local2 = i + 1
        set_local(st, FN, 2, local2)
        if local2 == 0:
            s = tattoo_access(ctx, "POSITION_STR")
            out.printl()
            out.printl(f"{pc}本人は気づいていないが、{s}にある紋様がその色を鮮やかに増してきているように見える・・・")
        else:
            out.print(f"{pc}の")
            out.print({1: "下腹部", 2: "腹部", 3: "右臀部", 4: "左乳房"}[local2])
            out.printl("に、新たな紋様が浮き出したようだ・・・")
    save_tattoo(ctx, percent_cal(c.cflag[30], l1))  # :270–271
    if fall == 0:  # :272–275
        print_tattoo(ctx, tattoo_position(ctx))
    out.printl()  # :276


def corrupt_change_looks_main(ctx: Ctx, who: int) -> None:
    """`ヒロイン関連/悪堕ち/CORRPUTION.ERB@CORRUPT_CHANGE_LOOKS_MAIN, ARG`:17–100（S21：`eragvt.game.corruption`）。
    :20–21 コンフィグ（CONFIG_CHECK_PRISON_F(4)）が 0 なら何もしない（基本セットは 0）。"""
    from ..corruption import corrupt_change_looks_main as _main

    _main(ctx, who)
