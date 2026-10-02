import re
import sys
from pathlib import Path

from app.agents.graph import build_research_graph
from app.config import GEMINI_API_KEY, MAX_CONCURRENCY
from app.report import render_markdown


REPORTS_DIR = Path("reports")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "report"


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("================================")
    print("     AI Research Agent")
    print("================================")

    if not GEMINI_API_KEY:
        print("Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
        return

    graph = build_research_graph()

    if "--graph" in sys.argv:
        print(graph.get_graph().draw_mermaid())
        return

    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    question = " ".join(args) or input("\nResearch question: ").strip()

    if not question:
        print("Please enter a research question.")
        return

    initial_state = {
        "question": question,
        "pending_queries": [],
        "queries_done": [],
        "sources": [],
        "notes": [],
        "iteration": 0,
        "report": None,
    }

    try:
        final_state = graph.invoke(
            initial_state,
            config={"max_concurrency": MAX_CONCURRENCY, "recursion_limit": 50},
        )
    except RuntimeError as error:
        print(f"\nResearch failed: {error}")
        print("Tip: on the free tier, try another model, e.g. GEMINI_MODEL=gemini-3.5-flash in .env")
        return

    markdown = render_markdown(question, final_state["report"], final_state["sources"])

    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{slugify(question)}.md"
    path.write_text(markdown, encoding="utf-8")

    print("\n" + "=" * 60 + "\n")
    print(markdown)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    main()
