import os

base_dir = r"c:\Users\sujit\OneDrive\Documents\Fusion_new\Fusion\FusionIIIT\applications\visitor_hostel"
files = [
    "models.py",
    os.path.join("api", "urls.py"),
    os.path.join("api", "serializers.py"),
    os.path.join("api", "views.py"),
    "selectors.py",
    "services.py"
]

out = []
for f in files:
    path = os.path.join(base_dir, f)
    with open(path, "r", encoding="utf-8") as file:
        out.append(f"### {f}\n```python\n" + file.read() + "\n```\n")

with open(r"c:\Users\sujit\.gemini\antigravity\brain\43727e82-aaa6-4536-91ea-9953e4fd2132\refactored_visitor_hostel_code.md", "w", encoding="utf-8") as out_file:
    out_file.write("# Refactored Visitor Hostel Code\n\n" + "\n".join(out))
