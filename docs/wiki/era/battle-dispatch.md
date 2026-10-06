# 戰鬥剩餘條件、回復與分派（S81）

本頁承接S80的[側事件](battle-side-events.md)。Python路徑相對`src/eragvt/`，ERB路徑相對`source/earGVP/`。只記已查證範圍，不把守衛存在當成整套功能缺失。

## 兩項漏翻修正

- `game/turnend.py@_ishole`接回既有`battle.core.is_hole`。`ERB/汎用関数/SEX_GENDER.ERB@ISHOLE:52–66`：明確ARG=0直接成立；其餘讀指定角色目前形態，女性或`男の娘 != 0`或男女平等ON成立。`@ISGIRLY:28–37`、`@ISFEMALE:121–129`。選項位元反向：`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F:43–47`。
- 真呼叫者是`ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB@AKUOTI_ATTACK:7–29`。先排除MASTER，再判CFLAG0=3、ISHOLE、機率；短路未過不抽RAND。沒有新增角色限制或改寫事件敘事。
- `game/battle/enemy.py@_enemy_action_once`行動4按`ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:574–617`補齊敵類比例及末王強化除數。原碼固定8%再除2，漏掉末王及雜魚比例。

| 敵類 | 先算／截斷 | 再除 | 最大HP10000、目前5000的結果 |
|---|---|---|---|
| 悪堕ち角色 | 最大HP×0.08 | 不除 | 5800 |
| 普通BOSS／市民 | 最大HP×0.08 | 2 | 5400 |
| 雜魚 | 最大HP×0.16 | 2 | 5800 |
| 末王、強化OFF | 最大HP×0.04 | 2 | 5200 |
| 末王、強化ON | 最大HP×0.04 | 10 | 5040 |

`ERB/ゲーム内_戦闘処理/LASTBOSS_POWERUP.ERB@LASTBOSS_REST:16–22`只在強化ON且末王回8，其他回0；強化HP在遭遇時已乘5，所以強化前態最大50000／目前25000回到25200。先截斷再除，最後以最大HP封頂。油斷回復保留原25%與TFLAG2規則。

引擎：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`的TIMES寫回Int64；`:2005–2023`的RETURN呼叫SetResultX；`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1732–1739`僅覆寫提供的RESULT格。本次呼叫LASTBOSS_REST同步RESULT0；其後原生PALAM結算仍可按原作覆寫，沒有聲稱整個回合保留所有RESULT。

## 行動4可達性

精確搜尋全ERB／ERH的`TENTACLE_COM`為0筆；舊規格所稱呼叫鏈實際為`SELECT_TENTACLE_ACTION`→`SOURCE_CHECK`→`ENEMY_ACTION`。

- `ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@SELECT_TENTACLE_ACTION:1019–1069`讀專用ATTACK_ROUTINE，0才抽通用1–4；FLAG902可將行動2轉4，敵HP≥75%又將4轉1。
- 末王1：`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_LASTBOSS_1_Ｋ触手.ERB@TENTACLE_LASTBOSS_1_ATTACK_ROUTINE:129–154`，例如RAND100=98回4。
- 末王2：`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_LASTBOSS_2_天使の樹.ERB@TENTACLE_LASTBOSS_2_ATTACK_ROUTINE:299–372`沒有直接回4，但第一形態角色體力0、RAND100=0回2，接FLAG902、RAND100=30即轉4。不能因專用routine無4就排除回復。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:710–830`先制／失衡會跳過本次敵行動；測試與人工前態明確清除先制，沒有修改正式排程。

## 原19處停止點的逐項結論

掃描原始函式標頭（完整比對，排除口上）：38個COM、7個BOSS、2個LASTBOSS、16個MOB、17個KARAMITUKU（16雜魚＋市民1150）。機器清單`tmp/s81/source-dispatch.json`含檔名、行號、原始symbol。
全ERB／ERH對`(?<![A-Za-z_])FLAG\s*:\s*10\s*=(?!=)`精確搜尋11筆，值只有0／1／2；不把TFLAG10或比較式`==`混入。MOB專用`_TENTACLE_SIZE`定義0筆。

| 守衛（處數） | 查證結論與合法路由 |
|---|---|
| `turnend._ishole`（1） | 真缺口已消除，見上方；剩18處守衛。 |
| `shop.shop_show_boss_info`（1） | 生存bit→末王號1／2；兩者已有顯示。`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_SURVIVE_CHECK:55–118`、`ERB/インターミッション画面/SHOP_SHOW_BOSS_INFO.ERB@SHOP_SHOW_BOSS_INFO:104–154`。超出已知末王資料仍停止。 |
| `battle.commands.run_com`（1） | 原38個COM全部已有分派，COM47也在RESTRAINT_COMS；註解所稱「只剩47」過時。代表入口為`ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF0.ERB@COM0:2`／`@COM201:118`與同目錄`COMF47.ERB@COM47:2`；非法指令不吞錯。 |
| `battle.core.boss_data`（3） | 7普通、2末王均有資料；MOB／CITIZEN由`tentacle_access`、`tentacle_palam_hosei`先分派。`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:198–309`。其他SAVESTR／不存在編號保留守衛；不再稱雜魚／市民系統未移植。 |
| `battle.enemy.msg_karamituku`（1） | 合法16雜魚皆有對應函式；代表`ERB/ゲーム内_戦闘処理/触手データ/雑魚敵/TENTACLE_MOB_1_無形（触手幼体の群れ）.ERB@MESSAGE_BATTLE_MOB_1_KARAMITUKU:529`，市民另走`ERB/ゲーム内_戦闘処理/触手データ/クズ市民/CITIZEN_1.ERB@MESSAGE_BATTLE_MOB_1150_KARAMITUKU:870`；catalog不可執行仍報錯，非新缺漏敵類。 |
| `battle.enemy._enemy_action_once`（1） | 非拘束行動1–6皆已實作；普通／末王／雜魚專用與共用選擇、悪堕ち選擇由`ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@SELECT_TENTACLE_ACTION:1019–1069`／`@SELECT_ENEMY_ACTION:1073–1134`分派。拘束指令另在本函式前段處理，不把其1000系列當非拘束缺口。 |
| `battle.gaping.boss_tentacle_size`（1） | 普通1–7已實作；各原資料函式存在，代表`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_BOSS_1_Ｃ触手.ERB@TENTACLE_BOSS_1_TENTACLE_SIZE:202–220`；分派見`ERB/ゲーム内_戦闘処理/GAPING.ERB@SET_TENTACLE_SIZE:1123–1128`。超出範圍守衛保留。 |
| `battle.gaping.set_tentacle_size`（2） | 末王1／2、敵類0／1／2皆已接；市民FLAG10=2。`ERB/ゲーム内_戦闘処理/GAPING.ERB@SET_TENTACLE_SIZE:1069–1170`，雜魚依原CATCH用固定倍率，未新增不存在的專用資料函式。 |
| `battle.sexcom._no_mob`（1） | 所有呼叫前已排除_mob，屬重複守衛。`_mob_or_msg`先走既有mob.message；其餘COM3／5／19都位於非_mob分支。原分派代表`ERB/ゲーム内_戦闘処理/戦闘コマンド(性攻撃)/SEX_COM3.ERB@SEX_COM3:75–98`；不改內容、不再列成雜魚顯示缺口。 |
| `battle.sexcom.boss_sex_routine／lastboss_sex_routine／lastboss_reaction_ref／boss_reaction_ref`（4） | 普通1–7／末王1–2均已有同名原資料函式與分派；非法編號保留守衛。`enemy_action_sex_routine`先分派悪堕ち／市民／雜魚，再到BOSS／LASTBOSS。代表`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_BOSS_1_Ｃ触手.ERB@TENTACLE_BOSS_1_SEX_ROUTINE:137`／`@TENTACLE_BOSS_1_REACTION_REF:166`；同目錄`TENTACLE_LASTBOSS_2_天使の樹.ERB@TENTACLE_LASTBOSS_2_SEX_ROUTINE:379`／`@TENTACLE_LASTBOSS_2_REACTION_REF:558–575`，分派見`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:248–250,302–304`。 |
| `prison.event._boss_prison_routine／tentacle_access_prison`（3） | 普通1–7／末王1–2皆有資料與routine；`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS_PRISON:314–343`，CFLAG20=2按原作不進兩分支。原作末王幽閉PALAM仍呼叫普通BOSS同號補正，沿既有測試保留。不存在編號不擅造資料。 |

這些結果是合法資料／既有路由核對，不是所有非法或原作錯誤前態均等價。悪堕ち戰FLAG11=0的原作GETNAME失敗字串已於S19處理；不存在數值函式的殘值／守衛相容性仍屬W08既有安全網範圍，沒有新增默認規則。

## 事件4與驗收範圍

`ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_救援共通.ERB@RAID_RESCUE:45–50`非除錯會RAND(2,6)，事件4可抽到；`:184–189`呼叫EXEC後依RETURN再遭遇。`ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/4 攫われた女性.ERB@EVENT_BATTLE_EXEC_4:27–45`已有流程，尾段設定上限40及`撤退不可,追撃戦,市民なし,レイプなし`；檔頭未實裝標籤不能豁免。

- `tests/test_battle_remaining.py`新增98案：8個ISHOLE、14個回復公式／上限／截斷、4個末王可達性、4個真候選caller短路、38個原指令分派、26個合法敵類資料路由、4個真run_train回復。
- 基礎案例在修正測試前態後先紅`18 failed, 8 passed`；產品修正後`26 passed`，追加後`98 passed in 0.25s`。
- 公式單測隔離PALAM結算；可達性另隔離attack_place_decision，只驗選擇與RNG。四個run_train案例未隔離產品結算，但使用Null敘事；瀏覽器fixture改用全catalog執行，只遮蔽輸出、不代按INPUT。
- 子代理定向：`python -m pytest -q tests/test_battle_remaining.py tests/test_turnend.py tests/test_akuoti.py tests/test_battle.py tests/test_battle_restraint.py tests/test_mob_battle.py tests/test_citizen_battle.py tests/test_lastboss.py tests/test_angel_tree.py tests/test_prison.py tests/test_raid.py --tb=short` → `774 passed in 9.31s`。
- `tmp/s81/browser_fixture.py`：末王四路按原7、條件四路按fixture0、事件4先fixture0再原201。全新25歲四欄、臨時存檔；gate以RAND70=69拒絕後續事件，只驗候選門檻及短路。主代理九路真瀏覽器通過，console錯誤0，末王HP與四gate候選77／RNG bounds符合，catalog失敗0；敘事遮蔽，不能說完整敘事可見。證據由主代理保存於`tmp/s81/`。
- 事件4按201後RESULT8=120是正常覆寫：人工敵為BOSS3，`ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_HOSEI_TENTACLE:564–568`→`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:251–253`→`ERB/ゲーム内_戦闘処理/触手データ/ボス触手/TENTACLE_BOSS_3_Ａ触手.ERB@TENTACLE_BOSS_3_PALAM_HOSEI:98–125`，`:117`令LOCAL8=120，`:125`RETURN十二格。Python的`core.tentacle_palam_hosei`同樣set_result_x；RESULTS8仍保留「尾格」。其他八路RESULT8保持765，不以通用保存器的舊假設判為產品bug；已保存本次結果，未重跑產品瀏覽器。
- 主代理全pytest：`5269 passed, 1 warning in 346.08s (0:05:46)`；局部條件與回復公式修正，未改共用RNG／排程／存讀檔，依分級驗證不跑500。
- 未完成W05整包：仍需自然遭遇抽樣、兩末王勝敗／撤退／時間切れ與救援事件完整連續鏈的瀏覽器彙整；本次人工下一行動／事件_exec邊界不冒充這些證據。下一成果仍留W05，不跳W06，也未觸發工作包完成的500局。
