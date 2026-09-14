"""align: end-to-end against an isolated repo + home with a fake tool CLI."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import align
import capabilities as cap
import installers


class FakeResult:
    def __init__(self, code=0, out=""):
        self.returncode, self.stdout, self.stderr = code, out, ""


class AlignTests(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp(prefix="ai-global-align-"))
        self.repo, self.home = base / "repo", base / "home"
        for folder in ("governance", "claude/skills/ai-global", "codex", "manifest"):
            (self.repo / folder).mkdir(parents=True)
        (self.repo / "governance/20-judgment.md").write_text("# rule v2\n", encoding="utf-8")
        (self.repo / "claude/CLAUDE.md").write_text("# router\n", encoding="utf-8")
        (self.repo / "codex/AGENTS.md").write_text("# router\n", encoding="utf-8")
        (self.repo / "claude/skills/ai-global/SKILL.md").write_text("# ai-global\n", encoding="utf-8")
        self.manifest = {"items": [
            {"tool": "claude", "type": "skill", "id": "ai-global", "default_enabled": True, "source": "repo:claude/skills/ai-global"},
            {"tool": "claude", "type": "plugin", "id": "wanted@m", "default_enabled": True, "source": "marketplace github:o/m"},
            {"tool": "claude", "type": "skill", "id": "parked", "default_enabled": True, "source": "github:o/s", "path": "skills/parked"},
        ]}
        (self.repo / "manifest/skills.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        self.cli_calls = []
        self.echo_lines = []
        self.codex_cli = None  # what `codex plugin list` would report; None = CLI unavailable

    def echo(self, line=""):
        self.echo_lines.append(str(line))

    def fake_run(self, args, **kwargs):
        args = [Path(args[0]).stem, *args[1:]]  # run_cli resolves the CLI to a full path
        self.cli_calls.append(list(args))
        if args[0] == "claude" and args[1:3] == ["plugin", "install"]:
            # Emulate the CLI registering the plugin.
            registry = self.home / ".claude/plugins/installed_plugins.json"
            data = cap.read_json(registry) if registry.exists() else {"plugins": {}}
            data.setdefault("plugins", {})[args[3]] = [{"scope": "user", "version": "1.0.0"}]
            registry.parent.mkdir(parents=True, exist_ok=True)
            registry.write_text(json.dumps(data), encoding="utf-8")
        return FakeResult()

    def run_align(self, **kwargs):
        with patch.object(installers, "subprocess") as sp, patch.object(cap, "claude_cli_plugins", lambda home: None),                 patch.object(cap, "codex_cli_plugins", lambda home: self.codex_cli):
            sp.run = self.fake_run
            sp.SubprocessError = subprocess.SubprocessError
            return align.run(self.repo, self.home, no_pull=True, tui=False, echo=self.echo, **kwargs)

    def test_plan_is_read_only_and_lists_everything(self):
        (self.home / ".claude/skills/stray/SKILL.md").parent.mkdir(parents=True)
        (self.home / ".claude/skills/stray/SKILL.md").write_text("# stray")
        before = sorted(p for p in self.home.rglob("*"))
        summary = self.run_align(plan=True)
        self.assertEqual(before, sorted(p for p in self.home.rglob("*")))
        self.assertEqual(self.cli_calls, [])
        self.assertIn("wanted@m", summary["missing"])
        self.assertEqual([c["kind"] for c in summary["conflicts"]], ["extra"])
        output = "\n".join(self.echo_lines)
        self.assertIn("--plan，唯讀", output)
        self.assertIn("MISSING", output)
        self.assertIn("INSTALL", output)
        self.assertIn("CONFLICT 1 項", output)
        self.assertIn("DONE     1 項衝突待決", output)

    def test_yes_deploys_installs_and_reports_conflicts_without_touching_them(self):
        stray = self.home / ".claude/skills/stray/SKILL.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("# stray")
        with patch.object(installers, "repo_url", lambda spec: "file:///nonexistent"):
            summary = self.run_align(yes=True)
        self.assertTrue((self.home / ".ai-global/governance/20-judgment.md").is_file())
        self.assertIn(["claude", "plugin", "marketplace", "add", "o/m"], self.cli_calls)
        self.assertIn(["claude", "plugin", "install", "wanted@m"], self.cli_calls)
        self.assertTrue(stray.exists())  # extra: default keep, never applied without a choice
        self.assertEqual([c["kind"] for c in summary["unresolved"]], ["extra"])
        # The git-backed skill could not be fetched (fake CLI clones nothing): a failure, not a crash.
        self.assertTrue(any("SKILL.md" in f for f in summary["failures"]))

    def test_edited_keep_and_writeback_are_honoured_before_deploy(self):
        self.run_align(yes=True)  # first deploy
        rule = self.home / ".ai-global/governance/20-judgment.md"
        router = self.home / ".claude/CLAUDE.md"
        rule.write_text("# local edit\n", encoding="utf-8")
        router.write_text("# router local\n", encoding="utf-8")
        (self.repo / "governance/20-judgment.md").write_text("# rule v3\n", encoding="utf-8")
        summary = self.run_align(yes=True, resolve={
            "edited:~/.ai-global/governance/20-judgment.md": "keep", "edited:~/.claude/CLAUDE.md": "writeback"})
        self.assertEqual(rule.read_text(encoding="utf-8"), "# local edit\n")
        self.assertEqual((self.repo / "claude/CLAUDE.md").read_text(encoding="utf-8"), "# router local\n")
        self.assertEqual(summary["unresolved"], [])
        kept = [r for r in summary["deploy"]["results"] if r[0] == "KEEP"]
        self.assertEqual(len(kept), 1)
        # Overwrite: repo wins and the local copy lands in the trash.
        summary = self.run_align(yes=True, resolve={"edited:~/.ai-global/governance/20-judgment.md": "overwrite"})
        self.assertEqual(rule.read_text(encoding="utf-8"), "# rule v3\n")
        self.assertTrue(any(p.read_text(encoding="utf-8") == "# local edit\n" for p in (self.home / ".ai-trash").rglob("20-judgment.md")))

    def test_extra_duplicate_switch_and_hook_actions(self):
        self.run_align(yes=True)
        # extra -> trash; duplicate (skill bundled in enabled plugin) -> trash; switch -> enable; hook -> unwire
        (self.home / ".claude/skills/stray/SKILL.md").parent.mkdir(parents=True)
        (self.home / ".claude/skills/stray/SKILL.md").write_text("# stray")
        bundled = self.home / ".claude/plugins/cache/m/wanted/1.0.0/skills/dupe"
        bundled.mkdir(parents=True)
        (bundled / "SKILL.md").write_text("# bundled")
        registry = self.home / ".claude/plugins/installed_plugins.json"
        data = cap.read_json(registry)
        data["plugins"]["wanted@m"][0]["installPath"] = str(bundled.parents[1])
        registry.write_text(json.dumps(data), encoding="utf-8")
        (self.home / ".claude/skills/dupe/SKILL.md").parent.mkdir(parents=True)
        (self.home / ".claude/skills/dupe/SKILL.md").write_text("# standalone")
        settings = {"enabledPlugins": {"wanted@m": True},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "bash ~/.claude/hooks/gone.sh"}]}]}}
        (self.home / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
        # switch: manifest recommends "parked" enabled, but it sits in the disabled folder
        parked = self.home / ".claude/ai-global-disabled/skills/parked/SKILL.md"
        parked.parent.mkdir(parents=True)
        parked.write_text("# parked")
        summary = self.run_align(yes=True)
        kinds = sorted(c["kind"] for c in summary["conflicts"])
        self.assertEqual(kinds, ["duplicate", "extra", "hook", "switch"])
        summary = self.run_align(yes=True, resolve={
            "claude:skill:stray": "trash", "claude:skill:dupe": "trash",
            "claude:skill:parked": "enable", "hook:Stop:bash ~/.claude/hooks/gone.sh": "unwire"})
        self.assertEqual(summary["unresolved"], [])
        self.assertEqual(summary["failures"], [])
        self.assertFalse((self.home / ".claude/skills/stray").exists())
        self.assertFalse((self.home / ".claude/skills/dupe").exists())
        self.assertTrue((self.home / ".ai-trash").rglob("stray"))
        after = cap.read_json(self.home / ".claude/settings.json")
        self.assertTrue((self.home / ".claude/skills/parked/SKILL.md").is_file())
        self.assertFalse(parked.exists())
        self.assertNotIn("Stop", after.get("hooks", {}))
        self.assertTrue(any(p.name == "settings.json.before-unwire" for p in (self.home / ".ai-trash").rglob("*")))

    def test_tool_shipped_plugins_are_not_conflicts_and_plugins_cannot_be_trashed(self):
        self.run_align(yes=True)
        registry = self.home / ".claude/plugins/installed_plugins.json"
        data = cap.read_json(registry)
        data["plugins"]["design@inline"] = [{"scope": "user", "version": "1.0.0"}]   # Claude desktop built-in
        data["plugins"]["stray@m"] = [{"scope": "user", "version": "1.0.0"}]        # a real extra plugin
        registry.write_text(json.dumps(data), encoding="utf-8")
        summary = self.run_align(yes=True)
        extras = {c["key"]: c for c in summary["conflicts"] if c["kind"] == "extra"}
        self.assertNotIn("claude:plugin:design@inline", extras)
        self.assertEqual(extras["claude:plugin:stray@m"]["actions"], ["keep", "disable"])
        summary = self.run_align(yes=True, resolve={"claude:plugin:stray@m": "trash"})
        self.assertTrue(any("不支援動作" in f for f in summary["failures"]))

    def test_version_update_refreshes_marketplace_and_only_claude_is_compared(self):
        self.run_align(yes=True)
        registry = self.home / ".claude/plugins/installed_plugins.json"
        data = cap.read_json(registry)
        data["plugins"]["wanted@m"][0]["version"] = "0.9.0"
        registry.write_text(json.dumps(data), encoding="utf-8")
        self.manifest["items"][1]["version"] = "1.0.0"
        self.manifest["items"].append({"tool": "codex", "type": "plugin", "id": "wanted@m", "default_enabled": True,
                                       "source": "marketplace github:o/m", "version": "1.0.0"})
        (self.repo / "manifest/skills.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.home / ".codex").mkdir(exist_ok=True)
        (self.home / ".codex/config.toml").write_text('[plugins."wanted@m"]\nenabled = true\n', encoding="utf-8")
        summary = self.run_align(yes=True)
        self.assertEqual([c["key"] for c in summary["conflicts"] if c["kind"] == "version"], ["claude:plugin:wanted@m"])
        # With the Codex CLI reporting an older install, the Codex row gets its own version conflict.
        self.codex_cli = {"wanted@m": (True, "0.9.0")}
        summary = self.run_align(yes=True)
        self.assertEqual(sorted(c["key"] for c in summary["conflicts"] if c["kind"] == "version"),
                         ["claude:plugin:wanted@m", "codex:plugin:wanted@m"])
        self.codex_cli = None
        self.cli_calls.clear()
        summary = self.run_align(yes=True, resolve={"claude:plugin:wanted@m": "update"})
        self.assertFalse([f for f in summary["failures"] if "wanted@m" in f])  # parked's fake clone failing is fixture noise
        self.assertIn(["claude", "plugin", "marketplace", "update", "m"], self.cli_calls)
        self.assertIn(["claude", "plugin", "update", "wanted@m"], self.cli_calls)  # install is a no-op when installed
        self.assertLess(self.cli_calls.index(["claude", "plugin", "marketplace", "update", "m"]),
                        self.cli_calls.index(["claude", "plugin", "update", "wanted@m"]))

    def test_unknown_action_is_reported(self):
        (self.home / ".claude/skills/stray/SKILL.md").parent.mkdir(parents=True)
        (self.home / ".claude/skills/stray/SKILL.md").write_text("# stray")
        summary = self.run_align(yes=True, resolve={"claude:skill:stray": "explode"})
        self.assertTrue(any("不支援動作" in f for f in summary["failures"]))
        self.assertTrue((self.home / ".claude/skills/stray").exists())


class TuiBootstrapTests(unittest.TestCase):
    """ensure_tui: builds .venv on a yes, re-runs inside it, never loops."""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="ai-global-venv-"))
        self.python = align.venv_python(self.repo)
        self.calls, self.lines = [], []
        self.venv_has_tui = False

    def fake_run(self, args, **kwargs):
        self.calls.append(list(args))
        if args[1:2] == ["-c"]:  # probe: does the venv python import prompt_toolkit?
            return FakeResult(0 if self.venv_has_tui else 1)
        if args[1:3] == ["-m", "venv"]:  # emulate venv creation
            self.python.parent.mkdir(parents=True, exist_ok=True)
            self.python.write_text("")
        if args[1:4] == ["-m", "pip", "install"]:
            self.venv_has_tui = True
        return FakeResult(7 if str(args[1]).endswith("align.py") else 0)  # 7 = exit code of the re-run

    def ensure(self, answer="y", env=None):
        with patch.object(align, "has_tui", lambda python=None, run=None: self.venv_has_tui if python else False):
            return align.ensure_tui(self.repo, ["--no-pull"], ask=lambda _: answer, run=self.fake_run,
                                    echo=self.lines.append, env=env or {})

    def test_yes_creates_venv_installs_and_reruns(self):
        code = self.ensure("")
        self.assertEqual(code, 7)
        self.assertEqual(self.calls[0][1:3], ["-m", "venv"])
        self.assertEqual(self.calls[1][:4], [str(self.python), "-m", "pip", "install"])
        rerun = self.calls[-1]
        self.assertEqual(rerun[0], str(self.python))
        self.assertTrue(rerun[1].endswith("align.py"))
        self.assertEqual(rerun[2:], ["--no-pull"])

    def test_no_keeps_text_mode_and_touches_nothing(self):
        self.assertIsNone(self.ensure("n"))
        self.assertEqual(self.calls, [])
        self.assertFalse((self.repo / ".venv").exists())
        self.assertTrue(any("--resolve" in line for line in self.lines))

    def test_existing_venv_is_reused_without_asking(self):
        self.python.parent.mkdir(parents=True)
        self.python.write_text("")
        self.venv_has_tui = True
        self.assertEqual(self.ensure("n"), 7)  # "n" never consulted: no prompt when the venv is ready
        self.assertEqual(len(self.calls), 1)

    def test_rerun_never_bootstraps_again(self):
        self.assertIsNone(self.ensure("y", env={align.REEXEC_FLAG: "1"}))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
