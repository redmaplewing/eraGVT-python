"""S63三個數值編輯選單的固定文字；流程仍手寫Python。"""
from pathlib import Path
from pprint import pformat
import re

ROOT=Path(__file__).resolve().parents[1]
FILES={'R':('FIRSTSETTING_CHARA_SYUZOKU.ERB',164),
       'T':('FIRSTSETTING_CHARA_TRANSFORMATION.ERB',66),
       'B':('FIRSTSETTING_CHARA_STATUS_BONUS.ERB',1000)}


def extract():
    text={}
    for key,(name,end) in FILES.items():
        path=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連'/name
        for n,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
            if n>end:break
            m=re.fullmatch(r'\s*PRINT(?:FORML|FORM|PLAIN|L|W)?(?: (.*))?',line)
            if m and m[1] and not any(c in m[1] for c in '{}%\\'):
                text[key,n]=m[1]
    return '# 由 tools/extract_character_build.py 抽取；key為檔案縮寫、原文行號。\nTEXT = '+pformat(text,sort_dicts=False)+'\n'


if __name__=='__main__':
    (ROOT/'src/eragvt/game/character_build_text.py').write_text(extract(),encoding='utf-8',newline='\n')
