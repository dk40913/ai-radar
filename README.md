# ai-radar：AI 知識雷達週報

一個 Claude Code skill。每週六 09:00 由 macOS launchd 自動執行，掃描上次執行到現在的 AI 論文、論壇、新聞與開源動態，深入研究後產出一份報紙式週報，寫進你的 Obsidian vault；可選擇同時用 Mail.app 寄一封短版信（附完整 HTML 版）。

## 週報長什麼樣子

每期一個檔案：`<vault>/AI知識雷達/<日期> AI知識雷達.md`，開頭是本週導讀與目錄，接著六個版面：

1. 頭版：本週最重要的 1–3 件事
2. 論文版
3. 產業與產品版：模型發布、公司動態、政策
4. 開源與工具版：GitHub、框架、本地部署
5. GitHub AI Agent 週榜：本週新增星數最多的 5 個 agent 相關 repo
6. 社群熱議版：HN、Reddit、PTT、掘金、V2EX 等討論，以及工程師的實作心得

產業、開源、社群三個版面依來源地分成「外國／台灣／中國」三群。

如果你填了 `harness_profile.md`（你自己的 AI 工作流現況），能直接裝進你工作流的條目會多一個「可加進工作流」標記。

## 需求

- macOS（排程用 launchd，寄信用 Mail.app）
- Claude Code 已安裝並登入。每週的自動執行是 launchd 呼叫 `claude -p`，用的是你的 Claude Code 登入與方案額度
- 方案額度要夠：一次執行會派 6 個 subagent 平行研究，約 30–60 分鐘
- `python3`、`uv`、`defuddle`（安裝時 Claude Code 會幫你檢查、問過你再補）
- 選用：Parallel API key（抓網頁比較穩；沒有也能跑，改用備援抓取）
- 選用：寄信需要 Mail.app 已登入寄件帳號

## 安裝

在 Claude Code 裡說：

> 照 `<repo URL>` 的 INSTALL.md 安裝 ai-radar

它會問你三件事（Obsidian vault 路徑、要不要寄信與寄到哪、有沒有 Parallel API key），然後 clone、安裝、驗證。vault 路徑例如 `~/Documents/Obsidian`。

Obsidian 這邊不用做任何設定，週報格式由 skill 產生。週報很長，想要「回到頂端」按鈕可以另裝社群插件 Scroll to Top（選用）。

## 安裝後的檔案

| 位置 | 內容 |
|------|------|
| `~/.claude/skills/ai-radar/` | skill 本體與腳本 |
| `~/.claude/skills/ai-radar/config.json` | 設定：vault、收件者、模型、是否用 Parallel |
| `~/.claude/skills/ai-radar/harness_profile.md` | 你的工作流現況（可自行改寫） |
| `~/Library/LaunchAgents/com.<你的帳號>.ai-radar.plist` | 每週六 09:00 的排程 |
| `~/.local/state/ai-radar/` | 上次執行時間與每次執行的中間檔 |
| `~/Library/Logs/ai-radar.log` | 執行 log |
| `<vault>/AI知識雷達/` | 週報、圖片與該資料夾的撰寫規範 `CLAUDE.md` |

`config.json` 裡 `mail_to` 留空＝不寄信；`model` 留空＝用 Claude Code 預設模型。

## 日常使用

- 自動：每週六 09:00 執行。Mac 當時在睡眠的話，醒來後補跑。
- 手動跑一次：

  ```bash
  ~/.claude/skills/ai-radar/scripts/run.sh
  ```

  可加 `since=YYYY-MM-DD` 指定起始日。也可以在 Claude Code 裡直接打 `/ai-radar`。
- 看執行狀況：`tail -f ~/Library/Logs/ai-radar.log`。失敗時（有設收件者的話）會寄一封失敗通知。
- 「可加進工作流」標記：改寫 `~/.claude/skills/ai-radar/harness_profile.md`，把範本裡的 `（填：…）` 換成你自己的環境。檔案刪掉或沒填就不會出現這個標記。

## 更新

```bash
cd ~/project/ai-radar   # 你 clone 的位置
git pull
./install.sh --vault <同樣的 vault> --parallel <yes|no> [其他當初用的旗標]
```

重跑 `install.sh` 是安全的：設定檔依旗標重寫，`harness_profile.md` 與 vault 裡的 `CLAUDE.md` 不會被覆蓋。

## 移除

```bash
launchctl bootout gui/$(id -u)/com.$USER.ai-radar
rm ~/Library/LaunchAgents/com.$USER.ai-radar.plist
rm -rf ~/.claude/skills/ai-radar ~/.local/state/ai-radar
```

vault 裡的 `AI知識雷達/` 資料夾是你的週報，要留要刪自己決定。有設 Parallel MCP 而且不再需要的話：`claude mcp remove --scope user Parallel-Search-MCP`。
