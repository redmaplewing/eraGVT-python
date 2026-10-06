# S62：W02 個別角色性格與精神素質編輯

## 完整成果
- 承接S61，完成共用角色編輯[7]的FIRSTSETTING_CHARA_SEIKAKU選單，屬W02／B02、B08。
- 性格與精神素質的可選條件、互斥／連動、修改、返回及重入均依原文；與S61的CSTR人格描述分開。
- 真正接回現有character_editor及其開局／招募／醫療／引繼呼叫者，不代按預設或寫無呼叫者的模組。
- 其他身體／種族／經歷／能力／基礎點／CSV及主製作初始狀態／人數仍是W02後續，不宣稱整包完成。

## 查證與實作
- 依序讀AGENTS、STATUS、PLAN與本規格；限定查本函式、呼叫者及必要資料／引擎依賴，不掃整包repo或口上。
- 原作引用檔案@函式:行號，引擎引用reference完整路徑:行號；不以名稱或慣例推斷欄位用途。
- 先從ERB列expected並寫table-driven紅測試，再手寫Python；expected不可呼叫實作反推。
- 固定文字優先抽取；資料驅動選項表可以，但不新增ERB直譯器。
- 核對TARGET、RESULT(S)、TALENT／CFLAG及RNG的精確副作用；保留未改設定時的原作結果。
- 沿用全新25歲人工測試資料；只驗本次數值／選單功能，不新增或執行敘事情節，不改產品年齡規則。
- 既有查證與裁決沿用，不重做年齡來源調查；若有具體新問題，一次列出函式、來源及受影響操作，獨立可做部分繼續。
- 原作錯誤／差異不自行修正；依AGENTS記錄UNVERIFIED或DEVIATION，不把原作不完整內容續寫。

## 驗收與交付
- 定向涵蓋所有選項分派、邊界、未改設定、修改／返回／重入、限制及原作殘值；少量真實GameSession邊界。
- 提供25歲人工瀏覽器fixture、確切步驟與只含一般數值的狀態端點；臨時存檔／NullNarration，主代理操作真瀏覽器到SHOP。
- 子代理定向通過後通知產品凍結；主代理跑一次全pytest及標準500，不重複跑耗時驗收。
- 500沿用tools/sim_adult.py的fresh-adult-25-v1；兩入口各seed0–249、max-shop200、actions101–108，每50局前景分批。
- 與tmp/s61/adult25-v1逐seed比較完整JSON；分開記錄遊戲停止、catalog失敗與fixture停止。
- 更新STATUS≤120、PLAN同一W02、PLAYABILITY及必要wiki／bridge；每頁只記當前狀態與必要證據。
- source/reference唯讀；LF／UTF-8無BOM；子代理不commit/push，主代理獨立驗收後明確stage並推main。
- 最後三段回報成果／依據／裁決；列清本階段範圍，不把其餘W02標完成。

## 已完成驗收
- 主代理全pytest：`3996 passed, 1 warning in 588.96s (0:09:48)`；工具title相容另獨立9案全綠。
- 真瀏覽器在25歲人工資料完成性格／素質限制、重置、亂數、title說明、確認／重入及SHOP；數值端點前後一致，catalog失敗0／瀏覽器錯誤0。
- 證據及人工資料範圍見[性格編輯](../wiki/era/character-personality.md)。
- 正式500：default247上限／3標題、tokusou250上限；catalog失敗0、fixture停止0；十批退出0，逐seed完整JSON與S61一致。
- source/reference未動，LF／UTF-8無BOM；無新增未決，COUNT仍沿既有W07事項。
