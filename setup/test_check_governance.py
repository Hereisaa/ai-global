"""Negative-path checks use memory fixtures and never create or delete files."""

from contextlib import ExitStack, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("check_governance", Path(__file__).with_name("check_governance.py"))
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

CODEX, CLAUDE = checker.ROUTERS


def router(title, prefix, claude_only=False):
    routes = "\n".join(f"- `{name}`" for name in checker.GOVERNANCE_FILES)
    text = (
        f"# {title}\n"
        f"## 多 session\n- 一律用 **`{prefix}`**\n"
        f"## 制度路由\n制度檔在 `{checker.ROUTE_PREFIX}`：\n{routes}\n"
    )
    if claude_only:
        text += "## Cowork / 多端一致\n本檔\n"
    return text


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/virtual/ai-global").resolve()
        self.files = {}
        self.files[self.root / CODEX] = router("AGENTS", checker.TOOL_PREFIX[CODEX])
        self.files[self.root / CLAUDE] = router("CLAUDE", checker.TOOL_PREFIX[CLAUDE], claude_only=True)
        for name in checker.GOVERNANCE_DOCUMENTS:
            self.files[self.root / "governance" / name] = "# 制度\n"
        self.files[self.root / "README.md"] = "# 倉庫\n"
        self.files[self.root / checker.RUNTIME_DOC] = "# 執行環境\n"
        self.files[self.root / checker.SYNC_SKILL] = "---\nname: ai-global\n---\n\n# ai-global\n"
        self.manifest_path = self.root / "manifest/settings.json"
        self.files[self.manifest_path] = json.dumps({
            "claude_settings": {},
            "codex_config": {"model_reasoning_effort": "ultra", "personality": "pragmatic"},
        })
        self.checks = checker.Checks()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Path, "read_text", lambda path, **kwargs: self.read(path, **kwargs)))
        self.stack.enter_context(patch.object(Path, "is_file", lambda path: path in self.files))
        self.stack.enter_context(patch.object(Path, "exists", lambda path: Path(os.path.normpath(path)) in self.files))
        self.stack.enter_context(patch.object(Path, "glob", lambda path, pattern: self.glob(path, pattern)))

    def read(self, path, **kwargs):
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def glob(self, path, pattern):
        return (p for p in self.files if p.parent == path and p.match(pattern))

    def run_repository(self):
        self.checks.repository(self.root)
        return self.checks.exit_code

    def output(self):
        return "\n".join(f"{status} {message}" for status, message in self.checks.results)

    def test_complete_repository_passes(self):
        self.assertEqual(self.run_repository(), 0)
        self.assertNotIn("WARN", self.output())
        self.assertIn("節次對齊", self.output())

    def test_section_drift_fails(self):
        self.files[self.root / CODEX] += "## 只有一邊有的節\n內容\n"
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("節次不對齊", self.output())

    def test_claude_only_cowork_section_is_allowed(self):
        self.files[self.root / CLAUDE] = router("CLAUDE", checker.TOOL_PREFIX[CLAUDE], claude_only=False)
        self.assertEqual(self.run_repository(), 0)
        self.files[self.root / CLAUDE] = router("CLAUDE", checker.TOOL_PREFIX[CLAUDE], claude_only=True)
        self.checks = checker.Checks()
        self.assertEqual(self.run_repository(), 0)

    def test_copied_prefix_from_other_tool_fails(self):
        self.files[self.root / CODEX] = router("AGENTS", checker.TOOL_PREFIX[CLAUDE])
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("照抄了對面工具的分支前綴", self.output())
        self.assertIn("缺少本工具的分支前綴", self.output())

    def test_mentioning_other_prefix_as_contrast_passes(self):
        self.files[self.root / CODEX] = self.files[self.root / CODEX].replace(
            "- 一律用 **`codex/<主題>`**",
            "- 一律用 **`codex/<主題>`**（Claude Code 側用 `claude/<主題>`）",
        )
        self.assertEqual(self.run_repository(), 0)

    def test_missing_route_even_in_fenced_example_fails(self):
        for name in checker.ROUTERS:
            path = self.root / name
            self.files[path] = self.files[path].replace("- `10-dispatch.md`", "```\n- `10-dispatch.md`\n```")
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("缺少制度路由", self.output())

    def test_missing_route_prefix_fails(self):
        for name in checker.ROUTERS:
            path = self.root / name
            self.files[path] = self.files[path].replace(checker.ROUTE_PREFIX, "~/somewhere/else/")
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("缺少制度目錄路徑", self.output())

    def test_missing_governance_target_fails(self):
        self.files.pop(self.root / "governance/10-dispatch.md")
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("必要文件不存在", self.output())

    def test_missing_runtime_document_fails(self):
        self.files.pop(self.root / checker.RUNTIME_DOC)
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("必要文件不存在", self.output())

    def test_each_required_guide_and_skill_must_exist(self):
        for name in ("README.md", "governance/README.md", "governance/USER-GUIDE.md", checker.SYNC_SKILL):
            with self.subTest(name=name):
                original = self.files.pop(self.root / name)
                self.checks = checker.Checks()
                self.assertEqual(self.run_repository(), 1)
                self.assertIn("必要文件不存在", self.output())
                self.files[self.root / name] = original

    def test_blank_governance_and_runtime_fail(self):
        for name in ("governance/50-safety.md", checker.RUNTIME_DOC):
            with self.subTest(name=name):
                original = self.files[self.root / name]
                self.files[self.root / name] = " \n\t\n"
                self.checks = checker.Checks()
                self.assertEqual(self.run_repository(), 1)
                self.assertIn("文件內容空白", self.output())
                self.files[self.root / name] = original

    def test_non_markdown_and_empty_title_fail(self):
        path = self.root / "governance/50-safety.md"
        for text in ("<!doctype html><html>wrong response</html>", "{}", "# \n"):
            with self.subTest(text=text):
                self.files[path] = text
                self.checks = checker.Checks()
                self.assertEqual(self.run_repository(), 1)
                self.assertIn("文件缺少首行標題", self.output())

    def test_skill_frontmatter_requires_following_title(self):
        self.files[self.root / checker.SYNC_SKILL] = "---\nname: ai-global\n---\nmissing heading\n"
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("文件缺少首行標題", self.output())

    def test_required_directory_cannot_substitute_for_file(self):
        missing_file = self.root / checker.RUNTIME_DOC
        with patch.object(Path, "is_file", lambda path: path in self.files and path != missing_file):
            self.assertEqual(self.run_repository(), 1)
        self.assertIn("不是檔案", self.output())

    def test_reference_readme_router_and_skill_links_are_checked(self):
        for name in (checker.RUNTIME_DOC, "docs/reference/new-guide.md", "README.md", CODEX, checker.SYNC_SKILL):
            with self.subTest(name=name):
                path = self.root / name
                original = self.files.get(path)
                self.files[path] = (original or "# 參考\n") + "[broken](absent.md#fragment)\n"
                self.checks = checker.Checks()
                self.assertEqual(self.run_repository(), 1)
                self.assertIn(f"相對連結斷鏈：{name}:", self.output())
                if original is None:
                    self.files.pop(path)
                else:
                    self.files[path] = original

    def test_runtime_relative_parent_link_is_resolved(self):
        self.files[self.root / checker.RUNTIME_DOC] += "[policy](../../governance/50-safety.md#section)\n"
        self.assertEqual(self.run_repository(), 0)

    def test_skill_command_links_are_checked(self):
        self.files[self.root / "claude/skills/ai-global/commands/capabilities.md"] = "# Capabilities\n[broken](absent.md)\n"
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("commands/capabilities.md:2", self.output())

    def test_deployed_external_links_use_source_repo_not_home(self):
        path = Path("/virtual/home/.ai-global/governance/10-dispatch.md")
        self.checks.links(path, "deployed", "[runtime](../docs/reference/agent-runtime.md)",
                          deployed=True, source_repo=self.root)
        self.assertEqual(self.checks.results, [])
        self.checks.links(path, "deployed", "[missing](../docs/reference/missing.md)",
                          deployed=True, source_repo=self.root)
        self.assertEqual(self.checks.exit_code, 1)

    def test_deployed_internal_links_stay_in_deployment(self):
        path = Path("/virtual/home/.ai-global/governance/10-dispatch.md")
        self.checks.links(path, "deployed", "[policy](20-judgment.md)",
                          deployed=True, source_repo=self.root)
        self.assertEqual(self.checks.exit_code, 1)

    def test_deployed_external_link_without_state_is_unverified(self):
        path = Path("/virtual/home/.ai-global/governance/10-dispatch.md")
        self.checks.links(path, "deployed", "[runtime](../docs/reference/agent-runtime.md)", deployed=True)
        self.assertIn("WARN 無法驗證跨目錄連結", self.output())

    def test_disabled_ai_global_is_used_by_local_check(self):
        home = Path("/virtual/home")
        disabled = home / ".claude/ai-global-disabled/skills/ai-global/SKILL.md"
        self.files[disabled] = self.files[self.root / checker.SYNC_SKILL]
        with patch.object(self.checks, "deployment") as deployed, patch.object(self.checks, "deployed_links"):
            self.checks.local(self.root, home, None)
        deployed.assert_any_call(self.root / checker.SYNC_SKILL, disabled)

    def test_unscoped_and_backup_documents_are_not_scanned(self):
        for name in ("other/invalid.md", "governance/backups/old.md", "docs/reference/backups/old.md"):
            self.files[self.root / name] = "[broken](absent.md)\n"
        self.assertEqual(self.run_repository(), 0)

    def test_broken_relative_link_reports_original_line(self):
        self.files[self.root / "governance/10-dispatch.md"] += "\n[missing](absent.md#section)\n"
        self.assertEqual(self.run_repository(), 1)
        self.assertIn("governance/10-dispatch.md:3", self.output())

    def test_existing_target_with_fragment_passes(self):
        self.files[self.root / "governance/10-dispatch.md"] += "[rule](20-judgment.md#任意片段)\n[here](#本頁)\n"
        self.assertEqual(self.run_repository(), 0)

    def test_url_fence_inline_example_and_archive_are_ignored(self):
        self.files[self.root / "governance/10-dispatch.md"] += (
            "```markdown\n[example](absent.md)\n```\n"
            "~~~\n[example](also-absent.md)\n~~~\n"
            "`[example](inline-absent.md)`\n"
            "[remote](https://example.invalid/no.md)\n"
            "[history](backups/old.md)\n"
        )
        self.assertEqual(self.run_repository(), 0)

    def test_reference_style_broken_target_fails(self):
        self.files[self.root / "governance/10-dispatch.md"] += "[rule]: absent.md#section\n"
        self.assertEqual(self.run_repository(), 1)

    def test_percent_encoded_filename_passes(self):
        self.files[self.root / "governance/a b.md"] = "# Rule\n"
        self.files[self.root / "governance/10-dispatch.md"] += "[rule](a%20b.md#part)\n"
        self.assertEqual(self.run_repository(), 0)

    def test_line_budget_is_warning_only(self):
        for name in checker.ROUTERS:
            self.files[self.root / name] += "\n" * (checker.ROUTER_LINE_BUDGET + 1)
        self.files[self.root / "governance/10-dispatch.md"] += "\n" * (checker.GOVERNANCE_LINE_BUDGET + 1)
        self.assertEqual(self.run_repository(), 0)
        self.assertEqual(sum(status == "WARN" for status, _ in self.checks.results), 3)

    def test_invalid_json_fails_without_disclosing_content(self):
        self.files[self.manifest_path] = '{"api_key":"SECRET_SENTINEL", broken}'
        self.assertEqual(self.run_repository(), 1)
        self.assertNotIn("SECRET_SENTINEL", self.output())
        self.assertIn("JSON 格式無效", self.output())

    def test_invalid_manifest_schema_fails_without_false_pass(self):
        for value in ([], {"claude_settings": {}, "codex_config": []},
                      {"claude_settings": {}, "codex_config": {"personality": 42}}):
            with self.subTest(value=value):
                self.checks = checker.Checks()
                self.files[self.manifest_path] = json.dumps(value)
                self.assertEqual(self.run_repository(), 1)
                self.assertNotIn("manifest 白名單設定結構有效", self.output())

    def test_local_drift_warns_without_disclosing_any_values(self):
        self.checks.compare_settings(
            {"model_reasoning_effort": "ultra", "personality": "pragmatic"},
            {"model_reasoning_effort": "SECRET_SENTINEL", "personality": "other", "api_key": "SECRET_SENTINEL"},
            "codex_config",
        )
        self.assertEqual(self.checks.exit_code, 0)
        self.assertEqual(len(self.checks.results), 2)
        self.assertTrue(all(status == "WARN" for status, _ in self.checks.results))
        self.assertNotIn("SECRET_SENTINEL", self.output())

    def test_manifest_does_not_require_unlisted_model(self):
        self.checks.compare_settings({}, {"model": "anything"}, "codex_config")
        self.assertEqual(self.checks.results, [])

    def test_local_invalid_field_type_fails(self):
        self.checks.compare_settings({"model": "expected"}, {"model": 42}, "claude_settings")
        self.assertEqual(self.checks.exit_code, 1)

    def test_local_missing_deployment_warns(self):
        self.checks.deployment(self.root / CODEX, Path("/virtual/home/.codex/AGENTS.md"))
        self.assertEqual(self.checks.exit_code, 0)
        self.assertIn("WARN 本地部署缺失", self.output())

    def test_local_symlink_deployment_warns_as_leftover(self):
        with patch.object(Path, "is_symlink", return_value=True):
            self.checks.deployment(self.root / CODEX, Path("/virtual/home/.codex/AGENTS.md"))
        self.assertEqual(self.checks.exit_code, 0)
        self.assertIn("應為實體副本", self.output())

    def test_local_copy_passes_and_drift_warns(self):
        source = self.root / CODEX
        target = Path("/virtual/home/.codex/AGENTS.md")
        self.files[target] = self.files[source]
        with patch.object(Path, "is_symlink", return_value=False):
            self.checks.deployment(source, target)
        self.assertIn("PASS 本地內容一致", self.output())
        self.files[target] += "drift"
        self.checks.content(source, target)
        self.assertIn("WARN 本地內容漂移", self.output())

    def test_missing_tomllib_warns(self):
        with patch.object(checker, "tomllib", None):
            self.assertIsNone(self.checks.codex_settings(Path("/virtual/config.toml")))
        self.assertEqual(self.checks.exit_code, 0)
        self.assertIn("略過 Codex TOML", self.output())

    @unittest.skipIf(checker.tomllib is None, "Python 3.11+ required for TOML parsing")
    def test_invalid_toml_fails_without_disclosing_content(self):
        path = Path("/virtual/config.toml")
        self.files[path] = 'api_key = "SECRET_SENTINEL"\ninvalid line'
        self.assertIsNone(self.checks.codex_settings(path))
        self.assertEqual(self.checks.exit_code, 1)
        self.assertNotIn("SECRET_SENTINEL", self.output())

    @unittest.skipIf(checker.tomllib is None, "Python 3.11+ required for TOML parsing")
    def test_toml_returns_only_allowlisted_fields(self):
        path = Path("/virtual/config.toml")
        self.files[path] = 'model_reasoning_effort = "high"\napi_key = "SECRET_SENTINEL"\n[profiles]\nmodel = "nested"\n'
        self.assertEqual(self.checks.codex_settings(path), {"model_reasoning_effort": "high"})

    def test_cli_returns_failure_for_structural_problem(self):
        self.files.pop(self.root / checker.RUNTIME_DOC)
        with redirect_stdout(io.StringIO()) as output:
            result = checker.main(["--repo", str(self.root)])
        self.assertEqual(result, 1)
        self.assertIn("1 項失敗", output.getvalue())


if __name__ == "__main__":
    unittest.main()
