# 設施擴充（S45）

入口為SHOP [150]，原生實作`eragvt.game.facilities.facilities_gen`。
以下省略路徑的行號皆指`ERB/インターミッション画面/SHOP_ENHANCING.ERB@HOME_ENHANCING`。
文字由`tools/extract_facilities_text.py`抽取；只做固定欄位插值，規則不交給ERB直譯器。

## 入口與升級

- `ERB/インターミッション画面/SHOP.ERB@USERSHOP:275–278`只排除GAMEOVER；沒有存活角色或FLAG:63門檻，只有MASTER也可操作。
- `:44–51`列0鍛錬、1休憩、2防衛、3放鬆設備、4研究；999離開。錯值只重讀INPUT，不重繪整張選單。
- `:54–144、296–325`四種等級≥5不可再升；顯示值>4為MAX。
  每次升級先顯示費用，0確認／1取消；包括999在內的其他值均提示後重問確認，不當成取消。

| 選項 | 等級欄位 | 升到下一級的費用 |
|---|---|---|
| 0 | FLAG:50 | MONEY扣5000×（當前等級+1） |
| 1 | FLAG:51 | MONEY扣1000×（當前等級+1） |
| 2 | FLAG:52 | MONEY扣10000×（當前等級+1） |
| 4 | FLAG:54 | FLAG:200欠片扣5×（當前等級+1），不扣資金 |

不足不修改資源／等級；成功加一。成功、取消、資源不足皆返回主選單。
防衛設備資金不足`:131`是PRINTL，不等待；其他不足`:69、100、312`是PRINTW，依原文分別處理。

## 放鬆設備

`:147–294`另有[99]回主選單，購入沒有第二次確認。bit定義在`ERB/DIM.ERH:173–184`。

| 按鈕 | 設備原名 | bit | 價格 | 前置bit |
|---|---|---:|---:|---:|
| 0 | 観葉植物 | 1 | 500 | 無 |
| 0 | 心休まる風景画 | 512 | 4500 | 1 |
| 0 | オシャレなオブジェ | 1024 | 8500 | 512 |
| 0 | ゴージャスな噴水 | 2048 | 100000 | 1024 |
| 1 | 上質なベッド | 2 | 12000 | 無 |
| 1 | 最高級ベッド | 4 | 95000 | 2 |
| 2 | マッサージチェア | 8 | 25800 | 無 |
| 3 | シャワー設備 | 16 | 50000 | 無 |
| 4 | ゲームコーナー | 32 | 100000 | 無 |
| 5 | 大浴場 | 64 | 200000 | 無 |
| 5 | 美容温泉 | 128 | 500000 | 64 |
| 6 | ビューティサロン | 256 | 1500000 | 無 |

- 選單逐項檢查未持有與前置bit；輸入則依原作ELSEIF順序選第一個符合項。
  非連續bit狀態也不自行修補：可能同時顯示相同按鈕，購買仍以第一個符合項為準。
- 升級保留低階bit；主選單的已購入摘要會隱藏被上級取代的床／浴場文字，但效果仍按各bit判斷。
- 全買檢查是`FLAG:53 == 4095`，不是`FLAG:53 & 4095 == 4095`；保留精確比較。
- 成功扣款並OR入bit後重畫目錄；資金不足、錯值與重複購入只重讀INPUT，不重買或退錢。

## 效果已有實際呼叫者

- 鍛錬：`ERB/ゲーム内_行動実行処理/ACTION_TRAINING.ERB@TRAINING:15–23、@TRAINING_DOWNTAIRYOKU:325–340`，
  沿用`action.training`與`shop.training_downtairyoku`；等級改變成長量及體力消耗。
- 休憩：`ERB/ゲーム内_行動実行処理/ACTION_REST.ERB@REST:9–18、59–105`，
  沿用`action.rest`；設施等級改變回復比例，放鬆設備bit另影響疲勞恢復。
- 回合恢復：`ERB/インターミッション画面/SHOP_TURNEND.ERB@RECOVERY_OVER_TIME:615–625、660–677`，
  沿用`turnend.recovery_over_time`；設備等級加回復比例，植物等RNG一律用注入的state.rng。
- 防衛：同檔`@DAILY_DEFENCE_CHANGE:397–448`，等級影響危險度與每回合防衛力加值（等級平方×5）。
  `ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB@RAID_HANTEI:100`與同目錄
  `FORCE_深夜の子触手襲来.ERB@SMALL_TENTACLE_HANTEI:56、66`、`ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:348`的既有實作亦讀FLAG:52。
- 研究：`ERB/武器と衣装/衣装関連/CLOTHDATAアウター_特殊.ERB@CLOTH_CUSTOMIZE_OPTION_199:323–342`，
  既有`clothing`／`clothing_custom`依FLAG:54解鎖項目；醫療室隱藏手術門檻依
  `ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:220`要求5。
- 原作FLAG:50–54的其餘直接引用包含開局／舊版相容、ENDING／SCORE／SUCCESSION、自由行動文字及口上選取；
  分別已有opening／ending／succession／pastime與catalog承接，本階段不另外重做。

## 輸入、顯示與保存

- INPUT只寫RESULT:0，結束一般函式設0；依`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`及`Process.ScriptProc.cs:61–67`。
- `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:701–737`在輸入後顯示輸入文字，本入口局部回顯數值。
  PRINTW等待沿用S44查證的EnterKey語意（同檔`:497–508`），不寫RESULT／RESULTS；沒有新增遊戲選項。
- 暫時的「按 Enter 繼續」操作提示在繼續時移除，不算入原作CLEARLINE的行數。
  CLEARLINE仍沿用已登記的「僅刪已完成行」顯示偏離；未宣稱Web換行／畫面幾何完全等同引擎。
  引擎依據：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–501`、`GameView/EmueraConsole.Print.cs:156–177`。
- FLAG:50–54與MONEY原本就在JSON存檔中；沒有新增欄位或格式版本。

## 驗證

- 先紅為新模組未建立；104項定向全綠：各等級／資源邊界、12設備與前置bit、全部持有／非連續bit、
  錯值／取消／返回、插值與確認按鈕保留、5類購入後實際效果、存讀檔、GameSession.screen及Web空白Enter。
- `104 passed, 1 warning in 3.56s`；既有Starlette/httpx警告。
- 主代理獨立完整pytest：`2979 passed, 1 warning in 358.92s (0:05:58)`；既有Starlette/httpx警告。
- 標準500局：default246上限／4回標題、tokusou250上限，catalog失敗0；逐seed全部欄位與S44一致。
  default／tokusou各seed0–249、max-shop200、actions101–108；10個50局獨立前景批次exit=0，seed全集與log／JSONL一致。
  產物及audit留在`tmp/s45/`，主代理亦獨立核對通過；標準模擬不操作[150]，選單與效果另由定向測試驗證。
- 無新增UNVERIFIED，沿用顯示偏離已在deviations.md說明。
