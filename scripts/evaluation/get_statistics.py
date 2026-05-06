import uuid
from SPARQLWrapper import SELECT
from rdflib import URIRef
from scripts.graph_construction.namespaces import NameSpaces
from scripts.graph_construction import graphdb as gd

np = NameSpaces()


def get_landmarks_per_final_graph(
        graphdb_url:URIRef, repository_name: str,
        out_file:str = None, graph_var: str = "graph", nb_var: str = "nb_landmarks"):
    """Returns a list of dicts with the number of landmarks per final graph, with keys "g" and "nb_landmarks"."""

    variables = [graph_var, nb_var]

    query = np.query_prefixes + f"""
    SELECT ?{graph_var} (COUNT(?{graph_var}) AS ?{nb_var}) WHERE {{
        ?{graph_var} a peg:FinalGraph .
        GRAPH ?{graph_var} {{ ?lm a peg:Landmark }}
    }} GROUP BY ?{graph_var}"""

    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)


def get_landmarks_per_type_per_final_graph(
        graphdb_url:URIRef, repository_name: str, out_file:str = None,
        graph_var: str = "graph", ltype_var: str = "ltype", nb_var: str = "nb_landmarks"
     ) -> list[dict]:
    """
    Returns a list of dicts with the number of landmarks per type and per final graph, with keys "g", "ltype" and "nb_landmarks".
    """

    variables = [graph_var, ltype_var, nb_var]

    query = np.query_prefixes + f"""
    SELECT ?{graph_var} ?{ltype_var} (COUNT(*) AS ?{nb_var}) WHERE {{
        ?{graph_var} a peg:FinalGraph .
        GRAPH ?{graph_var} {{?lm a peg:Landmark ; peg:isLandmarkType ?{ltype_var} }}
    }} GROUP BY ?{graph_var} ?{ltype_var} 
    """

    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)

def get_nb_geometry_versions_per_landmark(
        graphdb_url:URIRef, repository_name: str, fact_named_graph_name: str, out_file: str,
        limit: int = None,
        landmark_var: str = "lm", nb_var: str = "nbAttrVersions"
     ) -> list[dict]:
    """Returns a list of dicts with the number of geometry versions per landmark, with keys "lm" and "nbAttrVersions"."""
    
    fact_named_graph_uri = gd.get_named_graph_uri_from_name(graphdb_url, repository_name, fact_named_graph_name)
    variables = [landmark_var, nb_var]

    limit_str = f"LIMIT {limit}" if limit is not None else ""

    query = np.query_prefixes + f"""
    SELECT ?{landmark_var} (COUNT(DISTINCT ?attrVersion) AS ?{nb_var}) WHERE {{
        GRAPH {fact_named_graph_uri.n3()} {{
            ?{landmark_var} a peg:Landmark ; peg:isLandmarkType ltype:Thoroughfare ; peg:hasAttribute ?attr .
            ?attr peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?attrVersion .
        }}
    }}
    GROUP BY ?{landmark_var}
    ORDER BY DESC(?{nb_var})
    {limit_str}
    """

    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)

def get_geometry_valid_time_per_landmark(
        graphdb_url:URIRef, repository_name: str, facts_named_graph_name: str, out_file: str, limit: int = None,
        landmark_var: str = "lm", label_var: str = "lmLabel", diff_time_var: str = "diffTime"
     ) -> list:
    """
    Returns a list of dicts with the valid time of the geometries of each landmark, with keys "lm", "lmLabel" and "diffTime".
    "diffTime" is the difference in days between the valid time of the geometry version that makes the final graph effective and the valid time of the geometry version that is outdated by it. A
    """

    facts_named_graph_uri = gd.get_named_graph_uri_from_name(graphdb_url, repository_name, facts_named_graph_name)
    limit_str = f"LIMIT {limit}" if limit is not None else ""

    variables = [landmark_var, label_var, diff_time_var]
    
    query = np.query_prefixes + f"""
    SELECT ?{landmark_var} ?{label_var} ?{diff_time_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ 
            ?{landmark_var} a peg:Landmark ; peg:isLandmarkType ltype:Thoroughfare ; peg:hasAttribute ?attr ; rdfs:label ?{label_var}.
            ?attr peg:isAttributeType atype:Geometry ; peg:hasAttributeVersion ?attrVersion .
        }}
        ?cgMe peg:makesEffective ?attrVersion ; peg:dependsOn ?evMe .
        ?cgO peg:outdates ?attrVersion ; peg:dependsOn ?evO .
        ?evMe peg:hasTime ?timeMe .
        ?evO peg:hasTime ?timeO .

        {{ 
            ?timeMe peg:timeStamp ?timeMeStamp .
        }} UNION {{
            ?timeMe peg:hasFuzzyEnd/peg:timeStamp ?timeMeStamp .
            FILTER NOT EXISTS {{ ?timeMe a peg:CrispTimeInstant . }}
        }} UNION {{
            ?timeMe peg:hasFuzzyBeginning/peg:timeStamp ?timeMeStamp .
            FILTER NOT EXISTS {{ ?evMe peg:hasTime [a peg:CrispTimeInstant] . }}
            FILTER NOT EXISTS {{ ?evMe peg:hasFuzzyEnd/peg:timeStamp ?x1 . }}
        }}

        {{
            ?timeO peg:timeStamp ?timeOStamp .
        }} UNION {{
            ?timeO peg:hasFuzzyBeginning/peg:timeStamp ?timeOStamp .
            FILTER NOT EXISTS {{ ?evO peg:hasTime [a peg:CrispTimeInstant] . }}
        }} UNION {{
            ?timeO peg:hasFuzzyEnd/peg:timeStamp ?timeOStamp .
            FILTER NOT EXISTS {{ ?evO peg:hasTime [a peg:CrispTimeInstant] . }}
            FILTER NOT EXISTS {{ ?evO peg:hasFuzzyBeginning/peg:timeStamp ?x2 . }}
        }}
        BIND(ofn:asDays(?timeOStamp - ?timeMeStamp) AS ?diffTime)
    }}
    ORDER BY DESC(?diffTime)
    {limit_str}
    """

    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)

def get_nb_addresses_by_year(
        graphdb_url:URIRef, repository_name: str, facts_named_graph_name: str, list_of_years: list[str],
        time_var: str = "time", nb_addr_var: str = "nbAddresses",
        out_file: str = None
        ) -> list[dict]:
    """
    Returns a list of dicts with the number of addresses created per year, with keys "year" and "nbAddresses".
    """

    facts_named_graph_uri = gd.get_named_graph_uri_from_name(graphdb_url, repository_name, facts_named_graph_name)
    years_values = " ".join([f'"{year}-01-01T00:00:00Z"^^xsd:dateTimeStamp' for year in list_of_years])
    variables = [time_var, nb_addr_var]

    query = np.query_prefixes + f"""
    SELECT ?{time_var} (COUNT(DISTINCT ?sn) AS ?{nb_addr_var}) WHERE {{
    VALUES ?{time_var} {{
        {years_values}
    }}

    {{
        SELECT ?sn ?tsAppSn ?tsDisSn ?tsAppTh ?tsDisTh WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            BIND(lrtype:Belongs AS ?lrType)
            BIND(ltype:StreetNumber AS ?snType)
            GRAPH ?gf {{
                ?lr a peg:LandmarkRelation ; 
                peg:isLandmarkRelationType ?lrType ; 
                peg:locatum ?sn ; 
                peg:relatum ?th .
                ?sn peg:isLandmarkType ?snType .
            }}

            ?changeAppTh peg:appliedTo ?th ; peg:isChangeType ctype:LandmarkAppearance ; peg:dependsOn ?evThApp .
            ?changeDisTh peg:appliedTo ?th ; peg:isChangeType ctype:LandmarkDisappearance ; peg:dependsOn ?evThDis .
            ?evThApp peg:hasTime ?timeAppTh .
            ?evThDis peg:hasTime ?timeDisTh .

            {{ 
                ?timeAppTh peg:timeStamp ?tsAppTh .
            }} UNION {{
                ?timeAppTh peg:hasFuzzyEnd/peg:timeStamp ?tsAppTh .
                FILTER NOT EXISTS {{ ?evThApp a peg:CrispTimeInstant . }}
            }} UNION {{
                ?timeAppTh peg:hasFuzzyBeginning/peg:timeStamp ?tsAppTh .
                FILTER NOT EXISTS {{ ?evThApp peg:hasTime [a peg:CrispTimeInstant] . }}
                FILTER NOT EXISTS {{ ?evThApp peg:hasFuzzyEnd/peg:timeStamp ?x1 . }}
            }}

            {{ 
                ?timeDisTh peg:timeStamp ?tsDisTh .
            }} UNION {{
                ?timeDisTh peg:hasFuzzyBeginning/peg:timeStamp ?tsDisTh .
                FILTER NOT EXISTS {{ ?evThDis peg:hasTime [a peg:CrispTimeInstant] . }}
            }} UNION {{
                ?timeDisTh peg:hasFuzzyEnd/peg:timeStamp ?tsDisTh .
                FILTER NOT EXISTS {{ ?evThDis peg:hasTime [a peg:CrispTimeInstant] . }}
                FILTER NOT EXISTS {{ ?evThDis peg:hasFuzzyBeginning/peg:timeStamp ?x2 . }}
            }}

            ?changeAppSn peg:appliedTo ?sn ; peg:isChangeType ctype:LandmarkAppearance ; peg:dependsOn ?evSnApp .
            ?changeDisSn peg:appliedTo ?sn ; peg:isChangeType ctype:LandmarkDisappearance ; peg:dependsOn ?evSnDis .
            ?evSnApp peg:hasTime ?timeAppSn .
            ?evSnDis peg:hasTime ?timeDisSn .

            # Récupération des bornes pour sn
            {{ 
                ?timeAppSn peg:timeStamp ?tsAppSn .
            }} UNION {{
                ?timeAppSn peg:hasFuzzyEnd/peg:timeStamp ?tsAppSn .
                FILTER NOT EXISTS {{ ?evSnApp a peg:CrispTimeInstant . }}
            }} UNION {{
                ?timeAppSn peg:hasFuzzyBeginning/peg:timeStamp ?tsAppSn .
                FILTER NOT EXISTS {{ ?evSnApp peg:hasTime [a peg:CrispTimeInstant] . }}
                FILTER NOT EXISTS {{ ?evSnApp peg:hasFuzzyEnd/peg:timeStamp ?x1 . }}
            }}

            {{ 
                ?timeDisSn peg:timeStamp ?tsDisSn .
            }} UNION {{
                ?timeDisSn peg:hasFuzzyBeginning/peg:timeStamp ?tsDisSn .
                FILTER NOT EXISTS {{ ?evSnDis peg:hasTime [a peg:CrispTimeInstant] . }}
            }} UNION {{
                ?timeDisSn peg:hasFuzzyEnd/peg:timeStamp ?tsDisSn .
                FILTER NOT EXISTS {{ ?evSnDis peg:hasTime [a peg:CrispTimeInstant] . }}
                FILTER NOT EXISTS {{ ?evSnDis peg:hasFuzzyBeginning/peg:timeStamp ?x2 . }}
            }}
        }}
    }}

    FILTER(?{time_var} >= ?tsAppSn || ?{time_var} <= ?tDisSn)
    FILTER(?{time_var} >= ?tsAppTh || ?{time_var} <= ?tDisTh)
}}
GROUP BY ?{time_var}
ORDER BY ?{time_var}
"""
    
    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)

def get_triples_per_graph(
        graphdb_url:URIRef, repository_name: str, out_file:str = None,
        graph_var: str = "graph", nb_var: str = "nb_triples"
     ) -> list[dict]:
    """Returns a list of dicts with the number of triples per graph, with keys "g" and "nb_triples". """

    variables = [graph_var, nb_var]

    query = np.query_prefixes + f"""
    SELECT ?{graph_var} (COUNT(?s) AS ?{nb_var}) WHERE {{
        GRAPH ?{graph_var} {{?s ?p ?o }}
    }} GROUP BY ?{graph_var}"""


    return gd.run_select_query_to_txt_file(query, graphdb_url, repository_name, out_file)
