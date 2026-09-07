# check（唯讀）

先讀 [common.md](common.md)。全程不 pull、不 install、不改設定。

1. 找 `<repo>`（state 不存在 → 建議改跑 `deploy`，結束）。
2. `git -C <repo> fetch`，報 branch、ahead/behind、未 commit 數。
3. 跑部署腳本 `check`，列非 `OK` 的狀態碼。
4. 跑 `python <repo>/setup/check_governance.py --local`，列 FAIL 與非固定免責的 WARN（固定免責：settings.local.json 存在、「不代表已載入」）。
5. 做 common 的「第三方能力對帳」「settings 共用項對帳」，只回報差異。
6. 依 common「回報」格式輸出。差異需要動作時，建議對應指令（`sync`／`deploy`／`install <name>`），不自行執行。
