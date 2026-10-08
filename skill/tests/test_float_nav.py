"""右下角浮動按鈕：回頂端、目錄面板、到底端。

執行：uv run --quiet --with markdown python3 -m unittest discover -s ~/.claude/skills/ai-radar/tests
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_html  # noqa: E402

REPORT = """# AI 知識雷達 2026-10-10
> 涵蓋 2026/10/03 09:00 至 2026/10/10 09:00

## 頭版

### Headline A
**一句話** 頭版內容

## 附錄：其他掃到的項目

- 某項目
"""


class FloatNavTest(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as d:
            self.html = build_html.build_html({"title": "AI 知識雷達 2026-10-10", "item_count": 1}, REPORT, d)

    def test_three_buttons_in_order(self):
        nav = self.html.split('<div class="fab">')[1].split("</div>")[0]
        self.assertLess(nav.index('href="#top"'), nav.index('popovertarget="tocpop"'))
        self.assertLess(nav.index('popovertarget="tocpop"'), nav.index('href="#bottom"'))
        self.assertIn('id="bottom"', self.html)
        self.assertNotIn('class="top"', self.html)

    def test_toc_panel_links_to_sections_and_items(self):
        panel = self.html.split('<div id="tocpop" popover>')[1].split("</nav>")[0]
        self.assertIn('href="#頭版"', panel)
        self.assertIn('href="#headline-a"', panel)
        self.assertIn('href="#附錄其他掃到的項目"', panel)

    def test_panel_click_opens_collapsed_section(self):
        self.assertIn("closest('details')", self.html)
        self.assertIn("hidePopover()", self.html)


if __name__ == "__main__":
    unittest.main()
