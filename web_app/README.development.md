# PeGazUs — Development

This document describes the architecture and commands useful to people developing or maintaining the application. For installation and usage, see [README.md](README.md).

## Requirements and Commands

The project requires Node.js 22.12 or later and npm. Install dependencies from the repository root:

```sh
npm ci
```

To build and run the application locally:

```sh
npm start
```

This command builds `dist/` with Vite, then starts Express on port 3000. You can use another port with `PORT=3001 npm start`.

For development with Vite hot reload, start the API and frontend in two terminals:

```sh
npm run dev:api
npm run dev
```

Open the address printed by Vite, usually <http://127.0.0.1:5173>. Vite proxies `/api` requests to `http://127.0.0.1:3000`. If the API uses another port, set the target when starting Vite:

```sh
API_TARGET=http://127.0.0.1:3001 npm run dev
```

Other commands:

```sh
npm run build  # build the frontend into dist/
npm run check  # check syntax for selected JavaScript modules
npm test       # build the frontend, then run the Node tests
```

Tests use a mock SPARQL endpoint. An optional test can also verify the SPARQL certainty expressions against a live endpoint without modifying the repository:

```sh
SPARQL_TEST_ENDPOINT=https://data.geohistoricaldata.org/query npm test
```

## Application Structure

```text
frontend/                 Browser UI and application logic
  index.html              HTML entry point and interface structure
  app.js                  Initialization, interactions, map, and timeline
  settings.js             API calls and settings interface
  i18n.js                 Interface translations
  config.js               Links displayed in the header
  leaflet-objects.js      Map entity objects and styles
  map-styles.js           Applies styles to Leaflet layers
  vendor.js               Browser dependency imports
  style.css               Interface styles
backend/                  Server, API, and SPARQL data access
  server.js               Express server and /api routes
  config-store.js         Configuration loading, validation, and persistence
  config.defaults.json    Reference values; never written by the application
  config.json             Persisted active configuration; ignored by Git
  queries.js              SPARQL query construction
  data.js                 Fetches and transforms query results
  time.js                 Prepares timeline data
public/                   Static icons and symbols used by the application
dist/                     Vite-built frontend; generated output
```

The browser handles the interface and visualizations. The server queries the triplestore and transforms SPARQL results into map data. XYZ/WMS basemaps are loaded by the browser.

Dependencies and their versions are defined in `package.json` and `package-lock.json`. Generated files in `dist/` and dependencies in `node_modules/` are not tracked by Git.

## Configuration

The settings interface can change the SPARQL endpoint, default graph, map, XYZ/WMS layers, date range, interface and data languages, result limit, and time-related settings.

- `backend/config.defaults.json` contains the reference values and is never modified by the application.
- `backend/config.json` contains the active settings shared by browsers using the same server. It is created when settings are first saved or defaults are restored, and is excluded from version control.
- If there is no active configuration file, the server uses the reference values. An invalid active file causes an error instead of being silently replaced.
- Restoring defaults copies the reference values to the active file after confirmation.
- `frontend/config.js` contains the header links. Changes to this file require a production rebuild and are applied immediately during development.

The application is restricted to the local machine (`127.0.0.1`) and rejects other origins and hosts. Configuration is not a secrets store: do not put passwords in it. Before exposing the application on a network, add authentication, restrict access to configuration, and limit which SPARQL destinations the server can reach.

## JSON API

| Method | Route | Result |
| --- | --- | --- |
| GET | `/api/config` | Active configuration |
| GET | `/api/config/defaults` | Default values |
| PUT | `/api/config` | Validates and saves a complete configuration |
| POST | `/api/config/reset` | Restores defaults (body `{}`) |
| GET | `/api/graphs` | List of graphs as `{ id, name }` |
| GET | `/api/landmark-types?graph=...` | List of types as `{ id, label }` |
| GET | `/api/landmarks?graph=...&type=...` | List of entities as `{ uri, label }` |
| GET | `/api/evolution?graph=...&landmark=...` | Validity, timeline, and versions |
| POST | `/api/snapshot` | GeoJSON FeatureCollection |

URL parameters must be encoded. Write and snapshot requests require `Content-Type: application/json`. The server does not accept arbitrary SPARQL queries.

Snapshot and evolution responses include `source: { namedGraph, sparqlEndpoint, supportingDataScope: "default-dataset" }`. `namedGraph` is the validated graph actually passed to the selection queries (the requested graph, or the configured fallback). This metadata does not claim that all reads are graph-scoped: temporal details, type dictionaries and evolution version values are read outside `GRAPH`, using the endpoint's default dataset semantics. The frontend information dialog distinguishes the currently selected graph from the graph returned by the last result in each mode.

Snapshot calendar filters accept both `http` and `https` forms of a Wikidata entity URI within each temporal optional pattern, without creating an extra unmatched calendar solution. This preserves existing saved HTTPS configurations while matching the HTTP identifiers emitted by graph construction. Other calendar namespaces are not rewritten.

Errors use JSON objects `{ "error": "..." }`. The API uses status 400 for invalid input, 403 for a forbidden origin, 415 for an unsupported content type, 502 for an unavailable endpoint or invalid response, and 504 after waiting 30 seconds for the endpoint.

## Frontend Dependencies

Leaflet Draw requires a global `L`. `vendor.js` exposes this compatibility hook before loading the plugin. Vite also applies a targeted transform to Leaflet Draw 1.0.4 to declare a missing local variable in `readableArea`. It works in development and production without modifying `node_modules`, and fails explicitly if the upstream function changes.

TimelineJS is imported as an ES module with its CSS, local icon fonts, and English, French, and Spanish language files. The Lucide icons used by the application are emitted from the npm dependency by `vite.config.mjs`.