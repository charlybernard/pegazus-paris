const { readFile, mkdir, rename, writeFile } = require("node:fs/promises");
const path = require("node:path");

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function assert(condition, message) {
  if (!condition) throw new HttpError(400, message);
}

function validUri(value) {
  return typeof value === "string" && /^https?:\/\/[^\s<>"{}|^`\\]+$/.test(value) && URL.canParse(value);
}

function validDate(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}

function validateConfig(config) {
  assert(config && typeof config === "object" && !Array.isArray(config), "Configuration invalide.");
  const keys = ["sparqlEndpoint", "defaultGraphUri", "map", "dates", "language", "queryLanguage", "landmarkSearchLimit", "timeCalendarUri", "timeDelayYears"];
  assert(Object.keys(config).length === keys.length && keys.every(key => Object.hasOwn(config, key)), "Champs de configuration invalides.");
  for (const key of ["sparqlEndpoint", "defaultGraphUri", "timeCalendarUri"]) {
    assert(validUri(config[key]), `${key} : URL HTTP(S) invalide.`);
  }
  const endpoint = new URL(config.sparqlEndpoint);
  assert(!endpoint.username && !endpoint.password && !endpoint.hash, "Endpoint : identifiants et fragment interdits dans l'URL.");
  assert(["fr", "en", "es"].includes(config.language), "Langue d'interface invalide.");
  assert(typeof config.queryLanguage === "string" && /^[a-z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$/.test(config.queryLanguage), "Langue de requete invalide.");
  assert(Number.isInteger(config.landmarkSearchLimit) && config.landmarkSearchLimit >= 1 && config.landmarkSearchLimit <= 1000, "Limite de recherche : 1 a 1000.");
  assert(Number.isInteger(config.timeDelayYears) && config.timeDelayYears >= 0 && config.timeDelayYears <= 1000, "Marge temporelle : 0 a 1000 ans.");
  const map = config.map;
  assert(map && Array.isArray(map.center) && map.center.length === 2, "Centre de carte invalide.");
  assert(Number.isFinite(map.center[0]) && Math.abs(map.center[0]) <= 90, "Latitude : -90 a 90.");
  assert(Number.isFinite(map.center[1]) && Math.abs(map.center[1]) <= 180, "Longitude : -180 a 180.");
  assert(Number.isInteger(map.zoom) && map.zoom >= 0 && map.zoom <= 19, "Zoom : 0 a 19.");
  assert(Array.isArray(map.tileLayers) && map.tileLayers.length > 0 && map.tileLayers.length <= 30, "Fonds de carte invalides.");
  for (const layer of map.tileLayers) {
    assert(layer && ["xyz", "wms"].includes(layer.type) && typeof layer.name === "string" && layer.name.trim(), "Fond de carte invalide.");
    assert(typeof layer.url === "string" && validUri(layer.url.replace(/\{[a-z]+\}/g, "0")), "URL de fond de carte invalide.");
    assert(layer.type !== "wms" || typeof layer.layer === "string" && layer.layer.trim(), "Couche WMS manquante.");
  }
  assert(config.dates && validDate(config.dates.min) && validDate(config.dates.max), "Dates invalides (AAAA-MM-JJ).");
  assert(config.dates.min <= config.dates.max, "La date minimale doit preceder la date maximale.");
  assert(config.dates.default === null || validDate(config.dates.default) && config.dates.default >= config.dates.min && config.dates.default <= config.dates.max, "Date par defaut hors intervalle.");
  return structuredClone(config);
}

function createConfigStore(filename = path.join(__dirname, "config.json")) {
  let queue = Promise.resolve();
  const defaults = async () => JSON.parse(await readFile(path.join(__dirname, "config.defaults.json"), "utf8"));
  const read = async () => {
    try {
      return validateConfig(JSON.parse(await readFile(filename, "utf8")));
    } catch (error) {
      if (error.code === "ENOENT") return defaults();
      throw error;
    }
  };
  const save = config => {
    const validated = validateConfig(config);
    const operation = queue.then(async () => {
      await mkdir(path.dirname(filename), { recursive: true });
      const temporary = `${filename}.tmp`;
      await writeFile(temporary, JSON.stringify(validated, null, 2) + "\n", { mode: 0o600 });
      await rename(temporary, filename);
      return validated;
    });
    queue = operation.catch(() => {});
    return operation;
  };
  return { read, save, defaults, reset: async () => save(await defaults()) };
}

module.exports = { createConfigStore, validateConfig, validUri, validDate, assert, HttpError };