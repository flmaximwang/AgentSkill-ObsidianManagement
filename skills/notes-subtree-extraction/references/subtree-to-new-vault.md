# Subtree extraction recipe (notes vault -> new git repo)

Worked recipe for: classify a heterogeneous notes folder into buckets in a new repo, carry
attachments, commit, and prove nothing was lost. Verified on a 110-entity / 791-file extraction.

## 1. Classify from frontmatter, in one pass

Split top-level entries by tag instead of reading bodies:

- entity folders (dir whose name is the entity),
- flat entity notes (tag `Memos/<Entity>`, note only, no folder yet),
- entity folders that are only a *product* container (`(Owner) Product/`),
- nested asset dirs (`..._assets/`, `..._files/`) - never standalone buckets,
- non-entity notes (shopping lists, template notes) - repo root.

Shape out of that: every entity becomes `Letter/Entity/` holding `Entity.md` plus its
`(Entity) Product.md`, `_assets/` and product subfolders. A flat entity note therefore gains a
folder; a folder named after its parent (`Entity/Entity/`) is flattened one level.

Owner resolution for `(Prefix) Product`: exact name -> owner note `aliases:` -> unique
`startswith`. Keep unresolved owners visible in the dry run.

## 2. Script skeleton

```python
DRY = "--apply" not in sys.argv
# 1 classify -> entities / products / strays
# 2 resolve product prefixes -> owners
# 3 plan = {dest_dir: [sources]}
# 4 print plan per bucket if DRY else:
#     os.makedirs(dest)
#     shutil.move(s, os.path.dirname(dest)) if isdir(s) else shutil.move(s, dest)
```

The `dirname` on directory sources is the whole trick - see the pitfalls in SKILL.md.

## 3. Reconciliation ledger

- source file count minus junk (`.DS_Store`, `.trash`) == destination file count;
- extension census must match, so binaries (pdf/xlsx/docx/images) are proven to have travelled;
- count notes separately (`.md`) for the report.

## 4. Link audit (the cost of splitting a vault)

```python
names = {os.path.splitext(os.path.basename(f))[0] for f in files} | {os.path.basename(f) for f in files}
unres = collections.Counter()
for f in md_files:
    for link in re.findall(r"!?\[\[([^\]]+)\]\]", open(f, encoding="utf-8", errors="replace").read()):
        tgt = link.split("|")[0].split("#")[0].strip()
        if tgt and tgt not in names: unres[tgt] += 1
```

Before moving, also count link *styles*: `!?\[\[` (path-free, survives any reshape) vs
`\]\([^)]+\)` markdown links to local files (break when depth changes). Report the ratio.

After moving, classify the unresolved targets: present elsewhere in the SOURCE vault (broken by
the split) vs absent there too (already dangling). Also flag vault-absolute links (targets
containing `/`) - those are broken by definition once the path changes.

## 5. Report shape

1. entities / buckets / per-bucket counts / largest bucket;
2. files moved, notes vs binaries, bytes, commits with hashes, working tree clean, remote state;
3. judgement calls for veto: where strays went, alias/prefix resolutions, flattened duplicates;
4. follow-ups: stale template/button paths still pointing at the old vault, notes whose
   `parents:` lack the new owner link (the owner's dataview will not list them), outbound link
   count, remote still to be created, whether to keep the classification script in the repo.
