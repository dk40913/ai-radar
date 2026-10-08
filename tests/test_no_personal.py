import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN = [REPO / "skill", REPO / "vault-template", REPO / "launchd", REPO / "obsidian", REPO / "install.sh",
        REPO / "README.md", REPO / "INSTALL.md"]
FORBIDDEN = ["/Users/herb", "dk40913@", "Herb", "Documents/Obsidian"]
# Documents/Obsidian is allowed only as an example default vault path.
ALLOWED = {(name, "Documents/Obsidian") for name in ("config.example.json", "README.md", "INSTALL.md")}
# Design docs may name the author and the example vault, but not his home path or email.
DOCS = REPO / "docs"
DOCS_FORBIDDEN = ["/Users/herb", "dk40913@"]


def text_files(scan=SCAN):
    for root in scan:
        paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for p in paths:
            if "__pycache__" in p.parts:
                continue
            try:
                yield p, p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


class NoPersonalStringsTest(unittest.TestCase):
    def test_shipped_files_have_no_personal_strings(self):
        hits = []
        for path, text in text_files():
            for word in FORBIDDEN:
                if (path.name, word) in ALLOWED:
                    continue
                for n, line in enumerate(text.splitlines(), 1):
                    if word in line:
                        hits.append(f"{path.relative_to(REPO)}:{n}: {word}")
        self.assertEqual(hits, [])

    def test_docs_have_no_home_path_or_email(self):
        hits = [f"{path.relative_to(REPO)}:{n}: {word}"
                for path, text in text_files([DOCS])
                for n, line in enumerate(text.splitlines(), 1)
                for word in DOCS_FORBIDDEN if word in line]
        self.assertTrue(any(True for _ in text_files([DOCS])))
        self.assertEqual(hits, [])

    def test_scan_covers_expected_files(self):
        names = {p.name for p, _ in text_files()}
        self.assertTrue({"SKILL.md", "install.sh", "CLAUDE.md", "README.md", "INSTALL.md"} <= names, names)


if __name__ == "__main__":
    unittest.main()
