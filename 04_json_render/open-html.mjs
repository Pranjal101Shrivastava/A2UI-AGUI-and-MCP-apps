// Open-ended json-render: element types are HTML tags and props carry inline CSS.
// The builder, not the model, writes the markup: text is escaped, only the
// style/text/action/label props are read, and actions become one fixed script.
const TAGS = new Set(["div", "span", "p", "h1", "h2", "h3", "strong", "em", "small", "ul", "li", "button", "section"]);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const css = (style = {}) =>
  Object.entries(style)
    .filter(([, v]) => !/url\(|expression\(|javascript:|@import/i.test(String(v)))
    .map(([k, v]) => `${k.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)}:${esc(v)}`)
    .join(";");

export function buildHtml(spec) {
  const walk = (id) => {
    const el = spec.elements[id];
    if (!el || !TAGS.has(el.type)) return "";
    const p = el.props || {};
    const attrs = [p.style ? `style="${css(p.style)}"` : "", p.action ? `data-action="${esc(p.action)}"` : "",
      p.label ? `aria-label="${esc(p.label)}"` : ""].filter(Boolean).join(" ");
    const inner = (p.text !== undefined ? esc(p.text) : "") + (el.children || []).map(walk).join("");
    return `<${el.type}${attrs ? " " + attrs : ""}>${inner}</${el.type}>`;
  };
  const script = `<script>document.querySelectorAll("[data-action]").forEach((n) =>
    n.addEventListener("click", () => genux.send("action", { name: n.dataset.action })));<\/script>`;
  return walk(spec.root) + script;
}
