// The json-render spec format in the browser: resolve $state bindings, apply
// streamed patches, render with the shared catalog. Missing elements render
// as placeholders, so a half-streamed spec still paints.
import { renderElementMap } from "../shared/js/catalog.mjs";
import { applyPatch } from "../shared/js/json-patch.mjs";

export const EMPTY = { root: null, elements: {}, state: {} };

const read = (doc, pointer) => pointer.split("/").filter(Boolean).reduce((node, k) => node?.[k], doc);

export function resolve(spec) {
  const elements = {};
  for (const [id, el] of Object.entries(spec.elements || {})) {
    const props = {};
    for (const [k, v] of Object.entries(el.props || {})) {
      props[k] = v && typeof v === "object" && "$state" in v ? read(spec.state, v.$state) : v;
    }
    elements[id] = { ...el, props };
  }
  return { ...spec, elements };
}

export function render(spec, ctx = {}) {
  if (!spec.root) return document.createTextNode("…");
  return renderElementMap(resolve(spec), ctx);
}

export function applyPatchLine(spec, op) {
  return applyPatch(spec, [op]);
}
