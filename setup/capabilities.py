"""User-scope capability inventory and explicit, reversible enablement controls.

Python 3.11+; no third-party dependencies. Never installs or fetches capabilities.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
import unicodedata
import uuid


class ControlError(Exception):
    pass


def read_json(path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, OSError):
        raise ControlError(f"JSON 無法解析，未修改：{path}") from None


def read_toml(path):
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        return text, tomllib.loads(text)
    except (ValueError, OSError):
        raise ControlError(f"TOML 無法解析，未修改：{path}") from None


def defaults(repo):
    items = read_json(repo / "manifest/skills.json").get("items", [])
    result = {}
    if not isinstance(items, list):
        raise ControlError("manifest items 必須是清單")
    for item in items:
        if not isinstance(item, dict):
            raise ControlError("manifest 項目必須是物件")
        key = (item.get("tool"), item.get("type"), item.get("id"))
        if (key[0] not in ("claude", "codex") or key[1] not in ("skill", "plugin", "command")
                or not isinstance(key[2], str) or not key[2] or type(item.get("default_enabled")) is not bool
                or key in result):
            raise ControlError("manifest 能力識別碼、預設值無效或重複")
        result[key] = item
    return result


def normalized_skill(path, home):
    path = str(path)
    if path.startswith("~/"):
        path = str(home / path[2:])
    p = Path(path)
    if p.name == "SKILL.md":
        p = p.parent
    return os.path.normcase(str(p.resolve()))


def claude_cli_plugins(home):
    """Cross-check the registry with `claude plugin list` (read-only).

    installed_plugins.json is not documented; the CLI is the authority. Only
    consulted for the real home, since the CLI cannot be pointed at a fixture.
    Returns the set of listed plugin ids, or None when the CLI is unavailable.
    """
    if home != Path.home() or not shutil.which("claude"):
        return None
    try:
        result = subprocess.run(["claude", "plugin", "list"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return parse_cli_plugins(result.stdout)


def parse_cli_plugins(text):
    # Each entry starts with a marker glyph followed by "<plugin>@<marketplace>".
    return {m.group(1) for m in re.finditer(r"(?m)^\s*\S\s+([\w.-]+@[\w.-]+)\s*$", text)}


def inventory(repo, home, cli_plugins=None):
    wanted = defaults(repo)
    records = {}

    def add(tool, kind, identifier, installed=False, enabled=None, path=None, note=""):
        key = (tool, kind, identifier)
        default = wanted.get(key)
        records[key] = {"tool": tool, "kind": kind, "id": identifier,
                        "origin": "project-default" if default else "local-existing",
                        "default_enabled": default["default_enabled"] if default else None,
                        "installed": installed, "enabled": enabled,
                        "path": str(path) if path else None, "note": note}

    for tool, kind, identifier in wanted:
        add(tool, kind, identifier)

    for kind, folder in (("skill", "skills"), ("command", "commands")):
        active = home / ".claude" / folder
        parked = home / ".claude/ai-global-disabled" / folder
        for base, enabled in ((active, True), (parked, False)):
            if not base.exists():
                continue
            for p in sorted(base.iterdir()):
                valid = p.is_dir() and (p / "SKILL.md").is_file() if kind == "skill" else p.is_file() and p.suffix == ".md"
                if p.name.startswith(".") or not valid:
                    continue
                identifier = p.name if kind == "skill" else p.stem
                key = ("claude", kind, identifier)
                if key in records and records[key]["installed"]:
                    raise ControlError(f"啟用與停用位置同時存在：{identifier}")
                add("claude", kind, identifier, True, enabled, p)

    settings = read_json(home / ".claude/settings.json")
    plugins = read_json(home / ".claude/plugins/installed_plugins.json").get("plugins", {})
    switches = settings.get("enabledPlugins", {})
    if not isinstance(plugins, dict) or not isinstance(switches, dict):
        raise ControlError("Claude plugin 設定結構無效")
    for identifier in plugins.keys() | switches.keys():
        state = switches.get(identifier)
        if state is not None and type(state) is not bool:
            raise ControlError("Claude plugin enabled 值不是布林值")
        entries = plugins.get(identifier, [])
        user_entries = [e for e in entries if isinstance(e, dict) and e.get("scope", "user") == "user"] if isinstance(entries, list) else []
        installed = bool(user_entries)
        note = "使用者層設定；專案或管理政策可能覆蓋" if installed else "只有設定或其他 scope 安裝；請用原生插件管理確認"
        if cli_plugins is not None:
            if identifier in cli_plugins:
                installed, note = True, "CLI 已列出；專案或管理政策可能覆蓋"
            elif installed:
                note = "登錄有但 CLI 未列出（已停用的 plugin 不會列出；要卸載先 enable 再 uninstall）"
        add("claude", "plugin", identifier, installed, state, note=note)
    if cli_plugins is not None:
        for identifier in sorted(cli_plugins - (plugins.keys() | switches.keys())):
            add("claude", "plugin", identifier, True, None, note="CLI 列出但本機登錄與設定皆無；請用原生插件管理確認")

    _, config = read_toml(home / ".codex/config.toml")
    codex_plugins = config.get("plugins", {})
    skill_block = config.get("skills", {})
    if not isinstance(skill_block, dict):
        raise ControlError("Codex skills 設定結構無效")
    skill_settings = skill_block.get("config", [])
    if not isinstance(codex_plugins, dict) or not isinstance(skill_settings, list):
        raise ControlError("Codex 能力設定結構無效")
    for identifier, block in codex_plugins.items():
        if not isinstance(block, dict) or type(block.get("enabled", True)) is not bool:
            raise ControlError("Codex plugin 設定結構無效")
        # A configured entry is not proof of installation or runtime loading.
        add("codex", "plugin", identifier, None, block.get("enabled", True),
            note="已設定；安裝與當次載入狀態請由 Codex 插件管理確認")
    overrides = {}
    for entry in skill_settings:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or type(entry.get("enabled")) is not bool:
            raise ControlError("Codex skill override 結構無效")
        key = normalized_skill(entry["path"], home)
        if key in overrides:
            raise ControlError("Codex skill 有重複 override，請先由原生設定整理")
        overrides[key] = entry["enabled"]
    for folder in (".codex/skills", ".agents/skills"):
        base = home / folder
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if p.name.startswith(".") or not (p / "SKILL.md").is_file():
                continue
            add("codex", "skill", f"{folder}/{p.name}", True,
                overrides.get(normalized_skill(p, home), True), p,
                "獨立 skill；插件內 skills 請以所屬 plugin 開關")
    return [records[k] for k in sorted(records)]


def toml_enable(text, kind, identifier, enabled, home):
    original = tomllib.loads(text)
    expected = copy.deepcopy(original)
    value = "true" if enabled else "false"
    spans = list(re.finditer(r"(?m)^\s*(\[\[?[^\n]+?\]\]?)\s*(?:#[^\n]*)?$", text))
    selected = None
    if kind == "plugin":
        block = expected.setdefault("plugins", {}).setdefault(identifier, {})
        block["enabled"] = enabled
    else:
        entries = expected.setdefault("skills", {}).setdefault("config", [])
        matches = [e for e in entries if normalized_skill(e["path"], home) == normalized_skill(identifier, home)]
        if len(matches) > 1:
            raise ControlError("重複 skill override，未修改")
        if matches:
            matches[0]["enabled"] = enabled
        else:
            entries.append({"path": identifier, "enabled": enabled})
    for i, match in enumerate(spans):
        end = spans[i + 1].start() if i + 1 < len(spans) else len(text)
        fragment = text[match.start():end]
        try:
            parsed = tomllib.loads(fragment)
        except ValueError:
            continue
        if kind == "plugin":
            hit = isinstance(parsed.get("plugins"), dict) and identifier in parsed["plugins"]
        else:
            entries = parsed.get("skills", {}).get("config", [])
            hit = len(entries) == 1 and normalized_skill(entries[0].get("path", ""), home) == normalized_skill(identifier, home)
        if hit:
            if selected is not None:
                raise ControlError("無法唯一定位 TOML 開關，未修改")
            selected = (match.start(), end, fragment)
    if selected:
        start, end, fragment = selected
        pattern = r"(?m)^(\s*enabled\s*=\s*)(true|false)(\s*(?:#[^\n]*)?)$"
        if re.search(pattern, fragment):
            fragment = re.sub(pattern, lambda m: m[1] + value + m[3], fragment, count=1)
        else:
            first, sep, rest = fragment.partition("\n")
            fragment = first + "\n" + f"enabled = {value}\n" + rest
        updated = text[:start] + fragment + text[end:]
    else:
        header = f"[plugins.{json.dumps(identifier)}]" if kind == "plugin" else "[[skills.config]]"
        path = "" if kind == "plugin" else f"path = {json.dumps(identifier)}\n"
        updated = text.rstrip() + f"\n\n{header}\n{path}enabled = {value}\n"
    try:
        if tomllib.loads(updated) != expected:
            raise ValueError()
    except ValueError:
        raise ControlError("TOML 格式無法安全局部修改；請用原生設定開關，未寫入") from None
    return updated


def safe_write(path, before, after, home):
    if before == after:
        return None
    if path.is_symlink() or not path.resolve().is_relative_to(home.resolve()):
        raise ControlError("設定檔為連結，請由原生工具處理，未修改")
    batch = home / ".ai-trash" / ("ai-global-settings-" + uuid.uuid4().hex)
    batch.mkdir(parents=True, mode=0o700)
    if path.exists():
        backup = batch / path.name
        shutil.copy2(path, backup)
        backup.chmod(0o600)
    current = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if current != before:
        raise ControlError("設定在處理期間已改變，未覆寫；請重新列清單")
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = batch / (path.name + ".new")
    staged.write_text(after, encoding="utf-8", newline="\n")
    staged.chmod(0o600)
    current = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if current != before:
        raise ControlError("設定在寫入前已改變，未覆寫；請重新列清單")
    os.replace(staged, path)
    return batch


def toggle(repo, home, tool, kind, identifier, enabled):
    rows = inventory(repo, home)
    matches = [r for r in rows if (r["tool"], r["kind"], r["id"]) == (tool, kind, identifier)]
    if len(matches) != 1:
        raise ControlError("找不到唯一能力；請先 list 並使用完整 id")
    row = matches[0]
    if row["installed"] is False:
        raise ControlError("能力尚未在使用者層安裝；開關不會代為下載或安裝")
    if row["enabled"] is enabled:
        return "設定已符合，未修改"
    if tool == "claude" and kind in ("skill", "command"):
        folder = "skills" if kind == "skill" else "commands"
        source = Path(row["path"])
        base = home / ".claude" / folder if enabled else home / ".claude/ai-global-disabled" / folder
        dest = base / source.name
        allowed = (home / ".claude").resolve()
        if (source.is_symlink() or not source.resolve().is_relative_to(allowed)
                or not dest.resolve().is_relative_to(allowed) or dest.exists() or dest.is_symlink()):
            raise ControlError("能力路徑為連結、超出範圍或目的地已存在，未搬移")
        base.mkdir(parents=True, exist_ok=True)
        source.rename(dest)
        return f"已{'啟用' if enabled else '停用'}：{identifier}；保留於 {dest}"
    path = home / (".claude/settings.json" if tool == "claude" else ".codex/config.toml")
    if tool == "claude":
        before = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        config = read_json(path)
        config.setdefault("enabledPlugins", {})[identifier] = enabled
        after = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    else:
        before, _ = read_toml(path)
        target = str(Path(row["path"]).resolve()) if kind == "skill" else identifier
        after = toml_enable(before, kind, target, enabled, home)
    backup = safe_write(path, before, after, home)
    return f"已{'啟用' if enabled else '停用'}使用者層設定：{identifier}；備份 {backup}。請重新載入或重啟工具確認；專案或管理政策可能覆蓋。"


def display_width(text):
    """Count terminal columns for ordinary Latin/CJK text and combining marks."""
    return sum(0 if unicodedata.combining(char) else
               2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
               for char in text)


def table(header, rows, indent=""):
    """Column-aligned text table (CJK-aware); header, dashed rule, then rows."""
    cells = [[str(c) for c in header]] + [[str(c) for c in row] for row in rows]
    widths = [max(display_width(cell) for cell in column) for column in zip(*cells)]
    lines = [indent + "  ".join(cell + " " * (width - display_width(cell))
                                for cell, width in zip(row, widths)).rstrip() for row in cells]
    lines.insert(1, indent + "  ".join("-" * width for width in widths))
    return "\n".join(lines)


def capability_table(rows):
    label = lambda value: "未知" if value is None else ("是" if value else "否")
    return table(["工具", "種類", "ID", "來源", "專案預設", "安裝", "本機開關"],
                 [[row["tool"], row["kind"], row["id"],
                   "專案預設" if row["origin"] == "project-default" else "本機既有",
                   label(row["default_enabled"]), label(row["installed"]), label(row["enabled"])]
                  for row in rows])


def main(argv=None):
    parser = argparse.ArgumentParser(description="列出專案預設與本機既有能力，明確開關使用者層設定")
    parser.add_argument("action", choices=("list", "manage", "enable", "disable"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=Path.home(), help="僅隔離測試或指定使用者目錄")
    parser.add_argument("--tool", choices=("claude", "codex"))
    parser.add_argument("--kind", choices=("skill", "plugin", "command"))
    parser.add_argument("--id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--demo", action="store_true", help="manage 示範模式，不讀寫本機能力設定")
    args = parser.parse_args(argv)
    if args.demo and args.action != "manage":
        parser.error("--demo 僅用於 manage")
    if args.json and args.action != "list":
        parser.error("--json 僅用於 list")
    try:
        if args.action == "manage":
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ControlError("manage 需要互動式 Terminal；請在 PowerShell、Windows Terminal 或 macOS Terminal 直接執行。")
            try:
                from capabilities_tui import demo_rows, manage
            except ImportError:
                raise ControlError("互動模式需要 prompt_toolkit：請用目前 Python 執行 python -m pip install -r setup/requirements-tui.txt，或使用專案 .venv。") from None
            cli = None if args.demo else claude_cli_plugins(args.home)
            rows = demo_rows() if args.demo else inventory(args.repo, args.home, cli)
            rows = [r for r in rows if (not args.tool or r["tool"] == args.tool) and (not args.kind or r["kind"] == args.kind) and (not args.id or r["id"] == args.id)]
            return manage(rows, capability_table, lambda: inventory(args.repo, args.home, claude_cli_plugins(args.home)),
                          lambda tool, kind, identifier, enabled: toggle(args.repo, args.home, tool, kind, identifier, enabled), demo=args.demo)
        elif args.action != "list":
            if not all((args.tool, args.kind, args.id)):
                parser.error("開關必須指定 --tool、--kind、--id")
            print(toggle(args.repo, args.home, args.tool, args.kind, args.id, args.action == "enable"))
        else:
            rows = inventory(args.repo, args.home, claude_cli_plugins(args.home))
            rows = [r for r in rows if (not args.tool or r["tool"] == args.tool) and (not args.kind or r["kind"] == args.kind) and (not args.id or r["id"] == args.id)]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                print(capability_table(rows))
                print("唯讀；使用者層設定不等於當次載入。插件內 skills 隨 plugin 控制；其他專案／系統／管理層未枚舉。")
        return 0
    except (ControlError, OSError) as exc:
        print(str(exc) if isinstance(exc, ControlError) else "檔案操作失敗；未輸出設定內容，請檢查路徑與權限", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
