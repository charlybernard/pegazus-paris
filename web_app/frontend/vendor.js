import L from "leaflet";
import Split from "split.js";
import { Timeline } from "@knight-lab/timelinejs/src/js/timeline/Timeline.js";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIconRetina from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import frenchLocale from "@knight-lab/timelinejs/dist/js/locale/fr.json?url&no-inline";
import englishLocale from "@knight-lab/timelinejs/dist/js/locale/en.json?url&no-inline";
import spanishLocale from "@knight-lab/timelinejs/dist/js/locale/es.json?url&no-inline";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import "@knight-lab/timelinejs/dist/css/timeline.css";

L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIconRetina,
  shadowUrl: markerShadow
});

window.L = L;
await import("leaflet-draw");

export const timelineLanguages = { fr: frenchLocale, en: englishLocale, es: spanishLocale };
export { L, Split, Timeline };