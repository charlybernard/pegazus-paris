const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createServer } = require("node:http");
const { once } = require("node:events");
const { mkdtemp, rm } = require("node:fs/promises");
const { tmpdir } = require("node:os");
const path = require("node:path");
const { createApp } = require("./server");
const { createConfigStore } = require("./config-store");

test("HTTP API: config lifecycle, SPARQL transport, JSON contracts and private files", async () => {
  const directory = await mkdtemp(path.join(tmpdir(), "pegazus-api-"));
  const term = value => ({ value });
  const graph = "https://example.org/graph";
  const entity = "https://example.org/entity";
  const version = "https://example.org/version";
  const type = "https://example.org/type";
  const requests = [];
  let upstreamFailure = false;
  const upstream = createServer(async (req, res) => {
    let query = "";
    for await (const chunk of req) query += chunk;
    requests.push(query);
    assert.equal(req.method, "POST");
    assert.equal(req.headers["content-type"], "application/sparql-query");
    let bindings = [];
    if (query.includes("SELECT ?graph")) bindings = [{ graph: term(graph), label: term("Paris") }];
    else if (query.includes("SELECT DISTINCT ?lmType")) bindings = [{ lmType: term(type), lmTypeLabel: term("Rue") }];
    else if (query.includes("SELECT ?lm ?lmLabel")) bindings = [{ lm: term(entity), lmLabel: term("Rue de Paris") }];
    else if (query.includes("LIMIT 1")) bindings = [{ tStampApp: term("1800-01-01"), tPrecApp: term("http://www.w3.org/2006/time#unitYear") }];
    else if (query.includes("SELECT DISTINCT ?lm ?attrType")) bindings = [{ attrVers: term(version), attrType: term(type), tStampME: term("1850-01-01"), tPrecME: term("http://www.w3.org/2006/time#unitYear") }];
    else if (query.includes("SELECT DISTINCT ?vers ?val")) bindings = [{ vers: term(version), val: { value: "POINT (2.35 48.85)", datatype: "http://www.opengis.net/ont/geosparql#wktLiteral" } }];
    else if (query.includes("SELECT DISTINCT ?lm ?lmLabel")) bindings = [{ lm: term(entity), lmLabel: term("Rue de Paris"), existsForSure: term("true") }];
    else if (query.includes("SELECT DISTINCT ?lm ?vers")) bindings = [{ lm: term(entity), attrType: term(type), versValue: { value: "POINT (2.35 48.85)", datatype: "http://www.opengis.net/ont/geosparql#wktLiteral" } }];
    res.writeHead(upstreamFailure ? 500 : 200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ results: { bindings } }));
  });
  upstream.listen(0, "127.0.0.1");
  await once(upstream, "listening");
  const store = createConfigStore(path.join(directory, "config.json"));
  const app = createApp({ store }).listen(0, "127.0.0.1");
  await once(app, "listening");
  const base = `http://127.0.0.1:${app.address().port}`;
  const json = async (route, options = {}) => {
    const response = await fetch(base + route, { headers: { "Content-Type": "application/json" }, ...options });
    return { status: response.status, body: await response.json() };
  };
  try {
    const defaults = (await json("/api/config/defaults")).body;
    assert.deepEqual((await json("/api/config")).body, defaults);
    const modified = { ...defaults, sparqlEndpoint: `http://127.0.0.1:${upstream.address().port}/sparql`, defaultGraphUri: graph };
    assert.equal((await json("/api/config", { method: "PUT", body: JSON.stringify(modified) })).status, 200);
    assert.deepEqual(await createConfigStore(path.join(directory, "config.json")).read(), modified);
    const invalid = { ...modified, map: { ...modified.map, zoom: 99 } };
    assert.equal((await json("/api/config", { method: "PUT", body: JSON.stringify(invalid) })).status, 400);
    assert.deepEqual((await json("/api/config")).body, modified);
    assert.deepEqual((await json("/api/graphs")).body, [{ id: graph, name: "Paris" }]);
    assert.equal((await json(`/api/landmark-types?graph=${encodeURIComponent(graph)}`)).body[0].label, "Rue");
    assert.equal((await json(`/api/landmarks?${new URLSearchParams({ graph, type })}`)).body[0].uri, entity);
    const evolution = await json(`/api/evolution?${new URLSearchParams({ graph, landmark: entity })}`);
    assert.equal(evolution.status, 200);
    assert.equal(evolution.body.timeline.events[0].unique_id, version);
    assert.equal(evolution.body.validity.start.kind, "crisp");
    assert.equal(evolution.body.source.namedGraph, graph);
    const snapshot = await json("/api/snapshot", { method: "POST", body: JSON.stringify({ graph, date: "1850-01-01" }) });
    assert.equal(snapshot.status, 200);
    assert.equal(snapshot.body.features[0].geometry.type, "Point");
    assert.equal(snapshot.body.features[0].properties.existsForSure, true);
    assert.equal(snapshot.body.source.namedGraph, graph);
    assert.equal(snapshot.body.source.sparqlEndpoint, modified.sparqlEndpoint);
    assert.equal(snapshot.body.source.supportingDataScope, "default-dataset");
    assert(requests.length >= 10);
    const crossOrigin = await fetch(base + "/api/config/reset", { method: "POST", headers: { Origin: "https://elsewhere.test", "Content-Type": "application/json" }, body: "{}" });
    assert.equal(crossOrigin.status, 403);
    assert.equal((await fetch(base + "/api/config/reset", { method: "POST" })).status, 415);
    for (const route of ["/backend/config.json", "/backend/config.defaults.json", "/backend/queries.js", "/package.json", "/frontend/app.js", "/node_modules/leaflet/package.json", "/libs/leaflet/leaflet.js"]) {
      assert.equal((await fetch(base + route)).status, 404);
    }
    const home = await fetch(base + "/");
    assert.equal(home.status, 200);
    const html = await home.text();
    assert.match(html, /rel="icon"[^>]+href="\/icon\/pegazus_icon\.svg"/);
    const module = html.match(/<script[^>]+src="([^"]+)"/);
    assert(module, "production HTML must reference a bundled module");
    assert(module[1].startsWith("/assets/"));
    const script = await fetch(base + module[1]);
    assert.equal(script.status, 200);
    assert.match(script.headers.get("content-type"), /javascript/);
    for (const match of html.matchAll(/href="(\/assets\/[^"]+\.css)"/g)) {
      const stylesheet = await fetch(base + match[1]);
      assert.equal(stylesheet.status, 200);
      const css = await stylesheet.text();
      for (const asset of css.matchAll(/url\(["']?(\/assets\/[^)"']+)/g)) {
        assert.equal((await fetch(base + asset[1].split("#")[0])).status, 200);
      }
    }
    assert.equal((await fetch(base + "/icons/settings.svg")).status, 200);
    assert.equal((await fetch(base + "/icons/info.svg")).status, 200);
    assert.equal((await fetch(base + "/symbols/green_dot.svg")).status, 200);
    assert.equal((await fetch(base + "/icon/github_icon.svg")).status, 200);
    const favicon = await fetch(base + "/icon/pegazus_icon.svg");
    assert.equal(favicon.status, 200);
    assert.match(favicon.headers.get("content-type"), /image\/svg\+xml/);
    upstreamFailure = true;
    assert.equal((await json("/api/graphs")).status, 502);
    assert.deepEqual((await json("/api/config/reset", { method: "POST", body: "{}" })).body, defaults);
    assert.deepEqual((await json("/api/config/defaults")).body, defaults);
  } finally {
    app.closeAllConnections();
    upstream.closeAllConnections();
    await Promise.all([new Promise(resolve => app.close(resolve)), new Promise(resolve => upstream.close(resolve))]);
    await rm(directory, { recursive: true, force: true });
  }
});