#!/usr/bin/env python3
"""Extract all [!answer]- callouts from chapter exercise files into a standalone answer book (答案册.md).

Usage:
    python3 export_answer_book.py <习题目录> [输出路径]

- 默认输出到 <习题目录>/答案册.md
- 幂等：每次从习题文件全量重建，无增量状态；手改答案册会被下次导出覆盖。
- 只处理匹配 ch*.md 的文件；跳过答案册.md 本身。
"""

import argparse
import re
import sys
from pathlib import Path

# 题目标题行：### 1.1 概念题 · ☆☆ · Ch1 §1.2 p.15
QUESTION_HEADER = re.compile(r"^###\s+(\d+\.\d+)\s+([^·]+?)\s*·\s*([^·]+?)\s*·\s*(.+)$")


def extract_question_blocks(ch_file: Path):
    """Split a chapter file into question blocks.

    Returns list of (header_line, question_body_without_answer, answer_lines).
    A block runs from a `### ` header to the next `### ` header. The answer is the
    `> [!answer`...` callout block; everything before it is the question body.
    """
    lines = ch_file.read_text(encoding="utf-8").splitlines()
    blocks = []
    cur = None  # dict: header, body[], answer[]
    in_answer = False

    for line in lines:
        m = QUESTION_HEADER.match(line.strip())
        if m:
            if cur:
                blocks.append(cur)
            cur = {"header": line.strip(), "body": [], "answer": []}
            in_answer = False
            continue
        if cur is None:
            continue
        stripped = line.lstrip()
        if in_answer:
            # callout continuation lines start with '>'; the callout ends on a blank line
            if stripped.startswith(">"):
                cur["answer"].append(line)
            else:
                in_answer = False
                if stripped:
                    cur["body"].append(line)
        else:
            if stripped.startswith("> [!answer"):
                in_answer = True
                cur["answer"].append(line)
            else:
                cur["body"].append(line)
    if cur:
        blocks.append(cur)
    return blocks


def strip_callout_marker(line: str) -> str:
    """Remove the leading '> ' (or '>') from a callout continuation line."""
    s = line.lstrip()
    if s.startswith("> "):
        return s[2:]
    if s.startswith(">"):
        return s[1:]
    return s


def build_answer_book(chapter_files, title="答案册") -> str:
    out = [f"# {title}", "", "> 由 export_answer_book.py 自动生成，勿手改；重新导出会覆盖本文件。", "> 想修改某题答案 → 编辑对应习题文件里的 `[!answer]-` callout，再重新导出。", ""]
    count = 0
    for ch_file in sorted(chapter_files):
        blocks = extract_question_blocks(ch_file)
        if not blocks:
            continue
        chapter_name = ch_file.stem
        out.append(f"## {chapter_name}")
        out.append("")
        for blk in blocks:
            out.append(f"### {blk['header'][4:]}")  # strip '### '
            out.append("")
            out.extend(blk["body"])
            out.append("")
            out.append("**答案与解析**")
            out.append("")
            if blk["answer"]:
                lines = [strip_callout_marker(l) for l in blk["answer"]]
                # 去掉首行残留的 [!answer...] 标记，让答案册干净可打印
                if lines and lines[0].startswith("[!answer"):
                    m = re.match(r"^\[!answer[^\]]*\]-?\s*", lines[0])
                    if m:
                        lines[0] = lines[0][m.end():]
                out.extend(lines)
            else:
                out.append("（本题未找到答案 callout，请检查习题文件）")
            out.append("")
            count += 1
        out.append("")
    out.append(f"共 {count} 题。")
    out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="从习题文件生成答案册（抽取 [!answer]- callout）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("directory", type=Path, help="习题目录（含 ch*.md 习题文件）")
    parser.add_argument("output", nargs="?", type=Path, default=None, help="输出路径（默认 <directory>/答案册.md）")
    args = parser.parse_args()

    directory = args.directory.resolve()
    if not directory.is_dir():
        sys.exit(f"错误：目录不存在 {directory}")

    chapter_files = [
        p for p in directory.glob("ch*.md")
        if p.is_file() and p.name != "答案册.md"
    ]
    if not chapter_files:
        sys.exit(f"错误：{directory} 下没有 ch*.md 习题文件")

    output = args.output.resolve() if args.output else directory / "答案册.md"
    content = build_answer_book(chapter_files)
    output.write_text(content, encoding="utf-8")
    print(f"已生成：{output}")
    print(f"处理章节文件：{len(chapter_files)}，题目总数：{content.count('**答案与解析**')}")


if __name__ == "__main__":
    main()
