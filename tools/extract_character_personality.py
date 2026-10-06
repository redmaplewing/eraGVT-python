"""抽取S62固定選單文字；只抽字串，不解譯遊戲流程。"""
from pathlib import Path
from pprint import pformat
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB'


def extract():
    lines=SOURCE.read_text(encoding='utf-8-sig').splitlines()
    text={}
    for n,line in enumerate(lines,1):
        match=re.fullmatch(r'PRINTL (.+)',line)
        if match:text[n]=match[1]
    labels=[re.fullmatch(r'LOCALS \+= "(　　[^"<>]+)"',line)[1]
            for line in lines if re.fullmatch(r'LOCALS \+= "(　　[^"<>]+)"',line)]
    return ('# tools/extract_character_personality.py 產生；原文行號及十組標籤。\n'
            +'TEXT = '+pformat(text,sort_dicts=False)+'\nGROUP_LABELS = '+repr(tuple(labels))+'\n')


if __name__=='__main__':
    (ROOT/'src/eragvt/game/character_personality_text.py').write_text(extract(),encoding='utf-8',newline='\n')
