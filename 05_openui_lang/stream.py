"""Turn a model's OpenUI Lang text into events: chunks as they arrive, then an end marker."""


def program_events(model, messages, check=None):
    """Stream chunks. If `check` is given, validate the full text at the end and report problems."""
    text = ""
    for chunk in model.stream(messages):
        text += chunk
        yield {"type": "chunk", "text": chunk}
    if not text.endswith("\n"):
        yield {"type": "chunk", "text": "\n"}
        text += "\n"
    if check:
        errors = check(text)
        yield {"type": "trace", "text": "program valid" if not errors else "problems: " + "; ".join(errors)}
    yield {"type": "end"}
