from core.llm import generate_json, LLMError

ANGLES = [
    "context",
    "evidence_for",
    "evidence_against",
    "limitations",
    "expert_views",
    "future",
]

SYSTEM = """You are a research planning engine. You break a broad research
question into targeted sub-questions that can each be answered by searching
the web. You must cover multiple perspectives, including evidence that
SUPPORTS and evidence that CHALLENGES the main question. Return only JSON."""

PROMPT_TEMPLATE = """Research question: {question}

Create a research plan with 5 or 6 sub-questions.

Rules:
- Each sub-question must be specific and answerable with web sources.
- Include at least one sub-question looking for evidence that supports the
  idea and at least one looking for evidence that challenges or contradicts it.
- Include one sub-question about limitations or weaknesses of the evidence.
- "search_query" must be a short web search query (4 to 9 words), not a full sentence.
- "angle" must be exactly one of: {angles}
- Do not repeat the same idea in two sub-questions.

Return JSON in exactly this shape:
{{
  "objective": "one sentence describing the research goal",
  "sub_questions": [
    {{
      "id": "Q1",
      "question": "the specific sub-question",
      "angle": "one of the allowed angles",
      "search_query": "short search query",
      "why": "one short sentence on why this question matters"
    }}
  ]
}}"""


def make_plan(question):
    """Plan lautata hai: dict with objective, sub_questions, model."""
    question = (question or "").strip()
    if len(question) < 8:
        raise ValueError("Question bahut chhota hai. Thoda detail me likho.")
    if len(question) > 500:
        raise ValueError("Question bahut lamba hai. 500 characters se kam rakho.")

    prompt = PROMPT_TEMPLATE.format(question=question, angles=", ".join(ANGLES))
    data, model = generate_json(prompt, system=SYSTEM)

    if isinstance(data, list):
        data = {"objective": question, "sub_questions": data}

    raw = data.get("sub_questions", [])
    cleaned = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question", "")).strip()
        sq = str(item.get("search_query", "")).strip()
        if not q or not sq or sq.lower() in seen:
            continue
        seen.add(sq.lower())
        angle = str(item.get("angle", "context")).strip()
        if angle not in ANGLES:
            angle = "context"
        cleaned.append(
            {
                "id": f"Q{len(cleaned) + 1}",
                "question": q,
                "angle": angle,
                "search_query": sq,
                "why": str(item.get("why", "")).strip(),
            }
        )
        if len(cleaned) == 6:
            break

    if len(cleaned) < 3:
        raise LLMError("Planner ne kaafi sub-questions nahi banaye. Dobara try karo.")

    return {
        "question": question,
        "objective": str(data.get("objective", question)).strip(),
        "sub_questions": cleaned,
        "model": model,
    }