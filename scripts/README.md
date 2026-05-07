This folder is organized into several Python modules to construct, manage, and evaluate a knowledge graph. The code is structured into four main folders:
* `evaluation`;
* `graph_construction`;
* `resource_management`;
* `utils`.

---

## `scripts/evaluation`

Scripts for evaluating and analyzing the knowledge graph, especially addresses and street numbers:

* `add_labels_for_addresses_table.py` – add labels to the addresses table.
* `addr_matching.py` – match addresses across different sources.
* `create_addresses_table.py` – create a table of addresses from raw data.
* `create_addr_links.py` – create links between addresses and other entities.
* `create_links_table.py` – create a table of links extracted from the graph.
* `create_streetnumber_factoids.py` – create factoids for street numbers.
* `data_from_sparql_queries.py` – extract evaluation data using SPARQL queries.
* `evaluate_streetnumber_versions.py` – evaluate different versions of street numbers.
* `evaluate_streetnumber_fragmentary.py` – evaluate fragmentary street number data.
* `evaluation_aux.py` – auxiliary functions for evaluation scripts.
* `extract_addr_links.py` – extract address links from the knowledge graph.
* `get_statistics.py` – generate statistics about the knowledge graph (number of entities, links, etc.).

---

## `scripts/graph_construction`

Modules for knowledge graph construction:

* `attribute_version_comparisons.py` – compare different versions of attributes.
* `create_factoids_descriptions.py` – create descriptive factoids for entities.
* `description_initialisation.py` – initialize descriptions of entities.
* `evolution_construction.py` – construct the evolution of landmark attributes.
* `evolution_construction_without_sparql.py` – construct the evolution of landmark attributes by avoiding some SPARQL queries (to avoid problems of Java heap space).
* `fact_graph_construction.py` – build fact graphs from factoids.
* `factoids_creation.py` – create factoids from different sources.
* `graphdb.py` – interact with GraphDB (queries, named graphs, etc.).
* `graphrdf.py` – utilities to work with RDFLib.
* `multi_sources_processing.py` – centralize processing of multiple sources to build the knowledge graph.
* `namespaces.py` – initialize RDF namespaces used in the knowledge graph.
* `resource_rooting.py` – link resources from factoids graphs to facts graphs.
* `resource_rooting_without_sparql.py` – link resources from factoids graphs to facts graphs by avoiding some SPARQL queries (to avoid problems of Java heap space).
* `resource_transfert.py` – transfer information from one resource to another.

---

## `scripts/resource_management`

Modules for resource initialization and external data sources:

* `factoids_validation.py` – validate factoids named graphs to ensure they meet certain criteria before being used in the knowledge graph.
* `resource_initialisation.py` – initialize resources using RDFLib.
* `states_events_json.py` – manage states and events stored in JSON format.
* `wikidata.py` – access and query Wikidata via SPARQL.

---

## `scripts/utils`

General-purpose utility modules:

* `configs.py` – manage project configurations and settings.
* `db_utils.py` – helper functions to manage database interactions.
* `file_management.py` – read and write files (CSV, JSON, TTL, etc.).
* `geom_processing.py` – functions to process WKT geometries.
* `get_configs.py` – load and manage project configurations.
* `str_processing.py` – manipulate string labels in the knowledge graph.
* `time_processing.py` – compare and process temporal data (instants, intervals).

