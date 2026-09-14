"""Isolated fixtures are retained in the OS temp directory; no user settings touched."""

import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import capabilities as cap


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ai-global-capabilities-test-"))
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.write(self.repo / "manifest/skills.json", json.dumps({"items": [
            {"tool": "claude", "type": "skill", "id": "owned", "default_enabled": True},
            {"tool": "claude", "type": "plugin", "id": "missing@market", "default_enabled": False},
        ]}))

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def rows(self):
        return {(r["tool"], r["kind"], r["id"]): r for r in cap.inventory(self.repo, self.home)}

    def test_inventory_distinguishes_origin_missing_and_disabled(self):
        self.write(self.home / ".claude/ai-global-disabled/skills/owned/SKILL.md", "# Owned")
        self.write(self.home / ".claude/skills/extra/SKILL.md", "# Extra")
        rows = self.rows()
        owned = rows["claude", "skill", "owned"]
        self.assertEqual(owned["origin"], "project-default")
        self.assertTrue(owned["default_enabled"])
        self.assertFalse(owned["enabled"])
        self.assertEqual(rows["claude", "skill", "extra"]["origin"], "local-existing")
        self.assertFalse(rows["claude", "plugin", "missing@market"]["installed"])

    def test_listing_creates_nothing(self):
        before = sorted(self.root.rglob("*"))
        self.rows()
        self.assertEqual(before, sorted(self.root.rglob("*")))

    def test_table_aligns_terminal_columns_with_cjk_and_long_ids(self):
        rows = [dict(tool="claude", kind="skill", id="短名", origin="project-default",
                     default_enabled=True, installed=True, enabled=False),
                dict(tool="codex", kind="plugin", id="long-plugin-name@marketplace",
                     origin="local-existing", default_enabled=None, installed=None, enabled=True)]
        lines = cap.capability_table(rows).splitlines()
        self.assertNotIn("\t", "\n".join(lines))
        offsets = []
        for line, markers in ((lines[0], ["種類", "ID", "來源", "專案預設", "安裝", "本機開關"]),
                              (lines[2], ["skill", "短名", "專案預設", "是", "是", "否"]),
                              (lines[3], ["plugin", "long-plugin-name@marketplace", "本機既有", "未知", "未知", "是"])):
            start = 0
            positions = []
            for marker in markers:
                pos = line.index(marker, start)
                positions.append(cap.display_width(line[:pos]))
                start = pos + len(marker)
            offsets.append(positions)
        self.assertEqual(offsets[0], offsets[1])
        self.assertEqual(offsets[0], offsets[2])
        self.assertIn(rows[1]["id"], lines[3])
        self.assertEqual(cap.display_width("中文Ａe\u0301"), 7)

    def test_empty_table_keeps_header_and_json_output_remains_parseable(self):
        self.assertEqual(len(cap.capability_table([]).splitlines()), 2)
        with redirect_stdout(io.StringIO()) as output:
            result = cap.main(["list", "--repo", str(self.repo), "--home", str(self.home), "--json"])
        self.assertEqual(result, 0)
        self.assertIsInstance(json.loads(output.getvalue()), list)

    def test_claude_skill_and_command_roundtrip_preserves_bytes(self):
        for kind, folder, filename in (("skill", "skills", "owned/SKILL.md"), ("command", "commands", "extra.md")):
            with self.subTest(kind=kind):
                identifier = "owned" if kind == "skill" else "extra"
                path = self.home / ".claude" / folder / filename
                self.write(path, "unique payload\n")
                cap.toggle(self.repo, self.home, "claude", kind, identifier, False)
                self.assertFalse(path.exists())
                self.assertFalse(self.rows()["claude", kind, identifier]["enabled"])
                cap.toggle(self.repo, self.home, "claude", kind, identifier, True)
                self.assertEqual(path.read_text(), "unique payload\n")

    def test_duplicate_active_and_parked_rejected(self):
        for base in ("skills", "ai-global-disabled/skills"):
            self.write(self.home / ".claude" / base / "owned/SKILL.md", "# skill")
        with self.assertRaises(cap.ControlError):
            self.rows()

    def test_unknown_or_uninstalled_target_not_created(self):
        for kind, identifier in (("skill", "../../outside"), ("plugin", "missing@market")):
            with self.assertRaises(cap.ControlError):
                cap.toggle(self.repo, self.home, "claude", kind, identifier, True)
        self.assertFalse(self.home.exists())

    def test_codex_plugin_preserves_other_config_and_comments(self):
        path = self.home / ".codex/config.toml"
        text = '# header\nmodel = "kept"\n[plugins."superpowers@market"]\n# comment\nenabled = true # note\n[other]\nvalue = 5\n'
        self.write(path, text)
        cap.toggle(self.repo, self.home, "codex", "plugin", "superpowers@market", False)
        changed = path.read_text()
        expected = tomllib.loads(text)
        expected["plugins"]["superpowers@market"]["enabled"] = False
        self.assertEqual(tomllib.loads(changed), expected)
        self.assertIn("# comment", changed)
        self.assertIn("# note", changed)
        self.assertEqual(next((self.home / ".ai-trash").glob("*/config.toml")).read_text(), text)

    def test_claude_plugin_preserves_unrelated_settings(self):
        path = self.home / ".claude/settings.json"
        original = {"env": {"secret": "SENTINEL"}, "enabledPlugins": {"p@m": True, "other@m": False}}
        self.write(path, json.dumps(original))
        self.write(self.home / ".claude/plugins/installed_plugins.json", json.dumps({"plugins": {"p@m": [{"scope": "user"}]}}))
        result = cap.toggle(self.repo, self.home, "claude", "plugin", "p@m", False)
        expected = copy.deepcopy(original)
        expected["enabledPlugins"]["p@m"] = False
        self.assertEqual(json.loads(path.read_text()), expected)
        self.assertNotIn("SENTINEL", result)

    def test_other_scope_plugin_not_modified(self):
        self.write(self.home / ".claude/plugins/installed_plugins.json", json.dumps({"plugins": {"p@m": [{"scope": "project"}]}}))
        with self.assertRaises(cap.ControlError):
            cap.toggle(self.repo, self.home, "claude", "plugin", "p@m", False)

    def test_codex_skill_both_roots_and_existing_file_path_override(self):
        for root in (".codex/skills", ".agents/skills"):
            self.write(self.home / root / "extra/SKILL.md", "# skill")
        path = self.home / ".codex/config.toml"
        skill_path = self.home / ".codex/skills/extra/SKILL.md"
        self.write(path, 'model = "kept"\n[[skills.config]]\npath = ' + json.dumps(str(skill_path)) + '\nenabled = true\n')
        for root in (".codex/skills", ".agents/skills"):
            identifier = root + "/extra"
            cap.toggle(self.repo, self.home, "codex", "skill", identifier, False)
            self.assertFalse(self.rows()["codex", "skill", identifier]["enabled"])
            cap.toggle(self.repo, self.home, "codex", "skill", identifier, True)
            self.assertTrue(self.rows()["codex", "skill", identifier]["enabled"])
        self.assertEqual(len(tomllib.loads(path.read_text())["skills"]["config"]), 2)

    def test_builtin_hidden_skills_not_exposed(self):
        self.write(self.home / ".codex/skills/.system/SKILL.md", "# system")
        self.assertFalse(any(r["kind"] == "skill" and r["tool"] == "codex" for r in self.rows().values()))

    def test_codex_plugin_installation_remains_unknown(self):
        self.write(self.home / ".codex/config.toml", '[plugins."p@m"]\nenabled = false\n')
        row = self.rows()["codex", "plugin", "p@m"]
        self.assertIsNone(row["installed"])
        self.assertFalse(row["enabled"])

    def test_noop_does_not_backup_or_rewrite(self):
        path = self.home / ".codex/config.toml"
        self.write(path, '[plugins."p@m"]\nenabled = false\n')
        cap.toggle(self.repo, self.home, "codex", "plugin", "p@m", False)
        self.assertFalse((self.home / ".ai-trash").exists())

    def test_invalid_configuration_errors_never_echo_contents(self):
        for name, text in ((".claude/settings.json", '{"secret":"SENTINEL", broken'), (".codex/config.toml", 'secret="SENTINEL"\nbroken')):
            with self.subTest(name=name):
                path = self.home / name
                self.write(path, text)
                with self.assertRaises(cap.ControlError) as context:
                    self.rows()
                self.assertNotIn("SENTINEL", str(context.exception))
                self.write(path, "{}" if name.endswith("json") else "")

    def test_concurrent_setting_change_is_not_overwritten(self):
        path = self.home / ".codex/config.toml"
        self.write(path, 'value = "newer"\n')
        with self.assertRaises(cap.ControlError):
            cap.safe_write(path, 'value = "old"\n', 'value = "ours"\n', self.home)
        self.assertEqual(path.read_text(), 'value = "newer"\n')

    def test_unsupported_toml_layout_fails_without_rewrite(self):
        text = 'plugins = { "p@m" = { enabled = true } }\n'
        with self.assertRaises(cap.ControlError):
            cap.toml_enable(text, "plugin", "p@m", False, self.home)

    def test_duplicate_manifest_identity_fails(self):
        path = self.repo / "manifest/skills.json"
        data = json.loads(path.read_text())
        data["items"].append(data["items"][0])
        self.write(path, json.dumps(data))
        with self.assertRaises(cap.ControlError):
            self.rows()


if __name__ == "__main__":
    unittest.main()
