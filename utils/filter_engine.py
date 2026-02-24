from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Dict, Any

from models import Job


@dataclass
class FilterCriteria:
    keyword: Optional[str] = None
    location: Optional[str] = None
    remote_only: Optional[bool] = None
    employment_type: Optional[str] = None  # internship | full-time | part-time | contract
    min_salary: Optional[int] = None
    skills: List[str] = field(default_factory=list)
    posted_within_days: Optional[int] = None
    min_match_score: Optional[int] = None


def _normalize(text: str) -> str:
    return text.lower()


def _infer_employment_type(job: Job) -> Optional[str]:
    text = _normalize(job.title + " " + job.description)

    if "intern" in text or "internship" in text:
        return "internship"
    if "full time" in text or "full-time" in text or "fulltime" in text:
        return "full-time"
    if "part time" in text or "part-time" in text or "parttime" in text:
        return "part-time"
    if "contract" in text or "contractor" in text or "freelance" in text:
        return "contract"

    return None


def _is_remote(job: Job) -> bool:
    text = _normalize(job.location + " " + job.description)
    return "remote" in text or "work from home" in text or "wfh" in text


_salary_pattern = re.compile(
    r"(?:\$)?(\d[\d,]{3,})"  # simple heuristic: 4+ digit numbers, optional dollar sign
)


def _extract_salary_numbers(text: str) -> List[int]:
    numbers: List[int] = []
    for match in _salary_pattern.findall(text):
        try:
            numbers.append(int(match.replace(",", "")))
        except ValueError:
            continue
    return numbers


def _skills_match(job: Job, skills: List[str]) -> int:
    """
    Returns a simple 'match score' = number of skills that appear
    in either the job.skills list or the description text.
    """
    if not skills:
        return 0

    desc = _normalize(job.description)
    job_skill_set = {_normalize(s) for s in job.skills}
    score = 0

    for skill in skills:
        s = _normalize(skill)
        if not s:
            continue
        if s in job_skill_set or s in desc:
            score += 1

    return score


def filter_jobs(jobs: Iterable[Job], criteria: FilterCriteria) -> List[Job]:
    """
    Pure in-memory filtering over normalized Job objects.
    Scraping must already be done before calling this.
    """
    result: List[Job] = []
    now = datetime.now(timezone.utc)

    keyword_norm = _normalize(criteria.keyword) if criteria.keyword else None
    location_norm = _normalize(criteria.location) if criteria.location else None
    skills_norm = [s.strip() for s in criteria.skills if s.strip()]
    employment_type_norm = (
        criteria.employment_type.lower() if criteria.employment_type else None
    )

    for job in jobs:
        # keyword
        if keyword_norm is not None:
            text = _normalize(job.title + " " + job.description)
            if keyword_norm not in text:
                continue

        # location
        if location_norm is not None:
            if location_norm not in _normalize(job.location):
                continue

        # remote_only
        if criteria.remote_only:
            if not _is_remote(job):
                continue

        # employment_type (inferred)
        if employment_type_norm is not None:
            inferred = _infer_employment_type(job)
            if inferred is None or inferred != employment_type_norm:
                continue

        # posted_within_days
        if criteria.posted_within_days is not None:
            threshold = now - timedelta(days=criteria.posted_within_days)
            if job.scraped_at < threshold:
                continue

        # min_salary
        if criteria.min_salary is not None:
            salaries = _extract_salary_numbers(job.description)
            if not salaries or max(salaries) < criteria.min_salary:
                continue

        # skills + min_match_score
        match_score = 0
        if skills_norm:
            match_score = _skills_match(job, skills_norm)
            if match_score == 0:
                continue

        if criteria.min_match_score is not None:
            if match_score < criteria.min_match_score:
                continue

        result.append(job)

    return result


def criteria_to_applied_dict(criteria: FilterCriteria) -> Dict[str, Any]:
    """
    Helper to produce a compact dict of only filters that were actually set.
    """
    out: Dict[str, Any] = {}
    if criteria.keyword:
        out["keyword"] = criteria.keyword
    if criteria.location:
        out["location"] = criteria.location
    if criteria.remote_only:
        out["remote_only"] = criteria.remote_only
    if criteria.employment_type:
        out["employment_type"] = criteria.employment_type
    if criteria.min_salary is not None:
        out["min_salary"] = criteria.min_salary
    if criteria.skills:
        out["skills"] = criteria.skills
    if criteria.posted_within_days is not None:
        out["posted_within_days"] = criteria.posted_within_days
    if criteria.min_match_score is not None:
        out["min_match_score"] = criteria.min_match_score
    return out

