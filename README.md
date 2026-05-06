# PeGazUs : PErpetual GAZeteer of approach-address UtteranceS

This repository contains the documentation of the PeGazUs (PErpetual GAZeteer of approach-address UtteranceS) ontology and knowledge graph construction method.

## Structure of the repository
📂  
├── 📄 [`README.md`](./README.md)   
├── 📄 [`index.html`](./index.html)   
├── 📂 [`data`](./data/)   
├── 📂 [`evaluation`](./evaluation/)   
├── 📂 [`ontology`](./ontology/)   
│   ├── 📄 [`ontology.ttl`](./ontology/ontology.ttl)   
│   └── 📂 [`documentation`](./ontology/documentation/)  
│   │   ├── 📂 [`addresses`](./ontology/documentation/addresses/)   
│   │   ├── 📂 [`sources`](./ontology/documentation/sources/)   
│   │   └── 📂 [`temporal_evolution`](./ontology/documentation/temporal_evolution/)   
├── 📂 [`population`](./population/)   
├── 📂 [`scripts`](./scripts/)   
├── 📂 [`statistics`](./statistics/)   
├── 📄 [`LICENCE.md`](./LICENCE.md)  
└── 📄 [`README.md`](./README.md)  

### `data` folder

This folder stores files used to build knowledge graph. It contains csv and geojson files which describe addresses and streets from different sources at different times (RDF resources are built during process.

⚠️ To get more information about their content, please read their [readme](data/README.md).

## `evaluation` folder

This folder contains Jupyter notebook to populate knowledge graph from data in `data` folder and gets a evaluation a the population method:
* `create_graph_evaluation.ipynb` – creates a knowledge graph and runs evaluation procedures.

⚠️ To get more information about their content, please read their [readme](evaluation/README.md).

### `ontology` folder
`ontology.ttl` describes the ontology: it is the core part of the ontology and describe landmarks and addresses.

[Ontology documentation](ontology/documentation) is divided into as many parts as there are modelets:
* [`addresses`](ontology/documentation/addresses) ;
* [`sources`](ontology/documentation/sources) ;
* [`temporal_evolution`](ontology/documentation/temporal_evolution).

Each modelet documentation has 3 or 4 files:
* `{modelet_name}_scenario.md`: the natural-language argument describing the sub-problem to be addressed ;
* `{modelet_name}_glossary.md`: glossary which defines the main terms involved ;
* `{modelet_name}_competency_questions.md`: set of informal competence questions (in natural language) which represent the questions to be answered by the knowledge base ;
* `{modelet_name}_sparql_queries.md`: it translates informal competence questions into SPARQL queries.

## `population` folder

This folder contains Jupyter notebook to populate knowledge graph from data in `data` folder :
* `create_graph.ipynb` – creates the knowledge graph from data sources.

⚠️ To get more information about their content, please read their [readme](population/README.md).

### `scripts` folder
This folder contains code to build knowledge graphs.

⚠️ To get more information about their content, please read their [readme](scripts/README.md).

## `statistics` folder

This folder contains Jupyter notebook to get statistics about the graph built after population
* `stats_about_graph.ipynb` – create statistics files about the graph.

⚠️ To get more information about their content, please read their [readme](statistics/README.md).

### `web_app` folder
This folder contains code for the web application to see the evolution of the landmarks.

⚠️ To get more information about their content, please read their [readme](web_app/README.md).