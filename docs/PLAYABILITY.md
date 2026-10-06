# 完整遊玩現況盤點

停止點與搜尋統計基線：S55 `8a77ee8`；系統現況已更新至S70驗收（25歲人工基線，範圍見STATUS）。下一工作與順序只看[PLAN](PLAN.md)，本頁不另排優先序。
範圍是本機瀏覽器與原作已完成、可達功能；「已接通」表示有實作與測試，**不等於全瀏覽器驗收完成**。沒有完成比例。

## 系統現況與證據

Python路徑以下相對`src/eragvt/`；測試相對`tests/`。原作路徑相對`source/earGVP/`。

| 系統 | 已接通與現有證據 | 剩餘內容／驗收缺口 | 工作包 |
|---|---|---|---|
| 啟動／存讀 | `__main__.py`、`web/app.py`、`game/session.py:381–492`；`test_main.py`／`test_web.py`／`test_state_game.py` | 乾淨安裝、新程序讀回、損毀／版本限制、瀏覽器實測矩陣尚未完成 | W08、W09 |
| 開局／模式 | 共通角色製作、HEROINE_PRESET 0–3、關係、說明；`opening.py`／`creation_menu.py`；`test_creation_menu.py`／`test_tutorial.py` | 新局二擇捷徑固定NORMAL、完整模式與序章；`opening.py:83–98` | W04、W06 |
| 角色製作 | 主題命名、生成設定、姓名／變身命名、一人稱、武器、關係；各同名測試 | S60共用入口及12項子選單已接開局／招募／醫療／引繼；S61一般身體／外貌、S62性格／精神素質、S63種族／feat／變身能力／基礎點、S64共用CSV模板、S65性別、S66初始狀態／人數及GLOBAL權限、S67身體其餘操作已接通。經歷仍缺；S68子供獨立一人稱、S69實際身體收尾入口均已接真實輸入；S69僅25歲人工尾段函式邊界驗收，不代表完整出生／加入，見[角色編輯](wiki/era/character-editor.md) | W02 |
| 套組 | 0_特捜戦隊；`opening.py:334`、`test_opening.py` | 其餘1–11與14（12套）、6／7／8動態說明；不能由缺號推測待實作12／13 | W04 |
| SHOP／日常 | 8類行動、編成／排程、衣裝購買／穿戴、強化／醫療／設施／招募引退；`session.py:214–302`、各模組／測試 | 決策資訊、各子選單預設代按與特殊條件（SHOP[800]已於S57接通） | W01–W03、W07 |
| 成就／紀錄 | S57共用取得／保存、GET_STATE判定、catalog／原生呼叫者、SHOP[800]六頁；S58的20欄紀錄、模式通關數、ENDLESS紀錄與六觸發；[證據](wiki/era/achievements.md) | S59已按裁決修正新全域版本／最高總評113；未移植解鎖互動端屬W02 | W01 |
| 戰鬥／事件 | 普通戰、雜魚／市民／悪堕ち、襲擊／救援；`test_battle.py`／`test_mob_battle.py`／`test_citizen_battle.py`／`test_raid.py` | 觀眾妨礙、返り血、裝備零件／觸手服、部分救出、ISGIRLY、動態敵方安全網與模式分支 | W03、W05、W06 |
| 末王／終局 | Ｋ触手、天使の樹、SCORE、結局1–6函式及引繼；`test_lastboss.py`／`test_angel_tree.py`／`test_succession.py` | 不等於六結局全能自然到達；原作ENDING_6前置停用。末王強化已有HP／回合回復，敵行動回復待核對；全模式終局待驗 | W05、W06、W08 |
| 身體／生命週期 | 身體／裏プロフィール、妊娠出産／子供、幽閉／救出、寄生／悪堕ち、夜間與強制事件；對應測試 | S70三種TS原生轉換與幽閉首次事件／catalog等待已接通（68案）；妊娠TS呼叫者、女體受容、特殊裝備後續仍缺，不宣稱全TS生命週期或B05完成 | W02、W03、W05 |
| 設定 | config 1–3、各開關／篩選、GLOBAL；`test_config.py` | 分類指令、返り血、男女平等OFF、能力降低等開啟後的分支，逐項ON/OFF與相依組合驗收 | W03、W05–W08 |
| 口上／顯示 | catalog 13,384函式可執行，另有雜魚194／市民10；INPUT／INPUTS已有；`test_kojo_input.py`／`test_narration*.py` | 開局MESSAGE_FIRST、COUNT、同步失敗回復、字型／HTML／圖樣、WAIT、SHOP／戰鬥資訊簡化；可執行率不保證呼叫成功 | W04、W07 |
| 非NORMAL與除錯 | 引繼`succession.py:463–495`已可選SOLO／HARDCORE／SURVIVAL／FREEPLAY／INSTANT；GameMode／GameOption已有 | ENDLESS／能力降低等仍停止；除錯輸入／顯示未完成；不能說目前不可到達而排除 | W06、W08 |

## 原作未完成與原作錯誤：只保留有證據的範圍

| 範圍 | 原文證據 | 處置 |
|---|---|---|
| AMPUTEE替代處置 | `ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:245–266`明示翻譯／移植未完、`1==0`停用、CALL註解 | 依既有使用者裁決維持提示並截斷，不續寫；不連帶停用已完成醫療功能 |
| 角色製作隨機幅度入口 | `ERB/SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG:96`選項4000註解且標未完成 | 保持該入口未開放；不豁免已完成的其他角色設定 |
| 處刑接續／ENDING_6前置 | `ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_クズ市民の脅迫.ERB@KIDNAPPING:587–588`呼叫註解；`ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_6:657–661`前置註明尚未移植 | 不新增原作未接通的處刑流程；既有結局函式保留，不要求自然觸發原作死路 |
| 特殊戰鬥構想 | `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/特殊シチュエーション.ERB`檔頭`:6–40`以★標未實作、＠標已有但無使用例 | ★只屬原作構想；＠不能當未實作。W05接可達既有流程，不補作者構想 |
| 洞窟另一敵類分支 | `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/5 触手洞窟.ERB@EVENT_BATTLE_EXEC_5:125–132`註明另一分支未移植且ELSE註解 | 只保留該分支未完成，既有洞窟事件已在`raid.py`，不得整項排除 |
| 精神崩壞說明 | `ERB/ヒロイン関連/TALENT_INFO.ERB@TALENT_INFO:164–166`回傳原作未實作字串 | 保留說明，不自行設計新能力；對其他已使用此素質的程式仍照原文 |
| TS_NORMAL錯誤返回 | `ERB/ヒロイン関連/TRANS_SEX.ERB@TS_NORMAL:357–362`先令TARGET=ARG，普通形態為女性即RETURN0，早於末尾恢復 | 保留原TARGET殘值；不擅自修正或稱原作未完成。三轉換細節見[幽閉](wiki/era/prison.md) |
| 事件4檔頭「未實裝」 | `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/4 攫われた女性.ERB:2`，但同檔`@EVENT_BATTLE_EXEC_4:27–45`已有流程；`raid.py:874–955`亦有實作 | **不列整項豁免**；標籤可能過時，W05核對具體分支與可達性 |

其他「未完成」字樣（FLASHNEWS對應事件、引退表註解、共用函式）是線索，不自動豁免；W05／W08按呼叫與具體分支驗證。原作bug（越界、無限迴圈、終端錯誤、拼字）不能算未完成：既有裁決維持，新增差異需查證／使用者裁決。

## 搜尋統計與範圍

全域搜尋先計數，再逐組讀上下文；本次為S55快照，後續行號會移動，以函式名與提交重找。

- `src/**/*.py`：`raise NotImplementedError` **118行**；`DEVIATION:|UNVERIFIED:` **47行**，擴大為`DEVIATION|UNVERIFIED` **65行**（另18行含全形冒號、無冒號或舊說明，均已核對歸屬）；初步（忽略大小寫）`\bpass\b|TODO|未實作|未移植|略過|暫不|stub|no.op` **160行**。
- 擴充搜尋（忽略大小寫）`noop|no.op|何もしない|無操作|not implemented|未対応|未移植|略過|省略` **195行**（與前述大量重疊，不相加）。
- `deviations.md`實際未勾選26項、既有`unresolved.md`11項（不含格式範例）；本次新增末王回復查證1項，未決合計12項。
- 非口上／地の文ERB內`未完成|未実装|未移植|作成中|実装予定`13行；只用來定位原文，不作完整功能清單。
- 固定套組定義`^@SHOKISET_SELECT_\d+`13個：0–11、14。全ERB／ERH `\bNEXTCOM\b` 0筆；引擎介面安全網不代表遊戲缺一個自動戰鬥功能。
- 可重現（PowerShell）：`rg -n -g '*.py' 'raise NotImplementedError' src | Measure-Object`，確認總數後再讀完整結果；其他pattern同法。套組查`source/earGVP/ERB/SYSTEM/キャラメイキング関連/初期セット`；原作未完成搜尋排除口上／地の文。

這是入口、現有占位與偏離的盤點，不冒充逐行等價性證明。後續每包還要對原作可達分支與現有測試建立對照；查證未結者有歸屬，不能因沒有raise就聲稱完成。

## 無操作與略過：不能被停止點統計遮住

- 真缺口：新UI解鎖消費端→W02（W01成就／紀錄與S59兩項已裁決修正已接通）；S60已消除共用編輯入口／引繼代按；S68／S69子供一人稱及身體代按已消除；[8]經歷具體範圍阻塞→W02；模式／序章／MESSAGE_FIRST→W04、W06；資訊與WAIT／圖樣→W07。
- AST找到的`pass`多為原作空分支、條件不改值、例外捕捉與標記類別。例如`body.py:94,108`保持成長值，`input_request.py:7`請求標記，`narration/nodes.py:241,246`節點類別，`battle/train.py:1007`捕捉流程轉移；不計作待翻功能。
- `battle/restraint.py@_need_boss:79`是雜魚／市民接通後的空守衛；不能據此重做整套戰鬥。`battle/sexmsg.py`多處空分支只保留狀態fallback，原文顯示已有catalog；W07檢查fallback與缺資料行為。
- `narration/runtime.py:203`對CALL方法型別的空分支與註解不一致→W08核對合法呼叫與引擎規則，不在本次擅自定義修正。
- `battle/enemy.py:660–661`末王回復固定除2，原文`ERB/ゲーム内_戦闘処理/LASTBOSS_POWERUP.ERB@LASTBOSS_REST:16–22`強化時回8；W05／W08核對呼叫可達性與測試，詳見unresolved新增項。這是無raise的待查證差異。
- 過時說明例：`commands.py:1458`仍提COM47，但`restraint.py`已有COM47分派；`core.py:566`仍稱雜魚未移植。W05只核對遺留guard可達性；已完成系統不能由舊註解重新算成缺口。

## 停止語句的完整歸屬（S55基線118，S70現為113）

M＝已知移植／互動缺口；O＝已證實原作未完成且已有處置；G＝通用抽象介面；U＝可達性、原作錯誤或資料／catalog失敗尚需逐項核對。U不是豁免。
一行主歸屬一包；共享依賴看PLAN。S60移除兩處個別入口停止、新增一處細分子選單分派與兩處姓名原作錯誤安全網；S61新增一般身體頁剩餘分支一處停止；S66移除初始狀態與人數兩處停止；S67移除SIZE_SETTING選項停止；S68移除已無呼叫者的selfcall_default及兩個停止。S70移除幽閉首次事件／TS hook兩處停止。合計W02=1、W03=9、W04=3、W05=22、W06=6、W07=20、W08=52，總數113；W01原先沒有raise的成就／紀錄缺口已接通，最終驗收見STATUS。

| Python檔案@函式 | 行號 | 工作包／分類 | 內容 |
|---|---|---|---|
| `game/action.py@action_main` | 304 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/action.py@rest` | 420 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/akuoti.py@self_call` | 75 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/chara_make.py@initialize_personality` | 86,94,114 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/config.py@update` | 189 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/creation_menu.py@preset_menu` | 221,232 | W04／M | 動態說明／其他套組 |
| `game/character_editor.py@character_editor` | 經歷停止 | W02／M | [8]經歷維持未移植；S65已接[0]性別，具體範圍阻塞一次記於[角色編輯](wiki/era/character-editor.md)；非原作未完成 |
| `game/character_name.py@character_name、random_character_name` | CHARANUM／空姓守衛 | W08／U | 姓名原作越界及無窮重抽；[具體依據](wiki/era/character-editor.md) |
| `game/drug_preparation.py@drug_preparation_gen` | 320 | W08／O | AMPUTEE已裁決保留截斷 |
| `game/export_csv.py@csvbase` | 41 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/flashnews.py@_chara` | 58 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/flashnews.py@flashnews` | 83 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/flashnews.py@flash_viralmedia` | 321 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/flashnews.py@flashnews_chooseidol` | 376,402 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/gather.py@_citizen_encount_text` | 377 | W08／M | 除錯輸入／顯示 |
| `game/opening.py@chara_make_main_preset` | 334 | W04／M | 其他套組載入 |
| `game/opening.py@decode_weapon_data` | 411 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/opening.py@chara_make_finalize` | 480 | W03／M | 無內衣路徑 |
| `game/pastime.py@_fb_pool` | 184 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/pastime.py@fb` | 196 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/pastime_nanpa.py@_run` | 34 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/self_call_setting.py@selfcall_gen` | 251 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/shop.py@shop_show_boss_info` | 438 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/shop.py@shop_show_situation_list` | 1010 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/status_screen.py@_check_chara` | 80 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/status_screen.py@_father_name` | 844 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/succession.py@succession_gen` | 381 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/tentacle.py@tentacle_bitvalue` | 81 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/turnend.py@run_turn` | 75 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/turnend.py@event_turnend` | 122,180 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/turnend.py@raid_hantei` | 487 | W08／M | 除錯輸入／顯示 |
| `game/turnend.py@_ishole` | 502 | W05／M | ISGIRLY條件 |
| `game/yobai.py@_callname_at` | 142 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/yobai.py@yobai` | 204 | W03／M | 女體受容取得 |
| `game/battle/ablup.py@_talents` | 423 | W03／M | 女體受容取得 |
| `game/battle/after.py@event_end` | 406 | W06／M | ENDLESS期限 |
| `game/battle/angel_tree.py@show` | 185 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/battle/cheers.py@perform_cheers_first_hantei` | 52 | W08／M | 除錯輸入／顯示 |
| `game/battle/commands.py@_msg_nanori_byousha` | 287 | W03／M | 變身衣裝零件 |
| `game/battle/commands.py@run_com` | 1460 | W05／U | 未分派指令安全網；舊註解不能代表COM47仍缺 |
| `game/battle/core.py@boss_data` | 563,566,568 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/core.py@add_randchoose` | 1010 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/battle/encount.py@encount_enemy` | 164 | W08／M | 除錯輸入／顯示 |
| `game/battle/encount.py@encount_boss` | 254,312 | W08／M | 除錯輸入／顯示 |
| `game/battle/encount.py@encount_boss` | 310 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/battle/enemy.py@msg_karamituku` | 206 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/enemy.py@_enemy_action_once` | 641 | W06／M | 能力降低選項 |
| `game/battle/enemy.py@_enemy_action_once` | 826 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/enemy.py@attack_place_decision` | 1014 | W08／M | 除錯輸入／顯示 |
| `game/battle/func.py@act_limit` | 214 | W05／M | 市民觀眾妨礙 |
| `game/battle/func.py@act_limit` | 220 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/battle/gaping.py@print_tentacle_size` | 409 | W08／M | 除錯輸入／顯示 |
| `game/battle/gaping.py@printform_gaping_now` | 462 | W08／M | 除錯輸入／顯示 |
| `game/battle/gaping.py@boss_tentacle_size` | 520 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/gaping.py@set_tentacle_size` | 583,592 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/hantei.py@_hurihodoku` | 269 | W08／M | 除錯輸入／顯示 |
| `game/battle/hantei.py@act_hantei_tettai_tentacle` | 548 | W08／M | 除錯輸入／顯示 |
| `game/battle/hantei.py@damage` | 676,691 | W08／U | 非法值／原作錯誤或版本限制；逐項核對 |
| `game/battle/mob.py@message` | 93,97 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/battle/mob.py@message_gen` | 105,109 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/battle/mob.py@mob_tentacle_battle` | 127 | W08／M | 除錯輸入／顯示 |
| `game/battle/ninsin.py@ninsin_hantei` | 175 | W08／M | 除錯輸入／顯示 |
| `game/battle/ninsin.py@ninsin_flag` | 279 | W03／M | TS轉換 |
| `game/battle/ninsin.py@ninsin_ts_fix` | 296 | W03／M | TS轉換 |
| `game/battle/ninsin.py@after_pill` | 452 | W08／M | 除錯輸入／顯示 |
| `game/battle/palam.py@palam_up_enemy_reaction` | 544 | W08／M | 除錯輸入／顯示 |
| `game/battle/palam.py@endure_ecstasy` | 608 | W08／M | 除錯輸入／顯示 |
| `game/battle/palam.py@palam_kiryokudown` | 984 | W06／M | 能力降低選項 |
| `game/battle/palam.py@palam_seitaiseidown` | 1043 | W06／M | 能力降低選項 |
| `game/battle/palam.py@palam_up` | 1088 | W08／M | 除錯輸入／顯示 |
| `game/battle/restraint.py@com103` | 1303 | W08／M | 除錯輸入／顯示 |
| `game/battle/sexcom.py@_no_mob` | 106 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/sexcom.py@boss_sex_routine` | 2479 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/sexcom.py@lastboss_sex_routine` | 2488 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/sexcom.py@lastboss_reaction_ref` | 2500 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/sexcom.py@boss_reaction_ref` | 2514 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/battle/source_check.py@source_check` | 81,112 | W03／M | 特殊裝備／觸手服／運動快感 |
| `game/battle/source_check.py@_victory` | 262 | W06／M | ENDLESS擊破 |
| `game/battle/source_check.py@_rescue_deadnum` | 490 | W05／M | 失去角色發現／返り血 |
| `game/battle/source_check.py@_supart_blood` | 496 | W05／M | 失去角色發現／返り血 |
| `game/battle/source_check.py@_motion_palam` | 515 | W03／M | 特殊裝備／觸手服／運動快感 |
| `game/battle/source_check.py@_timeup` | 857 | W08／U | 救出時間切れ；既有查證TFLAG:9無寫入 |
| `game/battle/source_check.py@_hatujou_to_hairan` | 1035 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `game/battle/train.py@show_usercom` | 474 | W07／M | 分類指令顯示 |
| `game/battle/train.py@event_comend` | 978 | W06／M | INSTANT能力降低 |
| `game/battle/train.py@run_train` | 999 | W08／U | NEXTCOM；原作全ERB/ERH搜尋0筆 |
| `game/prison/event.py@_boss_prison_routine` | 87 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `game/prison/event.py@tentacle_access_prison` | 122,141 | W05／U | 動態敵方／資料分派安全網；先核對合法可達性 |
| `narration/expr.py@is_variable` | 98 | W08／G | 抽象介面；不等於三個遊戲缺口 |
| `narration/expr.py@is_function` | 101 | W08／G | 抽象介面；不等於三個遊戲缺口 |
| `narration/expr.py@is_csv_name` | 104 | W08／G | 抽象介面；不等於三個遊戲缺口 |
| `narration/service.py@_run` | 141,144 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `narration/service.py@_run_waiting` | 269 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `narration/service.py@run_function_gen` | 293,299 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `text/output.py@rep` | 260 | W07／U | catalog／文字支援或缺資料的失敗路徑 |
| `text/output.py@_parse_html` | 299 | W07／U | catalog／文字支援或缺資料的失敗路徑 |

## 偏離與未決的收口方式

26項既有未勾選偏離已在原項目前標工作包；不勾選、不默認批准。包括亂數、JSON／Web專用行為、COUNT與顯示、缺catalog與回復、預設代按、錯誤恢復等。已裁決項不重開；原始證據仍保留於bridge文件。
11項既有未決分配W05–W08，本次新增末王回復查證列W05／W08。舊SHOP169／170／180描述與目前已接通實作不同，改為核對CASE語意與既有裁決，不再聲稱只印未實作。
真瀏覽器完整驗收仍待[PLAN的B01–B09](PLAN.md#瀏覽器驗收矩陣)。既有Web測試主要是FastAPI TestClient與generator；沒有實際瀏覽器紀錄時只能稱API驗證。
S55標準500局固定選預設／特装戦隊、直接確認角色製作與固定行動策略；246／4、250／0及catalog零失敗僅證明此抽樣，未覆蓋所有模式、選項、編輯、解鎖、末王與終局。
