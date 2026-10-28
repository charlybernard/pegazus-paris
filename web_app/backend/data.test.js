const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createConfigStore } = require("./config-store");
const { createDataService, areaToLiteral, geometryFromWkt } = require("./data");

const term = value => ({ value });
const WKT = "http://www.opengis.net/ont/geosparql#wktLiteral";
const point = { value: "POINT (2.35 48.85)", datatype: WKT };
const polygon = { type: "Polygon", coordinates: [[[2, 48], [3, 48], [3, 49], [2, 49], [2, 48]]] };

test("snapshot joins landmarks, attributes and geometries and sends drawn areas to SPARQL", async () => {
  const config = await createConfigStore().defaults();
  const calls = [];
  const service = createDataService(config, async (endpoint, query) => {
    calls.push(query);
    assert.equal(endpoint, config.sparqlEndpoint);
    if (query.includes("SELECT DISTINCT ?lm ?lmLabel")) return [
      { lm: term("https://example.org/entity"), lmLabel: term("Paris"), existsForSure: term("false") },
      { lm: term("https://example.org/outside"), lmLabel: term("Outside") }
    ];
    if (query.includes("SELECT DISTINCT ?lm ?vers")) return [
      { lm: term("https://example.org/entity"), attrType: term("https://example.org/Geometry"), versValue: point },
      { lm: term("https://example.org/entity"), attrType: term("https://example.org/Name"), versValue: term("Paris") }
    ];
    return [{ attrType: term("https://example.org/Name"), attrTypeLabel: term("Nom") }];
  });
  const result = await service.snapshot({ date: "1850-01-01", area: { type: "FeatureCollection", features: [{ type: "Feature", geometry: polygon }] } });
  assert.equal(result.type, "FeatureCollection");
  assert.deepEqual(result.source, {
    namedGraph: config.defaultGraphUri, sparqlEndpoint: config.sparqlEndpoint, supportingDataScope: "default-dataset"
  });
  assert.equal(result.features.length, 1);
  assert.deepEqual(result.features[0].geometry, { type: "Point", coordinates: [2.35, 48.85] });
  assert.equal(result.features[0].properties.existsForSure, false);
  assert.deepEqual(result.features[0].properties.attributes, [{ type: "Nom", values: ["Paris"] }]);
  assert(calls.some(query => query.includes('"1850-01-01T00:00:00Z"^^xsd:dateTimeStamp')));
  assert(calls.some(query => query.includes('"1830-01-01T00:00:00.000Z"^^xsd:dateTimeStamp AS ?lowTimeStamp')));
  assert(calls.some(query => query.includes('"1870-01-01T00:00:00.000Z"^^xsd:dateTimeStamp AS ?highTimeStamp')));
  assert(calls.some(query => query.includes("POLYGON") && query.includes(`^^<${WKT}>`) && query.includes("geof:sfIntersects")));
});

test("snapshot always exposes existsForSure as a boolean", async () => {
  const rawValues = ["true", "1", true, "false", "0", false, undefined];
  const config = await createConfigStore().defaults();
  const service = createDataService(config, async (endpoint, query) => {
    if (query.includes("SELECT DISTINCT ?lm ?lmLabel")) return rawValues.map((value, index) => ({
      lm: term(`https://example.org/entity/${index}`),
      ...(value === undefined ? {} : { existsForSure: term(value) })
    }));
    if (query.includes("SELECT DISTINCT ?lm ?vers")) return rawValues.map((value, index) => ({
      lm: term(`https://example.org/entity/${index}`),
      attrType: term("https://example.org/Geometry"), versValue: point
    }));
    return [];
  });
  const result = await service.snapshot({ date: "1850-01-01" });
  assert.deepEqual(result.features.map(feature => feature.properties.existsForSure), [true, true, true, false, false, false, false]);
  assert(result.features.every(feature => typeof feature.properties.existsForSure === "boolean"));
});

test("evolution returns ready timeline, fuzzy validity and projected geometries", async () => {
  const config = await createConfigStore().defaults();
  const service = createDataService(config, async (endpoint, query) => {
    if (query.includes("LIMIT 1")) return [{ tStampAppFuzzyBeg: term("1800-01-01"), tStampAppFuzzyEnd: term("1810-01-01") }];
    if (query.includes("SELECT DISTINCT ?lm ?attrType")) return [{
      attrVers: term("https://example.org/version"), attrType: term("https://example.org/Geometry"),
      tStampME: term("1850-01-01T00:00:00Z"), tPrecME: term("http://www.w3.org/2006/time#unitYear"),
      tStampOFuzzyBeg: term("1900-01-01"), tStampOFuzzyEnd: term("1910-01-01")
    }];
    if (query.includes("SELECT DISTINCT ?vers ?val")) return [
      { vers: term("https://example.org/version"), val: point },
      { vers: term("https://example.org/version"), val: term("<script>alert(1)</script>") }
    ];
    return [];
  });
  const result = await service.evolution(null, "https://example.org/entity");
  assert.equal(result.source.namedGraph, config.defaultGraphUri);
  assert.equal(result.validity.start.kind, "fuzzy");
  assert.equal(result.timeline.events.length, 1);
  assert.equal(result.timeline.events[0].start_date.year, "1850");
  assert.equal(result.timeline.events[0].start_date.month, "");
  assert(result.timeline.events[0].text.text.includes("&lt;script&gt;"));
  assert.deepEqual(result.versions["https://example.org/version"].geometry.coordinates, [2.35, 48.85]);
  const projected = geometryFromWkt("<http://www.opengis.net/def/crs/EPSG/0/2154> POINT (651278.600083 6862856.041463)");
  assert(Math.abs(projected.coordinates[0] - 2.337) < 0.01);
  assert(Math.abs(projected.coordinates[1] - 48.864) < 0.01);
});

test("snapshot and evolution report the requested graph rather than the configured default", async () => {
  const config = await createConfigStore().defaults();
  const graph = "https://example.org/selected-graph";
  const calls = [];
  const service = createDataService(config, async (endpoint, query) => { calls.push(query); return []; });
  for (const result of [await service.snapshot({ graph, date: "1850-01-01" }), await service.evolution(graph, "https://example.org/entity")]) {
    assert.deepEqual(result.source, { namedGraph: graph, sparqlEndpoint: config.sparqlEndpoint, supportingDataScope: "default-dataset" });
  }
  assert.equal(calls.filter(query => query.includes(`<${graph}> AS ?g`)).length, 4);
});

test("multiple polygons, invalid areas and SPARQL injection", async () => {
  assert(areaToLiteral({ type: "FeatureCollection", features: [polygon, polygon] }).includes("MULTIPOLYGON"));
  assert.throws(() => areaToLiteral({ type: "Point", coordinates: [2, 48] }), { status: 400 });
  assert.throws(() => areaToLiteral({ type: "Polygon", coordinates: [[[2, 48], [3, 48], [3, 49], [4, 50]]] }), { status: 400 });
  const service = createDataService(await createConfigStore().defaults(), () => { throw new Error("must not execute"); });
  await assert.rejects(service.evolution('https://example.org/> } UNION {', "https://example.org/entity"), { status: 400 });
  await assert.rejects(service.snapshot({ date: "1850-01-01\" }" }), { status: 400 });
});