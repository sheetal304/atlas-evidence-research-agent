import re
from datetime import date

from core.llm import generate_json, LLMError

SYSTEM = """You are a research report writer. You write ONLY from the numbered
claims you are given. You never add outside facts, numbers, or sources.
You clearly separate evidence (what the sources say) from inference (your own
reasoning). Return only JSON."""

PROMPT_TEMPLATE = """Main research question: {question}

Write the narrative parts of an evidence-based research report.

Each sentence you write is an object:
{{"text": "...", "type": "evidence" or "inference", "claim_ids": ["C1", "C2"]}}

Rules:
- type "evidence": the sentence only restates what the cited claims say. It MUST
  list the claim_ids it is based on. Use numbers only if they appear in those claims.
- type "inference": your own reasoning or interpretation. Write it cautiously
  ("This suggests...", "One possible reading is..."). claim_ids may be empty.
- Use ONLY claim IDs from the list below. Never invent an ID.
- Be concrete. Avoid vague filler. Do not mention that you are an AI.

Sections:
- "executive_summary": 3 to 4 sentences. Must mention where sources disagree.
- "key_findings": 5 to 7 sentences, each a distinct finding.
- "perspectives": 3 to 4 sentences describing different viewpoints or conditions
  under which results differ.
- "conclusion": 2 to 3 sentences. Say clearly what the evidence supports and
  what remains uncertain.
- "further_questions": 3 to 4 plain strings (no claim IDs).

Return JSON in exactly this shape:
{{"executive_summary": [...], "key_findings": [...], "perspectives": [...],
  "conclusion": [...], "further_questions": ["..."]}}

THEMES FOUND IN ANALYSIS:
{themes_text}

CONTRADICTIONS FOUND:
{contra_text}

CLAIMS:
{claims_text}
"""

NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _cite(ids, claims_by_id, src_by_id):
    sids = []
    for i in ids:
        s = claims_by_id[i]["source_id"]
        if s not in sids:
            sids.append(s)
    return " ".join(f"[\\[{s}\\]]({src_by_id[s]['url']})" for s in sids)


def _numbers_grounded(text, claim_ids, claims_by_id):
    nums = set(NUM_RE.findall(text))
    if not nums:
        return True
    pool = " ".join(
        claims_by_id[i]["claim"] + " " + claims_by_id[i]["quote"] for i in claim_ids
    )
    have = set(NUM_RE.findall(pool))
    return nums <= have


def _render(items, claims_by_id, src_by_id, counters):
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        text = str(it.get("text", "")).strip()
        if not text:
            continue
        kind = str(it.get("type", "inference")).strip()
        ids = [str(i).strip() for i in it.get("claim_ids", []) if str(i).strip() in claims_by_id]
        counters["total"] += 1

        if kind == "evidence":
            if not ids:
                counters["demoted_no_citation"] += 1
                kind = "inference"
            elif not _numbers_grounded(text, ids, claims_by_id):
                counters["demoted_number_mismatch"] += 1
                kind = "inference"

        if kind == "evidence":
            counters["evidence"] += 1
            out.append(f"{text} {_cite(ids, claims_by_id, src_by_id)}")
        else:
            counters["inference"] += 1
            out.append(f"{text} *(inference)*")
    return out


def _themes_text(analysis):
    lines = []
    for t in analysis["themes"]:
        lines.append(f"- {t['title']} ({t['relationship']}): {t['summary']} claims={t['claim_ids']}")
    return "\n".join(lines)


def _contra_text(analysis):
    if not analysis["contradictions"]:
        return "none"
    lines = []
    for c in analysis["contradictions"]:
        lines.append(
            f"- {c['topic']}: A={c['side_a']['position']} {c['side_a']['claim_ids']} "
            f"vs B={c['side_b']['position']} {c['side_b']['claim_ids']}"
        )
    return "\n".join(lines)


def build_report(plan, search, extraction, analysis, model_note=""):
    sources = search["sources"]
    claims = extraction["claims"]
    src_by_id = {s["id"]: s for s in sources}
    claims_by_id = {c["id"]: c for c in claims}

    claims_text = "\n".join(
        f"[{c['id']}] ({c['source_id']}, {src_by_id[c['source_id']]['domain']}, "
        f"{c['evidence_type']}, {c['stance']}) {c['claim']}"
        for c in claims
    )
    prompt = PROMPT_TEMPLATE.format(
        question=plan["question"],
        themes_text=_themes_text(analysis),
        contra_text=_contra_text(analysis),
        claims_text=claims_text,
    )
    data, model = generate_json(prompt, system=SYSTEM)
    if not isinstance(data, dict):
        raise LLMError("Report ka format galat aaya. Dobara try karo.")

    counters = {"total": 0, "evidence": 0, "inference": 0,
                "demoted_no_citation": 0, "demoted_number_mismatch": 0}
    exec_s = _render(data.get("executive_summary"), claims_by_id, src_by_id, counters)
    findings = _render(data.get("key_findings"), claims_by_id, src_by_id, counters)
    persp = _render(data.get("perspectives"), claims_by_id, src_by_id, counters)
    concl = _render(data.get("conclusion"), claims_by_id, src_by_id, counters)
    if not exec_s or not findings:
        raise LLMError("Report me summary ya findings nahi bane. Dobara try karo.")

    ov = analysis["overall"]
    st = extraction["stats"]
    qlog = search["query_log"]
    md = []
    a = md.append

    a("# ATLAS Research Report\n")
    a(f"**Question:** {plan['question']}\n")
    a(f"**Objective:** {plan['objective']}\n")
    a(f"*Generated on {date.today().isoformat()}. Evidence-first report: evidence sentences carry "
      f"source citations, inference sentences are marked.*\n")

    a("## Executive summary\n")
    a(" ".join(exec_s) + "\n")

    a("## Research methodology\n")
    a(f"1. **Planning:** the question was split into {len(plan['sub_questions'])} sub-questions:")
    for sq in plan["sub_questions"]:
        a(f"   - {sq['id']} ({sq['angle']}): {sq['question']}")
    ok_q = sum(1 for q in qlog if not q["error"])
    a(f"2. **Search:** {ok_q} of {len(qlog)} web searches succeeded, giving "
      f"{len(sources)} unique sources (duplicates removed by URL).")
    a(f"3. **Evidence extraction:** {st['proposed']} claims were proposed from source excerpts. "
      f"{st['verified']} were kept because their supporting quote was found verbatim in the excerpt; "
      f"{st['rejected']} were rejected.")
    a("4. **Analysis:** claims were grouped into themes, compared for agreement and "
      "disagreement, and checked for gaps. Theme strength is computed by fixed rules, not by the AI.")
    a("5. **Writing:** evidence sentences must cite claims. Sentences without valid citations, "
      "or with numbers not found in the cited claims, are downgraded to inference.\n")

    a("## Key findings\n")
    for s in findings:
        a(f"- {s}")
    a("")

    a("## Evidence by theme\n")
    for t in analysis["themes"]:
        s = t["strength"]
        a(f"### {t['title']}")
        a(f"*Relationship: {t['relationship']} | Evidence strength: **{s['level']}** "
          f"({'; '.join(s['reasons'])})*\n")
        a(f"{t['summary']} {_cite(t['claim_ids'], claims_by_id, src_by_id)}\n")

    if persp:
        a("## Different perspectives\n")
        for s in persp:
            a(f"- {s}")
        a("")

    a("## Contradictions and disagreements\n")
    if analysis["contradictions"]:
        for c in analysis["contradictions"]:
            ca = _cite(c["side_a"]["claim_ids"], claims_by_id, src_by_id)
            cb = _cite(c["side_b"]["claim_ids"], claims_by_id, src_by_id)
            a(f"### {c['topic']}")
            a(f"- **Side A:** {c['side_a']['position']} {ca}")
            a(f"- **Side B:** {c['side_b']['position']} {cb}")
            a(f"- **Possible explanation (inference):** {c['possible_explanation']}\n")
    else:
        a("No direct contradictions were identified in the retrieved evidence.\n")

    a("## Limitations and evidence assessment\n")
    a(f"- **Evidence base:** {ov['evidence_base']} by ATLAS's simple rule: "
      f"{ov['claims']} verified claims from {ov['sources_with_claims']} sources on "
      f"{ov['domains']} domains; {ov['measured_data_claims']} claims are labelled measured data.")
    a(f"- **Theme strength:** {ov['theme_strength']['Strong']} strong, "
      f"{ov['theme_strength']['Moderate']} moderate, {ov['theme_strength']['Weak']} weak. "
      f"This is a transparent rule-based score and is not a probability of being correct. "
      f"For a theme about disagreement, a high score means the disagreement itself is well documented.")
    a(f"- **Recency:** only {ov['sources_with_known_date']} of {ov['sources_total']} sources "
      f"provided a publication date, so recency could not be assessed reliably.")
    a("- **Excerpts, not full pages:** claims come from search-result excerpts, so context outside "
      "the excerpt is not seen.")
    a("- **What verification means:** a verified quote proves the text exists in the excerpt. "
      "It does not prove the claim itself is true. Different sources can also report the same underlying study, so the number of sources is not the same as independent confirmation.")
    vendor = sum(1 for c in claims if c["evidence_type"] == "vendor_claim")
    survey = sum(1 for c in claims if c["evidence_type"] == "survey")
    a(f"- **Source type mix:** {vendor} vendor claims and {survey} survey-based claims; "
      f"these can reflect commercial interest or perception rather than measurement.")
    a("- **Coverage:** results depend on the search queries and on what the search provider returned. "
      "Claim labels (type, stance) were assigned by an AI model and can contain errors.")
    if st["rejected"] or counters["demoted_no_citation"] or counters["demoted_number_mismatch"]:
        a(f"- **Safeguards triggered:** {st['rejected']} claims rejected for unverifiable quotes; "
          f"{counters['demoted_no_citation'] + counters['demoted_number_mismatch']} report sentences "
          f"downgraded to inference.")
    a("")

    a("## Conclusion\n")
    a(" ".join(concl) + "\n" if concl else "No conclusion could be generated.\n")

    a("## Further research questions\n")
    questions = [str(q).strip() for q in data.get("further_questions", []) if str(q).strip()]
    for g in analysis["gaps"] + questions:
        a(f"- {g}")
    a("")

    a("## Sources\n")
    cited_sources = {c["source_id"] for c in claims}
    for s in sources:
        if s["id"] not in cited_sources:
            continue
        d = s["published_date"] or "date not provided"
        a(f"- **{s['id']}** [{s['title']}]({s['url']}) ({s['domain']}, {d})")
    a("")

    return {
        "markdown": "\n".join(md),
        "stats": counters,
        "report_model": model,
    }