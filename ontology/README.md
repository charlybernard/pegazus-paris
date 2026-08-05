# README.md

The PeGazUs ontology is identified by `https://w3id.org/PeGazUs#` URI.

## Overview

This folder contains the **PeGazUs ontology** (`ontology.ttl`), designed to represent the evolution of geographic entities over time.

## Main modeling scope

The ontology describes:

- **Landmarks** and their **types** (`Landmark`, `LandmarkType`)
- **Attributes**, their types and their **versions** (`Attribute`, `AttributeType`, `AttributeVersion`)
- **Relations between landmarks** (`LandmarkRelation`, `LandmarkRelationType`)
- **Changes and events** (`Change`, `LandmarkChange`, `LandmarkRelationChange`, `AttributeChange`, `Event`)
- **Temporal entities** (precise and uncertain time: `CrispTimeInstant`, `FuzzyTimeInstant`, intervals)
- **Indirect spatial references** through addresses (`Address`, `AddressSegment`)

## Reused standards

PeGazUs reuses common RDF vocabularies, including:

- **OWL / RDF / RDFS**
- **SKOS**
- **OWL-Time**
- **PROV-O**

## Ontology metadata

- Namespace IRI: `https://w3id.org/PeGazUs#`
- Version info in the file: `Version 0.2 - 2026-05-07`
- License: `CC BY-NC-SA 4.0`

## Detailed documentation

The project documentation is divided into two complementary folders: [`documentation`](./documentation) and [`samod`](./samod).

### [`documentation`](./documentation)

This folder contains the ontology documentation.  
It provides a complete description of the ontology, including its concepts, properties, and modeling choices.

### [`samod`](./samod)

This folder contains the conceptual and methodological documentation produced following the [SAMOD methodology](https://essepuntato.it/papers/samod-owled2016.html) (*Simplified Agile Methodology for Ontology Development*).

The `samod` folder is divided into two main parts:

* [`modelets`](./samod/modelets): contains the ontology engineering documentation for each modelet. It describes the design process and the methodological steps followed for the development of the ontology.
* [`data`](./samod/data): contains example datasets illustrating how the ontology can be populated for each developed modelet.

#### [`modelets`](./samod/modelets)

This folder documents the ontology engineering process and explains how each modelet was designed.

Each modelet has its own documentation folder:

* addresses;
* sources;
* temporal_evolution.

Each modelet documentation contains 3 or 4 files:

* `{modelet_name}_scenario.md`: a natural-language argument describing the sub-problem addressed by the modelet;
* `{modelet_name}_glossary.md`: a glossary defining the main concepts involved;
* `{modelet_name}_competency_questions.md`: a set of informal competency questions representing the expected queries the knowledge base should answer;
* `{modelet_name}_sparql_queries.md`: a SPARQL translation of the competency questions.

#### [`data`](./samod/data)

This folder contains example data for each developed modelet.

These datasets demonstrate how the ontology can be populated and provide concrete instances illustrating the concepts and relationships defined in each modelet.

#### [`publication`](./samod/publication)

An English translation and updated version of the article:

> Bernard, Charly, Abadie, Nathalie, Perret, Julien, et al.  
> *Création d'un référentiel géo-historique d'adresses à partir de sources multiples.*  
> GAST - Gestion et l’Analyse de données Spatiales et Temporelles, 2024.

is provided as:

[`PeGazUs_ontology_article_updated_2026_en.pdf`](./publication/samod/PeGazUs_ontology_article_updated_2026_en.pdf)

The PDF presents the PeGazUs ontology, its modeling approach, and its application for building a geo-historical address reference from heterogeneous and multi-temporal sources.

The LaTeX source files used to generate this document are also provided:

[`latex`](./publication/samod/latex)

They allow the document to be reproduced, modified, and extended.