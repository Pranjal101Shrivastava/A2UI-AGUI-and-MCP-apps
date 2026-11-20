import { renderComponent as c } from "../../shared/js/catalog.mjs";
import { startHarnessPage } from "../client.mjs";

// Three pre-built panels. The agent picks one; the harness fills it with real data.
const diff = (text) => {
  const pre = document.createElement("pre");
  pre.className = "h-diff";
  pre.innerHTML = text.split("\n").map((l) => {
    const safe = l.replace(/[&<>]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[ch]);
    return l.startsWith("+") && !l.startsWith("+++") ? `<span class="add">${safe}</span>`
      : l.startsWith("-") && !l.startsWith("---") ? `<span class="del">${safe}</span>` : safe;
  }).join("\n");
  return pre;
};

startHarnessPage({
  mode: "static",
  title: "The agent shows pre-built panels",
  blurb: "Besides its coding tools, the agent has show_status, show_test_report and show_diff. It picks when; the harness supplies the data.",
  prompt: "The tests in my project fail. Find the bug, fix it, and show me what you did.",
}, {
  Status: (p) => c("Card", { title: "Status" }, [c("Text", { text: p.step, variant: "h2" }), c("Text", { text: p.detail, variant: "muted" })]),
  TestReport: (p) => c("Card", { title: "Tests" }, [
    c("Row", {}, [c("Metric", { label: "Passed", value: `${p.passed}/${p.ran}` }),
      c("Badge", { text: p.failed ? `${p.failed} failing` : "all green", tone: p.failed ? "bad" : "ok" })]),
    ...(p.failures.length ? [c("Text", { text: p.failures.join(", "), variant: "muted" })] : []),
  ]),
  DiffView: (p) => c("Card", { title: "Diff" }, [diff(p.diff)]),
});
