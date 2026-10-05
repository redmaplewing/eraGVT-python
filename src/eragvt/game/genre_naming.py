"""主題命名；原文位於 ERB/SYSTEM/キャラメイキング関連/。"""
import re
from ..data.csv_loader import GameData
from ..state import GameState


def random_naming_from_genre(state: GameState, data: GameData, genre: int) -> str:
    """FIRSTSETTING_RANDOMNAMING.ERB@RANDOMNAMING_FROMGENRE:450–507。"""
    # :453–454 只在本次選擇主題；空格重抽不能重選主題。
    # RAND 上界不含：reference/emuera-1824/Emuera/_Library/SFMT.cs:60–64。
    if genre == 9:
        genre = 1 + state.rng.rand(8)
    if 1 <= genre <= 8:
        base = 400 + genre * 100
        while True:  # :456–503，各主題固定抽 50 格，空值繼續抽。
            raw = data.str_defaults.get(base + state.rng.rand(50), "")
            if raw != "":
                state.temp.genre_name_local = raw
                break
    # LOCALS 為函式靜態值；無對應主題時仍保留上次原始文字。
    # reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:23–28、69–70。
    # REPLACE 使用 Regex，命令只寫 RESULTS:0；裸 RETURN 只寫 RESULT:0。
    # reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2460–2472；
    # reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:397–404、2008–2012。
    state.results[0] = re.sub("・$", "", state.temp.genre_name_local)
    state.result[0] = 0
    return state.results[0]


def genre_name_tail(state: GameState, data: GameData, sel: int, *, generic: bool) -> str:
    """CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_INITIALIZE:173–194／@CHARA_MAKE_BASE_PROFILE:922–949。

    兩處相同的避重流程；汎用角色額外先寫入 CSTR:201／202。
    """
    c = state.charas[sel]
    head = state.savestr[11]
    retries = 0
    while True:
        tail = random_naming_from_genre(state, data, state.flag[820])
        if head + tail == "":
            return tail
        c.cstr[0] = head + tail
        if generic:
            c.cstr[201], c.cstr[202] = head, tail
        # :186–193／941–948：從 1 開始，跳過自己；第 11 次結果可重複。
        for other in range(1, state.charanum):
            if other != sel and c.cstr[0] == state.charas[other].cstr[0] and retries < 10:
                retries += 1
                break
        else:
            return tail
