import re
import datetime
from rdflib import Literal, URIRef
from rdflib.namespace import XSD
from scripts.graph_construction.namespaces import NameSpaces, OntologyMapping
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import graphrdf as gr
from convertdate import french_republican, gregorian, islamic, hebrew, julian

np = NameSpaces()
om = OntologyMapping()

def get_standardized_date(timestamp_str: str, cal: URIRef, precision: URIRef) -> str:
    """
    Get a standardized date in ISO 8601 format (string) from a date given in a specific calendar and with a specific precision.
    :param timestamp_str: Date with format "YYYY-MM-DDTHH:mm:ssZ" (ISO 8601)
    :param cal: URI of the calendar ('republican', 'julian', 'hebrew', etc.)
    :param precision: URIRef of the temporal precision (day, month, year, decade, century, millenium)
    :return: String of the standardized date in ISO 8601 format
    """
    
    # 1. Convert the date from the given calendar to the Gregorian calendar (ISO 8601 format)
    iso_greg = date_from_cal_to_gregorian(timestamp_str, cal)
    
    # 2. Format the ISO date according to the given precision URIRef
    std_date = format_date_by_uri_precision(iso_greg, precision)

    return std_date

def date_from_cal_to_gregorian(timestamp_str: str, from_cal: URIRef) -> str:
    """
    Convertit a date from a given calendar to the Gregorian calendar in ISO 8601 format.
    
    :param timestamp_str: Date with format "YYYY-MM-DDTHH:mm:ssZ" (ISO 8601)
    :param from_cal: URI of the calendar ('republican', 'julian', 'hebrew', etc.)
    :return: String of the date in the Gregorian calendar (ISO 8601)
    """
    
    # 1. Parse the input timestamp string to extract year, month, day, hour, minute, second, microsecond
    # We manage the case with or without milliseconds
    try:
        dt = datetime.datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Fallback for special case of timestamps ending with 'Z' and without milliseconds
        dt = datetime.datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%SZ")

    year, month, day = dt.year, dt.month, dt.day
    
    # 2. Convert the date from the source calendar to the Julian calendar
    # We select the appropriate converter based on the from_cal URIRef
    cal_map = {
        np.WD["Q181974"]: french_republican,
        np.WD["Q1985786"]: julian,
        np.WD["Q44722"]: hebrew,
        np.WD["Q28892"]: islamic,
        np.WD["Q1985727"]: gregorian
    }
    
    if from_cal not in cal_map:
        raise ValueError(f"Calendar'{from_cal.n3()}' not supported.")
    
    converter = cal_map[from_cal]
    
    # Convert towards the appropriate calendar's date tuple (year, month, day) and then to JD
    jd = converter.to_jd(year, month, day)
    
    # 3. Convert from Julian Day to Gregorian date
    greg_tuple = gregorian.from_jd(jd) # Retourne (year, month, day)
    
    # 4. Reconstruction du timestamp ISO (en conservant l'heure d'origine)
    greg_dt = datetime.datetime(
        year=greg_tuple[0], 
        month=greg_tuple[1], 
        day=greg_tuple[2],
        hour=dt.hour, 
        minute=dt.minute, 
        second=dt.second, 
        microsecond=dt.microsecond
    )
    
    return greg_dt.isoformat()

def format_date_by_uri_precision(iso_date: str, precision_uri: URIRef) -> str:
    """
    Format a date in ISO 8601 format according to a temporal precision URIRef.
    """

    # 1. Dictionary mapping URIRef to internal key (Adapted according to your self.time_units structure)
    uri_to_key = {
        np.TIME["unitDay"]: "day",
        np.TIME["unitMonth"]: "month",
        np.TIME["unitYear"]: "year",
        np.TIME["unitDecade"]: "decenium",
        np.TIME["unitCentury"]: "century",
        np.TIME["unitMillenium"]: "millenium"
    }

    precision = uri_to_key.get(precision_uri)
    if not precision:
        raise ValueError(f"URIRef de précision non supporté : {precision_uri}")

    # 2. Extraction via Regex (gestion des dates négatives et des années > 4 chiffres)
    import re
    match = re.match(r"(-?\d{4,})-(\d{2})-(\d{2})", iso_date)
    if not match:
        raise ValueError("Format ISO invalide. Attendu: YYYY-MM-DD ou -YYYY-MM-DD")
    
    year_str, month, day = match.groups()
    is_negative = year_str.startswith('-')
    abs_year = year_str.lstrip('-')

    # 3. Logic for truncation based on precision
    if precision == "millenium":
        res = abs_year[:-3] if len(abs_year) > 3 else "0"
        formatted_year = f"-{res}" if is_negative and res != "0" else res
        return formatted_year

    elif precision == "century":
        res = abs_year[:-2] if len(abs_year) > 2 else "0"
        formatted_year = f"-{res}" if is_negative and res != "0" else res
        return formatted_year

    elif precision == "decenium":
        res = abs_year[:-1] if len(abs_year) > 1 else "0"
        formatted_year = f"-{res}" if is_negative and res != "0" else res
        return formatted_year

    elif precision == "year":
        return year_str

    elif precision == "month":
        return f"{year_str}-{month}"

    elif precision == "day":
        return f"{year_str}-{month}-{day}"


def get_query_to_compare_time_instants(time_named_graph_uri:URIRef, time_instant_select_conditions:str):
    """"
    `time_instant_select_conditions` defines conditions to select two instants which have to be compared : ?ti1 and ?ti2
    """
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?g {{
            ?ti1 ?timeProp ?ti2 .
            ?ti1 ?precSameTime ?ti2 .

        }}
    }}
    WHERE {{
        BIND ({time_named_graph_uri.n3()} AS ?g)
        {{
            SELECT DISTINCT ?ti1 ?ti2 ?ts1 ?ts2 ?tp1 ?tp2 ?tc WHERE {{
                {time_instant_select_conditions}

                ?ti1 a peg:CrispTimeInstant; peg:timeStamp ?ts1; peg:timeCalendar ?tc; peg:timePrecision ?tp1.
                ?ti2 a peg:CrispTimeInstant; peg:timeStamp ?ts2; peg:timeCalendar ?tc; peg:timePrecision ?tp2.

                FILTER (?ti1 != ?ti2)
                FILTER(?ts1 <= ?ts2)

                MINUS {{
                    ?ti1 ?p ?ti2 .
                    FILTER(?p IN (peg:instantSameTime, peg:instantBefore, peg:instantAfter))
                }}
            }}
        }}


        BIND(YEAR(?ts1) = YEAR(?ts2) AS ?sameYear)
        BIND(MONTH(?ts1) = MONTH(?ts2) AS ?sameMonth)
        BIND(DAY(?ts1) = DAY(?ts2) AS ?sameDay)

        BIND(IF(time:unitMillenium in (?tp1, ?tp2), FLOOR(YEAR(?ts1)/1000) = FLOOR(YEAR(?ts2)/1000),
                IF(time:unitCentury in (?tp1, ?tp2), FLOOR(YEAR(?ts1)/100) = FLOOR(YEAR(?ts2)/100),
                    IF(time:unitDecade in (?tp1, ?tp2), FLOOR(YEAR(?ts1)/10) = FLOOR(YEAR(?ts2)/10),
                        IF(time:unitYear in (?tp1, ?tp2), ?sameYear,
                            IF(time:unitMonth in (?tp1, ?tp2), ?sameYear && ?sameMonth,
                                IF(time:unitDay in (?tp1, ?tp2), ?sameYear && ?sameMonth && ?sameDay,
                                    "false"^^xsd:boolean)
                            ))))) AS ?sameTime)

        BIND(IF(?tp1 = time:unitMillenium, "1"^^xsd:integer, 
                IF(?tp1 = time:unitCentury, "2"^^xsd:integer,
                    IF(?tp1 = time:unitDecade, "3"^^xsd:integer,
                        IF(?tp1 = time:unitYear, "4"^^xsd:integer,
                            IF(?tp1 = time:unitMonth, "5"^^xsd:integer,
                                IF(?tp1 = time:unitDay, "6"^^xsd:integer,
                                    "0"^^xsd:integer)
                            ))))) AS ?ti1prec)

        BIND(IF(?tp2 = time:unitMillenium, "1"^^xsd:integer, 
                IF(?tp2 = time:unitCentury, "2"^^xsd:integer,
                    IF(?tp2 = time:unitDecade, "3"^^xsd:integer,
                        IF(?tp2 = time:unitYear, "4"^^xsd:integer,
                            IF(?tp2 = time:unitMonth, "5"^^xsd:integer,
                                IF(?tp2 = time:unitDay, "6"^^xsd:integer,
                                    "0"^^xsd:integer)
                            ))))) AS ?ti2prec)

        BIND(IF(?ti1prec > ?ti2prec, peg:instantLessPreciseThan, 
                IF(?ti1prec < ?ti2prec, peg:instantMorePreciseThan, peg:instantAsPreciseAs
                )) AS ?precisonPred)
                
        OPTIONAL {{
            FILTER(?sameTime)
            BIND(?precisonPred AS ?precSameTime)
        }}

        BIND(IF(?sameTime, peg:instantSameTime, peg:instantBefore) AS ?timeProp)
    }}
    """

    return query

def get_query_to_compare_time_intervals(time_named_graph_uri:URIRef, time_interval_select_conditions:str):
    """
    Compare time intervals according Allen algebra
    """
    
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalBefore ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg .
        ?i1end peg:instantBefore ?i2beg .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalMeets ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg .
        ?i1end peg:instantSameTime ?i2beg .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalOverlaps ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasBeginning ?i1beg ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg ; peg:hasEnd ?i2end .
        ?i1beg peg:instantBefore ?i2beg .
        ?i1end peg:instantAfter ?i2beg .
        ?i1end peg:instantBefore ?i2end .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalStarts ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasBeginning ?i1beg ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg ; peg:hasEnd ?i2end .
        ?i1beg peg:instantSameTime ?i2beg .
        ?i1end peg:instantBefore ?i2end .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalDuring ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasBeginning ?i1beg ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg ; peg:hasEnd ?i2end .
        ?i1beg peg:instantAfter ?i2beg .
        ?i1end peg:instantBefore ?i2end .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalFinishes ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasBeginning ?i1beg ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg ; peg:hasEnd ?i2end .
        ?i1beg peg:instantAfter ?i2beg .
        ?i1end peg:instantSameTime ?i2end .
    }} ;

    INSERT {{
        GRAPH ?g {{
            ?i1 time:intervalEquals ?i2
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        {time_interval_select_conditions}
        
        ?i1 a peg:CrispTimeInterval ; peg:hasBeginning ?i1beg ; peg:hasEnd ?i1end .
        ?i2 a peg:CrispTimeInterval ; peg:hasBeginning ?i2beg ; peg:hasEnd ?i2end .
        ?i1beg peg:instantSameTime ?i2beg .
        ?i1end peg:instantSameTime ?i2end .
    }}
    """

    return query

def compare_time_instants_of_events_from_traces(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    """
    Sort all time instants related to events which are a trace of one event.
    """
    
    time_instant_select_conditions = """
        ?ev a peg:Event ; peg:hasTrace [?tpred1 ?ti1] ; [?tpred2 ?ti2] .
        FILTER(?tpred1 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
        FILTER(?tpred2 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
    """

    query = get_query_to_compare_time_instants(time_named_graph_uri, time_instant_select_conditions)

    gd.run_update_query(query, graphdb_url, repository_name)

def compare_time_instants_of_events(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    """
    Sort all time instants related to one event.
    """
    
    time_instant_select_conditions = """
        ?ev a peg:Event ; ?tpred1 ?ti1 ; ?tpred2 ?ti2 .
        FILTER(?tpred1 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
        FILTER(?tpred2 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
    """

    query = get_query_to_compare_time_instants(time_named_graph_uri, time_instant_select_conditions)

    gd.run_update_query(query, graphdb_url, repository_name)

def compare_time_instants_of_attributes(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    """
    Sort all time instants related to one attribute.
    """
    
    time_instant_select_conditions = """
        ?attr a peg:Attribute .
        ?cg1 a peg:AttributeChange ; peg:dependsOn [?tpred1 ?ti1] ; peg:appliedTo ?attr .
        ?cg2 a peg:AttributeChange ; peg:dependsOn [?tpred2 ?ti2] ; peg:appliedTo ?attr .
        FILTER(?tpred1 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
        FILTER(?tpred2 IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
        """
    
    query = get_query_to_compare_time_instants(time_named_graph_uri, time_instant_select_conditions)

    gd.run_update_query(query, graphdb_url, repository_name)

def compare_time_intervals_of_attribute_versions(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    """
    Sort all time intervals of versions related to one attribute.
    """
    
    time_interval_select_conditions = """
        ?attr a peg:Attribute ; peg:hasAttributeVersion ?av1, ?av2 .
        ?av1 peg:hasTime ?i1 .
        ?av2 peg:hasTime ?i2 .
        FILTER (?av1 != ?av2)
        """
    
    query = get_query_to_compare_time_intervals(time_named_graph_uri, time_interval_select_conditions)

    gd.run_update_query(query, graphdb_url, repository_name)

def get_earliest_and_latest_time_instants_for_events(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    """
    An event can get related to multiple instants through peg:hasTimeBefore and peg:hasTimeAfter. This function gets the latest and the earliest time instant for each event.
    If a previous latest or earliest time instant is no longer the correct one, it is removed.
    """
    
    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?g {{
            ?ev ?estPred ?t .
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        VALUES (?erPred ?estPred ?compPred) {{
            (peg:hasTimeAfter peg:hasEarliestTimeInstant peg:instantAfter)
            (peg:hasTimeBefore peg:hasLatestTimeInstant peg:instantBefore)
        }}
        ?ev a peg:Event ; ?erPred ?t .
        OPTIONAL {{
            ?ev peg:hasTime ?time .
        }}
        OPTIONAL {{
            ?ev ?erPred ?tBis .
            FILTER (?tBis != ?t)
            {{
                ?tBis ?compPred ?t .
            }}UNION{{
                ?tBis time:instantMorePreciseThan ?t ;
                peg:instantSameTime ?t .
            }}
        }}
        FILTER(!BOUND(?tBis) && !BOUND(?time))
    }}
    """

    query2 = np.query_prefixes + f"""
        DELETE {{
            ?ev ?estPred ?tEst
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            VALUES ?estPred {{ peg:hasEarliestTimeInstant peg:hasLatestTimeInstant }}
            ?ev a peg:Event ; ?estPred ?tEst .
            {{
                ?ev peg:hasTime ?time .
            }}UNION{{
                ?ev ?estPred ?tEstBis .
                FILTER(?tEst != ?tEstBis)
                MINUS {{
                    ?tEstBis peg:instantSameTime ?tEst ; peg:instantAsPreciseAs ?tEst .
                }}
            }}
        }}
        """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def remove_earliest_and_latest_time_instants(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    query = np.query_prefixes + f"""
    DELETE {{
        GRAPH ?g {{
            ?s ?p ?o
        }}
    }}
    WHERE {{
        BIND({time_named_graph_uri.n3()} AS ?g)
        ?s ?p ?o .
        FILTER(?p IN (peg:hasLatestTimeInstant, peg:hasEarliestTimeInstant))
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def get_validity_interval_for_attribute_versions(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    # Creation of a time interval of attribute version without any time interval
    query1 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{
                ?av peg:hasTime ?timeInterval .
                ?timeInterval a peg:CrispTimeInterval .
                }}
        }}
        WHERE {{
            ?av a peg:AttributeVersion .
            MINUS {{ ?av peg:hasTime [a peg:CrispTimeInterval] }}
            BIND(URI(CONCAT(STR(URI({URIRef(np.RES).n3()})), "TI_", STRUUID())) AS ?timeInterval)
        }}
    """

    # Add instants for time intervals related to attribute versions
    query2 = np.query_prefixes + f"""
        DELETE {{
            ?timeInterval peg:hasBeginning ?curTIBeg ; peg:hasEnd ?curTIEnd .
        }}
        INSERT {{
            GRAPH ?g {{
                ?timeInterval peg:hasBeginning ?ti1 ; peg:hasEnd ?ti2 .
            }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)

            ?av a peg:AttributeVersion ; peg:hasTime ?timeInterval .
            ?timeInterval a peg:CrispTimeInterval .
            ?cg1 a peg:AttributeChange; peg:dependsOn ?ev1 ; peg:makesEffective ?av .
            ?cg2 a peg:AttributeChange; peg:dependsOn ?ev2 ; peg:outdates ?av .
            OPTIONAL {{?ev1 peg:hasTime ?tip1}}
            OPTIONAL {{?ev2 peg:hasTime ?tip2}}
            OPTIONAL {{?ev1 peg:hasLatestTimeInstant ?til1 .}}
            OPTIONAL {{?ev2 peg:hasLatestTimeInstant ?til2 .}}
            OPTIONAL {{?ev1 peg:hasEarliestTimeInstant ?tie1 .}}
            OPTIONAL {{?ev2 peg:hasEarliestTimeInstant ?tie2 .}}
            
            FILTER(BOUND(?tip1) || BOUND(?til1) || BOUND(?tie1))
            FILTER(BOUND(?tip2) || BOUND(?til2) || BOUND(?tie2))

            BIND(IF(BOUND(?tip1), ?tip1, IF(BOUND(?til1), ?til1, ?tie1)) AS ?ti1)
            BIND(IF(BOUND(?tip2), ?tip2, IF(BOUND(?tie2), ?tie2, ?til2)) AS ?ti2)

            OPTIONAL{{
                ?timeInterval peg:hasBeginning ?curTIBeg .
                MINUS {{
                    ?curTIBeg peg:instantSameTime ?ti1 ; peg:instantAsPreciseAs ?ti1 .
                }}
                FILTER(?curTIBeg != ?ti1)
            }}
            OPTIONAL{{
                ?timeInterval peg:hasEnd ?curTIEnd .
                MINUS {{
                    ?curTIEnd peg:instantSameTime ?ti2 ; peg:instantAsPreciseAs ?ti2 .
                }}
                FILTER(?curTIEnd != ?ti2)
            }}
        }}
    """

    queries = [query1, query2]
    for query in queries :
        gd.run_update_query(query, graphdb_url, repository_name)

def add_time_relations(graphdb_url:URIRef, repository_name:str, time_named_graph_name:str):
    """
    Add temporal relationships:
    * comparison of instants belonging to the same event (i1 before/after i2)
    * comparison of instants linked to the same attribute (i1 before/after i2)
    * deduction of earliest/latest instants linked to events from before/after instants
    * creation of validity intervals for attribute versions
    * comparison of version intervals between versions of the same attribute

    The set of triples is stored in the named graph whose name is `time_named_graph_name`.
    """
    
    time_named_graph_uri = URIRef(gd.get_named_graph_uri_from_name(graphdb_url, repository_name, time_named_graph_name))
    compare_time_instants_of_events(graphdb_url, repository_name, time_named_graph_uri)
    compare_time_instants_of_attributes(graphdb_url, repository_name, time_named_graph_uri)
    get_earliest_and_latest_time_instants_for_events(graphdb_url, repository_name, time_named_graph_uri)
    get_validity_interval_for_attribute_versions(graphdb_url, repository_name, time_named_graph_uri)
    compare_time_intervals_of_attribute_versions(graphdb_url, repository_name, time_named_graph_uri)


def compare_events(graphdb_url:URIRef, repository_name:str, time_named_graph_name:str=None):

    time_named_graph_uri = URIRef(gd.get_named_graph_uri_from_name(graphdb_url, repository_name, time_named_graph_name))

    get_similar_events(graphdb_url, repository_name, time_named_graph_uri)
    get_events_before(graphdb_url, repository_name, time_named_graph_uri)

def get_similar_events(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):
    query = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 owl:sameAs ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?ev1 a peg:Event .
            ?ev2 a peg:Event .
            ?ev1 peg:eventBefore ?ev2 .
            ?ev1 peg:eventAfter ?ev2 .
        }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def get_events_before(graphdb_url:URIRef, repository_name:str, time_named_graph_uri:URIRef):

    # An event A whose time value is before a time value dependent on an event B, then A is before B.
    query1 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?ev1 a peg:Event .
            ?ev2 a peg:Event .
            FILTER (?ev1 != ?ev2)
            ?ev1 peg:hasTime ?t1 .
            ?ev2 peg:hasTime ?t2 .
            ?t1 peg:instantBefore ?t2 .
        }}
    """

    # For a landmark, the event linked to the change describing its appearance is located before the event linked to the change describing its disappearance.
    query2 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?lm a peg:Landmark .
            ?cg1 a peg:Change ; peg:isChangeType ctype:LandmarkAppearance ; peg:appliedTo ?lm ; peg:dependsOn ?ev1 .
            ?cg2 a peg:Change ; peg:isChangeType ctype:LandmarkDisappearance ; peg:appliedTo ?lm ; peg:dependsOn ?ev2 .
        }}
        """
    
    # For a landmark relation, the event linked to the change describing its appearance is located before the event linked to the change describing its disappearance.
    query3 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?lr a peg:LandmarkRelation .
            ?cg1 a peg:Change ; peg:isChangeType ctype:LandmarkRelationAppearance ; peg:appliedTo ?lr ; peg:dependsOn ?ev1 .
            ?cg2 a peg:Change ; peg:isChangeType ctype:LandmarkRelationDisappearance ; peg:appliedTo ?lr ; peg:dependsOn ?ev2 .
        }}
        """
    
    # For a landmark relation, the event linked to the change describing its appearance is after any event linked to a change in the appearance of a landmark included in the relationship.
    # Ie, a landmark relation can only exist when the landmarks described exist.
    query4 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?lr a peg:LandmarkRelation .
            ?lm a peg:Landmark .
            ?lr (peg:locatum|peg:relatum) ?lm .
            ?cg1 a peg:Change ; peg:isChangeType ctype:LandmarkAppearance ; peg:appliedTo ?lm ; peg:dependsOn ?ev1 .
            ?cg2 a peg:Change ; peg:isChangeType ctype:LandmarkRelationAppearance ; peg:appliedTo ?lr ; peg:dependsOn ?ev2 .
        }}
        """
    
    # For a landmark relation, the event linked to the change describing its disappearance is above all an event linked to a change in the disappearance of a landmark included in the relationship.
    # Ie, a rlandmark relation disappears before the landmarks described disappear.
    query5 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?lr a peg:LandmarkRelation .
            ?lm a peg:Landmark .
            ?lr (peg:locatum|peg:relatum) ?lm .
            ?cg1 a peg:Change ; peg:isChangeType ctype:LandmarkRelationDisappearance ; peg:appliedTo ?lr ; peg:dependsOn ?ev1 .
            ?cg2 a peg:Change ; peg:isChangeType ctype:LandmarkDisappearance ; peg:appliedTo ?lm ; peg:dependsOn ?ev2 .
        }}
        """
    
    # An event linked to a change describing a version's effectiveness is located before the event linked to the change describing the version's expiration.
    query6 = np.query_prefixes + f"""
        INSERT {{
            GRAPH ?g {{ ?ev1 peg:eventBefore ?ev2 . }}
        }}
        WHERE {{
            BIND({time_named_graph_uri.n3()} AS ?g)
            ?av a peg:AttributeVersion .
            ?cg1 a peg:AttributeChange ; peg:makesEffective ?av ; peg:dependsOn ?ev1 .
            ?cg2 a peg:AttributeChange ; peg:outdates ?av ; peg:dependsOn ?ev2 .
        }}
        """
    
    queries = [query1, query2, query3, query4, query5, query6]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def get_time_precision_from_integer(precision_int:int):
    """
    Get the precision of a time instant from an integer.
    The integer is defined in the ontology as follows:
    1: millennium
    2: century
    3: decade
    4: year
    5: month
    6: day
    """

    precisions = {
        0: "billion_years",
        1: "hundred_million_years",
        3: "million_years",
        4: "hundred_thousand_years",
        5: "ten_thousand_years",
        6: "millennium",
        7: "century",
        8: "decade",
        9: "year",
        10: "month",
        11: "day",
        12: "hour",
        13: "minute",
        14: "second"
    }

    precision = precisions.get(precision_int)    
    return precision

def more_precise(target_precision:URIRef, t_precision:URIRef):
    """Compare the precision of two time instants. Return true if t_precision is more precise than target_precision."""

    precisions = {
        np.TIME["unitBillionYears"]: 0,
        np.TIME["unitHundredMillionYears"]: 1,
        np.TIME["unitMillionYears"]: 3,
        np.TIME["unitHundredThousandYears"]: 4,
        np.TIME["unitTenThousandYears"]: 5,
        np.TIME["unitMillenium"]: 6,
        np.TIME["unitCentury"]: 7,
        np.TIME["unitDecade"]: 8,
        np.TIME["unitYear"]: 9,
        np.TIME["unitMonth"]: 10,
        np.TIME["unitDay"]: 11,
        np.TIME["unitHour"]: 12,
        np.TIME["unitMinute"]: 13,
        np.TIME["unitSecond"]: 14
    }

    target_val = precisions.get(target_precision, -1)
    t_val = precisions.get(t_precision, -1)

    return t_val > target_val

def get_time_calendar_from_wikidata_uri(calendar_uri:URIRef):
    """Get the calendar corresponding to a Wikidata URIRef. Return None if the calendar is not supported."""
    calendars = {
        np.WD["Q1985727"]: "gregorian",
        np.WD["Q181974"]: "republican",
        np.WD["Q1985786"]: "julian",
    }

    calendar = calendars.get(calendar_uri)
    return calendar

def get_time_instant_elements(time_dict:dict):
    """
    Get the elements of a time instant from a dictionary. The dictionary must have the following keys: "stamp", "calendar", "precision".
    Return a list of three elements: [stamp, calendar, precision]. If one of the keys is missing or if the value is not valid, return [None, None, None].
    """
    if not isinstance(time_dict, dict):
        return [None, None, None]
    
    time_stamp = time_dict.get("stamp")
    time_stamp = format_timestamp(time_stamp) if time_stamp is not None else None
    time_cal = time_dict.get("calendar")
    time_prec = time_dict.get("precision")
    
    if None in [time_stamp, time_cal, time_prec]:
        return [None, None, None]
    
    stamp = gr.get_time_stamp_literal(time_stamp)
    precision = om.get_time_unit(time_prec)
    calendar = om.get_time_calendar(time_cal)

    return [stamp, calendar, precision]

def get_current_timestamp():
    return datetime.datetime.now().isoformat() + "Z"

def get_valid_time_description(time_description:dict):
    stamp_key, calendar_key, precision_key = "stamp", "calendar", "precision"
    start_time_key, end_time_key = "start", "end"
    start_time = get_time_instant_elements(time_description.get(start_time_key))
    end_time = get_time_instant_elements(time_description.get(end_time_key))

    if not isinstance(start_time, list) or None in start_time:
        time_description[start_time_key] = {stamp_key:None, precision_key:None, calendar_key:None}

    if not isinstance(end_time, list) or None in end_time:
        time_description[end_time_key] = {stamp_key:get_current_timestamp(), precision_key:"day", calendar_key:"gregorian"}

    return time_description

def get_gregorian_date_from_timestamp(time_stamp:str):
    time_stamp = format_timestamp(time_stamp)
    time_match_pattern = "^(-|\+|)\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])$"
    if re.match(time_match_pattern, time_stamp) is not None:
        time_stamp += "T00:00:00Z"
        time_description = {"stamp":time_stamp, "calendar":"gregorian", "precision":"day"}
        time_elements = get_time_instant_elements(time_description)

        return time_elements
    
    return [None, None, None]

def format_timestamp(raw_ts: str) -> str:
    """
    Normalizes various date formats to YYYY-MM-DDTHH:MM:SSZ.
    Handles '-' and '/' separators, ISO formats (T), and microseconds.
    """
    # 1. Standardize the string:
    # - Replace 'T' with a space to separate Date from Time
    # - Remove 'Z' (UTC indicator)
    # - Replace '/' with '-' to unify date separators (e.g., 2026/04/22 -> 2026-04-22)
    normalized_input = raw_ts.strip().replace('T', ' ').replace('Z', '').replace('/', '-')
    
    # 2. Split into Date and Time components
    # Example: "2026-04-22 15:30:00" -> ["2026-04-22", "15:30:00"]
    parts = normalized_input.split(' ')
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else "00:00:00"

    # 3. Process Date
    # Since we replaced '/' with '-', splitting by '-' works for all cases
    y, m, d = [int(x) for x in date_part.split('-')]

    # 4. Process Time
    # - Truncate microseconds (e.g., "15:30:00.123" -> "15:30:00")
    time_only = time_part.split('.')[0]
    time_segments = time_only.split(':')
    
    # - Parse hours, minutes, and seconds with default values if missing
    h = int(time_segments[0])
    min_ = int(time_segments[1]) if len(time_segments) > 1 else 0
    s = int(time_segments[2]) if len(time_segments) > 2 else 0

    # 5. Return formatted string using f-string padding (e.g., 4:2 -> 04:02)
    return f"{y:04d}-{m:02d}-{d:02d}T{h:02d}:{min_:02d}:{s:02d}Z"