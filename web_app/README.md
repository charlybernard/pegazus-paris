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
- **Landmark Evolution** mode lets you choose a type and then an entity to view its validity and history on the timeline.
- The language menu changes the interface language. The language of queried data is configured separately in settings.

For details about the architecture, development, API, and tests, see [README.development.md](README.development.md).
