# sync

按需讀 [common.md](common.md)。

1. 確認 `<repo>` 與工作樹；未提交變更時保留現況，暫停 pull，繼續安全的唯讀對帳。回報需由原工作階段處理，不自行 stash、commit 或放棄變更。
2. 工作樹可安全更新才 `git -C <repo> pull --ff-only`；無法快轉時回報，不自行 rebase 或 push。
3. 接 [deploy.md](deploy.md) 的檢查、必要裁決與部署流程，不逐步重問相同授權。
4. 未列管、未安裝或本機停用能力只回報；要一併補裝與解衝突改走 [align.md](align.md)。
5. 回報變更、證據、限制與分支。
