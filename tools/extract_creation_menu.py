"""S55：只抽取角色製作 UI 固定文字；流程由 creation_menu 手翻。"""
from pathlib import Path
import re
from pprint import pformat

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連'
FILES=('CHARA_MAKE.ERB','FIRSTSETTING_TITLE.ERB','FIRSTSETTING_CROWNNAME.ERB',
       'FIRSTSETTING_CHARA.ERB','FIRSTSETTING_CHARA_SYUZOKU.ERB',
       'FIRSTSETTING_CHARA_TRANSFORMATION.ERB','SHOKISET.ERB')
def extract():
    text={}
    for name in FILES:
        for n,line in enumerate((BASE/name).read_text(encoding='utf-8-sig').splitlines(),1):
            if name=='FIRSTSETTING_CHARA.ERB' and not 1024<=n<=1068:continue
            if name=='FIRSTSETTING_CHARA_SYUZOKU.ERB' and n<168:continue
            if name=='FIRSTSETTING_CHARA_TRANSFORMATION.ERB' and n<453:continue
            m=re.fullmatch(r'\s*PRINT(?:L|W)(?: (.*))?',line,re.I)
            if name=='CHARA_MAKE.ERB' and 325<=n<=337:
                m=re.fullmatch(r'\s*PRINT(?:FORM)?L(?: (.*))?',line,re.I)
            if m:text[name,n]=m[1] or ''
    presets={}
    dynamic=set()
    for p in sorted((BASE/'初期セット').glob('*.ERB')):
        func=None
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            m=re.fullmatch(r'@SHOKISET_(NAME|SETUMEI)_(\d+)',line)
            if line.startswith('@'):
                func=(m[1],int(m[2])) if m else None
                continue
            if func:
                m=re.fullmatch(r'\s*PRINTL(?: (.*))?',line)
                if m:presets.setdefault(func,[]).append(m[1] or '')
                elif line.strip() and not line.lstrip().startswith(';'):dynamic.add(func)
    # 不把含 RNG／樣式／條件的說明冒充固定文字；它們在實際呼叫處停止。
    assert dynamic=={('SETUMEI',6),('SETUMEI',7),('SETUMEI',8)},dynamic
    for func in dynamic:presets.pop(func,None)
    dim=(ROOT/'source/earGVP/ERB/DIM.ERH').read_text(encoding='utf-8-sig')
    arrays={name:tuple(re.findall(r'"([^"]*)"',re.search(r'#DIMS CONST '+name+r'=(.*?)\}',dim,re.S)[1]))
            for name in ('transnamegenre','namelang','racegenre')}
    calls=(BASE/'FIRSTSETTING_変身デフォルト口上.ERB').read_text(encoding='utf-8-sig').split('@FIRSTSETTING_CHANGINGCALL_DETAIL')[0]
    calls=tuple(re.findall(r'^DATAFORM (.*)$',calls,re.M))
    return ('# 由 tools/extract_creation_menu.py 產生；來源 SYSTEM/キャラメイキング関連 與 DIM.ERH。\n'
            +f'TEXT = {pformat(text,sort_dicts=False)}\nPRESETS = {pformat(presets,sort_dicts=False)}\n'
            +f'UNPORTED_DESCRIPTIONS = (6, 7, 8)\nARRAYS = {pformat(arrays,sort_dicts=False)}\nCALLS = {pformat(calls)}\n')
if __name__=='__main__':
    (ROOT/'src/eragvt/game/creation_text.py').write_text(extract(),encoding='utf-8',newline='\n')
