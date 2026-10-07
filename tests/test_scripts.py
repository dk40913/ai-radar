import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# run.sh's own PATH outside $HOME; a real tool found here would be called by run.sh.
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


class ScriptsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = self.tmp / "home"
        self.skill = self.home / ".claude/skills/ai-radar"
        shutil.copytree(REPO / "skill", self.skill,
                        ignore=shutil.ignore_patterns("__pycache__", "tests"))
        self.bin = self.home / ".local/bin"
        self.bin.mkdir(parents=True)
        self.osa_args = self.tmp / "osascript_args.txt"
        self.claude_args = self.tmp / "claude_args.txt"
        self._stub("osascript", f'printf "%s\\n" "$@" >> "{self.osa_args}"\n')
        self._stub("claude", (
            f'printf "%s\\n" "$@" > "{self.claude_args}"\n'
            'mkdir -p "$HOME/.local/state/ai-radar"\n'
            'date +%s%N > "$HOME/.local/state/ai-radar/last_run.json"\n'
        ))
        self._stub("uv", '[ "${1:-}" = "--version" ] && echo "uv 0.0.0"\nexit 0\n')
        self._stub("defuddle", "exit 0\n")

    def _stub(self, name, body, directory=None):
        p = (directory or self.bin) / name
        p.write_text("#!/bin/bash\n" + body)
        p.chmod(0o755)

    def config(self, **kw):
        cfg = {"parallel": False, "vault": str(self.home / "Vault"), "mail_to": "",
               "model": "", "subagent_model": "opus"}
        cfg.update(kw)
        (self.skill / "config.json").write_text(json.dumps(cfg))

    def env(self):
        return {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin"}

    def send_mail(self, *extra):
        return subprocess.run(
            [str(self.skill / "scripts/send_mail.sh"), "subj", str(self.skill / "SKILL.md"), *extra],
            env=self.env(), capture_output=True, text=True)

    def run_sh(self):
        return subprocess.run([str(self.skill / "scripts/run.sh")], env=self.env(),
                              capture_output=True, text=True, timeout=60)

    def claude_lines(self):
        return self.claude_args.read_text().splitlines()


class SendMailTests(ScriptsTestCase):
    def test_empty_mail_to_disables_mail(self):
        self.config(mail_to="")
        r = self.send_mail()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mail disabled", r.stdout)
        self.assertFalse(self.osa_args.exists())

    def test_config_mail_to_used_by_default(self):
        self.config(mail_to="cfg@example.com")
        r = self.send_mail()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cfg@example.com", self.osa_args.read_text().splitlines())

    def test_third_argument_overrides_config(self):
        self.config(mail_to="cfg@example.com")
        r = self.send_mail("arg@example.com")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.osa_args.read_text().splitlines()
        self.assertIn("arg@example.com", lines)
        self.assertNotIn("cfg@example.com", lines)


class RunShTests(ScriptsTestCase):
    def test_empty_model_omits_model_flag(self):
        self.config(model="")
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("--model", self.claude_lines())

    def test_model_flag_passed(self):
        self.config(model="claude-sonnet-5-5")
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.claude_lines()
        self.assertEqual(lines[lines.index("--model") + 1], "claude-sonnet-5-5")

    def test_add_dir_uses_config_vault(self):
        self.config()
        self.run_sh()
        lines = self.claude_lines()
        self.assertIn(str(self.home / "Vault"), lines)
        self.assertEqual(lines[lines.index(str(self.home / "Vault")) - 1], "--add-dir")

    def test_missing_vault_fails_before_claude(self):
        self.config(vault="")
        r = self.run_sh()
        self.assertEqual(r.returncode, 1)
        failure = self.home / ".local/state/ai-radar/runs" / date.today().isoformat() / "failure.txt"
        self.assertTrue(failure.exists())
        self.assertFalse(self.claude_args.exists())

    def test_failure_shows_notification(self):
        self.config(vault="")
        self.run_sh()
        self.assertIn("display notification", self.osa_args.read_text())

    def test_path_prepend_comes_first(self):
        extra = self.tmp / "extra"
        extra.mkdir()
        marker = self.tmp / "extra_claude_called"
        self._stub("claude", (
            f'touch "{marker}"\n'
            'mkdir -p "$HOME/.local/state/ai-radar"\n'
            'date +%s%N > "$HOME/.local/state/ai-radar/last_run.json"\n'
        ), directory=extra)
        self.config(path_prepend=[str(extra)])
        r = self.run_sh()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(marker.exists())
        self.assertFalse(self.claude_args.exists())

    def assert_missing_tool_fails(self, tool):
        if shutil.which(tool, path=SYSTEM_PATH):
            self.skipTest(f"real {tool} on run.sh's fixed PATH")
        (self.bin / tool).unlink()
        self.config()
        r = self.run_sh()
        self.assertEqual(r.returncode, 1)
        failure = self.home / ".local/state/ai-radar/runs" / date.today().isoformat() / "failure.txt"
        self.assertIn(f"{tool} 不在 PATH 上", failure.read_text())
        self.assertFalse(self.claude_args.exists())

    def test_missing_claude_fails(self):
        self.assert_missing_tool_fails("claude")

    def test_missing_defuddle_fails(self):
        self.assert_missing_tool_fails("defuddle")

    def test_missing_config_fails(self):
        r = self.run_sh()
        self.assertEqual(r.returncode, 1)
        self.assertFalse(self.claude_args.exists())


if __name__ == "__main__":
    unittest.main()
