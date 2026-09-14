"""Isolated hook behavior checks; fixtures are retained for inspection."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "claude" / "hooks"
BASH = shutil.which("bash")
if os.name == "nt":
    BASH = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe")
PWSH = shutil.which("pwsh")


class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = Path(tempfile.mkdtemp(prefix="ai-global-hooks-"))

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_stop_never_runs_project_commands_or_blocks(self):
        # A hostile command on PATH would fail if the retired hook invoked it.
        folder = self.fixtures / "stop"
        folder.mkdir()
        (folder / "package.json").write_text('{"scripts":{"typecheck":"exit 91"}}')
        for payload in ({"cwd": str(folder)}, {"stop_hook_active": True}, {}):
            result = subprocess.run([BASH, str(HOOKS / "stop-typecheck.sh")],
                                    input=json.dumps(payload), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_macos_decisions_preserve_remote_control_and_global_ownership(self):
        source = (HOOKS / "cleanup-orphans.sh").read_text(encoding="utf-8")
        decisions = source[source.index("DECISIONS=$(snapshot"):source.index("\nkilled=0")]
        snapshot = "\n".join(
            f"P {pid} {parent} 10:00 1024\nC {pid} {name}\nA {pid} {args}"
            for pid, parent, name, args in (
                (10, 0, "claude", "claude"), (100, 10, "bash", "hook"),
                (11, 10, "node", "helper"), (12, 10, "node", "remote-control"),
                (13, 12, "python", "protected descendant"),
                (14, 1, "node", "unrelated orphan")))
        for scope in ("session", "global"):
            script = self.fixtures / f"mac-{scope}.sh"
            script.write_text(
                f"SCOPE={scope}\nme=100\nCLAUDE_MEM_WARN_MB=999999\nCLAUDE_AGE_WARN_H=24\n"
                + "snapshot() { cat <<'FIXTURE'\n" + snapshot + "\nFIXTURE\n}\n"
                + decisions + '\nprintf "%s\\n" "$DECISIONS"\n', encoding="utf-8")
            result = subprocess.run([BASH, str(script)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            if scope == "session":
                self.assertEqual(result.stdout.strip(), "KILL 11 1024 node descendant of ending session 10")
            else:
                self.assertNotIn("KILL", result.stdout)
                self.assertIn("REPORT 14 1024 node ownership unknown", result.stdout)

    def powershell_case(self, scope, failure=""):
        folder = Path(tempfile.mkdtemp(prefix="ps-", dir=self.fixtures))
        source = (HOOKS / "cleanup-orphans.ps1").read_text(encoding="utf-8")
        source = source.replace("Join-Path $HOME '.claude\\logs'", "$env:HOOK_TEST_LOG")
        script = folder / "cleanup.ps1"
        script.write_text(source, encoding="utf-8")
        harness = folder / "run.ps1"
        harness.write_text(r'''
$global:stops = @()
function Get-CimInstance {
  $created = (Get-Date).AddMinutes(-10)
  foreach ($entry in @(
    @(900001, 0, 'claude.exe', 'claude'),
    @($PID, 900001, 'pwsh.exe', 'hook'),
    @(900002, 900001, 'node.exe', 'helper'),
    @(900003, 900001, 'node.exe', 'remote-control helper'),
    @(900004, 900003, 'python.exe', 'protected descendant'),
    @(900005, 0, 'node.exe', 'unrelated orphan'),
    @(900006, 0, 'vmmem', 'vm')
  )) {
    [pscustomobject]@{ProcessId=$entry[0];ParentProcessId=$entry[1];Name=$entry[2];CommandLine=$entry[3];CreationDate=$created;WorkingSetSize=4GB}
  }
}
function Stop-Process { param($Id, [switch]$Force) $global:stops += $Id }
function docker { $global:LASTEXITCODE = 0; if ($env:HOOK_TEST_FAILURE -eq 'docker') { $global:LASTEXITCODE = 1 } }
function wsl { $global:LASTEXITCODE = 0; if ($env:HOOK_TEST_FAILURE -eq 'wsl') { $global:LASTEXITCODE = 1 } }
& $env:HOOK_TEST_SCRIPT -Scope $env:HOOK_TEST_SCOPE -ClaudeMemoryWarnMB 999999
@{stops=@($global:stops); log=(Get-Content (Join-Path $env:HOOK_TEST_LOG 'cleanup.log') -Raw)} | ConvertTo-Json -Compress
''', encoding="utf-8")
        env = dict(os.environ, HOOK_TEST_LOG=str(folder / "logs"),
                   HOOK_TEST_SCRIPT=str(script), HOOK_TEST_SCOPE=scope,
                   HOOK_TEST_FAILURE=failure)
        result = subprocess.run([PWSH, "-NoProfile", "-File", str(harness)],
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @unittest.skipUnless(PWSH, "PowerShell unavailable")
    def test_session_only_stops_proven_unprotected_helper(self):
        self.assertEqual(self.powershell_case("session")["stops"], [900002])

    @unittest.skipUnless(PWSH, "PowerShell unavailable")
    def test_global_never_stops_orphans_or_vm(self):
        result = self.powershell_case("global")
        self.assertEqual(result["stops"], [])
        self.assertIn("ownership unknown (report only)", result["log"])
        self.assertIn("runningDistros=0 (report only)", result["log"])

    @unittest.skipUnless(PWSH, "PowerShell unavailable")
    def test_failed_vm_queries_are_unknown(self):
        for failure in ("docker", "wsl"):
            result = self.powershell_case("global", failure)
            self.assertEqual(result["stops"], [])
            self.assertIn("usage unknown", result["log"])


if __name__ == "__main__":
    unittest.main()
