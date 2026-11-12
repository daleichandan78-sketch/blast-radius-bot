import os
import re
import json
import subprocess
import networkx as nx


def load_graph(graph_path="dependency_graph.json"):
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data)


def get_changed_lines_per_file():
    """Local uncommitted diff କିମ୍ବା GitHub PR branch diff ବାହାର କରେ"""
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        cmd = ["git", "diff", "-U0", f"origin/{base_ref}...HEAD"]
    else:
        cmd = ["git", "diff", "-U0"]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    diff_output = result.stdout

    changed_files = {}
    current_file = None

    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            if current_file.endswith(".py"):
                changed_files.setdefault(current_file, set())
        elif line.startswith("@@") and current_file and current_file.endswith(".py"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start_line = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                for ln in range(start_line, start_line + max(count, 1)):
                    changed_files[current_file].add(ln)

    return changed_files


def analyze_blast_radius():
    G = load_graph()
    changed_files = get_changed_lines_per_file()

    report_lines = ["## 💥 Automated Blast Radius Report\n"]

    if not changed_files:
        report_lines.append("✅ No Python file modifications detected in this change.")
    else:
        changed_nodes = set()
        for file_path, lines in changed_files.items():
            for node_id, attrs in G.nodes(data=True):
                if attrs.get("file") == file_path:
                    start = attrs.get("start_line", 0)
                    end = attrs.get("end_line", 0)
                    if any(start <= ln <= end for ln in lines):
                        changed_nodes.add(node_id)

        if not changed_nodes:
            report_lines.append("ℹ️ Changes were made outside function definitions (e.g., imports/comments).")
        else:
            for node_id in sorted(changed_nodes):
                impacted = nx.ancestors(G, node_id)
                risk_badge = "🔴 High Impact" if len(impacted) >= 4 else ("🟡 Medium Impact" if len(impacted) > 0 else "🟢 Low Impact")
                report_lines.append(f"### Changed Function: `{node_id}` ({risk_badge})")
                report_lines.append(f"**Total Impacted Callers:** `{len(impacted)}`\n")

                if not impacted:
                    report_lines.append("- *No downstream callers affected (Top-level entry point).*")
                else:
                    for caller in sorted(impacted):
                        report_lines.append(f"- `->` `{caller}`")
                report_lines.append("")

    final_report = "\n".join(report_lines)
    print(final_report)

    # GitHub PR Comment ପାଇଁ Markdown ଫାଇଲ୍ Save କରିବା
    with open("blast_report.md", "w", encoding="utf-8") as f:
        f.write(final_report)


if __name__ == "__main__":
    analyze_blast_radius()