import operator
from typing import Annotated, TypedDict

from app.models.research import ResearchReport, Source, SourceNotes


class ResearchState(TypedDict):
    question: str
    pending_queries: list[str]
    queries_done: Annotated[list[str], operator.add]
    sources: Annotated[list[Source], operator.add]
    notes: Annotated[list[SourceNotes], operator.add]
    iteration: int
    report: ResearchReport | None


class AnalyzeSourceInput(TypedDict):
    question: str
    source: Source
