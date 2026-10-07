> 刪掉這個檔案＝關閉「可加進工作流」標記（週報裡就不會出現 `> [!tip] 可加進工作流` callout）。

# 我目前的 AI 工作流（harness）現況

給週報撰稿時判斷「這條能不能加進現有工作流」用。照下面各段把你自己的環境填進去（刪掉範例文字），工作流有變動時更新這份。寫得越具體，判斷越準。

## 主力環境

- （填：主要用的 coding agent 與介面，例如「Claude Code（Mac，CLI 為主），主模型 Opus」）
- （填：全域 `CLAUDE.md` 或專案規範裡的重點，例如「開發預設先寫 plan 再 TDD」）
- （填：有沒有長期記憶、怎麼存，例如「檔案式 memory，一檔一事實」）

## 已裝的 plugins／skills

- （填：已裝的 plugin 與常用 skill，例如「superpowers（brainstorming、TDD、code review）」「document-skills（docx／pptx／xlsx／pdf）」）
- （填：自製的 skill，例如「ai-radar（本週報）」）

## MCP 與外部工具

- （填：已接的 MCP server 與用途，例如「網頁搜尋 MCP、瀏覽器自動化 MCP」）
- （填：排程或無人值守的做法，例如「launchd ＋ `claude -p` ＋ 權限白名單」）

## 知識管理

- （填：筆記工具與用法，例如「Obsidian vault，放工作日誌與 AI 概念筆記」）

## 已知缺口（加分項）

- （填：你覺得工作流還缺什麼，例如「跨 session 的經驗沒有自動萃取」「subagent 用量缺少監控」「無人值守任務沒有沙箱隔離」）

## 判斷「可加進工作流」的標準

標記條件（全部成立才標）：
1. 是能實際裝上或照做的東西（skill、plugin、MCP server、CLI、harness 設定、可複製的做法），不是只有新聞或論文結論。
2. 能補上面的缺口，或明顯強化現有某一環；不是已有功能的重複品（例如另一個完整 agent harness、另一套 brainstorming 流程）。
3. 跟 Claude Code／Mac 環境相容，或改一下就能接上。

標記時寫一句話說明：加在哪一環、補什麼、和現有的哪個東西有重疊要注意。
