# Obsidian print / PDF pipeline (source-verified)

Everything here was read out of a running install — `obsidian.asar` (Obsidian 1.6.7) and
`better-export-pdf`'s `main.js` — then reproduced on a real Chromium/Electron engine.
Re-verify against the current Obsidian version before repeating it as fact.

## Two pipelines, two kinds of "the print HTML is not the app HTML"

| | native: `Cmd+P` / command `workspace:export-pdf` | better-export-pdf: `export-current-file-to-pdf` |
|---|---|---|
| Where it renders | **the same document**: `document.body.createDiv("print")`, the note is rendered into that `div.print`, and `detach()` removes it right after | **a separate document**: `<webview src="app://obsidian.md/help.html" class="print-preview-container">`, filled with the app's `head.innerHTML` plus the `.print` subtree |
| Print CSS | real `@media print` (the PDF goes through `printToPDF`) | the plugin **unwraps** every `@media print` rule in the app's stylesheets (`cssText.replace(/@media print\s*{(.+)}/gms, "$1")`) and `insertCSS`s it into the webview, so those rules also apply under screen media |
| Theme mode | if the vault uses the default theme, `body` gains `theme-light` and loses `theme-dark` for the duration, then it is restored | the plugin decides itself (`theme-light-auto-patch` helper) |
| App UI | `body > :not(.print) { display: none !important }` | irrelevant — the webview has no app UI |
| Backgrounds | whatever `printToPDF` is given | plugin setting; `data.json` `printBackground: false` is a common silent cause of missing callout backgrounds |

Native path as it appears in `obsidian.asar`:

```js
// export flow
(t = "obsidian" === app.vault.getConfig("theme")) && (document.body.addClass("theme-light"),
  document.body.removeClass("theme-dark")), document.body.removeClass("theme-dark"),
  n = document.body.createDiv("print"), (i = new <PrintView>).load(),
  await this.print(n, i, e.includeName), await sleep(200),
  ipcRenderer.send("print-to-pdf", opts),   // main: sender.printToPDF(opts) -> fs.writeFile
  r = function () { n.detach(), i.unload(), /* restore theme classes */ }
// command
app.commands.addCommand({ id: "workspace:export-pdf", checkCallback: e => (e || t.printToPdf(), true) })
// MarkdownView.prototype.printToPdf = function () { new <ExportModal>(this.app, this.file).open() }
```

The app's own print block (verbatim; `body > :not(.print)` is the load-bearing rule):

```css
@media print {
  html, body { padding-top: 0 !important; overflow: auto !important; height: auto !important }
  iframe, .titlebar, .app-container, .progress-bar, .popover,
  .markdown-embed-link, .suggestion-container { display: none !important }
  body > :not(.print) { display: none !important }
  .print .markdown-preview-view { -webkit-print-color-adjust: exact; color: initial }
  .print .markdown-preview-view mark { color: initial }
  .print .markdown-preview-view .metadata-container { display: none }
  .print .markdown-preview-view .markdown-embed-content { max-height: none; overflow: visible }
  .print .markdown-preview-view .callout-content { display: inherit !important }
  .print .external-link { background: none; padding-right: 0 }
  * { text-shadow: none !important }
  webview { display: none }
  ::-webkit-scrollbar { display: none }
  body { --font-text: var(--font-print) !important }
}
```

Theme-side consequences: the print DOM is `<div class="print"><div class="markdown-preview-view ...">`,
so `.print > .markdown-preview-view` is the selector that matches; and print swaps the text font to
`--font-print`, so a theme that overrides fonts can look different on paper than on screen.

## Measured facts (reproduce, do not assume)

1. **`outerHTML` is identical under screen and print emulation.** Two dumps of the same probe page
   were byte-identical (846 chars, structural diff = 0) while the same element's computed style
   differed completely: screen `.print { display: none; width: auto }` vs print
   `.print { display: block; width: 714px; margin: 0 21px }`, font 15px, `--print-zoom: 100`.
   → Compare computed styles or rendered images; text diff is the wrong instrument.
2. **A document with no `.print` element prints as a completely blank page.** Measured: every pixel
   of that PDF page had `alpha = 0`; the control page (with `.print`) had opaque white plus content
   colour. That is `body > :not(.print) { display: none !important }` doing exactly what it says —
   which is why the native path must have `.print` frozen to be inspectable, and why
   better-export-pdf builds its own document instead.
3. **The native `.print` element is short-lived** — `detach()` runs right after the PDF is written,
   so after an export the DOM is clean and there is nothing to inspect.

## Capture recipes

### A — preferred: dump better-export-pdf's print document

Opening the export dialog is enough: the print document already exists as its own CDP target and
stays alive until the dialog closes. No printing, no race.

```bash
# Obsidian must be fully quit first (the debug port only applies at launch)
osascript -e 'quit app "Obsidian"'
./launch-obsidian-debug.sh
# in Obsidian: command palette -> "Better Export PDF: Export current file to PDF" (open dialog only)
python3 cdp.py targets                      # app://obsidian.md/index.html + the webview target
python3 cdp.py --target webview dump --out captures
python3 cdp.py --target webview pdf  --out captures/print.pdf --pagesize A4
```

If the webview does not show up as a target on the user's build, fall back to B/C and say so
rather than assuming.

### B — native path, freeze `.print` first

Patch the app DevTools console **before** exporting: wrap `Node.prototype.detach` so a node with
class `print` is kept (log it, return it) instead of removed, and expose an unfreeze function that
restores the original and clears leftovers. Export normally, then read
`document.querySelector('div.print').outerHTML` and its computed styles at leisure.

### C — lightest: computed style under both media

```bash
python3 cdp.py --target app styles --media screen
python3 cdp.py --target app styles --media print
```

Watch `.print`, `.print > .markdown-preview-view`, `.markdown-preview-view > div`, `table`,
`.callout`, and the theme's own `--print-zoom` / `--print-page-width` variables.

## Visual regression

```bash
python3 cdp.py --target app pdf --out out/before.pdf --pagesize A4    # before the CSS change
npm run build
python3 cdp.py --target app pdf --out out/after.pdf  --pagesize A4
python3 cdp.py png out/before.pdf --dpi 110     # -> out/before.pages/page-1.png
python3 cdp.py png out/after.pdf  --dpi 110
python3 cdp.py pxdiff out/before.pages/page-1.png out/after.pages/page-1.png --out out/diff.png
```

`RMSE 0` = pixel-identical; non-zero means open `diff.png`. The per-page PNGs are also the input for
a vision-capable agent — feed them into the conversation to judge pagination, margins and callout
backgrounds instead of inferring them from CSS.

## Proving print media really applied

Do not trust the emulation flag alone; check the artifact:
`magick page-1.png -format %c histogram:info:- | sort -rn | head`.
Content colour present plus no app-UI background colour (e.g. the `#eee` of `.app-container`) is
positive proof that print media rendered and the app UI was hidden.
