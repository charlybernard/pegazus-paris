import { i18nConfig } from "./i18n.js";

export let appConfig = null;
let getLanguage = () => "fr";

export function setAppConfig(config) {
  appConfig = config;
}
let settingsLayers = [];
let editingLayerIndex = null;

function getSettingsTexts() {
  return (i18nConfig[getLanguage()] || i18nConfig.fr).settings;
}

export async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...options.headers }
    });
  } catch {
    throw new Error(getSettingsTexts().apiUnavailable);
  }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

export function translateSettings() {
  const dictionary = getSettingsTexts();
  document.querySelectorAll("[data-settings-i18n]").forEach(element => {
    element.textContent = dictionary[element.dataset.settingsI18n];
  });
  const openButton = document.getElementById("btn-settings");
  openButton.title = dictionary.title;
  openButton.setAttribute("aria-label", dictionary.title);
  const closeButton = document.getElementById("settings-close");
  closeButton.title = dictionary.close;
  closeButton.setAttribute("aria-label", dictionary.close);
  renderSettingsLayers();
  updateLayerEditor();
}

function fillSettings(config) {
  const values = {
    endpoint: config.sparqlEndpoint, graph: config.defaultGraphUri,
    latitude: config.map.center[0], longitude: config.map.center[1], zoom: config.map.zoom,
    "date-min": config.dates.min, "date-max": config.dates.max, "date-default": config.dates.default || "",
    language: config.language, "query-language": config.queryLanguage, limit: config.landmarkSearchLimit,
    calendar: config.timeCalendarUri, delay: config.timeDelayYears
  };
  for (const [key, value] of Object.entries(values)) document.getElementById(`setting-${key}`).value = value;
  settingsLayers = structuredClone(config.map.tileLayers);
  renderSettingsLayers();
}

function readSettings() {
  const value = name => document.getElementById(`setting-${name}`).value;
  if (settingsLayers.length === 0 || settingsLayers.length > 30) {
    throw new Error(getSettingsTexts().invalidLayers);
  }
  return {
    ...appConfig,
    sparqlEndpoint: value("endpoint"), defaultGraphUri: value("graph"),
    map: { ...appConfig.map, center: [Number(value("latitude")), Number(value("longitude"))], zoom: Number(value("zoom")), tileLayers: structuredClone(settingsLayers) },
    dates: { min: value("date-min"), max: value("date-max"), default: value("date-default") || null },
    language: value("language"), queryLanguage: value("query-language"), landmarkSearchLimit: Number(value("limit")),
    timeCalendarUri: value("calendar"), timeDelayYears: Number(value("delay"))
  };
}

function renderSettingsLayers() {
  const dictionary = getSettingsTexts();
  const list = document.getElementById("settings-layer-list");
  list.replaceChildren();
  settingsLayers.forEach((layer, index) => {
    const row = document.createElement("li");
    row.className = "settings-layer-row";
    const content = document.createElement("div");
    content.className = "settings-layer-content";
    const heading = document.createElement("div");
    heading.className = "settings-layer-heading";
    const type = document.createElement("span");
    type.className = "settings-layer-type";
    type.textContent = layer.type.toUpperCase();
    const name = document.createElement("strong");
    name.textContent = layer.name;
    const url = document.createElement("span");
    url.className = "settings-layer-url";
    url.textContent = layer.url;
    heading.append(type, name);
    content.append(heading, url);
    row.appendChild(content);
    for (const action of ["edit", "delete"]) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "settings-icon-button";
      button.dataset.layerAction = action;
      const label = action === "edit" ? dictionary.editLayer : dictionary.deleteLayer;
      button.title = `${label} : ${layer.name}`;
      button.setAttribute("aria-label", button.title);
      const icon = document.createElement("img");
      icon.src = action === "edit" ? "/icons/pencil.svg" : "/icons/trash-2.svg";
      icon.width = icon.height = 16;
      icon.alt = "";
      button.appendChild(icon);
      if (action === "edit") {
        button.onclick = () => openLayerEditor(index);
      } else {
        button.disabled = settingsLayers.length === 1;
        if (button.disabled) button.title = dictionary.keepOneLayer;
        button.onclick = () => {
          if (settingsLayers.length <= 1) return;
          settingsLayers.splice(index, 1);
          renderSettingsLayers();
        };
      }
      row.appendChild(button);
    }
    list.appendChild(row);
  });
  for (const id of ["settings-add-xyz", "settings-add-wms"]) {
    document.getElementById(id).disabled = settingsLayers.length >= 30;
  }
}

function updateLayerEditor() {
  const dictionary = getSettingsTexts();
  const isWms = document.getElementById("layer-type").value === "wms";
  const fields = document.getElementById("layer-wms-fields");
  fields.hidden = !isWms;
  fields.disabled = !isWms;
  document.getElementById("layer-wms-name").required = isWms;
  document.getElementById("layer-editor-title").textContent = editingLayerIndex === null
    ? (isWms ? dictionary.addWmsLayer : dictionary.addXyzLayer) : dictionary.editLayer;
  document.getElementById("layer-url").placeholder = isWms
    ? "https://example.org/geoserver/wms" : "https://{s}.tile.example.org/{z}/{x}/{y}.png";
}

function openLayerEditor(index = null, type = "xyz") {
  if (index === null && settingsLayers.length >= 30) return;
  editingLayerIndex = index;
  const layer = index === null ? { type } : settingsLayers[index];
  const form = document.getElementById("layer-editor-form");
  form.reset();
  form.querySelectorAll("input").forEach(input => input.setCustomValidity(""));
  const values = {
    type: layer.type, name: layer.name || "", url: layer.url || "",
    attribution: layer.attribution || "", "max-zoom": layer.maxZoom ?? "",
    "wms-name": layer.layer || "", format: layer.format || "image/png", version: layer.version || "1.1.1"
  };
  for (const [key, value] of Object.entries(values)) {
    const input = document.getElementById(`layer-${key}`);
    if (input.tagName === "SELECT" && !Array.from(input.options).some(option => option.value === value)) {
      input.add(new Option(value, value));
    }
    input.value = value;
  }
  document.getElementById("layer-transparent").checked = layer.transparent !== false;
  updateLayerEditor();
  document.getElementById("layer-editor-dialog").showModal();
}

function applyLayerEditor(event) {
  event.preventDefault();
  const form = document.getElementById("layer-editor-form");
  const dictionary = getSettingsTexts();
  const nameInput = document.getElementById("layer-name");
  const urlInput = document.getElementById("layer-url");
  const name = nameInput.value.trim();
  const url = urlInput.value.trim();
  nameInput.setCustomValidity(!name ? dictionary.layerNameRequired : settingsLayers.some((layer, index) =>
    index !== editingLayerIndex && layer.name === name) ? dictionary.duplicateLayerName : "");
  let validUrl = false;
  try {
    const normalized = url.replace(/\{[a-z]+\}/g, "0");
    validUrl = /^https?:\/\/[^\s<>"{}|^`\\]+$/.test(normalized) && ["http:", "https:"].includes(new URL(normalized).protocol);
  } catch {}
  urlInput.setCustomValidity(validUrl ? "" : dictionary.invalidLayerUrl);
  const isWms = document.getElementById("layer-type").value === "wms";
  const wmsName = document.getElementById("layer-wms-name");
  wmsName.setCustomValidity(isWms && !wmsName.value.trim() ? dictionary.layerNameRequired : "");
  if (!form.reportValidity()) return;
  const layer = {
    ...(editingLayerIndex === null ? {} : settingsLayers[editingLayerIndex]),
    type: isWms ? "wms" : "xyz", name, url,
    attribution: document.getElementById("layer-attribution").value.trim()
  };
  const maxZoom = document.getElementById("layer-max-zoom").value;
  if (maxZoom === "") delete layer.maxZoom;
  else layer.maxZoom = Number(maxZoom);
  if (isWms) {
    layer.layer = wmsName.value.trim();
    layer.format = document.getElementById("layer-format").value;
    layer.transparent = document.getElementById("layer-transparent").checked;
    layer.version = document.getElementById("layer-version").value;
  } else {
    for (const key of ["layer", "format", "transparent", "version"]) delete layer[key];
  }
  if (editingLayerIndex === null) settingsLayers.push(layer);
  else settingsLayers[editingLayerIndex] = layer;
  renderSettingsLayers();
  document.getElementById("layer-editor-dialog").close();
}

export function initSettings(languageProvider) {
  getLanguage = languageProvider;
  const dialog = document.getElementById("settings-dialog");
  const form = document.getElementById("settings-form");
  const status = document.getElementById("settings-status");
  const confirmDialog = document.getElementById("settings-confirm");
  const busy = active => {
    form.setAttribute("aria-busy", String(active));
    form.querySelectorAll("input, select, textarea, button").forEach(control => { control.disabled = active; });
    document.getElementById("confirm-restore").disabled = active;
    if (!active) renderSettingsLayers();
  };
  document.getElementById("settings-add-xyz").onclick = () => openLayerEditor(null, "xyz");
  document.getElementById("settings-add-wms").onclick = () => openLayerEditor(null, "wms");
  document.getElementById("layer-type").onchange = updateLayerEditor;
  document.getElementById("layer-editor-cancel").onclick = () => document.getElementById("layer-editor-dialog").close();
  document.getElementById("layer-editor-form").onsubmit = applyLayerEditor;
  document.querySelectorAll("#layer-editor-form input").forEach(input => {
    input.addEventListener("input", () => input.setCustomValidity(""));
  });
  document.getElementById("btn-settings").onclick = async () => {
    translateSettings();
    dialog.showModal();
    busy(true);
    status.textContent = getSettingsTexts().loading;
    try {
      appConfig = await apiRequest("/api/config");
      fillSettings(appConfig);
      status.textContent = "";
    } catch (error) {
      status.textContent = error.message;
    } finally { busy(false); }
  };
  document.getElementById("settings-close").onclick = () => dialog.close();
  document.getElementById("settings-cancel").onclick = () => dialog.close();
  document.getElementById("settings-reset").onclick = () => confirmDialog.showModal();
  document.getElementById("cancel-restore").onclick = () => confirmDialog.close();
  document.getElementById("confirm-restore").onclick = async () => {
    busy(true);
    try {
      await apiRequest("/api/config/reset", { method: "POST", body: "{}" });
      window.location.reload();
    } catch (error) {
      confirmDialog.close();
      status.textContent = error.message;
      busy(false);
    }
  };
  form.onsubmit = async event => {
    event.preventDefault();
    status.textContent = "";
    try {
      const config = readSettings();
      busy(true);
      status.textContent = getSettingsTexts().saving;
      await apiRequest("/api/config", { method: "PUT", body: JSON.stringify(config) });
      window.location.reload();
    } catch (error) {
      status.textContent = error.message;
      busy(false);
    }
  };
}