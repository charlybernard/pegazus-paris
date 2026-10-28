import { defineConfig } from "vite";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const apiTarget = process.env.API_TARGET || "http://127.0.0.1:3000";

const icons = new Map(["settings", "x", "rotate-ccw", "save", "plus", "pencil", "trash-2", "check"].map(name => [
  `/${name}.svg`, readFileSync(new URL(`./node_modules/lucide-static/icons/${name}.svg`, import.meta.url))
]));

export default defineConfig({
  root: "frontend",
  publicDir: "../public",
  optimizeDeps: {
    exclude: ["leaflet-draw"]
  },
  plugins: [{
    name: "leaflet-draw-strict-compatibility",
    enforce: "pre",
    transform(code, id) {
      if (!id.split("?")[0].replaceAll("\\", "/").endsWith("/leaflet-draw/dist/leaflet.draw.js")) return;
      const signature = /readableArea:function\(([^)]*)\)\{var /;
      if (!signature.test(code)) this.error("Leaflet Draw readableArea changed; review its strict-mode compatibility fix.");
      return { code: code.replace(signature, "readableArea:function($1){var type, "), map: null };
    }
  }, {
    name: "application-icons",
    configureServer(server) {
      server.middlewares.use("/icons", (req, res, next) => {
        const source = icons.get(req.url?.split("?")[0]);
        if (!source) return next();
        res.setHeader("Content-Type", "image/svg+xml");
        res.end(source);
      });
    },
    generateBundle() {
      for (const [filename, source] of icons) {
        this.emitFile({ type: "asset", fileName: `icons${filename}`, source });
      }
    }
  }],
  server: {
    host: "127.0.0.1",
    fs: {
      allow: ["frontend", "public", "node_modules"].map(directory => fileURLToPath(new URL(`./${directory}/`, import.meta.url)))
    },
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyRequest, request) => {
            if (request.headers.origin === `http://${request.headers.host}`) {
              proxyRequest.setHeader("Origin", new URL(apiTarget).origin);
            }
          });
        }
      }
    }
  },
  build: {
    outDir: "../dist",
    emptyOutDir: true
  }
});