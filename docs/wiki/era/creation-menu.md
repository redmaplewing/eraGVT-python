# 角色製作主選單與共通設定（S55）

## 入口與範圍

`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:5–363`
由開局 `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:127` 呼叫。
Python 為 `game.creation_menu.creation_menu`，接在現有開局二擇之後：

- `[0]` 建立三名汎用角色後進入角色製作主選單。
- `[1]` 沿用既有特装戦隊捷徑，載入後也進入同一主選單。
- `[1000]` 完成時第一次 FINALIZE，返回 EVENTFIRST:135 再 FINALIZE。
- `[999]` 回傳 −1，EVENTFIRST:128–132 刪除 MASTER 以外角色並返回模式選擇。
  原作沒有減少 FLAG:8，因此第二次進入後由 3 累加成 6；照原作保留。
  MASTER_LOOP:68–76 重新清除 FLAG:100／101 並把防衛力 FLAG:852 設為 5000。

模式選擇二擇與略過序章仍是既有偏離。本階段縮小範圍，沒有把它們改成新的規則。
S60已將個別角色編輯接到共用`character_editor.character_editor`與12項子選單；初始角色狀態切換、人數變更及其餘個別子選單仍未移植，保留原入口並明確停止，詳見[角色編輯](character-editor.md)。
男性個別製作先依 `CHARA_MAKE.ERB@CHARA_MAKE_MAIN:142–145` 寫性別素質與名字，再進入同一編輯器；已存在角色依:202–204進入。
S78已接`[200]`的12套組0–9／11／14，含選擇、否決、確認、互換與編輯重入。
6／7／8的RAND:4／SETFONT／AA已手翻控制與字型，固定資料由工具抽取；套組10具體範圍仍停止，見[套組](initial-presets.md)。
初期套組依 `ERB/SYSTEM/キャラメイキング関連/SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:5–45`。
全域與共通設定可完整操作；`event_first` 與 `tools/sim.py` 多送一次 `[1000]`，其他預設選擇不變。

## 共通設定

以下路徑皆位於 `ERB/SYSTEM/キャラメイキング関連/`。

| 主選單 | 來源 | 狀態 |
|---|---|---|
| 1001 | `FIRSTSETTING_TITLE.ERB@FIRSTSETTING_TITLE:3–66` | FLAG:5、SAVESTR:10 |
| 1002 | `FIRSTSETTING_CROWNNAME.ERB@FIRSTSETTING_CROWNNAME:3–73` | FLAG:6、SAVESTR:11 |
| 1003 | `FIRSTSETTING_CROWNNAME.ERB@FIRSTSETTING_transnamegenre:76–136` | FLAG:820 |
| 1004 | `FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_TRANSCALL:453–502` | FLAG:7、SAVESTR:12 |
| 1005／1006 | `FIRSTSETTING_CHARA.ERB@FIRSTSETTING_familynamelang:1024–1044`／`@FIRSTSETTING_namelang:1045–1066` | FLAG:821／822 |
| 1007 | `FIRSTSETTING_CHARA_SYUZOKU.ERB@FIRSTSETTING_racegenre:168–182` | FLAG:823 |
| 1008／1009 | `CHARA_MAKE.ERB@CHARA_MAKE_MAIN:235–240` | FLAG:824／825 邏輯反轉 |

語言與種族名稱抽取 `ERB/DIM.ERH:282–314`；固定說明、選項、套組說明由
`tools/extract_creation_menu.py` 產生 `creation_text.py`，不在執行時解譯 ERB。
原文判斷、等待、重抽、取消均在 Python 手寫。所有 26 個套組名稱／說明函式已檢查，
只有SETUMEI 6／7／8含非PRINTL指令；一般抽取工具排除它們，S78另以extract_initial_presets.py抽取AA並原生處理亂數與字型。

## 保留的原作特性

- `FIRSTSETTING_TITLE.ERB@FIRSTSETTING_TITLE_RANDOM:70–141`：先在 :83 清空 RESULTS，
  再於 :85 判斷 `WHILE RESULTS != ""`，所以迴圈不執行；任何組成編號都回空字、不消耗 RNG。
  `[99]` 也是空字，但回傳 99。外層仍確認是否採用「無主題」，手動輸入可正常設定。
- 冠名重新抽選時 `FIRSTSETTING_CROWNNAME.ERB@FIRSTSETTING_CROWNNAME:44–46` 把 FLAG:6 清零，
  再跳回 :22 的選詞，不重新設 1；因此第二輪確認後仍可能關閉冠名。照原作保留。
- 冠名選詞復用 `FIRSTSETTING_RANDOMNAMING.ERB@FIRSTSETTING_RANDOMNAMING:278–303`，
  `@FIRSTSETTING_RANDOMNAMING_SELECT:431–438` 會寫 MASTER 的 CSTR:202；沒有另改成純選詞。
- 手動主題／冠名的文字 `999` 保留舊值，旗標先設 1；叫聲的 `999` 就是普通文字。
  停用共通項只清旗標，不清保存文字。返回保留已有值。
- 主題分類確認 `[2]` 即使沒有顯示也接受；最外層未列值自然返回，內層非法值則重印。
- 種族選單只顯示 0–9，但接受 10（ポリニアン）；99 設隨機，沒有「保留舊值」分支。
- 主選單最後以汎用角色數覆寫 RESULT:0；非汎用角色的種族／性格顯示會更新 RESULTS:0，
  依 `ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_CHECK:5–30` 與
  `ERB/ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_CHECK:5–37`，不是純格式化讀取。

## 全域與引擎

`CHARA_MAKE.ERB@CHARA_MAKE_MAIN:9–21、241–314`：進入與 `[180]` 都 LOADGLOBAL；
失敗保留記憶體既有值，仍複製進 FLAG／SAVESTR。`[170]` 顯示記憶體內容，確認 0 後
保存 GLOBAL:5–9、20–23 與 GLOBALS:15–17，再 PRINTW 等待；99 取消不寫。`[190]` 只清共通設定。

- INPUT／INPUTS：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`，各自只寫 RESULT:0／RESULTS:0。
- PRINTW：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:89–93、144–145`，
  等待不寫結果；沿既有 TextInputRequest 等待通道。
- SAVEGLOBAL 不改 RESULT；LOADGLOBAL 寫成功／失敗：同檔 :1271–1301。
- 全域檔案保存／載入失敗行為：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:2200–2310`。
- 叫聲 STRDATA：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:730–753`，19 項抽一次，
  文本來自 `FIRSTSETTING_変身デフォルト口上.ERB@FIRSTSETTING_CHANGINGCALL_RANDOM:3–26`。
- 普通函式自然終端 RESULT:0=0：同引擎 `Process.ScriptProc.cs:61–67`；不清其他結果格。

## 驗收

`tests/test_creation_menu.py` 覆蓋共通設定、原作特性、取消／重抽／非法輸入、RNG、全域跨程序存讀、
開局返回、套組取消／載入與10停止、抽取重現、Web 完成與遊戲存讀檔。完整 pytest 與標準 500 局見 STATUS。
無新增 UNVERIFIED／DEVIATION；原作已查明的特性保留，不自行修正。
