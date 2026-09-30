# Obsidian Bases formulas — syntax & cross-note patterns

Verified against `obsidianmd/obsidian-help` GitHub raw markdown (`en/Bases/Formulas.md`, `Functions.md`, `Bases syntax.md`), the Obsidian forum thread "Bases Formula: Cross-Note Lookup & Rollup", and optional.page "Obsidian Bases Tips and Tricks".

## List functions use implicit variables, not arrows

`value` / `index` / `acc` are the implicit loop variables:
- Sum: `[1,2,3].reduce(acc + value, 0)` → 6 (official example)
- Filter: `list.filter(value > 2)`; map: `list.map(value + 1)`
- On mapped Files: `value.properties["prop"]` (Object field), `value.asLink()` to render

Globals: `if(cond, a, b)`, `number(x)`, `date()`, `today()`, `list(x)` (wrap scalar → list for robust `.map()`).

## Pitfall: quoted numerics are strings

YAML `culture-pellet-original-volume-ml: "500"` is a STRING. Sum (input type Number) and `+` misbehave on it ("500"+"500" string-concats). Convert first: `number(culture-pellet-original-volume-ml)`, then summarize that formula column.

## Pitfall: contains() semantics

`.contains(x)` on a scalar string = substring match; on a list = membership. Equivalent for full UUIDs, but a prefix substring-matches too — compare full values.

## Cross-note in formulas: only file.backlinks

`file.backlinks` (File field) lists notes that LINK to the current note — the one reverse-reference channel formulas can use:
```
'file.backlinks.map(value.asFile()).map(value.asLink())'
```
Caveats: backlinks exist only for real wikilinks (a bare `culture-pellet-source: <uuid>` string creates none); performance-heavy; does not auto-refresh on vault change; docs suggest reversing the lookup via `file.links` when possible.

## Summaries = the real cross-row aggregation

View-level:
```yaml
views:
  - type: table
    name: 表格
    order:
      - file.name
      - formula.pellet-volume-num
    summaries:
      formula.pellet-volume-num: Sum
```
Base-level custom summary (uses `values` = all row values of that property):
```yaml
summaries:
  totalVolume: 'values.map(number(value)).reduce(acc + value, 0)'
```

## Worked example: %Culture2Purification%.base (zsqlab08)

Embedded in each BacterialCulture note; rows = Purification logs sourcing this culture's pellet; the filter does the cross-note match, the summary does the sum:
```yaml
filters:
  and:
    - file.tags.contains("Logs")
    - note["culture-pellet-source"].contains(this.note["UID"])
formulas:
  pellet-volume-num: 'number(culture-pellet-original-volume-ml)'
views:
  - type: table
    name: 表格
    order:
      - file.name
      - culture-pellet-original-volume-ml
      - formula.pellet-volume-num
      - highlight
    summaries:
      formula.pellet-volume-num: Sum
```

## Building a whole base from scratch (row-per-note table)

Verified against a live build (24 record notes + one `.base`, 6 views) plus the vault's own pre-existing `.base` files.

Identifier and type pitfalls first:

- **Hyphens break arithmetic.** `m-domain * 25` parses as subtraction. Score/number properties get camelCase names (`mDomain`), or must be referenced as `note["m-domain"]`.
- **Non-ASCII property names need brackets**: `note["否决"] != ""`, `note["地点"].contains("杭州")`. Bare CJK identifiers in an expression are not safe.
- **Unquoted numbers only.** `mDomain: 5` is a Number; `mDomain: "5"` is a String and a weighted sum will string-concat or summarize as empty.
- **Formula/`values` names may be CJK** (`formulas: {档位: '...'}`) and are then referenced as `formula.档位` — but the *expression* referencing them stays ASCII-bracketed.

Skeleton (all of it valid; derived ranking, forced exclusion, per-view filters and summaries):

```yaml
filters:
  and:
    - file.tags.contains("岗位库")
formulas:
  matchScore: '((note["mDomain"] * 25 + note["mWetlab"] * 15 + note["mEng"] * 20 + note["mClosure"] * 25 + note["mThreshold"] * 15) / 5).round(0)'
  档位: 'if(note["否决"] != "", "C·排除", if(formula.matchScore >= 78, "A", if(formula.matchScore >= 68, "B", "C")))'
properties:
  note.公司:
    displayName: 公司
  formula.matchScore:
    displayName: 匹配分
views:
  - type: table
    name: 全部·按分数
    order: [file.name, 公司, formula.档位, formula.matchScore, 来源]
    sort:
      - property: formula.matchScore
        direction: DESC
    summaries:
      formula.matchScore: Average
    columnSize:
      file.name: 260
    indentProperties: true
  - type: table
    name: 只看某地区
    filters:
      and:
        - 'note["地点"].contains("杭州")'
    order: [file.name, formula.matchScore]
```

Notes that cost time otherwise:

- A formula can rank and bucket but **cannot look at other rows** — every cross-row number comes from a view `summaries` (Average/Sum/Count), not from a formula.
- Nested `if()` chains are the only way to derive a "weakest dimension" / label column; there is no `sort`/`min` over named properties.
- The hub note that embeds the base (`![[X.base]]`) is excluded automatically when the base filters on a tag the hub does not carry — do not add the tag "so it links up".
- Validate the whole set programmatically before claiming success:

```python
import yaml, glob, os
bad = []
for p in glob.glob(base_dir + "/*.md"):
    fm = open(p, encoding="utf-8").read().split("---", 2)[1]
    d = yaml.safe_load(fm)
    if any(k not in d for k in required) or not all(isinstance(d[k], int) for k in numeric):
        bad.append(os.path.basename(p))
yaml.safe_load(open(base_dir + "/X.base", encoding="utf-8").read())  # .base is YAML: parse it too
```

## Dataview fallback (per-row cross-note list/sum)

When a per-row rollup is needed (e.g. "each culture row shows its purifications / total"), Bases formulas cannot do it — use dataviewjs and join on the UID field:
```dataviewjs
const cultures = dv.pages('"Logs"')
  .where(p => p.tags && p.tags.some(t => String(t).startsWith('Pipelines/Bacterial-Culture')) && !p.file.name.startsWith('_'))
  .sort(c => c.file.name);
const purifs = dv.pages('"Logs"').where(p => p['culture-pellet-source']);
dv.table(['培养', 'UID', '纯化记录', '总用量 (ml)'], cultures.map(c => {
  const used = purifs.filter(p => [p['culture-pellet-source']].flat().includes(c.UID));
  return [c.file.link, c.UID, used.map(p => p.file.link), used.reduce((s, p) => s + Number(p['culture-pellet-original-volume-ml'] ?? 0), 0)];
}));
```