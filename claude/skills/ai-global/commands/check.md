# check（唯讀）

按需讀 [common.md](common.md)。不 pull、不 install、不改設定。check 就是 `align --plan`。

1. 找 `<repo>`，列目前 branch 與未提交變更；明示遠端資訊可能未更新。
2. 跑 `python <repo>/setup/align.py --plan`：回報 PLAN（部署差異）、要補裝的項目、衝突清單三張表。
3. 使用者另要治理或共用設定對帳才跑 `govcheck.py --local` 與 common 的 settings 對帳；不主動連跑。
4. 回報差異與對應操作建議（多半是「跑 align」），不自行套用。
