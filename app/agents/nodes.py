import re
from datetime import date

from langgraph.types import Send

from app.agents.state import AnalyzeSourceInput, ResearchState
from app.config import (
    MAX_ITERATIONS,
    MAX_PAGE_CHARS,
    MAX_SOURCES_PER_ROUND,
    QUERIES_PER_ROUND,
    RESULTS_PER_QUERY,
)
from app.llm.client import ask_llm_structured
from app.models.research import (
    Reflection,
    ResearchReport,
    SearchPlan,
    Source,
    SourceAnalysis,
    SourceNotes,
)
from app.tools.fetch import fetch_page_text
from app.tools.search import search_web


SYSTEM_INSTRUCTION = f"""
You are a meticulous technical research assistant.
Today's date is {date.today().isoformat()}.
Base every statement on the provided sources. Never invent facts, numbers or sources.
"""


def format_notes(state: ResearchState) -> str:
    sources = {source.id: source for source in state["sources"]}
    blocks = []

    for note in sorted(state["notes"], key=lambda n: n.source_id):
        if not note.is_relevant or not note.key_findings:
            continue

        source = sources[note.source_id]
        findings = "\n".join(f"- {finding}" for finding in note.key_findings)
        blocks.append(
            f"[{source.id}] {source.title} ({source.url})\n"
            f"Reliability: {note.reliability}\n{findings}"
        )

    return "\n\n".join(blocks) or "(no relevant findings yet)"


def plan_queries(state: ResearchState) -> dict:
    print("\n[plan] Breaking the question into search queries...")

    plan = ask_llm_structured(
        prompt=(
            f"Research question: {state['question']}\n\n"
            f"Write {QUERIES_PER_ROUND} diverse web search queries that together "
            "cover the different aspects of this question. Keep them short, like "
            "something a person would type into a search engine."
        ),
        response_model=SearchPlan,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    queries = plan.queries[:QUERIES_PER_ROUND]
    for query in queries:
        print(f"  - {query}")

    return {"pending_queries": queries, "iteration": 1}


def search(state: ResearchState) -> dict:
    print(f"\n[search] Round {state['iteration']}")

    seen_urls = {source.url for source in state["sources"]}
    results_per_query = []

    for query in state["pending_queries"]:
        results = search_web(query, max_results=RESULTS_PER_QUERY)
        print(f"  - {query!r}: {len(results)} results")
        results_per_query.append((query, results))

    next_id = len(state["sources"]) + 1
    new_sources = []

    for rank in range(RESULTS_PER_QUERY):
        for query, results in results_per_query:
            if rank >= len(results) or len(new_sources) >= MAX_SOURCES_PER_ROUND:
                continue

            result = results[rank]
            if result["url"] in seen_urls:
                continue

            seen_urls.add(result["url"])
            new_sources.append(Source(id=next_id, query=query, **result))
            next_id += 1

    return {
        "sources": new_sources,
        "queries_done": state["pending_queries"],
        "pending_queries": [],
    }


def route_to_analysis(state: ResearchState) -> list[Send] | str:
    analyzed_ids = {note.source_id for note in state["notes"]}
    new_sources = [s for s in state["sources"] if s.id not in analyzed_ids]

    if not new_sources:
        return "reflect"

    print(f"\n[analyze] Reading {len(new_sources)} sources in parallel...")

    return [
        Send("analyze_source", {"question": state["question"], "source": source})
        for source in new_sources
    ]


def analyze_source(task: AnalyzeSourceInput) -> dict:
    source = task["source"]
    page_text = fetch_page_text(source.url, max_chars=MAX_PAGE_CHARS)

    content = page_text or f"(Only the search snippet is available.) {source.snippet}"

    try:
        analysis = ask_llm_structured(
            prompt=(
                f"Research question: {task['question']}\n\n"
                f"Source title: {source.title}\n"
                f"Source URL: {source.url}\n\n"
                f"Source content:\n{content}\n\n"
                "Extract every finding from this source that helps answer the "
                "research question. Include concrete numbers, dates and names. "
                "If nothing is relevant, set is_relevant to false."
            ),
            response_model=SourceAnalysis,
            system_instruction=SYSTEM_INSTRUCTION,
        )
    except RuntimeError as error:
        print(f"  ! [{source.id}] analysis failed, keeping snippet: {error}")
        analysis = SourceAnalysis(
            is_relevant=bool(source.snippet),
            key_findings=[source.snippet] if source.snippet else [],
            reliability="Unverified: search snippet only, page was not analyzed.",
        )

    status = f"{len(analysis.key_findings)} findings" if analysis.is_relevant else "not relevant"
    fetched = "page" if page_text else "snippet"
    print(f"  - [{source.id}] ({fetched}) {status}: {source.title[:60]}")

    notes = SourceNotes(source_id=source.id, **analysis.model_dump())
    return {"notes": [notes]}


def reflect(state: ResearchState) -> dict:
    if state["iteration"] >= MAX_ITERATIONS:
        print("\n[reflect] Reached the search round limit, writing the report.")
        return {"pending_queries": []}

    print("\n[reflect] Checking for knowledge gaps...")

    reflection = ask_llm_structured(
        prompt=(
            f"Research question: {state['question']}\n\n"
            f"Queries already searched: {state['queries_done']}\n\n"
            f"Findings so far:\n{format_notes(state)}\n\n"
            "Are these findings enough to write a thorough, well-supported "
            "report? If not, list the gaps and up to "
            f"{QUERIES_PER_ROUND} NEW search queries to fill them."
        ),
        response_model=Reflection,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    follow_ups = [
        query for query in reflection.follow_up_queries
        if query not in state["queries_done"]
    ][:QUERIES_PER_ROUND]

    if reflection.is_sufficient or not follow_ups:
        print("  Findings are sufficient.")
        return {"pending_queries": []}

    for gap in reflection.knowledge_gaps:
        print(f"  gap: {gap}")

    return {"pending_queries": follow_ups, "iteration": state["iteration"] + 1}


def should_continue(state: ResearchState) -> str:
    return "search" if state["pending_queries"] else "write_report"


def write_report(state: ResearchState) -> dict:
    print("\n[write] Writing the final report...")

    report = ask_llm_structured(
        prompt=(
            f"Research question: {state['question']}\n\n"
            f"Evidence (numbered sources):\n{format_notes(state)}\n\n"
            "Write a structured research report that answers the question.\n"
            "- Cite every factual claim with the source number in square "
            "brackets, e.g. [2] or [1][4]. Only use numbers listed above.\n"
            "- Where sources disagree, say so and cite both sides.\n"
            "- Use 3 to 6 sections with clear headings.\n"
            "- If the evidence is thin, say so in the limitations."
        ),
        response_model=ResearchReport,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    valid_ids = {source.id for source in state["sources"]}
    return {"report": remove_invalid_citations(report, valid_ids)}


def remove_invalid_citations(report: ResearchReport, valid_ids: set[int]) -> ResearchReport:
    def clean(text: str) -> str:
        return re.sub(
            r"\[(\d+)\]",
            lambda match: match.group(0) if int(match.group(1)) in valid_ids else "",
            text,
        )

    report.executive_summary = clean(report.executive_summary)
    report.key_takeaways = [clean(point) for point in report.key_takeaways]
    for section in report.sections:
        section.content = clean(section.content)

    return report
