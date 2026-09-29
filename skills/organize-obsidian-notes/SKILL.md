---
name: organize-obsidian-notes
description: Flatten deeply nested Obsidian note folders into a path-saving letter-index (A/, A/AB/...) with dry-run planning, git preflight, conflict guards and one-command rollback. Use when the user asks to 整理 Obsidian 笔记 / organize Obsidian notes / 铺平嵌套笔记 / 笔记按字母分桶, or complains about 超长路径 / Windows 255 限制 / Obsidian 视图太慢.
---

# Organize Obsidian Notes

把成百上千条嵌套笔记铺平成「同名父文件夹 + 字母索引桶」，并用 `.index.<n>` 标记索引层级。

解决的问题：笔记按主题层层嵌套 → 存储上不好用、Obsidian 视图效率低、产生 Windows 不友好的超长路径（上限 255 字符）。
目标形态：

```
Target/
  .index.1                 ← 标记「本层是第 1 级索引」
  A/                       ← 第 1 级桶
    .index.1
    AB/                    ← 第 2 级桶（仅当 A/ 内笔记 > 26 个时才出现）
      .index.2
      ACE2 from H. sapiens/ACE2 from H. sapiens.md
  B/
    BLAST/BLAST.md
```

## Before you run anything

| 你需要知道 | 事实 |
|---|---|
| 默认行为 | **dry run**：只读扫描、写一份 JSON 计划，磁盘不动。加 `--apply` 才落盘 |
| 撤销 | 每条计划自带 `--rollback <plan.json>`；未 git 跟踪的文件靠这份 JSON 找回 |
| 依赖 | 纯 stdlib（Python ≥ 3.9），无 pypinyin 也能跑（降级为码位序并**显式警告**） |
| 平台 | macOS / Linux / Windows；macOS 下自动用系统 ICU 做真拼音（`王小明→W`），零安装 |
| 幂等 | 已就位的笔记不再产生 move；重复 `--apply` 会收敛（见 Step 4） |

## Basic procedures

- **Step 1 · 定位目标并预检。** 目标可以是任意文件夹，脚本不假设它叫什么名字。
  ```bash
  python3 scripts/organize_notes.py --selftest                            # 拼音后端 + 分桶示例
  python3 scripts/organize_notes.py "<target>" --report plan.json         # dry run
  ```
  目标若处于 git 仓库且有未提交/被忽略文件，脚本会**拒绝执行**（退出码 2）——被 `.gitignore` 排除的
  `.pdf/.pdb/.json/.zip` 等文件 git 找不回，只有计划 JSON 是撤消依据。确认可以继续时加 `--allow-dirty`。

- **Step 2 · 读计划。** 🔴 **CHECKPOINT：必须把计划摘要展示给用户并得到确认，才能进 Step 3。**
  报告里逐条确认：`notes`（条数）、`moves`、`leaf buckets`、`fullest buckets`、`stays put`、`polyphone`（多音字待核），以及**所有 `[!]` 行**。
  退出码 **0** = 无致命问题；**3** = 计划不可执行（见「失败模式」）。

- **Step 3 · 执行。** 🔴 **CHECKPOINT：只有用户确认后才加 `--apply`。**
  ```bash
  python3 scripts/organize_notes.py "<target>" --apply --on-collision skip --report plan.json
  ```

- **Step 4 · 需要时再跑一次收敛。** 报告末尾出现
  `pass 2: N more move(s) available` 时，说明有容器要等笔记被抽走后才归属成某条笔记的附件——
  **再执行一次同样的命令**。实测 999 笔记子树：1096 → 38 → 2 → 0 moves（3 遍收敛）。

- **Step 5 · 回滚（如需）。** 计划链按**逆序**回滚，回到满意的那一步即停。
  ```bash
  python3 scripts/organize_notes.py --rollback plan.json      # 多条计划则从最新往回，逐条执行
  ```
  沙箱实测：3 遍 apply 后按逆序回滚 3 份计划 → `git status` 为空、文件数与内容逐字节还原。

## 规则细节（脚本已实现；改行为前先读源码）

| 规则 | 行为 |
|---|---|
| 铺平 | 每个 `.md` 移入「与其同名的父文件夹」；没有就建一个 |
| 索引桶 | 按排序键的第 n 个字符分桶，桶名 = 累积前缀（`A/AB/ABC`）；桶内 > `--limit`（默认 26）则继续下一字符 |
| 排序键 | 大小写归一 → 去除非字母数字 → 真拼音（`打孔蛋白→DAKONGDANBAI`）；`🧩 Actin (family)→ACTINFAMILY`、`α-synuclein→ASYNUCLEIN` |
| 多音字 | 首字符属于「两种读法首字母不同」的字表（重/仇/单/曾/解/查/区/乐/种/秘/繁/长/会/折/尉/覃）时，记入计划的 `polyphone_review` 字段并打印，**不自动改**。实测 `(MEMOS) Genes & Proteins`（745 条笔记）标出 5 条，其中 `重组表达…` 两条 ICU 取 zhòng→Z 而实际应 chóng→C |
| `.index.<n>` | 每个索引层一个标记文件，内容为层级号（`--index-content empty` 改零字节） |
| 附件跟随 | ① 名为 `X_assets/` 的目录归 `X`；② 目录内文件都被**同一条**笔记引用时归该笔记；③ 否则归最近的上层同名文件夹；都不满足 → 留原地并列 `stays put` |
| `.excalidraw.md` | 仅被一条笔记 `![[]]` 嵌入时当附件随行；被多条嵌入或无人嵌入则当普通笔记 |
| 容器 | 含笔记的容器只铺平、绝不整体跟随单条笔记；抽空的容器自动溶解 |
| 不进入 | `--preserve` 列出的目录（默认 `template,templates,data,assets,Scripts,.obsidian,.git,.trash`）整体跳过。实测 `👔 People` 里两个 `.excalidraw.md` 都在 `assets/` 下，故原地不动；`![[文件名.excalidraw]]` 按文件名解析，嵌入不受影响 |
| 根目录保留 | `README.md`、`index.md`、同名文件夹笔记（`Target/Target.md`）不动 |

## 失败模式与一线修复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 退出码 2 + `PREFLIGHT FAILED` | 目标在 git 仓库内：先 `git add -A && git commit` | 不想提交就加 `--allow-dirty`；被忽略文件的唯一撤消依据是计划 JSON |
| 退出码 3：`name collisions` | 两条笔记同名（含大小写冲突，macOS/Windows 会互相覆盖）→ 重命名其一 | 加 `--on-collision skip`：冲突笔记留原地，其余照常执行 |
| 退出码 3：`nested_src` / `dst_inside_src` | 一个 move 的源套在另一个 move 的源里（或目标落进源里）→ 脚本 bug，**不要 apply** | 保留 JSON 报告，`git diff` 核对工作树 |
| 退出码 4：`source vanished` / `destination already exists` | 扫描后目标被外部程序改动 → 重跑 dry run 出计划 | 已执行部分 `--rollback` 退回后重跑 |
| 退出码 1：apply 成功但 `verify:` 有行 | `over_limit_no_split`：一族名字共享长前缀（如 79 条 `(Obsidian) …`），字母索引在 `--max-level` 前分不开 | 调高 `--max-level`，或给这些笔记改名——**索引无法缩短名字本身** |
| 报告 `no pinyin backend` | 装 `pypinyin`，或 macOS 上指定 `--pinyin icu` | 接受码位序：CJK 散进 `_` 兜底桶，整理本身仍然正确 |
| 路径超过 `--max-path`（默认 240） | 报告给出最长路径及其构成 | 名字本身超长时唯一解是改名（报告会直说 an index cannot shorten a name） |
| `.base`/`.canvas` 引用了被溶解的文件夹 | 报告 `path_references` 逐条列出 | 整理后手改引用；`![[文件名]]` 嵌入按文件名解析，不受影响 |
| 命令中途被打断 | 用最近计划 `--rollback` 再重跑 | 计划 JSON 的 `applied` 字段是执行记录，半途失败也可逆 |
| 结果不满意 | `--rollback plan.json`（多条计划从最新往回） | 回滚会打印 `[!] not restored (…)` 逐条说明未能还原项，不静默跳过 |

## 反例黑名单（不要做的事）

| # | 不要做 | 为什么 | 替代做法 |
|---|---|---|---|
| 1 | 跳过 dry run 直接 `--apply` | 没人看过计划就落盘：冲突、超限、遗留文件全部不可见 | 先 dry run 并展示报告，用户确认后再 apply |
| 2 | 把 `--allow-dirty` 当默认 | 被 `.gitignore` 排除的 `.pdf/.pdb/.json/.zip` git 找不回 | 先提交；或明确告知风险后再用 |
| 3 | 在 vault 根目录直接跑 | 根目录含 `.obsidian/` 与其他主题树，一次动全库无法逐个复核 | 对单个子树跑、逐个确认 |
| 4 | 用 `git reset --hard` 收尾 | 丢未提交工作、断可追溯链 | `--rollback plan.json`（只反向搬动记录过的 move） |
| 5 | 手工改名/搬运后再 `--rollback` | 计划记的是绝对路径，手工改动会让回滚错位并报 `original path occupied` | 回滚后再做手工调整 |
| 6 | 加一段「删除所有空目录」的清理 | 会删掉刚落位的空附件目录（如 `_assets/` 唯一个文件被抽走后） | 只清理「曾装载过 move 源」的骨架目录（脚本已如此实现） |
| 7 | 硬编码 `database/` 之类的中间层名 | 目标可以是任意文件夹，中间层名字不固定 | 按「含笔记的容器」判定（`path_reference_scan` 接受任意 dissolved 列表） |
| 8 | 为达标把索引悄悄拆到 12 层 | 累积前缀让路径反而更长（实测 12 层桶前缀 90 字符，且仍有 42 条分不开） | 在 `--max-level` 处停下并报告，让用户决定改名 |
| 9 | 只看退出码不看 `[!]` 行 | 退出码 1 = 已执行但有告警，不是「全部干净」 | 逐条读 `[!]`，并在总结里转述 `verify:` 行 |
| 10 | 在未备份的库上直接 `--apply` | 本工具会移动上千个文件 | 先在 `cp -R` 的副本沙箱跑通（含 `git init`）再上真实库 |

## 脚本

| 路径 | 用途 |
|---|---|
| `scripts/organize_notes.py` | 主程序：扫描 → 计划 → 校验 → apply / rollback。默认 dry run |
| `scripts/organize.sh` | 一行启动器：自动挑解释器并跑 dry run 摘要（`./organize.sh <target> [apply]`） |
| `scripts/test_organize_notes.py` | 65 项断言自检，无需 pytest |
| `test-prompts.json` | 三个典型请求 + 期望产物（用于评测本 skill） |

```bash
python3 scripts/organize_notes.py --selftest                      # 本机能力与分桶示例
python3 scripts/organize_notes.py "<target>" --report plan.json   # dry run
python3 scripts/organize_notes.py "<target>" --apply --on-collision skip --report plan.json
python3 scripts/organize_notes.py --rollback plan.json
python3 scripts/test_organize_notes.py                            # 65 项自检
```

退出码：`0` 干净 ｜ `1` 已执行但有 verify 告警 ｜ `2` 预检/用法错误 ｜ `3` 计划有致命问题（未执行）｜ `4` 执行中途失败。

## 实测数据（999 笔记子树，2026-09-30，macOS 26.6.2 / Python 3.12.9）

被测目标是真实 vault 的 `wangfanlin1_Knowledge/🗂️ Classifications/T/TP/TP3/TP31/TP317 程序包（应用软件）`，
`cp -R` 一份副本后在副本上 `--apply`（真实库只跑 dry run）。复现：

```bash
cp -R "<该文件夹>" /tmp/tp317 && git -C /tmp init -q && git -C /tmp add -A && git -C /tmp commit -qm x
python3 scripts/organize_notes.py /tmp/tp317 --apply --on-collision skip   # 三遍直到无 pass 2 提示
python3 scripts/organize_notes.py --rollback <plan.json>                   # 逆序，逐份回滚
```

| 指标 | 整理前 | 整理后 |
|---|---|---|
| 笔记条数 | 999 | 999（无损） |
| 最长路径 | 364 字符 | 282 字符（瓶颈是笔记名本身 83 字符） |
| 每桶笔记数 | 单目录最多约 200 | 186 桶，185 桶 ≤ 26 |
| 收敛 | — | 1096 → 38 → 2 → 0 moves（3 遍） |
| 回滚 | — | 逆序回滚 3 份计划后 `git status` 为空，逐字节还原 |

未达标项（诚实记录）：`O/OB/OBS/OBSI/OBSID/OBSIDI/OBSIDIA/OBSIDIAN` 仍 79 条——它们是 `(Obsidian) …` /
`Obsidian …` 一族，共享 8 字符前缀，字母索引在不把路径拉得更长的前提下分不开。把 `--max-level` 放到 12
实测能让该桶从 79 降到 42，但桶路径前缀涨到 90 字符且仍未达标，故默认停在 8：解药是改名，不是继续加层。
