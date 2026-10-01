# S19：悪堕ちキャラの淫謀＋洗脳／悪堕ちキャラ戰

## 背景
使用者指定（2026-10-01）。悪堕ち／洗脳相關的停止點在程式中共 42 處（`grep -rn NotImplementedError src | grep 悪堕ち\|AKUOTI\|洗脳\|CORRUPT`），
分布在：強制事件（`turnend.py` AKUOTI_EVENT）、悪堕ち容姿（opening／party／prison 的 CORRUPT_CHANGE_LOOKS_MAIN、RECOVER_CORRUPTION）、
以及戰鬥內的「敵＝悪堕ち／洗脳キャラ」各分岐（encount／enemy／hantei／sexcom／syasei／palam／source_check／restraint／cheers／cloth／commands／gaping／train）。
S12 起ゲームオーバーモード中只要有悪堕ち角色，AKUOTI_EVENT 每回合必發生。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **事件**：`ゲーム内_イベント発生/強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB` 全體（AKUOTI_ATTACK 已移植部分對照確認、AKUOTI_EVENT）。
2. **悪堕ち容姿**：`ヒロイン関連/悪堕ち/CORRPUTION.ERB`（CORRUPT_CHANGE_LOOKS_MAIN 等）、`CORRUPTION_RECOVER.ERB`（RECOVER_CORRUPTION）；
   接上 opening／party／prison 的停止點。容姿設定若有 UI，照「跳過 UI 走原作預設路徑」規則。
3. **洗脳／悪堕ちキャラ戰**：上述戰鬥模組中所有「FLAG:111 ≠ 0（敵為角色）」的分岐——
   遭遇（`ENCOUNT_ENEMY`:76–129）、敵行動選擇（SELECT_ENEMY_ACTION、ENEMY_ACTION 各分岐、ENEMY_ACTION_SEX_ROUTINE:1173–1344）、
   命中判定、性攻擊與追加責め、敵絶頂・搾精、刻印、勝利／敗北（`BATTLE_COM_AFTER.ERB`:980–981、1044–1087）、
   拘束中指令與罵倒／反抗、COM47「説得する」、觀衆反應（PERFORM_CHEERS_HATE 等）、衣裝、觸手尺寸（SET_TENTACLE_SIZE ARG:2 > 0）。
   地の文 `地の文/MESSAGE_OTHER.ERB`／`MESSAGE_AKUOTI.ERB` 等走 S07 catalog，狀態變化以 hooks 表。
4. 範圍很大：若單一 session 做不完，**優先順序**為 (a) AKUOTI_EVENT 能觸發並完整打完一場悪堕ちキャラ戰（含勝敗）→
   (b) 容姿變化與回復 → (c) 其餘較罕見分岐。未完成的分岐保留停止並在報告中列出剩餘清單，不得以近似邏輯代替。
5. ラスボス相關分岐（source_check「ラスボス／悪堕ちキャラへの勝利」中的ラスボス部分）不在範圍。

## 查證要點
- FLAG:111、TCVARn 系、悪堕ち相關 CFLAG／TALENT 的意義照 `●開発者向け資料/●GVTフラグ一覧.txt` 與 `CSV定数定義/`。
- 引擎行為附 `reference/emuera-1824/...cs:行號`（已查證者引用既有註解即可）。

## 測試（table-driven，expected 由 ERB 推導）
- AKUOTI_EVENT 觸發條件與分岐；CORRUPT_CHANGE_LOOKS_MAIN／RECOVER_CORRUPTION 的狀態變化。
- 悪堕ちキャラ戰：遭遇 → 敵行動 → 性攻擊 → 勝利、以及 → 敗北 各一條整合路徑（FixedRng）。
- 說得する（COM47）的成功／失敗。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因、AKUOTI_EVENT 與悪堕ちキャラ戰的實際次數，與 S18 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS（≤150 行，必要時壓縮舊階段敘述）、deviations、unresolved 更新；必要時 `docs/wiki/era/akuoti.md`（< 300 行）。結束時務必送出三段報告。
