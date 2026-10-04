# 身體資料（プロフィール）

S09 查證結果。路徑相對 `source/earGVP/ERB/SYSTEM/キャラメイキング関連/`，Python：`eragvt.game.body`。

## 變數

| 變數 | 意義 | 依據 |
|---|---|---|
| BASE／MAXBASE:40 | 実年齢（MAXBASE 不用） | `CSV/Base.csv`:20 |
| BASE:41／MAXBASE:41 | 年齢（外見）通常時／変身時；MAXBASE:41 = -1 表示「変身なし」 | Base.csv:21、`CHARA_SIZE_UI.ERB`:2153–2154 |
| 43–48 | 身長（mm）・体重（0.1kg）・胸囲・胴囲・腰囲（mm）・胸の重量（0.1kg）；BASE 通常時、MAXBASE 変身時 | Base.csv:23–28、`CHARA_SIZE.ERB`:19–24 |
| CFLAG:33 | 体型乱数値（0〜535627332239）；各部位用 `% 11／31／59／15／16／13／23／7／53` | `CHARA_SIZE.ERB`:3–13、61–78、301–309 |
| CFLAG:34 | 成長曲線（15 位數，每位 0〜9 = 5〜19 歲每年的伸長）；**0 = プロフィール未設定** | `CHARA_SIZE.ERB`:15–16、`地の文/MESSAGE.ERB`:258–260 |

CFLAG:34 == 0 時停用的機能（原作）：拡張（`GAPING.ERB`:864 等）、年齢帯文字、悪堕ち的容貌變化（`CORRPUTION.ERB`:29）等。

## 何時生成

| 呼叫點 | 內容 | 本作 |
|---|---|---|
| `CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE`:493–505 | CSV キャラ：**CFLAG:34 == 0 且 `NO == 0`** 才 GENERATE_BODYLINE → AGE_SETTING → CHARA_SIZE_DEFAULT，之後一律 RETURN | 移植（`opening.chara_make_base_profile`） |
| 同 :507–980 | 汎用キャラ（未初期化）的全隨機生成（**預設開局經過這裡**） | S10 移植（`eragvt.game.chara_make.base_profile_generic`）：BODYLINE → AGE_SETTING → STATUS_TALENT／FLAVOR → CHARA_SIZE_DEFAULT，最後 `CFLAG:34 = 1`（:980，覆寫成長曲線） |
| `FIRSTSETTING_CHARA.ERB`:256–261（[6]身体データ：BODYLINE → SIZE_SETTING 畫面）／:321–333（[999]CSV 再ロード：AGE_SETTING → CHARA_SIZE_DEFAULT，**不跑 BODYLINE，CFLAG:33／34 仍為 0**） | 角色製作畫面的手動操作 | 未移植（UI） |
| `ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE5.ERB`:73–79（指令 20、FLAG:700 == 0） | 狀態畫面的「スリーサイズ等設定」 | 未移植（UI） |
| `FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE`:4–19 | 只重算 43–48（BASE／MAXBASE），**不看 CFLAG:34、不改 CFLAG:33／34 與年齢** | 移植，接 `PRISON_COM105_膨乳化.ERB`:70 |

`NO` 是 CSV 番号（`reference/emuera-1824/Emuera/GameData/Variable/CharacterData.cs`:99），初期セット（301〜303）≠ 0，
所以**初期セット → [1000] 的新遊戲不會生成身體資料**：BASE:40–48 = 0、CFLAG:33／34 = 0。原作的預設開局（汎用キャラ）則會生成（S10）。

汎用キャラ的怪處（照原作）：CHARA_SIZE_DEFAULT（:519）比「人間には必ず変身能力」（:531–534）早 → 人間也是 `MAXBASE:年齢 = -1`、
MAXBASE:43–48 = 0；`CFLAG:34 = 1`（:980）→ 之後拡張度系（`GAPING.ERB`:864 等，CFLAG:34 != 0）會動作（本程式該處未移植、會停止）；
AGE_SETTING 在決定「学生」（FLAVOR :1077–1087）之前，年齢一律 RAND:11+10（10〜20 歲）。
玩家在キャラメイク畫面按 [1]〜[3] → [6] 或 [999]，或開局後在狀態畫面 PAGE5 按 20，才會生成。

### 對戰鬥的影響（原作行為）

`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB` 的胸部重量補正（＠中國版，`更新履歴.txt`:358）
`value * (1 + 胸の重量) / (1 + BASE:体重)`：被弾判定 :606–614、撤退判定 :1097–1105 減去，DAMAGE :1207–1214 加上。
體重・胸の重量 = 0 時此項 = value 本身 → 女性敏捷 0、攻擊 2 倍。原作初期セット直接開始就是這個狀態
（Python：`battle.hantei.breast_weight_term`）。正常體重（例 48.0kg／0.5kg）時只差 1% 左右。
膨乳化（SET_PROFILE）之後，年齢 0 的角色會得到嬰兒體格（身長 544mm・体重 4.8kg 左右），補正因此幾乎消失。

## 計算（GENERATE_CHAR_SIZE:25–284）

1. 乱数値:1〜6 = CFLAG:33 % (11,31,59,15,16,13)；素質「○○乱数」(1〜m) 可上書（值 − 1）。
2. 成長値[i] = 成長曲線第 i 位 × 30 ＋（i<7: 400、i=7: 210、i=8: 100）。
3. 身長 = 10940×(r1+95)/100；0〜4 歲乘係數；5 歲起逐年加成長値（女性 13–16 歲遞減、17 歲後以成長値[14] 微增／40 歲後遞減；
   男性到 19 歲）；× (小柄でない×25 ＋ 長身×25 ＋ r2 ＋ 260)/3000；小さな体躯 ×0.75（妖精族再 ×0.5）；男性 ×1.085；身長指定上書。
4. BMI（外見素質 ±20、年齡 <20 時縮小）→ 体重 = 兩種式依身長混合 ＋ r3；胴囲・腰囲・アンダー = 身長 × 係數；25 歲起熟女補正。
5. TOP_UNDER:287–380：胸サイズ素質的 (基準, 最小, 最大) 表、年齢影響値、膨乳改造値 → サイズ値（男性 -1）。
   体重 −= 18600×影響値/50/1000；胸囲 = アンダー ＋ サイズ値。
6. CUP_SIZE:386–456 → CALC_BREAST_WEIGHT:554–670（球缺體積 ×0.87×2，再依カップ目安值加權）/100 = 胸の重量，加進体重。
7. 男性（男の娘でない）胸囲・胴囲・腰囲 = -1；各「○○指定」素質上書。

CHARATALENT_F（`汎用関数/コモン関数.ERB`:1079–1321）決定通常時／変身時的素質；S09 補上変身中（CFLAG:1 > 0）分岐。

GENERATE_BODYLINE:460–544：CFLAG:33 = RAND:535627332240；成長値以權重 (83,80,75,83,113,108,50,40,30,20,10,10,10,8,6)
抽 60 次 RAND:726、每年上限 9（超過重抽）。內層 FOR 的 BREAK 會先把計數器 +1（`Instraction.Child.cs`:2054–2077），
所以 `成長値:(LCOUNT:1 - 1)` 就是抽中的那一年。

CHARA_MAKE_AGE_SETTING:1336–1444：年齢 = RAND:11+10，學生／交際相手／種族改寫；:1404–1406 把 MAXBASE:年齢 也設成 AGE。
年齢指定（CSTR:204–206，:1408–1444）S10 移植：`"0"` → 0、`TOINT > 0` → 該值、否則 `RANDOM_AGE_F`（:1448–1497，未知字串 -99）；
最後「年齢に合わせる」「実年齢に合わせる」覆寫。TOINT 依 `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2357–2387`；
S50 補完十六／二進位、指數與 Int64 邊界，無效格式回 0、轉換錯誤照原作拋出，詳見 `../python/numeric-input.md`。
