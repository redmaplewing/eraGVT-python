# 開局遊戲說明（S52）

## 入口與流程

原文：`ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:403–405`，
`CALL TUTORIAL` 完成後回 `MASTER_LOOP` 重印開局選單。
實作：`game.opening.event_first_gen` → `game.tutorial.tutorial`；原文固定文字由
`tools/extract_tutorial.py` 擷取至 `tutorial_text.py`，key 為原作行號，流程手翻。

`ERB/ゲーム内_イベント発生/オープニング処理.ERB@TUTORIAL:454–581`：

| 輸入 | 原文行號 | 行為 |
|---|---|---|
| 0 | 469–484 | 遊戲目標與養成提示，PRINTW 後回主選單 |
| 1 | 486–502 | 被捕後的應對，PRINTW 後回主選單 |
| 2 | 504–517 | 資金用途與取得，PRINTW 後回主選單 |
| 3 | 519–541 | 選項效果說明，PRINTW 後回主選單 |
| 4 | 543–576 | 顯示難度提示，進入劇透子選單 |
| 999 | 577–578 | RETURN 999 |
| 其他 | 579–580 | 保留畫面，只再等待 INPUT |

劇透子選單的 99 回主選單、1 顯示進階提示並 PRINTW 等待，其他值只重等。
每次回主選單都重新顯示 :456–465，沒有清除歷史文字。
:480–482 的 REVERSE 說明已被原作註解，不抽取、不補寫。
全函式沒有其他 CALL、設定寫入、亂數或未完成分支；文字提到的遊戲功能不在本階段新增。

## 引擎依據與狀態

- INPUT 只寫 RESULT:0：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`。
- PRINTW 輸出、換行、ReadAnyKey：`reference/emuera-1824/Emuera/GameData/Expression/ExpressionMediator.cs:50–65`。
- ReadAnyKey 預設為 EnterKey：`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508`。
  同檔 :701–734 只有數值／字串輸入會寫結果；EnterKey 不改 RESULT／RESULTS。
- Web 沿用既有 TextInputRequest 等待通道及暫時的「按 Enter 繼續」提示；送出後移除提示，
  不把等待值當 INPUTS，也不提前顯示下一頁。
- 本函式不改色彩、字型或對齊；原有顯示狀態沿用。RESULT:0 隨數值輸入更新，退出為 999；
  其他 RESULT 格、RESULTS、角色／全域資料、RNG 保持不變。

## 驗收

`tests/test_tutorial.py` 從原文推導所有章節、無效值、劇透分支、等待、重入、顯示狀態及結果殘值；
固定文字可重抽，排除註解，兩種開局皆覆蓋 Web 讀完說明後正常到 SHOP。
`tests/test_config.py` 的舊停止斷言改為說明可進出，保留全域設定後接續操作的驗證。
500 局標準回歸與完整 pytest 摘要見 STATUS；原文與引擎目錄均唯讀。
無新增 UNVERIFIED／DEVIATION。
