# CSV 格式（`source/earGVP/CSV/`）

載入器：`src/eragvt/data/csv_loader.py`；測試：`tests/test_csv_loader.py`。
`python -m eragvt --check-data` 可列出載入摘要。

## 共通規則（已對照 Emuera 1.824 原始碼，路徑相對 `reference/emuera-1824/Emuera/`）

- 全部 93 個 `.csv` 皆為 **UTF-8**。多數有 BOM，但 `_ADD/Chara160–163` 與 `Chara18xx_New Generation/CHARA180*` 無 BOM；
  行尾 CRLF／LF 混用。原版 1.824 對無 BOM 的檔以 Shift-JIS 解碼（`Sub/EraStreamReader.cs`:42、`Config/Config.cs`:17），
  這 7 檔在原版會亂碼；本作附的是 +v10 派生版，實際行為見 unresolved。載入器一律以 UTF-8 讀（`# UNVERIFIED`）。
- 讀行（`Sub/EraStreamReader.cs@ReadEnabledLine`:62–95）：空行、只有空白的行略過；行首半形空白／tab 去掉。
  **引擎不處理 `;` 註解**。註解行只是因為「欄位不足」或「第一欄無法解讀」而被警告並略過；
  資料後的 `;註解` 會留在該欄位裡（名稱表的 `50,レベル,;…` 因為只取第 2 欄所以無影響）。
- 欄位以 `,` 分割，**不 trim**（值與名稱索引都保留前後空白）。
- Emuera 設定（`source/earGVP/emuera.config`）：`サブディレクトリを検索する:YES`、`読み込み順をファイル名順にソートする:YES`、
  `_Replace.csv を利用する:YES`、`全角スペースをホワイトスペースに含める:NO`。

## 名稱表（`番號,名稱[,註解]`）

定義各陣列變數「索引 → 名稱」，ERB 可用名稱當索引（`BASE:体力`、`TALENT:CCOUNT:口上設定`）。
讀法（`GameData/ConstantData.cs@loadDataTo`:1300–1343）：番號 `Int32.TryParse(tokens[0])`、名稱 = `tokens[1]` 原樣、
Item 價格 = `Int64.TryParse(tokens[2].TrimEnd())`；同番號重複以後者覆寫。

| 檔案 | 變數 | 筆數 | 備註 |
|---|---|---:|---|
| `Abl.csv` | ABL | 20 | 50 = レベル |
| `Base.csv` | BASE / MAXBASE | 29 | `42,` 為空名保留號（不計入） |
| `Talent.csv` | TALENT | 202 | 0–1218；999 = 固有キャラ |
| `Exp.csv` | EXP | 29 | |
| `Mark.csv` | MARK | 11 | 0–4 刻印、90–94 刻印防止 |
| `Palam.csv` | PALAM / UP / DOWN | 14 | 0–3 快CVAB、10–17、20 修練P、50 経験値 |
| `Juel.csv` | JUEL | 15 | 與 Palam 同號同名（`20,修練P`） |
| `Ex.csv` | EX / NOWEX | 5 | 最後一行 `99,行動ポイント` 無換行 |
| `Train.csv` | 指令名（TRAINNAME） | 38 | 戰鬥指令，見 battle-overview.md |
| `Item.csv` | ITEM / ITEMNAME / ITEMPRICE | 133 | 第 3 欄為價格：`101,セーラー服,2000,` |
| `Cdflag1.csv` | CDFLAG 第一維名稱 | 3 | 1 近 / 2 中 / 3 遠距離 |
| `Cdflag2.csv` | CDFLAG 第二維名稱 | 57 | 武器分類（`0,武器ＩＤ`、`1,斬撃`…） |

`Item.csv` 分區（註解，`Item.csv`:1/62/68/90/95/109）：100〜 アウター（非變身）、200〜 アウター（變身關係）、300〜 インナー、400〜 特殊衣裝、500〜 其他裝備、600〜 客製零件。

## `Str.csv`（STR 陣列初期值，**不是**名稱表）

12,671 筆，`番號,字串`。分區（依檔內註解）：

| 範圍 | 用途 |
|---|---|
| 0–499 | 主題用（日/英 上の句・下の句、ひらがな） |
| 500–1299 | 冠名與變身後名素材（魔法詞、天體、顏色、植物、英單字、寶石、人稱、武器） |
| 2500〜 | 敵人名稱（`2500,触手`、`2501,ザコ触手`）；ERB 以 `%STR:2500%` 引用 |
| 3000–19999 | 姓名產生用（日英法德義俄中韓，各語言區段見 `Str.csv:348–354`） |
| 20000〜 / 21000〜 | 顏色名 / RGB 值 |
| 30000〜 | 外觀（前髮 30000、髮型 30100、目つき 30200）、30500〜 パーソナリティ |

## 設定類

- `GameBase.csv`：`コード,891216222`、`バージョン,408`、`タイトル,eraGVT 社会派ニュース版(勝手版)`、
  `最初からいるキャラ,999`（開局時 Chara999 ダミー 為第 0 名角色）。
- `VariableSize.csv`：本作改寫的陣列大小——`EQUIP 1000`、`CFLAG 2000`、`CSTR 300`、`CDFLAG 100×1000`、
  `STR 32000`、`TRAINNAME 300`、`RELATION 9999`、`TALENT 1300`。其餘用 Emuera 預設。
  註解說明 `TCVAR` 不用，改用 `ERB/DIM.ERH` 的 `TCVARn`（見 variables.md）。
- `_Replace.csv`（`Config/ConfigData.cs@LoadReplaceFile`:528–563）：以 `,` 或 `:` 切出鍵，鍵與值都 trim，
  值 trim 後為空的行不生效。本作有效的只有 `販売アイテム数 = 0`、`DRAWLINE文字 = ─`；`BAR文字1, ` 不生效，維持預設 `*`（`ConfigData.cs`:129）。
- `_default.config` / `_fixed.config`：Emuera 設定，非遊戲資料。

## 角色 CSV

### 位置

檔名 `Chara*.csv`（大小寫不拘，`.CSV`／`CHARA*` 都有），**遞迴**搜尋 `CSV/` 下所有子資料夾，共 77 個：

| 資料夾 | 番号 |
|---|---|
| `Chara/`（直下） | 0 汎用♀、1 汎用♂、299 中間スリーサイズ、998 AA表示（範本）、999 ダミー |
| `Chara/Chara300~400_Shokiset/` | 301–376（初期セット用） |
| `Chara/Chara12xx_Toho/`、`Chara15xx_Squadron5/`、`Chara17xx_Lyrical/`、`Chara18xx_New Generation/` | 1201–1807 |
| `Chara3000 AssaultLily/`（名稱含空白） | 3080–3083 |
| `_ADD/` | 121, 131, 143, 144, 158–163 |

檔案順序：子資料夾優先（名稱不分大小寫排序、遞迴），再列目前資料夾的檔案（`Config/Config.cs@getFiles`:345–379）。
番号重複時只警告、保留先讀到的（`ConstantData.cs`:972–985）；本作沒有重複。`ADDCHARA` 以 `番号` 找角色；
新遊戲時引擎加入的角色 0 與「最初からいるキャラ」則以**檔名 `CHARA` 後的數字**找（`AddCharacterFromCsvNo`，
`VariableEvaluator.cs`:1044–1052；檔名番號見 `ConstantData.cs`:1033–1045）。

### 欄位

| 第一欄 | 格式 | 對應變數 |
|---|---|---|
| `番号` | `番号,N` | NO（`ADDCHARA N` 用此值） |
| `名前` / `呼び名` | `名前,字串` | NAME / CALLNAME |
| `あだ名` / `主人の呼び方` | 同上 | NICKNAME / MASTERNAME（本作未使用，載入器支援） |
| `基礎` | `基礎,索引,值` | BASE **與** MAXBASE |
| `能力` | `能力,索引,值` | ABL |
| `素質` | `素質,索引[,值]` | TALENT；省略值 = 1（`素質,0,;処女`） |
| `経験` | `経験,索引,值` | EXP |
| `珠` | `珠,索引,值` | JUEL（`Chara000`:14 `珠,20,200`） |
| `フラグ` | `フラグ,索引,值` | CFLAG |
| `CSTR` | `CSTR,索引,字串` | CSTR（索引只用數字） |
| `EQUIP` | `EQUIP,索引,值` | EQUIP（衣裝客製資料，值可達 15 位數） |
| `相性` | `相性,對方番号,值` | RELATION；值為 **64 位元 bitset**（`Chara361`:127 `相性,362,2199023255552` = bit 41 従者，位元定義見 variables.md） |

- **索引可寫名稱**：`基礎,体力,1100`、`能力,レベル,1`、`素質,固有キャラ,1`、`経験,Ｖ経験,10`，
  依對應名稱表反查（實際出現：基礎、能力、素質、経験）。
- 每種欄位出現次數（全 77 檔合計）：CSTR 1440、素質 1319、基礎 755、フラグ 534、能力 53、EQUIP 29、相性 26、経験 2、珠 2。

### 值與索引的解析（`ConstantData.cs@toCharacterTemplate`:1106–1289）

- 整數值：`tryToInt64(tokens[2])`——開頭（正負號後）必須是 ASCII 數字，之後讀到非數字為止（`1400` → 1400、
  `100.;私服` → 100）；**省略或無法解析時一律為 1**（:1276–1277）。例：`素質,0,;処女` → 1、
  `Chara998_AA表示.CSV` 的 `基礎,40,xx` → 1、`素質,200,変身能力` → 1。
- 索引：先 `tryToInt64(tokens[1].TrimEnd())`，失敗則以 `tokens[1]`（不 trim）查名稱表；範圍外、查無名稱都是警告後略過該行。
  RELATION 不接受名稱索引；CFLAG／EQUIP／CSTR 的名稱表本作不存在，名稱索引一律失敗。**JUEL 的名稱索引查 palam.csv**。
- 陣列長度：預設 100（TALENT／CFLAG 1000、JUEL 200、CSTR 100），再被 `VariableSize.csv` 覆寫（:168–173）。
- 字串值（`名前`、`CSTR` 等）= `tokens[2]`（或 `tokens[1]`）原樣。例：`Chara998` 的 `CSTR,9,バリアジャケットD;変身時…`
  整段含 `;` 都是值；`Chara1505` 等的 `CSTR,40, 負けず嫌い` 保留前導空白。
- `番号` 行之前的資料、`番号` 重複都只警告略過。CSTR 缺第 3 欄會在 C# 端丟例外，該檔剩餘內容不讀（本作無此情形）。

### 常見 CFLAG／CSTR 初期值（本作角色 CSV 的寫法）

- `フラグ,10,25` / `フラグ,11,110`：變身前能力減少率、SP 變身後增加率（％）。
- `フラグ,40/41/42`：初期アウター／アウター（變身後）／インナー的 Item 番號。
- `CSTR,10` 苗字；`CSTR,12–14` 前髮／髮型；`CSTR,15–17` 近中遠武器壓縮資料（`名稱// //通常`）；
  `CSTR,30–37` 髮／瞳／膚色；`CSTR,204–206` 年齡指定。完整定義見 variables.md 的 CSTR 節。
