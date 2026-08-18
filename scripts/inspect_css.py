with open("frontend/Style.css", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if "backdrop-filter" in l or "glass" in l.lower() or "sidebar-lang-select" in l:
        print(f"{i+1}: {l.strip()}")
