from datetime import datetime, timezone
from html import unescape
from typing import Any, List, Set

from models import Job


COMMON_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "aws",
    "gcp",
    "azure",
    "spark",
    "hadoop",
    "scala",
    "go",
    "c++",
    "c#",
    "rust",
    "kotlin",
    "react",
    "node",
    "django",
    "flask",
    "pandas",
    "numpy",
    "ml",
    "machine learning",
    "deep learning",
    "sql server",
    "postgres",
    "mysql",
}


def _scraped_at() -> datetime:
    return datetime.now(timezone.utc)


def _extract_common_skills_from_text(text: str) -> List[str]:
    """
    Heuristic extractor: look for common skills/technologies in the
    plain-text description and return a unique list.
    """
    if not text:
        return []
    lowered = text.lower()
    found: Set[str] = set()
    for skill in COMMON_SKILLS:
        if skill in lowered:
            found.add(skill)
    return sorted(found)


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

    # Greenhouse often returns HTML; keep it as-is for now but also
    # derive skills from a plain-text view.
    description = raw.get("content") or raw.get("description") or ""
    description_plain = unescape(description)
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

    # Add inferred skills from description text (e.g. Python, SQL)
    inferred = _extract_common_skills_from_text(description_plain)
    skills = list(dict.fromkeys(skills + inferred))  # dedupe, keep order

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
    description_plain = unescape(description)
    apply_url = raw.get("hostedUrl") or raw.get("applyUrl") or ""

    tags = raw.get("tags") or []
    skills: List[str] = [t for t in tags if isinstance(t, str)]

    inferred = _extract_common_skills_from_text(description_plain)
    skills = list(dict.fromkeys(skills + inferred))

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

