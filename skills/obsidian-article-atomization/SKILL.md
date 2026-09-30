---
name: obsidian-article-atomization
description: "Atomize articles into an Obsidian vault as linked notes."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [obsidian, note-taking, atomization, vault, wikilinks]
    related_skills: [obsidian, web-content-extraction]
platforms: [macos, linux, windows]
---

# Obsidian Article Atomization

## When to Use

- User shares an external article (WeChat 公众号 post, web long-read) and asks to 整理/原子化 it into the Obsidian vault, linked to existing notes ("把这个 post 整理到知识库中，注意原子化并与原有的知识库联系到一起").
- User's vault is `wangfanlin1` (rules in its root `README.md`, read it first).

The user's definition of success: the article becomes **multiple small atomic notes** (one concept per note) that **link into the existing note graph** — NOT one mega-note dump, and NOT orphan notes.

## Workflow (execute in this order)

### Step 1 — Extract the full article text
- `web_extract` on mp.weixin.qq.com returns only the title with empty content (JS-render signature). Go straight to curl + `#js_content` parse — see skill `web-content-extraction` Tier 3 for the exact script (paragraph-preserving version).
- Save HTML to a temp file (`/tmp/wechat_article.html`), parse with Python. Extract title via `var msg_title`, body from `<div id="js_content">...</div><script`.

### Step 2 — Survey the vault BEFORE planning
- Find the CLC folder for the topic (e.g. protein-stability → `Q51 蛋白质`). The README's "给 Hermes Agent 的写入规则" + `🗂️ Classifications.md` decide placement: 学科知识 → Classifications, 软件 → TP317/database.
- Search the target folder for EXISTING notes the article should link to or merge into (e.g. `Interactions in terms of proteins` hierarchy already had 氢键/盐桥/疏水 notes).
- **CRITICAL — check for the folder-note pattern**: this vault keeps many concept notes as `Topic/Topic.md` (folder containing a same-named md). Before planning to create `X.md`, run `terminal ls` on the parent dir — a `search_files(target="files")` glob can silently return 0 hits for names containing CJK/π/emoji (`*π*` missed an existing `蛋白质中涉及π体系的相互作用/蛋白质中涉及π体系的相互作用.md`). Never declare a note absent on glob alone.

### Step 3 — Present the atomization plan, WAIT for confirmation
- Multi-file writes to this vault require explain-first (strong user preference — see `obsidian` skill "Multi-file writes: Explain first"). Present a table: new notes (path + purpose), existing notes to supplement, link targets to update.
- Use `clarify` with options; do NOT proceed on silence.

### Step 4 — Backup, then write
- `cp` every existing `.md` you will modify to `<name>.backup.md` beside it, BEFORE editing.
- Re-read each file right before rewriting (user edits between sessions; never patch from stale content).
- New notes: use folder-note pattern when the concept is an entity (`Van der Waals force/Van der Waals force.md`), matching siblings.
- If a same-named folder already exists: DELETE any sibling you created and MERGE content into `Folder/Folder.md`, preserving the original frontmatter/body.
- Existing notes: keep original structure (frontmatter, MEMOS dataview, images) and APPEND a clearly-marked new section (e.g. "研算录视角" / case sections), never gut the original.

### Step 5 — Verify after all writes
- Confirm every file exists (`ls`/stat).
- **Wikilink verification**: run a script that (a) collects every `*.md` basename in the vault, (b) extracts `[[...]]` targets from the new/edited files, (c) reports targets that don't resolve. See `scripts/verify_wikilinks.py`.
- Distinguish `![[embeds]]` (images like `Pasted image ...`) from `[[wikilinks]]` — the verifier must skip `![[` embeds, else false positives.
- Link targets must be note basenames, NOT folder names (`[[(GROMACS) File - .cpt]]` not `[[(GROMACS) File > .cpt]]`). Fix broken links you introduced before reporting done.

## Pitfalls

1. **Folder-note collision** (real incident): planned `蛋白质中涉及π体系的相互作用.md` as a flat sibling; the vault already had it as `Folder/Folder.md`. Result: duplicate file, had to `rm` + merge. Always `ls` the parent dir first.
2. **`search_files` glob misses CJK/π/emoji filenames** — returned 0 for an existing file. Verify existence with terminal `ls`/`find` when the glob comes back empty.
3. **Wikilink to a folder name, not a file** — Obsidian links resolve to note files; a folder (`(GROMACS) File > .cpt`) with a different internal file (`(GROMACS) File - .cpt`) silently breaks.
4. **Whitespace-collapsing extraction** — flattening the article with `\s+ → ' '` destroys paragraph structure; convert `</p></section><br>` to newlines first (see web-content-extraction).
5. **Skip `![[Pasted image...]]` in link checks** — image embeds are not broken links.
6. **Don't overwrite from memory** — re-read files immediately before patching; the user edits notes between sessions.

## User conventions (wangfanlin1 vault)

- Hub/source note for the article (title, 公众号, URL, reading date) + atomic concept notes + link updates to existing hubs (`Interactions in terms of proteins`, `🧩 p53`, etc.).
- Existing notes carry YAML frontmatter with `aliases`, `parents:` (wikilinks), `tags`; MEMOS notes use dataview blocks that must be preserved verbatim.
- `.base` files are embedded via `![[X.base]]` — keep them.
