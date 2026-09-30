---
name: obsidian-howto-notes
description: Use when writing a how-to note for a tool in the vault.
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [obsidian, notes, vault, documentation, howto]
    related_skills: [obsidian, obsidian-entity-notes]
---

# How-to / tool-documentation notes in the vault

Companion to the bundled `obsidian` skill — load that one first for vault path resolution, the
README-first placement rule, and the multi-file explain-first gate. This skill carries the shape required
for a note that documents **how to do something with a tool**: install / configure / maintain, or the set
of alternative routes that lead to the same result.

## When to Use

- The user asks to record a procedure for a tool in the vault ("把具体的步骤记录到 Obsidian").
- He asks to **restructure** an existing procedure note — "重新组织你的笔记" plus a pasted skeleton.
- He pastes a command error and the diagnosis should land in the note.

Not for: entity/family research notes (→ `obsidian-entity-notes`), bench protocol SOPs, MEMOS records,
TP393 protocol notes — those have their own type sections in the bundled `obsidian` skill.

## Step 1 — locate the folder, mirror a live sibling and the parent note

- **Re-resolve the note's path every session — and again immediately before each write and before the commit; never reuse one remembered from an earlier session.** A reorganization pass or a sync client can move the note **between two calls of the same task**: it moved while an edit→commit pair was in flight, and only the deletion of the old path reached git.
  The vault is reorganized between sessions — letter-bucket passes move a procedure note to
  `…/<TP-code>/<Letter>/<Title>/<Title>.md`, and a folder-note conversion adds a level of depth — so the
  file has moved while its content is untouched. Glob on the filename prefix
  (`[p for p in vault.rglob("*.md") if p.name.startswith("<Title>")]`) and reuse the **exact string the
  glob printed**: these paths carry emoji and parentheses, and retyping one into a shell one-liner can
  mangle the emoji's variation selector into a phantom `FileNotFoundError`. Patching the remembered path
  instead silently creates a second copy of the note at the stale location.
1. Read `<vault_root>/README.md` for the placement rules; the target is usually a tool folder under a CLC
   code (e.g. `…/TP317 程序包（应用软件）/database/<Tool>/`).
2. Read **one or two existing notes in that folder** and copy their frontmatter fields literally — tags,
   `parents`, `abstract`/`keywords`. The user renames tags over time (tool/documentation notes carry
   `Memos/Documentations`), so a type-reference file may be one rename behind the live convention.
3. If the folder has a parent tool note (`(<Tool>).md`), link the new note to it with `parents: [[<Tool>]]`
   and add the reverse link in the parent.
4. Substantial notes on one topic get their **own file**, not an append into a `.base`/overview note — an
   overview holds the pointer, the procedure holds the detail.

## Step 2 — the skeleton (one per route/topic, four parts, in this order)

```
## <路径 / 主题>          ← one section per install path, mode, or variant
简介、适用范围             ← 1–2 lines: what it is, when it applies
### 安装流程              ← ordered, directly runnable steps
### 维护流程              ← same rule
### FAQs                   ← the detail lives here, as an unordered list
```

- **Each step carries at most one sentence of explanation**, and the steps run in order with no
  side-reading — the same discipline as protocol steps.
- **The FAQs are a `-` bullet list, one point per bullet.** Measured command output, error texts,
  mechanisms, caveats and "how do I find X" answers all go there — never into the step lists.
- **Per-route detail never sits in a cross-cutting section.** Distribute each pitfall into the FAQ of the
  step it affects; keep only genuinely shared material as its own top-level section (policy or decision
  tables, on-disk state layout, which command governs what).
- **When the answer depends on a classification, the classification comes first.** If the note maps
  "input X → form Y" but Y is fixed by which *class* X belongs to, the reader must be able to place their
  own case before any mapping appears: `## <标题>`, a one-line intro, then the classification section,
  then **one `###` per class** (`### 类型 1 的换算：<短名>`, `### 类型 2 的换算：<短名>`, …). A flat list of
  forms with the classes buried mid-section gets sent back — build the class-first skeleton in the first
  draft, and give every class heading the class's short name, not just a number.
- **A "how do I tell which class this is" section splits into two subsections: GUI evidence, then the
  command.** First what the reader sees on the page (which lists to open, which in-page search finds the
  whole tree), then the one-liner plus the judgement table and real output
  (`### 根据仓库的文件树分辨仓库类型` / `### 使用 gh 命令分辨仓库类型`). The reader who has no terminal must be able
  to classify without one.
- **End the section with the cases that fall out of the mapping** — a tail subsection for fallbacks and
  for symptoms that look like "X does not exist" while the cause is something else. Those misdirections
  do not belong inside any class table.

## Step 3 — evidence discipline

- Every command, flag and path inside a step must be one that was **actually run** (or read out of the
  installed source). A note that tells the user to run an untested command is worse than no note.
- Mark inferred mechanisms as inference ("机制推断，未实测") instead of stating them as measured behaviour.
- Paste **real** output into the FAQs — file inventories, sizes, status words, error strings. Placeholders
  inside commands (`<owner>/<repo>`) are fine; invented output is not. Run the command in the same step
  that pastes its output: a block assembled from recall reads as measured data and will contradict the
  tool (a guessed tree listing named sibling directories that do not exist). If one slipped in, re-run the
  commands and replace the whole block — do not leave a corrected line beside the invented ones.
- When a route has a known trap, say which artifact the trap produces (e.g. a skill that installs with
  its referenced files missing) rather than vaguely warning about it.
- **A later measurement that disproves an earlier bullet rewrites that bullet** — edit the sentence in
  place and state inside it what the first version claimed wrongly. Never leave the wrong claim and a
  corrective addendum side by side; a reader takes the first one.

## Step 4 — verify after writing

- **Back up before a rewrite**: `cp -p <note>.md <note>.md.bak-YYYYMMDD` (the vault's own convention).
- **A note that was only `patch`ed cannot be rewritten with `write_file` in the same session** — the
  stale-write guard requires a full `read_file` of the current file first, and content quoted earlier or
  read in part does not count. Read every page before a restructure, or keep editing with `patch`.
- Check the skeleton structurally: every `##` route/topic section carries all four parts (scope line +
  `### 安装流程` + `### 维护流程` + `### FAQs`), frontmatter parses, and every `[[wikilink]]` resolves to a
  real `.md`. A short throwaway script is faster and more reliable than eyeballing 300 lines.
- Report the real numbers (line count, sections, links checked) instead of "note written".

## Step 5 — commit only this note

The vault is a git repo and a documentation round ends with "记录到 Obsidian 文档并 commit".

1. `git -c core.quotepath=false status --porcelain` first. The vault is routinely mid-reorganization:
   letter-bucket moves appear as ` D` deletions plus a few untracked directories, and an organize run
   leaves `*_conflict_current/` folders next to the originals. Those are the user's to commit per
   category — report their count and leave them staged-free.
2. Commit **only the note you touched**: the path must be the one the glob printed (emoji + parentheses),
   so `git add -- "<path>"`, confirm the staged list is a single file, then
   `git commit -m "docs(<tool>): …"`.
3. **A note under a committed vault is tracked and modified**, not untracked: expect ` M` on it and stage
   it by path. Verify with `git log -1 --stat` — **one file changed *and* a diff carrying insertions**. A
   pure `N deletions(-)` means the note moved between your write and the `git add`: the commit recorded
   only the old path's removal while the moved copy sits untracked at its new location — content intact on
   disk, history reading as data loss. Recover by re-globbing the note and either moving it back or staging
   its new path, then `git commit --amend` (the vault has no remote, so there is no shared history to
   rewrite). Re-check `git status` — the note must no longer appear at either path.
4. Reuse the repo's existing message prefixes (`docs: …`, `chore(<scope>): …`) rather than inventing one.
