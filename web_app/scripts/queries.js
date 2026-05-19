const prefixes = {
    xsd: "http://www.w3.org/2001/XMLSchema#",
    skos: "http://www.w3.org/2004/02/skos/core#",
    rdfs: "http://www.w3.org/2000/01/rdf-schema#",
    wd: "http://www.wikidata.org/entity/",
    peg: "https://w3id.org/PeGazUs#",
    ctype: "https://w3id.org/PeGazUs/id/codes/ChangeType/",
    lrtype: "https://w3id.org/PeGazUs/id/codes/LandmarkRelationType/",
    atype: "https://w3id.org/PeGazUs/id/codes/AttributeType/",
    ltype: "https://w3id.org/PeGazUs/id/codes/LandmarkType/",
    geo: "http://www.opengis.net/ont/geosparql#",
    geof: "http://www.opengis.net/def/function/geosparql/",
    geor: "http://www.opengis.net/def/rule/geosparql/",
    geos: "http://www.opengis.net/def/srs/geosparql/",
    time: "http://www.w3.org/2006/time#",
    prov: "http://www.w3.org/ns/prov#",
    foaf: "http://xmlns.com/foaf/0.1/",
    dcterms: "http://purl.org/dc/terms/"
};

// function runSparqlQuery(endpoint, query){
//   return $.ajax({
//     url: endpoint,
//     Accept: "application/sparql-results+json",
//     contentType:"application/sparql-results+json",
//     dataType: "json",
//     data: { query }
//   }).then(res => res.results.bindings);
// }

function runSparqlQuery(endpoint, query){
  return $.ajax({
    url: endpoint,
    method: "POST",
    data: query,
    contentType: "application/sparql-query",
    dataType: "json",
    headers: {
      "Accept": "application/sparql-results+json"
    }
  })
  .then(res => res.results.bindings)

  .catch(err => {
    console.error("SPARQL request failed:", err);

    // Diagnose possible causes based on error status
    if (err.status === 0) {
      console.error("➡️ Probable CORS issue (blocked by browser)");
    } else if (err.status === 403) {
      console.error("➡️ Refused request (auth / security / endpoint)");
    }

    throw err;
  });
}

function getPrefixesForQuery(prefixes){
    var prefixesForQuery = "";
    for (p in prefixes){
        prefixesForQuery += `PREFIX ${p}: <${prefixes[p]}>\n` ;
    }
    return prefixesForQuery ;
}

function getValuesForQuery(variable, values){
    var strValues = `VALUES ?${variable} {`
    for (uri in values){
      strValues += "<" + uri + "> " ;
    }
    strValues += "}" ;
    return strValues ;
  }

function getQueryForGraphs(lang = "fr"){
    var query = getPrefixesForQuery(prefixes) + `
        SELECT ?graph ?label WHERE {
            ?graph a peg:FinalGraph .

            OPTIONAL {
                ?graph rdfs:label ?label
                FILTER(lang(?label) = "${lang}")
            }
        }
    `;
    return query ;
  }
  
// function getQueryForLandmarks(namedGraphURI, lang = "fr"){
//     var query = getPrefixesForQuery(prefixes) + `
//     SELECT ?lm ?lmLabel ?lmType ?lmTypeLabel ?relatumLabel
//     WHERE {
//         ?lm rdfs:label ?lmLabel .
//         FILTER(LANG(?lmLabel) IN ("${lang}", ""))
//         {
//             SELECT DISTINCT ?lm ?lmType WHERE {
//                 BIND(<` + namedGraphURI + `> AS ?g)
//                 GRAPH ?g { ?lm a peg:Landmark . }
//                 ?lm peg:isLandmarkType ?lmType .
//             }
//         }
//         OPTIONAL {
//             ?lmType skos:prefLabel ?lmTypeLabel .
//             FILTER(LANG(?lmTypeLabel) IN ("${lang}", ""))
//         }
//         OPTIONAL {
//             ?lr a ?lrClass ; peg:isLandmarkRelationType lrtype:Belongs ; peg:locatum ?lm ; peg:relatum [rdfs:label ?relatumLabel] .
//             ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
//             FILTER(LANG(?relatumLabel) IN ("${lang}", ""))
//         }
//     }
//         ORDER BY ?lmTypeLabel ?relatumLabel ?lmLabel
// ` ;

//     return query;
// }


function getQueryForAttributeTypes(namedGraphURI, lang = "fr"){
    var query = getPrefixesForQuery(prefixes) + `
    SELECT DISTINCT ?attrType ?attrTypeLabel
    WHERE {
        ?attrType a peg:AttributeType ; skos:prefLabel ?attrTypeLabel .
        FILTER(LANG(?attrTypeLabel) = "${lang}")
    }
    `;

    return query;
}

function getQueryForLandmarkTypes(namedGraphURI, lang = "fr"){
    var query = getPrefixesForQuery(prefixes) + `
    SELECT DISTINCT ?lmType ?lmTypeLabel
    WHERE {
        ?lmType a peg:LandmarkType ; skos:prefLabel ?lmTypeLabel .
        FILTER(LANG(?lmTypeLabel) = "${lang}")
    }
    `;
    return query;
}

function getQueryForLandmarks(namedGraphURI, lang = "fr"){
    var query = getPrefixesForQuery(prefixes) + `
    SELECT DISTINCT ?lm ?lmLabel ?lmType ?relatumLabel
    WHERE {
        GRAPH <${namedGraphURI}> {
            ?lm a peg:Landmark ; peg:isLandmarkType ?lmType ; rdfs:label ?lmLabel .
        }
        FILTER(LANG(?lmLabel) IN ("${lang}", ""))

        OPTIONAL {
            ?lr a ?lrClass ; peg:isLandmarkRelationType lrtype:Belongs ; peg:locatum ?lm ; peg:relatum ?relatum .
            ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
            ?relatum rdfs:label ?relatumLabel .
            FILTER(LANG(?relatumLabel) IN ("${lang}", ""))
        }
    }
    `;

    return query;
}

function getQueryValidTimeForLandmark(landmarkURI, namedGraphURI){
  var query = getPrefixesForQuery(prefixes) + `
  SELECT DISTINCT ?lm
  # Apparition
  ?tStampApp ?tPrecApp
  ?tStampAppFuzzyBeg ?tPrecAppFuzzyBeg
  ?tStampAppFuzzyEnd ?tPrecAppFuzzyEnd
  # Disparition
  ?tStampDis ?tPrecDis
  ?tStampDisFuzzyBeg ?tPrecDisFuzzyBeg
  ?tStampDisFuzzyEnd ?tPrecDisFuzzyEnd

  WHERE {
    BIND(<${namedGraphURI}> AS ?g)
    BIND(<${landmarkURI}> AS ?lm)

    ?changeApp peg:isChangeType ctype:LandmarkAppearance ; peg:appliedTo ?lm ; peg:dependsOn ?evApp .
    ?changeDis peg:isChangeType ctype:LandmarkDisappearance ; peg:appliedTo ?lm ; peg:dependsOn ?evDis .

    ?evApp peg:hasTime ?timeApp .
    OPTIONAL { 
      ?timeApp a peg:CrispTimeInstant ; peg:timeStamp ?tStampApp ; peg:timePrecision ?tPrecApp .
    }
    OPTIONAL {
      ?timeApp a peg:FuzzyTimeInstant .
      OPTIONAL { ?timeApp peg:hasFuzzyBeginning [peg:timeStamp ?tStampAppFuzzyBeg ; peg:timePrecision ?tPrecAppFuzzyBeg] }
      OPTIONAL { ?timeApp peg:hasFuzzyEnd [peg:timeStamp ?tStampAppFuzzyEnd ; peg:timePrecision ?tPrecAppFuzzyEnd] }
    }

    ?evDis peg:hasTime ?timeDis .
    OPTIONAL { 
      ?timeDis a peg:CrispTimeInstant ; peg:timeStamp ?tStampDis ; peg:timePrecision ?tPrecDis .
    }
    OPTIONAL {
      ?timeDis a peg:FuzzyTimeInstant .
      OPTIONAL { ?timeDis peg:hasFuzzyBeginning [peg:timeStamp ?tStampDisFuzzyBeg ; peg:timePrecision ?tPrecDisFuzzyBeg] }
      OPTIONAL { ?timeDis peg:hasFuzzyEnd [peg:timeStamp ?tStampDisFuzzyEnd ; peg:timePrecision ?tPrecDisFuzzyEnd] }
    }
  }
  LIMIT 1
  `
  return query;
}

function getQueryToInitTimeline(landmarkURI, namedGraphURI){
    var query = getPrefixesForQuery(prefixes) + `
  
  SELECT DISTINCT ?lm ?attrType ?attrVers ?cgME ?cgO
  # Bornes pour makesEffective (ME)
  ?tStampME ?tPrecME
  ?tStampMEFuzzyBeg ?tPrecMEFuzzyBeg
  ?tStampMEFuzzyEnd ?tPrecMEFuzzyEnd
  # Bornes pour outdates (O)
  ?tStampO ?tPrecO
  ?tStampOFuzzyBeg ?tPrecOFuzzyBeg
  ?tStampOFuzzyEnd ?tPrecOFuzzyEnd

  WHERE {
      BIND(<${namedGraphURI}> AS ?g)
      BIND(<${landmarkURI}> AS ?lm)
      
      ?lm a peg:Landmark ; peg:hasAttribute [peg:isAttributeType ?attrType ; peg:hasAttributeVersion ?attrVers] .
      
      ?cgME peg:makesEffective ?attrVers ; peg:dependsOn ?evME .
      ?cgO peg:outdates ?attrVers ; peg:dependsOn ?evO .

      ?evME peg:hasTime ?timeME .
      OPTIONAL { 
        ?timeME a peg:CrispTimeInstant ; peg:timeStamp ?tStampME ; peg:timePrecision ?tPrecME .
      }
      OPTIONAL {
        ?timeME a peg:FuzzyTimeInstant .
        OPTIONAL { ?timeME peg:hasFuzzyBeginning [peg:timeStamp ?tStampMEFuzzyBeg ; peg:timePrecision ?tPrecMEFuzzyBeg] }
        OPTIONAL { ?timeME peg:hasFuzzyEnd [peg:timeStamp ?tStampMEFuzzyEnd ; peg:timePrecision ?tPrecMEFuzzyEnd] }
      }

      ?evO peg:hasTime ?timeO .
      OPTIONAL { 
        ?timeO a peg:CrispTimeInstant ; peg:timeStamp ?tStampO ; peg:timePrecision ?tPrecO .
      }
      OPTIONAL {
        ?timeO a peg:FuzzyTimeInstant .
        OPTIONAL { ?timeO peg:hasFuzzyBeginning [peg:timeStamp ?tStampOFuzzyBeg ; peg:timePrecision ?tPrecOFuzzyBeg] }
        OPTIONAL { ?timeO peg:hasFuzzyEnd [peg:timeStamp ?tStampOFuzzyEnd ; peg:timePrecision ?tPrecOFuzzyEnd] }
      }
  }
  ORDER BY ?tStampME ?tStampMEFuzzyBeg
    `
  
    return query ;
}

function getValidLandmarksFromTime(timeStamp, timeCalendarURI, namedGraphURI, lowTimeStamp=null, highTimeStamp=null, lang = "fr"){
    
    var lowTimeStampFilter = ``;
    var highTimeStampFilter = ``;
    if (lowTimeStamp){
        // Utilisation du début du flou de disparition pour la borne basse
        lowTimeStampFilter = `BIND("${lowTimeStamp}"^^xsd:dateTimeStamp AS ?lowTimeStamp)
            BIND(?disFuzzyBegStamp >= ?lowTimeStamp AS ?disTimeAfterExists)`;
    }
    if (highTimeStamp){
        // Utilisation de la fin du flou d'apparition pour la borne haute
        highTimeStampFilter = `BIND("${highTimeStamp}"^^xsd:dateTimeStamp AS ?highTimeStamp)
            BIND(?appFuzzyEndStamp <= ?highTimeStamp AS ?appTimeBeforeExists)`;
    }

    var query = getPrefixesForQuery(prefixes) + `
    SELECT DISTINCT ?lm ?lmLabel ?relatumLabel ?existsForSure WHERE {
        BIND(<${namedGraphURI}> AS ?g)
        BIND("${timeStamp}"^^xsd:dateTimeStamp AS ?timeStamp)
        BIND(<${timeCalendarURI}> AS ?timeCalendar)
  
        GRAPH ?g {
            ?lm a peg:Landmark ; rdfs:label ?lmLabel .
            OPTIONAL {
                ?lr a ?lrClass ; peg:isLandmarkRelationType lrtype:Belongs ; peg:locatum ?lm ; peg:relatum [rdfs:label ?relatumLabel] .
                ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
                FILTER(LANG(?relatumLabel) IN ("${lang}", ""))
            }
            ?appCg peg:isChangeType ctype:LandmarkAppearance ; peg:appliedTo ?lm ; peg:dependsOn ?appEv .
            ?disCg peg:isChangeType ctype:LandmarkDisappearance ; peg:appliedTo ?lm ; peg:dependsOn ?disEv .
        }

        ?appEv peg:hasTime ?appTime .
        # Cas 1 : Temps net (Crisp)
        OPTIONAL {
            ?appTime a peg:CrispTimeInstant ; peg:timeStamp ?appCrispStamp ; peg:timeCalendar ?timeCalendar .
            BIND(?appCrispStamp <= ?timeStamp AS ?appCrispExists)
        }
        # Cas 2 : Temps flou (Fuzzy)
        OPTIONAL {
            ?appTime a peg:FuzzyTimeInstant .
            OPTIONAL { 
                ?appTime peg:hasFuzzyBeginning [peg:timeStamp ?appFuzzyBegStamp ; peg:timeCalendar ?timeCalendar] 
                BIND(?appFuzzyBegStamp <= ?timeStamp AS ?appFuzzyBegExists) # "Peut exister" car le flou a commencé
            }
            OPTIONAL { 
                ?appTime peg:hasFuzzyEnd [peg:timeStamp ?appFuzzyEndStamp ; peg:timeCalendar ?timeCalendar] 
                BIND(?appFuzzyEndStamp <= ?timeStamp AS ?appFuzzyEndExists) # "Existe pour sûr" car le flou est fini
                ` + highTimeStampFilter + `
            }
        }

        ?disEv peg:hasTime ?disTime .
        OPTIONAL {
            ?disTime a peg:CrispTimeInstant ; peg:timeStamp ?disCrispStamp ; peg:timeCalendar ?timeCalendar .
            BIND(?disCrispStamp > ?timeStamp AS ?disCrispExists)
        }
        OPTIONAL {
            ?disTime a peg:FuzzyTimeInstant .
            OPTIONAL { 
                ?disTime peg:hasFuzzyBeginning [peg:timeStamp ?disFuzzyBegStamp ; peg:timeCalendar ?timeCalendar] 
                BIND(?disFuzzyBegStamp > ?timeStamp AS ?disFuzzyBegExists) # "Existe pour sûr" car le flou n'a pas commencé
                ` + lowTimeStampFilter + `
            }
            OPTIONAL { 
                ?disTime peg:hasFuzzyEnd [peg:timeStamp ?disFuzzyEndStamp ; peg:timeCalendar ?timeCalendar] 
                BIND(?disFuzzyEndStamp > ?timeStamp AS ?disFuzzyEndExists) # "Peut encore exister" car le flou n'est pas fini
            }
        }

        FILTER(!BOUND(?appCrispExists) || ?appCrispExists)
        FILTER(!BOUND(?disCrispExists) || ?disCrispExists)
        FILTER(!BOUND(?appFuzzyBegExists) || ?appFuzzyBegExists)
        FILTER(!BOUND(?disFuzzyEndExists) || ?disFuzzyEndExists)

        BIND(
            IF(
                (BOUND(?appFuzzyEndExists) && !?appFuzzyEndExists) || 
                (BOUND(?disFuzzyBegExists) && !?disFuzzyBegExists), 
                "false"^^xsd:boolean, "true"^^xsd:boolean
            ) AS ?existsForSure
        )
    }
    `

    return query;
}
  
function getValidAttributeVersionsFromTime(timeStamp, timeCalendarURI, namedGraphURI, wktGeom=null){
    var query = getPrefixesForQuery(prefixes) + `
SELECT DISTINCT ?lm ?vers ?versValue ?existsForSure ?attrType ?lm WHERE {
    BIND(<${namedGraphURI}> AS ?g)
    BIND("${timeStamp}"^^xsd:dateTimeStamp AS ?timeStamp)
    BIND(<${timeCalendarURI}> AS ?timeCalendar)
    
    ${wktGeom ? `BIND(${wktGeom} AS ?searchArea)` : ""}

    GRAPH ?g {
        ?vers a peg:AttributeVersion .
        ?attr a peg:Attribute ; peg:isAttributeType ?attrType.
        ?lm peg:hasAttribute ?attr .
        ?vers peg:versionValue ?versValue .
        ?meCg peg:makesEffective ?vers ; peg:appliedTo ?attr ; peg:dependsOn ?meEv .
        ?oCg peg:outdates ?vers ; peg:appliedTo ?attr ; peg:dependsOn ?oEv .
    }

    # Filtrage spatial (si géométrie)
    FILTER( !BOUND(?searchArea) || ?attrType != atype:Geometry || geof:sfIntersects(?versValue, ?searchArea) )

    ?meEv peg:hasTime ?meTime .

    OPTIONAL {
        ?meTime a peg:CrispTimeInstant ; peg:timeStamp ?meCrispStamp ; peg:timeCalendar ?timeCalendar .
        BIND(?meCrispStamp <= ?timeStamp AS ?meCrispExists)
    }
    OPTIONAL {
        ?meTime a peg:FuzzyTimeInstant .
        OPTIONAL { 
            ?meTime peg:hasFuzzyBeginning [peg:timeStamp ?meFuzzyBegStamp ; peg:timeCalendar ?timeCalendar] 
            BIND(?meFuzzyBegStamp <= ?timeStamp AS ?meFuzzyBegExists) 
        }
        OPTIONAL { 
            ?meTime peg:hasFuzzyEnd [peg:timeStamp ?meFuzzyEndStamp ; peg:timeCalendar ?timeCalendar] 
            BIND(?meFuzzyEndStamp <= ?timeStamp AS ?meFuzzyEndExists) 
        }
    }

    ?oEv peg:hasTime ?oTime .
    OPTIONAL {
        ?oTime a peg:CrispTimeInstant ; peg:timeStamp ?oCrispStamp ; peg:timeCalendar ?timeCalendar .
        BIND(?oCrispStamp > ?timeStamp AS ?oCrispExists)
    }
    OPTIONAL {
        ?oTime a peg:FuzzyTimeInstant .
        OPTIONAL { 
            ?oTime peg:hasFuzzyBeginning [peg:timeStamp ?oFuzzyBegStamp ; peg:timeCalendar ?timeCalendar] 
            BIND(?oFuzzyBegStamp > ?timeStamp AS ?oFuzzyBegExists) 
        }
        OPTIONAL { 
            ?oTime peg:hasFuzzyEnd [peg:timeStamp ?oFuzzyEndStamp ; peg:timeCalendar ?timeCalendar] 
            BIND(?oFuzzyEndStamp > ?timeStamp AS ?oFuzzyEndExists) 
        }
    }

    FILTER(!BOUND(?meCrispExists) || ?meCrispExists)
    FILTER(!BOUND(?oCrispExists) || ?oCrispExists)
    FILTER(!BOUND(?meFuzzyBegExists) || ?meFuzzyBegExists)
    FILTER(!BOUND(?oFuzzyEndExists) || ?oFuzzyEndExists)
    BIND(
        IF(
            (BOUND(?meFuzzyEndExists) && !?meFuzzyEndExists) || 
            (BOUND(?oFuzzyBegExists) && !?oFuzzyBegExists), 
            "false"^^xsd:boolean, "true"^^xsd:boolean
        ) AS ?existsForSure
    )
}  
    `
    return query ;
}

function getQueryForAttributeVersionValues(valuesForQuery){
    var query = getPrefixesForQuery(prefixes) + `
    SELECT DISTINCT ?vers ?val WHERE {` + valuesForQuery +
    `?vers peg:versionValue ?val }`

    return query;
  }