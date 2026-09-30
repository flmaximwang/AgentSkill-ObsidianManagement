#!/usr/bin/env python3
"""Verify all [[wikilink]] targets in new/edited Obsidian notes resolve.

Usage:
    python3 verify_wikilinks.py <vault_root> <file1.md> [file2.md ...]

- Collects every *.md basename in the vault (plus *.base files, which are
  valid ![[embed]] targets).
- Extracts [[...]] targets from each listed file.
- Skips ![[ embeds (images/attachments like "Pasted image ...").
- Skips alias/heading suffixes via the [^\]\|#]+ character class.
- Reports targets that don't resolve; exit 1 if any broken link found.

Known false-positive note: `![[Pasted image ...]]` embeds inside a file are
NOT broken links even though the basename check fails — they're images whose
files live in an assets/ subfolder. The script strips the leading `!` before
parsing so embeds are correctly skipped.
"""
import os
import re
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    vault = sys.argv[1]
    files = sys.argv[2:]

    # Basenames of every note and embed target in the vault
    all_names = set()
    for root, _, fnames in os.walk(vault):
        for fn in fnames:
            if fn.endswith((".md", ".base")):
                all_names.add(os.path.splitext(fn)[0])

    broken = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            content = fh.read()
        # [[...]] — skip embeds (![[) and strip alias/heading suffixes
        for target in re.findall(r"(?<!\!)\[\[([^\]\|#]+)", content):
            target = target.strip()
            if target and target not in all_names:
                broken.setdefault(os.path.basename(f), []).append(target)

    if broken:
        print("Broken links found:")
        for f, targets in broken.items():
            print(f"  {f}: {sorted(set(targets))}")
        return 1
    print("OK: all wikilink targets in the checked files resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
