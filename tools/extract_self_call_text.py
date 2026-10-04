"""抽取 S47 固定文字及讀音表；控制流程另由原生 Python 手翻。"""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def main():
    setting=(ROOT/"source/earGVP/ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB").read_text(encoding="utf-8-sig").splitlines()
    sounds=(ROOT/"source/earGVP/ERB/口上/口上システム関係/SELF_CALL.ERB").read_text(encoding="utf-8-sig").splitlines()
    texts={}
    for number,line in enumerate(setting,1):
        if 1203<=number<=1491:
            match=re.match(r"\s*(PRINT(?:PLAIN)?(?:FORM)?[LW]?)\b(?: (.*))?$",line)
            if match: texts[number]=(match[1],match[2] or "")
    rows={}
    for number,line in enumerate(sounds,1):
        match=re.match(r"[ \t]*LOCALS = (.*)$",line)
        if 360<=number<=705 and match:
            rows[number]=match[1]
    text='"""原文抽取：FIRSTSETTING_CHARA_SELFCALL 與 SELF_CALL；由 tools/extract_self_call_text.py 重建。"""\n'
    text+='\nTEXT = {\n'+''.join(f'    {key}: {value!r},\n' for key,value in texts.items())+'}\n'
    text+='\nSOUND_ROWS = {\n'+''.join(f'    {key}: {value!r},\n' for key,value in rows.items())+'}\n'
    (ROOT/"src/eragvt/game/self_call_text.py").write_text(text,encoding="utf-8",newline="\n")
if __name__=="__main__": main()
