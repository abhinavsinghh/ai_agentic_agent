from pydantic import BaseModel


class ResearchResult(BaseModel):
    topic: str
    summary: str
    key_points: list[str]