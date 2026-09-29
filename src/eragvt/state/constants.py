"""主流程會用到的原作常數。

每個值的來源寫在類別 docstring（`檔案:行`，路徑相對 `source/earGVP/`）。
只收 S03–S06 確定會用到的；其餘常數需要時再補。
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

# ERB/DIM.ERH:24–26
PARTY_MAX = 6  # パーティ人数最大値
REGISTER_MAX = 30  # 登録最大人数
FORCE_REST_HP = 500  # 強制休憩体力


class ActionPlan(IntEnum):
    """行動預約（CFLAG:100）。ERB/CSV定数定義/CFLAG.ERH:30–38"""

    NONE = 0  # 予定_無し
    SORTIE = 101  # 予定_出撃
    TRAINING = 102  # 予定_鍛錬
    REST = 103  # 予定_休憩
    ACTIVITY = 104  # 予定_活動（特別活動）
    DEFENSE = 105  # 予定_防衛
    SUPPORT = 106  # 予定_支援
    INFORMATION = 107  # 予定_情報
    FREE = 108  # 予定_自由


class CharaState(IntEnum):
    """角色生存狀態（CFLAG:0）。ERB/CSV定数定義/CFLAG.ERH:13–22"""

    JUST_RESCUED = -1  # 状態_救出直後
    SAFE = 0  # 状態_無事
    IMPRISONED = 1  # 状態_幽閉
    BRAINWASHED = 2  # 状態_洗脳
    CORRUPTED = 3  # 状態_悪堕ち
    KIDNAPPED = 4  # 状態_クズ監禁
    DEAD = 9  # 状態_死亡
    BEFORE_BIRTH = 10  # 状態_出産直前
    CHILDCARE = 11  # 状態_育児中
    INHERIT = 999  # 状態_引継ぎフラグ


class KojoType(IntEnum):
    """口上番號（CFLAG:6）的特殊值；其他值 = 專用口上的角色番號。ERB/CSV定数定義/CFLAG.ERH:77–83"""

    HIDDEN = -2  # キャラ口上_非表示
    UNEDUCATED = -1  # キャラ口上_未教育
    FEMALE_GENERIC = 0  # キャラ口上_女性汎用
    MALE_GENERIC = 1  # キャラ口上_オトコ汎用
    ROBOT = 2  # キャラ口上_ロボ風
    ANATA = 3  # キャラ口上_あなた
    HYOHEN = 4  # キャラ口上_汎用豹変


class GameMode(IntEnum):
    """遊戲模式。ERB/DIM.ERH:40–47"""

    GAMEOVER = 0
    NORMAL = 1
    SOLO = 2
    HARDCORE = 3
    SURVIVAL = 4
    FREEPLAY = 5
    SANDBOX = 6
    INSTANT = 7


class GameOption(IntEnum):
    """FLAG:0 的位元號（`GAME_OPTION_CHECK_F` = `GETBIT(FLAG:0, n)`）。
    ERB/DIM.ERH:60–70、ERB/ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB:89–91"""

    EASY = 0
    NORMAL = 1
    HARDCORE = 2
    SOLO = 3
    ENDLESS = 4
    NO_INHERIT = 5  # 引継ぎ無し
    NO_TIME_LIMIT = 6  # 制限時間無し
    NO_ACHIEVEMENT_END = 7  # 実績エンド無し
    NO_GAMEOVER = 8  # ゲームオ－バー無し
    JOIN_RETIRE = 9  # 加入引退有り
    STAT_DECLINE = 10  # ステ低下有り


# 模式 → FLAG:0 的值（右端為 OPTION 0）。ERB/DIM.ERH:83–92 `モードオプション`
MODE_OPTIONS: dict[GameMode, int] = {
    GameMode.GAMEOVER: 0b00000000000,
    GameMode.NORMAL: 0b00000000010,
    GameMode.SOLO: 0b00000001010,
    GameMode.HARDCORE: 0b00000000100,
    GameMode.SURVIVAL: 0b00000010010,
    GameMode.FREEPLAY: 0b00001110010,
    GameMode.SANDBOX: 0b00111110010,
    GameMode.INSTANT: 0b11000000010,
}


class Base(IntEnum):
    """BASE／MAXBASE 的主要索引。CSV/Base.csv"""

    HP = 0  # 体力
    ENERGY = 1  # 気力
    SEX_RESIST = 2  # 性耐性
    ATTACK = 10  # 攻撃
    DEFENSE = 11  # 防御
    AGILITY = 12  # 敏捷
    INTELLECT = 13  # 知性
    EJACULATION = 20  # 射精
    LACTATION = 21  # 噴乳
    AIR_DASH = 22  # 空中ダッシュ
    SHIELD_C = 30  # Ｃ結界耐久力
    SHIELD_V = 31
    SHIELD_A = 32
    SHIELD_B = 33


class Palam(IntEnum):
    """PALAM／UP／DOWN 索引。CSV/Palam.csv、ERB/DIM.ERH（快Ｃ〜恐怖 定數）"""

    PLEASURE_C = 0  # 快Ｃ
    PLEASURE_V = 1
    PLEASURE_A = 2
    PLEASURE_B = 3
    LUBRICATION = 10  # 潤滑
    OBEDIENCE = 11  # 恭順
    LEARNING = 12  # 習得
    LUST = 13  # 欲情
    SUBMISSION = 14  # 屈服
    SHAME = 15  # 恥情
    PAIN = 16  # 苦痛
    FEAR = 17  # 恐怖
    TRAINING_POINT = 20  # 修練P（JUEL:20 同號）
    EXP_POINT = 50  # 経験値


class Distance(IntEnum):
    """戰鬥距離（TCVARn:0）。ERB/CSV定数定義/TCVARn.ERH:13–16"""

    RESTRAINED = 0  # 拘束中
    NEAR = 1
    MIDDLE = 2
    FAR = 3


class BattleStatus(IntFlag):
    """狀態異常（TCVARn:12）。ERB/DIM.ERH:129–136；ORGASM_FORBIDDEN 只見於
    ●開発者向け資料/●GVTフラグ一覧.txt:583"""

    FAINT = 1  # 気絶
    OVULATION = 2  # 排卵
    HEAT = 4  # 発情
    PARALYSIS = 8  # 麻痺
    STICKY = 16  # べとべと
    WOBBLY = 32  # 腰くだけ
    ECSTASY = 64  # 恍惚
    HARD_BIND = 128  # 強拘束
    ORGASM_FORBIDDEN = 256  # 絶頂禁止


class SexPart(IntFlag):
    """性部位位元（TFLAG:4 射精部位等）。ERB/DIM.ERH:94–105"""

    C = 1  # クリトリス
    V = 2  # 膣
    A = 4  # アナル
    B = 8  # 胸
    MOUTH = 16  # 口
    HAND = 32  # 手
    SLIT = 64  # ワレメ
    MISFIRE = 128  # 暴発


class Pose(IntEnum):
    """防禦體勢（TCVARn:2）。ERB/DIM.ERH:187–205"""

    NOTHING = -1  # 何もしない
    NORMAL = 0
    GUARD = 1
    SUBMIT = 2  # なすがまま
    ENDURE = 3
    ACCEPT = 4
    SERVE = 5
    GLARE = 6
    ABUSE = 7  # 罵倒する
    RESIST = 8  # 反抗する
    PERSUADE = 9
    SQUEEZE = 10  # 搾り取る
    V_GUARD = 100
    STRUGGLE_GUARD = 200  # 暴れる防御
    STRUGGLE_FAIL = 201
    STRUGGLE_CRITICAL = 202
    COUNTER = 300  # 反撃
    EX_COUNTER = 301
    COUNTER_SUCCESS = 302
