---
name: obsidian-entity-notes
description: Use when adding an entity note to the Obsidian vault.
platforms: [macos, linux]
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags:
      - obsidian
      - notes
      - vault
      - research-notes
    related_skills:
      - obsidian
      - obsidian-howto-notes
      - literature-evidence-analysis
---

# Entity / family reference notes in the vault

Companion to the bundled `obsidian` skill — load that one first for vault path resolution, search tooling,
the README-first rule, and the multi-file explain-first gate. This skill carries what a **new entity note**
needs in order to land right on the first attempt.

## When to Use

Trigger on any of these:

- "note this in my Obsidian" / "记到 vault 里" for a **single topic**: protein family (NLR, fluorescent
  protein), protein concept, chemical/macromolecule entity, bioinformatics database.
- A factual answer that the user then asks to persist as a note.
- Filling in an existing empty/stub note on an entity, or tightening its references and links.

Not for: protocol SOPs, tool how-to / software documentation notes (→ `obsidian-howto-notes`), TP393 protocol
notes, MEMOS records, multi-file families — those
have their own type sections in the bundled `obsidian` skill.

Use it for: protein families and protein concepts, macromolecule/chemical entities, bioinformatics databases,
and any single-topic note built from web or literature research.

## Step 0 — survey before writing

1. Read `<vault_root>/README.md` (placement rules) — mandatory.
2. `search_files` the topic keyword across the vault twice: `target=content` on the term, `target=files` on
   `*<term>*`. Existing notes may be absent, a stub, or named differently from what you would invent.
3. If a stub exists, **content-fill it in place** (backup first with `cp -p <note>.md <note>.md.bak-YYYYMMDD`);
   only create a new note when nothing covers the entity.

## Step 1 — placement

- Domain concept → matching CLC folder under `🗂️ Classifications/`, flat (never nested deeper).
- **Protein family / protein concept** → `🗂️ Classifications/Q51 蛋白质/NOTES/<Note>/<Note>.md` — folder plus a
  **same-named folder note** for anything new. The same directory also holds legacy bare `.md` notes; leave
  those filenames alone. Verified members of this class: `Fluorescent protein/`, `Glycoprotein/`,
  `Metalloprotein/`, `Protein folding/`, `Peptide.md`.
- When an entity belongs to two classes (protein × immunology, protein × plant science), keep **one** note in
  Q51 and express the second class through `parents:` + `# RELATED NOTES` — do not fork the note.

## Step 2 — frontmatter and body (family-note house style)

```yaml
---
cssclasses:
  - wide
aliases:
  - <English name>
  - <every common abbreviation and old name>
  - <中文别名>
tags:
  - Memos/Proteins/Families
parents:
  - "[[Q51 蛋白质]]"
  - "[[<second CLC note, e.g. Q94 植物学>]]"
keywords:
  - <5–12 searchable terms>
---
```

Body skeleton: `# ABSTRACT` (one paragraph: what it is + how it relates to the neighbouring concept) →
topical sections (architecture / classification / mechanism / concrete instances — tables are fine) →
`# REFERENCES` → `# MEMOS` dataview block → `# RELATED NOTES`.

`# MEMOS` block, copied from the family notes with only the keyword swapped:

```dataview
TABLE abstract AS Abstracts, references AS References FROM #Snippets
WHERE icontains(keywords, "<keyword>") OR contains(parents, this.file.link)
```

Give concrete anchors instead of abstractions: PDB ID + resolution + chain composition, gene counts, species
names, measured numbers. Density expected: an NLR note carries `PDB 6J5T (cryo-EM 3.4 Å, 15 chains =
5×[ZAR1 852 aa + RKS1 351 aa + PBL2 426 aa])` and `A. thaliana Col-0: 149 NLR genes`.

## Step 3 — check alias collisions, not just filenames

A generic abbreviation may already be claimed by a note in **another CLC class**. Real example:
`Q939.91 免疫学/Pattern recognition receptor/NOD-like receptor/NOD-like receptor.md` lists `NLR` in its
`aliases`, so a plant NLR note must not be called `NLR`.

Procedure: grep the abbreviation as a *content* search across `*.md` and read each hit's `aliases:` block.
On collision, name the new note with a qualifier (`Plant NLR`, not `NLR`), state the distinction explicitly in
`# ABSTRACT`, and cross-link both ways in `# RELATED NOTES`. Never merge into the other class's note and never
edit its `aliases`.

## Step 4 — verify every citation before it enters the note

Never write a reference title, journal, volume, or article number from memory. Search each one and confirm
title + year + volume/article number first; if it cannot be confirmed, mark it TBD rather than inventing it.
A remembered title can be flatly wrong (a 2022 *Science* paper about TIR-catalysed small molecules), and the
wrong string lives in the vault until someone notices. Correct a wrong entry with `patch` immediately instead
of appending a correction below it.

## Step 5 — post-write verification (do not skip)

Run this skill's script against the finished note:

```bash
python3 "<skill_dir>/scripts/verify_note.py" "<note path>" --vault "<vault root>"
# no PyYAML in the interpreter? Hermes' own python lacks it:
uv run --quiet --with pyyaml python3 "<skill_dir>/scripts/verify_note.py" "<note path>" --vault "<vault root>"
```

It reports frontmatter keys, the `#` section list, line count, and every `[[wikilink]]` that does not resolve
to a real `.md` in the vault; exit code 1 means unparsable frontmatter or an unresolved link. Fix and re-run
until it prints `RESULT: OK` — a note that ships broken links or broken YAML silently drops out of dataview
and graph view.

## Pitfalls

- **Multi-note writes need the plan first.** Any request touching more than one file (index + members,
  MEMOS + Snippet, template use) goes: propose filenames/paths/sections in a table → wait for explicit
  confirmation → then write. Standing user preference, not a suggestion.
- **Do not assume the note type from the topic alone.** Protocol notes, software notes, TP393 protocol notes,
  MEMOS records and entity notes each have their own folder + frontmatter rules; consult the bundled
  `obsidian` skill's type sections before allocating a path.
- **Search hits are evidence about a note, not about the user's situation** — never restate a vault fact as
  "your sample/reagent is X".
- **Definitional answers do not come with a note attached.** Write the note when the user asks for it; before
  that, offer it in one line at the end of the answer.
