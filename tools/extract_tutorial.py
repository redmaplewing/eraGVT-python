"""只擷取 TUTORIAL 固定文字；互動流程另以 Python 手翻。"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
SOURCE = "ゲーム内_イベント発生/オープニング処理.ERB"


def extract() -> str:
    lines = (ROOT / "source/earGVP/ERB" / SOURCE).read_text(encoding="utf-8-sig").splitlines()
    start = lines.index("@TUTORIAL")
    end = next(i for i in range(start+1, len(lines)) if lines[i].startswith("@"))
    output = ['"""由 tools/extract_tutorial.py 擷取；key 為原作行號。"""',
              f"# ERB/{SOURCE}@TUTORIAL:454–581", "TEXT = {"]
    for i in range(start+1, end):
        match = re.fullmatch(r"\s*PRINT[LW](?: (.*))?", lines[i])
        if match:
            output.append(f"    {i+1}: {(match[1] or '')!r},")
    output.extend(["}", ""])
    return "\n".join(output)


if __name__ == "__main__":
    (ROOT/"src/eragvt/game/tutorial_text.py").write_text(extract(), encoding="utf-8", newline="\n")
