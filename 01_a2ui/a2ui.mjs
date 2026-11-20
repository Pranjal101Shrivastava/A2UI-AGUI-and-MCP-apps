// A2UI v0.9 in the browser: a surface holds components (structure) and a data
// model (data). Each server message updates one of them; the surface redraws.
import { renderComponent } from "../shared/js/catalog.mjs";

export const VERSION = "v0.9";

export function getPath(data, path) {
  return path.split("/").filter(Boolean).reduce((node, key) => node?.[key], data);
}

export function setPath(data, path, value) {
  const keys = path.split("/").filter(Boolean);
  if (!keys.length) return value; // "/" replaces the whole model
  let node = data;
  for (const key of keys.slice(0, -1)) node = node[key] ??= {};
  node[keys.at(-1)] = value;
  return data;
}

export class Surface {
  constructor(id, catalogId) {
    this.id = id;
    this.catalogId = catalogId;
    this.components = new Map();
    this.data = {};
  }

  apply(msg) {
    if (msg.updateComponents) for (const c of msg.updateComponents.components) this.components.set(c.id, c);
    if (msg.updateDataModel) this.data = setPath(this.data, msg.updateDataModel.path, structuredClone(msg.updateDataModel.value));
  }

  // A dynamic value is a literal or a binding {path}. Resolve it against the data model.
  resolve(value) {
    return value && typeof value === "object" && "path" in value ? getPath(this.data, value.path) : value;
  }

  // The client half of an action: bind the context paths to current data, then send.
  action(componentId) {
    const event = this.components.get(componentId).action.event;
    const context = Object.fromEntries(Object.entries(event.context || {}).map(([k, v]) => [k, this.resolve(v)]));
    return { version: VERSION, action: { name: event.name, surfaceId: this.id, sourceComponentId: componentId,
      timestamp: new Date().toISOString(), context } };
  }

  render(onAction) {
    const ctx = {
      onAction: (name, componentId) => onAction(this.action(componentId)),
      setData: (path, value) => setPath(this.data, path, value), // two-way binding for inputs
    };
    // A message from an HtmlFrame's sandbox becomes an ordinary A2UI action from that component.
    const fromSandbox = (componentId) => (type, payload) => {
      if (type === "action") onAction({ version: VERSION, action: { name: payload.name, surfaceId: this.id,
        sourceComponentId: componentId, timestamp: new Date().toISOString(), context: payload.context || {} } });
    };
    const draw = (id) => {
      const c = this.components.get(id);
      if (!c) return renderComponent("Text", { text: "…", variant: "muted" });
      const kids = (c.children || []).map(draw);
      switch (c.component) {
        case "Text": {
          const variant = { h1: "h1", h2: "h2", h3: "h2", caption: "muted" }[c.variant] || "body";
          return renderComponent("Text", { text: this.resolve(c.text) ?? "", variant });
        }
        case "Row": return renderComponent("Row", {}, kids);
        case "Column": return renderComponent("Column", {}, kids);
        case "Card": return renderComponent("Card", {}, [draw(c.child)]);
        case "Divider": return document.createElement("hr");
        case "Button": {
          const label = this.resolve(this.components.get(c.child)?.text) ?? c.child;
          const node = renderComponent("Button", { label, action: c.action.event.name, variant: c.variant }, [], {
            onAction: () => ctx.onAction(c.action.event.name, c.id),
          });
          return node;
        }
        case "TextField": {
          const bind = c.value && typeof c.value === "object" ? c.value.path : undefined;
          return renderComponent("TextField", { label: this.resolve(c.label), value: this.resolve(c.value), bind }, [], ctx);
        }
        case "HtmlFrame":
          return renderComponent("GeneratedView", { html: c.html, height: c.height, title: `HtmlFrame "${c.id}"` }, [],
            { onSandboxMessage: fromSandbox(c.id) });
        default:
          return renderComponent(c.component, {}, []);
      }
    };
    return draw("root");
  }
}

// Route a stream of envelopes to surfaces and redraw the changed one.
export class SurfaceHost {
  constructor(container, onAction) {
    this.container = container;
    this.onAction = onAction;
    this.surfaces = new Map();
  }

  handle(msg) {
    if (msg.createSurface) this.surfaces.set(msg.createSurface.surfaceId, new Surface(msg.createSurface.surfaceId, msg.createSurface.catalogId));
    if (msg.deleteSurface) this.surfaces.delete(msg.deleteSurface.surfaceId);
    const id = (msg.updateComponents || msg.updateDataModel)?.surfaceId;
    if (id) this.surfaces.get(id)?.apply(msg);
    this.draw();
  }

  draw() {
    this.container.replaceChildren(...[...this.surfaces.values()]
      .filter((s) => s.components.has("root"))
      .map((s) => s.render(this.onAction)));
  }
}
