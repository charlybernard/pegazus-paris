import L from "leaflet";

export function setLayerStyle(layer, style) {
  if (!layer || !style) return;
  if (typeof layer.eachLayer === "function") {
    layer.eachLayer(child => setLayerStyle(child, style));
  } else if (layer instanceof L.Marker) {
    if (style.marker) layer.setIcon(style.marker);
  } else if (layer instanceof L.Polygon) {
    if (style.polygon) layer.setStyle(style.polygon);
  } else if (layer instanceof L.Polyline) {
    if (style.polyline) layer.setStyle(style.polyline);
  } else if (layer instanceof L.Path) {
    layer.setStyle(style.polygon || style.polyline || {});
  }
}