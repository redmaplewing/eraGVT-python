# 種族、變身能力與基礎點（S63／W02）

原作路徑相對`source/earGVP/`。實作在`game/character_build.py`；固定文字由`tools/extract_character_build.py`抽取，沒有增加ERB直譯器。

## 共用入口與權限

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:249–252、271–274、310–313`：[4]種族、[10]變身能力、[23]基礎點已接回開局／招募／醫療／引繼既有共用入口。
- [4]要求非固有角色且ARG:2=0；[10]只要求非固有角色；[23]固有角色也能使用。醫療ARG:2=1只鎖種族與CSV，沒有新增整個角色不可編輯的限制。
- 三頁沒有額外GLOBAL解鎖檢查。子供基礎點上限由CFLAG231控制，不依年齡判斷；原作獎勵已在引繼呼叫端加到修練P，主入口ARG:1僅在CSV重載使用，進入這三頁不重複加點。原有依據見[共用編輯器](character-editor.md)。

## 種族與feat

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SYUZOKU.ERB@FIRSTSETTING_CHARA_SYUZOKU:4–165`：顯示0–10，但`:39–42`的上界允許手輸11；確定時只清TALENT201–211，再設201+選項，因此選11會設定212，再選其他種族也不清212。保留原文，不補隱藏按鈕或擴大清除範圍。
- 選種族後依`ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@FEAT_ABLE_F:92–239`過濾原有1100–1299。每種六個可選feat，最多三個；吸血種每次繪頁強制1110。即使手動切換1110，也會在下一次繪頁重新打開。
- feat頁[1]取消只回種族頁並重新讀角色原有feat；確定之前不寫角色。種族頁沒有整個子流程的取消鍵。[0]確定才寫種族及feat，呼叫`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE:4–19`重算兩種形態的尺寸；不改年齡、空中能力或其他戰鬥基礎值。
- 機器種女性另問功能旗標，之後口上不是1才詢問是否改1。原文`:149`對非法口上輸入跳到前一題的INPUT_LOOP_1（包含男性）；照原文保留，沒有修成重問口上。
- 說明實呼叫catalog的`ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_INFO:32–89`與`@FEAT_INFO:243–418`；真catalog缺函式／執行失敗明確停止。只有驗證用Null敘事顯示函式標記，不能把Null截圖當原文敘事驗收。

## 變身能力

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_CHARA_TRANSABILITY:4–60`：選0／1／2，TALENT200依序設1／0／-1。空中能力直接讀CSV BASE22；非戰鬥員先減1，再夾0–5，同寫BASE與MAXBASE22。沒有額外套用有翼feat或重抽亂數。
- 先依當時TALENT呼叫`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:25–284`，將RESULT2–7寫MAXBASE43–48；選1／2才於尺寸生成後清變身時TS。因此這次尺寸可能保留剛清除TS之前的形態，不自行補算。
- 同函式`:239–249`的CUP_SIZE保留RESULTS0；確認PRINTW使用真正等待請求，不修改RESULT(S)。自然終端只把RESULT0設0，其他數值尾格保留。
- CSVBASE缺欄0、缺角色錯誤：`ERB/汎用関数/コモン関数.ERB@CSVBASE_F:966–969`；`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1383–1418`。沿用既有`export_csv.csvbase`，不把缺角色視為0。

## 基礎點與扣還

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_STATUS_BONUS.ERB@FIRSTSETTING_STATUS_BONUS:4–926`：進頁複製CFLAG50–56；修練P與TALENT即時修改，只有[200]把七格暫存寫回CFLAG並RETURN 1。沒有取消或交易回滾，也不在此修改BASE／MAXBASE。
- 七格對應BASE0、1、2、10–13；前兩格每點顯示+10，其餘+1。按鍵尾數0／1／2／3為-5／-1／+1／+5。`:614–626`依序限制現有點數、上限、下限，順序不可換；上限一般40、CFLAG231非零20，下限-20，修練P每點扣還10。
- 五組偏好（近／中／遠／空中／回復）成本為苦手-5、普通0、得意15，扣還新舊差額；資金不足不改。若前態同時有得意與苦手，購買判斷先讀得意，但[201]兩者分別扣還。
- 關係成本：友人5、警察關係者10／20、情報屋15、裕福10，切換／清除同樣扣還差額。原文沒有增加全域解鎖或一次購買限制。
- 同函式`:379–474`的關係顯示保留全形括號、成本欄寬與「＋１／＋２」按鈕；警察等級2顯示「警察上層部　（+20）」，新增9案先紅後綠，修正後本模組定向`105 passed, 1 warning in 3.45s`。
- 結界每項5點，五項合計上限`3 - (任一形態為男性)`（感覺數4見`ERB/DIM.ERH:154`）；V與避妊互斥，已有項目可退費。顯示灰色的上限硬編碼3與實際男性上限2不同，照原文保留。
- [201]退還七格、戰鬥偏好、四個部位結界與關係；原文`:547–562`沒有清除或退還避妊結界。本次不自行補上。
- [999]在**現有分配上**抽`修練P / 10`次RAND7，每次加1／扣10，尾數保留；原文`:918–922`沒有上限或子供上限檢查，因此可以超過40／20。FOR終值只讀一次：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1731–1743`。
- 除錯顯示`:33–91`刻意讀TARGET，不是ARG，每個TIMES逐步截斷；沿`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`與既有`era.times`。不改TARGET。
- INPUT／自然終端沿`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`、`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`；PRINTW沿`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734`。共用COUNT未完整模型化仍是既有W07議題，不在這裡宣稱消除。
- 主製作[1000]另有**完成製作補足**：`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:207–210`呼叫`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE:245–251`，將剩餘修練P/10次RAND7追加CFLAG50–56，每次扣10；`:356–364`才把最終分配加進BASE。因此子選單重入與完成製作後是兩個不同驗收時點，不能要求SHOP仍維持未分完的CFLAG。

## 驗證與剩餘範圍

- 新增105案，缺模組及關係顯示先紅後綠；修正後本模組定向`105 passed, 1 warning in 3.45s`。expected由上述ERB推導，包含每種六個feat切換、隱藏11、取消／重入、固定feat、非法值、CSV錯誤、扣還／限制／亂數、原作怪處、RESULT尾格、固有／醫療限制、獎勵不重複加與真GameSession到SHOP。
- 原作顯示catalog有獨立實跑案例，零失敗、RNG不變；這與Null瀏覽器fixture分開記錄。固定文字抽取可重現。
- `tmp/s63/browser_fixture.py`（gitignored）：`python -X utf8 tmp/s63/browser_fixture.py --port 8779`；全新fresh-adult-25-v1定義、Null敘事、臨時存檔。`/fixture/state`只讀一般數值，全員年齡檢查沿S60工具，未修改產品年齡規則。
- 主代理真瀏覽器：種族11手輸、吸血種固定feat／取消、人間feat確認；變身→非戰鬥員→恢復變身及按鈕／Enter等待；基礎點減點／偏好退款／關係與結界扣點、確認／重入後到SHOP。重入前後完整數值一致，points150、CFLAG50=-5、BASE0=1000；畫面950是加成顯示，未直接覆寫BASE。
- 關係名稱修正後另重啟fixture，驗證等級2顯示「警察上層部（+20）」及全形＋１／＋２；降回1退回10點，瀏覽器錯誤0，年齡保持25（未設變身年齡格-1）。Null端點的catalog失敗欄是常數，不列為catalog實測證據。
- 證據：`tmp/s63/build-settings-verified.jpg`、`police-level2-verified.jpg`及`browser-*.json`。主代理全pytest／正式500與S62逐seed比較結果由STATUS收口；人工前態及Null敘事不代表自然完整通關。
- 主代理真瀏覽器在[23]重入前後完整數值一致：修練P150、CFLAG50–56為`[-5,0,0,0,0,0,0]`；接著99→1000→1到SHOP時修練P0、CFLAG為`[-2,1,1,2,3,3,2]`，增量合計15，符合上述既有FINALIZE。原先要求SHOP仍是-5的斷言混用了完成製作前後的expected，屬驗收斷言錯誤，沒有修改產品或因此重跑。
- 性別、經歷、CSV讀入、SIZE_SETTING剩餘操作與主製作初始狀態／人數仍屬W02；TS與特殊裝備生命週期仍W03。未新增UNVERIFIED或DEVIATION。
