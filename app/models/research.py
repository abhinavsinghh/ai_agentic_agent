from pydantic import BaseModel, Field


class Source(BaseModel):
    id: int
    title: str
    url: str
    snippet: str
    query: str


class SearchPlan(BaseModel):
    queries: list[str] = Field(
        description="Distinct web search queries that together cover the research question."
    )


class SourceAnalysis(BaseModel):
    is_relevant: bool = Field(
        description="True if the source contains information that helps answer the question."
    )
    key_findings: list[str] = Field(
        description="Specific facts, numbers, claims or arguments from the source that are relevant to the question."
    )
    reliability: str = Field(
        description="One short sentence on how trustworthy the source is (e.g. official docs, news, blog, forum)."
    )


class SourceNotes(SourceAnalysis):
    source_id: int


class Reflection(BaseModel):
    is_sufficient: bool = Field(
        description="True if the gathered findings are enough to write a thorough, well-supported report."
    )
    knowledge_gaps: list[str] = Field(
        description="Important aspects of the question that are still missing or poorly supported."
    )
    follow_up_queries: list[str] = Field(
        description="New web search queries that would fill the knowledge gaps. Empty if sufficient."
    )


class ReportSection(BaseModel):
    heading: str
    content: str = Field(
        description="Markdown paragraphs. Every factual claim must cite its source like [1] or [2][5]."
    )


class ResearchReport(BaseModel):
    title: str
    executive_summary: str = Field(
        description="A short paragraph answering the research question, with citations."
    )
    sections: list[ReportSection]
    key_takeaways: list[str] = Field(description="Bullet points, with citations.")
    limitations: list[str] = Field(
        description="Caveats: conflicting sources, missing data, outdated information, etc."
    )
