# S11：拡張度（CFLAG:34 ≠ 0）與いちゃラブセックス（LOVESEX_NIGHT）

## 背景
S10 把開局改回原作預設（3 名汎用キャラ）後，預設角色 `CFLAG:34 = 1`（CHARA_MAKE_DEFAULT.ERB 汎用分岐末尾），
隨機模擬 250 場全部在敗北前停止：拡張度 159、LOVESEX_NIGHT 90（平均 4.58 次 SHOP）。本階段移植這兩個系統，讓預設開局可以玩下去。
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **拡張度**：`ゲーム内_戦闘処理/GAPING.ERB` 中 `CFLAG:34 ≠ 0` 才會走的部分。
   - `V_GAPING`（:851）、`A_GAPING`（:932）、`GET_V_GAPING_EXP`／`GET_A_GAPING_EXP` 的 CFLAG:34 ≠ 0 分岐、
     `GAPING_RANK_STR`、`GAPING_RANK_TO_POINT`、`GAPING_SIZE_TO_POINT`、`GET_HEIGHT`／`GET_HIP`（尚未移植者）、
     `PRINT_TENTACLE_SIZE`（:754）、`PRINTFORM_GAPING_NOW`（:789）。
   - 解除 `battle/gaping.py:_need_no_gaping`、`prison/commands.py`（PRINT_TENTACLE_SIZE）的停止點。
   - 拡張度經驗在戰後／回合結束的累積與回復（若有：以 GET_*_GAPING_EXP 的呼叫者為起點全域搜尋）。
   - `MESSAGE_SEX_SPCOM7`:1234–1260 的動画サイト表示（CFLAG:34 > 0）：若是 INPUTS 互動，照 S03 以來的輸入模式接 Web；
     若牽涉動画流出系統本體（未移植），照慣例停止並記錄。
   - 顯示：SHOP／狀態畫面若已有顯示拡張度的位置則接上，沒有就不新增畫面。
2. **いちゃラブ**：`ゲーム内_イベント発生/強制発生イベント/FORCE_いちゃラブセックス.ERB` 全體
   （`LOVESEX_NIGHT`、`LOVESEX_KIND`、`SEX_V`、`SEX_A`、`SEX_V_CONDOM`）與 SHOP_TURNEND 的呼叫條件（`turnend.py:381` 附近）。
   - 地の文 `MESSAGE_LOVESEX_NIGHT`、`MESSAGE_KATAOMOI_NIGHT`、`MESSAGE_SEX_V`、`MESSAGE_SEX_A`（`地の文/MESSAGE_SEX.ERB`）
     一律走 S07 catalog；其中的狀態變化照 hooks 表方式移植並對照測試。
   - `PALAM_VABCestimate`、`PALAM_CAL`、`AFTER_PILL`、`_ABLUP` 等依賴：已移植者重用，未移植者照原文移植。
   - `NINSIN_HANTEI` 判定照既有移植；受精成立以後仍屬未移植系統，照慣例停止（不在本階段）。
3. **交際相手**（TALENT:交際相手 1–4）的取得與變化條件若在上述流程中被讀寫，只移植被讀寫到的部分，不擴大到戀愛系統全體。

## 不做
- 受精成立以後（妊娠）、動画流出系統本體、戀愛事件全體、角色製作畫面的拡張度設定 UI。

## 查證要點
- CFLAG:34 等番號的意義照 `CSV定数定義/` 與原文註解。
- 引擎語意（INPUTS、PRINTFORM 寬度、SELECTCASE 等）附 `reference/emuera-1824/...cs:行號`。

## 測試（table-driven，expected 由 ERB 推導）
- 拡張度：V_GAPING／A_GAPING 在數個尺寸／經驗組合下的結果；RANK_STR、TO_POINT 邊界；PRINT_TENTACLE_SIZE 輸出。
- LOVESEX_NIGHT：觸發條件（交際相手、片思い、體力等）、LOVESEX_KIND 分岐、SEX_V_CONDOM 的選擇、PALAM 結果（FixedRng）。
- 既有測試全綠；初期セット路徑的 expected 不應改變（CFLAG:34 = 0）。
- 整合：預設開局 → 性攻擊命中 1 次；預設開局 → 夜間いちゃラブ 1 次 → SHOP。

## 模擬
隨機方針 250 場（seed 0–249），預設開局與初期セット各跑一次：停止原因頻度、停止前 SHOP 次數、敗北局數，
與 S10（預設 4.58／17、敗北 0）對照，寫進 STATUS。模擬腳本放 `tools/sim.py` 並 commit（之後各階段共用，避免每次重寫）。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；必要時 `docs/wiki/era/gaping.md`（< 300 行）。
