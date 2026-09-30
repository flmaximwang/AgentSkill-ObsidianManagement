# AgentSkill-ObsidianManagement

Obsidian vault 维护类 skill 的合集。每个 skill 自带**可执行脚本 + 自检**，默认 dry run。

## 索引

| skill | 用途 | 可执行入口 |
|---|---|---|
| [organize-obsidian-notes](skills/organize-obsidian-notes/SKILL.md) | 成百上千条嵌套笔记 → 「同名父文件夹 + 字母索引桶」 | `scripts/organize_notes.py`、`organize.sh`、`test_organize_notes.py` |
| [notes-subtree-extraction](skills/notes-subtree-extraction/SKILL.md) | 笔记子树 → **新的 git 仓库**（跨仓库迁移 + 链接完整性 + 源历史清理） | `references/subtree-to-new-vault.md`、`references/history-purge-filter-repo.md` |
| [book-to-quiz](skills/book-to-quiz/SKILL.md) | 知识书 / 长文档 → vault 里的习题集（+ 答案册） | `scripts/export_answer_book.py` |
| [obsidian-article-atomization](skills/obsidian-article-atomization/SKILL.md) | 外部文章 → 多个原子笔记，并接入已有笔记图谱 | `scripts/verify_wikilinks.py` |
| [obsidian-qa-discussion](skills/obsidian-qa-discussion/SKILL.md) | 多轮技术问答讨论 → 结构化 vault 笔记（两种格式分支） | `scripts/verify-note-edit.py` |
| [obsidian-bases](skills/obsidian-bases/SKILL.md) | 写 / 改 Obsidian Bases 的 formula、filter、summary | —（纯流程；官方文档取源见正文） |
| [obsidian-snippet](skills/obsidian-snippet/SKILL.md) | 创建 / 管理碎片笔记 Snippets（Dataview 检索） | —（模板 + 流程） |
| [obsidian-theme-development](skills/obsidian-theme-development/SKILL.md) | Workbench 主题的样式 / 打印 / 发布维护 | `scripts/cdp.py` |
| [obsidian-vault-bulk-move](skills/obsidian-vault-bulk-move/SKILL.md) | git vault 里成百上千个文件夹的重排 | —（顺序本身即安全保证，见正文） |
| [vault-math-notation](skills/vault-math-notation/SKILL.md) | vault 笔记里的数学 / 晶体学 / 化学记号约定 | —（约定，强制用户偏好） |
| [obsidian-entity-notes](skills/obsidian-entity-notes/SKILL.md) | 单主题实体笔记（蛋白家族 / 化合物 / 数据库）的落位与写作规范 | `scripts/verify_note.py` |
| [obsidian-howto-notes](skills/obsidian-howto-notes/SKILL.md) | 工具 how-to / 文档笔记的骨架与提交规范 | —（纯流程） |

装进 Hermes（三段式标识符，按仓库内路径，**不需要 tap**；`--category` 只决定落点）：

```bash
for s in organize-obsidian-notes notes-subtree-extraction book-to-quiz \
         obsidian-article-atomization obsidian-qa-discussion obsidian-bases \
         obsidian-snippet obsidian-theme-development obsidian-vault-bulk-move \
         vault-math-notation obsidian-entity-notes obsidian-howto-notes; do
  hermes skills install "flmaximwang/AgentSkill-ObsidianManagement/skills/$s" --category obsidian -y
done
```

安装时会 pin 到当时的 commit，之后 `hermes skills check` / `hermes skills update <name>` 直接可用。

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

## skills/notes-subtree-extraction

把一个**笔记子树**从原 vault 搬进**新的 git 仓库**——跨仓库这一步，外加只有写进第二个仓库时才会踩的坑。
与 `obsidian-vault-bulk-move` 的分工：那个管**仓内**重排，它的回滚 / ledger 机制在这里同样适用。

顺序即安全保证：先勘察源与目标（README / `git log` / `git status`）→ **一次澄清**（源是移走还是复制、分桶键、
二进制跟不跟走、目标是否独立 vault、remote/LFS）→ 分类只看路径 / 文件名 / frontmatter（**不读正文**）→
在目标仓库里**按 pathspec 精确 add**（`git add -A` 会把用户未提交的改动卷进你的 commit）→
源文件数（去掉 `.DS_Store` / `.trash`）与目标逐一相等后才允许删源 → 三条断言（无同名嵌套目录、NFC 规范化后
tracked == on-disk、外链代价量化）→ 最后才清源历史。

```bash
# 源历史里抹掉已迁走的路径（必须在目标逐字节可证之后）
git filter-repo --path <已迁走的路径> --invert-paths
```

分类配方、审计代码与报告格式见 [references/subtree-to-new-vault.md](skills/notes-subtree-extraction/references/subtree-to-new-vault.md)，
源历史清理的完整 rehashing / 演练流程见
[references/history-purge-filter-repo.md](skills/notes-subtree-extraction/references/history-purge-filter-repo.md)。

## skills/book-to-quiz

知识书 / 长文档（PDF、EPUB、MD、HTML、TXT）→ 用户 vault 里的**习题集**（每章一组题 + 可打印答案册）。

硬性规则（用户 2026-09 锁定，不得静默放宽）：只出**回忆式**题型（概念、举例、推导、应用），
禁选择题 / 填空 / 判断 / 找错；题干不得呈现错误命题或待找的错；每题必带难度（☆/☆☆/☆☆☆）
+ 答案与解析 + 出处（找不到就写 `出处：TBD（待核对）`，**不编页码**）；覆盖驱动——以结构化知识点为单元，
每点至少映射 1 题，不按固定配额凑题；答案分离（默认 `> [!answer]-` 折叠 callout）。

```bash
# 导出独立答案册（幂等：每次从习题文件全量重建，手改会被覆盖）
python3 scripts/export_answer_book.py <习题目录> [输出路径]   # 默认 <习题目录>/答案册.md
```

脚本只处理匹配 `ch*.md` 的文件，并跳过 `答案册.md` 自身。流程里另有两处硬约束：**生成计划要先给用户确认**，
以及**写完后做质量自检**（wikilink 全部可解析、`[!answer]-` 块成对、覆盖矩阵数字与实际题数一致）。

## skills/obsidian-article-atomization

外部文章（微信公众号长文、网页长读）→ **多个原子笔记**（一概念一笔记），并链进已有笔记图谱。
用户对成功的定义很明确：不是一篇大杂烩笔记，也不要孤儿笔记。

流程固定且按序执行：抽全文 → **先勘察 vault**（CLC 归类目录、可链接或可合并的既有笔记）→ 出原子化计划
**等待确认** → 备份后写入 → 全部写完后验证。微信 `mp.weixin.qq.com` 上 `web_extract` 只回标题，
要走 curl + `#js_content` 解析（见 `web-content-extraction` Tier 3）。

```bash
python3 scripts/verify_wikilinks.py <vault_root> <file1.md> [file2.md ...]
```

收集 vault 内所有 `*.md` basename（外加 `*.base`，它也是合法的 `![[embed]]` 目标）→ 抽取所列文件里的
`[[...]]` 目标 → 报告解析不到的；有断链则退出码 1。`![[...]]` 嵌入会被跳过（图片在 `assets/` 下，
basename 查不到属正常）。

坑：名称含 CJK / π / emoji 时 `search_files` 的 glob 会**静默返回 0 命中**——实测 `*π*` 漏掉已存在的
`蛋白质中涉及π体系的相互作用/蛋白质中涉及π体系的相互作用.md`。判定「笔记不存在」前必须 `ls` 父目录。

## skills/obsidian-bases

写或改 Obsidian Bases（`.base` 文件与内嵌 `![[X.base]]` 块）的 formula / filter / summary，任意 vault 通用。

**架构决定什么做不到，先看架构再承诺查询**：

| 组件 | 看得见什么 | 结论 |
|---|---|---|
| filters | base 数据集里的**每一条**笔记 | 跨笔记匹配只能写在这里（如 `note["culture-pellet-source"].contains(this.note["UID"])`） |
| formulas | 只有当前行 + `this` 上下文 | **没有** `notes()`，无法查询或聚合其他笔记 → 不能承诺「跨笔记求和 / rollup / 其他笔记列表」列 |
| summaries | 视图的所有行 | 「对全部命中笔记求和」的真正做法（内置 Sum/Average，或用 `values` 自定义） |

`this` 的含义随嵌入位置变：嵌在笔记里 = 嵌入它的那篇；独立打开 = base 文件本身；侧边栏 = 当前活动文件。
逐行取值一律用未限定的属性名（`prop` / `note["prop"]`），不要用 `this`。

官方文档 `help.obsidian.md` 是 JS 渲染的（`web_extract` 只拿到 TOC），要从 GitHub `obsidianmd/obsidian-help`
取 markdown：`en/Bases/Formulas.md`、`en/Bases/Functions.md`、`en/Bases/Bases syntax.md`（文件名里有空格）。

用户偏好：优先**改已有的 `.base`**（加公式列 / 汇总行）并先展示具体改动——这条是防止在有 base 覆盖的数据上
另建新文件，并不禁止新建；用户在还没有 base 的记录上要求「用 Obsidian 数据库插件展示」时，建 base 本身就是需求。
公式速查见 [references/bases-formulas.md](skills/obsidian-bases/references/bases-formulas.md)。

## skills/obsidian-qa-discussion

用户就某技术主题连续追问「为什么」，随后要求存进 vault 时使用。**触发措辞决定输出格式**，这是最容易错的地方：

| 触发措辞 | 产出 |
|---|---|
| 「把讨论记录 / 归纳总结到 Obsidian」「存成笔记」 | **Q&A 逐问逐答稿**——编号小节与推理链对应 |
| 「先整理一下」「把这个内容整理成笔记」「整理」 | **知识参考笔记**——百科式分节（定义、机制、实验、应用…），不是对话回放 |

后一种被读成 Q&A 稿是明确记录过的错误。流程另含：定位 CLC 分类 → 结构化 → 处理媒体（图与脚本落到笔记同目录的
`assets/`、`scripts/`，脚本 docstring 写明跑法与**哪个解释器装了依赖**）→ 更新交叉链接 → **程序化验证**。

```bash
python3 scripts/verify-note-edit.py <vault_root> <note.md> [<backup.md>]
```

每次改完笔记都要跑；它替掉「ls 目录 + 读回笔记」这种肉眼看：① YAML frontmatter 能解析；② 与备份做行集合 diff，
把**消失的行**逐条列出（只看「原行都还在」的布尔量没用——订正过的标题是合法删除，布尔会变 False 而分不出
「故意重写」和「静默丢数据」）；③ 所有 `[[wikilink]]` 解析到真实 `.md`；④ 所有 `![[embed]]` 按笔记相对与
vault 相对两种路径在文件系统上存在。干净退 0，任一检查失败退 1（可直接作为门禁）。
`references/electromagnetic-soliton-deep-dive.md` 是一份完整实例。

## skills/obsidian-snippet

创建 / 管理 **Snippet（碎片笔记）**：按 年 / 月 / 日 / 时间戳 组织在 `📝 Snippets/` 下，每条带结构化
frontmatter（`tags`、`parents`、`abstract`、`keywords`、`references`），靠 Dataview 做跨笔记检索。

定位：MEMOS 笔记是「主条目」（一个蛋白质、一个基因的完整记录），Snippet 是挂在某个主条目上的碎片
（一个实验条件、一种结晶方法），通过 `parents` 关联。完整方法论 / 综述 → `📚 Literatures/` 或
`🗂️ Classifications/`，不是 Snippet。

模板在 [skills/obsidian-snippet/SKILL.md](skills/obsidian-snippet/SKILL.md) 里给出（`📝 Snippets/_Snippets_.md`，
vault 根下、不在 `🌏 Public` 里）的 frontmatter 与正文结构；三条创建路径（手动 / Hermes Agent 当前工作流 /
Templater 自动化）、MEMOS 粒度规则（主条目 ~50–80 行，超出的按主题拆成独立 Snippet）、Snippet 索引表模式，
以及已在 1518 文件规模上验证的 Inbox → Snippets 归档流程都在正文。

## skills/obsidian-theme-development

主题开发与维护。用户主题是 **Workbench**（浮动侧栏 + 打印优化），仓库 `~/Repositories/Obsidian-Workbench-CSS`；
官方文档 `docs.obsidian.md` → Themes。

- 形态与构建：`src/**/*.css`（嵌套、`@import`）→ **`theme.css`**，由 PostCSS 构建
  （`postcss-import-ext-glob` + `postcss-import` + 本地 `postcss-collect-settings.js`）。
  `npm run build` == `postcss src/main.css -o theme.css`。`theme.css` 是构建产物，**永远手改 `src/` 再重建**。
- `postcss-collect-settings.js` 把所有 `src/` 里的 `/* @settings ... */` YAML 注释**提升**到 `theme.css` 顶部
  （Style Settings 只扫构建后的文件），所以 `@settings` 写在对应 CSS 旁边、构建后汇总成一块。
- `manifest.json` 的 `minAppVersion` 意思是「比这更旧的 Obsidian 装不上」，只有真的用到更新的 CSS 才抬高。
- 测试 vault：`VaultExample/`、`tests/TempVault`；vault 的 `.obsidian/appearance.json` 里 `cssTheme` 必须等于
  `.obsidian/themes/` 下真实存在的主题目录名。
- 发布清单、打印 / PDF 测试路径与踩过的坑见正文及
  [references/print-and-pdf-pipeline.md](skills/obsidian-theme-development/references/print-and-pdf-pipeline.md)、
  [references/electron-cdp-inspection.md](skills/obsidian-theme-development/references/electron-cdp-inspection.md)、
  [references/obsidian-dom-and-embeds.md](skills/obsidian-theme-development/references/obsidian-dom-and-embeds.md)。

```bash
# 经 CDP 抓 Obsidian（Electron）打印态 DOM / 计算样式 / PDF
python3 scripts/cdp.py targets
python3 scripts/cdp.py --target app  dump --out captures --media print   # 也可 --target webview：插件的打印文档
python3 scripts/cdp.py --target app  styles --media print
python3 scripts/cdp.py --target app  pdf --out out.pdf --pagesize A4 --background
python3 scripts/cdp.py png out.pdf --dpi 110
python3 scripts/cdp.py pxdiff a.png b.png --out diff.png
```

依赖 `websocket-client`；`png` / `pxdiff` 另需 poppler 与 imagemagick。已端到端验证的加强版（多一个 HTML 结构
diff 子命令）在 `~/Repositories/Obsidian-Workbench-CSS/tools/print-harness/cdp.py`。

## skills/obsidian-vault-bulk-move

git 跟踪的 vault 里做批量重排（上百个分类文件夹归入桶、层级改名、任何大规模 `mv`）。
**顺序本身就是安全保证**，四步不可跳过：

1. **快照**：`git add -A && git commit` 并记下 hash；开工前先告诉用户回滚命令（`git reset --hard <hash>`）。
2. **dry run**：在内存里算完整映射（source → target），渲染目标树，断言不变量（无重复目标、每项恰好落一次、桶上限）。
3. **先建齐所有目标父目录**（对*全部*桶路径 `mkdir -p`），**再**搬条目。否则第一个目标桶还不存在的条目会被
   「改名」成那个桶（`shutil.move(src, dst)` 在 `dst` 缺失时就是 rename），后续条目落成它的子节点——静默结构损坏。
4. **搬完按算出来的树验证**，不靠眼看：逐个桶比对 `set(os.listdir(bucket))` 与期望子集，统计落位条目数、
   前后目录/文件数。

数据丢失的失败模式（撞名、大小写不敏感文件系统、跨盘、符号链接等）与「真正能证明没丢东西」的验证方法见正文，
判定用 git 侧对照而不是 `ls`：

```bash
git ls-tree -r -z <snapshot> -- <dir>     # 快照里有、现在不在的 blob = 真丢
git ls-files -s -z -- <dir>               # 在 `git add -A` 之后跑
```

## skills/vault-math-notation

写 vault 笔记里的数学、晶体学、科学记号时遵守的约定（**强用户偏好**）。

核心：**只用 TeX**——`$...$` 行内、`$$...$$` 行间。`C₂ᵥ`（Unicode 下标）、`P2<sub>1</sub>`（HTML）、
`P1̄`（组合上划线）、`½`、裸 `O_h`、手写下标 `K$_3$Fe(CN)$_6$` 全部不接受；化学式用 mhchem
（Obsidian 的 MathJax 自带，用户在**依赖它**——他亲手把一条笔记从 `K$_3$Fe(CN)$_6$` 改成 `$\ce{K3[Fe(CN)6]}$`），
整物种包在 `$\ce{...}$` 里。晶体学符号、空间群表写法、陪集 / 商群那套解释框架（12 个例子的完整操作表参考），
以及「什么时候才该写这些」的务实规则都在正文。

## skills/obsidian-entity-notes

**单主题实体笔记**（蛋白家族、蛋白概念、化学 / 大分子实体、生物信息数据库）的落位与写作规范，
是 bundled `obsidian` skill 的配套（vault 路径解析、README-first 规则、多文件 explain-first 闸门仍在那边）。
触发：「note this in my Obsidian」/「记到 vault 里」+ 单个主题；补全已有的空 stub 笔记也算。

- 蛋白家族 / 蛋白概念 → `🗂️ Classifications/Q51 蛋白质/NOTES/<Note>/<Note>.md`（同名 folder note）。
- 跨类实体只留**一篇**，第二类用 `parents:` + `# RELATED NOTES` 表达，不分叉。
- 先查 **alias 撞名**，不只查文件名：`NLR` 已被免疫学那篇占走 → 新笔记叫 `Plant NLR`，并在摘要里写明区别。
- 每条引用先查证再落笔（题名 + 年 + 卷 / 文章号），查不到就写 TBD；密度要具体（PDB ID + 分辨率 + 链组成、基因数、物种名）。

```bash
python3 scripts/verify_note.py "<note path>" --vault "<vault root>"
# Hermes 自带解释器没有 PyYAML 时：
uv run --quiet --with pyyaml python3 scripts/verify_note.py "<note path>" --vault "<vault root>"
```

脚本报 frontmatter 键、`#` 小节表、行数、以及解析不到的 `[[wikilink]]`；干净时打印 `RESULT: OK`，
退出码 1 = frontmatter 不可解析或有断链。

## skills/obsidian-howto-notes

**工具 how-to / 文档笔记**（安装、配置、维护，或同一结果的多条路线）的骨架与提交规范，
同为 bundled `obsidian` 的配套。触发：「把具体的步骤记录到 Obsidian」、按用户给的骨架「重新组织你的笔记」、
把命令报错与诊断落进笔记。

骨架：每个路线 / 主题一个 `##`，四部分固定顺序——简介（1–2 行）→ `### 安装流程` → `### 维护流程` →
`### FAQs`（`-` 列表；实测输出、报错文本、机制、坑全放这里，不塞进步骤）。两条硬约束：

- **路径每个 session 重新解析**，写之前与 commit 之前再解析一次：vault 会在同一次任务的两步之间被重组
  （字母桶 / folder-note 转换），复用记住的路径会静默写出第二份副本。用 `rglob("<Title>*")` 并复用 glob
  原样打印的字符串（路径带 emoji 与括号，手抄会把 emoji 的变体选择符弄丢）。
- **证据纪律**：步骤里的命令必须真跑过；推断的机制标注「机制推断，未实测」；事后被实测推翻的那条**就地改写**，
  不能新旧并列——读者只会读到前一条。

提交时只 add 这一篇笔记的路径（vault 常年处于重组中），复用仓库已有的 message 前缀。
