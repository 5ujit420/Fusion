import ast
import json

with open(r"c:\Users\sujit\OneDrive\Documents\Fusion_new\Fusion\FusionIIIT\applications\placement_cell\views.py", "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)

funcs = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        name = node.name
        start = node.lineno
        end = node.end_lineno
        funcs.append({"name": name, "start": start, "end": end, "lines": end - start + 1})

funcs.sort(key=lambda x: x["start"])
for fn in funcs:
    print(f"{fn['name']}: {fn['start']} to {fn['end']} ({fn['lines']} lines)")
