---
name: ai-global
description: 僅在使用者明確要求部署、同步、對帳 ai-global 管理的 AI 開發環境，或查看及切換該環境的 skills/plugins/commands 時使用。一般網站部署、資料同步、純介紹或規則審查不觸發。
argument-hint: "[check | sync | deploy | govcheck | capabilities [list | manage | enable | disable] | install <name> | align | evolve [source-id]]"
---

# ai-global

| 指令 | 做什麼 | 動檔案？ |
|---|---|---|
| `check` | 對帳部署漂移、治理、能力與共用設定 | 否 |
| `sync` | pull → check → 必要裁決 → 部署 → 對帳 | 是，既有授權內連續執行 |
| `deploy` | 首次或重新部署本機，不 pull | 是 |
| `govcheck` | 治理結構與本機檢查 | 否 |
| `capabilities` | 列出專案預設、本機既有能力與啟用狀態；可指定開關或開啟互動模式 | list 否，開關只改指定項 |
| `install <name>` | 明確補裝清單中的指定能力 | 只該項 |
| `align` | pull → 部署 → 補裝 manifest 缺項 → 衝突逐項裁決（終端用 TUI，Claude Code 在對話中問）→ 對帳 | 是，自動項直接做；衝突只依使用者選擇 |
| `evolve [source-id]` | 核對 `manifest/sources.json` 的官方文件與 marketplace 是否有變，產出 harness 審查報告 | 只寫報告與核對日期 |

先依參數或明確自然語言分派，只讀對應流程；已有上下文不再列選單。單獨輸入 `/ai-global` 且無法判斷意圖，或參數無法識別時，列上表請使用者指定。

流程：[check](commands/check.md)、[sync](commands/sync.md)、[deploy](commands/deploy.md)、[govcheck](commands/govcheck.md)、[capabilities](commands/capabilities.md)、[install](commands/install.md)、[align](commands/align.md)、[evolve](commands/evolve.md)。[common](commands/common.md) 同一對話未變更只讀一次，引用不要求載入其他流程。
