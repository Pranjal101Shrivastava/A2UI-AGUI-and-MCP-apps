import { startHost } from "../host.mjs";

startHost({
  mode: "declarative",
  title: "A generic app draws the server's catalog spec",
  blurb: "The server's model writes an element map from the catalog; the server validates it; one generic ui:// view renders any valid spec.",
  prompt: "Give me a weather dashboard for Seattle",
});
