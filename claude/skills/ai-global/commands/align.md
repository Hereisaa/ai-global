# align（一鍵對齊本機與 manifest）

按需讀 [common.md](common.md) 的「原則」。align = pull → 部署 → 補裝 manifest 缺項 → 列出並解決衝突 → 對帳。自動項直接做；有兩種合理答案的才是「衝突」，只由使用者決定。所有取代與移除都進 `~/.ai-trash/`。

同一支腳本兩個入口：使用者在真正的終端跑 `python <repo>/setup/align.py` 會開互動選單；在 Claude Code 裡沒有 TTY，由本流程改在對話中呈現衝突並收集決定。

1. 先跑 `python <repo>/setup/align.py --plan`（唯讀）：看 pull 是否可行、部署差異、要補裝的項目、衝突清單。FAIL 或 `check_governance.py` 有 FAIL 就停下交付原因。
2. 使用者已授權對齊即執行 `python <repo>/setup/align.py --yes`：pull（工作樹髒則略過並回報）、部署、補裝缺項。回傳碼 2 代表有衝突待決；1 代表有失敗項，先報。
3. 衝突逐項列給使用者：類型、標題、說明、可選處置與預設值（腳本輸出的 `KEY=…` 行）。類型與預設：
   - `edited` 部署檔在 repo 外被改過 → 以 repo 覆蓋／回寫 repo／保留兩邊（預設覆蓋；先看差異再問）
   - `switch` 本機開關與 manifest 建議相反 → 開啟／關閉／維持（預設維持本機選擇）
   - `extra` 本機多出、manifest 沒有 → 保留／停用／移到 trash（預設保留，不追問）
   - `duplicate` 獨立 skill 與 plugin 內同名 → 獨立版移到 trash／停用／保留（預設移到 trash）
   - `version` 安裝版本與 manifest 不同 → 更新／維持（預設更新）
   - `hook` settings.json 的 hook 指向不存在的腳本 → 保留／從設定移除（預設保留）
   使用者沒回應的項目一律當「預設值」，但 `extra`、`switch`、`hook` 的預設都是不動，所以不會有隱性變更。
4. 收齊決定後執行 `python <repo>/setup/align.py --no-pull --yes --resolve KEY=ACTION ...`（可多個 `--resolve`）。
5. 跑 `python <repo>/setup/capabilities.py list` 對帳，並跑 `python <repo>/setup/deploy.py check`。回報：pull 結果、部署變更、補裝與失敗項、每項衝突的處置、trash 位置與分支。需要新工作階段才載入的能力明說。

`requires`（例如 `typescript-language-server`）不在 PATH 時腳本只 WARN 並附 `requires_hint`；安裝前置需求屬第三方安裝，依 common 的原則彙整一次裁決，不自動跑。
