import os
import json
import networkx as nx
from tree_sitter_languages import get_language, get_parser

PY_LANGUAGE = get_language("python")
parser = get_parser("python")

# ସ୍କାନ୍ ବେଳେ ଅଦରକାରୀ ଫୋଲ୍ଡର୍ ଗୁଡ଼ିକୁ ବାଦ୍ ଦେବା ପାଇଁ
IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env", "node_modules"}

FUNC_QUERY = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @func_name) @func_def
""")

CALL_QUERY = PY_LANGUAGE.query("""
(call
  function: [
    (identifier) @call_name
    (attribute attribute: (identifier) @call_name)
  ])
""")


def get_python_files(root_dir="."):
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            if filename.endswith(".py") and filename not in {"repo_scanner.py", "diff_analyzer.py", "test_parser.py"}:
                rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)
                py_files.append(rel_path.replace("\\", "/"))
    return py_files


def parse_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    source_bytes = bytes(source_code, "utf8")
    tree = parser.parse(source_bytes)
    root_node = tree.root_node

    functions = []
    func_captures = FUNC_QUERY.captures(root_node)

    # Function definitions ଏବଂ ସେମାନଙ୍କର line range ବାହାର କରିବା
    current_def = None
    for node, tag in func_captures:
        if tag == "func_def":
            current_def = node
        elif tag == "func_name" and current_def is not None:
            func_name = source_bytes[node.start_byte:node.end_byte].decode("utf8")
            start_line = current_def.start_point[0] + 1
            end_line = current_def.end_point[0] + 1

            # ଏହି function ଭିତରେ କେଉଁ କେଉଁ call ଅଛି ଖୋଜିବା
            calls = []
            call_captures = CALL_QUERY.captures(current_def)
            for c_node, c_tag in call_captures:
                if c_tag == "call_name":
                    called_func = source_bytes[c_node.start_byte:c_node.end_byte].decode("utf8")
                    if called_func != func_name:
                        calls.append(called_func)

            functions.append({
                "id": f"{file_path}::{func_name}",
                "name": func_name,
                "file": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "calls": list(set(calls))
            })
            current_def = None

    return functions


def build_repo_graph(root_dir="."):
    G = nx.DiGraph()
    all_functions = []
    name_to_ids = {}

    py_files = get_python_files(root_dir)
    print(f"Scanning {len(py_files)} Python files: {py_files}")

    # ୧. ପ୍ରଥମେ ସମସ୍ତ ଫାଇଲ୍‌ରୁ ସବୁ Function Node ଯୋଡ଼ିବା
    for file_path in py_files:
        funcs = parse_file(file_path)
        for fn in funcs:
            all_functions.append(fn)
            G.add_node(
                fn["id"],
                name=fn["name"],
                file=fn["file"],
                start_line=fn["start_line"],
                end_line=fn["end_line"]
            )
            name_to_ids.setdefault(fn["name"], []).append(fn["id"])

    # ୨. ଏବେ Cross-File ଏବଂ Same-File Call ସମ୍ପର୍କ (Edges) ଯୋଡ଼ିବା
    for fn in all_functions:
        caller_id = fn["id"]
        caller_file = fn["file"]

        for called_name in fn["calls"]:
            if called_name in name_to_ids:
                targets = name_to_ids[called_name]
                # ଯଦି ନିଜ ଫାଇଲ୍ ଭିତରେ ସେହି function ଅଛି, ତାହାକୁ ପ୍ରାଥମିକତା ଦେବା
                same_file_target = f"{caller_file}::{called_name}"
                if same_file_target in targets:
                    G.add_edge(caller_id, same_file_target)
                else:
                    # ନଚେତ୍ ଅନ୍ୟ ଫାଇଲ୍‌ରେ ଥିବା function ସହିତ ଯୋଡ଼ିବା (Cross-File Link)
                    for target_id in targets:
                        G.add_edge(caller_id, target_id)

    # Graph କୁ JSON ରେ Save କରିବା
    graph_data = nx.node_link_data(G)
    with open("dependency_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    print(f"Graph saved! Total Nodes: {G.number_of_nodes()}, Total Edges: {G.number_of_edges()}")


if __name__ == "__main__":
    build_repo_graph(".")