//////////////////////////////// Actions on the page //////////////////////////////////

const finalEndpointURI =
  typeof endpointURI !== "undefined"
    ? endpointURI
    : (typeof graphDBURI !== "undefined" &&
       typeof graphName !== "undefined")
        ? getGraphDBRepositoryURI(graphDBURI, graphName)
        : undefined;

console.log("finalEndpointURI : ", finalEndpointURI) ;

// Object of LeafletObjects class which contains all markers and dots*
const lo = new LeafletObjects(L);

setSystemLang(uiConfig, systemLang); // set the system language in the UI configuration, which will be used to display labels in the right language
setGraphLang(uiConfig, graphLang); // set the graph language in the UI configuration, which will be used to retrieve labels in the right language from the graphgetQueryToInitTimeline
createMainHTML(L, finalEndpointURI, defaultFinalGraphURI, uiConfig);
const contentDiv = document.getElementById(uiConfig.divIds.content);
const selectDiv = document.getElementById(uiConfig.divIds.selection);
const inputRadioDiv = document.getElementById(uiConfig.divIds.radioInput);
const graphSelectionDiv = document.getElementById(uiConfig.divIds.graphSelection);

var namedGraphURI = null;

// Initial display of the map with the first graph in the dropdown menu
inputRadioDiv.addEventListener("change", function () {
    namedGraphURI = graphSelectionDiv.value;
    handleRadioChange(L, uiConfig, finalEndpointURI, namedGraphURI);
  });

graphSelectionDiv.addEventListener('change', function(){
    namedGraphURI = graphSelectionDiv.value;
});