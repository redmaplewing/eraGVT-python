"""抽取S43追加招募的PRINT文字；規則仍由recruitment.py原生手翻。"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source/earGVP/ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB'
DESTINATION = ROOT / 'src/eragvt/game/recruitment_text.py'


def main():
    rows=[]
    for number,line in enumerate(SOURCE.read_text(encoding='utf-8-sig').splitlines(),1):
        match=re.match(r'\s*(PRINT(?:FORM)?[LW]?|PRINTPLAIN)\b(?: (.*))?$',line)
        if match:
            rows.append(f'    {number}: {(match[1],match[2] or "")!r},')
    text='"""從 ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB 抽取的原文；key 為行號。由 tools/extract_recruitment_text.py 重建。"""\n\nTEXT = {\n'
    DESTINATION.write_text(text+'\n'.join(rows)+'\n}\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()
