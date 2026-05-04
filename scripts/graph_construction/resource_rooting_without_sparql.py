import uuid
from rdflib import URIRef, Graph
from scripts.graph_construction.namespaces import NameSpaces
from scripts.resource_management import resource_initialisation as ri
from scripts.utils import time_processing as tp
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import graphrdf as gr


np = NameSpaces()

######### Main function

# Function to rely all resources from `factoids_named_graph_uri` named graph to similar resources in `facts_named_graph_uri` (if they exists, else create the similar resource)
# Triple to tell similarity is store in `inter_sources_named_graph_uri`

def link_factoids_with_facts(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, labels_named_graph_uri:URIRef,
        ttl_file:str):
    """
    Landmarks are created as follows:
        * creation of links (using `peg:hasRoot`) between landmarks in the facts named graph and those which are in the factoid named graph ;
        * using inference rules, new `peg:hasRoot` links are deduced
        * for each resource defined in the factoids, we check whether it exists in the fact graph (if it is linked with a `peg:hasRoot` to a resource in the fact graph)
        * for unlinked factoid resources, we create its equivalent in the fact graph
    """

    label_property = np.SKOS.hiddenLabel

    make_rooting_for_landmarks(graphdb_url, repository_name, label_property, facts_named_graph_uri, inter_sources_named_graph_uri, labels_named_graph_uri, ttl_file)
    make_rooting_for_landmark_relations(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    make_rooting_for_landmark_attributes(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    make_rooting_for_temporal_entities(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    
    # # Les racines de modification sont créées sauf pour les modifications d'attributs.
    make_rooting_for_changes(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    make_rooting_for_events(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)

    manage_labels_after_landmark_rooting(graphdb_url, repository_name, facts_named_graph_uri)

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

def make_rooting_for_landmarks(
        graphdb_url:URIRef, repository_name:str, label_property:URIRef,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, labels_named_graph_uri:URIRef, ttl_file:str):
    
    landmarks_types = [np.LTYPE["Municipality"], np.LTYPE["District"], np.LTYPE["PostalCodeArea"], np.LTYPE["Thoroughfare"]]
    make_rooting_for_landmarks_according_to_label(
        graphdb_url, repository_name, landmarks_types, label_property,
        facts_named_graph_uri, inter_sources_named_graph_uri, labels_named_graph_uri, ttl_file)

    lm_and_lr_type_uris = [
        [np.LTYPE["HouseNumber"], np.LRTYPE["Belongs"]],
        [np.LTYPE["DistrictNumber"], np.LRTYPE["Belongs"]],
        [np.LTYPE["StreetNumber"], np.LRTYPE["Belongs"]],
    ]

    make_rooting_for_landmarks_according_to_label_and_relation(
        graphdb_url, repository_name, lm_and_lr_type_uris, label_property,
        facts_named_graph_uri, inter_sources_named_graph_uri, labels_named_graph_uri, ttl_file)

def make_rooting_for_landmarks_according_to_label(
        graphdb_url:URIRef, repository_name:str,
        landmark_types:list[URIRef], label_property:URIRef,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, labels_named_graph_uri:URIRef, ttl_file:str):
    
    landmark_var = "landmark"
    landmark_type_var = "landmarkType"
    landmark_label_var = "landmarkLabel"

    factoids, facts = select_landmarks_to_root_according_to_label(graphdb_url, repository_name, facts_named_graph_uri, label_property, landmark_types)
    gf, gi, gl = reconcile_landmarks_according_to_label(factoids, facts, label_property, landmark_var, landmark_type_var, landmark_label_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri), (gl, labels_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_landmarks_according_to_label_and_relation(
        graphdb_url:URIRef, repository_name:str,
        lm_and_lr_type_uris:list[URIRef], label_property:URIRef,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef, labels_named_graph_uri:URIRef, ttl_file:str):
    
    landmark_var = "landmark"
    landmark_type_var = "landmarkType"
    landmark_label_var = "landmarkLabel"
    landmark_relation_var = "landmarkRelation"
    landmark_relation_type_var = "landmarkRelationType"
    root_relatum_var = "rootRelatum"

    factoids, facts = select_landmarks_to_root_according_to_label_and_relation(
        graphdb_url, repository_name, facts_named_graph_uri, label_property, lm_and_lr_type_uris,
        landmark_var, landmark_type_var, landmark_label_var, landmark_relation_var, landmark_relation_type_var, root_relatum_var)

    gf, gi, gl = reconcile_landmarks_with_label_and_relation(factoids, facts, label_property, landmark_var, landmark_type_var, landmark_label_var)
    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri), (gl, labels_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)


def make_rooting_for_landmark_relations(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    landmark_relation_var = "landmarkRelation"
    landmark_relation_type_var = "landmarkRelationType"
    root_locatum_var = "locatum"
    root_relatum_var = "relatum"

    factoids, facts = select_landmark_relations_to_root_according_to_label(
        graphdb_url, repository_name, facts_named_graph_uri,
        landmark_relation_var, landmark_relation_type_var, root_locatum_var, root_relatum_var)
    gf, gi = reconcile_landmark_relations(factoids, facts, landmark_relation_var, landmark_relation_type_var, root_locatum_var, root_relatum_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_landmark_attributes(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    attribute_var = "attribute"
    attribute_type_var = "attributeType"
    root_landmark_var = "rootLandmark"

    factoids, facts = select_landmark_attributes_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        attribute_var, attribute_type_var, root_landmark_var)
    gf, gi = reconcile_landmark_attributes(factoids, facts, attribute_var, attribute_type_var, root_landmark_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_temporal_entities(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    make_rooting_for_crisp_time_instants(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    make_rooting_for_fuzzy_time_instants(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)
    make_rooting_for_time_intervals(graphdb_url, repository_name, facts_named_graph_uri, inter_sources_named_graph_uri, ttl_file)

def make_rooting_for_crisp_time_instants(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    time_var = "time"
    time_stamp_var = "timeStamp"
    time_precision_var = "timePrecision"
    time_calendar_var = "timeCalendar"

    factoids, facts = select_crisp_time_instants_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        time_var, time_stamp_var, time_precision_var, time_calendar_var)
    gf, gi = reconcile_crisp_time_instants(factoids, facts, time_var, time_stamp_var, time_precision_var, time_calendar_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_fuzzy_time_instants(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    time_var = "time"
    time_start_var = "fuzzyTimeStart"
    time_end_var = "fuzzyTimeEnd"

    factoids, facts = select_fuzzy_time_instants_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        time_var, time_start_var, time_end_var)
    gf, gi = reconcile_fuzzy_time_instants(factoids, facts, time_var, time_start_var, time_end_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_time_intervals(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    time_var = "time"
    time_start_var = "timeStart"
    time_end_var = "timeEnd"

    factoids, facts = select_time_intervals_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        time_var, time_start_var, time_end_var)
    gf, gi = reconcile_time_intervals(factoids, facts, time_var, time_start_var, time_end_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_changes(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    change_var = "change"
    change_type_var = "changeType"
    applied_to_var = "appliedTo"

    factoids, facts = select_changes_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        change_var, change_type_var, applied_to_var)
    gf, gi = reconcile_changes(factoids, facts, change_var, change_type_var, applied_to_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

def make_rooting_for_events(
        graphdb_url:URIRef, repository_name:str,
        facts_named_graph_uri:URIRef, inter_sources_named_graph_uri:URIRef,
        ttl_file:str):
    
    event_var = "event"
    related_change_var = "relatedChange"

    factoids, facts = select_events_to_root(
        graphdb_url, repository_name, facts_named_graph_uri,
        event_var, related_change_var)
    gf, gi = reconcile_events(factoids, facts, event_var, related_change_var)

    for (g, named_graph_uri) in [(gf, facts_named_graph_uri), (gi, inter_sources_named_graph_uri)]:
        g.serialize(destination=ttl_file, format="turtle")
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ttl_file, named_graph_uri=named_graph_uri)

#### Concilisation functions ####

def reconcile_landmarks_according_to_label(
        factoids:list[dict], facts:list[dict], hidden_label_property: URIRef,
        landmark_var:str="landmark", landmark_type_var:str="landmarkType", landmark_label_var:str="landmarkLabel"):
    """
    Réconcilie les entités en utilisant les objets Literal et URI bruts.
    """
    g_f, g_i, g_l = Graph(), Graph(), Graph()

    def _get_signature(item):
        return f"label={item[landmark_label_var].n3()}&type={item[landmark_type_var].n3()}" # On peut aussi concaténer les n3 pour éviter les problèmes de hashabilité des tuples avec des URIRef

    # --- Étape 1 : Indexation sans transformation ---
    # On utilise directement la valeur telle quelle (sensible à la casse si non traitée en amont)
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[landmark_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        label_obj = x[landmark_label_var] # On garde l'objet rdflib.term.Literal
        type_x = x[landmark_type_var]
        uri_factoid = x[landmark_var]
        
        # La clé utilise la string pour le dictionnaire, mais on garde l'objet pour RDF
        key = _get_signature(x)

        if key in index_facts:
            uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, uri_fact, uri_factoid)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            uri_fact = URIRef(np.FACTS[f"Landmark/{uuid.uuid4().hex}"])
            
            # 1. Graphe de faits : Typage
            ri.create_landmark(g_f, uri_fact, None, type_x)
            
            # 2. Graphe de labels : On réutilise l'objet Literal 'label_obj'
            g_l.add((uri_fact, hidden_label_property, label_obj))
            
            # 3. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, uri_fact, uri_factoid)
            
            # 4. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = uri_fact
            
    return g_f, g_i, g_l

def reconcile_landmarks_with_label_and_relation(
        factoids: list[dict], facts: list[dict], hidden_label_property: URIRef,
        landmark_var: str = "landmark", landmark_type_var: str = "landmarkType", landmark_label_var: str = "landmarkLabel",
        landmark_relation_var: str = "landmarkRelation", landmark_relation_type_var: str = "landmarkRelationType", root_relatum_var: str = "rootRelatum"):
    
    g_f, g_i, g_l = Graph(), Graph(), Graph()

    def _get_signature(item):
        return f"label={item[landmark_label_var].n3()}&type={item[landmark_type_var].n3()}&relationType={item[landmark_relation_type_var].n3()}&relRoot={item[root_relatum_var].n3()}" # On peut aussi concaténer les n3 pour éviter les problèmes de hashabilité des tuples avec des URIRef
    
    # --- Étape 1 : Indexation avec Triplet (Label, Type, Parent) ---
    index_facts = {}
    for y in facts:
        # Clé composite : (Texte du label, URI du type, URI de la rue/parent)
        key = _get_signature(y)

        index_facts[key] = {landmark_var: y[landmark_var], landmark_relation_var: y[landmark_relation_var], landmark_relation_type_var: y[landmark_relation_type_var]}

    # --- Étape 2 : Traitement ---
    for x in factoids:
        lm_label = x[landmark_label_var]
        lm_type = x[landmark_type_var]
        lm = x[landmark_var]
        lr = x[landmark_relation_var]
        lr_type = x[landmark_relation_type_var]
        rel_root_x = x[root_relatum_var] # L'entité parente de référence
        
        key = _get_signature(x)

        if key in index_facts:
            # Correspondance trouvée dans la même rue
            lm_uri_fact = index_facts[key][landmark_var]
            lr_uri_fact = index_facts[key][landmark_relation_var]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, lm_uri_fact, lm)
            ri.create_trace_and_root_links(g_i, lr_uri_fact, lr)
            
        else:
            # Nouveau numéro dans cette rue
            lm_uri_fact = gr.generate_uri(np.FACTS, "Landmark", separator="/")
            lr_uri_fact = gr.generate_uri(np.FACTS, "LandmarkRelation", separator="/")

            # 1. Graphe de faits
            ri.create_landmark(g_f, lm_uri_fact, None, lm_type)
            ri.create_landmark_relation(g_f, lr_uri_fact, lr_type, lm_uri_fact, [rel_root_x])
          
            # 2. Graphe de labels
            g_l.add((lm_uri_fact, hidden_label_property, lm_label))
            
            # 3. Graphe inter-sources
            ri.create_trace_and_root_links(g_i, lm_uri_fact, lm)
            ri.create_trace_and_root_links(g_i, lr_uri_fact, lr)
            
            # 4. Mise à jour de l'index
            index_facts[key] = {landmark_var: lm_uri_fact, landmark_relation_var: lr_uri_fact, landmark_relation_type_var: lr_type}
    return g_f, g_i, g_l


def group_relatum_by_relation(data_list, id_key, value_key):
    """
    Regroupe les valeurs de 'relatum' dans une liste pour chaque 'landmarkRelation' unique.
    
    :param data_list: Liste de dictionnaires initiale
    :param id_key: La clé de pivot
    :param value_key: La clé dont les valeurs doivent être listées
    :return: Une nouvelle liste de dictionnaires regroupés
    """
    acc = {}

    for item in data_list:
        pivot_value = item[id_key]
        
        if pivot_value not in acc:
            # On crée une copie pour ne pas modifier l'original
            # et on initialise la liste pour la valeur à regrouper
            new_item = item.copy()
            new_item[value_key] = [item[value_key]]
            acc[pivot_value] = new_item
        else:
            # Si le pivot existe déjà, on ajoute la nouvelle valeur à la liste
            acc[pivot_value][value_key].append(item[value_key])

    return list(acc.values())

def reconcile_landmark_relations(
        factoids: list[dict], facts: list[dict],
        landmark_relation_var: str="landmarkRelation", landmark_relation_type_var: str="landmarkRelationType",
        root_locatum_var: str="rootLocatum", root_relatum_var: str="rootRelatum"):
    g_f, g_i = Graph(), Graph()

    factoids = group_relatum_by_relation(factoids, id_key=landmark_relation_var, value_key=root_relatum_var)
    facts = group_relatum_by_relation(facts, id_key=landmark_relation_var, value_key=root_relatum_var)

    def _get_signature(item):
        # 1. On récupère la liste des URIs (rel_root_list est une liste de URIRef)
        rel_root_list = item[root_relatum_var] 
        
        # 2. On transforme chaque URI en n3(), on trie la liste par ordre alphabétique
        #    puis on les joint avec le caractère '|'
        rel_root_string = "|".join(sorted([uri.n3() for uri in rel_root_list]))

        return f"relationType={item[landmark_relation_type_var].n3()}&locRoot={item[root_locatum_var].n3()}&relRoot={rel_root_string}"
    
    # --- Étape 1 : Indexation avec Triplet (Type de relation, Racine du locatum, Racine du relatum) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[landmark_relation_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        lr_type = x[landmark_relation_type_var]
        loc_root = x[root_locatum_var]
        rel_roots = x[root_relatum_var] # C'est une liste
        lr = x[landmark_relation_var]

        key = _get_signature(x)

        if key in index_facts:
            lr_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, lr_uri_fact, lr)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            lr_uri_fact = gr.generate_uri(np.FACTS, "LandmarkRelation", separator="/")
            
            # 1. Graphe de faits : Typage et liens avec les racines
            ri.create_landmark_relation(g_f, lr_uri_fact, lr_type, loc_root, rel_roots)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, lr_uri_fact, lr)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = lr_uri_fact
            
    return g_f, g_i

def reconcile_landmark_attributes(
        factoids:list[dict], facts:list[dict],
        attribute_var:str="attribute", attribute_type_var:str="attributeType", root_landmark_var:str="rootLandmark"):
    
    g_f, g_i = Graph(), Graph()

    def _get_signature(item):
        return f"type={item[attribute_type_var].n3()}&rootLandmark={item[root_landmark_var].n3()}" # On peut aussi concaténer les n3 pour éviter les problèmes de hashabilité des tuples avec des URIRef
    
    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[attribute_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        attr_type = x[attribute_type_var]
        root_entity = x[root_landmark_var]
        attr = x[attribute_var]

        key = _get_signature(x)

        if key in index_facts:
            attr_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, attr_uri_fact, attr)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            attr_uri_fact = gr.generate_uri(np.FACTS, "Attribute", separator="/")
            
            # 1. Graphe de faits : Typage et lien avec la racine
            ri.create_landmark_attribute(g_f, attr_uri_fact, attr_type, root_entity)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, attr_uri_fact, attr)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = attr_uri_fact
    
    return g_f, g_i

def reconcile_crisp_time_instants(
        factoids:list[dict], facts:list[dict],
        time_var:str="time", time_stamp_var:str="timeStamp", time_precision_var:str="timePrecision", time_calendar_var:str="timeCalendar"):
    
    g_f, g_i = Graph(), Graph()

    def _get_signature(item):
        return tp.get_standardized_date(item[time_stamp_var], item[time_calendar_var], item[time_precision_var])
    
    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[time_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        time_stamp = x[time_stamp_var]
        time_precision = x[time_precision_var]
        time_calendar = x[time_calendar_var]
        time_entity = x[time_var]

        key = _get_signature(x)

        if key in index_facts:
            time_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            time_uri_fact = gr.generate_uri(np.FACTS, "CrispTimeInstant", separator="/")
            
            # 1. Graphe de faits : Typage et propriétés temporelles
            ri.create_crisp_time_instant(g_f, time_uri_fact, time_stamp, time_calendar, time_precision)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = time_uri_fact
    
    return g_f, g_i

def reconcile_fuzzy_time_instants(
        factoids: list[dict], facts: list[dict],
        time_var: str="time", time_start_var: str="fuzzyStart", time_end_var: str="fuzzyEnd") -> tuple[Graph, Graph]:
    
    g_f, g_i = Graph(), Graph()

    def _get_signature(item):
        return f"start={item[time_start_var].n3()}&end={item[time_end_var].n3()}"
    
    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[time_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        time_start = x[time_start_var]
        time_end = x[time_end_var]
        time_entity = x[time_var]

        key = _get_signature(x)

        if key in index_facts:
            time_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            time_uri_fact = gr.generate_uri(np.FACTS, "FuzzyTimeInstant", separator="/")
            
            # 1. Graphe de faits : Typage et propriétés temporelles
            ri.create_fuzzy_time_instant(g_f, time_uri_fact, time_start, time_end)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = time_uri_fact

    return g_f, g_i

def reconcile_time_intervals(
        factoids: list[dict], facts: list[dict],
        time_var: str="time", time_start_var: str="timeStart", time_end_var: str="timeEnd") -> tuple[Graph, Graph]:
    
    g_f, g_i = Graph(), Graph()

    def _get_signature(item):
        return f"start={item[time_start_var].n3()}&end={item[time_end_var].n3()}"
    
    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[time_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        time_start = x[time_start_var]
        time_end = x[time_end_var]
        time_entity = x[time_var]

        key = _get_signature(x)

        if key in index_facts:
            time_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            time_uri_fact = gr.generate_uri(np.FACTS, "TimeInterval", separator="/")
            
            # 1. Graphe de faits : Typage et propriétés temporelles
            ri.create_crisp_time_interval(g_f, time_uri_fact, time_start, time_end)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, time_uri_fact, time_entity)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = time_uri_fact

    return g_f, g_i


def reconcile_changes(
        factoids: list[dict], facts: list[dict],
        change_var: str="change", change_type_var: str="changeType", applied_to_var: str="appliedTo") -> tuple[Graph, Graph]:
    
    g_f, g_i = Graph(), Graph()

    def _get_signature(item):
        return f"type={item[change_type_var].n3()}&appliedTo={item[applied_to_var].n3()}"
    
    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[change_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        change_type = x[change_type_var]
        applied_to = x[applied_to_var]
        change_entity = x[change_var]

        key = _get_signature(x)

        if key in index_facts:
            change_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, change_uri_fact, change_entity)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            change_uri_fact = gr.generate_uri(np.FACTS, "Change", separator="/")
            
            # 1. Graphe de faits : Typage et propriétés de changement
            ri.create_change_with_applied_to(g_f, change_uri_fact, change_type, applied_to)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, change_uri_fact, change_entity)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = change_uri_fact

    return g_f, g_i

def reconcile_events(
    factoids: list[dict], facts: list[dict],
    event_var: str="event", related_change_var: str="relatedChange") -> tuple[Graph, Graph]:

    g_f, g_i = Graph(), Graph()
    def _get_signature(item):
        return f"relatedChange={item[related_change_var].n3()}"

    # --- Étape 1 : Indexation avec Triplet (Type, Racine de l'entité liée) ---
    index_facts = {}
    for y in facts:
        key = _get_signature(y)
        index_facts[key] = y[event_var]

    # --- Étape 2 : Traitement ---
    for x in factoids:
        related_change = x[related_change_var]
        event_entity = x[event_var]

        key = _get_signature(x)

        if key in index_facts:
            event_uri_fact = index_facts[key]
            
            # Liens d'alignement inter-sources
            ri.create_trace_and_root_links(g_i, event_uri_fact, event_entity)
            
        else:
            # Création de la nouvelle entité consolidée (Fait)
            event_uri_fact = gr.generate_uri(np.FACTS, "Event", separator="/")
            
            # 1. Graphe de faits : Typage et propriétés de l'événement
            ri.create_event(g_f, event_uri_fact)
            ri.create_change_event_relation(g_f, related_change, event_uri_fact)
            
            # 2. Graphe inter-sources : Provenance
            ri.create_trace_and_root_links(g_i, event_uri_fact, event_entity)
            
            # 3. Mise à jour de l'index pour les itérations suivantes de la boucle
            index_facts[key] = event_uri_fact

    return g_f, g_i


###### SPARQL queries to select landmarks in the factoids and facts graphs, with or without relation context #######

def select_landmarks_to_root_according_to_label_and_relation(
        graphdb_url: URIRef, repository_name: str, facts_named_graph_uri: URIRef, label_property: URIRef, lm_and_lr_type_uris: list[list[URIRef]],
        landmark_var: str = "landmark", landmark_type_var: str = "landmarkType", landmark_label_var: str = "landmarkLabel",
        landmark_relation_var: str = "landmarkRelation", landmark_relation_type_var: str = "landmarkRelationType", root_relatum_var: str = "rootRelatum"):
    
    variables = [landmark_relation_var, landmark_relation_type_var, landmark_var, landmark_type_var, landmark_label_var, root_relatum_var]

    formatted_values = ' '.join([f"({pair[0].n3()} {pair[1].n3()})" for pair in lm_and_lr_type_uris])

    query_factoids = np.query_prefixes + f"""
    SELECT DISTINCT ?{landmark_relation_var} ?{landmark_relation_type_var} ?{landmark_var} ?{landmark_type_var} ?{landmark_label_var} ?{root_relatum_var} WHERE {{
        VALUES (?{landmark_type_var} ?{landmark_relation_type_var}) {{ {formatted_values} }}
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{
            ?{landmark_relation_var} a ?lrClass .
            ?{landmark_var} a peg:Landmark .
        }}
        GRAPH ?gf {{ ?{root_relatum_var} a ?rRelClass . }} 
        ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
        ?{landmark_relation_var} peg:isLandmarkRelationType ?{landmark_relation_type_var} ; 
                peg:locatum ?{landmark_var} ; 
                peg:relatum [peg:hasRoot ?{root_relatum_var}] .
        ?{landmark_var} peg:isLandmarkType ?{landmark_type_var} ; {label_property.n3()} ?{landmark_label_var} .
        
        FILTER NOT EXISTS {{
            ?{landmark_var} peg:hasRoot ?x .
            GRAPH ?gf {{ ?x a peg:Landmark . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT DISTINCT ?{landmark_relation_var} ?{landmark_relation_type_var} ?{landmark_var} ?{landmark_type_var} ?{landmark_label_var} ?{root_relatum_var} WHERE {{
        VALUES (?{landmark_type_var} ?{landmark_relation_type_var}) {{ {formatted_values} }}
        GRAPH {facts_named_graph_uri.n3()} {{
            ?{landmark_relation_var} a ?lrClass .
            ?{landmark_var} a peg:Landmark .
            ?{root_relatum_var} a ?rRelClass .
        }}
        ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
        ?{landmark_relation_var} peg:isLandmarkRelationType ?{landmark_relation_type_var} ; 
                peg:locatum ?{landmark_var} ; 
                peg:relatum ?{root_relatum_var} .
        ?{landmark_var} peg:isLandmarkType ?{landmark_type_var} ; {label_property.n3()} ?{landmark_label_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)
    return factoids, facts


def select_landmarks_to_root_according_to_label(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef, label_property:URIRef, landmark_types:list[URIRef],
        landmark_var:str="landmark", landmark_type_var:str="landmarkType", landmark_label_var:str="landmarkLabel"):
    
    variables = [landmark_var, landmark_type_var, landmark_label_var]
    formatted_values = ' '.join([lt.n3() for lt in landmark_types])
    query_factoids = np.query_prefixes + f"""
    SELECT ?{landmark_var} ?{landmark_type_var} ?{landmark_label_var} WHERE {{
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        VALUES ?{landmark_type_var} {{ {formatted_values} }}
        GRAPH ?g {{ ?{landmark_var} a peg:Landmark . }}
        ?{landmark_var} peg:isLandmarkType ?{landmark_type_var} ; {label_property.n3()} ?{landmark_label_var} .
            FILTER NOT EXISTS {{
            ?{landmark_var} peg:hasRoot ?x .
            GRAPH {facts_named_graph_uri.n3()} {{ ?x a peg:Landmark . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{landmark_var} ?{landmark_type_var} ?{landmark_label_var} WHERE {{
        VALUES ?{landmark_type_var} {{ {formatted_values} }}
        GRAPH {facts_named_graph_uri.n3()} {{ ?{landmark_var} a peg:Landmark . }}
        ?{landmark_var} peg:isLandmarkType ?{landmark_type_var} ; {label_property.n3()} ?{landmark_label_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_landmark_relations_to_root_according_to_label(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        landmark_relation_var:str="landmarkRelation", landmark_relation_type_var:str="landmarkRelationType",
        root_locatum_var:str="rootLocatum", root_relatum_var:str="rootRelatum"):
    
    variables = [landmark_relation_var, landmark_relation_type_var, root_locatum_var, root_relatum_var]

    query_factoids = np.query_prefixes + f"""
    SELECT ?{landmark_relation_var} ?{landmark_relation_type_var} ?{root_locatum_var} ?{root_relatum_var} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{landmark_relation_var} a ?lrClass . }}
        GRAPH ?gf {{
            ?{root_locatum_var} a ?rLocClass .
            ?{root_relatum_var} a ?rRelClass .
        }}
        ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
        ?{landmark_relation_var} peg:isLandmarkRelationType ?{landmark_relation_type_var} ; 
                peg:locatum [peg:hasRoot ?{root_locatum_var} ] ;
                peg:relatum [peg:hasRoot ?{root_relatum_var} ] .
            FILTER NOT EXISTS {{
            ?{landmark_relation_var} peg:hasRoot ?x .
            GRAPH ?gf {{ ?x a ?xClass. }}
        }}
    }}
    """
    
    query_facts = np.query_prefixes + f"""
    SELECT ?{landmark_relation_var} ?{landmark_relation_type_var} ?{root_locatum_var} ?{root_relatum_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{
            ?{landmark_relation_var} a ?lrClass .
            ?{root_locatum_var} a ?rLocClass .
            ?{root_relatum_var} a ?rRelClass .
        }}
        ?lrClass rdfs:subClassOf* peg:LandmarkRelation .
        ?{landmark_relation_var} peg:isLandmarkRelationType ?{landmark_relation_type_var} ; 
                peg:locatum [peg:hasRoot ?{root_locatum_var} ] ;
                peg:relatum [peg:hasRoot ?{root_relatum_var} ] .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_landmark_attributes_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        attribute_var:str="attribute", attribute_type_var:str="attributeType", root_landmark_var:str="rootLandmark"):
    
    variables = [attribute_var, attribute_type_var, root_landmark_var]
    query_factoids = np.query_prefixes + f"""
    SELECT ?{attribute_var} ?{attribute_type_var} ?{root_landmark_var} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{attribute_var} a peg:Attribute . }}
        GRAPH ?gf {{ ?{root_landmark_var} a ?rlClass . }}
        [peg:hasRoot ?{root_landmark_var}] peg:hasAttribute ?{attribute_var} .
        ?{attribute_var} peg:isAttributeType ?{attribute_type_var} .
            FILTER NOT EXISTS {{
            ?{attribute_var} peg:hasRoot ?x .
            GRAPH ?gf {{ ?x a peg:Attribute . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{attribute_var} ?{attribute_type_var} ?{root_landmark_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{
            ?{attribute_var} a peg:Attribute .
            ?{root_landmark_var} a ?rLmClass .    
        }}
        ?{attribute_var} peg:isAttributeType ?{attribute_type_var} .
        ?{root_landmark_var} peg:hasAttribute ?{attribute_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_crisp_time_instants_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        time_var:str="time", time_stamp_var:str="timeStamp", time_precision_var:str="timePrecision", time_calendar_var:str="timeCalendar"):
    
    variables = [time_var, time_stamp_var, time_precision_var, time_calendar_var]
    query_factoids = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_stamp_var} ?{time_precision_var} ?{time_calendar_var} WHERE {{
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{time_var} a peg:CrispTimeInstant . }}
        ?{time_var} peg:timeStamp ?{time_stamp_var} ;
                  peg:timePrecision ?{time_precision_var} ;
                  peg:timeCalendar ?{time_calendar_var} .
            FILTER NOT EXISTS {{
                ?{time_var} peg:hasRoot ?x .
                GRAPH {facts_named_graph_uri.n3()} {{ ?x a peg:CrispTimeInstant . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_stamp_var} ?{time_precision_var} ?{time_calendar_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{time_var} a peg:CrispTimeInstant . }}
        ?{time_var} peg:timeStamp ?{time_stamp_var} ;
                  peg:timePrecision ?{time_precision_var} ;
                  peg:timeCalendar ?{time_calendar_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_fuzzy_time_instants_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        time_var:str="time", time_start_var:str="timeStart", time_end_var:str="timeEnd"):
    
    variables = [time_var, time_start_var, time_end_var]
    query_factoids = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_start_var} ?{time_end_var} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{time_var} a peg:FuzzyTimeInstant . }}
        GRAPH ?gf {{
            ?{time_start_var} a ?tsClass .
            ?{time_end_var} a ?teClass .
        }} 
        ?{time_var} peg:hasBeginning [peg:hasRoot ?{time_start_var}] ;
                  peg:hasEnd [peg:hasRoot ?{time_end_var}] .
        FILTER NOT EXISTS {{
            ?{time_var} peg:hasRoot ?x .
            GRAPH ?gf {{ ?x a peg:FuzzyTimeInstant . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_start_var} ?{time_end_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{time_var} a peg:FuzzyTimeInstant . }}
        ?{time_var} peg:hasFuzzyBeginning ?{time_start_var} ;
                  peg:hasFuzzyEnd ?{time_end_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_time_intervals_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        time_var:str="time", time_start_var:str="timeStart", time_end_var:str="timeEnd"):
    
    variables = [time_var, time_start_var, time_end_var]
    query_factoids = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_start_var} ?{time_end_var} WHERE {{
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{time_var} a ?timeClass . }}
        ?timeClass rdfs:subClassOf* peg:TimeInterval .
        ?{time_var} peg:hasBeginning [peg:hasRoot ?{time_start_var}] ;
                  peg:hasEnd [peg:hasRoot ?{time_end_var}] .
        FILTER NOT EXISTS {{
            ?{time_var} peg:hasRoot ?x .
            GRAPH {facts_named_graph_uri.n3()} {{ ?x a peg:TimeInterval . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{time_var} ?{time_start_var} ?{time_end_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{ ?{time_var} a peg:TimeInterval . }}
        ?{time_var} peg:hasBeginning ?{time_start_var} ; peg:hasEnd ?{time_end_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_changes_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        change_var:str="change", change_type_var:str="changeType", applied_to_var:str="appliedTo"):
    
    variables = [change_var, change_type_var, applied_to_var]

    query_factoids = np.query_prefixes + f"""
    SELECT ?{change_var} ?{change_type_var} ?{applied_to_var} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{change_var} a ?changeClass . }}
        GRAPH ?gf {{ ?{applied_to_var} a ?aToClass . }} 
        ?changeClass rdfs:subClassOf* peg:Change .
        ?{change_var} peg:isChangeType ?{change_type_var} ; peg:appliedTo [peg:hasRoot ?{applied_to_var}] .
        FILTER NOT EXISTS {{
            ?{change_var} peg:hasRoot ?changeRoot .
            GRAPH ?gf {{ ?changeRoot a ?x . }}
        }}
        FILTER NOT EXISTS {{ ?{change_var} a peg:AttributeChange . }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{change_var} ?{change_type_var} ?{applied_to_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{
            ?{change_var} a ?changeClass . 
            ?{applied_to_var} a ?ToClass .    
        }}
        ?changeClass rdfs:subClassOf* peg:Change .
        ?{change_var} peg:isChangeType ?{change_type_var} ; peg:appliedTo ?{applied_to_var} .
        FILTER NOT EXISTS {{ ?{change_var} a peg:AttributeChange . }}
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts

def select_events_to_root(
        graphdb_url:URIRef, repository_name:str, facts_named_graph_uri:URIRef,
        event_var:str="event", related_change_var:str="relatedChange"):
    
    variables = [event_var, related_change_var]

    query_factoids = np.query_prefixes + f"""
    SELECT ?{event_var} ?{related_change_var} WHERE {{
        BIND({facts_named_graph_uri.n3()} AS ?gf)
        ?g a peg:SourceGraph ; peg:isActiveGraph "true"^^xsd:boolean.
        GRAPH ?g {{ ?{event_var} a peg:Event . }}
        GRAPH ?gf {{ ?{related_change_var} a ?relCgClass . }} 
        [peg:hasRoot ?{related_change_var}] peg:dependsOn ?{event_var} .
        FILTER NOT EXISTS {{
            ?{event_var} peg:hasRoot ?x .
            GRAPH ?gf {{ ?x a ?xClass . }}
        }}
    }}
    """

    query_facts = np.query_prefixes + f"""
    SELECT ?{event_var} ?{related_change_var} WHERE {{
        GRAPH {facts_named_graph_uri.n3()} {{
            ?{event_var} a peg:Event .
            ?{related_change_var} a ?relCgClass .
        }}
        ?{related_change_var} peg:dependsOn ?{event_var} .
    }}
    """

    factoids = gd.fetch_sparql_data(query_factoids, graphdb_url, repository_name, variables)
    facts = gd.fetch_sparql_data(query_facts, graphdb_url, repository_name, variables)

    return factoids, facts