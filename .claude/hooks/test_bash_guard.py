"""Self-check for bash_guard.py: `python3 .claude/hooks/test_bash_guard.py`."""
import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).with_name("bash_guard.py")

DENY = [
    "git checkout -b feat/x",
    "git switch -c fix/y",
    "git -C /repo checkout -b feat/x",
    "git branch feat/z",
    "git worktree add ../wt -b feat/w",
    'git commit -m "update stuff"',
    'git commit -am "update"',
    'git -C backend commit -m "wip"',
    'git commit -m "feat: x" -m "body paragraph"',
    "git commit -m \"$(cat <<'EOF'\nfeat: x\nEOF\n)\"",
    "git push origin main",
    "git push --force-with-lease origin feat/x",
    "cat backend/.env",
    "source .env",
    "sed -i 's/a/b/' .github/workflows/ci.yml",
    'gh pr create --title "x"',
    "gh pr merge 12",
    "gh pr review 12 --approve",
]

ALLOW = [
    "git branch",
    "git branch --show-current",
    "git branch -a",
    "git branch -d feat/old",
    "git branch | cat",
    "git checkout main",
    "git switch feat/x",
    'git commit -m "feat: add x"',
    'git commit -m "fix(voting): y"',
    'git commit src/my-program -m "feat: x"',
    "git commit -F /tmp/msg.txt",
    "git push -u origin feat/x",
    "grep -rn platform .github/workflows/",
    "cat backend/app/core/config.py",
    "gh pr view 12",
]


def denied(cmd: str) -> bool:
    payload = json.dumps({"tool_input": {"command": cmd}})
    out = subprocess.run([sys.executable, GUARD], input=payload, capture_output=True, text=True, check=True)
    return "hookSpecificOutput" in json.loads(out.stdout)


fails = [f"should deny: {c!r}" for c in DENY if not denied(c)]
fails += [f"should allow: {c!r}" for c in ALLOW if denied(c)]
assert not fails, "\n".join(fails)
print(f"ok: {len(DENY)} denied, {len(ALLOW)} allowed")
