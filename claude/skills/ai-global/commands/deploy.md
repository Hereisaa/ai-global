# deploy

按需讀 [common.md](common.md)。不 pull。

1. 從 state 或目前工作樹確認 `<repo>`；找不到才詢問 clone 位置。
2. 跑 `python <repo>/setup/check_governance.py`。FAIL 時停止部署、交付具體原因；只有原授權涵蓋修正才修改 clone。
3. 跑部署腳本 check；對 EDITED 看差異，只有尚未涵蓋的取代決定才裁決。
4. 執行 install，再跑 check 驗證結果。回報 WARN／DROP／NOTE 與備份位置。
5. 執行能力清單，讓使用者看到專案預設與本機既有的安裝及啟用狀態；保留本機開關，不自動安裝缺項。首次部署另按需對帳共用設定。
6. 依 common 回報。已完成的相同版本檢查不重跑；有變更才驗受影響項。
