# 各地社群反應加 Threads（試用，選用）— Plan

**Goal:** 「各地社群反應」版面可選擇多看 Threads。另開旗標，讓有 Parallel key 的使用者自己評估要不要開、要不要繼續用；不開時行為與現在完全相同。

**Spec（Herb 2026-10-08）：** 「可以加進 threads 看看，給使用者自己選擇評估要不要開啟、要不要繼續使用，但我這邊先不用」。

**已實測（2026-10-08）：**
- 本機 curl／Jina 只拿到 HTML 空殼。
- Parallel `web_fetch`（`full_content: true`）抓 `threads.com/@<帳號>/post/<id>` 拿得到本文與第一批回覆（帳號、日期、全文、幾個互動數字），但只是第一批：一篇顯示 39 則回覆抓回約 16 則，另一篇顯示 19 則回覆只抓回作者自己的 11 段串文。頁面底部附「Related threads」（別篇，日期不一）。
- 互動數字頁面上沒有標籤，無法確定哪個是讚數。
- `web_search` 用事件名稱搜得到當週貼文；泛搜只會撈到舊文。

## Global Constraints

- 新旗標 `--threads yes|no`，預設 `no`；只在 `--parallel yes` 時可以是 `yes`。Herb 的 live 安裝不帶（＝no）。
- `threads` 為 false 時 SKILL.md 的反應步驟、輸出格式、info 行都和現在一樣（三個平台）。
- 不改 `build_html.py`（版面與摘要只看 `###` 標題，平台段落數不影響）。
- 出貨檔案不得含個人字串（`tests/test_no_personal.py` 照舊要過）。
- 測試：repo 根目錄 `python3 -m unittest discover -s tests`，以及 `cd skill && uv run --quiet --with markdown python3 -m unittest discover -s tests`，全部通過。

## Task 1: 旗標、SKILL.md、文件與測試

Files: `install.sh`、`skill/config.example.json`、`skill/SKILL.md`、`tests/test_install.py`、`tests/test_skill_md.py`、`README.md`、`INSTALL.md`。

1. `install.sh`：
   - 新增 `--threads yes|no`（不帶＝`no`）。值不是 yes/no → `die "--threads must be yes or no"`；`--threads yes` 但 parallel 不是 yes → `die "--threads yes needs --parallel yes"`。
   - config.json 寫入 `"threads": true|false`。
   - usage 加 `[--threads yes|no]`；安裝摘要在 parallel 那行之後加一行 `  threads:   yes` 或 `  threads:   no`。
2. `skill/config.example.json`：在 `"parallel": false` 之後加 `"threads": false`。
3. `skill/SKILL.md`：
   - 步驟 0「記下六個值」改「七個值」，加一項 `- THREADS = \`threads\`（沒有這個鍵時當 false；只在 PARALLEL 為 true 時有作用）`。
   - 步驟 5 反應 subagent 的 prompt 內容清單加上 THREADS 的值。
   - 固定指令開頭改成「到知乎、Dcard、Reddit（THREADS 為 true 時再加 Threads）找本週的討論」。
   - 第 2 點平台清單在 Reddit 之後加：
     > - Threads（THREADS 為 true 才做）：搜 `threads <搜尋詞>`，取 `threads.com/@<帳號>/post/<id>`（或 `threads.net`）的貼文，web_fetch 最多 2 篇並帶 `full_content: true`。抓回來的是本文加第一批回覆，常少於頁面顯示的回覆總數，有時只有作者自己的連續串文：作者自己的串文寫明是原 po 的說法，不要當成別人的反應。每則後面的互動數字頁面沒標示是哪一項，所以 Threads 的引用不寫讚數括號。頁面底部「Related threads」是別篇，只在日期於 SINCE 之後且講同一事件時才用，引用時附那篇自己的網址。
   - 第 5 點輸出格式：「三行，依序 `**知乎** `、`**Dcard** `、`**Reddit** ` 開頭」改成依序這三個、THREADS 為 true 時再加 `**Threads** ` 一段；「三個平台各自一段」改「每個平台各自一段」。
   - 步驟 6 的 info 行：THREADS 為 true 時改成 `> [!info] 依本週頭版搜尋知乎、Dcard、Reddit、Threads 的討論，留言是網友意見，未經查證。`，false 時維持原句。
4. `tests/test_install.py`：不帶旗標 → config `threads` 為 False、輸出含 `threads:   no`；`--parallel yes --threads yes` → True、輸出含 `threads:   yes`；`--threads maybe` → 失敗且 stderr 含 `--threads must be yes or no`；`--threads yes`（不帶 parallel）→ 失敗且 stderr 含 `--threads yes needs --parallel yes`。既有兩個比對整份 config 的測試補上 `"threads": False`。
5. `tests/test_skill_md.py`：`ReactionsStepTest` 的 needles 加 `THREADS = \`threads\`` 與 `threads.com/@`。
6. `README.md`：
   - 各地社群反應段落補一句：可另外開 Threads（試用，`--threads yes`）：只抓得到每篇的第一批回覆、互動數字沒有標籤，看過幾期再決定要不要留著，重裝時改 `--threads no` 即關閉。
   - config 表說明「是否用 Parallel」改「是否用 Parallel、是否加看 Threads」；重裝指令加 `--threads <yes|no>`。
   - 「Facebook、Threads、Instagram 擋抓取或要登入，沒有收錄」改成 Threads 不是候選來源，只在開了 `--threads yes` 時用來看頭版反應（Facebook、Instagram 維持沒有收錄）。
7. `INSTALL.md`：
   - 第 2 步第 6 題後補：有 key 的話接著問要不要試用 Threads（說明同 README 那句的限制）。
   - install 指令加 `--threads <yes|no>`，參數說明加一行：使用者有 Parallel 且想試 Threads 才填 `yes`，否則 `no`。
