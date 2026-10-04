"""抽取衣裝的原文常數；不抽取或執行遊戲規則。"""
from pathlib import Path
import re
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/earGVP/ERB/武器と衣装/衣装関連"
DEST = ROOT / "src/eragvt/game/clothing_text.py"


def arguments(text):
    """只切開逗號分隔的資料引數；不計算任何 ERB 表達式。"""
    result, start, depth, quote = [], 0, 0, False
    for i, ch in enumerate(text):
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                result.append(text[start:i].strip())
                start = i + 1
    result.append(text[start:].strip())
    return result


def literals(text):
    return re.findall(r'"([^"\r\n]*)"', text)


def extract():
    descriptions = {}
    parts = {}
    menus = {}
    for path in sorted(SOURCE.glob("CLOTHDATA*.ERB")):
        current = None
        source = path.read_text(encoding="utf-8-sig")
        for line in source.splitlines():
            if line.startswith("@"):
                match = re.fullmatch(r"@CLOTH_DESCRIPTION_(\d+)", line)
                current = int(match[1]) if match else None
                if current is not None:
                    descriptions[current] = []
            elif current is not None and line.startswith("PRINTL "):
                descriptions[current].append(line[7:])
            elif current is not None and line.strip() and not line.strip().startswith(";"):
                raise ValueError(f"未處理的描述文字：{path.name}: {line}")
        for m in re.finditer(r"@CLOTH_CUSTOM_HOSEI_(\w+)_(\d+)\s+LOCAL = (-?\d+)\s+RETURN LOCAL", source):
            parts.setdefault(int(m[2]), {})[m[1]] = int(m[3])
        for block in re.split(r"(?m)(?=^@)", source):
            match = re.match(r"@CLOTH_CUSTOMIZE_OPTION_(\d+),", block)
            if not match or int(match[1]) >= 900:
                continue
            cid = int(match[1])
            menu = {"categories": [], "choices": {}, "extra": [], "local_text": [],
                    "count": int(re.search(r"#DIM CUSTOM_NUM\s*=\s*(\d+)", block)[1]),
                    "source": f"ERB/武器と衣装/衣装関連/{path.name}@CLOTH_CUSTOMIZE_OPTION_{cid}:{source.count(chr(10), 0, source.index(block))+1}"}
            option_number = None
            for line in block.splitlines():
                line = line.strip()
                command = re.match(r"(?:IF|ELSEIF) RESULT == (\d+)", line)
                if command:
                    option_number = int(command[1])
                if line.startswith("CALL CLOTH_CUSTOMIZE_OPTION_COMMON(ID,ARG,"):
                    menu["categories"] = [literals(a) for a in arguments(line[line.index('(')+1:-1])[2:-1]]
                m = re.match(r"CALL (?:CLOTH|INNER)_CUSTOMIZE_OPTION_PRINT\((.*)\)$", line)
                if m:
                    args = arguments(m[1])
                    text = [literals(a) for a in args[1:-1]]
                    index = re.fullmatch(r"CUSTOM:(\d+)", args[0])
                    if index:
                        menu["choices"].setdefault(int(index[1]), []).append(text)
                    elif args[0] == "CFLAG:ARG:(900 + ID)":
                        menu["extra"] = text
                        menu["extra_input"] = option_number
                    else:
                        raise ValueError(f"非靜態欄位：{cid}: {args[0]}")
                if line.startswith("LOCALS'="):
                    menu["local_text"].extend(literals(line))
            menus[cid] = menu
    lines = [
        '"""衣裝原文文字。由 tools/extract_clothing_text.py 產生；規則另於 clothing。"""',
        "", "DESCRIPTIONS = " + pformat(descriptions, width=110, sort_dicts=True), "",
        "PARTS = " + pformat(parts, width=110, sort_dicts=True), "",
        "MENUS = " + pformat(menus, width=120, sort_dicts=True), "",
    ]
    wear = (SOURCE / "CLOTH_WEAR.ERB").read_text(encoding="utf-8-sig").splitlines()
    bondage = [line.strip()[11:] for line in wear[470:480] if line.strip().startswith("PRINTFORML ")]
    lines.extend(["BONDAGE_TEXT = " + repr(bondage), ""])
    DEST.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    extract()
