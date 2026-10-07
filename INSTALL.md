# 安裝 ai-radar（給執行安裝的 AI agent）

這份文件是寫給替使用者安裝 ai-radar 的 AI agent。照順序做每一步，達到該步的「完成條件」才進下一步。用使用者的語言（繁體中文）跟他溝通。

三條規則全程適用：

- 安裝任何依賴、執行第 7 步的完整試跑之前，都要先問使用者並取得同意。
- Parallel API key 絕對不能出現在你寫的任何檔案、log、指令輸出或對話摘要裡；它只能由使用者自己輸入。
- 某一步失敗就停下來，把錯誤訊息原文告訴使用者，不要跳過、不要自行改 repo 裡的檔案繞過去。

## 1. 確認環境

確認你是 Claude Code（有 Bash 工具、能執行 `claude` 指令），而且系統是 macOS（`uname` 輸出 `Darwin`）。

- 不是 Claude Code：停下，告訴使用者這套工具需要 Claude Code（每週自動執行是 launchd 呼叫 `claude -p`）。
- 不是 macOS：停下，告訴使用者這套工具只支援 macOS（launchd 排程、Mail.app 寄信）。

完成條件：兩項都確認。

## 2. 問使用者三件事

一次問完：

1. Obsidian vault 的路徑（例如 `~/Documents/Obsidian`）。用 `ls` 確認資料夾存在；不存在就請使用者確認路徑。
2. 要不要每週寄信？要的話寄到哪個 email。不寄就不帶 `--mail-to`。
3. 有沒有 Parallel API key？（選用。只問有沒有，不要請他把 key 貼給你。）

也順便提醒：每週的自動執行用的是他的 Claude Code 登入與方案額度，一次會派 6 個 subagent；Claude Code 要保持登入狀態，排程才跑得起來。

完成條件：拿到存在的 vault 路徑、寄信與否（含 email）、有沒有 key。

## 3. 設定 Parallel MCP（只有使用者有 key 時）

執行 `claude mcp list`。列表裡已有 `Parallel-Search-MCP` 時不用再設定：跟使用者確認他要讓 ai-radar 使用它，確認後第 5 步帶 `--parallel yes`，然後進第 4 步。

沒有的話，把下面這條指令給使用者，請他把 `<KEY>` 換成自己的 key 後，自己另開一個終端機視窗執行。不要由你代為執行，也不要請他在 Claude Code 輸入框用 `!` 執行，因為那樣 key 會進到你的對話紀錄：

```bash
claude mcp add --transport http --scope user Parallel-Search-MCP https://search.parallel.ai/mcp --header "x-api-key: <KEY>"
```

MCP 名稱必須一字不差是 `Parallel-Search-MCP`（skill 用這個名稱呼叫工具）。

完成條件：`claude mcp list` 出現 `Parallel-Search-MCP`。第 5 步帶 `--parallel yes`；沒有 key 則跳過這步、帶 `--parallel no`。

## 4. 補依賴

逐一檢查 `command -v python3 uv defuddle git`。缺的列給使用者看，取得同意後再裝：

- `uv`：`brew install uv`
- `defuddle`：`npm install -g defuddle`
- `python3`、`git`：`xcode-select --install` 或 `brew install python git`

沒有 Homebrew 或 npm 時，告訴使用者要先裝它們，等他裝好再繼續。

完成條件：四個指令都找得到。

## 5. Clone 並執行 install.sh

預設 clone 到 `~/project/ai-radar`；使用者指定別處就用他的。資料夾已存在而且是這個 repo 時，改成 `git pull`。

```bash
git clone <repo URL> ~/project/ai-radar
cd ~/project/ai-radar
./install.sh --vault "<vault 路徑>" --parallel <yes|no> \
  [--mail-to <email>] --model <你自己目前的 model ID> --subagent-model <opus|sonnet|haiku>
```

- `--model`：填你自己這個 session 的 model ID（例如你系統提示裡寫的那個）。這樣排程跑的是同一個模型。
- `--subagent-model`：填你的模型家族：`opus`、`sonnet` 或 `haiku`。
- `install.sh` 重跑是安全的；它會檢查依賴，缺東西會列出來並以非 0 結束。

完成條件：結尾印出 `ai-radar installed` 與設定摘要，`schedule` 那行是 `Saturday 09:00`。

## 6. 驗證

在第 5 步的 repo 目錄裡跑 skill 的測試：

```bash
cd "<第 5 步的 repo 目錄>/skill" && uv run --quiet --with markdown python3 -m unittest discover -s tests
```

完成條件：輸出 `OK`。

有設定寄信時，再寄一封測試信：

```bash
BODY="$(mktemp)"
printf 'ai-radar 安裝測試信\n' > "$BODY"
~/.claude/skills/ai-radar/scripts/send_mail.sh "ai-radar 測試" "$BODY"; rm -f "$BODY"
```

執行前先提醒使用者：Mail.app 必須已登入寄件帳號；macOS 會跳出「允許控制 Mail」的視窗，要按「允許」。

完成條件：指令印出 `sent: ai-radar 測試 -> <email>`，並請使用者確認收到信。

## 7. （選用）跑第一期週報

先問使用者要不要現在跑一次，並告知約需 30–60 分鐘、會消耗不少方案額度。同意才執行：

```bash
~/.claude/skills/ai-radar/scripts/run.sh
```

進度看 `~/Library/Logs/ai-radar.log`。

完成條件：`<vault>/AI知識雷達/` 出現今天日期的週報；或使用者選擇不跑，等週六自動執行。

## 8. 收尾說明

告訴使用者：

- `~/.claude/skills/ai-radar/harness_profile.md` 是他的 AI 工作流現況範本。照裡面的 `（填：…）` 改寫成自己的環境後，週報裡能裝進他工作流的條目會加上「可加進工作流」標記；不填或刪掉這個檔案，就不會有這個標記。
- 排程：每週六 09:00；log 在 `~/Library/Logs/ai-radar.log`。
- 更新與移除方式寫在 repo 的 `README.md`。

完成條件：以上三點都已告知使用者。
