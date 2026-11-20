// OpenUI Lang in the browser: tokenize, parse, resolve (forward references
// become placeholders), and render with the shared catalog. Mirrors openui.py.
import { renderComponent } from "../shared/js/catalog.mjs";

const TOKEN = /\s*(?:("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?)|([A-Za-z_]\w*)|([=(),\[\]]))/y;

export const PRIMITIVES = {
  Stack: ["children", "direction"], Card: ["title", "children"], Text: ["text", "variant"],
  Metric: ["label", "value", "delta"], Table: ["columns", "rows"], BarChart: ["title", "labels", "values"],
  Badge: ["text", "tone"], Progress: ["label", "value"], Button: ["label", "action", "variant"],
};
export const HTML_ARTIFACT = { HtmlArtifact: ["html", "title", "height"] };

function tokenize(line) {
  const tokens = [];
  TOKEN.lastIndex = 0;
  const end = line.trimEnd().length;
  while (TOKEN.lastIndex < end) {
    const start = TOKEN.lastIndex;
    const m = TOKEN.exec(line);
    if (!m || TOKEN.lastIndex === start) throw new Error(`unexpected character at column ${start + 1}`);
    if (m[1]) tokens.push(["lit", JSON.parse(m[1])]);
    else if (m[2]) tokens.push(["lit", Number(m[2])]);
    else if (m[3]) tokens.push(m[3] in LITERALS ? ["lit", LITERALS[m[3]]] : ["id", m[3]]);
    else tokens.push(["p", m[4]]);
  }
  return tokens;
}
const LITERALS = { true: true, false: false, null: null };

function parseExpr(t) {
  const [kind, value] = t.shift() ?? [];
  if (kind === "lit") return ["lit", value];
  if (kind === "p" && value === "[") return ["list", parseItems(t, "]")];
  if (kind === "id" && t[0]?.[1] === "(") { t.shift(); return ["call", value, parseItems(t, ")")]; }
  if (kind === "id") return ["ref", value];
  throw new Error(`unexpected ${value}`);
}

function parseItems(t, close) {
  const items = [];
  if (t[0]?.[1] === close) { t.shift(); return items; }
  for (;;) {
    items.push(parseExpr(t));
    const [, p] = t.shift() ?? [];
    if (p === close) return items;
    if (p !== ",") throw new Error(`expected , or ${close}`);
  }
}

// Parse every complete line. While streaming, the unfinished last line is skipped.
export function parseProgram(text, { partial = false } = {}) {
  const statements = new Map();
  const errors = [];
  let lines = text.split("\n");
  if (partial && !text.endsWith("\n")) lines = lines.slice(0, -1);
  lines.forEach((line, i) => {
    if (!line.trim() || line.trim().startsWith("#")) return;
    try {
      const t = tokenize(line);
      if (t[0]?.[0] !== "id" || t[1]?.[1] !== "=") throw new Error("a statement is: name = expression");
      const name = t[0][1];
      const expr = parseExpr(t.slice(2));
      statements.set(name, expr);                         // later assignments replace earlier ones
    } catch (err) {
      errors.push(`line ${i + 1}: ${err.message}`);
    }
  });
  return { statements, errors };
}

export function resolve(statements, components) {
  if (!statements.size) return null;
  const entry = statements.has("root") ? "root" : statements.keys().next().value;
  const value = (expr, seen) => {
    switch (expr[0]) {
      case "lit": return expr[1];
      case "list": return expr[1].map((e) => value(e, seen));
      case "ref":
        if (seen.has(expr[1]) || !statements.has(expr[1])) return { type: "_pending", name: expr[1] };
        return value(statements.get(expr[1]), new Set([...seen, expr[1]]));
      default: {
        const [, name, args] = expr;
        const params = components[name];
        if (!params) return { type: "_error", name };
        const props = Object.fromEntries(params.map((p, i) => [p, args[i] ? value(args[i], seen) : undefined]));
        const children = props.children ?? [];
        delete props.children;
        return { type: name, props, children: Array.isArray(children) ? children : [children] };
      }
    }
  };
  return value(statements.get(entry), new Set([entry]));
}

// Render a resolved tree. `widgets` lets a codelab add its own pre-built components.
export function renderNode(node, ctx = {}, widgets = {}) {
  if (!node || typeof node !== "object") return renderComponent("Text", { text: String(node ?? "") });
  if (node.type === "_pending") return renderComponent("Text", { text: `… ${node.name}`, variant: "muted" });
  if (node.type === "_error") return renderComponent("Badge", { text: `unknown ${node.name}`, tone: "bad" });
  const kids = node.children.map((c) => renderNode(c, ctx, widgets));
  if (widgets[node.type]) return widgets[node.type](node.props, ctx, kids);
  const props = Object.fromEntries(Object.entries(node.props).filter(([, v]) => v !== undefined));
  // A prop that is still a forward reference (e.g. Table(..., rows) before `rows` arrives): wait for it.
  const waiting = Object.values(props).find((v) => v && v.type === "_pending");
  if (waiting) return renderComponent("Text", { text: `… ${node.type} waits for ${waiting.name}`, variant: "muted" });
  if (node.type === "Stack") return renderComponent(props.direction === "row" ? "Row" : "Column", {}, kids, ctx);
  if (node.type === "HtmlArtifact") return renderComponent("GeneratedView", props, [], ctx);
  return renderComponent(node.type, props, kids, ctx);
}

export function countPending(node) {
  if (!node || typeof node !== "object") return 0;
  if (node.type === "_pending") return 1;
  const inProps = Object.values(node.props || {}).filter((v) => v && v.type === "_pending").length;
  return inProps + (node.children || []).reduce((n, c) => n + countPending(c), 0);
}
