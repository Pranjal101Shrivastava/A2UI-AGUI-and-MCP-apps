"""Run a codelab end to end and record what happened.

For one codelab directory this:

1. starts ``shared/devserver.py`` on a free port,
2. opens the codelab page in headless Chromium (Playwright), which runs the
   prompt against the real server,
3. performs the codelab's ``DEMO_STEPS`` (clicks inside the page or inside the
   sandboxed iframe), waiting for each server round trip,
4. writes ``output.txt`` (the wire transcript), ``recording.json`` (the same
   events, replayed when the page is opened from a static host) and
   ``demo.png`` (the screenshot).

Without Playwright it still runs the agent in process and writes the transcript.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared import devserver  # noqa: E402


def _short(value, limit: int = 150) -> str:
    text = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _event_line(event) -> tuple[str, str]:
    if isinstance(event, dict) and "type" in event:
        rest = {k: v for k, v in event.items() if k != "type"}
        return event["type"], _short(rest, 130)
    if isinstance(event, dict) and len(event) <= 2 and "version" in event:  # A2UI envelope
        key = next(k for k in event if k != "version")
        return key, _short(event[key], 130)
    return "", _short(event)


def format_transcript(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        body = dict(entry["body"])
        method = body.get("method")
        head = f"POST api/{entry['api']}" + (f"  {method}" if method else "")
        lines.append(f"{head}  {_short(body.get('params', body), 110)}")
        events = entry["events"]
        i = 0
        while i < len(events):
            kind, text = _event_line(events[i])
            j = i
            while j + 1 < len(events) and kind and _event_line(events[j + 1])[0] == kind:
                j += 1
            if j - i >= 3:  # collapse a run of deltas
                lines.append(f"  <- {kind} x{j - i + 1}  (first: {text[:70]})")
            else:
                for k in range(i, j + 1):
                    kk, tt = _event_line(events[k])
                    lines.append(f"  <- {kk + ' ' if kk else ''}{tt}")
            i = j + 1
    return "\n".join(lines)


def _wait_done(page, count: int, timeout: float = 20.0) -> None:
    page.wait_for_function(f"Number(document.body.dataset.done || 0) >= {count}", timeout=timeout * 1000)


def run_demo(codelab: str | Path, server=None, quiet: bool = False) -> str:
    codelab = Path(codelab).resolve()
    if codelab.is_file():
        codelab = codelab.parent
    agent = devserver.load_agent(codelab)
    rel = codelab.relative_to(ROOT).as_posix()
    own_server = server is None
    server = server or devserver.start()
    start_index = len(devserver.TRANSCRIPT)
    shots = []
    console: list[str] = []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        sync_playwright = None

    began = time.perf_counter()
    if sync_playwright:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1100, "height": 900})
            page.on("console", lambda m: console.append(m.text) if m.text.startswith("[genux]") else None)
            page.goto(f"http://127.0.0.1:{server.server_port}/{rel}/index.html")
            _wait_done(page, 1)
            done = 1
            for step in getattr(agent, "DEMO_STEPS", []):
                if "screenshot" in step:
                    page.wait_for_timeout(400)
                    page.screenshot(path=str(codelab / step["screenshot"]), full_page=True)
                    shots.append(step["screenshot"])
                    continue
                target = page
                if step.get("frame"):  # click inside a sandboxed iframe
                    target = page.frame_locator(step["frame"]).first
                if "fill" in step:
                    target.locator(step["fill"]).fill(step["value"])
                    continue
                target.locator(step["click"]).first.click()
                done += step.get("round_trips", 1)
                _wait_done(page, done)
            page.wait_for_timeout(600)
            page.screenshot(path=str(codelab / "demo.png"), full_page=True)
            shots.append("demo.png")
            browser.close()
    else:  # no browser: drive the agent directly with the default prompt
        for _ in agent.handle("run", {"prompt": agent.PROMPT}):
            pass
    elapsed = time.perf_counter() - began

    entries = devserver.TRANSCRIPT[start_index:]
    recording = []
    for e in entries:
        item = {"api": e["api"], "method": e["body"].get("method", "")}
        if e.get("kind") == "json":
            item["json"] = e["events"][0]
        else:
            item["events"] = e["events"]
        recording.append(item)
    (codelab / "recording.json").write_text(json.dumps(recording, indent=1), encoding="utf-8")

    parts = [f"$ python {rel}/demo.py", "", format_transcript(entries)]
    if console:
        parts += ["", "browser console:"] + [f"  {c}" for c in console]
    notes = getattr(agent, "demo_notes", None)
    if notes:
        parts += ["", notes()]
    parts += ["", f"screenshots: {', '.join(shots) or 'none (Playwright not installed)'}"
              f"   ({len(entries)} request(s), {elapsed:.1f}s)"]
    output = "\n".join(parts) + "\n"
    (codelab / "output.txt").write_text(output, encoding="utf-8")
    if own_server:
        server.shutdown()
    if not quiet:
        print(output)
    return output


if __name__ == "__main__":
    run_demo(sys.argv[1])
