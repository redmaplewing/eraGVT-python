"""抽取S44引退的PRINT文字；規則仍由retirement.py原生手翻。"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/earGVP/ERB/ヒロイン関連'
DESTINATION=ROOT/'src/eragvt/game/retirement_text.py'


def main():
    rows=[]
    for filename in ('INTAI.ERB','INTAI_CHARA_LIST.ERB'):
        for number,line in enumerate((SOURCE/filename).read_text(encoding='utf-8-sig').splitlines(),1):
            match=re.match(r'\s*(PRINT(?:FORM)?[LW]?)\b(?: (.*))?$',line)
            if match:
                rows.append(f'    {(filename,number)!r}: {(match[1],match[2] or "")!r},')
    text='"""從 INTAI.ERB／INTAI_CHARA_LIST.ERB 抽取原文；key 為檔名及行號。由 tools/extract_retirement_text.py 重建。"""\n\nTEXT = {\n'
    DESTINATION.write_text(text+'\n'.join(rows)+'\n}\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()
