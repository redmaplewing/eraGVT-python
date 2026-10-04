# 天使の樹（S38）

Python：`game.battle.angel_tree`；既有戰鬥、幽閉與 SHOP 入口均接通。
以下原作路徑相對 `source/earGVP/`；內容與數值只由原作轉換。

## 解鎖與形態

- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:176–180,270–272`：只有 `FLAG:854 > 0` 且 HARDCORE 擊破Ｋ触手，才增加末王數、期限並設 `FLAG:21=1`、`FLAG:101=2`。
- `ERB/ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT_BOSS:309–421`：沿用既有末王遭遇；不增加解鎖捷徑。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:40–112`：以下採實際判定，不能採末王資料檔頭的 75%／50% 註解。

| FLAG:21 | 名稱 | 下一形態條件 |
|---|---|---|
| 1 | 天使の樹 | HP 百分比 ≤75 → 2 |
| 2 | 楽園の花 | HP 百分比 ≤37 → 3 |
| 3 | 堕落の核 | HP 百分比 ≤10 → HP 回到最大值70%，形態4 |
| 4 | 堕落の核 | HP≤0 → 形態0，接一般末王擊破處理 |

每次 SOURCE_CHECK 最多切換一次（ELSEIF）。原作沒有中間形態最低HP保護，未擅自加入。
最終形態歸零後 `ENEMY_TYPE_CHECK_F("LASTBOSS")==1`，因此進入既有擊破、解救、完全殲滅、TURNEND及結局／繼承。
第三形態回復量保留在 `SOURCE_CHECK` 的 LOCAL:0；後續勝利迴圈（:121）或一般回合計算（:458–470）才覆寫。
敘述使用 `narration.catalog._TEXT_FRAGMENTS` 讀原文；Python 只做狀態判定與更新。
片段新增的函式終端會清 RESULT:0，呼叫端恢復原 inline PRINT 前的百分比，避免額外副作用。

## 資料、甲殼與亂數

資料檔：`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_LASTBOSS_2_天使の樹.ERB`。

- `@TENTACLE_LASTBOSS_2_GETNAME:8–15`、`@TENTACLE_LASTBOSS_2_DEFENITION:19–29`：按全域 FLAG:21 決定名稱與顯示，包含幽閉期間。
- `@TENTACLE_LASTBOSS_2_KOUGEKI:69–84`、`@TENTACLE_LASTBOSS_2_BOUGYO:88–133`：依玩家攻防動態計算；防禦的各次 TIMES 分別截斷。
- `@TENTACLE_LASTBOSS_2_SAKUSEI:47–53`：形態≥3回25，≥1回50；形態0不代入，保留該函式 LOCAL。
- `@TENTACLE_LASTBOSS_2_ATTACK_ROUTINE:299–372`：按HP／MP百分比、形態選擇既有指令，保留短路亂數呼叫順序。
- `@TENTACLE_LASTBOSS_2_SEX_ROUTINE:379–551`：使用既有共享 RANDCHOOSE 候選陣列；第一形態門檻100、其他形態門檻200，但兩者補足迴圈終點都是 `101-CHOICECOUNT_F()`。保留未使用的 RAND:100 消耗。
- `@TENTACLE_LASTBOSS_2_REACTION_REF:558–575`：沿用與Ｋ触手相同的反應；`@TENTACLE_LASTBOSS_2_TENTACLE_SIZE:618–631`：四個亂數按 C/V/A/B 原序。
- `ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COM_ATTACK_COMMON.ERB@COM_ATTACK_COMMON:60–64`：先做命中判定，再以 `TFLAG:13 & TCVARn:0` 強制命中結果0，接原本擦傷判定。遠距離值為3，**不同於**防禦公式的bit4；怪處照原作。
- `ERB/ゲーム内_戦闘処理/触手データ/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:329–342`：末王2幽閉指令使用末王2，但 PALAM 補正呼叫一般 `TENTACLE_BOSS_2`，照原作保留。
- `@TENTACLE_LASTBOSS_2_PRISON_ROUTINE:579–613`：各指令門檻5/10/15/20/28/36/44/52/60/68，68以上回0。

## 引擎查證

- 短路：`reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–553`。
- FOR 終點進入時求值一次：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1735–1743`。
- TIMES decimal乘算再轉整數：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`。
- LOCAL依函式保留：`reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:24–30,69–70`。
- 函式終端 RESULT:0=0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`；多值RETURN只覆寫指定格：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1740`。

## 驗證

`tests/test_angel_tree.py`：68個ERB推導案例。首輪22例為19紅／3綠，實作後通過。
定向案例明確使用人工前置狀態：四種解鎖門檻、遭遇、形態邊界、甲殼、候選與亂數、殘值、尺寸、幽閉、SHOP及實際GameSession擊破→結局→存檔→繼承→SHOP。
一般模擬不保證自然抵達周回末王；不可把定向測試宣稱為自然通關。完整回歸與標準500局摘要見STATUS，產物在gitignored `tmp/s38/`。
無新增UNVERIFIED／DEVIATION。
