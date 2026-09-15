"""Isolated hook behavior checks; fixtures are retained for inspection."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_guard_delete_blocks_delete_verbs_anywhere_and_allows_the_rest(self):
        script = HOOKS / "guard-delete.sh"

        def run(payload):
            result = subprocess.run([BASH, str(script)], input=payload, text=True, capture_output=True)
            return result.returncode, result.stderr

        blocked = ["rm foo", "cd x && rm -rf y", "ls | xargs rm", "sudo rm -rf /tmp/x",
                   "find . -name '*.log' -delete", "rmdir empty", "$(rm x)",
                   "pwsh -c \"Remove-Item x\"", "git clean -fd",
                   # reviewer bypasses (2026-09-15)
                   "ls | while read f; do rm \"$f\"; done", "if true; then rm x; fi", "for f in *; do unlink $f; done",
                   "/bin/rm x", "\\rm -rf /tmp/x", "env FOO=1 rm x", "bash -c \"rm x\"",
                   "python3 -c \"import shutil; shutil.rmtree('x')\"", "python3 -c \"import os; os.remove('x')\"",
                   "node -e \"require('fs').unlinkSync('x')\"", "rsync -a --delete a/ b/", "npx rimraf dist"]
        allowed = ["mv a ~/.ai-trash/cleanup-1/", "npm rm pkg", "git rm --cached x",
                   "echo confirm; grep -rn model .", "python3 setup/deploy.py check", "# rm in a comment",
                   # reviewer false positives (2026-09-15): auditing the rules must stay possible
                   "grep -rn 'rm -rf' docs/", "rg 'Remove-Item' claude/", "echo 'del' > f",
                   "echo \"rm is banned\"", "git clean -n", "cat README.md | grep unlink"]
        for command in blocked:
            code, err = run(json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))
            self.assertEqual(code, 2, command)
            self.assertIn("50-safety", err)
        for command in allowed:
            code, _ = run(json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))
            self.assertEqual(code, 0, command)
        self.assertEqual(run(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "rm"}}))[0], 0)
        code, err = run("not json")
        self.assertEqual(code, 0)
        self.assertIn("不是 JSON", err)
        # PowerShell pipes prepend a BOM; the guard must still parse and block.
        code, err = run("\ufeff" + json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}}) + "\r\n")
        self.assertEqual(code, 2)

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_session_check_reports_missing_state_and_sync_status(self):
        home = Path(tempfile.mkdtemp(prefix="home-", dir=self.fixtures))
        env = dict(os.environ, HOME=str(home))

        env["AI_GLOBAL_CHECK_NO_FETCH"] = "1"

        def hook():
            return subprocess.run([BASH, str(HOOKS / "ai-global-check.sh")], env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")

        result = hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("尚未部署", result.stdout)

        repo = Path(tempfile.mkdtemp(prefix="repo-", dir=self.fixtures))
        for name in ("claude/CLAUDE.md", "codex/AGENTS.md", "governance/20-judgment.md"):
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text("# rules\n", encoding="utf-8")
        shutil.copytree(ROOT / "setup", repo / "setup", ignore=shutil.ignore_patterns("__pycache__", "test_*"))
        subprocess.run(["git", "init", "-q", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-q", "--allow-empty", "-m", "fixture"], capture_output=True, check=True)
        deploy = subprocess.run([sys.executable, str(repo / "setup/deploy.py"), "--home", str(home)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(deploy.returncode, 0, deploy.stdout + deploy.stderr)
        result = hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("一致", result.stdout)
        self.assertNotIn("不同步", result.stdout)
        self.assertIn("沒有 upstream", result.stdout)
        self.assertIn("部署自分支", result.stdout)  # fixture is on the default branch, not main

        (repo / "governance/20-judgment.md").write_text("# newer\n", encoding="utf-8")
        result = hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("不同步（1 項", result.stdout)
        self.assertIn("BEHIND", result.stdout)

        (repo / "setup/deploy.py").write_text("import sys\nprint('boom')\nsys.exit(3)\n", encoding="utf-8")
        result = hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("部署檢查本身失敗", result.stdout)
        self.assertIn("boom", result.stdout)
        self.assertNotIn("0 項", result.stdout)

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_guard_delete_without_python_fails_open_but_says_so(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm x"}})
        env = dict(os.environ, PATH="/nonexistent")
        result = subprocess.run([BASH, str(HOOKS / "guard-delete.sh")], input=payload, env=env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0)
        self.assertIn("hook 失效", result.stderr)

    @unittest.skipUnless(BASH and Path(BASH).exists(), "Bash unavailable")
    def test_guard_delete_skips_a_python3_that_does_not_run(self):
        # Windows ships a "python3" on PATH that is only the Microsoft Store redirector:
        # it exits (code 49) with no output. The guard must fall through to a real python.
        shims = Path(tempfile.mkdtemp(prefix="shims-", dir=self.fixtures))
        (shims / "python3").write_text("#!/bin/sh\nexit 49\n", encoding="utf-8", newline="\n")
        real = sys.executable.replace("\\", "/")
        (shims / "python").write_text(f'#!/bin/sh\nexec "{real}" "$@"\n', encoding="utf-8", newline="\n")
        for shim in ("python3", "python"):
            (shims / shim).chmod(0o755)
        env = dict(os.environ, PATH=str(shims) + os.pathsep + os.environ.get("PATH", ""))
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm x"}})
        result = subprocess.run([BASH, str(HOOKS / "guard-delete.sh")], input=payload, env=env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("50-safety", result.stderr)


if __name__ == "__main__":
    unittest.main()
