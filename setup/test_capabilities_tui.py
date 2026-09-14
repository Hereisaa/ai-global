"""Keyboard integration uses prompt_toolkit pipe input, never real user settings."""

import asyncio
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import capabilities as cap

try:
    import capabilities_tui as tui
    from prompt_toolkit.input.defaults import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from prompt_toolkit.data_structures import Size
    from prompt_toolkit.formatted_text import to_plain_text
    from prompt_toolkit.utils import get_cwidth
except ImportError:
    tui = None


@unittest.skipIf(tui is None, "Install setup/requirements-tui.txt for interactive tests")
class TuiTests(unittest.TestCase):
    def setUp(self):
        self.rows = tui.demo_rows()

    def key_run(self, keys, rows=None):
        with create_pipe_input() as pipe:
            app = tui.create_app(self.rows if rows is None else rows, cap.capability_table,
                                 input=pipe, output=DummyOutput())
            pipe.send_text(keys)
            return app.run()

    def test_down_space_enter_returns_only_selected_change(self):
        before = copy.deepcopy(self.rows)
        self.assertEqual(self.key_run("\x1b[B \r"), {tui.identity(self.rows[1]): True})
        self.assertEqual(self.rows, before)

    def test_space_twice_restores_original_state(self):
        self.assertEqual(self.key_run("  \r"), {})

    def test_escape_and_ctrl_c_cancel_staged_changes(self):
        self.assertIsNone(self.key_run(" \x1b"))
        self.assertIsNone(self.key_run(" \x03"))

    def test_missing_item_cannot_toggle(self):
        self.assertEqual(self.key_run("\x1b[B\x1b[B \r"), {})

    def test_empty_inventory_and_navigation_boundaries(self):
        self.assertEqual(self.key_run("\x1b[A \r", rows=[]), {})
        self.assertEqual(self.key_run("\x1b[6~ \r"), {tui.identity(self.rows[-1]): False})

    def test_stale_selection_does_not_apply_anything(self):
        current = copy.deepcopy(self.rows)
        current[0]["enabled"] = False
        toggle = Mock()
        code, messages = tui.apply_changes(self.rows, {tui.identity(self.rows[0]): False}, lambda: current, toggle)
        self.assertEqual(code, 1)
        self.assertIn("狀態已改變", messages[0])
        toggle.assert_not_called()

    def test_partial_failure_reports_success_count_without_secrets(self):
        pending = {tui.identity(self.rows[0]): False, tui.identity(self.rows[1]): True,
                   tui.identity(self.rows[3]): False}
        toggle = Mock(side_effect=["first applied", RuntimeError("SECRET_SENTINEL")])
        code, messages = tui.apply_changes(self.rows, pending, lambda: self.rows, toggle)
        self.assertEqual(code, 1)
        self.assertEqual(toggle.call_count, 2)
        self.assertIn("已完成 1 項", messages[-1])
        self.assertNotIn("SECRET_SENTINEL", "".join(messages))

    def test_apply_uses_exact_ids_and_new_states(self):
        toggle = Mock(return_value="applied")
        code, _ = tui.apply_changes(self.rows, {tui.identity(self.rows[1]): True}, lambda: self.rows, toggle)
        self.assertEqual(code, 0)
        toggle.assert_called_once_with("codex", "plugin", "demo-local-plugin@market", True)

    def test_demo_and_cancel_never_read_or_write_settings(self):
        for result, demo in ((None, False), ({tui.identity(self.rows[0]): False}, True)):
            with self.subTest(demo=demo), patch.object(tui, "create_app") as factory, redirect_stdout(io.StringIO()):
                factory.return_value.run.return_value = result
                read, toggle = Mock(), Mock()
                self.assertEqual(tui.manage(self.rows, cap.capability_table, read, toggle, demo=demo), 0)
                read.assert_not_called()
                toggle.assert_not_called()

    def test_cli_demo_does_not_inventory_real_home(self):
        with patch.object(cap.sys.stdin, "isatty", return_value=True), \
                patch.object(cap.sys.stdout, "isatty", return_value=True), \
                patch.object(cap, "inventory") as inventory, patch.object(tui, "manage", return_value=0) as manage:
            self.assertEqual(cap.main(["manage", "--demo"]), 0)
            inventory.assert_not_called()
            self.assertTrue(manage.call_args.kwargs["demo"])

    def test_noninteractive_cli_rejects_before_inventory(self):
        with patch.object(cap.sys.stdin, "isatty", return_value=False), \
                patch.object(cap, "inventory") as inventory, patch.object(cap.sys, "stderr", io.StringIO()) as error:
            self.assertEqual(cap.main(["manage"]), 1)
            self.assertIn("互動式 Terminal", error.getvalue())
            inventory.assert_not_called()

    def test_keyboard_apply_roundtrip_in_isolated_home(self):
        root = Path(tempfile.mkdtemp(prefix="ai-global-tui-test-"))
        repo, home = root / "repo", root / "home"
        (repo / "manifest").mkdir(parents=True)
        (repo / "manifest/skills.json").write_text(json.dumps({"items": []}))
        skill = home / ".claude/skills/example/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# preserved content\n")
        for enabled in (False, True):
            rows = cap.inventory(repo, home)
            pending = self.key_run(" \r", rows=rows)
            self.assertEqual(skill.exists(), not enabled)
            status, _ = tui.apply_changes(rows, pending, lambda: cap.inventory(repo, home),
                                          lambda *args: cap.toggle(repo, home, *args))
            self.assertEqual(status, 0)
            self.assertEqual(cap.inventory(repo, home)[0]["enabled"], enabled)
        self.assertEqual(skill.read_text(), "# preserved content\n")

    def test_table_fits_narrow_and_normal_terminals(self):
        for columns in (50, 80):
            with self.subTest(columns=columns), create_pipe_input() as pipe:
                output = DummyOutput()
                output.get_size = lambda: Size(rows=24, columns=columns)
                app = tui.create_app(self.rows, cap.capability_table, input=pipe, output=output)
                captured = []
                def capture(sender):
                    for control in sender.layout.find_all_controls():
                        value = to_plain_text(getattr(control, "text", ""))
                        if value.startswith("       工具") or value.startswith("> [x]"):
                            captured.append(value)
                app.before_render += capture
                pipe.send_text("\r")
                app.run()
                self.assertTrue(captured)
                self.assertTrue(all(get_cwidth(line) <= columns - 1 for value in captured for line in value.splitlines()))

    def test_long_id_does_not_hide_status_in_40_column_screen(self):
        rows = [dict(self.rows[0], id="start-" + "x" * 130 + "-tail-marker")]
        with create_pipe_input() as pipe:
            output = DummyOutput()
            output.get_size = lambda: Size(rows=24, columns=40)
            app = tui.create_app(rows, cap.capability_table, input=pipe, output=output)
            screens = []
            def capture(sender):
                screen = sender.renderer.last_rendered_screen
                if screen:
                    screens.append("\n".join("".join(screen.data_buffer[y][x].char for x in range(40)) for y in range(24)))
            app.after_render += capture
            async def feed():
                pipe.send_text("\x1b[C" * 13)
                await asyncio.sleep(0.1)
                pipe.send_text("\r")
            app.pre_run_callables.append(lambda: app.create_background_task(feed()))
            app.run()
            self.assertTrue(any("目前 開 → 預定 開" in screen for screen in screens))
            self.assertTrue(any("tail-marker" in screen for screen in screens))


if __name__ == "__main__":
    unittest.main()
