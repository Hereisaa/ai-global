"""One-shot alignment of this machine with the manifest.

    python setup/align.py            pull -> deploy -> install missing -> resolve conflicts
    python setup/align.py --plan     read-only: print what would happen
    python setup/align.py --yes      apply the automatic part, print conflicts, exit 2
    python setup/align.py --resolve KEY=ACTION ...   apply chosen conflict actions

Automatic: deploying repo-owned files and installing manifest items that are
missing. Anything with two defensible answers is a *conflict* and is only ever
resolved by the user - in the TUI (real terminal) or via --resolve (Claude Code,
CI). Nothing is deleted; replaced items go to ~/.ai-trash.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capabilities as cap  # noqa: E402
import deploy  # noqa: E402
import installers  # noqa: E402

KEEP = "keep"
CONFLICT_ACTIONS = {
    # deployed file changed outside the repo
    "edited":    (("overwrite", "以 repo 覆蓋"), ("writeback", "回寫 repo"), (KEEP, "保留兩邊，下次再問")),
    # local switch contradicts the manifest recommendation
    "switch":    (("enable", "開啟"), ("disable", "關閉"), (KEEP, "維持本機選擇")),
    # installed locally but not in the manifest
    "extra":     ((KEEP, "保留"), ("disable", "停用"), ("trash", "移到 trash")),
    # a standalone skill with the same name as one bundled in an enabled plugin
    "duplicate": (("trash", "獨立版移到 trash"), ("disable", "獨立版停用"), (KEEP, "保留兩份")),
    # installed version differs from the manifest
    "version":   (("update", "更新到 manifest 版本"), (KEEP, "維持目前版本")),
    # settings.json hook points at a script that does not exist
    "hook":      ((KEEP, "保留"), ("unwire", "從 settings.json 移除")),
}


def sh(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


# ---------------------------------------------------------------- git pull

def pull(repo, echo):
    ok, status = sh(["git", "status", "--porcelain"], cwd=repo)
    if not ok:
        echo("PULL    略過：無法讀取 git 狀態")
        return "skipped"
    if status:
        echo("PULL    略過：工作樹有未提交變更，先處理再對齊")
        return "dirty"
    ok, upstream = sh(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=repo)
    if not ok:
        echo("PULL    略過：目前分支沒有 upstream；以目前 clone 內容對齊")
        return "no-upstream"
    ok, output = sh(["git", "pull", "--ff-only"], cwd=repo)
    if not ok:
        echo(f"PULL    失敗（{output.splitlines()[-1] if output else '無輸出'}）；以目前 clone 內容對齊")
        return "failed"
    echo("PULL    " + (output.splitlines()[-1] if output else "ok"))
    return "pulled"


# ---------------------------------------------------------------- conflicts

def plugin_bundled_skills(home):
    """Skill names shipped inside enabled Claude plugins (from the plugin cache)."""
    registry = cap.read_json(home / ".claude/plugins/installed_plugins.json").get("plugins", {})
    switches = cap.read_json(home / ".claude/settings.json").get("enabledPlugins", {})
    names = {}
    for identifier, entries in registry.items():
        if switches.get(identifier) is False or not isinstance(entries, list):
            continue
        for entry in entries:
            root = Path(entry.get("installPath", "")) if isinstance(entry, dict) else None
            if not root or not root.is_dir():
                continue
            for folder in (root / "skills", root / ".claude/skills"):
                if folder.is_dir():
                    for p in folder.iterdir():
                        if (p / "SKILL.md").is_file():
                            names.setdefault(p.name, identifier)
    return names


def installed_versions(home):
    registry = cap.read_json(home / ".claude/plugins/installed_plugins.json").get("plugins", {})
    versions = {}
    for identifier, entries in registry.items():
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("scope", "user") == "user" and entry.get("version"):
                versions[identifier] = str(entry["version"])
    return versions


def hook_commands(settings):
    """Yield (event, command) for every command hook in settings.json."""
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        for group in groups if isinstance(groups, list) else []:
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                if isinstance(hook, dict) and hook.get("type") == "command" and isinstance(hook.get("command"), str):
                    yield event, hook["command"]


def dangling_hooks(home):
    settings = cap.read_json(home / ".claude/settings.json")
    result = []
    for event, command in hook_commands(settings):
        for match in re.finditer(r"~/\.claude/hooks/([\w.-]+)", command):
            if not (home / ".claude/hooks" / match.group(1)).exists():
                result.append((event, command))
    return result


DEPLOY_ROOTS = (  # deployed location -> repo-relative prefix
    (".ai-global/governance", "governance"),
    (".claude/ai-global-disabled/skills", "claude/skills"),
    (".claude/ai-global-disabled/commands", "claude/commands"),
    (".claude/skills", "claude/skills"),
    (".claude/commands", "claude/commands"),
    (".claude/agents", "claude/agents"),
    (".claude/hooks", "claude/hooks"),
    (".claude", "claude"),
    (".codex", "codex"),
)


def repo_relative(home, target):
    """Map a deployed path back to its repo-relative source path."""
    rel = Path(target).resolve().relative_to(home.resolve()).as_posix()
    for prefix, source in DEPLOY_ROOTS:
        if rel == prefix or rel.startswith(prefix + "/"):
            return source + rel[len(prefix):]
    raise installers.InstallError(f"不是 ai-global 部署的路徑：{target}")


def conflict(kind, key, title, detail, default=None):
    actions = CONFLICT_ACTIONS[kind]
    return {"kind": kind, "key": key, "title": title, "detail": detail,
            "actions": [a for a, _ in actions], "labels": dict(actions),
            "default": default or actions[0][0]}


def find_conflicts(repo, home, deploy_results, rows):
    wanted = cap.defaults(repo)
    conflicts = []
    for status, path, _ in deploy_results:
        if status == "EDITED":
            conflicts.append(conflict("edited", f"edited:{path}", f"部署檔在 repo 外被改過：{path}",
                                      "repo 版本與本機版本不同，且本機不是上次部署的內容。"))
    bundled = plugin_bundled_skills(home)
    versions = installed_versions(home)
    for row in rows:
        key = f"{row['tool']}:{row['kind']}:{row['id']}"
        item = wanted.get((row["tool"], row["kind"], row["id"]))
        if item is None:
            if row["tool"] == "codex" and row["id"].endswith(("@openai-bundled", "@openai-primary-runtime")):
                continue  # tool-shipped plugins are not ours to manage
            if row["kind"] == "skill" and row["tool"] == "claude" and row["id"] in bundled:
                conflicts.append(conflict("duplicate", key, f"重複 skill：{row['id']}",
                                          f"plugin {bundled[row['id']]} 已內含同名 skill；兩份都會被列入觸發。"))
            else:
                conflicts.append(conflict("extra", key, f"本機多出：{row['tool']} {row['kind']} {row['id']}",
                                          "manifest 沒有這項；預設保留。要納管請加進 manifest/skills.json。", default=KEEP))
            continue
        if row["installed"] is False:
            continue  # handled by the automatic install step
        if isinstance(row["enabled"], bool) and row["enabled"] != item["default_enabled"]:
            wanted_label = "開啟" if item["default_enabled"] else "關閉"
            conflicts.append(conflict("switch", key, f"開關與 manifest 建議相反：{row['id']}",
                                      f"manifest 建議{wanted_label}，本機目前{'開啟' if row['enabled'] else '關閉'}。", default=KEEP))
        if row["kind"] == "plugin" and item.get("version") and versions.get(row["id"]) and versions[row["id"]] != item["version"]:
            conflicts.append(conflict("version", key, f"版本不同：{row['id']}",
                                      f"本機 {versions[row['id']]}，manifest {item['version']}。"))
    for event, command in dangling_hooks(home):
        conflicts.append(conflict("hook", f"hook:{event}:{command}", f"settings.json 的 {event} hook 指向不存在的腳本",
                                  command, default=KEEP))
    return conflicts


# ---------------------------------------------------------------- actions

def apply_action(c, action, repo, home, trash, echo):
    if action == KEEP:
        echo(f"KEEP    {c['title']}")
        return
    kind, key = c["kind"], c["key"]
    if kind == "edited":
        # "overwrite" and "keep" are carried out by the deploy pass in run().
        if action == "writeback":
            target = Path(key.split(":", 1)[1])
            rel = repo_relative(home, target)
            shutil.copy2(target, repo / rel)
            echo(f"WRITEBACK {rel} <- {target}")
        return
    tool, ckind, identifier = key.split(":", 2)
    if action in ("enable", "disable"):
        echo(cap.toggle(repo, home, tool, ckind, identifier, action == "enable"))
    elif action == "trash":
        row = next(r for r in cap.inventory(repo, home) if (r["tool"], r["kind"], r["id"]) == (tool, ckind, identifier))
        if not row.get("path"):
            raise installers.InstallError(f"沒有可移動的路徑：{identifier}")
        dest = installers.move_to_trash(Path(row["path"]), home, trash)
        echo(f"TRASH   {row['path']} -> {dest}")
    elif action == "update":
        item = cap.defaults(repo)[(tool, ckind, identifier)]
        installers.install_item(item, home, trash=trash, echo=echo)
    elif action == "unwire":
        unwire_hook(home, key, trash, echo)
    else:
        raise installers.InstallError(f"不支援的動作：{action}")


def unwire_hook(home, key, trash, echo):
    _, event, command = key.split(":", 2)
    path = home / ".claude/settings.json"
    settings = cap.read_json(path)
    backup = trash / "settings.json.before-unwire"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    groups = settings.get("hooks", {}).get(event, [])
    for group in groups:
        group["hooks"] = [h for h in group.get("hooks", []) if h.get("command") != command]
    settings["hooks"][event] = [g for g in groups if g.get("hooks")]
    if not settings["hooks"][event]:
        del settings["hooks"][event]
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    echo(f"UNWIRE  {event}: {command}（備份 {backup}）")


# ---------------------------------------------------------------- main

def run(repo, home, *, plan=False, yes=False, no_pull=False, resolve=None, only=None, echo=print, tui=True):
    """Order matters: deployed-file conflicts (EDITED) are decided *before* the
    install pass so a "keep" never gets overwritten; capability conflicts are
    decided after the install pass so freshly installed items are visible."""
    trash = installers.trash_dir(home)
    failures = []
    echo(f"repo:   {repo}")
    echo(f"home:   {home}")
    pulled = None if plan or no_pull else pull(repo, echo)
    check = deploy.run(repo, home, "check", echo=lambda *_: None)
    for status, path, note in check["results"]:
        if status != "OK" and (plan or status != "EDITED"):
            echo(f"{'PLAN ' if plan else 'DRIFT'}   {status} {path}" + (f" - {note}" if note else ""))
    cli = cap.claude_cli_plugins(home)
    rows = cap.inventory(repo, home, cli)
    conflicts = find_conflicts(repo, home, check["results"], rows)
    chosen = dict(resolve or {})
    interactive = not plan and not yes and tui and sys.stdin.isatty() and sys.stdout.isatty()

    def decide(pending):
        if not pending or plan or all(c["key"] in chosen for c in pending):
            return
        if interactive:
            try:
                from capabilities_tui import resolve_conflicts
            except ImportError:
                echo("互動模式需要 prompt_toolkit（setup/requirements-tui.txt）；改用 --resolve 或在 Claude Code 中處理。")
                return
            picked = resolve_conflicts([c for c in pending if c["key"] not in chosen])
            if picked:
                chosen.update(picked)

    def apply(pending):
        unresolved = []
        for c in pending:
            action = chosen.get(c["key"])
            if action is None:
                unresolved.append(c)
                continue
            if action not in c["actions"]:
                failures.append(f"{c['key']} 不支援動作 {action}")
                continue
            try:
                apply_action(c, action, repo, home, trash, echo)
            except (installers.InstallError, cap.ControlError, OSError) as exc:
                failures.append(f"{c['key']}: {exc}")
                echo(f"FAIL    {c['key']}: {exc}")
        return unresolved

    # 1. Deployed files: decide EDITED ones, then deploy with "keep" honoured.
    edited = [c for c in conflicts if c["kind"] == "edited"]
    decide(edited)
    unresolved = apply([c for c in edited if chosen.get(c["key"]) == "writeback"])  # writeback before install
    keep = {repo_relative(home, c["key"].split(":", 1)[1]) for c in edited
            if chosen.get(c["key"]) in (None, KEEP)}
    unresolved += [c for c in edited if chosen.get(c["key"]) is None]
    for c in edited:
        if chosen.get(c["key"]) in ("overwrite", KEEP):
            echo(f"{'OVERWRITE' if chosen[c['key']] == 'overwrite' else 'KEEP   '} {c['title']}")
    result = check if plan else deploy.run(repo, home, "install", echo=echo, keep_edited=keep)

    # 2. Missing manifest items: automatic.
    wanted = cap.defaults(repo)
    missing = [wanted[(r["tool"], r["kind"], r["id"])] for r in rows
               if r["origin"] == "project-default" and r["installed"] is False]
    if only:
        unknown = sorted(set(only) - {i["id"] for i in wanted.values()})
        if unknown:
            failures.append(f"manifest 沒有這些 id：{', '.join(unknown)}")
        missing = [i for i in wanted.values() if i["id"] in only]
    for item in missing:
        try:
            installers.install_item(item, home, trash=trash, echo=echo, dry_run=plan)
        except installers.InstallError as exc:
            failures.append(str(exc))
            echo(f"FAIL    {exc}")

    # 3. Capability conflicts: decided on the post-install inventory.
    if missing and not plan:
        rows = cap.inventory(repo, home, cap.claude_cli_plugins(home))
        conflicts = edited + [c for c in find_conflicts(repo, home, [], rows)]
    others = [] if only else [c for c in conflicts if c["kind"] != "edited"]
    decide(others)
    unresolved += apply(others)

    if unresolved:
        echo("")
        echo(f"CONFLICT {len(unresolved)} 項需要你決定（--resolve KEY=ACTION，或在真正的終端執行以開啟互動選單）：")
        for c in unresolved:
            options = " / ".join(f"{a}={c['labels'][a]}" for a in c["actions"])
            echo(f"  [{c['kind']}] {c['title']}")
            echo(f"      {c['detail']}")
            echo(f"      KEY={c['key']}  選項：{options}（預設 {c['default']}）")
    if trash.exists():
        echo(f"NOTE    被取代的項目在 {trash}")
    return {"pull": pulled, "deploy": result, "missing": [i["id"] for i in missing],
            "conflicts": conflicts, "unresolved": unresolved, "failures": failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description="把本機對齊 manifest：部署、補裝缺項、列出並解決衝突")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=Path.home(), help="僅隔離測試或指定使用者目錄")
    parser.add_argument("--plan", action="store_true", help="只列計畫與衝突，不動任何檔案")
    parser.add_argument("--yes", action="store_true", help="套用自動項；衝突只列出（不開互動選單）")
    parser.add_argument("--no-pull", action="store_true", help="不執行 git pull")
    parser.add_argument("--resolve", action="append", default=[], metavar="KEY=ACTION", help="指定衝突的處置，可重複")
    parser.add_argument("--only", action="append", default=[], metavar="ID", help="只（重新）安裝指定 manifest id，不處理能力衝突；可重複")
    parser.add_argument("--json", action="store_true", help="最後輸出 JSON 摘要")
    args = parser.parse_args(argv)
    resolve = {}
    for pair in args.resolve:
        key, sep, action = pair.rpartition("=")
        if not sep or not key:
            parser.error(f"--resolve 格式為 KEY=ACTION：{pair}")
        resolve[key] = action
    try:
        summary = run(args.repo.resolve(), args.home.resolve(), plan=args.plan, yes=args.yes,
                      no_pull=args.no_pull, resolve=resolve, only=set(args.only) or None)
    except cap.ControlError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({k: v for k, v in summary.items() if k != "deploy"}, ensure_ascii=False, indent=2, default=str))
    if summary["failures"]:
        return 1
    return 2 if summary["unresolved"] and not args.plan else 0


if __name__ == "__main__":
    raise SystemExit(main())
