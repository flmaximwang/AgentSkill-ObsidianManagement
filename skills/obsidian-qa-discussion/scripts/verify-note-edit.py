#!/usr/bin/env python3
"""Verify an Obsidian note edit against its backup, and resolve every link/embed.

Usage:
    python3 verify-note-edit.py <vault_root> <note.md> [<backup.md>]

Run this after EVERY note modification. It replaces the old eyeball checks
("ls the directory, read the note back") with four checks that actually fail
loudly:

  1. YAML frontmatter parses.
  2. Line-set diff vs the backup: every line that DISAPPEARED is printed, and
     each one must be a line you deliberately rewrote. A bare "all original
     lines still present" test is useless here -- a corrected heading is a
     legitimate deletion, so the boolean goes False on a correct edit and
     cannot tell a deliberate rewrite from silent data loss.
  3. Every [[wikilink]] resolves to a real .md somewhere in the vault.
  4. Every ![[embed]] resolves on the filesystem, tested note-relative AND
     vault-relative (Obsidian accepts both). Kept separate from check 3 on
     purpose: a resolver globbing name + ".md" reports every ![[assets/x.png]]
     as broken, and an asset path is not a note name.

Exit status: 0 if clean, 1 if any check failed (safe to gate on).
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

WIKILINK = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
EMBED = re.compile(r"!\[\[([^\]|]+)")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2

    vault = Path(argv[1]).expanduser().resolve()
    note = Path(argv[2]).expanduser().resolve()
    bak = Path(argv[3]).expanduser().resolve() if len(argv) > 3 else None
    new = note.read_text(encoding="utf-8")
    ok = True

    print(f"note:  {note}")
    print(f"vault: {vault}\n")

    # --- 1. frontmatter -------------------------------------------------
    if new.startswith("---"):
        parts = new.split("---", 2)
        if yaml is None:
            print("[1] frontmatter: SKIPPED (pyyaml not installed)")
        else:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                print(f"[1] frontmatter OK, keys={list(fm)}")
            except Exception as exc:
                ok = False
                print(f"[1] frontmatter PARSE FAILED: {exc}")
    else:
        print("[1] no frontmatter block (fine for non-Memo notes)")

    # --- 2. line-set diff -----------------------------------------------
    if bak and bak.exists():
        old = bak.read_text(encoding="utf-8")
        missing = [l for l in old.splitlines() if l.strip() and l not in new]
        added = [l for l in new.splitlines() if l.strip() and l not in old]
        print(f"[2] vs {bak.name}: +{len(added)} lines, -{len(missing)} lines")
        if missing:
            print("    DISAPPEARED -- each line below must be one you MEANT to remove:")
            for l in missing:
                print("      !", l[:140])
        else:
            print("    nothing removed (pure append)")
    else:
        print("[2] no backup given -- skipped; pass the .bak path to enable")

    # --- 3. wikilinks ---------------------------------------------------
    links = sorted({m.split("|")[0].split("#")[0].strip()
                    for m in WIKILINK.findall(new)})
    unresolved = [n for n in links if not list(vault.rglob(n + ".md"))]
    print(f"[3] wikilinks: {len(links)} distinct, {len(unresolved)} unresolved")
    for n in unresolved:
        print(f"      ! [[{n}]] -- no {n}.md in the vault")
    if unresolved:
        ok = False

    # --- 4. embeds ------------------------------------------------------
    for m in sorted({e.split("|")[0].strip() for e in EMBED.findall(new)}):
        rel = (note.parent / m).exists()
        root = (vault / m).exists()
        print(f"[4] embed {m!r}: note-relative={rel}  vault-relative={root}")
        if not (rel or root):
            ok = False
            print("      ! UNRESOLVED -- the embed will render as a broken link")

    print("\nRESULT:", "OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
