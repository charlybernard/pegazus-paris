const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");

test("snapshot opacity updates the mask live and is reused without accumulating masks", () => {
  const app = readFileSync(require.resolve("../frontend/app.js"), "utf8");
  const listeners = {};
  const output = {};
  const map = { removeLayer: layer => removed.push(layer) };
  const removed = [];
  const layers = [];
  const context = {
    snapshotMask: null,
    snapshotMaskOpacity: 0.45,
    document: {
      getElementById: id => id === "snapshot-mask-opacity-value" ? output : {
        addEventListener: (event, listener) => { listeners[id] = listener; }
      }
    },
    L: {
      polygon: (coordinates, options) => {
        const layer = {
          options,
          addTo: target => assert.equal(target, map),
          setStyle: style => Object.assign(options, style)
        };
        layers.push(layer);
        return layer;
      }
    }
  };
  const start = app.indexOf('  document.getElementById("snapshot-mask-opacity").addEventListener');
  const end = app.indexOf('  document.getElementById("btn-source-info")', start);
  runInNewContext(app.slice(start, end), context);
  const maskStart = app.indexOf("function applySelectedAreaMask(");
  const maskEnd = app.indexOf("// 4. CRÉATION DU CALQUE GEOJSON", maskStart);
  runInNewContext(app.slice(maskStart, maskEnd), context);
  const area = { type: "Polygon", coordinates: [[[2, 48], [3, 48], [3, 49], [2, 48]]] };
  context.applySelectedAreaMask(map, area);
  assert.equal(layers[0].options.fillOpacity, 0.45);
  for (const value of ["0", "73", "100"]) {
    listeners["snapshot-mask-opacity"]({ target: { value } });
    assert.equal(layers[0].options.fillOpacity, Number(value) / 100);
    assert.equal(output.textContent, `${value} %`);
  }
  context.applySelectedAreaMask(map, area);
  assert.equal(layers.length, 2);
  assert.equal(removed[0], layers[0]);
  assert.equal(layers[1].options.fillOpacity, 1);
  context.applySelectedAreaMask(map, null);
  assert.equal(context.snapshotMask, null);
  assert.equal(removed[1], layers[1]);
  listeners["snapshot-mask-opacity"]({ target: { value: "30" } });
  context.applySelectedAreaMask(map, area);
  assert.equal(layers[2].options.fillOpacity, 0.3);
});
