"""襲撃／救援イベント戦（S20）。

路徑相對 `source/earGVP/ERB/ゲーム内_イベント発生/`。行番号は各ファイル：
- 判定 `強制発生イベント/FORCE_襲撃or救援イベント発生.ERB@RAID_HANTEI`（`turnend.raid_hantei`）から `JUMP RAID_RESCUE／RAID_ATTACK`。
- 共通 `イベントから派生する特殊戦闘/●イベント戦闘_救援共通.ERB`（RESCUE = @RAID_RESCUE:3–216、@RAID_MISSION_SUCCESS:222–225、
  @RAID_MISSION_FAILURE:227–230）、`●イベント戦闘_襲撃共通.ERB`（ATTACK = @RAID_ATTACK:3–178）。
- 個別 `イベントから派生する特殊戦闘/2 女子高救出.ERB`・`3 女性自衛官小隊救援.ERB`・`4 攫われた女性.ERB`・`5 触手洞窟.ERB`・
  `3001 ボス触手の襲撃.ERB`・`3002 ボス触手の夜襲.ERB`・`3003 ライブ奇襲.ERB`・`3004 プール奇襲.ERB`、
  `特殊シチュエーション.ERB`（EVENT_BATTLE_SET_COSTUME:53–79。RESET は `battle.after.event_battle_reset_costume`）。

引擎語意：
- `JUMP` 先が RETURN すると JUMP 元（RAID_HANTEI）もそのまま RETURN する（reference/emuera-1824/Emuera/GameProc/
  Process.State.cs@Return:368–378）→ EVENTTURNEND:135 に戻る。`BEGIN TRAIN`／`BEGIN TURNEND` は呼び出しスタックを捨てる
  → ここでは `Step` を返す（`None` は RETURN）。
- 関数末尾まで流れ落ちると RESULT = 0（GameProc/Process.ScriptProc.cs:61–67）→ EVENT_BATTLE_EXEC_n は RESULT 0 を返し、
  呼び出し元は必ず ENCOUNT_BOSS を呼ぶ（RESCUE:187–189、ATTACK:152–154）。
- `RAND(a, b)` は a 以上 b 未満（GameData/Function/Creator.Method.cs@RandMethod:953–973）。PRINTDATA／STRDATA は
  `RAND:(DATA 数)` を 1 回引いて 1 つ選ぶ（GameProc/Function/Instraction.Child.cs@PRINT_DATA_Instruction:190–235、
  GameProc/Process.ScriptProc.cs:730–756）。
- `&&` と `||` は同じ優先度（0x40）で左結合（GameData/Expression/OperatorCode.cs:33–34、ExpressionParser.cs:502–507）。
- TINPUTS 100,"WARNING",0,""（演出ループ）：UI を飛ばすときは原作の既定路（＝何も入力しない：時間切れ）を通す（AGENTS.md）。
  時間切れで RESULTS = "WARNING"、入力値が 1 行エコーされる（S19 `akuoti` と同じ：GameView/EmueraConsole.cs@endTimer:638–662）。
  `CLEARLINE 5` は 4 行＋エコー 1 行を消すので、30 コマ後に残る表示は無い（色・太字の状態だけが残る）。
- INPUT の不正値は原作の `GOTO INPUT_LOOP`（何も表示せず再入力）。
- `@RAID_RESCUE` の LOCAL:1（:31 の試行回数）は :53 まで初期化されない関数の静的 LOCAL（呼び出し間で持ち越す）。
  通常の路では :53 で 0 にした後の演出ループ（30 コマ）で 0 に戻るので、次回は 0 から始まる。:35 の「見つからない」路だけは
  999 のまま残り、以後の RAID_RESCUE は毎回すぐ「気のせい」で終わる（原作どおり、`battle.core.get_local` で保持）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state.constants import ActionPlan
from .action import Ctx, Step, config_check_other, print_callname, print_transcallname, print_transname
from .battle.cloth import cloth_battle_damage, cloth_battle_sethp, refresh_cloth_data
from .battle.core import (
    add_randchoose,
    add_battle_situation,
    choicecount,
    clear_randchoose,
    get_local,
    is_girly,
    is_hole,
    randchoose_f,
    set_local,
    t,
    tc,
)
from .battle.func import state_change_betobeto, state_change_hairan
from .chara_common import is_female, is_male
from .era import div, limit
from .shop import charanum_safe
from .tentacle import enemy_type_check

RaidGen = Generator[None, int, "Step | None"]

HOTPINK = "#ff69b4"  # SETCOLORBYNAME HOTPINK（.NET Color.HotPink）
RED = "#ff0000"  # SETCOLORBYNAME RED
FUCHSIA = "#ff00ff"  # SETCOLORBYNAME Fuchsia

_FN_RESCUE = "RAID_RESCUE"


def _b(ctx: Ctx, name: str) -> int:
    return ctx.data.index_of("BASE", name)


def _name(ctx: Ctx) -> str:
    """`%PRINT_CALLNAME(TARGET)%`。"""
    return print_callname(ctx.state, ctx.state.target)


def _input(choices: tuple[int, ...]) -> Generator[None, int, int]:
    """`$INPUT_LOOP / INPUT / IF … ELSE GOTO INPUT_LOOP`：choices 以外は何も出さずに再入力。"""
    while True:
        r = yield
        if r in choices:
            return r


def _warning_loop(ctx: Ctx, text: str, color) -> None:
    """RESCUE:58–88／ATTACK:66–96 の演出（FLAG:999 == 0 のときだけ 30 コマ）と最後の 1 コマ。"""
    st, out = ctx.state, ctx.out
    out.printl()
    out.printl()
    out.printl()
    if st.flag[999] == 0:
        l1, l2 = 0, 0
        for _ in range(30):  # REPEAT 30
            if l2 == 0:
                l1 += 50
                if l1 == 250:
                    l2 = 1
            else:
                l1 -= 50
                if l1 == 0:
                    l2 = 0
            out.set_bold(True)
            out.set_color(color(l1))
            out.printl(text)
            out.printl()
            out.printl()
            out.printl()
            out.printl("WARNING")  # TINPUTS 100,"WARNING",0,""：時間切れ（既定路）→ 入力値のエコー
            out.clearline(5)
            # SIF RESULTS != "WARNING" / BREAK：既定路では RESULTS = "WARNING"
    out.set_color(color(250))
    out.printl(text)
    out.printl()
    out.printl()
    out.printl()
    out.reset_color()
    out.set_bold(False)  # FONTREGULAR


def _heal(ctx: Ctx) -> None:
    """RESCUE:91–95／ATTACK:108–112「狙われたキャラはわずかに体力気力が回復する」。"""
    c = tc(ctx)
    local = div(c.maxbase[0], 10) + 500
    c.base[0] = limit(local + c.base[0], 0, c.maxbase[0])
    local = div(c.maxbase[1], 100) + 500
    c.base[1] = limit(local + c.base[1], 0, c.maxbase[1])


def _pre_train_init(ctx: Ctx) -> None:
    """RESCUE:168–178／ATTACK:124–133：VARSET TCVARn（TARGET）・VARSET TFLAG・TFLAG:0 = -1・TCVARn:0 = 3・衣装耐久。
    TFLAG は BEGIN TRAIN でもう一度 0 になる（VariableEvaluator.cs@UpdateInBeginTrain：`battle.train.update_in_begin_train`）が、
    イベント本文中の CLOTH_BATTLE_DAMAGE 等は TFLAG:0 = -1（敵名の前置きなし）を見る。"""
    st = ctx.state
    c = tc(ctx)
    c.tcvarn.clear()
    st.tflag.clear()
    st.tflag[0] = -1
    c.tcvarn[0] = 3
    cloth_battle_sethp(ctx)
    refresh_cloth_data(ctx)


def _sex_resist_down(ctx: Ctx, base_div: int, floor: int, rnd: int, rnd_min: int = 0) -> int:
    """`LOCAL = MAX(BASE:性耐性 / d, f) + RAND…` / `BASE:性耐性 = MAX(BASE:性耐性 - LOCAL, 0)`。rnd_min > 0 は RAND(min, max)。"""
    st = ctx.state
    c = tc(ctx)
    r = st.rng.rand(rnd - rnd_min) + rnd_min
    local = max(div(c.base[2], base_div), floor) + r
    c.base[2] = max(c.base[2] - local, 0)
    return local


# --- @RAID_RESCUE ---------------------------------------------------------------------------------


def raid_rescue(ctx: Ctx) -> RaidGen:
    """`●イベント戦闘_救援共通.ERB@RAID_RESCUE`:3–216。"""
    from .battle.ninsin import check_pregnant

    st, out = ctx.state, ctx.out
    # :8–20 全員非戦闘員ならイベント終了
    local = 0
    for i in range(1, st.charanum):
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        if t(ctx, c, "繁殖袋") > 0 or t(ctx, c, "四肢欠損") > 0:
            continue
        if (
            c.cflag[0] == 0
            and c.cflag[100] != ActionPlan.SORTIE
            and c.cflag[100] != ActionPlan.DEFENSE
            and t(ctx, c, "変身能力") != -1
            and check_pregnant(ctx, i) == 0
            and c.cflag[99] < 50
        ):
            local += 1
    if local < 1:
        return None
    out.drawline()  # :22
    st.flag[43] = 0  # :23
    # :27–40 $LOOP
    l1 = get_local(st, _FN_RESCUE, 1)
    while True:
        local = st.rng.rand(st.charanum - 1) + 1
        c = st.charas[local]
        if (
            c.cflag[100] == ActionPlan.SORTIE
            or c.cflag[100] == ActionPlan.DEFENSE
            or c.cflag[0] != 0
            or c.cflag[999] == 0
            or t(ctx, c, "変身能力") == -1
        ) and l1 < 999:
            l1 += 1
            continue
        if l1 >= 999:
            set_local(st, _FN_RESCUE, 1, l1)
            st.flag[45] = 0
            out.printl(f"{c.callname}は何か嫌な気配を感じたが、気のせいだったようだ…")
            out.printw()
            return None
        break
    st.target = local  # :42
    if st.flag[999]:  # :45–50（デバッグ等で指定済み）
        pass
    else:
        st.flag[45] = st.rng.rand(6 - 2) + 2  # RAND(2, 6)
    set_local(st, _FN_RESCUE, 1, 0)  # :53（演出ループ後も 0：モジュール docstring）
    _warning_loop(ctx, "　　　―――――　　　ＥＭＥＲＧＥＮＣＹ　！！　　―――――", lambda v: (v, v, 0))  # :55–88
    _heal(ctx)  # :91–95
    out.printl()  # :97
    c = tc(ctx)
    cf100 = c.cflag[100]
    if st.time == 0:  # :98–108
        text = {
            ActionPlan.TRAINING: "鍛錬を終えて街に出ていた",
            ActionPlan.REST: "息抜きがてらに街に出ていた",
            ActionPlan.ACTIVITY: "特別活動を終えて帰り仕度していた",
            ActionPlan.SUPPORT: "戦闘支援を終えて街に出ていた",
        }.get(cf100)
    else:  # :109–124
        text = {
            ActionPlan.TRAINING: "鍛錬を終えたばかりの",
            ActionPlan.REST: "自室に居た",
            ActionPlan.ACTIVITY: "特別活動を終えて戻った",
            ActionPlan.SUPPORT: "戦闘支援を行っていた",
            107: "情報収集を終えて戻った",
            108: "自由行動を終えて戻った",
        }.get(cf100)
    if text:
        out.print(text)
    out.printl(f"{_name(ctx)}のもとに、緊急の連絡が入った。")
    # :128–142 TRYCCALLFORM EVENT_BATTLE_SITUATION_{FLAG:45}
    sit = _SITUATION.get(st.flag[45])
    if sit is None:
        out.printl()
        out.printl("#####     ERROR !!     #####")
        out.printl(f"存在しないイベントが選択されました。（EVENT_BATTLE_SITUATION_{st.flag[45]}）")
        if st.flag[999]:
            out.printl("存在するイベントを選択してください")
        else:
            out.printl("原因究明のため、掲示板にできるだけ詳細な発生状況を報告してください")
        out.printw()
        out.printl("イベントを強制スキップして無理やりゲームを続行します")
        out.printw()
        return None
    sit(ctx)
    out.wait()  # :144 FORCEWAIT
    out.printl()  # :145–148
    out.printl("どうする？")
    out.printl("（ボス触手と撤退不可の戦闘になります。助けに行かなくてもペナルティはありません）")
    out.printl(" 　[0]助けに行く　　[1]助けに行かない")
    r = yield from _input((0, 1))  # :149–163
    if r == 0:
        out.printl()
        _RESCUE_MSG[st.flag[45]](ctx)  # CALLFORM EVENT_BATTLE_RESCUE_{FLAG:45}
    else:
        out.printl()
        _abandon(ctx)  # CALLFORM EVENT_BATTLE_ABANDON_{FLAG:45}
        out.printw()
        st.flag[45] = 0
        return None
    _pre_train_init(ctx)  # :168–178
    out.printw()  # :181
    from .akuoti import dot_after

    dot_after(ctx, 1)  # :182
    out.printl()
    step = yield from _exec(ctx)  # :184 CALLFORM EVENT_BATTLE_EXEC_{FLAG:45}
    if step is not None:
        return step
    return _encount_and_begin(ctx)  # :186–216


def _encount_and_begin(ctx: Ctx) -> "Step | None":
    """RESCUE:186–216／ATTACK:151–178：EXEC の RESULT（常に 0）→ ENCOUNT_BOSS → BEGIN TRAIN。"""
    from .battle.encount import encount_boss

    st, out = ctx.state, ctx.out
    result = encount_boss(ctx)  # RESULT != 1 → CALL ENCOUNT_BOSS
    if st.flag[999] == 1:
        out.printw(f"エンカウント番号 == {result}")
    if result != 1:
        out.printl()
        out.printl("#####     ERROR !!     #####")
        out.printl("ボス襲撃イベント不発バグです。原因究明のため、")
        out.printl("掲示板にできるだけ詳細な発生状況を報告してください")
        out.printw()
        out.printl("イベントを強制スキップして無理やりゲームを続行します")
        out.printw()
        return None
    if enemy_type_check(st, "AKUOTI"):
        out.printl()
        out.printl("#####     ERROR !!     #####")
        out.printl('ENEMY_TYPE_CHECK_F("AKUOTI")TRUEバグです。原因究明のため、')
        out.printl("掲示板にできるだけ詳細な発生状況を報告してください")
        out.printw()
        out.printl("イベントを強制スキップして無理やりゲームを続行します")
        out.printw()
        return None
    return Step.TRAIN


# --- @RAID_ATTACK ---------------------------------------------------------------------------------


def raid_attack(ctx: Ctx) -> RaidGen:
    """`●イベント戦闘_襲撃共通.ERB@RAID_ATTACK`:3–178。"""
    st, out = ctx.state, ctx.out
    out.drawline()  # :5
    st.flag[43] = 0  # :6
    clear_randchoose(st)  # :10
    for i in range(st.charanum):  # :11–30
        if i == 0:  # MASTER
            continue
        if not is_hole(ctx):  # :15 ISHOLE()：引数省略 = TARGET（候補 CCOUNT ではない：原作どおり。汎用関数/SEX_GENDER.ERB:52–56）
            continue
        c = st.charas[i]
        if c.cflag[100] in (101, 105) or c.cflag[0] != 0 or c.cflag[999] == 0:  # :18
            continue
        add_randchoose(st, i)
        if t(ctx, c, "巻き込まれ体質") > 0:
            add_randchoose(st, i)
            add_randchoose(st, i)
        if t(ctx, c, "人外の美貌") > 0:
            add_randchoose(st, i)
            add_randchoose(st, i)
    if choicecount(st) < 1:  # :32–35
        st.flag[45] = 0
        return None
    st.target = randchoose_f(st)  # :36
    c = tc(ctx)
    if st.flag[999]:  # :41–60
        pass
    elif t(ctx, c, "四肢欠損") > 0 or t(ctx, c, "繁殖袋") > 0:
        st.flag[45] = 3002
    elif c.cflag[100] == 104 and c.cflag[101] == 8:
        st.flag[45] = 3003
    elif c.cflag[100] == 108 and c.cflag[101] == 20 and st.time == 1:
        st.flag[45] = 3004
    elif st.time == 0 and t(ctx, c, "夜魔の貴族") == 0:
        st.flag[45] = 3001
    else:
        st.flag[45] = 3002
    _warning_loop(ctx, "　　　―――――　　　ＷＡＲＮＩＮＧ　！！　　―――――", lambda v: (v, 0, 0))  # :63–96
    c.tcvarn.clear()  # :101 VARSET TCVARn
    cloth_battle_sethp(ctx)  # :103–105
    refresh_cloth_data(ctx)
    _heal(ctx)  # :108–112
    out.printl()  # :116
    _pre_train_init(ctx)  # :124–133
    if st.flag[45] not in _EXEC:  # :136–150 TRYCCALLFORM EVENT_BATTLE_EXEC_{FLAG:45} / CATCH
        out.printl()
        out.printl("#####     ERROR !!     #####")
        out.printl(f"存在しない襲撃イベントが選択されました。（EVENT_BATTLE_SITUATION_{st.flag[45]}）")
        if st.flag[999]:
            out.printl("存在するイベントを選択してください")
        else:
            out.printl("原因究明のため、掲示板にできるだけ詳細な発生状況を報告してください")
        out.printw()
        out.printl("イベントを強制スキップして無理やりゲームを続行します")
        out.printw()
        return None
    step = yield from _exec(ctx)
    if step is not None:
        return step
    return _encount_and_begin(ctx)


# --- 戦闘後：RAID_MISSION_SUCCESS／FAILURE（BATTLE_TRAIN_AFTER.ERB から）----------------------------


def mission_check(ctx: Ctx, default: int) -> None:
    """`BATTLE_TRAIN_AFTER.ERB`:187–198／:286–297／:379–390：TRYCCALLFORM EVENT_BATTLE_MISSION_CHECKER_{FLAG:45}、
    CATCH なら default（時間切れ・勝利 1、敗北 0）→ RAID_MISSION_SUCCESS／FAILURE。"""
    st = ctx.state
    checker = _CHECKER.get(st.flag[45])
    result = checker(ctx) if checker is not None else default
    if result == 1:
        raid_mission_success(ctx)
    else:
        raid_mission_failure(ctx)


def raid_mission_success(ctx: Ctx) -> None:
    """`●イベント戦闘_救援共通.ERB@RAID_MISSION_SUCCESS`:222–225。"""
    from .akuoti import dot_after

    dot_after(ctx, 1)
    ctx.out.printl()
    f = _SUCCESS.get(ctx.state.flag[45])  # TRYCALLFORM
    if f is not None:
        f(ctx)


def raid_mission_failure(ctx: Ctx) -> None:
    """`●イベント戦闘_救援共通.ERB@RAID_MISSION_FAILURE`:227–230。"""
    from .akuoti import dot_after

    dot_after(ctx, 1)
    ctx.out.printl()
    f = _FAILURE.get(ctx.state.flag[45])  # TRYCALLFORM
    if f is not None:
        f(ctx)


def event_battle_turnend(ctx: Ctx) -> None:
    """`BATTLE_COM.ERB@EVENTCOMEND`:981 `TRYCALLFORM EVENT_BATTLE_TURNEND_{FLAG:45}`（3003／3004 のみ定義）。"""
    f = _TURNEND.get(ctx.state.flag[45])
    if f is not None:
        f(ctx)


def news_failure(ctx: Ctx) -> None:
    """`Sif !FLAG:60 / FLAG:60 = 100000 + (TFLAG:98 == 0 ? 0 # 20000) + FLAG:45`（各 FAILURE）。"""
    st = ctx.state
    if not st.flag[60]:
        st.flag[60] = 100000 + (0 if st.tflag[98] == 0 else 20000) + st.flag[45]


def news_success(ctx: Ctx) -> None:
    """`Sif !FLAG:60 / FLAG:60 = 110000 + FLAG:45`（各 SUCCESS）。"""
    st = ctx.state
    if not st.flag[60]:
        st.flag[60] = 110000 + st.flag[45]


def _abandon(ctx: Ctx) -> None:
    """EVENT_BATTLE_ABANDON_2〜5（2:19–25、3:21–27、4:197–203、5:23–29）。5 だけ 1 行目が違う。"""
    st, out = ctx.state, ctx.out
    if st.flag[45] == 5:
        out.printl("不確定要素も多く、退路すら万全でない状態で触手の巣に踏み込むのは自殺行為だ。")
    else:
        out.printl("不確定要素も多く、万全でもない状態で触手生物と戦うのは危険すぎる。")
    out.printl(f"状況から判断した結果、{_name(ctx)}は助けに行かないという決断を下した……")
    if not st.flag[60]:
        st.flag[60] = 100000 + st.flag[45]


def _rescue_msg(ctx: Ctx) -> None:
    """EVENT_BATTLE_RESCUE_2〜5（2:15–17 ほか同文）。"""
    ctx.out.printl("たとえ危険が伴うとしても、この事態を見過ごすわけにはいかない。")
    ctx.out.printl(f"{_name(ctx)}は意を決して現場に向かうことにした……")


def event_battle_set_costume(ctx: Ctx, num: int, a0: int, a1: int, a2: int, a3: int) -> None:
    """`特殊シチュエーション.ERB@EVENT_BATTLE_SET_COSTUME(num,ARG,ARG:1,ARG:2,ARG:3)`:53–79。"""
    st = ctx.state
    if config_check_other(st, 8) == 1:  # :56–57
        return
    c = st.charas[num]
    if c.cflag[544] == 0:  # :60–66
        c.cflag[544] = 1
        for i in (40, 41, 42, 43):
            c.cflag[500 + i] = c.cflag[i]
    for i, a in zip((40, 41, 42, 43), (a0, a1, a2, a3)):  # :68–75
        if a >= 0:
            c.cflag[i] = a
    cloth_battle_sethp(ctx)  # :77–79（TARGET）
    refresh_cloth_data(ctx)


def battle_event_cloth_status(ctx: Ctx, cid: int) -> str:
    """`武器と衣装/衣装関連/CLOTHDATA※イベント専用装備.ERB@CLOTH_STATUS_990／991／992`:81–99 が SAVESTR:0 に入れる文字列。
    `TRYCCALLFORM BATTLE_EVENT_CLOTH_STATUS_{FLAG:45}("info", 部位)`：定義はプール奇襲（3004：`3004 プール奇襲.ERB`:172–249）のみ。
    3004 の OUTER／OUTER_TRANS は何も代入しない（SAVESTR:0 は前の値のまま：原作どおり）。
    `@CLOTH_STATUS_991` は同ファイルに 2 つ（:73 と :88）あり、同名の非イベント関数は最初に定義されたもの（:73
    「SLOT-1,HP0,def0,」）が呼ばれる（reference/emuera-1824/Emuera/GameProc/LabelDictionary.cs:66–76、
    LogicalLine.cs@CompareTo:274–282）。"""
    st = ctx.state
    if cid == 991:
        return "SLOT-1,HP0,def0,"
    if st.flag[45] != 3004:  # CATCH
        return {990: "SLOT-1,HP100,", 992: "SLOT-1,HP80,SEITAISEI95,"}[cid]
    if cid == 990:
        return st.savestr[0]
    c = tc(ctx)
    name, text = {
        0: ("紐ビキニ", "SLOT-1,HP20,SEITAISEI45,"),
        1: ("ローライズビキニ", "SLOT-1,HP25,SEITAISEI45,"),
        2: ("チューブトップ", "SLOT-1,HP25,SEITAISEI45,"),
        3: ("ハイレグ水着", "SLOT-1,HP25,SEITAISEI45,"),
        4: ("少女用スクール水着", "SLOT-1,HP35,SEITAISEI55,"),
        5: ("競泳水着", "SLOT-1,HP35,SEITAISEI55,"),
    }.get(c.cflag[270], ("水着", "SLOT-1,HP35,SEITAISEI55,"))  # :198–248 SELECTCASE CFLAG:TARGET:270
    c.cstr[82] = name
    return text


# =====================================================================================================
# 個別イベント
# =====================================================================================================


def _exec(ctx: Ctx) -> RaidGen:
    return (yield from _EXEC[ctx.state.flag[45]](ctx))


def _turn_limit(ctx: Ctx, n: int) -> None:
    """`ターン上限 = n`（DIM.ERH の非 SAVEDATA 変数：`state.temp.turn_limit`）。"""
    ctx.state.temp.turn_limit = n


# --- 2 女子高救出 ---------------------------------------------------------------------------------


def _situation_2(ctx: Ctx) -> None:
    """`2 女子高救出.ERB@EVENT_BATTLE_SITUATION_2`:4–13。"""
    out = ctx.out
    out.printl("どうやら近くの女子高に大型触手生物が出現し、大暴れしているらしい。")
    out.printl("自衛隊が出動したが、生徒たちは校舎の中に取り残されたままだという。")
    out.printl("放っておけば多数の犠牲者が出るだろう。")
    out.set_color(HOTPINK)
    out.printl("校舎全体が触手に侵蝕され、中心部への進入も困難を極めるようだが……")
    out.reset_color()
    out.printl()
    out.printl("危険を承知で助けに行くべきだろうか？")


def _entangled(ctx: Ctx) -> None:
    """2:55–63 ほか「絡みつかれてしまった」→ 性耐性 MAX(/10, 10) + RAND:3 減少。"""
    out = ctx.out
    out.printl("絡みつかれてしまった！")
    out.printl("触手が胸や腰を撫でまわし、股間にも伸びて先端を擦りつけてくる。")
    out.printl(f"何とか触手を振り解いた{_name(ctx)}だが、全身を粘液まみれにされてしまった。")
    out.printw()
    local = _sex_resist_down(ctx, 10, 10, 3)
    out.printl(f"　性耐性が{local}減少した！")
    out.printw()


def _exec_2(ctx: Ctx) -> RaidGen:
    """`2 女子高救出.ERB@EVENT_BATTLE_EXEC_2`:28–258。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name
    out.printl("襲撃されたという女子高までやってくると、既に特殊部隊が突入路を確保してくれていた。")
    out.printl("夥しい数の雑魚触手の死体で校庭が埋め尽くされ、")
    out.printl("周囲は返り血と粘液と弾痕で酷い有様だ。")
    out.printl(f"自衛隊員に襲いかかっていた雑魚触手を叩き伏せ、{n(ctx)}は状況の悪さに眉をしかめた。")
    out.printw()
    out.printl("このまま雑魚触手を倒し続けても埒が明かない。")
    out.printl("ボスを叩かなければ収拾が付かないだろう……そう判断して外部の制圧を自衛隊に任せ、")
    out.printl(f"{n(ctx)}は校舎の内部へと踏み込むことにする。")
    out.printw()
    out.printl("学校内部は触手の浸食により、建物と肉とがグロテスクに融合した触手の巣になりつつあった。")
    out.printl("本来ならコツコツと足音を反響するはずの床は不気味な臓器に覆われてブヨブヨと変形し、")
    out.printl("天井からは得体の知れない肉腫が垂れ下っている。")
    out.printl(f"すると突然壁から触手が伸びてきて、{n(ctx)}を捕まえようとしてきた！")
    out.printw()
    out.printl("どうする？")
    out.printl("　[0]触手を薙ぎ払う　[1]咄嗟に避ける　[2]動きを見極める")
    out.printl()
    r = yield from _input((0, 1, 2))  # :46–101
    atk, dfn, agi, intel = (c.base[_b(ctx, k)] for k in ("攻撃", "防御", "敏捷", "知性"))
    if r == 0:
        ok = atk + dfn >= 250
        good = f"{n(ctx)}が迫りくる触手を薙ぎ払うと、触手はたちまち細切れになった。"
        bad = f"{n(ctx)}は迫りくる触手を薙ぎ払おうとしたが力負けしてしまい、"
    elif r == 1:
        ok = dfn + agi >= 250
        good = f"{n(ctx)}は咄嗟に触手から身を躱わした。"
        bad = f"{n(ctx)}は触手から身を躱わそうとしたが間に合わず、"
    else:
        ok = intel >= 110
        good = f"{n(ctx)}は触手の動きを見極め、回避することに成功した。"
        bad = f"{n(ctx)}は触手の動きを見極めようとしたが動きに反応しきれず、"
    if ok:
        out.printl(good)
        out.printl("分かってはいたが、探索は簡単にはいかないようだ。")
        out.printw()
    else:
        out.printl(bad)
        _entangled(ctx)
    out.printl(f"{n(ctx)}は警戒を怠らずに奥へと進んでいく……")  # :102–103
    out.printw()
    out.printl("途中何度か雑魚触手と遭遇して戦いながら、魔境と化した校内を進む。")
    out.printl("すると壁際から「誰か…」という声がしたので振り返ると、")
    local = st.rng.rand(7)  # :106（RAND:7 は 0〜6：LOCAL == 7 の分岐には来ない、原作どおり）
    who = {
        7: ("捕まってしまった自衛隊員らしき女性が", "女性"),
        6: ("授業参観に来ていた保護者らしき女性が", "女性"),
        5: ("眼鏡を掛けた教員らしき女性が", "女性"),
        4: ("凛々しい見た目の教員らしき女性が", "女性"),
        3: ("地味な見た目の教員らしき女性が", "女性"),
        2: ("体操服とニーソックス姿の少女が", "少女"),
        1: ("風紀委員の腕章を付けた制服の少女が", "少女"),
    }.get(local, ("派手なアクセサリを付けた金髪の制服少女が", "少女"))
    out.print(who[0])
    ls = who[1]
    out.printl("触手に手足を取り込まれて、")
    out.printl("まるで磔にされたような状態で犯されていた。")
    l1 = st.rng.rand(2)  # :134
    if l1 == 0:
        if local == 7:
            out.print("迷彩柄のズボンは脱がされ")
        elif local in (6, 5, 4, 3):
            out.print("ストッキングを破られて")
        elif local == 2:
            out.print("胸を突き出すような体勢で")
        else:
            out.print("スカートを捲り上げられ")
        out.printl("触手が股間に突き立てられ、卑猥な水音を立てている。")
    else:
        out.printw()
        out.printl("風船のように膨らんだ腹部がピストンのストロークのたびに揺れ、")
        out.printl("半透明の壺状の触手が両胸の乳房から母乳を搾り取っていた。")
        out.printw()
        out.printl(f"おそらく{ls}はもう、妊娠している。")
        out.printl(f"手遅れという言葉が{n(ctx)}の脳裏をよぎったとき、")
        out.printl(f"虫の息の{ls}と目が合った。")
    out.printw()
    out.printl(f"{ls}はこちらに気づくと、自分のことはいいから奥にいる生徒たちを助けてくれと懇願してきた。")
    out.printl("恐怖と快楽と苦痛に尊厳を踏みにじられながらも、気丈にも他人の心配をする様が胸を打つ。")
    out.printl(f"早く…皆を…と声を振り絞った{ls}は、歯を食いしばって凌辱に耐え続けている。")
    out.printl("すぐに後続の自衛隊員が駆けつけてくれるだろうが、")
    out.printl(f"このまま放っておいたら{ls}が保たないかもしれない……")
    out.printw()
    out.printl("どうする？")
    out.printl(f"　[0]先を急ぐ　[1]{ls}を助け出す")
    out.printl()
    r = yield from _input((0, 1))  # :165–226
    if r == 0:
        out.printl("今はこの悪夢を早く終わらせることのほうが先決だ。")
        out.printl(f"{n(ctx)}は{ls}に謝罪して、先を急いでその場を立ち去った……")
        out.printl(f"背後から聴こえ始めた悲鳴、嬌声の入り混じる絶叫が{n(ctx)}の心を責め立てる……")
        out.printw()
    else:
        if l1 == 0:
            out.printl(f"{n(ctx)}は{ls}を凌辱する触手を止めようと掴みかかったが、")
            out.printl("ヌメヌメとしていて動きをうまく止められない。")
            out.printl(f"為すすべなく焦る{n(ctx)}の目の前で触手の動きが速くなっていき、")
            out.printl(f"やがて触手は{ls}の胎内に溢れんばかりの白濁液を注ぎ込んだ。")
            out.printw()
            out.printl(f"悪戦苦闘の末に何とか{ls}を助け出すことに成功したものの、")
            out.printl(f"{ls}は既に十数回も中出しされてしまっており、疲れ果てて気絶してしまっていた。")
            out.printl(f"遅れてやってきた自衛隊の救援部隊に{ls}を預けて先に進む{n(ctx)}だったが、")
            if t(ctx, c, "主観視点") > 0:
                out.printl("目の前で繰り広げられた痴態に股間をじわりと濡らしてしまった……")
            else:
                out.printl("目の前で繰り広げられた痴態に股間がじわりと濡れてしまっている……")
        else:
            out.printl(f"{n(ctx)}は苗床にされた{ls}から触手を引きはがそうとするが、")
            out.printl("すでに半ばまで取り込まれてしまっており手の施しようが無かった。")
            out.printl(f"すると次の瞬間、{ls}の様子が急変して叫び始め、")
            out.printl("膨らんだ腹部が不気味に蠢き始めた。")
            out.printw()
            out.printl("精液を撒き散らしながら触手がヴァギナから引き抜かれると、")
            out.printl("続いて白濁交じりの大量の羊水と十数匹もの触手の幼生が吹き出した。")
            out.printl(f"精根尽き果てぐったり項垂れる{ls}の膣口からは無数のへその緒が垂れ下っており、")
            out.printl(f"{n(ctx)}は茫然と足元の水たまりに蠢く幼生たちを見つめるしかなかった。")
            out.printw()
            out.printl(f"遅れてやってきた自衛隊の衛生班に{ls}を預けて先に進む{n(ctx)}だったが、")
            male = is_male(ctx.data, c)  # ISMALE()：TARGET
            if t(ctx, c, "主観視点") > 0:
                if male:
                    out.printl("目の前で繰り広げられた異種出産の様子に股間をじわりと疼かせてしまった……")
                else:
                    out.printl("目の前で繰り広げられた異種出産の様子に股間をじわりと濡らしてしまった……")
            elif male:
                out.printl("目の前で繰り広げられた異種出産の様子に股間がじわりと疼かせてしまっている……")
            else:
                out.printl("目の前で繰り広げられた異種出産の様子に股間がじわりと濡らしてしまっている……")
        out.printw()
        local2 = _sex_resist_down(ctx, 4, 20, 6)  # :218–219
        st.flag[853] += 1
        out.printl("　人気度が1上昇した！")
        out.printl(f"　性耐性が{local2}減少した！")
        out.printw()
    out.printl("さらに奥へと進んでいくと、大きく開けた場所に出た。")  # :227
    if st.rng.rand(2) == 0:  # :228–244
        place = "体育館"
        out.printl("元は体育館だったであろうその場所には多くの生徒たちが寄り集まっており、")
        out.printl("互いを庇い合って何とか凌いでいるようだ。")
        out.printl((
            "まだ無事な者も多いが、雑魚触手に襲われてしまっている少女の姿が目立つ。",
            "少女らだけで触手を防げるはずもなく、凌辱の宴が始まるのも時間の問題だろう。",
        )[st.rng.rand(2)])  # PRINTDATAL（DATAFORM 2 つから 1 つ）
    else:
        place = "礼拝堂"
        out.printl("おそらく礼拝堂なのだろうか、")
        out.printl("神聖なステンドグラスやオルガンの周囲に這いまわる異形の触手が冒涜的だ。")
        out.printl((
            "見れば多数の気絶した生徒があちこちに倒れている。",
            "ほとんどの生徒は意識を失い、雑魚触手に組み伏せられつつある。",
        )[st.rng.rand(2)])
    out.printw()
    out.printl(f"生存者を助けようと{n(ctx)}が{place}に踏み込むと、")
    out.printl("目の前に超重量の物体が躍り出てきた。")
    out.printl("おそらくコイツが親玉……今回の事件の元凶だろう。")
    out.printl(f"邪悪な怪物の首魁を前に、{n(ctx)}は戦闘態勢を取った！")
    out.printw()
    out.printl("（救援イベント中は撤退できません！　１５ターン耐えればミッション成功です！）")
    out.printw()
    out.drawline()
    _turn_limit(ctx, 15)
    add_battle_situation(st, "撤退不可,耐久戦,市民なし,レイプなし")
    return None


def _checker_not_lose(ctx: Ctx) -> int:
    """MISSION_CHECKER_2／3／5／3001／3002：`IF TFLAG:98 == 2 RETURN 0 ELSE RETURN 1`。"""
    return 0 if ctx.state.tflag[98] == 2 else 1


def _success_2(ctx: Ctx) -> None:
    """2:270–285。"""
    out, st = ctx.out, ctx.state
    n = _name(ctx)
    out.printl(f"{n}の活躍により、多数の生存者を助け出すことができた。")
    out.printl("多くはまだ年端も行かぬ少女たちであり、")
    out.printl("未来がこんな事件で閉ざされてしまうことなどあってはならないのだ。")
    out.printw()
    out.printl(f"精一杯の感謝の言葉と共に手を振る少女たちに{n}は頬笑みを返す。")
    out.printl("彼女らが失ったものは大きい。だが、それでもきっと立ち直って強く生きていくだろう。")
    out.printl(f"なぜなら少女たちはきっと、触手と戦う{n}の姿を一生忘れないだろうから……")
    out.printw()
    _reward(ctx, 3, 5000)
    news_success(ctx)


def _reward(ctx: Ctx, pop: int, money: int) -> None:
    """`PRINTFORML 　人気度がN上昇した！ / 報酬として政府から$M入手した！ / FLAG:853 += N / MONEY += M`。"""
    st, out = ctx.state, ctx.out
    out.printl(f"　人気度が{pop}上昇した！")
    out.printl(f"　報酬として政府から${money}入手した！")
    st.flag[853] += pop
    st.money += money


def _failure_2(ctx: Ctx) -> None:
    """2:287–302。"""
    out = ctx.out
    out.printl(f"{_name(ctx)}が敗北したことで作戦は失敗し、学校は壊滅した。")
    out.printl("いかに特殊装備を身に付けた自衛隊といえども巨大触手の相手が務まるはずはなく、")
    out.printl("多数の生存者とともに女子高は汚染区域として放棄された……")
    out.printw()
    out.printl("　救出ミッションに失敗しました……")
    news_failure(ctx)


# --- 3 女性自衛官小隊救援 -------------------------------------------------------------------------


def _situation_3(ctx: Ctx) -> None:
    """3:4–15。"""
    out = ctx.out
    out.printl("自衛官専用の回線に、救援要請が発信されていた。")
    out.printl("女性だけの小隊が屋外で訓練していたところ、大型触手生物の襲撃を受けてしまったらしい。")
    out.printl("折悪く付近の部隊は小型触手と交戦中であり、誰も救援に応えることができない。")
    out.printl("目下交戦中とのことだが、大型触手が相手とあってはあまり長く保たないだろう。")
    out.printl(f"{_name(ctx)}が今すぐ駆け付ければ、どうにか彼女たちを救援できるかもしれない…")
    out.set_color(HOTPINK)
    out.printl("事態は一刻を争い、戦闘前に体勢を整える余裕もなさそうだが……")
    out.reset_color()
    out.printl()
    out.printl("危険を承知で助けに行くべきだろうか？")


def _exec_3(ctx: Ctx) -> RaidGen:
    """3:30–117。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name
    out.printl(f"現場に接近した{n(ctx)}が見たものは、")
    out.printl("いまにも陣形が崩れそうになっている女性自衛官の一個小隊と、")
    out.printl("獲物を弄ぶかのように執拗に迫る触手生物の姿だった。")
    out.printl()
    out.printl("見れば、隊員たちは逃げ遅れた一般人を庇いながら戦っている。")
    out.printl("自ら囮となり身を張って市民の盾となる彼女たちを嘲笑うように、")
    out.printl("触手生物は触手を鞭のようにしならせ打ち据えようとしている…！")
    out.printw()
    out.printl("どうする？")
    out.printl("　[0]正面から滑り込む　[1]触手の動きを見極める")
    out.printl()
    r = yield from _input((0, 1))  # :42–109
    if r == 0:
        if c.base[_b(ctx, "防御")] > 140 or c.base[_b(ctx, "攻撃")] > 200:
            out.printl("ガツン！")
            out.printl("鈍い音が響き渡り、咄嗟に身を竦めた女性隊員の一人が恐る恐る目を開けると……")
            out.printl(f"そこには触手の攻撃を正面から受け止める{n(ctx)}の姿があった！")
            out.printl(f"コンクリートをも砕く触手の一撃を受けて傷一つなく立つ{n(ctx)}の姿に、")
            out.printl("戦闘中である事も一瞬忘れて呆気にとられてしまったようだ。")
            out.printw()
            st.flag[853] += 2
            out.printl("　人気度が2上昇した！")
            out.printw()
            out.printl(f"{n(ctx)}が声を掛けると、茫然としていた隊員たちは我に返り、")
            out.printl("すぐさま退路を確保するべく行動を開始した。")
            out.printl("さすがはプロと言うべきか、立ち直りが早い。逃げ遅れた一般人は任せてもいいだろう。")
            out.printw()
            out.printl("さて、後は目の前のデカブツを片づけるだけだが…")
            out.printw()
        else:
            out.printl("グシャッ！")
            out.printl("鈍い音が響き渡り、咄嗟に身を竦めた女性隊員の一人が恐る恐る目を開けると、")
            out.printl(f"触手の攻撃に割り込み弾き飛ばされた{n(ctx)}の姿があった……")
            out.printl("狙われていた女性隊員は無事に庇えたものの、自身の防御までは間に合わなかったのだ。")
            out.printl(f"コンクリートをも砕く触手に薙ぎ倒された{n(ctx)}は、")
            out.printl("全身を襲う激痛に苦しみながらもふらつきよろめいて立ち上がる…")
            out.printw()
            local = div(c.base[0], 6) + st.rng.rand(300)  # :70–71
            c.base[0] = max(c.base[0] - local, 0)
            out.printl(f"　体力が{local}減少した！")
            out.printw()
            out.printl(f"{n(ctx)}が必死に呼吸を整えて声を掛けると、")
            out.printl("驚く隊員たちも我に返り、すぐさま退路を確保するべく行動を開始した。")
            out.printl("さすがはプロと言うべきか、立ち直りが早い。逃げ遅れた一般人は任せてもいいだろう。")
            out.printw()
            out.printl(f"さて、後は{n(ctx)}が目の前のデカブツを片づけられるかどうかだが…")
            out.printw()
    else:
        if c.base[_b(ctx, "知性")] >= 120:
            out.printl(f"{n(ctx)}は冷静に触手の動きを見極め、弱点と思しき箇所に遠距離攻撃を放った！")
            out.printl(f"{n(ctx)}の鋭い一撃は触手の付け根に直撃し、僅かに起動の逸れた触手が女性隊員の身体を掠めてゆく。")
            out.printw()
        else:
            out.printl(f"{n(ctx)}は触手の動きを見極め奇襲を掛けようとしたが、")
            out.printl(f"既に{n(ctx)}の気配を察知していたらしい触手が大量の白濁液で迎え撃つ。")
            out.printl(f"想定外の攻撃に{n(ctx)}は反応できず、腐敗臭の漂う汚液を全身に浴びてしまった！")
            out.printw()
            state_change_betobeto(ctx, 100)  # :93–95
            state_change_hairan(ctx, 25)
            cloth_battle_damage(ctx, 8)
            local = _sex_resist_down(ctx, 10, 10, 3)
            out.printl(f"　性耐性が{local}減少した！")
            out.printw()
        out.printl("驚く隊員たちも、救援が来た事を理解すると即座に退路を確保するべく行動を開始した。")
        out.printl("さすがはプロと言うべきか、立ち直りが早い。逃げ遅れた一般人は任せてもいいだろう。")
        out.printw()
        out.printl(f"さて、後は{n(ctx)}が触手に立ち向かうだけだが…")
        out.printw()
    out.printl()  # :110 PRINTFORML（空）
    out.printw()
    out.printl("（救援イベント中は撤退できません！　１５ターン耐えればミッション成功です！）")
    out.printw()
    out.drawline()
    _turn_limit(ctx, 15)
    add_battle_situation(st, "撤退不可,耐久戦,市民なし,レイプなし")
    return None


def _success_3(ctx: Ctx) -> None:
    """3:129–144。"""
    out = ctx.out
    n = _name(ctx)
    out.printl(f"{n}の活躍により、女性自衛官の小隊を助け出すことができた。")
    out.printl(f"小隊の誰にも余裕は無く、あと少し{n}の助けが遅ければ全滅していたに違いない。")
    out.printw()
    out.printl(f"女性自衛官たちは{n}に向かって全員で敬礼をすると、気丈にも周辺の被害を調べ始めた。")
    out.printl(f"見ればそのほとんどが年若き新入隊員であったらしく、中には{n}と同年齢の少女も混じっていた。")
    out.printl(f"{n}は救援が間一髪で間に合った事実を改めて噛み締め安堵する。")
    out.printl("彼女たちもまた国の護りを担う若き花であり、触手などに摘み取らせてしまうわけにはいかないのだ……")
    out.printw()
    _reward(ctx, 3, 5000)
    news_success(ctx)


def _failure_3(ctx: Ctx) -> None:
    """3:147–165。"""
    out = ctx.out
    n = _name(ctx)
    out.printl(f"{n}が敗北したことで作戦は失敗し、女性自衛官の小隊は壊滅した。")
    out.printl("若き女性隊員らは最早成すすべもなく、一人一人念入りに触手に絡め取られて締め上げられ、")
    out.printl(f"意識を失った{n}と共にそのまま何処かへと連れ去られてしまった……")
    out.printw()
    out.printl("彼女らは終わりの見えない幽閉の中で倒すべき敵の子種を幾度も注がれ、孕まされてしまうのだろう。")
    out.printl("訓練を受けた隊員といえど、女性に巨大触手の相手など務まるはずもなかったのかもしれない……")
    out.printw()
    out.printl("　救出ミッションに失敗しました……")
    news_failure(ctx)


# --- 4 攫われた女性 -------------------------------------------------------------------------------


def _situation_4(ctx: Ctx) -> None:
    """4:4–12。"""
    out = ctx.out
    out.printl("つい先ほど起きた襲撃事件後に逃走した大型触手生物が、もう間もなく近くを通過するらしい。")
    out.printl("女性数名が連れ去られたとのことで、救出の依頼が来ている。")
    out.printl("付近の部隊が急行しているものの、このままでは逃亡速度に間に合わないようだ。")
    out.set_color(HOTPINK)
    out.printl("今すぐ仕留めに向かわない限り、女性たちの行方を追うのは絶望的となるだろう……")
    out.reset_color()
    out.printl()
    out.printl("危険を承知で助けに行くべきだろうか？")


def _exec_4(ctx: Ctx) -> RaidGen:
    """4:27–45。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    out.printl(f"現場に辿り着いた{n}の前に触手生物が現れた。")
    out.printl("ズルズルと気味の悪い粘液を引きながら、捕らえた女性たちを何処かへと連れ去ろうとしていたようだ。")
    out.printl(f"漂う臭気に思わず身震いした{n}の気配を察知したのか、")
    if is_girly(ctx):
        out.printl("新たな獲物を見つけたと言わんばかりに何本もの太い触手が蠢き始める。")
    else:
        out.printl("邪魔をするなと言わんばかりに触手を向けて威嚇を始める。")
    out.printl()
    out.printl(f"一度姿を消した触手の行方を追うのは{n}であっても難しいだろう。")
    out.printl("何としてもこの場で決着を付けなければ……")
    out.printw()
    out.printl("（追撃イベントは規定ターン以内に触手生物を撃破する必要があります！）")
    out.printw()
    out.drawline()
    _turn_limit(ctx, 40)
    add_battle_situation(st, "撤退不可,追撃戦,市民なし,レイプなし")
    return None
    yield  # pragma: no cover（ジェネレータにする）


def _success_4(ctx: Ctx) -> None:
    """4:51–71。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    out.printl(f"{n}の活躍により、攫われた女性たちを助け出すことができた。")
    out.printl("衣服は溶かされ粘液に塗れているが、幸い意識を失っているだけで命に別状はなさそうだ。")
    out.printl(f"安藤を覚える一方で、か弱い女性を狙う触手の卑劣さに憤りも隠せない{n}。")
    out.printw()
    if st.temp.tcreport[5] and is_girly(ctx):  # :58 TCREPORT:TCR内装耐久零（REPORT.ERH:9）
        out.printl(f"{n}まで被害女性の一人に間違われるハプニングこそあったものの、")
    out.printl("遅れて駆け付けた救急隊は被害女性を手早く救急車で搬送し、周囲の市民を避難誘導してゆく。")
    out.printl("必要な「治療」は媚毒粘液の拭き取りから淫気の除去、膣内の応急処置まで多岐に渡る事だろう。")
    out.printl(f"{n}が手助けを試みようにも、素人ではかえって邪魔になりそうだ。")
    out.printl(f"その場は専門チームの仕事に任せ、{n}は後を託して去る事にした……")
    out.printw()
    _reward(ctx, 3, 5000)
    news_success(ctx)


def _checker_4(ctx: Ctx) -> int:
    """4:73–80：勝った場合のみ達成。"""
    return 0 if ctx.state.tflag[98] != 1 else 1


def _failure_4(ctx: Ctx) -> None:
    """4:82–99。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    if st.tflag[98] != 2:
        out.printl(f"{n}が触手を仕留めきれなかった事で作戦は失敗し、")
        out.printl("攫われた被害者の行方も分からなくなってしまった。")
    else:
        out.printl(f"{n}が敗北したことで作戦は失敗し、攫われた被害者の行方も分からなくなってしまった。")
    out.printl("衣服の切れ端や僅かな装飾品だけを遺留品として、女性たちは姿を消してしまったのだ。")
    out.printl("……行方こそ知れずとも、彼女たちを待ち受ける運命は分かり切っている。")
    out.printl()
    out.printl("陽の届かぬ薄暗い肉の洞窟で、今日も新たな苗床たちが悲痛な嬌声を上げていた……")
    out.printw()
    out.printl("　追撃ミッションに失敗しました……")
    news_failure(ctx)


# --- 5 触手洞窟 -----------------------------------------------------------------------------------


def _situation_5(ctx: Ctx) -> None:
    """5:8–17。"""
    out = ctx.out
    out.printl("近くの区域で突如として地面が陥没し、大規模な触手の巣が出現したらしい。")
    out.printl("集団下校中の女子生徒らが湧き出した触手に連れ去られ、巣の奥へと連れ去られてしまったようだ。")
    out.printl("緊急出動した特殊部隊も溢れた触手の対処に手一杯で、触巣内部まで突入する余裕がない。")
    out.printl(f"{_name(ctx)}が今すぐ先行して助けに行かなければ、攫われた少女たちは犠牲になるだろう。")
    out.set_color(HOTPINK)
    out.printl("触巣深部では通信が阻害されてしまうため、満足な支援は望めないが……")
    out.reset_color()
    out.printl()
    out.printl("それでも危険を承知で助けに行くべきだろうか？")


_BOSS_LINE = ("おそらくコイツが親玉……今回の事件の元凶だろう。", "邪悪な怪物の首魁を前に、{n}は戦闘態勢を取った！")
_NO_RETREAT_5 = "（救出イベント中は撤退できません！　増援の到着まで持ちこたえる必要があります！）"


def _cave_after_hit(ctx: Ctx) -> None:
    """5:159–184 ほか：体力の残りでデバフ（拘束／挿入）を決める。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name(ctx)
    if c.base[0] > div(c.maxbase[0] * 70, 100):
        out.printl(_BOSS_LINE[0])
        out.printl(_BOSS_LINE[1].format(n=n))
        out.printw()
        tail = ""
    elif c.base[0] > div(c.maxbase[0] * 50, 100):
        out.printl(f"{n}は激しい打撃を受けて意識を失ってしまった。")
        out.printl("新たな「獲物」に気付いた周囲の触手が、無防備な身体に殺到する……。")
        out.printw()
        tail = ",強制拘束"
    else:
        out.printl(f"{n}は強い衝撃によって昏倒し、")
        out.printl("そのまま無数の触手にがっちりと拘束されてしまった。")
        out.printl("そして我に返った時には、もう――")
        out.printw()
        tail = ",強制挿入"
    out.printl(_NO_RETREAT_5)
    out.printw()
    out.drawline()
    add_battle_situation(st, "撤退不可,支援無効,耐久戦,市民なし,レイプなし" + tail)


def _cave_hit(ctx: Ctx, first: str) -> None:
    """5:153–157 ほか：`LOCAL = MAX(BASE:体力 / 10, 10) + RAND(300, 400)` の打撃。first は直前の文（防御／回避の失敗）。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    local = max(div(c.base[0], 10), 10) + st.rng.rand(100) + 300
    c.base[0] = max(c.base[0] - local, 0)
    out.printl(f"体力が{local}減少した！")
    out.printw()
    _cave_after_hit(ctx)


def _cave_ok(ctx: Ctx, first: str) -> None:
    """5:187–193 ほか：攻撃を防いだ／回避した。"""
    out = ctx.out
    n = _name(ctx)
    out.printl(first)
    out.printl()
    out.printl(_BOSS_LINE[0])
    out.printl(_BOSS_LINE[1].format(n=n))
    out.printw()
    out.drawline()
    add_battle_situation(ctx.state, "撤退不可,支援無効,耐久戦,市民なし,レイプなし")


def _cave_guard_fail(ctx: Ctx) -> None:
    """5:203–208 ほか：防御態勢を整えたが防ぎきれない。"""
    out = ctx.out
    n = _name(ctx)
    out.printl(f"{n}は素早く防御態勢を整えたが、")
    out.printl("超重量級のプレス攻撃を防ぎきれない！")
    out.printl(f"{n}は鈍い打撃音と共に打ち倒され、地面を何度も転がった…")


def _cave_bound(ctx: Ctx) -> None:
    """5:305–322／:351–368：知性不足・誤入力 → 拘束・服を溶かされる。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name(ctx)
    out.printl(f"狼狽える{n}には反応する時間がなかった……")
    out.printl("暗闇から伸びてきた触手に四肢を絡め取られ、がっちりと拘束されてしまった！")
    if st.flag[111] == 0:
        out.printl("ぬるぬるした触手はべとついた粘液を分泌し、")
        if c.cflag[40] != -1 or c.cflag[41] != -1 or c.cflag[42] != -1:
            out.printl(f"{n}の服を溶かしてしまった！")
        out.printl("ゲル状の粘液に染まった肌が紅潮してゆく…。")
        local = _sex_resist_down(ctx, 10, 10, 30, 15)  # RAND(15, 30)
        out.printl(f"性耐性が{local}減少した！")
        out.printl()
        out.printl(f"触手に拘束されてもがく{n}の前に、超重量級の触手生物が姿を現した……！")
    out.printw()
    out.printl(_NO_RETREAT_5)
    out.printw()
    out.drawline()
    add_battle_situation(st, "撤退不可,支援無効,市民なし,レイプなし,強制全裸,強制発情,強制拘束")


def _exec_5(ctx: Ctx) -> RaidGen:
    """5:32–380。"""
    from .battle.func import state_change_betobeto as betobeto

    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name
    out.printl(f"触手生物が這いずった粘液の痕だけを頼りに、アリの巣よりも複雑に枝分かれする触巣を潜る{n(ctx)}。")
    out.printl("粘液は時間が経てば揮発し、手掛かりとして機能しなくなるばかりか媚毒ガスとして追加の被害をもたらす。")
    out.printl("…地上は完全な混戦状態で、特殊部隊をもってしても制圧には時間が掛かりそうだった。")
    out.printl(f"単身突入する{n(ctx)}の背後で増援を誓った彼らだったが、おそらく揮発には間に合わないだろう。")
    out.printw()
    out.printl("触巣に進入してしばらくすると、外部との通信も途切れてしまった。")
    out.printl(f"今の{n(ctx)}は完全な孤立無援であり、もしも敗けて捕獲されれば救助など到底望めない…")
    out.printl("陽光の届かない巣の内部は想像以上に深く、触手被害女性の侵蝕された膣道を思わせる不気味な肉壁に覆われていた。")
    out.printl("ぐねぐねと蠢く無数の触手が繊毛のように肉の床や壁面を覆い、一瞬でも油断すれば足を取られてしまいそうだ。")
    out.printw()
    out.printl(f"不気味に発光する触手が照らす薄暗い洞窟を{n(ctx)}が警戒しながら進むうち、")
    out.printl("脈動する壁や床から漏れ出す悪臭が次第に強まってきた。")
    out.printl("やがて触手の蠢動や精液の汚臭に混じり、洞窟の奥から女性の悲鳴らしき声が複数聞こえ始める。")
    out.printl("それらが攫われた女生徒たちの声であるなら、残された時間はあまり多くないようだが……")
    out.printw()
    out.printl("どうする？")
    out.printl("　[0]突入速度を優先する　[1]警戒を解かず慎重に進む")
    out.printl()
    r = yield from _input((0, 1))  # :54–94
    if r == 0:
        out.printl("……悲鳴が嬌声へ変わる前に、攫われた少女たちに追い付かなければ。")
        out.printl(f"そう判断した{n(ctx)}は、本来守るべき警戒を多少犠牲にして突入速度を早めた。")
        out.printw()
        if c.base[_b(ctx, "知性")] + c.base[_b(ctx, "敏捷")] >= 300:
            out.printl(f"足元から伸びてきた触手を{n(ctx)}が素早く薙ぎ払うと、触手はドロリと溶けて細切れになった。")
            if is_male(ctx.data, c):  # ISMALE()
                out.printl("十分に予想できた罠とはいえ、洞窟への侵入者を無事に進ませる気はないようだ。")
            else:
                out.printl("十分に予想できた罠とはいえ、洞窟に入り込んだ女性を無事に進ませる気はないようだ。")
            out.printl()
        else:
            out.printl("…焦りが原因だろうか、足元から伸びる触手に反応できず、絡みつかれて転倒してしまった！")
            out.printl(f"触手が{n(ctx)}の胸や腰を撫でまわし、股間にも伸びて先端を擦りつけてくる。")
            out.printl(f"何とか触手を振り解き立ち上がる頃には、{n(ctx)}は全身を粘液まみれにされてしまっていた……")
            out.printl()
            local = _sex_resist_down(ctx, 10, 10, 3)
            out.printl(f"　性耐性が{local}減少した！")
            betobeto(ctx, 100)
            out.printl()
        _turn_limit(ctx, 20)
    else:
        out.printl("……焦りのせいで全員の救出に失敗してしまえば元も子もない。")
        out.printl(f"{n(ctx)}は警戒を怠らずに奥へと進んでいく……")
        out.printw()
        _turn_limit(ctx, 25)
    out.printl()  # :95
    out.printl(f"…触巣洞窟の最深部へ辿り着いた{n(ctx)}の前に、大きく開けた空洞が広がった。")
    out.printl("床には道中と比べ物にならないほど長い触手が粘液を噴き散らしながらひしめき、")
    out.printl("地形本来の凹凸さえ明瞭には判別できない。")
    out.printl()
    out.printl("触巣道中を侵蝕された膣に喩えるなら、最深部たる空洞は汚染された子宮なのだろう。")
    out.printl("そして、卵巣や受精卵に相当する存在は――。")
    out.printw()
    out.printl(f"{n(ctx)}の眼前で愛液と母乳を漏らす無数の繁殖袋は、被害女性の成れの果てだった。")
    out.printl("触手に攫われた女性は凌辱されるだけに留まらず、最後にはその手足を触手に取り込まれ…")
    out.printl("終わらぬ強制絶頂と出産の快楽に溺れる中で、全身を繁殖に適した苗床へと造り替えられてしまう。")
    out.printl("肉壁に半ば同化され、あるいは触手に穴を貫かれて天井に釣り下がる大勢の「元・女性」こそが、")
    out.printl("時には痙攣し、時には絶頂しながらボテ腹を揺らす、哀れな触手の花嫁たちだった。")
    out.printw()
    out.printl("犠牲者の乳房や下腹部は不自然なほど肥大化し、もはや救出されたところで日常に戻れる身体ではない。")
    out.printl("漏れ出る喘ぎ声にも最早女性としての意思は含まれず、雌の器官が快楽に捧げる原始的な反射に過ぎない。")
    out.printl("彼女ら繁殖袋は既に触巣の一部分であり、手遅れであり、ヒトとしての尊厳や意識すら残っているか定かでない。")
    out.printl("そして今回地上へ湧き出てきた無数の触手も、おそらくは目の前の繁殖袋たちが産み落としたのだ……")
    out.printw()
    out.printl(f"攫われた少女らの姿はどこにも見当たらない。間に合わなかったかと{n(ctx)}が唇を噛んだ次の瞬間、")
    out.printl("床に倒れ伏し触手に半ば埋もれた状態で、肉壁に向かって引きずられつつある少女たちの姿を視界に捉えた！")
    # :117 PRINT（空）：何も出さない
    out.printl("一度気付いてしまえば、空洞内の随所に倒れた女生徒とおぼしき少女の姿を確認できた。")
    out.printl("少女らは蠢く床の小型触手に絡め取られ、一人残らず意識を失っているようだ。")
    out.printl("服は大半溶かされて素肌を晒しており、既に凌辱されてしまった可能性もあるが…今ならまだ助け出せる。")
    out.printw()
    out.printl(f"{n(ctx)}が意を決して空洞の中心まで踏み込むと、")
    out.printl()  # :128 PRINTFORML（空）
    if st.flag[111] == 0:  # :129–133
        out.printl("突然どこからともなく笛のような鋭い音が聞こえてきた。")
    out.printl(f"{n(ctx)}は咄嗟に――")
    out.printl("　[0]周囲を見回す　[1]頭上を見上げる　[2]足を止める")
    if c.base[_b(ctx, "知性")] > 600:
        out.print("　[7]後ずさる")
    if c.base[_b(ctx, "防御")] > 600:
        out.print("　[8]防御を固める")
    if c.base[_b(ctx, "敏捷")] > 600:
        out.print("　[9]前方に跳ねる")
    out.printl()
    r = yield  # :143 INPUT（:145 SELECTCASE：CASEELSE があるので何でも受け付ける）
    boss_appear = "頭上から超重量の物体が躍り出てきた。"
    rush = f"凶暴な触手を伸ばし、猛烈な勢いで{n(ctx)}に襲い掛かる！"
    if r == 0:  # :146–195
        if st.flag[111] == 0:
            out.printl(boss_appear)
            out.printl(rush)
            if c.base[_b(ctx, "敏捷")] < 500:
                out.printl(f"回避できなかった{n(ctx)}は強力な打撃を受けてしまった……")
                _cave_hit(ctx, "")
            else:
                _cave_ok(ctx, f"{n(ctx)} は巧みに攻撃を回避した！")
    elif r == 1:  # :196–247
        if st.flag[111] == 0:
            out.printl(boss_appear)
            out.printl(rush)
            if c.base[_b(ctx, "防御")] < 200:
                _cave_guard_fail(ctx)
                _cave_hit(ctx, "")
            else:
                _cave_ok(ctx, f"{n(ctx)}は攻撃をどうにか防ぎきった！")
    elif r == 2:  # :249–323
        if c.base[_b(ctx, "知性")] > 600:
            if st.flag[111] == 0:
                out.printl(boss_appear)
                out.printl(rush)
                if c.base[_b(ctx, "防御")] < 600:
                    _cave_guard_fail(ctx)
                    _cave_hit(ctx, "")
                else:
                    _cave_ok(ctx, f"{n(ctx)}は攻撃をどうにか防ぎきった！")
        else:
            _cave_bound(ctx)
    elif r in (7, 8, 9):  # :327–346（表示の有無に関わらず受け付ける：原作どおり）
        if st.flag[111] == 0:
            out.printl("頭上から何か超重い物体が飛び出してきた。")
            if r == 8:
                out.printl(f"伸ばされた猛々しい触手が、守りを固めた{n(ctx)}と衝突する！")
                out.printl(f"……{n(ctx)}は突然の激しい攻撃を凌ぎきった！！")
            else:
                out.printl(rush)
                out.printl(f"……{n(ctx)}華麗に攻撃を回避した！！")
        out.printl(f"{n(ctx)}が奇襲攻撃の出所を見上げると、超重量級の触手生物が肉の地面へと落ちてきた。")
        out.printl(_BOSS_LINE[0])
        out.printl(_BOSS_LINE[1].format(n=n(ctx)))
        out.printw()
        out.printl(_NO_RETREAT_5)
        out.printw()
        out.drawline()
        add_battle_situation(st, "撤退不可,支援無効,市民なし,レイプなし")
    else:  # :350–368 CASEELSE（誤入力へのペナルティ）
        _cave_bound(ctx)
    return None


def _success_5(ctx: Ctx) -> None:
    """5:393–422。"""
    out = ctx.out
    n = _name(ctx)
    out.printl("「いたぞっ！」")
    out.printl(f"単身戦い続けていた{n}の後方から、唐突に人の叫び声が響く。")
    out.printl("声に続いて人工の光が幾筋も差し込み、薄暗い触巣深部を眩しいまでに照らし出した。")
    out.printl("雪崩れ込んできた特殊部隊が危険を顧みず触手の花畑へと飛び込み、攫われた少女たちを抱え上げてゆく。")
    out.printl("…どうやら彼らは予想以上の速度で地上の触手を片付けたらしい。")
    out.printl(f"驚きを隠せない{n}に隊長らしき女性が歩み寄ると、")
    out.printl(f"みな{n}の勇気ある姿に奮い立てられたのだ、と手短に伝えて救出作業に戻っていった。")
    out.printw()
    out.printl("…とはいえ、触巣深部から運び出せる被害者の人数には限界がある。")
    out.printl("救出に手間取り時間が経ってしまえば、巣は蠢いて道も変わる。脱出できる保証が無くなるのだ。")
    out.printl(f"特殊部隊と{n}が力を合わせても、気絶した女生徒らを運び出すのが精一杯で、")
    out.printl("最深部に囚われた「手遅れ」の苗床までは助けられなかった……")
    out.printw()
    out.printl()
    out.printl("触巣からの脱出成功後、緊急搬送先の病院で被害少女らの身体検査が行われた。")
    out.printl("不幸中の幸いと言うべきか、彼女たちの身体に別状はなかった。")
    out.printl("早期に失神したためだろうか？　懸念された性被害も繊毛触手の浅い挿入程度で済んでいたようだ。")
    out.printl(f"報告を受領した{n}は、我が事のように胸をなでおろす。")
    out.printl("被害に対する精神面のケアこそ必要なものの、最善の結果に収まったと言ってよいのだろう。")
    out.printl("なにより少女たちは触巣最深部のおぞましい光景を目にせず、その一部にもならずに済んだのだから……")
    out.printw()
    _reward(ctx, 5, 7000)
    news_success(ctx)


def _failure_5(ctx: Ctx) -> None:
    """5:425–469。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    out.printl(f"{n}が敗北したことで救出作戦は失敗した。")
    out.printl()
    out.printl("特殊部隊がようやく地上の掃討を終えつつあった頃、")
    out.printl("触巣の入り口から大量の媚毒ガスと共に新たな触手生物が湧き出してきた。")
    out.printl("疲弊していた特殊部隊の隊員らに媚毒の中で連戦する余力は無く…")
    out.printl("部隊は壊滅し、若い女性隊員にいたっては全員が触手に絡み付かれ、触巣の中へと引きずり込まれてしまった。")
    out.printl()
    out.printl("惨状に絶望する市民たちの前で、陥没した地面はブヨブヨした肉壁で覆われてゆき…")
    out.printl(f"攫われた女生徒と連れ去られた女性隊員、そして{n}を呑み込んだまま、ゆっくりと口を閉じていったのだった……")
    out.printw()
    out.printl("――――")
    out.printl("――")
    out.printl("触巣の最深部で、攫われた女生徒の一人が意識を取り戻した。")
    out.printl("噎せ返るほどの性臭に思わず鼻を塞ごうとしたが、不快な肉触手に埋まった四肢はぴくりとも動かせない。")
    ls = ("クラス委員長", "生徒会長", "風紀委員")[st.rng.rand(3)]  # :447–451 STRDATA LOCALS
    out.printl(f"{ls}の彼女は、気丈にも状況を確認しようと周囲を見回したが……目に映ったのは、")
    out.printw()
    out.printl("触手に膣を突き上げられるたびあられもなく嬌声を響かせる同級生の少女たち")
    out.printl("絶叫を伴って触手をひり出すヒトとも思えぬ苗床袋たち")
    out.printl(f"空洞の中心部で穴という穴を執拗に犯される生死すら不明な{n}")
    out.printl()
    out.printw("女にとっての地獄だった。")
    out.printl()
    out.printl("そして、少女自身の膣口にグロテスクな触手が突き付けられた瞬間…")
    out.printl(f"才色兼備にして聡明な{ls}であった優秀な彼女の子宮は、")
    out.printl("「目の前に広がる光景こそが自らに待ち受ける未来である」と、")
    out.printl("その優秀だった理性より素早く理解してしまったのだった……")
    out.printw()
    out.printl()
    out.printl("　救出ミッションに失敗しました……")
    news_failure(ctx)


# --- 3001 ボス触手の襲撃 --------------------------------------------------------------------------


_ATTACK_DAY = {
    102: "鍛錬を終えて街に出ていた",
    103: "息抜きがてらに街に出ていた",
    104: "特別活動を終えて帰り仕度していた",
    106: "戦闘支援を終えて街に出ていた",
    107: "情報収集を終えて帰り仕度していた",
    108: "自由行動を終えて帰り仕度していた",
}


def _haltu(ctx: Ctx) -> None:
    """`IF TALENT:主観視点 > 0 … はっとする。 ELSE … はっとした。`"""
    n = _name(ctx)
    if t(ctx, tc(ctx), "主観視点") > 0:
        ctx.out.printl(f"{n}は、突然響き渡った轟音にはっとする。")
    else:
        ctx.out.printl(f"{n}は、突然響き渡った轟音にはっとした。")


def _exec_3001(ctx: Ctx) -> RaidGen:
    """3001:3–42。"""
    st, out = ctx.state, ctx.out
    text = _ATTACK_DAY.get(tc(ctx).cflag[100])
    if text:
        out.print(text)
    _haltu(ctx)
    out.printl("サイレンが鳴り響き、街行く人々がぎょっとスピーカーの方を振りかえって数秒、")
    out.printl("すぐ近くで誰かの悲鳴が響き渡り、周囲はパニックの渦に巻き込まれた。")
    out.printl()
    out.wait()  # :26 FORCEWAIT
    out.printl("触手生物の襲撃。まさか、こんな街中にまで――")
    out.printl("そう思った次の瞬間、目の前のビルの壁が粉砕され、")
    out.printl("土煙りの中からソレは姿を現した。")
    out.printw()
    out.printl('――"人類の敵"、触手生物。')
    out.printl("触手に巻き取られた犠牲者の亡骸を無造作に放り投げ、")
    out.printl("逃げまどう人々の方へと突進し始める。")
    out.printw()
    out.printl(f"それを見た{_name(ctx)}は、咄嗟に駆け出していた――")
    out.printl()
    out.printl("（襲撃イベント中は撤退できません！　何とか１５ターン耐えてください！）")
    out.printw()
    out.drawline()
    _turn_limit(ctx, 15)
    add_battle_situation(st, "撤退不可,支援無効,市民確定,レイプなし,耐久戦")
    return None
    yield  # pragma: no cover


# --- 3002 ボス触手の夜襲 --------------------------------------------------------------------------


def _exec_3002(ctx: Ctx) -> RaidGen:
    """3002:3–124。繁殖袋・四肢欠損は戦闘なしで拉致（:9–56 → BEGIN TURNEND）。"""
    st, out, data = ctx.state, ctx.out, ctx.data
    c = tc(ctx)
    n = _name
    if t(ctx, c, "繁殖袋") > 0 or t(ctx, c, "四肢欠損") > 0:  # :9–56
        if t(ctx, c, "繁殖袋") > 0:
            out.printl(f"{n(ctx)}は部屋で意識を失ったまま横たわり、突然の大音響に対して何の反応も示さない。")
        else:
            out.printl(f"部屋の中で力なく横たわっていた{n(ctx)}は、突然の大音響に驚く。")
        out.printl(f"遅れて響き渡る警報音。急いで装備を整えようとする{n(ctx)}をさらなる衝撃が襲い、")
        out.printl("電線がショートする火花とともに一瞬照明が落ち、非常灯に切り替わる。")
        out.wait()  # :17 FORCEWAIT
        if t(ctx, c, "繁殖袋") < 1:
            out.print("異変に気付く事も無い")
        else:
            out.print("ベッドから動けない")
        out.print(f"{n(ctx)}に")
        safe = charanum_safe(st)
        if safe == 1:
            out.print("外の世界に警告する方法はなく、助けが来る気配もない。")  # :25 PRINTFORM（改行なし：原作どおり）
        else:
            out.printl(f"外の世界に警告する方法はなく、ただ仲間{'達' if safe >= 3 else ''}を待つことしかできない。")
        out.printl(f"次の瞬間、{n(ctx)}のすぐ傍で壁が崩落し――")
        out.printw()
        out.printl("――ヌ　メ　リ")
        out.print("という音と共に現れた触手")
        if t(ctx, c, "繁殖袋") == 0:
            out.print(f"に、{n(ctx)}の顔から血の気が引いていく…")
        out.printl()
        out.printl('それは――"人類の敵"、触手生物。')
        out.printl("その巨体がズズンと地響きを起こしながら、目の前の闇から姿を現そうとしている！")
        out.printl("光の届かない暗闇から、その巨体が轟音を立てて現れた！")
        out.printw()
        out.printl("抵抗など不可能だった。")
        out.printl(f"動けない{n(ctx)}の身体は無数の触手に捕らえられ、ズルズルと虚空へ引き込まれてゆく。")
        out.printl("彼女を待ち受ける未来は、間違いなく触手の繁殖袋としての運命だろう……")
        out.printl()
        out.set_color((150, 0, 0))
        out.set_bold(True)
        out.printl(f"{n(ctx)}は触手生物に拉致されました")
        out.set_bold(False)
        out.reset_color()
        c.cflag[0] = 9  # :50
        c.talent[data.index_of("TALENT", "苗床化")] = 1  # :52
        c.exp[data.index_of("EXP", "幽閉経験")] += 1  # :54
        return Step.TURNEND  # :55 BEGIN TURNEND
    text = {
        102: "鍛錬を終えたばかりの",
        103: "自室に居た",
        104: "特別活動を終えて戻った",
        106: "戦闘支援を行っていた",
        107: "情報収集を終えて戻った",
        108: "自由行動を終えて戻った",
    }.get(c.cflag[100])  # :59–71
    if text:
        out.print(text)
    if c.cflag[100] == 106:  # :72–73
        c.cflag[100] = 103
    _haltu(ctx)
    out.printl(f"遅れて響き渡る警報音。急いで装備を整えようとする{n(ctx)}をさらなる衝撃が襲い、")
    out.printl("電線がショートする火花とともに一瞬照明が落ち、非常灯に切り替わる。")
    out.printl()
    out.wait()  # :84 FORCEWAIT
    safe = charanum_safe(st)
    if safe == 1:
        out.printl("このままでは危ない、何とか外部と連絡を取らなければ…！")
    else:
        out.print("このままでは危ない、何とか仲間")
        if charanum_safe(st) >= 3:
            out.print("たち")
        out.printl("と連絡を取らなければ…！")
    out.printl(f"そう思って{n(ctx)}が立ち上がったそのとき！")
    out.printl("すぐ傍で壁が崩落し――")
    out.printw()
    out.printl("――ヌ　メ　リ")
    out.printl(f"という音と共に現れた触手に、{n(ctx)}の顔から血の気が引いていく…")
    out.printl('見間違えるはずもない――"人類の敵"、触手生物。')
    out.printl("その巨体がズズンと地響きを起こしながら、目の前の闇から姿を現そうとしている！")
    out.printw()
    out.printl("突然の襲来に驚き戸惑いながらも、")
    out.printl(f"{n(ctx)}は咄嗟に距離を取って触手の一撃を避わした。")
    out.printl("――まさか自分を狙ってきたのだろうか？")
    out.printw()
    if charanum_safe(st) == 1:  # :105–115
        out.printl("頼れる相手は他に居らず、逃げようにも退路は塞がれている。")
        out.printl("もし自分がここで捕まってしまったら――")
    elif charanum_safe(st) - st.flag[41] < 2:
        out.printl("仲間は出払っていて、今この場で対応できるのは自分しか居ない。")
        out.printl("もし皆が戻ってくる前に捕まってしまったら――")
    else:
        out.printl("仲間が駆けつけてくるまで、何とか時間を稼ぐしかない。")
        out.printl("いや、もしも皆が既に捕まっていたら――")
    out.printl()
    out.printl("（襲撃イベント中は撤退できません！　何とか閉所で１５ターン耐えてください！）")
    out.printw()
    out.drawline()
    _turn_limit(ctx, 15)
    c.tcvarn[0] = 1  # :123 近距離スタート
    add_battle_situation(st, "撤退不可,空中不可,遠距離不可,支援無効,市民なし,レイプなし,耐久戦")
    return None
    yield  # pragma: no cover


# --- 3003 ライブ奇襲 -----------------------------------------------------------------------------


def _exec_3003(ctx: Ctx) -> RaidGen:
    """3003:3–52。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name
    # :6 現在のアウターを「ステージ衣装」（105）に一時設定
    event_battle_set_costume(ctx, st.target, 105 if c.cflag[1] == 0 else -1, 105 if c.cflag[1] > 0 else -1, -1, -1)
    out.print("公演を締め括る挨拶を舞台上で始めていた")
    if c.cflag[100] == 106:  # :10–11
        c.cflag[100] = 103
    _haltu(ctx)
    out.printl(f"事態を掴みかねる{n(ctx)}をさらなる揺れと衝撃が襲う。")
    out.printl("壁が不自然にひしゃげ始め、観客席から悲鳴が上がる。")
    out.printl()
    out.wait()  # :22 FORCEWAIT
    out.printl("このままでは危険だ、まず観客たちの安全を確保しなければ…！")
    out.printl(f"避難誘導のために{n(ctx)}が声を張り上げようとした、その瞬間！")
    out.printl("すぐ傍で床が陥没し――")
    out.printw()
    out.printl("――ヌ　メ　リ")
    out.printl(f"という音と共に現れた触手に、{n(ctx)}の顔から血の気が引いていく…")
    out.printl('見間違えるはずもない――"人類の敵"、触手生物。')
    out.printl("巨体がズズンと地響きを起こしながら、足元の闇から姿を現そうとしている！")
    out.printw()
    out.printl(f"表情を強張らせた{n(ctx)}の周囲で、ボコリ、ボコリとステージを取り囲むように生え揃う触手。")
    out.printl("触手生物の狙いは若い女性、ここはライブ会場、その中心にいる獲物といえば……！")
    out.printl(f"事の深刻さを察した{n(ctx)}は咄嗟に飛び退き距離を作るが、")
    out.printl("臨戦態勢を取る寸前で自身の置かれた状況に思い至ってしまった。")
    out.printw()
    tn = print_transname(st, st.target)
    out.printl(f"……この瞬間、{n(ctx)}は群衆に紛れた一人の市民ではない。")
    out.printl(f"衆目集まるアイドル「{tn}」として、舞台の上に立っている。")
    out.printl("悲鳴と混乱の中でステージに向けられる観客たちの目、")
    out.printl(f"{tn}の全身を余すところなく捉える何台もの撮影用カメラ……")
    out.printw()
    out.printl("観客の安全は最優先だが、もしもここで「戦って」しまえば正体は隠せない。")
    out.printl(f"だとすれば、{n(ctx)}が選べる唯一の選択肢は――")
    out.printl()
    out.set_color(HOTPINK)
    out.printl("（観客の前では正体を明かせません！　避難誘導完了までアイドルとして囮になってください！）")
    out.reset_color()
    out.printw()
    out.drawline()
    _turn_limit(ctx, 30)
    add_battle_situation(st, "先制無し,支援無効,身バレ不可,常時撮影,市民確定,レイプなし,耐久戦,")
    return None
    yield  # pragma: no cover


def _turnend_3003(ctx: Ctx) -> None:
    """3003:56–72：7 ターン目以降で拘束されていなければ避難完了。"""
    st, out = ctx.state, ctx.out
    if st.tflag[0] >= 7 and tc(ctx).tcvarn[0] != 0:
        out.set_color(RED)
        out.set_bold(True)
        if st.flag[70] > 0:
            out.printl("スタッフの懸命な誘導で、逃げ遅れていた観衆の避難が完了したようだ！")
            st.flag[70] = 0
        if st.flag[71] > 0:
            out.printl("スタッフに無理矢理引きずられ、残った「観衆」の「避難」が完了したようだ…")
            st.flag[71] = 0
        out.reset_color()
        out.set_bold(False)
        out.wait()  # FORCEWAIT


def _checker_idol(ctx: Ctx) -> int:
    """3003:75–83／3004:205–214：
    `IF TFLAG:98 == 2 || (TFLAG:98 == 0 && (TFLAG:21 & 3) || (TFLAG:21 & 4) || (TFLAG:21 & 5) || (TFLAG:21 & 6))`。
    括弧内は独立した部分式（reference/emuera-1824/Emuera/GameData/Expression/ExpressionParser.cs:404–414）、その中は
    `&&`／`||` 同優先度・左結合（OperatorCode.cs:33–34）なので `98==2 || ((((98==0 && 21&3) || 21&4) || 21&5) || 21&6)`
    → 敗北は常に「失敗」（S26b 修正：S20 は外側の括弧を無視して「凌辱されずに敗北すると達成」としていた）。"""
    st = ctx.state
    t98, t21 = st.tflag[98], st.tflag[21]
    inner = (t98 == 0 and (t21 & 3)) or (t21 & 4) or (t21 & 5) or (t21 & 6)
    return 0 if (t98 == 2 or inner) else 1


def _success_3003(ctx: Ctx) -> None:
    """3003:85–116。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    tcn = print_transcallname(st, st.target)
    if st.tflag[98] == 1:
        out.printl(f"観客のいないステージで、{n}は触手生物と戦っていた。")
        out.printl("先程までは無力な囮だったが、今なら全力で立ち向かえる……")
        out.printl("のたうつ触手を踊るように躱し、的確に急所へと攻撃を叩き込む。")
        out.printl("やがて触手生物に決定的な一撃が入ったのか、どさりと音を立てて倒れ込み、そのまま沈黙した。")
        out.printl()
        out.printl(f"{n}が注意深く確かめようとした時、イベントスタッフたちの慌てた声や足音が触手越しに聞こえてきた。")
        out.printl(f"どうやら「{tcn}」の安否を確かめに戻ってきたようだ。")
        out.printl()
        out.printl(f"{n}はくるりと向き直り、アイドルとして精一杯のにこやかな笑顔を振り撒いた……")
    else:
        out.printl("時間を稼いだ甲斐あって、スタッフによる避難誘導が無事に完了したようだ。")
        out.printl(f"もう観客の視線はない！　{n}は触手に向き直る。")
        out.printl("先程までは無力な囮だったが、今なら全力で立ち向かえる……")
        out.printl(f"本来の実力で戦闘態勢に入り、素早く身構える{n}。")
        out.printl("すると触手生物は異変を察知したのか、巨体に見合わぬ速度で元来た穴へ潜り込み始めた……")
        out.printl()
        out.printl("追うべきか、体制を整えるべきか。")
        out.printl(f"{n}が逡巡していると、イベントスタッフたちの慌てた声や足音が会場に響いた。")
        out.printl(f"「{tcn}」の安否を確かめに戻ってきたようだが、こうなると追撃は難しい。")
        out.printl("……幸いこの場の人的被害は抑えられた、今は他にもすべき事がある。")
        out.printl(f"{n}はくるりと向き直り、アイドルとして精一杯のにこやかな笑顔を振り撒いた……")
    out.printw()
    out.printl("　無事に被害を最小限に抑えました！")
    news_success(ctx)


def _failure_3003(ctx: Ctx) -> None:
    """3003:118–158。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    t21 = st.tflag[21]
    if st.tflag[98] != 2:
        out.printl(f"{n}が嬲られている間に、かろうじて観客の避難誘導が完了したようだ。")
        out.printl(f"既に満身創痍の{n}だが、それでも触手に立ち向うため最後の力を振り絞り……")
        out.printl()
        out.printl("……と、獲物の意外な抵抗を警戒したのだろうか？")
        out.printl(f"触手生物は{n}に向けていた全ての触手をシュルシュルと引っ込め、")
        out.printw("巨体に見合わぬ速度で元来た穴へ滑り込んでゆく。")
        out.printl("・・・")
        out.printl(f"瓦礫まみれのイベントステージに取り残され、呆然とへたり込む{n}。")
        if t21 & 4:
            out.print("ドロリと膣から垂れてきた触手精液の感触")
        elif t21 & 5:
            out.print("ドロリと尻から垂れてきた触手精液の感触")
        elif t21 & 6:
            out.print("触手精液でベトついたボロボロの衣装")
        elif t21 & 3:
            out.print("ボタボタと垂れる触手体液の音")
        out.printl("で正気に返ると、")
        out.printl(f"アイドル「{print_transname(st, st.target)}」が永遠に穢されてしまった事実を理解し、声も無くさめざめと泣いた……")
        out.printw()
        out.printl("　避難ミッションは成功しましたが、アイドルとしては嬲り尽くされてしまいました……")
    else:
        out.printl(f"{n}が力尽きたことで会場は大混乱に陥った。")
        out.printl(f"触手生物は意識を失った{n}をトロフィーのように掲げると、")
        out.printl("まるで撮影用カメラへ見せつけるように大量射精を繰り返す。")
        if st.flag[70] > 0:
            out.print("穴から湧き出した無数の触手生物が逃げ遅れた女性客を襲い始める中、")
        out.printl(f"蠢く触手が白濁に染まった{n}を悠々と絡め取り、用は済んだとばかりに大穴へ姿を消した……")
        out.printw()
        out.printl("　避難ミッションに失敗しました……")
    news_failure(ctx)


# --- 3004 プール奇襲 -----------------------------------------------------------------------------


def _pool_shower(ctx: Ctx, d: int, floor: int) -> None:
    """3004:301–307／:348–354：べとべと・排卵 35%・衣装ダメージ 8・性耐性 MAX(/d, floor) + RAND:3 減少。"""
    out = ctx.out
    state_change_betobeto(ctx, 100)
    state_change_hairan(ctx, 35)
    cloth_battle_damage(ctx, 8)
    local = _sex_resist_down(ctx, d, floor, 3)
    out.printl(f"　性耐性が{local}減少した！")
    out.printl()


def _exec_3004(ctx: Ctx) -> RaidGen:
    """3004:256–336。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    n = _name
    out.print("そろそろ帰ろうと思いつつナイトプールの中央で浮き輪に揺られる")
    if c.cflag[100] == 106:  # :260–261
        c.cflag[100] = 103
    _haltu(ctx)
    out.printl("激しい揺れと共に施設内の照明が落ち、怯えた声色の囁き声が飛び交う。")
    out.printl()
    out.wait()  # :271 FORCEWAIT
    out.printl("何が起きているのか、まず周囲の状況を把握しなければ…！")
    out.printl(f"{n(ctx)}が咄嗟に身構えた、その瞬間！")
    out.printl("金属のへしゃげるような音と共に天井が歪み――")
    out.printw()
    out.printl("――ベ　タ　リ")
    out.printl(f"という音と共に現れた触手に、{n(ctx)}の顔から血の気が引いていく…")
    out.printl('見間違えるはずもない――"人類の敵"、触手生物。')
    out.printl("巨体が大穴を広げながら、天井を突き破り姿を現そうとしている！")
    out.printw()
    if is_girly(ctx) and t(ctx, c, "変身能力") > 0 and c.cflag[1] == 0:  # :282–288
        out.printl("ここは人の目が多すぎる。まさかプールの中で変身するわけにも……")
        out.printl(f"一瞬の躊躇いから反応が遅れた{n(ctx)}。")
    else:
        out.printl("こんな場所で襲撃……！？")
        out.printl(f"一虚を突かれ、反応が遅れた{n(ctx)}。")
    out.printl("太い触手が見る見るうちに天井から垂れ下がったと思うと、")
    out.printl("異臭を放つ粘液がボドリ、ボチャリと零れ始め……")
    out.printw()
    out.printl("プール内外に降り注ぎ始める白濁のシャワー。")
    out.printl("渦巻く混乱の中で横転するフローター、急激に粘つき始めた水面へ投げ出される女性客。")
    out.printl(f"戸惑う{n(ctx)}の眼前にひときわ大きな触手塊が落下すると、")
    out.printl(f"粘液混じりの波にあおられた浮き輪と{n(ctx)}は軽々吹き飛ばされて宙を舞い……")
    out.printw()
    # :299 アウターを一時的に没収、インナーを「イベント専用装備」（992）に
    event_battle_set_costume(ctx, st.target, 0 if c.cflag[1] == 0 else -1, 0 if c.cflag[1] > 0 else -1, 992, -1)
    _pool_shower(ctx, 5, 20)  # :300–307
    out.print(f"鼻をつく精臭と予想外の襲撃に凍った{n(ctx)}の思考を、")
    if is_female(ctx.data, c):  # :310 ISFEMALE(TARGET)
        out.printl("粘液プールの底から迫り来る触手の不快な感触が現実に引き戻す。")
        out.printl(f"触手の狙いはただ一つ、{n(ctx)}を含む女性たち。")
        out.printl("そしてこの場で立ち向かえる存在はただ一人…！")
        out.printw()
        out.printl(f"……噎せ返る精臭の中で必死に息を整え、肩まで粘液に漬かりながら臨戦態勢を取る{n(ctx)}。")
        out.printl("白濁の臭いに思考を阻害され、自身が纏う「衣装」にまでは考えが及んでいない。")
        out.printl(f"{n(ctx)}が着ている水着は、間違っても戦闘に適した「衣装」ではない。")
        out.printl("無防備、それどころか触手生物にとって格好の――")
        out.printw()
    else:
        out.printl("粘液プールの底を這う触手に脚を絡め取られた女性たちの悲鳴が現実に引き戻した。")
        out.printl("そうだ、ここには守るべき市民が、狙われた女性たちがいる。ならば成すべき事は一つ…！")
        out.printw()
    out.printl()
    out.set_color(HOTPINK)
    out.printl("（水着姿のまま耐久し、触手生物の狙いを市民から逸らしてください！）")
    out.reset_color()
    out.printw()
    out.drawline()
    out.drawline()  # :332
    _turn_limit(ctx, 15)
    c.tcvarn[0] = 1  # :335 近距離スタート
    add_battle_situation(st, "先制無し,支援無効,市民なし,レイプなし,変身不可")
    return None
    yield  # pragma: no cover


def _turnend_3004(ctx: Ctx) -> None:
    """3004:340–372。"""
    st, out = ctx.state, ctx.out
    if st.tflag[0] % 3 == 0:  # :343（C# の % は 0 方向：TFLAG:0 ≥ 0）
        out.set_color(FUCHSIA)
        out.set_bold(True)
        out.printl("天井を這い回る触手から白濁シャワーが降り注ぐ！")
        out.reset_color()
        # FONTREGULAR はここでは無い（:347 RESETCOLOR のみ：太字のまま下の文も出る、原作どおり）
        _pool_shower(ctx, 7, 15)
    if st.tflag[0] >= 7 and tc(ctx).tcvarn[0] != 0:  # :358–372
        out.set_color(RED)
        out.set_bold(True)
        if st.flag[70] > 0:
            out.printl("逃げ遅れていた利用客の避難が完了したようだ！")
            st.flag[70] = 0
        out.reset_color()
        out.set_bold(False)
        out.wait()  # FORCEWAIT


def _success_3004(ctx: Ctx) -> None:
    """3004:386–417（ニュースは原作で注釈化）。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    cs = tc(ctx).cstr[82]
    if st.tflag[98] == 1:
        out.printl(f"{n}の一撃が触手の急所に叩き込まれる。")
        out.printl("触手の巨体はひときわ不気味にブヨブヨと痙攣し、")
        out.printl("精という精を撒き散らさんばかりに白濁を散らしながら上体が弾け飛び――完全に動きを止めた。")
        out.printl()
        out.printl("階下から駆け付けた警備スタッフが目にしたのは、")
        out.printl("互いに慰め励まし粘液を拭き取り合う若い女性客たち。")
        out.printl("そしてうっかり大型触手を返り討ちにしてしまい説明に困り果てている、")
        out.printl(f"{cs}姿の美しい少女だった……")
        out.printw()
        out.printl("　無事に被害を最小限に抑えました！")
    else:
        out.printl(f"触手生物は{n}の激しい抵抗を警戒したのか、")
        out.printl("巨体に見合わぬ速さで元来た穴へと滑り込んでいった。")
        out.printl("……逃げられる！？")
        out.printl(f"咄嗟に距離を詰め駆け寄る{n}は、周囲への警戒が薄れてしまう。")
        out.printl("その無防備な頭上へと、天井で蠢動する全ての触手から一斉に精のシャワーが放たれ――")
        out.printl()
        out.printl("階下から駆け付けた警備スタッフが目にしたのは、")
        out.printl("蕩けた顔で互いに「慰め」あう粘液まみれの若い女性客たち。")
        out.printl("そしてプレゼントされた白濁粘塊に溺れかけつつ発情自慰に耽る、")
        out.printl(f"{cs}姿の無様な雌の姿だった……")
        out.printw()
        out.printl("　無事に被害を最小限（？）に抑えました！")


def _failure_3004(ctx: Ctx) -> None:
    """3004:419–443。"""
    st, out = ctx.state, ctx.out
    n = _name(ctx)
    if st.tflag[98] == 2:
        out.printl(f"{n}が力尽きたことでナイトプールは触手の餌場と化した。")
        out.printl(f"触手生物は意識を失った{n}を執拗に粘液プールへと沈め続け、")
        out.printl("漬け込まれ少女の肢体はべたつく精にコーティングされてゆく。")
        out.printl("絶望の悲鳴を上げる他の女性客も、一人また一人と這い回る触手に囚われてゆき……")
        out.printl()
        out.printl("触手生物は目ぼしい獲物の「加工」を終えたと判断してか、")
        out.printl("白濁化粧を施された女性たちの手足に粘つく触手を絡み付かせる。")
        out.printl(f"意識を失った{n}や他の女体を垂れ下がる触手の莢へと詰め込み、")
        out.printl("触手生物はヌチャヌチャ下品な音を立てながら悠々と引き上げていった。")
        out.printl()
        out.printl("階下から駆け付けた女性スタッフが目にしたのは散乱する汚濁塗れの女性用下着や私物、")
        out.printl("そして追加の「おこぼれ」に気付いて歓喜に蠢く小型触手の群れだった……")
        out.printw()
        out.printl("　耐久ミッションに失敗しました……")
    news_failure(ctx)


def _nothing(ctx: Ctx) -> None:
    """SUCCESS／FAILURE_3001・3002（本文はすべて注釈）。"""


_SITUATION = {2: _situation_2, 3: _situation_3, 4: _situation_4, 5: _situation_5}
_RESCUE_MSG = {2: _rescue_msg, 3: _rescue_msg, 4: _rescue_msg, 5: _rescue_msg}
_EXEC = {2: _exec_2, 3: _exec_3, 4: _exec_4, 5: _exec_5, 3001: _exec_3001, 3002: _exec_3002, 3003: _exec_3003,
         3004: _exec_3004}
_CHECKER = {2: _checker_not_lose, 3: _checker_not_lose, 4: _checker_4, 5: _checker_not_lose, 3001: _checker_not_lose,
            3002: _checker_not_lose, 3003: _checker_idol, 3004: _checker_idol,
            6001: _checker_not_lose, 6002: _checker_not_lose}
_SUCCESS = {2: _success_2, 3: _success_3, 4: _success_4, 5: _success_5, 3001: _nothing, 3002: _nothing,
            3003: _success_3003, 3004: _success_3004, 6001: _nothing, 6002: _nothing}
_FAILURE = {2: _failure_2, 3: _failure_3, 4: _failure_4, 5: _failure_5, 3001: _nothing, 3002: _nothing,
            3003: _failure_3003, 3004: _failure_3004, 6001: _nothing, 6002: _nothing}
_TURNEND = {3003: _turnend_3003, 3004: _turnend_3004}


# --- EVENT_BATTLE_FLASHNEWS_n（S26）：SHOP_FLASHNEWS.ERB@FLASHNEWS:74–87 の TRYCALLFORM 先 -------------------------------
# ARG：1 = ミッション成功、0 = 失敗、-1 = ミッション以前に敗北幽閉。書くのは共用 RESULTS:0 だけ（`RESULTS'=…`）。
# 本体が全部コメントの関数（3001:76–86、3002:158–168、6001:58–68、6002:56–66）や、書かない ARG（3004 の 0、5 の -1）は
# RESULTS:0 を変えない（FLASHNEWS 側は前回の RESULTS:0 を読む）。関数終端の RESULT:0 = 0 は FLASHNEWS 側で読まないので書かない。
# 3001／3002／6001／6002 は SUCCESS／FAILURE の FLAG:60 代入もコメント（3001:54–74 ほか）なので FLAG:60 がこの番号になることは無く、
# 実際に前回値を読むのは 3004 の ARG 0 と 5 の ARG -1 だけ（S26b：前回値は戰後オートセーブの @SAVEINFO が書く "408"）。


def _fn_2(st, arg: int) -> None:
    """`2 女子高救出.ERB@EVENT_BATTLE_FLASHNEWS_2`:305–315。"""
    if arg == 1:
        st.results[0] = "お手柄！ 女子高襲う触手生物を撃退、可憐な魔法少女に女生徒ら感謝の声"
    elif arg == 0:
        st.results[0] = "女子高が触手生物の襲撃で壊滅、女生徒ら多数残されたまま汚染区域に認定へ…"
    elif arg == -1:
        st.results[0] = ""


def _fn_3(st, arg: int) -> None:
    """`3 女性自衛官小隊救援.ERB@EVENT_BATTLE_FLASHNEWS_3`:168–178。"""
    if arg == 1:
        st.results[0] = "お見事！ 触手の奇襲で窮地に陥る女性自衛官らを魔法少女が華麗に救援"
    elif arg == 0:
        st.results[0] = "凶悪な巨大触手が女性自衛官の小隊を奇襲、複数の女性隊員が行方不明に……"
    elif arg == -1:
        st.results[0] = ""


def _fn_4(st, arg: int) -> None:
    """`4 攫われた女性.ERB@EVENT_BATTLE_FLASHNEWS_4`:101–111。"""
    if arg == 1:
        st.results[0] = "触手生物に攫われかけた女性らを魔法少女が華麗に救出、市民ら感謝の声"
    elif arg == 0:
        st.results[0] = "大型触手生物が市街地を襲来、複数の女性が行方不明に"
    elif arg == -1:
        st.results[0] = "大型触手生物が市街地を襲来、女性ら多数行方不明。中には魔法少女の姿も？"


def _fn_5(st, arg: int) -> None:
    """`5 触手洞窟.ERB@EVENT_BATTLE_FLASHNEWS_5`:472–482（ARG -1 の代入はコメント：:481）。"""
    if arg == 1:
        st.results[0] = "触手生物に攫われた女性たちを魔法少女が華麗に救出、市民ら感謝の声"
    elif arg == 0:
        st.results[0] = "市街地に突如大穴、触巣出現で集団下校中の女子生徒ら犠牲に"


def _fn_3003(st, arg: int) -> None:
    """`3003 ライブ奇襲.ERB@EVENT_BATTLE_FLASHNEWS_3003`:160–170（PRINT_TRANSNAME(TARGET)）。"""
    if arg == 1:
        st.results[0] = f"客を魅了、触手を翻弄！　アイドル「{print_transname(st, st.target)}」が囮となり避難の時間を稼ぐ"
    elif arg == 0:
        st.results[0] = f"巨大触手がライブ会場を襲撃、アイドル「{print_transname(st, st.target)}」が触手凌辱の餌食に"
    elif arg == -1:
        st.results[0] = f"巨大触手がライブ会場を襲撃、アイドル「{print_transname(st, st.target)}」や女性客ら攫われ失踪"


def _fn_3004(st, arg: int) -> None:
    """`3004 プール奇襲.ERB@EVENT_BATTLE_FLASHNEWS_3004`:275–291（ARG 0 の代入はコメント：:287）。"""
    if arg == 1:
        st.results[0] = ""
        if st.tflag[98] == 1:
            st.results[0] = "お手柄！　ナイトプール襲撃の巨大触手、居合わせた謎の少女が返り討ち"
        else:
            st.results[0] = "巨大触手がナイトプールを襲撃、女性客らに深刻な粘液被害か"
    elif arg == -1:
        st.results[0] = "巨大触手が室内プール襲撃、女性客ら多数行方不明に"


def _fn_empty(st, arg: int) -> None:
    """本体がすべてコメントの関数（3001／3002／6001／6002）。"""


# 定義されている関数（全域 grep `@EVENT_BATTLE_FLASHNEWS_`：11 件、うち `_6xxx` はテンプレートで数値 FLAG:60 からは呼べない）
_FLASHNEWS = {2: _fn_2, 3: _fn_3, 4: _fn_4, 5: _fn_5, 3001: _fn_empty, 3002: _fn_empty, 3003: _fn_3003, 3004: _fn_3004,
              6001: _fn_empty, 6002: _fn_empty}


def event_battle_flashnews(st, no: int, arg: int) -> bool:
    """`TRYCALLFORM EVENT_BATTLE_FLASHNEWS_{no}(arg)`。関数が無ければ何もしない（False）
    （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2316–2325）。"""
    f = _FLASHNEWS.get(no)
    if f is None:
        return False
    f(st, arg)
    return True
