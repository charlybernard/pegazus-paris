const { test } = require("node:test");
const assert = require("node:assert/strict");
const { mkdtemp, readFile, rm } = require("node:fs/promises");
const { tmpdir } = require("node:os");
const path = require("node:path");
const { createConfigStore, validateConfig } = require("./config-store");

test("configuration persisted, restored, and defaults unchanged", async () => {
  const directory = await mkdtemp(path.join(tmpdir(), "pegazus-config-"));
  try {
    const filename = path.join(directory, "config.json");
    const store = createConfigStore(filename);
    const original = await readFile(path.join(__dirname, "config.defaults.json"), "utf8");
    const defaults = await store.read();
    const modified = structuredClone(defaults);
    modified.map.center = [45.76, 4.84];
    modified.map.zoom = 10;
    modified.sparqlEndpoint = "http://localhost:7200/repositories/other";
    await store.save(modified);
    assert.deepEqual(await createConfigStore(filename).read(), modified);
    await store.reset();
    assert.deepEqual(await store.read(), defaults);
    assert.equal(await readFile(path.join(__dirname, "config.defaults.json"), "utf8"), original);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("reject invalid config without changing persisted values", async () => {
  const defaults = await createConfigStore().defaults();
  for (const mutate of [
    config => { config.map.center[0] = 91; },
    config => { config.map.zoom = -1; },
    config => { config.dates.min = "2026-02-30"; },
    config => { config.dates.default = "1700-01-01"; },
    config => { config.sparqlEndpoint = "file:///etc/passwd"; },
    config => { config.queryLanguage = 'fr" ) }'; }
  ]) {
    const config = structuredClone(defaults);
    mutate(config);
    assert.throws(() => validateConfig(config), { status: 400 });
  }
});