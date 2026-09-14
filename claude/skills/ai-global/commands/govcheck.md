# govcheck（唯讀）

在已確認的 `<repo>` 執行以下之一：

```bash
python setup/govcheck.py --local
```

`--local` 包含 repo 靜態檢查；只需離線檢查時省略此參數，不連跑兩者。Codex TOML 本機對帳需 Python 3.11+。

檢查 router 節次與工具前綴、制度路由、連結及 manifest 結構；行數只是 WARN。列 FAIL 的具體修法；govcheck 本身不授權改制度，若當前任務已授權修正則依該範圍處理，不重問。
