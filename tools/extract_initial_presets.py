"""S78：抽取套組固定資料與AA；流程、亂數及狀態修改由原生Python處理。"""
from pathlib import Path
from pprint import pformat
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'source/earGVP/ERB/SYSTEM/キャラメイキング関連/初期セット'

def extract():
    presets={};descriptions={}
    for path in sorted(BASE.glob('*.ERB')):
        text=path.read_text(encoding='utf-8-sig')
        number=int(path.name.split('_')[0])
        select=text.split(f'@SHOKISET_SELECT_{number}',1)[1]
        ids=tuple(map(int,re.findall(r'^ADDCHARA (\d+)$',select,re.M)))
        strings=dict((int(k),v) for k,v in re.findall(r'^SAVESTR:(\d+)=(.*)$',select,re.M))
        presets[number]=(ids,strings[10],strings.get(12))
        if number not in (6,7,8):continue
        description=text.split(f'@SHOKISET_SETUMEI_{number}',1)[1].split('@SHOKISET_SELECT_',1)[0]
        variants={}
        for case,block in re.findall(r'CASE (\d)\n(.*?)(?=\n\s*CASE|\nENDSELECT)',description,re.S):
            font=None;rows=[]
            for line in block.splitlines():
                value=line.lstrip()
                if value.startswith('SETFONT'):
                    font='ＭＳ Ｐゴシック' if '"' in value else None
                elif value.startswith('PRINTL'):
                    rows.append((value[7:] if len(value)>6 else '',font))
                elif value:raise ValueError((path,value))
            variants[int(case)]=tuple(rows)
        assert set(variants)=={0,1,2,3}
        tail=tuple(re.findall(r'^PRINTL(?: (.*))?$',description.split('ENDSELECT')[1],re.M))
        descriptions[number]=(variants,tail)
    assert set(presets)=={*range(12),14}
    return ('# 由tools/extract_initial_presets.py抽取，來源ERB/SYSTEM/キャラメイキング関連/初期セット。\n'
            +f'PRESET_DATA = {pformat(presets,sort_dicts=False)}\n'
            +f'DESCRIPTIONS = {pformat(descriptions,sort_dicts=False,width=160)}\n')

if __name__=='__main__':
    (ROOT/'src/eragvt/game/initial_preset_data.py').write_text(extract(),encoding='utf-8',newline='\n')
