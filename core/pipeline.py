import os
import time

from dotenv import load_dotenv

from core.analyze import analyze
from core.extract import extract_claims
from core.planner import make_plan
from core.report import build_report
from core.search import collect_sources

load_dotenv()


def check_keys():
    missing = []
    if not os.getenv("TAVILY_API_KEY"):
        missing.append("TAVILY_API_KEY")
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")
    return missing


def run_research(question, on_event=None):
    """Poori pipeline chalata hai. Errors upar app tak jaate hain."""

    def say(text):
        if on_event:
            on_event(text)

    t0 = time.time()

    say("Stage 1/5: planning the research")
    plan = make_plan(question)
    say(f"Plan ready: {len(plan['sub_questions'])} sub-questions")

    say("Stage 2/5: searching the web for each sub-question")

    def search_progress(done, total, sq):
        say(f"Searched {done}/{total}: {sq['search_query']}")

    search = collect_sources(plan, progress=search_progress)
    n_dom = len({s["domain"] for s in search["sources"]})
    say(f"Collected {len(search['sources'])} unique sources from {n_dom} domains")

    say("Stage 3/5: extracting and verifying claims")

    def extract_progress(done, total):
        say(f"Extraction batch {done}/{total} done")

    extraction = extract_claims(plan["question"], search["sources"], progress=extract_progress)
    st_ = extraction["stats"]
    say(f"{st_['verified']} claims verified, {st_['rejected']} rejected (quote not found in source)")

    say("Stage 4/5: comparing sources")
    analysis = analyze(plan["question"], extraction["claims"], search["sources"])
    say(f"Found {len(analysis['themes'])} themes and {len(analysis['contradictions'])} contradictions")

    say("Stage 5/5: writing the citation-linked report")
    report = build_report(plan, search, extraction, analysis)

    return {
        "plan": plan,
        "search": search,
        "extraction": extraction,
        "analysis": analysis,
        "report": report,
        "elapsed": round(time.time() - t0),
    }