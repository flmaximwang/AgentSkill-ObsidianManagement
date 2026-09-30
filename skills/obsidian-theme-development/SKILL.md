---
name: obsidian-theme-development
description: "Use when styling Obsidian's DOM or building/publishing a theme."
version: 1.0.0
metadata:
  domains: [obsidian, css, electron, theme-publishing]
  related_skills: [obsidian, macos-computer-use, github-pr-workflow]
---

# Obsidian Theme Development & Maintenance

Maxim's theme is **Workbench** (floating sidebars + print-optimised layout), repo
`~/Repositories/Obsidian-Workbench-CSS`. Official docs: `docs.obsidian.md` → Themes →
Build a theme / Submit your theme.

## Repo shape and build

- `src/**/*.css` (nested, `@import`ed) → **`theme.css`**, built by PostCSS:
  `postcss-import-ext-glob` + `postcss-import` + a local `postcss-collect-settings.js`.
- `npm run build` == `postcss src/main.css -o theme.css`. `theme.css` is a build artifact
  (thousands of lines) — never hand-edit it, edit `src/` and rebuild.
- `postcss-collect-settings.js` hoists every `/* @settings ... */` YAML comment found in
  `src/` to the **top** of `theme.css`, because Style Settings scans the built file. So
  `@settings` blocks live beside the CSS they configure but land in one block after build.
- `manifest.json`: `name` / `version` / `author` / `minAppVersion`. `minAppVersion` means
  "Obsidian older than this cannot install the theme" — raise it only when the theme really
  uses newer CSS, or it cuts off users.
- Test/dev vaults: `VaultExample/` (has `obsidian-style-settings`, `better-export-pdf`) and
  `tests/TempVault`. A vault's `.obsidian/appearance.json` `cssTheme` must equal the theme
  folder name actually present under `.obsidian/themes/`.
- Keep `src/*.css.bak*` out of the tree: agents read `.bak` files as source.

## Verification loop (applies to every change)

1. **Load the built file, never a copy.** Symlink the repo root (it already contains both
   `manifest.json` and `theme.css`) into `<dev-vault>/.obsidian/themes/<Name>/`.
   Prove the link is live before trusting observations:
   `md5 -q theme.css` vs `md5 -q <dev-vault>/.obsidian/themes/<Name>/theme.css`.
   Equal hashes only prove "not stale"; an identical pair right after editing `src/` without a
   rebuild is the signature of hand-copying, i.e. you are looking at old CSS.
2. **Judge CSS from rendered pixels, never from reading selectors.** Produce an artifact —
   a screenshot of the Obsidian window, or a print PDF converted to PNG — and look at it.
   Reading CSS is how you reach plausible-but-wrong conclusions.
3. **Only a seeing agent can close this loop.** For visual iteration use a path with
   screenshots + vision (Hermes `computer_use` on the Obsidian window; PNG → `vision_analyze`).
   A terminal-only coding agent is the "hand" for mechanical work (refactors, build scripts,
   release chores); give it the constraining rules through `AGENTS.md`, not visual judgement.
   `AGENTS.md` at the repo root is the right carrier (Codex/Cursor read it).
4. **Maxim runs anything that restarts or mutates his running apps.** For steps such as
   quitting Obsidian to relaunch it with a debug flag, hand him the command plus expected
   output and how to verify — do not quit/relaunch or drive his app yourself.
5. Put new tooling in `tools/` inside the theme repo and leave it **untracked** unless he asks
   to commit it.

## Print / PDF testing

Read `references/print-and-pdf-pipeline.md` before touching any `@media print` rule: it holds the
three rendering pipelines, the app's own print CSS, and the measured traps. Run `scripts/cdp.py`
(live full copy, with an extra HTML-diff subcommand: `tools/print-harness/cdp.py` in the repo).

Two traps to know before starting:

- **Printing with no `.print` element in the DOM renders a blank page** — Obsidian's app.css has
  `body > :not(.print) { display: none !important }` inside its print block.
- **Under print-media emulation `outerHTML` is byte-identical to screen media.** Only computed
  style and layout change, so compare `getComputedStyle` or rendered pixels; diffing HTML text
  returns "0 differences" and tells you nothing.

## Publishing / review checklist

- The community directory reads `manifest.json` at the **HEAD of the default branch** — commit it
  before submitting.
- Obsidian installs from the GitHub release whose **tag equals the manifest version**, taking
  `manifest.json` + `theme.css` from that release's assets. A tag/version mismatch is a broken
  install for every user.
- Needed before review: a `README.md` describing the theme, a 512×288 screenshot, a license.
- Run `stylelint-config-obsidianmd` the way obsidian-sample-theme does (`npm install` once, then
  `npm run lint`): it enforces the same CSS rules the theme review applies, far cheaper than a
  rejection round.
- Submit at `community.obsidian.md` with an Obsidian account and a linked GitHub account. Only
  the first version is submitted; later versions reach users through GitHub releases.
- Never claim the theme is published without checking: fetch
  `obsidianmd/obsidian-releases` → `community-css-themes.json` and search the theme name/author.

## Pitfalls

- A theme folder named differently from `.obsidian/appearance.json`'s `cssTheme`, or from the
  symlink target, means "I already symlinked it" silently is not in effect — verify by path, not
  by memory.
- When print output surprises you, re-read the app's own `@media print` block inside
  `obsidian.asar` (see `references/electron-cdp-inspection.md` for reading packed asar) instead of
  reasoning from the theme's CSS alone.
- **Never infer Obsidian's DOM or class names from a third-party theme's CSS found in the vault.**
  Blue Topaz contributes `.el-embed-image` and its own body toggles (`body.naked-embed`,
  `body.hide-embed-title`) that exist only while that theme is active, so a map read this way is
  wrong on every other install. `obsidian.asar` is the tie-breaker: if a class is not in the bundle
  it is not the app's. Class map for embeds, links, Live Preview widgets and the grep hygiene to
  build it: `references/obsidian-dom-and-embeds.md`.
