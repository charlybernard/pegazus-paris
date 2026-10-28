const express = require("express");
const path = require("node:path");
const { existsSync } = require("node:fs");
const { createConfigStore, HttpError } = require("./config-store");
const { createDataService } = require("./data");

function createApp({ store = createConfigStore(), execute } = {}) {
  const app = express();
  app.disable("x-powered-by");
  app.use((req, res, next) => {
    if (!["localhost", "127.0.0.1", "[::1]"].includes(req.hostname)) return next(new HttpError(403, "Hote non autorise."));
    const origin = req.get("origin");
    if (origin && origin !== `${req.protocol}://${req.get("host")}`) return next(new HttpError(403, "Origine non autorisee."));
    res.set("X-Content-Type-Options", "nosniff");
    res.set("Referrer-Policy", "strict-origin-when-cross-origin");
    next();
  });
  app.use("/api", (req, res, next) => {
    res.set("Cache-Control", "no-store");
    if (["POST", "PUT"].includes(req.method) && !req.is("application/json")) return next(new HttpError(415, "Content-Type application/json requis."));
    next();
  });
  app.use("/api", express.json({ limit: "1mb" }));
  app.get("/api/config", async (req, res) => res.json(await store.read()));
  app.get("/api/config/defaults", async (req, res) => res.json(await store.defaults()));
  app.put("/api/config", async (req, res) => res.json(await store.save(req.body)));
  app.post("/api/config/reset", async (req, res) => res.json(await store.reset()));
  app.get("/api/graphs", async (req, res) => res.json(await createDataService(await store.read(), execute).graphs()));
  app.get("/api/landmark-types", async (req, res) => res.json(await createDataService(await store.read(), execute).types(req.query.graph)));
  app.get("/api/landmarks", async (req, res) => res.json(await createDataService(await store.read(), execute).landmarks(req.query.graph, req.query.type)));
  app.get("/api/evolution", async (req, res) => res.json(await createDataService(await store.read(), execute).evolution(req.query.graph, req.query.landmark)));
  app.post("/api/snapshot", async (req, res) => res.json(await createDataService(await store.read(), execute).snapshot(req.body)));
  app.use("/api", (req, res) => res.status(404).json({ error: "Route API inconnue." }));

  const distribution = path.join(__dirname, "..", "dist");
  app.get(["/", "/index.html"], (req, res) => {
    const index = path.join(distribution, "index.html");
    if (!existsSync(index)) return res.status(503).send("Frontend not built. Run npm run build or npm run dev.");
    res.set("Cache-Control", "no-cache");
    res.sendFile(index);
  });
  app.use(express.static(distribution, { index: false, dotfiles: "deny" }));
  app.use((req, res) => res.status(404).send("Not found"));
  app.use((error, req, res, next) => {
    const status = error.status || 500;
    if (status >= 500) console.error(error.message);
    res.status(status).json({ error: status === 500 ? "Erreur interne du serveur." : error.message });
  });
  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 3000);
  const server = createApp().listen(port, "127.0.0.1", () => console.log(`PeGazUs Paris: http://localhost:${port}`));
  server.on("error", error => {
    console.error(error.code === "EADDRINUSE" ? `Port ${port} occupe. Utiliser PORT=3001 npm start.` : error.message);
    process.exitCode = 1;
  });
}

module.exports = { createApp };