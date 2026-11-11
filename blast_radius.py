import json
import networkx as nx

GRAPH_FILE = "dependency_graph.json"

def load_graph():
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, edges="links")

def calculate_blast_radius(changed_function):
    G = load_graph()
    
    if changed_function not in G:
        print(f"\n[!] Function '{changed_function}' ଗ୍ରାଫ୍‌ରେ ମିଳିଲା ନାହିଁ।")
        return []

    # ଫଙ୍କସନ୍ ବଦଳିଲେ ତାହା ଉପରେ ନିର୍ଭରଶୀଳ (Ancestors/Callers) ଫଙ୍କସନ୍ ପ୍ରଭାବିତ ହୁଅନ୍ତି
    affected = nx.ancestors(G, changed_function)
    return list(affected)

# ପରୀକ୍ଷା: ଯଦି ଆମେ 'log_status' କୁ ବଦଳାଉ
target_fn = "log_status"
affected_fns = calculate_blast_radius(target_fn)

print(f"\n--- BLAST RADIUS REPORT FOR '{target_fn}' ---")
print(f"ପ୍ରଭାବିତ ହେଉଥିବା ଫଙ୍କସନ୍ ସଂଖ୍ୟା: {len(affected_fns)}")
for fn in affected_fns:
    print(f"  ⚠️  {fn}")

if not affected_fns:
    print("  କୌଣସି Caller ପ୍ରଭାବିତ ହେବେ ନାହିଁ।")