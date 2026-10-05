# 主題隨機命名（S53）

## 來源與實際入口

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_RANDOMNAMING.ERB@RANDOMNAMING_FROMGENRE:450–507`。
- 呼叫者：`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_INITIALIZE:169–210`，
  以及同檔 `@CHARA_MAKE_BASE_PROFILE:919–960`。前者處理已有普通名字的角色，後者處理汎用角色生成。
- 共通設定由 `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:9–21`
  的 `GLOBAL:8 → FLAG:820` 讀入。Python 沿用既有 `GlobalStore` 載入流程，不新增開局輸入。
- 主題手動選單位於 `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CROWNNAME.ERB@FIRSTSETTING_transnamegenre:76–136`，
  仍留待完整角色製作 UI 階段；S53 不增加無呼叫者的選單函式。

## 抽選規則

| FLAG:820 | 主題 | STR 抽選區間 |
|---|---|---|
| 0 | 無指定；沿用普通呼び名 | 不抽 |
| 1 | 魔法風格 | 500–549 |
| 2 | 天體 | 600–649 |
| 3 | 色彩 | 700–749 |
| 4 | 植物 | 800–849 |
| 5 | 雜項英文詞 | 900–949 |
| 6 | 寶石 | 1000–1049 |
| 7 | 人物稱呼 | 1100–1149 |
| 8 | 武器 | 1200–1249 |
| 9 | 先用 `1 + RAND:8` 選主題 | 再抽該組 50 格 |

名稱直接使用既有 CSV 載入器抽取的 `GameData.str_defaults`，不重抄名字表。
原始資料為 `CSV/Str.csv:122–331`（8 組），未填格為空字。
每組均抽 `RAND:50`，空字只重抽同組；不能先移除空格再抽，也不消除資料中的重複詞。
`REPLACE RESULTS,"・$",""` 只刪除一個結尾中點；`LOCALS` 保留修改前原始字串。
無效主題直接沿用該函式先前的 `LOCALS`；第一次為空，不消耗亂數。

## 避重與欄位

兩個呼叫者先組合 `SAVESTR:11 + 主題名`，再掃描索引 1 至 CHARANUM−1；跳過自己，主角索引 0 不參與。
遇到同名便重新呼叫命名函式，最多重抽 10 次，所以最多生成 11 次；最後仍同名也接受。
第 9 類每次避重重試都會重新抽主題，空格重抽則不會。
汎用角色在每次掃描前同時寫 CSTR:0／201／202；另一條路只寫 CSTR:0，不補寫 201／202。
組合結果為空時不寫這些欄位。其餘變身名稱、名乘、旗標處理沿用兩個 caller 原有後續流程。

## 引擎與殘值依據

- RAND 上界不含：`reference/emuera-1824/Emuera/_Library/SFMT.cs:60–64`。
- REPLACE 使用 .NET Regex：`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2460–2472`。
  字串函式當命令使用只寫 RESULTS:0：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:397–404`。
- 裸 RETURN 只寫 RESULT:0 = 0，同檔 :2008–2012；其他 RESULT／RESULTS 格不動。
- 每函式各有 LOCALS，呼叫間保留：`reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:23–70`。
  清除時重設：`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:514–520`。
  Python 使用非存檔 `TempVars.genre_name_local`；存讀檔後恢復空字，不增加存檔資料。

## 驗收

`tests/test_genre_naming.py` 覆蓋 8 主題與隨機主題、空字重抽、Regex 尾端、無效主題靜態殘值、
10 次避重上限、排除主角／自己、兩條實際 caller、CSV 全區間重讀、9 類全域設定、兩種 Web 開局與存讀檔。
主題手動 UI 仍未移植；沒有新增 UNVERIFIED／DEVIATION。完整 pytest 與標準 500 局摘要見 STATUS。
