"""只抽取一般身體UI固定文字；遊戲分支由body_editor手寫。"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB'
    lines=source.read_text(encoding='utf-8-sig').splitlines()
    # 行號為原作來源，不包含ERB運算式或敘事情節。
    selected=(73,74,138,143,151,187,236,762,763,773,800,835,868,927,971,992,1005,1023,1041,1054,1058,1250,1253,1300,1301,1346,1347,1349,1350,1352,1353,1355,1356,1358,1359,1361,1362,1364,1365,1367,1368,1370,1371,1375,1436,1438,1444,1450,2258,2260,2261)
    out=['"""由tools/extract_body_editor.py抽取；CHARA_SIZE_UI.ERB行號為key。"""','TEXT = {']
    for n in selected:
        line=lines[n-1].strip()
        value=re.sub(r'^(?:PRINT(?:PLAIN|FORM)?L?|LOCALS:1\s*=)\s*','',line)
        out.append(f'    {n}: {value!r},')
    out.append('}\n')
    target=ROOT/'src/eragvt/game/body_editor_text.py'
    target.write_text('\n'.join(out),encoding='utf-8',newline='\n')

if __name__=='__main__':main()
