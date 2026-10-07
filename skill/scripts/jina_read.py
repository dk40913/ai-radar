#!/usr/bin/env python3
"""用 Jina Reader（r.jina.ai，免 key、約每分鐘 20 次）把網頁轉成 markdown 印到 stdout。
沒有 Parallel API key 時當 defuddle 讀不到的備援；有設 JINA_API_KEY 環境變數會帶上，額度較高。

用法: jina_read.py <url> [最多字元數，預設 30000]
"""
import os
import re
import sys
import urllib.request

url = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30000
headers = {"User-Agent": "ai-radar/0.1", "X-Return-Format": "markdown"}
if os.environ.get("JINA_API_KEY"):
    headers["Authorization"] = f"Bearer {os.environ['JINA_API_KEY']}"
try:
    with urllib.request.urlopen(urllib.request.Request(f"https://r.jina.ai/{url}", headers=headers), timeout=90) as r:
        text = r.read().decode("utf-8", errors="replace")
except Exception as e:  # noqa: BLE001
    sys.exit(f"jina_read failed: {e}")
if re.search(r"^Warning: Target URL returned error [45]\d\d", text, re.M):
    sys.exit("jina_read: target returned an HTTP error page (blocked or login wall), treat as unreadable")
if len(text.strip()) < 500:
    sys.exit(f"jina_read: content too short ({len(text.strip())} chars), treat as unreadable")
print(text[:limit])
