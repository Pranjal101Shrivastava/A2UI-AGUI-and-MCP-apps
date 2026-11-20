"""Run this codelab end to end: server, headless browser, clicks, screenshot, transcript."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.demo_kit import run_demo  # noqa: E402

run_demo(Path(__file__).parent)
