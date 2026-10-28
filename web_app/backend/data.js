const { wktToGeoJSON, geojsonToWKT } = require("@terraformer/wkt");
const proj4 = require("proj4");
const queries = require("./queries");
const { createTimelineFeature } = require("./time");
const { assert, HttpError, validUri, validDate } = require("./config-store");

proj4.defs("EPSG:2154", "+proj=lcc +lat_1=49 +lat_2=44 +lat_0=46.5 +lon_0=3 +x_0=700000 +y_0=6600000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs");
const WKT_TYPE = "http://www.opengis.net/ont/geosparql#wktLiteral";

function uri(value, field) {
  assert(validUri(value), `${field} : URI HTTP(S) invalide.`);
  return value;
}

function geometryFromWkt(value) {
  const crs = value.match(/^\s*<([^>]+)>\s*/);
  const code = crs?.[1].match(/\/EPSG\/0\/(\d+)$/)?.[1];
  if (crs && !code && !crs[1].endsWith("/OGC/1.3/CRS84")) {
    throw new HttpError(502, "Systeme de coordonnees WKT non pris en charge.");
  }
  const geometry = wktToGeoJSON(crs ? value.slice(crs[0].length) : value);
  const project = coordinates => typeof coordinates[0] === "number"
    ? proj4(`EPSG:${code || "4326"}`, "EPSG:4326", coordinates)
    : coordinates.map(project);
  const transform = item => item.type === "GeometryCollection"
    ? { ...item, geometries: item.geometries.map(transform) }
    : { ...item, coordinates: project(item.coordinates) };
  return transform(geometry);
}

function combinedGeometry(geometries) {
  if (!geometries.length) return null;
  return geometries.length === 1 ? geometries[0] : { type: "GeometryCollection", geometries };
}

function areaToLiteral(area) {
  if (area === null || area === undefined) return null;
  const features = area.type === "FeatureCollection" ? area.features : [area];
  assert(Array.isArray(features) && features.length > 0 && features.length <= 100, "Zone GeoJSON vide ou invalide.");
  const polygons = [];
  let count = 0;
  for (const feature of features) {
    const geometry = feature.type === "Feature" ? feature.geometry : feature;
    assert(geometry && ["Polygon", "MultiPolygon"].includes(geometry.type), "La zone doit contenir des polygones.");
    const coordinates = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    assert(Array.isArray(coordinates) && coordinates.length > 0, "Polygone vide.");
    for (const polygon of coordinates) {
      assert(Array.isArray(polygon) && polygon.length > 0, "Polygone invalide.");
      for (const ring of polygon) {
        assert(Array.isArray(ring) && ring.length >= 4, "Anneau de polygone invalide.");
        for (const position of ring) {
          assert(Array.isArray(position) && position.length === 2 && position.every(Number.isFinite) && Math.abs(position[0]) <= 180 && Math.abs(position[1]) <= 90, "Coordonnees GeoJSON invalides.");
          count++;
          assert(count <= 10000, "Zone trop complexe.");
        }
        assert(ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1], "Anneau non ferme.");
      }
      polygons.push(polygon);
    }
  }
  const geometry = polygons.length === 1 ? { type: "Polygon", coordinates: polygons[0] } : { type: "MultiPolygon", coordinates: polygons };
  return `${JSON.stringify(geojsonToWKT(geometry))}^^<${WKT_TYPE}>`;
}

function boundary(binding, key) {
  const precision = name => binding[`tPrec${name}`]?.value?.split(/#unit|\//).pop().toLowerCase() || null;
  const calendar = binding[`timeCalendar${key}`]?.value || null;
  if (binding[`tStamp${key}`]) return { kind: "crisp", value: binding[`tStamp${key}`].value, precision: precision(key), calendar };
  const edge = suffix => binding[`tStamp${key}${suffix}`]
    ? { value: binding[`tStamp${key}${suffix}`].value, precision: precision(key + suffix), calendar } : null;
  const begin = edge("FuzzyBeg");
  const end = edge("FuzzyEnd");
  return begin || end ? { kind: "fuzzy", begin, end, precision: begin?.precision || end?.precision, calendar } : null;
}

async function runSparql(endpoint, query) {
  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      redirect: "error",
      headers: { Accept: "application/sparql-results+json", "Content-Type": "application/sparql-query" },
      body: query,
      signal: AbortSignal.timeout(30000)
    });
  } catch (error) {
    throw new HttpError(error.name === "TimeoutError" ? 504 : 502, "Endpoint SPARQL indisponible ou delai depasse.");
  }
  if (!response.ok) throw new HttpError(502, `Le endpoint SPARQL a repondu HTTP ${response.status}.`);
  let payload;
  try { payload = await response.json(); } catch { throw new HttpError(502, "Reponse SPARQL JSON invalide."); }
  if (!Array.isArray(payload?.results?.bindings)) throw new HttpError(502, "Reponse SPARQL sans resultats SELECT.");
  return payload.results.bindings;
}

function createDataService(config, execute = runSparql) {
  const run = query => execute(config.sparqlEndpoint, query);
  const graphUri = graph => uri(graph || config.defaultGraphUri, "Graphe");
  const source = graph => ({ namedGraph: graph, sparqlEndpoint: config.sparqlEndpoint, supportingDataScope: "default-dataset" });
  const labels = async graph => new Map((await run(queries.getQueryForAttributeTypes(graph, config.queryLanguage)))
    .map(binding => [binding.attrType.value, { label: binding.attrTypeLabel?.value || binding.attrType.value }]));

  return {
    async graphs() {
      const graphs = queries.parseGraphsResults(await run(queries.getQueryForGraphs(config.queryLanguage)));
      return graphs.length ? graphs : [{ id: config.defaultGraphUri, name: config.defaultGraphUri.split("/").pop() }];
    },
    async types(graph) {
      return queries.parseLandmarkTypesResults(await run(queries.getQueryForLandmarkTypes(graphUri(graph), config.queryLanguage)));
    },
    async landmarks(graph, type) {
      return queries.parseLandmarksFilteringResults(await run(queries.getQueryForLandmarksFilteringByType(graphUri(graph), uri(type, "Type"), config.queryLanguage)));
    },
    async evolution(graph, landmark) {
      graph = graphUri(graph);
      landmark = uri(landmark, "Entite");
      const [validityBindings, bindings, attrLabels] = await Promise.all([
        run(queries.getQueryValidTimeForLandmark(landmark, graph)),
        run(queries.getQueryToInitTimeline(landmark, graph)),
        labels(graph)
      ]);
      const versions = Object.create(null);
      for (const binding of bindings) versions[binding.attrVers.value] = { ...binding, values: [] };
      if (bindings.length) {
        const values = await run(queries.getQueryForAttributeVersionValues(queries.getValuesForQuery("vers", versions)));
        for (const binding of values) versions[binding.vers.value]?.values.push(binding.val);
      }
      const events = [];
      const displayVersions = Object.create(null);
      for (const [id, version] of Object.entries(versions)) {
        const temporal = suffix => ({
          crisp: { stamp: version[`tStamp${suffix}`], precision: version[`tPrec${suffix}`] },
          fuzzy: {
            beginning: { stamp: version[`tStamp${suffix}FuzzyBeg`], precision: version[`tPrec${suffix}FuzzyBeg`] },
            end: { stamp: version[`tStamp${suffix}FuzzyEnd`], precision: version[`tPrec${suffix}FuzzyEnd`] }
          }
        });
        const event = createTimelineFeature(version.attrVers, version.attrType, version.values, attrLabels, temporal("ME"), temporal("O"));
        if (event.start_date) events.push(event);
        displayVersions[id] = { geometry: combinedGeometry(version.values.filter(value => value.datatype === WKT_TYPE).map(value => geometryFromWkt(value.value))) };
      }
      const first = validityBindings[0];
      return {
        source: source(graph),
        validity: first ? { start: boundary(first, "App"), end: boundary(first, "Dis") } : null,
        timeline: { events },
        versions: displayVersions
      };
    },
    async snapshot({ graph, date, area = null } = {}) {
      graph = graphUri(graph);
      assert(validDate(date) && date >= config.dates.min && date <= config.dates.max, "Date hors intervalle ou invalide.");
      const searchArea = areaToLiteral(area);
      const timestamp = `${date}T00:00:00Z`;
      const low = new Date(timestamp);
      const high = new Date(timestamp);
      low.setUTCFullYear(low.getUTCFullYear() - config.timeDelayYears);
      high.setUTCFullYear(high.getUTCFullYear() + config.timeDelayYears);
      const [landmarks, values, attrLabels] = await Promise.all([
        run(queries.getQueryValidLandmarksFromTime(timestamp, config.timeCalendarUri, graph, low.toISOString(), high.toISOString(), config.queryLanguage)),
        run(queries.getQueryValidAttributeVersionsFromTime(timestamp, config.timeCalendarUri, graph, searchArea)),
        labels(graph)
      ]);
      const items = new Map();
      for (const binding of landmarks) {
        if (items.has(binding.lm.value)) continue;
        items.set(binding.lm.value, {
          type: "Feature", id: binding.lm.value, geometries: [], attributes: new Map(),
          properties: {
            name: `${binding.lmLabel?.value || binding.lm.value}${binding.relatumLabel ? ` (${binding.relatumLabel.value})` : ""}`,
            existsForSure: ["true", "1"].includes(String(binding.existsForSure?.value))
          }
        });
      }
      for (const binding of values) {
        const item = items.get(binding.lm.value);
        if (!item) continue;
        if (binding.versValue.datatype === WKT_TYPE) {
          item.geometries.push(geometryFromWkt(binding.versValue.value));
        } else {
          const type = binding.attrType.value;
          if (!item.attributes.has(type)) item.attributes.set(type, { type: attrLabels.get(type)?.label || type, values: [] });
          const attribute = item.attributes.get(type);
          if (!attribute.values.includes(binding.versValue.value)) attribute.values.push(binding.versValue.value);
        }
      }
      return {
        type: "FeatureCollection",
        source: source(graph),
        features: [...items.values()].filter(item => item.geometries.length).map(item => ({
          type: "Feature", id: item.id, geometry: combinedGeometry(item.geometries),
          properties: { ...item.properties, attributes: [...item.attributes.values()] }
        }))
      };
    }
  };
}

module.exports = { createDataService, runSparql, geometryFromWkt, areaToLiteral };