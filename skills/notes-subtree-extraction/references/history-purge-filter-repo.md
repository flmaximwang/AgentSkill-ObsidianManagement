# Purging an extracted subtree from the source repo's history

Trigger: "if you are sure everything is migrated, use filter-repo to delete X from history".
Two gates come first; the rewrite itself is one command.

## Gate 0 - prove the destination holds everything the source ever committed

```bash
git -C SRC ls-tree -r <last-commit-containing-PATH> -- "<PATH>"   # mode sha\tpath
git -C DST hash-object <every destination file>                    # blob sha of the new copy
```

Compare **blob-SHA multisets with counts**, never paths: re-bucketing changes paths, content does
not, so equal multisets are the byte-level proof the user is asking for. Two numbers to report:
blobs present in source history but missing from the destination (must be 0), and blobs present in
the destination but never in source history - those are exactly the files the source `.gitignore`
excluded (`*.pdf`, `*.xlsx`, `*.docx`, `*.pptx`, `*.key`, `*.mp4`). History cannot confirm them, so
rely on the on-disk census (count + extension inventory) taken **before** the source was deleted,
and say so in the report.

## Gate 1 - protect the user's uncommitted work

`git filter-repo` aborts on a dirty tree (its sanity check), but with `--force` it runs anyway and
then its cleanup executes `git reset --hard`, `git reflog expire --expire=now --all` and
`git gc --prune=now`. The `reset --hard` happens whenever the repo is non-bare and there is no
`--no-reset` flag, so on a vault the user is working in it silently reverts their pending deletions
and edits. Protect first, in this order:

1. `cp -al .git <outside-the-repo>/<name>.git.prefilter-<date>` - hardlink snapshot, instant,
   keeps the pre-rewrite packs alive. Validate later: `git --git-dir=<snap> fsck --connectivity-only`
   (exit 0; dangling-blob lines are normal) and `git --git-dir=<snap> log --oneline` (old tip present).
2. `git add -A && git commit -m "WIP(temp): pending state snapshot - restored by reset --mixed"` so
   the tree is clean and nothing can be reset away.

## Rewrite

```bash
git filter-repo --force --path "<PATH>" --invert-paths      # brew install git-filter-repo if missing
```

`--force` also bypasses the fresh-clone / single-remote checks. Point `--path` at the directory:
it covers everything beneath it. Rewriting 15 commits of a 3.8 GB repo took ~15 s.

## More than one historical prefix - check before you purge

`--path` does not follow renames, and a bucket reorganisation leaves the same folder under two
prefixes (`🗂️ Classifications/TH …` before the re-bucketing commit, `🗂️ Classifications/T/TH …`
after). A purge listing only one prefix leaves the old copies in history: grep the filtered repo for
the folder name (`git rev-list --objects --all | grep -ci "<marker>"`) and it is non-zero.
Enumerate every prefix by scanning each commit's tree (`git ls-tree -r <rev>` for every rev);
`git rev-list --objects --all` alone under-reports because it lists each blob once, at its *first*
path. Full procedure and recon script: skill `git-history-purge`.

## Rehearse and back up before touching the source

- Rehearse on a throwaway bare copy - `git clone --no-local --bare SRC $SCRATCH/rehearsal.git` - run the
  exact command there and verify it; the live repo stays untouched until the command is proven.
- APFS alternative to the hardlink snapshot: `cp -Rc SRC <backup-outside-repo>` (clonefile) is instant
  and costs no extra space; it diverges as the user keeps editing, so delete it after verification.
- `--force` skips filter-repo's fresh-clone / packed-repo sanity checks, so validate repo state
  yourself first (`git remote -v`, `git worktree list`, `git tag`, `git stash list`).
- Do not reach for `--dry-run` on a multi-GB repo: it writes the full fast-export stream for both the
  original and the filtered history (~2x repo size) into `.git/filter-repo/`.

## Restore the pending state

`git reset --mixed HEAD~1` - the WIP commit's content stays in the working tree while the index goes
back to the parent, so the user's pending changes reappear exactly as unstaged deletions / untracked
directories. The WIP commit stays in the object db as a dangling rescue handle until the next gc.

## Verify with numbers

```bash
git -C SRC ls-tree -r HEAD | shasum      # identical before/after -> nothing else was touched
git -C SRC rev-parse HEAD^{tree}         # unchanged OID (the tip no longer contained PATH)
git -C SRC log --all --oneline -- "<PATH>" | wc -l        # 0
git -C SRC rev-list --all --objects | grep -ci <name>     # 0
git -C SRC rev-list --count --all                         # commits kept / empty ones pruned
git -C SRC count-objects -vH | grep size-pack             # pack before vs after
```

The strongest pair is the first two: an identical `ls-tree` digest and an unchanged tip tree OID
prove the rewrite removed the path and nothing else. Also prove the purge is *reversible*: a purged
file's blob in the snapshot must equal the destination repo's copy -
`git --git-dir=<snap> rev-parse '<commit>^:"<PATH>/<file>"'` vs `git -C DST rev-parse HEAD:<new/path>`.

## Reporting honesty

- Reclaimed size reflects **committed** bytes only. When the source `.gitignore` excluded the heavy
  binaries, the pack shrinks by roughly the tracked bytes while the folder itself was far larger
  (e.g. 3.67 -> 3.54 GiB pack for a 218 MB folder). Say which, instead of implying the folder size.
- A hardlink snapshot stops sharing once `gc` replaces the packs, so it then costs its full size.
  State the number and hand over the `rm -rf <snap>` for reclaiming it.
- Rewriting history invalidates every existing clone: if the repo has a remote, force-push is
  required (state it); if it has none, say that too, so nobody assumes a push happened.
