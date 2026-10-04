"""S49：只抽取固定文字／詞庫；生成演算法由 Python 手翻。"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source/earGVP/ERB/武器と衣装/武器カスタマイズ関連"


def read(name):
    return (SRC / (name + ".ERB")).read_text(encoding="utf-8-sig")


def constants(text):
    return {
        key: int(value)
        for key, value in re.findall(r"^#DIM CONST (\S+) = (\d+)$", text, re.M)
    }


def mask(value, values):
    return sum(values[v.strip()] for v in value.split("+"))


def main():
    kana = read("GENERATE_WEAPON_STR")
    jp = read("GENERATE_WEAPON_STR_JP")
    kc = constants(kana)
    jc = constants(jp)
    ks = []
    for m in re.finditer(
        r"^\t\tIF \(PER_VAR & ([^)]*)\)([^\n]*)\n(.*?)\t\t\tSELECTED_NO:NOW_NO",
        kana,
        re.S | re.M,
    ):
        ban = next(
            (
                bit
                for name, bit in [("長音", 1), ("促音", 2), ("撥音", 4)]
                if name + "使用済み" in m.group(2)
            ),
            0,
        )
        choices = re.findall(r"ADD_STR = ([^\n]*)", m.group(3))
        ks.append((mask(m.group(1), kc), choices, ban, "IF RAND:2 == 0" in m.group(3)))
    js = []
    for m in re.finditer(
        r"^\t\tIF \(PER_VAR & (.*?)\) && RAND:[^\n]*\n(.*?)\t\t\tSELECTED_NO = RAND_NO",
        jp,
        re.S | re.M,
    ):
        chance = re.search(r"(語頭|語尾) \* \(RAND:(\d+) == 0\)", m.group(1))
        cond = re.sub(r" \* \(RAND:\d+ == 0\)", "", m.group(1))
        body = "\n".join(
            x for x in m.group(2).splitlines() if not x.lstrip().startswith(";")
        )
        fields = [
            re.findall(r"\b" + key + r":\(NOW_NO:0\) = ([^\n]*)", body)
            for key in ("NAME_STR", "KUN_STR", "ON_STR")
        ]
        category = re.search(r"CAT_VAR = ([^\n]*)", body)[1]
        js.append(
            (
                mask(cond, jc),
                jc[chance[1]] if chance else 0,
                int(chance[2]) if chance else 0,
                *fields,
                mask(category, jc),
            )
        )
    assert len(ks) == len(re.findall(r"^\t\tIF \(PER_VAR", kana, re.M)) == 167
    assert len(js) == len(re.findall(r"^\t\tIF \(PER_VAR", jp, re.M)) == 205
    add = read("GENERATE_ADD_STR")
    ac = constants(add)
    words = {
        ac[k]: v.split("/") for k, v in re.findall(r"^AD_STR:(\S+) = (.*)$", add, re.M)
    }
    text = {
        i: (m.group(1), m.group(2) or "")
        for i, line in enumerate(read("WEAPON_CUSTOMIZE").splitlines(), 1)
        if (m := re.match(r"\s*(PRINT(?:FORM)?[LW]?)\s?(.*)", line))
    }
    out = '"""由 tools/extract_weapon_customize.py 抽取；來源行號見工具及 weapon-customize.md。"""\n'
    for name, value, source in [("KANA", ks, kana), ("JAPANESE", js, jp)]:
        lines = [
            i
            for i, line in enumerate(source.splitlines(), 1)
            if line.startswith("\t\tIF (PER_VAR")
        ]
        out += (
            name
            + " = [\n"
            + "".join(
                "    " + repr(entry) + ",  # " + str(line) + "\n"
                for entry, line in zip(value, lines)
            )
            + "]\n"
        )
    for name, value in [("ADD_WORDS", words), ("TEXT", text)]:
        out += (
            name
            + " = {\n"
            + "".join(
                "    " + repr(key) + ": " + repr(entry) + ",\n"
                for key, entry in value.items()
            )
            + "}\n"
        )
    (ROOT / "src/eragvt/game/weapon_customize_text.py").write_text(
        out, encoding="utf-8", newline="\n"
    )
    print(len(ks), len(js), len(words), len(text))


if __name__ == "__main__":
    main()
