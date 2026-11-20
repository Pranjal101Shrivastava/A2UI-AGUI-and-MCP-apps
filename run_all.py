"""Run every codelab end to end and refresh its recorded execution.

For each codelab: start the page in headless Chromium against the real
server, perform the demo clicks, then write output.txt, recording.json and the
screenshots, and paste output.txt into the README between the
<!-- OUTPUT --> markers. Usage: python run_all.py [filter], e.g. python run_all.py 03
"""
import re
import sys
from pathlib import Path

from shared import devserver
from shared.demo_kit import run_demo

ROOT = Path(__file__).resolve().parent
MARK = re.compile(r"(<!-- OUTPUT -->\n```text\n).*?(\n```\n<!-- /OUTPUT -->)", re.S)


def codelabs(pattern: str = ""):
    return [p.parent for p in sorted(ROOT.glob("0*/*/agent.py")) if pattern in p.parent.relative_to(ROOT).as_posix()]


def main() -> None:
    server = devserver.start()
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    for lab in codelabs(pattern):
        output = run_demo(lab, server=server, quiet=True)
        readme = lab / "README.md"
        if readme.exists():
            text = readme.read_text(encoding="utf-8")
            readme.write_text(MARK.sub(lambda m: m.group(1) + output.rstrip("\n") + m.group(2), text), encoding="utf-8")
        print(f"ok  {lab.relative_to(ROOT).as_posix():<28} {output.strip().splitlines()[-1]}")
    server.shutdown()


if __name__ == "__main__":
    main()
