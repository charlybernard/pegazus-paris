# SPARQL queries for *Temporal evolution* modelet

SPARQL queries describing informal competence questions

## To find out which geographical entities of a defined type exist at a given time

What roads existed in Paris in 1860? Note: `<http://www.wikidata.org/entity/Q1985727>` indicates that the calendar in which the date is written is the proleptic Gregorian calendar.

```sparql
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX time: <http://www.w3.org/2006/time#>
PREFIX peg: <http://rdf.geohistoricaldata.org/def/address#>
PREFIX ctype: <http://rdf.geohistoricaldata.org/id/codes/address/changeType/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?lm ?lmLabel ?lmType WHERE {
    VALUES (?timeStamp ?timePrecision ?timeCalendar) {
        ("1860-01-01T00:00:00"^^xsd:dateTime time:unitDay <http://www.wikidata.org/entity/Q1985727>)
    }

    ?lm a peg:Landmark ; peg:isLandmarkType ?lmType ; peg:changedBy [peg:isChangeType ctype:LandmarkAppearance ; peg:dependsOn ?evApp], [peg:isChangeType ctype:LandmarkDisappearance ; peg:dependsOn ?evDis] ; rdfs:label ?lmLabel.
    ?evApp a peg:Event ; ?pApp ?timeApp .
    ?evDis a peg:Event ; ?pDis ?timeDis .
    FILTER(?pApp IN (peg:hasTime, peg:hasLatestTimeInstant, peg:hasEarliestTimeInstant))
    FILTER(?pDis IN (peg:hasTime, peg:hasLatestTimeInstant, peg:hasEarliestTimeInstant))
    ?timeApp peg:timeStamp ?tsApp ; peg:timePrecision ?tpApp ; peg:timeCalendar ?timeCalendar .
    ?timeDis peg:timeStamp ?tsDis ; peg:timePrecision ?tpDis ; peg:timeCalendar ?timeCalendar .

    FILTER(
        ((?pApp = peg:hasTime && ?timeStamp >= ?tsApp) ||
            (?pApp = peg:hasLatestTimeInstant && ?timeStamp >= ?tsApp))
        &&
        ((?pDis = peg:hasTime && ?timeStamp <= ?tsDis) ||
            (?pDis = peg:hasEarliestTimeInstant && ?timeStamp <= ?tsDis)))
}
```

## To find out how long an address is valid under a given name

In what years can you find the address ‘50 rue Gérard’?

```sparql
```

## To obtain the history of a landmark

What events related to a change of geometry have occurred on rue Gérard?

```sparql
PREFIX peg: <http://rdf.geohistoricaldata.org/def/address#>
PREFIX ltype: <http://rdf.geohistoricaldata.org/id/codes/address/landmarkType/>
PREFIX atype: <http://rdf.geohistoricaldata.org/id/codes/address/attributeType/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?street ?change ?timeStamp ?timeStampEarliest ?timeStampLatest ?oudatedVersion ?madeEffectiveVersion WHERE {
    BIND("rue Gérard"@fr AS ?streetLabel)
    ?street a peg:Landmark ; peg:isLandmarkType ltype:Thoroughfare ; peg:hasAttribute ?attrGeom ; (rdfs:label|skos:altLabel) ?streetLabel.
    ?attrGeom a peg:Attribute ; peg:isAttributeType atype:Geometry .
    ?change peg:appliedTo ?attrGeom ; peg:dependsOn ?event.
    ?event a peg:Event.
    OPTIONAL {?event peg:hasTime [a peg:TimeInstant; peg:timeStamp ?timeStamp; peg:timePrecision ?timePrecision; peg:timeCalendar ?timeCalendar]}
    OPTIONAL {?event peg:hasEarliestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampEarliest; peg:timePrecision ?timePrecisionEarliest; peg:timeCalendar ?timeCalendarEarliest]}
    OPTIONAL {?event peg:hasLatestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampLatest; peg:timePrecision ?timePrecisionLatest; peg:timeCalendar ?timeCalendarLatest]}
    OPTIONAL {?change peg:makesEffective [peg:versionValue ?madeEffectiveVersion]}
    OPTIONAL {?change peg:outdates [peg:versionValue ?oudatedVersion]}
}
```

What is the history of the geometry of the rue Gérard? (set of geometries with their validity interval)

```sparql
PREFIX peg: <http://rdf.geohistoricaldata.org/def/address#>
PREFIX ltype: <http://rdf.geohistoricaldata.org/id/codes/address/landmarkType/>
PREFIX atype: <http://rdf.geohistoricaldata.org/id/codes/address/attributeType/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?street ?geomValue ?change ?timeStampME ?timeStampEarliestME ?timeStampLatestME ?timeStampO ?timeStampEarliestO ?timeStampLatestO WHERE {
    BIND("rue Gérard"@fr AS ?streetLabel)
    ?street a peg:Landmark ; peg:isLandmarkType ltype:Thoroughfare ; peg:hasAttribute ?attrGeom ; (rdfs:label|skos:altLabel) ?streetLabel.
    ?attrGeom a peg:Attribute ; peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?geomVersion .
    ?geomVersion peg:versionValue ?geomValue .
    ?geomVersion peg:isMadeEffectiveBy [peg:appliedTo ?attrGeom ; peg:dependsOn ?eventME] ; peg:isOutdatedBy [peg:appliedTo ?attrGeom ; peg:dependsOn ?eventO].
    OPTIONAL {?eventME peg:hasTime [a peg:TimeInstant; peg:timeStamp ?timeStampME; peg:timePrecision ?timePrecisionME; peg:timeCalendar ?timeCalendarME]}
    OPTIONAL {?eventME peg:hasEarliestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampEarliestMEME; peg:timePrecision ?timePrecisionEarliestME; peg:timeCalendar ?timeCalendarEarliestME]}
    OPTIONAL {?eventME peg:hasLatestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampLatestME; peg:timePrecision ?timePrecisionLatestME; peg:timeCalendar ?timeCalendarLatestME]}
    OPTIONAL {?eventO peg:hasTime [a peg:TimeInstant; peg:timeStamp ?timeStampO; peg:timePrecision ?timePrecisionO; peg:timeCalendar ?timeCalendarO]}
OPTIONAL {?eventO peg:hasEarliestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampEarliestOO; peg:timePrecision ?timePrecisionEarliestO; peg:timeCalendar ?timeCalendarEarliestO]}
OPTIONAL {?eventO peg:hasLatestTimeInstant [a peg:TimeInstant; peg:timeStamp ?timeStampLatestO; peg:timePrecision ?timePrecisionLatestO; peg:timeCalendar ?timeCalendarLatestO]}
}
```
