# 角色強化（S41）

入口：`ERB/インターミッション画面/SHOP.ERB@USERSHOP:251–254` 的 [111]。
只有非ゲームオーバーモード且 `CHARANUM_ACTIVE()` 非0才進入。
實作：`eragvt.game.character_powerup.character_powerup_gen`，由 `GameSession` 直接呼叫。
以下主函式引用均為 `ERB/インターミッション画面/SHOP_CHARA_POWERUP.ERB@CHARA_POWERUP`。

## 選取與分配

- :29–36：CHARANUM≥3 呼叫 `ERB/汎用関数/コモン関数.ERB@CHARA_LIST:303–355`，參數1、2。
  排除MASTER、CFLAG:999=0與CFLAG:0非0；顯示修練P。[999]取消並回傳0。
  CHARANUM<3則直接指定1，不再檢查角色資格。
- :43–61：初始預覽使用MAXBASE，欄寬至少4，以MAXBASE+1的位數擴大；每圈將TARGET寫入LOCAL:99，再指定新TARGET。
- :64–87：每圈先更新部位結界；上一位／下一位只搜尋CFLAG:999非0、CFLAG:0=0的角色。
- :336–343：退出恢復當圈LOCAL:99。因此選取後立即退出可回到原TARGET；任何一次重繪後，退出通常留在該角色。
  切換後立即退出回前一角色，並非固定恢復整個選單進入前的TARGET。
- :523–538：[200]與角色切換清空所有未確認分配及費用；確認後也清空。
  全程未確認前不扣修練P／資金、不修改刻印或基礎值；每圈的結界上限更新仍照原作執行。

## 費用與確認

| 指令 | 分配效果 | 費用／限制 |
|---|---|---|
| 0–63的尾數0／1／2／3 | 七項基礎值減2段／減1段／加1段／加2段 | 每段50修練P；只能撤回本次分配 |
| 70–74 | 五種刻印各減1級 | 當下未消除等級×100，再套兩次性格補正 |
| 79 | 取消全部刻印消除 | 退還本次分配的費用 |
| 80–83 | 以修練P重建部位結界 | 每部位30P；再次選取取消 |
| 85–88 | 以資金重建部位結界 | 等級×625；再次選取取消 |
| 89 | 取消全部重建 | 清除兩種重建方式及資金費用 |
| 90–94 | 取得Ｃ／Ｖ／Ａ／Ｂ／避妊結界 | 各50P；再次選取取消 |
| 100 | 一次確認 | 修改角色、扣款、LEVELSTATUS、更新結界上限 |

- 基礎值：:358–390、481–491、543–561。體力／氣力每段+50，性耐性及四戰鬥值每段+5。
  寫BASE:50／51／52／10／11／12／13；當前體力／氣力／性耐性不補滿。
  **沒有購買基礎值上限**；MAXBASE由 `ERB/汎用関数/コモン関数.ERB@LEVELSTATUS:885–894`、
  `@LEVELSTATUS_UP:901–918` 限制體力／氣力99999，其他9999。達上限仍允許付款。
- 刻印：:172–190、386–398、493–498。對應PALAM為13／16／14／17／15。
  `ERB/ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_PALAM_F:472–848` 的補正各自截斷，
  例如性格12的欲情：100→115→132。確認時MARK:90–94保存消除前較高等級，已有更高紀錄不降低。
- 重建：:399–425、499–504。BASE<MAXBASE且資源足才可選；可互換支付方式，原已分配費用隨之改變。
  輸入分支**沒有檢查TALENT**，因此未顯示的部位仍可用數值鍵操作，只要耐久條件成立。
- 取得：:426–477、505–518。已有或待取得的結界合計上限3；通常或變身任一型態為男性時上限2。
  Ｖ與避妊互斥；已有素質不重複付費。四部位取得時先以舊MAXBASE算耐久，再由LEVELSTATUS更新上限。
  共用 `ERB/汎用関数/コモン関数.ERB@BASEUP_CAL_SHIELD:638–648`、`@CAL_SHIELD_F:653–656`。
- [400]：:349–356，隱藏debug切換FLAG:999 bit0；整值恰1才設定深藍背景，否則回預設背景，跳過本圈預覽計算。
- 原文:262–270的重建[89]按鈕位置計算偏一位，正常最後一個結界不顯示[89]；仍可手動輸入89。
  灰色按鈕僅提示，所有允許／拒絕均照各輸入分支，未額外加防護。

## 引擎與共享結果

實際核對下列唯讀原始碼，沿用共用輸入、格式與背景色實作：

- `reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`：INPUT只寫RESULT:0，INPUTS寫RESULTS:0。
- `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2006–2023`：無參數RETURN寫RESULT:0=0；
  `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`：普通函式流落結尾同樣寫0。
- `reference/emuera-1824/Emuera/GameData/StrForm.cs:233–263`：數字欄寬向左補空白，字串欄寬考慮全形。
  主函式:118的RESULTS逐欄覆寫，畫面最後保留格式化後知性預覽；RESULTS:1以後不碰。
- `reference/emuera-1824/Emuera/GameView/PrintStringBuffer.cs:111–119、275–285、313–330`：
  PRINTPLAIN先結算前段PRINT的按鈕，再加入不可點文字；主函式全部10處PRINTPLAIN照原文保留，避免狀態／合計變成按鈕的一部分。
- 部位結界顯示的PERCENT_CAL及COLOR_BAR沿用共用函式並同步RESULT:0；退出則按RETURN歸0。

沿用的顯示偏離：共用CLEARLINE只刪已完成行，詳見 `../bridge/deviations.md`。
本入口沒有成就呼叫，不新增GLOBAL成就空操作影響；沒有新增UNVERIFIED。

## 驗證

- 99項原文推導測試：費用不足／恰足／超額、確認前不生效、反覆確認、取消、切換、資格與單人捷徑、
  刻印歷史、二次性格截斷、結界取得數量／互斥、重建支付互換、隱藏輸入、MAXBASE上限、共享RESULT(S)、debug、PRINTPLAIN按鈕分段及GameSession往返。
- S39／S40／S41定向：`343 passed in 10.98s`；主代理獨立完整pytest：`2622 passed, 1 warning in 219.96s (0:03:39)`（既有Starlette警告）。
- 標準500局：default／tokusou各seed0–249、max-shop200、actions101–108；10個50局獨立前景程序皆exit=0。
  default為246上限＋4標題返回，tokusou為250上限，catalog失敗皆0；seed全集、verbose log與JSONL一致，
  500筆完整record（含events）逐seed與S40完全相同。產物及核對摘要留於`tmp/s41/`。
  標準腳本不操作角色強化，功能由定向測試涵蓋。
