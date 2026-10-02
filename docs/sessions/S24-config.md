# S24：設定畫面（CONFIG）與開局プリセット選擇

自主推進（使用者指定 2026-10-02）第 3 階段。目標：玩家能在網頁上選擇プリセット、改設定（例：打開ヒロイン悪堕ち機能），
解除 deviations.md「開局的 UI 跳過」中 HEROINE_PRESET 的部分，以及「全域資料（GLOBAL）不讀不寫」中 config 的部分。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **CONFIG_INIT 全プリセット**：`SYSTEM/コンフィグ/CONFIG_初期設定.ERB`（CASE 0〜3；CASE 0 從 GLOBAL 繼承）。目前 `opening.config_init` 只支援 1。
2. **開局 HEROINE_PRESET**：`オープニング処理.ERB`:173 `CALL HEROINE_PRESET`（定義約 :617 起）與 :758 `CALL CONFIG_INIT(LOCAL)`、:401／:654 `CALL CONFIG("mainmenu")`。
   照原文顯示選單並接收輸入；**預設仍為 [1] 基本セット**（不改變「おまかせ」開局的結果，既有測試的 expected 不得因此改變）。
   Web 的新遊戲流程：在既有的 2 択之後加入 HEROINE_PRESET 畫面（或依原文順序插入），照原作輸入模式。
3. **設定畫面本體**：`SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG`（:68–516，各分類切換 FLAG:800〜805 的 bit），以及
   `CONFIG_GLOBAL_MANIAC.ERB`／`CONFIG_GLOBAL_MOB.ERB`／`CONFIG_GLOBAL_TRANSFORM.ERB` 中由 CONFIG 畫面呼叫的部分。
   SHOP 的進入點 `インターミッション画面/SHOP.ERB`:303 接上（SHOP 選單照原文顯示該項）。
4. **GLOBAL**：config 相關的 GLOBAL 讀寫（FLAG:800 自動ロード、GLOBAL:11〜15、MANIAC／MOB／TRANSFORM 所用的 GLOBAL／MOB_GLOBAL）
   照原作實作，使用既有 `state.GlobalState`；SAVEGLOBAL／LOADGLOBAL 的時機與檔案查 `reference/emuera-1824`（附行號），
   在 Web 端以獨立的全域 JSON 檔保存（與存檔分開，存放在 saves 目錄）。成就／歷代紀錄等其他 GLOBAL 用途不在範圍，deviations 該條縮小範圍。
5. 若 `CONFIG_SYSTEM.ERB` 中某些設定項目會開啟尚未移植的系統（雜魚戰、クズ市民戰等），照原作允許切換；遊戲中走到未移植系統時照慣例停止。
   在 STATUS 中列出「打開後會碰到未移植系統」的設定項清單。

## 測試（table-driven，expected 由 ERB 推導）
- CONFIG_INIT 0〜3 的 FLAG:800〜805；HEROINE_PRESET 各選項；CONFIG 畫面切換 bit 的代表 case；GLOBAL 存讀往返（含自動ロード）。
- Web 整合：新遊戲選淫獄セット → SHOP；SHOP 進設定畫面切換一項 → 返回。

## 模擬
`tools/sim.py` 加 `--preset N`（0〜3，0 需 GLOBAL 則略過或以空 GLOBAL 執行並註明）：預設（=1）、初期セット、`--preset 2`、`--preset 3` 各 250 場（seed 0–249，`--max-shop 200`；可分批），
停止原因與 S23 對照（預期 2／3 會碰到未移植系統，列出頻度）。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、`docs/wiki/era/flow.md` 更新。結束時務必送出三段報告。
