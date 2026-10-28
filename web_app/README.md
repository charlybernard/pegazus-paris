# PeGazUs webapp

PeGazUs web application lets you explore historical data from an RDF graph on a map and timeline.

## Requirements

- Node.js 22.12 or later and npm.
- A SPARQL endpoint accessible from the machine running the application.
- To use GraphDB locally, a running instance with a repository containing the PeGazUs data.

## Install and Run

From the project root, install the dependencies and start the application:

```sh
npm ci
npm start
```

Then open <http://localhost:3000>. `npm start` builds the frontend and starts the application server. Do not open `frontend/index.html` directly or use Live Server: the application requires its API.

If port 3000 is already in use, choose another port:

```sh
PORT=3001 npm start
```

## Connect to a SPARQL Endpoint

Use the settings button (gear icon) to change the SPARQL endpoint and default graph. Save the settings after entering the values; the application reloads with the updated configuration.

For a local GraphDB instance, the repository endpoint follows this format:

```text
{graphdb_uri}/repositories/{repository_name}
```

For example, for GraphDB running locally with a repository named `fbg_saint_antoine`:

```text
SPARQL endpoint: http://localhost:7200/repositories/fbg_saint_antoine
Default graph: https://w3id.org/PeGazUs/id/Graph/facts
```

The endpoint identifies the GraphDB repository; the default graph is the URI of the RDF graph queried within that repository. Make sure the repository is running, the data has been loaded, and the PeGazUs server can reach the endpoint.

The server uses the saved configuration for every browser connected to it. Settings are stored in `backend/config.json`; restoring the defaults replaces this saved configuration.

## Explore the Data

- **Snapshot** mode displays entities on the map for a selected date. Draw an area to limit the spatial search.
  The map options menu (sliders icon, top right) groups basemaps and outside-area opacity under separate headings. The opacity slider adjusts the dark mask immediately from 0% (transparent) to 100% (opaque), starting at 45%. Its value is kept for subsequent snapshots until the page is reloaded.
- **Landmark Evolution** mode lets you choose a type and then an entity to view its validity and history on the timeline.
  Its map uses the same styled map options menu for basemap selection, with section headings matching the body text size. Outside-area opacity is specific to Snapshot mode.
- The language menu changes the interface language. The language of queried data is configured separately in settings.
  The map entity details panel updates immediately, including when an entity is selected; attribute labels and values from RDF keep the configured data language.
  The panel expands to fit its content up to 560 pixels (or the available viewport width), keeping attribute types on one line and wrapping long values when necessary.
- The discreet information button next to settings shows the selected named graph URI, the SPARQL endpoint, and the graph reported by the last result in the current mode, even when only one graph is available. Entity, attribute and change selection uses that named graph; supporting dates, calendars, type labels and some values use the endpoint's default dataset, which may span other graphs.
- Snapshot certainty accepts both HTTP and HTTPS Wikidata identifiers for the configured calendar. Other calendar identifiers remain exact matches. The default Gregorian calendar identifier is `http://www.wikidata.org/entity/Q1985727`, matching the generated RDF. Missing temporal bounds remain uncertain; the configured time margin is unchanged.

For details about the architecture, development, API, and tests, see [README.development.md](README.development.md).
