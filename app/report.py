import re

from app.models.research import ResearchReport, Source


def cited_ids(report: ResearchReport) -> set[int]:
    text = " ".join(
        [report.executive_summary, *report.key_takeaways]
        + [section.content for section in report.sections]
    )
    return {int(number) for number in re.findall(r"\[(\d+)\]", text)}


def render_markdown(question: str, report: ResearchReport, sources: list[Source]) -> str:
    lines = [
        f"# {report.title}",
        "",
        f"> **Research question:** {question}",
        "",
        "## Executive Summary",
        "",
        report.executive_summary,
        "",
    ]

    for section in report.sections:
        lines += [f"## {section.heading}", "", section.content, ""]

    lines += ["## Key Takeaways", ""]
    lines += [f"- {point}" for point in report.key_takeaways]

    lines += ["", "## Limitations", ""]
    lines += [f"- {point}" for point in report.limitations]

    used = cited_ids(report)
    lines += ["", "## References", ""]
    lines += [
        f"[{source.id}] {source.title}. {source.url}"
        for source in sources
        if source.id in used
    ]

    markdown = "\n".join(lines) + "\n"

    return markdown.replace("\\n", "\n")
