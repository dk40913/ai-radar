# AI知識雷達/ 資料夾規範

這個資料夾放每週自動產生的 AI 動態週報。產生流程由 `~/.claude/skills/ai-radar/` 的 skill 執行。

## 命名

`YYYY-MM-DD AI知識雷達.md`，日期為產出當天。

## Frontmatter

```yaml
---
title: "AI 知識雷達 YYYY-MM-DD"
date: YYYY-MM-DD
tags:
  - type/journal
  - AI
  - radar
period_start: YYYY-MM-DD
period_end: YYYY-MM-DD
item_count: 0
sources_failed: []
---
```

## 固定版面順序

1. 頭版（1–3 條）
2. 論文版
3. 產業與產品版
4. 開源與工具版
5. GitHub AI Agent 週榜（固定 5 條，依 GitHub weekly trending 本週新增星數排名，標題 `### 名次. owner/repo（本週 +N ⭐，總計 M ⭐）`）
6. 社群熱議版
7. 本週值得跟進
8. 附錄：其他掃到的項目

產業與產品版、開源與工具版、社群熱議版依來源地區分群，每組前一行標記 `**▍外國**`／`**▍台灣**`／`**▍中國**`（沒有條目的地區省略）；目錄、HTML、信件摘要都靠這個標記分群，人工編輯時保持原樣。

`## 頭版` 之前有「本週導讀」；`> 涵蓋` 行之後有 `> [!abstract] 本期目錄` callout，由 `~/.claude/skills/ai-radar/scripts/add_toc.py` 從 `##`／`###` 標題自動產生（同頁 `[[#標題]]` 連結），人工改過標題後重跑即可更新，不要手寫。回頂端可選用社群插件 Scroll to Top 的浮動按鈕（沒裝也沒關係），筆記裡不放。

## 每條項目的寫法

標題用 `###`，接著一行 `**一句話** <20–45 字結論>`；若判斷可加進目前工作流（標準在 `~/.claude/skills/ai-radar/harness_profile.md`；該檔不存在或仍是 `（填：…）` 範本時不標），再放 `> [!tip] 可加進工作流` callout 寫理由，目錄會自動標「🔧 可加進工作流」；有圖的話放 `![[<attachments 裡的檔名>]]` 加一行 `*圖：說明*`，然後正文固定四段：**是什麼**、**技術核心**、**為什麼重要**、**對 AI Agent 工程師的意義**。結尾列原始連結與討論連結。

圖片都是從原文抓來的（論文架構圖、文章主圖、專案示意圖），存在 `attachments/`，檔名 `YYYY-MM-DD-<索引>-<slug>.<ext>`。沒抓到圖的條目就沒有圖，不用 AI 生圖補。若原始來源讀不到、只依摘要撰寫，在該條開頭加 `> [!warning] 僅依摘要`。

## Wikilink

提到 vault 已有的概念筆記時要連結（例如 `[[MoE 混合專家架構]]`、`[[KV Cache]]`、`[[MCP]]`、`[[LangGraph]]`）。若 vault 的 `INDEX.md` 有「AI 概念筆記」區塊，可連結的名單以它為準；沒有就不加 wikilink。

## INDEX.md

若 vault 有 `INDEX.md`，每期產出後在「AI 知識雷達」區塊加一行：`- [[YYYY-MM-DD AI知識雷達]] — 頭版一句話`。

## 交付格式

- Obsidian：這個資料夾的 markdown（Obsidian 會渲染圖片與 wikilink）
- Email：短版摘要為內文，完整報紙排版的單檔 HTML 為附件（由 `build_html.py` 產生，圖片內嵌）

## 人工編輯

週報是自動產出，之後人工補註或修正都可以，不會被下一期覆寫。
