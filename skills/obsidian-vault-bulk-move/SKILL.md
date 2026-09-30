---
name: obsidian-vault-bulk-move
description: Use when bulk-moving hundreds of folders in a git vault.
---

# Bulk folder reorganization in a git-tracked vault

Use for: re-filing hundreds of classification folders into buckets, renaming tiers, any mass
`mv` inside a vault that is also a git repo.

## Non-negotiable sequence

1. **Snapshot**: `git add -A && git commit` and record the hash. Tell the user the rollback
   command (`git reset --hard <hash>`) before starting.
2. **Dry-run**: compute the full mapping (source -> target) in memory, render the target tree,
   assert invariants (no duplicate targets, every item placed exactly once, bucket limits).
3. **Create every target parent directory first** (`mkdir -p` for *all* bucket paths), *then*
   move items. Otherwise the first item destined for a not-yet-existing bucket gets **renamed
   into the bucket** (`shutil.move(src, dst)` renames when `dst` is absent) and later items land
   as its children - silent structural corruption.
4. **Move, then verify against the computed tree**, not by eyeballing: for every expected bucket
   node compare `set(os.listdir(bucket))` with the expected children set; count items placed;
   count dirs/files before vs after.

## Failure modes that lose data

- **Never use `git reset --hard` to undo a move-based reorganization.** git only restores
  *tracked* files: moved-away copies stay behind as untracked duplicates, and files matched by
  `.gitignore` (pasted images, PDFs, .tsv) are **not restored at all** - they stay orphaned at
  the new path while the tracked files come back at the old one, splitting folders in two.
  To roll back a move, roll back the moves themselves (use the computed mapping backwards).
- **Reconciliation scripts must compare canonical paths.** If you verify "old path" vs
  "new path" to decide which copy to delete, an item whose bucket path *equals* its current
  parent (e.g. bucket `A` contains item `A/...`) yields `old == new` - the check passes and you
  delete the item itself. Guard with `os.path.realpath(old) == os.path.realpath(new) -> skip`
  and list such items explicitly before deleting anything.
- **Destructive steps (rmtree/rm) need user approval**; a blocked script is not consent, and
  do not re-run it through another tool to dodge the prompt.

## Verification that actually proves no loss

The only ledger for the vault is git, and it misses gitignored files:

```bash
# tracked content: blobs present in snapshot but absent now -> real loss
git ls-tree -r -z <snapshot> -- <dir>     # mode sha\tpath
git ls-files -s -z -- <dir>              # after `git add -A`
```
Compare blob SHAs (content-based) - path comparison gives false positives for renames.
For attachments (.png/.pdf/.excalidraw, often gitignored): scan every restored note for
`![[...]]` embeds and test basename presence **with and without `.md`** (Obsidian embeds
`X.excalidraw.md` as `X.excalidraw`). Report the lost-attachment count per affected folder; it
cannot be recovered from git, so check Time Machine / iCloud / vault `.trash` immediately.

## Pitfalls

- `git status` hides content edits on files that were moved (they show as untracked at the new
  path), so a clean `git status` is **not** evidence the working tree matches the commit.
  Obsidian rewrites links when folders are renamed; those edits live only in the working tree.
- `git status --ignored --porcelain` counts ignored *directories* as one entry; add `-uall` for
  a file-level count. Compare like with like.
- Emoji/quoted paths: parse git output with `-z` and NUL splitting, never `sed`/escaping.
- Verify final invariants numerically (root holds only buckets + known strays; every bucket
  <= limit; every item exactly once) and give the user those numbers.
