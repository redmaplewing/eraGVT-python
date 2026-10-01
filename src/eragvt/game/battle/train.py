"""戦闘（TRAIN）の流れ：`BEGIN TRAIN` から `BEGIN AFTERTRAIN`／`@EVENTEND` まで。

路徑相對 `source/earGVP/ERB/`。エンジン側の流れ（reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs）：

- `beginTrain`:249–258：`UpdateInBeginTrain`（VariableEvaluator.cs:1422–1462）→ `@EVENTTRAIN`
- `endCallEventTrain`:266–292：NEXTCOM < 0 なら `@SHOW_STATUS`
- `endCallShowStatus`／`endCallComAbleXX`:294–354：Train.csv の各 COM_ABLE を呼び、RESULT≠0 のものを
  `名前[番号]` で表示して選択肢に加える。本作の COM_ABLE はすべて `TCVARn:8 < 10` の間 0 を返す
  （`戦闘コマンド(ヒロイン)/COMABLE.ERB` 各関数の末尾 `SIF TCVARn:8 < 10 / RETURN 0`）ので、エンジンの選択肢は空。
- `endCallShowUserCom`:356–378：`UpdateAfterShowUsercom`（UP／DOWN／LOSEBASE を 0）→ 入力待ち
- `trainWaitInput`:395–427：選択肢が空なので入力値はそのまま RESULT として `@USERCOM` へ。
- `@USERCOM` の `DOTRAIN` → `doTrain`:430–436（ScriptProc.cs:865–894）→ `callEventCom`:438–444
  （`UpdateAfterInputCom` で全キャラの NOWEX を 0）→ `@EVENTCOM` → `@COM{n}` → RESULT≠0 なら
  `@SOURCE_CHECK` → `UpdateAfterSourceCheck` → `@EVENTCOMEND`（中で WAIT が無ければ WAIT を 1 つ足す：:476、515–517）
  → `@SHOW_STATUS` へ戻る。`@USERCOM` がそれ以外で終わった場合も `endCallEventComEnd`:485–520 から
  `@SHOW_STATUS` へ戻る（EVENTCOMEND は呼ばれない）。
- `BEGIN AFTERTRAIN` → `beginAfterTrain`:524–534 → `@EVENTEND`（after.py）。
"""

from __future__ import annotations

from collections.abc import Generator

from ...state import GameState
from ..action import Ctx, Step, config_check_event, config_check_screen, print_callname, print_transcallname
from ...state.constants import GameOption
from ..era import div, format_curly, format_percent, isqrt, limit
from ..opening import game_option
from ..shop import _bar
from ..tentacle import enemy_type_check, tentacle_survive_num
from .cheers import perform_cheers_first_hantei
from .cloth import cloth_battle_hosei, cloth_battle_sethp, refresh_cloth_data
from .commands import com_able, print_comname, run_com
from .core import (
    is_penis,
    msg_other,
    BETOBETO,
    DARAKU,
    HAIRAN,
    HATUJOU,
    KAIRAKU_TOROKE,
    KIZETU,
    KOSHIKUDAKE,
    KOUKOTSU,
    KUSEN,
    KYOUKOUSOKU,
    MAHI,
    P_NORMAL,
    PALAM_END,
    SEI_TEIKOU,
    ZETSUBOU,
    BeginAfterTrain,
    config_check_balance,
    get_battle_situation,
    get_local,
    message_branch,
    palamlv,
    percent_cal,
    print_distance,
    set_local,
    shinkyou_change,
    shinkyou_check,
    t,
    tc,
    tentacle_access,
    tentacle_level,
    unlock_achievement,
)
from .enemy import select_enemy_action, select_tentacle_action
from .func import calc_chisei_shien, check_can_retreat, kojo, transform
from .hantei import act_hantei_tettai_tentacle
from .source_check import source_check

TCRLENGTH = 100  # ゲーム内_戦闘処理/REPORT.ERH:3
# DIM.ERH:16–19 戦闘系 TFLAG の別名は使わず番号で書く。


# --- エンジン：UpdateInBeginTrain ----------------------------------------------------


def update_in_begin_train(st: GameState) -> None:
    """reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs@UpdateInBeginTrain:1422–1462。

    ASSIPLAY=0、PREVCOM=NEXTCOM=-1、TFLAG／TSTR を 0、全キャラの GOTJUEL・TEQUIP・EX・PALAM・SOURCE・TCVAR を 0、
    STAIN を既定値に（setDefaultStain：ConfigData.cs:134 の既定 {0,0,2,1,8}、_Replace.csv で上書きなし）。
    本作で建模していない ASSIPLAY／TSTR／GOTJUEL／TEQUIP／SOURCE／TCVAR（TCVARn とは別）は省略。
    """
    st.temp.prevcom = -1
    st.temp.nextcom = -1
    st.tflag.clear()
    for c in st.charas:
        c.ex.clear()
        c.palam.clear()
        c.stain.clear()
        for i, v in enumerate((0, 0, 2, 1, 8)):
            c.stain[i] = v


# --- @EVENTTRAIN（BATTLE_TRAIN.ERB:4–240）-------------------------------------------


def event_train(ctx: Ctx) -> None:
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    v = c.tcvarn
    name = print_callname(st, st.target)  # %CALLNAME%（TARGET）
    # :16–29
    if st.flag[45] == 0:
        st.temp.battle_situation = ""  # INITBATTLESITUATION（特殊シチュエーション.ERB:41–42）
        v.clear()  # VARSET TCVARn（CHARADATA 変数の VARSET は TARGET のみ：VariableEvaluator.cs:75–101）
        st.temp.turn_limit = 15 if st.flag[10] == 2 else 50
        v[0] = 0 if st.flag[73] > 0 else 3
    else:
        raise NotImplementedError("イベント戦闘（FLAG:45）は未移植")
    # :31–33
    for i in range(TCRLENGTH):
        st.temp.tcreport[i] = 0
    # :35–45
    st.tflag[6] = 0
    st.tflag[16] = -1
    st.tflag[17] = -1
    st.temp.ex_com = 0
    st.temp.sh_com = 0
    st.temp.insert = 0
    st.temp.tentacle_size.clear()
    st.temp.tentacle_num.clear()
    # :48–61 MESSAGE_BRANCH_F（副作用・乱数なし）
    mb = message_branch(ctx)
    for bit in (DARAKU, KAIRAKU_TOROKE, ZETSUBOU, SEI_TEIKOU, KUSEN):
        if mb & bit:
            st.tflag[97] |= bit
    # :64
    st.temp.max_palam.clear()
    # :67–68
    c.base[20] = 0
    c.base[21] = 0
    # :72–83 空中ダッシュ
    if cloth_battle_hosei(ctx, "AIRPLUS", st.target) > 0:
        c.maxbase[22] += 1
    if c.cflag[43] == 510:
        c.maxbase[22] += 1
    if t(ctx, c, "有翼") > 0:
        c.maxbase[22] += 1
    c.base[22] = c.maxbase[22]
    if c.base[22] >= 8:
        c.base[22] = 8
    # :86–91
    if t(ctx, c, "魔力貯蔵") > 0:
        out.set_color((255, 128, 0))
        out.printw(f"[魔力貯蔵]の効果で{name}のEXゲージが2つチャージされた！")
        out.reset_color()
        v[4] += 200
    # :94–99
    if st.flag[45] == 0:
        cloth_battle_sethp(ctx)
        refresh_cloth_data(ctx)
    # :103–128 特殊シチュエーション（通常戦闘では空文字列）
    if get_battle_situation(st, "強制発情") == 1:
        v[12] |= HATUJOU
        out.printw(f"{name}は抑えきれないほど発情している……")
    if get_battle_situation(st, "強制麻痺") == 1:
        v[12] |= MAHI
        out.printw(f"{name}の全身が痺れ、自由に動けない……")
    if get_battle_situation(st, "強制全裸") == 1:
        c.cflag[40] = 0
        if c.cflag[41] != 402:
            c.cflag[41] = 0
        if c.cflag[42] != 400:
            c.cflag[42] = 0
        c.cflag[43] = 0
        out.printw(f"{name}は裸で敵と戦うしかない…")
    if get_battle_situation(st, "強制拘束") == 1:
        v[0] = 0
        out.printw(f"{name}は力ずくで戦闘に引きずり込まれた……")
    if get_battle_situation(st, "強制挿入") == 1:
        v[0] = 0
        v[12] |= KYOUKOUSOKU
        out.printw(f"{name}がっちりと巻き上げられ、強引に戦闘に引きずり込まれていく…。")
    # :132–136
    if enemy_type_check(st, "AKUOTI") == 1:
        select_enemy_action(ctx)
    else:
        select_tentacle_action(ctx)
    # :139
    st.flag[700] = 1
    # :142–148 解析度
    if enemy_type_check(st, "BOSS") == 1:
        st.flag[20] = st.flag[500 + st.flag[11]]
    elif enemy_type_check(st, "LASTBOSS") >= 1:
        st.flag[20] = st.flag[600 + st.flag[11]]
    elif enemy_type_check(st, "MOB") == 1:
        st.flag[20] = 100
    # :151–166
    chisei_sum = calc_chisei_shien(ctx, 0)
    if enemy_type_check(st, "AKUOTI") == 1:  # :156–162
        chisei_enemy = max(st.charas[st.flag[111]].maxbase[13], 100)
    else:
        chisei_enemy = int(tentacle_access(ctx, "CHISEI"))
    if percent_cal(chisei_sum, chisei_enemy) >= 200:
        unlock_achievement(ctx, 268, "タクティカルオーダー")
    # :169–207 先制攻撃
    initiative_loop(ctx, initiative_rate(ctx, chisei_sum, chisei_enemy))
    # :208–236
    if st.tflag[24] > 0:
        if t(ctx, c, "精霊交信") > 0:
            out.set_color((255, 128, 0))
            out.printw("[精霊交信]の効果で先制率が上昇！")
            out.reset_color()
        if t(ctx, c, "狩人の勘") > 0:
            out.set_color((255, 128, 0))
            out.printw("[狩人の勘]の効果で先制率が上昇！")
            out.reset_color()
        out.printl()
        out.set_bold(True)
        out.print("　先制攻撃")
        if st.tflag[24] > 1:
            out.print(f"(+{st.tflag[24] - 1})")
        out.print("！ ")
        out.set_bold(False)
        if st.tflag[24] == 1:
            out.printw("敵はこのターン動けない！")
        else:
            out.printw(f"敵は{st.tflag[24]}ターンの間動けない！")
        out.printl()
    elif config_check_event(st, 3) > 0 and st.flag[73] == 0:
        perform_cheers_first_hantei(ctx)
    # :239–240
    if t(ctx, c, "変身能力") != 1 and config_check_screen(st, 2) > 0:
        v[8] = 1


def initiative_rate(ctx: Ctx, chisei_sum: int, chisei_enemy: int) -> int:
    """`@EVENTTRAIN`:169–189 先制率。"""
    st = ctx.state
    c = tc(ctx)
    initiative = min(isqrt(c.exp[0]), 20) + min(isqrt(percent_cal(chisei_sum, chisei_enemy)), 25) + 5
    survive = tentacle_survive_num(st)
    if st.flag[3] == survive:
        initiative += 15
    if st.flag[3] - 1 == survive:
        initiative += 15
    if t(ctx, c, "精霊交信") > 0:
        initiative += 15
    if t(ctx, c, "狩人の勘") > 0:
        initiative += 15
    if enemy_type_check(st, "MOB") == 1 and st.flag[73] == 0:
        initiative *= 2
    if get_battle_situation(st, "市民確定") or get_battle_situation(st, "先制無し"):
        initiative = 0
    return initiative


def initiative_loop(ctx: Ctx, initiative: int) -> None:
    """`@EVENTTRAIN`:192–207 `$INITIATIVE_LOOP`：成功するたびに TFLAG:24 を 1 増やし、確率を 3/4 にして再判定。"""
    st, out = ctx.state, ctx.out
    while True:
        if st.flag[73] > 0:
            initiative = 0
        if st.flag[999] > 0 and st.flag[73] == 0:
            out.set_color((105, 105, 105))
            out.printl()
            out.printl(f"　先制率　{initiative}％")
            out.printl()
            out.reset_color()
        if st.rng.rand(100) < initiative:
            st.tflag[24] += 1
            initiative = div(initiative * 3, 4)
            if initiative > 0:
                continue
        break


# --- @SHOW_STATUS（BATTLE_SHOW_STATUS.ERB:3–351）-------------------------------------


def status_charge_limit(ctx: Ctx) -> int:
    """`ヒロイン関連/CHARA_STATUS.ERB@STATUS_PRINT_CHARGE`:1477–1489 の代入部：消耗度（体力＋気力＋疲労度×150）で
    TCVARn:206（[反撃]バーストの蓄積ダメージ限度値）を決める。表示部（:1491–1525）は省略（deviations「戦闘画面の簡略表示」）。"""
    c = tc(ctx)
    p = percent_cal(c.base[0] + c.base[1] + c.cflag[99] * 150, c.maxbase[0] + c.maxbase[1])
    local = 80 if 0 <= p <= 39 else 100 if 40 <= p <= 74 else 120  # SELECTCASE 0 TO 39／40 TO 74／CASEELSE
    c.tcvarn[206] = div(c.maxbase[0] * local, 100)
    return c.tcvarn[206]


def show_status(ctx: Ctx) -> None:
    """`@SHOW_STATUS` の簡略表示。

    DEVIATION（表示のみ）：原作の SHOW_STATUS（BATTLE_SHOW_STATUS.ERB:3–351、CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:18–、
    SHOW_TRAIN_PALAM_STATUS、CLOTH_BATTLE_DISPHP、SHOW_DISTANCE_WINDOW）は COLOR_BAR 等を多用するため、同じ情報の一部を
    単純なバーと文字で表示する（deviations.md「戦闘画面の簡略表示」）。SHOW_STATUS とその下位関数には
    RAND が無く、代入は STATUS_PRINT_CHARGE（CHARA_STATUS.ERB:1477–1489、SHOW_STATUS_BASE_DISPBATTLE:205 から
    毎回無条件に呼ばれる）の TCVARn:206（蓄積ダメージ限度値）だけ（S16 で確認・移植：`status_charge_limit`）。
    例外は SHOW_TRAIN_PALAM_STATUS（CHARA_STATUS.ERB:1715–1750）→ SHOW_STATUS_PALAM（BATTLE_SHOW_STATUS.ERB:353–）→
    PRINTFORM_GAPING_NOW（GAPING.ERB:789–：CFLAG:35／36 の初期値代入と V_GAPING／A_GAPING の RAND）で、
    CONFIG_CHECK_SCREEN_F(5) == 1（FLAG:801 bit 5）のときだけ呼ばれる。既定（FLAG:801 = 1）では呼ばれず、
    コンフィグ画面が未移植なので到達しないが、到達したら停止する（S11）。
    """
    st, data, out = ctx.state, ctx.data, ctx.out
    if config_check_screen(st, 5) == 1:
        raise NotImplementedError("調教ステータス表示（SHOW_TRAIN_PALAM_STATUS、FLAG:801 bit 5）は未移植")
    status_charge_limit(ctx)  # 表示より前に置いても結果は同じ（表示部に代入なし）
    c = tc(ctx)
    v = c.tcvarn
    out.reset_color()
    out.drawline()
    out.printl()
    head = f"{c.name if c.cflag[1] == 0 else print_transcallname(st, st.target)} Lv.{c.abl[data.index_of('ABL', 'レベル')]}"
    if t(ctx, c, "変身能力") == 1 and c.cflag[1] == 0:
        head += "　<<未変身>>"
    out.printl(head)
    for label, idx in (("体力", 0), ("気力", 1), ("性耐性", 2)):
        _bar(out, label, c.base[idx], c.maxbase[idx])
        out.printl()
    # EX ゲージ（TCVARn:4、SP 変身中は TCVARn:5）
    if c.cflag[1] == 2:
        out.printl(f"S.P.　（{v[5]}/500）")
    else:
        out.printl(f"E.X.　（{v[4]}/500）")
    # :18–66 状態
    out.print("状態　　　")
    if c.cflag[1] == 1:
        out.print("[変身]")
    if c.cflag[1] == 2:
        out.print("[SP変身]")
    if v[40] > 0:
        out.print("[絶頂禁止]")
    if c.cflag[99]:
        out.print(f"[疲労 {c.cflag[99]}]")
    if st.flag[70]:
        out.print(f"[観衆 {st.flag[70]}人]")
    if st.flag[71]:
        out.print(f"[動画撮影者 {st.flag[71]}人]")
    for bit, label in ((KIZETU, "気絶"), (HAIRAN, "排卵"), (HATUJOU, "発情"), (MAHI, "麻痺"), (BETOBETO, "べとべと"),
                       (KOSHIKUDAKE, "腰くだけ"), (KOUKOTSU, "恍惚")):
        if v[12] & bit:
            out.print(f"[{label}]")
    out.printl()
    # :134–137
    out.print("心境　　　")
    shinkyou_check(ctx, "PRINT", 0)
    out.printl()
    out.printl()
    akuoti = enemy_type_check(st, "AKUOTI") == 1
    if not akuoti:  # :145–156
        tentacle_access(ctx, "NAME")
        if enemy_type_check(st, "BOSS") == 1:
            out.print("(ＢＯＳＳ)")
        elif enemy_type_check(st, "LASTBOSS") >= 1:
            out.print("(ＬＡＳＴ)")
        elif enemy_type_check(st, "MOB") == 1:
            out.print("(ＭＯＢ)")
        out.printl(f" Lv.{tentacle_level(st)} ")
    else:  # :157–174 対キャラ
        e = st.charas[st.flag[111]]
        if e.cflag[0] == 2:  # 状態_洗脳
            out.print(f"洗脳された{print_transcallname(st, st.flag[111])}[")
            from ..prison.event import tentacle_access_prison

            tentacle_access_prison(ctx, st.flag[111], "NAME")
            out.print("]")
        elif e.cflag[0] == 3:  # 状態_悪堕ち
            if e.cstr[55] != "":
                from ..action import print_transname

                out.print(f"《{print_transname(st, st.flag[111])}》{e.name}")
            else:
                out.print(f"悪堕ちした{print_transcallname(st, st.flag[111])}")
        out.printl(f" Lv.{e.abl[ctx.data.index_of('ABL', 'レベル')]} ")
    # 距離（SHOW_DISTANCE_WINDOW の代わりに PRINT_DISTANCE）
    out.print("距離　　　")
    print_distance(ctx)
    out.printl()
    # :232–242
    lim_ = st.temp.turn_limit
    if lim_ > 0:
        out.printl(f"残り時間　（{format_curly(lim_ - st.tflag[0], 5)}/{format_curly(lim_, 5)}）")
    else:
        out.printl("残り時間　（-----/-----）")
    # :256 COLORSENTENCE_ENEMYBAR（コモン関数.ERB:146–190）：解析度 50％未満は現在値、25％未満は最大値を伏せる
    known_cur = st.flag[999] == 1 or st.flag[20] >= 50
    known_max = st.flag[999] == 1 or st.flag[20] >= 25
    cur = format_curly(st.flag[13], 5) if known_cur else "？？？"
    mx = format_curly(st.flag[12], 5) if known_max else "？？？"
    out.print(f"{ctx.data.str_defaults.get(2500, '')}体力（{cur}/{mx}）")
    # :258–265
    if st.tflag[2] >= 1:
        out.print("　<<油断中>> ")
    elif st.flag[20] >= 100 or akuoti:
        out.print(f"　(油断度：{div(st.flag[17] * 100, st.flag[16])}％) ")
    elif st.tflag[24] > 0:
        out.print(f"先制攻撃可能！(残り{st.tflag[24]}ターン)")
    out.printl()
    # :274–276
    # :269–284 射精ゲージの見出し（悪堕ちキャラはペニスか寄生があれば「敵射精」、無ければ「敵絶頂」）
    if akuoti:
        e = st.charas[st.flag[111]]
        head = "敵射精" if (is_penis(ctx, st.flag[111]) or t(ctx, e, "寄生") > 0) else "敵絶頂"
    else:
        head = f"{ctx.data.str_defaults.get(2500, '')}射精"
    out.printl(f"{head}（{format_curly(st.flag[15], 5) if known_cur else '？？？'}/"
               f"{format_curly(st.flag[14], 5) if known_max else '？？？'}）")
    if akuoti:  # :319–328
        e = st.charas[st.flag[111]]
        out.printl(f"攻：{e.maxbase[10]:>3} 防：{e.maxbase[11]:>3} 敏：{e.maxbase[12]:>3} 知：{e.maxbase[13]:>3} ")
        out.printl(f"近：{e.abl[30]:>3} 中：{e.abl[31]:>3} 遠：{e.abl[32]:>3} ")
    # :286–331
    elif st.flag[999] == 1 or st.flag[20] >= 75:
        vals = [max(int(tentacle_access(ctx, k)), 0) for k in ("KOUGEKI", "BOUGYO", "BINSYOU", "CHISEI")]
        out.printl(f"攻：{vals[0]:>3} 防：{vals[1]:>3} 敏：{vals[2]:>3} 知：{vals[3]:>3} ")
        if st.flag[20] >= 100:
            out.printl(
                f"近：{int(tentacle_access(ctx, 'SHORT')):>3} 中：{int(tentacle_access(ctx, 'MIDDLE')):>3} "
                f"遠：{int(tentacle_access(ctx, 'LONG')):>3} 捕：{tentacle_access(ctx, 'HOLD')} "
            )
        else:
            out.printl(f"解析度：{st.flag[20]}％")
    else:
        out.printl(f"解析度：{st.flag[20]}％")
    # :335–349
    if config_check_screen(st, 2) > 0:
        return
    out.drawline()
    if v[0] == 0:
        if v[12] & KYOUKOUSOKU:
            out.set_color((200, 50, 50))
            out.print("  <<強拘束>>")
        else:
            out.set_color((255, 146, 238))
            out.print("  <<拘束中>>")
        out.reset_color()
        out.printl()


# --- @SHOW_USERCOM（BATTLE_COM.ERB:4–568：カテゴリ分けしない表示＝:379–568）-------------------


def _forecast_color(value: int) -> tuple[int, int, int]:
    """`FORECAST.ERB@FORECAST_OUTPUT_SETCOLOR(ARG, "COM")`:344–367。"""
    if value == -1:
        return (128, 128, 128)
    r = 0 if value <= 60 else limit(-105 + div(40 * value, 10), 55, 255)
    if value <= 50:
        g = limit(55 + div(40 * value, 10), 55, 255)
    elif value >= 80:
        g = 0
    else:
        g = limit(455 - div(35 * value, 10), 55, 255)
    b = 0 if value >= 40 else limit(255 - div(40 * value, 10), 55, 255)
    return (r, g, b)


def _forecast_line(ctx: Ctx) -> None:
    """:453–462／:486–495 の《危険度》表示。"""
    out = ctx.out
    v = tc(ctx).tcvarn
    for i, k in enumerate((30, 31, 32)):
        out.set_color(_forecast_color(v[k]))
        text = "《危険度:" + (str(v[k]) if v[k] >= 0 else "??") + "》"
        out.print(format_percent(text, 22, left=False))
        if i < 2:
            out.print_plain("　 ")
    out.reset_color()
    out.printl()


def show_usercom(ctx: Ctx) -> None:
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    v = c.tcvarn
    out.reset_color()
    out.printl()
    if config_check_screen(st, 2) > 0:
        raise NotImplementedError("コマンドのカテゴリ分け表示（CONFIG_CHECK_SCREEN_F(2)）は未移植")
    v[8] += 10  # :380
    if v[0] == 0:
        _show_usercom_restraint(ctx)
    else:
        _show_usercom_normal(ctx)
    v[8] -= 10  # :554
    out.print("　 ステータス表示[800]")
    if check_can_retreat(ctx) == 0:
        out.set_color((128, 128, 128))
    if _can_try_retreat(ctx):
        out.print("　　　　　　　　撤退[999]")
    out.reset_color()
    v[8] += 10
    out.print_plain("　 ")
    print_comname(ctx, 99)
    v[8] -= 10
    out.printl()


def _show_usercom_restraint(ctx: Ctx) -> None:
    """BATTLE_COM.ERB:382–441 拘束されている最中のコマンド。"""
    out = ctx.out
    v = tc(ctx).tcvarn
    sp = "　 "

    def row(ns: tuple[int, ...], seps: tuple[str, ...]) -> None:
        for n, sep in zip(ns, seps):
            print_comname(ctx, n)
            if sep:
                out.print_plain(sep)
        out.printl()

    print_comname(ctx, 11)
    out.printl()
    out.printl()
    row((40 if v[12] & KYOUKOUSOKU else 8, 9, 10), (sp, sp, sp))
    row((12, 13, 14), (sp, sp, sp))
    for n in (44, 45, 46):  # :408 FOR LOCAL,44,47（終値は含まない）
        if com_able(ctx, n)[0]:
            print_comname(ctx, n)
            out.print_plain(sp)
    out.printl()
    row((70, 71, 72), (sp, sp, "　"))  # :421 だけ末尾の半角空白なし
    row((100, 101, 102), (sp, sp, ""))
    row((103, 104, -1), (sp, sp, ""))
    row((15, -1), (sp, ""))


def _show_usercom_normal(ctx: Ctx) -> None:
    """BATTLE_COM.ERB:444–548 通常時のコマンド。"""
    out = ctx.out
    v = tc(ctx).tcvarn
    if com_able(ctx, 0)[0]:
        if com_able(ctx, 201)[0]:
            _forecast_line(ctx)
            print_comname(ctx, 201)
            out.print_plain("　 ")
            print_comname(ctx, 202)
            out.print_plain("　 ")
            print_comname(ctx, 203)
            out.printl()
            out.print("　　　         ----------------------------------------------")
        else:
            print_comname(ctx, 0)
        out.printl()
    else:
        if com_able(ctx, 11)[0]:
            print_comname(ctx, 11)
            out.printl()
        else:
            _forecast_line(ctx)
    for row in ((1, 2, 3), (6, 7, 5)):
        for i, n in enumerate(row):
            print_comname(ctx, n)
            if i < 2:
                out.print_plain("　 ")
        out.printl()
    out.printl()
    print_comname(ctx, 4)
    out.print_plain("　 ")
    print_comname(ctx, 16)  # FORECAST_OUTPUT_SETCOLOR(TCVARn:33) の色は PRINT_COMNAME 内の SETCOLOR で上書きされうる
    out.print_plain("　 ")
    print_comname(ctx, 17)
    out.printl()
    print_comname(ctx, 73 if com_able(ctx, 73)[0] else 70)
    out.print_plain("　 ")
    print_comname(ctx, 71)
    out.print_plain("　 ")
    print_comname(ctx, 72)
    out.printl()
    print_comname(ctx, 74)
    out.print_plain("　 ")
    print_comname(ctx, -1)
    out.print_plain("　 ")
    if com_able(ctx, 69)[0]:
        print_comname(ctx, 69)
    out.printl()
    out.printl()
    out.printl()


def _can_try_retreat(ctx: Ctx) -> bool:
    """:560／:573 `(TCVARn:0 > 0 && GETBATTLESITUATION("撤退不可") == 0 && (TCVARn:12 & 気絶) == 0) || FLAG:999 == 1`。"""
    st = ctx.state
    v = tc(ctx).tcvarn
    return (v[0] > 0 and get_battle_situation(st, "撤退不可") == 0 and (v[12] & KIZETU) == 0) or st.flag[999] == 1


# --- @USERCOM（BATTLE_COM.ERB:572–664）------------------------------------------------


def _my_action_header(ctx: Ctx) -> None:
    out = ctx.out
    out.printl()
    out.set_bold(True)
    out.set_color((0, 255, 150))
    out.printl("********** 自分の行動 **********")
    out.reset_color()
    out.set_bold(False)
    out.printl()


def _msg_tettai_success(ctx: Ctx) -> None:
    """`地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_TETTAI_SUCCESS`:376–387。"""
    st, out = ctx.state, ctx.out
    out.printl(f"分が悪いと見た{print_transcallname(st, st.target)}は大きく後退し、")
    if st.flag[70] + st.flag[71]:
        out.printl("避難誘導をしながらその場から撤退した・・・")
    elif t(ctx, tc(ctx), "主観視点") > 0:
        out.printl("すぐさまその場から撤退した・・・")
    else:
        out.printl("悔しさを噛み殺しながらその場から撤退した・・・")
    kojo(ctx, "BATTLE_CHARA_TETTAI_SUCCESS")
    out.printw()


def _msg_tettai_false(ctx: Ctx) -> None:
    """`MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_TETTAI_FALSE`:390–401。"""
    st, out = ctx.state, ctx.out
    if st.flag[70] + st.flag[71] > 0:
        out.printl("周りの一般人の避難が完了していないため、撤退できませんでした")
    elif enemy_type_check(st, "AKUOTI") == 0:
        out.printl(f"複数の{ctx.data.str_defaults.get(2500, '')}に回り込まれて逃げられない！！")
    else:
        out.printl(f"しかし一足先に動いた{print_transcallname(st, st.flag[111])}に素早く回り込まれてしまった！！")
    if st.flag[70] + st.flag[71] == 0:
        kojo(ctx, "BATTLE_CHARA_TETTAI_FALSE")
    out.printw()


def usercom(ctx: Ctx, value: int) -> Generator[None, int, None]:
    st, out = ctx.state, ctx.out
    v = tc(ctx).tcvarn
    if value == 999 and _can_try_retreat(ctx):  # :573–625
        if not check_can_retreat(ctx):
            return
        _my_action_header(ctx)
        akuoti = enemy_type_check(st, "AKUOTI") == 1  # :584 / :605（悪堕ち側は KYUSHUTU_SUCCESS_HANTEI なし）
        if act_hantei_tettai_tentacle(ctx) == 1:
            _msg_tettai_success(ctx)
            if akuoti:
                msg_other(ctx, "BATTLE_CHARA_TETTAI_SUCCESS")
            elif st.tflag[19] == 1:  # :593 TRYCALL KYUSHUTU_SUCCESS_HANTEI（COMF15.ERB:70–73）
                from .restraint import kyushutu_success

                kyushutu_success(ctx)
            raise BeginAfterTrain
        _msg_tettai_false(ctx)
        if akuoti:
            msg_other(ctx, "BATTLE_CHARA_TETTAI_FALSE")
        yield from source_check(ctx)  # JUMP SOURCE_CHECK
        return
    if value == 999:
        return
    if value == 800:  # :626–628
        out.drawline()
        # DEVIATION（表示のみ）：SHOW_STATUS_CHARA_SELECT（ステータス画面、5 ページ）は未移植
        out.printl("（ステータス画面は未移植です）")
        return
    if value in (810, 820, 830):  # :629–634
        v[8] = {810: 0, 820: 1, 830: 2}[value]
        return
    if value == 898:  # :636–637
        st.flag[801] ^= 1 << 8
        return
    if value == 899:  # :638–639
        st.flag[801] ^= 1 << 6
        return
    if value == 400:  # :641–655（デバッグモード切替）
        out.printl()
        out.printl()
        if st.flag[999] == 0:
            out.printl("DEBUG ON")
            st.flag[999] = 1
        elif st.flag[999] == 1:
            out.printl("DEBUG OFF")
            st.flag[999] = 0
        return
    if value < 400:  # :656–663
        v[8] += 10
        r = com_able(ctx, value)[0]
        v[8] -= 10
        if r:
            yield from do_train(ctx, value)


# --- DOTRAIN → EVENTCOM → COMn → SOURCE_CHECK → EVENTCOMEND ------------------------------


def do_train(ctx: Ctx, com: int) -> Generator[None, int, None]:
    st, out = ctx.state, ctx.out
    st.temp.up.clear()  # UpdateAfterShowUsercom
    st.temp.losebase.clear()
    st.temp.selectcom = com
    for c in st.charas:  # UpdateAfterInputCom（VariableEvaluator.cs:1497–1507）
        c.nowex.clear()
    event_com(ctx)
    result = yield from run_com(ctx, com)
    if result == 0:  # endCallComXX：RESULT==0 なら EVENTCOMEND を呼ばずに終了
        return
    yield from source_check(ctx)
    before = out.wait_count
    event_comend(ctx)
    if out.wait_count == before:  # NeedWaitToEventComEnd（Process.SystemProc.cs:476、515–517）
        out.wait()


def event_com(ctx: Ctx) -> None:
    """`BATTLE_COM.ERB@EVENTCOM`:666–683。

    :668 の SIF は次の論理行（:671 `TFLAG:4 = 0`）だけを飛ばす（空行は論理行でない：
    reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@SIF_Instruction:1771–1791）。
    """
    st, out = ctx.state, ctx.out
    if st.temp.selectcom not in (16, 17, 71, 72):
        st.tflag[4] = 0
    tc(ctx).tcvarn[2] = P_NORMAL
    st.temp.common_palam.clear()
    out.printl()
    out.set_bold(True)
    out.set_color((0, 255, 150))
    out.printl("********** 自分の行動 **********")
    out.reset_color()
    out.set_bold(False)
    out.printl()


def battle_report(ctx: Ctx) -> None:
    """`REPORT.ERB@BATTLE_REPORT`:6–29（TCR*絶頂回数 はすべて定数 10：REPORT.ERH:11–13）。"""
    st = ctx.state
    c = tc(ctx)
    v = c.tcvarn
    rep = st.temp.tcreport
    ecs = c.ex[0] + c.ex[1] + c.ex[2] + c.ex[3]
    for base_idx, slot in ((0, 0), (1, 1), (2, 2)):
        if c.base[base_idx] == 0 and rep[slot] == 0:
            rep[slot] = st.tflag[0]
            rep[10] = ecs
    for tcv, slot in ((21, 3), (23, 4), (25, 5)):
        if v[tcv] == 0 and rep[slot] == 0:
            rep[slot] = st.tflag[0]


def _msg_transrelease(ctx: Ctx) -> None:
    """`MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_TRANSRELEASE`:345–359。"""
    st, out = ctx.state, ctx.out
    out.set_bold(True)
    out.set_color("#FFFF00")
    if enemy_type_check(st, "AKUOTI") == 1:
        who = print_transcallname(st, st.flag[111])
    else:
        who = ctx.data.str_defaults.get(2500, "") if st.flag[73] == 0 else "男たち"  # 触手市民(STR:2500,"男たち")
    out.printl(f"{who}の猛攻によって、限界を越えた{print_transcallname(st, st.target)}の変身が解けてしまった！")
    out.set_bold(False)
    out.reset_color()
    unlock_achievement(ctx, 276, "絶体絶命ヒロイン")
    kojo(ctx, "BATTLE_CHARA_TRANSRELEASE")
    out.printw()


def _msg_transrelease_ecs(ctx: Ctx) -> None:
    """`MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_TRANSRELEASE_ECS`:362–371（HOTPINK = #FF69B4）。"""
    st, out = ctx.state, ctx.out
    out.set_bold(True)
    out.set_color("#FF69B4")
    out.printl(f"絶頂によって{print_transcallname(st, st.target)}の変身が解けてしまった！")
    out.set_bold(False)
    out.reset_color()
    unlock_achievement(ctx, 277, "絶対絶頂ヒロイン")
    kojo(ctx, "BATTLE_CHARA_TRANSRELEASE_ECS")
    out.printw()


def _shinkyou_random(ctx: Ctx) -> None:
    """:849–856／:868–875。"""
    r = ctx.state.rng.rand(100)
    if r < 30:
        shinkyou_change(ctx, "IKARI_TEIKAN")
    elif r < 60:
        shinkyou_change(ctx, "REISEI_DOUYOU")
    elif r < 90:
        shinkyou_change(ctx, "KOUYOU_SYOUTIN")


def event_comend(ctx: Ctx) -> None:
    """`BATTLE_COM.ERB@EVENTCOMEND`:685–986。LOCAL:1 は関数の静的 LOCAL（:895 は前回 :957–968 の値を読む）。"""
    st, out = ctx.state, ctx.out
    c = tc(ctx)
    v = c.tcvarn
    battle_report(ctx)  # :692
    if v[1] > 0:  # :694–695
        v[11] += 1
    # :698–712 空中
    if v.get_bit(216, 2) or v[0] == 0:
        v[216] = 0
        c.base[22] = c.maxbase[22]
        if c.base[22] >= 8:
            c.base[22] = 8
    elif v.get_bit(216, 1) and not v.get_bit(216, 0):
        v.set_bit(216, 2)
        if v.get_bit(216, 1):
            v[216] -= 2
    if v.get_bit(216, 0) and c.base[22] == 0:
        v[216] -= 1
    v[217] = 0  # :715
    if v[0] != 0:  # :718–719
        st.tflag[23] = 0
    if v[0] == 0:  # :722–726
        st.tflag[30] = 0
        st.tflag[31] = 0
    st.tflag[32] = 1 if st.temp.selectcom == 4 and st.flag[73] == 0 else 0  # :728–732
    refresh_cloth_data(ctx)  # :735
    # :738–780 ゲージ増減
    if c.cflag[1] == 2:
        v[6] += -17
    else:
        v[6] += 12
        for bit, add in ((KIZETU, 23), (HAIRAN, 3), (HATUJOU, 3), (MAHI, 8), (BETOBETO, 5), (KOSHIKUDAKE, 8),
                         (KOUKOTSU, 5), (KYOUKOUSOKU, 2)):
            if v[12] & bit:
                v[6] += add
        if v[6] > 0:
            local = 0
            if t(ctx, c, "変身能力") > 0 and c.cflag[1] == 0:
                local += 100
            if c.cflag[43] == 503:
                local += 30
            if t(ctx, c, "不屈") > 0:
                local -= 15
            if t(ctx, c, "スタミナ") > 0:
                local -= 15
            local += cloth_battle_hosei(ctx, "EXBOOST")
            if local < -100:
                local = -100
            v[6] = div(v[6] * (100 + local), 100)
    # :782–787
    if c.cflag[1] == 2:
        v[5] += v[6]
    else:
        v[4] = limit(v[4] + v[6], 0, 600)
        v[4] = limit(v[4] + v[7], -100, 500)
    # :790–809 SP 変身解除
    if v[5] <= 0 and c.cflag[1] == 2:
        transform(ctx, 1 if t(ctx, c, "変身能力") else 0)
        out.printl()
        out.set_bold(True)
        out.printl("ＳＰ変身の効果時間が終了した！")
        out.set_bold(False)
        v[4] = -1
        c.cflag[99] += st.tflag[99]
        out.printl(f"{print_callname(st, st.target)}の身体の底に疲労が蓄積した……（＋{_tofull(st.tflag[99])}）")
        out.printw()
        st.tflag[99] = 0
    v[3] = 0  # :812
    v[6] = 0
    v[7] = 0
    # :818–824 触手の太さと数を保存
    for i in range(4):
        st.tflag[101 + i] = st.temp.tentacle_size[(0, i)]
        st.tflag[105 + i] = st.temp.tentacle_num[(1, i)]
    st.tflag[109] = st.temp.insert
    st.temp.tentacle_size.clear()
    # :827–834
    l2 = sum(c.nowex[i] for i in range(4))
    # :831–832 LOCAL:4 = 気力の残量％（以後使われない）
    result = percent_cal(c.base[2], c.maxbase[2])
    l3 = 100 - div(result * 4, 3)
    # :837–879（:837 は CFLAG:41 == 199 を 2 回書いている：暴走中テンタクルスーツ）
    if c.cflag[1] >= 1 and c.cflag[41] == 199 and v[41] != 0:
        pass
    elif config_check_balance(st, 6) == 0 and c.cflag[1] >= 1 and c.base[1] <= 0 and (v[12] & KYOUKOUSOKU) == 0:
        out.printl()
        _msg_transrelease(ctx)
        if enemy_type_check(st, "AKUOTI") == 1:  # :845–846
            msg_other(ctx, "BATTLE_CHARA_TRANSRELEASE")
        transform(ctx, 0)
        _shinkyou_random(ctx)
    elif (
        config_check_balance(st, 6) == 0
        and c.cflag[1] == 1
        and l2 > 0
        and st.rng.rand(100) < l3
        and result < 50
        and (v[12] & KYOUKOUSOKU) == 0
    ):
        out.printl()
        _msg_transrelease_ecs(ctx)
        if enemy_type_check(st, "AKUOTI") == 1:  # :863–864
            msg_other(ctx, "BATTLE_CHARA_TRANSRELEASE_ECS")
        transform(ctx, 0)
        _shinkyou_random(ctx)
    elif c.cflag[1] == 1 and l2 > 0 and result < 50 and (v[12] & KIZETU) == 0:
        out.printl()
        out.printl(f"{print_transcallname(st, st.target)}は気力を振り絞り何とか変身を維持した！")
    # :882–927 解析度
    if enemy_type_check(st, "AKUOTI") == 0 and st.flag[20] < 100:
        local = calc_chisei_shien(ctx, 2)  # :883 の MAX(BASE:知性 - 100, 1) は :886 で上書きされる
        if v[1] == 2:
            local = div(local, 2)
        elif v[1] == 4:
            local += 5
        elif v[1] == 5:
            local = div(local, 3)
        local = st.rng.rand(5) + div(local, 4) + get_local(st, "EVENTCOMEND", 1)
        lv = tentacle_level(st)
        if lv < 10:
            local += 10 - div(lv, 3)
        if v[2] != P_NORMAL:
            local += 2 + st.rng.rand(5)
        if c.cflag[43] == 500:
            local += 5 + st.rng.rand(6)
        out.printl()
        out.drawline()
        if local > 0:
            out.printl(f"敵の解析度が{local}％上がった！")
        else:
            out.printl("敵の解析度は上がらなかった…")
        f20 = st.flag[20]
        if f20 < 25 and f20 + local >= 25:
            out.printl("敵の体力最大値が判明した！")
        if f20 < 50 and f20 + local >= 50:
            out.printl("敵の体力現在値が判明した！")
        if f20 < 75 and f20 + local >= 75:
            out.printl("敵の能力基礎値が判明した！")
        if f20 < 100 and f20 + local >= 100:
            out.printl("敵の行動補正値が判明した！")
            out.printl("敵の油断度が判明した！")
            out.printl("敵の解析が完了した！")
        st.flag[20] += local
        if st.flag[20] > 100:
            st.flag[20] = 100
        out.printl()
    # :929–931
    for i in range(4):
        c.ex[i] += c.nowex[i]
    st.temp.prevcom = st.temp.selectcom  # :933
    if v[0] == 0 and v[40] > 0:  # :936–937
        v[40] -= 1
    if st.flag[999] == 1:
        out.set_color((96, 96, 96))
        out.printl(f"/* debug */ 絶頂禁止残ターン{v[40]}")
        out.reset_color()
    # :944 AT_VAR（PALAMLV_F は引数でなく前回の戻り値を見る：core.palamlv）
    at_var = limit(950 + palamlv(ctx, 11) * 3 + palamlv(ctx, 13) * 3 + palamlv(ctx, 14) * 2 + palamlv(ctx, 17) * 2,
                   950, 995)
    # :947–954
    mp = st.temp.max_palam
    for i in range(PALAM_END):
        if c.palam[i] > mp[i]:
            mp[i] = c.palam[i]
        if i == 10:  # 潤滑
            continue
        c.palam[i] = div(c.palam[i] * at_var, 1000)
    # :957–978 逃げ遅れ市民と野次馬。FOR の終値は開始時に 1 回だけ評価
    # （reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs@REPEAT_Instruction:1736–1738）。
    # RAND は FLAG:70／71 の有無にかかわらず先に評価される（`&&` は左から、右辺の FLAG だけが短絡対象）。
    evac = 0
    for _ in range(st.flag[70] + st.flag[71]):
        extra = (50 if st.flag[70] > 5 else 15) if get_battle_situation(st, "正体バレ不可") else 0
        if st.rng.rand(100) < 5 + st.tflag[0] + (st.time == 0) * 5 + extra and st.flag[70]:
            st.flag[70] -= 1
            evac += 1
        if st.rng.rand(100) < -10 + st.tflag[0] + (st.time == 0) * 5 + (50 if st.flag[71] > 5 else 0) and st.flag[71]:
            st.flag[71] -= 1
            evac += 1
    set_local(st, "EVENTCOMEND", 1, evac)
    if evac:
        if st.flag[72]:
            out.printl(f"危険を感じた観衆が{evac}人避難した！")
        else:
            out.printl(f"{evac}人の一般人が安全な場所まで避難できたようだ・・・")
        if st.flag[70] + st.flag[71] == 0:
            out.printl("どうやら周囲の避難が完了したようだ！")
        out.printw()
    # :981 EVENT_BATTLE_TURNEND_{FLAG:45}（通常戦闘 FLAG:45 == 0 は event_train で保証）
    # :984–986
    if game_option(st, GameOption.STAT_DECLINE):
        raise NotImplementedError("インスタントモードの能力低下（INSTANT_ARG_DOWN）は未移植")


def _tofull(n: int) -> str:
    """`RESULTS = {n}` → `TOFULL RESULTS`：半角数字を全角に。"""
    return str(n).translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))


# --- 全体 ------------------------------------------------------------------------


def run_train(ctx: Ctx) -> Generator[None, int, Step]:
    """`BEGIN TRAIN` 〜 `@EVENTEND`（`BEGIN TURNEND` を返す）。"""
    from .after import event_end

    st = ctx.state
    update_in_begin_train(st)
    try:
        event_train(ctx)
        while True:
            if st.temp.nextcom >= 0:  # endCallEventTrain:268–276
                raise NotImplementedError("NEXTCOM による自動コマンドは未移植")
            show_status(ctx)
            show_usercom(ctx)
            st.temp.up.clear()  # endCallShowUserCom → UpdateAfterShowUsercom
            st.temp.losebase.clear()
            value = yield
            yield from usercom(ctx, value)
    except BeginAfterTrain:
        pass
    return (yield from event_end(ctx))


