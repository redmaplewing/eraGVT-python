# S16：ＳＰ変身・ＳＰバースト・バースト攻撃（COM73／70／74／17）

## 背景
S15 後，模擬中除了跑到上限以外的停止全部來自戰鬥指令：ＳＰ変身（COM73）、ＳＰバースト（COM70）、ＳＰフルバースト（COM74）、
バースト攻撃（COM17，`TCVARn:217` bit0 的切換）之後的命中／回避／傷害補正。
停止點：`battle/commands.py`（COM17 表示・本體、COM70／73／74）、`battle/hantei.py`（:177、:281、:337、:445、:545、:638 的 COM17 補正）。
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **指令本體**：`ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF73.ERB`（ＳＰ変身）、`COMF70.ERB`（ＳＰバースト）、
   `COMF74.ERB`（ＳＰフルバースト）、`COMF17.ERB`（バースト攻撃切換），以及 `COMABLE.ERB` 中這些指令的可用條件（已移植者對照確認）。
   被呼叫的 `MESSAGE_BATTLE_CHARA_SP_TRANSFORMCALL`／`_SP_BURST`／`_SP_FBURST` 等地の文走 S07 catalog（狀態變化走 hooks 表）；
   `PRINT_DISTANCE`、`SEIKAKU_CHECK "GET_TALENT_VALUE"`、`ADDBATTLESITUATION` 等依賴已移植者重用，未移植者照原文移植。
2. **ＳＰ変身狀態（CFLAG:1 == 2）的全部影響**：全域搜尋 `CFLAG:1 == 2`／`CFLAG:1 >= 2` 等在**已移植檔案**中的分岐，
   逐一確認已照原文移植（例：胸部重量補正改用 MAXBASE、消耗度固定 100、CORRECTION_TRANS），缺的補上；
   ＳＰ変身的持續與解除（戰鬥結束、回合結束）照原文。
3. **バースト攻撃**：`TCVARn:217` 的切換與 `hantei.py` 6 處補正（命中、カス当たり、回避、[反撃]攻撃力、傷害）、
   `commands.py` 的バースト表示；照 `COMMON_BATTLE_HANTEI.ERB` 等原文移植。
4. 若某補正需要的系統屬 S16 範圍外（例如 [反撃]スタイル本體、HANGEKI_TO_TENTACLE），只移植補正式本身，
   系統本體照慣例停止並記錄。

## 不做
- [反撃]スタイル（反撃準備・ＥＸ反撃・HANGEKI_TO_TENTACLE）本體、COM15 救出以外的其他未移植指令、悪堕ち戰。

## 查證要點
- TCVARn／CFLAG 番號與意義照 `●開発者向け資料/●GVTフラグ一覧.txt` 與 `CSV定数定義/`。
- 引擎行為（INVERTBIT、TIMES 等）附 `reference/emuera-1824/...cs:行號`（已查證者引用既有註解即可）。

## 測試（table-driven，expected 由 ERB 推導）
- COM73／70／74：可用條件、狀態變化（CFLAG:1、ＥＸゲージ、狀態異常回復等）、RETURN 值（FixedRng）。
- COM17：切換前後的 TCVARn:217，以及 hantei 6 處補正的數值（手算）。
- ＳＰ変身中的各補正分岐（至少胸部重量、消耗度、CORRECTION_TRANS）。
- 整合：戰鬥中ＳＰ変身 → 攻擊 → 戰鬥結束後解除。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因頻度、停止前 SHOP 次數，與 S15 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；wiki 只在必要時新增（< 300 行）。結束時務必送出三段報告。
