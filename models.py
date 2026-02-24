from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, HttpUrl, Field


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: HttpUrl
    skills: List[str] = Field(default_factory=list)
    source: str
    scraped_at: datetime


class JobsResponse(BaseModel):
    count: int
    jobs: List[Job]
    duration_ms: float
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

