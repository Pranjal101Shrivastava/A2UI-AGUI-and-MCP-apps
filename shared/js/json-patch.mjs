// RFC 6902 JSON Patch (add, replace, remove, test) on a copy of the document.
export function applyPatch(doc, ops) {
  doc = structuredClone(doc);
  for (const op of ops) {
    if (op.path === "") { doc = structuredClone(op.value); continue; }
    const keys = op.path.split("/").slice(1).map((k) => k.replace(/~1/g, "/").replace(/~0/g, "~"));
    const last = keys.pop();
    const parent = keys.reduce((node, k) => node[Array.isArray(node) ? Number(k) : k], doc);
    if (Array.isArray(parent)) {
      const i = last === "-" ? parent.length : Number(last);
      if (op.op === "add") parent.splice(i, 0, op.value);
      if (op.op === "replace") parent[i] = op.value;
      if (op.op === "remove") parent.splice(i, 1);
    } else {
      if (op.op === "add" || op.op === "replace") parent[last] = op.value;
      if (op.op === "remove") delete parent[last];
    }
  }
  return doc;
}
