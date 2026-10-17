#!/usr/bin/env python3
"""PreToolUse guard for Bash: enforces the CLAUDE.md Hard Constraints a shell command
can break (branch creation, PR create/merge/approve, push to main, .env access,
.github/workflows/ edits) plus the Conventional Commits message format.
Self-check: `python3 .claude/hooks/test_bash_guard.py`.
"""
import json
import re
import sys

# `git` plus any `-C <path>` / `-c <key=val>` globals, so `git -C backend commit` is caught too.
GIT = r"\bgit(?:\s+-[Cc]\s+\S+)*\s+"

RULES = [
    (
        "block-branch-creation",
        # Creation forms: `checkout -b/-B/--orphan`, `switch -c/-C/--create/--force-create/--orphan`,
        # `worktree add ... -b/-B`, and bare `git branch <name>`. The lookahead on the `branch` arm
        # lets flag forms (`--show-current`, `-a`, `-d <name>`, `-m`) and pipes (`git branch | ...`) through.
        # ponytail: flag-led creation (`git branch -c/-f/--track <name>`) and `worktree add <path>`'s
        # implicit branch are not caught; add arms if an agent ever reaches for them.
        re.compile(
            GIT + r"(?:"
            r"(?:checkout|switch)\s+(?:-\S+\s+)*(?:-[bc]|--create|--force-create|--orphan)\s"
            r"|worktree\s+add\b[^\n]*\s-b\s"
            r"|branch[ \t]+(?![-|;&<>)])\S"
            r")",
            re.IGNORECASE,
        ),
        "Claude never creates git branches in this repo (CLAUDE.md Hard Constraint #5).\n\n"
        "Propose the branch name — `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`, `test/` or `style/` "
        "plus a short description, e.g. `feat/vote-reminders` — and wait for the user to create it.\n\n"
        "Read-only, delete and rename forms (`git branch --show-current`, `-a`, `-d <name>`, `-m`) are not affected.",
    ),
    (
        "enforce-commit-convention",
        re.compile(
            GIT + r"commit\b[^\n]*?\s-[a-z]*m\s+"
            r"(?![\"']?(?:feat|fix|chore|docs|refactor|build|ci|perf|style|test|revert)(?:\([^)]+\))?!?:\s)",
            re.IGNORECASE,
        ),
        "Commit message doesn't follow Conventional Commits (CLAUDE.md).\n\n"
        "Use `type: description` or `type(scope): description`, e.g. `fix(voting): break ties by first "
        "preference`. Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `build`, `ci`, `perf`, "
        "`style`, `test`, `revert`. A space is required after the colon.\n\n"
        "This rule checks every `-m` argument (including `-am`). For a multi-line message, write it to a file "
        "and use `git commit -F <file>` — `-F` is not checked here and there are no local git hooks, so check "
        "the subject yourself.",
    ),
    (
        "block-push-to-main",
        re.compile(GIT + r"push\b[^\n]*(?:\b(?:main|master)\b|\s(?:-f|--force)\b)", re.IGNORECASE),
        "Pushing to `main`/`master`, and force-pushing of any kind, is blocked (CLAUDE.md Hard Constraint #2).\n\n"
        "Changes reach `main` only through a feature branch and a PR the user submits. If a branch's history "
        "really needs rewriting, ask the user first.",
    ),
    (
        "block-env-bash",
        re.compile(
            r"(?:\b(?:cat|less|more|head|tail|vim|vi|nano|emacs|code|open|bat|sed|awk|grep|tee|cp|mv|source)|>>?)"
            r"\s+[^\n]*\.env(?:\.[\w.-]+)?\b",
            re.IGNORECASE,
        ),
        "`.env` files are never read or written via shell (CLAUDE.md Hard Constraint #1). Access environment "
        "variables only through `backend/app/core/config.py`.\n\n"
        "If you need to know whether a variable is set, ask the user.",
    ),
    (
        "block-workflow-edits-bash",
        re.compile(
            r"(?:>>?|\b(?:sed\s+-i|tee|rm|mv|cp|install|truncate)\b)[^\n]*\.github/workflows/", re.IGNORECASE
        ),
        "`.github/workflows/` is off-limits (CLAUDE.md Hard Constraint #3). This command appears to write, "
        "move, copy or delete a workflow file.\n\n"
        "Describe the change you think is needed and let the user make it.",
    ),
    (
        "block-pr-actions",
        re.compile(r"\bgh\s+pr\s+(?:create|merge)\b|\bgh\s+pr\s+review\b[^\n]*\s(?:--approve|-a)\b", re.IGNORECASE),
        "Claude never creates, merges or approves PRs (CLAUDE.md Hard Constraints #4 and #6).\n\n"
        "Prepare the PR title and description and hand them to the user to submit.",
    ),
]


def main() -> None:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")

    for name, pattern, message in RULES:
        if pattern.search(command):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    # What Claude sees; systemMessage alone only reaches the user.
                    "permissionDecisionReason": f"[{name}] {message}",
                },
                "systemMessage": f"**[{name}]**\n{message}",
            }))
            return

    print(json.dumps({}))


if __name__ == "__main__":
    main()
