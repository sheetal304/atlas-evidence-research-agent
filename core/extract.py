import re

from core.llm import generate_json, LLMError

BATCH_SIZE = 7

EVIDENCE_TYPES = ["measured_data", "survey", "expert_opinion", "vendor_claim", "anecdote"]
STANCES = ["supports", "challenges", "mixed", "neutral"]

SYSTEM = """You are an evidence extraction engine for a research tool.
You read source excerpts and extract only claims that are explicitly stated
in them. You never use outside knowledge. You never invent numbers or quotes.
Return only JSON."""

PROMPT_TEMPLATE = """Main research question: {question}

Below are source excerpts. Extract up to 3 of the most relevant factual claims
from EACH source.

Rules:
- "claim": your own short paraphrase (max 30 words). Use numbers only if they appear in the excerpt.
- "quote": an EXACT passage copied character-for-character from that source's
  excerpt (max 30 words). Do not edit it. Do not combine separate passages.
- "source_id": the ID of the source the claim came from.
- "evidence_type": exactly one of: {types}
    measured_data = controlled experiment, trial, or analysis of real data
    survey = self-reported opinions or perceptions from a group of people
    expert_opinion = commentary or judgement by one person or organization
    vendor_claim = claim made by a company about its own product
    anecdote = a single personal experience or example
- "stance": how the claim relates to the main question. Exactly one of: {stances}
- Skip a source completely if it has nothing relevant.

Return JSON in exactly this shape:
{{"claims": [{{"source_id": "S1", "claim": "...", "quote": "...", "evidence_type": "...", "stance": "..."}}]}}

SOURCES:
{sources_text}
"""


def _norm(text):
    text = text.lower()
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " ")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def quote_is_verified(quote, excerpt):
    """True agar quote (ya uske ... se alag hue hisse) excerpt me sach me maujood hain."""
    parts = re.split(r"\.\.\.|\u2026", quote)
    parts = [p.strip(" .\"'") for p in parts if len(p.strip(" .\"'")) >= 10]
    if not parts:
        return False
    hay = _norm(excerpt)
    return all(_norm(p) in hay for p in parts)


def _format_sources(batch):
    blocks = []
    for s in batch:
        blocks.append(f"[{s['id']}] {s['title']} ({s['domain']})\n{s['excerpt']}")
    return "\n\n---\n\n".join(blocks)


def extract_claims(question, sources, progress=None):
    """
    Lautata hai: {"claims": [...], "stats": {...}, "batch_errors": [...]}
    Sirf wahi claims bachte hain jinka quote source ke text me verify hua.
    """
    by_id = {s["id"]: s for s in sources}
    batches = [sources[i:i + BATCH_SIZE] for i in range(0, len(sources), BATCH_SIZE)]

    claims = []
    batch_errors = []
    proposed = 0
    rejected = 0

    for n, batch in enumerate(batches, start=1):
        prompt = PROMPT_TEMPLATE.format(
            question=question,
            types=", ".join(EVIDENCE_TYPES),
            stances=", ".join(STANCES),
            sources_text=_format_sources(batch),
        )
        try:
            data, _model = generate_json(prompt, system=SYSTEM)
            items = data.get("claims", []) if isinstance(data, dict) else data
        except LLMError as e:
            batch_errors.append(f"Batch {n}: {str(e)[:150]}")
            items = []

        allowed = {s["id"] for s in batch}
        for item in items:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("source_id", "")).strip()
            claim = str(item.get("claim", "")).strip()
            quote = str(item.get("quote", "")).strip()
            if sid not in allowed or not claim or not quote:
                continue
            proposed += 1
            if not quote_is_verified(quote, by_id[sid]["excerpt"]):
                rejected += 1
                continue
            etype = str(item.get("evidence_type", "")).strip()
            stance = str(item.get("stance", "")).strip()
            claims.append({
                "id": f"C{len(claims) + 1}",
                "source_id": sid,
                "claim": claim,
                "quote": quote,
                "evidence_type": etype if etype in EVIDENCE_TYPES else "expert_opinion",
                "stance": stance if stance in STANCES else "neutral",
            })

        if progress:
            progress(n, len(batches))

    if not claims:
        detail = f" {batch_errors[0]}" if batch_errors else ""
        raise LLMError("Koi bhi verified claim nahi mila." + detail)

    return {
        "claims": claims,
        "stats": {"proposed": proposed, "verified": len(claims), "rejected": rejected},
        "batch_errors": batch_errors,
    }
