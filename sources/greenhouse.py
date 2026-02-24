"""
Greenhouse job board scraper (JSON API).
API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
"""
from typing import List

import httpx

from config import Settings
from models import Job
from utils.deduplicator import Deduplicator
from utils.normalizer import normalize_greenhouse_job
from utils.rate_limiter import RateLimiter
from utils.retry import retry_async


BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


async def _fetch_page(
    client: httpx.AsyncClient,
    company: str,
    settings: Settings,
) -> dict:
    url = f"{BASE_URL}/{company}/jobs"
    params = {"content": "true"}

    async def _get() -> dict:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    return await retry_async(
        _get,
        retries=settings.max_retries,
        base_delay=0.5,
    )


async def scrape_company_jobs(
    company: str,
    client: httpx.AsyncClient,
    settings: Settings,
    rate_limiter: RateLimiter,
    deduplicator: Deduplicator,
) -> List[Job]:
    await rate_limiter.acquire()
    data = await _fetch_page(client, company, settings)
    jobs_raw = data.get("jobs") or []
    jobs: List[Job] = []
    for raw in jobs_raw:
        apply_url = raw.get("absolute_url") or raw.get("apply_url") or ""
        if not apply_url:
            continue
        job_id = deduplicator.is_new(apply_url)
        if job_id is None:
            continue 
        job = normalize_greenhouse_job(raw, company, job_id)
        jobs.append(job)
    return jobs
