# 共用角色CSV模板載入（S64／W02）

## 入口與資料來源

- Python：`game/character_csv.py@load_character_csv`，由共用`character_editor`的[999]呼叫；不是檔案上傳或OS檔案選擇器。
- 原作：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_LOADCSV:1496–1620`；以下短稱LOADCSV。同檔`@FIRSTSETTING_CHARA_MAIN:321–333`短稱MAIN。
- 從遊戲啟動已讀入的角色定義按「番号」排序，0到9998，排除999。不是CSV檔名的數字，兩者可不同。
- 引擎`EXISTCSV`／`CSVNAME`查模板番号及一般角色：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1326–1353`；`ADDCHARA`同樣查模板番号，追加全新角色：同檔`:1026–1033`。
- 固有角色仍能使用[999]。醫療入口`ARG:2=1`隱藏且拒絕[999]，也拒絕手輸；不能以固有標記或NO非零自行鎖CSV。

## 操作與原作邊界

- LOADCSV:1508–1547：每頁30筆，頁碼從0開始；最大頁為`筆數//30`。恰30、60筆時保留可達的空白末頁，不自行減一。無候選仍有Page(0/0)與返回。
- [-1]／[-2]翻頁且夾在合法範圍；無效編號重畫同頁，不抽RNG、不改角色。手輸可選別頁存在的模板。
- [99]直接取消，重入從第0頁開始。若定義番号99，清單仍顯示，但輸入99優先命中取消，無法選入；排除條件原本只有999，不增補例外。
- [1]要求模板1存在，但實際`ADDCHARA 0`，再設男素質及NAME=`汎用キャラ(♂)`；其他號碼直接加入指定定義。
- 原作不做替換前確認／預覽／回滾：先替換、清SAVESTR0–3、顯示已替換訊息並PRINTFORMW等待，確認後才CSVFIX。Web使用真正WaitInputRequest，Enter與確認按鈕續行，WAIT不寫RESULT(S)。

## 替換與數值次序

1. LOADCSV:1551–1564依ADDCHARA→SWAPCHARA→DELCHARA。整筆新Character取代who；其他角色、角色數、MASTER／TARGET／ASSI保持原索引，不保留舊角色欄位。引擎依據：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1061–1067、1165–1174`。
2. 清SAVESTR0–3，保留其他格；等待後沿既有`firstsetting_chara_csvfix`：等級最少1、缺省BASE、舊色碼遷移、解碼CSTR15–17並清空。同檔`@FIRSTSETTING_CHARA_CSVFIX:1624–1670`；武器`ERB/武器と衣装/武器カスタマイズ関連/WEAPON_ARCHIVE.ERB@DECODE_WEAPON_DATA:7–50`。
3. 無固有素質即NO=0。接著七項BASE/MAXBASE重新取此NO的CSVBASE，故非固有模板用0的基礎；CSVFIX剛補的1000/100也會被CSV零值覆寫。`CSVBASE`模板Maxbase依據：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1383–1396`。
4. NO=0才套性格補正，BASE與MAXBASE同值。性格公式沿`ERB/ヒロイン関連/CHARA_SEIKAKU.ERB@SEIKAKU_HOSEI_F:63–470`。其後CFLAG60–66遺傳值只加BASE，MAXBASE不加。
5. MAIN每次CSV子函式返回都加`bonus*10`，**包括取消**；同一次返回只加一次。進入主編輯、[99]完成及未再開CSV的重入不加。這是MAIN:323的明文次序，未修成只成功載入才加。
6. CALLNAME仍為`汎用キャラ`時回MASTER_LOOP：CFLAG240=0才INITIALIZE，之後解碼／清CSTR15–17。非汎用呼稱只在CFLAG34=0時依序AGE_SETTING→SIZE_DEFAULT。後者不生成新成長曲線，0仍可為0，依`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:53`與`CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT:2156–2158`。
7. LOADCSV本身不抽RNG；上層必要初始化仍使用注入RNG。INPUT只寫RESULT0；自然終端只寫RESULT0=0，其他RESULT／RESULTS保留：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`、`Process.ScriptProc.cs:61–67`。主畫面既有顯示會再留下尺寸等RESULT值，不與子函式終點混淆。

## 四個呼叫者

- 開局`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:142–145、202–204`：`creation_menu`返回後break，下次從索引重讀，沒有舊c繼續使用。
- 招募`ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB@TSUIKAYOUSEI_NORMAL:29–40、145–149`：原作後續以TARGET讀種族與加入標記；Python需在編輯返回後刷新c，否則仍寫被丟棄的舊角色。本次修正並驗加入標記／TARGET還原。
- 醫療`ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:303–315`：restricted=1禁止替換，舊c保持有效。
- 引繼`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:1491–1560`：先給修練點再把bonus交CHARA_MAKE_MAIN；Python在creation_menu後重新enumerate角色，不持有替換前c。CSV取消bonus規則同上述第5點。

## 驗證與範圍

- 新增35案，先缺模組紅測試，再實作；包含候選排序、0/1/29/30/31/60/61筆、99鍵衝突、上下界、離頁輸入、取消、限制、NO、整筆替換、色碼／武器、數值補正、結果殘值、RNG、bonus次數、尺寸缺值、汎用初始化、Web至SHOP與招募。
- 定向加既有共用編輯／招募／醫療／引繼／主製作：`306 passed, 1 warning in 14.18s`。警告為既有Starlette/httpx棄用提示。父代理抽查後補2筆／奇數尾列／翻頁3案，先紅後綠；最終本檔35案通過。主代理全pytest、真瀏覽器、500局結果見STATUS；本頁不把API當真瀏覽器。
- `tmp/s64/browser_fixture.py`（gitignored）：`python -X utf8 tmp/s64/browser_fixture.py --port 8779`。全新25歲資料沿fresh-adult-25-v1，加人工7000（固有、有尺寸）及7001（非固有、缺尺寸）；兩者有CSV武器。Null敘事、臨時存檔；`/fixture/state`只讀一般數值／全員年齡，不提供虛構catalog失敗計數。
- 瀏覽器路徑：主編輯999→翻頁→手輸7000→Enter→999/99取消→99退出→1重入→999/7001/Enter→999/1/Enter→99→1000→1到SHOP。7001經NO=0重置與尺寸分支，1經男性汎用真初始化；API煙測同路徑到SHOP。
- 清單維持原文每兩筆一行，使用共用print_lc與32字元欄寬；字型寬度近似及REPEAT4的COUNT未共用沿既有W07顯示／COUNT項，見[deviations](../bridge/deviations.md)。沒有新狀態規則或引擎UNVERIFIED；七個無BOMCSV解碼等原有W08未決不因本次清除。
- [0]性別、[8]經歷、其他SIZE_SETTING及主製作初始狀態／人數仍未完成。CSV可選到原有裝備生命週期停止者仍屬W03；本次不宣稱所有模板後續玩法均完成。
