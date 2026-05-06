## Graph Statistics Extraction

This section provides a set of utilities to compute descriptive statistics on the generated knowledge graphs. These statistics help to analyze the structure, temporal richness, and content distribution of the populated ontology.

All results are exported as `.csv` files in the specified `results_folder`.

---

### 🔢 Extracted Statistics

#### 1. Number of Landmarks per Final Graph

- **File**: `landmarks_per_final_graph.csv`
- **Description**:  
  Counts the total number of landmarks in each final graph.

---

#### 2. Number of Landmarks per Type per Final Graph

- **File**: `landmarks_per_type_per_final_graph.csv`
- **Description**:  
  Provides a breakdown of landmarks by type (e.g., house numbers, streets, etc.) for each final graph.

---

#### 3. Number of Geometry Versions per Landmark

- **File**: `nb_geometry_versions_per_landmark.csv`
- **Description**:  
  Counts how many geometry versions are associated with each landmark.  
  This reflects the **temporal granularity** of spatial evolution.

- **Parameter**:
  - `limit`: maximum number of landmarks processed (default: 1000)

---

#### 4. Geometry Valid Time per Landmark

- **File**: `geometry_valid_time_per_landmark.csv`
- **Description**:  
  Extracts the temporal validity intervals of geometries associated with each landmark.  
  Useful for analyzing **temporal coverage** and **consistency**.

- **Parameter**:
  - `limit`: maximum number of landmarks processed (default: 1000)

---

#### 5. Number of Addresses by Year

- **File**: `nb_addresses_by_year.csv`
- **Description**:  
  Counts the number of addresses present in the graph for a set of given years.

- **Parameters**:
  - `list_of_years`: range from 1795 to 2025 (step = 10 years)

---

#### 6. Number of Triples per Graph

- **File**: `get_triples_per_graph.csv`
- **Description**:  
  Computes the total number of RDF triples for each graph.  
  This gives an estimate of the **graph size** and **data volume**.

---

### 📁 Output

Each function:
- Queries the GraphDB repository
- Computes the requested statistic
- Saves the result as a `.csv` file
- Prints the output file path for traceability

---

### 💡 Purpose

These statistics are useful for:

- Understanding the **structure and scale** of the graphs
- Evaluating **data completeness**
- Analyzing **temporal dynamics**
- Supporting the interpretation of evaluation metrics