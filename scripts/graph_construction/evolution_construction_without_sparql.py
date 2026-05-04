from rdflib import URIRef, Graph
from scripts.graph_construction.namespaces import NameSpaces
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import graphrdf as gr
from scripts.graph_construction import multi_sources_processing as msp
from scripts.graph_construction import resource_transfert as rt
from scripts.resource_management import resource_initialisation as ri
from scripts.utils import time_processing as tp

np = NameSpaces()

#####################################################################################################################

def initialize_missing_changes_and_events_for_landmarks(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_name_graph_uri, tmp_named_graph_uri):

    # Vos données structurées
    data_configs = [
    {
        "class": np.PEG["Landmark"],
        "change": np.CTYPE["LandmarkAppearance"],
        "interval": np.PEG["hasBeginning"],
        "instant": np.PEG["hasTimeBefore"]
    },
    {
        "class": np.PEG["Landmark"],
        "change": np.CTYPE["LandmarkDisappearance"],
        "interval": np.PEG["hasEnd"],
        "instant": np.PEG["hasTimeAfter"]
    },
    {
        "class": np.PEG["LandmarkRelation"],
        "change": np.CTYPE["LandmarkRelationAppearance"],
        "interval": np.PEG["hasBeginning"],
        "instant": np.PEG["hasTimeBefore"]
    },
    {
        "class": np.PEG["LandmarkRelation"],
        "change": np.CTYPE["LandmarkRelationDisappearance"],
        "interval": np.PEG["hasEnd"],
        "instant": np.PEG["hasTimeAfter"]
    }
]
       
    create_missing_changes(graphdb_url, repository_name, facts_named_graph_uri, data_configs)
    map_potential_times_to_events(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri, data_configs)
    finalize_event_times(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)

    # Nettoyage et finalisation
    gd.remove_named_graph_from_uri(tmp_named_graph_uri)
    rt.transfer_elements_to_roots(graphdb_url, repository_name, facts_named_graph_uri)

def create_missing_changes(graphdb_url, repository_name, facts_named_graph_uri, data_configs:list[dict] = []):

    formatted_values = gd.format_sparql_values(data_configs, ["class", "change"])
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{
            ?missingChange a peg:Change ;
                peg:isChangeType ?changeType ;
                peg:appliedTo ?elem ;
                peg:dependsOn ?missingEvent .
            ?missingEvent a peg:Event .
        }}
    }} WHERE {{
        {{
            SELECT * WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                VALUES (?elemSelectedClass ?changeType) {{ {formatted_values} }}
                GRAPH ?gf {{ ?elem a ?elemClass . }}
                ?elemClass rdfs:subClassOf* ?elemSelectedClass .
                FILTER NOT EXISTS {{
                    ?change peg:isChangeType ?changeType ; peg:appliedTo ?elem .
                }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI(facts:)), "Change/", STRUUID())) AS ?missingChange)
        BIND(URI(CONCAT(STR(URI(facts:)), "Event/", STRUUID())) AS ?missingEvent)
    }}
    """
    gd.run_update_query(query, graphdb_url, repository_name)


def map_potential_times_to_events(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri, data_configs:list[dict] = []):
    formatted_values = gd.format_sparql_values(data_configs, ["class", "change", "interval", "instant"])
    query = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gt {{ ?event ?propInstantTime ?time }}
}} WHERE {{
    BIND({facts_named_graph_uri.n3()} AS ?gf)
    BIND({tmp_named_graph_uri.n3()} AS ?gt)
    {{
        GRAPH ?gf {{ ?event a peg:Event }}
        ?event peg:hasTrace [?propInstantTime ?timeTrace ] .
        ?time peg:hasTrace ?timeTrace .
        FILTER (?propInstantTime IN (peg:hasTime, peg:hasTimeBefore, peg:hasTimeAfter))
    }}
    UNION
    {{	
        VALUES (?class ?changeType ?propIntervalTime ?propInstantTime) {{ {formatted_values} }}
        GRAPH ?gf {{ ?elem a ?elemClass . }}
        ?elemClass rdfs:subClassOf* ?class .
        ?change peg:appliedTo ?elem ; peg:isChangeType ?changeType ; peg:dependsOn ?event .
        ?elem peg:hasTrace [peg:hasTime ?timeIntervalTrace] .
        ?timeIntervalTrace ?propIntervalTime ?timeTrace .
        ?time peg:hasTrace ?timeTrace .
    }}
}}
"""

    gd.run_update_query(query, graphdb_url, repository_name)

def finalize_event_times(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    This function finalizes the times of events based on the potential times mapped in the previous step. It consists of two queries:
    1. The first query inserts the potential times as actual times for events that do not have any time assigned yet.
    2. The second query selects the minimum and maximum time differences for events with potential times and assigns the time with the minimum difference as the time before and the time with the maximum difference as the time after.
    
    Args:
        graphdb_url (URIRef): The URL of the GraphDB instance.
        repository_name (str): The name of the repository in GraphDB.
        facts_named_graph_uri (URIRef): The URI of the named graph containing the facts.
        tmp_named_graph_uri (URIRef): The URI of the temporary named graph used for intermediate results.
        calendar_uri (URIRef): The URI of the calendar used for time calculations.
    """

    query1 = np.query_prefixes + f"""
    INSERT {{ GRAPH ?gf {{ ?event ?propTime ?time . }} }}
    WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
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
            SELECT ?gf ?gt ?propTime ?event (MIN(?timeStamp) AS ?minTimeStamp) (MAX(?timeStamp) AS ?maxTimeStamp) WHERE {{
                BIND({facts_named_graph_uri.n3()} AS ?gf)
                BIND({tmp_named_graph_uri.n3()} AS ?gt)
                VALUES ?propTime {{ peg:hasTimeBefore peg:hasTimeAfter }}
                GRAPH ?gf {{ ?lm a peg:Landmark . }}
                ?change peg:dependsOn ?event ; peg:appliedTo ?lm .
                GRAPH ?gt {{ ?event ?propTime ?time . }}
                ?time peg:timeStamp ?timeStamp .
                FILTER NOT EXISTS {{ GRAPH ?gf {{ ?event peg:hasTime ?t }}}}
            }}
            GROUP BY ?gf ?gt ?propTime ?event
        }}
        BIND(IF(?propTime = peg:hasTimeBefore, ?minTimeStamp, ?maxTimeStamp) AS ?extTimeStamp)
        ?event ?propTime ?time .
        ?time peg:timeStamp ?timeStamp .
        GRAPH ?gf {{ ?time a ?timeClass . }}
        FILTER(?timeStamp = ?extTimeStamp)
    }}
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

##### Work on attributes ######
def get_elementary_versions_and_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef, ttl_file:str):
    
    types = select_attribute_types(graphdb_url, repository_name, facts_named_graph_uri)
    versions = select_attribute_versions(graphdb_url, repository_name, facts_named_graph_uri)
    changes = select_attribute_changes(graphdb_url, repository_name, facts_named_graph_uri)

    evolutions = construct_evolutions(types, changes, versions)

    # import json
    # json_evolutions = json.dumps(evolutions, indent=2)
    # with open("/Users/charlybernard/Downloads/evolutions.json", "w") as f:
    #     f.write(json_evolutions)

    gd.remove_named_graph_from_uri(tmp_named_graph_uri)
    loop_limit = 50000
    loop_nb = 0
    g = Graph()

    for attr_uri, data in evolutions.items():
        loop_nb += 1
        if loop_nb > loop_limit:
            # Nettoyage et finalisation
            g.serialize(destination=ttl_file, format="turtle")

            # Import the TTL file in GraphDB
            gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=tmp_named_graph_uri)

            g = Graph()
            loop_nb = 0

        data = generate_temporary_changes(data)
        data = add_infinite_boundaries_for_temporary_changes(data)
        data["temporary_versions"] = generate_temporary_versions(data["temporary_changes"])

        mapping = map_version_indices(data.get("temporary_changes", []), data.get("versions", []))
        data["version_map"] = mapping # Ajout de la map pour debug
        temporary_versions = fill_temporary_versions_data(data)
        g += create_graph_for_attribute_evolution(data)

    # Nettoyage et finalisation
    g.serialize(destination=ttl_file, format="turtle")

    # Import the TTL file in GraphDB
    gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=tmp_named_graph_uri)

def construct_evolutions(types, changes, versions):
    # Le dictionnaire final indexé par l'URI de l'attribut
    evolutions = {}

    # --- 1. Initialisation avec les types ---
    for item in types:
        uri = item['attr']
        evolutions[uri] = {
            "uri": uri,
            "type": item['attrType'],
            "changes": [],
            "versions": set() # On utilise un set pour éviter les doublons d'URIs
        }

    # --- 2. Traitement des CHANGES (Changements explicites) ---
    for c in changes:
        attr_uri = c['attr']
        if attr_uri in evolutions:
            # Construction du dictionnaire de changement
            change_entry = {
                "real_change": True,
                "change_uri": c.get('change'),
                "time": c.get('time'),
                "timestamp": c.get('timeStamp'),
                "time_precision": c.get('timePrecision'),
                "makes_effective": [c.get('madeEffectiveVersion')] if c.get('madeEffectiveVersion') else [],
                "outdates": [c.get('outdatedVersion')] if c.get('outdatedVersion') else []
            }
            evolutions[attr_uri]["changes"].append(change_entry)
            
            # Ajout des versions mentionnées s'il y en a
            if c.get('madeEffectiveVersion'):
                evolutions[attr_uri]["versions"].add(c['madeEffectiveVersion'])
            if c.get('outdatedVersion'):
                evolutions[attr_uri]["versions"].add(c['outdatedVersion'])

    # --- 3. Traitement des VERSIONS (Intervalles temporels) ---
    for v in versions:
        attr_uri = v['attr']
        version_uri = v['version']
        
        if attr_uri in evolutions:
            # Ajout de l'URI de la version au set
            evolutions[attr_uri]["versions"].add(version_uri)
            
            # Création du changement d'APPARITION (Start)
            evolutions[attr_uri]["changes"].append({
                "real_change": False,
                "change_uri": gr.generate_uri(np.FACTS, "Change", separator="/"),
                "time": v.get('startTime'),
                "timestamp": v.get('startTimeStamp'),
                "time_precision": v.get('startTimePrecision'),
                "makes_effective": [version_uri],
                "outdates": []
            })
            
            # Création du changement de DISPARITION (End)
            evolutions[attr_uri]["changes"].append({
                "real_change": False,
                "change_uri": gr.generate_uri(np.FACTS, "Change", separator="/"),
                "time": v.get('endTime'),
                "timestamp": v.get('endTimeStamp'),
                "time_precision": v.get('endTimePrecision'),
                "makes_effective": [],
                "outdates": [version_uri]
            })

    # --- Nettoyage final ---
    for attr_uri in evolutions:
        # Conversion du set de versions en liste pour le format final
        evolutions[attr_uri]["versions"] = list(evolutions[attr_uri]["versions"])
        
        # Optionnel : Trier les changements par timestamp pour faciliter la lecture de l'évolution
        evolutions[attr_uri]["changes"].sort(key=lambda x: x['timestamp'] if x['timestamp'] else "")

    return evolutions

def generate_temporary_changes(attr_evolutions):
    """
    Generate temporary changes for each attribute by grouping them based on their time and timestamp. This function handles both real changes and inferred changes from version intervals, ensuring that all changes are properly merged and that the traces are preserved."""
    # Clé : (time_uri, timestamp) -> Valeur : dictionnaire consolidé
    grouped = {}

    for ch in attr_evolutions["changes"]:
        t_uri = ch["time"]
        t_stamp = ch["timestamp"]
        t_prec = ch["time_precision"]
        group_key = (t_stamp)

        if group_key not in grouped:
            grouped[group_key] = {
                "time": t_uri,
                "timestamp": t_stamp,
                "time_precision": t_prec,
                "change_uri": gr.generate_uri(np.FACTS, "Change", separator="/"), # URI générique pour le changement consolidé
                "makes_effective": [],
                "outdates": [],
                "traces": []
            }

        target = grouped[group_key]

        if tp.more_precise(target["time_precision"], t_prec):
            target["time"] = t_uri
            target["time_precision"] = t_prec
        
        # 1. Gestion des versions (entrées/sorties)
        # On vérifie si c'est une liste ou un URI seul pour être robuste
        m_eff = ch.get("makes_effective")
        if m_eff:
            vals = m_eff if isinstance(m_eff, list) else [m_eff]
            target["makes_effective"].extend(vals)
        
        outd = ch.get("outdates")
        if outd:
            vals = outd if isinstance(outd, list) else [outd]
            target["outdates"].extend(vals)

        # 2. Ajout de la trace avec son métadonnée "real_change"
        target["traces"].append({
            "uri": ch.get("change_uri"),
            "is_real": ch.get("real_change", False)
        })

    # 3. Nettoyage et dédoublonnage
    for g in grouped.values():
        g["makes_effective"] = list(set(g["makes_effective"]))
        g["outdates"] = list(set(g["outdates"]))
        
        # Pour les traces, on dédoublonne sur l'URI pour éviter les répétitions
        # tout en gardant la structure de dictionnaire
        unique_traces = {}
        for t in g["traces"]:
            if t["uri"] not in unique_traces:
                unique_traces[t["uri"]] = t
        g["traces"] = list(unique_traces.values())

    # Mise à jour de l'attribut
    attr_evolutions["temporary_changes"] = list(grouped.values())
    attr_evolutions["temporary_changes"].sort(key=lambda x: x['timestamp'] if x['timestamp'] else "")

    return attr_evolutions

def add_infinite_boundaries_for_temporary_changes(attr_evolutions):
    temp_changes = attr_evolutions.get("temporary_changes", [])
    
    # 1. Création du changement "Infini Négatif" (Début des temps)
    start_inf = {
        "time": None,
        "timestamp": "-inf", # Ou "0001-01-01T00:00:00Z"
        "change_uri": gr.generate_uri(np.FACTS, "Change", separator="/"),
        "makes_effective": [],
        "outdates": [],
        "traces": []
    }
    
    # 2. Création du changement "Infini Positif" (Fin des temps)
    end_inf = {
        "time": None,
        "timestamp": "+inf", # Ou "9999-12-31T23:59:59Z"
        "change_uri": gr.generate_uri(np.FACTS, "Change", separator="/"),
        "makes_effective": [],
        "outdates": [],
        "traces": []
    }
    
    # On s'assure que c'est bien trié (au cas où)
    temp_changes.sort(key=lambda x: x['timestamp'] if x['timestamp'] else "")
    
    # Insertion aux extrémités
    temp_changes.insert(0, start_inf)
    temp_changes.append(end_inf)
    
    return attr_evolutions

def generate_temporary_versions(temporary_changes:list[dict]):
    """
    Generate temporal segments based on the consolidated temporal changes. Each segment represents a time interval between two consecutive changes.
    If there are n changes, there will be n-1 segments. Each segment will have a URI, the time of the change that made it effective, the time of the change that outdated it, and the corresponding timestamps. The index_range is useful for mapping versions to segments later on.

    temporary_changes: List of consolidated temporal changes for an attribute, sorted by timestamp. Each change is a dictionary with keys like "time", "timestamp", "made_effective", "outdated", and "traces".
    """

    temporary_versions = []
    
    # On parcourt de 0 à n-1 pour pouvoir comparer i et i+1
    for i in range(len(temporary_changes) - 1):
        c_start = temporary_changes[i]
        c_end = temporary_changes[i+1]
        
        segment = {
            "uri": gr.generate_uri(np.FACTS, "AttributeVersion", separator="/"),
            "made_effective_by": c_start["change_uri"], # URI du changement de début
            "outdated_by": c_end["change_uri"],        # URI du changement de fin
            "traces": []                          # Sera rempli par la suite       
        }
        
        temporary_versions.append(segment)
        
    return temporary_versions


def map_version_indices(temporary_changes, versions):
    """
    versions: Liste d'URIs de versions récupérées initialement.
    temporary_changes: Liste des changements consolidés.
    """
    # 1. Initialisation avec toutes les versions connues
    # On utilise None pour indiquer que l'événement n'a pas encore été trouvé
    version_map = {
        v_uri: {"made_by": None, "outdated_by": None} 
        for v_uri in versions
    }

    # 2. Remplissage via le parcours des changements
    for idx, change in enumerate(temporary_changes):
        # Tracking des apparitions
        for v_uri in change.get("makes_effective", []):
            if v_uri not in version_map:
                # Cas rare : une version apparaît dans les changements mais pas dans la liste initiale
                version_map[v_uri] = {"made_by": idx, "outdated_by": None}
            else:
                version_map[v_uri]["made_by"] = idx
        
        # Tracking des disparitions
        for v_uri in change.get("outdates", []):
            if v_uri not in version_map:
                version_map[v_uri] = {"made_by": None, "outdated_by": idx}
            else:
                version_map[v_uri]["outdated_by"] = idx

    # 3. Vérification des versions "fantômes" ou "incomplètes"
    for v_uri, indices in version_map.items():
        if indices["made_by"] is None and indices["outdated_by"] is None:
            print(f"Version {v_uri} does not appear in any change. It might be a 'ghost' version or an error in data.")
        elif indices["made_by"] is None:
            # Cas d'une version qui finit mais n'a jamais commencé (ex: existait avant -inf)
            # On peut décider de la lier à l'index 0 (-inf)
            indices["made_by"] = indices["outdated_by"] - 1
        elif indices["outdated_by"] is None:
            # Cas d'une version qui commence mais n'a jamais fini (ex: existe après +inf)
            # On peut décider de la lier à l'index final (+inf)
            indices["outdated_by"] = indices["made_by"] + 1
            
    return version_map

def fill_temporary_versions_data(attr_data):
    """
    Remplit les 'versions_uris' et les 'traces' de chaque temporary_version
    en se basant sur le version_map et les indices de changements.
    """
    temp_versions = attr_data.get("temporary_versions", [])
    temp_changes = attr_data.get("temporary_changes", [])
    version_map = attr_data.get("version_map", {})

    for v_uri, indices in version_map.items():
        start_idx = indices["made_by"]
        end_idx = indices["outdated_by"]

        # L'intervalle est semi-ouvert [start_idx, end_idx[
        # Chaque i correspond à l'index de la temporary_version
        for i in range(start_idx, end_idx):
            if i < len(temp_versions):
                current_temp_v = temp_versions[i]
                current_temp_v["traces"].append(v_uri) if v_uri not in current_temp_v["traces"] else None

    return attr_data


def create_graph_for_attribute_evolution(data):
    """
    Crée un graphe RDF pour l'évolution d'un attribut à partir de sa structure de données consolidée.
    data: Dictionnaire contenant les informations sur l'attribut, ses changements, ses versions temporaires, etc.
    """
    g = Graph()
    attr_uri = data["uri"]
    temporary_versions = data.get("temporary_versions", [])
    temporary_changes = data.get("temporary_changes", [])

    change_type_uri = np.CTYPE["AttributeVersionTransition"]

    for c in temporary_changes:
        c_uri = c["change_uri"]
        time_uri = c["time"]
        traces = c.get("traces", [])
        ri.create_attribute_change(g, c_uri, change_type_uri, attr_uri)
        if time_uri:
            g.add((c_uri, np.PEG["hasRelatedTime"], time_uri))
        for trace in traces:
            is_real_change = trace.get("is_real", False)
            if is_real_change:
                g.add((c_uri, np.PEG.hasTrace, trace["uri"]))
            
    for v in temporary_versions:
        v_uri = v["uri"]
        made_effective_by = v["made_effective_by"]
        outdated_by = v["outdated_by"]
        ri.create_attribute_version_and_add_to_attribute(g, attr_uri, v_uri)
        g.add((made_effective_by, np.PEG["makesEffective"], v_uri))
        g.add((outdated_by, np.PEG["outdates"], v_uri))

        for trace in v.get("traces", []):
            g.add((v_uri, np.PEG.hasTrace, gr.get_valid_uri(trace)))

    return g

########################################################################################################

def select_attribute_types(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        attr_var:str = "attr", attr_type_var:str = "attrType"):
    
    variables = [attr_var, attr_type_var]

    query = np.query_prefixes + f"""
    SELECT ?{attr_var} ?{attr_type_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{attr_var} a peg:Attribute . }}
        ?{attr_var} peg:isAttributeType ?{attr_type_var} .
    }}
    """

    types = gd.fetch_sparql_data(query, graphdb_url, repository_name, variables)
    return types


def select_attribute_versions(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        attr_var:str = "attr", attr_version_var:str = "version",
        start_time_var:str = "startTime", start_time_stamp_var:str = "startTimeStamp", start_time_precision_var:str = "startTimePrecision",
        end_time_var:str = "endTime", end_time_stamp_var:str = "endTimeStamp", end_time_precision_var:str = "endTimePrecision"):
    
    variables = [attr_var, attr_version_var, start_time_var, start_time_stamp_var, start_time_precision_var, end_time_var, end_time_stamp_var, end_time_precision_var]

    query = np.query_prefixes + f"""
    SELECT ?{attr_var} ?{attr_version_var} ?{start_time_var} ?{start_time_stamp_var} ?{start_time_precision_var} ?{end_time_var} ?{end_time_stamp_var} ?{end_time_precision_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{attr_var} a peg:Attribute . }}
        ?{attr_var} peg:hasTrace ?attrTrace .
        ?attrTrace peg:hasAttributeVersion ?{attr_version_var} .
        ?elemTrace peg:hasAttribute ?attrTrace  ; peg:hasTime [ peg:hasBeginning ?{start_time_var}Trace ; peg:hasEnd ?{end_time_var}Trace ].
        ?{start_time_var} peg:timeStamp ?{start_time_stamp_var} ; peg:timePrecision ?{start_time_precision_var} ; peg:hasTrace ?{start_time_var}Trace .
        ?endTime peg:timeStamp ?endTimeStamp ; peg:timePrecision ?{end_time_precision_var} ; peg:hasTrace ?endTimeTrace .
    }}
    """

    versions = gd.fetch_sparql_data(query, graphdb_url, repository_name, variables)
    return versions

def select_attribute_changes(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        attr_var:str = "attr", change_var:str = "change",
        time_var:str = "time", time_stamp_var:str = "timeStamp", time_precision_var:str = "timePrecision",
        made_effective_var:str = "madeEffectiveVersion", outdated_var:str = "outdatedVersion"):
    
    variables = [attr_var, change_var, time_var, time_stamp_var, time_precision_var, made_effective_var, outdated_var]

    query = np.query_prefixes + f"""
    SELECT ?{attr_var} ?{change_var} ?{time_var} ?{time_stamp_var} ?{time_precision_var} ?{made_effective_var} ?{outdated_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{attr_var} a peg:Attribute . }}
        ?{attr_var} peg:hasTrace ?attrTrace .
        ?{change_var} peg:appliedTo ?attrTrace ; peg:dependsOn [peg:hasTime ?timeTrace].
        ?{time_var} peg:timeStamp ?{time_stamp_var} ; peg:timePrecision ?{time_precision_var} ; peg:hasTrace ?timeTrace .
        OPTIONAL {{ ?{change_var} peg:makesEffective ?{made_effective_var} }}
        OPTIONAL {{ ?{change_var} peg:outdates ?{outdated_var} }}
    }}
    """

    changes = gd.fetch_sparql_data(query, graphdb_url, repository_name, variables)
    return changes

###########################################################################

def get_attribute_version_evolution_from_elementary_elements(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    remove_empty_attribute_versions_and_changes(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    merge_similar_successive_attribute_versions(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, tmp_named_graph_uri)

    # Transfer factoid information to facts
    rt.transfer_elements_to_roots(graphdb_url, repository_name, facts_named_graph_uri)



def remove_empty_attribute_versions_and_changes(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
   """
   Remove elementary changes and versions that are not linked to any trace, meaning they do not have any version associated with them. This process is done in three steps:
   1. Identify the elementary changes and versions to remove by marking them with a "toRemove" flag.
   2. Insert the new clean data for the changes and versions to keep, while keeping the "toRemove" flag for the ones to remove.
   3. Delete all the changes and versions that are marked with the "toRemove" flag, which are the ones that are not linked to any trace and are considered useless.

    graphdb_url: URI of the GraphDB instance
    repository_name: Name of the repository in GraphDB
    facts_named_graph_uri: URI of the named graph containing the facts
    tmp_named_graph_uri: URI of the temporary named graph used for intermediate results
   """

   get_elementary_changes_and_versions_to_remove(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
   replace_elementary_changes_and_versions_to_remove(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
   remove_elementary_changes_and_versions_to_remove(graphdb_url, repository_name, tmp_named_graph_uri)

def get_elementary_changes_and_versions_to_remove(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    
    query = np.query_prefixes + f""" 
    INSERT {{
        GRAPH ?gt {{
            ?attrVersion peg:toRemove "true"^^xsd:boolean .
            ?meChange peg:toRemove ?toRemoveMEChange .
            ?oChange peg:toRemove ?toRemoveOChange .
        }}
    }} WHERE {{
        BIND({tmp_named_graph_uri.n3()} AS ?gt)
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        GRAPH ?gf {{ ?attr a peg:Attribute . }}
        GRAPH ?gt {{ ?attrVersion a peg:AttributeVersion . }}
        
        ?attr peg:hasAttributeVersion ?attrVersion .
        ?meChange peg:makesEffective ?attrVersion .
        ?oChange peg:outdates ?attrVersion .
        FILTER NOT EXISTS {{ ?attrVersion peg:hasTrace ?x . }}
        
        OPTIONAL {{ ?meChange peg:hasTrace ?changeMETrace . }}
        OPTIONAL {{ ?oChange peg:hasTrace ?changeOTrace . }}
        BIND(IF(BOUND(?changeMETrace), "false"^^xsd:boolean, "true"^^xsd:boolean) AS ?toRemoveMEChange)
        BIND(IF(BOUND(?changeOTrace), "false"^^xsd:boolean, "true"^^xsd:boolean) AS ?toRemoveOChange)
        FILTER(?toRemoveMEChange || ?toRemoveOChange)
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def replace_elementary_changes_and_versions_to_remove(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):

    query1 = np.query_prefixes + f"""
    INSERT {{
        GRAPH {tmp_named_graph_uri.n3()} {{
            ?newChange a peg:AttributeChange ; peg:appliedTo ?attr ; peg:makesEffective ?oAttrVersion ; peg:outdates ?meAttrVersion ;
                peg:hasRelatedTime [peg:hasFuzzyBeginning ?meChangeTime ; peg:hasFuzzyEnd ?oChangeTime ].
        }}
    }} WHERE {{
        {{
            SELECT * WHERE {{
                ?attr peg:hasAttributeVersion ?attrVersion .
                ?attrVersion a peg:AttributeVersion ; peg:toRemove "true"^^xsd:boolean .
                ?meChange peg:toRemove "true"^^xsd:boolean ; peg:makesEffective ?attrVersion .
                ?oChange peg:toRemove "true"^^xsd:boolean ; peg:outdates ?attrVersion .
                OPTIONAL {{ ?meChange peg:outdates ?meAttrVersion . }}
                OPTIONAL {{ ?oChange peg:makesEffective ?oAttrVersion . }}
                OPTIONAL {{ ?meChange peg:hasRelatedTime ?meChangeTime . }}
                OPTIONAL {{ ?oChange peg:hasRelatedTime ?oChangeTime . }}
            }}
        }}
        BIND(URI(CONCAT(STR(URI(facts:)), "Change/", STRUUID())) AS ?newChange)
    }}
    """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH {tmp_named_graph_uri.n3()} {{
            ?oChange peg:outdates ?meAttrVersion .
            ?meChange peg:makesEffective ?oAttrVersion .
        }}
    }}
    WHERE {{
        # On définit les deux combinaisons de statuts possibles
        VALUES (?meRem ?oRem) {{
            ("true"^^xsd:boolean  "false"^^xsd:boolean)
            ("false"^^xsd:boolean "true"^^xsd:boolean)
        }}

        ?attr peg:hasAttributeVersion ?attrVersion .
        ?attrVersion a peg:AttributeVersion ; peg:toRemove "true"^^xsd:boolean .

        # Les liens avec les changements
        ?meChange peg:toRemove ?meRem ; peg:makesEffective ?attrVersion .
        ?oChange peg:toRemove ?oRem ; peg:outdates ?attrVersion .

        # On récupère les versions de remplacement si elles existent
        OPTIONAL {{ ?meChange peg:outdates ?meAttrVersion . }}
        OPTIONAL {{ ?oChange peg:makesEffective ?oAttrVersion . }}
    }}
    """

    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)


def remove_elementary_changes_and_versions_to_remove(graphdb_url:URIRef, repository_name:str, tmp_named_graph_uri:URIRef):

    query = np.query_prefixes + f"""
    DELETE {{
        ?s ?p ?elem .
    ?elem ?p ?o .
    }}
    WHERE {{
        GRAPH {tmp_named_graph_uri.n3()} {{
            ?elem peg:toRemove "true"^^xsd:boolean .
            {{ ?s ?p ?elem }} UNION {{ ?elem ?p ?o }}
        }}
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def merge_similar_successive_attribute_versions(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    to_be_merged_with(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    generate_new_versions_for_successive_attribute_versions(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    transfer_attribute_versions_and_changes_in_facts_graph(graphdb_url, repository_name, facts_named_graph_uri, tmp_named_graph_uri)
    transfer_traces_of_attribute_versions_and_changes(graphdb_url, repository_name, inter_sources_named_graph_uri, tmp_named_graph_uri)
    
# Get attribute versions to merge
def to_be_merged_with(graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Get attribute versions to merge :
    * if an untraced change (a change ?cg such as ∄ ?cg peg:hasTrace ?cgTrace) makesEffective ?vME, outdates ?vO and ?vME has same version value as ?vO then ?vME has to be merged with ?vO
    
    """

    # Define if two consecutive versions has to be merged -> <previousVersion peg:toBeMergedWith nextVersion>
    query = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gt {{ ?vO peg:toBeMergedWith ?vME . }}
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

    gd.run_update_query(query, graphdb_url, repository_name)

def generate_new_versions_for_successive_attribute_versions(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef):
    """
    Merge similar successive attribute versions :
    * if an untraced change (a change ?cg such as ∄ ?cg peg:hasTrace ?cgTrace) makesEffective ?firstAttrVers, outdates ?lastAttrVers and ?firstAttrVers has same version value as ?lastAttrVers then all the versions from ?firstAttrVers to ?lastAttrVers (included) has to be merged into a new version ?newAttrVers and ?firstAttrVers, ?lastAttrVers and all the versions between them has to be marked as "toBeMergedWith ?newAttrVers"
    * the new version ?newAttrVers has to be linked to all the changes that made effective or outdated the versions between ?firstAttrVers and ?lastAttrVers (included) and has to be marked as a final attribute version (peg:isFinalAttributeElement "true"^^xsd:boolean)
    """
   
    query1 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gt {{
        ?attr peg:hasAttributeVersion ?newAttrVers .
        ?newAttrVers a peg:AttributeVersion ; peg:isFinalAttributeElement "true"^^xsd:boolean .
        ?meChange peg:makesEffective ?newAttrVers ; peg:isFinalAttributeElement "true"^^xsd:boolean .
        ?oChange peg:outdates ?newAttrVers ; peg:isFinalAttributeElement "true"^^xsd:boolean .
    }}
}}
WHERE {{
    {{
        SELECT ?gt ?attr ?firstAttrVers ?lastAttrVers ?meChange ?oChange WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            GRAPH ?gf {{ ?attr a peg:Attribute . }}
            GRAPH ?gt {{
                ?attr peg:hasAttributeVersion ?firstAttrVers .
                ?firstAttrVers a peg:AttributeVersion . }}
            {{
                ?firstAttrVers peg:toBeMergedWith+ ?lastAttrVers .
            }} UNION {{
                BIND(?firstAttrVers AS ?lastAttrVers)
            }}

            FILTER NOT EXISTS {{?av1 peg:toBeMergedWith ?firstAttrVers . }}
            FILTER NOT EXISTS {{?lastAttrVers peg:toBeMergedWith ?av2 . }}

            ?meChange peg:makesEffective ?firstAttrVers .
            ?oChange peg:outdates ?lastAttrVers .
        }}
    }}
    BIND(URI(CONCAT(STR(URI(facts:)), "AttributeVersion/", STRUUID())) AS ?newAttrVers)
}} 
"""
   
    query2 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gt {{ ?finalAttrVers peg:hasTrace ?attrVersTrace . }}
}} WHERE {{
    BIND({tmp_named_graph_uri.n3()} AS ?gt)
    GRAPH ?gt {{ 
        ?firstAttrVers a peg:AttributeVersion .
        ?finalAttrVers peg:isFinalAttributeElement "true"^^xsd:boolean .
    }}
    FILTER NOT EXISTS {{ ?firstAttrVers peg:isFinalAttributeElement "true"^^xsd:boolean }}

    {{
        ?firstAttrVers peg:toBeMergedWith+ ?attrVers  .
    }} UNION {{
        BIND(?firstAttrVers AS ?attrVers)
    }}

    ?attrVers peg:hasTrace ?attrVersTrace .
    ?meChange peg:makesEffective ?firstAttrVers, ?finalAttrVers .
}}
"""
   
    queries = [query1, query2]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def transfer_attribute_versions_and_changes_in_facts_graph(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, tmp_named_graph_uri:URIRef
):
    
    query1 = np.query_prefixes + f"""
    INSERT {{
    GRAPH ?gf {{
        ?attr peg:hasAttributeVersion ?attrVers .
        ?attrVers a peg:AttributeVersion .
        ?meChange peg:makesEffective ?attrVers .
        ?oChange peg:outdates ?attrVers .
    }}
}} WHERE {{
    BIND({tmp_named_graph_uri.n3()} AS ?gt)
    BIND({facts_named_graph_uri.n3()} AS ?gf)
    GRAPH ?gf {{ ?attr a peg:Attribute . }}
    GRAPH ?gt {{
        ?attr peg:hasAttributeVersion ?attrVers .
        ?attrVers peg:isFinalAttributeElement "true"^^xsd:boolean .
        ?meChange peg:makesEffective ?attrVers .
        ?oChange peg:outdates ?attrVers .
    }}
}}
"""

    query2 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{ 
        ?change a peg:AttributeChange ;peg:isChangeType ctype:AttributeVersionTransition ; peg:appliedTo ?attr ; peg:dependsOn ?event . 
    	?event a peg:Event .
    }}  
}} WHERE {{ 
    {{
        SELECT ?gf ?attr ?change WHERE {{
            BIND({tmp_named_graph_uri.n3()} AS ?gt)
            BIND({facts_named_graph_uri.n3()} AS ?gf)
            GRAPH ?gf {{ ?attr a peg:Attribute . }}
            GRAPH ?gt {{ ?change peg:appliedTo ?attr ; peg:isFinalAttributeElement "true"^^xsd:boolean . }}
        }}   
    }}
    BIND(URI(CONCAT(STR(URI(facts:)), "Event/", STRUUID())) AS ?event)
}}
"""
    
    query3 = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gf {{ ?event ?propTimeInstant ?eventTime . }}
}}
WHERE {{
    BIND({facts_named_graph_uri.n3()} AS ?gf)
    BIND({tmp_named_graph_uri.n3()} AS ?gt)
    GRAPH ?gf {{?attr a peg:Attribute . }}
    GRAPH ?gt {{ ?change peg:isFinalAttributeElement "true"^^xsd:boolean . }}
    ?change peg:appliedTo ?attr ; peg:dependsOn ?event ; peg:hasRelatedTime ?time .
    {{ 
        ?time a peg:CrispTimeInstant .
        BIND(peg:hasTime AS ?propTimeInstant)
        BIND(?time AS ?eventTime)
    }} UNION {{
        VALUES (?propTimeInstant ?propFuzzyTimeInstant) {{
            (peg:hasTimeAfter peg:hasFuzzyBeginning)
            (peg:hasTimeBefore peg:hasFuzzyEnd)
        }}
        ?time ?propFuzzyTimeInstant ?eventTime .
    }}
}} 
"""
    
    queries = [query1, query2, query3]
    gd.run_multiple_update_queries(queries, graphdb_url, repository_name)

def transfer_traces_of_attribute_versions_and_changes(
        graphdb_url:URIRef, repository_name:str,
        inter_sources_name_graph_uri:URIRef, tmp_named_graph_uri:URIRef
):
    """
    Transfer traces of attribute versions and changes to the facts graph :
    * for each final attribute version ?attrVers, transfer its trace ?attrVersTrace to the graph of sources as trace of the attribute ?attr (which is the subject of ?attrVers)
    * for each change ?change, transfer its trace ?changeTrace to the graph of sources as trace of the attribute ?attr to which the change is applied (which is the subject of ?change peg:appliedTo ?attr)
    """
    
    query = np.query_prefixes + f"""
INSERT {{
    GRAPH ?gi {{ ?attrElem peg:hasTrace ?attrElemTrace . }}
}} WHERE {{
    BIND({tmp_named_graph_uri.n3()} AS ?gt)
    BIND({inter_sources_name_graph_uri.n3()} AS ?gi)
    GRAPH ?gt {{
        ?attrElem peg:isFinalAttributeElement "true"^^xsd:boolean .
    }}
    ?attrElem peg:hasTrace ?attrElemTrace .
}}
"""
    
    gd.run_update_query(query, graphdb_url, repository_name)

####################################### Transform event bounds to fuzzy times ########################################

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
        BIND(URI(CONCAT(STR(facts:), "TimeInstant/", STRUUID())) AS ?generatedTime)
        BIND(COALESCE(?time, ?generatedTime) AS ?finalTime)
    }}
    """

    # 2. Associer les événements à leur FuzzyTimeInstant (existant ou nouveau)
    # query2 = np.query_prefixes + f"""
    # INSERT {{
    #     GRAPH ?gf {{ ?ev peg:hasTime ?finalTime . }}
    # }}
    # WHERE {{
    #     BIND({facts_named_graph_uri.n3()} AS ?gf)
    #     GRAPH ?gf {{ 
    #         ?ev a peg:Event .
    #         OPTIONAL {{ ?ev peg:hasTimeBefore ?tBefore . }}
    #         OPTIONAL {{ ?ev peg:hasTimeAfter ?tAfter . }}

    #         FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }}
    #         FILTER (BOUND(?tBefore) || BOUND(?tAfter))

    #         # On retrouve le FuzzyTimeInstant correspondant (forcément présent grâce à query1)
    #         ?finalTime a peg:FuzzyTimeInstant .
    #         OPTIONAL {{ ?finalTime peg:hasFuzzyBeginning ?tAfterFuzzy . }}
    #         OPTIONAL {{ ?finalTime peg:hasFuzzyEnd ?tBeforeFuzzy . }}

    #         FILTER (
    #             ( (!BOUND(?tAfter) && !BOUND(?tAfterFuzzy)) || (sameterm(?tAfter, ?tAfterFuzzy)) ) &&
    #             ( (!BOUND(?tBefore) && !BOUND(?tBeforeFuzzy)) || (sameterm(?tBefore, ?tBeforeFuzzy)) )
    #         )
    #     }}
    # }}
    # """

    query2 = np.query_prefixes + f"""
    INSERT {{
        GRAPH ?gf {{ ?ev peg:hasTime ?finalTime . }}
    }}
    WHERE {{
    BIND({facts_named_graph_uri.n3()} AS ?gf)
    GRAPH ?gf {{ 
        ?ev a peg:Event .
        FILTER NOT EXISTS {{ ?ev peg:hasTime ?x }}
        ?finalTime a peg:FuzzyTimeInstant .
        {{ 
            ?ev peg:hasTimeBefore ?tBefore .
            ?ev peg:hasTimeAfter ?tAfter .
            ?finalTime peg:hasFuzzyBeginning ?tAfter ; peg:hasFuzzyEnd ?tBefore .
        }} UNION {{
			?ev peg:hasTimeBefore ?tBefore .
            FILTER NOT EXISTS {{ ?ev peg:hasTimeAfter ?tAfter . }}
            ?finalTime peg:hasFuzzyEnd ?tBefore .
            FILTER NOT EXISTS {{ ?finalTime peg:hasFuzzyBeginning ?tAfter . }}
        }} UNION {{
			?ev peg:hasTimeAfter ?tAfter .
            FILTER NOT EXISTS {{ ?ev peg:hasTimeBefore ?tBefore . }}
            ?finalTime peg:hasFuzzyBeginning ?tAfter .
            FILTER NOT EXISTS {{ ?finalTime peg:hasFuzzyEnd ?tBefore . }}
        }}

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