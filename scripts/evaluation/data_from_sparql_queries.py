from scripts.graph_construction import graphdb as gd
from scripts.graph_construction.namespaces import NameSpaces

np = NameSpaces()

def select_streetnumbers_attr_geom_change_times(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    query = np.query_prefixes  + f"""
    SELECT DISTINCT 
    ?lm ?label ?change 
    (ofn:asDays(?time - "0001-01-01"^^xsd:dateTimeStamp) AS ?timeDay)
    (ofn:asDays(?timeBefore - "0001-01-01"^^xsd:dateTimeStamp) AS ?timeBeforeDay)
    (ofn:asDays(?timeAfter - "0001-01-01"^^xsd:dateTimeStamp) AS ?timeAfterDay)
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?lm a peg:Landmark }}
        ?lm peg:isLandmarkType ltype:StreetNumber ; peg:hasAttribute ?attr ; skos:hiddenLabel ?snLabel .
        ?lr a peg:LandmarkRelation ; peg:isLandmarkRelationType lrtype:Belongs ; peg:locatum ?lm ; peg:relatum [skos:hiddenLabel ?thLabel] .
        BIND(CONCAT(?thLabel, "||", ?snLabel) AS ?label)
        ?attr peg:isAttributeType atype:Geometry .
        ?change peg:appliedTo ?attr ; peg:dependsOn ?event .
        OPTIONAL {{ ?event peg:hasTime [peg:timeStamp ?time] }} 
        OPTIONAL {{ ?event peg:hasTime [peg:hasFuzzyBeginning [peg:timeStamp ?timeAfter]] }}
        OPTIONAL {{ ?event peg:hasTime [peg:hasFuzzyEnd [peg:timeStamp ?timeBefore]] }}
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

def select_streetnumbers_attr_geom_version_and_sources(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    query = np.query_prefixes  + f"""
    SELECT DISTINCT 
    ?sn ?label ?attrVersion ?sourceLabel
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?sn a peg:Landmark ; peg:isLandmarkType ltype:StreetNumber ; skos:hiddenLabel ?snLabel .}}
        ?sn peg:hasAttribute [peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?attrVersion] .
        [] a peg:LandmarkRelation ; peg:locatum ?sn ; peg:relatum ?th ; peg:isLandmarkRelationType lrtype:Belongs .
        ?th peg:isLandmarkType ltype:Thoroughfare ; skos:hiddenLabel ?thLabel .
        BIND(CONCAT(?thLabel, "||", ?snLabel) AS ?label)
        ?attrVersion prov:wasDerivedFrom ?prov .
        ?prov rico:isOrWasDescribedBy [rdfs:label ?sourceLabel] .
    }}
    """
    
    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

##################################

def select_streetnumbers_labels(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    query = np.query_prefixes  + f"""
    SELECT DISTINCT ?sn ?snLabel ?thLabel
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{
            ?sn a peg:Landmark ;peg:isLandmarkType ltype:StreetNumber ; rdfs:label|skos:altLabel ?snLabel .
            [] a peg:LandmarkRelation ; peg:locatum ?sn ; peg:relatum ?th ; peg:isLandmarkRelationType lrtype:Belongs .
            ?th peg:isLandmarkType ltype:Thoroughfare ; rdfs:label|skos:altLabel ?thLabel .
        }}
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)


def select_streetnumbers_attr_geom_version_valid_times(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    
    query = np.query_prefixes  + f"""

    SELECT DISTINCT ?sn ?attrVersion ?startTime ?endTime
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{
            ?sn a peg:Landmark ; peg:isLandmarkType ltype:StreetNumber ; peg:hasAttribute [peg:isAttributeType atype:Geometry; peg:hasAttributeVersion ?attrVersion].
        }}
        FILTER NOT EXISTS {{
            ?attrVersion peg:hasTrace ?traceAV1, ?traceAV2 .
            ?traceAV1 peg:differentVersionValueFrom ?traceAV2 .
            }}
        ?cgMe peg:makesEffective ?attrVersion ; peg:dependsOn ?evME .
        ?cgO peg:outdates ?attrVersion ; peg:dependsOn ?evO .
        ?evME peg:hasTime ?meTime .
        ?evO peg:hasTime ?oTime .
        {{ ?meTime peg:timeStamp ?startTime }} UNION {{ ?meTime peg:hasFuzzyEnd [peg:timeStamp ?startTime] }}
        {{ ?oTime peg:timeStamp ?startTime }} UNION {{ ?oTime peg:hasFuzzyBeginning [peg:timeStamp ?endTime] }}
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

def select_streetnumbers_attr_geom_version_values(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    
    query = np.query_prefixes  + f"""

    SELECT DISTINCT ?attrVersion ?versionValue
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{
            ?sn a peg:Landmark ;peg:isLandmarkType ltype:StreetNumber ; peg:hasAttribute [peg:isAttributeType atype:Geometry; peg:hasAttributeVersion ?attrVersion].
        }}
        ?attrVersion peg:versionValue ?versionValue .
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

def select_streetnumbers_attr_geom_change_valid_times(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    
    query = np.query_prefixes  + f"""
    SELECT DISTINCT ?sn ?attr ?change ?time ?timeAfter ?timeBefore 
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?change a peg:AttributeChange ; peg:appliedTo ?attr ; peg:dependsOn ?ev . }}
        ?attr peg:isAttributeType atype:Geometry .
        ?sn a peg:Landmark ; peg:isLandmarkType ltype:StreetNumber ; peg:hasAttribute ?attr .
        OPTIONAL {{ ?ev peg:hasTime [peg:timeStamp ?time] }} 
        OPTIONAL {{ ?ev peg:hasTime [peg:hasFuzzyBeginning [peg:timeStamp ?timeAfter]] }}
        OPTIONAL {{ ?ev peg:hasTime [peg:hasFuzzyEnd [peg:timeStamp ?timeBefore]] }}
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

def select_streetnumber_modified_attr_geom_versions(
        graphdb_url, repository_name,
        facts_named_graph_uri, named_graph_uris:list, res_query_file):
    named_graph_filter = ",".join([uri.n3() for uri in named_graph_uris])
    
    query = np.query_prefixes  + f"""
    SELECT DISTINCT 
    ?newAttrVersion ?attrVersion
    (ofn:asDays(?tStampApp - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppDay)
    (ofn:asDays(?tStampAppBefore - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppBeforeDay)
    (ofn:asDays(?tStampAppAfter - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppAfterDay)
    (ofn:asDays(?tStampDis - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisDay)
    (ofn:asDays(?tStampDisBefore - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisBeforeDay)
    (ofn:asDays(?tStampDisAfter - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisAfterDay)
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?lm a peg:Landmark ; peg:isLandmarkType ltype:StreetNumber .}}
        ?lm peg:hasAttribute [peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?newAttrVersion] .
        ?cgME peg:makesEffective ?newAttrVersion ; peg:dependsOn ?evME.
        ?cgO peg:outdates ?newAttrVersion ; peg:dependsOn ?evO.
        ?newAttrVersion prov:wasDerivedFrom ?attrVersion .
        GRAPH ?g {{ ?attrVersion a prov:Entity . }}
        FILTER (?g IN ({named_graph_filter}))
        
        OPTIONAL {{ ?evME peg:hasTime [peg:timeStamp ?tStampApp ; peg:timePrecision ?tPrecApp] }}
        OPTIONAL {{ ?evME peg:hasTimeBefore [peg:timeStamp ?tStampAppBefore ; peg:timePrecision ?tPrecAppBefore] }}
        OPTIONAL {{ ?evME peg:hasTimeAfter [peg:timeStamp ?tStampAppAfter ; peg:timePrecision ?tPrecAppAfter] }}
        OPTIONAL {{ ?evO peg:hasTime [peg:timeStamp ?tStampDis ; peg:timePrecision ?tPrecDis] }}
        OPTIONAL {{ ?evO peg:hasTimeBefore [peg:timeStamp ?tStampDisBefore ; peg:timePrecision ?tPrecDisBefore] }}
        OPTIONAL {{ ?evO peg:hasTimeAfter [peg:timeStamp ?tStampDisAfter ; peg:timePrecision ?tPrecDisAfter] }}
    }}
    """
    print(query)

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)

def select_streetnumber_unmodified_attr_geom_versions(graphdb_url, repository_name, facts_named_graph_uri, res_query_file):
    query = np.query_prefixes  + f"""
    SELECT DISTINCT 
    ?attrVersion
    (ofn:asDays(?tStampApp - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppDay)
    (ofn:asDays(?tStampAppBefore - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppBeforeDay)
    (ofn:asDays(?tStampAppAfter - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampAppAfterDay)
    (ofn:asDays(?tStampDis - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisDay)
    (ofn:asDays(?tStampDisBefore - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisBeforeDay)
    (ofn:asDays(?tStampDisAfter - "0001-01-01"^^xsd:dateTimeStamp) AS ?tStampDisAfterDay)
    WHERE {{
        ?lm a peg:Landmark ; peg:isLandmarkType ltype:StreetNumber .
        ?lm peg:hasAttribute [peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?attrVersion] .
        ?cgME peg:makesEffective ?attrVersion ; peg:dependsOn ?evME.
        ?cgO peg:outdates ?attrVersion ; peg:dependsOn ?evO.

        OPTIONAL {{ ?evME peg:hasTime [peg:timeStamp ?tStampApp ; peg:timePrecision ?tPrecApp] }}
        OPTIONAL {{ ?evME peg:hasTimeBefore [peg:timeStamp ?tStampAppBefore ; peg:timePrecision ?tPrecAppBefore] }}
        OPTIONAL {{ ?evME peg:hasTimeAfter [peg:timeStamp ?tStampAppAfter ; peg:timePrecision ?tPrecAppAfter] }}
        OPTIONAL {{ ?evO peg:hasTime [peg:timeStamp ?tStampDis ; peg:timePrecision ?tPrecDis] }}
        OPTIONAL {{ ?evO peg:hasTimeBefore [peg:timeStamp ?tStampDisBefore ; peg:timePrecision ?tPrecDisBefore] }}
        OPTIONAL {{ ?evO peg:hasTimeAfter [peg:timeStamp ?tStampDisAfter ; peg:timePrecision ?tPrecDisAfter] }}
    }}
    """

    gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, res_query_file)