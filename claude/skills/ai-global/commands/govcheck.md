# govcheck（唯讀）

在 `<repo>`（`~/.ai-global/.deploy-state.json` 的 `source_repo`）跑：

```bash
python setup/check_governance.py            # 離線
python setup/check_governance.py --local    # 加本機副本內容與白名單設定（Codex TOML 需 Python 3.11+）
```

檢查項：兩個 router `##` 節次對齊（Cowork 為 Claude 專屬例外）、各自含本工具分支前綴且沒照抄對面的（`claude/` vs `codex/`）、制度目錄路徑與逐檔路由、相對連結、manifest 結構；行數只是 WARN。

逐條解釋 FAIL 的修法，**不自行改制度檔**（改制度依 `governance/40-maintenance.md`，需使用者授權）。
