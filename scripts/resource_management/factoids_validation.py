from rdflib import Graph, Literal, URIRef, SKOS
from scripts.graph_construction.namespaces import NameSpaces
from scripts.graph_construction import graphdb as gd
from scripts.graph_construction import graphrdf as gr
from scripts.utils import file_management as fm

np = NameSpaces()

################################ Checking about properties ############################

def check_property_domain(graphdb_url:URIRef, repository_name:str, named_graph_uri:URIRef, property:URIRef, expected_domain:URIRef, subject_var: str = "subject"):
    """
    Check if the domain of a property is correctly defined in the graph.

    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    property: URI of the property to check
    expected_domain: URI of the expected domain class for the property
    """

    query = np.query_prefixes + f"""
    SELECT ?{subject_var}
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{ ?{subject_var} {property.n3()} ?object . }}
        FILTER NOT EXISTS {{ ?{subject_var} a/rdfs:subClassOf* {expected_domain.n3()} . }}
    }}
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    elements = gd.parse_sparql_results(results, [subject_var])
    return elements

def check_property_range(graphdb_url:URIRef, repository_name:str, named_graph_uri:URIRef, property:URIRef, expected_range:URIRef, object_var: str = "object"):
    """
    Check if the range of a property is correctly defined in the graph.
    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    property: URI of the property to check
    expected_range: URI of the expected range class for the property
    """
    
    query = np.query_prefixes + f"""
    SELECT ?{object_var}
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{ ?subject {property.n3()} ?{object_var} . }}
        FILTER NOT EXISTS {{ ?{object_var} a/rdfs:subClassOf* {expected_range.n3()} . }}
    }}
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    elements = gd.parse_sparql_results(results, [object_var])
    return elements

def check_properties_domains(graphdb_url: URIRef, repository_name: str, named_graph_uri: URIRef,
                             domain_mapping: list[tuple[URIRef, URIRef]],
                             property_var: str = "property", subject_var: str = "subject", expected_domain_var: str = "expected_domain"):
    """
    Vérifie les domaines de plusieurs propriétés en une seule fois.
    domain_mapping: [(prop1, domain1), (prop2, domain2), ...]
    """
    
    # Construction de la chaîne VALUES
    values_content = " ".join([f"({p.n3()} {d.n3()})" for p, d in domain_mapping])

    query = np.query_prefixes + f"""
    SELECT ?{property_var} ?{subject_var} ?{expected_domain_var}
    WHERE {{
        VALUES (?{property_var} ?{expected_domain_var}) {{ {values_content} }}
        
        GRAPH {named_graph_uri.n3()} {{ 
            ?{subject_var} ?{property_var} ?object . 
        }}
        
        FILTER NOT EXISTS {{ ?{subject_var} a/rdfs:subClassOf* ?{expected_domain_var} . }}
    }}
    """

    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    elements = gd.parse_sparql_results(results, [property_var, subject_var, expected_domain_var])
    return elements

def check_properties_ranges(graphdb_url: URIRef, repository_name: str, named_graph_uri: URIRef,
                            range_mapping: list[tuple[URIRef, URIRef]], 
                            property_var: str = "property", object_var: str = "object", expected_range_var: str = "expected_range"):
    """
    Vérifie les ranges (Classes ou Datatypes) de plusieurs propriétés.
    range_mapping: [(prop1, class1), (prop2, xsd_type), ...]
    """
    
    values_content = " ".join([f"({p.n3()} {r.n3()})" for p, r in range_mapping])

    query = np.query_prefixes + f"""
    SELECT ?{property_var} ?{object_var} ?{expected_range_var}
    WHERE {{
        VALUES (?{property_var} ?{expected_range_var}) {{ {values_content} }}
        
        GRAPH {named_graph_uri.n3()} {{ 
            ?subject ?{property_var} ?{object_var} . 
        }}
        
        FILTER (
            # Cas 1 : C'est une ressource (URI), on vérifie la classe
            (isIRI(?{object_var}) && NOT EXISTS {{ ?{object_var} a/rdfs:subClassOf* ?{expected_range_var} . }}) ||
            
            # Cas 2 : C'est un littéral, on vérifie le type de donnée
            (isLiteral(?{object_var}) && datatype(?{object_var}) != ?{expected_range_var})
        )
    }}
    """

    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    elements = gd.parse_sparql_results(results, [property_var, object_var, expected_range_var])
    return elements

def check_property_cardinality(graphdb_url:URIRef, repository_name:str, named_graph_uri:URIRef, property:URIRef, subject_class:URIRef, min_cardinality:int=None, max_cardinality:int=None):
    """
    Check if the cardinality of a property is respected in the graph.
    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    property: URI of the property to check
    subject_class: URI of the class for which to check the cardinality
    min_cardinality: Minimum cardinality (inclusive) for the property (if specified)
    max_cardinality: Maximum cardinality (inclusive) for the property (if specified)
    """

    cardinality_filter = ""
    if min_cardinality is not None:
        cardinality_filter += f"HAVING (COUNT(?object) < {min_cardinality})"
    if max_cardinality is not None:
        if cardinality_filter:
            cardinality_filter += " || "
        else:
            cardinality_filter += "HAVING "
        cardinality_filter += f"(COUNT(?object) > {max_cardinality})"

    query = np.query_prefixes + f"""
    SELECT ?subject (COUNT(?object) AS ?objectCount)
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{  ?subject a ?subjectClass ; {property.n3()} ?object . }}
        ?subjectClass rdfs:subClassOf* {subject_class.n3()} .
    }}
    GROUP BY ?subject
    {cardinality_filter}
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    return results

def check_property_functionality(graphdb_url:URIRef, repository_name:str, named_graph_uri:URIRef, property:URIRef):
    """
    Check if a property is functional in the graph (i.e., it has at most one value for each subject).
    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    property: URI of the property to check
    """

    query = np.query_prefixes + f"""
    SELECT ?subject (COUNT(?object) AS ?objectCount)
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{  ?subject {property.n3()} ?object . }}
    }}
    GROUP BY ?subject
    HAVING (COUNT(?object) > 1)
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    return results

def check_property_inverse_functionality(graphdb_url:URIRef, repository_name:str, named_graph_uri:URIRef, property:URIRef):
    """
    Check if a property is inverse functional in the graph (i.e., it has at most one value for each object).
    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    property: URI of the property to check
    """

    query = np.query_prefixes + f"""
    SELECT ?object (COUNT(?subject) AS ?subjectCount)
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{  ?subject {property.n3()} ?object . }}
    }}
    GROUP BY ?object
    HAVING (COUNT(?subject) > 1)
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    return results

def check_class_has_property(graphdb_url: URIRef, repository_name: str, named_graph_uri: URIRef, 
                             subject_class: URIRef, property_uri: URIRef):
    """
    Check if all instances of a specific class (including its subclasses) 
    have at least one triple with the defined property.

    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_uri: URI of the named graph to query
    subject_class: URI of the class to check
    property_uri: URI of the property that must be present
    
    Returns:
        List of subjects (instances of subject_class) that LACK the property.
    """

    query = np.query_prefixes + f"""
    SELECT ?subject
    WHERE {{
        GRAPH {named_graph_uri.n3()} {{
            ?subject a ?actualClass .            
            FILTER NOT EXISTS {{ ?subject {property_uri.n3()} ?anyObject . }}
        }}
        ?actualClass rdfs:subClassOf* {subject_class.n3()} .

    }}
    """

    # Execute the query against the graph database and return the results
    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    return results

def check_classes_have_properties(graphdb_url: URIRef, repository_name: str, named_graph_uri: URIRef, 
                                 mapping: list[tuple[URIRef, URIRef]],
                                 class_var: str = "class", 
                                 property_var: str = "property", 
                                 subject_var: str = "subject"):
    """
    Checks multiple class-property pairs. 
    Finds instances of a class (and its subclasses) that are missing a specific property.
    
    mapping: [(class1, prop1), (class2, prop2), ...]
    """
    
    # Format the mapping for the VALUES clause
    values_content = " ".join([f"({c.n3()} {p.n3()})" for c, p in mapping])

    query = np.query_prefixes + f"""
    SELECT ?{subject_var} ?{class_var} ?{property_var}
    WHERE {{
        # Define the pairs to check
        VALUES (?{class_var} ?{property_var}) {{ {values_content} }}
        
        GRAPH {named_graph_uri.n3()} {{
            # Find instances of the class (including subclasses)
            ?{subject_var} a ?actualClass .
            ?actualClass rdfs:subClassOf* ?{class_var} .
            
            # Filter those that DO NOT have the required property
            FILTER NOT EXISTS {{ 
                ?{subject_var} ?{property_var} ?anyObject . 
            }}
        }}
    }}
    """

    results = gd.run_select_query_to_json(query, graphdb_url, repository_name)
    return gd.parse_sparql_results(results, [subject_var, class_var, property_var])

############################ Checking about landmarks ############################

def check_elements(graphdb_url:URIRef, repository_name:str, named_graph_name:str, output_csv_path:str):
    """
    Check if the main classes of the ontology have the required properties in the graph.

    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_name: Name of the named graph to query
    output_csv_path: Path to the output CSV file where the errors will be written
    """

    named_graph_uri = gd.get_named_graph_uri_from_name(graphdb_url, repository_name, named_graph_name)

    has_property_checks = [
        {"class": np.PEG["Landmark"], "property": np.PEG["isLandmarkType"]},
        {"class": np.PEG["LandmarkRelation"], "property": np.PEG["isLandmarkRelationType"]},
        {"class": np.PEG["LandmarkRelation"], "property": np.PEG["locatum"]},
        {"class": np.PEG["LandmarkRelation"], "property": np.PEG["relatum"]},
        {"class": np.PEG["Attribute"], "property": np.PEG["isAttributeType"]},
        {"class": np.PEG["Change"], "property": np.PEG["isChangeType"]},
        {"class": np.PEG["Change"], "property": np.PEG["appliedTo"]},
        {"class": np.PEG["Change"], "property": np.PEG["dependsOn"]},
        {"class": np.PEG["Address"], "property": np.PEG["targets"]},
        {"class": np.PEG["Address"], "property": np.PEG["firstStep"]},
        {"class": np.PEG["AddressSegment"], "property": np.PEG["nextStep"]},
        {"class": np.PEG["CrispTimeInstant"], "property": np.PEG["timeStamp"]},
        {"class": np.PEG["CrispTimeInstant"], "property": np.PEG["timePrecision"]},
        {"class": np.PEG["CrispTimeInstant"], "property": np.PEG["timeCalendar"]},
    ]

    subject_var = "subject"
    property_var = "property"
    class_var = "class"

    mapping = [(check["class"], check["property"]) for check in has_property_checks]
    res = check_classes_have_properties(graphdb_url, repository_name, named_graph_uri, mapping, class_var=class_var, property_var=property_var, subject_var=subject_var)
    errors_header = ["URI", "Class", "Missing Property"]
    errors = []
    for r in res:
        errors.append([r[subject_var], r[class_var], r[property_var]])

    file_content_lines = [errors_header] + errors
    fm.write_csv_file_from_rows(file_content_lines, output_csv_path)

def check_properties(graphdb_url:URIRef, repository_name:str, named_graph_name:str, output_csv_path:str):
    """
    Check if the properties of the ontology are correctly used in the graph, in terms of domains and ranges.

    graphdb_url: URL of the graph database
    repository_name: Name of the repository in the graph database
    named_graph_name: Name of the named graph to query
    output_csv_path: Path to the output CSV file where the errors will be written
    """
    
    named_graph_uri = gd.get_named_graph_uri_from_name(graphdb_url, repository_name, named_graph_name)

    property_checks = [
        {"property": np.PEG["isLandmarkType"], "domain": np.PEG["Landmark"], "range": np.PEG["LandmarkType"]},
        {"property": np.PEG["isLandmarkRelationType"], "domain": np.PEG["LandmarkRelation"], "range": np.PEG["LandmarkRelationType"]},
        {"property": np.PEG["isAttributeType"], "domain": np.PEG["Attribute"], "range": np.PEG["AttributeType"]},
        {"property": np.PEG["isChangeType"], "domain": np.PEG["Change"], "range": np.PEG["ChangeType"]},
    
        {"property": np.PEG["targets"], "domain": np.PEG["Address"], "range": np.PEG["Landmark"]},
        {"property": np.PEG["firstStep"], "domain": np.PEG["Address"], "range": np.PEG["LandmarkRelation"]},
        {"property": np.PEG["nextStep"], "domain": np.PEG["LandmarkRelation"], "range": np.PEG["LandmarkRelation"]},
        {"property": np.PEG["locatum"], "domain": np.PEG["LandmarkRelation"], "range": np.PEG["Landmark"]},
        {"property": np.PEG["relatum"], "domain": np.PEG["LandmarkRelation"], "range": np.PEG["Landmark"]},

        {"property": np.PEG["appliedTo"], "domain": np.PEG["Change"], "range": None},
        {"property": np.PEG["dependsOn"], "domain": np.PEG["Change"], "range": np.PEG["Event"]},

        {"property": np.PEG["timeStamp"], "domain": np.PEG["CrispTimeInstant"], "range": np.XSD["dateTimeStamp"]},
        {"property": np.PEG["timePrecision"], "domain": np.PEG["CrispTimeInstant"], "range": np.TIME["TemporalUnit"]},
        {"property": np.PEG["timeCalendar"], "domain": np.PEG["CrispTimeInstant"], "range": np.TIME["TRS"]},
    ]

    errors_header = ["URI", "Property", "Range/Domain", "Expected Range/Domain"]
    errors = []

    range_mapping = [(check["property"], check["range"]) for check in property_checks if check["range"] is not None]
    domain_mapping = [(check["property"], check["domain"]) for check in property_checks if check["domain"] is not None]

    subject_var = "subject"
    property_var = "property"
    object_var = "object"
    expected_range_var = "expected_range"
    expected_domain_var = "expected_domain"

    range_errors = check_properties_ranges(graphdb_url, repository_name, named_graph_uri, range_mapping, property_var, object_var, expected_range_var)
    domain_errors = check_properties_domains(graphdb_url, repository_name, named_graph_uri, domain_mapping, property_var, object_var, expected_domain_var)

    for res in range_errors:
        errors.append([res[subject_var], res[property_var], "Range", res[expected_range_var]])
        
    for res in domain_errors:
        errors.append([res[subject_var], res[property_var], "Domain", res[expected_domain_var]])

    file_content_lines = [errors_header] + errors
    fm.write_csv_file_from_rows(file_content_lines, output_csv_path)