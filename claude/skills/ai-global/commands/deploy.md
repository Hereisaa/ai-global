# deploy

先讀 [common.md](common.md)。不 pull。

1. 找 `<repo>`。state 不存在 → 首次部署：clone 路徑問使用者，或依慣例找（macOS `~/Developer/GitHub/ai-global`、Windows `D:\GitHub\ai-global`）；都沒有就請使用者先 `git clone git@github.com:Hereisaa/ai-global.git`。
2. 跑部署腳本 `check`，依 common 的狀態碼表處置；`EDITED` 一律先問。
3. 裁決完跑 install（不帶 check 參數）。
4. 再跑一次 `check` 確認全部 `OK`；原樣轉述 install 的 `WARN`／`DROP`／`NOTE`。
5. 跑 `python <repo>/setup/check_governance.py`。FAIL 代表 repo 本身有問題，要先修 clone，不是部署端的漂移。
6. 首次部署時接著做 common 的兩項對帳；依「回報」格式輸出。
