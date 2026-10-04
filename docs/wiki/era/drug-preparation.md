# 醫療室／藥品調製（S42）

入口：`ERB/インターミッション画面/SHOP.ERB@USERSHOP:261–264` 的 [113]。
`GameSession` 呼叫 `eragvt.game.drug_preparation.drug_preparation_gen`；沿用SHOP入口資格。
以下兩個函式均位於 `ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB`。
畫面文字由 `tools/extract_drug_text.py` 抽取到 `drug_text.py`；分支及狀態處理為原生Python。

## 指令與費用

| 指令 | 效果 | 實際消耗 |
|---|---|---|
| 0 | 移除指定素質、觸手中毒與欲情／屈服JUEL清零 | 碎片5 |
| 1–4 | 移除對應素質；1另處理變身形態 | 碎片2 |
| 5 | 胸部異常減一階，更新身體資料 | 碎片2 |
| 10 | 檢查懷孕；狀態4且經過至少3單位才轉5 | 資金50 |
| 11 | 精密檢查；狀態4立刻轉5 | 入口需500、實扣250 |
| 12 | 清除懷孕及指定CFLAG，入院者回隊，依RESULT索引疲勞+25 | 資金7000 |
| 13 | 輸入購買數量、再次確認才入庫 | 每個125 |
| 14 | 重分配角色處方與共用庫存；負數取消 | 無額外費用 |
| 15 | 機器人維修及器官切換 | 維修500／1500／5500 |
| 20 | 清CFLAG:30／32 | 碎片10 |
| 21 | CFLAG:32至少500000000000000000時，30／32乘0.10 | 資金1250 |
| 30／31 | 更新成熟／成長停滯狀態 | 碎片1 |
| 51（未顯示） | 研究FLAG:54至少5時可修復肢體，取得共生 | 資金25000＋碎片40 |
| 100 | 加入機器人角色；非單人且CHARANUM≤29 | 資金50000 |
| 999 | 返回SHOP | 無 |

費用入口：`@DRUG_PREPARATION:65–243`；角色處理：`@CHARA_LIST_DRUG:601–1041`。
角色選擇[999]回醫療室；不合格的角色索引繼續等待，不扣費。
原文沒有製作系統；只有[13]購入道具，其餘是直接治療或處方。

## 保留的原作差異

- `@CHARA_LIST_DRUG:456–590／601–1025`：列表與手輸入資格不完全相同，不能拿顯示名單取代輸入判斷。
  例如共生者不顯示於[3]，仍能手動選取；[14]列表的懷孕條件使用OR而永真，但輸入會拒絕1／3／5；
  [15]只列可用女性機器人，手動索引接受其他機器人；[20]／[21]輸入不再檢查可用狀態。
- `@CHARA_LIST_DRUG:878–939`：維修顯示的灰色邊界與實際條件不同。
  疲勞1–19按0減5；11–29按1減20；疲勞>20的完整維修實際也是按0，畫面的[2]無作用。
  疲勞20時，0無作用、1可用。扣費不足留在維修輸入等待。
- `@CHARA_LIST_DRUG:835–838`：入院者呼叫 `ERB/ヒロイン関連/RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY:1–23`，
  該函式無RETURN而將RESULT設0，因此後續疲勞+25實際寫角色索引0；非入院者才寫原選取角色。
- `@DRUG_PREPARATION:11–15／172–175`：ROBO與LOCAL:1在同一次入口重畫時累加，並非每次清零。
- `@CHARA_LIST_DRUG:674–702`：改造值減RAND(5,20)，正常形態與變身形態依原文分別調整；SET_PROFILE同步資料。
- `@CHARA_LIST_DRUG:1012`：成長計數225只排除0與>14，手輸入負數也可通過；列表只顯示1–14。
  225不是歲數：`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@GROW_HANTEI:16–24` 每次累加，7與>14觸發成長階段。

## [51]確認死循環修復（2026-10-04使用者授權）

- **原文事實**：`@DRUG_PREPARATION:31–61`完整顯示清單沒有51，:219接受手輸入；:220–223要求研究FLAG:54≥5。
  未找到隱藏原因的直接註解，因此不宣稱是故意隱藏或漏加按鈕，也不自行新增入口。
- `@DRUG_PREPARATION:225–232`說明修復四肢、25000資金／40碎片與共生代價，問「本当に手術をしてよろしいですか？」並顯示0是／1否。
  :232的INPUT在:233標籤之前；:274–276錯誤分支跳過INPUT，非0反覆PRINTW而無法改答。
- `@DRUG_PREPARATION:245–273`明註「翻訳・移植終わるまでデッドコード化」，以`1==0`停用否分支。
  原否分支是少女研究者另提處置方案，第二次0／1均回醫療室，其中0的`;CALL AMPUTEE`亦已註解。
  第二次確認也有INPUT位於標籤之前的問題；本次不啟用或擴寫這段不可達功能。
- 手術正支線`@DRUG_PREPARATION:234–243`核對資源再呼叫`@CHARA_LIST_DRUG:584–599／1022–1038`；
  角色999取消、成功扣費並清欠損／設共生均保留；列表倒數限制與手輸入資格差異也保留。
- **歷史佐證**：`更新履歴.txt:383／402–415`的2023/10/16項記錄中國版部分移植、醫療室欠損治療及剩餘內容待翻譯；
  `●開発者向け資料/●中国mod調査メモ.txt:58–75`分別記錄試驗性販賣／處刑與欠損治療。
  `＠中国版逆輸入作業(未訳テキスト類)/SHOP_AMPUTEE.ERB@AMPUTEE:2–4／26–41`在正式ERB目錄外且註明翻譯未完；
  `ERB/インターミッション画面/SHOP_TURNEND.ERB@RECOVERY_OVER_TIME:719–731`的處刑呼叫同樣註解。
- **搜尋限制**：全來源精確搜尋AMPUTEE、確認標籤與51手術呼叫，先計數後完整讀結果；玩家說明與補丁README的四肢／生物質／共生／醫療關鍵詞無命中。
  Git全部refs中相關原作檔僅有`728222e`匯入，沒有上游修改歷史；未展開舊版壓縮包，不宣稱已還原中國版最初實作。
- **有界推論與修復**：使用者授權判斷意圖後修bug；1拒絕手術回醫療室、其他值提示後重新INPUT，是尊重提問及作者停用邊界的最小修復，
  不是證實作者最終設計。0仍照既有手術；不啟用NPC／AMPUTEE、不新增51按鈕。已記錄DEVIATION，無新增UNVERIFIED。

## 機器人加入的預設路徑

`@DRUG_PREPARATION:280–430`：等待性別0／1或取消99，確定才扣費、ADDCHARA0、保存／切換TARGET、設五項素質。
後續特徵選單正常等待0手選／1不設／2隨機；手選最多3項。最後CHARA_MAKE_FINALIZE後恢復TARGET。

個別編輯暫走 `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–34／318–353`
不改任何設定直接[99]的路徑：暫存衣裝、初始化角色、解碼既有武器、清壓縮字串、身體計算殘值、更新結界、
清SAVESTR:0–3、恢復衣裝。沒有提供名字／性格／身體／武器等完整手動編輯器；沿用既有角色製作UI偏離。
特徵的資格與隨機設定沿用既有原生函式；手選畫面沿用同源的 `feat_select_ui`，其種族9分支不適用實際201以上種族。

## 引擎語意與顯示

- INPUT只寫RESULT:0：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`。
- GOTO跳指定標籤：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2415–2437`；[51]因此跳過原INPUT。
- 一般函式終端將RESULT:0設0；RETURN999只寫第0格：
  `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`、
  `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2006–2023`。
- RAND(a,b)上限不包含b：`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:953–972`。
- TIMES精確模式decimal乘算後截斷：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`。
- PRINT累積段落到換行／PRINTPLAIN才切按鈕，沿用TextOutput：
  `reference/emuera-1824/Emuera/GameView/PrintStringBuffer.cs:111–115／151–164／275–325`。
  主選單的非數字素質括號不額外產生按鈕；角色附註與同一行PRINT相接。
  特徵的「固定取得」仍走PRINTPLAIN，不併進按鈕。原作DOT_AFTER與SHORTLINE使用既有語意。
- 不新增UNVERIFIED；個別編輯畫面略過及既有CLEARLINE顯示簡化沿用既有偏離。

## 驗證

- 定向112項：各項消耗與恰足／不足、兩形態、處方、診斷、手術、維修、成長、機器人三種特徵路徑、取消、
  無效輸入、RESULT尾格、按鈕與GameSession實際購買返回；`112 passed in 2.59s`。
- [51]修復先紅：新增9例中`5 failed, 4 passed`，原因為非0停止／GameSession HALTED；修復後全綠。
  覆蓋多次錯值再0／1、資源不足、角色999取消與GameSession不停止；既有按鈕斷言確保51仍隱藏。
- 修復後主代理獨立完整pytest：`2734 passed, 1 warning in 199.78s (0:03:19)`；警告為既有Starlette/httpx棄用提醒。
- 標準500局完成：default 246上限／4回標題，tokusou 250上限；catalog失敗0。
  十個50局獨立前景批次exit=0，seed全集、log／JSONL完全一致；逐seed全欄位與S41相同。
  產物與核對程式留在`tmp/s42/`；標準模擬不操作本選單，本次局部確認修復採定向＋全套pytest，不重跑相同模擬。
