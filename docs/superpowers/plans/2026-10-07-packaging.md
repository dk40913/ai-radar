# ai-radar 打包成可安裝 repo — Plan

**Goal:** 把 Herb 個人的 ai-radar skill 變成同事（macOS、用 Claude Code）可以「把 repo 網址丟給自己的 Claude Code 就裝好」的 repo。安裝時可選：有／沒有 Parallel API key、寄／不寄信、vault 路徑、模型（預設＝安裝它的那個 AI 的模型）。

**Spec（Herb 2026-10-07 拍板）：**
1. 同事用 Mac → 排程 launchd、寄信 Mail.app 照舊。
2. 寄信由安裝者選擇；不寄信時只寫進 Obsidian，流程仍要算成功。
3. 模型：誰安裝就用誰的模型（安裝的 AI 把自己的 model ID 傳給 install.sh；留空＝claude 預設模型）。
4. 分享：Herb 個人 GitHub repo，把網址給同事的 AI 安裝。
5. 有 Parallel key 走 defuddle → Parallel web_fetch → Jina；沒有走 defuddle → Jina（已實作，由 `config.json` 的 `parallel` 決定）。

## Global Constraints

- Repo 版面：`skill/`（安裝到 `~/.claude/skills/ai-radar/` 的全部內容）、`vault-template/AI知識雷達/CLAUDE.md`、`launchd/ai-radar.plist.template`、`install.sh`、`INSTALL.md`、`README.md`、`tests/`（repo 層測試）。
- 安裝後的設定檔 `~/.claude/skills/ai-radar/config.json`，格式固定：
  ```json
  {"parallel": false, "vault": "/Users/<user>/Documents/Obsidian", "mail_to": "", "model": "", "subagent_model": "opus", "path_prepend": ["/opt/homebrew/bin"]}
  ```
  `vault` 一律存展開後的絕對路徑；`mail_to` 空字串＝不寄信；`model` 空字串＝不傳 `--model`；`subagent_model` 只能是 `opus`／`sonnet`／`haiku`；`path_prepend` 是 install.sh 找到 `claude`、`defuddle`、`uv`、`python3` 的目錄（去重，可為空 list），run.sh 會把它們放在 PATH 最前面。
- 讀 config 一律用 `python3` 一行（不引入 jq 等新依賴）。
- 出貨檔案（`skill/`、`vault-template/`、`launchd/`、`install.sh`、`INSTALL.md`、`README.md`）不得含作者的家目錄路徑（`/Users/<user>`）、作者的帳號／信箱前綴、`Documents/Obsidian`（README/INSTALL 中當「預設值範例」除外）、`Herb`。
- Claude Code 權限規則路徑：家目錄底下寫 `~/相對路徑`；家目錄外的絕對路徑寫 `//絕對路徑`（單斜線開頭會被當成相對於 settings 檔）。
- 測試用 `python3 -m unittest`，`build_html` 相關測試需 `uv run --quiet --with markdown`。全部測試從 repo 根目錄跑：`uv run --quiet --with markdown python3 -m unittest discover -s skill/tests && python3 -m unittest discover -s tests`。
- shell 腳本維持 bash、`set -uo pipefail` 或 `set -euo pipefail`（照原檔）。
- 不改週報內容邏輯（抓取來源、版面、分群）。

## Task 1: send_mail.sh 與 run.sh 讀 config

Files: `skill/scripts/send_mail.sh`、`skill/scripts/run.sh`、`skill/scripts/fetch_sources.py`、`skill/scripts/fetch_images.py`、新增 `tests/test_scripts.py`。

1. `send_mail.sh`：收件者 `TO="${3:-<config mail_to>}"`；config 路徑 `$(dirname "$0")/../config.json`。若 `TO` 為空：印 `mail disabled (config mail_to empty): <主旨>` 並 exit 0，不呼叫 osascript。其他行為不變。
2. `run.sh`：
   - 刪掉 `HOME` 的 `/Users/<user>` 預設（改 `export HOME="${HOME:?}"`）。
   - `eval "$(/opt/homebrew/bin/brew shellenv)"` 改成檔案存在才執行。
   - 從 `$SKILL_DIR/config.json` 讀 `vault` 與 `model`；config 不存在或 vault 空 → 呼叫 `fail "config.json 缺少 vault，請重跑 install.sh" "前置檢查"` 並 exit 1。
   - `claude` 的 `--add-dir "$HOME/Documents/Obsidian"` 改成 `--add-dir "$VAULT"`；`--model claude-opus-5-5` 改成 model 非空才加 `--model "$MODEL"`。其餘旗標（`--max-turns 200` 等）、重試邏輯不變。
3. `fetch_sources.py`、`fetch_images.py` 的 UA 改成 `"ai-radar/0.1 (personal research bot)"`（拿掉 email）。
4. 測試 `tests/test_scripts.py`（repo 根目錄 `tests/`），全部在暫存目錄、用假的 `HOME` 與 PATH stub：
   - 把 `skill/` 複製到 `<tmp>/home/.claude/skills/ai-radar/`，寫入 config.json。
   - stub `osascript`：把收到的參數寫到檔案。stub `claude`：把參數一行一個寫到檔案，並寫一個新的 `~/.local/state/ai-radar/last_run.json`（內容含時間戳，確保狀態前進）。stub `uv`：`--version` 印版本。
   - send_mail：`mail_to` 空 → exit 0、輸出含 `mail disabled`、osascript 沒被呼叫；`mail_to` 有值且未給第 3 參數 → osascript 收到該收件者；給了第 3 參數 → 以參數為準。
   - run.sh：`model` 空 → claude 參數不含 `--model`；`model` = `claude-sonnet-5-5` → 含 `--model claude-sonnet-5-5`；`--add-dir` 含 config 的 vault；exit code 0。config 缺 vault → exit 1 且 `runs/<今天>/failure.txt` 存在。
   - run.sh 執行時 PATH 只放 stub 目錄＋`/usr/bin:/bin`，避免碰到真的 claude；注意 run.sh 自己會覆寫 PATH，測試要讓 `$HOME/.local/bin` 放 stub（run.sh 的 PATH 第一個就是它）。

## Task 2: settings 範本、plist 範本、install.sh

Files: `skill/settings.json` → 改名 `skill/settings.template.json`；`launchd/com.herb.ai-radar.plist` → 改成 `launchd/ai-radar.plist.template`；新增 `install.sh`、`tests/test_install.py`。

1. `settings.template.json`：所有 `/Users/<user>/` 開頭的規則改用 `__HOME__/`（之後渲染成絕對路徑，Bash 規則用絕對路徑沒問題）；`Edit(~/Documents/Obsidian/AI知識雷達/**)`、`Edit(~/Documents/Obsidian/INDEX.md)` 改成 `Edit(__VAULT_RULE__/AI知識雷達/**)`、`Edit(__VAULT_RULE__/INDEX.md)`。其餘不變。
2. `ai-radar.plist.template`：Label `com.__USER__.ai-radar`，路徑用 `__HOME__`。排程維持週六 09:00。
3. `install.sh`（bash，`set -euo pipefail`），旗標：
   - `--vault PATH`（必填，`~` 要展開成絕對路徑；目錄不存在 → 錯誤 exit 1）
   - `--parallel yes|no`（必填）
   - `--mail-to EMAIL`（選填，預設空＝不寄信）
   - `--model ID`（選填，預設空）
   - `--subagent-model opus|sonnet|haiku`（選填，預設 `opus`；其他值 → 錯誤）
   - `--no-launchd`（不載入排程，測試用）
   - `--skip-checks`（跳過依賴檢查，測試用）
   步驟：
   a. 依賴檢查（除非 `--skip-checks`）：`claude`、`python3`、`uv`、`defuddle`、`osascript`；缺的列出安裝方式（`brew install uv`、`npm install -g defuddle`、Claude Code 安裝網址）後 exit 1。
   b. 把 repo 的 `skill/` 同步到 `$HOME/.claude/skills/ai-radar/`（用 `rsync -a`，排除 `tests/`？→ 不排除，一起裝；排除 `__pycache__`、`config.json`、`harness_profile.md`、`settings.template.json`）。目標若已有其他檔案不刪。
   c. 寫 `config.json`（格式見 Global Constraints，用 python3 產生合法 JSON）。
   d. `harness_profile.md` 不存在時，從 `skill/harness_profile.example.md` 複製（Task 3 建立此檔；install.sh 找不到範例檔就略過）。已存在不覆蓋。
   e. 渲染 `settings.json`：`__HOME__` → `$HOME`；`__VAULT_RULE__` → vault 在 `$HOME` 底下時是 `~/<相對路徑>`，否則 `/<絕對路徑>`（結果為 `//abs`）。
   f. vault：`mkdir -p "$VAULT/AI知識雷達/attachments"`；`$VAULT/AI知識雷達/CLAUDE.md` 不存在才從 `vault-template/` 複製。
   g. 渲染 plist 到 `$HOME/Library/LaunchAgents/com.$USER.ai-radar.plist`；除非 `--no-launchd`，執行 `launchctl bootout gui/$(id -u)/com.$USER.ai-radar 2>/dev/null || true` 再 `launchctl bootstrap gui/$(id -u) <plist>`。
   h. `mkdir -p "$HOME/.local/state/ai-radar"`，最後印出摘要（安裝位置、vault、寄信、Parallel、模型、排程）。
   重複執行要安全（idempotent）：第二次用不同旗標跑會更新 config 與 settings，但不覆蓋 harness_profile.md 與 vault 的 CLAUDE.md。
4. 測試 `tests/test_install.py`：暫存 HOME（含 `Documents/Vault` 目錄），`USER=tester`，跑 `install.sh --vault ~/Documents/Vault --parallel no --no-launchd --skip-checks`：
   - skill 檔案存在、`config.json` 等於 `{"parallel": false, "vault": "<tmp>/home/Documents/Vault", "mail_to": "", "model": "", "subagent_model": "opus"}`
   - `settings.json` 是合法 JSON、含 `Edit(~/Documents/Vault/AI知識雷達/**)` 與 `Bash(<tmp>/home/.claude/skills/ai-radar/scripts/send_mail.sh:*)`，不含 `__`
   - vault 外路徑：`--vault <另一個暫存目錄>` → 規則為 `Edit(//<abs>/AI知識雷達/**)`
   - plist 在 `Library/LaunchAgents/com.tester.ai-radar.plist`、含 run.sh 絕對路徑、不含 `__`
   - vault 的 `AI知識雷達/CLAUDE.md` 與 `attachments/` 存在
   - 重跑：先改寫 harness_profile.md 與 vault CLAUDE.md 內容，再用 `--parallel yes --mail-to a@b.c --model m1 --subagent-model sonnet` 重跑 → config 更新、兩個檔案內容沒被覆蓋
   - 錯誤：缺 `--vault`、vault 不存在、`--subagent-model fable` → 非 0 結束

## Task 3: SKILL.md、vault 規範、範本檔去個人化

Files: `skill/SKILL.md`、`vault-template/AI知識雷達/CLAUDE.md`、新增 `skill/harness_profile.example.md`、`skill/config.example.json`、`tests/test_no_personal.py`。

1. `SKILL.md`：
   - description 改成「寫進 Obsidian，可選擇寄信」，拿掉 Gmail 字樣。
   - 刪「設計文件：`~/Documents/Obsidian/藍圖/AI 知識雷達.md`」那行。
   - 新增「### 0. 讀設定」：`cat ~/.claude/skills/ai-radar/config.json`，得到 VAULT、MAIL_TO、PARALLEL、SUBAGENT_MODEL；路徑表 VAULT 改成「config 的 `vault`」。
   - 全文 `~/Documents/Obsidian` 改成 `$VAULT`（指令裡）或 VAULT（說明裡）。
   - 步驟 4 wikilink：INDEX.md 不存在或沒有「## AI 概念筆記」區塊 → NOTE_NAMES 為空，subagent 不加 wikilink。
   - 步驟 5：`model: "opus"` 改成 `model: SUBAGENT_MODEL`（仍強調不可省略）。「Herb」改成「使用者」。`harness_profile.md` 不存在時告訴 subagent 不放「可加進工作流」callout。defuddle 寫法改成直接用 CLI `defuddle parse <url> --md`（不依賴 obsidian:defuddle skill）。
   - 步驟 3 評分的「與 Herb 領域的相關性」改成「與 AI Agent 工程師的相關性」。
   - 步驟 6 INDEX：INDEX.md 不存在就跳過這步；存在但沒有「藍圖」區塊時把新區塊加在檔尾。
   - 步驟 7：`send_mail.sh` 的收件者參數拿掉（腳本自己讀 config）；MAIL_TO 空時 HTML 與 digest 照做，send_mail 會印 `mail disabled` 並成功，不算失敗。
   - 步驟 8：改成「寄信成功（或 MAIL_TO 為空）後才寫」。失敗處理：MAIL_TO 空時只寫 failure.txt。
   - 收尾回覆：寄信結果含「未設定寄信」。
2. `settings.template.json` 的 allow 清單移除 `Skill(obsidian:defuddle)` 以外不動（保留也無害，**不動**）。
3. `vault-template/AI知識雷達/CLAUDE.md`：刪掉「設計文件見 [[AI 知識雷達]]（`藍圖/`）」半句；wikilink 段改成「若 vault 的 `INDEX.md` 有『AI 概念筆記』區塊，以它為準；沒有就不加」；INDEX 段改成「若 vault 有 `INDEX.md`」；Scroll to Top 標為選用。
4. `harness_profile.example.md`：一份範本，保留原檔結構（主力環境、已裝 plugins／skills、MCP 與外部工具、知識管理、已知缺口、判斷「可加進工作流」的三個標準），內容換成待填的說明文字與通用例子；第一行說明「刪掉這個檔案＝關閉『可加進工作流』標記」。原檔末段三個判斷標準照原文保留（從 `~/.claude/skills/ai-radar/harness_profile.md` 讀，只複製標準段，不複製個人工作流內容）。
5. `config.example.json`：Global Constraints 的格式，vault 放 `"/Users/you/Documents/Obsidian"`。
6. `tests/test_no_personal.py`：掃 `skill/`、`vault-template/`、`launchd/`、`install.sh` 的所有文字檔，斷言不含作者的家目錄路徑、作者的帳號／信箱前綴、`Herb`、`Documents/Obsidian`（`config.example.json` 允許 `Documents/Obsidian`）。

## Task 4: README.md 與 INSTALL.md

Files: 新增 `README.md`、`INSTALL.md`。

- `README.md`（給人看，繁中）：這是什麼（每週六 09:00 自動產出 AI 週報到 Obsidian，可選寄信）、六個版面與外國／台灣／中國分群、需求（macOS、Claude Code 已登入且方案額度夠：一次 run 會派 6 個 subagent）、安裝方式＝在 Claude Code 裡說「照 <repo URL> 的 INSTALL.md 安裝 ai-radar」、手動跑法 `~/.claude/skills/ai-radar/scripts/run.sh`、Log 位置 `~/Library/Logs/ai-radar.log`、更新方式（`git pull` 後重跑 install.sh，同樣旗標）、移除方式。Obsidian 版面：不用設定，週報格式由 skill 產生；Scroll to Top 插件選用。
- `INSTALL.md`（給安裝的 AI 看，繁中，步驟式）：
  1. 確認自己是 Claude Code（不是的話停下，告訴使用者這套工具需要 Claude Code）。
  2. 問使用者三件事：Obsidian vault 路徑；要不要寄信、寄到哪；有沒有 Parallel API key。
  3. 有 key：`claude mcp list` 看有沒有 `Parallel-Search-MCP`；沒有就 `claude mcp add --transport http --scope user Parallel-Search-MCP https://search.parallel.ai/mcp --header "x-api-key: <KEY>"`（key 由使用者自己貼，不要寫進任何檔案或 log）。MCP 名稱必須是 `Parallel-Search-MCP`。
  4. 補依賴：`brew install uv`、`npm install -g defuddle`（缺什麼裝什麼，先問使用者同意）。
  5. clone 到 `~/project/ai-radar`（或使用者指定處），執行 `./install.sh --vault ... --parallel yes|no [--mail-to ...] --model <你自己目前的 model ID> --subagent-model <你的模型家族：opus/sonnet/haiku>`。
  6. 驗證：`cd skill && uv run --quiet --with markdown python3 -m unittest discover -s tests`；要寄信的話 `~/.claude/skills/ai-radar/scripts/send_mail.sh "ai-radar 測試" <一個暫存文字檔>`，提醒使用者 macOS 會跳「允許控制 Mail」視窗要按允許，且 Mail.app 要已登入寄件帳號。
  7. （選用，問過使用者再做）手動跑一次 `run.sh` 產生第一期週報，告知約需 30–60 分鐘並消耗不少額度。
  8. 告訴使用者 `harness_profile.md` 可以依自己的工作流改寫，刪掉就不會有「可加進工作流」標記。

## Task 5（controller 執行，不派 subagent）：Herb 本機改用 repo 安裝

1. 備份 `~/.claude/skills/ai-radar` 成 `~/.claude/skills/ai-radar.bak-20261007-pkg`。
2. `./install.sh --vault ~/Documents/Obsidian --parallel yes --mail-to <你的信箱> --model claude-opus-5-5 --subagent-model opus`（Herb 的 harness_profile.md 保留）。
3. 驗證：`launchctl print gui/$(id -u)/com.herb.ai-radar` 有載入；新 settings.json 與舊版 diff 只有預期差異；skill 測試全過；send_mail.sh 用 config 寄一封測試信前先問 Herb（不寄）。
