# 安裝 ai-radar（給執行安裝的 AI agent）

這份文件是寫給替使用者安裝 ai-radar 的 AI agent。照順序做每一步，達到該步的「完成條件」才進下一步。用使用者的語言（繁體中文）跟他溝通。

三條規則全程適用：

- 安裝任何依賴、執行第 6 步的完整試跑之前，都要先問使用者並取得同意。
- 某一步失敗就停下來，把錯誤訊息原文告訴使用者，不要跳過、不要自行改 repo 裡的檔案繞過去。

## 1. 確認環境

確認你是 Claude Code（有 Bash 工具、能執行 `claude` 指令），而且系統是 macOS（`uname` 輸出 `Darwin`）。

- 不是 Claude Code：停下，告訴使用者這套工具需要 Claude Code（每週自動執行是 launchd 呼叫 `claude -p`）。
- 不是 macOS：停下，告訴使用者這套工具只支援 macOS（launchd 排程、Mail.app 寄信）。

完成條件：兩項都確認。

## 2. 問使用者幾件事

一次問完：

1. Obsidian vault 的路徑（例如 `~/Documents/Obsidian`）。用 `ls` 確認資料夾存在；不存在就請使用者確認路徑。
2. 要不要每週寄信？要的話寄到哪個 email。不寄就不帶 `--mail-to`。
3. 要不要順便裝 Obsidian skills 套件（`obsidian@obsidian-skills`，讓 Claude Code 會寫 Obsidian 筆記格式、讀網頁、操作 vault；建議裝，ai-radar 本身不依賴它）。
4. 只有你自己的 model ID 含 `fable` 時才問：告訴他 Fable 的額度消耗遠高於 Opus，而每週排程會沿用安裝時的模型、一次派 6 個 subagent；問他要沿用 Fable，還是改用 `claude-opus-5-5`（建議）。
5. 週報要以誰的角度、關注哪些主題？（直接 Enter＝預設：AI Agent 工程師，關注 AI Agent、LLM 推論與部署、RAG、本地模型、agent 框架與工具）
6. 要不要一併裝 Obsidian 的週報外觀與導覽按鈕？（選用：右下角回頂端／目錄／到底端按鈕，以及報紙風配色。配色會套用到整個 vault。）

也順便提醒：每週的自動執行用的是他的 Claude Code 登入與方案額度，一次會派 6 個 subagent；Claude Code 要保持登入狀態，排程才跑得起來。

完成條件：拿到存在的 vault 路徑、寄信與否（含 email）、要不要裝 Obsidian skills、讀者與關注主題（或用預設）、要不要裝 Obsidian 外觀與導覽按鈕；你是 Fable 時另有他選的模型。

## 3. 補依賴

逐一檢查 `command -v python3 uv defuddle git`。缺的列給使用者看，取得同意後再裝：

- `uv`：`brew install uv`
- `defuddle`：`npm install -g defuddle`
- `python3`、`git`：`xcode-select --install` 或 `brew install python git`

沒有 Homebrew 或 npm 時，告訴使用者要先裝它們，等他裝好再繼續。

使用者在第 2 步要裝 Obsidian skills 時，`claude plugin list` 沒有 `obsidian@obsidian-skills` 就執行：

```bash
claude plugin marketplace add kepano/obsidian-skills
claude plugin install obsidian@obsidian-skills
```

裝完提醒使用者：新的 Claude Code session 才會載入這些 skills。

完成條件：四個指令都找得到；要裝 Obsidian skills 時 `claude plugin list` 出現 `obsidian@obsidian-skills`。

## 4. Clone 並執行 install.sh

預設 clone 到 `~/project/ai-radar`；使用者指定別處就用他的。資料夾已存在而且是這個 repo 時，改成 `git pull`。

```bash
git clone https://github.com/dk40913/ai-radar.git ~/project/ai-radar
cd ~/project/ai-radar
./install.sh --vault "<vault 路徑>" \
  [--mail-to <email>] --model <你自己目前的 model ID> --subagent-model <opus|sonnet|haiku> \
  [--reader "<讀者>"] [--focus "<關注主題>"] [--arxiv-keywords "<k1,k2,...>"] \
  [--obsidian-addons]
```

- `--model`：填你自己這個 session 的 model ID，一字不差照你系統提示裡寫的抄，連後綴一起保留（例如 `claude-opus-5-5[1m]` 的 `[1m]` 不能拿掉）。這樣排程跑的是同一個模型。使用者在第 2 步選了改用 Opus 時，填 `claude-opus-5-5`，`--subagent-model` 填 `opus`。
- `--subagent-model`：你的模型家族是 `opus`、`sonnet` 或 `haiku` 就填那個；其他家族一律填 `opus`。
- `--reader`／`--focus`／`--arxiv-keywords`：第 2 步使用者用預設時三個都不帶。他自訂了讀者就用 `--reader` 填讀者；自訂了關注主題就用 `--focus` 填主題，並依主題產生 15–30 個英文小寫 arXiv 關鍵字（會拿來對論文標題與摘要做子字串比對，所以要用常見詞形，例如 `diffusion`、`medical imag`），先給使用者看、他同意後用逗號串起來傳給 `--arxiv-keywords`。只改讀者、主題沿用預設時，不帶 `--focus` 與 `--arxiv-keywords`。
- `--obsidian-addons`：使用者在第 2 步要裝 Obsidian 外觀與導覽按鈕時才帶。它只把檔案複製進 vault 的 `.obsidian/`，不會啟用；啟用步驟在第 7 步告訴使用者。
- `install.sh` 重跑是安全的；它會檢查依賴，缺東西會列出來並以非 0 結束。

完成條件：結尾印出 `ai-radar installed` 與設定摘要，`schedule` 那行是 `Saturday 09:00`。

## 5. 驗證

在第 4 步的 repo 目錄裡跑 skill 的測試：

```bash
cd "<第 4 步的 repo 目錄>/skill" && uv run --quiet --with markdown python3 -m unittest discover -s tests
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

## 6. （選用）跑第一期週報

先問使用者要不要現在跑一次，並告知約需 30–60 分鐘、會消耗不少方案額度。同意才執行。

這一步一定要在背景執行：前景的 Bash 工具 10 分鐘就逾時，會把執行中斷。用 Bash 工具的 `run_in_background`，或用 `nohup`：

```bash
nohup ~/.claude/skills/ai-radar/scripts/run.sh >/dev/null 2>&1 &
```

之後用 `tail ~/Library/Logs/ai-radar.log` 看進度，結尾出現 `=== ai-radar end (code 0) ===` 代表成功。

完成條件：`<vault>/AI知識雷達/` 出現今天日期的週報；或使用者選擇不跑，等週六自動執行。

## 7. 收尾說明

告訴使用者：

- `~/.claude/skills/ai-radar/harness_profile.md` 是他的 AI 工作流現況範本。照裡面的 `（填：…）` 改寫成自己的環境後，週報裡能裝進他工作流的條目會加上「可加進工作流」標記；不填或刪掉這個檔案，就不會有這個標記。
- 排程：每週六 09:00；log 在 `~/Library/Logs/ai-radar.log`。
- 更新與移除方式寫在 repo 的 `README.md`。
- 第 4 步帶了 `--obsidian-addons` 時，另外請使用者在 Obsidian 裡依序完成（Obsidian 執行中改設定檔會被覆寫，所以這幾步要他自己點）：
  1. 設定 → 社群插件：關閉「限制模式」，在已安裝插件裡啟用「Note Nav Buttons」。
  2. 設定 → 外觀 → CSS 片段：按重新整理，啟用 `newspaper`。
  3. （要完全一樣的外觀才需要）設定 → 外觀 → 主題：瀏覽並安裝、套用「Things」；設定 → 社群插件 → 瀏覽：安裝並啟用「Style Settings」，到 Style Settings 的設定頁按 Import，貼上 repo 裡 `obsidian/style-settings.json` 的內容。

完成條件：以上各點都已告知使用者（Obsidian 那一點只在帶了 `--obsidian-addons` 時需要）。
