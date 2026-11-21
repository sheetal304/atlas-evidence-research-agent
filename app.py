import html
import json
import os

import streamlit as st

from core.pipeline import check_keys, run_research

CACHE_FILE = "cache_run.json"
EXAMPLE = "Does AI coding assistance actually make developers more productive?"

st.set_page_config(page_title="ATLAS", page_icon="◆", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, textarea { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; max-width: 1180px; }
#MainMenu, footer { visibility: hidden; }
.atlas-title { font-size: 2rem; font-weight: 700; letter-spacing: .22em; margin: 0; }
.atlas-sub { color: #8B96A5; font-size: .95rem; margin: .25rem 0 1.4rem 0; }
.card { background: #121821; border: 1px solid #1F2937; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }
.metric { background: #121821; border: 1px solid #1F2937; border-radius: 12px; padding: 12px 14px; }
.metric .v { font-size: 1.6rem; font-weight: 700; line-height: 1.1; }
.metric .l { color: #8B96A5; font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; margin-top: 4px; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: .72rem; font-weight: 600; border: 1px solid; margin-right: 6px; }
.b-Strong { color: #4ADE80; border-color: #1F6F3F; background: #0F2A1A; }
.b-Moderate { color: #FBBF24; border-color: #7A5A12; background: #2A2208; }
.b-Weak { color: #F87171; border-color: #7A2A2A; background: #2A1010; }
.b-supports { color: #7CB2FF; border-color: #284B80; background: #0E1B30; }
.b-challenges { color: #FB9F5B; border-color: #7A4518; background: #2A1A0C; }
.b-mixed { color: #C4A1FF; border-color: #53388A; background: #1C1230; }
.b-neutral, .b-type { color: #9AA7B8; border-color: #2B3647; background: #151C27; }
.muted { color: #8B96A5; font-size: .8rem; }
.claim { margin: 8px 0 6px 0; font-size: .95rem; }
.quote { border-left: 3px solid #2B3647; padding-left: 10px; color: #AEB9C8; font-size: .85rem; font-style: italic; }
.section-label { color: #8B96A5; font-size: .75rem; text-transform: uppercase; letter-spacing: .09em; margin: 18px 0 8px 0; }
a { color: #7CA9FF !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def metric(value, label):
    return f'<div class="metric"><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div></div>'


def claim_card(c, src_by_id):
    s = src_by_id[c["source_id"]]
    return (
        '<div class="card">'
        f'<span class="badge b-{c["stance"]}">{esc(c["stance"])}</span>'
        f'<span class="badge b-type">{esc(c["evidence_type"].replace("_", " "))}</span>'
        f'<span class="muted">{esc(c["id"])} · '
        f'<a href="{esc(s["url"])}" target="_blank">{esc(c["source_id"])} · {esc(s["domain"])}</a></span>'
        f'<div class="claim">{esc(c["claim"])}</div>'
        f'<div class="quote">“{esc(c["quote"])}”</div>'
        "</div>"
    )


def set_example():
    st.session_state.question = EXAMPLE


def load_saved():
    with open(CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for key in ["plan", "search", "extraction", "analysis", "report"]:
        if key not in data:
            raise ValueError(
                f"Saved run incomplete ('{key}' missing). Run test_report.py or a live run first."
            )
    data["saved"] = True
    return data


def save_run(res):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


def render_results(res):
    plan, search, extraction = res["plan"], res["search"], res["extraction"]
    analysis, report = res["analysis"], res["report"]
    sources, claims = search["sources"], extraction["claims"]
    src_by_id = {s["id"]: s for s in sources}
    claims_by_id = {c["id"]: c for c in claims}
    ov, stats = analysis["overall"], extraction["stats"]

    if res.get("saved"):
        st.info("Showing a saved earlier run. No new API calls were made.")

    st.markdown(f"**Question:** {esc(plan['question'])}")

    cols = st.columns(6)
    items = [
        (len(sources), "Unique sources"),
        (ov["domains"], "Domains with claims"),
        (stats["verified"], "Verified claims"),
        (stats["rejected"], "Rejected claims"),
        (len(analysis["themes"]), "Themes"),
        (len(analysis["contradictions"]), "Contradictions"),
    ]
    for col, (v, l) in zip(cols, items):
        col.markdown(metric(v, l), unsafe_allow_html=True)

    t_map, t_report, t_claims, t_sources, t_plan = st.tabs(
        ["Evidence map", "Report", "Claim explorer", "Sources", "Research plan"]
    )

    # ---------------- Evidence map ----------------
    with t_map:
        ts = ov["theme_strength"]
        st.markdown(
            '<div class="card">'
            f'<b>Evidence base: {esc(ov["evidence_base"])}</b><br>'
            f'<span class="muted">{ov["claims"]} verified claims from {ov["sources_with_claims"]} sources on '
            f'{ov["domains"]} domains. {ov["measured_data_claims"]} claims are labelled measured data. '
            f'Themes: {ts["Strong"]} strong, {ts["Moderate"]} moderate, {ts["Weak"]} weak. '
            f'Publication date known for {ov["sources_with_known_date"]} of {ov["sources_total"]} sources. '
            "Strength is a transparent rule (domains and measured data), not a probability of being correct, "
            "and it does not judge how trustworthy each source is. Several sources can repeat the same study, so more sources is not always independent confirmation.</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-label">Themes across sources</div>', unsafe_allow_html=True)
        for t in analysis["themes"]:
            s = t["strength"]
            st.markdown(
                '<div class="card">'
                f'<span class="badge b-{s["level"]}">{esc(s["level"])}</span>'
                f'<span class="badge b-type">{esc(t["relationship"].replace("_", " "))}</span>'
                f'<b>{esc(t["title"])}</b>'
                f'<div class="claim">{esc(t["summary"])}</div>'
                f'<div class="muted">Why this strength: {esc("; ".join(s["reasons"]))}</div>'
                "</div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Show the {len(t['claim_ids'])} supporting claims"):
                for cid in t["claim_ids"]:
                    st.markdown(claim_card(claims_by_id[cid], src_by_id), unsafe_allow_html=True)

        st.markdown('<div class="section-label">Where sources disagree</div>', unsafe_allow_html=True)
        if not analysis["contradictions"]:
            st.write("No direct contradictions were identified in the retrieved evidence.")
        for c in analysis["contradictions"]:
            st.markdown(f"**{esc(c['topic'])}**")
            left, right = st.columns(2)
            for col, side, name in ((left, c["side_a"], "Side A"), (right, c["side_b"], "Side B")):
                with col:
                    st.markdown(
                        f'<div class="card"><span class="badge b-type">{name}</span>'
                        f'<div class="claim">{esc(side["position"])}</div></div>',
                        unsafe_allow_html=True,
                    )
                    for cid in side["claim_ids"]:
                        st.markdown(claim_card(claims_by_id[cid], src_by_id), unsafe_allow_html=True)
            st.markdown(
                f'<div class="muted"><b>Possible explanation (inference):</b> {esc(c["possible_explanation"])}</div>',
                unsafe_allow_html=True,
            )
            st.divider()

        st.markdown('<div class="section-label">Research gaps</div>', unsafe_allow_html=True)
        for g in analysis["gaps"]:
            st.markdown(f"- {g}")

    # ---------------- Report ----------------
    with t_report:
        md = report["markdown"]
        st.download_button(
            "Download report (Markdown)", md, file_name="atlas_report.md", mime="text/markdown"
        )
        with st.expander("Copy raw Markdown"):
            st.code(md, language="markdown")
        st.markdown(md)

    # ---------------- Claim explorer ----------------
    with t_claims:
        f1, f2 = st.columns(2)
        stance = f1.selectbox("Stance", ["all", "supports", "challenges", "mixed", "neutral"])
        etype = f2.selectbox(
            "Evidence type",
            ["all", "measured_data", "survey", "expert_opinion", "vendor_claim", "anecdote"],
        )
        shown = [
            c for c in claims
            if (stance == "all" or c["stance"] == stance)
            and (etype == "all" or c["evidence_type"] == etype)
        ]
        st.caption(f"{len(shown)} of {len(claims)} claims. Every quote was found verbatim in the source excerpt.")
        for c in shown:
            st.markdown(claim_card(c, src_by_id), unsafe_allow_html=True)

    # ---------------- Sources ----------------
    with t_sources:
        st.caption("Missing metadata is shown as not provided. Nothing is guessed.")
        for s in sources:
            n_claims = sum(1 for c in claims if c["source_id"] == s["id"])
            with st.expander(f"{s['id']} · {s['domain']} · {s['title'][:90]}"):
                score = f"{s['score']:.2f}" if isinstance(s.get("score"), (int, float)) else "not provided"
                date = s.get("published_date") or "not provided"
                st.markdown(f"[{s['url']}]({s['url']})")
                st.markdown(
                    f"Relevance score: **{score}** · Published: **{date}** · "
                    f"Claims extracted: **{n_claims}** · Found for: **{', '.join(s['found_for'])}**"
                )
                st.markdown("**Excerpt**")
                st.write(s["excerpt"])
                for c in claims:
                    if c["source_id"] == s["id"]:
                        st.markdown(claim_card(c, src_by_id), unsafe_allow_html=True)

    # ---------------- Plan ----------------
    with t_plan:
        st.markdown(f"**Objective:** {esc(plan['objective'])}")
        for sq in plan["sub_questions"]:
            q = next((e for e in search["query_log"] if e["id"] == sq["id"]), None)
            found = f"{q['found']} results" if q and not q["error"] else "search failed"
            st.markdown(
                '<div class="card">'
                f'<span class="badge b-type">{esc(sq["angle"].replace("_", " "))}</span>'
                f'<span class="muted">{esc(sq["id"])} · query: {esc(sq["search_query"])} · {found}</span>'
                f'<div class="claim">{esc(sq["question"])}</div>'
                f'<div class="muted">{esc(sq["why"])}</div></div>',
                unsafe_allow_html=True,
            )


# ======================= PAGE =======================
st.markdown('<p class="atlas-title">ATLAS</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="atlas-sub">Adaptive Tool-powered Literature &amp; Analysis System. '
    "Evidence-first research: every claim traced to a source.</p>",
    unsafe_allow_html=True,
)

if "result" not in st.session_state:
    st.session_state.result = None
if "question" not in st.session_state:
    st.session_state.question = ""

st.text_area(
    "Research question",
    key="question",
    height=90,
    placeholder="Ask a complex research question, for example: " + EXAMPLE,
    label_visibility="collapsed",
)
b1, b2, b3, _ = st.columns([1, 1.3, 1.2, 3])
run = b1.button("Run research", type="primary")
b2.button("Use demo question", on_click=set_example)
open_saved = b3.button("Open saved run")

if open_saved:
    try:
        st.session_state.result = load_saved()
    except FileNotFoundError:
        st.error("No saved run yet. Run a live research first.")
    except Exception as e:
        st.error(f"Could not open saved run: {e}")

if run:
    missing = check_keys()
    if missing:
        st.error(
            "Missing API key(s): " + ", ".join(missing)
            + ". Add them to the .env file (see .env.example) and restart the app."
        )
    else:
        with st.status("Researching...", expanded=True) as status:
            try:
                res = run_research(st.session_state.question, on_event=lambda t: st.write(t))
                save_run(res)
                st.session_state.result = res
                status.update(label=f"Research complete in {res['elapsed']} seconds",
                              state="complete", expanded=False)
            except ValueError as e:
                status.update(label="Please check your question", state="error")
                st.error(str(e))
            except Exception as e:
                status.update(label="Research failed", state="error")
                st.error(f"{type(e).__name__}: {e}")

if st.session_state.result:
    render_results(st.session_state.result)
else:
    st.markdown('<div class="section-label">How ATLAS differs from ordinary AI search</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        '<div class="card"><b>Plans, then searches</b><div class="claim muted">'
        "The question is split into sub-questions, including ones that look for evidence "
        "against the idea, and each is searched separately.</div></div>",
        unsafe_allow_html=True,
    )
    c2.markdown(
        '<div class="card"><b>Verifies its own quotes</b><div class="claim muted">'
        "Each claim must come with a quote. Code checks the quote exists in the source text; "
        "claims that fail are rejected.</div></div>",
        unsafe_allow_html=True,
    )
    c3.markdown(
        '<div class="card"><b>Shows where sources disagree</b><div class="claim muted">'
        "Claims are compared across sources. Agreements, conflicts, weak evidence and gaps "
        "are shown, with the evidence behind each.</div></div>",
        unsafe_allow_html=True,
    )