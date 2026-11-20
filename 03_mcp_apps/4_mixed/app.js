import { startHost } from "../host.mjs";

startHost({
  mode: "mixed",
  title: "Catalog app with one generated region, two sandboxes deep",
  blurb: "weather_studio returns a catalog spec with one GeneratedView radar. Refresh calls refresh_radar, an app-only tool the model never sees.",
  prompt: "Open the weather studio for Seattle",
});
