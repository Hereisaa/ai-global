"""ai-global deploy script (cross-platform; replaces install.sh / install.ps1).

Copies this clone's global AI config into the paths the tools actually read.
Everything deployed is a REAL FILE - no symlinks, no junctions - so a moved or
deleted clone can never leave the machine with a dangling global config.

  repo/governance   -> ~/.ai-global/governance   (rules SSOT the routers point at)
  repo/claude/*     -> ~/.claude/*
  repo/codex/*      -> ~/.codex/*

Usage: python setup/deploy.py [install|check] [--home PATH] [--repo PATH]
  install  deploy (idempotent; anything replaced is kept in trash)
  check    report drift, change nothing (exit 1 if anything needs attention)

Importable: run(repo, home, mode, echo=print) -> dict. Python 3.11+, stdlib only.
Nothing here ever deletes: replaced items are moved under ~/.ai-trash/.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import uuid


class DeployError(Exception):
    pass


# Statuses that make a check run fail. SKIP/DISABLED/WARN/PUT/DROP/UNLINK are
# informational and never fail a run.
FAIL_STATUSES = frozenset(("MISSING", "STALE", "BEHIND", "EDITED", "EXTRA"))
HOOK_MSG = "ai-global: pull done -> run python setup/deploy.py check (or /ai-global in Claude Code)"
GLOBAL_KEEP = ("governance", ".deploy-state.json")


def blob_hash(path):
    """Git blob sha1 of the raw bytes (no clean filters), so it matches the
    hash of a byte-for-byte deployed copy regardless of git's eol settings."""
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def is_link(path):
    """Symlink on any OS, or a junction on Windows. Nothing deployed is ever a
    link, so any link at a target is left over from an older install."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    mount_point = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
    return getattr(st, "st_reparse_tag", 0) == mount_point


def git_output(repo, *args):
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def platform_name():
    return {"Windows": "Windows", "Darwin": "macOS"}.get(platform.system(), platform.system() or "unknown")


def read_state(path):
    """Previous deploy on this machine (~/.ai-global/.deploy-state.json):
      files    blob hash of every file as deployed. A deployed file that still
               matches its recorded hash was not touched since -> BEHIND (safe
               to update); anything else -> EDITED (needs a human).
      managed  repo-relative paths of the item-level deploys (skills, commands,
               agents). An item the repo no longer has must be removed.
      commit   informational only."""
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return "", [], {}
    if not isinstance(state, dict):
        return "", [], {}
    commit = state.get("commit") if isinstance(state.get("commit"), str) else ""
    managed = [m for m in state.get("managed", []) if isinstance(m, str) and m.startswith("claude/")] if isinstance(state.get("managed"), list) else []
    files = {k: v for k, v in state.get("files", {}).items() if isinstance(k, str) and isinstance(v, str)} if isinstance(state.get("files"), dict) else {}
    return commit, managed, files


class Deployer:
    def __init__(self, repo, home, mode, echo=print, keep_edited=()):
        if mode not in ("install", "check"):
            raise DeployError(f"unknown mode: {mode}")
        # Repo-relative paths whose EDITED deployed copy the user chose to keep
        # for now (align's conflict resolution); left untouched, not recorded.
        self.keep_edited = set(keep_edited)
        self.repo = Path(os.path.abspath(repo))
        self.home = Path(os.path.abspath(os.path.expanduser(str(home))))
        self.mode = mode
        self.echo = echo
        self.global_dir = self.home / ".ai-global"
        self.state_path = self.global_dir / ".deploy-state.json"
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.trash = self.home / ".ai-trash" / f"ai-global-deploy-{stamp}-{uuid.uuid4().hex}"
        self.prev_commit, self.prev_managed, self.prev_files = read_state(self.state_path)
        self.managed = []
        self.files = {}
        self.results = []
        self.fail = False

    def report(self, status, path, note=""):
        self.results.append((status, str(path), note))
        if status in FAIL_STATUSES:
            self.fail = True
        line = f"{status:<7} {path}"
        self.echo(line + (f" - {note}" if note else ""))

    def move_to_trash(self, path):
        """Park an item under the trash dir keeping its home-relative layout.
        Never overwrites an existing trash entry and refuses anything outside
        the selected home."""
        path = Path(path)
        if not os.path.lexists(path):
            return
        home = os.path.normcase(str(self.home)).rstrip(os.sep) + os.sep
        full = os.path.normcase(str(path))
        if not full.startswith(home):
            raise DeployError("Trash source is outside the selected home")
        dest = self.trash / str(path)[len(home):]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(dest):
            raise DeployError("Trash destination already exists")
        # os.rename moves the entry itself (a link stays a link), never copies.
        os.rename(path, dest)

    def status(self, rel, dst):
        """OK | MISSING | STALE | BEHIND | EDITED for one deployed file."""
        src = self.repo / rel
        if not os.path.lexists(dst):
            return "MISSING"
        if is_link(dst):
            return "STALE"
        if not dst.is_file():
            return "EDITED"
        src_bytes = src.read_bytes()
        if src_bytes == dst.read_bytes():
            return "OK"
        prev = self.prev_files.get(rel, "")
        if prev and prev == blob_hash(dst):
            return "BEHIND"
        return "EDITED"

    def put(self, rel, dst):
        src = self.repo / rel
        dst = Path(dst)
        if not src.is_file():
            self.report("SKIP", rel, "missing in repo")
            return
        st = self.status(rel, dst)
        if self.mode == "check":
            notes = {"OK": "", "MISSING": "not deployed yet",
                     "STALE": "dangling link left by an older install",
                     "BEHIND": "repo moved on, run install to update",
                     "EDITED": "changed outside the repo, review before install"}
            self.report(st, dst, notes[st])
            return
        if st == "EDITED" and rel in self.keep_edited:
            self.report("KEEP", dst, "edited copy kept by user choice; not recorded as deployed")
            return
        # Record what is deployed after this run, whether or not we had to copy.
        self.files[rel] = blob_hash(src)
        if st == "OK":
            return
        if st == "EDITED":
            self.report("WARN", dst, "differed from the repo; the old copy goes to trash")
        self.move_to_trash(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        if os.name != "nt" and dst.suffix == ".sh":
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.report("PUT", dst)

    def put_dir(self, rel, dst):
        src = self.repo / rel
        dst = Path(dst)
        if not src.is_dir():
            self.report("SKIP", rel, "missing in repo")
            return
        if self.mode == "install":
            # A directory left as a link by an older install must go first,
            # otherwise every copy below would be written straight into the repo.
            if is_link(dst):
                self.report("UNLINK", dst, "link left by an older install")
                self.move_to_trash(dst)
            elif os.path.lexists(dst) and not dst.is_dir():
                self.report("WARN", dst, "is a file where a directory belongs; the old copy goes to trash")
                self.move_to_trash(dst)
        for sub in self.walk_files(src):
            self.put(f"{rel}/{sub.replace(os.sep, '/')}", dst / sub)
        # Skip the extras scan while the destination is still a link: install
        # already unlinked it above, and in check mode every file under it is
        # reported as STALE/MISSING anyway.
        if not os.path.lexists(dst) or is_link(dst) or not dst.is_dir():
            return
        for sub in self.walk_files(dst):
            if os.path.exists(src / sub):
                continue
            self.extra(dst / sub, "no longer in repo")

    @staticmethod
    def walk_files(root):
        found = []
        for base, dirs, names in os.walk(root):
            dirs.sort()
            for name in sorted(names):
                found.append(os.path.relpath(os.path.join(base, name), root))
        return found

    def extra(self, path, note):
        """A leftover: report in check mode, park it in trash in install mode."""
        if self.mode == "check":
            self.report("EXTRA", path, note)
        else:
            self.move_to_trash(path)
            self.report("DROP", path, "-> trash")

    def run(self):
        home, repo = self.home, self.repo
        self.echo(f"repo:   {repo}")
        self.echo(f"target: {self.global_dir} + {home / '.claude'} + {home / '.codex'}")
        self.echo("")

        self.put_dir("governance", self.global_dir / "governance")
        # ~/.ai-global is owned by this script outright, so anything at its top
        # level that this version does not deploy is a leftover from an older layout.
        if self.global_dir.is_dir():
            for entry in sorted(self.global_dir.iterdir(), key=lambda p: p.name):
                if entry.name not in GLOBAL_KEEP:
                    self.extra(entry, "no longer deployed here")

        self.put_dir("claude/hooks", home / ".claude/hooks")
        self.put("claude/CLAUDE.md", home / ".claude/CLAUDE.md")
        self.put("claude/statusline.sh", home / ".claude/statusline.sh")
        self.put("codex/AGENTS.md", home / ".codex/AGENTS.md")

        # Repo-owned skills/commands/agents are deployed item by item so
        # third-party installs keep coexisting in the same parent directories.
        # A locally disabled item is updated in place under ai-global-disabled.
        disabled = home / ".claude/ai-global-disabled"
        for skill in self.children(repo / "claude/skills", dirs=True):
            rel = f"claude/skills/{skill}"
            if os.path.lexists(disabled / "skills" / skill):
                self.report("DISABLED", rel, "preserving local choice")
                self.put_dir(rel, disabled / "skills" / skill)
            else:
                self.put_dir(rel, home / ".claude/skills" / skill)
            self.managed.append(rel)
        for command in self.children(repo / "claude/commands", dirs=False):
            rel = f"claude/commands/{command}"
            if os.path.lexists(disabled / "commands" / command):
                self.report("DISABLED", rel, "preserving local choice")
                self.put(rel, disabled / "commands" / command)
            else:
                self.put(rel, home / ".claude/commands" / command)
            self.managed.append(rel)
        for agent in self.children(repo / "claude/agents", dirs=False):
            rel = f"claude/agents/{agent}"
            self.put(rel, home / ".claude/agents" / agent)
            self.managed.append(rel)

        # Items deployed last time that the repo no longer has (a renamed or
        # removed skill, command or agent).
        for rel in self.prev_managed:
            if rel in self.managed:
                continue
            dst = home / ".claude" / rel[len("claude/"):]
            if os.path.lexists(dst):
                self.extra(dst, "no longer in repo")

        head = git_output(repo, "rev-parse", "HEAD") or "unknown"
        if self.mode == "check":
            self.echo("")
            if not self.prev_commit:
                self.echo("STATE   never deployed on this machine")
            elif self.prev_commit != head:
                self.echo(f"STATE   deployed from {self.prev_commit[:9]}, repo HEAD is {head[:9]}")
            else:
                self.echo(f"STATE   deployed from {self.prev_commit[:9]} (current)")
            if self.fail:
                self.echo(f"out of sync - run: python {repo / 'setup' / 'deploy.py'}")
            else:
                self.echo("global deployment is in sync")
            return self.summary(head)

        branch = git_output(repo, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
        state = {"source_repo": str(repo), "commit": head, "branch": branch,
                 "deployed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "platform": platform_name(), "managed": self.managed, "files": self.files}
        self.global_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        self.echo(f"STATE   {self.state_path} -> {head[:9]}")
        self.write_hooks()
        if self.trash.exists():
            self.echo("")
            self.echo(f"NOTE: replaced items are in {self.trash} (confirm, then empty manually)")
        self.echo("deploy complete")
        return self.summary(head)

    @staticmethod
    def children(folder, dirs):
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir()
                      if not p.name.startswith(".") and (p.is_dir() if dirs else p.is_file()))

    def write_hooks(self):
        """Remind after a pull. Deliberately does not auto-deploy, so a pull can
        never silently overwrite something edited on this machine. Existing
        hooks are never touched."""
        hook_dir = self.repo / ".git/hooks"
        if not hook_dir.is_dir():
            return
        scripts = {"post-merge": f"#!/bin/sh\necho '{HOOK_MSG}'\n",
                   "post-rewrite": f"#!/bin/sh\n[ \"$1\" = rebase ] && echo '{HOOK_MSG}'\nexit 0\n"}
        for name, body in scripts.items():
            hook = hook_dir / name
            if os.path.lexists(hook):
                continue
            with open(hook, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            if os.name != "nt":
                hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def summary(self, head):
        return {"results": self.results, "state_path": self.state_path,
                "trash": self.trash if self.trash.exists() else None,
                "ok": not self.fail, "mode": self.mode, "commit": head}


def run(repo, home, mode="install", echo=print, keep_edited=()):
    """Deploy or check. Returns {"results": [(status, path, note), ...],
    "state_path": Path, "trash": Path | None, "ok": bool, "mode": str, "commit": str}.
    "ok" is False only when a failing status (MISSING/STALE/BEHIND/EDITED/EXTRA)
    was reported, which can only happen in check mode. keep_edited lists
    repo-relative paths whose EDITED copy must be left alone this run."""
    return Deployer(repo, home, mode, echo, keep_edited).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deploy this clone's global AI config as real files, or check for drift.")
    parser.add_argument("mode", nargs="?", choices=("install", "check"), default="install",
                        help="install: deploy (default); check: report drift, change nothing")
    parser.add_argument("--home", type=Path, default=Path.home(), help="target home (default: the current user's)")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="clone to deploy from")
    args = parser.parse_args(argv)
    try:
        result = run(args.repo, args.home, args.mode)
    except (DeployError, OSError) as exc:
        print(f"deploy failed: {exc}", file=sys.stderr)
        return 1
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
