#!/usr/bin/env python3
"""AI 知識雷達抓取腳本。只用標準庫。

用法:
    fetch_sources.py --since 2026-09-01T01:00:00Z [--until ...] [--out candidates.json]

輸出 JSON:
    {"meta": {since, until, counts: {source: n}, failed: {source: error}}, "items": [...]}
每筆 item:
    {source, title, url, published_at, score, score_kind, summary, extra}
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

UA = "ai-radar/0.1 (personal research bot)"
TIMEOUT = 30

# arXiv 一週新投稿有兩千多篇，只留命中關鍵字的；config 的 arxiv_keywords 非空時改用它
ARXIV_KEYWORDS = [
    "agent", "llm", "large language model", "language model", "rag", "retrieval-augmented",
    "retrieval augmented", "tool use", "tool-use", "tool calling", "function calling",
    "quantiz", "mixture of experts", "mixture-of-experts", "kv cache", "kv-cache",
    "speculative decoding", "long context", "long-context", "context window",
    "code generation", "model context protocol", "reasoning model", "chain-of-thought",
    "chain of thought", "test-time", "inference-time", "instruction tuning",
]
ARXIV_MAX_ITEMS = 200
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

HN_QUERIES = ["AI", "LLM", "GPT", "Claude", "Gemini", "OpenAI", "Anthropic",
              "agent", "language model", "open source model"]
HN_MIN_POINTS = 50
HN_TITLE_RE = re.compile(
    r"\b(ai|llm|llms|gpt|gpt-\d|claude|gemini|openai|anthropic|deepmind|model|models|agent|agents|"
    r"nvidia|hugging ?face|transformer|neural|copilot|chatbot|machine learning|deep learning|"
    r"inference|diffusion|mistral|llama|qwen|deepseek|grok|cursor|codex|mcp|rag|fine-?tun\w*|"
    r"embedding|token|tokens|prompt|benchmark|robot|autonomous)\b", re.I)

REDDIT_SUBS = ["LocalLLaMA", "MachineLearning", "artificial"]

RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Meta Newsroom": "https://about.fb.com/feed/",
}

GITHUB_SEARCH_TOPICS = ["llm", "ai-agent", "agents", "rag", "mcp", "llm-inference"]
GITHUB_MIN_STARS = 50

# 全語言的 trending 頁只有 20 多個 repo，agent 工具多半被擠掉，要逐語言抓
GITHUB_TRENDING_LANGS = ["", "python", "typescript", "javascript", "go", "rust", "shell",
                         "unknown", "jupyter-notebook"]
GITHUB_AGENT_RE = re.compile(
    r"\b(agents?|agentic|subagents?|skills?|mcp|claude|codex|cursor|copilot|gemini|llms?|"
    r"harness|rag|prompts?|ai)\b", re.I)
GITHUB_AGENT_MAX_ITEMS = 20


# 台灣、簡中來源。各站一頁只有一兩天的量，要翻頁或用 API 的時間條件抓滿一週
TAIPEI = timezone(timedelta(hours=8))
ITHOME_MAX_PAGES = 15          # 全站新聞一頁 12 則、約一天一頁
TECHNEWS_AI_CATEGORY = 19819   # technews.tw「AI 人工智慧」分類
PTT_BOARDS = ["Soft_Job", "AI"]
PTT_MAX_PAGES = 10
JUEJIN_AI_CATE = "6809637773935378440"
JUEJIN_MAX_PAGES = 10
CN_COMMUNITY_MAX_ITEMS = 60
V2EX_NODES = ["openai", "claude"]
ITHELP_MAX_PAGES = 5           # iT邦幫忙 AI 標籤，一頁約一週內的文章
CN_NEWS_FEEDS = {"雷锋网": "https://www.leiphone.com/feed", "36氪": "https://www.36kr.com/feed"}
CSDN_HOT_MAX_ITEMS = 25

# 英文部落格平台。Medium 本站擋爬蟲（Cloudflare 403、會員牆），只有出版物 RSS 附全文，
# 而且每個 feed 只給最新 10 篇，所以是執行當下的快照，不是整週
MEDIUM_FEEDS = {
    "Towards AI": "https://pub.towardsai.net/feed",
    "AI Advances": "https://ai.gopubby.com/feed",
    "Generative AI": "https://generativeai.pub/feed",
    "Data Science Collective": "https://medium.com/feed/data-science-collective",
}
DEVTO_TAGS = ["ai", "llm", "agents", "mcp"]
DEVTO_MIN_REACTIONS = 10
BLOG_FEEDS = {
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
}
CONTENT_LIMIT = 8000           # 原文頁讀不到的來源，把 feed 全文存進 extra.content 給撰稿用

# 英文詞要前後不是英文字母，避免 Email、Firefox 這種誤判
_ZH_AI_LATIN = ["AI", "AGI", "LLM", "LLMs", "GPT", "ChatGPT", "Claude", "Gemini", "OpenAI", "Anthropic",
                "DeepSeek", "Qwen", "Kimi", "GLM", "Llama", "Mistral", "Agent", "Agents", "MCP", "RAG",
                "Copilot", "Cursor", "Codex", "NVIDIA", "Nvidia", "Hugging Face", "Transformer", "Token"]
_ZH_AI_CJK = ["人工智慧", "人工智能", "生成式", "大模型", "語言模型", "语言模型", "智能體", "智能体", "代理人",
              "機器學習", "机器学习", "深度學習", "深度学习", "神經網路", "神经网络", "輝達", "英伟达",
              "通義", "通义", "千問", "千问", "文心", "豆包", "智譜", "智谱", "算力", "微調", "微调",
              "提示詞", "提示词", "向量資料庫", "向量数据库", "多模態", "多模态", "推理模型"]
ZH_AI_RE = re.compile("(?<![A-Za-z])(?:" + "|".join(re.escape(w) for w in _ZH_AI_LATIN) + ")(?![A-Za-z])|"
                      + "|".join(_ZH_AI_CJK), re.I)


def zh_ai(text):
    return bool(ZH_AI_RE.search(text or ""))


# ---------- 工具 ----------

def http_get(url, headers=None, retries=2):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def http_json(url, headers=None):
    return json.loads(http_get(url, headers))


def to_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso(s):
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return to_utc(datetime.fromisoformat(s))


def parse_any_date(s):
    """RSS 各家日期格式不一，能解就解。"""
    s = s.strip()
    try:
        return parse_iso(s)
    except ValueError:
        pass
    try:
        return to_utc(parsedate_to_datetime(s))
    except Exception:  # noqa: BLE001
        pass
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S %z"):
        try:
            return to_utc(datetime.strptime(" ".join(s.split()), fmt))
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {s!r}")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_html(s, limit=500):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def item(source, title, url, published_at, score, score_kind, summary, **extra):
    return {
        "source": source,
        "title": strip_html(title, 300),
        "url": url,
        "published_at": iso(published_at),
        "score": score,
        "score_kind": score_kind,
        "summary": strip_html(summary, 500),
        "extra": extra,
    }


# ---------- 各來源 ----------

def arxiv_keywords():
    """config 的 arxiv_keywords 非空就用它（轉小寫），否則（含 config 不存在或壞掉）用內建清單。"""
    try:
        kws = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("arxiv_keywords")
        kws = [k.strip().lower() for k in kws if isinstance(k, str) and k.strip()]
    except (OSError, ValueError, AttributeError, TypeError):
        return ARXIV_KEYWORDS
    return kws or ARXIV_KEYWORDS


def _arxiv_relevance(title, summary, keywords):
    """標題命中權重 3、摘要命中權重 1，回傳 (分數, 命中關鍵字)。"""
    t, a = title.lower(), summary.lower()
    hits = [k for k in keywords if k in t or k in a]
    score = sum(3 if k in t else 1 for k in hits)
    return score, hits


def fetch_arxiv(since, until):
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out, start, page = [], 0, 200
    keywords = arxiv_keywords()
    while start < 4000:  # 一週 cs.AI/CL/LG 約 2500 篇，保險上限
        q = urllib.parse.urlencode({
            "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "sortBy": "submittedDate", "sortOrder": "descending",
            "start": start, "max_results": page,
        })
        root = ET.fromstring(http_get(f"https://export.arxiv.org/api/query?{q}"))
        entries = root.findall("a:entry", ns)
        if not entries:
            break
        reached_since = False
        for e in entries:
            pub = parse_iso(e.findtext("a:published", "", ns))
            if pub < since:
                reached_since = True
                break
            if pub > until:
                continue
            title = e.findtext("a:title", "", ns)
            summary = e.findtext("a:summary", "", ns)
            score, hits = _arxiv_relevance(title, summary, keywords)
            if score == 0:
                continue
            authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
            cats = [c.get("term") for c in e.findall("a:category", ns)]
            out.append(item("arxiv", title, e.findtext("a:id", "", ns).strip(), pub,
                            score, "keyword_hits", summary, authors=authors[:6],
                            categories=cats, keywords=hits))
        if reached_since:
            break
        start += page
        time.sleep(3)  # arXiv API 禮貌間隔
    out.sort(key=lambda x: (-x["score"], x["published_at"]))
    return out[:ARXIV_MAX_ITEMS]


def fetch_hf_papers(since, until):
    out, seen = [], set()
    day = since.date()
    failed = []
    while day <= until.date():
        # HF 不接受還沒開放的日期（回 400），單日失敗跳過，全部失敗才算來源失敗
        try:
            data = http_json(f"https://huggingface.co/api/daily_papers?date={day.isoformat()}")
        except RuntimeError as e:
            failed.append(str(e))
            day += timedelta(days=1)
            continue
        for d in data:
            p = d.get("paper", {})
            pid = p.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            pub_s = d.get("publishedAt") or p.get("submittedOnDailyAt") or p.get("publishedAt")
            pub = parse_iso(pub_s) if pub_s else datetime.combine(day, datetime.min.time(), timezone.utc)
            if pub < since or pub > until:
                continue
            out.append(item(
                "hf_papers", p.get("title") or d.get("title", ""),
                f"https://huggingface.co/papers/{pid}", pub,
                int(p.get("upvotes") or 0), "upvotes",
                p.get("ai_summary") or p.get("summary") or d.get("summary", ""),
                arxiv_url=f"https://arxiv.org/abs/{pid}",
                authors=[a.get("name") for a in (p.get("authors") or [])[:6] if isinstance(a, dict)],
                github_repo=p.get("githubRepo"), github_stars=p.get("githubStars"),
                keywords=p.get("ai_keywords"), comments=d.get("numComments"),
            ))
        day += timedelta(days=1)
        time.sleep(0.5)
    if failed and not out and len(failed) == (until.date() - since.date()).days + 1:
        raise RuntimeError(failed[-1])
    return out


def fetch_hackernews(since, until):
    out, seen = [], set()
    since_ts, until_ts = int(since.timestamp()), int(until.timestamp())
    for query in HN_QUERIES:
        page = 0
        while page < 5:
            q = urllib.parse.urlencode({
                "query": query, "tags": "story", "hitsPerPage": 100, "page": page,
                "numericFilters": f"created_at_i>{since_ts},created_at_i<{until_ts},points>{HN_MIN_POINTS}",
            })
            data = http_json(f"https://hn.algolia.com/api/v1/search_by_date?{q}")
            hits = data.get("hits", [])
            for h in hits:
                oid = h.get("objectID")
                if oid in seen:
                    continue
                seen.add(oid)
                if not HN_TITLE_RE.search(h.get("title") or ""):
                    continue
                hn_url = f"https://news.ycombinator.com/item?id={oid}"
                out.append(item(
                    "hackernews", h.get("title", ""), h.get("url") or hn_url,
                    datetime.fromtimestamp(h["created_at_i"], timezone.utc),
                    int(h.get("points") or 0), "points",
                    h.get("story_text") or "",
                    comments_url=hn_url, num_comments=h.get("num_comments"),
                    matched_query=query,
                ))
            if page + 1 >= data.get("nbPages", 0):
                break
            page += 1
        time.sleep(0.3)
    return out


def fetch_reddit(since, until):
    """三個子版用 multireddit 語法合併成一個請求；未登入時第二個請求就會被 429。"""
    ns = {"a": "http://www.w3.org/2005/Atom"}
    subs = "+".join(REDDIT_SUBS)
    url = f"https://www.reddit.com/r/{subs}/top/.rss?t=week&limit=100"
    try:
        text = http_get(url, retries=0)
    except RuntimeError as e:
        if "429" not in str(e):
            raise
        time.sleep(60)  # 限流窗口以分鐘計，短間隔重試只會更糟
        text = http_get(url, retries=0)
    root = ET.fromstring(text)
    out = []
    for rank, e in enumerate(root.findall("a:entry", ns)):
        pub = parse_iso(e.findtext("a:published", "", ns) or e.findtext("a:updated", "", ns))
        if pub < since or pub > until:
            continue
        link = e.find("a:link", ns)
        cat = e.find("a:category", ns)
        # RSS 不帶票數，用週榜名次反推熱度
        out.append(item(
            "reddit", e.findtext("a:title", "", ns), link.get("href") if link is not None else "",
            pub, max(0, 100 - rank), "rank", e.findtext("a:content", "", ns),
            subreddit=cat.get("term") if cat is not None else None, rank=rank + 1,
            author=e.findtext("a:author/a:name", "", ns),
        ))
    return out


def _parse_rss(text, publisher):
    root = ET.fromstring(text)
    out = []
    # RSS 2.0
    for it in root.iter("item"):
        title = it.findtext("title", "")
        link = it.findtext("link", "") or ""
        date = it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")
        desc = it.findtext("description", "") or it.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
        if not date:
            continue
        out.append((title, link.strip(), parse_any_date(date), desc))
    # Atom
    ans = "{http://www.w3.org/2005/Atom}"
    for e in root.iter(f"{ans}entry"):
        title = e.findtext(f"{ans}title", "")
        link_el = e.find(f"{ans}link")
        link = link_el.get("href", "") if link_el is not None else ""
        date = e.findtext(f"{ans}published") or e.findtext(f"{ans}updated")
        desc = e.findtext(f"{ans}summary", "") or e.findtext(f"{ans}content", "")
        if not date:
            continue
        out.append((title, link, parse_any_date(date), desc))
    return [(t, l, d, s, publisher) for t, l, d, s in out]


def _parse_anthropic_news(text):
    """Anthropic 沒有 RSS，從 /news 列表的每個 <a href="/news/slug"> 區塊抓 <time> 與 class 含 title 的元素。"""
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]*href="(/news/[^"]+)"[^>]*>(.*?)</a>', text, re.S):
        path, inner = m.groups()
        if path in seen:
            continue
        time_m = re.search(r'<time[^>]*>([^<]+)</time>', inner)
        title_m = re.search(r'<[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)<', inner)
        if not time_m or not title_m:
            continue
        try:
            d = parse_any_date(time_m.group(1))
        except ValueError:
            continue
        seen.add(path)
        body_m = re.search(r'<p[^>]*class="[^"]*body[^"]*"[^>]*>(.*?)</p>', inner, re.S)
        out.append((title_m.group(1), f"https://www.anthropic.com{path}", d,
                    body_m.group(1) if body_m else "", "Anthropic"))
    return out


def fetch_news(since, until):
    out = []
    errors = []
    for publisher, url in RSS_FEEDS.items():
        try:
            rows = _parse_rss(http_get(url), publisher)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{publisher}: {e}")
            continue
        for title, link, pub, desc, pubr in rows:
            if since <= pub <= until:
                out.append(item("news", title, link, pub, 0, "none", desc, publisher=pubr))
    try:
        for title, link, pub, desc, pubr in _parse_anthropic_news(http_get("https://www.anthropic.com/news")):
            if since <= pub <= until:
                out.append(item("news", title, link, pub, 0, "none", desc, publisher=pubr))
    except Exception as e:  # noqa: BLE001
        errors.append(f"Anthropic: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    if errors:
        # 部分失敗：夾帶在第一筆 extra 讓 meta 看得到
        out[0]["extra"]["partial_failures"] = errors
    return out


def _parse_github_trending(text):
    out = []
    blocks = text.split('<article class="Box-row">')[1:]
    for b in blocks:
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"', b)
        if not m:
            continue
        repo = m.group(1)
        desc_m = re.search(r'<p class="col-9[^"]*">(.*?)</p>', b, re.S)
        lang_m = re.search(r'itemprop="programmingLanguage">([^<]*)<', b)
        stars_m = re.search(r'([\d,]+)\s+stars this week', b)
        total_m = re.search(r'href="/' + re.escape(repo) + r'/stargazers"[^>]*>(.*?)</a>', b, re.S)
        weekly = int(stars_m.group(1).replace(",", "")) if stars_m else 0
        total = int(re.sub(r"[^\d]", "", strip_html(total_m.group(1))) or 0) if total_m else None
        out.append((repo, strip_html(desc_m.group(1)) if desc_m else "",
                    lang_m.group(1).strip() if lang_m else None, weekly, total))
    return out


def fetch_github(since, until):
    out, seen = [], set()
    ai_words = ["llm", "agent", "ai", "gpt", "claude", "model", "rag", "mcp", "inference",
                "transformer", "diffusion", "ml", "neural", "embedding", "vector", "prompt", "openai"]
    for repo, desc, lang, weekly, total in _parse_github_trending(http_get("https://github.com/trending?since=weekly")):
        text = f"{repo} {desc}".lower()
        if not any(re.search(rf"\b{w}\b", text) for w in ai_words):
            continue
        seen.add(repo.lower())
        out.append(item("github", repo, f"https://github.com/{repo}", until, weekly, "stars_this_week",
                        desc, language=lang, total_stars=total, via="trending"))
    since_day = since.strftime("%Y-%m-%d")
    for topic in GITHUB_SEARCH_TOPICS:
        q = urllib.parse.urlencode({
            "q": f"topic:{topic} created:>{since_day} stars:>{GITHUB_MIN_STARS}",
            "sort": "stars", "order": "desc", "per_page": 30,
        })
        try:
            data = http_json(f"https://api.github.com/search/repositories?{q}",
                             {"Accept": "application/vnd.github+json"})
        except Exception:  # noqa: BLE001
            continue  # search API 有 rate limit，失敗就跳過該 topic
        for r in data.get("items", []):
            name = r["full_name"]
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            out.append(item("github", name, r["html_url"], parse_iso(r["created_at"]),
                            int(r.get("stargazers_count") or 0), "stars",
                            r.get("description") or "", language=r.get("language"),
                            topics=r.get("topics"), via=f"search:{topic}"))
        time.sleep(1)
    return out


def fetch_github_agents(since, until):
    """「GitHub AI Agent 週榜」的候選：各語言 weekly trending 合併，依本週新增星數排序。
    正則只做粗篩，是不是 agent 工具由選稿步驟判斷，所以多留一些。"""
    repos = {}
    for lang in GITHUB_TRENDING_LANGS:
        url = f"https://github.com/trending/{lang}?since=weekly" if lang else "https://github.com/trending?since=weekly"
        for repo, desc, language, weekly, total in _parse_github_trending(http_get(url)):
            if GITHUB_AGENT_RE.search(f"{repo.replace('-', ' ').replace('_', ' ')} {desc}"):
                repos[repo.lower()] = (repo, desc, language, weekly, total)
        time.sleep(1)
    ranked = sorted(repos.values(), key=lambda r: -r[3])[:GITHUB_AGENT_MAX_ITEMS]
    return [item("github", repo, f"https://github.com/{repo}", until, weekly, "stars_this_week",
                 desc, language=language, total_stars=total, via="agent-trending")
            for repo, desc, language, weekly, total in ranked]



# ---------- 台灣、簡中來源 ----------

def _parse_ithome_list(text):
    """iThome 新聞列表頁：每則 <p class="title"> 連結、<div class="summary">、<p class="post-at">日期。"""
    out = []
    for m in re.finditer(r'<p class="title"><a href="(/news/\d+)">(.*?)</a>.*?'
                         r'<div class="summary">(.*?)</div>.*?<p class="post-at">\s*(\d{4}-\d{2}-\d{2})', text, re.S):
        path, title, summary, day = m.groups()
        d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=TAIPEI)
        out.append((strip_html(title), f"https://www.ithome.com.tw{path}", to_utc(d), strip_html(summary)))
    return out


def _wp_posts(base, since, until, extra_query="", max_pages=3):
    """WordPress REST API，用 after/before 直接抓時間窗內的文章。"""
    out = []
    for page in range(1, max_pages + 1):
        q = f"per_page=100&page={page}&after={iso(since)}&before={iso(until)}{extra_query}"
        try:
            data = http_json(f"{base}/wp-json/wp/v2/posts?{q}")
        except RuntimeError:
            if page == 1:
                raise
            break  # 超過最後一頁時 WordPress 回 400
        for p in data:
            out.append((p["title"]["rendered"], p["link"], parse_iso(p["date_gmt"] + "Z"),
                        p.get("excerpt", {}).get("rendered", "")))
        if len(data) < 100:
            break
    return out


def fetch_tw_news(since, until):
    """iThome 全站新聞用標題關鍵字篩 AI；TechNews 直接抓 AI 分類。兩站都沒有熱度數字。"""
    out, errors, seen = [], [], set()
    try:
        for page in range(ITHOME_MAX_PAGES):
            rows = _parse_ithome_list(http_get(f"https://www.ithome.com.tw/news?page={page}"))
            if not rows:
                break
            for title, url, pub, summary in rows:
                # 列表只有日期，用台北日期比對時間窗
                if url in seen or not (since.astimezone(TAIPEI).date() <= pub.astimezone(TAIPEI).date() <= until.astimezone(TAIPEI).date()):
                    continue
                if zh_ai(f"{title} {summary}"):
                    seen.add(url)
                    out.append(item("tw_news", title, url, max(pub, since), 0, "none", summary, publisher="iThome"))
            if min(r[2] for r in rows).astimezone(TAIPEI).date() < since.astimezone(TAIPEI).date():
                break
            time.sleep(1)
    except Exception as e:  # noqa: BLE001
        errors.append(f"iThome: {e}")
    try:
        for title, url, pub, summary in _wp_posts("https://technews.tw", since, until,
                                                  f"&categories={TECHNEWS_AI_CATEGORY}"):
            out.append(item("tw_news", title, url, pub, 0, "none", summary, publisher="TechNews"))
    except Exception as e:  # noqa: BLE001
        errors.append(f"TechNews: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    if errors:
        out[0]["extra"]["partial_failures"] = errors
    return out


def _parse_ptt_index(text, until):
    """PTT 看板列表頁，回傳 ([(標題, URL, 日期, 推文數)], 上一頁路徑)。列表日期沒有年份，用 until 推回。"""
    rows = []
    for block in text.split('<div class="r-ent">')[1:]:
        link = re.search(r'<div class="title">\s*<a href="(/bbs/[^"]+\.html)">(.*?)</a>', block, re.S)
        date = re.search(r'<div class="date">\s*(\d{1,2})/(\d{1,2})</div>', block)
        if not link or not date:
            continue  # 已刪除的文章沒有連結
        nrec = re.search(r'<div class="nrec">(?:<span[^>]*>([^<]*)</span>)?</div>', block)
        n = (nrec.group(1) or "") if nrec else ""
        pushes = 100 if n == "爆" else int(n) if n.isdigit() else 0
        month, day = int(date.group(1)), int(date.group(2))
        year = until.astimezone(TAIPEI).year
        if (month, day) > (until.astimezone(TAIPEI).month, until.astimezone(TAIPEI).day + 1):
            year -= 1
        d = datetime(year, month, day, tzinfo=TAIPEI)
        rows.append((html.unescape(link.group(2)).strip(), "https://www.ptt.cc" + link.group(1), to_utc(d), pushes))
    prev = re.search(r'href="(/bbs/[^"]+/index\d+\.html)">&lsaquo; 上頁', text)
    return rows, prev.group(1) if prev else None


def fetch_tw_community(since, until):
    """PTT Soft_Job（標題篩 AI）與 AI 板往回翻頁到時間窗起點，分數是推文數；iT邦幫忙 AI 標籤，分數是 Like 數。"""
    out = []
    since_day = since.astimezone(TAIPEI).date()
    for board in PTT_BOARDS:
        path = f"/bbs/{board}/index.html"
        for _ in range(PTT_MAX_PAGES):
            rows, prev = _parse_ptt_index(http_get("https://www.ptt.cc" + path), until)
            for title, url, pub, pushes in rows:
                if pub.astimezone(TAIPEI).date() < since_day or title.startswith(("[公告]", "Fw: [公告]")):
                    continue
                if board == "AI" or zh_ai(title):
                    out.append(item("tw_community", title, url, max(pub, since), pushes, "pushes", "", board=f"PTT {board}"))
            if not prev or (rows and min(r[2] for r in rows).astimezone(TAIPEI).date() < since_day):
                break
            path = prev
            time.sleep(1)
    for page in range(1, ITHELP_MAX_PAGES + 1):
        rows = _parse_ithelp_tag(http_get(f"https://ithelp.ithome.com.tw/tags/articles/AI?page={page}"))
        for title, url, pub, desc, likes, views in rows:
            if since <= pub <= until:
                out.append(item("tw_community", title, url, pub, likes, "likes", desc, board="iT邦幫忙", views=views))
        if not rows or min(r[2] for r in rows) < since:
            break
        time.sleep(1)
    return out


def fetch_cn_news(since, until):
    """量子位（整站都是 AI）用 WordPress API；雷锋网、36氪 RSS 用關鍵字篩 AI，36氪原文頁讀不全，全文存 extra.content。
    開源中國的 RSS 只有兩百字摘要、內文頁要跑 JS，讀不到原文所以不收。"""
    out, errors = [], []
    try:
        for title, url, pub, summary in _wp_posts("https://www.qbitai.com", since, until):
            out.append(item("cn_news", title, url, pub, 0, "none", summary, publisher="量子位"))
    except Exception as e:  # noqa: BLE001
        errors.append(f"量子位: {e}")
    for name, url in CN_NEWS_FEEDS.items():
        try:
            for title, link, pub, body in _feed_entries(http_get(url)):
                if since <= pub <= until and zh_ai(f"{title} {strip_html(body, 300)}"):
                    out.append(item("cn_news", title, link.split("?")[0], pub, 0, "none", body, publisher=name,
                                    content=strip_html(body, CONTENT_LIMIT)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    if errors:
        out[0]["extra"]["partial_failures"] = errors
    return out


def fetch_cn_community(since, until):
    """掘金「人工智能」分類（依點讚數取前段）、CSDN 人工智能熱榜、V2EX openai／claude 節點。"""
    out, errors = [], []
    try:
        juejin, cursor = [], "0"
        for _ in range(JUEJIN_MAX_PAGES):
            req = urllib.request.Request(
                "https://api.juejin.cn/recommend_api/v1/article/recommend_cate_feed",
                data=json.dumps({"id_type": 2, "sort_type": 300, "cate_id": JUEJIN_AI_CATE,
                                 "cursor": cursor, "limit": 20}).encode(),
                headers={"User-Agent": UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
            rows = data.get("data") or []
            oldest = until
            for x in rows:
                a = x.get("article_info", {})
                pub = datetime.fromtimestamp(int(a.get("ctime", 0)), timezone.utc)
                oldest = min(oldest, pub)
                if since <= pub <= until:
                    juejin.append(item("cn_community", a.get("title", ""), f"https://juejin.cn/post/{a.get('article_id')}",
                                       pub, int(a.get("digg_count") or 0), "likes", a.get("brief_content", ""),
                                       board="掘金", views=a.get("view_count"), comments=a.get("comment_count")))
            if not data.get("has_more") or oldest < since:
                break
            cursor = data.get("cursor")
            time.sleep(1)
        juejin.sort(key=lambda x: -x["score"])
        out += juejin[:CN_COMMUNITY_MAX_ITEMS]
    except Exception as e:  # noqa: BLE001
        errors.append(f"掘金: {e}")
    try:
        # CSDN「人工智能」熱榜是當下快照、沒有發文時間，時間記為 until
        data = http_json("https://blog.csdn.net/phoenix/web/blog/hot-rank?page=0&pageSize=50&type=AI")["data"]
        for x in data[:CSDN_HOT_MAX_ITEMS]:
            out.append(item("cn_community", x.get("articleTitle", ""), x.get("articleDetailUrl", ""), until,
                            int(x.get("hotRankScore") or 0), "hot", "", board="CSDN 熱榜",
                            views=x.get("viewCount"), comments=x.get("commentCount"), favorites=x.get("favorCount")))
    except Exception as e:  # noqa: BLE001
        errors.append(f"CSDN: {e}")
    for node in V2EX_NODES:
        try:
            for title, link, pub, desc, _ in _parse_rss(http_get(f"https://www.v2ex.com/feed/{node}.xml"), "V2EX"):
                if since <= pub <= until:
                    out.append(item("cn_community", title, link, pub, 0, "none", desc, board=f"V2EX {node}"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"V2EX {node}: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    if errors:
        out[0]["extra"]["partial_failures"] = errors
    return out


def _feed_entries(text):
    """RSS／Atom 逐條回傳 (標題, 連結, 日期, 全文 HTML)；全文取 content:encoded、content、description 中最長的。"""
    root = ET.fromstring(text)
    a = "{http://www.w3.org/2005/Atom}"
    out = []
    for it in root.iter("item"):
        bodies = [it.findtext("{http://purl.org/rss/1.0/modules/content/}encoded"), it.findtext("description")]
        date = it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")
        if date:
            out.append((it.findtext("title", ""), (it.findtext("link") or "").strip(), parse_any_date(date),
                        max((b or "" for b in bodies), key=len)))
    for e in root.iter(f"{a}entry"):
        link = next((l.get("href") for l in e.findall(f"{a}link") if l.get("rel", "alternate") == "alternate"), "")
        date = e.findtext(f"{a}published") or e.findtext(f"{a}updated")
        if date:
            out.append((e.findtext(f"{a}title", ""), link, parse_any_date(date),
                        max((e.findtext(f"{a}content") or "", e.findtext(f"{a}summary") or ""), key=len)))
    return out


def _parse_ithelp_tag(text):
    """iT邦幫忙標籤文章列表，回傳 [(標題, URL, 時間, 摘要, Like 數, 瀏覽數)]。"""
    def count(s):
        s = s.strip().lower()
        return int(float(s[:-1]) * 1000) if s.endswith("k") else int(s) if s.isdigit() else 0
    out = []
    for block in text.split('<div class="qa-list">')[1:]:
        title = re.search(r'<a href="(https://ithelp\.ithome\.com\.tw/articles/\d+)" class="qa-list__title-link">(.*?)</a>', block, re.S)
        when = re.search(r'class="qa-list__info-time"[^>]*title="([\d\- :]+)"|title="([\d\- :]+)" class="qa-list__info-time"', block)
        if not title or not when:
            continue
        counts = dict((label, count(n)) for n, label in re.findall(
            r'qa-condition__count">([^<]*)</span>\s*<span class="qa-condition__text">([^<]*)</span>', block))
        desc = re.search(r'<p class="qa-list__desc">(.*?)</p>', block, re.S)
        d = datetime.strptime((when.group(1) or when.group(2)).strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=TAIPEI)
        out.append((strip_html(title.group(2)), title.group(1), to_utc(d), strip_html(desc.group(1)) if desc else "",
                    counts.get("Like", 0), counts.get("瀏覽", 0)))
    return out


def fetch_blogs(since, until):
    """英文部落格平台：Medium 出版物、dev.to 本週熱門、Hugging Face 部落格、Simon Willison、Lobsters AI 標籤。"""
    out, errors = [], []
    for name, url in MEDIUM_FEEDS.items():
        try:
            for title, link, pub, body in _feed_entries(http_get(url)):
                if since <= pub <= until:
                    out.append(item("blogs", title, link.split("?")[0], pub, 0, "none", body, publisher=f"Medium/{name}",
                                    content=strip_html(body, CONTENT_LIMIT)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"Medium {name}: {e}")
    seen = set()
    for tag in DEVTO_TAGS:
        try:
            for a in http_json(f"https://dev.to/api/articles?tag={tag}&top=7&per_page=30"):
                pub = parse_iso(a["published_at"])
                if a["id"] in seen or a.get("public_reactions_count", 0) < DEVTO_MIN_REACTIONS or not since <= pub <= until:
                    continue
                seen.add(a["id"])
                out.append(item("blogs", a["title"], a["url"], pub, a["public_reactions_count"], "reactions",
                                a.get("description", ""), publisher="dev.to", tags=a.get("tag_list"),
                                comments=a.get("comments_count")))
        except Exception as e:  # noqa: BLE001
            errors.append(f"dev.to {tag}: {e}")
    for name, url in BLOG_FEEDS.items():
        try:
            for title, link, pub, body in _feed_entries(http_get(url)):
                if since <= pub <= until:
                    out.append(item("blogs", title, link, pub, 0, "none", body, publisher=name))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    try:
        for s in http_json("https://lobste.rs/t/ai.json"):
            pub = parse_iso(s["created_at"])
            if since <= pub <= until:
                out.append(item("blogs", s["title"], s.get("url") or s["comments_url"], pub, s.get("score", 0), "points",
                                s.get("description", ""), publisher="Lobsters", comments_url=s["comments_url"]))
    except Exception as e:  # noqa: BLE001
        errors.append(f"Lobsters: {e}")
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    if errors:
        out[0]["extra"]["partial_failures"] = errors
    return out

SOURCES = {
    "arxiv": fetch_arxiv,
    "hf_papers": fetch_hf_papers,
    "hackernews": fetch_hackernews,
    "reddit": fetch_reddit,
    "news": fetch_news,
    "github": fetch_github,
    "github_agents": fetch_github_agents,
    "blogs": fetch_blogs,
    "tw_news": fetch_tw_news,
    "tw_community": fetch_tw_community,
    "cn_news": fetch_cn_news,
    "cn_community": fetch_cn_community,
}

# 週報產業／開源／社群三個版面依來源所在地分群
SOURCE_REGION = {n: "外國" for n in SOURCES} | {
    "tw_news": "台灣", "tw_community": "台灣", "cn_news": "中國", "cn_community": "中國"}


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="ISO8601，例如 2026-09-01T01:00:00Z")
    ap.add_argument("--until", default=None, help="ISO8601，預設現在")
    ap.add_argument("--out", default=None, help="輸出檔，預設 stdout")
    ap.add_argument("--only", default=None, help="逗號分隔，只跑指定來源")
    args = ap.parse_args()

    since = parse_iso(args.since)
    until = parse_iso(args.until) if args.until else datetime.now(timezone.utc)
    names = args.only.split(",") if args.only else list(SOURCES)

    items, counts, failed = [], {}, {}
    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        futures = {ex.submit(SOURCES[n], since, until): n for n in names}
        for fut, n in futures.items():
            try:
                rows = fut.result()
                for r in rows:
                    r["region"] = SOURCE_REGION[n]
                counts[n] = len(rows)
                items.extend(rows)
                print(f"[ok]   {n:<11} {len(rows)}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                counts[n] = 0
                failed[n] = str(e)
                print(f"[FAIL] {n:<11} {e}", file=sys.stderr)

    items.sort(key=lambda x: x["published_at"], reverse=True)
    result = {
        "meta": {"since": iso(since), "until": iso(until), "counts": counts,
                 "failed": failed, "generated_at": iso(datetime.now(timezone.utc))},
        "items": items,
    }
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        # 同時輸出一行一條的精簡清單，給 LLM 做初步排序用，不用讀完整 JSON
        brief = args.out.rsplit(".", 1)[0] + ".brief.md"
        with open(brief, "w", encoding="utf-8") as f:
            f.write(f"# candidates {result['meta']['since']} → {result['meta']['until']}\n")
            f.write(f"counts: {json.dumps(counts)}  failed: {json.dumps(failed)}\n\n")
            for i, x in enumerate(items):
                tag = (x["extra"].get("publisher") or x["extra"].get("subreddit") or x["extra"].get("board")
                       or x["extra"].get("via") or "")
                f.write(f"{i}\t{x['region']}\t{x['source']}{('/' + tag) if tag else ''}\t{x['score']}{x['score_kind'][:1] if x['score_kind'] != 'none' else ''}"
                        f"\t{x['published_at'][:10]}\t{x['title'][:120]}\t{x['url']}\n")
        print(f"wrote {args.out} ({len(items)} items) and {brief}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
