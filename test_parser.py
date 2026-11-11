from tree_sitter_languages import get_language, get_parser

# Python parser ପ୍ରସ୍ତୁତ କରିବା
language = get_language("python")
parser = get_parser("python")

sample_code = """
def calculate_tax(amount):
    rate = get_tax_rate()
    return amount * rate

def process_order(order_id):
    total = fetch_order_amount(order_id)
    final_tax = calculate_tax(total)
    save_invoice(order_id, final_tax)
"""

tree = parser.parse(bytes(sample_code, "utf-8"))

query = language.query("""
(function_definition
  name: (identifier) @function_name)

(call
  function: (identifier) @call_name)
""")

captures = query.captures(tree.root_node)

print("\n--- AST Parser ଫଳାଫଳ (Extracted Symbols) ---")
if isinstance(captures, dict):
    for tag, nodes in captures.items():
        for node in nodes:
            print(f"[{tag}] -> {node.text.decode('utf-8')}")
else:
    for node, tag in captures:
        print(f"[{tag}] -> {node.text.decode('utf-8')}")