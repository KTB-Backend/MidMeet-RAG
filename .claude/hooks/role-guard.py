#!/usr/bin/env python3
"""PreToolUse 경고형 가드.

Claude Code가 구현 코드 영역(packages/ scripts/ apps/ evals/ tests/)을
Edit/Write/MultiEdit로 수정하려 할 때 경고만 띄운다. 진행을 막지 않는다.
구현은 Codex CLI 담당이고 Claude는 설계·리뷰 전담이라는 역할 경계를 환기한다.
"""
import json
import os
import sys

IMPL_PREFIXES = ("packages/", "scripts/", "apps/", "evals/", "tests/")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path:
        sys.exit(0)

    project_dir = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        rel = os.path.relpath(file_path, project_dir)
    except ValueError:
        rel = file_path
    rel = rel.replace(os.sep, "/")

    if rel.startswith(IMPL_PREFIXES):
        msg = (
            f"⚠️ role-guard: '{rel}' 은(는) 구현 코드 영역입니다. "
            "CLAUDE.md상 Claude Code는 설계·리뷰 전담이며 구현은 Codex CLI 담당입니다. "
            "사용자가 직접 구현을 명시적으로 요청한 경우에만 진행하세요. "
            "위임이 맞다면 /codex-task 로 프롬프트를 만들어 Codex에 넘기세요."
        )
        print(json.dumps({"systemMessage": msg}))

    sys.exit(0)


if __name__ == "__main__":
    main()
