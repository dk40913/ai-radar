const { Plugin, MarkdownView } = require("obsidian");

module.exports = class NoteNavButtons extends Plugin {
  onload() {
    this.fab = document.body.createDiv({ cls: "nnb-fab" });
    this.button("↑", "回到頂端", () => this.scrollTo(0));
    this.button("☰", "目錄", () => this.togglePanel());
    this.button("↓", "到底端", (view) => this.scrollTo(view.editor.lineCount()));
    this.panel = document.body.createDiv({ cls: "nnb-panel" });
    this.panel.hide();

    this.registerDomEvent(document, "mousedown", (e) => {
      if (!this.panel.contains(e.target) && !this.fab.contains(e.target)) this.panel.hide();
    });
    this.registerDomEvent(document, "keydown", (e) => {
      if (e.key === "Escape") this.panel.hide();
    });
    const refresh = () => {
      this.fab.toggle(!!this.view());
      this.panel.hide();
    };
    this.registerEvent(this.app.workspace.on("active-leaf-change", refresh));
    this.app.workspace.onLayoutReady(refresh);
  }

  onunload() {
    this.fab.remove();
    this.panel.remove();
  }

  view() {
    return this.app.workspace.getActiveViewOfType(MarkdownView);
  }

  button(text, label, onClick) {
    const b = this.fab.createEl("button", { text, attr: { "aria-label": label } });
    b.addEventListener("click", () => {
      const view = this.view();
      if (view) onClick(view);
    });
  }

  scrollTo(line) {
    const view = this.view();
    if (view) view.currentMode.applyScroll(line);
  }

  togglePanel() {
    // isShown() 看 offsetParent，固定定位的元素永遠是 null，所以改看 display
    if (this.panel.style.display !== "none") return this.panel.hide();
    const view = this.view();
    const headings = (view && this.app.metadataCache.getFileCache(view.file)?.headings) || [];
    this.panel.empty();
    this.panel.createDiv({ cls: "nnb-title", text: "目錄" });
    if (!headings.length) this.panel.createDiv({ cls: "nnb-empty", text: "這篇筆記沒有標題" });
    const top = Math.min(...headings.map((h) => h.level));
    for (const h of headings) {
      const item = this.panel.createDiv({ cls: "nnb-item", text: h.heading });
      item.style.paddingLeft = `${(h.level - top) * 14 + 10}px`;
      if (h.level === top) item.addClass("nnb-top");
      item.addEventListener("click", () => {
        view.setEphemeralState({ subpath: "#" + h.heading });
        this.panel.hide();
      });
    }
    this.panel.show();
  }
};
