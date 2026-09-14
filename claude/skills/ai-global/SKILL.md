---
name: ai-global
description: 僅在使用者明確要求部署、同步、對帳 ai-global 管理的 AI 開發環境，或查看及切換該環境的 skills/plugins/commands 時使用。一般網站部署、資料同步、純介紹或規則審查不觸發。
argument-hint: "[check | align [--only <id>] | deploy | govcheck | capabilities [list | manage | enable | disable] | evolve [source-id]]"
---

# ai-global

每個指令對應 `<repo>/setup/` 的同名腳本或 flag，名字一樣、行為一樣：

| 指令 | 腳本 | 做什麼 | 動檔案？ |
|---|---|---|---|
| `check` | `align.py --plan` | 唯讀：部署漂移、要補裝的項目、衝突清單 | 否 |
| `align [--only <id>]` | `align.py` | pull → 部署 → 補裝缺項 → 衝突逐項裁決（在對話中問）→ 對帳；`--only` 只補裝指定項 | 是，自動項直接做；衝突只依使用者選擇 |
| `deploy` | `deploy.py` | 只重新部署 repo 自己的檔，不 pull、不碰第三方 | 是 |
| `govcheck` | `govcheck.py` | 治理結構與本機檢查 | 否 |
| `capabilities` | `capabilities.py` | 列能力與開關；可指定開關 | list 否，開關只改指定項 |
| `evolve [source-id]` | — | 核對 `manifest/sources.json` 的官方文件與 marketplace 是否有變，產出 harness 審查報告 | 只寫報告與核對日期 |

先依參數或明確自然語言分派，只讀對應流程；已有上下文不再列選單。單獨輸入 `/ai-global` 且無法判斷意圖，或參數無法識別時，列上表請使用者指定。「同步」「更新」「另一台改了」都是 align。

流程：[check](commands/check.md)、[align](commands/align.md)、[deploy](commands/deploy.md)、[govcheck](commands/govcheck.md)、[capabilities](commands/capabilities.md)、[evolve](commands/evolve.md)。[common](commands/common.md) 同一對話未變更只讀一次，引用不要求載入其他流程。
