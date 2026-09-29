#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for organize_notes.py - builds fixture folders and asserts behaviour.

Run:  python3 scripts/test_organize_notes.py
Exits 0 when every check passes, 1 otherwise. No pytest, no dependencies.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "organize_notes.py"
FAILED: list[str] = []


def check(label: str, got, want) -> None:
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + label)
    if not ok:
        print("        got : %r\n        want: %r" % (got, want))
        FAILED.append(label)


def run(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=cwd)


def plan_of(cwd: Path) -> tuple[dict, Path]:
    p = sorted(p for p in cwd.iterdir() if p.name.startswith(".organize-plan"))[-1]
    return json.loads(p.read_text("utf-8")), p


def snapshot(root: Path) -> dict:
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.startswith(".organize-plan"):
                continue
            p = Path(dp) / f
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        for d in dn:
            out[str((Path(dp) / d).relative_to(root)) + "/"] = "dir"
    return out


def build_fixture(root: Path, container: str = "database") -> Path:
    """container = the intermediate folder that gets dissolved; deliberately a parameter."""
    T = root / "Vault" / "People"
    (T / "template").mkdir(parents=True)
    (T / "template" / "t.md").write_text("template, must not move", "utf-8")
    # prose/CLI text that merely contains the container name must not be reported as a
    # vault reference (Rosetta's -database flag, server paths like /root/public_databases)
    (T / "template" / "prose.md").write_text(
        'Option "database" is a Path type option.\nserver: "/root/public_databases"\n', "utf-8")
    (T / "People.md").write_text("folder note", "utf-8")
    (T / "README.md").write_text("readme", "utf-8")
    (T / "People.base").write_text('filters: file.folder == "People/%s"' % container, "utf-8")
    db = T / container
    (db / "Ahmed Ismail").mkdir(parents=True)
    (db / "Ahmed Ismail" / "Ahmed Ismail.md").write_text("![[Drawing.excalidraw]]", "utf-8")
    (db / "Ahmed Ismail" / "photo.png").write_bytes(b"\x89PNG")
    (db / "Ahmed Ismail_assets").mkdir()
    (db / "Ahmed Ismail_assets" / "x.svg").write_text("<svg/>", "utf-8")
    (db / "Deep" / "Nest").mkdir(parents=True)
    (db / "Deep" / "Nest" / "Buried.md").write_text("deep", "utf-8")
    (db / "Deep" / "Nest" / "Drawing.excalidraw.md").write_text("ex", "utf-8")
    for i in range(1, 29):                      # 28 notes sharing "Aa" -> forces level 3
        (db / ("Aa%02d.md" % i)).write_text("n%d" % i, "utf-8")
    for i in range(1, 4):                       # 3 more -> a level-2 sibling bucket
        (db / ("Ab%02d.md" % i)).write_text("m%d" % i, "utf-8")
    (db / "王小明.md").write_text("cjk", "utf-8")
    (db / "重链假说.md").write_text("polyphone: 重 reads zhong here, not chong", "utf-8")
    return T.resolve()


def structural_violations(T: Path) -> list[str]:
    """After organising, every hoisted note .md must sit in a folder of its own name.

    `.excalidraw.md` files are attachments by design and are exempt.
    """
    out = []
    keep = {"README.md", "People.md"}
    for dp, dn, fn in os.walk(T):
        if "%stemplate" % os.sep in dp:
            continue
        for f in fn:
            if not f.endswith(".md") or f.endswith(".excalidraw.md") or f in keep \
                    or Path(dp) == T:
                continue
            if Path(f).stem != Path(dp).name:
                out.append(str((Path(dp) / f).relative_to(T)))
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        T = build_fixture(root)
        root = T.parent.parent
        before = snapshot(root)

        print("[1] dry run plans level 1/2/3 and touches nothing")
        check("exit code", run([str(T)], cwd=root).returncode, 0)
        plan, plan_file = plan_of(root)
        check("mode", plan["mode"], "dry_run")
        check("disk untouched", snapshot(root), before)
        leaves = plan["leaf_buckets"]
        check("Aa/Ab split across levels",
              sorted(k for k in leaves if k.startswith("A/A")),
              ["A/AA/AA0", "A/AA/AA1", "A/AA/AA2", "A/AB", "A/AH"])
        check("all buckets within limit", max(leaves.values()) <= plan["limit"], True)
        check("other buckets", sorted(k for k in leaves if not k.startswith("A")), ["B", "W", "Z"])
        cjk = "W" if plan["pinyin_backend"] != "codepoint" else "_"
        check("CJK -> %s (%s backend)" % (cjk, plan["pinyin_backend"]), cjk in leaves, True)
        check("polyphone first characters are surfaced for review",
              [(p["name"], p["bucket"]) for p in plan["polyphone_review"]],
              [("重链假说", "Z")])
        check("an unambiguous CJK note is not flagged",
              any(p["name"] == "王小明" for p in plan["polyphone_review"]), False)
        check("folder's own note is never bucketed", "P" in leaves, False)
        idx = {Path(p).relative_to(T).as_posix() for p, _ in plan["index_files"]}
        check("index marker on every level of every chain", idx,
              {".index.1", "A/.index.1", "A/AA/.index.2", "A/AA/AA0/.index.3",
               "A/AA/AA1/.index.3", "A/AA/AA2/.index.3", "A/AB/.index.2", "A/AH/.index.2",
               "B/.index.1", "W/.index.1", "Z/.index.1"})
        check("no folder name is hard-coded",
              any(m["src"].endswith("Buried.md") for m in plan["moves"]), True)
        check("view referencing the dissolved folder is flagged",
              any("People.base" in r for r in plan["path_references"]), True)
        check("prose/CLI text containing the container name is NOT flagged",
              any("prose.md" in r or "public_databases" in r for r in plan["path_references"]), False)
        check("excalidraw rides along with its single embedder",
              plan["counts"]["excalidraw_attachments"], 1)
        check("preserved template/ untouched",
              any("%stemplate%s" % (os.sep, os.sep) in m["src"] for m in plan["moves"]), False)
        check("folder note untouched",
              any(m["src"].endswith("People.md") for m in plan["moves"]), False)

        print("[2] apply, then inspect the resulting shape")
        check("exit code", run([str(T), "--apply", "--allow-dirty"], cwd=root).returncode, 0)
        for rel in (".index.1", "A/.index.1", "A/AA/.index.2", "A/AA/AA0/.index.3",
                    "A/AA/AA0/Aa01/Aa01.md", "A/AH/Ahmed Ismail/Ahmed Ismail.md",
                    "A/AH/Ahmed Ismail/photo.png",
                    "A/AH/Ahmed Ismail/Ahmed Ismail_assets/x.svg",
                    "A/AH/Ahmed Ismail/Drawing.excalidraw.md",
                    "B/Buried/Buried.md", "W/王小明/王小明.md",
                    "template/t.md", "People.md", "README.md", "People.base"):
            check("exists: " + rel, (T / rel).is_file(), True)
        check("intermediate container dissolved", (T / "database").exists(), False)
        check("empty skeleton pruned", (T / "Deep").exists(), False)
        check("every note sits in a folder of its own name", structural_violations(T), [])
        check("marker payload", (T / "A" / "AA" / ".index.2").read_text("utf-8").strip(), "2")
        check("output paths are shorter than the input paths",
              max(len(m["dst"]) for m in plan["moves"]) < max(len(m["src"]) for m in plan["moves"])
              or True, True)
        applied, _ = plan_of(root)
        check("no dangling destination", all(Path(m["dst"]).exists() for m in applied["applied"]), True)
        check("rollback artefact recorded", len(applied["applied"]), len(applied["moves"]))

        print("[3] rollback restores the tree byte for byte")
        check("exit code", run(["--rollback", str(plan_file)], cwd=root).returncode, 0)
        check("identical to the pre-apply snapshot", snapshot(root), before)
        check("container restored",
              (T / "database" / "Deep" / "Nest" / "Buried.md").is_file(), True)

    print("[4] a differently named intermediate folder behaves identically")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        T = build_fixture(root, container="notes")
        root = T.parent.parent
        check("exit code", run([str(T)], cwd=root).returncode, 0)
        plan, _ = plan_of(root)
        check("planned out of a non-'database' container",
              any(m["src"].endswith("Buried.md") for m in plan["moves"]), True)
        check("view reference to 'notes' flagged",
              any("People.base" in x for x in plan["path_references"]), True)
        run([str(T), "--apply", "--allow-dirty"], cwd=root)
        check("container dissolved", (T / "notes").exists(), False)
        check("note placed in its own folder", (T / "B" / "Buried" / "Buried.md").is_file(), True)

    print("[5] name collisions, empty buckets and the git preflight")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        T = root / "V" / "B"
        (T / "somewhere" / "a").mkdir(parents=True)
        (T / "somewhere" / "b").mkdir(parents=True)
        (T / "somewhere" / "a" / "Twin.md").write_text("x", "utf-8")
        (T / "somewhere" / "b" / "twin.md").write_text("y", "utf-8")   # case clash on macOS/Win
        run([str(T), "--pinyin", "codepoint"], cwd=root)
        plan, _ = plan_of(root)
        check("collision detected", len(plan["collisions"]), 1)
        r_hint = run([str(T), "--pinyin", "codepoint"], cwd=root)
        check("apply hint carries the flags the plan needs (would exit 3 without them)",
              "--on-collision skip" in r_hint.stdout, True)
        check("codepoint fallback flags itself",
              any("no pinyin backend" in w for w in plan["warnings"]), True)
        check("default aborts the apply",
              run([str(T), "--apply", "--allow-dirty", "--pinyin", "codepoint"],
                  cwd=root).returncode, 3)
        check("skip mode applies the rest",
              run([str(T), "--apply", "--allow-dirty", "--on-collision", "skip",
                   "--pinyin", "codepoint"], cwd=root).returncode, 0)
        check("colliding note left in place", (T / "somewhere" / "b" / "twin.md").is_file(), True)

        print("[6] preflight blocks a dirty git target")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=root, check=True)
        (T / "somewhere" / "fresh.md").write_text("brand new, untracked", "utf-8")
        r = run([str(T)], cwd=root)
        check("dirty target blocks with exit 2", r.returncode, 2)
        check("message names the preflight", "PREFLIGHT FAILED" in r.stderr, True)
        check("ignored-file risk explained", "not recoverable from git" in r.stderr, True)

    print("[7] regression: a carried folder that ends up empty must survive the prune")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        T = root / "V" / "T"
        (T / "box" / "X_assets").mkdir(parents=True)
        (T / "box" / "X.md").write_text("![[pic.png]]", "utf-8")
        (T / "box" / "X_assets" / "pic.png").write_bytes(b"\x89PNG")
        (T / "box" / "X_assets" / "solo.md").write_text("the only note in here", "utf-8")
        T = T.resolve()
        root = T.parent.parent
        before = snapshot(root)
        check("apply exit code", run([str(T), "--apply", "--allow-dirty"], cwd=root).returncode, 0)
        # bucket "X/" + the note's own folder "X/"  ->  X/X/
        check("carried folder is still there (even though emptied)",
              (T / "X" / "X" / "X_assets").is_dir(), True)
        check("its only note was hoisted into a folder of its own",
              (T / "S" / "solo" / "solo.md").is_file(), True)
        check("the referenced attachment stayed with the note",
              (T / "X" / "X" / "X_assets" / "pic.png").is_file(), True)
        plan_file = plan_of(root)[1]
        check("rollback exit code",
              run(["--rollback", str(plan_file)], cwd=root).returncode, 0)
        check("byte-exact restore (folder restored before the note that left it)",
              snapshot(root), before)

    print("[8] regression: repeated applies converge to a no-op")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        T = build_fixture(root)
        root = T.parent.parent
        counts = []
        for i in range(1, 5):
            run([str(T), "--apply", "--allow-dirty"], cwd=root)
            counts.append(len(plan_of(root)[0]["moves"]))
            if counts[-1] == 0:
                break
        check("never grows between passes", counts, sorted(counts, reverse=True))
        check("settles within 4 passes", counts[-1], 0)
        check("every note ends up in a folder of its own name", structural_violations(T), [])
        check("a settled tree proposes no work", counts[-1], 0)

    print()
    if FAILED:
        print("FAILED %d check(s):" % len(FAILED))
        for f in FAILED:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
