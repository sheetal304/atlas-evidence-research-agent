import json
import time
from collections import Counter

from core.planner import make_plan
from core.search import collect_sources
from core.extract import extract_claims

t0 = time.time()
question = "Does AI coding assistance actually make developers more productive?"

plan = make_plan(question)
print("Plan ready:", len(plan["sub_questions"]), "sub-questions", flush=True)

search = collect_sources(plan)
sources = search["sources"]
print("Sources:", len(sources), flush=True)


def show(done, total):
    print(f"  Extraction batch {done}/{total} done", flush=True)


ex = extract_claims(plan["question"], sources, progress=show)

# Agle steps me dobara search na karna pade, isliye save kar lete hain
with open("cache_run.json", "w", encoding="utf-8") as f:
    json.dump({"plan": plan, "search": search, "extraction": ex}, f, ensure_ascii=False, indent=2)

print()
print("STATS:", ex["stats"])
print("BATCH ERRORS:", ex["batch_errors"] or "none")
print("STANCES:", dict(Counter(c["stance"] for c in ex["claims"])))
print("EVIDENCE TYPES:", dict(Counter(c["evidence_type"] for c in ex["claims"])))
print("SOURCES WITH CLAIMS:", len({c["source_id"] for c in ex["claims"]}), "of", len(sources))
print()
print("3 SAMPLE CLAIMS:")
for c in ex["claims"][:3]:
    print(c["id"], c["source_id"], "|", c["stance"], "|", c["evidence_type"])
    print("   claim:", c["claim"])
    print("   quote:", c["quote"][:140])
print()
print("Total time:", round(time.time() - t0), "seconds")