"""產業／開源／社群三個版面的「外國／台灣／中國」分群。

執行：uv run --quiet --with markdown python3 -m unittest discover -s ~/.claude/skills/ai-radar/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import add_toc  # noqa: E402
import build_html  # noqa: E402

REPORT = """# AI 知識雷達 2026-10-10
> 涵蓋 2026/10/03 09:00 至 2026/10/10 09:00

## 頭版

### Headline A
**一句話** 頭版內容

## 產業與產品版

**▍外國**

### Intl News
**一句話** 外國條目

**▍台灣**

### TW News
**一句話** 台灣條目
> [!tip] 可加進工作流
> 理由

**▍中國**

### CN News
**一句話** 中國條目

## 社群熱議版

**▍外國**

### HN Thread
**一句話** 討論
"""


class TocTest(unittest.TestCase):
    def test_outline_records_region_per_item(self):
        sections = add_toc.outline(REPORT.split("\n"))
        industry = dict(sections)["產業與產品版"]
        self.assertEqual([(t, r) for t, _, r in industry],
                         [("Intl News", "外國"), ("TW News", "台灣"), ("CN News", "中國")])
        self.assertEqual([r for _, _, r in dict(sections)["頭版"]], [None])

    def test_callout_shows_region_labels_and_keeps_numbering(self):
        lines = add_toc.build_callout(add_toc.outline(REPORT.split("\n")))
        text = "\n".join(lines)
        self.assertIn("> *外國*\n> 1. [[#Intl News]]\n> *台灣*\n> 2. [[#TW News]] 🔧 可加進工作流\n> *中國*\n> 3. [[#CN News]]", text)
        self.assertNotIn("▍", text)


class HtmlTest(unittest.TestCase):
    def test_region_marker_not_swallowed_into_previous_item(self):
        _, body = build_html.split_sections(REPORT)[0], dict(build_html.split_sections(REPORT))["產業與產品版"]
        html = build_html.render_section_body(body)
        intl = html.split('id="intl-news"')[1].split("</article>")[0]
        self.assertNotIn("台灣", intl)
        self.assertIn('<div class="region">台灣</div>', html)
        self.assertLess(html.index('<div class="region">台灣</div>'), html.index('id="tw-news"'))

    def test_digest_lists_titles_by_region(self):
        fm = {"date": "2026-10-10", "period_start": "2026-10-03", "period_end": "2026-10-10", "item_count": 5}
        digest = build_html.build_digest(fm, REPORT)
        self.assertIn("【產業與產品版】外國：Intl News；台灣：TW News；中國：CN News", digest)
        self.assertIn("【社群熱議版】外國：HN Thread", digest)

    def test_sections_without_regions_unchanged(self):
        fm = {"date": "2026-10-10", "period_start": "2026-10-03", "period_end": "2026-10-10", "item_count": 5}
        md = "## 論文版\n\n### Paper A\n**一句話** x\n\n### Paper B\n**一句話** y\n"
        self.assertIn("【論文版】Paper A、Paper B", build_html.build_digest(fm, md))


if __name__ == "__main__":
    unittest.main()
