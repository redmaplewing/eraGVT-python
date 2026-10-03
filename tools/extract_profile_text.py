"""從唯讀 SEXUAL_PROFILE.ERB 抽取 STRDATA 候選；規則由 sexual_profile.py 手寫。"""
from pathlib import Path
import pprint

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/earGVP/ERB/ヒロイン関連/SEXUAL_PROFILE.ERB"
DEST = ROOT / "src/eragvt/game/profile_text.py"


def extract():
    groups = {}
    name = ""
    collecting = False
    for raw in SOURCE.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line.startswith("@"):
            name = line[1:].split(",")[0]
        elif line.startswith("STRDATA "):
            groups.setdefault(name, []).append([])
            collecting = True
        elif line == "ENDDATA":
            collecting = False
        elif collecting:
            assert line.startswith("DATA "), line
            groups[name][-1].append(line[5:])
    return groups


if __name__ == "__main__":
    DEST.write_text(
        '\"\"\"抽取自 ヒロイン関連/SEXUAL_PROFILE.ERB@MAKE_ADJ_BC～MAKE_BAD_REPUTATION:114–630。\n'
        '由 tools/extract_profile_text.py 產生；不手動修改。\"\"\"\n\n'
        + "TABLES = " + pprint.pformat(extract(), width=110, sort_dicts=False) + "\n",
        encoding="utf-8", newline="\n",
    )
