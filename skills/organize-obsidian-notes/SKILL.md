---
name: organize-obsidian-notes
description: Organize hundreds of notes in a path-saving hierarchical structure to accelerate Obsidian while avoid long paths unfriendly for Windows. Use when the user asks to "整理 Obsidian 笔记" / "organize Obsidian notes".
---

# Organize Obsidian Notes: 把成百上千的 Obsidian Notes 整理成高效的数据库形式

用户往往会将 Obsidian 的笔记按照主题整理成分层形式。对于复杂概念，这常常会造成大量嵌套，在文件存储层面不方便，降低 Obsidian 视图的展示效率，并产生对 Windows 不友好的超长路径（上限 255）。本方案将阐释将这些笔记整理为存储友好形式的流程。

## Basic procedures

- 第一步：确认目标文件夹已在 git 中提交，并且不存在未追踪文件与被 .gitignore 忽略的文件，避免整理错误导致数据丢失
- 第二步：确认目标文件夹为第n级索引文件夹。第n级文件夹具有 .index.<n> 文件，否则不是索引文件夹。
- 第三步：将所有的嵌套 md 在需要整理的目录铺平，并为没有同名父文件夹的 md 建立同名的父文件夹。
  - 例外：仅被一个 .md 使用 `![[]]` 嵌入的 `*.excalidraw.md` 作为附件而非笔记
- 第四步：将所有的笔记文件夹按照字母/拼音的第 n 个字母索引。
- 第四步：将所有的笔记文件夹按照索引分层保存。
- 第五步：逐个进入索引文件夹，检查该索引文件夹中的笔记数量，要求不多于26个。否则，从第二步继续。直到