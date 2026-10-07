"""台灣、簡中來源的解析與 region 標記。

執行：python3 -m unittest discover -s ~/.claude/skills/ai-radar/tests
"""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fetch_sources as fs  # noqa: E402

PTT_INDEX = '''
<a class="btn wide" href="/bbs/Soft_Job/index1834.html">&lsaquo; 上頁</a>
<div class="r-ent">
  <div class="nrec"><span class="hl f3">12</span></div>
  <div class="title"><a href="/bbs/Soft_Job/M.1.A.html">[心得] 用 Claude Code 寫後端一個月</a></div>
  <div class="meta"><div class="date"> 1/03</div></div>
</div>
<div class="r-ent">
  <div class="nrec"><span class="hl f1">爆</span></div>
  <div class="title"><a href="/bbs/Soft_Job/M.2.A.html">[請益] 轉職 AI 工程師要學什麼</a></div>
  <div class="meta"><div class="date">12/30</div></div>
</div>
<div class="r-ent">
  <div class="nrec"></div>
  <div class="title">(本文已被刪除) [someone]</div>
  <div class="meta"><div class="date">12/30</div></div>
</div>
'''

ITHOME_LIST = '''
<div class="item">
  <p class="title"><a href="/news/179446">新創Ghost打造AI代理人專用個人電腦</a> </p>
  <div class="summary">讓模型與記憶常駐本機
 </div>
  <p class="post-at">2026-10-06 </p>
</div>
<div class="item">
  <p class="title"><a href="/news/179464">Mozilla推出Firefox 157.0.1更新</a> </p>
  <div class="summary">修補檔案處理元件弱點</div>
  <p class="post-at">2026-10-07 </p>
</div>
'''


class ZhFilterTest(unittest.TestCase):
    def test_matches_chinese_and_latin_terms(self):
        for t in ["生成式 AI 導入", "大模型推理加速", "Claude 新功能", "智能体框架", "OpenAI 發表"]:
            self.assertTrue(fs.zh_ai(t), t)

    def test_ignores_latin_substrings(self):
        for t in ["Email 安全更新", "Firefox 157 修補", "台積電法說會"]:
            self.assertFalse(fs.zh_ai(t), t)


class PttTest(unittest.TestCase):
    def test_parses_rows_infers_year_and_skips_deleted(self):
        until = datetime(2027, 1, 5, tzinfo=timezone.utc)
        rows, prev = fs._parse_ptt_index(PTT_INDEX, until)
        self.assertEqual(prev, "/bbs/Soft_Job/index1834.html")
        self.assertEqual([(r[0], r[1], r[2].astimezone(fs.TAIPEI).date().isoformat(), r[3]) for r in rows], [
            ("[心得] 用 Claude Code 寫後端一個月", "https://www.ptt.cc/bbs/Soft_Job/M.1.A.html", "2027-01-03", 12),
            ("[請益] 轉職 AI 工程師要學什麼", "https://www.ptt.cc/bbs/Soft_Job/M.2.A.html", "2026-12-30", 100),
        ])


class IthomeTest(unittest.TestCase):
    def test_parses_list_items(self):
        rows = fs._parse_ithome_list(ITHOME_LIST)
        self.assertEqual([(t, u, d.astimezone(fs.TAIPEI).date().isoformat()) for t, u, d, _ in rows], [
            ("新創Ghost打造AI代理人專用個人電腦", "https://www.ithome.com.tw/news/179446", "2026-10-06"),
            ("Mozilla推出Firefox 157.0.1更新", "https://www.ithome.com.tw/news/179464", "2026-10-07"),
        ])


ITHELP_TAG = '''
<div class="qa-list">
 <div class="qa-list__condition">
  <a href="https://ithelp.ithome.com.tw/articles/10421766" class="qa-condition "> <span class="qa-condition__count">5</span> <span class="qa-condition__text">Like</span></a>
  <a href="https://ithelp.ithome.com.tw/articles/10421766" class="qa-condition "> <span class="qa-condition__count">2</span> <span class="qa-condition__text">留言</span> </a>
  <a href="https://ithelp.ithome.com.tw/articles/10421766" class="qa-condition qa-condition--change "> <span class="qa-condition__count">1.2k</span> <span class="qa-condition__text">瀏覽</span> </a>
 </div>
 <div class="qa-list__content"> <h3 class="qa-list__title"> <span class="title-badge title-badge--tech"> 技術 </span>
  <a href="https://ithelp.ithome.com.tw/articles/10421766" class="qa-list__title-link">AI 誤刪、外洩越來越嚴重</a> </h3>
  <p class="qa-list__desc"> 最近接連看到好幾篇 </p>
  <div class="qa-list__info"> <a title="2026-10-06 22:31:57" class="qa-list__info-time">2026-10-06</a> </div>
 </div>
</div>
'''


class IthelpTest(unittest.TestCase):
    def test_parses_tag_list(self):
        rows = fs._parse_ithelp_tag(ITHELP_TAG)
        self.assertEqual([(t, u, d.astimezone(fs.TAIPEI).strftime("%Y-%m-%d %H:%M"), likes, views) for t, u, d, _, likes, views in rows],
                         [("AI 誤刪、外洩越來越嚴重", "https://ithelp.ithome.com.tw/articles/10421766", "2026-10-06 22:31", 5, 1200)])

class RegionTest(unittest.TestCase):
    def test_every_source_has_region(self):
        self.assertEqual(set(fs.SOURCE_REGION), set(fs.SOURCES))
        self.assertEqual(fs.SOURCE_REGION["arxiv"], "外國")
        self.assertEqual(fs.SOURCE_REGION["tw_news"], "台灣")
        self.assertEqual(fs.SOURCE_REGION["cn_community"], "中國")
        self.assertEqual(fs.SOURCE_REGION["blogs"], "外國")


if __name__ == "__main__":
    unittest.main()
