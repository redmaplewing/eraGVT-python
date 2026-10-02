# S25：ステータス畫面（SHOW_STATUS_CHARA_SELECT 與各頁）

自主推進（使用者指定 2026-10-02）第 4 階段。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. `ヒロイン関連/ステータス画面/` 全部（SHOW_STATUS_CHARA_SELECT 與 PAGE1〜5，共約 1700 行）及其呼叫的 SHOW_STATUS_CHARA_*（種族、性格、戰鬥能力、基礎、戰技、
   結界、淫紋、衣裝等）；顯示用函式照原文輸出到 TextOutput。
2. 入口：SHOP 的 [110] ステータス表示（`shop.py` 目前只顯示目標摘要）與原作中所有進入狀態畫面的位置（全域 grep 確認），
   HEROINE_PRESET 的 [20+]（`オープニング処理.ERB`:657，S24 留下的停止點）。
3. 狀態畫面中的**操作指令**（例：PAGE5 的指令 20 會生成身體資料 → 拡張度初期值等狀態變化；PAGE3 的 `SET_FSTYLE_INFO` 寫 RESULTS:0〜2，須寫進 S22 共用 RESULTS）：
   照原文移植並接上。PAGE5 顯示時 `PRINTFORM_GAPING_NOW` 會設定拡張度初期值（S11 使用者裁決「狀態畫面移植後自然會在顯示時設定」）——照原作。
4. 需要未移植系統的子畫面（武器カスタマイズ、名前・口上編輯等手動 UI）照慣例停止並列出。
5. `控えメンバー一覧 SHOP_SHOW_STATUS_RESERVE_LIST`（`shop.py:262` 目前印未實作）若屬狀態顯示系，一併移植。

## 測試（table-driven，expected 由 ERB 推導）
各頁對代表角色（預設開局的汎用キャラ與初期セット）的輸出關鍵行；操作指令的狀態變化；Web 整合：SHOP [110] → 翻頁 → 返回。

## 模擬
`tools/sim.py` 預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）；sim 的隨機按鈕會進入狀態畫面，確認無新停止並與 S24 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved 更新。結束時務必送出三段報告。
