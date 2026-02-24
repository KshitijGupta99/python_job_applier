from datetime import datetime, timezone
from typing import Any, List

from models import Job


def _scraped_at() -> datetime:
    return datetime.now(timezone.utc)


def normalize_greenhouse_job(
    raw: dict,
    company: str,
    job_id: str,
) -> Job:
    title = raw.get("title") or ""
    location = ""
    location_data = raw.get("location")
    if isinstance(location_data, dict):
        location = location_data.get("name") or ""
    elif isinstance(location_data, str):
        location = location_data

    description = raw.get("content") or raw.get("description") or ""
    apply_url = raw.get("absolute_url") or raw.get("apply_url") or ""

    # Greenhouse may have metadata or tags; collect text-like values as skills
    skills: List[str] = []
    for key in ("tags", "metadata"):
        value: Any = raw.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    skills.append(item)
                elif isinstance(item, dict):
                    label = item.get("value") or item.get("name")
                    if isinstance(label, str):
                        skills.append(label)

    return Job(
        id=job_id,
        title=title,
        company=company,
        location=location,
        description=description,
        apply_url=apply_url,
        skills=skills,
        source="greenhouse",
        scraped_at=_scraped_at(),
    )


def normalize_lever_job(
    raw: dict,
    company: str,
    job_id: str,
) -> Job:
    title = raw.get("text") or raw.get("title") or ""

    location = ""
    categories = raw.get("categories") or {}
    if isinstance(categories, dict):
        location = categories.get("location") or categories.get("commitment") or ""

    description = raw.get("descriptionPlain") or raw.get("description") or ""
    apply_url = raw.get("hostedUrl") or raw.get("applyUrl") or ""

    tags = raw.get("tags") or []
    skills: List[str] = [t for t in tags if isinstance(t, str)]

    return Job(
        id=job_id,
        title=title,
        company=company,
        location=location,
        description=description,
        apply_url=apply_url,
        skills=skills,
        source="lever",
        scraped_at=_scraped_at(),
    )

