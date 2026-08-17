# ai-global — AI 全域環境同步倉庫

跨機器（macOS ↔ Windows）同步 AI 工具的**使用者全域層**：system prompt（CLAUDE.md／AGENTS.md）、制度規則（agent-governance）、自製 skills／commands／agents、hooks，以及第三方能力的安裝清單。

## 設計原則

- **搬得動的檔案**：正本放本倉庫，各機器用 symlink（macOS/Linux）或 Junction（Windows）鋪回 AI 工具認得的固定位置。改一處即全機同步，物理上不可能漂移。
- **搬不動的安裝品**（官方/第三方 skills、plugins）：只記 `manifest/` 清單，各機器用 `/sync-check` 對帳補裝。上游活著的東西不揹拷貝。
- **機器特有的**（`settings.local.json`、Codex 的機器路徑設定、憑證）：留在本機，永不進倉庫。

## 目錄結構與部署對照

| 倉庫路徑 | 部署位置（連結終點 ← 連結來源） |
|---|---|
| `governance/` | ← `~/Developer/agent-governance/`（制度規則單一事實來源） |
| `claude/CLAUDE.md` | ← `~/.claude/CLAUDE.md`（Claude 全域指令） |
| `claude/statusline.sh` | ← `~/.claude/statusline.sh` |
| `claude/hooks/` | ← `~/.claude/hooks/` |
| `claude/skills/<name>/` | ← `~/.claude/skills/<name>/`（**逐一連結**，skills 目錄本體保持實體，讓第三方 skill 能並存） |
| `claude/commands/<name>` | ← `~/.claude/commands/<name>`（逐一連結） |
| `claude/agents/<name>` | ← `~/.claude/agents/<name>`（逐一連結） |
| `codex/AGENTS.md` | ← `~/.codex/AGENTS.md`（Codex 全域指令） |

`manifest/skills.json`：每台機器該有的第三方 skills／plugins／commands 清單（名稱＋來源＋版本）。
`manifest/settings.json`：`~/.claude/settings.json` 與 `~/.codex/config.toml` 裡「應該存在的共用設定項」。這兩個檔案由工具自己回寫，所以不連結、只對帳。

## 新機器上手

### macOS / Linux

```bash
git clone git@github.com:Hereisaa/ai-global.git ~/Developer/GitHub/ai-global
bash ~/Developer/GitHub/ai-global/setup/install.sh
```

### Windows（原生）

1. 一次性設定：開啟「開發人員模式」（設定 → 隱私權與安全性 → 開發人員專用），否則單檔 symlink 需系統管理員權限（腳本會自動退回複製模式並警告）。
2. ```powershell
   git clone git@github.com:Hereisaa/ai-global.git $env:USERPROFILE\Developer\GitHub\ai-global
   powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\Developer\GitHub\ai-global\setup\install.ps1
   ```
3. 注意：`claude/hooks/` 內是 bash 腳本，原生 Windows 需 Git Bash 才能執行；制度路徑統一為 `~/Developer/agent-governance`（install.ps1 會在 `%USERPROFILE%\Developer\` 建 Junction，Git Bash 下 `$HOME/Developer/...` 同樣成立）。

### 裝完之後（兩平台相同）

開一個 Claude Code session，執行 `/sync-check`：照 manifest 補裝第三方 skills/plugins、核對 settings 共用項。

## 日常工作流

- 改了 CLAUDE.md／制度檔／自製 skill → 在任一台 `git commit && git push`。
- 換到另一台開工前 → `git pull`（或直接跑 `/sync-check`，它包含 pull）。
- 裝了新的第三方 skill 且想要兩台都有 → 把它記進 `manifest/skills.json` 再 push。
- 制度檔的修改規範（備份、變更紀錄、權限分級）照 `governance/40-maintenance.md`，不因搬進 git 而改變；git 歷史是第二層回滾機制。

## 紅線

- 憑證類（`.credentials.json`、`auth.json`、`.env`、API key）**永不進本倉庫**。commit 前發現疑似金鑰，停下來處理。
- 本倉庫必須保持 **private**。
