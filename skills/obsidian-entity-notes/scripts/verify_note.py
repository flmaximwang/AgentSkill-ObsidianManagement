#!/usr/bin/env python3
"""Verify an Obsidian note after writing it.

Checks, in order:
  1. frontmatter parses as a YAML mapping (degrades to a light key/indent check when PyYAML
     is not importable)
  2. folder-note convention: filename == parent folder name (warning only)
  3. every [[wikilink]] in the note resolves to a real .md file somewhere in the vault
  4. prints the '# ' section list and the line count

Usage:
    python3 scripts/verify_note.py "<note path>" --vault "<vault root>"
    uv run --quiet --with pyyaml python3 scripts/verify_note.py "<note path>"   # no PyYAML locally

Exit code 0 = clean, 1 = unparsable frontmatter or an unresolved wikilink.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_VAULT = "~/Documents/Obsidian/wangfanlin1_Knowledge"
SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules", "assets", "attachments"}
LINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def split_frontmatter(text: str):
    """Return (frontmatter or None, body)."""
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def check_frontmatter(fm):
    problems = []
    if fm is None:
        return ["no YAML frontmatter block (--- ... ---) at the top of the file"]
    try:
        import yaml  # type: ignore
    except ImportError:
        print("! PyYAML not importable -> light check only "
              "(re-run with: uv run --quiet --with pyyaml python3 ...)")
        for line in fm.splitlines():
            if not line.strip():
                continue
            looks_like_entry = re.match(r"^[A-Za-z0-9_.\-]+:\s*", line)
            looks_like_continuation = line.startswith((" ", "\t", "- ", "#"))
            if not (looks_like_entry or looks_like_continuation):
                problems.append(f"line is neither a key nor a list/indent continuation: {line!r}")
        return problems
    try:
        data = yaml.safe_load(fm)
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        return [f"YAML parse error: {exc}"]
    if not isinstance(data, dict):
        problems.append(f"frontmatter parsed as {type(data).__name__}, expected a mapping")
    return problems


def index_vault(vault: Path) -> set:
    names = set()
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                names.add(f[:-3])
    return names


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("note", help="path to the .md note just written")
    ap.add_argument("--vault", default=DEFAULT_VAULT,
                    help="vault root used to resolve wikilinks")
    args = ap.parse_args()

    note = Path(os.path.expanduser(args.note))
    vault = Path(os.path.expanduser(args.vault))
    if not note.is_file():
        print(f"FAIL: note not found: {note}")
        return 1
    if not vault.is_dir():
        print(f"FAIL: vault root not found: {vault}")
        return 1

    text = note.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)

    problems = check_frontmatter(fm)
    print(f"note      : {note}")
    print(f"lines     : {len(text.splitlines())}")
    if fm is not None:
        keys = re.findall(r"^([A-Za-z0-9_.\-]+):", fm, re.M)
        print(f"frontmatter keys: {keys}")

    if note.parent.name == note.stem:
        print("folder    : OK (folder-note convention)")
    elif note.parent.name != "NOTES":
        print(f"folder    : note (filename {note.stem!r} != folder {note.parent.name!r}; "
              "fine for legacy bare notes, otherwise use folder + same-name note)")

    sections = [ln.strip() for ln in body.splitlines() if ln.startswith("# ")]
    print(f"sections  : {sections}")

    targets = []
    for m in LINK_RE.finditer(text):
        target = m.group(1).split("|")[0].split("#")[0].strip()
        if target:
            targets.append(target)
    uniq = sorted(set(targets))
    index = index_vault(vault)
    missing = [t for t in uniq if t not in index]
    print(f"wikilinks : {len(targets)} total, {len(uniq)} unique, {len(missing)} unresolved")
    for t in missing:
        print(f"  MISSING [[{t}]]")

    if problems or missing:
        for p in problems:
            print(f"  PROBLEM {p}")
        print("RESULT: NEEDS FIX")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
