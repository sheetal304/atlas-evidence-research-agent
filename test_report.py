import json
import re

from core.report import build_report

with open("cache_run.json", encoding="utf-8") as f:
    cache = json.load(f)

rep = build_report(
    cache["plan"], cache["search"], cache["extraction"], cache["analysis"]
)

with open("report_test.md", "w", encoding="utf-8") as f:
    f.write(rep["markdown"])

cache["report"] = rep
with open("cache_run.json", "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

md = rep["markdown"]
links = re.findall(r"\]\((https?://[^)]+)\)", md)
known = {s["url"] for s in cache["search"]["sources"]}
bad = [u for u in links if u not in known]

print("REPORT MODEL:", rep["report_model"])
print("SENTENCE STATS:", rep["stats"])
print("TOTAL LINKS IN REPORT:", len(links))
print("LINKS NOT FROM RETRIEVED SOURCES:", len(bad))
print("REPORT LENGTH:", len(md.split()), "words")
print()
print("---- PREVIEW (first 45 lines) ----")
print("\n".join(md.splitlines()[:45]))
print()
print("Poora report 'report_test.md' file me save ho gaya.")