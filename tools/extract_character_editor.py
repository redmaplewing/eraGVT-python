"""抽取S60角色編輯/姓名/口上選單固定原文；不解譯ERB流程。"""
from pathlib import Path
import re
from pprint import pformat

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB'

def extract():
    text={}
    for n,line in enumerate(SOURCE.read_text(encoding='utf-8-sig').splitlines(),1):
        if n>1200:break
        m=re.fullmatch(r'\s*PRINT(?:L|W)(?: (.*))?',line)
        if m and m[1]:text[n]=m[1]
    return '# 由 tools/extract_character_editor.py 產生；FIRSTSETTING_CHARA.ERB，key為行號。\nTEXT = '+pformat(text,sort_dicts=False)+'\n'

if __name__=='__main__':
    (ROOT/'src/eragvt/game/character_editor_text.py').write_text(extract(),encoding='utf-8',newline='\n')
