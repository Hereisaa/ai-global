# 環境與維護備忘

本頁保存入口移出的環境背景；操作前仍須以實際偵測為準，不因表格存在就視為已啟用。

| 項目 | macOS 主力 | Windows 副機 |
|---|---|---|
| 機器 | Apple Silicon M4 Mac mini | Windows 11 |
| Shell | zsh | PowerShell／Git Bash |
| GitHub 專案 | `~/Developer/GitHub/` | `D:\GitHub\`（Git Bash：`/d/GitHub/`） |
| 家目錄 | `/Users/<user>` | `C:\Users\<user>` |

記憶體問題先看 `~/.claude/logs/cleanup.log`。macOS 原有 SessionEnd hook 與每兩小時 launchd 排程；Windows 自 2026-09-08 起手動執行桌面「Claude 清理背景程序.cmd」或 `~/.claude/hooks/cleanup-orphans.ps1 -Scope global`。這是既有配置備忘，不是本次掛載或執行證據；詳見 [README](../../README.md) 的 hooks 與記憶體回收。

部署、同步、能力管理的命令與參數集中在 [README](../../README.md)。Claude Code 的 `/ai-global` 由本 repo 的 skill 提供；Codex 可直接使用同一套 Python 腳本。能否委派、使用 hook 或讀取特定設定，依本次工具與實際掛載查證，不以工具名稱推定。

## 變更紀錄
- 2026-10-02 移入兩工具入口中的機器與維護背景，改為任務需要時查閱。
