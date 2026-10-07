#!/usr/bin/env python3
"""在週報開頭插入（或更新）「本期目錄」callout。

用法:
    python3 add_toc.py "<週報.md>" ["<週報.md>" ...]

目錄放在 `> 涵蓋…` 那行之後、第一個 `##` 之前，用 Obsidian 同頁標題連結 `[[#標題]]`。
放在第一個 `##` 之前是為了讓 build_html.py 自然略過它（信件版 HTML 自己有目錄）。
重跑會整塊換掉既有目錄，不會重複插入。
"""
import re
import sys

CALLOUT_HEAD = "> [!abstract] 本期目錄"
HINT_MARK = "> [!tip] 可加進工作流"
HINT_BADGE = "🔧 可加進工作流"
# 產業／開源／社群版面內的分群標記行，例如 `**▍台灣**`
REGION_RE = re.compile(r"^\*\*▍(外國|台灣|中國)\*\*\s*$")
# wikilink 目標裡不能出現的字元；標題含這些字元時連結會壞，只能警告請人改標題
BAD_CHARS = set("[]|#^")


def outline(lines):
    """回傳 [(h2, [[h3, 有無工作流提示, 分群或 None], ...])]，略過 code fence 內的 # 行。"""
    out, in_fence, region = [], False, None
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            out.append((line[3:].strip(), []))
            region = None
        elif REGION_RE.match(line):
            region = REGION_RE.match(line).group(1)
        elif line.startswith("### ") and out:
            out[-1][1].append([line[4:].strip(), False, region])
        elif line.startswith(HINT_MARK) and out and out[-1][1]:
            out[-1][1][-1][1] = True
    return out


def link(title):
    if BAD_CHARS & set(title):
        print(f"警告：標題含 wikilink 不允許的字元，連結會壞：{title}", file=sys.stderr)
    return f"[[#{title}]]"


def build_callout(sections):
    lines = [CALLOUT_HEAD]
    if any(hint for _, items in sections for _, hint, _ in items):
        lines += [f"> {HINT_BADGE}：可能值得加進目前的工作流（理由見該條的提示框）", ">"]
    for h2, items in sections:
        lines.append(f"> **{link(h2)}**")
        region = None
        for n, (h3, hint, r) in enumerate(items, 1):
            if r and r != region:
                lines.append(f"> *{r}*")
                region = r
            lines.append(f"> {n}. {link(h3)}" + (f" {HINT_BADGE}" if hint else ""))
        lines.append(">")
    if lines[-1] == ">":
        lines.pop()
    return lines


def strip_existing(lines):
    """移除既有的目錄 callout（從 CALLOUT_HEAD 起連續以 > 開頭的行，含其後一個空行）。"""
    try:
        start = lines.index(CALLOUT_HEAD)
    except ValueError:
        return lines
    end = start
    while end < len(lines) and lines[end].startswith(">"):
        end += 1
    if end < len(lines) and lines[end] == "":
        end += 1
    return lines[:start] + lines[end:]


def insert_position(lines):
    """`> 涵蓋…` 行之後（跳過緊接的空行）；找不到就放在第一個 ## 之前。"""
    for i, line in enumerate(lines):
        if line.startswith("> 涵蓋"):
            j = i + 1
            while j < len(lines) and lines[j] == "":
                j += 1
            return j
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    raise SystemExit("找不到插入點：沒有 `> 涵蓋` 行也沒有 ## 標題")


def process(path):
    text = open(path, encoding="utf-8").read()
    lines = strip_existing(text.split("\n"))
    sections = outline(lines)
    if not sections:
        raise SystemExit(f"{path}：沒有 ## 標題，不產生目錄")
    pos = insert_position(lines)
    callout = build_callout(sections)
    new = lines[:pos] + callout + [""] + lines[pos:]
    open(path, "w", encoding="utf-8").write("\n".join(new))
    print(f"{path}：目錄 {len(sections)} 個版面、{sum(len(i) for _, i in sections)} 條")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        process(p)
