# 口上／地の文 catalog（`eragvt.narration`，S07）

原作 `ERB/口上/`（114 檔）與 `ERB/地の文/`（61 檔）的函式**不手翻**：執行期從 `source/earGVP/ERB` 抽取成節點樹，
由受限的執行器求值。**不是** ERB 直譯器：只支援「文字輸出＋條件分岐」子集，子集外一律 unsupported（附原因與行號），
不去補一般化的執行引擎。ERB 路徑相對 `source/earGVP/ERB/`，引擎路徑相對 `reference/emuera-1824/Emuera/`。

## 模組

| 模組 | 內容 |
|---|---|
| `lexer.py` | 字句解析（`Sub/LexicalAnalyzer.cs`）：式、FORM 字串（`%式,幅,LEFT%`／`{式}`／`\@ 式 ? 左 # 右 \@`）、`"…"`、`@"…"` |
| `expr.py` | 式 AST＋shift-reduce 剖析（`GameData/Expression/ExpressionParser.cs`:327–637 的 `TermStack` 原樣移植） |
| `extract.py` | 讀檔（`{ }` 連結、`[SKIPSTART]`、註解）、`@` 標籤、函式本體 → `nodes`（命令判定：`LogicalLineParser.cs`:386–480） |
| `nodes.py` | 節點格式（下節） |
| `symbols.py` | 命令名表（`BuiltInFunctionCode.cs`）、內建變數、CSV 名稱索引表（`ConstantData.cs`:707–860）、ERH `#DIM` |
| `catalog.py` | 全 ERB 的函式索引（檔案順序 `Config.cs@getFiles`:345–379、同名先定義者優先 `LabelDictionary.cs`:58–77、名稱 ToUpper）＋lazy 抽取＋可執行性判定＋覆蓋率報告 |
| `runtime_support.py` | 可讀變數（狀態模型有對應欄位者）、已實作式中関数、靜態檢查 |
| `runtime.py`／`builtins.py` | 執行器、式中関数（`GameData/Function/Creator.Method.cs`） |
| `hooks.py` | 狀態變化行的 hook 表（下述） |
| `service.py` | `CatalogNarrationService`：`call_kojo`（KOJO_ROOT 派發）、`run_function`（地の文）、`run_function_gen`（含 INPUTS，S14）、`run_event_gen`（S28c2）、失敗回復 |
| `windowlib.py` | `汎用関数/WindowDrawer.ERB`＋`TagSetText.ERB` 的 Python 移植（`CALL WINDOW_*`，S14；只有動画サイト使用） |

產生物不落地：啟動時只掃 label（約 0.5 秒），函式本體第一次用到時解析、快取在記憶體。

## 節點格式（`nodes.py`）

`FuncDef(name, file, line, params, kind=proc|int|str, private, consts, body, unsupported, calls, dynamic_calls, hooks)`。
文：`Print(kind=raw|form|expr|forms, arg, newline, wait, dflag, plain)`、`PrintData(var, items)`（item = 行のリスト：
DATA／DATAFORM／DATALIST）、`If(branches, orelse)`、`Select(expr, cases[(CaseCond…), body], orelse)`
（CaseCond: eq／`a TO b`／`IS 演算子 a`）、`Sif(cond, body)`、`Assign(target, op, values)`、`BitOp`、`VarSet`、`StrLen`、
`Style(SETCOLOR|RESETCOLOR|FONTBOLD|FONTITALIC|FONTREGULAR|ALIGNMENT|SETFONT)`、`DrawLine`、`ClearLine`、`Wait`、
`Return`、`ReturnF`、`CallStmt(name=str|Form, args, try_, catch, success, callf)`、`MethodStmt`（式中関数を命令として：
結果は RESULT／RESULTS）、`For`／`While`／`Repeat`／`Loop`／`Break`／`Continue`、`Hook(key, text, [文])`、`Unsupported(reason)`、
S14：`Label(name)`／`Goto(name)`、`Input`（INPUTS）、`DrawLine(form)`（DRAWLINEFORM）。
式：`Lit`、`Var(name, args)`、`Call(name, args)`、`Unary`、`Binary`、`Ternary`、`Form(strs, parts)`。

## 子集（可執行的條件）

- 命令：上表的文＋ TRYCALL／TRYCALLFORM／TRYCCALL(FORM)…CATCH…ENDCATCH（見つからない → CATCH 側：`Instraction.Child.cs`:2310–2317、
  呼べたら CATCH までの文を実行して ENDCATCH へ：:2034–2038）。
- 代入先：LOCAL／LOCALS／ARG／ARGS／函式內 `#DIM`（靜態：`UserDefinedVariable.cs`:27）、RESULT（S21 起＝`GameState.result`）／RESULTS（S22 起＝`GameState.results`，範圍外添字は錯誤；兩者與 Python 共用、失敗回復時一併還原：`result.md`）／COUNT、
  **口上專用的非 SAVEDATA `#DIM`**（口上／地の文的 ERH 宣告、且口上／地の文以外的 ERB 完全不參照者：例 `真面目_フラグ_シチュ`）。
  其他代入（CFLAG、TALENT、FLAG…）→ unsupported。
- 讀取：狀態模型有對應的變數（BASE・TALENT・CFLAG…・FLAG・TFLAG・DAY・TCVARn・TENTACLE_SIZE・CLOTH_*・SHIELD・STR（Str.csv）…）。
  SOURCE・TEQUIP・PLAYER・GLOBAL 等模型沒有的變數 → unsupported（讀了等於猜 0）。
- 呼叫：呼叫先（任何 ERB 檔的函式，包含 `汎用関数/` 等）本身也可執行才算可執行（遞迴判定）。
  KOJO_ROOT 以 Python 實作（`action.kojo_root_full`＋`service.call_kojo`）；`WINDOW_CREATE／SETTEXT／DESTROY／DISPLAY` 也是
  （`windowlib.py`，`WINDOW_DISPLAY_EX` 的 REF 配列引數在執行時 unsupported）。
- GOTO（S14）：只支援定數ラベル、且 `$ラベル` 在函式本體最上層（S28c2 起也支援 IF／SELECTCASE 內，見下）。FOR 等在引擎是線形跳躍、
  沒有堆疊（`Instraction.Child.cs@GOTO_Instruction`:2366–2406），所以「從最上層ラベル的下一行重新執行本體」等價。
- INPUTS（S14，無既定值者）：只有 generator 呼叫端（`run_function_gen`，以 `yield from` 呼叫）可執行；`run_function`／口上派發遇到
  （含靜態呼叫先，`Catalog.needs_input`）視為不可執行。實作是**重放**：到達尚無輸入的 INPUTS 時中斷、`yield` 取得輸入、把輸出・亂數・
  LOCAL 回到開始時，再以累積的輸入列從頭執行（同輸入列 → 同結果）。中斷前若已有狀態變化（hook、KOJO_ROOT）則無法重放 → 停止。
  輸入值 = `str(Web 的整數)`（deviations「INPUTS 只能輸入整數」）。
- DRAWLINEFORM：評價字串（空字串 → 引擎錯誤），但畫面上與 DRAWLINE 同樣是區切線（線的字元不反映，deviations「口上 catalog 的表示」）。
- S21 追加：`SPLIT`（`Process.ScriptProc.cs`:522–538；分割數→個數變數或 RESULT:0，超過配列長〔LOCALS／ARGS 100：`ConstantData.cs`:153–154，
  `#DIMS`／`#LOCALSSIZE` 的宣告長〕截斷）、式中関数 STRFINDU・STRCOUNT・REPLACE（.NET Regex；只接受與 Python re 同義的字元類／字面，
  其他 unsupported）・ISNUMERIC・TOINT（10 進；0x／0b／指數 unsupported）（`Creator.Method.cs`:2222–2302、2357–2387、2452–2474、2532–2569）。
  `地の文/MESSAGE_AKUOTI.ERB`、`SETCOLOR_BY_STR` 等因此可執行（覆蓋率 12844／13384＝96.0%）。
- S28b 追加：式中関数 VARSIZE（ERH の `#DIM CONST` 配列のみ：`Creator.Method.cs@VarsizeMethod`:335–375、要素数省略時は初期値の個数
  `UserDefinedVariable.cs`:287–288）、CONST 初期値の `__INT_MAX__`／`__INT_MIN__`（`VariableToken.cs`:1669–1690）、hook の代入先に
  EXP・TARGET（`SEISAN_HOOK_LINES`）。`#DIMS REF` 引数は値渡しの関数内変数として扱う（呼び出し側が `state.temp.narr` から読む：
  `seisan._gravure_title`）。特別活動の地の文 58 函式はすべて実行可能（覆蓋率 12851／13384）。
- S28c2 追加：
  - INPUT（整數、無既定值）→ RESULT:0（`GameProc/Process.cs@InputInteger`:249–252）。同 INPUTS 只在 generator 呼叫端可執行。
  - 入れ子內的 $ラベル：ラベル的路徑只經過 IF／SELECTCASE 的枝時可執行。引擎的 ELSEIF／ELSE／CASE／CASEELSE 只是跳到 ENDIF／ENDSELECT、
    ENDIF 什麼都不做（`Instraction.Child.cs@ELSEIF_Instruction`:1805–1821、`ENDIF_Instruction`:1822–1832、`FunctionIdentifier.cs`:231–237），
    所以「ラベル之後的剩餘 → 外側入れ子文的下一句 → …」等價（`nodes.label_path`、`Interp._exec_body`）。ループ內的ラベル仍 unsupported。
  - `run_event_gen`（事件本體用：`eragvt.game.pastime_nanpa`）：不重放，直接在另一條執行緒跑直譯器，INPUT（與 hook 的 Python 移植
    ——AFTER_PILL・CALC_GANGBANG——yield 的輸入等待）時真正中斷；兩邊交替執行，輸出・亂數順序與同步執行相同。所以輸入前有狀態變化也可以。
    執行中途才發現不可執行 → 無法回復 → NotImplementedError（Web 停止）。generator 被關閉時以 `_Abort` 收掉執行緒。
  - hook 的 CALL 可回傳 generator（在執行緒中驅動）；新增 HOOK_CALLS：COMMON_PRISON・COMMON_PRISON_EXP・_ABLUP・AFTER_PILL・CALC_GANGBANG・
    ENCOUNT_CITIZEN（停止）。表 `NANPA_HOOK_LINES` 72 行。
- 不支援：GOTOFORM／TRYGOTO 系、ループ內的 $ラベル、TINPUT・ONEINPUT 系與有既定值的 INPUT／INPUTS、BEGIN、JUMP、PRINTV・
  PRINT K 系・PRINTC 系、STRDATA、TIMES、SETCOLORBYNAME、`@` 付き変数、未實作的式中関数（覆蓋率報告）。

語意重點（皆有引擎行號，見 `runtime.py` docstring）：`&&`／`||` 短絡；`/`・`%` 先評價右辺；C# 的切り捨て除算；
`PRINTDATA` 以 `RAND(件數)` 選 1 件；`%…,幅%` 以 cp932 位元組寬補空白；文字列中 `\n` 換行；函式末尾流れ落ち → RESULT = 0；
省略引數 → 0／""；`PRINT` 系的引數是命令後 1 字元之後的全部（`;` 也照印）。RAND 一律 `state.rng`，照 ERB 求值順序。

## 口上派發（KOJO_ROOT.ERB）

`action.kojo_root(ctx, code, force)` = `kojo_root_full(ctx, TARGET の CFLAG:6, …)`：:17–21 気絶、:23–39 結界（部分一致）→ 0；
其餘交給 `narration.call_kojo`（:46–90）：汎用口上（C_NO 0／1：`CSV定数定義/CFLAG.ERH`:79–80）呼
`KOJO_{C_NO}_COLOR_{SEIKAKU_CHECK_F(TARGET)}` 再 `KOJO_{C_NO}_%CODE%_{同}`；`OTHER_` 含み → FLAG:62 = 1、`SEIKAKU_CHECK_F(FLAG:111)`。
找不到 → RESETCOLOR・FLAG:900 = 0・-1；有 → 執行、RESETCOLOR・FLAG:900 = 0、RESULT == 999 ならそれ、否則輸出行數。
ERB 內的 `TRYCALLFORM KOJO_ROOT(…)`（地の文）也走同一實作。`NullNarrationService` 只走「找不到」路徑。

## 地の文與 hook

呼叫端用 `core.run_chinobun(ctx, 函式, args, fallback)`：可執行 → catalog 輸出本文（含其中的 KOJO_ROOT）；否則印
「〈地の文：函式〉」並執行 fallback（該地の文中本文以外的處理，如 KOJO_ROOT 呼叫）。性攻擊地の文（`sexmsg.msg_*`）以
`@_catalog` 裝飾：可執行就整個以 catalog 執行，否則走 S06 的 Python 移植。

`MESSAGE_SEX_COM*`／`MESSAGE_SEX_SPCOM*` 中的狀態變化行（FLAG:900、TFLAG:4／21／23、TENTACLE_SIZE、CFLAG:206、TCVARn:12／25、
CALL SET_TENTACLE_SIZE_BY_MESSAGE／TENTACLE_SYASEI_UP／NINSIN_HANTEI／LOSTVIRGIN）逐行列在 `hooks.HOOK_LINES`（140 行，
附 sexmsg 對應函式與註解引用）。抽取時這些行成為 `Hook`：代入以「可寫入狀態」模式執行，CALL 轉呼叫既有 Python 移植，
**依 ERB 的順序**與本文、RAND 交錯執行。表外的狀態變化仍是 unsupported。測試 `test_hook_table_matches_sexmsg` 對照原文、
sexmsg 引用、以及「表外沒有漏掉的代入」。

## 失敗回復

執行中才發現不可執行（動態 CALLFORM 的呼叫先 unsupported、除以 0 等引擎會報錯者）→ 回復輸出（TextOutput 內部狀態）、
亂數（`GameRng.snapshot/restore`）、LOCAL／narr；口上當「找不到」、地の文走 fallback。hook 已執行（狀態已變）之後失敗則
無法回復 → `NotImplementedError`（Web 停止）。

## 覆蓋率

`python -m eragvt --narration-report`（函式數・可執行數〔其中需要 INPUTS 者〕・unsupported 第一原因前 10 名・檔案別）。數字見 `docs/STATUS.md`。

## 動画サイト（S14）

`MESSAGE_SEX_SPCOM7`（`地の文/MESSAGE_SEX_COMSP.ERB`:1126–1300）與其呼叫的 `MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window`
整個由 catalog 執行（`sexmsg.msg_spcom7` 以 `run_function_gen`）。視窗內容（`strVSWBrowser`／`strVSWText`，函式內靜態 #DIMS）照 ERB 組出，
`CALL WINDOW_*` 走 `windowlib.py`：各視窗以 cp932 位元組寬成形、疊合成 84 桁的行，`@B:n@…@/B@` 變成按鈕（PRINTBUTTON），其餘 PRINTPLAIN。
迴圈 `$PRINT_LOOP`→INPUTS→`CLEARLINE LINECOUNT`（清除整個畫面紀錄，照原作）→`GOTO PRINT_LOOP`，輸入 "99" 結束。無狀態變化。
