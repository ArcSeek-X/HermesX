#!/usr/bin/env python3
"""校验仓库 AI 资产的一致性，供 CI / 本地预检使用。

检查项包括：CLAUDE.md 是否为指向 AGENTS.md 的符号链接、Copilot 入口是否引用规范来源、
.github/instructions 与 .claude/skills 必备文件是否齐全且引用 AGENTS.md、
.gitignore 是否包含放行 skills 目录的规则，以及 .claude 下是否存在不该被跟踪的产物。
任一项不满足即打印错误并以非零码退出；全部通过时输出 ``[ai-assets] OK``。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
CLAUDE = ROOT / "CLAUDE.md"
COPILOT = ROOT / ".github" / "copilot-instructions.md"
INSTRUCTIONS_DIR = ROOT / ".github" / "instructions"
CLAUDE_SKILLS_DIR = ROOT / ".claude" / "skills"

REQUIRED_INSTRUCTION_FILES = {
    "backend.instructions.md",
    "client.instructions.md",
    "governance.instructions.md",
}

REQUIRED_SKILL_FILES = {
    "README.md",
    "analyze-issue/SKILL.md",
    "analyze-pr/SKILL.md",
    "fix-issue/SKILL.md",
}

REQUIRED_GITIGNORE_SNIPPETS = (
    ".claude/*",
    "!.claude/skills/",
    "!.claude/skills/**",
)


def fail(message: str) -> None:
    """打印校验失败信息到标准错误并以状态码 1 退出。"""
    print(f"[ai-assets] ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def ensure_file_exists(path: Path, description: str) -> None:
    """确保给定路径存在；缺失时以带描述的相对路径信息报错退出。"""
    if not path.exists():
        fail(f"{description} is missing: {path.relative_to(ROOT)}")


def ensure_symlink() -> None:
    """校验规范来源：AGENTS.md 存在，且 CLAUDE.md 是指向 AGENTS.md 的符号链接。"""
    ensure_file_exists(AGENTS, "canonical AGENTS.md")
    if not CLAUDE.exists():
        fail("CLAUDE.md is missing")
    if not CLAUDE.is_symlink():
        fail("CLAUDE.md must be a symlink to AGENTS.md")

    target = Path(CLAUDE.readlink())
    if target != Path("AGENTS.md"):
        fail(f"CLAUDE.md must point to AGENTS.md, found: {target}")


def ensure_copilot_entry() -> None:
    """校验 .github/copilot-instructions.md 包含所有必需的规范来源引用片段。"""
    ensure_file_exists(COPILOT, "repository Copilot instructions")
    content = COPILOT.read_text(encoding="utf-8")
    required_fragments = (
        "Canonical source:",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/skills/",
    )
    for fragment in required_fragments:
        if fragment not in content:
            fail(f".github/copilot-instructions.md is missing required text: {fragment!r}")


def ensure_instruction_files() -> None:
    """校验 instructions 目录存在且包含全部必需的 *.instructions.md 文件。"""
    ensure_file_exists(INSTRUCTIONS_DIR, "instructions directory")
    actual = {path.name for path in INSTRUCTIONS_DIR.glob("*.instructions.md")}
    missing = REQUIRED_INSTRUCTION_FILES - actual
    if missing:
        fail(f"missing instruction files: {', '.join(sorted(missing))}")


def ensure_skill_files() -> None:
    """校验技能资产齐全，且除 README 外每个 SKILL.md 都引用 AGENTS.md 作为规则来源。"""
    ensure_file_exists(CLAUDE_SKILLS_DIR, "Claude skills directory")
    for relative_path in REQUIRED_SKILL_FILES:
        path = CLAUDE_SKILLS_DIR / relative_path
        if not path.exists():
            fail(f"missing repository skill asset: {path.relative_to(ROOT)}")
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            if relative_path != "README.md" and "AGENTS.md" not in content:
                fail(f"{path.relative_to(ROOT)} must reference AGENTS.md as the rule source")


def ensure_gitignore_rules() -> None:
    """校验 .gitignore 包含忽略 .claude/* 且放行 .claude/skills/ 的规则片段。"""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for snippet in REQUIRED_GITIGNORE_SNIPPETS:
        if snippet not in gitignore:
            fail(f".gitignore is missing required AI asset rule: {snippet}")


def ensure_no_tracked_claude_artifacts() -> None:
    """校验 .claude 下被 git 跟踪的文件都位于 skills/ 目录内，避免误提交本地产物。"""
    result = subprocess.run(
        ["git", "ls-files", "--", ".claude"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    allowed_prefixes = (".claude/skills/",)
    for path in tracked:
        if path.startswith(allowed_prefixes):
            continue
        fail(f"tracked .claude artifact outside skills/: {path}")


def main() -> None:
    """依次执行全部 AI 资产校验；全部通过时输出 ``[ai-assets] OK``。"""
    ensure_symlink()
    ensure_copilot_entry()
    ensure_instruction_files()
    ensure_skill_files()
    ensure_gitignore_rules()
    ensure_no_tracked_claude_artifacts()
    print("[ai-assets] OK")


if __name__ == "__main__":
    main()
