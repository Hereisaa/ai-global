# sync

先讀 [common.md](common.md)。

1. 找 `<repo>`（state 不存在 → 建議改跑 `deploy`，結束）。
2. 確認工作樹：有未 commit 變更 → 停下來列給使用者，問要 commit、放棄還是先不同步；不要自行 stash 後忘掉。
3. 乾淨才 `git -C <repo> pull --ff-only`；不能快轉時保留現況回報，不自行 rebase 或推送。
4. 接 [deploy.md](deploy.md) 的第 2～5 步。
5. 做 common 的「第三方能力對帳」「settings 共用項對帳」；缺漏逐項確認後補。
6. 依 common「回報」格式輸出。
