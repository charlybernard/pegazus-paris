// ---------------------------- Settings to get the endpoint ----------------------------

// Configuration file for the web application if you want to use a graph in GraphDB,
// you can set the graphDBURI and graphName variables,
// and the finalEndpointURI variable will be automatically set to the correct value for querying the graph.
// If you want to use a different SPARQL endpoint, you can set the finalEndpointURI variable directly.

// const graphDBURI = "http://localhost:7200" ;
// // const graphName = "paris" ;
// const graphName = "fbg_saint_antoine" ;

// Other case : if you want to use a different SPARQL endpoint, you can set the finalEndpointURI variable directly, for example : `endpointURI = "https://data.geohistoricaldata.org/query"`

const endpointURI = "https://data.geohistoricaldata.org/query"

// ----------------------------- Settings to get the graph URI ----------------------------

const defaultFinalGraphURI = "https://www.w3id.org/PeGazUs/pegazus-paris" ; // default graph URI to use if no graph is selected in the dropdown menu

// ---------------------------- Other settings ----------------------------

const graphLang = "fr" ; // language of the graph, used to retrieve labels in the right language
const systemLang = "en" ; // language of the system, used to display labels in the right language (if different from graphLang)
const gregorianCalendarURI = "http://www.wikidata.org/entity/Q1985727" ;

