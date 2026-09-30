---
name: obsidian-bases
description: Author Obsidian Bases formulas, filters, and summaries.
platforms: [linux, macos, windows]
---

# Obsidian Bases (formulas / filters / summaries)

Use when the user asks to write or modify an Obsidian Bases formula, filter, view, or summary — in any vault (`.base` files and embedded `![[X.base]]` blocks).

## Architecture decides what is possible — check it before promising a query

- **filters** scan EVERY note in the base's dataset → cross-note matching lives here (e.g. `note["culture-pellet-source"].contains(this.note["UID"])`).
- **formulas** are per-row: they only see the current row's note + the `this` context. There is NO `notes()` function and no way to query or aggregate OTHER notes inside a formula (official Functions/Formulas docs + forum thread "Bases Formula: Cross-Note Lookup & Rollup"). Do not promise a rollup / 跨笔记求和 / "list of other notes" as a formula column — it does not exist.
- **summaries** aggregate across the view's rows (built-in Sum/Average, or custom via the `values` keyword) → this is how "sum over all matched notes" is actually done.
- **`this` context**: base embedded in a note → `this` = the embedding note; opened standalone → the base file; sidebar → the active file. Per-row values use the UNQUALIFIED property (`prop` / `note["prop"]`), never `this`.

## Reading the official docs

help.obsidian.md is JS-rendered — web_extract/browser return only the TOC. Pull the markdown from GitHub `obsidianmd/obsidian-help`: `en/Bases/Formulas.md`, `en/Bases/Functions.md`, `en/Bases/Bases syntax.md` (note the space in the filename).

## User preferences (this user)

- Prefer **editing the existing `.base`** (formula column / summary row) and show the concrete edit before writing. That rule exists to stop you inventing new files where a base already covers the data — it does NOT forbid creation: when the user asks to "用 Obsidian 数据库插件展示" records that have no base yet, building the base IS the request. Check first (`search_files pattern="*.base"` in the vault), then build and tell them the path.
- Ask before modifying vault files; when a Bases request turns out technically impossible, state the constraint with the source, give the working alternatives, and let them pick.

## Building a new row-per-note base (the "make me a database" request)

The shape that works: **one note per record, fields in frontmatter, one `.base` that filters on a tag, plus a hub note that embeds the base.**

1. **Confirm the key syntax against a `.base` the user already has** — read their vault's existing `.base` files instead of guessing keys. Their files are the ground truth for `sort: - property: / direction:`, view-level `filters`, `columnSize`, `indentProperties`.
2. One note per row; put every displayable/scorable value in frontmatter, including a tag used only by the base filter (`tags: - <库名>`). The hub/index note must NOT carry that tag or it shows up as a row.
3. **Numeric fields unquoted and camelCase**: `mDomain: 5`, never `"5"` (string) and never `m-domain` (the hyphen parses as subtraction inside a formula).
4. Reference non-ASCII property names as `note["闭环"]`, never bare — keep formula identifiers ASCII.
5. Derive ranking in a formula (weighted sum → nested `if()` for the bucket), and keep a manual `否决: ""` string field so an excluded row is forced out of the top bucket **without faking its score**. Never hard-code a composite number that contradicts the per-dimension fields.
6. One view per question the user will ask (all rows by score, one region, top bucket, dimension spread, excluded-with-reason, still-to-verify), each with its own `filters` + `sort` + `summaries`.
7. **Validate before reporting done**: `yaml.safe_load` the `.base` and the frontmatter of every row note; assert required fields exist, numeric fields are `int`, the filter tag is present, and print the computed ranking + row count. Then name the one runtime dependency — Bases is a core plugin and must be enabled in that vault, or the embed renders nothing.

## Depth

Syntax details (implicit `value`/`acc` list functions, `number()`/`contains()` pitfalls), the `file.backlinks` cross-note hatch, summary YAML, a worked `%Culture2Purification%.base` example, the Dataview fallback for per-row rollups, and a from-scratch row-per-note table base recipe (frontmatter schema, ranking formula, per-view filters, validation script): `references/bases-formulas.md`.