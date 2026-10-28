import { L, Split, Timeline, timelineLanguages } from "./vendor.js";
import { i18nConfig } from "./i18n.js";
import { LeafletObjects } from "./leaflet-objects.js";
import { setLayerStyle } from "./map-styles.js";
import { appLinks } from "./config.js";
import { appConfig, setAppConfig, apiRequest, initSettings, translateSettings } from "./settings.js";
import "./style.css";

// ==========================================
// CONFIGURATION API & ÉTAT GLOBAL
// ==========================================

let DEFAULT_GRAPH_URI;
let DEFAULT_MAP_SETTINGS;
let nbResultsForLandmarks;
let currentLang = "fr";
let currentGraphId = null;
let selectedLandmarkUri = null;
let currentLandmarkValidity = null;
const resultSources = { snapshot: null, landmark: null };

// Cartes et composants JS
let mapSnapshot = null;
let mapLandmark = null;
let currentLandmarkGeometriesGroup = null; // Variable globale pour stocker les géométries actives sur mapLandmark
let timelineInstance = null;
let splitInstance = null;
let snapshotMarkerGroup = null;
let snapshotMask = null;
let snapshotMaskOpacity = 0.45;

// ==========================================
// INITIALISATION
// ==========================================
async function initializeApp() {
  initSettings(() => currentLang);
  try {
    setAppConfig(await apiRequest("/api/config"));
    DEFAULT_GRAPH_URI = appConfig.defaultGraphUri;
    DEFAULT_MAP_SETTINGS = appConfig.map;
    nbResultsForLandmarks = appConfig.landmarkSearchLimit;
    currentLang = appConfig.language;
    initAppHeader();
    initI18n();
    initDateControls(appConfig.dates.min, appConfig.dates.max, appConfig.dates.default);
    initEventListeners();
    await loadGraphs();
    const defaultMode = document.querySelector('input[name="tool"]:checked')?.value;
    switchMode(defaultMode);
  } catch (error) {
    const status = document.getElementById("app-status");
    status.textContent = error.message;
    status.classList.remove("hidden");
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}

// ==========================================
// 1. TRADUCTIONS & GESTION MULTILINGUE (i18n)
// ==========================================
function initI18n() {
  const langSelect = document.getElementById("lang-select");
  langSelect.value = currentLang;

  langSelect.addEventListener("change", (e) => {
    currentLang = e.target.value;
    document.documentElement.lang = currentLang;
    updateLanguageTexts();
    loadGraphs();
  });

  document.documentElement.lang = currentLang;
  updateLanguageTexts();
}

function initAppHeader() {
  const headerLinks = document.getElementById("app-header-links");

  if (!headerLinks) return;

  headerLinks.innerHTML = "";

  for (const key in appLinks) {
    const entry = appLinks[key];
    if (!entry) continue;

    const normalized = typeof entry === "string" 
      ? { url: entry, name: { mul: key } } 
      : entry;

    if (!normalized.url) continue;

    const a = document.createElement("a");
    a.href = normalized.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.className = "header-link";

    // On utilise data-i18n-applink pour stocker la clé du lien
    a.setAttribute("data-i18n-applink", key);

    if (normalized.icon) {
      const img = document.createElement("img");
      img.src = normalized.icon;
      img.className = "header-link-icon";
      a.appendChild(img);
    }

    headerLinks.appendChild(a);
  }

  // Appliquer les textes dans la langue actuelle
  updateLanguageTexts();
}

// Variable globale ou stockée dans app.js pour garder une référence sur les dernières versions chargées
let currentVersionsData = null; 
let currentTimelineData = null;

function refreshTimelineLanguage() {
  if (!timelineInstance || !currentTimelineData) return;
  const currentSlideIndex = timelineInstance.getCurrentSlide()?.slide_number || 1;
  const dict = i18nConfig[currentLang] || {};
  renderEvolutionTimeline(currentTimelineData, dict.timelineHeadline, currentSlideIndex);
}

function updateLanguageTexts() {
  const dict = i18nConfig[currentLang];

  document.title = dict.appTitle;
  document.documentElement.lang = currentLang;

  // 1. Traduction des éléments HTML classiques avec data-i18n
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) {
      if (el.tagName === "INPUT" && el.type === "text") {
        el.placeholder = dict[key];
      } else {
        el.textContent = dict[key];
      }
    }
  });

  // 2. Traduction dynamique des appLinks dans le Header
  document.querySelectorAll("[data-i18n-applink]").forEach(el => {
    const key = el.getAttribute("data-i18n-applink");
    const entry = appLinks[key];
    if (!entry) return;

    const nameDict = typeof entry === "string" ? { mul: entry } : entry.name;

    // Ordre de priorité : Langue courante -> 'mul' -> Premier texte trouvé
    const labelText = nameDict?.[currentLang] 
      || nameDict?.["mul"] 
      || (nameDict ? Object.values(nameDict)[0] : key);

    const img = el.querySelector("img");
    if (img) {
      img.alt = labelText;
      el.title = labelText; // Infobulle au survol pour les liens avec icône
    } else {
      el.textContent = labelText;
    }
  });

  // 3. Info-bulle du splitter / gutter
  const gutter = document.querySelector('.gutter-horizontal');
  if (gutter) {
    gutter.setAttribute('title', dict.resizeTooltip);
  }

  // 4. Rafraîchissement du composant de validité
  renderLandmarkValidity(currentLandmarkValidity);

  //5. Rafraîchissement de la timeline si elle est active
  refreshTimelineLanguage();
  translateSettings();
  updateSnapshotLegend();
  updateSnapshotMapMenu();
  updateSourceInfo();
  renderInfoPanel();
}

function updateSourceInfo() {
  const dict = i18nConfig[currentLang];
  const button = document.getElementById("btn-source-info");
  button.title = dict.sourceInfoTitle;
  button.setAttribute("aria-label", dict.sourceInfoTitle);
  const close = document.getElementById("source-info-close");
  close.title = dict.settings.close;
  close.setAttribute("aria-label", dict.settings.close);
  document.getElementById("source-info-endpoint").textContent = appConfig.sparqlEndpoint;
  document.getElementById("source-info-graph").textContent = currentGraphId || DEFAULT_GRAPH_URI;
  const mode = document.querySelector('input[name="tool"]:checked')?.value;
  document.getElementById("source-info-result").textContent = resultSources[mode]?.namedGraph || dict.sourceNoResult;
}

// ==========================================
// 2. SÉLECTION DU GRAPHE (HTTP)
// ==========================================
/**
 * Charge la liste des graphes via la requête SPARQL et met à jour le sélecteur UI
 */
async function loadGraphs() {
  try {
    let graphs = await apiRequest("/api/graphs");

    if (!graphs || graphs.length === 0) {
      console.warn("Aucun graphe trouvé dans le triple store.");
      if (DEFAULT_GRAPH_URI) {
        graphs = [{ id: DEFAULT_GRAPH_URI, name: i18nConfig[currentLang].defaultGraphName }];
      } else {
        console.error("Aucun graphe par défaut défini. Veuillez vérifier la configuration.");
        return;
      }
    }

    // Sélection du premier graphe par défaut
    currentGraphId = graphs.some(graph => graph.id === currentGraphId) ? currentGraphId
      : graphs.find(graph => graph.id === DEFAULT_GRAPH_URI)?.id || graphs[0].id;

    console.log("Graphes récupérés via SPARQL:", graphs);
    console.log("Graphe sélectionné par défaut:", currentGraphId);

    // Si > 1 graphe, on affiche et remplit le sélecteur
    const container = document.getElementById("graph-select-container");
    const select = document.getElementById("graph-select");

    if (graphs.length > 1) {
      select.innerHTML = "";

      graphs.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = g.name;
        select.appendChild(opt);
      });
      select.value = currentGraphId;

      container.classList.remove("hidden");

      select.onchange = (e) => {
        currentGraphId = e.target.value;
        onGraphChanged();
      };

      updateLanguageTexts();
    } else {
      // S'il n'y a qu'un seul graphe, on masque le sélecteur
      container.classList.add("hidden");
    }

  } catch (err) {
    console.error("Erreur lors de la récupération des graphes via SPARQL:", err);
    currentGraphId = DEFAULT_GRAPH_URI;
    const status = document.getElementById("app-status");
    status.textContent = err.message;
    status.classList.remove("hidden");
  }
  updateSourceInfo();
}
function onGraphChanged() {
  resultSources.snapshot = null;
  resultSources.landmark = null;
  updateSourceInfo();
  // 1. Vider le cache des landmarks car le graphe a changé
  landmarksByType = {};
  currentVersionsData = null;
  currentTimelineData = null;
  timelineInstance = null;
  clearLandmarkValidity();
  if (mapLandmark) clearMapLayers(mapLandmark);
  currentLandmarkGeometriesGroup = null;
  if (mapSnapshot) clearMapLayers(mapSnapshot);
  snapshotDrawnItems?.clearLayers();
  if (mapSnapshot && snapshotDrawnItems) snapshotDrawnItems.addTo(mapSnapshot);

  // 2. Vérifier si un mode est actuellement sélectionné
  const activeRadio = document.querySelector('input[name="tool"]:checked');
  
  if (activeRadio && activeRadio.value === "landmark") {
    loadLandmarkTypes();
  }
}

// ==========================================
// 3. SYNCHRONISATION DATE & CURSEUR
// ==========================================
function initDateControls(minDate, maxDate, defaultDate = null) {
  const dateInput = document.getElementById("snapshot-date");
  const sliderInput = document.getElementById("snapshot-slider");

  const minDateObj = new Date(minDate);
  const maxDateObj = new Date(maxDate);

  const minTime = minDateObj.getTime();
  const maxTime = maxDateObj.getTime();

  dateInput.min = minDateObj.toISOString().split("T")[0];
  dateInput.max = maxDateObj.toISOString().split("T")[0];

  sliderInput.min = minTime;
  sliderInput.max = maxTime;
  sliderInput.step = 24 * 60 * 60 * 1000; // 1 jour en millisecondes

  let initialTime;

  if (defaultDate) {
    initialTime = new Date(defaultDate).getTime();

    // On borne la date dans l'intervalle autorisé
    initialTime = Math.min(Math.max(initialTime, minTime), maxTime);
  } else {
    // Milieu de l'intervalle
    initialTime = Math.round((minTime + maxTime) / 2);

    // Arrondi au jour le plus proche
    initialTime -= initialTime % sliderInput.step;
  }

  sliderInput.value = initialTime;
  dateInput.value = new Date(initialTime).toISOString().split("T")[0];

  sliderInput.addEventListener("input", (e) => {
    const time = Number(e.target.value);
    dateInput.value = new Date(time).toISOString().split("T")[0];
  });

  dateInput.addEventListener("change", (e) => {
    if (e.target.value) {
      sliderInput.value = new Date(e.target.value).getTime();
    }
  });
}
// ==========================================
// 4. ÉCOUTEURS D'ÉVÉNEMENTS ET NAVIGATION
// ==========================================
function initEventListeners() {
  document.getElementById("snapshot-mask-opacity").addEventListener("input", (event) => {
    snapshotMaskOpacity = Number(event.target.value) / 100;
    document.getElementById("snapshot-mask-opacity-value").textContent = `${event.target.value} %`;
    snapshotMask?.setStyle({ fillOpacity: snapshotMaskOpacity });
  });
  document.getElementById("btn-source-info").addEventListener("click", () => {
    updateSourceInfo();
    document.getElementById("source-info-dialog").showModal();
  });
  // Changement de mode (Radio)
  document.querySelectorAll('input[name="tool"]').forEach(radio => {
    radio.addEventListener("change", (e) => {
      switchMode(e.target.value);
    });
  });

  // Validation Snapshot
  document.getElementById("btn-load-snapshot").addEventListener("click", () => {
    const selectedDate = document.getElementById("snapshot-date").value;
    const selectedArea = snapshotDrawnItems && snapshotDrawnItems.getLayers().length > 0 ? snapshotDrawnItems.toGeoJSON() : null;
    fetchSnapshotData(currentGraphId, selectedDate, selectedArea);
  });
  document.getElementById("btn-clear-snapshot").addEventListener("click", clearSnapshot);

  // Sélection Type Landmark
  document.getElementById("type-select").addEventListener("change", (e) => {
    const selectedType = e.target.value;
    if (selectedType) {
      enableLandmarkSearch(selectedType, nbResultsForLandmarks);
    } else {
      disableLandmarkSearch();
    }
  });

  // Validation Landmark
  document.getElementById("btn-load-landmark").addEventListener("click", () => {
    if (selectedLandmarkUri) {
      fetchLandmarkEvolution(currentGraphId, selectedLandmarkUri);
    }
  });
}

// --- GESTION DE L'AFFICHAGE CONDITIONNEL SNAPSHOT / LANDMARK ---
function switchMode(mode) {
  updateSourceInfo();
  const snapshotView = document.getElementById("snapshot-view");
  const landmarkView = document.getElementById("landmark-view");
  const snapshotControls = document.getElementById("snapshot-controls");
  const landmarkControls = document.getElementById("landmark-controls");

  if (mode === "snapshot") {
    // Afficher les contrôles & la vue Snapshot
    snapshotControls.classList.remove("hidden");
    snapshotView.classList.remove("hidden");

    // Masquer les contrôles & la vue Landmark
    landmarkView.classList.add("hidden");
    landmarkControls.classList.add("hidden");

    initSnapshotMap();
    setTimeout(() => mapSnapshot.invalidateSize(), 100);
  } else {
    // Masquer les contrôles & la vue Snapshot
    snapshotControls.classList.add("hidden");
    snapshotView.classList.add("hidden");

    // Afficher les contrôles & la vue Landmark
    landmarkView.classList.remove("hidden");
    landmarkControls.classList.remove("hidden");

    initLandmarkView();
    loadLandmarkTypes();
  }
}

// ==========================================
// 5. TRAITEMENT MAP
// ==========================================

function initLeafletTileLayers(tileLayersSettings, map, layerControl, tileLayers = {}) {
  // 1. Initialisation de chaque fond de carte configuré
  if (Array.isArray(tileLayersSettings)) {
    tileLayersSettings.forEach(setting => {
      const tileLayer = initLeafletTileLayer(setting);
      if (tileLayer) {
        layerControl.addBaseLayer(tileLayer, setting.name);
        tileLayers[setting.name] = tileLayer;
      }
    });
  }

  const layerNames = Object.keys(tileLayers);
  let tileLayerToDisplay = null;

  // 2. Choix de la couche à afficher par défaut (ou secours OSM)
  if (layerNames.length === 0) {
    const xyzUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
    var tileLayer = { type:"xyz", url:"https://tile.openstreetmap.de/{z}/{x}/{y}.png ", name:"OpenStreetMap", attribution:"© OpenStreetMap" };
    tileLayerToDisplay = initLeafletTileLayer(tileLayer);
  } else {
    tileLayerToDisplay = tileLayers[layerNames[0]];
  }

  // 3. Affichage du contrôle des couches uniquement s'il y a plus d'1 couche
  if (layerNames.length > 1 && layerControl) {
    layerControl.addTo(map);
  }

  // 4. Ajout du fond de carte par défaut à la carte
  if (tileLayerToDisplay && map) {
    tileLayerToDisplay.addTo(map);
  }

  return tileLayerToDisplay;
}

/**
 * Crée une couche standard de tuiles XYZ (ex: OpenStreetMap)
 */
function initLeafletTileLayerForXyz(url, options = {}) {
  const { maxZoom = 19, attribution = "", ...rest } = options;
  return L.tileLayer(url, { maxZoom, attribution, ...rest });
}

/**
 * Crée une couche de tuiles WMS (ex: GeoServer)
 */
function initLeafletTileLayerForWms(url, options = {}) {
  const { layer, format = "image/png", transparent = true, attribution = "", ...rest } = options;
  return L.tileLayer.wms(url, {
    layers: layer,
    format,
    transparent,
    attribution,
    ...rest
  });
}

/**
 * Registre des constructeurs selon le type de couche
 */
const TILE_LAYER_BUILDERS = {
  xyz: (setting) => initLeafletTileLayerForXyz(setting.url, setting),
  wms: (setting) => initLeafletTileLayerForWms(setting.url, setting)
};

/**
 * Initialise une couche Leaflet générique à partir d'un objet de configuration
 */
function initLeafletTileLayer(setting) {
  if (!setting?.type || !setting?.url) return null;

  const builder = TILE_LAYER_BUILDERS[setting.type.toLowerCase()];
  return builder ? builder(setting) : null;
}

function showMapLoadingState(isLoading) {
  const mapContainer = document.getElementById("map-snapshot");
  document.getElementById("btn-load-snapshot").disabled = isLoading;
  if (mapContainer) {
    mapContainer.classList.toggle("map-loading", isLoading);
  }
}

// ==========================================
// 6. TRAITEMENT SNAPSHOT
// ==========================================
let snapshotDrawnItems;
let snapshotDrawControl;
let snapshotRequestId = 0;
let snapshotLegendControl = null;

function updateSnapshotMapMenu() {
  const label = i18nConfig[currentLang].snapshotMapSettings;
  document.querySelectorAll(".snapshot-map-menu .leaflet-control-layers-toggle").forEach(toggle => {
    toggle.title = label;
    toggle.setAttribute("aria-label", label);
  });
}

function initMapOptionsMenu(layerControl) {
  const menu = layerControl.getContainer();
  menu.classList.add("snapshot-map-menu");
  const menuList = menu.querySelector(".leaflet-control-layers-list");
  const basemapTitle = document.createElement("h3");
  basemapTitle.className = "snapshot-map-section-title";
  basemapTitle.dataset.i18n = "snapshotBasemaps";
  basemapTitle.textContent = i18nConfig[currentLang].snapshotBasemaps;
  menuList.prepend(basemapTitle);
  updateSnapshotMapMenu();
  return menuList;
}

function updateSnapshotLegend() {
  const container = snapshotLegendControl?.getContainer();
  if (!container) return;
  const dictionary = i18nConfig[currentLang] || i18nConfig.fr;
  container.replaceChildren();
  container.setAttribute("aria-label", dictionary.snapshotLegendTitle);
  const title = document.createElement("strong");
  title.textContent = dictionary.snapshotLegendTitle;
  container.appendChild(title);
  for (const [existsForSure, label] of [
    [true, dictionary.snapshotLegendCertain],
    [false, dictionary.snapshotLegendUncertain]
  ]) {
    const row = document.createElement("div");
    row.className = "snapshot-legend-row";
    const swatch = document.createElement("span");
    swatch.className = "snapshot-legend-swatch";
    swatch.style.backgroundColor = getLandmarkStyle(existsForSure).polygon.color;
    swatch.setAttribute("aria-hidden", "true");
    row.append(swatch, document.createTextNode(label));
    container.appendChild(row);
  }
}

function initSnapshotMap() {
  if (!mapSnapshot) {
    mapSnapshot = L.map("map-snapshot").setView(
      DEFAULT_MAP_SETTINGS.center,
      DEFAULT_MAP_SETTINGS.zoom
    );

    // Fonds de carte
    const snapshotLayerControl = L.control.layers();
    const snapshotTileLayers = {};

    initLeafletTileLayers(
      DEFAULT_MAP_SETTINGS.tileLayers,
      mapSnapshot,
      snapshotLayerControl,
      snapshotTileLayers
    );
    const menuList = initMapOptionsMenu(snapshotLayerControl);
    const maskControl = document.getElementById("snapshot-mask-control");
    menuList.appendChild(maskControl);
    maskControl.classList.remove("hidden");
    L.DomEvent.disableClickPropagation(maskControl);
    L.DomEvent.disableScrollPropagation(maskControl);
    L.DomEvent.on(maskControl, "keydown keyup", L.DomEvent.stopPropagation);

    // Couche contenant les marqueurs
    snapshotMarkerGroup = L.layerGroup().addTo(mapSnapshot);

    // Couche contenant les géométries dessinées
    snapshotDrawnItems = new L.FeatureGroup();
    mapSnapshot.addLayer(snapshotDrawnItems);

    // Outil de dessin
    snapshotDrawControl = new L.Control.Draw({
      position: "topleft",
      draw: {
        polyline: false,
        polygon: true,
        rectangle: true,
        circle: false,
        circlemarker: false,
        marker: false
      },
      edit: {
        featureGroup: snapshotDrawnItems,
        remove: true
      }
    });

    mapSnapshot.addControl(snapshotDrawControl);
    snapshotLegendControl = L.control({ position: "bottomleft" });
    snapshotLegendControl.onAdd = () => {
      const container = L.DomUtil.create("div", "snapshot-legend");
      container.setAttribute("role", "group");
      L.DomEvent.disableClickPropagation(container);
      L.DomEvent.disableScrollPropagation(container);
      return container;
    };
    snapshotLegendControl.addTo(mapSnapshot);
    updateSnapshotLegend();

    // Lorsqu'une géométrie est créée
    mapSnapshot.on(L.Draw.Event.CREATED, function (e) {
      const layer = e.layer;
      snapshotDrawnItems.addLayer(layer);

      console.log(layer.toGeoJSON());
    });

    // Lorsqu'une géométrie est modifiée
    mapSnapshot.on(L.Draw.Event.EDITED, function (e) {
      e.layers.eachLayer(function (layer) {
        console.log("Edited:", layer.toGeoJSON());
      });
    });

    // Lorsqu'une géométrie est supprimée
    mapSnapshot.on(L.Draw.Event.DELETED, function (e) {
      console.log("Deleted", e.layers);
    });
  }
}

// ==========================================
// 7. TRAITEMENT LANDMARK EVOLUTION
// ==========================================
function initLandmarkView() {
  if (!splitInstance) {
    splitInstance = Split(['#pane-map', '#pane-timeline'], {
      sizes: [50, 50],
      minSize: 200,
      gutterSize: 10,
      cursor: 'col-resize',
      onDrag: () => {
        if (mapLandmark) mapLandmark.invalidateSize();
      }
    });

    const gutter = document.querySelector('.gutter-horizontal');
    if (gutter) {
      gutter.setAttribute('title', i18nConfig[currentLang].resizeTooltip);
    }
  }

  if (!mapLandmark) {
    mapLandmark = L.map("map-landmark").setView(
      DEFAULT_MAP_SETTINGS.center,
      DEFAULT_MAP_SETTINGS.zoom
    );

    const landmarkLayerControl = L.control.layers();
    const landmarkTileLayers = {};

    initLeafletTileLayers(
      DEFAULT_MAP_SETTINGS.tileLayers,
      mapLandmark,
      landmarkLayerControl,
      landmarkTileLayers
    );
    initMapOptionsMenu(landmarkLayerControl);
  }

  disableLandmarkSearch();
  setTimeout(() => mapLandmark.invalidateSize(), 100);
}

function resetTimelineEmptyState() {
  showTimelineState(i18nConfig[currentLang].chooseLandmark);
}

function formatDateValue(value) {
  if (!value) return null;
  return value.replace("T", " ").split(".")[0];
}

function formatDateWithPrecision(value, precision) {
  if (!value) return null;

  // On extrait YYYY-MM-DD (marche avec ISO String "1784-01-01T00:00:00Z" ou "1784-01-01")
  const isoString = String(value).trim();
  const datePart = isoString.split("T")[0]; // "YYYY-MM-DD"
  const [yearStr, monthStr, dayStr] = datePart.split("-");

  if (!yearStr) return formatDateValue(value);

  const year = parseInt(yearStr, 10);
  const precisionLower = (precision || "").toLowerCase();

  switch (precisionLower) {
    case "day":
      // Reconstitue YYYY-MM-DD
      return (monthStr && dayStr) ? `${yearStr}-${monthStr}-${dayStr}` : datePart;

    case "month":
      // Reconstitue YYYY-MM
      return monthStr ? `${yearStr}-${monthStr}` : yearStr;

    case "year":
      return yearStr;

    case "decade": {
      // 1869 -> 1860s
      const decadeStart = Math.floor(year / 10) * 10;
      return `${decadeStart}s`;
    }

    case "century": {
      // 1784 -> C18 (18ème siècle)
      const century = Math.ceil(year / 100);
      return `C${century}`;
    }

    default:
      return datePart || formatDateValue(value);
  }
}

// Fonction utilitaire pour extraire l'unité (ex: "http://www.w3.org/2006/time#unitYear" -> "year")
function formatTemporalBoundary(boundary) {
  if (!boundary) return null;

  if (boundary.kind === "crisp") {
    return boundary.value ? formatDateWithPrecision(boundary.value, boundary.precision) : null;
  }

  if (boundary.kind === "fuzzy") {
    const dict = i18nConfig[currentLang] || {};

    const begin = boundary.begin?.value 
      ? formatDateWithPrecision(boundary.begin.value, boundary.begin?.precision) 
      : null;
      
    const end = boundary.end?.value 
      ? formatDateWithPrecision(boundary.end.value, boundary.end?.precision) 
      : null;

    if (begin && end) {
      // Ex: "entre 1784-01 et 1869-09"
      return `${dict.betweenTime || "between"} ${begin} ${dict.andTime || "and"} ${end}`;
    }

    if (begin) {
      // Ex: "après 1784-01"
      return `${dict.afterTime || "after"} ${begin}`;
    }

    if (end) {
      // Ex: "avant 1869-09"
      return `${dict.beforeTime || "before"} ${end}`;
    }
  }

  return null;
}

function getTemporalMetadata(boundary) {
  if (!boundary) return "";

  const pieces = [];
  if (boundary.calendar) pieces.push(boundary.calendar);
  if (boundary.precision) pieces.push(boundary.precision);

  if (boundary.kind === "fuzzy") {
    const beginMeta = boundary.begin?.calendar || boundary.begin?.precision;
    const endMeta = boundary.end?.calendar || boundary.end?.precision;
    const extra = [beginMeta, endMeta].filter(Boolean);
    if (extra.length) pieces.push(...extra);
  }

  return pieces.length ? ` (${pieces.join(", ")})` : "";
}

function renderLandmarkValidity(validity) {
  const container = document.getElementById("landmark-validity");
  if (!container) return;

  currentLandmarkValidity = validity;
  if (!validity || (!validity.start && !validity.end)) {
    container.classList.add("hidden");
    container.textContent = "";
    return;
  }

  const dict = i18nConfig[currentLang];

  const startText = formatTemporalBoundary(validity.start);
  const endText = formatTemporalBoundary(validity.end);

  const parts = [];
  if (startText) {
    parts.push(
      `<span><strong>${dict.validityCreated}</strong> : ${escapeHtml(startText)}</span>`
    );
  }
  if (endText) {
    parts.push(
      `<span><strong>${dict.validityDisappeared}</strong> : ${escapeHtml(endText)}</span>`
    );
  }

  const intervalText = parts.length 
    ? parts.join('<span style="opacity: 0.5; margin: 0 6px;">|</span>') 
    : `<span>${dict.validityUnknown}</span>`;

  // Application de la couleur bleue globale sur tout le conteneur (#0056b3 ou de la couleur exacte souhaitée)
  container.innerHTML = `
    <div style="display: inline-flex; align-items: center; gap: 12px; flex-wrap: wrap; color: #0056b3;">
      
      <!-- Titre principal -->
      <span style="font-weight: 800; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; background: rgba(0, 86, 179, 0.1); padding: 3px 8px; border-radius: 4px;">
        ${dict.validityLabel}
      </span>
      
      <!-- Informations (Dates) en bleu avec libellés en gras -->
      <div style="display: inline-flex; align-items: center; gap: 6px;">
        ${intervalText}
      </div>

    </div>
  `;
  container.classList.remove("hidden");
}

function clearLandmarkValidity() {
  renderLandmarkValidity(null);
}

function showTimelineState(message, isLoading = false) {
  const container = document.getElementById("timeline");
  if (!container) return;

  container.classList.add("timeline-empty-state");
  container.style.display = "flex";
  container.style.width = "100%";
  container.style.height = "100%";
  container.style.minHeight = "300px";

  container.innerHTML = `
    <div class="timeline-placeholder">
      ${isLoading ? '<span class="timeline-loader" aria-hidden="true"></span>' : ""}
      <p data-i18n="chooseLandmark">${message}</p>
    </div>
  `;
}
/**
 * Charge les types de landmarks depuis SPARQL et remplit le sélecteur
 */
async function loadLandmarkTypes() {
  const typeSelect = document.getElementById("type-select");

  try {
    const types = await apiRequest(`/api/landmark-types?${new URLSearchParams({ graph: currentGraphId })}`);

    // 4. Reconstitution des options du sélecteur
    typeSelect.innerHTML = `<option value="" data-i18n="typePlaceholder">${i18nConfig[currentLang].typePlaceholder}</option>`;

    types.forEach(type => {
      const opt = document.createElement("option");
      opt.value = type.id;
      opt.textContent = type.label;
      typeSelect.appendChild(opt);
    });

    // Réinitialise et désactive la recherche de landmark tant qu'aucun type n'est choisi
    disableLandmarkSearch();

  } catch (err) {
    console.error("Erreur chargement des types de landmarks via SPARQL:", err);
    
    // En cas d'erreur, réinitialiser proprement le sélecteur
    typeSelect.innerHTML = `<option value="" data-i18n="errorFetch">${i18nConfig[currentLang].errorFetch}</option>`;
    disableLandmarkSearch();
  }
}

// Globales dans app.js
let landmarksByType = {}; // Cache : { "http://.../TypeA": [ {uri, label}, ... ], ... }

/**
 * Active la recherche de landmarks en utilisant un système de cache par type.
 * @param {string} selectedTypeUri - URI du type de landmark choisi
 */
// Fonction utilitaire pour nettoyer les accents
function removeAccents(str) {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

async function enableLandmarkSearch(selectedTypeUri, nbResults = 10) {
  const input = document.getElementById("landmark-input");
  const dropdown = document.getElementById("landmark-dropdown");
  const btnLoad = document.getElementById("btn-load-landmark");
  const loader = document.getElementById("landmark-loader");

  const renderSuggestions = (queryText = "") => {
    // 1. Normalisation du texte tapé (minuscules + sans accents)
    const normalizedQuery = removeAccents(queryText.trim().toLowerCase());
    
    const items = landmarksByType[selectedTypeUri] || [];
    
    // 2. Filtrage en normalisant également le libellé de chaque item
    const matches = items
      .filter(item => removeAccents(item.label.toLowerCase()).includes(normalizedQuery))
      .slice(0, nbResults);

    dropdown.innerHTML = "";

    if (matches.length === 0) {
      const emptyItem = document.createElement("div");
      emptyItem.className = "dropdown-item empty";
      emptyItem.textContent = i18nConfig[currentLang].noResults;
      dropdown.appendChild(emptyItem);
      dropdown.classList.remove("hidden");
      return;
    }

    matches.forEach(item => {
      const div = document.createElement("div");
      div.className = "dropdown-item";
      div.textContent = item.label;

      div.onclick = () => {
        input.value = item.label;
        selectedLandmarkUri = item.uri;
        dropdown.classList.add("hidden");
        btnLoad.disabled = false;
      };

      dropdown.appendChild(div);
    });

    dropdown.classList.remove("hidden");
  };

  // Réinitialisation des états UI
  input.value = "";
  selectedLandmarkUri = null;
  btnLoad.disabled = true;
  dropdown.innerHTML = "";
  dropdown.classList.add("hidden");
  loader.classList.add("hidden");

  // ---------------------------------------------------------------
  // VERIFICATION DU CACHE
  // ---------------------------------------------------------------
  if (!landmarksByType[selectedTypeUri]) {
    input.disabled = true;
    input.placeholder = i18nConfig[currentLang].loading || "Chargement...";
    loader.classList.remove("hidden");

    try {
      landmarksByType[selectedTypeUri] = await apiRequest(`/api/landmarks?${new URLSearchParams({ graph: currentGraphId, type: selectedTypeUri })}`);
    } catch (err) {
      console.error(`Erreur chargement landmarks pour le type ${selectedTypeUri}:`, err);
      input.placeholder = i18nConfig[currentLang].errorFetch;
      loader.classList.add("hidden");
      return;
    }
  }

  // Activer le champ après chargement (ou récupération du cache)
  input.disabled = false;
  input.placeholder = i18nConfig[currentLang].entityPlaceholder;
  loader.classList.add("hidden");

  // ---------------------------------------------------------------
  // RECHERCHE EN MÉMOIRE ET AUTOCOMPLÉTION
  // ---------------------------------------------------------------
  input.onfocus = () => renderSuggestions(input.value);
  input.onclick = () => renderSuggestions(input.value);

  input.oninput = (e) => {
    const queryText = e.target.value;

    selectedLandmarkUri = null;
    btnLoad.disabled = true;
    renderSuggestions(queryText);
  };
}

function disableLandmarkSearch() {
  const input = document.getElementById("landmark-input");
  input.disabled = true;
  input.value = "";
  selectedLandmarkUri = null;
  document.getElementById("btn-load-landmark").disabled = true;
  document.getElementById("landmark-dropdown").classList.add("hidden");
  timelineInstance = null;
  currentTimelineData = null;
  currentVersionsData = null;
  if (currentLandmarkGeometriesGroup && mapLandmark) mapLandmark.removeLayer(currentLandmarkGeometriesGroup);
  currentLandmarkGeometriesGroup = null;
  clearLandmarkValidity();
  showTimelineState(i18nConfig[currentLang].chooseLandmark);
}

async function fetchLandmarkEvolution(graphId, landmarkUri) {
  resultSources.landmark = null;
  updateSourceInfo();
  timelineInstance = null;
  currentTimelineData = null;
  currentVersionsData = null;
  clearLandmarkValidity();
  if (currentLandmarkGeometriesGroup) mapLandmark.removeLayer(currentLandmarkGeometriesGroup);
  currentLandmarkGeometriesGroup = null;
  showTimelineState(i18nConfig[currentLang].loadingHistory, true);

  try {
    const data = await apiRequest(`/api/evolution?${new URLSearchParams({ graph: graphId, landmark: landmarkUri })}`);
    if (graphId !== currentGraphId || landmarkUri !== selectedLandmarkUri) return;
    resultSources.landmark = data.source;
    updateSourceInfo();
    renderLandmarkValidity(data.validity);
    if (data.timeline.events.length === 0) {
      showTimelineState(i18nConfig[currentLang].timelineNoHistory);
      return;
    }
    currentVersionsData = data.versions;
    currentTimelineData = data.timeline;
    renderEvolutionTimeline(data.timeline, i18nConfig[currentLang].timelineHeadline);

  } catch (err) {
    console.error("Erreur chargement évolution :", err);
    showTimelineState(i18nConfig[currentLang].historyError);
  }
}

function renderEvolutionTimeline(data, headline, startAt = 1) {
  const container = document.getElementById("timeline");
  container.classList.remove("timeline-empty-state");
  container.style.display = "block";
  container.innerHTML = "";
  timelineInstance = new Timeline("timeline", {
    ...data, title: { text: { headline } }
  }, { scale_factor: 1, language: timelineLanguages[currentLang], font: false, start_at_slide: startAt, hash_bookmark: false, initial_zoom: 0 });
  timelineInstance.on("change", () => actionsOnTimelineChange());
  timelineInstance.on("loaded", () => actionsOnTimelineChange());
}

// Variables globales pour suivre l'état de la sélection (Panneau "figé")
let selectedFeatureId = null;
let selectedLayer = null;
let infoPanelControl = null;
let infoPanelData = null;


// ===================================================================
// 1. STYLES DES GÉOMÉTRIES (Marker, LineString, Polygon)
// ===================================================================

const lo = new LeafletObjects(L) ; // Instance globale pour créer des objets Leaflet

const LANDMARK_STYLES = {
  default : {marker:lo.blueDot, polyline:lo.blueDefaultLineStringStyle, polygon:lo.blueDefaultPolygonStyle},
  defaultSelected : {marker:lo.blueMarker, polyline:lo.blueSelectedLineStringStyle, polygon:lo.blueSelectedPolygonStyle},
  existsForSure: {marker:lo.greenDot, polyline:lo.greenDefaultLineStringStyle, polygon:lo.greenDefaultPolygonStyle},
  existsForSureSelected: {marker:lo.greenMarker, polyline:lo.greenSelectedLineStringStyle, polygon:lo.greenSelectedPolygonStyle},
  existNotForSure: {marker:lo.redDot, polyline:lo.redDefaultLineStringStyle, polygon:lo.redDefaultPolygonStyle},
  existNotForSureSelected: {marker:lo.redMarker, polyline:lo.redSelectedLineStringStyle, polygon:lo.redSelectedPolygonStyle}
};

/**
 * Retourne le style Leaflet adapté selon la valeur de existsForSure et l'état de sélection.
 * 
 * @param {boolean|null} [existsForSure=null] - État de certitude (true, false, ou null/undefined)
 * @param {boolean} [selected=false] - Si la couche est actuellement sélectionnée
 * @returns {Object} Le dictionnaire de styles { marker, polyline, polygon }
 */
function getLandmarkStyle(existsForSure = null, selected = false) {
  // 1. Cas par défaut (null ou undefined)
  if (existsForSure === null || existsForSure === undefined) {
    return selected ? LANDMARK_STYLES.defaultSelected : LANDMARK_STYLES.default;
  }

  // 2. Cas certain (true)
  if (existsForSure === true) {
    return selected ? LANDMARK_STYLES.existsForSureSelected : LANDMARK_STYLES.existsForSure;
  }

  // 3. Cas incertain (false)
  return selected ? LANDMARK_STYLES.existNotForSureSelected : LANDMARK_STYLES.existNotForSure;
}

// ===================================================================
// 2. PANNEAU D'INFORMATION FIXE (Coin de la carte)
// ===================================================================

/**
 * Initialise le panneau d'information dans le coin bas-droit de la carte.
 */
function initInfoPanelControl(map) {
  if (infoPanelControl) return;

  infoPanelControl = L.control({ position: 'bottomright' });

  infoPanelControl.onAdd = function () {
    const div = L.DomUtil.create('div', 'landmark-info-panel');
    // Empêcher la propagation des clics dans le panneau vers la carte Leaflet
    L.DomEvent.disableClickPropagation(div);

    Object.assign(div.style, {
      backgroundColor: '#ffffff',
      padding: '12px 16px',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
      fontFamily: 'sans-serif',
      fontSize: '13px',
      lineHeight: '1.4',
      color: '#1e293b'
    });
    return div;
  };

  infoPanelControl.addTo(map);
  infoPanelData = null;
  renderInfoPanel();
}

/**
 * Met à jour le contenu du panneau d'information avec un tableau pour les attributs
 * et un titre cliquable (URI).
 */
function updateInfoPanel(properties, id, graphId) {
  infoPanelData = properties ? { properties, id } : null;
  renderInfoPanel();
}

function renderInfoPanel() {
  if (!infoPanelControl) return;

  const div = infoPanelControl.getContainer();
  const dict = i18nConfig[currentLang];

  if (!infoPanelData) {
    div.innerHTML = `<em>${escapeHtml(dict.infoPanelHint)}</em>`;
    return;
  }

  const { properties, id } = infoPanelData;
  const name = escapeHtml(properties.name || dict.infoPanelUnnamed);
  const uri = /^https?:\/\//.test(id || "") ? escapeHtml(id) : "#";
  const attributes = properties.attributes || [];
  const isPinned = selectedFeatureId === id;

  // Construction du tableau HTML des attributs
  let attrHtml = "";
  if (attributes.length > 0) {
    attrHtml = `
      <div style="margin-top: 10px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
        <strong style="display: block; margin-bottom: 6px; color: #475569;">${escapeHtml(dict.infoPanelAttributes)}</strong>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
          <thead>
            <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
              <th style="padding: 4px 6px; color: #64748b; font-weight: 600;">${escapeHtml(dict.infoPanelType)}</th>
              <th style="padding: 4px 6px; color: #64748b; font-weight: 600;">${escapeHtml(dict.infoPanelValues)}</th>
            </tr>
          </thead>
          <tbody>
            ${attributes.map(attr => `
              <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 4px 6px; font-weight: 500; color: #334155; vertical-align: top;">${escapeHtml(attr.type)}</td>
                <td style="padding: 4px 6px; color: #0f172a;">${attr.values.map(escapeHtml).join(", ")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  // Le Nom est désormais la balise <a> cliquable qui redirige vers l'URI
  div.innerHTML = `
    <div>
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 6px;">
        <h4 style="margin: 0; min-width: 0; overflow-wrap: anywhere; font-size: 15px; line-height: 1.3;">
          <a href="${uri}" target="_blank" 
             title="${uri}" 
             style="color: #2563eb; text-decoration: none; font-weight: 600;"
             onmouseover="this.style.textDecoration='underline'" 
             onmouseout="this.style.textDecoration='none'">
            ${name}
          </a>
        </h4>
        ${isPinned ? `<span style="font-size: 10px; background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; white-space: nowrap;">${escapeHtml(dict.infoPanelSelected)}</span>` : ''}
      </div>
      
      ${attrHtml}
      
    </div>
  `;
}

// ===================================================================
// 3. FONCTIONS DE TRAITEMENT SPATIAL & DONNÉES
// ===================================================================

/**
 * Applique un masque inversé pour assombrir tout l'extérieur de selectedArea.
 * Accepte une FeatureCollection, une Feature ou directement une Geometry.
 */
function applySelectedAreaMask(map, selectedArea) {
  if (snapshotMask) {
    map.removeLayer(snapshotMask);
    snapshotMask = null;
  }
  if (!selectedArea) return;

  // 1. Détection et extraction des features (gère FeatureCollection, Feature seule ou Geometry)
  let features = [];
  
  if (selectedArea.type === "FeatureCollection" && Array.isArray(selectedArea.features)) {
    features = selectedArea.features;
  } else if (selectedArea.type === "Feature") {
    features = [selectedArea];
  } else if (selectedArea.type && selectedArea.coordinates) {
    // Cas où on passe directement un objet geometry
    features = [{ type: "Feature", geometry: selectedArea }];
  }

  if (features.length === 0) return;

  // 2. Cadre extérieur géant (sens horaire pour Leaflet)
  const outerWorld = [
    [90, -360],
    [90, 360],
    [-90, 360],
    [-90, -360]
  ];

  const holes = [];
  const convertRing = (ring) => ring.map(coord => [coord[1], coord[0]]);

  // 3. Parcourir toutes les features de la FeatureCollection
  features.forEach(feature => {
    const geom = feature.geometry;
    if (!geom) return;

    if (geom.type === "Polygon") {
      geom.coordinates.forEach(ring => {
        holes.push(convertRing(ring));
      });
    } else if (geom.type === "MultiPolygon") {
      geom.coordinates.forEach(polygonCoords => {
        polygonCoords.forEach(ring => {
          holes.push(convertRing(ring));
        });
      });
    }
  });

  // 4. Ajouter le masque à la carte
  if (holes.length > 0) {
    snapshotMask = L.polygon([outerWorld, ...holes], {
      color: 'transparent',
      fillColor: '#000000',
      fillOpacity: snapshotMaskOpacity,
      interactive: false // Laisse passer les événements de clic
    });

    snapshotMask.addTo(map);
  }
}

// ===================================================================
// 4. CRÉATION DU CALQUE GEOJSON & INTERACTIONS (Zoom + Figeage)
// ===================================================================

/**
 * Réinitialise la sélection courante.
 */
function clearSelection() {
  if (selectedLayer) {
    const prevExists = selectedLayer.feature.properties.existsForSure;
    setLayerStyle(selectedLayer, getLandmarkStyle(prevExists, false));
  }
  selectedFeatureId = null;
  selectedLayer = null;
  updateInfoPanel(null, null, null);
}


/**
 * Crée la couche GeoJSON Leaflet configurée avec les interactions et styles.
 */
function createGeoJsonLayer(featureCollection, graphId, map) {
  return L.geoJSON(featureCollection, {
    pointToLayer: (feature, latlng) => L.marker(latlng, {
      icon: getLandmarkStyle(feature.properties.existsForSure, false).marker
    }),

    onEachFeature: (feature, layer) => {
      // Si la couche est un marqueur, on applique l'icône initiale
      const existsForSure = feature.properties.existsForSure;
      const initialStyle = getLandmarkStyle(existsForSure, false);
      const selectedStyle = getLandmarkStyle(existsForSure, true);
      setLayerStyle(layer, initialStyle);

      layer.on({
        mouseover: (e) => {
          if (selectedFeatureId) return;
          const target = e.target;
          setLayerStyle(target, selectedStyle);
          updateInfoPanel(feature.properties, feature.id, graphId);
        },

        mouseout: (e) => {
          if (selectedFeatureId) return;
          const target = e.target;
          setLayerStyle(target, initialStyle);
          updateInfoPanel(null, null, graphId);
        },

        click: (e) => {
          L.DomEvent.stopPropagation(e);

          if (selectedLayer && selectedLayer !== layer) {
            const prevExists = selectedLayer.feature.properties.existsForSure;
            setLayerStyle(selectedLayer, getLandmarkStyle(prevExists, false));
          }

          selectedFeatureId = feature.id;
          selectedLayer = layer;
          setLayerStyle(layer, selectedStyle);

          updateInfoPanel(feature.properties, feature.id, graphId);

          if (typeof layer.getBounds === 'function') {
            map.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 18 });
          } else if (typeof layer.getLatLng === 'function') {
            map.flyTo(layer.getLatLng(), 17, { duration: 0.8 });
          }
        }
      });
    }
  });
}


// ===================================================================
// 5. FONCTION PRINCIPALE EXÉCUTABLE
// ===================================================================

function clearSnapshot() {
  resultSources.snapshot = null;
  updateSourceInfo();
  snapshotRequestId++;
  if (snapshotDrawControl) {
    Object.values(snapshotDrawControl._toolbars).forEach(toolbar => toolbar.disable());
  }
  clearSelection();
  snapshotDrawnItems?.clearLayers();
  clearMapLayers(mapSnapshot);
  if (infoPanelControl) {
    infoPanelControl.remove();
    infoPanelControl = null;
  }
  clearTimeout(window._mapNotificationTimeout);
  document.getElementById("map-notification-toast")?.remove();
  showMapLoadingState(false);
}

async function fetchSnapshotData(graphId, selectedDate, selectedArea) {
  resultSources.snapshot = null;
  updateSourceInfo();
  const requestId = ++snapshotRequestId;
  showMapLoadingState(true);

  try {
    clearMapLayers(mapSnapshot);
    clearSelection();

    // Initialiser le panneau fixe dans le coin de la carte
    initInfoPanelControl(mapSnapshot);

    // ÉCOUTEUR CLIC SUR LA CARTE : Réinitialise tout lors d'un clic dans le vide
    mapSnapshot.off('click');
    mapSnapshot.on('click', () => {
      clearSelection();
    });

    // 1. Masque extérieur pour assombrir autour de selectedArea
    applySelectedAreaMask(mapSnapshot, selectedArea);

    // 2. Charger les données
    const featureCollection = await apiRequest("/api/snapshot", {
      method: "POST",
      body: JSON.stringify({ graph: graphId, date: selectedDate, area: selectedArea })
    });
    if (requestId !== snapshotRequestId || graphId !== currentGraphId) return;
    resultSources.snapshot = featureCollection.source;
    updateSourceInfo();

    if (featureCollection.features.length === 0) {
      showMapNotification(i18nConfig[currentLang]?.noDataForDate || "Aucune donnée à cette date.");
      return;
    }

    // 3. Générer et afficher le GeoJSON
    const geoJsonLayer = createGeoJsonLayer(featureCollection, graphId, mapSnapshot);
    console.log("GeoJSON Layer créé :", featureCollection);
    geoJsonLayer.addTo(mapSnapshot);

    // 4. Ajuster le zoom initial
    if (selectedArea) {
      mapSnapshot.fitBounds(L.geoJSON(selectedArea).getBounds(), { padding: [20, 20] });
    } else if (geoJsonLayer.getLayers().length > 0) {
      mapSnapshot.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    }

  } catch (err) {
    if (requestId !== snapshotRequestId) return;
    console.error("Erreur lors de la récupération du snapshot :", err);
    showMapNotification(i18nConfig[currentLang]?.snapshotError || "Erreur de chargement des données.");
  } finally {
    if (requestId === snapshotRequestId) showMapLoadingState(false);
  }
}

/**
 * Nettoie toutes les couches/marqueurs temporaires de la carte Leaflet ciblée,
 * sans supprimer son fond de carte de base (TileLayer).
 *
 * @param {L.Map} targetMap - L'instance de la carte Leaflet à nettoyer (ex: mapLandmark ou mapSnapshot).
 */
function clearMapLayers(targetMap) {
  if (!targetMap) return;
  if (targetMap === mapSnapshot) snapshotMask = null;

  targetMap.eachLayer((layer) => {
    // Conserve le fond de carte (TileLayer)
    // et supprime uniquement les autres calques (Marker, Polygon, GeoJSON, etc.)
    if (!(layer instanceof L.TileLayer) && layer !== snapshotDrawnItems) {
      targetMap.removeLayer(layer);
    }
  });
}
/**
 * Affiche une notification à l'utilisateur (Toast / Alerte).
 * Si tu utilises une librairie comme Toastify ou SweetAlert, tu peux adapter ce code.
 * Sinon, cette version crée un message élégant directement au-dessus de la carte.
 * 
 * @param {string} message - Le texte à afficher
 * @param {number} duration - Durée d'affichage en millisecondes (défaut : 3000ms)
 */
function showMapNotification(message, duration = 3000) {
  // Recherche un conteneur de notification existant ou en crée un sur la carte
  let notificationContainer = document.getElementById('map-notification-toast');

  if (!notificationContainer) {
    notificationContainer = document.createElement('div');
    notificationContainer.id = 'map-notification-toast';
    
    // Style minimaliste et moderne pour superposer sur la carte
    Object.assign(notificationContainer.style, {
      position: 'absolute',
      top: '20px',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: '1000',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      color: '#ffffff',
      padding: '10px 18px',
      borderRadius: '8px',
      fontSize: '14px',
      fontWeight: '500',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
      opacity: '0',
      pointerEvents: 'none'
    });

    // S'assure que le conteneur de la carte est en position relative
    const mapElement = mapSnapshot?.getContainer() || mapLandmark?.getContainer();
    if (mapElement) {
      mapElement.style.position = 'relative';
      mapElement.appendChild(notificationContainer);
    } else {
      document.body.appendChild(notificationContainer);
    }
  }

  // Injecter le texte et animer l'apparition
  notificationContainer.textContent = message;
  notificationContainer.style.opacity = '1';
  notificationContainer.style.transform = 'translateX(-50%) translateY(0px)';

  // Masquer automatiquement après la durée spécifiée
  clearTimeout(window._mapNotificationTimeout);
  window._mapNotificationTimeout = setTimeout(() => {
    notificationContainer.style.opacity = '0';
    notificationContainer.style.transform = 'translateX(-50%) translateY(-10px)';
  }, duration);
}

// ########################### Test ##################################

function actionsOnTimelineChange() {
  if (!timelineInstance) return;
  const currentSlide = timelineInstance.getCurrentSlide();
  const selectedVersion = currentVersionsData?.[currentSlide?.data?.unique_id];
  if (!mapLandmark) return;
  if (currentLandmarkGeometriesGroup) {
    mapLandmark.removeLayer(currentLandmarkGeometriesGroup);
    currentLandmarkGeometriesGroup = null;
  }
  if (!selectedVersion?.geometry) return;
  const style = getLandmarkStyle(null, true);
  currentLandmarkGeometriesGroup = L.geoJSON(selectedVersion.geometry, {
    pointToLayer: (feature, latlng) => L.marker(latlng, { icon: style.marker }),
    onEachFeature: (feature, layer) => setLayerStyle(layer, style)
  }).addTo(mapLandmark);
  const bounds = currentLandmarkGeometriesGroup.getBounds();
  if (bounds.isValid()) mapLandmark.fitBounds(bounds, { padding: [20, 20], maxZoom: 17 });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}