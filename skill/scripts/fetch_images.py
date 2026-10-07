#!/usr/bin/env python3
"""為週報挑選出的每一條抓一張「有資訊量」的原文圖片（論文架構圖、文章主圖、專案 demo 圖）。

用法:
    fetch_images.py --run-dir ~/.local/state/ai-radar/runs/2026-09-07 --date 2026-09-07 \
                    --out-dir ~/Documents/Obsidian/AI知識雷達/attachments

輸出 <run-dir>/images.json: {"<候選索引>": {"file": "檔名", "image_url": ..., "page_url": ..., "width": w, "height": h}}
圖片存到 <out-dir>/<date>-<idx>-<slug>.<ext>。只用標準庫 + macOS sips。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

UA = "ai-radar/0.1 (personal research bot; contact: dk40913@gmail.com)"
TIMEOUT = 25
MIN_WIDTH = 400          # 比這窄的多半是 icon / 頭像
MAX_WIDTH = 1200         # 存檔前縮到這個寬度以內
SKIP_URL_WORDS = ("logo", "favicon", "avatar", "icon", "badge", "shields.io", "gradient.png",
                  "social-thumbnails", "opengraph.githubassets", "spacer", "pixel", "tracking")
RASTER_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def http_get(url, headers=None, binary=False):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
        return (data, r.geturl(), r.headers.get("Content-Type", "")) if binary else (data.decode("utf-8", "replace"), r.geturl())


def looks_generic(url):
    u = url.lower()
    return any(w in u for w in SKIP_URL_WORDS) or u.endswith(".svg")


def meta_image(html, page_url):
    """og:image / twitter:image，屬性順序不限。"""
    for prop in ("og:image", "twitter:image", "og:image:secure_url"):
        for m in re.finditer(r"<meta\s+[^>]*>", html, re.I):
            tag = m.group(0)
            if re.search(rf'(property|name)\s*=\s*["\']{re.escape(prop)}["\']', tag, re.I):
                c = re.search(r'content\s*=\s*["\']([^"\']+)["\']', tag, re.I)
                if c:
                    return urllib.parse.urljoin(page_url, c.group(1))
    return None


def first_body_image(html, page_url):
    for m in re.finditer(r"<img\s+[^>]*src\s*=\s*[\"']([^\"']+)[\"'][^>]*>", html, re.I):
        src = urllib.parse.urljoin(page_url, m.group(1))
        if src.startswith("http") and not looks_generic(src) and src.lower().split("?")[0].endswith(RASTER_EXT):
            return src
    return None


def arxiv_id_from(url):
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url or "")
    return m.group(1) if m else None


def candidates_arxiv(aid):
    """arXiv HTML 版的第一張 figure。"""
    page = f"https://arxiv.org/html/{aid}"
    try:
        html, final = http_get(page)
    except Exception:  # noqa: BLE001
        return []
    urls = []
    for fig in re.finditer(r"<figure[^>]*>(.*?)</figure>", html, re.S | re.I):
        m = re.search(r"<img[^>]*src\s*=\s*[\"']([^\"']+)[\"']", fig.group(1), re.I)
        if m:
            # src 形如 "2609.04199v1/figures/x.png"，相對於 /html/ 這一層
            urls.append(urllib.parse.urljoin(final, m.group(1)))
    return urls[:3]


def candidates_github(repo_url):
    m = re.search(r"github\.com/([^/]+/[^/#?]+)", repo_url)
    if not m:
        return []
    repo = m.group(1)
    urls = []
    try:
        readme, _ = http_get(f"https://api.github.com/repos/{repo}/readme",
                             {"Accept": "application/vnd.github.raw"})
        for mm in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)|<img[^>]*src\s*=\s*[\"']([^\"']+)[\"']", readme, re.I):
            src = mm.group(1) or mm.group(2)
            if not src.startswith("http"):
                src = f"https://raw.githubusercontent.com/{repo}/HEAD/{src.lstrip('./')}"
            if not looks_generic(src) and src.lower().split("?")[0].endswith(RASTER_EXT):
                urls.append(src)
        # 也接受 github.com/user-attachments 這種沒有副檔名的圖
        for mm in re.finditer(r"\((https://github\.com/user-attachments/assets/[^)\s]+)\)", readme):
            urls.append(mm.group(1))
    except Exception:  # noqa: BLE001
        pass
    return urls[:3]


def candidates_page(url):
    try:
        html, final = http_get(url)
    except Exception:  # noqa: BLE001
        return []
    urls = []
    og = meta_image(html, final)
    if og and not looks_generic(og):
        urls.append(og)
    body = first_body_image(html, final)
    if body and body not in urls:
        urls.append(body)
    return urls


def candidates_reddit(item, reddit_feed):
    """Reddit RSS 的 content 裡有 preview.redd.it 縮圖；feed 只抓一次給整個 run 共用。"""
    if not reddit_feed:
        return []
    key = item["url"].rstrip("/")
    block = reddit_feed.get(key)
    if not block:
        return []
    urls = re.findall(r"src=&quot;(https://(?:preview|i)\.redd\.it/[^&]+)&quot;", block)
    urls = [u.replace("&amp;", "&") for u in urls]
    return urls[:2]


def load_reddit_feed(subs):
    try:
        text, _ = http_get(f"https://www.reddit.com/r/{'+'.join(subs)}/top/.rss?t=week&limit=100")
    except Exception:  # noqa: BLE001
        return {}
    feed = {}
    for entry in re.findall(r"<entry>(.*?)</entry>", text, re.S):
        link = re.search(r'<link href="([^"]+)"', entry)
        if link:
            feed[link.group(1).rstrip("/")] = entry
    return feed


def image_candidates(item, reddit_feed):
    src = item["source"]
    urls = []
    if src in ("arxiv", "hf_papers"):
        aid = arxiv_id_from(item.get("extra", {}).get("arxiv_url") or item["url"])
        if aid:
            urls += candidates_arxiv(aid)
    elif src == "github":
        urls += candidates_github(item["url"])
    elif src == "reddit":
        urls += candidates_reddit(item, reddit_feed)
    else:  # hackernews / news
        urls += candidates_page(item["url"])
    # 合併進來的其他來源也試
    for also in item.get("also", []):
        if also.get("source") in ("hackernews", "news") and also["url"] != item["url"]:
            urls += candidates_page(also["url"])
        elif also.get("source") in ("arxiv", "hf_papers"):
            aid = arxiv_id_from(also.get("extra", {}).get("arxiv_url") or also["url"])
            if aid:
                urls += candidates_arxiv(aid)
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def sips_dims(path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                       capture_output=True, text=True)
    w = re.search(r"pixelWidth:\s*(\d+)", r.stdout)
    h = re.search(r"pixelHeight:\s*(\d+)", r.stdout)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def slugify(title):
    s = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
    return s[:40] or "img"


def download(url, dest_base):
    data, final, ctype = http_get(url, binary=True)
    if len(data) < 5_000:
        return None
    ext = None
    for e in RASTER_EXT:
        if final.lower().split("?")[0].endswith(e):
            ext = e
            break
    if not ext:
        ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}.get(ctype.split(";")[0].strip())
    if not ext:
        return None
    tmp = dest_base + ext
    with open(tmp, "wb") as f:
        f.write(data)
    w, h = sips_dims(tmp)
    if w < MIN_WIDTH or h < 150 or w > 8 * h:
        os.remove(tmp)
        return None
    # 統一轉成 png/jpg，縮到 MAX_WIDTH 內；webp/gif 轉 jpg 避免 Obsidian 與郵件相容問題
    out_ext = ".jpg" if ext in (".jpg", ".jpeg", ".webp", ".gif") else ".png"
    final_path = dest_base + out_ext
    fmt = "jpeg" if out_ext == ".jpg" else "png"
    r = subprocess.run(["sips", "-s", "format", fmt, "-Z", str(MAX_WIDTH), tmp, "--out", final_path],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(final_path):
        os.remove(tmp)
        return None
    if tmp != final_path:
        os.remove(tmp)
    w, h = sips_dims(final_path)
    return {"file": os.path.basename(final_path), "image_url": url, "width": w, "height": h}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    run = os.path.expanduser(args.run_dir)
    out_dir = os.path.expanduser(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    items = json.load(open(f"{run}/candidates.json", encoding="utf-8"))["items"]
    sel = json.load(open(f"{run}/selection.json", encoding="utf-8"))
    merged = sel.get("merged", {})
    chosen = [i for idxs in sel["sections"].values() for i in idxs]
    reddit_feed = None
    if any(items[i]["source"] == "reddit" for i in chosen):
        reddit_feed = load_reddit_feed(["LocalLLaMA", "MachineLearning", "artificial"])

    results = {}
    for i in chosen:
        it = dict(items[i])
        it["also"] = [items[j] for j in merged.get(str(i), []) if j != i]
        got = None
        for url in image_candidates(it, reddit_feed):
            try:
                got = download(url, f"{out_dir}/{args.date}-{i}-{slugify(it['title'])}")
            except Exception:  # noqa: BLE001
                got = None
            if got:
                break
            time.sleep(0.3)
        if got:
            got["page_url"] = it["url"]
            results[str(i)] = got
            print(f"[img ] {i:<4} {got['width']}x{got['height']} {got['file']}", file=sys.stderr)
        else:
            print(f"[none] {i:<4} {it['source']:<10} {it['title'][:60]}", file=sys.stderr)
        time.sleep(0.5)

    json.dump(results, open(f"{run}/images.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"images: {len(results)}/{len(chosen)} -> {run}/images.json", file=sys.stderr)


if __name__ == "__main__":
    main()
