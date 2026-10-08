import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def note_names_command():
    for line in (REPO / "skill/SKILL.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("awk ") and "AI 概念筆記" in line:
            return line
    raise AssertionError("step-4 one-liner not found in SKILL.md")


class NoteNamesOneLinerTest(unittest.TestCase):
    def run_on(self, index_text):
        with tempfile.TemporaryDirectory() as vault:
            if index_text is not None:
                Path(vault, "INDEX.md").write_text(index_text, encoding="utf-8")
            r = subprocess.run(["bash", "-c", note_names_command()], env={"VAULT": vault, "PATH": "/usr/bin:/bin"},
                               capture_output=True, text=True)
        return r.stdout.split("\n")[:-1]

    def test_stops_at_next_heading(self):
        index = ("# INDEX\n\n## AI 概念筆記\n\n- [[KV Cache]]\n- [[MCP|Model Context Protocol]]\n\n"
                 "## 讀書筆記\n\n- [[Some Book]]\n")
        self.assertEqual(self.run_on(index), ["KV Cache", "MCP"])

    def test_no_block_gives_empty(self):
        self.assertEqual(self.run_on("# INDEX\n\n## 其他\n\n- [[X]]\n"), [])

    def test_missing_index_gives_empty(self):
        self.assertEqual(self.run_on(None), [])


class ReaderFocusTest(unittest.TestCase):
    def test_reader_placeholder_replaces_fixed_audience(self):
        text = (REPO / "skill/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("對 AI Agent 工程師的意義", text)
        self.assertIn("**對 <READER>的意義**", text)


class NoParallelTest(unittest.TestCase):
    def test_no_parallel_references(self):
        for name in ("SKILL.md", "settings.template.json"):
            self.assertNotIn("Parallel", (REPO / "skill" / name).read_text(encoding="utf-8"), name)


if __name__ == "__main__":
    unittest.main()
