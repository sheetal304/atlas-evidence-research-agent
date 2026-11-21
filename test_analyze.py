import json

from core.analyze import analyze

with open("cache_run.json", encoding="utf-8") as f:
    cache = json.load(f)

plan = cache["plan"]
sources = cache["search"]["sources"]
claims = cache["extraction"]["claims"]

an = analyze(plan["question"], claims, sources)

cache["analysis"] = an
with open("cache_run.json", "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print("MODEL:", an["model"])
print("OVERALL:", an["overall"])
print()
print("THEMES:")
for t in an["themes"]:
    s = t["strength"]
    print(f"- [{s['level']}] {t['title']} ({t['relationship']}) claims={t['claim_ids']}")
    print("     ", t["summary"])
    print("      why:", "; ".join(s["reasons"]))
print()
print("CONTRADICTIONS:", len(an["contradictions"]))
for c in an["contradictions"]:
    print("-", c["topic"])
    print("   A:", c["side_a"]["position"], c["side_a"]["claim_ids"])
    print("   B:", c["side_b"]["position"], c["side_b"]["claim_ids"])
    print("   inference:", c["possible_explanation"])
print()
print("GAPS:")
for g in an["gaps"]:
    print("-", g)