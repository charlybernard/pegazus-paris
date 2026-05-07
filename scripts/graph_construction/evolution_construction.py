from rdflib import URIRef
from scripts.graph_construction.namespaces import NameSpaces
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import multi_sources_processing as msp
from scripts.graph_construction import resource_transfert as rt

np = NameSpaces()

#####################################################################################################################

def initialize_missing_changes_and_events_for_landmarks(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri):

    gregorian_calendar_uri = np.WD["Q1985727"] #URIRef("http://www.wikidata.org/entity/Q1985727")
    
    create_missing_landmark_entities(graphdb_url, repository_name, facts_named_graph_uri)
    map_potential_times_to_events(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    finalize_event_times(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri, gregorian_calendar_uri)

    # Nettoyage et finalisation
    gd.remove_named_graph_from_uri(tmp_named_graph_uri)
    rt.transfer_elements_to_roots(graphdb_url, repository_name, facts_named_graph_uri)


def create_missing_landmark_entities(graphdb_url, repository_name, facts_named_graph_uri):
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?missingChange a peg:LandmarkChange ; peg:isChangeType ?changeType ; peg:appliedTo ?lm ; peg:dependsOn ?missingEvent .
            ?missingEvent a peg:Event .
        }}
    }} WHERE {{
        {{
            SELECT * WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                VALUES ?changeType {{ ctype:LandmarkAppearance ctype:LandmarkDisappearance }}
                GRAPH ?gf {{ ?lm a peg:Landmark . }}
                FILTER NOT EXISTS {{
                    ?change peg:isChangeType ?changeType ; peg:appliedTo ?lm .
                }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "CG_", STRUUID())) AS ?missingChange)
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "EV_", STRUUID())) AS ?missingEvent)
    }}
    """
    gd.run_update_query(query, graphdb_url, repository_name)


def map_potential_times_to_events(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri):
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?event ?propInstantTime ?time . }}
    }}
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        GRAPH ?gf {{
            ?lm a peg:Landmark .
            ?time a ?timeClass . 
        }}
        ?lm peg:hasTrace ?lmTrace .
        ?change peg:isChangeType ?changeType ; peg:appliedTo ?lm ; peg:dependsOn ?event .
        {{
            VALUES (?changeType ?propIntervalTime ?propInstantTime) {{
                (ctype:LandmarkAppearance peg:hasBeginning peg:hasTimeBefore)
                (ctype:LandmarkDisappearance peg:hasEnd peg:hasTimeAfter)
            }}
            ?lmTrace peg:hasTime [?propIntervalTime ?timeTrace ] .
        }} UNION {{
            ?changeTrace peg:isChangeType ?changeType ; peg:appliedTo ?lmTrace ; peg:dependsOn ?eventTrace .
            ?eventTrace ?propInstantTime ?timeTrace .
            FILTER (?propInstantTime IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
        }}
        ?time peg:hasTrace ?timeTrace .
        FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }} }}
    }}
    """
    gd.run_update_query(query, graphdb_url, repository_name)


def finalize_event_times(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri, calendar_uri):
    """Étape 3 : Sélectionner et insérer les meilleures dates (précises puis estimées)."""


    query1 = np.query_prefixes + f"""
    INSERT {{ GRAPH ?gf {{ ?event ?propTime ?time . }} }}
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND(peg:hasTime AS ?propTime)
        GRAPH ?gf {{ ?lm a peg:Landmark . ?time a ?timeClass . }}
        ?change peg:dependsOn ?event ; peg:appliedTo ?lm .
        FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }} }}
        GRAPH ?gt {{ ?event ?propTime ?time . }}              
        ?event ?propTime ?time .
    }}
    """

    query2 = np.query_prefixes + f"""
    INSERT {{ GRAPH ?gf {{ ?event ?propTime ?time . }} }}
    WHERE {{
        {{
            SELECT DISTINCT ?gf ?gt ?propTime ?timeCal ?event (MIN(?diffTime) AS ?diffTimeMin) (MAX(?diffTime) AS ?diffTimeMax) WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                BIND({calendar_uri.n3()} AS ?timeCal)
                VALUES ?propTime {{ peg:hasTimeBefore peg:hasTimeAfter }}
                GRAPH ?gf {{ ?lm a peg:Landmark . }}
                ?change peg:dependsOn ?event ; peg:appliedTo ?lm .
                GRAPH ?gt {{ ?event ?propTime ?time . }}
                ?time peg:timeStamp ?timeStamp ; peg:timeCalendar ?timeCal .
                BIND(ofn:asDays(?timeStamp - "0001-01-01"^^xsd:dateTimeStamp) AS ?diffTime)
                FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }}}}
            }}
            GROUP BY ?gf ?gt ?propTime ?timeCal ?event
        }}
        BIND(IF(?propTime = peg:hasTimeBefore, ?diffTimeMin, ?diffTimeMax) AS ?diffTime)
        ?event ?propTime ?time .
        ?time peg:timeStamp ?timeStamp ; peg:timeCalendar ?timeCal .
        GRAPH ?gf {{ ?time a ?timeClass . }}
        FILTER(ofn:asDays(?timeStamp - "0001-01-01"^^xsd:dateTimeStamp) = ?diffTime)
    }}
    """
    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


# def initialize_missing_changes_and_events_for_landmarks(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri):
#     gregorian_calendar_uri = np.WD["Q1985727"] # URIRef("http://www.wikidata.org/entity/Q1985727")
    
#     # Exécution des étapes
#     step_create_base_structures(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, gregorian_calendar_uri)
#     step_process_crisp_times(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
#     step_process_fuzzy_times(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, gregorian_calendar_uri)
#     step_finalize_links(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, gregorian_calendar_uri)

#     # Nettoyage
#     gd.remove_named_graph_from_uri(tmp_named_graph_uri)
#     rt.transfer_elements_to_roots(graphdb_url, repository_name, facts_named_graph_uri)

# def step_create_base_structures(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, calendar_uri):
#     """
#     We create missing changes and events for landmarks and landmark relations and we collect all potential time information related to these events in a temporary named graph. This step is necessary to be able to process fuzzy times in the next step.
#     """
    
#     query1 = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gf {{
#             ?missingChange a peg:Change ; peg:isChangeType ?changeType ; peg:appliedTo ?elem ; peg:dependsOn ?missingEvent .
#             ?missingEvent a peg:Event .
#         }}
#     }} WHERE {{
#         {{
#             SELECT * WHERE {{
#                 BIND({facts_named_graph_uri.n3()} AS ?gf)
#                 VALUES (?class ?changeType) {{
#                     (peg:Landmark peg:LandmarkAppearance)
#                     (peg:Landmark peg:LandmarkDisappearance)
#                     (peg:LandmarkRelation peg:LandmarkRelationAppearance)
#                     (peg:LandmarkRelation peg:LandmarkRelationDisappearance)    
#                 }}
#                 GRAPH ?gf {{ ?elem a ?elemClass . }}
#                 ?elemClass rdfs:subClassOf* ?class .

#                 FILTER NOT EXISTS {{ ?change peg:isChangeType ?changeType ; peg:appliedTo ?elem . }}
#             }}
#         }}
#         BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "CG_", STRUUID())) AS ?missingChange)
#         BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "EV_", STRUUID())) AS ?missingEvent)
#     }}
#     """

#     query2 = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH {tmp_named_graph_uri.n3()} {{ ?event ?propInstantTime ?time . }} 
#     }} WHERE {{
#         BIND({facts_named_graph_uri.n3()} AS ?gf)
#         GRAPH ?gf {{ ?elem a ?elemClass . ?time a ?timeClass . }}
#         ?elemClass rdfs:subClassOf* ?class .
#         ?elem peg:hasTrace ?elemTrace .
#         ?change peg:isChangeType ?changeType ; peg:appliedTo ?elem ; peg:dependsOn ?event .
#         {{
#             VALUES (?class ?changeType ?propIntervalTime ?propInstantTime) {{
#                 (peg:Landmark peg:LandmarkAppearance peg:hasBeginning peg:hasTimeBefore)
#                 (peg:Landmark peg:LandmarkDisappearance peg:hasEnd peg:hasTimeAfter)
#                 (peg:LandmarkRelation peg:LandmarkRelationAppearance peg:hasBeginning peg:hasTimeBefore)
#                 (peg:LandmarkRelation peg:LandmarkRelationDisappearance peg:hasEnd peg:hasTimeAfter)
#             }}
#             ?elemTrace peg:hasTime [?propIntervalTime ?timeTrace ] .
#         }} UNION {{
#             ?changeTrace peg:isChangeType ?changeType ; peg:appliedTo ?elemTrace ; peg:dependsOn ?eventTrace .
#             ?eventTrace ?propInstantTime ?timeTrace .
#             FILTER (?propInstantTime IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
#         }}
#         ?time peg:hasTrace ?timeTrace .
#         FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }} }}
#     }}"""

#     queries = [query1, query2]
#     gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

# def step_process_crisp_times(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri):
#     """
#     We process crisp times related to events of appearance and disappearance of landmarks to transfer them to the event and be able to use them in the next step to process fuzzy times. If an event has already a time, we keep it, otherwise we transfer the time related to its traces or the time related to the landmark valid time (startTime if it is a event related to a LandmarkAppearance, endTime if it is a event related to a LandmarkDisappearance).
#     """

#     query = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gf {{ ?event peg:hasTime ?time . }}
#     }} WHERE {{
#         BIND(peg:hasTime AS ?propTime)
#         BIND({facts_named_graph_uri.n3()} AS ?gf)
#         BIND({tmp_named_graph_uri.n3()} AS ?gt)
#         GRAPH ?gf {{
#             ?elem a ?elemClass .
#             ?time a ?timeClass .
#         }}
#         ?elemClass rdfs:subClassOf* ?selectedClass .
#         FILTER(?selectedClass IN (peg:Landmark, peg:LandmarkRelation))
#         ?change peg:dependsOn ?event ; peg:appliedTo ?elem .
#         FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }} }}
#         GRAPH ?gt {{ ?event ?propTime ?time . }}
#     }}"""

#     gd.run_update_query(query, graphdb_url, repository_name)
    
# def step_process_fuzzy_times(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, calendar_uri):
#     # 1. Associer les temps min/max (en jours) aux événements dans ?gt
#     query_calc_bounds = np.query_prefixes + f"""
#     INSERT {{ GRAPH {tmp_named_graph_uri.n3()} {{ ?event ?rawPropTime ?selectDiffTime . }} }}
#     WHERE {{
#         {{
#             SELECT ?event ?rawPropTime (IF(?rawPropTime = peg:hasRawTimeBefore, MIN(?diffTime), MAX(?diffTime)) AS ?selectDiffTime) WHERE {{
#                 VALUES (?propTime ?rawPropTime) {{
#                     (peg:hasTimeBefore peg:hasRawTimeBefore) (peg:hasTimeAfter peg:hasRawTimeAfter) 
#                 }}
#                 GRAPH {facts_named_graph_uri.n3()} {{ ?elem a ?elemClass . }}
#                 ?elemClass rdfs:subClassOf* ?selectedClass .
#                 FILTER(?selectedClass IN (peg:Landmark, peg:LandmarkRelation))
#                 ?change peg:dependsOn ?event ; peg:appliedTo ?elem .
                
#                 GRAPH {tmp_named_graph_uri.n3()} {{ ?event ?propTime ?time . }}
#                 ?time peg:timeStamp ?timeStamp ; peg:timeCalendar {calendar_uri.n3()} .
#                 BIND(ofn:asDays(?timeStamp - "0001-01-01"^^xsd:dateTimeStamp) AS ?diffTime)
#                 FILTER NOT EXISTS {{ GRAPH {facts_named_graph_uri.n3()} {{ ?event peg:hasTime ?t }} }}
#             }}
#             GROUP BY ?event ?rawPropTime
#         }}
#     }}"""

#     # 2. Créer les FuzzyTimeInstant
#     query_create_fuzzy = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH {facts_named_graph_uri.n3()} {{ ?time a peg:FuzzyTimeInstant . }}
#         GRAPH {tmp_named_graph_uri.n3()} {{ ?time peg:hasRawTimeBefore ?tB ; peg:hasRawTimeAfter ?tA . }}
#     }} WHERE {{
#         {{
#             SELECT DISTINCT ?tB ?tA WHERE {{
#                 GRAPH {facts_named_graph_uri.n3()} {{ ?ev a peg:Event . FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }} }}
#                 GRAPH {tmp_named_graph_uri.n3()} {{ 
#                     OPTIONAL {{ ?ev peg:hasRawTimeBefore ?tB . }}
#                     OPTIONAL {{ ?ev peg:hasRawTimeAfter ?tA . }}
#                 }}
#                 FILTER (BOUND(?tB) || BOUND(?tA))
#             }}
#         }}
#         BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "TI_", STRUUID())) AS ?time)
#     }}"""

#     queries = [query_calc_bounds, query_create_fuzzy]
#     gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

# def step_finalize_links(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri, calendar_uri):
#     # Associer les débuts/fins réels aux temps flous via le calcul de diffTime
#     query_link_fuzzy_bounds = np.query_prefixes + f"""
#     INSERT {{ GRAPH {facts_named_graph_uri.n3()} {{ ?time peg:hasFuzzyBeginning ?fBeg ; peg:hasFuzzyEnd ?fEnd }} }}
#     WHERE {{
#         GRAPH {facts_named_graph_uri.n3()} {{ ?time a peg:FuzzyTimeInstant . }}
#         GRAPH {tmp_named_graph_uri.n3()} {{ 
#             OPTIONAL {{ ?time peg:hasRawTimeAfter ?tA . }}
#             OPTIONAL {{ ?time peg:hasRawTimeBefore ?tB . }}
#         }}
#         OPTIONAL {{
#             GRAPH {facts_named_graph_uri.n3()} {{ ?fBeg peg:timeStamp ?tsBeg . }}
#             FILTER(ofn:asDays(?tsBeg - "0001-01-01"^^xsd:dateTimeStamp) = ?tA)
#         }}
#         OPTIONAL {{
#             GRAPH {facts_named_graph_uri.n3()} {{ ?fEnd peg:timeStamp ?tsEnd . }}
#             FILTER(ofn:asDays(?tsEnd - "0001-01-01"^^xsd:dateTimeStamp) = ?tB)
#         }}
#     }}"""

#     # Liaison finale Event -> FuzzyTime
#     query_final_event_time = np.query_prefixes + f"""
#     INSERT {{ GRAPH {facts_named_graph_uri.n3()} {{ ?ev peg:hasTime ?time }} }}
#     WHERE {{
#         GRAPH {facts_named_graph_uri.n3()} {{ ?ev a peg:Event ; FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }} }}
#         GRAPH {tmp_named_graph_uri.n3()} {{ 
#             OPTIONAL {{ ?ev peg:hasRawTimeAfter ?tA . }}
#             OPTIONAL {{ ?ev peg:hasRawTimeBefore ?tB . }}
#         }}
#         ?time a peg:FuzzyTimeInstant .
#         OPTIONAL {{
#             GRAPH {facts_named_graph_uri.n3()} {{ ?time peg:hasFuzzyBeginning [ peg:timeStamp ?tsA ] . }}
#             BIND(ofn:asDays(?tsA - "0001-01-01"^^xsd:dateTimeStamp) AS ?fA)
#         }}
#         OPTIONAL {{
#             GRAPH {facts_named_graph_uri.n3()} {{ ?time peg:hasFuzzyEnd [ peg:timeStamp ?tsB ] . }}
#             BIND(ofn:asDays(?tsB - "0001-01-01"^^xsd:dateTimeStamp) AS ?fB)
#         }}
#         FILTER ((?tA = ?fA) || (!BOUND(?tA) && !BOUND(?fA)))
#         FILTER ((?tB = ?fB) || (!BOUND(?tB) && !BOUND(?fB)))
#         FILTER (BOUND(?tA) || BOUND(?tB))
#     }}"""

#     queries = [query_link_fuzzy_bounds, query_final_event_time]
#     gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

#####################################################################################################################

# Construction of the evolution from states (versions) and events (changes)

def create_changes_for_versions_with_valid_time(graphdb_url:URIRef, repository_name:str, tmp_named_graph_uri:URIRef):
    """
    We create two changes for attribute versions which have a valid time (start and end time) :
    AttributeVersion(v) ^ Landmark(lm) ^ hasTime(lm, t) ^ hasAttribute(lm, attr) ^ hasAttributeVersion(attr, v) => AttributeChange(cgME) ^ AttributeChange(cgO) ^ makesEffective(cgME, v) ^ outdates(cgO, v)
    """

    # Create triples for real attribute changes (changes according factoids) : < ?change peg:isRealChange "true"^^xsd:boolean>
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?change peg:isRealChange "true"^^xsd:boolean.
        }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        ?rootAttr a peg:Attribute ; peg:hasTrace ?attr .
        ?change peg:appliedTo ?attr .
    }}
    """

    # Initialisation of changes and events of attribute versions with valid time
    # These resources are temporary and will be removed later
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?event a peg:Event ; peg:hasTime ?time .
            ?change a peg:AttributeChange ; peg:appliedTo ?attr ; peg:dependsOn ?event ; ?changeProp ?vers ; peg:isRealChange "false"^^xsd:boolean.
        }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        {{
            SELECT DISTINCT ?attr ?vers ?changeProp ?time WHERE {{
                VALUES (?changeProp ?propTime) {{ (peg:makesEffective peg:hasBeginning) (peg:outdates peg:hasEnd) }}
                GRAPH ?g {{ ?lm a peg:Landmark . }}
                ?lm peg:hasTime [?propTime ?time] ; peg:hasAttribute ?attr .
                ?attr peg:hasAttributeVersion ?vers .
                FILTER NOT EXISTS {{ ?change ?changeProp ?vers . }}
                ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean .
            }}
        }}
        BIND(URI(CONCAT(STR(URI(factoids:)), "CG_", STRUUID())) AS ?change)
        BIND(URI(CONCAT(STR(URI(factoids:)), "EV_", STRUUID())) AS ?event)
    }}
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


def get_elementary_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    gregorian_calendar_uri = URIRef("http://www.wikidata.org/entity/Q1985727")

    # Four step to get elementary changes : 
    # 1. For each attribute, create as many TimeDescription object as there are temporal values related to it
    # 2. For each attribute, detect duplicate time values and create a list of changes without doublons, each change is related to a unique value (which is a simplified time)
    # 3. Order changes temporally (according simplified time which is a double)
    # 4. Create fake changes (related to -inf and +inf temporal values)

    # For each attribute, create as many TimeDescription object as there are temporal values related to it
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?rootAttr peg:hasTimeDescription [a peg:TimeDescription ; peg:hasTimeElement ?rootTime ; peg:hasTimeProperty peg:hasTime ; peg:hasSimplifiedTime ?simplifiedTime ; peg:hasRelatedChange ?change ] .
        }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        BIND({gregorian_calendar_uri.n3()} AS ?timeCal)
        GRAPH ?gf {{ ?rootAttr a peg:Attribute . }}
        ?rootAttr peg:hasTrace ?attr .
        ?change a peg:AttributeChange ; peg:appliedTo ?attr ; peg:dependsOn [peg:hasTime ?time] .
        ?rootTime peg:hasTrace ?time ; peg:timeStamp ?timeStamp ; peg:timeCalendar ?timeCal .
        BIND(ofn:asDays(?timeStamp - "0001-01-01"^^xsd:dateTimeStamp) AS ?simplifiedTime)
        FILTER NOT EXISTS {{ ?rootAttr peg:hasTimeDescription [peg:hasRelatedChange ?change] }}
    }}
    """

    # For each attribute, detect duplicate time values and create a list of changes without doublons
    query2 =  np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?change a peg:AttributeChange ; peg:appliedTo ?attr ; peg:hasTimeDescription [a peg:TimeDescription ; peg:hasTimeProperty peg:hasTime ; peg:hasSimplifiedTime ?simplifiedTime] .
        }}
    }} WHERE {{
        {{
            SELECT DISTINCT ?gt ?attr ?simplifiedTime ?timeProperty WHERE {{
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                GRAPH ?gt {{ ?attr peg:hasTimeDescription [peg:hasSimplifiedTime ?simplifiedTime ; peg:hasTimeProperty ?timeProperty] }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI(factoids:)), "CG_", STRUUID())) AS ?change)
        }}
    """

    # Order changes
    query3 =  np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?cg peg:hasNextChange ?cgBis . }}
    }}
    WHERE {{
        {{
            SELECT ?gt ?attr ?cg (MIN(?diffTime) AS ?minDiffTime) WHERE {{
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?gt {{
                    ?cg peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime].
                    ?cgBis peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?stBis ; peg:hasTimeProperty peg:hasTime].
                }}
                BIND(?stBis - ?st AS ?diffTime)
                FILTER(!sameTerm(?cg, ?cgBis) && ?diffTime > 0)
            }}
            GROUP BY ?gt ?attr ?cg
        }}
        ?cg peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime].
        ?cgBis peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?stBis ; peg:hasTimeProperty peg:hasTime].
        FILTER(?stBis - ?st = ?minDiffTime)
    }}
    """

    # Create fake changes (related to -inf and +inf temporal values) 
    query4 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?newChange a peg:AttributeChange ; peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime] .
            ?prevChange peg:hasNextChange ?nextChange .
        }} 
    }} WHERE {{
        {{
            SELECT DISTINCT ?gt ?attr ?cg ?firstChangeMissing ?st WHERE {{
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?gf {{ ?attr a peg:Attribute . }}
                GRAPH ?gt {{ ?cg peg:appliedTo ?attr . }}
                {{
                    FILTER NOT EXISTS {{ ?cg peg:hasNextChange ?x }}
                    BIND("false"^^xsd:boolean AS ?firstChangeMissing)
                    BIND("INF"^^xsd:double AS ?st)
                }} UNION {{
                    FILTER NOT EXISTS {{ ?x peg:hasNextChange ?cg }}
                    BIND("true"^^xsd:boolean AS ?firstChangeMissing)
                    BIND("-INF"^^xsd:double AS ?st)
                }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI(factoids:)), "CG_", STRUUID())) AS ?newChange)
        BIND(IF(?firstChangeMissing, ?newChange, ?cg)  AS ?prevChange)
        BIND(IF(?firstChangeMissing, ?cg, ?newChange)  AS ?nextChange)
    }}
    """

    queries = [query1, query2, query3, query4]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)
    
def get_elementary_versions(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    # Create versions between two successive changes (one makes effective the version while the other outdates it)
    # Get an explicit triple to have successive changes (`?cg1 peg:hasNextChange ?cg2`)
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?attr peg:hasAttributeVersion ?vers .
            ?vers a peg:AttributeVersion .
            ?cg1 peg:makesEffective ?vers .
            ?cg2 peg:outdates ?vers .
        }}
    }} WHERE {{
        {{
            SELECT DISTINCT ?gt ?attr ?cg1 ?cg2 WHERE {{
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?gf {{ ?attr a peg:Attribute . }}
                GRAPH ?gt {{
                    ?cg1 peg:appliedTo ?attr .
                    ?cg2 peg:appliedTo ?attr .
                    ?cg1 peg:hasNextChange ?cg2 .
                }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI(factoids:)), "AV_", STRUUID())) AS ?vers)
    }}
    """

    # Order versions : hasNextVersion()
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?vO peg:hasNextVersion ?vME .
        }}
    }} WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?attr a peg:Attribute . }}
        ?cg peg:appliedTo ?attr ; peg:makesEffective ?vME ; peg:outdates ?vO .
    }}
    """

    query3 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{
            ?cg1 peg:precedes ?cg2 .
        }}
    }} WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        GRAPH ?gt {{
            ?cg1 peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?val1] .
            ?cg2 peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?val2] .
            FILTER(?val1 < ?val2)
        }}
    }}
    """

    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def get_elementary_change_traces(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    # Link existing attribute changes with created one when the are related
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?cg peg:derives ?cgTrace ; ?propTrace ?cgTrace. }}
    }} WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?attr a peg:Attribute . }}
        GRAPH ?gt {{
            ?cg peg:appliedTo ?attr ; peg:hasTimeDescription [peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime] .
            ?attr peg:hasTimeDescription [peg:hasSimplifiedTime ?st ; peg:hasRelatedChange ?cgTrace] .
        }}
        ?cgTrace a peg:AttributeChange ; peg:isRealChange ?realChange .
        BIND(IF(?realChange, peg:hasTrace, peg:derives) AS ?propTrace)
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

# def get_elementary_version_traces(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):

#     # Link existing attribute versions related to changes with created one when the are related :
#     # * peg:makesEffective(cg, v) ^ peg:makesEffective(cgTrace, vTrace) ^ peg:hasTrace(cg, cgTrace) => peg:hasTrace(v, vTrace)
#     # * peg:outdates(cg, v) ^ peg:outdates(cgTrace, vTrace) ^ peg:hasTrace(cg, cgTrace) => peg:hasTrace(v, vTrace)
#     query1 = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gt {{ ?vers peg:hasTrace ?versTrace . }}
#     }}
#     WHERE {{
#         BIND({tmp_named_graph_uri.n3()} AS ?gt)
#         BIND({facts_named_graph_uri.n3()} AS ?gf)
#         GRAPH ?gf {{ ?attr a peg:Attribute . }}
#         ?cgTrace ?changeProp ?versTrace .
#         GRAPH ?gt {{
#             VALUES ?changeProp {{ peg:makesEffective peg:outdates }}
#             ?cg a peg:AttributeChange ; peg:appliedTo ?attr ; peg:hasTrace ?cgTrace ; ?changeProp ?vers.
#         }}
#     }}
#     """

#     # Get traces for elementary versions which are not already traced
#     # If hasTrace(vi, vTrace) ^ hasTrace(vj, vTrace) ^ vk is between vi and vj => hasTrace(vk, vTrace)
#     query2 = np.query_prefixes + f"""
#     INSERT {{
#         GRAPH ?gt {{ ?vers peg:hasTrace ?vTrace . }}
#         }}
#     WHERE {{
#         BIND({tmp_named_graph_uri.n3()} AS ?gt)
#         BIND({facts_named_graph_uri.n3()} AS ?gf)
#         GRAPH ?gf {{ ?attr a peg:Attribute . }}
#         ?attr peg:hasAttributeVersion ?vers .
#         GRAPH ?gt {{
#             ?cgME peg:makesEffective ?vers .
#             ?cgO peg:outdates ?vers .
#             {{ ?cgStart peg:hasNextChange+ ?cgME }} UNION {{ BIND(?cgME AS ?cgStart) }}
#             {{ ?cgO peg:hasNextChange+ ?cgEnd }} UNION {{ BIND(?cgO AS ?cgEnd) }}
#             ?cgStart peg:derives ?cgMEVTrace .
#             ?cgEnd peg:derives ?cgOVTrace .
#         }}
#         ?cgMEVTrace peg:makesEffective ?vTrace .
#         ?cgOVTrace peg:outdates ?vTrace .
#     }}
#     """

#     queries = [query1, query2]
#     for query in queries:
#         gd.run_update_query(query, graphdb_url, repository_name)

def get_elementary_version_traces(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    # Link existing attribute versions related to changes with created one when the are related :
    # * peg:makesEffective(cg, v) ^ peg:makesEffective(cgTrace, vTrace) ^ peg:hasTrace(cg, cgTrace) => peg:hasTrace(v, vTrace)
    # * peg:outdates(cg, v) ^ peg:outdates(cgTrace, vTrace) ^ peg:hasTrace(cg, cgTrace) => peg:hasTrace(v, vTrace)
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?vers peg:hasTrace ?versTrace . }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?attr a peg:Attribute . }}
        ?cgTrace ?changeProp ?versTrace .
        GRAPH ?gt {{
            VALUES ?changeProp {{ peg:makesEffective peg:outdates }}
            ?cg a peg:AttributeChange ; peg:appliedTo ?attr ; peg:hasTrace ?cgTrace ; ?changeProp ?vers.
        }}
    }}
    """

    # Get traces for elementary versions which are not already traced
    # If hasTrace(vi, vTrace) ^ hasTrace(vj, vTrace) ^ vk is between vi and vj => hasTrace(vk, vTrace)
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?vers peg:hasTrace ?vTrace . }}
        }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?attr a peg:Attribute . }}
        ?attr peg:hasAttributeVersion ?vers .
        GRAPH ?gt {{
            ?cgME peg:makesEffective ?vers .
            ?cgO peg:outdates ?vers .
            {{ ?cgStart peg:precedes ?cgME }} UNION {{ BIND(?cgME AS ?cgStart) }}
            {{ ?cgO peg:precedes ?cgEnd }} UNION {{ BIND(?cgO AS ?cgEnd) }}
            ?cgStart peg:derives ?cgMEVTrace .
            ?cgEnd peg:derives ?cgOVTrace .
        }}
        ?cgMEVTrace peg:makesEffective ?vTrace .
        ?cgOVTrace peg:outdates ?vTrace .
    }}
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def get_elementary_versions_and_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    create_changes_for_versions_with_valid_time(graphdb_url, repository_name, tmp_named_graph_uri)
    get_elementary_changes(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    get_elementary_versions(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    get_elementary_change_traces(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    get_elementary_version_traces(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)

    
def remove_empty_attribute_versions(graphdb_url:URIRef, repository_name:str, tmp_named_graph_uri:URIRef):
    """
    Remove empty attribute versions, ie versions which don't have any trace (∄ ?version peg:hasTrace ?versionTrace), excepted if this version is made effective AND outdated by two changes which have traces.
    Let's take a version named ?version. ∃ (?changeME, ?changeO), ?changeME peg:makesEffective ?version && ∄ ?changeO peg:hasTrace ?version.
    If ∄ ?version peg:hasTrace ?versionTrace:
    * (a) if ∃ (?changeMETrace, ?changeOTrace), ?changeME peg:hasTrace ?changeMETrace && ?changeO peg:hasTrace ?changeOTrace -> ø
    * (b) if ∃ ?changeME, ?changeME peg:hasTrace ?changeMETrace && ∄ ?changeO, ?changeO peg:hasTrace ?changeOTrace -> remove ?version and ?changeO
    * (c) if ∄ ?changeME, ?changeME peg:hasTrace ?changeMETrace && ∃ ?changeO, ?changeO peg:hasTrace ?changeOTrace -> remove ?version and ?changeME
    * (d) if ∄ ?changeME, ?changeME peg:hasTrace ?changeMETrace && ∄ ?changeO, ?changeO peg:hasTrace ?changeOTrace -> remove ?version, ?changeME and ?changeO

    The subquery selects all the empty versions to be removed and get their related changes.
    ?hasChangeMETrace and ?hasChangeOTrace are boolean to know if these changes have traces for the query to know which case the version belongs to (a, b, c or d).
    """

    query1 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gt {{
                ?toRemoveChangeME peg:toRemove "true"^^xsd:boolean .
                ?toRemoveChangeO peg:toRemove "true"^^xsd:boolean .
                ?version peg:toRemove "true"^^xsd:boolean .
                ?change a peg:AttributeChange ; peg:appliedTo ?attr ; peg:makesEffective ?vME ; peg:outdates ?vO.
                ?change peg:hasTimeDescription [peg:hasSimplifiedTime ?stME ; peg:hasTimeProperty peg:hasTimeAfter ] , [peg:hasSimplifiedTime ?stO ; peg:hasTimeProperty peg:hasTimeBefore ]
                }}
        }}
        WHERE {{
            {{
                SELECT DISTINCT ?gt ?attr ?version ?changeME ?changeO ?hasChangeMETrace ?hasChangeOTrace WHERE {{
                    BIND({tmp_named_graph_uri.n3()} AS ?gt)
                    GRAPH ?gt {{
                        ?attr peg:hasAttributeVersion ?version .
                        ?version a peg:AttributeVersion .
                        ?changeME a peg:AttributeChange ; peg:makesEffective ?version .
                        ?changeO a peg:AttributeChange ; peg:outdates ?version .
                    }}
                    FILTER NOT EXISTS {{ ?version peg:hasTrace ?versionTrace . }}
                    OPTIONAL {{ ?changeME peg:hasTrace ?changeMETrace . }}
                    OPTIONAL {{ ?changeO peg:hasTrace ?changeOTrace . }}
                    BIND(IF(BOUND(?changeMETrace), "true"^^xsd:boolean, "false"^^xsd:boolean) AS ?hasChangeMETrace)
                    BIND(IF(BOUND(?changeOTrace), "true"^^xsd:boolean, "false"^^xsd:boolean) AS ?hasChangeOTrace)
                    FILTER(!(?hasChangeMETrace && ?hasChangeOTrace))
                }} 
            }}

            BIND(URI(CONCAT(STR(URI(factoids:)), "CG_", STRUUID())) AS ?newChange)
            BIND(IF(!?hasChangeMETrace && !?hasChangeOTrace, ?newChange, IF(!?hasChangeMETrace, ?changeO, ?changeME)) AS ?change)

            OPTIONAL {{
                ?changeME peg:hasTimeDescription [peg:hasSimplifiedTime ?stME ; peg:hasTimeProperty peg:hasTime ] .
                FILTER(!?hasChangeMETrace)
            }}
            OPTIONAL {{
                ?changeO peg:hasTimeDescription [peg:hasSimplifiedTime ?stO ; peg:hasTimeProperty peg:hasTime ] .
                FILTER(!?hasChangeOTrace)
            }}
            OPTIONAL {{
                ?changeO peg:makesEffective ?vME .
                FILTER(!?hasChangeOTrace)
            }}
            OPTIONAL {{
                ?changeME peg:outdates ?vO .
                FILTER(!?hasChangeMETrace)
            }}
            OPTIONAL {{
                BIND(?changeME AS ?toRemoveChangeME)
                FILTER(!?hasChangeMETrace)
            }}
            OPTIONAL {{
                BIND(?changeO AS ?toRemoveChangeO)
                FILTER(!?hasChangeOTrace)
            }}
        }}
        """
    
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?changeME peg:hasNextChange ?changeO . }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        GRAPH ?gt {{
            ?attr peg:hasAttributeVersion ?version .
            ?version a peg:AttributeVersion .
            ?changeME a peg:AttributeChange ; peg:makesEffective ?version .
            ?changeO a peg:AttributeChange ; peg:outdates ?version .
        }}
    }} 
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

    # Remove all triples where resources r for which it exists a triple <r peg:toRemove "true"^^xsd:boolean> is in these triples
    # In this case, remove selected versions and their related changes which are not traced
    msp.remove_all_triples_for_resources_to_remove(graphdb_url, repository_name)

# Get attribute versions to merge
def to_be_merged_with(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Get attribute versions to merge :
    * a version has to be merged with itself ;
    * if an untraced change (a change ?cg such as ∄ ?cg peg:hasTrace ?cgTrace) makesEffective ?vME, outdates ?vO and ?vME has same version value as ?vO then ?vME has to be merged with ?vO
    * transitivity: if v1 peg:toBeMergedWith v2 and v2 peg:toBeMergedWith v3 then v1 peg:toBeMergedWith v3.
    
    """
  
    # query1 = np.query_prefixes + f"""
    #     INSERT {{
    #         GRAPH ?gt {{
    #             ?vers peg:toBeMergedWith ?vers .
    #         }}
    #     }} WHERE {{
    #         BIND({tmp_named_graph_uri.n3()} AS ?gt)
    #         GRAPH ?gt {{ ?vers a peg:AttributeVersion . }}
    #     }}
    # """

    # query2 = np.query_prefixes + f"""
    # INSERT {{
    #     GRAPH ?gt {{
    #         ?vME peg:toBeMergedWith ?vO .
    #         ?vO peg:toBeMergedWith ?vME . 
    #     }}
    # }}
    # WHERE {{
    #     BIND({tmp_named_graph_uri.n3()} AS ?gt)
    #     ?change a peg:AttributeChange ; peg:makesEffective ?vME ; peg:outdates ?vO .
    #     FILTER NOT EXISTS {{ ?change peg:hasTrace ?changeTrace . }}
    #     ?vME peg:hasTrace ?vMETrace .
    #     ?vO peg:hasTrace ?vOTrace .
    #     {{ ?vMETrace peg:sameVersionValueAs ?vOTrace . }} UNION {{ FILTER(sameTerm(?vMETrace, ?vOTrace)) }}
    #     MINUS {{
    #         ?vME peg:hasTrace ?vMETrace2 .
    #         ?vO peg:hasTrace ?vOTrace2 .
    #         ?vMETrace2 peg:differentVersionValueFrom ?vOTrace2 .
    #     }}
    # }}
    # """

    # # Aggregation of successive versions with similar values (in several queries)
    # # Add triples indicating similarity (peg:toBeMergedWith) with successive versions that have similar values (peg:hasNextVersion or peg:hasOverlappingVersion)
    # # If v1 peg:toBeMergedWith v2 and v2 peg:toBeMergedWith v3 then v1 peg:toBeMergedWith v3.
    # query3 = np.query_prefixes + f"""
    #     INSERT {{
    #         GRAPH ?gt {{ ?attrVers1 peg:toBeMergedWith ?attrVers2 . }}
    #     }} WHERE {{
    #         BIND({tmp_named_graph_uri.n3()} AS ?gt)
    #         ?attrVers1 peg:toBeMergedWith+ ?attrVers2 .
    #     }}
    # """

    # queries = [query1, query2, query3]
    
    # # ################################## Test part ######################################

    # Define if two consecutive versions has to be merged
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?vME peg:toBeMergedWith ?vO . }}
    }}
    WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        GRAPH ?gt {{
            ?change a peg:AttributeChange ; peg:makesEffective ?vME ; peg:outdates ?vO .
        }}
        FILTER NOT EXISTS {{ ?change peg:hasTrace ?changeTrace . }}
        ?vME peg:hasTrace ?vMETrace .
        ?vO peg:hasTrace ?vOTrace .
        {{ ?vMETrace peg:sameVersionValueAs ?vOTrace . }} UNION {{ FILTER(sameTerm(?vMETrace, ?vOTrace)) }}
        MINUS {{
            ?vME peg:hasTrace ?vMETrace2 .
            ?vO peg:hasTrace ?vOTrace2 .
            ?vMETrace2 peg:differentVersionValueFrom ?vOTrace2 .
        }}
    }}
    """

    # Aggregation of successive versions with similar values (in several queries)
    # Add triples indicating similarity (peg:toBeMergedWith) with successive versions that have similar values (peg:hasNextVersion or peg:hasOverlappingVersion)
    # If v1 peg:toBeMergedWith v2 and v2 peg:toBeMergedWith v3 then v1 peg:toBeMergedWith v3.
    query2 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gt {{ ?attrVers1 peg:toBeMergedWith ?attrVers2 . }}
        }} WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            ?attrVers1 peg:toBeMergedWith+ ?attrVers2 .
        }}
    """

    # Reflexivity of the peg:toBeMergedWith property
    query3 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?vers2 peg:toBeMergedWith ?vers1 . }}
    }} WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        ?vers1 peg:toBeMergedWith ?vers2 .
    }}
    """

    # A version has to be merged with itself 
    query4 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gt {{ ?vers peg:toBeMergedWith ?vers . }}
        }} WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            GRAPH ?gt {{ ?vers a peg:AttributeVersion . }}
            ?rootAttr a peg:Attribute ; peg:hasAttributeVersion ?vers .
        }}
    """

    queries = [query1, query2, query3, query4]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


def merge_attribute_versions_to_be_merged(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    It may be more than two versions are similar to each other. To detect all the similar versions, we will associate them with a mergedVal constructed from the URIs of the similar versions.
    So if v1 is similar to v2, v3 and v4, the mergedVal will be ‘uriV1;uriV2;uriV3;uriV4’ where uriVi is the URI of version i. v2, v3 and v4 will have the same mergedVal.
    Triple created will then be <v1 peg:hasMergedVal ‘uriV1;uriV2;uriV3;uriV4’>.
    This step is done with `query3`.
    """
    
    # For each version, we create a value (versMergeVal) which is the fusion of the URIs of versions that are similar.
    query1 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gt {{ ?vers1 peg:versMergeVal ?versMergeVal }}
        }} WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            {{
                SELECT ?vers1 (GROUP_CONCAT(STR(?vers2) ; separator="|") as ?versMergeVal) WHERE {{
                    ?vers1 peg:toBeMergedWith ?vers2 .
                }}
                GROUP BY ?vers1 ORDER BY ?vers2
            }}
        }}
    """

    # Creation of merged attribute versions
    query2 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gf {{
                ?attr peg:hasAttributeVersion ?rootAttrVers .
                ?rootAttrVers a peg:AttributeVersion .
            }}
            GRAPH ?gt {{
                ?rootAttrVers peg:derives ?attrVers .
            }}
        }}
        WHERE {{
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "AV_", STRUUID())) AS ?rootAttrVers)
            {{
                SELECT DISTINCT ?gt ?versMergeVal WHERE {{
                    BIND({tmp_named_graph_uri.n3()} AS ?gt)
                    GRAPH ?gt {{
                        ?attrVers a peg:AttributeVersion ; peg:versMergeVal ?versMergeVal .
                    }}
                }}
            }}
            ?attr peg:hasAttributeVersion ?attrVers .
            ?attrVers peg:versMergeVal ?versMergeVal .
        }}
        """
    

    # Creation of changes between consecutive merged attribute versions
    query3 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?gf {{
                ?newChange a peg:AttributeChange ; peg:appliedTo ?attr ; peg:makesEffective ?vME ; peg:outdates ?vO .
            }}
            GRAPH ?gt {{
                ?newChange peg:derives ?change .
            }}
        }}
        WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            {{
                SELECT * WHERE {{
                    BIND({facts_named_graph_uri.n3()} AS ?gf)
                    ?change a peg:AttributeChange .
                    {{
                        ?change peg:makesEffective ?vMETrace ; peg:outdates ?vOTrace .
                        ?vME peg:derives ?vMETrace .
                        ?vO peg:derives ?vOTrace .
                        FILTER(!sameTerm(?vME, ?vO))
                    }} UNION {{
                        ?change peg:makesEffective ?vMETrace .
                        ?vME peg:derives ?vMETrace .
                        FILTER NOT EXISTS {{ ?change peg:outdates ?vOTrace . }}
                    }} UNION {{
                        ?change peg:outdates ?vOTrace .
                        ?vO peg:derives ?vOTrace .
                        FILTER NOT EXISTS {{ ?change peg:makesEffective ?vMETrace . }}
                    }}
                }}
            }}
            ?change peg:appliedTo ?attr .
            BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "CG_", STRUUID())) AS ?newChange)
        }}
        """

    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


def merge_similar_successive_attribute_versions(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    to_be_merged_with(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri)
    merge_attribute_versions_to_be_merged(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri)
    

def create_events_and_times_from_attribute_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?event a peg:Event .
            ?change peg:dependsOn ?event .
        }} 
    }}
    WHERE {{
        {{
            SELECT DISTINCT * WHERE {{
                BIND ({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?gf {{
                    ?change peg:appliedTo ?attr .
                    ?attr a peg:Attribute .
                    FILTER NOT EXISTS {{ ?change peg:dependsOn ?event . }}
                }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "EV_", STRUUID())) AS ?event)
    }} 
    """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{ ?event ?propTime ?time }}
    }}
    WHERE {{
        BIND ({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{
            ?change peg:appliedTo ?attr ; peg:dependsOn ?event .
            ?attr a peg:Attribute .
            ?time a ?timeClass .
        }}
        ?change peg:derives ?derivedCg .
        {{
            VALUES ?propTime {{ peg:hasTime }}
            ?derivedCg peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ; peg:hasTimeProperty ?propTime ].
            ?attr peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime ; peg:hasTimeElement ?time ].
        }} UNION {{
            ?derivedCg peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ; peg:hasTimeProperty ?propTime ].
            FILTER NOT EXISTS {{ ?derivedCg peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime ]. }}
            ?attr peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ; peg:hasTimeProperty peg:hasTime ; peg:hasTimeElement ?time ].
        }}
    }}
    """

    # if facts_named_graph_uri.n3() == "<http://localhost:7200/repositories/addresses_from_factoids/rdf-graphs/facts_with_fragmentary_sn_states>":
    #     queries = [query1, query2]
    #     for query in queries:
    #         gd.run_update_query(query, graphdb_url, repository_name)

    #     print("----")
    #     print(0/0)

    #     query2 = np.query_prefixes + f"""
    #     INSERT {{
    #         GRAPH ?gf {{ ?event peg:hasTime ?time }}
    #     }}
    #     WHERE {{
    #         BIND ({facts_named_graph_uri.n3()} AS ?gf)

    #         GRAPH ?gf {{
    #             ?change peg:appliedTo ?attr ; peg:dependsOn ?event .
    #             ?attr a peg:Attribute .
    #             ?time a ?timeClass .
    #         }}

    #         ?change peg:derives ?derivedCg .

    #         ?derivedCg peg:hasTimeDescription [ peg:hasSimplifiedTime ?st ].

    #         ?attr peg:hasTimeDescription [ 
    #             peg:hasSimplifiedTime ?st ;
    #             peg:hasTimeProperty peg:hasTime ;
    #             peg:hasTimeElement ?time
    #         ].
    #     }}
    # """

    query3 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gi {{ ?version peg:hasTrace ?versionTrace . }}
    }}
    WHERE {{
        BIND ({facts_named_graph_uri.n3()} AS ?gf)
        BIND ({inter_sources_name_graph_uri.n3()} AS ?gi)
        GRAPH ?gf {{
            ?version a peg:AttributeVersion .
        }}
        ?version peg:derives [ peg:hasTrace ?versionTrace ] .
    }}
    """

    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def get_attribute_version_evolution_from_elementary_elements(graphdb_url:URIRef, repository_name:str,
                                                             facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    
    # First step : remove empty attribute versions : remove untraced versions if there are related at least to one untraced change 
    remove_empty_attribute_versions(graphdb_url, repository_name, tmp_named_graph_uri)

    # Merge similar successive versions if they have similar values
    merge_similar_successive_attribute_versions(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri)
    
    # For all changes which are in facts named graph, link it to an event which has to have a time
    # <event peg:hasTime time> if possible, then <event peg:hasTimeBefore beforeTime> and/or <event peg:hasTimeAfter afterTime>
    create_events_and_times_from_attribute_changes(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri)

    # Transfer factoid information to facts
    rt.transfer_elements_to_roots(graphdb_url, repository_name, facts_named_graph_uri)


#################################################################################################

def transform_event_bounds_to_fuzzy_times(graphdb_url, repository_name, facts_named_graph_uri):
    """
    Transforme les bornes temporelles (hasTimeBefore/After) en instances 
    FuzzyTimeInstant et lie les événements via peg:hasTime.
    """
    
    # 1. Créer les instances FuzzyTimeInstant manquantes
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?finalTime a peg:FuzzyTimeInstant ; 
                       peg:hasFuzzyBeginning ?tAfter ; 
                       peg:hasFuzzyEnd ?tBefore .
        }}
    }}
    WHERE {{
        {{
            SELECT DISTINCT ?gf ?time ?tAfter ?tBefore WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                GRAPH ?gf {{ 
                    ?ev a peg:Event .
                    OPTIONAL {{ ?ev peg:hasTimeBefore ?tBefore . }}
                    OPTIONAL {{ ?ev peg:hasTimeAfter ?tAfter . }}

                    FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }}
                    FILTER (BOUND(?tBefore) || BOUND(?tAfter))

                    OPTIONAL {{
                        ?time a peg:FuzzyTimeInstant .
                        OPTIONAL {{ ?time peg:hasFuzzyBeginning ?tAfterFuzzy . }}
                        OPTIONAL {{ ?time peg:hasFuzzyEnd ?tBeforeFuzzy . }}

                        FILTER (
                            ( (!BOUND(?tAfter) && !BOUND(?tAfterFuzzy)) || (sameterm(?tAfter, ?tAfterFuzzy)) ) &&
                            ( (!BOUND(?tBefore) && !BOUND(?tBeforeFuzzy)) || (sameterm(?tBefore, ?tBeforeFuzzy)) )
                        )
                    }}
                }}
            }}
        }}
        # On ne crée un URI que si ?time n'existe pas déjà
        BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "FuzzyTimeInstant/", STRUUID())) AS ?generatedTime)
        BIND(COALESCE(?time, ?generatedTime) AS ?finalTime)
    }}
    """

    # 2. Associer les événements à leur FuzzyTimeInstant (existant ou nouveau)
    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{ ?ev peg:hasTime ?finalTime . }}
    }}
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ 
            ?ev a peg:Event .
            OPTIONAL {{ ?ev peg:hasTimeBefore ?tBefore . }}
            OPTIONAL {{ ?ev peg:hasTimeAfter ?tAfter . }}

            FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }}
            FILTER (BOUND(?tBefore) || BOUND(?tAfter))

            # On retrouve le FuzzyTimeInstant correspondant (forcément présent grâce à query1)
            ?finalTime a peg:FuzzyTimeInstant .
            OPTIONAL {{ ?finalTime peg:hasFuzzyBeginning ?tAfterFuzzy . }}
            OPTIONAL {{ ?finalTime peg:hasFuzzyEnd ?tBeforeFuzzy . }}

            FILTER (
                ( (!BOUND(?tAfter) && !BOUND(?tAfterFuzzy)) || (sameterm(?tAfter, ?tAfterFuzzy)) ) &&
                ( (!BOUND(?tBefore) && !BOUND(?tBeforeFuzzy)) || (sameterm(?tBefore, ?tBeforeFuzzy)) )
            )
        }}
    }}
    """

    # 3. Supprimer les anciennes propriétés de bornes devenues redondantes
    query3 = np.query_prefixes + f"""
    DELETE {{
        GRAPH ?gf {{ ?ev ?propTime ?timeToRemove . }}
    }}
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        VALUES ?propTime {{ peg:hasTimeBefore peg:hasTimeAfter }}
        GRAPH ?gf {{ 
            ?ev a peg:Event ; 
                peg:hasTime ?x ; 
                ?propTime ?timeToRemove . 
        }}
    }}
    """

    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)