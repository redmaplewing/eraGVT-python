"""ターン終了：`インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`:3–139 と `@EVENTSHOP` の通常分岐（:158–215）。

路徑相對 `source/earGVP/ERB/`。夜間イベント等のうち未移植のものは「開始条件」だけを原作どおり判定し、
条件が成立したら `NotImplementedError`（戦闘なしでは起こり得ない状態）か、
DEVIATION として発生を見送る（通常プレイで起こる乱数イベント：襲撃・救援、子触手襲来）。
"""

from __future__ import annotations

from collections.abc import Generator

from ..state import GameState, IntArray
from ..state.constants import ActionPlan, CharaState, GameOption
from .action import (
    BEAUTY_SALON,
    FUNSUI,
    FUUKEIGA,
    KANYOU,
    MASSAGE_CHAIR,
    OBJET,
    SHOWER,
    Ctx,
    Step,
    _fatigue_scale,
    action_main,
    config_check_event,
    config_check_maniac,
    config_check_other,
    config_check_prison,
    config_check_screen,
    kojo_root,
)
from .chara_common import charatalent, is_male, level_status, talent
from .era import div, isqrt, limit, mod, times
from .opening import game_option
from .shop import charanum_active, charanum_safe, charanum_safe_partycheck, check_gameover, check_pregnant
from .tentacle import enemy_type_check, get_lastboss_phase, tentacle_survive_num

# --- 1 ターン（JUMP ACTION_MAIN → BEGIN TURNEND の繰り返し → BEGIN SHOP）-------------------


def run_turn(ctx: Ctx) -> Generator[None, int, None]:
    """`SHOP.ERB@USERSHOP_ACTION_CONFIRM`:557 の JUMP ACTION_MAIN から BEGIN SHOP まで。
    BEGIN／JUMP は呼び出しスタックを捨てるので、ここでは順に呼び直すだけでよい。"""
    step = yield from action_main(ctx)
    while True:
        if step == Step.TURNEND:
            step = event_turnend(ctx)
        elif step == Step.ACTION_MAIN:
            step = yield from action_main(ctx)
        elif step == Step.SHOP:
            return
        else:
            raise NotImplementedError("BEGIN TRAIN（戦闘）は S05")


# --- @EVENTTURNEND ---------------------------------------------------------------


def event_turnend(ctx: Ctx) -> Step:
    """`SHOP_TURNEND.ERB@EVENTTURNEND`:3–139。戻り値は JUMP／BEGIN の行き先。"""
    st, out = ctx.state, ctx.out
    # :7–12
    st.flag[70] = 0
    st.flag[71] = 0
    st.flag[72] = 0
    st.temp.max_palam = IntArray()
    # :15–16
    if st.flag[799] < st.charanum and st.flag[45] == 0:
        return Step.ACTION_MAIN
    set_partymember(ctx)  # :19
    # :25–37
    if st.charas[st.flag[798]].cflag[0] != CharaState.SAFE:
        for i in range(st.charanum):
            if i == GameState.MASTER:
                continue
            if st.charas[i].cflag[0] == CharaState.SAFE:
                st.target = i
                break
    else:
        st.target = st.flag[798]
    ending(ctx)  # :40
    # :42–49（ENDING が戻ってきた場合のみ到達。FLAG:999 == -999／FLAG:64 != 0 は ENDING 本体でしか立たない）
    if st.flag[999] == -999 or st.flag[64] != 0:
        raise NotImplementedError("ENDING 後のタイトル復帰／引き継ぎは未移植")
    recalc_partymember(ctx)  # :52
    # :56–61
    if st.flag[45] > 0:
        st.flag[45] = 0
        return Step.SHOP
    # :66–67
    if st.flag[64] == 0:
        st.flag[799] = 0
    out.printl()
    st.flag[49] = 0  # :73
    boss_tentacle_recover(ctx)  # :76
    # :79–85 口上のターン終了時処理
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        st.target = i
        kojo_root(ctx, "TURNEND")  # 地の文/MESSAGE.ERB@MESSAGE_TURNEND:8–10
    # :88–99 クズ市民による脅迫／誘拐監禁
    for i in range(1, st.charanum):
        c = st.charas[i]
        if (
            config_check_prison(st, 10) == 1
            and c.cflag[0] in (CharaState.SAFE, 5)
            and (c.cflag[286] + c.cflag[320] + c.cflag[321]) > 0
        ):
            raise NotImplementedError("INTIMIDATION_EVENT（クズ市民の脅迫）は未移植")
        if c.cflag[0] == CharaState.KIDNAPPED:
            raise NotImplementedError("KIDNAPPING（クズ市民監禁）は未移植")
    prison(ctx)  # :103
    birth_hantei(ctx)  # :105
    grow_hantei(ctx)  # :107
    akuoti_attack(ctx)  # :110
    lovesex_night(ctx)  # :112
    self_night(ctx)  # :114
    if config_check_event(st, 2) > 0:  # :116–117
        yobai(ctx)
    daily_defence_change(ctx)  # :120
    daily_popularity_change(ctx)  # :122
    if config_check_screen(st, 3) == 0:  # :125–126
        out.wait()
    if config_check_event(st, 0) > 0:  # :129–130
        raid_hantei(ctx)
    # :133–134（FLAG:45 は襲撃戦闘でのみ立つ。未移植のため常に 0）
    if st.flag[45] == 0:
        return Step.SHOP
    raise NotImplementedError("襲撃／救援イベントの戦闘（BEGIN TRAIN）は S05")


def set_partymember(ctx: Ctx) -> None:
    """`ヒロイン関連/SET_PARTYMEMBER.ERB@SET_PARTYMEMBER`:1–28。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    if st.charanum < 3 and charanum_safe_partycheck(st) == 0:
        st.flag[63] = 0
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        c = st.charas[i]
        if game_option(st, GameOption.SOLO) or check_gameover(st):
            pass
        elif check_pregnant(data, st, i) and c.cflag[100] == ActionPlan.SORTIE and c.cflag[0] < 1:
            out.printl(f"{c.callname}は妊娠しているため出撃できなくなりました")
            out.printw()
            c.cflag[100] = ActionPlan.REST
        elif check_pregnant(data, st, i) and c.cflag[100] == ActionPlan.DEFENSE:
            out.printl(f"{c.callname}は妊娠しているため防衛できなくなりました")
            out.printw()
            c.cflag[100] = ActionPlan.REST
        if c.cflag[0] != CharaState.SAFE and i < st.charanum - 1 and c.cflag[999]:
            raise NotImplementedError("SHIFTBACK_CHARA（離脱キャラを最後尾へ）は未移植")
        elif c.cflag[0] != CharaState.SAFE and c.cflag[999]:
            c.cflag[999] = 0


def ending(ctx: Ctx) -> None:
    """`ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING`:3–88 の判定部分。結末画面本体は未移植。"""
    st = ctx.state
    f = st.flag
    if f[64] > 0:  # :4–5
        raise NotImplementedError("引き継ぎ（ENDING START_SUCCESSION）は未移植")
    if f[100] <= 0 and f[101] <= 0 and not check_gameover(st):  # :9
        raise NotImplementedError("ENDING_2（ゲームクリア）は未移植")
    # :74–85 日数制限超過
    if f[999] == 0 and not check_gameover(st) and not game_option(st, GameOption.NO_TIME_LIMIT):
        alive = tentacle_survive_num(st)
        if enemy_type_check(st, "BOSS") == 1:
            if ((f[3] - alive + 1) * f[2] - st.day[0] + st.day[1]) <= 0 and st.time == 1:
                raise NotImplementedError("ENDING_3（日数制限超過）は未移植")
        elif get_lastboss_phase(st) >= 1:
            if (f[1] - st.day[0] + st.day[1]) == 0 and st.time == 1:
                raise NotImplementedError("ENDING_3（日数制限超過）は未移植")
    if f[999] == -997:  # :86–87
        raise NotImplementedError("ENDING（FLAG:999 == -997 のスコア処理）は未移植")


def recalc_partymember(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@RECALC_PARTYMEMBER`:220–258。"""
    st, data = ctx.state, ctx.data
    saved = st.target
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        level_status(data, st, i)
        if st.charas[i].cflag[0] == CharaState.JUST_RESCUED:
            raise NotImplementedError("救出直後の処理（RESCUE_CHILD／AFTER_RESCUED）は未移植")
        inmon_recovery(ctx, i)
        # :251–255 UPDATE_STATUS_RECORD（GLOBAL:103–131／GLOBALS と SAVEGLOBAL）と GET_STATE_TROPHY（GLOBAL の実績）。
        # DEVIATION: GLOBAL は読み書きしない（deviations.md「全域資料」）ので実行しない。SAVEDATA への影響はない。
    st.target = saved


def inmon_recovery(ctx: Ctx, who: int) -> None:
    """`SHOP_TURNEND.ERB@INMON_RECOVERY`:850–996。淫紋（CFLAG:32）が無ければ何もしない。"""
    st, data = ctx.state, ctx.data
    c = st.charas[who]
    if config_check_maniac(st, 9) == 1:
        if c.cflag[32] > 0 and c.cflag[0] == CharaState.SAFE and talent(data, c, "触手の虜") == 1:
            raise NotImplementedError("淫紋の進行（INMON_RECOVERY:857–）は未移植")
    elif c.cflag[32] > 0:
        raise NotImplementedError("淫紋の回復（INMON_RECOVERY:983–）は未移植")


def boss_tentacle_recover(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@BOSS_TENTACLE_RECOVER`:352–375。"""
    st, out = ctx.state, ctx.out
    if get_lastboss_phase(st) >= 2:
        return
    if st.flag[999] == 1:
        out.set_color((128, 128, 128))
        out.printl("DEBUG ボスのキズが回復")
        out.reset_color()
    for i in range(1, st.flag[3] + 1):
        st.flag[300 + i] -= st.rng.rand(3000000) + 8000000
        if st.flag[300 + i] < 0:
            st.flag[300 + i] = 0
    for i in range(1, st.flag[4] + 1):
        # @LASTBOSS_REST（ゲーム内_戦闘処理/LASTBOSS_POWERUP.ERB:16–22）
        rest_div = 8 if st.flag.get_bit(803, 5) and enemy_type_check(st, "LASTBOSS") >= 1 else 0
        st.flag[400 + i] -= div(st.rng.rand(3000000) + 1000000, 2 + rest_div)
        if st.flag[400 + i] < 0:
            st.flag[400 + i] = 0


# --- 夜間イベント（開始条件のみ） ------------------------------------------------------


def prison(ctx: Ctx) -> None:
    """`ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB@PRISON`:3–31。"""
    st, out = ctx.state, ctx.out
    if st.flag[999] == -998:
        st.flag[999] = 0  # RESETBGCOLOR は背景色が時間帯で決まるので不要
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        if st.charas[i].cflag[0] == CharaState.IMPRISONED or check_gameover(st):
            raise NotImplementedError("幽閉中イベント（PRISON_EVENT）は未移植")


def birth_hantei(ctx: Ctx) -> None:
    """`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@BIRTH_HANTEI`:277–410。妊娠（素質 妊娠 = 1,3,4,5）が無ければ何もしない。"""
    st, data = ctx.state, ctx.data
    for c in st.charas:
        if c.cflag[0] == CharaState.DEAD:
            continue
        if talent(data, c, "妊娠") in (1, 3, 4, 5):
            raise NotImplementedError("妊娠・出産の進行（BIRTH_HANTEI）は未移植")
    # TARGET は :279 で退避・:410 で復元


def grow_hantei(ctx: Ctx) -> None:
    """`ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@GROW_HANTEI`:4–25。"""
    st, data = ctx.state, ctx.data
    for c in st.charas:
        if c.cflag[0] == CharaState.CHILDCARE or c.cflag[22] > 0:
            raise NotImplementedError("育児（GROW_HANTEI:10–15）は未移植")
        if talent(data, c, "性徴停滞") > 0:
            pass
        elif c.cflag[225] > 14 or c.cflag[225] == 7:
            raise NotImplementedError("CHILD_GROW_1／2 は未移植")
        elif c.cflag[225] > 0:
            c.cflag[225] += 1


def akuoti_attack(ctx: Ctx) -> None:
    """`ゲーム内_イベント発生/強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB@AKUOTI_ATTACK`:5–29：
    候補は CFLAG:0 == 状態_悪堕ち のキャラのみ。"""
    st = ctx.state
    for i in range(1, st.charanum):
        if st.charas[i].cflag[0] == CharaState.CORRUPTED:
            raise NotImplementedError("悪堕ちキャラの淫謀（AKUOTI_ATTACK）は未移植")


def lovesex_night(ctx: Ctx) -> None:
    """`FORCE_いちゃラブセックス.ERB@LOVESEX_NIGHT`:5–97：夜のみ。交際相手 1–4 が居なければ必ず CONTINUE（:28–29）。"""
    st, data = ctx.state, ctx.data
    if st.time != 1:
        return
    saved = st.target
    for i in range(1, st.charanum):
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        st.target = i
        if c.cflag[0] != 0 or c.cflag[99] >= 30:
            continue
        partner = talent(data, c, "交際相手")
        if partner == 0 or partner >= 5 or (partner == 1 and st.rng.rand(10) > 4):
            continue
        raise NotImplementedError("いちゃラブセックス（LOVESEX_NIGHT:31–）の判定は未移植")
    st.target = saved


def self_night(ctx: Ctx) -> None:
    """`FORCE_夜間自慰.ERB@SELF_NIGHT`:5–61。"""
    st, data = ctx.state, ctx.data
    if st.time != 1:
        return
    tc = st.target_chara
    a = lambda c, n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    # :10–11（TARGET の素質で判定）
    if (
        talent(data, tc, "初心") > 0
        and a(tc, "Ｃ感覚") < 3
        and a(tc, "Ｖ感覚") < 3
        and a(tc, "Ａ感覚") < 3
        and a(tc, "Ｂ感覚") < 3
        and a(tc, "触手中毒") < 3
    ):
        return
    saved = st.target
    for i in range(1, st.charanum):
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        if talent(data, c, "繁殖袋") > 0 or talent(data, c, "四肢欠損") > 0:
            continue
        st.target = i
        if c.cflag[0] != 0:
            continue
        partner = talent(data, c, "交際相手")
        if 2 <= partner <= 4 and talent(data, c, "処女") < 1 and st.rng.rand(4) != 0:
            continue
        l1 = a(c, "欲望") * 5 + a(c, "触手中毒") * 2
        onani = a(c, "自慰中毒")
        l1 += 35 if onani >= 5 else {4: 30, 3: 25, 2: 20, 1: 15}.get(onani, 0)
        if st.rng.rand(100) < l1:
            raise NotImplementedError("夜間自慰イベント（SELF_NIGHT:49–）は未移植")
    st.target = saved


def yobai(ctx: Ctx) -> None:
    """`FORCE_夜這い.ERB@YOBAI`:8–100 の候補選び。候補がいれば YOBAI_EVENT（未移植）。"""
    st, data = ctx.state, ctx.data
    if st.time == 0:
        return
    if charanum_active(st) < 2:
        return
    if not any(st.charas[i].cflag[999] for i in range(1, st.charanum)):
        return
    if st.flag[999] == 1:
        ctx.out.set_color((105, 105, 105))
        ctx.out.printl("------ 夜這い判定 ------")
        ctx.out.reset_color()
    a = lambda c, n: c.abl[data.index_of("ABL", n)]  # noqa: E731
    candidates = []
    for i in range(1, st.charanum):
        c = st.charas[i]
        if c.cflag[999] == 0:
            continue
        t = lambda n: talent(data, c, n)  # noqa: E731
        if t("繁殖袋") > 0 or t("四肢欠損") > 0:
            continue
        st.target = i
        conds = (
            t("淫核") * 3 + a(c, "Ｃ感覚") >= 3,
            t("淫壷") * 3 + a(c, "Ｖ感覚") >= 3,
            t("淫尻") * 3 + a(c, "Ａ感覚") >= 3,
            t("淫乳") * 3 + a(c, "Ｂ感覚") >= 3,
            (t("ふたなり") > 0 or t("変身時ふたなり") > 0 or is_male(data, c)) and a(c, "射精中毒") > 0,
        )
        if not any(conds):
            continue
        if c.cflag[0] != 0:
            continue
        l1 = (t("淫乱") > 0) * 2 + sum(int(x) for x in conds)
        l2 = max(a(c, "欲望") + a(c, "自慰中毒") + a(c, "触手中毒"), 0)
        local = (l1 * 2 + 22) * (125 + l2 * 10) if l1 else 0
        if 1 <= t("交際相手") < 5:
            local = times(local, "0.5")
        if t("清純派"):
            local = times(local, "0.5")
        if t("人間不信") > 0:
            local = times(local, "0.25")
        if st.rng.rand(10000) < local:
            candidates.append(i)
    if candidates:
        raise NotImplementedError("夜這いイベント（YOBAI_EVENT）は未移植")


def raid_hantei(ctx: Ctx) -> None:
    """`ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB@RAID_HANTEI`:9–106。"""
    st = ctx.state
    # :14–21 男女平等オプション（ISHOLE）：CONFIG_CHECK_MANIAC_F(5) == 1 なら全員 1（汎用関数/SEX_GENDER.ERB@ISHOLE:52–66）
    if not any(st.charas[i].cflag[999] and _ishole(ctx, i) for i in range(1, st.charanum)):
        return
    if st.flag[21]:  # :24–25
        return
    if st.flag[41] >= st.charanum - 1:  # :27–28
        return
    if st.day[0] < 3:  # :30–31
        return
    # :35–45
    idle = sum(
        1
        for i in range(1, st.charanum)
        if st.charas[i].cflag[999]
        and st.charas[i].cflag[0] == 0
        and st.charas[i].cflag[100] not in (ActionPlan.SORTIE, ActionPlan.DEFENSE)
    )
    if idle < 1:
        return
    # :49–73
    d = st.flag[852]
    for bound, n in ((1000, 6), (1750, 12), (2500, 24), (3750, 36), (5000, 48), (7500, 60), (10000, 72),
                     (12500, 84), (15000, 96), (17500, 112), (20000, 128)):
        if d < bound:
            l2 = st.rng.rand(n)
            break
    else:
        l2 = st.rng.rand(256)
    st.temp.battle_situation = ""  # :76 INITBATTLESITUATION（特殊シチュエーション.ERB:41–42）
    if st.flag[999] == 1:  # :79–90
        raise NotImplementedError("RAID_HANTEI のデバッグ入力は未移植")
    # :94–105
    if l2 == 0 and st.rng.rand(2) == 0 and st.time == 0:
        _skip_event(ctx, "救援イベント（RAID_RESCUE）")
    elif l2 == 0 and st.rng.rand(18 - st.flag[52] * 3) != 0:
        _skip_event(ctx, "襲撃イベント（RAID_ATTACK）")
    elif st.rng.rand(100) == 0:
        _skip_event(ctx, "襲撃イベント（RAID_ATTACK）")


def _skip_event(ctx: Ctx, name: str) -> None:
    """DEVIATION: 発生条件を満たしたが未移植のイベント（戦闘を伴う）。発生しなかったものとして進める。"""
    ctx.out.printl(f"（未實作：{name}が発生しましたが、スキップします）")


def _ishole(ctx: Ctx, who: int) -> bool:
    """`汎用関数/SEX_GENDER.ERB@ISHOLE`:52–66。"""
    if config_check_maniac(ctx.state, 5) == 1:
        return True
    raise NotImplementedError("ISGIRLY（男女平等オプション OFF 時）は未移植")


# --- 防衛力・人気度 ------------------------------------------------------------------


def tentacle_level(state: GameState) -> int:
    """`ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_LEVEL`:356–408。"""
    kills = state.flag[3] - tentacle_survive_num(state)
    local = 3
    if game_option(state, GameOption.HARDCORE):
        local += 2
    if game_option(state, GameOption.SOLO):
        local += 1
    if game_option(state, GameOption.ENDLESS):
        local -= 1
    if game_option(state, GameOption.JOIN_RETIRE):
        local -= 1
    if game_option(state, GameOption.STAT_DECLINE):
        local -= 1
    if local < -4:
        local = -4
    base_level = kills * local + 4
    if enemy_type_check(state, "MOB") == 1:
        base_level = div(base_level * 3, 4)
    local = 150
    if game_option(state, GameOption.ENDLESS):
        local = div(local, 3)
    if game_option(state, GameOption.HARDCORE):
        local = div(local * 4, 3)
    if game_option(state, GameOption.STAT_DECLINE):
        local = div(local * 2, 3)
    if game_option(state, GameOption.JOIN_RETIRE):
        local = div(local, 2)
    if local < 0:
        local = 0
    day_level = div(div(local * state.day[0], state.flag[2]), 100)
    return base_level + day_level


def daily_defence_change(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@DAILY_DEFENCE_CHANGE`:378–453。"""
    st, out = ctx.state, ctx.out
    f = st.flag
    if check_gameover(st):
        f[852] = 0
        return
    if f[41] == 0:
        if f[41] == 0 and (f[2] != 2 or (mod(st.day[0], 2) == 0 and st.time == 0)):
            f[42] += 1
        out.drawline()
        out.printl()
        out.set_bold(True)
        out.printl("防衛力の変動　　")
        d = f[42] - f[52]
        if f[42] < f[52]:
            out.printl("　防衛設備が効果的に機能しています")
        elif f[42] < 2 + f[52]:
            out.printl(f"　危険度レベル{d}：まだ比較的安全です")
        elif f[42] < 3 + f[52]:
            out.printl(f"　危険度レベル{d}：まだ無視できるレベルです")
        elif f[42] < 5 + f[52]:
            out.printl(f"　危険度レベル{d}：触手の活動が活発化しています")
        elif f[42] < 7 + f[52]:
            out.printl(f"　危険度レベル{d}：あちこちで被害が多発中！")
        else:
            out.printl("　危険度レベルMAX：かなり危険な状態です！")
        out.set_bold(False)
        out.print(f"　防衛力( {f[852]} )　")
        if f[41] == 0:
            r = tentacle_level(st)
            if f[42] < f[52]:
                drop = 0
            elif f[42] < 2 + f[52]:
                drop = r + 5
            elif f[42] == 2 + f[52]:
                drop = div(f[852] * 1, 100) + r + 5
            elif f[42] == 3 + f[52]:
                drop = div(f[852] * 4, 100) + r + 10
            elif f[42] == 4 + f[52]:
                drop = div(f[852] * 8, 100) + r + 20
            elif f[42] == 5 + f[52]:
                drop = div(f[852] * 12, 100) + r + 40
            elif f[42] == 6 + f[52]:
                drop = div(f[852] * 15, 100) + r + 80
            elif f[42] == 7 + f[52]:
                drop = div(f[852] * 20, 100) + r + 160
            else:
                drop = div(f[852] * 50, 100) + r + 320
            out.print(f"−　時間経過( {drop} )　")
            f[852] = max(f[852] - drop, 0)
        else:
            f[42] = 0
        up = f[52] * f[52] * 5
        f[852] = f[852] + up
        if up:
            out.print(f"＋　防衛設備Lv{f[52]}( {up} )　")
        if (f[41] == 0 and not game_option(st, GameOption.SOLO)) or f[52]:
            out.print(f"＝　{f[852]}")
        out.printl()
    elif f[41] > 0:
        f[42] = 0


def daily_popularity_change(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@DAILY_POPULARITY_CHANGE`:456–588。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    f = st.flag
    rng = st.rng
    f[853] = limit(f[853], -100, 100)
    if check_gameover(st):
        return
    out.drawline()
    out.printl()
    out.set_bold(True)
    out.printl("人気度の変動　　")
    out.set_bold(False)
    out.print(f"　人気度( {f[853]} )　")
    before = f[853]
    # :471–505 一般評価（乱数判定の回数と符号）
    d = f[852]
    if d == 0:
        rolls = (-1, -1, -1)
    elif d < 1250:
        rolls = (-1, -1)
    elif d < 2500:
        rolls = (-1, +1)
    elif d < 5000:
        rolls = (+1,)
    elif d < 7500:
        rolls = (+1, +1)
    else:
        rolls = (+1, +1, +1)
    delta = sum(sign for sign in rolls if rng.rand(100) < 5)
    if delta < 0:
        out.print(f"−　一般評価( {abs(delta)} )　")
    if delta > 0:
        out.print(f"＋　一般評価( {delta} )　")
    f[853] = f[853] + delta
    # :512–525 処女ボーナス（ELSEIF の TALENT:変身時非処女 は TARGET のもの）
    tc = st.target_chara
    delta = 0
    for i in range(1, st.charanum):
        c = st.charas[i]
        if talent(data, c, "処女") > 0:
            if rng.rand(100) < 5:
                delta += 1
        elif (
            charatalent(data, c, 0, "オトコ") > 0
            and charatalent(data, c, 1, "オトコ") == 0
            and talent(data, tc, "変身時非処女") == 0
        ):
            if rng.rand(100) < 5:
                delta += 1
    if delta > 0:
        out.print(f"＋　処女ボーナス( {delta} )　")
    f[853] = f[853] + delta
    # :529–562 ファン人気
    delta = 0
    for i in range(1, st.charanum):
        c = st.charas[i]
        t = lambda n: talent(data, c, n)  # noqa: E731
        charm = c.exp[data.index_of("EXP", "魅了経験")]
        if charm >= 100:
            if rng.rand(100) < 5:
                delta += 1
            if charm >= 150 and rng.rand(100) < 5:
                delta += 1
            if charm >= 200 and rng.rand(100) < 5:
                delta += 1
        if t("清純派") > 0 and rng.rand(100) < 5:
            delta += 1
        if rng.rand(100) < min(div(c.cflag[284], 4), 10):
            delta += 1
        for name, p in (("母性的", 5), ("小悪魔", 5), ("目立ちたがり", 5), ("上品", 5), ("泣き虫", 5),
                        ("獣性の証", 5), ("人外の美貌", 10)):
            if t(name) > 0 and rng.rand(100) < p:
                delta += 1
    if delta > 0:
        out.print(f"＋　ファン人気( {delta} )　")
    f[853] = f[853] + delta
    # :564–572 悪いうわさ（CFLAG:825 は TARGET のもの）
    delta = 0
    for i in range(1, st.charanum):
        if rng.rand(50) < min(tc.cflag[825], 10):
            delta += 1
    if delta > 0:
        out.print(f"−　悪いうわさ( {delta} )")
    f[853] = f[853] - delta
    f[853] = limit(f[853], -100, 100)
    out.print(f"＝　{f[853]}　")
    if f[853] < before:
        out.print("(↓下降)")
    elif f[853] > before:
        out.print("(↑上昇)")
    else:
        out.print("(変動なし)")
    out.printl()
    out.drawline()
    out.printl()


# --- @EVENTSHOP（通常ターン）------------------------------------------------------------


def event_shop_normal(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@EVENTSHOP`:158–215（DAY != 0）。この後 SystemProc がオートセーブ → @SHOW_SHOP。"""
    st, out = ctx.state, ctx.out
    parasite(ctx)  # :160
    if config_check_event(st, 1) > 0:  # :162–163
        small_tentacle_hantei(ctx)
    birth_auto_random(ctx)  # :165
    st.flag[41] = 0  # :168–169
    st.flag[43] = 0
    st.time ^= 1  # :172 INVERTBIT TIME, 0
    recovery_over_time(ctx)  # :175
    out.drawline()  # :178
    if st.time == 0:
        st.day[0] += 1
        if st.day[0] > 1:
            out.printl("一日が終了しました")
            st.savestr[0] = ""
            if not check_gameover(st):
                calc_income_expend(ctx)
    else:
        out.printl("夜になりました")
        out.wait()
    st.savestr[20] = ""  # :193
    if check_gameover(st):  # :196–201
        st.flag[60] = 10001
    elif st.flag[101] > 0:
        st.flag[60] = 10000
    check_shield_all(ctx)  # :206
    st.target = st.flag[798]  # :209


def parasite(ctx: Ctx) -> None:
    """`FORCE_深夜の寄生触手暴走.ERB@PARASITE`:3–。ループで FLAG:799 を上書きする（:9、原作どおり）。"""
    st, data = ctx.state, ctx.data
    if config_check_maniac(st, 3) == 0:
        return
    for i in range(st.charanum):
        st.flag[799] = i
        if i == GameState.MASTER:
            continue
        if st.charas[i].cflag[999] == 0:
            continue
        if talent(data, st.charas[i], "寄生"):
            raise NotImplementedError("寄生触手（PARASITE:15–）は未移植")


def small_tentacle_hantei(ctx: Ctx) -> None:
    """`FORCE_深夜の子触手襲来.ERB@SMALL_TENTACLE_HANTEI`:8–74。"""
    st, out = ctx.state, ctx.out
    if charanum_active(st) == 0:
        return
    if not any(st.charas[i].cflag[999] and _ishole(ctx, i) for i in range(1, st.charanum)):
        return
    if st.time != 1:
        return
    local = st.flag[44] - sum(c.cflag[220] for c in st.charas)
    if local < 1:
        return
    saved = st.target
    d = st.flag[852]
    for bound, n in ((1000, 3), (2500, 4), (5000, 8), (10000, 16), (15000, 32), (20000, 64)):
        if d < bound + local * 50:
            l2 = st.rng.rand(n)
            break
    else:
        l2 = st.rng.rand(128)
    if l2 == 0 and st.rng.rand(12 - st.flag[52] * 2) != 0:
        _skip_event(ctx, "子触手襲来（SMALL_TENTACLE_ATTACK）")
    elif st.rng.rand(20) == 10:
        _skip_event(ctx, "子触手襲来（SMALL_TENTACLE_ATTACK）")
    elif st.rng.rand(local) >= 9:
        st.flag[44] -= 1
        out.drawline()
        if st.flag[52] and (st.rng.rand(st.flag[52]) != 0 or l2 != 0):
            out.printw("子触手は防衛システムに引っかかって黒焦げにされた...")
        elif st.rng.rand(2) == 0:
            out.printw("子触手は何かの動物に襲われた...")
        else:
            out.printw("子触手は迷子になった...")
    st.target = saved


def _printdata(ctx: Ctx, choices: tuple[str, ...]) -> str:
    """PRINTDATA 系：DATA の中から `GetNextRand(件数)` で 1 つ選ぶ
    （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@PRINT_DATA_Instruction:195–）。
    DATAFORM 先頭の全角空白は本文として残る（emuera.config:54「全角スペースをホワイトスペースに含める:NO」）。"""
    return choices[ctx.state.rng.rand(len(choices))]


def birth_auto_random(ctx: Ctx) -> None:
    """`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@BIRTH_AUTO_RANDOM`:606–746。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    if config_check_other(st, 2) > 0:  # :611–612 常時避妊
        return
    local = max(div(st.flag[852], 100), 2)  # :614–617（SIF LOCAL <= 2 → 2）
    born = 0
    if st.rng.rand(local) == 0 and st.flag[852] < 10000:  # :618–670
        out.drawline()
        born += 1
        out.printl("【避けられた悲劇】")
        if st.time == 0:
            if st.rng.rand(2) == 0:
                out.print(_printdata(ctx, ("　街のどこかで", "　公園の奥で", "　更衣室で着替えていた", "　体育倉庫で", "　下校中の")))
                out.print("少女が襲われ、")
            else:
                out.print(_printdata(ctx, ("　街のどこかで", "　公園の奥で", "　更衣室で着替えていた", "　帰宅中の")))
                out.print("女性が襲われ、")
        else:
            if st.rng.rand(2) == 0:
                out.print(_printdata(ctx, ("　街のどこかで", "　夜の公園で", "　塾帰りの", "　両親の帰りを待つ", "　自室で就寝中の")))
                out.print("少女が襲われ、")
            else:
                out.print(_printdata(ctx, ("　街のどこかで", "　深夜の公園で", "　夫の帰りを待つ", "　自室で就寝中の")))
                out.print("女性が襲われ、")
        out.printw(_printdata(ctx, (
            "何匹もの子触手が産み落とされたようだ...",
            "子触手を産まされながらアヘ顔を晒してしまったようだ...",
            "子宮を触手の繁殖袋にされてしまったようだ...",
            "触手の苗床にされてしまったようだ...",
            "衣服を残して行方不明になってしまったようだ...",
        )))
    # :671–742 苗床出産
    for i in range(1, st.charanum):
        c = st.charas[i]
        if c.cflag[0] == CharaState.DEAD and talent(data, c, "苗床化") and st.rng.rand(4) == 0:
            raise NotImplementedError("苗床出産（BIRTH_AUTO_RANDOM:675–）は未移植")
    if born > 0:  # :744–746
        st.flag[44] += born


# --- 回復・収支 ----------------------------------------------------------------------


def recovery_over_time(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@RECOVERY_OVER_TIME`:591–768。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    rng = st.rng
    f53 = st.flag[53]
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        c = st.charas[i]
        t = lambda n: talent(data, c, n)  # noqa: E731
        # :599–613
        if st.time == 0:
            l1 = 8
            if t("回復早い") == 1:
                l1 += 4
            elif t("回復遅い") == 1:
                l1 -= 4
            if st.flag[901]:
                l1 += 4
        else:
            l1 = 0
            if talent(data, st.target_chara, "夜魔の貴族") > 0:  # TALENT:夜魔の貴族（CCOUNT ではなく TARGET、原作どおり）
                l1 += 8
        l1 += {2: 2, 3: 4, 4: 6, 5: 8}.get(st.flag[51], 0)  # :615–625
        l1 = _fatigue_scale(l1, c.cflag[99])  # :628–639
        # :642–657
        if c.cflag[0] in (CharaState.IMPRISONED, CharaState.BRAINWASHED, CharaState.CORRUPTED, CharaState.DEAD):
            c.base[0] = 0
            c.base[1] = 0
            c.base[2] = 0
        else:
            for k in (0, 1, 2):
                c.base[k] = limit(div(c.maxbase[k] * l1, 100) + c.base[k], 0, c.maxbase[k])
        # :660–735 疲労度自動回復
        if c.cflag[99] > 0 and c.cflag[0] == CharaState.SAFE:
            local = 0
            if f53 & KANYOU and rng.rand(2) == 0:
                local += 1
            if f53 & FUUKEIGA and rng.rand(3) == 0:
                local += 1
            if f53 & OBJET and rng.rand(4) == 0:
                local += 1
            if f53 & FUNSUI and rng.rand(2) == 0:
                local += 1
            if f53 & MASSAGE_CHAIR:
                local += 1
            if f53 & BEAUTY_SALON:
                local += 2
            if c.cflag[100] == ActionPlan.TRAINING and f53 & SHOWER:
                local += 1
            if t("不老長寿") > 0 and st.time == 0:
                local += 1 + rng.rand(2) + rng.rand(2)
            if t("不老長寿") > 0 and st.time == 1:
                local += 1 + rng.rand(2)
            if c.cflag[99] <= 0:
                local = 0
            c.cflag[99] -= local
            if c.cflag[99] < 0:
                c.cflag[99] = 0
            if c.cflag[0] in (CharaState.BRAINWASHED, CharaState.CORRUPTED):
                if c.cflag[99] > 50:
                    c.cflag[99] = 50
            elif c.cflag[99] > 200:
                c.cflag[99] = 200
            if c.cflag[100] != ActionPlan.REST and local > 0:
                if c.cflag[99] == 0:
                    out.printl(f"{c.callname}の身体から疲労が完全に抜けた！")
                else:
                    out.printl(f"{c.callname}の身体から疲労が少し抜けた…")
            if t("繁殖袋") == 1:  # :709–717
                if rng.rand(25 - _charanum_actress(ctx) * 4) < 1:
                    out.printl("理性回復")
                    prefix = "仲間の献身的な治療による" if _charanum_actress(ctx) > 0 else "誰にも理由は分からないが、"
                    out.printl(f"{prefix}絆と愛の力なのかもしれない")
                    out.printl(f"廃人化していた{c.callname}の理性が奇跡的に回復した！")
                    c.talent[data.index_of("TALENT", "繁殖袋")] = 0
                    out.wait()  # FORCEWAIT
            kaimetsu = data.index_of("TALENT", "毀滅倒計時")  # :720–733
            if t("四肢欠損") < 1:
                c.talent[kaimetsu] = 0
            if c.talent[kaimetsu] > 0:
                c.talent[kaimetsu] += rng.rand(2) + 1  # RAND(1,3)（GameData/Function/Creator.Method.cs:953–972）
            if c.talent[kaimetsu] >= 15:
                st.target = i  # CALL AMPUTEE_EXECUTION はコメントアウトされている
        # :738–748 部位結界の回復（感覚数 = 4、DIM.ERH:154）
        for k in range(4):
            local = 0
            if c.cflag[0] == CharaState.SAFE:
                local = 3
                if c.cflag[100] == ActionPlan.REST:
                    local += 3
            local = div(c.maxbase[30 + k] * local, 100)
            if c.base[30 + k] > 0:
                c.base[30 + k] = limit(c.base[30 + k] + local, 0, c.maxbase[30 + k])
        # :751–755
        if t("社交的") > 0 and rng.rand(100) < 4 + isqrt(c.exp[data.index_of("EXP", "魅了経験")]):
            c.cflag[285] += 1
        if t("小心者") > 0 and rng.rand(100) < 8 and c.cflag[285] > 0:
            c.cflag[285] -= 1
        if c.cflag[241] > 0:  # :758–759
            c.cflag[241] -= 1
        c.cflag[400] = 0  # :761
        if st.time == 0:  # :763–766
            estrus_cycle(ctx, i)


def _charanum_actress(ctx: Ctx) -> int:
    """`汎用関数/CHARANUM.ERB@CHARANUM_ACTRESS`:29–36。"""
    st, data = ctx.state, ctx.data
    n = st.charanum - 1
    for c in st.charas[1:]:
        if c.cflag[0] != 0 or talent(data, c, "四肢欠損") or talent(data, c, "繁殖袋"):
            n -= 1
    return n


def estrus_cycle(ctx: Ctx, who: int) -> None:
    """`ヒロイン関連/ESTRUS_CYCLE.ERB@ESTRUS_CYCLE`:49–65。"""
    c = ctx.state.charas[who]
    abnormal = talent(ctx.data, c, "排卵異常")
    if c.cflag[217] > 0:
        if c.cflag[217] <= 29 - abnormal * 2:
            c.cflag[217] += 1
        else:
            c.cflag[217] = 1 + abnormal * 2
    else:
        c.cflag[217] = 1 + ctx.state.rng.rand(29)


def calc_income_expend(ctx: Ctx) -> None:
    """`SHOP_TURNEND.ERB@CALC_INCOME_EXPEND`:771–847。"""
    st, data, out = ctx.state, ctx.data, ctx.out
    day = st.day[0]
    if day == 7:
        out.printw("国から支援表明の通知が届きました。")
        out.printw("これからは一週間ごとに政府からの支援と市民からの義援金が届きます。")
        out.printw("防衛成果に応じて金額が増えるので、防衛力に注意しましょう。")
        out.printl()
        out.printl("最初の資金援助が届いています。")
        out.printw()
    elif day == 21:
        out.printl("国からの援助金が増額されました。")
        out.printw()
    elif day == 42:
        out.printl("不況の影響で、国からの援助金が大幅に減額されました。")
        out.printw()
    elif day == 63:
        out.printl("不況の影響で、国からの援助金が打ち切られました。")
        out.printw()
    if mod(day, 7) == 0:  # :795–829
        f852, f853 = st.flag[852], st.flag[853]
        gov = 1000 + div(f852 + 1, 25)
        l1 = st.rng.rand(div(f852 + 1, 10) + 50) + 10
        if f853 <= -50:
            l2 = 0
        elif f853 <= -25:
            l2 = 200
        elif f853 < 0:
            l2 = 600
        elif f853 < 25:
            l2 = 1200
        elif f853 < 50:
            l2 = 1800
        elif f853 < 75:
            l2 = 3600
        else:
            l2 = 7200
        charm_no = data.index_of("EXP", "魅了経験")
        for c in st.charas[1:]:
            charm = c.exp[charm_no]
            if charm > 100:
                l2 += isqrt(max(charm - 100, 0)) * 500 + st.rng.rand(charm)
        if day >= 21:
            gov += 800
        if day >= 42:
            gov = div(gov, 4)
        if day >= 63:
            gov = 0
        if day < 63:
            out.printl(f"政府からの援助金として資金${gov}を得た！")
        out.printl(f"市民からの義援金として資金${l1 + l2}を得た！")
        st.money += gov + l1 + l2
    # :832–847 支出
    cost = 40 + 20 * charanum_safe(st)
    if game_option(st, GameOption.HARDCORE):
        cost *= 3
    if st.money >= cost:
        out.printl(f"維持費や生活費として資金${cost}を支払った。")
        st.money -= cost
        out.wait()
    else:
        out.printl("維持費や生活費のための資金が不足しています！")
        out.printl("体力と気力を消耗しました……")
        out.wait()
        st.money = 0
        for c in st.charas:
            c.base[0] = times(c.base[0], "0.8")
            c.base[1] = times(c.base[1], "0.8")


def check_shield_all(ctx: Ctx) -> None:
    """`汎用関数/コモン関数.ERB@CHECK_SHIELD_ALL`:659–670。"""
    st = ctx.state
    for i in range(st.charanum):
        if i == GameState.MASTER:
            continue
        c = st.charas[i]
        for k in range(4):
            if c.talent[190 + k] == 0:
                c.maxbase[30 + k] = 0
            c.base[30 + k] = limit(c.base[30 + k], 0, c.maxbase[30 + k])
