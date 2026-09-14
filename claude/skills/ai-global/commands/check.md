# check（唯讀）

按需讀 [common.md](common.md)。不 pull、fetch、install 或修改設定。

1. 找 `<repo>`，列目前 branch、依現有本機 refs 判斷的 ahead/behind 及未提交變更；明示遠端資訊可能未更新。
2. 跑部署腳本 check，回報非 OK 狀態。
3. 跑 `python <repo>/setup/check_governance.py --local` 一次，列 FAIL 與有行動意義的 WARN。
4. 執行 common 的能力對帳與 settings 共用項對帳；僅補足 checker 尚未涵蓋的欄位，列出來源、狀態與設定差異，不寫檔。
5. 回報差異與對應操作建議，不自行套用。
