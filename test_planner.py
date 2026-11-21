from core.planner import make_plan

plan = make_plan("Does AI coding assistance actually make developers more productive?")

print("MODEL:", plan["model"])
print("OBJECTIVE:", plan["objective"])
print()
for sq in plan["sub_questions"]:
    print(sq["id"], "[" + sq["angle"] + "]", sq["question"])
    print("     search:", sq["search_query"])
    print()