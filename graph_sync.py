import os
import json
import networkx as nx
from tree_sitter_languages import get_language, get_parser  # type: ignore

GRAPH_FILE = "dependency_graph.json"

language = get_language("python")
parser = get_parser("python")

def parse_python_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = parser.parse(bytes(source_code, "utf-8"))
    dependencies = []

    def extract_calls(node, current_function=None):
        if node.type == "function_definition":
            for child in node.children:
                if child.type == "identifier":
                    current_function = child.text.decode("utf-8")
                    break

        if node.type == "call" and current_function:
            fn_node = node.child_by_field_name("function")
            if fn_node and fn_node.type == "identifier":
                callee_name = fn_node.text.decode("utf-8")
                dependencies.append((current_function, callee_name))

        for child in node.children:
            extract_calls(child, current_function)

    extract_calls(tree.root_node)
    return dependencies

# app_logic.py ରୁ dependencies ବିଶ୍ଳେଷଣ
target_file = "app_logic.py"
deps = parse_python_file(target_file)

print(f"Extracted Dependencies from {target_file}:")
for caller, callee in deps:
    print(f"  {caller} -> {callee}")

# Local Graph ତିଆରି ଏବଂ ସେଭ୍
G = nx.DiGraph()

# ଯଦି ପୂର୍ବରୁ ଗ୍ରାଫ୍ ଫାଇଲ୍ ଥିବ, ତାହାକୁ ଲୋଡ୍ କରିବ
if os.path.exists(GRAPH_FILE):
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            G = nx.node_link_graph(data, edges="links")
    except Exception:
        G = nx.DiGraph()

for caller, callee in deps:
    G.add_edge(caller, callee)

# JSON ଫାଇଲ୍‌ରେ ଗ୍ରାଫ୍ ସେଭ୍
with open(GRAPH_FILE, "w", encoding="utf-8") as f:
    json.dump(nx.node_link_data(G, edges="links"), f, indent=2)

print(f"\n[OK] {target_file} ର ସମସ୍ତ Dependencies ସଫଳତାର ସହ Local Graph ରେ ସେଭ୍ ହୋଇଗଲା!")