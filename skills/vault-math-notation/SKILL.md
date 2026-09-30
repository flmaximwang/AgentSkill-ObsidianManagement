---
name: vault-math-notation
description: Format mathematical notation in Obsidian vault notes — TeX conventions, crystallography symbols, and rendering best practices.
platforms: [macos]
---

# Vault Math Notation

When writing mathematical, crystallographic, or scientific notation in Obsidian vault notes, follow these conventions. **This is a strong user preference.**

## Core rule: TeX only

Always use `$...$` (inline) or `$$...$$` (display) math mode:

| ❌ Wrong | ✓ Correct |
|----------|-----------|
| `C₂ᵥ` (Unicode subscript) | `$C_{2v}$` |
| `P2<sub>1</sub>` (HTML) | `$P2_1$` |
| `P1̄` (Unicode combining overline) | `$P\bar{1}$` |
| `½` (Unicode fraction) | `$1/2$` or `$\tfrac12$` |
| O_h (bare underscore) | `$O_h$` |
| `K$_3$Fe(CN)$_6$` (manual subscripts) | `$\ce{K3[Fe(CN)6]}$` |

### Chemical formulas: use `\ce{}` (mhchem)

Obsidian's MathJax bundles mhchem, and the user **actively relies on it** — he hand-edited a note from `K$_3$Fe(CN)$_6$` to `$\ce{K3[Fe(CN)6]}$`. Wrap whole chemical species in `$\ce{...}$`: `$\ce{K3[Fe(CN)6]}$`, `$\ce{Na2S2O4}$`, `$\ce{H2S}$`, `$\ce{H2O}$`.

Do NOT hand-place `_2` subscripts. Limits of this preference: reagent names used as plain prose labels (`NaOH`, `Tris`, `HEPES`, `吡啶`) stay plain text — the user did not convert those, so don't either. Convert the molecular formulas that were carrying markup, not every occurrence of every reagent.

## Crystallography conventions

| Notation | TeX form | Example |
|----------|----------|---------|
| Screw axis | `$N_m$` | `$6_3$`, `$2_1$` |
| Rotoinversion | `$\bar{N}$` | `$\bar{4}$`, `$\bar{1}$` |
| Space group (full) | Wrap WHOLE symbol in `$...$` | `$P2_1/c$`, `$Fm\bar{3}m$` |
| Split by `\bar` | Do NOT fragment: `$P\bar{4}2m$` not `P$\bar{4}$2m` | |
| Schönflies | `$C_{2v}$`, `$D_{2h}$`, `$O_h$` | |
| Crystal coordinates | `$(x,y,z)$`, `$(\bar{x}, y, \bar{z})$` | |
| Seitz operator | `$\{2_{010} \mid \tfrac12,0,0\}$` | |

## Space-group table writing

When writing the 230 space group tables into a note:

1. Every HM symbol in its own `$...$` block — including symbols without subscripts (`$P2/m$`, `$P222$`)
2. Symbols with `\bar` (rotoinversion): `$P\bar{4}2m$`, `$P\bar{3}1m$` — one block, no splitting
3. Symbols with subscript: `$P2_1/c$`, `$P4_2/mmc$`
4. Point-group column (rotoinversion only): `$\bar{4}$2m` is acceptable since `\bar{4}` must be in math but `2m` following is plain text

## Space group tables: coset interpretation

Each row in a space group table is **one left coset of $T$ (the translation subgroup) in $G$ (the full space group)**. Below is the complete chain from definition to space-group table, following the mathematical progression.

### 1. 群 $G$

空间群 $G$ 是所有对称操作（旋转、平移、反射、滑移）的集合，构成群。

### 2. 子群 $T \\leq G$

$T = \\{\\{1 \\mid \\mathbf{t}\\} \\mid \\mathbf{t} \\in \\Lambda\\}$ 是所有纯晶格平移的集合。$T$ 是 $G$ 的子群。

### 3. 陪集（coset）

**定义.** 设 $H \\leq G$，$g \\in G$。称

$$
gH := \\{ gh \\mid h \\in H \\}
$$

为 $H$ 关于 $g$ 在 $G$ 中的左陪集（left coset of $H$ in $G$ with respect to $g$）。

**注意**：$g$ 遍历所有 $G$，**没有** $g \\notin H$ 的限制。当 $g \\in H$ 时，$gH = H$（$H$ 本身也是自己的一个陪集）。"陪"字可能让人以为只有不在 $H$ 中的元素才有陪集，但定义并不排除 $H$ 自身。

陪集性质：
- $\\bigcup_{g \\in G} gH = G$（覆盖）
- $g_1 H \\cap g_2 H \\neq \\varnothing \\implies g_1 H = g_2 H$（不交，即陪集划分 $G$）

### 4. 正规子群 $T \\trianglelefteq G$

$T$ 在 $G$ 中是正规的，因为 $\\forall g = \\{R \\mid \\mathbf{u}\\} \\in G$，$\\forall t = \\{1 \\mid \\mathbf{v}\\} \\in T$：

$$
g t g^{-1} = \\{1 \\mid R\\mathbf{v}\\} \\in T
$$

晶格在点群操作 $R$ 下不变，所以旋转后的晶格平移仍是晶格平移。

正规子群保证左陪集 = 右陪集（$gT = Tg$），这是商群运算 well-defined 的必要条件。

### 5. 商群 $G/T$

**定义.** 设 $N \\trianglelefteq G$。商群定义为

$$
G/N := \\{\\, aN \\mid a \\in G \\,\\}
$$

配上运算 $(aN)(bN) := (ab)N$。需要验证该运算与代表元的选取无关（well-definedness 依赖于正规性）。

对空间群 P2：

$$
\\text{P2} / T \\cong C_2, \\quad [\\text{P2}:T] = 2
$$

### 6. 同态基本定理（第一同构定理）

**定理.** 设 $\\varphi: G \\to K$ 是群同态。则 $G/\\ker\\varphi \\cong \\text{Im}\\varphi$。

对空间群，定义 $\\varphi: G \\to \\text{点群}$ 把每个操作映射到其旋转部分（去掉平移）。$\\ker\\varphi = T$，故 $G/T \\cong \\text{点群}$。

### 7. 回到国际表

国际晶体学表中的每一行是一个陪集的**代表元**：

| 表中所列（代表元） | 对应的 $T$ 在 $G$ 中的左陪集 | 包含的实际操作 |
|------------------|---------------------------|-------------|
| $\\{1 \\mid 0\\}$ | $T = eT$ | 所有纯晶格平移（无限多） |
| $\\{2_{010} \\mid 0\\}$ | $\\{2_{010} \\mid 0\\}T$ | 转 180° 再作任意晶格平移 |
| $\\{m_{010} \\mid 0\\}$ | $\\{m_{010} \\mid 0\\}T$ | 反射再作任意晶格平移 |

行数 = 指数 $[G:T]$ = 陪集个数 = 点群的阶。

### 何时写这些内容

写空间群表格、一般等效位置、或解释空间群与点群的关系时，必须在文中建立 **群 → 子群 → 陪集 → 正规子群 → 商群 → 同态定理 → 空间群具体例子** 的完整链条。不要跳过中间步骤。

具体检查清单：
- 是否指定了"谁在谁中的陪集"？（如"$T$ 在 $G$ 中的左陪集"而非仅"陪集"）
- $G/N$ 的定义是否写了 $a \\in G$（遍历所有元素）而非 $a \\notin N$？
- 是否区分了"陪集"（对任意子群可定义）和"商群"（要求正规子群）？
- 是否用具体空间群（P1 一行、P2 两行、P2₁/c 四行）说明了陪集个数与点群阶的关系？

### 具体例子：P2₁/c (#14) 的 4 个等效位置

$$
(x,y,z), \\quad (\\bar{x},\\; y+\\tfrac12,\\; \\bar{z}), \\quad (\\bar{x},\\bar{y},\\bar{z}), \\quad (x,\\; \\bar{y}+\\tfrac12,\\; z)
$$

这 4 行对应 $[G:T] = 4$，点群 $C_{2h}$。

## Writing full operation tables (12‑example reference)

When writing comprehensive space group examples (like the 12 in this note), use this structure per entry:

1. **HM symbol + IT number + crystal system + lattice type + symmorphic?**
2. **Generators** — list the generating operations in Seitz notation
3. **Full operation table** — Seitz + coordinate transform
4. **For high-order groups (>16 ops)**: list generators + representative key operations only, note the total count
5. **Comparison table** at the end: # / HM / lattice / generator count / total ops / prototype structure

Each Seitz entry MUST be in a single `$...$` block:
- ✓ `$\{2_{010} \mid \tfrac12,0,0\}$`
- ✗ `$\{2_{010} \mid$ ` outside math

Coordinate transforms in `$(x,y,z)$` notation:
- `$(\bar{x}, y+\tfrac12, \bar{z})$`, NOT `$(-x, y+1/2, -z)$`

## Mathematical exposition style (user preference)

When writing mathematical definitions and derivations in vault notes:

- **Start from definitions**. State the group, the subgroup, the operation explicitly. E.g. "设 $H \leq G$，$g \in G$。称 $gH := \{gh \mid h \in H\}$ 为 $H$ 关于 $g$ 在 $G$ 中的左陪集" — NOT "左陪集就是……" without context.
- **No unnecessary conditions**. The definition of $G/N = \{aN \mid a \in G\}$ does not require $a \notin N$. Do NOT split into cases ("$N$ itself plus the rest") unless the logic actually requires it.
- **No analogies**. Do NOT reach for "think of it like integers modulo 3" unless the user explicitly asks. Pure deduction from definitions.
- **Complete the full chain**: definition → key properties (with proof sketch) → connection to the specific object (space group, crystal system). Don't stop mid-way.
- **Explicit context for every symbol**: "$\ker\varphi$ 是 $G$ 到 $K$ 的同态", not just "$\ker\varphi$".

## Pragmatism rule

If 95%+ of symbols are correctly in TeX and the remaining edge cases require elaborate multi-pass regex scripts to fix, **stop and accept the current state**. Do not chase the last 5% with increasingly complex workarounds — the user considers this wasted effort.

## Why not Unicode or HTML

| Format | Problem |
|--------|---------|
| Unicode subscript (₁₂₃ᵢₕ) | Rendering varies by font, platform, and Obsidian theme |
| Unicode combining overline (X̄) | Breaks on copy-paste, invisible in search, font-dependent |
| HTML `<sub>` / `<sup>` | Obsidian may or may not resolve them; inconsistent |
| Bare `_` in markdown | Parsed as italic emphasis — breaks the text |

TeX in Obsidian renders via MathJax/KaTeX which is deterministic and platform-independent.
