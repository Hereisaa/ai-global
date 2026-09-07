---
name: sync-check
description: 對帳 ai-global 與本機 AI 全域環境，檢查部署、第三方能力與設定差異。使用者要求同步檢查、對帳 AI 環境或同步另一台已發布版本時使用；預設唯讀，明確要求同步或修復才套用範圍內變更。
---

# AI 全域環境對帳

倉庫：`~/Developer/GitHub/ai-global`（Windows 為 `%USERPROFILE%\Developer\GitHub\ai-global`）。授權依 [20](../../../governance/20-judgment.md)，安全依 [50](../../../governance/50-safety.md)，修改共用制度依 [40](../../../governance/40-maintenance.md)。

## 先辨識要求

- 「檢查／對帳／sync-check」只做唯讀：不 pull、補裝、改連結、改設定或 push。
- 明確要求同步已發布版本：先查分支、遠端與工作樹；確認目標正確且無未提交工作後才 `git pull --ff-only`。本地有變更或更新不能快轉時保留現況，回報阻礙；不自行 stash、丟棄或推送。
- 明確要求修復／補裝：只處理指定範圍，先比對再套用；具體授權仍有效就不重問。調整權限、模型或第三方安裝不能只憑「有差異」推定獲准。

## 唯讀檢查

在倉庫根目錄跑 `python3 setup/check_governance.py --local`；Codex TOML 對帳需 Python 3.11+，舊版跳過時明列缺口，不自行解析 TOML 或安裝依賴。

- macOS／Linux：另跑 `bash setup/install.sh check` 核對全部安裝連結。
- Windows：比對 repo 與部署路徑的 Junction／symlink 目標及副本內容；不以重跑安裝腳本冒充唯讀檢查。
- `manifest/skills.json`：核對 skill 目錄、command 的 target、已安裝 plugin 記錄；回報缺漏與本機獨有項，不自動加入 manifest。
- `manifest/settings.json`：核對列出的共用 key。檢查器只涵蓋白名單模型欄位；permissions、statusLine、enabledPlugins、extraKnownMarketplaces 另做結構比對。
- 設定用正規 JSON／TOML parser，僅輸出差異的欄位名稱及影響，不貼原始設定或秘密值；本機／專案覆寫與執行時有效值分開標示。

## 套用已授權修復

- 連結修復使用對應平台安裝腳本；先確認實際受影響目標在授權內，既有內容依安全規範可回復。
- 缺少 skill／command 時核實 manifest 的來源與目標；plugin 依當前平台安裝機制處理，不能執行就回報，不自行換替代品。
- 設定差異先確定以本機還是 manifest 為準，修改前備份有未提交內容的重要檔；含秘密的備份不得進 repo。保留授權外的本機 key，不為對帳全綠覆蓋整個設定。
- 修改後重跑受影響的檢查；不自動 push，發布需對指定遠端／分支的明確授權。

## 回報

先說已檢查／已修復的範圍，再給實跑證據、剩餘差異與未驗證項目。連結、內容、設定、當次載入與執行保護分開描述；未檢查的項目不能稱已同步。
