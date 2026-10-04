"""擷取 S51 固定顯示文字；不翻譯 ERB 邏輯。"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "RELATION": ("SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB", 189, 553),
    "OPENING": ("ゲーム内_イベント発生/オープニング処理.ERB", 659, 752),
}

def extract():
    out = ['"""由 tools/extract_relation_setting.py 擷取；key 為原作行號。"""', '']
    for name, (path, lo, hi) in SOURCES.items():
        out.extend([f'# ERB/{path}', f'{name} = {{'])
        lines = (ROOT / "source/earGVP/ERB" / path).read_text(encoding="utf-8-sig").splitlines()
        for i in range(lo, hi+1):
            match = re.fullmatch(r"\s*PRINT(?:FORM)?(?:L|W)?(?: (.*))?", lines[i-1])
            if match:
                out.append(f'    {i}: {(match[1] or "")!r},')
        out.extend(['}', ''])
    return '\n'.join(out)

if __name__ == "__main__":
    (ROOT / "src/eragvt/game/relation_setting_text.py").write_text(extract(), encoding="utf-8", newline="\n")
