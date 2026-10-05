# 追加招募（S43）

入口為SHOP [180]，不是引退選單。`eragvt.game.recruitment.recruitment_gen`由GameSession呼叫。
以下省略檔名的引用均指`ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB@TSUIKAYOUSEI_NORMAL`。
字串由`tools/extract_recruitment_text.py`抽取至`recruitment_text.py`；遊戲規則手翻為原生Python。

## 入口與範圍

- `ERB/インターミッション画面/SHOP.ERB@SHOW_SHOP:174–179`：加入引退選項開啟就顯示[169]/[170]/[180]，不因滿員隱藏。
- `ERB/インターミッション画面/SHOP.ERB@USERSHOP:288–295`：[180]要求CHARANUM≤登錄上限−1，且加入引退選項開啟。
  `ERB/DIM.ERH:25`登錄上限為30（含MASTER）；`ERB/ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB@GAME_OPTION_CHECK_F:89–91`讀FLAG:0對應bit。
  `ERB/DIM.ERH:69`為9；Python沿用GameOption.JOIN_RETIRE=9。資金、遊戲結束旗標不影響這個入口。
- 同一段的[169]是CHAR_INTAI_LIST、[170]是CHARA_INTAI，都是獨立入口；S44已接通，見`retirement.md`，不從名稱推定[180]含引退。
- 完整163行沒有扣款或費用判斷；招募免費。

## 選擇與狀態順序

1. `:9–19`顯示FLAG:250累計次數，以及0女性、1男性、2隨機、99取消。雖然文案說無法取消，99確實返回。
2. `:20–35`只接受0/1/2進行加入：FLAG:250加一，LB與DOT_AFTER保留RESULT；保存TARGET，ADDCHARA0，TARGET設新角色索引。
   1先設男性素質與NAME，0/1呼叫個別編輯；2跳過該呼叫。錯值在`:155–157`重讀，不新增角色。
3. `:39–50`讀種族並顯示特徵選單。0/1已走初始化，2仍是CSV未初始化狀態，因此種族值可以為0；不能為了顯示特徵先初始化。
4. `:51–126`手選特徵，最多3項，100–299可取得項目反覆切換，確認後重寫1100–1299素質並SET_PROFILE。
   `:127–136`的1不設定，2呼叫SET_FEAT_DEFAULT再SET_PROFILE；其他輸入只回`:50`，不重複加入。
5. `:141–154`顯示加入訊息，若安全編成人數至少6則留在候補，否則CFLAG:999設1；最後CHARA_MAKE_FINALIZE，再恢復原TARGET。
   `ERB/汎用関数/CHARANUM.ERB@CHARANUM_SAFE_PARTYCHECK:114–121`排除狀態1/2/3/4/9或未編成者，但不排除10/11。
   新角色此時尚未編成，計數不會把它算入；判斷在FINALIZE之前。

## 共用流程與原作細節

- S60已將[0]/[1]接到`character_editor.character_editor`，等待玩家操作共用個別編輯器；不再自動代按[99]。[2]仍依原作略過個別編輯。
  依據`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–34、112–122、318–353`：
  保存命名衣裝的ITEM100–699、暫設1、初始化、解碼武器、清壓縮字串、保留身體顯示計算殘值、更新結界、清SAVESTR0–3並恢復ITEM。
  姓名／呼稱／一人稱／口上設定／變身文字／衣裝／武器共12項子選單已接通；身體等其餘子選單仍未移植，詳見[角色編輯](character-editor.md)。
- `ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_CHECK:5–28`只回201–249中第一個存在種族，否則0。
  [2]路徑保留先選特徵再初始化的原作順序；未自行修正種族0時沒有可選特徵的怪處。
- 手選沿用`firstsetting.feat_select_ui`；逐段對照`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:549–627`與本函式`:51–126`。
  共用函式的race==9預選在本入口不成立（只有0或201–249），其餘選取、三項限制、文字、顏色、PRINTPLAIN及SET_PROFILE一致。
- `ERB/汎用関数/コモン関数.ERB@PRINT_CALLNAME:268–285`在CFLAG:6==3時回「あなた」；`:128`使用既有print_callname，不能直接當成CALLNAME。
- `ERB/汎用関数/PRINT_LINE.ERB@LB:12–18、@DOT_AFTER:34–55`明確RETURN RESULT，保留最初輸入，故男性／隨機分支仍可判斷。
- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_FINALIZE:221–487`沿用既有實作及注入RNG。

## 引擎依據

- `reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`：INPUT只寫RESULT:0，不清其他格。
- `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`：一般函式末端將RESULT:0設0；99取消與成功加入均以0返回。
- 命名ITEM、SAVESTR與身體計算的共用路徑沿用S42查證，未改原作或引擎目錄。

## 驗證

- 測試先紅：缺少recruitment模組；實作後新測試全綠。稱呼補測先1失敗／1通過，改用既有helper後全綠。
- 定向39項：0/1/2×特徵0/1/2、取消／錯值、入口旗標與29/30人邊界、免費與負資金、TARGET／RESULT、
  5/6名編成與特殊狀態、初始化先後、ITEM／SAVESTR復原、四項不可確認與反選、實際GameSession接通。
- S43加醫療室回歸：`151 passed in 6.84s`。主代理獨立完整pytest：`2773 passed, 1 warning in 372.09s (0:06:12)`；既有Starlette/httpx警告。
- 標準500局：default246上限／4回標題、tokusou250上限，catalog失敗0；逐seed全欄位與S42截斷版一致。
  default／tokusou各seed0–249、max-shop200、actions101–108；10個50局獨立前景批次exit=0，seed全集與log／JSONL一致。
  產物及核對程式留在`tmp/s43/`；標準模擬不操作[180]，選單互動另由定向測試驗證。
