from core.llm import generate_json, LLMError

SYSTEM = """You are a cross-source analysis engine for a research tool.
You only use the numbered claims you are given. You never add outside facts.
You separate what the claims say (evidence) from your own reasoning (inference).
Return only JSON."""

PROMPT_TEMPLATE = """Main research question: {question}

Below are claims extracted from different web sources. Each line shows:
[claim_id] (source_id, domain, evidence_type, stance) claim text

Analyze them together.

Rules:
- Use ONLY the claim IDs listed below. Never invent an ID.
- "themes": 3 to 5 themes. Each has a short title, a 1-2 sentence summary that
  only restates what the cited claims say, the claim_ids that support it, and a
  "relationship": exactly one of agreement, disagreement, mixed, single_source.
    agreement = several sources point the same way
    disagreement = sources point in different directions
    mixed = results depend on conditions or context
    single_source = only one source makes the point
- "contradictions": 0 to 3 real conflicts between claims. Each has a topic,
  side_a and side_b (a "position" in one sentence and its claim_ids), and a
  "possible_explanation". The explanation is YOUR inference, so write it
  cautiously (for example "One possible reason is ..."). If you cannot think of
  a reasonable explanation, write "Not clear from the retrieved evidence."
- "gaps": 2 to 4 specific things the claims do NOT answer but that matter for
  the question. Write each as a short sentence.

Return JSON in exactly this shape:
{{
  "themes": [{{"title": "", "summary": "", "claim_ids": ["C1"], "relationship": ""}}],
  "contradictions": [{{"topic": "", "side_a": {{"position": "", "claim_ids": ["C1"]}},
                       "side_b": {{"position": "", "claim_ids": ["C2"]}},
                       "possible_explanation": ""}}],
  "gaps": [""]
}}

CLAIMS:
{claims_text}
"""

RELATIONSHIPS = ["agreement", "disagreement", "mixed", "single_source"]


def _claims_text(claims, src_by_id):
    lines = []
    for c in claims:
        s = src_by_id[c["source_id"]]
        lines.append(
            f"[{c['id']}] ({c['source_id']}, {s['domain']}, "
            f"{c['evidence_type']}, {c['stance']}) {c['claim']}"
        )
    return "\n".join(lines)


def _valid_ids(ids, valid):
    out = []
    for i in ids if isinstance(ids, list) else []:
        i = str(i).strip()
        if i in valid and i not in out:
            out.append(i)
    return out


def theme_strength(claim_ids, claims_by_id, src_by_id):
    """Strength code nikalta hai (LLM nahi), sirf observable cheezon se."""
    cl = [claims_by_id[i] for i in claim_ids]
    source_ids = {c["source_id"] for c in cl}
    domains = {src_by_id[s]["domain"] for s in source_ids}
    measured = sum(1 for c in cl if c["evidence_type"] == "measured_data")

    if len(domains) >= 3 and measured >= 2:
        level = "Strong"
    elif len(domains) >= 2 and (measured >= 1 or len(cl) >= 3):
        level = "Moderate"
    else:
        level = "Weak"

    reasons = [
        f"{len(cl)} claims from {len(source_ids)} sources on {len(domains)} domains",
        f"{measured} based on measured data",
    ]
    if len(domains) == 1:
        reasons.append("only one domain, so no independent confirmation")
    return {"level": level, "reasons": reasons,
            "n_claims": len(cl), "n_sources": len(source_ids),
            "n_domains": len(domains), "n_measured": measured}


def analyze(question, claims, sources):
    """Lautata hai: {"themes", "contradictions", "gaps", "overall", "model"}"""
    src_by_id = {s["id"]: s for s in sources}
    claims_by_id = {c["id"]: c for c in claims}
    valid = set(claims_by_id)

    prompt = PROMPT_TEMPLATE.format(
        question=question, claims_text=_claims_text(claims, src_by_id)
    )
    data, model = generate_json(prompt, system=SYSTEM)
    if not isinstance(data, dict):
        raise LLMError("Analysis ka format galat aaya. Dobara try karo.")

    themes = []
    for t in data.get("themes", []):
        if not isinstance(t, dict):
            continue
        ids = _valid_ids(t.get("claim_ids"), valid)
        title = str(t.get("title", "")).strip()
        if not ids or not title:
            continue
        rel = str(t.get("relationship", "")).strip()
        themes.append({
            "title": title,
            "summary": str(t.get("summary", "")).strip(),
            "claim_ids": ids,
            "relationship": rel if rel in RELATIONSHIPS else "mixed",
            "strength": theme_strength(ids, claims_by_id, src_by_id),
        })

    contradictions = []
    for c in data.get("contradictions", []):
        if not isinstance(c, dict):
            continue
        a, b = c.get("side_a") or {}, c.get("side_b") or {}
        a_ids = _valid_ids(a.get("claim_ids"), valid)
        b_ids = _valid_ids(b.get("claim_ids"), valid)
        if not a_ids or not b_ids:
            continue
        contradictions.append({
            "topic": str(c.get("topic", "")).strip(),
            "side_a": {"position": str(a.get("position", "")).strip(), "claim_ids": a_ids},
            "side_b": {"position": str(b.get("position", "")).strip(), "claim_ids": b_ids},
            "possible_explanation": str(c.get("possible_explanation", "")).strip(),
        })

    gaps = [str(g).strip() for g in data.get("gaps", []) if str(g).strip()]

    if not themes:
        raise LLMError("Analysis me koi valid theme nahi bana. Dobara try karo.")

    used_sources = {c["source_id"] for c in claims}
    domains = {src_by_id[s]["domain"] for s in used_sources}
    measured = sum(1 for c in claims if c["evidence_type"] == "measured_data")
    dated = sum(1 for s in sources if s.get("published_date"))
    counts = {"Strong": 0, "Moderate": 0, "Weak": 0}
    for t in themes:
        counts[t["strength"]["level"]] += 1

    if len(domains) >= 8 and counts["Strong"] + counts["Moderate"] >= 3:
        base = "Broad"
    elif len(domains) >= 4:
        base = "Moderate"
    else:
        base = "Limited"

    overall = {
        "evidence_base": base,
        "claims": len(claims),
        "sources_with_claims": len(used_sources),
        "domains": len(domains),
        "measured_data_claims": measured,
        "theme_strength": counts,
        "contradictions_found": len(contradictions),
        "sources_with_known_date": dated,
        "sources_total": len(sources),
    }
    return {"themes": themes, "contradictions": contradictions,
            "gaps": gaps, "overall": overall, "model": model}