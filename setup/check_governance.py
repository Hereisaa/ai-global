#!/usr/bin/env python3
"""Read-only checks, Python 3.9+, standard library only.

Require two routers, ten governance documents, root README, runtime reference,
and sync-check skill. Check links in those files and current governance/*.md
and docs/reference/*.md only; never recursively scan the repository or backups.
"""

import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

try:
    import tomllib
except ImportError:
    tomllib = None


GOVERNANCE_FILES = (
    "10-dispatch.md", "20-judgment.md", "30-templates.md", "40-maintenance.md",
    "50-safety.md", "60-project-bootstrap.md", "70-behavior-contract.md",
    "80-engineering.md",
)
ROUTERS = ("codex/AGENTS.md", "claude/CLAUDE.md")
RUNTIME_DOC = "docs/reference/agent-runtime.md"
SYNC_SKILL = "claude/skills/sync-check/SKILL.md"
GOVERNANCE_DOCUMENTS = GOVERNANCE_FILES + ("README.md", "USER-GUIDE.md")
REQUIRED_DOCUMENTS = ROUTERS + tuple("governance/" + name for name in GOVERNANCE_DOCUMENTS) + (
    "README.md", RUNTIME_DOC, SYNC_SKILL,
)
SETTINGS_KEYS = {
    "claude_settings": ("model", "effortLevel"),
    "codex_config": ("model", "model_reasoning_effort", "personality"),
}


def prose_lines(text):
    """Ignore fenced examples while retaining original line numbers."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def markdown_targets(text):
    for number, line in prose_lines(text):
        # Inline code is an example, not a rendered Markdown link.
        line = re.sub(r"(`+).*?\1", "", line)
        for match in re.finditer(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)", line):
            yield number, match.group(1) or match.group(2)
        reference = re.match(r"^\s{0,3}\[[^]]+\]:\s*(?:<([^>]+)>|(\S+))", line)
        if reference:
            yield number, reference.group(1) or reference.group(2)


class Checks:
    def __init__(self):
        self.results = []

    def report(self, status, message):
        self.results.append((status, message))

    @property
    def exit_code(self):
        return int(any(status == "FAIL" for status, _ in self.results))

    def read(self, path, required=True):
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            self.report("FAIL" if required else "WARN", f"無法讀取：{path}")
            return None

    def json_object(self, path, required=True):
        text = self.read(path, required)
        if text is None:
            return None
        try:
            value = json.loads(text)
        except (ValueError, RecursionError):
            self.report("FAIL", f"JSON 格式無效：{path}（不顯示設定內容）")
            return None
        if not isinstance(value, dict):
            self.report("FAIL", f"JSON 頂層必須是物件：{path}")
            return None
        return value

    def budget(self, path, text, limit):
        count = len(text.splitlines())
        if count > limit:
            self.report("WARN", f"行數預算超標：{path}，{count}/{limit} 行")

    def document(self, path, name):
        if not path.is_file():
            self.report("FAIL", f"必要文件不存在或不是檔案：{name}")
            return None
        text = self.read(path)
        if text is None:
            return None
        body = text.strip()
        if not body:
            self.report("FAIL", f"文件內容空白：{name}")
            return text
        if name == SYNC_SKILL and body.startswith("---\n"):
            parts = body.split("\n---", 1)
            body = parts[1].strip() if len(parts) == 2 else ""
        if not body or not re.fullmatch(r"# \S.*", body.splitlines()[0]):
            self.report("FAIL", f"文件缺少首行標題：{name}")
        return text

    def links(self, path, name, text):
        for number, target in markdown_targets(text):
            parsed = urlsplit(target)
            relative = unquote(parsed.path)
            if parsed.scheme or parsed.netloc or not relative:
                continue
            if relative.startswith(("/", "~")) or "backups" in Path(relative).parts:
                continue
            if not (path.parent / relative).exists():
                self.report("FAIL", f"相對連結斷鏈：{name}:{number}，{relative}")

    def repository(self, root):
        names = set(REQUIRED_DOCUMENTS)
        for directory in ("governance", "docs/reference"):
            names.update(path.relative_to(root).as_posix() for path in (root / directory).glob("*.md"))
        documents = {name: self.document(root / name, name) for name in sorted(names)}
        for name, text in documents.items():
            if text is None:
                continue
            if name.startswith("governance/"):
                self.budget(name, text, 300)
            self.links(root / name, name, text)
        if not self.exit_code:
            self.report("PASS", "文件內容與連結有效：兩個 router、十份必要治理文件、根 README、runtime、sync-check skill，以及 governance 與 docs/reference 直層 Markdown；未掃描 backups")
        routers = [documents[name] for name in ROUTERS]
        if all(text is not None for text in routers):
            bodies = [text.splitlines()[1:] for text in routers]
            if bodies[0] != bodies[1]:
                self.report("FAIL", "兩個 router 除首行外內容不一致")
            else:
                self.report("PASS", "兩個 router 共通內容一致")
        for name, text in zip(ROUTERS, routers):
            if text is None:
                continue
            self.budget(name, text, 60)
            prose = "\n".join(line for _, line in prose_lines(text))
            for filename in GOVERNANCE_FILES:
                route = f"~/Developer/agent-governance/{filename}"
                if route not in prose:
                    self.report("FAIL", f"router 缺少制度路由：{name}，{filename}")
        manifest = self.json_object(root / "manifest/settings.json")
        if manifest is not None:
            valid = True
            for section, keys in SETTINGS_KEYS.items():
                block = manifest.get(section)
                if not isinstance(block, dict):
                    self.report("FAIL", f"manifest 區塊缺失或格式無效：{section}")
                    valid = False
                    continue
                for key in keys:
                    if key in block and (not isinstance(block[key], str) or not block[key]):
                        self.report("FAIL", f"manifest 白名單欄位必須是非空字串：{section}.{key}")
                        valid = False
            if valid:
                self.report("PASS", "manifest 白名單設定結構有效")
        return manifest

    def deployment(self, source, target, directory=False):
        if not target.exists():
            self.report("WARN", f"本地部署缺失或斷鏈：{target}")
            return
        try:
            same = source.samefile(target)
            kind = "連結" if target.is_symlink() or same else "副本"
            self.report("PASS" if same else "WARN", f"本地部署類型：{target}，{kind}，{'指向正本' if same else '未指向目前正本'}")
            if directory:
                for filename in GOVERNANCE_DOCUMENTS:
                    self.content(source / filename, target / filename)
            else:
                self.content(source, target)
        except OSError:
            self.report("WARN", f"本地部署無法比對：{target}")

    def content(self, source, target):
        expected = self.read(source)
        actual = self.read(target, required=False)
        if expected is not None and actual is not None:
            equal = expected == actual
            self.report("PASS" if equal else "WARN", f"本地內容{'一致' if equal else '漂移'}：{target}")

    def compare_settings(self, expected, actual, section):
        for key in SETTINGS_KEYS[section]:
            if key not in expected:
                continue
            if key not in actual:
                self.report("WARN", f"本地白名單設定缺失或未能解析：{section}.{key}")
            elif not isinstance(actual[key], str):
                self.report("FAIL", f"本地白名單設定必須是字串：{section}.{key}")
            elif expected[key] != actual[key]:
                self.report("WARN", f"本地白名單設定與 manifest 不一致：{section}.{key}（不顯示值）")
            else:
                self.report("PASS", f"本地白名單設定一致：{section}.{key}")

    def codex_settings(self, path):
        if tomllib is None:
            self.report("WARN", "Python 未提供 tomllib；略過 Codex TOML 對帳，請使用 Python 3.11 以上")
            return None
        text = self.read(path, required=False)
        if text is None:
            return None
        try:
            config = tomllib.loads(text)
        except (ValueError, RecursionError):
            self.report("FAIL", f"TOML 格式無效：{path}（不顯示設定內容）")
            return None
        return {key: config[key] for key in SETTINGS_KEYS["codex_config"] if key in config}

    def local(self, root, home, manifest):
        self.deployment(root / ROUTERS[0], home / ".codex/AGENTS.md")
        self.deployment(root / ROUTERS[1], home / ".claude/CLAUDE.md")
        self.deployment(root / "governance", home / "Developer/agent-governance", directory=True)
        if (home / ".codex/AGENTS.override.md").exists():
            self.report("WARN", "本地存在 Codex AGENTS.override.md，可能覆蓋全域 router")
        if (home / ".claude/settings.local.json").exists():
            self.report("WARN", "本地存在 Claude settings.local.json，本工具不判定設定優先序")
        if not isinstance(manifest, dict):
            return
        for section in SETTINGS_KEYS:
            expected = manifest.get(section)
            if not isinstance(expected, dict):
                continue
            if section == "claude_settings":
                actual = self.json_object(home / ".claude/settings.json", required=False)
            else:
                actual = self.codex_settings(home / ".codex/config.toml")
            if actual is not None:
                self.compare_settings(expected, actual, section)
        self.report("WARN", "本地對帳不代表當次會話已載入、讀取或遵循；僅比對白名單設定，未驗證操作權限")


def main(argv=None):
    parser = argparse.ArgumentParser(description="唯讀檢查治理路由、文件連結與本地部署")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="待檢查的倉庫路徑")
    parser.add_argument("--local", action="store_true", help="額外對帳本地部署與白名單設定")
    args = parser.parse_args(argv)
    checks = Checks()
    root = args.repo.resolve()
    manifest = checks.repository(root)
    if args.local:
        checks.local(root, Path.home(), manifest)
    for status, message in checks.results:
        print(f"{status} {message}")
    print(f"{'FAIL' if checks.exit_code else 'PASS'} 檢查結束：{sum(s == 'FAIL' for s, _ in checks.results)} 項失敗，{sum(s == 'WARN' for s, _ in checks.results)} 項提醒；未修改檔案")
    return checks.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
