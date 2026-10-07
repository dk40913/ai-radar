import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class InstallTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        (self.home / "Documents/Vault").mkdir(parents=True)
        self.skill = self.home / ".claude/skills/ai-radar"
        self.vault = self.home / "Documents/Vault"
        self.repo = REPO
        self.tools = self.tmp / "tools"
        self.tools.mkdir()
        self.path = f"{self.tools}:/usr/bin:/bin"

    def install(self, *args, repo=None):
        base = ["--no-launchd", "--skip-checks"]
        return subprocess.run(
            ["bash", str((repo or self.repo) / "install.sh"), *args, *base],
            env={"HOME": str(self.home), "USER": "tester", "PATH": self.path},
            capture_output=True, text=True)

    def stub_tool(self, name):
        p = self.tools / name
        p.write_text("#!/bin/bash\nexit 0\n")
        p.chmod(0o755)

    def config(self):
        cfg = json.loads((self.skill / "config.json").read_text(encoding="utf-8"))
        self.assertIsInstance(cfg.pop("path_prepend"), list)
        return cfg

    def ok(self, *args, **kw):
        r = self.install(*args, **kw)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def default(self):
        return self.ok("--vault", "~/Documents/Vault", "--parallel", "no")

    def test_skill_files_and_config(self):
        self.default()
        self.assertTrue((self.skill / "SKILL.md").exists())
        self.assertTrue((self.skill / "scripts/run.sh").exists())
        self.assertTrue((self.skill / "tests").is_dir())
        self.assertFalse((self.skill / "settings.template.json").exists())
        self.assertFalse(list(self.skill.rglob("__pycache__")))
        self.assertEqual(self.config(), {
            "parallel": False, "vault": str(self.vault), "mail_to": "",
            "model": "", "subagent_model": "opus", "reader": "AI Agent 工程師",
            "focus": "AI Agent、LLM 推論與部署、RAG、本地模型、agent 框架與工具", "arxiv_keywords": []})
        self.assertTrue((self.home / ".local/state/ai-radar").is_dir())

    def test_settings_inside_home(self):
        self.default()
        text = (self.skill / "settings.json").read_text()
        json.loads(text)
        self.assertIn("Edit(~/Documents/Vault/AI知識雷達/**)", text)
        self.assertIn("Edit(~/Documents/Vault/INDEX.md)", text)
        self.assertIn(f"Bash({self.skill}/scripts/send_mail.sh:*)", text)
        self.assertNotRegex(text, r"__(HOME|USER|VAULT_RULE)__")

    def test_path_prepend_lists_tool_dirs(self):
        for name in ("claude", "defuddle", "uv"):
            self.stub_tool(name)
        self.default()
        cfg = json.loads((self.skill / "config.json").read_text())
        python_dir = os.path.dirname(shutil.which("python3", path=self.path))
        self.assertEqual(cfg["path_prepend"], [str(self.tools), python_dir])

    def test_path_prepend_skips_missing_tools(self):
        self.default()
        cfg = json.loads((self.skill / "config.json").read_text())
        self.assertEqual(cfg["path_prepend"], [os.path.dirname(shutil.which("python3", path=self.path))])

    def test_special_characters_are_escaped(self):
        self.home = self.tmp / 'h&o "me"'
        self.skill = self.home / ".claude/skills/ai-radar"
        vault = self.home / 'Documents/My "Notes" & Co'
        vault.mkdir(parents=True)
        self.ok("--vault", str(vault), "--parallel", "no")
        allow = json.loads((self.skill / "settings.json").read_text())["permissions"]["allow"]
        self.assertIn('Edit(~/Documents/My "Notes" & Co/AI知識雷達/**)', allow)
        self.assertIn(f"Bash({self.skill}/scripts/send_mail.sh:*)", allow)
        plist = self.home / "Library/LaunchAgents/com.tester.ai-radar.plist"
        if shutil.which("plutil"):
            r = subprocess.run(["plutil", "-lint", str(plist)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_settings_outside_home(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        self.ok("--vault", str(other), "--parallel", "no")
        text = (self.skill / "settings.json").read_text()
        self.assertIn(f"Edit(/{other}/AI知識雷達/**)", text)
        self.assertNotRegex(text, r"__(HOME|USER|VAULT_RULE)__")

    def test_plist(self):
        self.default()
        plist = self.home / "Library/LaunchAgents/com.tester.ai-radar.plist"
        text = plist.read_text()
        self.assertIn(f"{self.skill}/scripts/run.sh", text)
        self.assertIn("com.tester.ai-radar", text)
        self.assertNotRegex(text, r"__(HOME|USER|VAULT_RULE)__")

    def test_vault_dirs(self):
        self.default()
        self.assertTrue((self.vault / "AI知識雷達/CLAUDE.md").exists())
        self.assertTrue((self.vault / "AI知識雷達/attachments").is_dir())

    def test_rerun_updates_config_keeps_user_files(self):
        self.default()
        (self.skill / "harness_profile.md").write_text("mine")
        (self.vault / "AI知識雷達/CLAUDE.md").write_text("mine too")
        self.ok("--vault", "~/Documents/Vault", "--parallel", "yes", "--mail-to", "a@b.c",
                "--model", "m1", "--subagent-model", "sonnet")
        self.assertEqual(self.config(), {
            "parallel": True, "vault": str(self.vault), "mail_to": "a@b.c",
            "model": "m1", "subagent_model": "sonnet", "reader": "AI Agent 工程師",
            "focus": "AI Agent、LLM 推論與部署、RAG、本地模型、agent 框架與工具", "arxiv_keywords": []})
        self.assertEqual((self.skill / "harness_profile.md").read_text(), "mine")
        self.assertEqual((self.vault / "AI知識雷達/CLAUDE.md").read_text(), "mine too")

    def test_reader_focus_keywords(self):
        r = self.ok("--vault", "~/Documents/Vault", "--parallel", "no", "--reader", "醫療影像研究員",
                    "--focus", "醫學影像、診斷模型", "--arxiv-keywords", " Medical Imag, segmentation,,MRI ")
        cfg = self.config()
        self.assertEqual(cfg["reader"], "醫療影像研究員")
        self.assertEqual(cfg["focus"], "醫學影像、診斷模型")
        self.assertEqual(cfg["arxiv_keywords"], ["medical imag", "segmentation", "mri"])
        self.assertIn("醫療影像研究員", (self.skill / "config.json").read_text(encoding="utf-8"))
        self.assertIn("focus:", r.stdout)
        self.assertIn("醫學影像、診斷模型", r.stdout)

    def test_harness_profile_copied_from_example(self):
        repo = self.tmp / "repo"
        shutil.copytree(REPO, repo, ignore=shutil.ignore_patterns(".git", ".superpowers", "__pycache__"))
        (repo / "skill/harness_profile.example.md").write_text("example profile")
        self.ok("--vault", "~/Documents/Vault", "--parallel", "no", repo=repo)
        self.assertEqual((self.skill / "harness_profile.md").read_text(), "example profile")

    def test_no_example_means_no_profile(self):
        self.default()
        if not (REPO / "skill/harness_profile.example.md").exists():
            self.assertFalse((self.skill / "harness_profile.md").exists())

    def test_errors(self):
        self.assertNotEqual(self.install("--parallel", "no").returncode, 0)
        self.assertNotEqual(self.install("--vault", str(self.tmp / "nope"), "--parallel", "no").returncode, 0)
        self.assertNotEqual(self.install("--vault", str(self.vault), "--parallel", "no",
                                         "--subagent-model", "fable").returncode, 0)
        self.assertNotEqual(self.install("--vault", str(self.vault)).returncode, 0)
        self.assertNotEqual(self.install("--vault", str(self.vault), "--parallel", "maybe").returncode, 0)


if __name__ == "__main__":
    unittest.main()
