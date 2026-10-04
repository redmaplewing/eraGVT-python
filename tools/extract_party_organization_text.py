"""抽取 S46 編成原文；選擇與狀態規則由原生 Python 手翻。"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'source/earGVP/ERB/インターミッション画面/SHOP_ORGANIZE_PARTY.ERB'
    rows = []
    for number, line in enumerate(source.read_text(encoding='utf-8-sig').splitlines(), 1):
        match = re.match(r'\s*PRINT(?:PLAIN|FORM)?L?\b(?: (.*))?$', line)
        if match:
            rows.append(f'    {number}: {(match[1] or "")!r},')
    text = '"""SHOP_ORGANIZE_PARTY.ERB 原文，行號為 key；以 tools/extract_party_organization_text.py 重建。"""\n\nTEXT = {\n'
    (ROOT / 'src/eragvt/game/party_organization_text.py').write_text(text+'\n'.join(rows)+'\n}\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
