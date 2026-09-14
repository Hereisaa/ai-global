"""Install one manifest capability through the tool's own CLI or a git checkout.

Python 3.11+; standard library only. Every action is explicit (called with one
manifest item), reversible (replaced files go to ~/.ai-trash) and never deletes.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

MARKER = ".ai-global.json"  # written inside a checked-out skill: source + commit


class InstallError(Exception):
    pass


def trash_dir(home, label="align"):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return home / ".ai-trash" / f"ai-global-{label}-{stamp}-{uuid.uuid4().hex[:8]}"


def move_to_trash(path, home, trash):
    """Move a file or directory under home into the trash; never overwrite there."""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return None
    try:
        label = path.resolve().relative_to(home.resolve())
    except ValueError:
        raise InstallError(f"不在使用者目錄內，拒絕移動：{path}")
    dest = trash / label
    if dest.exists():
        raise InstallError(f"trash 目標已存在，未移動：{dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # rename, not shutil.move: a cross-volume move would copy then delete.
    os.rename(path, dest)
    return dest


def run_cli(args, run=None, timeout=300):
    """Run a tool CLI; return (ok, combined output). Never raises on failure."""
    run = run or subprocess.run  # resolved late so tests can substitute subprocess
    # Windows installs claude/codex as .CMD shims; CreateProcess needs the resolved path.
    args = [shutil.which(args[0]) or args[0], *args[1:]]
    try:
        result = run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def parse_source(item):
    """Classify a manifest source string.

    repo:<path>                       -> ("repo", None)
    marketplace <name>                -> ("marketplace", None)   known to the tool already
    marketplace github:<owner>/<repo> -> ("marketplace", "<owner>/<repo>")
    github:<owner>/<repo>             -> ("github", "<owner>/<repo>")
    """
    source = item.get("source", "")
    if source.startswith("repo:"):
        return "repo", None
    if source.startswith("marketplace "):
        rest = source[len("marketplace "):].strip()
        return "marketplace", rest[len("github:"):] if rest.startswith("github:") else None
    if source.startswith("github:"):
        return "github", source[len("github:"):].strip()
    return "unknown", None


def requirements_missing(item):
    """Commands the capability needs on PATH (e.g. a language server)."""
    return [name for name in item.get("requires", []) if not shutil.which(name)]


def plugin_commands(item, marketplace_repo):
    """CLI invocations that install a plugin for the item's tool."""
    tool, identifier = item["tool"], item["id"]
    if tool == "claude":
        add = ["claude", "plugin", "marketplace", "add", marketplace_repo] if marketplace_repo else None
        return add, ["claude", "plugin", "install", identifier]
    add = ["codex", "plugin", "marketplace", "add", marketplace_repo] if marketplace_repo else None
    return add, ["codex", "plugin", "add", identifier]


def skill_target(item, home):
    """Where a standalone skill/command lands; a parked (disabled) copy wins."""
    tool, kind, identifier = item["tool"], item["type"], item["id"]
    if tool == "codex":
        return home / identifier  # ids are ".codex/skills/<name>"
    folder = "commands" if kind == "command" else "skills"
    name = f"{identifier}.md" if kind == "command" else identifier
    parked = home / ".claude/ai-global-disabled" / folder / name
    return parked if parked.exists() else home / ".claude" / folder / name


def same_tree(a, b):
    """Byte-compare two files or directory trees (marker file excluded)."""
    a, b = Path(a), Path(b)
    if a.is_file() or b.is_file():
        return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()
    def listing(root):
        return {p.relative_to(root).as_posix(): p.read_bytes()
                for p in root.rglob("*") if p.is_file() and p.name != MARKER}
    return listing(a) == listing(b)


def repo_url(repo_spec):
    return f"https://github.com/{repo_spec}.git"


def checkout(repo_spec, ref, trash, run=None):
    """Shallow-clone owner/repo straight into the trash folder (disposable by
    construction, so nothing ever needs deleting); return (path, commit)."""
    url = repo_url(repo_spec)
    trash.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix=f"checkout-{repo_spec.replace('/', '-')}-", dir=trash))
    args = ["git", "clone", "--depth", "1", "-q"] + (["--branch", ref] if ref else []) + [url, str(target)]
    ok, output = run_cli(args, run=run)
    if not ok:
        raise InstallError(f"git clone 失敗：{repo_spec}（{output.splitlines()[-1] if output else '無輸出'}）")
    ok, commit = run_cli(["git", "-C", str(target), "rev-parse", "--short", "HEAD"], run=run)
    return target, commit if ok else "unknown"


def install_github_skill(item, home, trash, run=None, echo=print):
    repo_spec = parse_source(item)[1]
    source_root, commit = checkout(repo_spec, item.get("ref"), trash, run=run)
    sub = item.get("path") or ""
    source = source_root / sub if sub else source_root
    if item["type"] == "command":
        candidates = [source] if source.is_file() else list(source.glob("*.md"))
        if len(candidates) != 1:
            raise InstallError(f"command 來源需指向單一 .md：{repo_spec}/{sub}")
        source = candidates[0]
    elif not (source / "SKILL.md").is_file():
        raise InstallError(f"來源缺少 SKILL.md：{repo_spec}/{sub}")
    target = skill_target(item, home)
    if target.exists() and same_tree(source, target):
        echo(f"SAME    {target}")
        result = "same"
    else:
        if target.exists() or target.is_symlink():
            move_to_trash(target, home, trash)
            echo(f"REPLACE {target} -> trash")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.copy2(source, target)
        else:
            shutil.copytree(source, target)
            (target / MARKER).write_text(json.dumps({
                "source": item["source"], "path": sub, "commit": commit,
                "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        echo(f"PUT     {target} ({repo_spec}@{commit})")
        result = "installed"
    return result


def refresh_marketplace(item, run=None, echo=print):
    """Pull the latest marketplace snapshot so a re-install can see a newer version.
    `claude plugin install` only ever installs what the local snapshot lists."""
    name = item["id"].rpartition("@")[2]
    cmd = ["claude", "plugin", "marketplace", "update", name] if item["tool"] == "claude"         else ["codex", "plugin", "marketplace", "upgrade"]
    ok, output = run_cli(cmd, run=run)
    if not ok:
        echo(f"WARN    marketplace 更新失敗，仍嘗試安裝：{' '.join(cmd)}（{output.splitlines()[-1] if output else '無輸出'}）")


def update_plugin(item, run=None, echo=print):
    """Bring an installed plugin up to the marketplace's current version.
    `claude plugin install` is a no-op for an installed plugin; `update` is the
    upgrade path. Codex has no update verb: re-adding from a refreshed snapshot."""
    refresh_marketplace(item, run=run, echo=echo)
    cmd = ["claude", "plugin", "update", item["id"]] if item["tool"] == "claude" \
        else ["codex", "plugin", "add", item["id"]]
    ok, output = run_cli(cmd, run=run)
    if not ok:
        raise InstallError(f"更新失敗：{' '.join(cmd)}（{output.splitlines()[-1] if output else '無輸出'}）")
    echo(f"UPDATE  {item['tool']} plugin {item['id']}（需重啟工具才生效）")
    return "updated"


def install_plugin(item, marketplace_repo, run=None, echo=print):
    add, install = plugin_commands(item, marketplace_repo)
    if add:
        ok, output = run_cli(add, run=run)
        # "already exists" is fine; anything else is reported but we still try install.
        if not ok and "already" not in output.lower() and "exist" not in output.lower():
            echo(f"WARN    marketplace add 失敗，仍嘗試安裝：{' '.join(add)}")
    ok, output = run_cli(install, run=run)
    if not ok:
        raise InstallError(f"安裝失敗：{' '.join(install)}（{output.splitlines()[-1] if output else '無輸出'}）")
    echo(f"PUT     {item['tool']} plugin {item['id']}")
    return "installed"


def install_item(item, home, *, trash=None, run=None, echo=print, dry_run=False):
    """Install one manifest item. Returns 'installed' | 'same' | 'skipped' | 'planned'."""
    kind, _ = parse_source(item)
    missing = requirements_missing(item)
    if missing:
        hint = item.get("requires_hint", "")
        echo(f"WARN    {item['id']} 需要 PATH 上的 {', '.join(missing)}" + (f"；{hint}" if hint else ""))
    if kind == "repo":
        echo(f"SKIP    {item['id']} 由 deploy 部署")
        return "skipped"
    if kind == "unknown":
        raise InstallError(f"無法解析來源：{item['id']} -> {item.get('source')!r}")
    if dry_run:
        echo(f"PLAN    install {item['tool']} {item['type']} {item['id']} <- {item['source']}")
        return "planned"
    trash = trash or trash_dir(home)
    if item["type"] == "plugin":
        return install_plugin(item, parse_source(item)[1], run=run, echo=echo)
    if kind != "github":
        raise InstallError(f"skill／command 只支援 github: 來源：{item['id']}")
    return install_github_skill(item, home, trash, run=run, echo=echo)
