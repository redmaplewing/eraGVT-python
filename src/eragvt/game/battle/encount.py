"""出撃時の遭遇判定：`ゲーム内_戦闘処理/ENCOUNT.ERB` と報酬関数（`汎用関数/コモン関数.ERB`）。

路徑相對 `source/earGVP/ERB/`。
- `@ENCOUNT`:5–13 → `@ENCOUNT_ENEMY`:19–131（洗脳／悪堕ちキャラ）→ 遭遇しなければ `@ENCOUNT_BOSS`:137–424。
- ボスとも遭遇しなければ ACTION.ERB:82–83 が `@MOB_TENTACLE_ENCOUNT`:429–522。基本設定（FLAG:802 = 15 で
  bit4「雑魚戦」OFF）では `CONFIG_CHECK_EVENT_F(4) == 0` なので文章のみの自動勝利（:449–521、RETURN 0）。
- 関数が RETURN なしで終端に達すると RESULT = 0（reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。
"""

from __future__ import annotations

from ...state.constants import ActionPlan, GameOption
from ..action import Ctx, config_check_event, get_exp, get_syuren, kojo_root, print_callname
from ..chara_common import charatalent
from ..era import div, limit, times
from ..opening import game_option
from ..shop import syouhi_keigen
from ..tentacle import BOSS_ERB_NUM, enemy_type_check, tentacle_survive_check, tentacle_survive_num
from .cloth import cloth_battle_hosei
from .core import (
    BOSSES,
    add_randchoose,
    choicecount,
    clear_randchoose,
    config_check_balance,
    t,
    tc,
    tentacle_access,
    randchoose_f,
    tentacle_level,
)


# --- 報酬（汎用関数/コモン関数.ERB）--------------------------------------------------------


def get_exp_battle(ctx: Ctx) -> None:
    """`@GET_EXP_BATTLE`:370–400。"""
    st = ctx.state
    c = tc(ctx)
    level = c.abl[ctx.data.index_of("ABL", "レベル")]
    if st.savestr[13] == "MOB" or st.flag[73] > 0:
        local = div(8 * (tentacle_level(st) + 2), level) + st.rng.rand(15)
        if local < 1:
            local = 1
        if c.cflag[43] == 505:
            local = times(local, "1.10")
        get_exp(ctx, min(local, 75))
    elif st.savestr[13] == "BOSS":
        local = div(50 * (tentacle_level(st) + 2), level) + st.rng.rand(15) + 25
        if local < 10:
            local = 10
        if c.cflag[43] == 505:
            local = times(local, "1.10")
        get_exp(ctx, min(local, 150))
    else:
        ctx.out.printw("ERROR NO EXP DATA")


def get_money(ctx: Ctx, value: int) -> None:
    """`@GET_MONEY, ARG`:424–426。"""
    ctx.state.money += value
    ctx.out.printl(f"{value}＄を手に入れた")


def get_kakera(ctx: Ctx, value: int) -> None:
    """`@GET_KAKERA, ARG`:430–432。"""
    ctx.state.flag[200] += value
    ctx.out.printl(f"触手の欠片を{value}個を手に入れた")


def research_progress(ctx: Ctx, value: int) -> None:
    """`@RESEARCH_PROGRESS, ARG`:1051–1055。"""
    f = ctx.state.flag
    if f[47] < f[46] and f[47] + value >= f[46]:
        ctx.out.printw("ボス触手の居場所を特定した！")
    f[47] += value


def support_heal(ctx: Ctx) -> None:
    """戦闘支援効果で回復（ENCOUNT.ERB:499–520 と BATTLE_TRAIN_AFTER.ERB:443–464 は同じ本文）。条件は呼び出し側。"""
    st, out = ctx.state, ctx.out
    l1 = st.flag[43] * 8
    saved = st.target
    for i in range(st.charanum):
        if i == 0 or st.charas[i].cflag[999] == 0:
            continue
        st.target = i
        r = cloth_battle_hosei(ctx, "HEALUP")
        if st.charas[i].cflag[100] == ActionPlan.SUPPORT and r > 0:
            l1 = div(l1 * (100 + r), 100)
    st.target = saved
    c = tc(ctx)
    heal = div(c.maxbase[0] * l1, 100)
    c.base[0] = limit(heal + c.base[0], 0, c.maxbase[0])
    heal = div(c.maxbase[1] * l1, 100)
    c.base[1] = limit(heal + c.base[1], 0, c.maxbase[1])
    out.printl()
    out.printl(f"戦闘支援効果で{print_callname(st, st.target)}の体力と気力が回復した！")


def print_defense_change(ctx: Ctx, local: int) -> None:
    """`ABS LOCAL` / `PRINTFORM 防衛力が{RESULT}` / 低下／上昇（ENCOUNT.ERB:490–496 など）。"""
    ctx.out.print(f"防衛力が{abs(local)}")
    ctx.out.printl("低下した" if local < 0 else "上昇した")


# --- @ENCOUNT ------------------------------------------------------------------------


def encount(ctx: Ctx) -> int:
    """`@ENCOUNT`:5–13。"""
    ctx.state.flag[73] = 0
    result = encount_enemy(ctx)
    if result == 0:
        result = encount_boss(ctx)
    return result


def encount_enemy(ctx: Ctx) -> int:
    """`@ENCOUNT_ENEMY`:19–131（洗脳／悪堕ちキャラとの遭遇）。

    - 候補（CFLAG:0 が 2／3）は LOCAL:100〜 に並べ、`RAND:(LOCAL:1)` で選ぶ（:77–79）。その後 :81–86 の「遭遇率アップ」で
      CFLAG:23 が最大のキャラ（CFLAG:0 が 1／2／3：幽閉中も含む。MASTER も除外しない）に置き換わる（原作どおり）。
    - FLAG:10／FLAG:11 は ACTION.ERB:37–38 で 0 のまま（悪堕ちキャラ戦では TENTACLE_ACCESS がボス 0 を指す：core.tentacle_access）。
    - 遭遇しなかった場合 FLAG:110 は 1 のまま（ENCOUNT_BOSS:144 で 0 に戻る）。
    """
    from .core import msg_other, run_chinobun
    from .func import transform

    st, data = ctx.state, ctx.data
    c = tc(ctx)
    st.savestr[13] = "BOSS"  # :22 文字列変数への `=` は右辺をそのまま文字列として代入
    st.flag[110] = 1
    encount_up = 0
    c.exp[data.index_of("EXP", "戦闘経験")] += 1  # :28
    cands: list[int] = []  # LOCAL:100〜（LOCAL:1 = 件数）
    for i in range(st.charanum):  # :31–51
        if i == 0:
            continue
        ch = st.charas[i]
        if (
            t(ctx, ch, "変身能力") > 0
            and charatalent(data, ch, 0, "オトコ") == 0
            and charatalent(data, ch, 1, "オトコ") > 0
            and t(ctx, ch, "妊娠") > 0
        ):
            continue
        if ch.cflag[0] == 2:
            cands.append(i)
        if ch.cflag[0] == 3:
            cands.append(i)
        encount_up += ch.cflag[23]
    encount_up += t(ctx, c, "巻き込まれ体質") * 15  # :54
    per = 0
    if st.time == 0:  # :57–61
        per = 40
    elif st.time == 1:
        per = 20
    per += encount_up - min(div(st.flag[852], 500), 40)
    per = min(per, 80)
    if st.flag[999] == 1 and cands:  # :67–71
        raise NotImplementedError("デバッグモードの遭遇率入力は未移植")
    if st.rng.rand(100) < per and cands:  # :74–76（ENEMY_TYPE_CHECK_F("AKUOTI") は FLAG:110 = 1 なので常に 1）
        st.flag[111] = cands[st.rng.rand(len(cands))]  # :77–79
        l3 = 0
        for i in range(st.charanum):  # :81–86
            o = st.charas[i]
            if o.cflag[23] > 0 and o.cflag[23] > l3 and o.cflag[0] in (1, 2, 3):
                l3 = o.cflag[23]
                st.flag[111] = i
        e = st.charas[st.flag[111]]
        e.cflag[23] = div(e.cflag[23], 2)  # :87–89
        if e.cflag[23] < 25:
            e.cflag[23] = 0
        if e.cflag[0] == 2:  # :91–109（CFLAG:300／301 は TARGET の初遭遇フラグ）
            if c.cflag[300] == 0:
                run_chinobun(ctx, "MESSAGE_ENCOUNT_SENNOU_FIRST", fallback=lambda: kojo_root(ctx, "ENCOUNT_SENNOU_FIRST"))
                c.cflag[300] = 1
            else:
                run_chinobun(ctx, "MESSAGE_ENCOUNT_SENNOU", fallback=lambda: kojo_root(ctx, "ENCOUNT_SENNOU"))
        elif e.cflag[0] == 3:
            if c.cflag[301] == 0:
                run_chinobun(ctx, "MESSAGE_ENCOUNT_AKUOTI_FIRST", fallback=lambda: kojo_root(ctx, "ENCOUNT_AKUOTI_FIRST"))
                c.cflag[301] = 1
            else:
                run_chinobun(ctx, "MESSAGE_ENCOUNT_AKUOTI", fallback=lambda: kojo_root(ctx, "ENCOUNT_AKUOTI"))
        msg_other(ctx, "ENTRY")  # :112
        lv = e.abl[data.index_of("ABL", "レベル")]
        st.flag[12] = e.maxbase[0] + div(e.maxbase[11] * (15 + lv), 2)  # :115（MAXBASE:体力・防御）
        st.flag[13] = st.flag[12]
        st.flag[14] = 1000  # :119–123
        st.flag[15] = 0
        st.flag[16] = 760 + lv * 10
        st.flag[17] = 0
        st.flag[22] = -1
        if enemy_type_check(st, "AKUOTI") and t(ctx, e, "変身能力") > 0 and e.cflag[1] == 0:  # :126–127
            transform(ctx, 1, st.flag[111])
        return 1
    return 0


def encount_boss(ctx: Ctx) -> int:
    """`@ENCOUNT_BOSS`:137–424（ボス触手分。ラスボスは遭遇が決まったところで停止）。"""
    st = ctx.state
    c = tc(ctx)
    f = st.flag
    st.savestr[13] = "BOSS"
    f[110] = 0
    f[111] = 0
    per = 0
    select = 0
    defense = c.cflag[100] == ActionPlan.DEFENSE
    if f[100] > 0:  # :149
        if st.time == 0:
            per = div((40 + f[3] * 3) * f[47], f[46])
        elif st.time == 1:
            per = div((50 + f[3] * 3) * f[47], f[46])
        per += t(ctx, c, "巻き込まれ体質") * 20
        if f[45] == 0 and (f[47] < f[46] or f[49]):  # :159–160
            return 0
        if defense:  # :163–177
            return 0
        if f[45] > 0:
            per = 100
        if per > st.rng.rand(100):  # :184
            if config_check_balance(st, 1) > 0 and not defense:  # :188–200 索敵ターゲット
                if f[18] > 0 and f[45] == 0 and per > 0:
                    if tentacle_survive_check(st, 2 ** (f[18] - 1)):
                        if st.rng.rand(100) < 50 + (f[41] + f[43]) * 10 or game_option(st, GameOption.ENDLESS):
                            select = f[18]
                    else:
                        f[18] = 0
            if select == 0:  # :201–219
                clear_randchoose(st)
                for n in range(BOSS_ERB_NUM + 1):
                    # POWER(2, -1) は (long)0.5 = 0（Creator.Method.cs@PowerMethod:1051–1062）
                    if tentacle_survive_check(st, 2 ** (n - 1) if n >= 1 else 0) > 0:
                        add_randchoose(st, n)
                select = randchoose_f(st) if choicecount(st) > 0 else 0
        else:
            select = 0
        # :226–239 捕まっているキャラを捕獲している触手の出現率アップ
        if config_check_balance(st, 0) > 0 and not defense and f[45] == 0 and per > 0:
            for count in range(BOSS_ERB_NUM):
                for i in range(st.charanum):
                    ch = st.charas[i]
                    if ch.cflag[0] == 1 and ch.cflag[21] == count and st.rng.rand(100) < 50:
                        ctx.out.printl("捕獲触手遭遇率アップ判定に成功！")
                        select = count
                        break
        if select > 0 and f[999] == 1 and f[45] == 0:  # :242–248
            raise NotImplementedError("デバッグモードの対戦相手指名は未移植")
        if f[45] > 0 and select == 0:  # :251–255
            ctx.out.printl("【エラー：ENCOUNT.ERB…イベントで戦闘する敵を決定できませんでした】")
            return 0
        if select <= 0:
            return 0
        f[10] = 0  # :262
        if f[18] == 0 and f[45] == 0:
            f[18] = select
        f[11] = select
        if select not in BOSSES:  # :271–278 TENTACLE_BOSS_{n}_GETNAME が無い
            ctx.out.printl(f"【エラー：ENCOUNT.ERB…TENTACLE_BOSS_{select}は未定義の番号です】")
            f[10] = 0
            f[11] = 0
            st.savestr[13] = ""
            return 0
        f[12] = int(tentacle_access(ctx, "HP"))  # :280–288
        f[13] = f[12]
        f[14] = int(tentacle_access(ctx, "SYASEI"))
        f[15] = 0
        f[16] = int(tentacle_access(ctx, "YUDAN"))
        f[17] = 0
        c.exp[ctx.data.index_of("EXP", "ボス経験")] += 1
        acc = f[300 + f[11]]  # :293–297 蓄積ダメージ
        f[13] = div(f[13] * (1000000 - div(acc, 100)), 1000000)
        if acc % 100:
            f[13] = min(f[13] + 1, f[12])
        if f[13] <= 0:
            f[13] = 1
        if f[45] == 0:
            message_encount_boss(ctx)
        else:
            raise NotImplementedError("MESSAGE_RAID_BOSS は未移植")
        return 1
    # :309– ラスボス触手
    if f[45] == 0 and (f[47] < f[46] or f[49]):
        return 0
    if st.time == 0:
        per = div(70 * f[47], f[46])
    elif st.time == 1:
        per = div(80 * f[47], f[46])
    if defense:
        return 0
    if f[45] > 0:
        per = 100
    if per > st.rng.rand(100):
        clear_randchoose(st)
        for n in range(BOSS_ERB_NUM + 1):
            if tentacle_survive_check(st, 2 ** (n - 1) if n >= 1 else 0) > 0:
                add_randchoose(st, n)
        select = randchoose_f(st) if choicecount(st) > 0 else 0
    if f[45] > 0 and select == 0:
        raise NotImplementedError("襲来イベントのラスボス選択（GOTO RAID_LOOP）は未移植")
    if select > 0 and f[999] == 1 and f[45] == 0:
        raise NotImplementedError("デバッグモードの対戦相手指名は未移植")
    if select <= 0:
        return 0
    raise NotImplementedError("ラスボス触手との戦闘（ENCOUNT_BOSS:365–421）は未移植")


def message_encount_boss(ctx: Ctx) -> None:
    """`地の文/MESSAGE_BATTLE.ERB@MESSAGE_ENCOUNT_BOSS`:27–35。"""
    st, out = ctx.state, ctx.out
    tentacle_access(ctx, "NAME")
    out.printl(f" Lv.{tentacle_level(st)} と遭遇した！")
    for line in BOSSES[st.flag[11]].definition:  # TENTACLE_BOSS_{n}_DEFENITION
        out.printl(line)
    out.printl("・・・・・・・・・・・・・・・")
    kojo_root(ctx, "ENCOUNT_BOSS")
    out.printw()


# --- @MOB_TENTACLE_ENCOUNT --------------------------------------------------------------


def mob_tentacle_encount(ctx: Ctx) -> int:
    """`@MOB_TENTACLE_ENCOUNT`:429–522。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    c = tc(ctx)
    st.savestr[13] = "MOB"
    c.exp[data.index_of("EXP", "戦闘経験")] += 1  # :432
    if config_check_event(st, 4) > 0:  # :436–447
        raise NotImplementedError("雑魚戦システム（MOB_TENTACLE_BATTLE）は未移植")
    mob = data.str_defaults.get(2501, "")
    # MESSAGE_ENCOUNT_MOB（地の文/MESSAGE_BATTLE.ERB:5–11）
    out.printl(f"{mob} と遭遇した！")
    out.printl("・・・・・・・・・・・・・・・")
    out.printl(f"{mob} を倒した!")
    kojo_root(ctx, "ENCOUNT_MOB")
    out.printw()
    # :453–461
    local = times(c.maxbase[0], "0.35")
    c.base[0] = limit(c.base[0] - syouhi_keigen(data, st, st.target, local, 0), 0, c.base[0])
    out.printl(f"{data.names['BASE'].get(0, '')}が{local}減少した")
    local = times(c.maxbase[1], "0.30")
    c.base[1] = limit(c.base[1] - syouhi_keigen(data, st, st.target, local, 1), 0, c.base[1])
    out.printl(f"{data.names['BASE'].get(1, '')}が{local}減少した")
    # :464–474 探索度
    if enemy_type_check(st, "CITIZEN") == 0:
        local = 6 + st.rng.rand(4)
        if c.cflag[100] != ActionPlan.SORTIE:
            local = div(local, 2)
        if t(ctx, c, "狩人の勘") > 0:
            local += 5
        out.printl(f"探索度が{local}上昇した")
        research_progress(ctx, local)
        out.printl()
    # :477–482
    get_exp_battle(ctx)
    tentacle_survive_num(st)
    get_syuren(ctx, 10 + st.rng.rand(15))
    a = 25 + st.rng.rand(11)
    get_money(ctx, a * (5 + st.rng.rand(5)))
    # :485–496
    local = st.rng.rand(50) + div(tentacle_level(st), 2) + 25
    st.flag[852] += local
    if st.flag[852] < 0:
        st.flag[852] = 0
    print_defense_change(ctx, local)
    # :499–520（GROUPMATCH(CFLAG:100, 予定_出撃, 予定_防衛)）
    if st.flag[43] and c.cflag[100] in (ActionPlan.SORTIE, ActionPlan.DEFENSE):
        support_heal(ctx)
    return 0
