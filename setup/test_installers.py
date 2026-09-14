"""installers: source parsing, CLI invocations and git-backed skill installs in an isolated home."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import installers as inst


class FakeResult:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ai-global-installers-"))
        self.home = self.root / "home"
        self.home.mkdir()
        self.trash = self.home / ".ai-trash/test"
        self.calls = []

    def fake_run(self, args, **kwargs):
        self.calls.append(list(args))
        if args[:2] == ["git", "clone"]:
            return subprocess.run(args, **kwargs)  # real git against the local fixture repo
        if args[:2] == ["git", "-C"]:
            return subprocess.run(args, **kwargs)
        return FakeResult()

    def fixture_repo(self):
        src = self.root / "upstream"
        (src / "skills/demo").mkdir(parents=True)
        (src / "skills/demo/SKILL.md").write_text("---\nname: demo\n---\n# Demo\n", encoding="utf-8")
        (src / "skills/demo/ref.txt").write_text("v1\n", encoding="utf-8")
        for args in (["init", "-q"], ["add", "."], ["-c", "user.name=f", "-c", "user.email=f@example.invalid", "commit", "-q", "-m", "one"]):
            subprocess.run(["git", "-C", str(src)] + args, check=True, capture_output=True)
        return src

    def test_source_parsing(self):
        self.assertEqual(inst.parse_source({"source": "repo:claude/skills/x"}), ("repo", None))
        self.assertEqual(inst.parse_source({"source": "marketplace claude-plugins-official"}), ("marketplace", None))
        self.assertEqual(inst.parse_source({"source": "marketplace github:a/b"}), ("marketplace", "a/b"))
        self.assertEqual(inst.parse_source({"source": "github:a/b"}), ("github", "a/b"))
        self.assertEqual(inst.parse_source({"source": "ftp://x"}), ("unknown", None))

    def test_plugin_install_uses_each_tools_cli(self):
        item = {"tool": "claude", "type": "plugin", "id": "p@m", "source": "marketplace github:a/b"}
        self.assertEqual(inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None), "installed")
        self.assertEqual(self.calls, [["claude", "plugin", "marketplace", "add", "a/b"], ["claude", "plugin", "install", "p@m"]])
        self.calls.clear()
        item = {"tool": "codex", "type": "plugin", "id": "p@claude-plugins-official", "source": "marketplace claude-plugins-official"}
        inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None)
        self.assertEqual(self.calls, [["codex", "plugin", "add", "p@claude-plugins-official"]])

    def test_plugin_install_failure_is_reported_not_raised_as_crash(self):
        item = {"tool": "claude", "type": "plugin", "id": "p@m", "source": "marketplace m"}
        with self.assertRaises(inst.InstallError):
            inst.install_item(item, self.home, trash=self.trash, run=lambda *a, **k: FakeResult(1, "", "boom"), echo=lambda *_: None)

    def test_dry_run_and_repo_source_touch_nothing(self):
        before = sorted(self.root.rglob("*"))
        item = {"tool": "claude", "type": "skill", "id": "s", "source": "github:a/b", "path": "skills/s"}
        self.assertEqual(inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None, dry_run=True), "planned")
        self.assertEqual(inst.install_item({"tool": "claude", "type": "skill", "id": "ai-global", "source": "repo:x"}, self.home, trash=self.trash, echo=lambda *_: None), "skipped")
        self.assertEqual(before, sorted(self.root.rglob("*")))
        self.assertEqual(self.calls, [])

    def test_github_skill_installs_replaces_and_respects_parked_copy(self):
        src = self.fixture_repo()
        item = {"tool": "claude", "type": "skill", "id": "demo", "source": "github:up/stream", "path": "skills/demo"}
        with patch.object(inst, "repo_url", lambda spec: str(src)):
            self.assertEqual(inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None), "installed")
            target = self.home / ".claude/skills/demo"
            self.assertEqual((target / "ref.txt").read_text(), "v1\n")
            marker = json.loads((target / inst.MARKER).read_text(encoding="utf-8"))
            self.assertEqual(marker["source"], "github:up/stream")
            self.assertEqual(len(marker["commit"]), 7)
            # Same content again -> nothing replaced.
            self.assertEqual(inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None), "same")
            # Local edit -> old copy goes to trash, fresh copy installed.
            (target / "ref.txt").write_text("edited\n")
            self.assertEqual(inst.install_item(item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None), "installed")
            self.assertEqual((target / "ref.txt").read_text(), "v1\n")
            self.assertTrue(any(p.read_text() == "edited\n" for p in self.trash.rglob("ref.txt")))
            # A parked (disabled) copy is updated in place, not duplicated.
            parked = self.home / ".claude/ai-global-disabled/skills/demo"
            parked.mkdir(parents=True)
            (parked / "SKILL.md").write_text("old")
            codex_item = dict(item, tool="codex", id=".codex/skills/demo")
            inst.install_item(codex_item, self.home, trash=self.trash, run=self.fake_run, echo=lambda *_: None)
            self.assertTrue((self.home / ".codex/skills/demo/SKILL.md").is_file())
            self.assertEqual(inst.skill_target(item, self.home), parked)
        # All clones live inside the trash: nothing was ever deleted.
        self.assertTrue(list(self.trash.glob("checkout-up-stream-*")))

    def test_move_to_trash_refuses_paths_outside_home(self):
        outside = self.root / "elsewhere.txt"
        outside.write_text("x")
        with self.assertRaises(inst.InstallError):
            inst.move_to_trash(outside, self.home, self.trash)
        self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
