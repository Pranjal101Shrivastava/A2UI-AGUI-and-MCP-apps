// The shared component catalog: one hand-written DOM renderer per component name.
// Every format in this repository resolves to calls of renderComponent().
// The model never supplies code here: it can only pick a name and fill props.
import { mountSandbox } from "./sandbox.mjs";

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
};

export const RENDERERS = {
  Card(p, kids) {
    const box = el("section", "c-card");
    if (p.title) box.append(el("h3", "c-card-title", p.title));
    box.append(...kids);
    return box;
  },
  Row(p, kids) {
    const row = el("div", "c-row");
    row.append(...kids);
    return row;
  },
  Column(p, kids) {
    const col = el("div", "c-col");
    col.append(...kids);
    return col;
  },
  Text(p) {
    const tag = { h1: "h1", h2: "h2" }[p.variant] || "p";
    return el(tag, `c-text c-${p.variant || "body"}`, p.text);
  },
  Metric(p) {
    const box = el("div", "c-metric");
    box.append(el("div", "c-metric-label", p.label), el("div", "c-metric-value", p.value));
    if (p.delta) box.append(el("div", String(p.delta).startsWith("-") ? "c-delta c-down" : "c-delta c-up", p.delta));
    return box;
  },
  Table(p) {
    const table = el("table", "c-table");
    const head = table.createTHead().insertRow();
    for (const c of p.columns || []) head.append(el("th", "", c));
    const body = table.createTBody();
    for (const r of p.rows || []) {
      const tr = body.insertRow();
      for (const cell of r) tr.append(el("td", "", cell));
    }
    return table;
  },
  BarChart(p) {
    const box = el("figure", "c-chart");
    box.append(el("figcaption", "", p.title));
    const values = (p.values || []).map(Number);
    const max = Math.max(1, ...values);
    const w = 320, h = 140, bw = w / Math.max(1, values.length);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${w} ${h + 18}`);
    values.forEach((v, i) => {
      const bh = (v / max) * h;
      const rect = document.createElementNS(svg.namespaceURI, "rect");
      Object.entries({ x: i * bw + 4, y: h - bh, width: bw - 8, height: bh, rx: 3, class: "c-bar" })
        .forEach(([k, val]) => rect.setAttribute(k, val));
      const label = document.createElementNS(svg.namespaceURI, "text");
      Object.entries({ x: i * bw + bw / 2, y: h + 14, "text-anchor": "middle", class: "c-axis" })
        .forEach(([k, val]) => label.setAttribute(k, val));
      label.textContent = (p.labels || [])[i] ?? "";
      svg.append(rect, label);
    });
    box.append(svg);
    return box;
  },
  Badge(p) {
    return el("span", `c-badge c-${p.tone || "info"}`, p.text);
  },
  Progress(p) {
    const box = el("div", "c-progress");
    box.append(el("div", "c-progress-label", `${p.label} · ${p.value}%`));
    const track = el("div", "c-track");
    const fill = el("div", "c-fill");
    fill.style.width = `${Math.max(0, Math.min(100, Number(p.value)))}%`;
    track.append(fill);
    box.append(track);
    return box;
  },
  TextField(p, kids, ctx) {
    const label = el("label", "c-field");
    label.append(el("span", "", p.label));
    const input = el("input");
    input.value = p.value ?? "";
    if (p.bind) input.oninput = () => ctx.setData?.(p.bind, input.value);
    label.append(input);
    return label;
  },
  Button(p, kids, ctx) {
    const button = el("button", `c-button c-${p.variant || "default"}`, p.label);
    button.dataset.action = p.action;
    button.onclick = () => ctx.onAction?.(p.action, p.context || {});
    return button;
  },
  GeneratedView(p, kids, ctx) {
    const box = el("div", "c-generated");
    if (p.title) box.append(el("div", "c-generated-title", `${p.title} · sandboxed`));
    mountSandbox(box, p.html, { height: p.height || 220, onMessage: ctx.onSandboxMessage });
    return box;
  },
};

export function renderComponent(type, props = {}, children = [], ctx = {}) {
  const render = RENDERERS[type];
  if (!render) return el("div", "c-error", `unknown component: ${type}`);
  return render(props, children, ctx);
}

// A nested tree: {type, props, children: [node]}.
export function renderTree(node, ctx = {}) {
  if (!node) return el("div", "c-placeholder", "…");
  const kids = (node.children || []).map((child) => renderTree(child, ctx));
  return renderComponent(node.type, node.props || {}, kids, ctx);
}

// A flat element map: {root, elements: {id: {type, props, children: [id]}}}.
// Missing ids render as placeholders, so a half-streamed map still paints.
export function renderElementMap(spec, ctx = {}) {
  const seen = new Set();
  const walk = (id) => {
    const element = spec.elements?.[id];
    if (!element || seen.has(id)) return el("div", "c-placeholder", "…");
    seen.add(id);
    const kids = (element.children || []).map(walk);
    const node = renderComponent(element.type, element.props || {}, kids, ctx);
    node.dataset.id = id;
    return node;
  };
  return walk(spec.root);
}
