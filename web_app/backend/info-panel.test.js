const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");

test("entity panel translates empty, hovered and selected states without replacing RDF values", async () => {
  const { i18nConfig } = await import("../frontend/i18n.js");
  const app = readFileSync(require.resolve("../frontend/app.js"), "utf8");
  const functions = app.slice(app.indexOf("function updateInfoPanel("), app.indexOf("// 3. FONCTIONS DE TRAITEMENT SPATIAL"));
  const container = { innerHTML: "" };
  const context = {
    i18nConfig,
    currentLang: "fr",
    infoPanelControl: { getContainer: () => container },
    infoPanelData: null,
    selectedFeatureId: null,
    escapeHtml: value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;")
  };
  runInNewContext(functions, context);
  for (const language of ["fr", "en", "es"]) {
    context.currentLang = language;
    context.updateInfoPanel(null, null);
    assert(container.innerHTML.includes(i18nConfig[language].infoPanelHint));
  }
  const properties = { attributes: [{ type: "Nom", values: ["Valeur RDF", "<script>"] }] };
  context.updateInfoPanel(properties, "https://example.org/entity");
  for (const language of ["fr", "en", "es"]) {
    context.currentLang = language;
    context.selectedFeatureId = null;
    context.renderInfoPanel();
    const dict = i18nConfig[language];
    for (const key of ["infoPanelUnnamed", "infoPanelAttributes", "infoPanelType", "infoPanelValues"]) {
      assert(container.innerHTML.includes(dict[key]));
    }
    assert(!container.innerHTML.includes(dict.infoPanelSelected));
    context.selectedFeatureId = "https://example.org/entity";
    context.renderInfoPanel();
    assert(container.innerHTML.includes(dict.infoPanelSelected));
    assert(container.innerHTML.includes("Nom"));
    assert(container.innerHTML.includes("Valeur RDF"));
    assert(container.innerHTML.includes("&lt;script&gt;"));
    assert(!container.innerHTML.includes("<script>"));
  }
  context.updateInfoPanel(null, null);
  assert(container.innerHTML.includes(i18nConfig.es.infoPanelHint));
  assert(!container.innerHTML.includes("Valeur RDF"));
  assert.match(app, /function updateLanguageTexts\(\)[\s\S]*?renderInfoPanel\(\);/);
});
