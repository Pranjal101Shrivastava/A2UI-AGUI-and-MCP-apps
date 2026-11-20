"""The scripted coding session every harness codelab shares: the fix the model makes."""
from pathlib import Path

BUGGY = (Path(__file__).resolve().parent / "toy_project" / "calc.py").read_text(encoding="utf-8")
FIXED = BUGGY.replace("return total(values) / (len(values) - 1)", "return total(values) / len(values)")
PROMPT = "The tests in my project fail. Find the bug, fix it, and show me what you did."
