#!/usr/bin/env python3
"""Read-only checks, Python 3.9+, standard library only.

Require two routers, ten governance documents, root README, runtime reference,
and the ai-global skill. Check links in those files and current governance/*.md,
docs/reference/*.md and ai-global commands/*.md only; never recursively scan
the repository.

The two routers are parallel, not identical: they must share the same `##`
section order (Claude may add its Cowork section) and each must carry its own
tool's branch prefix. Copying the other tool's prefix is the classic mistake,
so it is checked explicitly.
"""

import argparse
from datetime import date
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
ROUTE_PREFIX = "~/.ai-global/governance/"
TOOL_PREFIX = {"codex/AGENTS.md": "codex/<主題>", "claude/CLAUDE.md": "claude/<主題>"}
CLAUDE_ONLY_SECTIONS = ("## Cowork / 多端一致",)
RUNTIME_DOC = "docs/reference/agent-runtime.md"
SYNC_SKILL = "claude/skills/ai-global/SKILL.md"
SOURCES_FILE = "manifest/sources.json"
GOVERNANCE_DOCUMENTS = GOVERNANCE_FILES + ("README.md", "USER-GUIDE.md")
REQUIRED_DOCUMENTS = ROUTERS + tuple("governance/" + name for name in GOVERNANCE_DOCUMENTS) + (
    "README.md", RUNTIME_DOC, SYNC_SKILL,
)
DEPLOYED_GOVERNANCE = ".ai-global/governance"
SETTINGS_KEYS = {
    "claude_settings": ("model", "effortLevel"),
    "codex_config": ("model", "model_reasoning_effort", "personality"),
}
ROUTER_LINE_BUDGET = 120
GOVERNANCE_LINE_BUDGET = 300


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


def sections(text):
    return [line.rstrip() for _, line in prose_lines(text) if line.startswith("## ")]


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

    def links(self, path, name, text, deployed=False, source_repo=None):
        for number, target in markdown_targets(text):
            parsed = urlsplit(target)
            relative = unquote(parsed.path)
            if parsed.scheme or parsed.netloc or not relative:
                continue
            if relative.startswith(("/", "~")):
                continue
            base = path.parent
            if deployed and relative.startswith("../"):
                if source_repo is None:
                    self.report("WARN", f"無法驗證跨目錄連結（部署 state 的 source_repo 不可用）：{name}:{number}，{relative}")
                    continue
                base = source_repo / "governance"
            if not (base / relative).exists():
                self.report("FAIL", f"相對連結斷鏈：{name}:{number}，{relative}")

    def routers(self, documents):
        texts = {name: documents[name] for name in ROUTERS}
        if all(text is not None for text in texts.values()):
            codex = sections(texts[ROUTERS[0]])
            claude = [s for s in sections(texts[ROUTERS[1]]) if s not in CLAUDE_ONLY_SECTIONS]
            if codex != claude:
                self.report("FAIL", "兩個 router 節次不對齊（Cowork 為 Claude 專屬例外）")
            else:
                self.report("PASS", "兩個 router 節次對齊")
        for name, text in texts.items():
            if text is None:
                continue
            self.budget(name, text, ROUTER_LINE_BUDGET)
            prose = "\n".join(line for _, line in prose_lines(text))
            if ROUTE_PREFIX not in prose:
                self.report("FAIL", f"router 缺少制度目錄路徑：{name}，{ROUTE_PREFIX}")
            for filename in GOVERNANCE_FILES:
                if filename not in prose:
                    self.report("FAIL", f"router 缺少制度路由：{name}，{filename}")
            own = TOOL_PREFIX[name]
            other = next(prefix for other_name, prefix in TOOL_PREFIX.items() if other_name != name)
            if f"`{own}`" not in prose:
                self.report("FAIL", f"router 缺少本工具的分支前綴：{name}，{own}")
            if re.search(r"一律用\s*\**`" + re.escape(other) + "`", prose):
                self.report("FAIL", f"router 照抄了對面工具的分支前綴：{name}，{other}")

    def repository(self, root):
        names = set(REQUIRED_DOCUMENTS)
        for directory in ("governance", "docs/reference", "claude/skills/ai-global/commands"):
            names.update(path.relative_to(root).as_posix() for path in (root / directory).glob("*.md"))
        documents = {name: self.document(root / name, name) for name in sorted(names)}
        for name, text in documents.items():
            if text is None:
                continue
            if name.startswith("governance/"):
                self.budget(name, text, GOVERNANCE_LINE_BUDGET)
            self.links(root / name, name, text)
        if not self.exit_code:
            self.report("PASS", "文件內容與連結有效：兩個 router、十份必要治理文件、根 README、runtime、ai-global skill 與 commands，以及 governance 與 docs/reference 直層 Markdown")
        self.routers(documents)
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
        self.sources(root)
        return manifest

    def sources(self, root, today=None):
        """evolve 的核對來源：結構有效，且 last_checked 未超過 stale_days。"""
        data = self.json_object(root / SOURCES_FILE)
        if data is None:
            return
        stale_days = data.get("stale_days")
        entries = data.get("sources")
        if type(stale_days) is not int or stale_days <= 0 or not isinstance(entries, list):
            self.report("FAIL", f"{SOURCES_FILE} 需要正整數 stale_days 與 sources 清單")
            return
        today = today or date.today()
        stale = []
        for entry in entries:
            if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k] for k in ("id", "url", "last_checked")):
                self.report("FAIL", f"{SOURCES_FILE} 每筆需要非空 id、url、last_checked")
                return
            try:
                checked = date.fromisoformat(entry["last_checked"])
            except ValueError:
                self.report("FAIL", f"{SOURCES_FILE} last_checked 需為 YYYY-MM-DD：{entry['id']}")
                return
            if (today - checked).days > stale_days:
                stale.append(f"{entry['id']}（{entry['last_checked']}）")
        if stale:
            self.report("WARN", f"核對來源超過 {stale_days} 天未核對，建議執行 /ai-global evolve：{'、'.join(stale)}")
        else:
            self.report("PASS", f"{len(entries)} 個核對來源皆在 {stale_days} 天內核對過")

    def deployment(self, source, target, directory=False):
        # Deployed files are copies by design; a link here is a leftover from the
        # old symlink layout and install.* will replace it.
        if target.is_symlink():
            self.report("WARN", f"本地部署是連結，應為實體副本（重跑 setup/install.*）：{target}")
            return
        if not target.exists():
            self.report("WARN", f"本地部署缺失：{target}")
            return
        if directory:
            for filename in GOVERNANCE_DOCUMENTS:
                self.content(source / filename, target / filename)
        else:
            self.content(source, target)

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

    def deployed_links(self, home):
        state = self.json_object(home / ".ai-global/.deploy-state.json", required=False)
        source_repo = None
        if state is not None:
            source = state.get("source_repo")
            if not isinstance(source, str) or not source.strip():
                self.report("WARN", "部署 state 缺少有效 source_repo；跨目錄治理連結無法驗證")
            else:
                candidate = Path(source)
                if not candidate.is_absolute() or not candidate.is_dir():
                    self.report("WARN", "部署 state 的 source_repo 必須是存在的絕對目錄；跨目錄治理連結無法驗證")
                else:
                    source_repo = candidate
        for path in (home / DEPLOYED_GOVERNANCE).glob("*.md"):
            text = self.read(path, required=False)
            if text is not None:
                self.links(path, str(path), text, deployed=True, source_repo=source_repo)

    def local(self, root, home, manifest):
        self.deployment(root / ROUTERS[0], home / ".codex/AGENTS.md")
        self.deployment(root / ROUTERS[1], home / ".claude/CLAUDE.md")
        self.deployment(root / "governance", home / DEPLOYED_GOVERNANCE, directory=True)
        active = home / ".claude/skills/ai-global/SKILL.md"
        disabled = home / ".claude/ai-global-disabled/skills/ai-global/SKILL.md"
        if active.exists() and disabled.exists():
            self.report("WARN", "ai-global skill 同時存在啟用與停用副本；請用能力清單對帳")
        target = active if active.exists() or not disabled.exists() else disabled
        self.deployment(root / SYNC_SKILL, target)
        self.deployed_links(home)
        if (home / ".codex/AGENTS.override.md").exists():
            self.report("WARN", "本地存在 Codex AGENTS.override.md，會覆蓋全域 router")
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
        self.report("WARN", "本地對帳不代表當次會話已載入、讀取或遵循；僅比對白名單設定，未驗證操作權限。完整部署對帳用 setup/install.* check")


def main(argv=None):
    parser = argparse.ArgumentParser(description="唯讀檢查治理路由、文件連結與本地部署")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="待檢查的倉庫路徑")
    parser.add_argument("--local", action="store_true", help="額外對帳本地部署副本與白名單設定")
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
