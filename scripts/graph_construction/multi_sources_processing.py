import os
from rdflib import Graph, Literal, URIRef, SKOS
from scripts.graph_construction.namespaces import NameSpaces
from scripts.utils import str_processing as sp
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import graphrdf as gr
from scripts.graph_construction import resource_rooting as rr
import time
import json


np = NameSpaces()

def get_elements_with_labels(graphdb_url:URIRef, repository_name:str, has_filter_hidden_label=False,
                             elem_var:str="elem", elem_type_var:str="elemType", label_var:str="label"
                             ):
    """
    Retrieves elements with labels and their types from a specified named graph in a GraphDB repository.

    Parameters:
    - graphdb_url (URIRef): The URL of the GraphDB instance that holds the repository.
    - repository_name (str): The name of the repository from which the elements will be retrieved.
    - has_filter_hidden_label (str): filter to avoid selecting elements which have already a hidden label

    Returns:
    - list: A list of bindings (elements with labels and their types) from the query result. Each binding contains the element, label, and element type.

    Description:
    This function executes a SPARQL query to retrieve elements of type `peg:AttributeVersion` or `peg:Landmark` from a specified named graph.
    For each element, it retrieves its label and type (e.g., `peg:Landmark` type or `peg:AttributeVersion` type). The result is returned as a list of bindings.

    Example usage:
    ```python
    graphdb_url = URIRef('http://localhost:7200')
    repository_name = 'exampleRepository'
    named_graph_uri = URIRef('http://example.org/named_graph')

    # Retrieve elements with labels
    elements = get_elements_with_labels(graphdb_url, repository_name, has_filter_hidden_label)
    ```
    """

    hidden_label_property = np.SKOS.hiddenLabel
    filter_hidden_label = ""
    if has_filter_hidden_label:
        filter_hidden_label = f'FILTER NOT EXISTS {{ ?{elem_var} {hidden_label_property.n3()} ?x }}'

    query = np.query_prefixes + f"""
        SELECT ?{elem_var} ?{elem_type_var} ?{label_var} WHERE {{
            {{
                GRAPH ?g {{ ?{elem_var} a peg:AttributeVersion . }}
                ?lm a peg:Landmark ; peg:isLandmarkType ?{elem_type_var} ; peg:hasAttribute ?attr .
                ?attr a peg:Attribute ; peg:isAttributeType atype:Name ; peg:hasAttributeVersion ?{elem_var} .
                ?elem peg:versionValue ?{label_var} .
            }} UNION {{
                GRAPH ?g {{ ?{elem_var} a peg:Landmark . }}
                ?{elem_var} rdfs:label ?{label_var} ; peg:isLandmarkType ?{elem_type_var} .
            }}
            ?g a peg:SourceGraph .
            {filter_hidden_label}
        }}
        """
        
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    elements = gd.parse_sparql_results(results, [elem_var, elem_type_var, label_var])
    return elements

def get_pref_and_hidden_label_triples_for_element(element: URIRef, element_type: URIRef, label: Literal):
    """
    Generates preferred and hidden label triples for a given element based on its type and label.

    Parameters:
    - element (URIRef): The URI of the element for which the labels will be generated.
    - element_type (URIRef): The type of the element (e.g., Thoroughfare, Municipality, HouseNumber, etc.).
    - label (Literal): The label associated with the element, which will be used to generate the preferred and hidden labels.

    Returns:
    - list: A list of triples representing the preferred and hidden labels for the element. Each triple is a tuple of (subject, predicate, object),
            where the subject is the element URI, the predicate is either `SKOS.prefLabel` or `SKOS.hiddenLabel`, and the object is the label.

    Description:
    This function determines the type of the element and generates appropriate preferred and hidden label triples.
    The labels are normalized and simplified before being added to the list of triples.

    Example usage:
    ```python
    element = URIRef('http://example.org#SomeElement')
    element_type = URIRef('http://example.org#Thoroughfare')
    label = Literal('Main Street', lang='en')

    # Generate preferred and hidden label triples
    triples = get_pref_and_hidden_label_triples_for_element(element, element_type, label)
    ```
    """
    triples = []

    if element_type == np.LTYPE["Thoroughfare"]:
        lm_label_type = "thoroughfare"
    elif element_type in [np.LTYPE["Municipality"], np.LTYPE["District"]]:
        lm_label_type = "area"
    elif element_type in [np.LTYPE["HouseNumber"],np.LTYPE["StreetNumber"],np.LTYPE["DistrictNumber"],np.LTYPE["PostalCodeArea"]]:
        lm_label_type = "number"
    else:
        lm_label_type = None

    normalized_name, simplified_name = sp.normalize_and_simplify_name_version(label.strip(), lm_label_type, label.language)

    if normalized_name is not None:
        normalized_name_lit = Literal(normalized_name, lang=label.language)
        triple = (element, SKOS.prefLabel, normalized_name_lit)
        triples.append(triple)
    if simplified_name is not None:
        simplified_name_lit = Literal(simplified_name, lang=label.language)
        triple = (element, SKOS.hiddenLabel, simplified_name_lit)
        triples.append(triple)

    return triples

def get_pref_and_hidden_label_triples_for_elements(elements: list, elem_var:str="elem", elem_type_var:str="elemType", label_var:str="label"):
    """
    Generates preferred and hidden label triples for a list of elements.

    Parameters:
    - elements (list): A list of dictionaries, where each dictionary represents an element containing the following keys:
        - 'elem': The element URI.
        - 'elemType': The type of the element according landmark type it is related to (e.g., Housenumber, Thoroughfare, City...).
        - 'label': The label associated with the element.

    Returns:
    - list: A list of triples representing the preferred and hidden labels for the elements. Each triple is a tuple of (subject, predicate, object),
            where the subject is the element URI, the predicate is either `SKOS.prefLabel` or `SKOS.hiddenLabel`, and the object is the label.

    Description:
    This function processes a list of elements, retrieving the necessary URIs and labels for each element, and then calls
    `get_pref_and_hidden_label_triples_for_element` to generate the corresponding triples. The function accumulates the triples for all elements
    and returns them as a list.

    Example usage:
    ```python
    elements = [
        {'elem': some_elem_uri, 'elemType': some_elem_type, 'label': some_label},
        {'elem': another_elem_uri, 'elemType': another_elem_type, 'label': another_label}
    ]

    # Generate preferred and hidden label triples for the elements
    triples = get_pref_and_hidden_label_triples_for_elements(elements)
    ```
    """

    g = Graph()

    for element in elements:
        # Retrieval of URIs (attribute and attribute version) and geometry
        elem = element.get(elem_var)
        elem_type = element.get(elem_type_var)
        label = element.get(label_var)

        triples_to_add = get_pref_and_hidden_label_triples_for_element(elem, elem_type, label)
        for triple in triples_to_add:
            g.add(triple)

    return g


def add_pref_and_hidden_labels_for_elements(graphdb_url:URIRef, repository_name:str, labels_named_graph_uri:URIRef, pref_hidden_labels_ttl_file:str):
    """
    Adds preferred and hidden labels for the elements (name attribute versions and landmark) to a specified repository in GraphDB.

    Parameters:
    - graphdb_url (URIRef): The URL of the GraphDB instance that holds the repository where the labels will be added.
    - repository_name (str): The name of the repository where the labels will be inserted.
    - labels_named_graph_uri (URIRef): The URI of the named graph containing the factoids from which the labels are generated.

    Returns:
    - None: The function does not return any value. It performs an update on the GraphDB repository by adding the triples.

    Description:
    This function retrieves elements with labels from the specified named graph, generates the triples for preferred and hidden labels,
    and then adds them to the specified repository.

    Example usage:
    ```python
    graphdb_url = URIRef('http://localhost:7200')
    repository_name = 'exampleRepository'
    labels_named_graph_uri = URIRef('http://example.org/labels')

    # Add preferred and hidden labels for name attribute versions
    add_pref_and_hidden_labels_for_elements(graphdb_url, repository_name, labels_named_graph_uri)
    ```
    """

    elem_var = "elem"
    elem_type_var = "elemType"
    label_var = "label"

    elements = get_elements_with_labels(graphdb_url, repository_name, has_filter_hidden_label=True, elem_var=elem_var, elem_type_var=elem_type_var, label_var=label_var)
    graph_with_triples_to_add = get_pref_and_hidden_label_triples_for_elements(elements, elem_var=elem_var, elem_type_var=elem_type_var, label_var=label_var)
    graph_with_triples_to_add.serialize(pref_hidden_labels_ttl_file)

    # Import the `kg_file` file into the directory
    gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, pref_hidden_labels_ttl_file, named_graph_uri=labels_named_graph_uri)
    

def remove_all_triples_for_resources_to_remove(graphdb_url:URIRef, repository_name:str):
    """
    Removes all triples associated with resources marked for removal from the specified GraphDB repository.

    Parameters:
    - graphdb_url (URIRef): The URL of the GraphDB instance where the repository is located.
    - repository_name (str): The name of the repository from which the triples will be removed.

    Returns:
    - None: The function does not return any value. It performs an update on the GraphDB repository to delete the relevant triples.

    Description:
    This function constructs and executes a SPARQL `DELETE` query that removes all triples associated with resources 
    that are marked for removal. A resource is considered for removal if it has a `toRemove` property set to `true`.
    The query deletes both the triples directly referencing the resources marked for removal as well as any triples
    where these resources are the subject of other triples.

    Example usage:
    ```python
    graphdb_url = URIRef('http://localhost:7200')
    repository_name = 'exampleRepository'

    # Remove all triples for resources marked for removal
    remove_all_triples_for_resources_to_remove(graphdb_url, repository_name)
    ```
    """

    to_remove_property = np.PEG["toRemove"]

    query = np.query_prefixes + f"""
    DELETE {{
        ?s ?p ?tmpResource.
        ?tmpResource ?p ?o.
    }}
    WHERE {{
        ?tmpResource {to_remove_property.n3()} ?toRemove.
        FILTER(?toRemove)
        {{?tmpResource ?p ?o}} UNION {{?s ?p ?tmpResource}}
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def transfert_rdflib_graph_to_named_graph_repository(
        g: Graph, graphdb_url: URIRef,
        repository_name: str, named_graph_uri: URIRef,
        kg_file: str, named_graph_type:str=None,
        meta_named_graph_uri:URIRef=None, is_active: bool=True):
    
    g.serialize(kg_file)

    # Import the `kg_file` file into the directory
    r = gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, kg_file, named_graph_uri=named_graph_uri)

    if meta_named_graph_uri is not None:
        # Get the URI of the meta graph
        if named_graph_type == "source":
            add_source_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, named_graph_uri, is_active=is_active)
        elif named_graph_type == "construction":
            add_construction_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, named_graph_uri, is_active=is_active)
        elif named_graph_type == "facts":
            add_final_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, named_graph_uri, is_active=is_active)
        else:
            add_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, named_graph_uri, is_active=is_active)

####################################################################


def import_factoids_in_facts(
        graphdb_url:URIRef, repository_name:str,
        factoids_named_graph_uri:URIRef, facts_named_graph_uri:URIRef, inter_sources_name_graph_uri:URIRef,
        pref_hidden_labels_ttl_file:str):
    """
    Imports factoids into the facts graph and links them with inter-sources in a GraphDB repository.

    Parameters:
    - graphdb_url (URIRef): The URL of the GraphDB instance where the repository is located.
    - repository_name (str): The name of the repository containing the factoids and facts graphs.
    - factoids_named_graph_uri (URIRef): The URI of the graph containing the factoids to be imported.
    - facts_named_graph_uri (URIRef): The URI of the graph containing the facts to be linked with the factoids.
    - inter_sources_name_graph_uri (URIRef): The URI of the graph containing the inter-sources to link with factoids.

    Returns:
    - None: The function does not return any value. It performs the import and linking of factoids with facts.

    Description:
    This function imports factoids into the facts graph in the specified repository and links the factoids with the facts using inter-source data.
    It first adds standardized and simplified labels for landmarks in the factoid graph to facilitate linking with fact landmarks.
    Then, it links the factoids with the facts in the specified graphs.
    """

    # Addition of standardised and simplified labels for landmarks (on the factoid graph) in order to make links with fact landmarks
    add_pref_and_hidden_labels_for_elements(graphdb_url, repository_name, pref_hidden_labels_ttl_file)

    rr.link_factoids_with_facts(graphdb_url, repository_name, factoids_named_graph_uri, facts_named_graph_uri, inter_sources_name_graph_uri)

def load_ontologies(
        graphdb_url:URIRef, repository_name:str, ont_files:list[str],
        ontology_named_graph_uri:URIRef, metadata_named_graph_uri:URIRef=None
    ):
    """
    Load a list of ontology files into the given repository.
    
    Args:
        graphdb_url (URIRef): The base URL of the GraphDB instance.
        repository_name (str): The name of the repository to load ontologies into.
        ont_files (list of str): List of file paths to the ontology files.
        ontology_named_graph_uri (URIRef): The URI of the named graph for ontologies.
        metadata_named_graph_uri (URIRef, optional): The URI of the named graph for metadata (default is None).
    """
    
    for ont_file in ont_files:
        gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, ont_file, named_graph_uri=ontology_named_graph_uri)

    if metadata_named_graph_uri is not None:
        # Add the metadata named graph to the repository if it does not exist yet
        add_named_graph_to_repository(graphdb_url, repository_name, metadata_named_graph_uri, ontology_named_graph_uri)


######################################################### Named graph management ######################################################

def add_named_graph_to_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef, named_graph_uri:URIRef,
        graph_class:URIRef=None, is_active:bool=True):
    """Add a named graph to the meta graph and set it as active or not in the repository."""

    if graph_class is None:
        graph_class = np.PEG["Graph"]

    query = np.query_prefixes + f"""
        INSERT DATA {{
            GRAPH {meta_named_graph_uri.n3()} {{
                {named_graph_uri.n3()} a {graph_class.n3()} .
            }}
        }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

    if is_active is not None:
        # Set the named graph as active or not
        set_named_graph_active(graphdb_url, repository_name, named_graph_uri, meta_named_graph_uri, active=is_active)

def add_source_named_graph_to_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef, source_named_graph_uri:URIRef, is_active:bool=True):
    
    graph_class = np.PEG["SourceGraph"]
    add_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, source_named_graph_uri, graph_class=graph_class, is_active=is_active)


def add_construction_named_graph_to_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef,
        construction_named_graph_uri:URIRef, is_active:bool=True):
    
    graph_class = np.PEG["ConstructionGraph"]
    add_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, construction_named_graph_uri, graph_class=graph_class, is_active=is_active)

def add_final_named_graph_to_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef,
        facts_named_graph_uri:URIRef, facts_named_graph_name_label:str=None, lang:str=None,
        is_active:bool=None):
    
    graph_class = np.PEG["FinalGraph"]
    add_named_graph_to_repository(graphdb_url, repository_name, meta_named_graph_uri, facts_named_graph_uri, graph_class=graph_class, is_active=is_active)

    if facts_named_graph_name_label is not None:
        add_final_named_graph_label_to_repository(graphdb_url, repository_name, meta_named_graph_uri, facts_named_graph_uri, facts_named_graph_name_label, lang=lang)

def add_final_named_graph_label_to_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef,
        facts_named_graph_uri:URIRef, facts_named_graph_name_label:str, lang:str=None):
    
    # Add label for the final graph in the meta graph

    label = gr.get_literal_with_lang(facts_named_graph_name_label, lang=lang)

    query = np.query_prefixes + f"""
        INSERT DATA {{
            GRAPH {meta_named_graph_uri.n3()} {{
                {facts_named_graph_uri.n3()} rdfs:label {label.n3()} .
            }}
        }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def remove_named_graph_from_repository(
        graphdb_url:URIRef, repository_name:str,
        meta_named_graph_uri:URIRef, named_graph_uri:URIRef):
    """Remove a named graph from the meta graph and delete all its triples from the repository."""
    
    gd.remove_named_graph_with_query(graphdb_url, repository_name, named_graph_uri)

    query = np.query_prefixes + f"""
        DELETE {{
            GRAPH {meta_named_graph_uri.n3()} {{
                {named_graph_uri.n3()} ?p ?o .
            }}
        }} WHERE {{
            GRAPH {meta_named_graph_uri.n3()} {{
                {named_graph_uri.n3()} ?p ?o .
            }}
        }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)

def set_all_named_graphs_active(
    graphdb_url: URIRef,
    repository_name: str,
    meta_named_graph_uri: URIRef,
    active: bool,
    graph_type: str=None
):
    
    # Booléen RDF
    new_value = gr.get_boolean_literal(active)

    graph_types = {
        "source":np.PEG["SourceGraph"],
        "final":np.PEG["FinalGraph"],
        "construction":np.PEG["ConstructionGraph"]
    }

    graph_class = graph_types.get(graph_type, np.PEG["Graph"])

    query = np.query_prefixes + f"""
    DELETE {{
        GRAPH ?g {{
            ?gs peg:isActiveGraph ?oldValue .
        }}
    }}
    INSERT {{
        GRAPH ?g {{
            ?gs peg:isActiveGraph {new_value.n3()} .
        }}
    }}
    WHERE {{
        BIND ({meta_named_graph_uri.n3()} AS ?g)

        GRAPH ?g {{
            ?gs a ?gsClass .
            OPTIONAL {{ ?gs peg:isActiveGraph ?oldValue . }}
        }}

        ?gsClass rdfs:subClassOf* {graph_class.n3()} .
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)


def set_named_graph_active(
    graphdb_url: URIRef,
    repository_name: str,
    named_graph_uri: URIRef,
    meta_named_graph_uri: URIRef,
    active: bool=True,
):
    """
    Set the status of a single source graph in the meta graph.
    
    Args:
        graphdb_url: URI of the GraphDB instance
        repository_name: repository name
        named_graph_uri: URI of the named graph to update
        meta_named_graph_uri: URI of the meta graph containing the sources
        active: True to activate (set as active), False to deactivate
    """

    # Booléen RDF
    new_value = gr.get_boolean_literal(active)

    query = np.query_prefixes + f"""
    DELETE {{
        GRAPH ?g {{
            {named_graph_uri.n3()} peg:isActiveGraph ?oldValue .
        }}
    }}
    INSERT {{
        GRAPH ?g {{
            {named_graph_uri.n3()} peg:isActiveGraph {new_value.n3()} .
        }}
    }}
    WHERE {{
        BIND({meta_named_graph_uri.n3()} AS ?g)
        GRAPH ?g {{
            {named_graph_uri.n3()} a ?gsClass .
            OPTIONAL {{ {named_graph_uri.n3()} peg:isActiveGraph ?oldValue . }}
        }}
        ?gsClass rdfs:subClassOf* peg:Graph .
    }}
    """

    gd.run_update_query(query, graphdb_url, repository_name)


def remove_construction_named_graphs(graphdb_url, repository_name):
    """
    Remove all named graphs of type peg:ConstructionGraph from a GraphDB repository.

    This function executes a SPARQL UPDATE query that:
    - Identifies all named graphs typed as peg:ConstructionGraph
    - Deletes all triples contained in each of these graphs

    Parameters
    ----------
    graphdb_url : URIRef
        Base URL of the GraphDB instance.
    repository_name : str
        Name of the repository where the construction graphs are stored.

    Notes
    -----
    - The named graphs are emptied by deleting all their triples.
      (GraphDB treats empty named graphs as removed.)
    - This operation is irreversible; use with caution.
    """

    # ---------------------------------------------------------------
    # Delete all construction graphs and their references
    #
    # This operation performs two actions:
    # 1) Deletes all triples contained in each named graph ?g
    #    typed as peg:ConstructionGraph (the type is stored outside the graph).
    # 2) Deletes all triples where ?g is used either as a subject or an object
    #    in any graph ?h.
    #
    # The SPARQL query uses:
    # - DELETE { ... } WHERE { ... } to clear graphs and references
    # - GRAPH ?g and GRAPH ?h to distinguish targeted graphs
    # - UNION to capture ?g as either subject or object in any graph
    # ---------------------------------------------------------------

    query1 = np.query_prefixes + f"""

    DELETE {{
        GRAPH ?g {{ ?s ?p ?o }}
    }}
    WHERE {{
        ?g a peg:ConstructionGraph .
        GRAPH ?g {{ ?s ?p ?o }}
    }}
    """

    query2 = np.query_prefixes + f"""

    DELETE {{
        ?g ?p1 ?o .
        ?s ?p2 ?g .
    }}
    WHERE {{
        ?g a peg:ConstructionGraph .

        {{ ?g ?p1 ?o }} UNION {{ ?s ?p2 ?g }}
    }}
    """

    queries = [query1, query2]

    for query in queries:
        # Execute the SPARQL UPDATE query on the target repository
        gd.run_update_query(query, graphdb_url, repository_name)