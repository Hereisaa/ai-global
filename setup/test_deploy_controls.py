"""Deploy against isolated homes; retain fixtures and backups for inspection."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
if os.name == "nt":
    BASH = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe")
PWSH = shutil.which("powershell") if os.name == "nt" else shutil.which("pwsh")


class DeployControlTests(unittest.TestCase):
    def exercise(self, platform):
        base = Path(tempfile.mkdtemp(prefix="ai-global-deploy-controls-"))
        repo, home = base / "repo", base / "home"
        repo.mkdir()
        for folder in ("setup", "claude/skills/ai-global", "claude/commands", "claude/agents", "claude/hooks", "governance", "codex"):
            (repo / folder).mkdir(parents=True, exist_ok=True)
        for filename in ("install.sh", "install.ps1"):
            shutil.copy2(ROOT / "setup" / filename, repo / "setup" / filename)
        for name in ("claude/CLAUDE.md", "codex/AGENTS.md", "governance/20-judgment.md", "claude/skills/ai-global/SKILL.md", "claude/commands/owned.md"):
            (repo / name).write_text("# Updated\n", encoding="utf-8")
        subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-m", "fixture"], capture_output=True, check=True)
        for name in ("post-merge", "post-rewrite"):
            (repo / ".git/hooks" / name).write_text("# existing custom hook\n")
        parked = home / ".claude/ai-global-disabled/skills/ai-global/SKILL.md"
        parked.parent.mkdir(parents=True)
        parked.write_text("# Old\n")
        command = home / ".claude/ai-global-disabled/commands/owned.md"
        command.parent.mkdir(parents=True)
        command.write_text("# Old command\n")
        local = home / ".claude/skills/local/SKILL.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Local\n")
        env = os.environ.copy()
        if platform == "bash":
            env["AI_GLOBAL_TARGET_HOME"] = home.as_posix()
            cmd = [BASH, str(repo / "setup/install.sh")]
            check_cmd = cmd + ["check"]
        else:
            cmd = [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(repo / "setup/install.ps1"), "-TargetHome", str(home)]
            check_cmd = cmd + ["-Mode", "check"]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DISABLED", result.stdout)
        self.assertEqual(parked.read_text(), "# Updated\n")
        self.assertEqual(command.read_text(), "# Updated\n")
        self.assertFalse((home / ".claude/skills/ai-global").exists())
        self.assertFalse((home / ".claude/commands/owned.md").exists())
        self.assertEqual(local.read_text(), "# Local\n")
        for name in ("post-merge", "post-rewrite"):
            self.assertEqual((repo / ".git/hooks" / name).read_text(), "# existing custom hook\n")
        self.assertTrue(any(p.read_text() == "# Old\n" for p in (home / ".ai-trash").rglob("SKILL.md")))
        state = json.loads((home / ".ai-global/.deploy-state.json").read_text())
        self.assertIn("claude/skills/ai-global/SKILL.md", state["files"])
        result = subprocess.run(check_cmd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_bash_preserves_disabled_capabilities(self):
        self.exercise("bash")

    @unittest.skipUnless(PWSH, "PowerShell unavailable")
    def test_powershell_preserves_disabled_capabilities(self):
        self.exercise("powershell")


if __name__ == "__main__":
    unittest.main()
