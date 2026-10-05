from pathlib import Path
import re
import pprint
root=Path('source/earGVP/ERB')
p=next(p for p in root.rglob('SHOP_TROPHY.ERB') if p.parent != root)
s=p.read_text(encoding='utf-8-sig')
pages=[]
for line in s.splitlines():
    m=re.fullmatch(r'\s*CALL PRINT_ACHIEVEMENT\((.*)\)',line)
    if not m: continue
    import csv
    args=next(csv.reader([m[1]]))
    if args[1]=='init': pages.append([int(args[0]),[]])
    else:
        args[0]=int(args[0]); args[3]=int(args[3])
        pages[-1][1].append(tuple(args))
names={int(n):name for n,name in re.findall(r'CALL UNLOCK_ACHIEVEMENT\((\d+),"([^"]*)"\)',s)}
out='"""抽取自 ERB/インターミッション画面/SHOP_TROPHY.ERB@SHOW_TROPHY／GET_STATE_*。\n由 tools/extract_achievements.py 重建；文字保持原文。\n"""\n'
out+='PAGES = '+pprint.pformat(tuple((n,tuple(rows)) for n,rows in pages),width=110,sort_dicts=False)+'\n'
out+='NAMES = '+pprint.pformat(names,width=110,sort_dicts=False)+'\n'
for function in ('GET_STATE_ABLUP','GET_STATE_EXPUP'):
    body=s.split('@'+function+',ARG')[1].split('\n@')[0]
    values=[]
    for arr,name,threshold,num in re.findall(r'IF (ABL|EXP):ARG:([^\s]+) >= (\d+)\s+CALL UNLOCK_ACHIEVEMENT\((\d+),',body):
        values.append((arr,name,int(threshold),int(num)))
    out+=function+' = '+pprint.pformat(tuple(values),width=110,sort_dicts=False)+'\n'
Path('src/eragvt/game/achievements_data.py').write_text(out,encoding='utf-8',newline='\n')
