"""Check that every code snippet in the READMEs exists, line for line, in the file it names.

A snippet is a fenced block (python, js, html, css) whose preceding non-empty
line names a file in backticks, e.g. `agent.py`:. A snippet with no file name
continues the file of the snippet before it. Lines are compared with
whitespace collapsed; a line that is just "..." skips code. Usage:
python check_snippets.py [path-filter]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FENCE = re.compile(r"(?P<intro>[^\n]*)\n+```(?P<lang>python|js|html|css)\n(?P<body>.*?)\n```", re.S)
NAME = re.compile(r"`([^`]+\.(?:py|mjs|js|html|css|jsonl))`")
norm = lambda s: " ".join(s.split())  # noqa: E731


def check(readme: Path) -> list[str]:
    problems, last = [], None
    for m in FENCE.finditer(readme.read_text(encoding="utf-8")):
        found = NAME.search(m.group("intro"))
        name = found.group(1) if found else last
        if not name:
            problems.append(f"{readme}: a {m.group('lang')} snippet has no file name before it")
            continue
        last = name
        target = (readme.parent / name).resolve()
        if not target.exists():
            problems.append(f"{readme}: {name} does not exist")
            continue
        source = {norm(line) for line in target.read_text(encoding="utf-8").splitlines()}
        for line in m.group("body").splitlines():
            if line.strip() and line.strip() != "..." and norm(line) not in source:
                problems.append(f"{readme}: not in {name}: {line.strip()[:80]}")
    return problems


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    readmes = [p for p in sorted(ROOT.glob("**/README.md")) if pattern in str(p) and ".venv" not in p.parts]
    problems = [p for r in readmes for p in check(r)]
    print("\n".join(problems) or f"all snippets match their files ({len(readmes)} READMEs checked)")
    sys.exit(1 if problems else 0)
