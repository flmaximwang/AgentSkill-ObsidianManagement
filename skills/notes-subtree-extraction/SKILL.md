---
name: notes-subtree-extraction
description: Use when extracting a notes subtree into a new git repo.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [obsidian, git, migration, bulk-move, vault]
    related_skills: [obsidian-vault-bulk-move, obsidian]
---

# Extracting a notes subtree into a new vault / git repo

## When to Use

- "把 X 文件夹整理到一个新的 git 仓库" / "move folder X out of vault A into new repo B".
- A notes subtree has to change shape (A-Z / topic buckets, one folder per entity) **and** land
  in a different repository, so the destination needs its own commit and its own link integrity.
- Also load `obsidian-vault-bulk-move` (user-owned) for the in-vault mechanics; this skill adds
  the cross-repo gates.

Use for: "take folder X out of vault/repo A and organise it into a new repo B" - letter or topic
buckets, one folder per entity, attachments and binaries travelling with their notes.

Related: `obsidian-vault-bulk-move` (user-owned) covers re-bucketing *inside* one vault - its
rollback/ledger mechanics apply here too. This skill is the cross-repo case, plus the traps that
only fire when you commit into a second repository.

## Standing rules

1. **Recon, then one clarify call.** Census the source (shape, extensions, weight, asset dirs),
   read the destination's README/`git log`/`git status`, then ask the 3-5 decisions that change
   the work - source moved or copied, bucket key, binaries in or out, destination standalone
   vault, remote/LFS. Recommended option first. Do not start moving before they are answered.
2. **Filing is metadata work, not reading work.** Decide placement from path, filename and
   frontmatter (`tags:` / `aliases:` / `parents:`). Never read note bodies to classify, never
   edit note content as part of a move (button/template paths, `parents:` links) - list those as
   follow-ups. A classification script plus a commit is the deliverable.
3. **Re-read the destination's README/plan before the final verification and before committing.**
   The user edits it while you migrate (bucketing rules, layout conventions). Patch or append;
   never overwrite a README they wrote.
4. **Stage explicit pathspecs in the destination repo.** `git add -A` folds the user's
   pre-existing uncommitted work (unrelated renames, stray binaries, `.gitignore` edits) into
   YOUR commit. If it already happened: `git reset --soft HEAD~1` -> `git reset -- <unrelated
   paths>` -> re-commit your paths -> leave their work-in-progress pending exactly as found,
   never committed under a message that does not describe it.
5. **Reconcile before deleting the source**: source files minus junk (`.DS_Store`, `.trash`) must
   equal the destination's file count, extension by extension. Only then `rm` the emptied tree.
6. **Three assertions afterwards**: no directory contains a child directory of the same name
   (double-nesting); tracked-vs-on-disk file sets are equal after NFC normalisation; the
   outbound-link cost is quantified (see below). Report all three as numbers.
7. **Purge the source history last, and only behind proof.** `git filter-repo` on the source repo is
   the final step, gated on (a) byte-level proof that the destination holds every file the source
   ever committed, and (b) the user's uncommitted work protected first. Never purge before the
   destination is verified. Recipe: `references/history-purge-filter-repo.md`; for a purge that does
   not follow a migration (or when the path has several historical prefixes) use `git-history-purge`.

## Sequence (as executed)

```bash
# source census
find <SRC> -maxdepth 2 | head -50
find <SRC> -type f | awk -F. '{print $NF}' | sort | uniq -c | sort -rn
find <SRC> -type d -name '*_assets' | wc -l && du -sh <SRC>
# destination state
cd <DST> && git log --oneline && git status --short && cat README.md
```

Write one script that: classifies every top-level entry from frontmatter, resolves product ->
owner, computes `bucket/entity/` targets, prints the plan per entity, and only acts with
`--apply` (`DRY = "--apply" not in sys.argv`). Run the dry run, read the plan, then apply.

Bucket key for CJK names - pinyin initial, no install needed:

```bash
uv run --with pypinyin --quiet python -c "from pypinyin import lazy_pinyin, Style; \
print(lazy_pinyin('安琪酵母', style=Style.FIRST_LETTER))"   # ['a','q','j','m']
```

`[0]` is the bucket, the whole list gives successive sub-buckets (`A` -> `AQ` -> `AQJ` -> `AQJM`)
when a bucket exceeds the user's limit. Latin names take their first ASCII letter. Print
per-bucket counts and the largest bucket in the report so the reader sees whether the split rule
bit (a maximum under the limit means no sub-buckets are needed *yet*).

Product-to-owner resolution order: exact folder name -> owner note's `aliases:` (brand prefix,
e.g. `(Cobetter)` -> 科百特) -> unique `startswith` match (`(上海纳洛捷)` -> 上海纳洛捷生物科技有限公司).
Report unresolved owners instead of guessing. Non-entity notes (shopping lists, misc) go to the
repo root, not into a bucket - flag that placement as a judgement call.

## Verification

```python
tracked = set(subprocess.run(["git","-C",DST,"ls-files","-z"],capture_output=True,text=True)
              .stdout.split("\0")) - {""}
walk = {os.path.relpath(os.path.join(r,f), DST)
        for r,ds,fs in os.walk(DST) if ".git" not in r for f in fs}
norm = lambda p: unicodedata.normalize("NFC", p)
assert {norm(p) for p in tracked} == {norm(p) for p in walk}
```

Outbound-link audit: resolve every `[[target]]` against the destination's basename set (match
both `name` and `name.ext`; strip `|alias` and `#heading`), then split unresolved targets into
*stayed behind in the source vault* vs *already dangling before the move*. Quote both instance
counts; offer to copy the stayed-behind notes over or leave them as stubs.

## Pitfalls

- `shutil.move(src_dir, dst)` **nests** `src_dir` inside `dst`. Pass the parent
  (`os.path.dirname(dst)`) or move `src/*`. A destination folder sharing the source's name gains a
  silent duplicate level; the same mistake hits a catch-all folder (`template/` ->
  `template/template/`). Detect with one pass over `find <root> -mindepth 2 -type d` comparing
  basenames, fix it before committing, and commit the correction separately - a nesting bug of
  that size is invisible in a diff and does not surface as data loss until much later.
- Comparing `git ls-files` with an `os.walk` listing shows phantom differences on macOS for
  accented names (`ÄKTA`): git stores NFD, the filesystem returns NFC. Normalise before believing
  anything is missing; do not go hunting for files that are present.
- Emoji / quoted paths: parse git output with `-z` and NUL splitting instead of text munging; verify
  with a set comparison instead of shell loops.
- Report the binary inventory separately from the notes (`.md` per entity vs images/PDF/xlsx) - the
  user tracks whether datasheets and order forms came along, not just the notes.
- A migration that reports "done" without per-bucket counts, commit hashes and the link-audit
  number is not finished; those figures are the deliverable's proof.
- Comparing a worktree against a commit with a rebuilt tree needs the temp index **seeded**:
  `GIT_INDEX_FILE=$T git read-tree HEAD && GIT_INDEX_FILE=$T git add -A && GIT_INDEX_FILE=$T git
  write-tree`. With an empty index, `git add -A` skips files that are tracked *and* match
  `.gitignore`, so the rebuilt tree looks short and you chase a mismatch that is not there.
- Do not diagnose from collapsed or quoting-mangled git output: `git status --porcelain` reports a
  wholly untracked directory as a single `??` entry (hundreds of files behind one line), and after a
  `reset` a `git diff <commit>` reads as mass deletion because it is measured against the index.
  Decode with `-z`, check existence on disk, and compare trees before raising an alarm.
- A filter command that exits non-zero on zero matches kills an `&&` chain and silently skips every
  check after it (`grep -c` on git output is the usual culprit) - the classic symptom is a
  verification block whose output stops halfway. Join shell checks with `;` and re-run the tail
  instead of trusting a truncated block.
- Flattening a duplicate level (or any depth change) is safe *because* Obsidian refs are path-free -
  confirm that first: count `!?\[\[` refs against local markdown links. A single relative `](path)`
  reference breaks on flattening, so preserve the depth for that folder instead.

See `references/subtree-to-new-vault.md` for the classification recipe, audit code and report shape,
and `references/history-purge-filter-repo.md` for removing the extracted path from the source history.
