import subprocess
import re
import json
import networkx as nx
from tree_sitter_languages import get_language, get_parser  # type: ignore

language = get_language("python")
parser = get_parser("python")
GRAPH_FILE = "dependency_graph.json"

def get_git_diff_lines(file_path):
    """
    Git diff ବ୍ୟବହାର କରି କେଉଁ କେଉଁ ଲାଇନ୍ ପରିବର୍ତ୍ତନ ହୋଇଛି (added/modified lines) ତାହା ବାହାର କରେ।
    """
    try:
        # unstaged କିମ୍ବା staged ପରିବର୍ତ୍ତନ ଯାଞ୍ଚ କରିବା
        cmd = ["git", "diff", "HEAD", "--", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        diff_text = result.stdout
        
        # ଯଦି HEAD ତୁଳନାରେ କିଛି ନାହିଁ, ତେବେ ଖାଲି diff ଚେକ୍ କରିବା
        if not diff_text:
            cmd = ["git", "diff", "--", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            diff_text = result.stdout
    except Exception as e:
        print(f"[!] Git Diff error: {e}")
        return []

    changed_lines = []
    current_line = 0
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    for line in diff_text.splitlines():
        hunk_match = hunk_pattern.match(line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue
        
        if line.startswith("+") and not line.startswith("+++"):
            changed_lines.append(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass
        else:
            current_line += 1

    return changed_lines

def find_functions_at_lines(file_path, target_lines):
    """
    Tree-sitter ବ୍ୟବହାର କରି ପରିବର୍ତ୍ତିତ ଲାଇନ୍ ନମ୍ବରଗୁଡ଼ିକ କେଉଁ ଫଙ୍କସନ୍ ଭିତରେ ପଡ଼ୁଛି ତାହା ଚିହ୍ନଟ କରେ।
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = parser.parse(bytes(source_code, "utf-8"))
    modified_functions = set()

    def traverse(node):
        if node.type == "function_definition":
            # Node ର start_point ଏବଂ end_point 0-indexed ଥାଏ, ତେଣୁ +1
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # ଯଦି କୌଣସି ପରିବର୍ତ୍ତିତ ଲାଇନ୍ ଏହି ଫଙ୍କସନ୍ ସୀମା ଭିତରେ ଥାଏ
            for changed_line in target_lines:
                if start_line <= changed_line <= end_line:
                    for child in node.children:
                        if child.type == "identifier":
                            modified_functions.add(child.text.decode("utf-8"))
                            break

        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return list(modified_functions)

def get_blast_radius(changed_functions):
    """
    Local dependency graph ରୁ ପ୍ରଭାବିତ ସମସ୍ତ callers ଖୋଜେ।
    """
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        G = nx.node_link_graph(data, edges="links")
    except Exception:
        print("[!] Graph file ମିଳିଲା ନାହିଁ। ପ୍ରଥମେ graph_sync.py ଚଲାନ୍ତୁ।")
        return {}

    report = {}
    for fn in changed_functions:
        if fn in G:
            affected = list(nx.ancestors(G, fn))
            report[fn] = affected
        else:
            report[fn] = []
    return report

if __name__ == "__main__":
    target = "app_logic.py"
    
    print(f"[*] Analyzing Git Diff for: {target}")
    lines = get_git_diff_lines(target)
    print(f"[*] Modified Lines: {lines}")

    fns = find_functions_at_lines(target, lines)
    print(f"[*] Detected Changed Functions: {fns}")

    if fns:
        impact = get_blast_radius(fns)
        print("\n================ BLAST RADIUS REPORT ================")
        for fn, callers in impact.items():
            print(f"\nChanged Function: ⚠️  {fn}")
            print(f"Impacted Callers ({len(callers)}):")
            for caller in callers:
                print(f"   -> {caller}")
        print("=====================================================")
    else:
        print("\n[OK] କୌଣସି ଫଙ୍କସନ୍‌ରେ ପରିବର୍ତ୍ତନ ହୋଇନାହିଁ।")