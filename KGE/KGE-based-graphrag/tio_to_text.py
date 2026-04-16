import os
from rdflib import Graph, RDF, RDFS, SKOS, Namespace
from rdflib.namespace import DCTERMS

# 定義 TIO 命名空間
ICM = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/")
IMO = Namespace("http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/")

def parse_ttl_to_narrative(ttl_file, output_dir):
    """
    將單個 .ttl 檔案解析為描述性的文本文件，以便 GraphRAG 索引。
    """
    # 定義必要的 prefix 字串
    prefixes = """
@prefix icm:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentCommonModel/> .
@prefix imo:  <http://tio.models.tmforum.org/tio/v3.6.0/IntentManagementOntology/> .
@prefix fun:  <http://tio.models.tmforum.org/tio/v3.6.0/FunctionOntology/> .
@prefix log:  <http://tio.models.tmforum.org/tio/v3.6.0/LogicalOperators/> .
@prefix math: <http://tio.models.tmforum.org/tio/v3.6.0/MathFunctions/> .
@prefix set:  <http://tio.models.tmforum.org/tio/v3.6.0/SetOperators/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct:  <http://purl.org/dc/terms/> .
"""
    g = Graph()
    
    try:
        # 讀取檔案內容並加上 prefix
        with open(ttl_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析合成後的內容
        g.parse(data=prefixes + content, format="turtle")
    except Exception as e:
        print(f"Error parsing {ttl_file}: {e}")
        return

    base_name = os.path.basename(ttl_file).replace('.ttl', '')
    output_file = os.path.join(output_dir, f"{base_name}.txt")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"--- Ontology Module: {base_name} ---\n\n")
        
        # 提取類別 (Classes)
        f.write("### Classes Defined in this Module:\n")
        for s in g.subjects(RDF.type, RDFS.Class):
            label = g.value(s, RDFS.label)
            comment = g.value(s, RDFS.comment)
            subclass_of = g.value(s, RDFS.subClassOf)
            
            f.write(f"Class: {s}\n")
            if label: f.write(f"  Label: {label}\n")
            if comment: f.write(f"  Description: {comment}\n")
            if subclass_of: f.write(f"  Subclass of: {subclass_of}\n")
            f.write("\n")

        # 提取屬性 (Properties)
        f.write("\n### Properties Defined in this Module:\n")
        for s in g.subjects(RDF.type, RDF.Property):
            label = g.value(s, RDFS.label)
            comment = g.value(s, RDFS.comment)
            domain = g.value(s, RDFS.domain)
            range_val = g.value(s, RDFS.range)
            
            f.write(f"Property: {s}\n")
            if label: f.write(f"  Label: {label}\n")
            if comment: f.write(f"  Description: {comment}\n")
            if domain: f.write(f"  Applies to (Domain): {domain}\n")
            if range_val: f.write(f"  Value type (Range): {range_val}\n")
            f.write("\n")

def main():
    input_dir = "TM Forum Intent Ontology"
    output_dir = "graphrag_input"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".ttl"):
            ttl_path = os.path.join(input_dir, filename)
            print(f"Processing {filename}...")
            parse_ttl_to_narrative(ttl_path, output_dir)
            print(f"Done processing {filename}.")

if __name__ == "__main__":
    main()
