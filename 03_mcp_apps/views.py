"""Assemble the HTML documents the server serves as ``ui://`` resources."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _script(path: Path) -> str:
    """Inline an ES module as a classic script: drop import lines and export keywords."""
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.startswith("import ")]
    code = "\n".join(l.replace("export ", "", 1) if l.startswith("export ") else l for l in lines)
    return code.replace("</script>", "<\\/script>")  # keep the HTML parser from closing our <script> early


def build(view_file: Path, with_catalog: bool = False) -> str:
    html = view_file.read_text(encoding="utf-8")
    scripts = [_script(HERE / "app-bridge.js")]
    if with_catalog:  # the shared catalog renderers, so the view can draw a spec
        scripts += [_script(ROOT / "shared/js/sandbox.mjs"), _script(ROOT / "shared/js/catalog.mjs")]
        html = html.replace("<!--CATALOG_CSS-->", "<style>" + (ROOT / "shared/style.css").read_text(encoding="utf-8") + "</style>")
    return html.replace("<!--APP_BRIDGE-->", "<script>\n" + "\n".join(scripts) + "\n</script>")
