# 與原作的偏離（需使用者決定）

凡是 Python 版與原作行為不同的地方（簡化、跳過、近似規則、額外保存的資料…）都列在這裡，
程式對應位置標 `# DEVIATION:`。使用者決定後，在該項註明「已同意（日期）」或改回與原作一致並刪除該項。

格式：`- [ ] 內容（原作：檔案@函式／reference 位置；Python：模組@函式）— 為什麼要偏離／替代方案`
ERB 路徑相對 `source/earGVP/ERB/`。

## 狀態會不同

- [ ] **亂數**：用 Python `random.Random`（可 seed），不是 Emuera 的 MT 實作；RAND 的呼叫次數也不追求一致（例：`RESEARCH_QUOTA` 的 `RAND:5` 是否短路求值）。同 seed 不會得到原作同樣的結果。（原作：`reference/.../GameData/Variable/VariableEvaluator.cs`:36–52；Python：`eragvt.state.rng.GameRng`）— 要完全一致需移植 MTRandom 並逐一核對求值順序，成本高。
- [ ] **開局：身體資料生成未移植**：`CHARA_MAKE_BASE_PROFILE`（年齡、身高體重三圍 `CHARA_SIZE_DEFAULT`、`GENERATE_BODYLINE`、髮色瞳色等的補完，含亂數）沒有執行，這些 BASE（40–48）／CSTR 維持 CSV 值或空。（原作：`SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE`:493–984；Python：`eragvt.game.opening.chara_make_initialize`）— 約 500 行＋`CHARA_SIZE.ERB` 670 行，主選單與戰鬥用不到；建議排到角色製作完整版時一併翻。
- [ ] **FLASHNEWS 未移植**：新聞產生（含亂數、寫入 `SAVESTR:20`、`FLAG:60`）沒有執行，畫面顯示「（未實作）」。（原作：`インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS`:3–752；Python：`eragvt.game.shop.flashnews`）
- [ ] **全域資料（GLOBAL）不讀不寫**：永遠走「真正的初次啟動」路徑（MOB_FLAG 初始化為 100、不套用 GLOBAL 的 config／性嗜好フィルタ），也不存成就等全域資料。（原作：`オープニング処理.ERB@EVENTFIRST`:29–45、`バージョン間互換処理.ERB@UPDATE`:95–130；Python：`eragvt.game.opening.event_first`）— 等設定畫面／成就功能時一起做。
- [ ] **開局固定路徑**：模式固定 NORMAL、初期セット固定「特装戦隊」（301–303）、config 固定「基本セット」，不顯示模式選擇／角色製作／序章畫面。（Python：`eragvt.game.opening`）— S03 規格指定的最小路徑。

## 只影響顯示

- [ ] **口上**：`MESSAGE_FIRST`、SHOP 一口メッセージ等口上文字未輸出（`NullNarrationService`），SHOP 以「無口上」的 4 行空行處理。（原作：`口上/口上システム関係/KOJO_ROOT.ERB`；Python：`eragvt.text.narration`）— S07 抽取管線處理。
- [ ] **SHOW_SHOP 簡化**：狀態條（`COLOR_BAR` 的色階與長度）以 20 格單色近似；`SHOW_SHOP_STATUS_SIGN`（生理周期・疲勞等標記）、隊伍列表的欄寬對齊與第 2 行詳細、控えメンバー一覽未移植；`SHOP_NG_ACTION_INFO` 的紅字在函式結尾重設顏色（原作不重設）。（Python：`eragvt.game.shop`）
- [ ] **未實作的選單**：`[50]`、`[110]`〜`[180]`、`[700]`、`[800]` 只顯示「（未實作）」。`[100]` 確認後停在「ACTION_MAIN は S04」。
- [ ] **WAIT／PRINTW 不阻塞**：Web 一次顯示到下一個 INPUT 為止，WAIT 位置以虛線標示，不需按鍵繼續。（Python：`eragvt.game.session`、`eragvt.web`）
- [ ] **存檔格式與檔名**：JSON（`saves/saveNN.json`），不是 Emuera 的 `.sav`；存檔說明文字（日時＋`@SAVEINFO`）與一覽格式照原作。
- [ ] **Web 專用按鈕**：頁尾「タイトルに戻る」（重建 session）是原作沒有的。
- [ ] **無效輸入訊息**：Emuera 以「刪一行＋暫時行」顯示「無効な値です」，這裡以一般行輸出。
- [ ] **SHOW_SHOP 的 TARGET == CHARANUM**：原作會因越界參照報錯，這裡視為「編成外」重新選擇 TARGET（`eragvt.game.shop.show_shop`）。

## 原作行為（照翻，但請留意）

- `USERSHOP_ACTION_CONFIRM` 的確認只有 `CASE 9` 會開始行動，`[1]はい` 會中斷回到選單（`インターミッション画面/SHOP.ERB`:521–532）。看起來像原作 bug，目前照原作；要不要修正請決定。
