# S27：ラスボス＋結局（ENDING_2／3／6・SCORE）

自主推進（使用者指定 2026-10-02）第 6 階段。範圍較大：若單一 session 做不完，**照下列優先順序**做，未完成者保留停止並列出。路徑相對 `source/earGVP/ERB/`。

## 背景
ラスボス相關停止點 15 處（`grep -rn NotImplementedError src | grep 'ラスボス\|LASTBOSS'`）、結局相關 8 處（`ending.py`、`turnend.py`:102–181、`session.py`:388）。
全ボス撃破（FLAG:100 == 0）後的流程與日數超過的結局目前都會停止。

## 優先順序與範圍
1. **ラスボス出現與戰鬥**：全ボス撃破（`source_check.py`:264）→ ラスボス出現（SHOP 顯示 `shop.py`:412、狀況一覧 `SHOP_SHOW_SITUATION_LIST`:26–38）→
   遭遇（`ENCOUNT.ERB@ENCOUNT_BOSS`:365–421、襲来的 RAID_LOOP 選擇）→ 戰鬥：觸手資料 `触手データ/ボス触手/TENTACLE_LASTBOSS_1_Ｋ触手.ERB`、`TENTACLE_LASTBOSS_2_天使の樹.ERB`，
   以及 `core.py`／`commands.py`／`gaping.py`／`source_check.py`／`restraint.py`／`after.py`（蓄積ダメージ保持）中的 LASTBOSS 分岐；
   REACTION_REF、SET_TENTACLE_SIZE 的ラスボス分岐（雜魚敵分岐不在範圍，保留停止）；ラスボス幽閉（`prison/event.py`:123）。
   戰鬥中寫共用 RESULT／RESULTS 的位置照 `docs/wiki/python/result.md` 同步。
2. **結局**：`ゲーム内_イベント発生/エンディング/ENDING.ERB` 的 @ENDING 本體、ENDING_2（クリア）、ENDING_3（日數超過；S18 模擬曾停在此）、ENDING_6、
   ENDING_1 的エンドレス分岐（:266–），以及 `SCORE.ERB@SCORE`（FLAG:999 == -997 的スコア處理）；`session.py`:388 的 JUMP ENDING；結局後回標題。
   成就（GLOBAL）照既有 deviation 不寫。
3. **引き継ぎ（SUCCESSION.ERB，約 1640 行）**：本階段**不做**，保留停止（`turnend.py`:168），列入後續候選。

## 測試（table-driven，expected 由 ERB 推導）
全ボス撃破 → ラスボス出現的狀態；兩隻ラスボス的代表行動與傷害；勝利／敗北；各結局的觸發條件與狀態；SCORE 的計算。
整合：以人工 prestate（FLAG:100 = 0）走ラスボス戰到勝利 → ENDING_2 → SCORE → 回標題。

## 模擬
`tools/sim.py` 預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）＋一組人工選項（例：`--bosses-cleared`，開局即全ボス撃破，明示為人工狀態）：
停止原因、ラスボス戰次數、各結局次數，與 S26b 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved 更新；必要時 `docs/wiki/era/lastboss.md`（< 300 行）。結束時務必送出三段報告（含未完成清單）。
