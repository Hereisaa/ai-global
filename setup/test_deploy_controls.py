"""Deploy against isolated homes; retain fixtures and backups for inspection."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "setup/deploy.py"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def fixture():
    """A throwaway clone plus a home with a disabled skill/command and a local
    skill the repo does not own. Nothing is cleaned up on purpose."""
    base = Path(tempfile.mkdtemp(prefix="ai-global-deploy-controls-"))
    repo, home = base / "repo", base / "home"
    for folder in ("claude/skills/ai-global", "claude/commands", "claude/agents", "claude/hooks", "governance", "codex"):
        (repo / folder).mkdir(parents=True)
    for name in ("claude/CLAUDE.md", "codex/AGENTS.md", "governance/20-judgment.md",
                 "claude/skills/ai-global/SKILL.md", "claude/commands/owned.md", "claude/commands/extra.md"):
        (repo / name).write_text("# Updated\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", "fixture"], capture_output=True, check=True)
    for name in ("skills/ai-global/SKILL.md", "commands/owned.md"):
        parked = home / ".claude/ai-global-disabled" / name
        parked.parent.mkdir(parents=True)
        parked.write_text("# Old\n")
    local = home / ".claude/skills/local/SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("# Local\n")
    return repo, home


def cli(repo, home, mode):
    return subprocess.run([sys.executable, str(SCRIPT), mode, "--repo", str(repo), "--home", str(home)],
                          env=ENV, capture_output=True, text=True, encoding="utf-8")


class DeployControlTests(unittest.TestCase):
    def statuses(self, result):
        return {status for status, _, _ in result["results"]}

    def test_install_preserves_disabled_and_local_then_check_is_clean(self):
        repo, home = fixture()
        for name in ("post-merge", "post-rewrite"):
            (repo / ".git/hooks" / name).write_text("# existing custom hook\n")
        lines = []
        result = deploy.run(repo, home, "install", echo=lines.append)
        self.assertTrue(result["ok"])
        self.assertIn("DISABLED", self.statuses(result))
        self.assertTrue(any(line.startswith("DISABLED") for line in lines))
        self.assertEqual((home / ".claude/ai-global-disabled/skills/ai-global/SKILL.md").read_text(), "# Updated\n")
        self.assertEqual((home / ".claude/ai-global-disabled/commands/owned.md").read_text(), "# Updated\n")
        self.assertFalse((home / ".claude/skills/ai-global").exists())
        self.assertFalse((home / ".claude/commands/owned.md").exists())
        self.assertEqual((home / ".claude/commands/extra.md").read_text(), "# Updated\n")
        self.assertEqual((home / ".claude/skills/local/SKILL.md").read_text(), "# Local\n")
        self.assertFalse((home / ".claude/CLAUDE.md").is_symlink())
        for name in ("post-merge", "post-rewrite"):
            self.assertEqual((repo / ".git/hooks" / name).read_text(), "# existing custom hook\n")
        self.assertIsNotNone(result["trash"])
        self.assertTrue(any(p.read_text() == "# Old\n" for p in (home / ".ai-trash").rglob("SKILL.md")))
        state = json.loads(result["state_path"].read_text(encoding="utf-8"))
        self.assertEqual(state["commit"], subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip())
        self.assertEqual(state["platform"], deploy.platform_name())
        self.assertEqual(state["managed"], ["claude/skills/ai-global", "claude/commands/extra.md", "claude/commands/owned.md"])
        self.assertEqual(state["files"]["claude/skills/ai-global/SKILL.md"], deploy.blob_hash(repo / "claude/skills/ai-global/SKILL.md"))
        self.assertEqual(result["state_path"].read_bytes().count(b"\r"), 0)
        check = deploy.run(repo, home, "check", echo=lambda _: None)
        self.assertTrue(check["ok"])
        self.assertEqual(self.statuses(check) - {"OK", "SKIP", "DISABLED"}, set())
        completed = cli(repo, home, "check")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("global deployment is in sync", completed.stdout)

    def test_check_reports_behind_edited_extra_and_install_repairs(self):
        repo, home = fixture()
        deploy.run(repo, home, "install", echo=lambda _: None)
        (repo / "governance/20-judgment.md").write_text("# Newer in repo\n", encoding="utf-8")
        (home / ".claude/CLAUDE.md").write_text("# Edited locally\n", encoding="utf-8")
        os.rename(repo / "claude/commands/extra.md", repo / "claude/commands/renamed.md")
        (home / ".ai-global/leftover.txt").write_text("old layout\n")
        (home / ".claude/hooks").mkdir(exist_ok=True)
        (home / ".claude/hooks/stray.sh").write_text("not from repo\n")
        check = deploy.run(repo, home, "check", echo=lambda _: None)
        self.assertFalse(check["ok"])
        by_path = {Path(path): status for status, path, _ in check["results"]}
        self.assertEqual(by_path[home / ".ai-global/governance/20-judgment.md"], "BEHIND")
        self.assertEqual(by_path[home / ".claude/CLAUDE.md"], "EDITED")
        self.assertEqual(by_path[home / ".claude/commands/extra.md"], "EXTRA")
        self.assertEqual(by_path[home / ".ai-global/leftover.txt"], "EXTRA")
        self.assertEqual(by_path[home / ".claude/hooks/stray.sh"], "EXTRA")
        self.assertEqual(by_path[home / ".claude/commands/renamed.md"], "MISSING")
        self.assertEqual((home / ".claude/CLAUDE.md").read_text(), "# Edited locally\n")
        completed = cli(repo, home, "check")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("out of sync", completed.stdout)

        result = deploy.run(repo, home, "install", echo=lambda _: None)
        by_path = {Path(path): status for status, path, _ in result["results"]}
        self.assertEqual(by_path[home / ".claude/commands/extra.md"], "DROP")
        self.assertEqual(by_path[home / ".ai-global/leftover.txt"], "DROP")
        self.assertEqual(by_path[home / ".claude/hooks/stray.sh"], "DROP")
        self.assertEqual(by_path[home / ".claude/commands/renamed.md"], "PUT")
        self.assertIn(("WARN", str(home / ".claude/CLAUDE.md"), "differed from the repo; the old copy goes to trash"), result["results"])
        self.assertEqual((home / ".ai-global/governance/20-judgment.md").read_text(), "# Newer in repo\n")
        self.assertEqual((home / ".claude/CLAUDE.md").read_text(), "# Updated\n")
        trash = result["trash"]
        self.assertEqual((trash / ".claude/CLAUDE.md").read_text(), "# Edited locally\n")
        self.assertEqual((trash / ".claude/commands/extra.md").read_text(), "# Updated\n")
        self.assertTrue((trash / ".ai-global/leftover.txt").is_file())
        state = json.loads(result["state_path"].read_text(encoding="utf-8"))
        self.assertNotIn("claude/commands/extra.md", state["managed"])
        self.assertTrue(deploy.run(repo, home, "check", echo=lambda _: None)["ok"])
        self.assertEqual(cli(repo, home, "check").returncode, 0)

    def test_fresh_repo_gets_reminder_hooks_and_file_where_dir_belongs_is_parked(self):
        repo, home = fixture()
        (home / ".claude/hooks").parent.mkdir(parents=True, exist_ok=True)
        (home / ".claude/hooks").write_text("a file, not a directory\n")
        (repo / "claude/hooks/tidy.sh").write_text("#!/bin/sh\n")
        result = deploy.run(repo, home, "install", echo=lambda _: None)
        self.assertEqual((home / ".claude/hooks/tidy.sh").read_text(), "#!/bin/sh\n")
        self.assertEqual((result["trash"] / ".claude/hooks").read_text(), "a file, not a directory\n")
        for name in ("post-merge", "post-rewrite"):
            self.assertIn("python setup/deploy.py check", (repo / ".git/hooks" / name).read_text())

    def test_link_at_target_is_stale_then_replaced_by_real_file(self):
        repo, home = fixture()
        (home / ".claude/CLAUDE.md").parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(repo / "claude/CLAUDE.md", home / ".claude/CLAUDE.md")
        except OSError:
            self.skipTest("symlink creation not permitted")
        check = deploy.run(repo, home, "check", echo=lambda _: None)
        self.assertIn(("STALE", str(home / ".claude/CLAUDE.md"), "dangling link left by an older install"), check["results"])
        result = deploy.run(repo, home, "install", echo=lambda _: None)
        self.assertFalse((home / ".claude/CLAUDE.md").is_symlink())
        self.assertTrue((result["trash"] / ".claude/CLAUDE.md").is_symlink())
        self.assertEqual((repo / "claude/CLAUDE.md").read_text(), "# Updated\n")

    def test_help_and_never_deployed_state_line(self):
        completed = subprocess.run([sys.executable, str(SCRIPT), "--help"], env=ENV, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("install", completed.stdout)
        repo, home = fixture()
        completed = cli(repo, home, "check")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("STATE   never deployed on this machine", completed.stdout)
        self.assertIn("MISSING", completed.stdout)


if __name__ == "__main__":
    unittest.main()
