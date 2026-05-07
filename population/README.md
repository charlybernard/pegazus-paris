# Multi-source Ontology Population

This document describes the process of populating the ontology using various geo-historical data sources.

## Sources
The following sources are used for this population:
* **Current Administrative & Crowdsourced Data:**
    * City of Paris street nomenclature (current and named thoroughfares);
    * OpenStreetMap (OSM);
    * Wikidata;
    * Base Adresse Nationale (BAN).
* **Event-based Sources:**
    * Evolution events (renaming, deletions, creations) manually structured in JSON from Wikipedia pages.
* **Historical Atlases and Plans of Paris:**
    * Plan Delagrive (1728)
    * Verniquet Atlas (1784–1791)
    * General Cadastre of Paris (1807)
    * Vasserot Atlas (1810–1836)
    * Jacoubet Atlas (1827–1839)
    * Andriveau Plan (1849)
    * Municipal Parcel Map of Paris (1871)
    * Municipal Atlas of Paris (1888)

| Source                               | House Numbers | Thoroughfares | Districts / Areas 
| :----------------------------------- | :-----------: | :-----------: | :---------------: 
| **City of Paris nomenclature**       |               |       ✅      |         ❓          
| **OpenStreetMap (OSM)**              |       ✅      |       ✅      |         ✅        
| **Wikidata**                         |               |       ✅      |         ✅        
| **Base Adresse Nationale (BAN)**     |       ✅      |       ❓      |         ❓        
| **Wikipedia (JSON events)**          |       ❓      |       ❓      |         ❓         
| **Plan Delagrive (1728)**            |               |       ✅      |                   
| **Verniquet Atlas (1784–1791)**      |               |       ✅      |                   
| **General Cadastre of Paris (1807)** |       ✅      |       ❓      |                   
| **Vasserot Atlas (1810–1836)**       |       ✅      |       ✅      |                   
| **Jacoubet Atlas (1827–1839)**       |       ✅      |       ✅      |                   
| **Napoleonic cadastre (1847)**       |       ✅      |       ✅      |                   
| **Andriveau Plan (1849)**            |       ✅      |       ✅      |                   
| **Municipal Parcel Map (1871)**      |               |       ✅      |                   
| **Municipal Atlas (1888)**           |       ✅      |       ✅      |                   

❓ Semantic data only (names and attributes are available, but no geographical information for these entities)

> **Note on Geometries:** For historical sources, data is distinguished by its geometric nature: **thoroughfares** (linear or polygonal paths) and **house numbers** (address points).

## `data` Folder
This folder contains the files used as input for the population process. The file naming convention distinguishes data types using the suffixes `_th_` (thoroughfares) and `_addr_` (addresses/numbers).

The following variables in the notebook refer to these files:

### Current Reference and Event Files
* `vpta_csv_file_name`: File containing the names of the rights-of-way of the current Parisian thoroughfares;
* `vptc_csv_file_name`: File of names of obsolete City of Paris thoroughfares;
* `osm_csv_file_name`: Thoroughfare data extracted from OpenStreetMap;
* `osm_hn_csv_file_name`: House number data from OpenStreetMap;
* `bpa_csv_file_name`: File from the BAN;
* `wdp_land_csv_file_name`: Geographical entities from Wikidata (thoroughfares, districts, cities);
* `wdp_loc_csv_file_name`: Relations between geographical entities (thoroughfare/area links) from Wikidata;
* `events_json_file_name`: JSON file describing historical evolution events (extracted from Wikipedia).

### Historical GeoJSON Files
For historical sources, when a source contains both streets and addresses, two separate files are used:

* ** Plan Delagrive (1728):**
    * `del_1728_th_geojson_file_name`: streets.
* **Verniquet Atlas (1784–1791):**
    * `ve_1790_th_geojson_file_name`: streets.
* **General Cadastre of Paris (1807)**
    * `cad_1807_addr_geojson_file_name`: house numbers.
* **Vasserot Atlas (1810–1836):**
    * `va_1810_th_geojson_file_name`: streets.
    * `va_1810_addr_geojson_file_name`: house numbers.
* **Jacoubet Atlas (1827–1839):**
    * `ja_1836_th_geojson_file`: streets.
    * `ja_1836_addr_geojson_file`: house numbers.
* **Andriveau Plan (1849):**
    * `an_1849_th_geojson_file_name`: streets.
* **Municipal Parcel Map (1871):**
    * `pm_1871_th_geojson_file_name`: streets.
* **Municipal Atlas (1888):**
    * `am_1888_th_geojson_file_name`: streets.
    * `am_1888_addr_geojson_file_name`: house numbers.

How to obtain some of theses files is shown below.

### Base Adresse Nationale

Data from [Base Adresse Nationale (BAN)](https://adresse.data.gouv.fr/base-adresse-nationale) are available [here](https://adresse.data.gouv.fr/data/ban/adresses/latest/csv). For this project, downloaded data are related to Paris (`adresses-75.csv.gz`). File name must correspond to `bpa_csv_file_name` in the notebook.

### OpenStreetMap

Files are the results of two queries from [OSM planet SPARQL endpoint](https://qlever.cs.uni-freiburg.de/osm-planet). See *Bast, H., Brosi, P., Kalmbach, J., & Lehmann, A. (2021, November). An efficient RDF converter and SPARQL endpoint for the complete OpenStreetMap data. In Proceedings of the 29th International Conference on Advances in Geographic Information Systems (pp. 536-539)*.

Extracted data from OpenStreetMap are :
* house numbers (_house numbers_) : their value (a number and optionally a complement), their geometry, the thoroughfare or the district they belong to ;
* thoroughfares : their name
* districts : their name and INSEE code.

1. Extract Paris addresses
In the query interface, there are two queries to launch.
* Query 1 :
```
PREFIX osmrel: <https://www.openstreetmap.org/relation/>
PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX osmrdf: <https://osm2rdf.cs.uni-freiburg.de/rdf/member#>
PREFIX osm: <https://www.openstreetmap.org/>
PREFIX ogc: <http://www.opengis.net/rdf#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?houseNumberId ?streetId ?streetName ?arrdtId ?arrdtName ?arrdtInsee
 WHERE {
  ?selectedArea osmkey:wikidata "Q90"; ogc:sfContains ?houseNumberId.
  ?houseNumberId osmkey:addr:housenumber ?housenumberName.
  ?arrdtId ogc:sfContains ?houseNumberId; osmkey:name ?arrdtName; osmkey:ref:INSEE ?arrdtInsee; osmkey:boundary "administrative"; osmkey:admin_level "9"^^xsd:int .
  ?streetId osmkey:type "associatedStreet"; osmrel:member ?member; osmkey:name ?streetName.
  ?member osmrel:member_role "house"; osmrel:member_id ?houseNumberId.
}
```

* Query 2 :
```
PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX ogc: <http://www.opengis.net/rdf#>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>

SELECT DISTINCT ?houseNumberId ?houseNumberLabel ?houseNumberGeomWKT
 WHERE {
  ?selectedArea osmkey:wikidata "Q90"; ogc:sfContains ?houseNumberId.
  ?houseNumberId osmkey:addr:housenumber ?houseNumberLabel; geo:hasGeometry ?houseNumberGeom.
  ?houseNumberGeom geo:asWKT ?houseNumberGeomWKT.
}
```

The queries select all the house numbers in Paris, but it is possible to change the extraction zone by modifying the `osmkey:wikidata ‘Q90’` condition. For example, you can replace it with `osmkey:wikidata ‘Q2378493’` to restrict it to the Maison Blanche district of Paris. Note that only building numbers belonging to an `associatedStreet` type relationship and having the `house` role in this relationship are selected. For each query, results are exported to `csv` files: `osm_adresses.csv` for query 1 and `osm_hn_adresses.csv` for query 2. There are two queries instead of one because, endpoint is not able to return any result (due to limited performances).

2. Export the result in two `csv` files and insert them in the folder defined by the `tmp_folder` variable. The file names must correspond to those defined in the notebook:
* for query 1, the name is linked to the `osm_csv_file_name` variable;
* for query 2, the name is linked to the `osm_hn_csv_file_name` variable.

### Wikidata
Via Wikidata, the extracted data are:
* geographical entities:
    * Paris thoroughfares (current and old ones) ;
    * areas linked to Paris:
      * districts of Paris ;
      * arrondissements (those before and after 1860) of Paris;
      * communes (past and present) of the former department of Seine;
* the relationships between these geographical entities.

Three files in CSV format must be stored in the `data` folder, the names of which are linked to variables in the notebook:
* `wdp_land_csv_file_name`: for of geographical entities (thoroughfares, districts, cities) ;
* `wdp_loc_csv_file_name`: file of geographical entity relations (between thoroughfares and areas).

Obtaining these files is straightforward. Simply run the `get_data_from_wikidata()` function defined in the notebook.

### Ville de Paris
The data for the city of Paris is made up of two datasets:
* [dénominations des emprises des voies actuelles](https://opendata.paris.fr/explore/dataset/denominations-emprises-voies-actuelles)
* [dénominations caduques des voies](https://opendata.paris.fr/explore/dataset/denominations-des-voies-caduques)

The information used here is the names of the thoroughfares (and their geographical extent for current lanes) with their period of validity (if known).

The two datasets must be downloaded in CSV format into the `data` folder and their names must correspond to the names given by the variables `vpta_csv_file_name` (for current lanes) and `vptc_csv_file_name` for obsolete lanes.

### Geojson files
#### GeoHistoricalData
You can get some of geojson files on [GeoHistoricalData](https://geohistoricaldata.org/) website. Click on `Download` then `Paris street networks` to download data. Extract files you need and convert shapefiles to geojson format. Then, put them in the `data` folder with the names corresponding to those defined in the notebook. Available sources are:
* Plan Delagrive (1728)
* Verniquet Atlas (1784–1791)
* Andriveau Plan (1849)
* Municipal Atlas of Paris (1888)

#### Fabrique Numérique du passé
Streets and house numbers from the Vasserot Atlas (1810–1836) are available in [Fabrique Numérique du passé](https://www.fabriquenumeriquedupasse.fr/) website :
* Streets: [Vasserot Atlas (1810–1836) - Streets](https://www.fabriquenumeriquedupasse.fr/explore/dataset/alpage-voies-vasserot/)
* House numbers: [Vasserot Atlas (1810–1836) - House numbers](https://www.fabriquenumeriquedupasse.fr/explore/dataset/alpage-adresses-vasserot/)

Export the data in geojson format and put them in the `data` folder with the names corresponding to those defined in the notebook.

## Launch the process
Once the files are in the `data` folder, the process can be started by running `create_graph.ipynb` file.

⚠️ However, you need to ensure that GraphDB is installed and running during the process. [GraphDB](https://graphdb.ontotext.com/) is used to store and work on knowledge graphs. A variable is associated with the software: `graphdb_url` which is the URL of the web application.

### Step by step process
* Download GraphDB from https://www.ontotext.com/products/graphdb/download/
* Download the repository, for instance:
```
git clone git@github.com:charlybernard/pegazus-paris.git
cd pegazus-paris
```
* Create an environment with conda for instance:
```
conda create -n p3-12 python=3.12
conda activate p3-12
```
* Install the dependencies. For conda for instance:
```
conda install jupyter
conda install pyproj
conda install conda-forge::geojson
conda install conda-forge::rdflib
conda install conda-forge::sparqlwrapper
conda install unidecode
```
* Run the notebook:
```
cd population
jupyter notebook
```
* In the jupyter interface:
    * uncomment relevant lines in "Creating factoids in directories" (if it is not done)
    * run all cells (it might take a while)
