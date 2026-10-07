"""arXiv 關鍵字可由 config 的 arxiv_keywords 覆蓋。

執行：python3 -m unittest discover -s ~/.claude/skills/ai-radar/tests
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fetch_sources as fs  # noqa: E402


class ArxivKeywordsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config = Path(tmp.name) / "config.json"
        patcher = mock.patch.object(fs, "CONFIG_PATH", self.config)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, text):
        self.config.write_text(text, encoding="utf-8")

    def test_config_keywords_used_lowercased(self):
        self.write(json.dumps({"arxiv_keywords": ["Medical Imag", "MRI"]}))
        self.assertEqual(fs.arxiv_keywords(), ["medical imag", "mri"])

    def test_empty_list_falls_back(self):
        self.write(json.dumps({"arxiv_keywords": []}))
        self.assertEqual(fs.arxiv_keywords(), fs.ARXIV_KEYWORDS)

    def test_missing_key_falls_back(self):
        self.write(json.dumps({"vault": "/x"}))
        self.assertEqual(fs.arxiv_keywords(), fs.ARXIV_KEYWORDS)

    def test_non_list_falls_back(self):
        self.write(json.dumps({"arxiv_keywords": "mri"}))
        self.assertEqual(fs.arxiv_keywords(), fs.ARXIV_KEYWORDS)

    def test_missing_file_falls_back(self):
        self.assertEqual(fs.arxiv_keywords(), fs.ARXIV_KEYWORDS)

    def test_broken_json_falls_back(self):
        self.write("{not json")
        self.assertEqual(fs.arxiv_keywords(), fs.ARXIV_KEYWORDS)

    def test_relevance_uses_given_keywords(self):
        score, hits = fs._arxiv_relevance("MRI segmentation", "an agent", ["mri", "agent"])
        self.assertEqual((score, hits), (4, ["mri", "agent"]))
        self.assertEqual(fs._arxiv_relevance("LLM agents", "", ["mri"]), (0, []))


if __name__ == "__main__":
    unittest.main()
