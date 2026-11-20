import { startHost } from "../host.mjs";

startHost({
  mode: "open-ended",
  title: "The server's model writes the whole app",
  blurb: "design_weather_widget generates a full HTML document, bridge code included. The host mounts it behind the same sandbox and CSP.",
  prompt: "Design me a moody little weather widget for Seattle",
});
