#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""organize_notes.py - flatten + letter-index an Obsidian folder tree.

Turn a deeply nested note folder into a storage-friendly "database":

    <Target>/database/Deep/Nest/Note.md        becomes
    <Target>/<bucket>/<bucket2>/Note/Note.md   with  .index.<n>  markers

Buckets are cumulative prefixes of the note's sort key (level 1 = 1st char,
level 2 = first 2 chars, ...).  Any index folder holding more than --limit
notes is split again by the next character.

Cross-platform: macOS / Linux / Windows, Python 3.8+, standard library only.
CJK names are sorted by pinyin using the first adapter that works on the host:

    1. pypinyin            optional install, works on every OS
    2. macOS ICU           via osascript, zero install (same engine Finder uses)
    3. locale collation    glibc / Windows NLS, zero install
    4. codepoint fallback  CJK-initial names land in "_", flagged in the report

Safety
------
* dry-run by default: with no --apply nothing on disk is touched
* the full move plan is written to JSON and ``--rollback PLAN.json`` reverses it
* git alone is NOT enough: a vault .gitignore typically excludes .pdf/.pdb/.json
  inside the target, so those files have no version-control safety net

Examples
--------
    python3 organize_notes.py "/Vault/Some Folder"                  # dry run
    python3 organize_notes.py "/Vault/Some Folder" --apply          # do it
    python3 organize_notes.py --rollback .organize-plan-20260930-010203.json
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

PROG = "organize_notes.py"
DEF_LIMIT = 26        # notes per index folder
DEF_MAX_PATH = 240    # chars; Windows MAX_PATH = 260 incl. drive letter + NUL
DEF_PRESERVE = "template,templates,data,assets,Scripts,.obsidian,.git,.trash"
ROOT_KEEP = {"README.md", "index.md"}          # stay at the target root
MAX_LEVEL = 8                                   # index levels per chain; see --max-level
# First characters with more than one reading, where the readings start with DIFFERENT
# letters - so the pinyin reading decides the bucket. ICU picks one; only a human knows
# which one the note means. Reported for review, never rewritten automatically.
POLYPHONE = {
    "重": "chóng/zhòng", "仇": "qiú(姓)/chóu", "单": "shàn(姓)/dān", "曾": "zēng(姓)/céng",
    "解": "xiè(姓)/jiě", "查": "zhā(姓)/chá", "区": "ōu(姓)/qū", "乐": "yuè/lè",
    "种": "chóng(姓)/zhǒng", "秘": "bì(秘鲁)/mì", "繁": "pó(姓)/fán", "长": "cháng/zhǎng",
    "会": "kuài(会计)/huì", "折": "shé/zhé", "尉": "yù(姓)/wèi", "覃": "qín(姓)/tán",
}
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL",
                    *{"COM%d" % i for i in range(1, 10)},
                    *{"LPT%d" % i for i in range(1, 10)}}
ILLEGAL_FS = set('\\/:*?"<>|')
EMBED_RE = re.compile(r"!\[\[([^\]|#]+)|!\[[^\]]*\]\(([^)]+)\)")
QUOTED_RE = re.compile(r"""["']([^"']{2,200})["']""")

PRESERVE: set[str] = set()


# ---------------------------------------------------------------------------
# pinyin adapters
# ---------------------------------------------------------------------------

ANCHORS = "啊八擦搭蛾发噶哈衣基科勒摸讷哦坡欺日思特屋西迂匝"   # one per A..Z


class Pinyin:
    """Name -> latin sort key; ``backend`` reports the rung that is active."""

    def __init__(self, mode: str = "auto", cache_path: Path | None = None):
        self.backend = "codepoint"
        self.cache_path = cache_path
        self.cache: dict[str, str] = {}
        self._anchors: list[str] = []
        self._anchors_ready = False
        self._warned = False
        if cache_path and cache_path.is_file():
            try:
                self.cache = json.loads(cache_path.read_text("utf-8"))
            except (OSError, ValueError):
                self.cache = {}
        ladders = {
            "auto": ["pypinyin", "icu", "locale", "codepoint"],
            "pypinyin": ["pypinyin", "codepoint"],
            "icu": ["icu", "codepoint"],
            "locale": ["locale", "codepoint"],
            "codepoint": ["codepoint"],
        }
        for rung in ladders[mode]:
            if self._probe(rung):
                self.backend = rung
                break

    # -- probes ------------------------------------------------------------
    def _probe(self, rung: str) -> bool:
        if rung == "pypinyin":
            try:
                return self._via_pypinyin("打") == "da"
            except Exception:
                return False
        if rung == "icu":
            if sys.platform != "darwin":
                return False
            return self._via_icu(["打"]).get("打") == "da"
        if rung == "locale":
            return self._locale_init()
        return rung == "codepoint"

    # -- backends ----------------------------------------------------------
    @staticmethod
    def _via_pypinyin(name: str) -> str:
        from pypinyin import lazy_pinyin
        return "".join(lazy_pinyin(name))

    @staticmethod
    def _via_icu(names: list[str]) -> dict[str, str]:
        """Batch transliteration. NOTE: osascript -l JavaScript prints to STDERR."""
        js = (
            "ObjC.import('Foundation');\n"
            "const items = %s;\n"
            "console.log(JSON.stringify(items.map(s => {\n"
            "  const ns = $.NSString.alloc.initWithString(s);\n"
            "  const t = ns.stringByApplyingTransformReverse('Any-Latin; Latin-ASCII', false);\n"
            "  return [s, ObjC.unwrap(t).replace(/\\s+/g, '')];\n"
            "})));\n"
        ) % json.dumps(names, ensure_ascii=False)
        try:
            proc = subprocess.run(["osascript", "-l", "JavaScript", "-e", js],
                                  capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            return {}
        raw = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        try:
            return dict(json.loads(raw))
        except ValueError:
            return {}

    def _locale_init(self) -> bool:
        if self._anchors_ready:
            return True
        for cand in ("zh_CN.UTF-8", "zh_CN.utf8", "Chinese_China", "zh_CN"):
            try:
                locale.setlocale(locale.LC_COLLATE, cand)
                break
            except locale.Error:
                continue
        else:
            return False
        try:
            self._anchors = sorted(ANCHORS, key=locale.strxfrm)
        except Exception:
            return False
        if self._anchors[0] != ANCHORS[0] or self._anchors[-1] != ANCHORS[-1]:
            return False                    # collation is not pinyin-ordered
        self._anchors_ready = True
        return True

    def _locale_first(self, ch: str) -> str | None:
        k = locale.strxfrm(ch)
        letter = None
        for i, a in enumerate(self._anchors):
            if locale.strxfrm(a) <= k:
                letter = chr(ord("A") + ANCHORS.index(a))
            else:
                break
        return letter

    # -- public ------------------------------------------------------------
    @staticmethod
    def _needs_latin(name: str) -> bool:
        return any("\u3400" <= c <= "\u9fff" or "\u0370" <= c <= "\u03ff" for c in name)

    def prewarm(self, names: list[str]) -> None:
        """Batch-transliterate up front: one osascript call instead of one per name."""
        todo = [n for n in dict.fromkeys(names)
                if n not in self.cache and self._needs_latin(n)]
        if not todo:
            return
        try:
            if self.backend == "icu":
                for i in range(0, len(todo), 300):
                    self.cache.update(self._via_icu(todo[i:i + 300]))
            elif self.backend == "pypinyin":
                for n in todo:
                    self.cache[n] = self._via_pypinyin(n)
        except Exception:
            pass

    def latinize(self, name: str) -> str:
        if name in self.cache:
            return self.cache[name]
        if not self._needs_latin(name):
            self.cache[name] = name
            return name
        out = name
        try:
            if self.backend == "pypinyin":
                out = self._via_pypinyin(name)
            elif self.backend == "icu":
                out = self._via_icu([name]).get(name, name)
            elif self.backend == "locale" and self._anchors_ready:
                out = "".join(self._locale_first(c) or "_" if "\u3400" <= c <= "\u9fff" else c
                              for c in name)
            else:
                if not self._warned:
                    print("  [!] no pinyin backend on this host: CJK names bucket into '_'",
                          file=sys.stderr)
                    self._warned = True
                return name
        except Exception:
            out = name
        self.cache[name] = out
        return out

    def save_cache(self) -> None:
        if self.cache_path:
            try:
                self.cache_path.write_text(
                    json.dumps(self.cache, ensure_ascii=False, indent=1), "utf-8")
            except OSError:
                pass


def sort_key(name: str, py: Pinyin) -> str:
    """ASCII-alphanumeric-uppercase key; emoji/symbols/punctuation are dropped."""
    latin = unicodedata.normalize("NFKD", py.latinize(name))
    latin = "".join(c for c in latin if not unicodedata.combining(c))
    return re.sub(r"[^0-9A-Za-z]", "", latin).upper()


def bucket_name(key: str, level: int) -> str:
    """Cumulative prefix: level 1 -> 'A', level 2 -> 'AB', level 3 -> 'ABC'."""
    if not key:
        return "_"
    seg = key[:level]
    return "".join("_" if c in ILLEGAL_FS else c for c in seg) or "_"


# ---------------------------------------------------------------------------
# scanning
# ---------------------------------------------------------------------------

class Unit:
    """One note: its .md plus the payload that travels with it."""

    __slots__ = ("name", "md", "own_dir", "key", "carry", "chain", "dst_dir", "skip")

    def __init__(self, name: str, md: Path, own_dir: Path | None, key: str):
        self.name = name
        self.md = md
        self.own_dir = own_dir          # the "<Name>/" folder, if the note has one
        self.key = key
        self.carry: list[Path] = []     # files/dirs moved next to the .md
        self.chain: list[str] = []
        self.dst_dir: Path | None = None
        self.skip = False

    @property
    def depth(self) -> int:
        return len(self.md.parts)


def scan(target: Path, preserve: set[str], py: Pinyin):
    """Classify the subtree: note units, orphan containers, root noise."""
    all_dirs: list[Path] = []
    all_md: list[Path] = []
    all_files: list[Path] = []
    for dp, dn, fn in os.walk(target, followlinks=False):
        dp_ = Path(dp)
        dn[:] = sorted(d for d in dn if d not in preserve and not (dp_ / d).is_symlink())
        all_dirs.append(dp_)
        for f in sorted(fn):
            p = dp_ / f
            all_files.append(p)
            if f.endswith(".md"):
                all_md.append(p)

    # embed references: target name -> set of referencing note stems
    refs: dict[str, set[str]] = collections.defaultdict(set)
    py.prewarm([m.stem for m in all_md])      # one batched transliteration call
    for m in all_md:
        try:
            text = m.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        for a, b in EMBED_RE.findall(text):
            tgt = os.path.basename((a or b).strip())
            refs[tgt].add(m.stem)
            refs[tgt.split(".")[0]].add(m.stem)

    def is_root_keep(m: Path) -> bool:
        # the folder's own note (a folder note) and the usual root files stay put
        return m.parent == target and (m.name in ROOT_KEEP or m.name == target.name + ".md")

    def is_excalidraw(m: Path) -> bool:
        return m.name.endswith(".excalidraw.md")

    # --- units ------------------------------------------------------------
    units: dict[Path, Unit] = {}
    for m in all_md:
        if is_root_keep(m) or is_excalidraw(m):
            continue
        own = m.parent if (m.parent != target and m.parent.name == m.stem) else None
        units[m] = Unit(m.stem, m, own, sort_key(m.stem, py))

    # excalidraw exception: embedded by exactly one note -> rides along as an attachment
    exc_units: list[Unit] = []
    for m in all_md:
        if not is_excalidraw(m) or is_root_keep(m):
            continue
        referrers = refs.get(m.name, set()) | refs.get(m.stem, set())
        host = next((u for u in units.values() if u.name in referrers), None) if len(referrers) == 1 else None
        if host is not None:
            host.carry.append(m)
        else:
            own = m.parent if (m.parent.name == m.stem) else None
            exc_units.append(Unit(m.stem, m, own, sort_key(m.stem, py)))
    for u in exc_units:
        units[u.md] = u

    claimed: set[Path] = {u.md for u in units.values()}
    claimed |= {p for u in units.values() for p in u.carry}
    own_dirs = {u.own_dir for u in units.values() if u.own_dir}
    claimed_dirs: set[Path] = set()

    # a directory that CONTAINS a note folder is a container of notes, never an
    # attachment: carrying it inside a note would preserve the very nesting we are
    # flattening.  Loose .md files inside a carried directory are fine - they are
    # hoisted out first and the directory keeps the rest of its (program/data) files.
    note_folders = {u.own_dir for u in units.values() if u.own_dir}

    def contains_note_folder(d: Path) -> bool:
        return any(d == o or d in o.parents for o in note_folders)

    # --- payload inside each note's own folder ----------------------------
    for u in sorted(units.values(), key=lambda u: -u.depth):
        if not u.own_dir:
            continue
        try:
            children = sorted(u.own_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if child in claimed or child.name in preserve:
                continue
            if child.is_dir() and contains_note_folder(child):
                continue                     # a nested note folder hoists itself
            claimed.add(child)
            u.carry.append(child)
            if child.is_dir():
                claimed_dirs.add(child)

    # --- attachment containers / loose files -----------------------------
    def attribute(p: Path) -> Unit | None:
        if p.is_dir() and contains_note_folder(p):
            return None                      # container of notes: leaves, never follows one
        if p.name.endswith("_assets"):
            base = p.name[:-len("_assets")]
            hit = next((u for u in units.values() if u.name == base), None)
            if hit is None and base:
                # naming drift between a note and its assets folder: accept a unique
                # prefix relationship, e.g. "(X) Basics" vs "(X) Basics setup"
                cands = [u for u in units.values()
                         if u.name.startswith(base) or base.startswith(u.name)]
                if len(cands) == 1:
                    hit = cands[0]
            if hit:
                return hit
        # a loose file (or a small attachment dir) belongs to a note only when that
        # single note references every file in it
        try:
            inner = [q for q in (p.rglob("*") if p.is_dir() else [p]) if q.is_file()]
        except OSError:
            inner = []
        if inner:
            owners = [refs.get(q.name, set()) | refs.get(q.stem, set()) for q in inner]
            common = set.intersection(*owners) if owners else set()
            if len(common) == 1:
                return next((u for u in units.values() if u.name in common), None)
        anc = p.parent
        while anc != target.parent:
            if anc in own_dirs:
                return next((u for u in units.values() if u.own_dir == anc), None)
            if anc == target:
                return None
            anc = anc.parent
        return None

    orphans: list[Path] = []
    noise: list[Path] = []
    for d in all_dirs:
        if d == target or d in own_dirs or d in claimed:
            continue
        # only the payload loop above claims items, and it only walks note own_dirs,
        # so anything nested deeper is still unclaimed and must be attributed here
        if any(par in own_dirs for par in d.parents):
            continue
        if d.name.startswith("."):
            noise.append(d)
            continue
        host = attribute(d)
        if host is None:
            orphans.append(d)
        else:
            host.carry.append(d)
            claimed_dirs.add(d)
        claimed.add(d)
    # a carried directory travels as one whole unit: everything inside it is now claimed,
    # otherwise its files would be attributed a second time and generate moves that
    # overlap the directory move (one of the two always fails on disk)
    for d in claimed_dirs:
        for p in d.rglob("*"):
            claimed.add(p)
    for f in all_files:
        if f in claimed or f.name.endswith(".md") or f.parent == target:
            continue
        if any(par in own_dirs for par in f.parents):
            continue
        if f.name.startswith("."):
            noise.append(f)
            continue
        host = attribute(f)
        if host is None:
            orphans.append(f)
        else:
            host.carry.append(f)
        claimed.add(f)
    # a carried directory already contains its own files: keep only the outermost item.
    # This must be GLOBAL: two different notes can claim a folder and a file inside it,
    # and whichever unit moves the folder takes the file along - the second move would fail.
    outer = set(prune_nested([p for u in units.values() for p in u.carry]))
    for u in units.values():
        u.carry = [p for p in u.carry if p in outer]
    return units, orphans, noise, all_md, all_files


def prune_nested(items: list[Path]) -> list[Path]:
    """Drop every item that lives inside another item of the same list."""
    keep: list[Path] = []
    for p in sorted(items, key=lambda x: len(x.parts)):
        if any(k == p or k in p.parents for k in keep):
            continue
        keep.append(p)
    return keep


def assign_buckets(units: list[Unit], limit: int, max_level: int = MAX_LEVEL):
    """Recursive split by key prefix; returns {chain: [units]} + problems."""
    leaves: dict[tuple[str, ...], list[Unit]] = {}
    issues: list[str] = []

    def split(items: list[Unit], chain: tuple[str, ...], level: int) -> None:
        while True:
            if not items:
                return
            maxlen = max(len(u.key) for u in items)
            if level > maxlen or level > max_level:
                leaves[chain] = items
                if len(items) > limit:
                    issues.append("cannot split `%s`: %d notes share one key prefix"
                                  % ("/".join(chain), len(items)))
                return
            groups: dict[str, list[Unit]] = collections.defaultdict(list)
            for u in items:
                groups[bucket_name(u.key, level)].append(u)
            if len(groups) > 1:
                for b, members in sorted(groups.items()):
                    if len(members) <= limit:
                        leaves[chain + (b,)] = members
                    else:
                        split(members, chain + (b,), level + 1)
                return
            b, members = next(iter(groups.items()))     # single group: keep the level
            chain, items, level = chain + (b,), members, level + 1
            if len(members) <= limit:
                leaves[chain] = members
                return

    split(list(units), (), 1)
    return leaves, issues


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------

def git_preflight(target: Path, require_clean: bool) -> dict:
    out = {"is_repo": False, "head": None, "dirty": [], "ignored": [], "verdict": "not-a-repo"}
    try:
        r = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return out
        out["is_repo"] = True
        out["head"] = r.stdout.strip()
        st = subprocess.run(["git", "-C", str(target), "status", "--porcelain", "--ignored",
                             "--", "."], capture_output=True, text=True)
        lines = [l for l in st.stdout.splitlines() if l.strip()]
        out["dirty"] = [l for l in lines if not l.startswith("!!")]
        out["ignored"] = [l for l in lines if l.startswith("!!")]
    except (OSError, subprocess.SubprocessError):
        return out
    if out["dirty"] or out["ignored"]:
        out["verdict"] = "dirty-abort" if require_clean else "dirty-warn"
    else:
        out["verdict"] = "clean"
    return out


def path_reference_scan(target: Path, dissolved: list[str]) -> list[str]:
    """Views (.base) / dataview queries that hardcode a path which is about to vanish.

    ``dissolved`` are the intermediate folders that disappear because their content
    is hoisted up. No folder name is assumed - whatever exists gets checked.
    """
    hits: list[str] = []
    if not dissolved:
        return hits
    needles = sorted({d for d in dissolved if d}, key=len, reverse=True)
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in (".git", ".obsidian")]
        for f in fn:
            if not f.endswith((".base", ".md")):
                continue
            p = Path(dp) / f
            try:
                text = p.read_text("utf-8", errors="ignore")
            except OSError:
                continue
            if not any(n in text for n in needles):
                continue
            for m in QUOTED_RE.finditer(text):
                if any(n in m.group(1) for n in needles):
                    hits.append("%s -> \"%s\"" % (p.relative_to(target), m.group(1)))
                    break
            if len(hits) >= 12:
                return hits
    return hits


def build_plan(target: Path, args, py: Pinyin, plan_path: Path) -> dict:
    units, orphans, noise, all_md, all_files = scan(target, PRESERVE, py)
    leaves, issues = assign_buckets(list(units.values()), args.limit, args.max_level)

    # collision handling: same final path (case-insensitive -> macOS/Windows clash)
    by_name: dict[str, list[Unit]] = collections.defaultdict(list)
    for u in units.values():
        by_name[unicodedata.normalize("NFC", u.name).casefold()].append(u)
    collisions = []
    for key, group in sorted(by_name.items()):
        if len(group) > 1:
            group.sort(key=lambda u: u.depth)
            collisions.append({"name": group[0].name,
                               "src": [str(u.md) for u in group]})
            if args.on_collision == "skip":
                for u in group[1:]:
                    u.skip = True
            else:
                for u in group:
                    u.skip = True

    moves: list[tuple[str, str]] = []
    dirs_needed: set[str] = set()
    index_files: dict[str, str] = {}
    unit_rows = []
    longest: list[list] = []

    for chain, members in sorted(leaves.items()):
        live = [u for u in members if not u.skip]
        parent = target.joinpath(*chain)
        # every folder on the chain is an index folder: T/<c1> is level 1,
        # T/<c1>/<c2> is level 2, ... so each one carries .index.<its level>
        for k in range(1, len(chain) + 1):
            index_files[str(target.joinpath(*chain[:k]) / (".index.%d" % k))] = str(k)
        if live:
            dirs_needed.add(str(parent))
        for u in live:
            dst_dir = parent / u.name
            u.dst_dir = dst_dir
            u.chain = list(chain)
            dirs_needed.add(str(dst_dir))
            rows = [(u.md, dst_dir / u.md.name)]
            rows += [(p, dst_dir / p.name) for p in u.carry]
            for src, dst in rows:
                if str(src) == str(dst):
                    continue          # already in place: re-running must change nothing
                moves.append((str(src), str(dst)))
            longest.append([str(dst_dir / (u.name + ".md")), len(str(dst_dir / (u.name + ".md")))])
            unit_rows.append({"name": u.name, "key": u.key, "chain": list(chain),
                              "src_md": str(u.md), "dst_dir": str(dst_dir),
                              "carried": len(rows) - 1})

    if leaves:
        index_files[str(target / ".index.1")] = "1"

    # first characters with more than one reading: the bucket depends on which reading the
    # note means, and no script can know that. Surface them instead of guessing silently.
    polyphone = []
    for u in sorted(units.values(), key=lambda u: u.name):
        ch = u.name[0] if u.name else ""
        if ch in POLYPHONE:
            polyphone.append({"name": u.name, "char": ch, "readings": POLYPHONE[ch],
                              "bucket": "/".join(u.chain) if u.chain else "(left in place)",
                              "src_md": str(u.md)})

    # what stays put: collision-skipped notes, unattributable attachments, root files.
    # Containers that end up empty are dissolved, so only report the ones still holding
    # something nobody claimed.
    moved_paths = [Path(s) for s, _ in moves]

    def is_moved(p: Path) -> bool:
        return any(p == m or m in p.parents for m in moved_paths)

    leftovers = sorted(str(p.relative_to(target)) for p in all_files
                       if p.parent != target and not is_moved(p))
    orphans = [o for o in orphans
               if any(o == target / l or o in (target / l).parents for l in leftovers)]

    # --- validation -------------------------------------------------------
    dst_list = [d for _, d in moves]
    src_list = [s for s, _ in moves]
    dup_dst = sorted({d for d, n in collections.Counter(dst_list).items() if n > 1})
    dup_dst_ci = sorted({d for d, n in collections.Counter(d.casefold() for d in dst_list).items()
                         if n > 1})
    dup_src = sorted({s for s, n in collections.Counter(src_list).items() if n > 1})
    missing_src = [s for s in src_list if not os.path.lexists(s)]
    src_set = set(src_list)
    nesting = []
    for d in dst_list:
        for p in Path(d).parents:
            if str(p) in src_set:
                nesting.append([d, str(p)])
                break
    # no source may contain another source: that means one payload was claimed twice
    # (e.g. an attachment folder AND the files inside it) and one move must fail
    nested_src = []
    note_md_set = {str(u.md) for u in units.values()}
    for s in src_list:
        for p in Path(s).parents:
            if str(p) in src_set:
                # a note hoisting out of a carried directory is fine: the note leaves
                # first (deepest move first), then the directory moves without it
                if s not in note_md_set:
                    nested_src.append([s, str(p)])
                break
    for d in dst_list:
        dirs_needed.add(os.path.dirname(d))
    over = sorted({p for p, n in longest if n > args.max_path}, key=lambda p: -len(p))

    warnings = []
    if py.backend == "codepoint":
        warnings.append("no pinyin backend: CJK-initial names bucket into '_'")
    if over:
        warnings.append("longest resulting path is %d chars and the note name alone is %d "
                        "chars - an index cannot shorten a name; rename that note if it matters"
                        % (len(over[0]), len(Path(over[0]).parent.name)))
    if leftovers:
        warnings.append("%d file(s) will not move (collision-skipped or unattributable); "
                        "see 'leftovers' in the plan" % len(leftovers))
    if polyphone:
        warnings.append("%d note(s) start with a character that has two readings (%s); the "
                        "reading decides the bucket, so check these by hand: %s"
                        % (len(polyphone), ", ".join(sorted({p["char"] for p in polyphone})),
                           ", ".join(p["name"] for p in polyphone[:3])))
    deep = sorted({k for k in leaves if len(k) > 4})
    if deep:
        warnings.append("%d bucket chain(s) reach deeper than 4 index levels (deepest %s); "
                        "cumulative prefixes make those paths long - rename notes that share "
                        "a long common prefix if that matters"
                        % (len(deep), "/".join(max(deep, key=len))))
    for u in units.values():
        if u.name.upper() in WINDOWS_RESERVED:
            warnings.append("name %r is reserved on Windows" % u.name)
        if u.name.endswith((".", " ")):
            warnings.append("name %r ends with dot/space (illegal on Windows)" % u.name)
    # folders that disappear because their content is hoisted up: any ancestor of a
    # moved source that is not itself a planned bucket.  No name is hard-coded.
    created = {Path(d) for d in dirs_needed}
    skeleton: set[Path] = set()
    for s in src_list:
        p = Path(s).parent
        while p != target and target in p.parents:
            skeleton.add(p)
            p = p.parent
    dissolved = sorted(str(p.relative_to(target)) for p in skeleton - created)
    path_refs = path_reference_scan(target, dissolved)
    if path_refs:
        warnings.append("%d view/query file(s) reference a folder that gets dissolved "
                        "(%s) -> they will break" % (len(path_refs), ", ".join(dissolved[:3])))
    if collisions and args.on_collision == "skip":
        warnings.append("%d colliding note name(s) left in place (--on-collision skip)"
                        % sum(len(c["src"]) - 1 for c in collisions))
    if noise:
        warnings.append("%d dot-file(s)/dot-dir(s) hoisted to the target root" % len(noise))

    return {
        "version": 1, "tool": PROG,
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry_run",
        "target": str(target), "limit": args.limit,
        "pinyin_backend": py.backend,
        "counts": {
            "notes": sum(1 for u in units.values() if not u.skip),
            "md_in_subtree": len(all_md),
            "leaf_buckets": len(leaves),
            "moves": len(moves),
            "orphan_containers": len(orphans),
            "excalidraw_attachments": sum(1 for u in units.values()
                                          for p in u.carry if p.name.endswith(".excalidraw.md")),
        },
        "units": unit_rows,
        "leaf_buckets": {"/".join(k): len([u for u in v if not u.skip])
                         for k, v in sorted(leaves.items())},
        "dirs_to_create": sorted(dirs_needed),
        "index_files": [[p, c] for p, c in sorted(index_files.items())],
        "moves": [{"src": s, "dst": d} for s, d in moves],
        "orphans": [str(o) for o in orphans],
        "leftovers": leftovers,
        "noise": [str(n) for n in noise],
        "collisions": collisions,
        "path_references": path_refs,
        "problems": {
            "missing_src": missing_src, "duplicate_src": dup_src,
            "duplicate_dst": dup_dst, "duplicate_dst_casefold": dup_dst_ci,
            "dst_inside_src": nesting, "nested_src": nested_src,
            "over_limit_no_split": issues,
            "paths_over_max": over,
        },
        "warnings": warnings,
        "polyphone_review": polyphone,
        "git": git_preflight(target, not args.allow_dirty),
    }


# ---------------------------------------------------------------------------
# apply / rollback / verify
# ---------------------------------------------------------------------------

def apply_plan(plan: dict, plan_path: Path, index_content: str) -> int:
    # every destination parent first: shutil.move(src, dst) RENAMES src into dst
    # when dst is absent, silently corrupting the tree.
    for d in plan["dirs_to_create"]:
        os.makedirs(d, exist_ok=True)
    done = []
    for m in sorted(plan["moves"], key=lambda m: -m["src"].count(os.sep)):   # deepest first
        src, dst = m["src"], m["dst"]
        if not os.path.lexists(src):
            print("  [x] source vanished: %s" % src, file=sys.stderr)
            return 4
        if os.path.lexists(dst):
            print("  [x] destination already exists, refusing to merge: %s" % dst, file=sys.stderr)
            return 4
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.rename(src, dst)
        except OSError:
            shutil.move(src, dst)
        done.append(m)
    for path, level in plan["index_files"]:
        Path(path).write_text("" if index_content == "empty" else level + "\n", "utf-8")
    plan["applied"] = done
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")
    # dissolve the emptied source skeleton. Only directories that used to hold a moved
    # source may be pruned: a blanket "remove every empty directory" would also delete
    # freshly created destinations that legitimately ended up empty - e.g. a carried
    # folder whose only file was hoisted out into its own bucket.
    skeleton = set()
    for m in done:
        p = os.path.dirname(m["src"])
        while p.startswith(plan["target"] + os.sep):
            skeleton.add(p)
            p = os.path.dirname(p)
    for dp in sorted(skeleton, key=lambda x: -x.count(os.sep)):
        try:
            Path(dp).rmdir()          # rmdir refuses non-empty: leftovers survive
        except OSError:
            pass
    return 0


def rollback(plan_path: Path) -> int:
    plan = json.loads(plan_path.read_text("utf-8"))
    moves = plan.get("applied") or plan.get("moves") or []
    n = 0
    skipped = []
    emptied = set()
    # exact reverse of the apply order (apply moved deepest-first, so a carried folder is
    # restored BEFORE the note that was hoisted out of it - that note's restore needs the
    # folder to be back). Re-sorting by destination depth recreated the parent first and
    # then skipped the folder itself, stranding it in the bucket.
    for m in reversed(moves):
        src, dst = m["src"], m["dst"]
        if not os.path.lexists(dst):
            skipped.append(("already moved back / absent at destination", dst))
            continue
        if os.path.lexists(src):
            skipped.append(("original path occupied", src))
            continue
        os.makedirs(os.path.dirname(src), exist_ok=True)
        try:
            os.rename(dst, src)
        except OSError:
            shutil.move(dst, src)
        n += 1
        p = os.path.dirname(dst)
        while p.startswith(plan["target"] + os.sep):
            emptied.add(p)
            p = os.path.dirname(p)
    for path, _ in plan.get("index_files", []):
        try:
            Path(path).unlink()
        except OSError:
            pass
    for dp in sorted(emptied, key=lambda x: -x.count(os.sep)):
        try:
            Path(dp).rmdir()
        except OSError:
            pass
    print("[ok] rolled back %d move(s)" % n)
    for why, p in skipped[:10]:
        print("  [!] not restored (%s): %s" % (why, p))
    if len(skipped) > 10:
        print("  [!] ... and %d more" % (len(skipped) - 10))
    return 1 if skipped else 0


def verify(plan: dict) -> list[str]:
    errs = []
    for m in plan.get("applied", []):
        if not os.path.lexists(m["dst"]):
            errs.append("missing after move: %s" % m["dst"])
    for path, _ in plan["index_files"]:
        if not os.path.isfile(path):
            errs.append("index marker missing: %s" % path)
    for chain, size in plan["leaf_buckets"].items():
        if size > plan["limit"]:
            errs.append("bucket %s holds %d > %d notes" % (chain, size, plan["limit"]))
    return errs


# ---------------------------------------------------------------------------
# report / main
# ---------------------------------------------------------------------------

def print_report(plan: dict, plan_path: Path) -> None:
    c = plan["counts"]
    print("\n=== %s ===" % plan["target"])
    print("pinyin backend : %s      mode: %s" % (plan["pinyin_backend"], plan["mode"]))
    print("notes          : %d  (of %d .md in subtree) | moves %d"
          % (c["notes"], c["md_in_subtree"], c["moves"]))
    print("leaf buckets   : %d | index markers %d | orphan containers %d | excalidraw rides-along %d"
          % (c["leaf_buckets"], len(plan["index_files"]), c["orphan_containers"],
             c["excalidraw_attachments"]))
    sizes = sorted(plan["leaf_buckets"].items(), key=lambda kv: -kv[1])
    print("fullest buckets: " + ", ".join("%s=%d" % (k, v) for k, v in sizes[:8]))
    g = plan["git"]
    print("git            : %s%s" % (g["verdict"], "" if not g["is_repo"] else
          "  (dirty %d, ignored %d)" % (len(g["dirty"]), len(g["ignored"]))))
    for key in ("missing_src", "duplicate_src", "duplicate_dst", "duplicate_dst_casefold",
                "dst_inside_src", "nested_src", "over_limit_no_split"):
        if plan["problems"][key]:
            print("  [!] %-24s %d   e.g. %s" % (key, len(plan["problems"][key]),
                                                 str(plan["problems"][key][:2])[:120]))
    if plan["problems"]["paths_over_max"]:
        print("  [!] %-24s %d   longest %d chars"
              % ("paths_over_max", len(plan["problems"]["paths_over_max"]),
                 len(plan["problems"]["paths_over_max"][0])))
    if plan["collisions"]:
        print("  [!] %-24s %d   e.g. %s" % ("name collisions", len(plan["collisions"]),
                                            plan["collisions"][0]["name"]))
    for w in plan["warnings"]:
        print("  [!] %s" % w)
    if plan.get("polyphone_review"):
        poly = plan["polyphone_review"]
        print("polyphone      : %d note(s) need a human check before applying" % len(poly))
        for p in poly[:5]:
            print("    %-34s -> bucket %-10s (%s 可读 %s)"
                  % (p["name"][:34], p["bucket"], p["char"], p["readings"]))
    if plan["leftovers"]:
        print("  stays put      : %d file(s)  e.g. %s"
              % (len(plan["leftovers"]), ", ".join(plan["leftovers"][:4])))
    print("plan written   : %s" % plan_path)
    if plan["mode"] == "dry_run":
        print("\nDRY RUN - nothing on disk was touched.")
        print("  apply   : python3 %s \"%s\" --apply" % (PROG, plan["target"]))
        print("  discard : rm %s" % plan_path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog=PROG, formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Flatten nested notes and letter-index them (Obsidian vaults).")
    ap.add_argument("target", nargs="?", help="folder to organize")
    ap.add_argument("--apply", action="store_true",
                    help="execute the plan; without it nothing is written")
    ap.add_argument("--rollback", metavar="PLAN.json",
                    help="reverse a previously applied plan, then exit")
    ap.add_argument("--limit", type=int, default=DEF_LIMIT,
                    help="max notes per index folder (count of notes)")
    ap.add_argument("--max-level", type=int, default=MAX_LEVEL,
                    help="hard stop for how many index levels a chain may reach")
    ap.add_argument("--max-path", type=int, default=DEF_MAX_PATH,
                    help="warn above this path length (chars)")
    ap.add_argument("--preserve", default=DEF_PRESERVE,
                    help="comma-separated dir names never descended into")
    ap.add_argument("--on-collision", choices=("abort", "skip"), default="abort",
                    help="abort=stop; skip=leave colliding notes untouched and plan the rest")
    ap.add_argument("--index-content", choices=("level", "empty"), default="level",
                    help=".index.<n> payload: level=one line holding n, empty=zero bytes")
    ap.add_argument("--pinyin", choices=("auto", "pypinyin", "icu", "locale", "codepoint"),
                    default="auto", help="pinyin backend for CJK names")
    ap.add_argument("--allow-dirty", dest="allow_dirty", action="store_true",
                    help="proceed although the target has uncommitted/ignored files "
                         "(default: refuse to touch a dirty target)")
    ap.add_argument("--report", default=None, help="plan JSON path")
    ap.add_argument("--selftest", action="store_true",
                    help="print the environment's capabilities and exit")
    a = ap.parse_args(argv)

    if a.rollback:
        return rollback(Path(a.rollback).expanduser())

    global PRESERVE
    PRESERVE = {p.strip() for p in a.preserve.split(",") if p.strip()}
    cache = Path.home() / ".cache" / "organize_notes-pinyin.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    py = Pinyin(a.pinyin, cache)

    if a.selftest:
        print("platform      : %s" % sys.platform)
        print("python        : %s" % sys.version.split()[0])
        print("pinyin backend: %s" % py.backend)
        for probe in ("打孔蛋白", "王小明", "🧩 Actin (family)", "2-Mercaptoethanol", "α-synuclein"):
            print("  %-22s key=%s  bucket1=%s bucket2=%s"
                  % (probe, sort_key(probe, py), bucket_name(sort_key(probe, py), 1),
                     bucket_name(sort_key(probe, py), 2)))
        return 0

    if not a.target:
        ap.error("target is required unless --rollback/--selftest is given")
    target = Path(a.target).expanduser().resolve()
    if not target.is_dir():
        print("[x] not a directory: %s" % target, file=sys.stderr)
        return 2

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    plan_path = Path(a.report).expanduser() if a.report else Path.cwd() / (".organize-plan-%s.json" % stamp)
    plan = build_plan(target, a, py, plan_path)
    py.save_cache()
    print_report(plan, plan_path)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")

    if plan["git"]["verdict"] == "dirty-abort":
        print("\n[x] PREFLIGHT FAILED: target has uncommitted/ignored files "
              "(%d dirty, %d ignored). Commit them first, or pass --allow-dirty."
              % (len(plan["git"]["dirty"]), len(plan["git"]["ignored"])), file=sys.stderr)
        print("    [i] committed files are not recoverable from git only if a move is "
              "recorded: the plan JSON is your undo log.", file=sys.stderr)
        print("    [i] files matched by .gitignore are not recoverable from git at all: "
              "%d such entry/entries sit inside the target." % len(plan["git"]["ignored"]),
              file=sys.stderr)
        return 2
    fatal = any(plan["problems"][k] for k in
                ("missing_src", "duplicate_src", "duplicate_dst", "duplicate_dst_casefold",
                 "dst_inside_src", "nested_src"))
    if fatal or (plan["collisions"] and a.on_collision == "abort"):
        print("\n[x] plan has fatal problems -> not applying (see above).", file=sys.stderr)
        return 3
    if not a.apply:
        return 0

    rc = apply_plan(plan, plan_path, a.index_content)
    if rc:
        return rc
    errs = verify(plan)
    print("[ok] applied %d move(s), wrote %d index marker(s)"
          % (len(plan["applied"]), len(plan["index_files"])))
    for e in errs[:10]:
        print("  [!] verify: %s" % e)
    print("rollback: python3 %s --rollback %s" % (PROG, plan_path))
    # settle check: hoisting the notes out of a container releases the leftover payload that
    # the container guard skipped on this pass, so a 2nd run can still have real work to do.
    again = build_plan(target, a, py, plan_path)
    if again["counts"]["moves"]:
        print("pass 2   : %d more move(s) available; their containers only became "
              "attributable after this pass - re-run the same command to settle"
              % again["counts"]["moves"])
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
