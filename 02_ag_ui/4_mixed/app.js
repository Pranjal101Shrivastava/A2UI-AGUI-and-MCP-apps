import { renderComponent as c, renderTree } from "../../shared/js/catalog.mjs";
import { partialJSON } from "../agui.mjs";
import { startAgUiPage } from "../client.mjs";

startAgUiPage({
  mode: "mixed",
  title: "Catalog state, a generated region, and an approval",
  blurb: "The itinerary is a catalog tree in shared state with one sandboxed GeneratedView. The agent asks for approval through a frontend tool.",
  prompt: "Plan my Kyoto weekend and book a ryokan if it fits ¥40,000",
}, ({ session, canvas, send }) => {
  // A frontend tool: declared here, sent in RunAgentInput.tools, executed by the user.
  session.tools = [{ name: "confirm_booking", description: "Ask the user to approve a hotel booking",
    parameters: { type: "object", properties: { hotel: { type: "string" }, nights: { type: "number" }, price: { type: "string" } } } }];

  const view = document.createElement("div");
  const approvals = document.createElement("div");
  canvas.append(view, approvals);
  let drawnHtml = null;
  session.onState = (state) => {
    // Keep the sandbox alive across deltas: redraw only when the tree changed outside it.
    const key = JSON.stringify(state.ui);
    if (key !== drawnHtml) view.replaceChildren(renderTree(state.ui, {}));
    drawnHtml = key;
  };
  session.onToolCall = (callInfo, phase) => {
    if (callInfo.name !== "confirm_booking" || phase !== "end") return;
    const a = partialJSON(callInfo.raw);
    const answer = (approved) => {
      card.remove();
      send([{ id: `tool_${Date.now()}`, role: "tool", toolCallId: callInfo.id, content: JSON.stringify({ approved }) }]);
    };
    const card = c("Card", { title: "Approve this booking?" }, [
      c("Text", { text: `${a.hotel} · ${a.nights} nights · ${a.price}` }),
      c("Text", { text: a.why, variant: "muted" }),
      c("Row", {}, [
        c("Button", { label: "Approve", action: "approve", variant: "primary" }, [], { onAction: () => answer(true) }),
        c("Button", { label: "Decline", action: "decline" }, [], { onAction: () => answer(false) }),
      ]),
    ]);
    card.classList.add("ag-approval");
    approvals.append(card);
    console.log(`[genux] frontend tool confirm_booking is waiting for the user`);
  };
});
