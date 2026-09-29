"""觸手（敵）相關的共通判定。路徑相對 `source/earGVP/ERB/`。"""

from __future__ import annotations

from ..state import GameState

# `ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@GET_BOSS_ERB_NUM`:413–423 は @TENTACLE_BOSS_1 から連番で
# 存在する関数の数を数える。本作で定義されているのは
# `ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_BOSS_{1..7}_*.ERB`:4 の 7 個。
BOSS_ERB_NUM = 7

# `@TENTACLE_MOB_{n}` が定義されている n（`触手データ/雑魚敵/*.ERB`）。
# `@EVENTFIRST`（オープニング処理.ERB:36–44）と `@UPDATE` が TRYCCALLFORM で存在確認する。
MOB_TENTACLE_NUMBERS = (1, 2, 3, 101, 102, 201, 301, 501, 601, 701, 702, 801, 802, 803, 901, 902)


def enemy_type_check(state: GameState, kind: str) -> int:
    """`汎用関数/コモン関数.ERB@ENEMY_TYPE_CHECK_F`:1356–1371。"""
    f = state.flag
    if kind == "BOSS":
        return 1 if f[110] == 0 and f[73] == 0 and f[10] == 0 else 0
    if kind == "LASTBOSS":
        if f[110] == 0 and f[73] == 0 and f[10] == 1:
            return 1 if f[101] == 1 else 1 + f[21]
        return 0
    if kind == "MOB":
        return 1 if f[110] == 0 and f[73] == 0 and f[10] == 2 else 0
    if kind == "CITIZEN":
        return 1 if f[110] == 0 and f[73] > 0 else 0
    if kind == "AKUOTI":
        return 1 if f[110] > 0 else 0
    return -1


def get_lastboss_phase(state: GameState) -> int:
    """`@GET_LASTBOSS_PHASE_F`（汎用関数/コモン関数.ERB:1345–1353）。"""
    if state.flag[101] == 1:
        return 1
    if state.flag[101] == 2:
        return 1 + state.flag[21]
    return 0


_BOSS_BIT_TO_NO = {1: 1, 2: 2, 4: 3, 8: 4, 16: 5, 32: 6, 64: 7}
_LASTBOSS_BIT_TO_NO = {1: 1, 2: 2}


def tentacle_survive_check(state: GameState, bit: int) -> int:
    """`COMMON_TENTACLE_DATA.ERB@TENTACLE_SURVIVE_CHECK`:55–118：生存していればボス番号、でなければ 0
    （関数終端に達した場合 RESULT = 0：reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67）。"""
    if state.flag[100] > 0 or enemy_type_check(state, "MOB") == 1:
        if state.flag[100] & bit:
            return _BOSS_BIT_TO_NO.get(bit, 0)
    elif state.flag[101] & bit:
        return _LASTBOSS_BIT_TO_NO.get(bit, 0)
    return 0


def tentacle_survive_num(state: GameState) -> int:
    """`@TENTACLE_SURVIVE, "NUM"`（COMMON_TENTACLE_DATA.ERB:5–53）：生存しているボス（ラスボス）の数。"""
    bit, count = 1, 0
    if enemy_type_check(state, "BOSS") == 1 or enemy_type_check(state, "MOB") == 1:
        n = state.flag[3]
    else:
        n = state.flag[4]
    for _ in range(n):
        if tentacle_survive_check(state, bit) > 0:
            count += 1
        bit *= 2
    return count
