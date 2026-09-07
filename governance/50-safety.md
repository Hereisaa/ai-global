# 50 — 安全細則（Safe Delete 完整版與其他紅線）

> 摘要版在全域 CLAUDE.md / AGENTS.md 的「安全紅線」。本檔是完整流程與例外清單，
> 動手刪除前不確定就讀這裡。

## Safe Delete Policy（禁止直接銷毀檔案）

**禁止**：`rm`、`rm -rf`、`rmdir`，以及任何程式化刪除（Python `os.remove()`、Node `fs.unlinkSync()` 等）——它們全部繞過垃圾桶，直接從 inode 移除，未 commit 的檔案將永久消失。

**正確做法**：`mv` 到 `~/.ai-trash/` 暫存，由使用者事後確認再真正清除。

### 操作流程
```bash
# 1. 確保 trash 存在
mkdir -p ~/.ai-trash

# 2. 單檔：加時間戳避免衝突
mv src/old_button.tsx ~/.ai-trash/old_button.tsx.$(date +%Y%m%d-%H%M%S)

# 3. 批次：先開當次子資料夾再整批移入
BATCH="$HOME/.ai-trash/cleanup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BATCH"
mv file1.txt old_dir/ "$BATCH/"
```

Windows PowerShell 等效寫法（**不要用 `Remove-Item`**）：
```powershell
$Batch = Join-Path $env:USERPROFILE (".ai-trash\cleanup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $Batch | Out-Null
Move-Item -LiteralPath .\file1.txt, .\old_dir -Destination $Batch
```

### 刪除後必須回報
- 移到 trash 的檔案清單與新路徑。
- 請使用者確認後自行清空 trash——**代理不主動清 trash**。

### 例外（可不進 trash）
- 工具原生清理指令產生的暫存：`flutter clean`、`node_modules`（刪後重 `npm install`）、`build/`、`.dart_tool/`、`Pods/`、`DerivedData/` 等。
- Git stage 取消：用 `git restore --staged <file>`，不是刪檔。
- 系統暫存：macOS 的 `.DS_Store`、Windows 的 `Thumbs.db` 可直接清。

### 理由（給想便宜行事的自己）
Git 只能救回已 commit 的追蹤檔。未 commit 新檔、`.gitignore` 內的檔案（`.env`、`*.db`）被 `rm` 就是永久消失；Time Machine 也救不了當下未備份的版本。

## 其他紅線細則

### 不可逆／對外動作——先確認清單
以下動作執行前必須取得使用者當次明確同意（先前類似情境的同意不延用）：
- `git push --force`（含 `--force-with-lease` 推到共用分支）、刪除遠端分支、改寫已推送的歷史。
- 對外發布：部署到 production、發 npm/pypi 套件、公開 GitHub repo。
- 對外通訊：寄 email、發訊息、在 issue/PR 留言（若使用者未明確要求）。
- 覆寫或刪除**不是本次 session 建立**的檔案：先看內容，若與描述不符，回報而非執行。

### 憑證與秘密
- `.env` / `.env.local` / 一切 `.env.*`、`auth.json`、API key：不讀進回覆內文、不 commit、不傳外部服務、不寫進 log。
- 需要引用環境變數時只寫變數名，不寫值。

### 修改既有重要檔案前先備份
指令檔（CLAUDE.md/AGENTS.md）、設定檔、制度檔：一律改 ai-global clone 內的正本（clone 路徑見 `~/.ai-global/.deploy-state.json`），先 `cp` 一份到該 clone 的 `governance/backups/`（檔名加來源與時間戳）再改。

## 變更紀錄
- 2026-07-03 建檔（Fable 5）
- 2026-09-07 trash 路徑改為 `~/.ai-trash/`；補上 PowerShell 版流程與 Windows 系統暫存例外（Opus 5，應使用者要求）
