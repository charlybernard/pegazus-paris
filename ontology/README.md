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
For full documentation (detailed definitions, examples, and modeling rules), see the [`documentation`](./documentation) folder.