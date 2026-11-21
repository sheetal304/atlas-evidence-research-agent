from core.planner import make_plan
from core.search import collect_sources

plan = make_plan("Does AI coding assistance actually make developers more productive?")
print("Plan ready:", len(plan["sub_questions"]), "sub-questions")
print()


def show(done, total, sq):
    print(f"  Search {done}/{total} done: {sq['search_query']}")


result = collect_sources(plan, progress=show)

print()
print("UNIQUE SOURCES:", len(result["sources"]))
print("UNIQUE DOMAINS:", len({s["domain"] for s in result["sources"]}))
print()

for entry in result["query_log"]:
    status = "ERROR: " + entry["error"] if entry["error"] else "ok"
    print(entry["id"], "->", entry["found"], "results,", status)

print()
print("TOP 3 SOURCES:")
for s in result["sources"][:3]:
    print(s["id"], "|", s["domain"], "| score:", s["score"], "| date:", s["published_date"])
    print("    ", s["title"][:90])
    print("     excerpt:", s["excerpt"][:150].replace("\n", " "), "...")
