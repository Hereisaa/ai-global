---
name: ai-global
description: ai-global 全域 AI 環境的部署與同步。使用者說「ai-global」「部署」「同步」「對帳 AI 環境」時使用。不帶參數先列指令清單讓使用者選；選定或帶參數後才讀該指令的流程檔。
argument-hint: "[check | sync | deploy | govcheck | install <name>]"
---

# ai-global

| 指令 | 做什麼 | 動檔案？ |
|---|---|---|
| `check` | 唯讀對帳：部署漂移、治理檢查、第三方能力、settings 共用項 | 否 |
| `sync` | 另一台改了：pull → check → 裁決 → install → 對帳 | 是（每步確認） |
| `deploy` | 首次或重新部署這台（不 pull） | 是 |
| `govcheck` | 只跑 `check_governance.py`，改完 router／制度檔後用 | 否 |
| `install <name>` | 補裝 manifest 裡指定的一項 | 只該項 |

**`$ARGUMENTS` 為空** → 立刻用 AskUserQuestion 列出前四項（description 用上表「做什麼」），並提醒 `install` 要帶名稱。不做任何其他事、不猜意圖。
**有參數**（或使用者選定後）→ 讀 `commands/<指令>.md` 照做；不認得的參數 → 列上表請重選。

流程檔：[check](commands/check.md)、[sync](commands/sync.md)、[deploy](commands/deploy.md)、[govcheck](commands/govcheck.md)、[install](commands/install.md)；共用背景在 [common](commands/common.md)。
