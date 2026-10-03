# 市民戰（S36）

原作路徑以下相對 `source/earGVP/`。Python 入口為 `game.battle.citizen.encount_citizen`。
只轉換既有規則；文字由 catalog 抽取，無新增情節。

## 遭遇及入口

- `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_クズ市民共通.ERB@ENCOUNT_CITIZEN:4–58`：
  SAVESTR:13=CITIZEN、FLAG:11=1150；事件編號大於0時清 TARGET 的 TCVARn 與 TFLAG、設 TFLAG:0=-1、更新衣裝並執行事件。
  FLAG:73 加入70與71，再清70～72；人數小於3則加5，人數同時作敵HP；射精上限500、油斷100+等級×10。
- `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/6001 クズ市民の泥酔レイプ.ERB@EVENT_BATTLE_EXEC_6001:4–23`：
  呼叫 STATE_CHANGE_HATUJOU(100)，設15回合、先制無し／支援無効／レイプなし。
- 同目錄 `6002 クズ市民の媚薬レイプ.ERB@EVENT_BATTLE_EXEC_6002:4–21`：沒有前項狀態呼叫；15回合及相同限制，加上呼叫端補充字串。
- `ERB/ゲーム内_行動実行処理/ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:350–416,1016–1046`：
  調查入口檢查config 802 bit5；找到監禁地點的救援入口不檢查此設定。兩者遭遇後仍抽 RAND:100 決定 CFLAG:825，然後 RETURN。
  調查CASE1只顯示傷害、不扣體力；CASE2扣體力；LOCALS先清空，CASE0／1才設定補充狀態。
- `ERB/ゲーム内_イベント発生/自由行動中イベント/PASTIME_ナンパ.ERB@PASTIME_NANPA_RAPE:3086`、
  `ERB/ゲーム内_イベント発生/自由行動中イベント/PASTIME_酒ナンパ.ERB@PASTIME_SAKE_NANPA_RAPE:1696`：catalog hook 接到6001。
  `ERB/ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN:145–163` 依 FLAG:73 返回TRAIN，沿用既有控制流程。

## 敵方及戰鬥

- `ERB/ゲーム内_戦闘処理/触手データ/クズ市民/CITIZEN_1.ERB@TENTACLE_CITIZEN_1150_HP:25` 至 `@TENTACLE_CITIZEN_1150_HOLD:93`：
  數值直接回傳，不套雜魚的等級乘數。攻250、防500、敏150、知10，近／中／遠120、拘束180。
- 同檔 `@TENTACLE_CITIZEN_1150_ATTACK_ROUTINE:130–138`、`@TENTACLE_CITIZEN_1150_SEX_ROUTINE:144–200`：原生Python閾值分支，保持亂數次序。
  MESSAGE_* 顯示與其既有狀態呼叫沿用 catalog／Python hooks。
- `ERB/ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB@ACT_HANTEI_CHARA_TO_TENTACLE:80–88,236–300`：
  振り解き市民分支降低知性影響、變身時以 LOCAL:0/2（上限50）覆蓋防禦值；敵油斷只加10。原有 LOCAL:O 裁決維持。
- `ERB/ゲーム内_戦闘処理/COMMON_BATTLE_FUNC.ERB@CHECK_CAN_RETREAT_F:396–417`：
  保留拘束、回合／體力、觀眾及撤退不可判斷。
- `ERB/ゲーム内_戦闘処理/FORECAST.ERB@INT_EVAL:409–426`：市民沒有對LOCAL賦值的分支，保留前次敵方補正，再套難度倍率。

## 戰後及原作的特殊行為

- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:117–133,850–950,1113–1130`：
  解除拘束即走時間切れ；敵HP正常不會歸零進勝利。三項資源皆0且仍拘束時設敗北，依config 804 bit10分捕獲或釋放。
  捕獲設 CFLAG:0=4、CFLAG:71=30並依條件減FLAG:799；等待輸入由既有CALC_GANGBANG續行。
- `ERB/ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_RAPED_CITIZEN:55–65`：經驗加1、清NOWEX、PALAM_CAL使用此函式LOCAL（原文未寫入，初始0）。
- `ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:179–198,355–390`：時間切れ及敗北整理救援標記；6001／6002只有TFLAG:98=2判任務失敗，SUCCESS／FAILURE不寫新聞。
- `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/特殊シチュエーション.ERB@ADDBATTLESITUATION:43–44`：
  **覆寫**而非附加。因此救援先設的強制狀態會被6002的無補充呼叫覆蓋，照原作保留。
- `ERB/ゲーム内_戦闘処理/触手データ/クズ市民/CITIZEN_1.ERB@SEX_TYPE_MOB_901_COM2:405` 及 `@MESSAGE_MOB_901_COM2:408`：
  編號是901，並不存在1150的COM2型別與文字；TRYCALLFORM缺函式不發，不能自行改名。
- `ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMABLE.ERB@COM_ABLE103:991–996`、`COMF100.ERB@COM100:53–60`、
  `COMF103.ERB@COM103:192–201` 及 `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:1152–1159`：
  拼的是 TENTACLE_MOB_1150_REACTION_REF，原作只有 CITIZEN_1150。TRYCCALLFORM走CATCH禁用103；TRYCALLFORM保持RESULT殘值。

## 引擎依據與驗證

- `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2316–2322`：缺動態函式的CALL報錯、TRYCALL不發、TRYCCALL跳CATCH。
- `reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:24–29,70–71`：依函式保存LOCAL；市民INT_EVAL無賦值分支仍讀舊值。
- `reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1422–1460`：BEGIN TRAIN清TFLAG及TCVAR，TCVARn是另一變數。
  原作沒有TCVAR寫入（既有test_tcvar_never_written）；市民專用例程的TCVAR:12條件保持0，不能擅改TCVARn。
- `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`：函式終端只清RESULT:0；多值殘值不清。
- 測試：`tests/test_citizen_battle.py`；既有情報停止案例在 `tests/test_actions_s28a.py` 改為實際遭遇驗證。
  包含數值／閾值／RNG尾值、缺函式、型別、catalog、輸入等待、時間切れ／敗北到TURNEND及撤退判定。

無新增UNVERIFIED／DEVIATION；既有框架的裁決維持。
