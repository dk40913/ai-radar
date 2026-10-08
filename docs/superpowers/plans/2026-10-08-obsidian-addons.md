# Obsidian 外觀與導覽插件 — Plan

**Goal:** 讓安裝 ai-radar 的人可以選擇一併拿到作者在 Obsidian 裡用的週報外觀與導覽按鈕，並在 README／INSTALL 寫清楚需要裝什麼。週報本身只用 Obsidian 內建功能（callout、wikilink、frontmatter），這些全部是選用。

**Spec（Herb 2026-10-08）：** 「把這個插件也放進 ai-radar repo，還有其他我們在 obsidian 裡面有使用的套件也寫進去，需要安裝什麼之類的」。

已匯入 repo（commit 82b6978，不用再改內容）：
- `obsidian/plugins/note-nav-buttons/`：本地插件（manifest.json、main.js、styles.css）。右下角 ↑ ☰ ↓，☰ 跳出目前筆記的標題清單。不在社群插件市集，只能手動放進 vault。
- `obsidian/snippets/newspaper.css`：報紙風配色與標題字體，CSS 片段，作用於整個 vault（不只週報）。
- `obsidian/style-settings.json`：Things 主題的 Style Settings 設定（19 個 `things-style@@` 鍵），可用 Style Settings 的 Import 匯入。

README 截圖的外觀＝Things 主題（社群主題）＋Style Settings 插件（社群插件，匯入上面的 JSON）＋newspaper 片段。

## Global Constraints

- 全部選用；不選時安裝行為與現在完全相同。
- 安裝程式只「複製檔案」，不改 `.obsidian/community-plugins.json`、`appearance.json` 或任何 Obsidian 設定檔（Obsidian 執行中改這些會被覆寫）。啟用由使用者在 Obsidian 介面操作，文件寫清楚步驟。
- 已存在的 `newspaper.css` 不覆蓋（印一行 `kept existing ...`）；`note-nav-buttons` 插件資料夾每次覆蓋成 repo 版本（它是本專案的檔案，等同更新）。
- 不安裝社群主題／社群插件（Things、Style Settings）；只在文件說明怎麼在 Obsidian 裡裝。
- 出貨檔案不得含個人字串：把 `obsidian/` 加進 `tests/test_no_personal.py` 的 SCAN。
- 測試：`uv run --quiet --with markdown python3 -m unittest discover -s skill/tests && python3 -m unittest discover -s tests`（repo 根目錄），全部通過。

## Task 1: install.sh 選項、文件與測試

Files: `install.sh`、`tests/test_install.py`、`tests/test_no_personal.py`、`INSTALL.md`、`README.md`。

1. `install.sh`：新增旗標 `--obsidian-addons`（不帶值）。帶了才做：
   - 把 `obsidian/plugins/note-nav-buttons/` 複製到 `<vault>/.obsidian/plugins/note-nav-buttons/`（先建目錄；覆蓋）。
   - 把 `obsidian/snippets/newspaper.css` 複製到 `<vault>/.obsidian/snippets/newspaper.css`，已存在就保留並印 `kept existing <路徑>`。
   - 安裝摘要多印一行 `obsidian:  addons copied (enable them in Obsidian)`；沒帶旗標印 `obsidian:  no addons`。
   - usage 字串加上 `[--obsidian-addons]`。
2. `tests/test_install.py`：
   - 帶 `--obsidian-addons`：vault 下出現插件三個檔與 `newspaper.css`，內容與 repo 相同。
   - 預先放一個內容不同的 `newspaper.css` 再帶旗標：檔案不被覆蓋，輸出含 `kept existing`。
   - 不帶旗標：vault 下沒有 `.obsidian/plugins/note-nav-buttons`。
   - 不得建立或修改 `community-plugins.json`、`appearance.json`。
3. `tests/test_no_personal.py`：SCAN 加 `REPO / "obsidian"`。
4. `INSTALL.md`：
   - 第 2 步多問一題：「要不要一併裝 Obsidian 的週報外觀與導覽按鈕？（選用：右下角回頂端／目錄／到底端按鈕，以及報紙風配色。配色會套用到整個 vault。）」
   - 第 4 步：使用者要的話，install.sh 加 `--obsidian-addons`。
   - 第 7 步收尾：要的話，告訴使用者在 Obsidian 裡完成這些（用使用者語言、照順序）：
     1. 設定 → 社群插件：關閉「限制模式」，在已安裝插件裡啟用「Note Nav Buttons」。
     2. 設定 → 外觀 → CSS 片段：按重新整理，啟用 `newspaper`。
     3. （要完全一樣的外觀才需要）設定 → 外觀 → 主題：瀏覽並安裝、套用「Things」；設定 → 社群插件 → 瀏覽：安裝並啟用「Style Settings」，到 Style Settings 的設定頁按 Import，貼上 repo 裡 `obsidian/style-settings.json` 的內容。
5. `README.md`：
   - 新增一節「Obsidian 外觀與導覽（選用）」放在「安裝」之後：表格列出四項（Note Nav Buttons 插件、newspaper 片段、Things 主題、Style Settings＋設定檔），欄位為「是什麼」「從哪裡來」「怎麼裝」。說明週報本身不依賴任何一項；newspaper 片段影響整個 vault；Note Nav Buttons 適用任何筆記。
   - 「安裝」段提到可用 `--obsidian-addons` 一併複製插件與片段。
   - 「安裝後的檔案」表加兩列（帶 `--obsidian-addons` 時）：`<vault>/.obsidian/plugins/note-nav-buttons/`、`<vault>/.obsidian/snippets/newspaper.css`。
   - 「移除」段補一句：在 Obsidian 停用並刪除上述兩項。
   - 「需求」段在 Obsidian 那行補「外觀與導覽按鈕是選用，見下方」。
