from rdflib import URIRef, Graph
from scripts.graph_construction.namespaces import NameSpaces
from scripts.graph_construction import graphdb as gd


np = NameSpaces()

######### Main function

# Function to rely all resources from `factoids_named_graph_uri` named graph to similar resources in `facts_named_graph_uri` (if they exists, else create the similar resource)
# Triple to tell similarity is store in `inter_sources_named_graph_uri`

def link_factoids_with_facts(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Landmarks are created as follows:
        * creation of links (using `peg:hasRoot`) between landmarks in the facts named graph and those which are in the factoid named graph ;
        * using inference rules, new `peg:hasRoot` links are deduced
        * for each resource defined in the factoids, we check whether it exists in the fact graph (if it is linked with a `peg:hasRoot` to a resource in the fact graph)
        * for unlinked factoid resources, we create its equivalent in the fact graph
    """

    label_property = np.SKOS.hiddenLabel

    make_rooting_for_landmarks(graphdb_url, repository_name, label_property, facts_named_graph_uri, inter_sources_named_graph_uri, tmp_named_graph_uri)
    make_rooting_for_landmark_relations(graphdb_url, repository_name, label_property, facts_named_graph_uri, inter_sources_named_graph_uri)
    make_rooting_for_landmark_attributes(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)
    make_rooting_for_temporal_entities(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)
    manage_labels_after_landmark_rooting(graphdb_url, repository_name, facts_named_graph_uri)
    
    # Les racines de modification sont créées sauf pour les modifications d'attributs.
    make_rooting_for_changes(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)
    make_rooting_for_events(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)
    
####################################################################

## Management of root elements
"""
This part includes functions for creating roots: each element of named graphs that include factoids must have an equivalent
in the factoid named graph. This equivalent is a root. A root can be the equivalent of several elements of several elements.
For example, if there is a ‘rue Gérard’ in several named graphs, they must be linked to the same root.
Roots apply to Landmark, LandmarkRelation, Attribute, AttributeVersion, Event, Change.
"""

########## Landmark

# Make rooting at landmarks level
# The way the rooting is made depends on the type of landmark

def make_rooting_for_landmarks(
        graphdb_url:URIRef, repository_name:str, label_property:URIRef,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Create `peg:hasRoot` links between similar landmarks.
    """

    landmark_type_uris = [np.LTYPE["Municipality"], np.LTYPE["District"], np.LTYPE["PostalCodeArea"], np.LTYPE["Thoroughfare"]]
    for landmark_type_uri in landmark_type_uris:
        make_rooting_for_landmarks_according_label(graphdb_url, repository_name, landmark_type_uri, label_property,
                                                   facts_named_graph_uri, inter_sources_named_graph_uri)
        
    lm_and_lr_type_uris = [
        [np.LTYPE["HouseNumber"], np.LRTYPE["Belongs"]],
        [np.LTYPE["DistrictNumber"], np.LRTYPE["Belongs"]],
        [np.LTYPE["StreetNumber"], np.LRTYPE["Belongs"]],
    ]
    for elem in lm_and_lr_type_uris:
        lm_type_uri, lm_type_uri = elem
        make_rooting_for_landmarks_according_label_and_relation(graphdb_url, repository_name, lm_type_uri, lm_type_uri, label_property,
                                                                facts_named_graph_uri, inter_sources_named_graph_uri, tmp_named_graph_uri)

def make_rooting_for_landmarks_according_label(graphdb_url:URIRef, repository_name:str, landmark_type_uri:URIRef, label_property:URIRef,
                                               facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    """
    Create roots and traces for landmark according a label criterion : a landmark is similar to a root landmark if they share the same label.
    `label_property` is the property for which the label is linked to the landmark (`rdfs:label`, `skos:hiddenLabel`, ...)
    """

    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{ ?rootLandmark a peg:Landmark ; peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel . }}
    }}
    WHERE {{
        {{
            SELECT DISTINCT ?gf ?landmarkType ?keyLabel ?propLabel WHERE {{
                VALUES (?gf ?propLabel ?landmarkType) {{
                    ({facts_named_graph_uri.n3()} {label_property.n3()} {landmark_type_uri.n3()})
                }}
                ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
                GRAPH ?g {{ ?landmark a peg:Landmark . }}
                ?landmark peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel .
                FILTER NOT EXISTS {{
                    ?landmark peg:hasRoot ?x .
                    GRAPH ?gf {{ ?x a peg:Landmark . }}
                    }}
            }}
        }}
        OPTIONAL {{ GRAPH ?gf {{?existingRootLandmark a peg:Landmark ; peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel . }} }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "Landmark/", STRUUID())) AS ?toCreateRootLandmark)
        BIND(IF(BOUND(?existingRootLandmark), ?existingRootLandmark, ?toCreateRootLandmark) AS ?rootLandmark)
    }}
    """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?landmark peg:hasRoot ?rootLandmark .
            ?rootLandmark peg:hasTrace ?landmark .
        }}
    }}
    WHERE {{
        VALUES (?gf ?gi ?propLabel ?landmarkType) {{
            ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()} {label_property.n3()} {landmark_type_uri.n3()})
        }}
        GRAPH ?gf {{ ?rootLandmark a peg:Landmark . }}
        ?rootLandmark peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel .
        GRAPH ?g {{ ?landmark a peg:Landmark . }}
        ?landmark peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel .
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
    }}   
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


def make_rooting_for_landmarks_according_label_and_relation(
        graphdb_url:URIRef, repository_name:str,
        landmark_type_uri:URIRef, landmark_relation_type_uri:URIRef, label_property:URIRef,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Reconcile landmark entities by creating/linking to 'Root' entities based on 
    shared labels and shared parent relations.

    This function implements a "Rooting" logic necessary for non-unique identifiers. 
    For example, a House Number "10" is not globally unique, but becomes unique 
    when associated with a specific street (the relatum).

    The process follows three stages:
    1.  **Identify/Create Roots**: Finds landmarks in active source graphs that lack 
        a root. It checks if a 'Root Landmark' with the same label and same parent 
        relation already exists in the facts graph; if not, it generates a new UUID-based 
        Root Landmark and Relation.
    2.  **Generate Match Keys**: Constructs a temporary lookup table in `tmp_named_graph_uri`. 
        Each relation is assigned a composite string key: 
        `type + locatum_label + locatum_type + root_relatum_uri`.
    3.  **Link Sources to Roots**: Performs a join on the generated keys to insert 
        `peg:hasRoot` and `peg:hasTrace` properties, effectively merging 
        disparate source data (factoids) into consolidated factual entities.

    Args:
        graphdb_url: The SPARQL endpoint URL.
        repository_name: Target GraphDB repository.
        landmark_type_uri: The class of the landmark (e.g., peg:HouseNumber).
        landmark_relation_type_uri: The predicate type (e.g., lrtype:Belongs).
        label_property: The property linking the label (e.g., rdfs:label).
        facts_named_graph_uri: Graph containing consolidated factual data.
        inter_sources_named_graph_uri: Graph for cross-source metadata.
        tmp_named_graph_uri: Temporary graph for reconciliation keys.
    """

    query1 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{
        ?rootLandmark a peg:Landmark ; peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel .
        ?rootLR a peg:LandmarkRelation ; peg:isLandmarkRelationType ?landmarkRelationType ; peg:locatum ?rootLandmark ; peg:relatum ?rootRelatum .
    }}
    GRAPH ?gt {{ ?rootLR ?propLabel ?lrKeyLabel . }}
}}
WHERE {{
    {{
        SELECT DISTINCT ?gf ?gt ?landmarkType ?propLabel ?keyLabel ?landmarkRelationType ?rootRelatum WHERE {{
            VALUES (?gf ?gt ?propLabel ?landmarkType ?landmarkRelationType) {{
                ({facts_named_graph_uri.n3()} {tmp_named_graph_uri.n3()} {label_property.n3()} {landmark_type_uri.n3()} {landmark_relation_type_uri.n3()})
                }}
            GRAPH ?g {{ ?lr a peg:LandmarkRelation . }}
            ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
            ?lr peg:isLandmarkRelationType ?landmarkRelationType ;
                peg:locatum [a peg:Landmark ; peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel] ;
                peg:relatum [peg:hasRoot ?rootRelatum] .
            GRAPH ?gf {{ ?rootRelatum a ?rRClass . }}
            FILTER NOT EXISTS {{
                ?lr peg:hasRoot ?x .
                GRAPH ?gf {{ ?x a peg:LandmarkRelation . }}
            }}
        }}  
    }}
    OPTIONAL {{
        GRAPH ?gf {{
            ?existingRootLandmark a peg:Landmark ; peg:isLandmarkType ?landmarkType ; ?propLabel ?keyLabel .
            ?existingRootLR a peg:LandmarkRelation ; peg:isLandmarkRelationType ?landmarkRelationType ;
                peg:locatum ?existingRootLandmark ; peg:relatum ?rootRelatum .
        }}
    }}
    BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "Landmark/", STRUUID())) AS ?toCreateRootLandmark)
    BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "LandmarkRelation/", STRUUID())) AS ?toCreateRootLR)
    BIND(IF(BOUND(?existingRootLandmark), ?existingRootLandmark, ?toCreateRootLandmark) AS ?rootLandmark)
    BIND(IF(BOUND(?existingRootLR), ?existingRootLR, ?toCreateRootLR) AS ?rootLR)
    BIND(CONCAT("type=", STR(?landmarkRelationType), "&locatum_label=", STR(?keyLabel), "&locatum_type=", STR(?landmarkType), "&relatum=", STR(?rootRelatum)) AS ?lrKeyLabel)
}}
    """

    query2 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gt {{
        ?landmarkRelation skos:hiddenLabel ?label
    }}
}}
WHERE {{
    VALUES (?gt ?propLabel ?landmarkType ?landmarkRelationType) {{
         ({tmp_named_graph_uri.n3()} {label_property.n3()} {landmark_type_uri.n3()} {landmark_relation_type_uri.n3()})
    }}

    ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
    GRAPH ?g {{
        ?landmarkRelation a peg:LandmarkRelation ;
                          peg:isLandmarkRelationType ?landmarkRelationType ;
                          peg:relatum ?relatum ;
                          peg:locatum ?locatum .
        ?locatum a peg:Landmark ; peg:isLandmarkType ?landmarkType .
    }}
    ?rootRelatum peg:hasTrace ?relatum .
    ?locatum ?propLabel ?locatumLabel .
    
    BIND(CONCAT("type=", STR(?landmarkRelationType), "&locatum_label=", STR(?locatumLabel), "&locatum_type=", STR(?landmarkType), "&relatum=", STR(?rootRelatum)) AS ?label)
}}
    """

    query3 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gi {{
        ?landmarkRelation peg:hasRoot ?rootLandmarkRelation .
        ?rootLandmarkRelation peg:hasTrace ?landmarkRelation .
        ?locatum peg:hasRoot ?rootLocatum .
        ?rootLocatum peg:hasTrace ?locatum .
    }}
}} WHERE {{
    VALUES (?gf ?gi ?propLabel) {{
        ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()} {label_property.n3()})
    }}
    ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
    GRAPH ?gt {{
        ?landmarkRelation ?propLabel ?lrLabel .
        ?rootLandmarkRelation ?propLabel ?lrLabel .
    }}   
    GRAPH ?g {{ ?landmarkRelation a peg:LandmarkRelation ; peg:locatum ?locatum . }}
    GRAPH ?gf {{ ?rootLandmarkRelation a peg:LandmarkRelation ; peg:locatum ?rootLocatum . }}
}}
"""

    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

########## Changes / Events

def make_rooting_for_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    """
    Create `peg:hasRoot` links between similar changes in a graph database.
    This function establishes rooting relationships for changes across source graphs and 
    integrates them into a fact graph. It performs two main operations:
    1. Identifies unique changes (excluding attribute changes) from active source graphs 
        and creates root change nodes in the fact graph if they don't already exist.
    2. Links changes to their corresponding root changes by creating `peg:hasRoot` and 
        `peg:hasTrace` relationships in the inter-sources named graph.
    Args:
         graphdb_url (URIRef): The URI reference to the graph database endpoint.
         repository_name (str): The name of the repository in the graph database.
         facts_named_graph_uri (URIRef): The URI reference to the named graph containing 
              fact data where root changes are created.
         inter_sources_named_graph_uri (URIRef): The URI reference to the named graph where 
              rooting relationships are established between changes and their roots.
    Returns:
         None
    Note:
         - Attribute changes are excluded from rooting operations.
         - Only active source graphs (with `peg:isActiveGraph "true"`) are processed.
         - Root changes are created if they don't already exist for a given change type 
            and applied element combination.
    """

    # Integration of changes in the fact graph (except for attribute changes, which are not unique)
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?rootCg a peg:Change ; peg:isChangeType ?changeType ; peg:appliedTo ?rootElem .
        }}
    }} WHERE {{
        {{
            SELECT DISTINCT ?gf ?changeType ?rootElem WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
                GRAPH ?g {{ ?cg a ?cgClass }}
                ?cgClass rdfs:subClassOf* peg:Change .
                ?cg peg:isChangeType ?changeType ; peg:appliedTo [peg:hasRoot ?rootElem].
                GRAPH ?gf {{ ?rootElem a ?rEClass . }}
                FILTER NOT EXISTS {{?cg a peg:AttributeChange .}}
                FILTER NOT EXISTS {{ 
                    ?cg peg:hasRoot ?x1 .
                    GRAPH ?gf {{ ?x a peg:Change . }}
                }}
            }} 
        }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "Change/", STRUUID())) AS ?toCreateRootCg)
        OPTIONAL {{
            GRAPH ?gf {{
                ?existingRootCg a peg:Change .
                ?rootElem a ?x2 .
                 }}
            ?existingRootCg peg:isChangeType ?changeType ; peg:appliedTo ?rootElem .
        }}
        BIND(IF(BOUND(?existingRootCg), ?existingRootCg, ?toCreateRootCg) AS ?rootCg)
    }}
    """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?cg peg:hasRoot ?rootCg .
            ?rootCg peg:hasTrace ?cg .
        }}
    }} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
        GRAPH ?g {{ ?cg a ?cgClass . }}
        GRAPH ?gf {{
            ?rootCg a peg:Change .
            ?rootElem a ?x .   
        }}
        ?cgClass rdfs:subClassOf* peg:Change .
        ?cg peg:isChangeType ?changeType ; peg:appliedTo [peg:hasRoot ?rootElem] .
        ?rootCg peg:isChangeType ?changeType ; peg:appliedTo ?rootElem .
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        FILTER NOT EXISTS {{ ?cg a peg:AttributeChange .}}
    }}
    """ 

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def make_rooting_for_events(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    """
        Create root event mappings and trace relationships in a graph database.
        This function executes two SPARQL INSERT queries to establish rooting for events:
        - Query 1: Creates root events and links them to dependent changes in the facts graph
        - Query 2: Establishes hasRoot and hasTrace relationships between events across graphs
        Args:
            graphdb_url (URIRef): The URI reference of the graph database endpoint.
            repository_name (str): The name of the repository in the graph database.
            facts_named_graph_uri (URIRef): The URI reference of the named graph containing fact statements.
            inter_sources_named_graph_uri (URIRef): The URI reference of the named graph for inter-source relationships.
        Returns:
            None
        Raises:
            Exception: Propagates any exceptions raised by gd.run_update_query() during SPARQL query execution.
    """

    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?rootEvent a peg:Event .
            ?rootChange peg:dependsOn ?rootEvent .
        }}
    }}
    WHERE {{
        {{
            SELECT DISTINCT ?gf ?rootChange WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?g {{ ?ev a peg:Event }}
                ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
                [ peg:dependsOn ?ev ] peg:hasRoot ?rootChange .
                GRAPH ?gf {{ ?rootChange a ?x1 . }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "Event/", STRUUID())) AS ?toCreateRootEvent)
        OPTIONAL {{
            GRAPH ?gf {{
                ?existingRootEvent a peg:Event .
                ?rootChange a ?x2 .
                
            }}
            ?rootChange peg:dependsOn ?existingRootEvent .
        }}
        BIND(IF(BOUND(?existingRootEvent), ?existingRootEvent, ?toCreateRootEvent) AS ?rootEvent)
    }}
    """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?event peg:hasRoot ?rootEvent .
            ?rootEvent peg:hasTrace ?event .
        }}
    }} WHERE {{
        VALUES (?gf ?gi) {{
            ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()})
        }}
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?ev a peg:Event . }}
        GRAPH ?gf {{
            ?rootEv a peg:Event .
            ?rootChange a ?x .
            }}
        [peg:hasRoot ?rootChange] peg:dependsOn ?ev.
        ?rootChange peg:dependsOn ?rootEv .
    }}
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

########## Landmark relations

def make_rooting_for_landmark_relations(graphdb_url, repository_name, label_property:URIRef, facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    """
    Pour des relations entre repères dans le graphe nommé `factoids_named_graph_uri`, les lier avec une relation entre repères dans `facts_named_graph_uri` qui sont similaires (mêmes locatum, relatums et type de relation).
    Le lien créé est mis dans `factoids_facts_named_graph_uri`.
    """

    # Creation of a hiddenLabel for each LandmarkRelation in the (aggregation) fact graph. It is composed as follows: URI of the locatum + ‘&’ + ordered URIs of the relatums separated by a semicolon
    # For example, if a relationship has URILoc as its locatum and URIRel1 and URIRel2 as its relatums, the hidden label will be ‘URILoc1&URIRel1;URIRel2’.
    # We create this label for relationships that don't have one
    query1 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gf {{?lr {label_property.n3()} ?keyLabel}}
        }} WHERE {{
            {{
                SELECT ?gf ?lr (CONCAT(STR(?rootLoc), "|", GROUP_CONCAT(STR(?rootRel); separator=";")) AS ?keyLabel) WHERE {{
                    BIND({facts_named_graph_uri.n3()} AS ?gf)
                    GRAPH ?gf {{
                        ?lr a peg:LandmarkRelation .
                        ?rootLoc a ?x1 .
                        ?rootRel a ?x2 .
                        }}
                    ?lr peg:relatum ?rootRel ; peg:locatum ?rootLoc .
                }}
                GROUP BY ?gf ?lr ?rootLoc ORDER BY ?rootRel
            }}
        }}
    """

    # We do the same thing for the relations in the factoid graph. We don't integrate the URIs of the locatums and relatums, but the URIs of their root in the fact graph.
    query2 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gi {{?lr {label_property.n3()} ?keyLabel}}
        }} WHERE {{
            BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
            {{
                SELECT ?g ?lr (CONCAT(STR(?rootLoc), "|", GROUP_CONCAT(STR(?rootRel); separator=";")) AS ?keyLabel) WHERE {{
                    BIND({facts_named_graph_uri.n3()} AS ?gf)
                    GRAPH ?g {{ ?lr a ?lrClass . }}
                    ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
                    ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
                    ?lr peg:relatum [peg:hasRoot ?rootRel] ; peg:locatum [peg:hasRoot ?rootLoc] .
                    GRAPH ?gf {{
                        ?rootLoc a ?x1 .
                        ?rootRel a ?x2 .
                    }}
                }}
                GROUP BY ?g ?lr ?rootLoc
                ORDER BY ?rootRel
            }}
        }}
    """

    # query3 = np.query_prefixes + f"""
    #     INSERT {{
    #         GRAPH ?gf {{ ?rootLandmarkRelation a peg:LandmarkRelation ; peg:isLandmarkRelationType ?landmarkRelationType ; skos:hiddenLabel ?keyLabel . }}
    #         GRAPH ?gi {{
    #             ?landmarkRelation peg:hasRoot ?rootLandmarkRelation .
    #             ?rootLandmarkRelation peg:hasTrace ?landmarkRelation .
    #         }}
    #     }}
    #     WHERE {{
    #         BIND({facts_named_graph_uri.n3()} AS ?gf)
    #         BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
    #         BIND({factoids_named_graph_uri.n3()} AS ?gs)
    #         {{
    #             SELECT DISTINCT ?landmarkRelationType ?keyLabel WHERE {{
    #                 ?lr a peg:LandmarkRelation ; peg:isLandmarkRelationType ?landmarkRelationType ; skos:hiddenLabel ?keyLabel .
    #             }}
    #         }}
    #         BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "LandmarkRelation/", STRUUID())) AS ?toCreateRootLR)
    #         OPTIONAL {{
    #             GRAPH ?gf {{ ?existingRootLR a peg:LandmarkRelation }}
    #             ?existingRootLR skos:hiddenLabel ?keyLabel .
    #         }}
    #         BIND(IF(BOUND(?existingRootLR), ?existingRootLR, ?toCreateRootLR) AS ?rootLandmarkRelation)
    #         GRAPH ?gs {{ ?landmarkRelation a ?lrClass . }}
    #         ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
    #         ?landmarkRelation peg:isLandmarkRelationType ?landmarkRelationType ; skos:hiddenLabel ?keyLabel .
    #     }}
    # """

    query3 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?rootLR a peg:LandmarkRelation ; peg:isLandmarkRelationType ?landmarkRelationType ; ?propLabel ?keyLabel .
        }}
    }}
    WHERE {{
        {{
            SELECT DISTINCT ?gf ?landmarkRelationType ?propLabel ?keyLabel WHERE {{
                VALUES (?gf ?propLabel) {{
                    ({facts_named_graph_uri.n3()} {label_property.n3()})
                }}
                ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
                GRAPH ?g {{ ?lr a peg:LandmarkRelation . }}
                ?lr peg:isLandmarkRelationType ?landmarkRelationType ; ?propLabel ?keyLabel .
                FILTER NOT EXISTS {{
                    ?lr peg:hasRoot ?x .
                    GRAPH ?gf {{ ?x a peg:LandmarkRelation . }}
                }}
            }}  
        }}
        OPTIONAL {{
            GRAPH ?gf {{ ?existingRootLR a peg:LandmarkRelation . }}
            ?existingRootLR peg:isLandmarkRelationType ?landmarkRelationType ; ?propLabel ?keyLabel .
        }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "LandmarkRelation/", STRUUID())) AS ?toCreateRootLR)
        BIND(IF(BOUND(?existingRootLR), ?existingRootLR, ?toCreateRootLR) AS ?rootLR)
    }}
    """

    query4 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gi {{
                ?landmarkRelation peg:hasRoot ?rootLandmarkRelation .
                ?rootLandmarkRelation peg:hasTrace ?landmarkRelation .
            }}
        }}
        WHERE {{
            VALUES (?gf ?gi ?propLabel) {{
                ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()} {label_property.n3()})
            }}
            ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
            GRAPH ?g {{ ?landmarkRelation a ?lrClass . }}
            GRAPH ?gf {{ ?rootLandmarkRelation a peg:LandmarkRelation . }}
            ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
            ?landmarkRelation peg:isLandmarkRelationType ?landmarkRelationType ; ?propLabel ?keyLabel .
            ?rootLandmarkRelation peg:isLandmarkRelationType ?landmarkRelationType ; ?propLabel ?keyLabel .
        }}  
    """


    query5 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gf {{ ?rootLandmarkRelation ?prop ?rootLandmark . }}
        }}
        WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            GRAPH ?gf {{
                ?rootLandmarkRelation a peg:LandmarkRelation .
                ?rootLandmark a peg:Landmark .
                }}
            ?lr peg:hasRoot ?rootLandmarkRelation ; ?prop [peg:hasRoot ?rootLandmark] .
            FILTER (?prop IN (peg:locatum, peg:relatum))
        }}
    """

    queries = [query1, query2, query3, query4, query5]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

########## Atttibutes

def make_rooting_for_landmark_attributes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    # Integration of changes in the fact graph (except for attribute changes, which are not unique)
    # query = np.query_prefixes + f"""
    # INSERT {{
    #     GRAPH ?gf {{
    #         ?rootAttr a peg:Attribute ; peg:isAttributeType ?attrType .
    #         ?rootLandmark peg:hasAttribute ?rootAttr .
    #     }}
    #     GRAPH ?gi {{
    #         ?attr peg:hasRoot ?rootAttr .
    #         ?rootAttr peg:hasTrace ?attr .
    #         }}
    # }} WHERE {{
    #     BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
    #     BIND({factoids_named_graph_uri.n3()} AS ?gs)
    #     {{
    #         SELECT DISTINCT ?gf ?attrType ?rootLandmark ?rootAttr WHERE {{
    #             {{
    #                 SELECT DISTINCT ?gf ?attrType ?rootLandmark ?existingRootAttr WHERE {{
    #                     BIND({facts_named_graph_uri.n3()} AS ?gf)
    #                     ?landmark peg:hasRoot ?rootLandmark ; peg:hasAttribute [a peg:Attribute ; peg:isAttributeType ?attrType] . 
    #                     OPTIONAL {{
    #                         GRAPH ?gf {{ ?existingRootAttr a peg:Attribute . }}
    #                         ?existingRootAttr peg:isAttributeType ?attrType .
    #                         ?rootLandmark peg:hasAttribute ?existingRootAttr .
    #                     }}
    #                 }}
    #             }}
    #             BIND(IF(BOUND(?existingRootAttr), ?existingRootAttr, URI(CONCAT(STR(URI(facts:)), "Attribute/", STRUUID()))) AS ?rootAttr)
    #         }}
    #     }}

    #     GRAPH ?gs {{ ?attr a peg:Attribute . }}
    #     ?attr peg:isAttributeType ?attrType .
    #     ?landmark peg:hasRoot ?rootLandmark ; peg:hasAttribute ?attr .
    #     FILTER NOT EXISTS {{ ?attr peg:hasRoot ?x . }}
    # }}
    # """

    query1 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{
        ?rootAttr a peg:Attribute ; peg:isAttributeType ?attrType .
        ?rootLandmark peg:hasAttribute ?rootAttr .
    }}
}}
WHERE {{
    {{
        SELECT DISTINCT ?gf ?attrType ?rootLandmark WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
            GRAPH ?g {{ ?attr a peg:Attribute . }}
            FILTER NOT EXISTS {{
                ?attr peg:hasRoot ?x .
                GRAPH ?gf {{ ?x a peg:Attribute . }}
            }}
            ?attr peg:isAttributeType ?attrType .
            ?landmark peg:hasRoot ?rootLandmark ; peg:hasAttribute ?attr .
            GRAPH ?gf {{ ?rootLandmark a peg:Landmark . }}
        }}
    }}
    OPTIONAL {{
        GRAPH ?gf {{ 
            ?existingRootAttr a peg:Attribute .
            ?rootLandmark a peg:Landmark .
            }}
        ?rootLandmark peg:hasAttribute ?existingRootAttr .
        ?existingRootAttr peg:isAttributeType ?attrType .
    }}
    BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "Attribute/", STRUUID())) AS ?toCreateRootAttr)
    BIND(IF(BOUND(?existingRootAttr), ?existingRootAttr, ?toCreateRootAttr) AS ?rootAttr)
}}
"""

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?attr peg:hasRoot ?rootAttr .
            ?rootAttr peg:hasTrace ?attr .
        }}  
    }} WHERE {{
        VALUES (?gf ?gi) {{
            ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()})
        }}
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?attr a peg:Attribute . }}
        GRAPH ?gf {{ ?rootAttr a peg:Attribute . }}
        ?attr peg:isAttributeType ?attrType .
        ?rootAttr peg:isAttributeType ?attrType .
        ?lm peg:hasAttribute ?attr ; peg:hasRoot [peg:hasAttribute ?rootAttr].
    }}
    """ 

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

########## Temporal entities

# def make_rooting_for_crisp_time_instants(graphdb_url:URIRef, repository_name:str,
#                                         facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
#     query = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gf {{ ?rootTime a peg:CrispTimeInstant ; peg:timeStamp ?ts ; peg:timeCalendar ?tc ; peg:timePrecision ?tp . }}
#         GRAPH ?gi {{
#             ?time peg:hasRoot ?rootTime .
#             ?rootTime peg:hasTrace ?time .
#         }}
#     }} WHERE {{
#         BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
#         {{
#             SELECT DISTINCT ?gf ?rootTime ?existingRootTime ?toCreateRootTime ?ts ?tc ?tp WHERE {{
#                 {{
#                     SELECT DISTINCT ?gf ?existingRootTime ?ts ?tc ?tp {{
#                         BIND({facts_named_graph_uri.n3()} AS ?gf)
#                         GRAPH ?gs {{ ?time peg:timeStamp ?ts ; peg:timeCalendar ?tc ; peg:timePrecision ?tp .}}
#                         OPTIONAL {{
#                             GRAPH ?gf {{ ?existingRootTime peg:timeStamp ?ts ; peg:timeCalendar ?tc ; peg:timePrecision ?tp .}}
#                         }}
#                         FILTER (?gs != ?gf)
#                     }}
#                 }}
#                 BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "TI_", STRUUID())) AS ?toCreateRootTime)
#                 BIND(IF(BOUND(?existingRootTime), ?existingRootTime, ?toCreateRootTime) AS ?rootTime)
#             }}
#         }}
#         GRAPH ?gs {{ ?time peg:timeStamp ?ts ; peg:timeCalendar ?tc ; peg:timePrecision ?tp .}}
#         FILTER (?gs != ?gf)
#     }}
#     """

#     gd.run_update_query(query, graphdb_url, repository_name)


def make_rooting_for_crisp_time_instants(graphdb_url:URIRef, repository_name:str,
                                        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    query1 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{
        ?rootTime a peg:CrispTimeInstant ; peg:timeStamp ?timeStamp ; peg:timePrecision ?timePrec ; peg:timeCalendar ?timeCal .
    }}
}}
WHERE {{
    {{
        SELECT DISTINCT ?gf ?timeStamp ?timePrec ?timeCal WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
            GRAPH ?g {{ ?time a peg:CrispTimeInstant . }}
            FILTER NOT EXISTS {{
                ?time peg:hasRoot ?x .
                GRAPH ?gf {{ ?x a peg:CrispTimeInstant . }}
            }}
            ?time peg:timeStamp ?timeStamp ; peg:timePrecision ?timePrec ; peg:timeCalendar ?timeCal .
        }}
    }}
    OPTIONAL {{
        GRAPH ?gf {{ ?existingRootTime a peg:CrispTimeInstant . }}
        ?existingRootTime a peg:CrispTimeInstant ; peg:timeStamp ?timeStamp ; peg:timePrecision ?timePrec ; peg:timeCalendar ?timeCal .
    }}
    BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "CrispTimeInstant/", STRUUID())) AS ?toCreateRootTime)
    BIND(IF(BOUND(?existingRootTime), ?existingRootTime, ?toCreateRootTime) AS ?rootTime)
}}
"""
    
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?time peg:hasRoot ?rootTime .
            ?rootTime peg:hasTrace ?time .
        }}  
    }} WHERE {{
        VALUES (?gf ?gi) {{
            ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()})
        }}
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?time a peg:CrispTimeInstant . }}
        GRAPH ?gf {{ ?rootTime a peg:CrispTimeInstant . }}
        ?time peg:timeStamp ?timeStamp ; peg:timePrecision ?timePrec ; peg:timeCalendar ?timeCal .
        ?rootTime peg:timeStamp ?timeStamp ; peg:timePrecision ?timePrec ; peg:timeCalendar ?timeCal .
    }}
    """ 

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

# def make_rooting_for_crisp_time_intervals(graphdb_url:URIRef, repository_name:str,
#                                           facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):

#     query = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gf {{ ?rootTimeInt a peg:CrispTimeInterval ; peg:hasBeginning ?rootStartTime ; peg:hasEnd ?rootEndTime. }}
#         GRAPH ?gi {{
#             ?timeInt peg:hasRoot ?rootTimeInt .
#             ?rootTimeInt peg:hasTrace ?timeInt .
#         }}
#     }} WHERE {{
#         BIND({inter_sources_named_graph_uri.n3()} AS ?gi)
#         {{
#             SELECT DISTINCT ?gf ?rootTimeInt ?existingRootTimeInt ?toCreateRootTimeInt ?rootStartTime ?rootEndTime WHERE {{
#                 {{
#                     SELECT DISTINCT ?gf ?existingRootTimeInt ?rootStartTime ?rootEndTime {{
#                         BIND({facts_named_graph_uri.n3()} AS ?gf)
#                         GRAPH ?gs {{ ?time peg:hasBeginning ?startTime ; peg:hasEnd ?endTime . }}
#                         ?rootStartTime peg:hasTrace ?startTime .
#                         ?rootEndTime peg:hasTrace ?endTime .
#                         OPTIONAL {{ GRAPH ?gf {{?existingRootTimeInt peg:hasBeginning ?rootStartTime ; peg:hasEnd ?rootEndTime .}} }}
#                         FILTER (?gs != ?gf)
#                     }}
#                 }}
#                 BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "TI_", STRUUID())) AS ?toCreateRootTimeInt)
#                 BIND(IF(BOUND(?existingRootTimeInt), ?existingRootTimeInt, ?toCreateRootTimeInt) AS ?rootTimeInt)
#             }}
#         }}
#         GRAPH ?gs {{ ?timeInt peg:hasBeginning ?startTime ; peg:hasEnd ?endTime .}}
#         FILTER (?gs != ?gf)
#     }}
#     """

#     gd.run_update_query(query, graphdb_url, repository_name)


def make_rooting_for_crisp_time_intervals(graphdb_url:URIRef, repository_name:str,
                                          facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    query1 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{
        ?rootTime a peg:CrispTimeInterval ; peg:hasBeginning ?rootStartTime ; peg:hasEnd ?rootEndTime .
    }}
}}
WHERE {{
    {{
        SELECT DISTINCT ?gf ?rootStartTime ?rootEndTime WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            GRAPH ?g {{ ?time peg:hasBeginning ?startTime ; peg:hasEnd ?endTime . }}
            FILTER NOT EXISTS {{
                ?time peg:hasRoot ?x .
                GRAPH ?gf {{ ?x a peg:CrispTimeInterval . }}
            }}
            ?rootStartTime peg:hasTrace ?startTime .
            ?rootEndTime peg:hasTrace ?endTime .
            ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
            GRAPH ?gf {{ 
                ?rootStartTime a ?x1 .
                ?rootEndTime a ?x2 .
            }}
        }}
    }}
    OPTIONAL {{
        GRAPH ?gf {{ ?existingRootTime a peg:CrispTimeInterval . }}
        ?existingRootTime a peg:CrispTimeInterval ; peg:hasBeginning ?rootStartTime ; peg:hasEnd ?rootEndTime .
    }}
    BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "CrispTimeInterval/", STRUUID())) AS ?toCreateRootTime)
    BIND(IF(BOUND(?existingRootTime), ?existingRootTime, ?toCreateRootTime) AS ?rootTime)
}}
"""
    
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{
            ?time peg:hasRoot ?rootTime .
            ?rootTime peg:hasTrace ?time .
        }}  
    }} WHERE {{
        VALUES (?gf ?gi) {{
            ({facts_named_graph_uri.n3()} {inter_sources_named_graph_uri.n3()})
        }}
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?time a peg:CrispTimeInterval . }}
        GRAPH ?gf {{
            ?rootTime a peg:CrispTimeInterval .
            ?rootStartTime a ?x1 .
            ?rootEndTime a ?x2 .
            }}
        ?time peg:hasBeginning ?startTime ; peg:hasEnd ?endTime .
        ?rootTime peg:hasBeginning ?rootStartTime ; peg:hasEnd ?rootEndTime .
        ?startTime peg:hasRoot ?rootStartTime .
        ?endTime peg:hasRoot ?rootEndTime .
    }}
    """ 

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def make_rooting_for_temporal_entities(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef):
    make_rooting_for_crisp_time_instants(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)
    make_rooting_for_crisp_time_intervals(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri)

###################################################### Other processes ######################################################

def manage_labels_after_landmark_rooting(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef):
    # Add a label for root landmarks which have been initialized after landmark rooting
    # If there is already a label (∃ <landmark rdfs:label label>), then add alternative labels if they exists
    # This query exists to get only one label per landmark, other labels are alt labels
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{ ?rootLandmark rdfs:label ?rlLabel ; skos:altLabel ?rlAltLabel . }}
    }} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
    
        GRAPH ?gf {{ ?rootLandmark a peg:Landmark . }}
        ?rootLandmark peg:hasTrace ?landmark .
        OPTIONAL {{ ?rootLandmark rdfs:label ?rootLandmarkLabel . }}
        OPTIONAL {{ ?rootLandmark skos:altLabel ?rootLandmarkAltLabel . }}
        OPTIONAL {{ ?landmark rdfs:label ?landmarkLabel . }}
        OPTIONAL {{ ?landmark skos:prefLabel ?landmarkPrefLabel . }}

        BIND(IF(BOUND(?rootLandmarkLabel), ?rootLandmarkLabel,
                IF(BOUND(?landmarkPrefLabel), ?landmarkPrefLabel, ?landmarkLabel)
                ) AS ?rlLabel)

        BIND(IF(BOUND(?landmarkPrefLabel) && ?landmarkPrefLabel != ?rlLabel, ?landmarkPrefLabel, ?landmarkLabel) AS ?rlAltLabel)
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)
