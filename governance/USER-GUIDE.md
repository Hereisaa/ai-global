# Harness Engineering 使用手冊（給 Aaron 本人）

> 本目錄其他檔案的讀者是模型；**這一份的讀者是你**。
> 它回答三個問題：這套系統是什麼、你每天怎麼用它、怎麼知道它還健康。

## 一、這套系統是什麼（一分鐘版）

```
你說的話（prompt）
   ↓
兩個 router（每個 session 自動載入，只放紅線與路由）
   ├─ ~/.claude/CLAUDE.md          （Claude Code / Cowork）
   └─ ~/.codex/AGENTS.md           （Codex）
   ↓ 按情境指向
制度目錄 ~/.ai-global/governance/        ← 實質規則的單一事實來源
   ├─ 10 委派與驗證   20 判斷 rubric   30 派工模板
   ├─ 40 維護協議     50 安全細則     60 新專案起手式
   └─ 70 行為契約     80 工程原則與輸出格式
   ↓ 疊加
專案層（每個專案自己的 CLAUDE.md + AGENTS.md router）
   ↓ 最底層兜底
環境強制層（CI、hooks、typecheck——模型忘了也會被擋下）
```

核心思想：**模型是無狀態的臨時工，這整套是工廠**。模型會換（Sonnet、Opus、GPT……），工廠不換。

## 二、日常口令表（你唯一需要「做」的事）

制度大多會自動運作，但這些一句話口令能讓它發揮全力：

| 時機 | 對模型說 |
|---|---|
| 開新專案 | 「照 60 號檔幫這個專案做 T1（或 T2）bootstrap」 |
| 一段工作結束 | 「照 60 號檔的收尾儀式收尾」 |
| 要驗收成果 | 「派 fresh agent 驗收，逐條 PASS/FAIL 附證據」 |
| 懷疑它在唬你 | 「**這個結論的驗證證據是什麼？**」（戳破九成自驗偏誤） |
| 踩了坑 | 「把這個教訓照 40 號檔格式寫回去」 |
| 每月一次 | 「照 40 號檔盤點制度：哪些規則被違反過、哪些教訓該畢業、哪些檔超長」 |
| 要改制度 | 「我想把 X 規則改成 Y，照 40 號檔流程處理」 |

## 三、你自己要守的三件事（人也是 harness 的一部分）

1. **需求給三件套**：做什麼＋為什麼＋怎樣算做完。這跟模型派工給 subagent 的格式同構——你給得越完整，整條鏈的品質越高。說不出「怎樣算做完」時，先讓模型幫你 brainstorm 再開工。
2. **一個 session 一個任務**。多個不相關任務塞同一個對話，context 互相污染，是失焦的最大人為來源。新任務開新 session，很便宜。
3. **大改動先要 Plan**（plan mode 或直接說「先給我計畫」）。批准計畫比修正成品便宜十倍。

## 四、環境強制層狀態表（2026-08-16 實測更新）

| 項目 | 狀態 | 備註 |
|---|---|---|
| digrit CI（test＋typecheck） | ✅ 已 commit 生效 | `.github/workflows/ci.yml`（另有 `lockfile-sync.yml`） |
| Stop hook：typecheck 守門 | ⏸ 腳本就緒，**仍未掛載** | 腳本在 `~/.claude/hooks/stop-typecheck.sh`。掛載方式見下方 |
| 全域 model 設定 | ✅ 釘在 `claude-fable-5[1m]`，目前可用 | 若日後該模型下架，用 `/model` 改 |
| 權限白名單 | 未做（可選） | defaultMode 已是 auto，提示本來就少；有需要再跑 `/fewer-permission-prompts` |

### Stop hook 掛載方式（擇一）
- **方式 A**：在互動 session 對 Claude 說「把 `~/.claude/hooks/stop-typecheck.sh` 掛成 Stop hook」，跳出權限提示時核准。
- **方式 B**：自己把下面片段合併進 `~/.claude/settings.json`（改前先備份），存檔後開 `/hooks` 確認生效：

```json
"hooks": {
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "bash ~/.claude/hooks/stop-typecheck.sh",
          "timeout": 120,
          "statusMessage": "Typecheck gate (Stop hook)"
        }
      ]
    }
  ]
}
```

效果：模型想結束回合時，若工作區有改過的 `.ts/.tsx` 且專案有 typecheck script，就自動跑 `npm run typecheck`；失敗會**擋下收工**並把錯誤塞回給模型修——這就是「環境會自己說不」。

## 五、健康檢查：制度退化的訊號（人眼版）

看到以下任一現象，說一句「照 40 號檔盤點制度」即可，通常一次就能矯正：

- 模型宣稱完成但拿不出指令輸出或檔案證據（自驗偏誤回潮）。
- 主對話又開始整檔整檔地貼程式碼（委派紀律鬆動）。
- 全域 CLAUDE.md 超過 60 行、或制度檔越改越長（規則肥大）。
- Claude 側和 Codex 側行為明顯不一致（兩側漂移）。
- 模型引用不存在的檔案路徑而沒告訴你（router 斷鏈被吞掉）。

## 六、FAQ

**Q：換了新模型（比如以後接 GPT 或新版 Claude）要做什麼？**
第一個 session 說「先讀 `~/.ai-global/governance/README.md`」。router 會自動載入，這句只是保險。

**Q：我想改某條規則？**
直接對模型說，它會走 40 號檔流程（備份→改→留變更紀錄→兩側同步）。安全紅線類它會反過來要你確認，這是設計好的。

**Q：新專案不是 Node/TypeScript 怎麼辦？**
60 號檔的模板換掉指令即可（Python 換 pytest/mypy、Flutter 換 flutter test/analyze）。三級制與收尾儀式跟語言無關。

**Q：這套會不會太重？**
T1 專案只花 5 分鐘。覺得哪裡重，說出來讓模型提案精簡——制度的長度預算是硬上限，「刪」永遠是合法選項（只是要經過你）。

## 變更紀錄
- 2026-07-05 建檔（Fable 5）
- 2026-08-16 狀態表依實測更新；架構圖補 70/80、移除已歸檔的 90（Fable 5）
