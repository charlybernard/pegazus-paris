# Multi-Source Ontology Population --- Evaluation README

## Overview

This evaluation assesses the robustness and correctness of the PeGazUs
ontology population method when integrating heterogeneous and
fragmentary data sources.

The goal is to:
* Compare reconstructed address evolutions against a reference evolution derived from geometry changes.
* Measure the impact of adding coherent fragmentary data (states and events).
* Quantify consistency and temporal correctness using dedicated metrics.

------------------------------------------------------------------------

## Configuration

Before running the evaluation, ensure the following `user_settings` are
correctly defined and consistent:

``` json
{
  "data_folder_name": "../data/fbg_saint_antoine",
  "repository_name": "fbg_saint_antoine_test",
  "ont_file_name": "ontology.ttl",
  "str_graphdb_url": "http://localhost:7200"
}
```

------------------------------------------------------------------------

## Evaluation Workflow

### 1. Ontology Population

Populate the PeGazUs ontology using dataset D.

* Input: set of datasets $D$
* Output: graph $G$
* Location: GraphDB repository

------------------------------------------------------------------------

### 2. Reference Evolution Construction

A baseline evolution of addresses is computed using the evolution of
house number geometries.

------------------------------------------------------------------------

### 3. Generation of Fragmentary Data

Generate additional coherent fragmentary datasets:

* $d_st$: spatio-temporal states\
* $d_ev$: events describing changes

------------------------------------------------------------------------

### 4. Population with Extended Data

* $D + d_{st}$ → $G_{st}$
* $D + d_{st} + d_{ev}$ → $G_{st+ev}$

------------------------------------------------------------------------

### 5. Metrics Computation

#### First Evaluation

* Compare: evolutions of adresses in $G$ with evolutions of same adresses built with a reference algorithm
* Metric: Number of addresses with matching evolution

------------------------------------------------------------------------

#### Second Evaluation

We compare the reconstructed evolutions across the pairs ($G$, $G'$) with $G' \in \{G_{st}, G_{st+ev}\}$.

The following metrics are computed:

---

### **Preserved**

Measures whether the **structure of the evolution** is preserved.
For each house number, the **number of changes** and the **number of versions** must be identical in both graphs.

---

### **Strict**

Measures **exact temporal equivalence**.

* Each change must correspond to:
  - The **same timestamp**, or  
  - The **same temporal interval**

This metric requires **full equality** of temporal information.

---

### **Consistent**

Measures **temporal compatibility** between evolutions.

* For each change in \(G\) occurring at time \(t\),  
  its corresponding change in the derived graph occurs at time \(t'\)

The following constraint must hold:

* \(t'\) must be **included in** \(t\)

This inclusion is defined depending on the nature of temporal representations:

* **Crisp vs. crisp**:  
  \(t' = t\)

* **Crisp vs. fuzzy** (where \(t = [t_{begin}, t_{end}]\)):  
  \(t' \in t\), i.e. \(t_{begin} \leq t' \leq t_{end}\)

* **Fuzzy vs. fuzzy**:  
  \(t' \subseteq t\)

where:
* \(t = [t_{begin}, t_{end}]\)
* \(t' = [t'_{begin}, t'_{end}]\)
* and:
  \(t_{begin} \leq t'_{begin} \leq t'_{end} \leq t_{end}\)

---

### Interpretation

* **Preserved** → structural stability of the evolution  
* **Strict** → exact reconstruction  
* **Consistent** → temporally valid reconstruction under uncertainty  

------------------------------------------------------------------------

## Output

* Number of correctly reconstructed evolutions
* Metrics for ($G$, $G_{st}$) and ($G$, $G_{st+ev}$)
* Scores: Preserved, Strict, Consistent

------------------------------------------------------------------------

## Pre-Evaluation Checklist

* GraphDB is running
* Repository exists
* Dataset is complete
* Ontology file is valid
* No temporal inconsistencies

------------------------------------------------------------------------

## Execution

1.  Populate ontology from $D$
2.  Compute reference evolutions
3.  Generate $d_{st}$ and $d_{ev}$
4.  Populate extended graphs
5.  Compute metrics
