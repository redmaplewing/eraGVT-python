# 初期套組（S78／W04）

## 原生流程

`ERB/SYSTEM/キャラメイキング関連/SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:5–45`：列出0–98間有定義的名稱，只有0–11與14；12／13無定義。
選定後先顯示說明，確認只接受0／1，0回選單、99在套組列表回傳-1。否決不改角色，但6／7／8已消耗說明亂數。
確認1先逐一DELCHARA 1並減FLAG8，再呼叫套組、最後CSVFIX；每套組自己也呼叫CSVFIX，所以成功路徑共兩次。
ADD／DEL不改TARGET及RESULT：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1026–1067`、`GameProc/Function/Instraction.Child.cs:934–965`；
自然函式終端RETURN0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。RESULTS維持原值。

下表路徑前綴為`ERB/SYSTEM/キャラメイキング関連/初期セット/`；每列函式為`@SHOKISET_SELECT_n`。

| 編號／檔案 | 原文行號 | CSV編號依序 | 共通口號 |
|---|---|---|---|
| 0_特捜戦隊.ERB | 18–32 | 301,302,303 | 覆寫 |
| 1_マジカルハンター.ERB | 18–32 | 311,312,313 | 覆寫 |
| 2_地球防衛クラブ.ERB | 18–30 | 321,322,323 | 保留 |
| 3_侍女式自動人形.ERB | 21–33 | 331,332,333 | 保留 |
| 4_ＫＪガールズ.ERB | 19–37 | 341–346 | 保留 |
| 5_RWBY.ERB | 20–34 | 351–354 | 保留 |
| 6_リリカルハンターAs.ERB | 169–183 | 1701–1703 | 覆寫 |
| 7_リリカルハンターStS.ERB | 172–186 | 1711–1713 | 覆寫 |
| 8_リリカルハンターViVid.ERB | 186–200 | 1741–1743 | 覆寫 |
| 9_アイサイガー５.ERB | 19–37 | 1501–1505 | 覆寫 |
| 10_髙橋退魔団.ERB | 22–54 | 361–366 | 本次保留停止，見下方 |
| 11_JSKチーム.ERB | 19–34 | 371–374 | 保留 |
| 14_船田姉妹＋燈雪.ERB | 18–32 | 3081,3080,3082,3083 | 保留 |

各套組只設FLAG5、SAVESTR10；只有標覆寫者另設FLAG7、SAVESTR12，其他共通設定保留。
0–9、11、14已接選擇、否決、確認、互換、重入個別編輯與開始；不宣稱13套全部完成。
初始化、FINALIZE及進SHOP沿既有流程，原作`オープニング処理.ERB@EVENTFIRST:254–267`把前6人隊列旗標設1（`DIM.ERH:24`），不是只前3人。

## 動態說明

6／7／8的`@SHOKISET_SETUMEI_n:8`均RAND:4；四分支AA由抽取工具保留原文，流程由Python原生選取。
SETFONT先設「ＭＳ Ｐゴシック」、印AA、重設預設字型再印圖名和共通說明。
引擎：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:486–492`、`Emuera/GameView/EmueraConsole.Print.cs:60`。
本次新增TextOutput字型欄與Web呈現，按鈕拆分及catalog交易回復均保留欄位；catalog的SETFONT指令仍屬W07既有缺口，沒有冒充已全面完成。

## 套組10具體範圍阻塞

`10_髙橋退魔団.ERB@SHOKISET_SELECT_10:39–52`直接設定固定性經驗／性特徵。
`CSV/Chara365_アンネリース シュミット.csv:9–11`明示CSTR204=13、205=実年齢に合わせる、206=-1；
`CSV/Chara366_フィーア マイヤー.csv:7–9`明示CSTR204=60、205=15、206=15。
`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE:501、515`呼叫年齡設定；
`@CHARA_MAKE_AGE_SETTING:1409–1444`套回這些指定，365實際／外見13，366外見兩形態15。
因此本次不能交付新增性經驗初始化接到未成年模板；不以25歲fixture推論產品輸入，不新增成人guard、不改原CSV／產品年齡規則。
套組10仍可看說明／否決；確認在SHOKISET原有刪除舊角色後、任何套組10配置之前明確停止。沒有無聲略過該段後宣稱成功，也不稱原作未完成。
另有計數索引疑似筆誤，事實與待裁決推論集中於[未決](../bridge/unresolved.md)。

## 驗收範圍

`tests/test_initial_presets.py`採fresh-adult-25-v1人工姓名／全新25歲定義；12套均檢查四年齡欄25。
產品數值配置、初始化、亂數、真正選單與返回保留；Null敘事。沒有擴張W02[8]、序章或新模式。
瀏覽器前態：`python tmp/s78/browser_fixture.py --port 8790`，`/fixture/control`可見表單重建標題；`/fixture/state`只讀證據。
從標題0→0→200；逐套n→0否決→n→1確認→200→99退回，再1→99個別編輯確認、1000→1開始。
覆蓋人數差異：3人任一、4人5／11／14、5人9、6人4；6／7／8分別實際看隨機AA、否決重選。14確認CSV順序3081先於3080。
原始套組10不能列入「開始成功」，僅驗說明／否決／明確停止。主代理另記真瀏覽器／全pytest／正式500的實際結果。

主代理驗收：全pytest5072、十二套真瀏覽器（否決／確認／返回／編輯／開始）通過，AA字型及25歲四欄核對，console錯誤0。正式500完整JSON與S76一致，default247上限／3回標題、tokusou250上限，catalog／fixture失敗0。證據位於tmp/s78；本次不宣稱序章、套組10或W04整包完成。
