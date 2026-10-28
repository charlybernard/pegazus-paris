const { test } = require("node:test");
const assert = require("node:assert/strict");
const { getQueryValidLandmarksFromTime, getQueryValidAttributeVersionsFromTime } = require("./queries");
const { runSparql } = require("./data");

const timestamp = "1850-01-01T00:00:00Z";
const calendar = "http://www.wikidata.org/entity/Q1985727";
const graph = "https://example.org/graph";

test("snapshot calendar filters accept Wikidata HTTP/HTTPS aliases without duplicating outer solutions", () => {
  for (const build of [getQueryValidLandmarksFromTime, getQueryValidAttributeVersionsFromTime]) {
    const http = build(timestamp, calendar, graph);
    assert.equal(build(timestamp, calendar.replace("http:", "https:"), graph), http);
    const filters = [...http.matchAll(/FILTER\(\?\w+Calendar IN \(([^)]+)\)\)/g)];
    assert.equal(filters.length, 6);
    assert(filters.every(([, identifiers]) => identifiers === `<${calendar}>, <${calendar.replace("http:", "https:")}>`));
    assert(!http.includes("VALUES ?timeCalendar"));
    const custom = build(timestamp, "https://example.org/calendar", graph);
    assert(!custom.includes("wikidata.org/entity/Q1985727"));
    assert(custom.includes("IN (<https://example.org/calendar>)"));
  }
});

test("SPARQL calendar filters match both Wikidata schemes and reject other calendars", {
  skip: !process.env.SPARQL_TEST_ENDPOINT
}, async () => {
  for (const build of [getQueryValidLandmarksFromTime, getQueryValidAttributeVersionsFromTime]) {
    const query = build(timestamp, calendar.replace("http:", "https:"), graph);
    for (const [filter, variable] of query.matchAll(/FILTER\(\?(\w+Calendar) IN \([^)]+\)\)/g)) {
      const fixture = `SELECT ?${variable} WHERE {
        VALUES ?${variable} {
          <${calendar}> <${calendar.replace("http:", "https:")}>
          <http://www.wikidata.org/entity/Q1985786> <https://example.org/calendar>
        }
        ${filter}
      }`;
      const results = await runSparql(process.env.SPARQL_TEST_ENDPOINT, fixture);
      assert.deepEqual(results.map(row => row[variable].value).sort(), [calendar, calendar.replace("http:", "https:")].sort());
    }
  }
});

test("landmark certainty consumes low and high bounds instead of assuming missing dates are certain", () => {
  const query = getQueryValidLandmarksFromTime(timestamp, calendar, graph, "1830-01-01T00:00:00Z", "1870-01-01T00:00:00Z");
  assert(query.includes('BIND("1830-01-01T00:00:00Z"^^xsd:dateTimeStamp AS ?lowTimeStamp)'));
  assert(query.includes('BIND("1870-01-01T00:00:00Z"^^xsd:dateTimeStamp AS ?highTimeStamp)'));
  assert(query.includes("?disFuzzyBegStamp >= ?lowTimeStamp AS ?disTimeAfterExists"));
  assert(query.includes("?appFuzzyEndStamp <= ?highTimeStamp AS ?appTimeBeforeExists"));
  const certainty = query.slice(query.lastIndexOf("BIND("));
  assert(certainty.includes("COALESCE(?appTimeBeforeExists, ?appFuzzyEndExists, false)"));
  assert(certainty.includes("COALESCE(?disTimeAfterExists, ?disFuzzyBegExists, false)"));
  assert(certainty.includes("&&"));
  const withoutMargin = getQueryValidLandmarksFromTime(timestamp, calendar, graph);
  assert(!withoutMargin.includes("AS ?lowTimeStamp"));
  assert(!withoutMargin.includes("AS ?highTimeStamp"));
});

test("SPARQL engine evaluates certainty at the tolerance boundaries", {
  skip: !process.env.SPARQL_TEST_ENDPOINT
}, async () => {
  const date = value => `"${value}-01-01T00:00:00Z"^^xsd:dateTimeStamp`;
  const rows = [
    `("within_margin" UNDEF UNDEF ${date("1860")} ${date("1840")})`,
    `("at_margin" UNDEF UNDEF ${date("1870")} ${date("1830")})`,
    `("appearance_outside" UNDEF UNDEF ${date("1871")} ${date("1840")})`,
    `("disappearance_outside" UNDEF UNDEF ${date("1840")} ${date("1829")})`,
    `("missing_appearance" UNDEF UNDEF UNDEF ${date("1900")})`,
    `("missing_disappearance" UNDEF UNDEF ${date("1800")} UNDEF)`,
    `("crisp" ${date("1800")} ${date("1900")} UNDEF UNDEF)`
  ];
  for (const margin of [false, true]) {
    const query = getQueryValidLandmarksFromTime(timestamp, calendar, graph,
      margin ? "1830-01-01T00:00:00Z" : null, margin ? "1870-01-01T00:00:00Z" : null);
    const bindings = [...query.matchAll(/BIND\([\s\S]*?\s+AS\s+\?\w+\s*\)/g)].map(match => match[0]);
    const fixture = `PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
      SELECT ?case ?existsForSure WHERE {
        VALUES (?case ?appCrispStamp ?disCrispStamp ?appFuzzyEndStamp ?disFuzzyBegStamp) {
          ${rows.join("\n")}
        }
        ${bindings.join("\n")}
      }`;
    const results = await runSparql(process.env.SPARQL_TEST_ENDPOINT, fixture);
    assert.deepEqual(Object.fromEntries(results.map(row => [row.case.value, row.existsForSure.value])), {
      within_margin: String(margin), at_margin: String(margin),
      appearance_outside: "false", disappearance_outside: "false",
      missing_appearance: "false", missing_disappearance: "false", crisp: "true"
    });
  }
});