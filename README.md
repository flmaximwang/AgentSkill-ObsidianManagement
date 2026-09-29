# AgentSkill-ObsidianManagement

Obsidian vault 维护类 skill 的合集。每个 skill 自带**可执行脚本 + 自检**，默认 dry run。

## skills/organize-obsidian-notes

把成百上千条嵌套笔记铺平成「同名父文件夹 + 字母索引桶」，解决三件事：存储不便、Obsidian 视图慢、
Windows 超长路径（255 字符上限）。

```bash
cd skills/organize-obsidian-notes

# 1. 看本机能力（拼音后端、分桶示例）
python3 scripts/organize_notes.py --selftest

# 2. dry run：只读 + 写一份 JSON 计划，磁盘不动
python3 scripts/organize_notes.py "<target>" --report plan.json

# 3. 确认后执行（撞名笔记留原地，其余照常）
python3 scripts/organize_notes.py "<target>" --apply --on-collision skip

# 4. 需要时收敛（报告出现 "pass 2: N more move(s)" 时再跑一次同样的命令）
# 5. 回滚
python3 scripts/organize_notes.py --rollback plan.json

# 一行启动器（自动挑解释器，apply 前先自动跑一遍 dry run）
./scripts/organize.sh "<target>" [apply]

# 自检
python3 scripts/test_organize_notes.py
```

`target` 可以是**任意文件夹**——脚本不假设它叫 `database` 或任何固定名字。默认只碰这一个子树。

| 事实 | 值 |
|---|---|
| 依赖 | 纯 stdlib（Python ≥ 3.9）。pypinyin 可选：Linux/Windows 装了就用，没装自动降级并警告 |
| 平台 | macOS / Linux / Windows。macOS 走系统 ICU 得到真拼音（`王小明 → W`），零安装 |
| 默认行为 | dry run；`--apply` 才落盘 |
| 撤销 | 每条计划一行 `--rollback plan.json`；未被 git 跟踪的文件靠这份 JSON 找回 |
| 退出码 | `0` 干净 ｜ `1` 已执行但有 verify 告警 ｜ `2` 预检/用法错误 ｜ `3` 计划有致命问题（未执行）｜ `4` 执行中途失败 |
| 实测（999 笔记子树） | 最长路径 364 → 282 字符；186 桶中 185 桶 ≤ 26 条；1096 → 38 → 2 → 0 moves 收敛；逆序回滚后 `git status` 为空、逐字节还原 |

细节、失败模式与反例清单见 [skills/organize-obsidian-notes/SKILL.md](skills/organize-obsidian-notes/SKILL.md)。
