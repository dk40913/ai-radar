"""「各地社群反應」版面：HTML 目錄與信件摘要。

執行：uv run --quiet --with markdown python3 -m unittest discover -s ~/.claude/skills/ai-radar/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_html  # noqa: E402

FM = {"date": "2026-10-10", "period_start": "2026-10-03", "period_end": "2026-10-10", "item_count": 2}

REPORT = """# AI 知識雷達 2026-10-10
> 涵蓋 2026/10/03 09:00 至 2026/10/10 09:00

## 頭版

### Alpha Model 發布
**一句話** 頭版一

### Beta Tool 開源
**一句話** 頭版二

## 各地社群反應

> [!info] 依本週頭版搜尋知乎、Dcard、Reddit 的討論，留言是網友意見，未經查證。

### Alpha Model 發布：社群反應
**知乎** 看法兩極。（[來源](https://example.com/a)）
**Dcard** 本週沒有找到相關討論
**Reddit** 多數支持。（[來源](https://example.com/b)）

### Beta Tool 開源：社群反應
**知乎** 本週沒有找到相關討論
**Dcard** 本週沒有找到相關討論
**Reddit** 本週沒有找到相關討論
"""


class ReactionsTest(unittest.TestCase):
    def test_html_has_section_and_toc_entries(self):
        html = build_html.build_html(FM, REPORT, "/nonexistent")
        self.assertIn('<details class="section" id="各地社群反應"', html)
        toc = html.split("</nav>")[0]
        self.assertIn("Alpha Model 發布：社群反應", toc)
        self.assertIn("Beta Tool 開源：社群反應", toc)

    def test_digest_lists_headline_names_without_suffix(self):
        digest = build_html.build_digest(FM, REPORT)
        self.assertIn("【各地社群反應】Alpha Model 發布、Beta Tool 開源", digest)
        self.assertNotIn("：社群反應", digest)

    def test_digest_without_section(self):
        md = REPORT.split("## 各地社群反應")[0]
        self.assertNotIn("【各地社群反應】", build_html.build_digest(FM, md))


if __name__ == "__main__":
    unittest.main()
