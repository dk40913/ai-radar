# 移除 Parallel MCP — Plan

**Goal:** ai-radar 不再使用 Parallel MCP。defuddle 讀不到的頁面一律用 Jina Reader 補抓，安裝時不再詢問或設定 Parallel API key。

**Spec（Herb 2026-10-08）：** 「拔掉 parallel mcp 在知識雷達裡面的應用，這樣我或是其他使用者也不需要再申請 api key」。背景：雷達的來源是固定清單，Parallel 只用在補抓，Jina 涵蓋同樣的來源（README 的來源表兩欄都是 ✅）。

## Global Constraints

- 補抓只剩一條路：`python3 ~/.claude/skills/ai-radar/scripts/jina_read.py <url>`（非 0 結束＝讀不到，改依摘要撰寫並標「僅依摘要」，這段既有行為不變）。
- config.json 移除 `parallel` 鍵，其他鍵不變。
- `install.sh` 不再需要 `--parallel`。為了讓照舊說明重跑的人不會失敗：仍接受 `--parallel <值>`，忽略並在 stderr 印一行 `note: --parallel is no longer used, ignoring`。
- 不動來源清單、`fetch_sources.py`、版面與撰稿規則。
- 不處理使用者電腦上已設定的 Parallel MCP（其他工具可能在用）；README 解除安裝段把「有設 Parallel MCP…」那句刪掉即可。
- 出貨檔案不得含個人字串（`tests/test_no_personal.py` 照跑）。
- 測試：`uv run --quiet --with markdown python3 -m unittest discover -s skill/tests && python3 -m unittest discover -s tests`（repo 根目錄），全部通過。
- 跑完 `grep -rn -i parallel --exclude-dir=.git --exclude-dir=.superpowers --exclude-dir=docs .` 只剩 install.sh 的忽略分支與其測試。

## Task 1: 拔除 Parallel

Files: `install.sh`、`skill/SKILL.md`、`skill/settings.template.json`、`skill/config.example.json`、`skill/scripts/jina_read.py`（docstring）、`INSTALL.md`、`README.md`、`tests/test_install.py`、`tests/test_scripts.py`、必要時 `tests/test_skill_md.py`。

1. `install.sh`：
   - 拿掉 `PARALLEL` 變數、必填檢查與 `yes|no` 驗證、寫入 config 的 `parallel`、安裝摘要的 `parallel:` 行。
   - usage 改成 `install.sh --vault PATH [--mail-to EMAIL] [--model ID] ...`。
   - `--parallel` 照 Global Constraints 接受並忽略。
2. `skill/SKILL.md`：
   - 第 0 步拿掉 `PARALLEL = parallel`。
   - 補抓方式那段（「依 PARALLEL 二選一」）改成固定一句：跑 `jina_read.py`（Jina Reader，免 key；非 0 結束代表讀不到）。固定指令裡 `<補抓方式>` 的代入改成直接寫死這句，或保留佔位符但只剩一個值；選較簡單者。
   - 其他文字不動。
3. `skill/settings.template.json`：移除 `mcp__Parallel-Search-MCP__web_fetch` 那條 allow（注意 JSON 逗號）。
4. `skill/config.example.json`：移除 `"parallel": false`。
5. `skill/scripts/jina_read.py`：docstring 第二行改成「defuddle 讀不到時的補抓；有設 JINA_API_KEY 環境變數會帶上，額度較高。」程式不動。
6. `INSTALL.md`：
   - 刪掉 Parallel key 的安全規則、第 2 步「有沒有 Parallel API key」那題、整個「設定 Parallel MCP」步驟；後面步驟重新編號，並修正文內所有「第 N 步」的交叉引用。
   - install 指令範例拿掉 `--parallel`。
7. `README.md`：
   - 「來源與讀取方式」：說明改成「讀原文先用 defuddle，擋爬蟲或要跑 JavaScript 的頁面改用 Jina Reader 補抓（免 key，約每分鐘 20 次；設 `JINA_API_KEY` 可提高額度）」。表格把「有 Parallel／沒有 Parallel」兩欄合併成一欄「讀得到原文」，值沿用原本（✅、⚠️ 僅摘要等），「✅ Parallel」「✅ Jina」都變成 ✅。表下那段改成只講 Jina 的次數上限與「僅依摘要」，保留 Medium 與未收錄平台的說明。
   - Mermaid 圖 `讀不到時：Parallel web_fetch（有 key）→ Jina Reader` 改成 `讀不到時：Jina Reader`。
   - 需求清單刪掉 Parallel 那行；安裝段「會問你幾件事」刪掉 Parallel key；config 說明表刪掉「是否用 Parallel」；更新段指令拿掉 `--parallel <yes|no>`；解除安裝段刪掉 Parallel MCP 那句。
   - 英文介紹段若提到 Parallel 一併處理（目前沒有就不動）。
8. 測試：
   - `tests/test_install.py`：所有呼叫拿掉 `--parallel`；config 全等比對拿掉 `parallel`；刪掉「缺 `--parallel`」與「`--parallel maybe`」這兩個失敗案例；新增一個測試：帶 `--parallel yes` 仍安裝成功、config 沒有 `parallel` 鍵、stderr 含 `no longer used`。
   - `tests/test_scripts.py`：測試用 config 拿掉 `parallel`。
   - `tests/test_skill_md.py`：加一個檢查：SKILL.md 與 settings.template.json 都不含 `Parallel`。
