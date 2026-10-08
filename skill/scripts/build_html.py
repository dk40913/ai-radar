#!/usr/bin/env python3
"""把週報 markdown 轉成報紙排版的單檔 HTML（圖片內嵌 base64），並產生短版純文字信摘要。

用法:
    uv run --quiet --with markdown build_html.py --report "<週報.md>" --images-dir "<vault>/AI知識雷達/attachments" \
        --out "<run_dir>/<date> AI知識雷達.html" --digest "<run_dir>/digest.txt"
"""
import argparse
import base64
import html as htmlmod
import os
import re
import subprocess
import tempfile

import markdown
from markdown.extensions.toc import slugify_unicode

EMBED_MAX_WIDTH = 900
EMBED_JPEG_QUALITY = "72"

CSS = """
:root{--ink:#1c1b18;--muted:#6b675e;--rule:#d9d4c7;--paper:#fbf9f4;--accent:#8c2f1f;--soft:#f1ede3;--warn:#8a6d1a}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 -apple-system,"PingFang TC","Noto Sans TC","Helvetica Neue",Arial,sans-serif}
.page{max-width:780px;margin:0 auto;padding:28px 22px 80px}
.masthead{text-align:center;border-top:3px double var(--ink);border-bottom:1px solid var(--ink);padding:18px 0 12px;margin-bottom:8px}
.masthead h1{font-family:"Songti TC","Noto Serif TC",Georgia,serif;font-size:40px;letter-spacing:.08em;margin:0;font-weight:700}
.masthead .period{color:var(--muted);font-size:13px;letter-spacing:.12em;margin-top:6px}
.masthead .stats{color:var(--muted);font-size:12px;margin-top:2px}
nav.toc{background:var(--soft);border:1px solid var(--rule);border-radius:6px;padding:12px 18px;margin:18px 0 26px;font-size:14px}
nav.toc .sec{font-weight:700;margin-top:6px}
nav.toc ol{margin:2px 0 4px 18px;padding:0;color:var(--muted)}
nav.toc li{margin:1px 0}
nav.toc a{color:inherit;text-decoration:none}
nav.toc a:hover{color:var(--accent);text-decoration:underline}
details.section{border-top:2px solid var(--ink);margin-top:34px;padding-top:4px}
details.section>summary{cursor:pointer;list-style:none;display:flex;align-items:baseline;gap:12px;padding:8px 0}
details.section>summary::-webkit-details-marker{display:none}
details.section>summary h2{font-family:"Songti TC","Noto Serif TC",Georgia,serif;font-size:26px;margin:0;letter-spacing:.06em}
details.section>summary .hint{color:var(--muted);font-size:12px}
details.section>summary .hint::before{content:"收合 ▾"}
details.section:not([open])>summary .hint::before{content:"展開 ▸"}
article.item{padding:10px 0 22px;border-bottom:1px solid var(--rule)}
article.item:last-child{border-bottom:none}
.region{font-family:"Songti TC","Noto Serif TC",Georgia,serif;font-size:17px;letter-spacing:.2em;color:var(--muted);border-bottom:1px solid var(--muted);margin:22px 0 4px;padding-bottom:2px}
article.item h3{font-family:"Songti TC","Noto Serif TC",Georgia,serif;font-size:21px;line-height:1.4;margin:14px 0 6px}
p.oneliner{background:var(--soft);border-left:4px solid var(--accent);padding:8px 12px;margin:6px 0 12px;font-size:15.5px}
p.oneliner b{color:var(--accent);margin-right:6px}
figure{margin:14px 0 16px}
figure img{width:100%;height:auto;display:block;border:1px solid var(--rule);border-radius:4px;background:#fff}
figcaption{color:var(--muted);font-size:12.5px;margin-top:6px}
.lead{font-size:17px;line-height:1.85}
.lead p:first-of-type::first-letter{font-family:"Songti TC",Georgia,serif;font-size:2.6em;float:left;line-height:.9;padding:6px 8px 0 0;color:var(--accent)}
p{margin:8px 0}
strong{font-weight:700}
a{color:var(--accent)}
.links{font-size:13px;color:var(--muted);margin-top:10px;word-break:break-all}
.links a{color:var(--muted)}
.callout{border-left:4px solid var(--warn);background:#fdf6e3;padding:6px 12px;margin:8px 0;font-size:14px;border-radius:0 4px 4px 0}
.callout.note{border-color:#3b6ea5;background:#eef4fb}
.callout.tip{border-color:#2e7d4f;background:#edf7f0}
.toc .hint{color:#2e7d4f;font-size:12px;margin-left:6px}
.wl{border-bottom:1px dotted var(--accent);color:var(--accent)}
blockquote{margin:8px 0;padding-left:12px;border-left:3px solid var(--rule);color:var(--muted)}
ul,ol{padding-left:22px}
li{margin:4px 0}
hr{border:none;border-top:1px solid var(--rule);margin:18px 0}
code{background:var(--soft);padding:1px 5px;border-radius:3px;font-size:.92em}
pre{background:#f4f1ea;padding:10px;border-radius:5px;overflow-x:auto;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:10px 0}
th,td{border:1px solid var(--rule);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--soft)}
.fab{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:10}
.fab a,.fab button{width:44px;height:44px;border-radius:50%;border:none;background:var(--ink);color:#fff;font-size:18px;line-height:44px;text-align:center;text-decoration:none;cursor:pointer;padding:0;box-shadow:0 2px 6px rgba(0,0,0,.25)}
.fab a:hover,.fab button:hover{background:var(--accent)}
#tocpop{inset:auto;right:72px;bottom:16px;margin:0;width:min(380px,calc(100vw - 96px));max-height:75vh;overflow-y:auto;padding:0;border:1px solid var(--rule);border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.2);background:var(--paper)}
#tocpop nav.toc{margin:0;border:none}
.footer{margin-top:40px;color:var(--muted);font-size:12px;text-align:center;border-top:1px solid var(--rule);padding-top:12px}
@media (max-width:600px){.masthead h1{font-size:30px}.page{padding:16px 14px 70px}body{font-size:15.5px}}
"""


def read_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def find_image(images_dir, name):
    name = name.split("|")[0].strip()
    p = os.path.join(images_dir, name)
    if os.path.exists(p):
        return p
    for root, _, files in os.walk(images_dir):
        if name in files:
            return os.path.join(root, name)
    return None


def embed_image(path):
    """縮成 ≤900px 的 jpeg 再 base64，控制單檔體積。"""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
        tmp = t.name
    r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", EMBED_JPEG_QUALITY,
                        "-Z", str(EMBED_MAX_WIDTH), path, "--out", tmp], capture_output=True)
    src = tmp if r.returncode == 0 and os.path.getsize(tmp) > 0 else path
    mime = "image/jpeg" if src == tmp else ("image/png" if path.lower().endswith(".png") else "image/jpeg")
    data = base64.b64encode(open(src, "rb").read()).decode()
    if os.path.exists(tmp):
        os.remove(tmp)
    return f"data:{mime};base64,{data}"


def preprocess(md, images_dir):
    # 圖片嵌入 ![[file|600]] + 緊接的 *說明* 行 → <figure>
    def img_sub(m):
        path = find_image(images_dir, m.group(1))
        cap = m.group(2) or ""
        if not path:
            return ""
        cap_html = f"<figcaption>{htmlmod.escape(cap.strip('* '))}</figcaption>" if cap else ""
        return f'\n<figure><img src="{embed_image(path)}" alt="">{cap_html}</figure>\n'
    md = re.sub(r"^!\[\[([^\]]+)\]\]\s*\n(?:(\*[^\n]+\*)\s*\n)?", img_sub, md, flags=re.M)
    # callout > [!type] 內容（可多行）
    def callout_sub(m):
        kind = m.group(1).lower()
        body = " ".join(l.lstrip("> ").strip() for l in m.group(0).splitlines())
        body = re.sub(r"^\[![^\]]+\]\s*", "", body)
        if kind == "tip" and body.startswith("可加進工作流"):
            body = "🔧 可加進工作流：" + body[len("可加進工作流"):].strip()
        return f'\n<div class="callout {htmlmod.escape(kind)}">{htmlmod.escape(body)}</div>\n'
    md = re.sub(r"^> \[!(\w+)\][^\n]*(?:\n> [^\n]*)*", callout_sub, md, flags=re.M)
    # wikilink → 淡色標示（信件裡點不了 Obsidian 連結）
    md = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", lambda m: f'<span class="wl">{htmlmod.escape(m.group(2))}</span>', md)
    md = re.sub(r"\[\[([^\]]+)\]\]", lambda m: f'<span class="wl">{htmlmod.escape(m.group(1))}</span>', md)
    # 一句話結論
    md = re.sub(r"^\*\*一句話\*\*\s*(.+)$", lambda m: f'<p class="oneliner"><b>一句話</b>{htmlmod.escape(m.group(1))}</p>', md, flags=re.M)
    # 原文／討論／另見 連結行 → 收成一段小字
    def links_sub(m):
        lines = []
        for l in m.group(0).strip().splitlines():
            lab, url = l.split("：", 1)
            url = url.strip()
            lines.append(f'{htmlmod.escape(lab)}：<a href="{htmlmod.escape(url)}">{htmlmod.escape(url)}</a>')
        return '\n<p class="links">' + "<br>".join(lines) + "</p>\n"
    md = re.sub(r"(?:^(?:原文|討論|另見|來源)：\S+\s*$\n?)+", links_sub, md, flags=re.M)
    return md


def split_sections(md):
    """回傳 [(h2 標題, 內容 md)]，h2 之前的內容標題為空字串。"""
    parts = re.split(r"^## (.+)$", md, flags=re.M)
    out = [("", parts[0])]
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


# 產業／開源／社群版面內的分群標記行，例如 `**▍台灣**`
REGION_RE = re.compile(r"^\*\*▍(外國|台灣|中國)\*\*[ \t]*$", re.M)


def split_regions(body_md):
    """回傳 [(分群或 None, 內容 md)]；沒有分群標記時整段一組。"""
    parts = REGION_RE.split(body_md)
    out = [(None, parts[0])] if parts[0].strip() else []
    return out + [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]


def render_section_body(body_md):
    """把 ### 條目各包成 <article>；有分群標記時每組前面放分群小標。"""
    groups = split_regions(body_md)
    if any(r for r, _ in groups):
        return "".join((f'<div class="region">{htmlmod.escape(r)}</div>' if r else "") + render_items(md)
                       for r, md in groups)
    return render_items(body_md)


def render_items(body_md):
    chunks = re.split(r"^### (.+)$", body_md, flags=re.M)
    html = ""
    if chunks[0].strip():
        html += markdown.markdown(chunks[0], extensions=["extra", "sane_lists"])
    for i in range(1, len(chunks), 2):
        title = chunks[i].strip()
        inner = re.sub(r"^\s*---\s*$", "", chunks[i + 1], flags=re.M)
        hid = slugify_unicode(title, "-")
        html += (f'<article class="item" id="{hid}"><h3>{htmlmod.escape(title)}</h3>'
                 + markdown.markdown(inner, extensions=["extra", "sane_lists"]) + "</article>")
    return html


def build_html(fm, body_md, images_dir):
    md = preprocess(body_md, images_dir)
    md = re.sub(r"^# .+\n", "", md, count=1, flags=re.M)  # 主標題交給 masthead
    period_line = ""
    m = re.search(r"^> (涵蓋[^\n]+)\n", md, flags=re.M)
    if m:
        period_line = m.group(1)
        md = md[:m.start()] + md[m.end():]
    sections = split_sections(md)

    toc = '<nav class="toc"><div class="sec">目錄</div>'
    body = ""
    for title, content in sections:
        if not title:
            continue
        sid = slugify_unicode(title, "-")
        items = re.findall(r"^### ([^\n]+)\n(.*?)(?=^### |\Z)", content, flags=re.M | re.S)
        toc += f'<div class="sec"><a href="#{sid}">{htmlmod.escape(title)}</a></div>'
        if items:
            toc += "<ol>" + "".join(f'<li><a href="#{slugify_unicode(t.strip(), "-")}">{htmlmod.escape(t.strip())}</a>'
                                  + ('<span class="hint">🔧 可加進工作流</span>' if 'class="callout tip"' in inner else "") + "</li>"
                                  for t, inner in items) + "</ol>"
        is_open = "" if title.startswith("附錄") else " open"
        lead_cls = ' class="lead"' if title.startswith("本週導讀") else ""
        body += (f'<details class="section" id="{sid}"{is_open}><summary><h2>{htmlmod.escape(title)}</h2>'
                 f'<span class="hint"></span></summary><div{lead_cls}>{render_section_body(content)}</div></details>')
    toc += "</nav>"

    title = fm.get("title", "AI 知識雷達")
    stats = f"共 {fm.get('item_count', '?')} 條"
    if fm.get("sources_failed") and fm["sources_failed"] not in ("[]", ""):
        stats += f"｜抓取失敗來源：{htmlmod.escape(fm['sources_failed'])}"
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{htmlmod.escape(title)}</title><style>{CSS}</style></head>
<body><div class="page" id="top">
<header class="masthead"><h1>{htmlmod.escape(title)}</h1>
<div class="period">{htmlmod.escape(period_line)}</div><div class="stats">{stats}</div></header>
{toc}
{body}
<div class="footer" id="bottom">由 AI 知識雷達自動產生 · 完整 Markdown 版在 Obsidian「AI知識雷達」資料夾</div>
</div>
<div class="fab"><a href="#top" title="回到頂端">↑</a><button type="button" popovertarget="tocpop" title="目錄">☰</button><a href="#bottom" title="到底端">↓</a></div>
<div id="tocpop" popover>{toc}</div>
<script>
document.querySelectorAll('#tocpop a').forEach(function (a) {{
  a.addEventListener('click', function () {{
    var t = document.getElementById(decodeURIComponent(a.hash.slice(1)));
    var d = t && (t.tagName === 'DETAILS' ? t : t.closest('details'));
    if (d) d.open = true;
    document.getElementById('tocpop').hidePopover();
  }});
}});
</script></body></html>"""


def build_digest(fm, body_md):
    sections = dict(split_sections(body_md))
    date = fm.get("date", "")
    ps, pe = fm.get("period_start", ""), fm.get("period_end", "")
    fmt = lambda d: d[5:].replace("-", "/") if d else ""
    out = [f"AI 知識雷達 {date}（涵蓋 {fmt(ps)}–{fmt(pe)}）",
           f"共 {fm.get('item_count', '?')} 條。完整版請開附件 HTML；Obsidian 的「AI知識雷達」資料夾也有 Markdown 版。", ""]

    def plain(s):
        s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
        s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        return s.strip()

    lead = sections.get("本週導讀", "").strip()
    if lead:
        out += ["【本週導讀】", plain(lead), ""]

    head = sections.get("頭版", "")
    if head:
        out.append("【頭版】")
        for n, (title, inner) in enumerate(re.findall(r"^### ([^\n]+)\n(.*?)(?=^### |\Z)", head, flags=re.M | re.S), 1):
            one = re.search(r"^\*\*一句話\*\*\s*(.+)$", inner, flags=re.M)
            out.append(f"{n}. {plain(title)}")
            if one:
                out.append(f"   {plain(one.group(1))}")
        out.append("")

    for sec in ("論文版", "產業與產品版", "開源與工具版", "GitHub AI Agent 週榜", "社群熱議版"):
        content = sections.get(sec, "")
        groups = [(r, re.findall(r"^### (.+)$", md, flags=re.M)) for r, md in split_regions(content)]
        groups = [(r, ts) for r, ts in groups if ts]
        if groups:
            out.append(f"【{sec}】" + "；".join((f"{r}：" if r else "") + "、".join(plain(t) for t in ts)
                                               for r, ts in groups))
    out.append("")

    follow = sections.get("本週值得跟進", "").strip()
    if follow:
        out += ["【本週值得跟進】"]
        for l in follow.splitlines():
            if l.strip().startswith("- "):
                out.append("- " + plain(l.strip()[2:]))
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--images-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--digest", required=True)
    a = ap.parse_args()
    text = open(os.path.expanduser(a.report), encoding="utf-8").read()
    fm, body = read_frontmatter(text)
    html = build_html(fm, body, os.path.expanduser(a.images_dir))
    open(os.path.expanduser(a.out), "w", encoding="utf-8").write(html)
    open(os.path.expanduser(a.digest), "w", encoding="utf-8").write(build_digest(fm, body))
    print(f"html: {a.out} ({len(html)//1024} KB)\ndigest: {a.digest}")


if __name__ == "__main__":
    main()
