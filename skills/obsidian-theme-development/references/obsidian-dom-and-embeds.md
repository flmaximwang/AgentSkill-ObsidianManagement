# Obsidian's rendered DOM: embeds, links, Live Preview widgets

Verified against the installed app bundle, not against community CSS:
`/Applications/Obsidian.app/Contents/Resources/obsidian.asar` (decode as utf-8 with
`errors='replace'`, then regex over the text — full recipe in
`references/electron-cdp-inspection.md` §4).

Use this file when writing selectors that target embeds, or when the question is "how does Obsidian
represent X in HTML/DOM?".

## Markdown → element mapping (the app's own remark transformer)

| Markdown | Element produced |
|---|---|
| `![[Note]]`, `![[Note#^blockid]]`, `![[Note#Heading]]` | `<span class="internal-embed" src="Note" alt="Note">` — the link rides in **`src`**, never `href` |
| `![](vault-file)` (standard syntax pointing at a vault-local file) | same class, but `hName: "div"` |
| `[[Note]]` (no `!`) | `<a class="internal-link" href="Note">` (long form adds `aria-label` + `data-tooltip-position`) |

The transformer emits an `iembed` AST node with `hProperties: {className: "internal-embed", src: …}`.
A `span` cannot legally hold block children, which is exactly why the app ships
`.internal-embed:not(.image-embed) { display: block; }` in its own app.css — that rule is the
mechanism, not a styling preference.

## Classes the embed loader adds at render time

- `.markdown-embed` — always, on the same element as `.internal-embed`.
- `.inline-embed` — added when the embed renders inline inside a note (this is the branch that also
  creates the title element).
- `.is-loaded` — added once content is in; **`.internal-embed:not(.is-loaded)` is the app's own
  "not yet rendered" selector**, useful for probing load state.
- Children created: `<div class="embed-title markdown-embed-title">` (title bar, `prepend: true`),
  `<div class="markdown-embed-link">` (hover link icon), and the rendered body wrapped in
  `markdown-embed-content` → `markdown-preview-view markdown-rendered`.
- Nesting is confirmed by app.css: `.popover.hover-popover > .markdown-embed > .markdown-embed-content > .markdown-preview-view`.

Sibling families that reuse the same pattern (all preceded by `.internal-embed`): `.pdf-embed`,
`.image-embed` (the `:not(.image-embed)` in the block rule exists to exclude it), `.file-embed`
(plus `.file-embed-title`, `.file-embed-icon`). A target that fails to resolve renders
`.file-embed.mod-empty-attachment` — a ready-made check for broken embeds instead of a CSS hack.

## Live Preview (CM6) is a different tree

In `markdown-source-view.mod-cm6`, the same embed sits inside `.cm-embed-block` (tables inside
`.cm-table-widget`). The hover box-shadow and the "edit block" button are styled there. A selector
written for reading view (`.markdown-embed …`) does nothing in Live Preview, and vice versa — cover
the mode you actually mean.

## Selector discipline (this is where wrong answers come from)

- Prefer `.internal-embed` / `.markdown-embed` / `.cm-embed-block`; they are emitted by the app.
- **Do not infer app DOM from a third-party theme's CSS sitting in the vault.** Blue Topaz defines
  `.el-embed-image` and its own body toggles (`body.naked-embed`, `body.hide-embed-title`) driven by
  its Style Settings — those exist only while that theme is active, so selectors derived from them
  are wrong everywhere else.
- Tie-breaker: grep the class string in `obsidian.asar`. If it is not there, it is not the app's.

## Grep hygiene for the bundle

When you enumerate hits for a class string, expect most of them to be noise: the flattened app.css
(selectors, easy to spot — braces, `display`/`padding` nearby) and the locale JSON blocks for every
language (`option-internal-embed`, `"Add embed"`). Filter those out and read the remaining hits for
JS signals — `className:"…"`, `hProperties`, `addClass(`, `createDiv(`, `createSpan(`. The JS hit is
where the real element and its class list are decided.
