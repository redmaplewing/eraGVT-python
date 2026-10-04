"""抽取S45設施擴充的PRINT文字；規則由facilities.py原生手翻。"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/earGVP/ERB/インターミッション画面/SHOP_ENHANCING.ERB'
DESTINATION=ROOT/'src/eragvt/game/facilities_text.py'


def main():
    rows=[]
    for number,line in enumerate(SOURCE.read_text(encoding='utf-8-sig').splitlines(),1):
        match=re.match(r'\s*(PRINT(?:FORM)?[LW]?)\b(?: (.*))?$',line)
        if match: rows.append(f'    {number}: {(match[1],match[2] or "")!r},')
    text='"""從 SHOP_ENHANCING.ERB 抽取原文；key 為行號。由 tools/extract_facilities_text.py 重建。"""\n\nTEXT = {\n'
    DESTINATION.write_text(text+'\n'.join(rows)+'\n}\n',encoding='utf-8',newline='\n')


if __name__=='__main__': main()
