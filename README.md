\# ATLAS: Adaptive Tool-powered Literature \& Analysis System



\*\*An evidence-first research agent. Every claim is traced to a source quote, and disagreement between sources is shown, not hidden.\*\*



Built for the Tavily Research Agent challenge at a Global AI Hackathon.



\## Problem



Ordinary AI search gives one fluent answer. You cannot easily see which source said what, whether the sources agree, or where the evidence is weak. A confident summary can hide conflicting studies and missing evidence.



\## Solution



ATLAS treats research as a pipeline, not a single prompt:



1\. \*\*Plan:\*\* the question is split into sub-questions, including ones that look for evidence \*against\* the idea.

2\. \*\*Search:\*\* each sub-question is searched separately with Tavily; duplicate URLs are removed.

3\. \*\*Extract and verify:\*\* an LLM proposes claims, each with an exact quote. Code checks that the quote really appears in the source excerpt. Claims that fail are rejected.

4\. \*\*Analyze:\*\* claims are grouped into themes, compared across sources for agreement and disagreement, and checked for research gaps.

5\. \*\*Report:\*\* a citation-linked report where evidence sentences cite sources and reasoning is marked as inference.



\## Key features



\- \*\*Claim-to-source traceability:\*\* every claim shows its source link, evidence type, stance and verbatim quote.

\- \*\*Quote verification:\*\* unverifiable claims are rejected and counted.

\- \*\*Side-by-side contradictions:\*\* conflicting claims are shown next to each other with a possible explanation clearly marked as inference.

\- \*\*Rule-based evidence strength:\*\* Strong / Moderate / Weak is computed by code from observable facts (number of domains, measured-data claims). It is not an AI opinion and not a probability of being correct.

\- \*\*Evidence vs inference:\*\* report sentences without valid citations, or with numbers not found in the cited claims, are automatically downgraded to inference.

\- \*\*Research gaps:\*\* questions the retrieved evidence does not answer.

\- \*\*Source explorer:\*\* excerpt, relevance score and publication date shown only when the search provider returns them; otherwise "not provided".

\- \*\*Reliability:\*\* LLM calls use timeouts, retries and automatic fallback between models.

\- \*\*Export:\*\* download the report as Markdown.



\## Architecture



```mermaid

flowchart LR

&#x20;   U\[User question] --> P\[Planner<br/>core/planner.py]

&#x20;   P --> S\[Search orchestration<br/>Tavily, core/search.py]

&#x20;   S --> E\[Evidence extraction + quote verification<br/>core/extract.py]

&#x20;   E --> A\[Cross-source analysis<br/>core/analyze.py]

&#x20;   A --> R\[Citation-linked report<br/>core/report.py]

&#x20;   R --> UI\[Streamlit workspace<br/>app.py]

&#x20;   L\[LLM layer with timeout and model fallback<br/>core/llm.py] -.-> P

&#x20;   L -.-> E

&#x20;   L -.-> A

&#x20;   L -.-> R

```



| Module | Responsibility |

|---|---|

| `core/llm.py` | Gemini calls, JSON mode, timeouts, retries, model fallback |

| `core/planner.py` | Question to sub-questions with search queries |

| `core/search.py` | Tavily search, URL normalization, de-duplication, source IDs |

| `core/extract.py` | Claim extraction and verbatim quote verification |

| `core/analyze.py` | Themes, contradictions, gaps, rule-based strength |

| `core/report.py` | Report writing, citation and number checks |

| `core/pipeline.py` | Connects all stages for the UI |

| `app.py` | Streamlit interface |



\## Tech stack



Python, Streamlit, Tavily API, Google Gemini API (`google-genai`), python-dotenv.



\## Screenshots



!\[Evidence map](docs/screenshots/evidence-map.png)

!\[Where sources disagree](docs/screenshots/contradictions.png)



\## Setup



1\. Clone the repository and open the folder.

2\. Create and activate a virtual environment.

&#x20;  - Windows: `python -m venv venv` then `venv\\Scripts\\activate`

3\. Install dependencies: `pip install -r requirements.txt`

4\. Copy `.env.example` to `.env` and add your own keys:

&#x20;  - `TAVILY\_API\_KEY` from tavily.com

&#x20;  - `GEMINI\_API\_KEY` from Google AI Studio

5\. Run: `python -m streamlit run app.py`



Never commit your `.env` file. It is listed in `.gitignore`.



\## Usage



Type a research question (or press \*\*Use demo question\*\*) and press \*\*Run research\*\*. A full run usually takes a few minutes. Results appear in tabs: Evidence map, Report, Claim explorer, Sources, Research plan. The repository includes one saved example run, which \*\*Open saved run\*\* displays without any API calls.



Example question: \*Does AI coding assistance actually make developers more productive?\*



\## Limitations



\- Claims come from search-result excerpts, not full pages, so context outside the excerpt is not seen.

\- A verified quote proves the text exists in the excerpt. It does not prove the claim is true.

\- Different sources can repeat the same underlying study, so more sources does not always mean independent confirmation.

\- Evidence strength does not judge how trustworthy a source is (a blog post and a paper count the same).

\- Claim labels (evidence type, stance) and contradiction explanations are produced by an LLM and can be wrong.

\- Many sources do not provide a publication date, so recency is often unknown.

\- Results depend on the search queries and on what Tavily returns, and can differ between runs.



\## Roadmap



\- Source quality weighting (peer-reviewed, vendor, personal blog)

\- Detecting when several sources cite the same underlying study

\- Follow-up questions that reuse the collected evidence

\- Full-page extraction instead of excerpts

\- PDF export

