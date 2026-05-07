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

The project documentation is divided into two complementary folders `documentation` and `samod`:

### [`documentation`](./documentation)
It contains the ontology documentation. This documentation provides a complete description of the ontology.

### [`samod`](./samod)
It contains the conceptual and methodological documentation produced following the [SAMOD methodology](https://essepuntato.it/papers/samod-owled2016.html) (*Simplified Agile Methodology for Ontology Development*).  

This folder documents the ontology engineering process and explains how the ontology was designed.
Ontology documentation in the `samod` folder is divided into several parts corresponding to the main modelets:
* addresses ;
* sources ;
* temporal_evolution.

Each modelet documentation contains 3 or 4 files:
* `{modelet_name}_scenario.md`: a natural-language argument describing the sub-problem to address ;
* `{modelet_name}_glossary.md`: a glossary defining the main concepts involved ;
* `{modelet_name}_competency_questions.md`: a set of informal competency questions representing the expected queries the knowledge base should answer ;
* `{modelet_name}_sparql_queries.md`: a SPARQL translation of the competency questions.