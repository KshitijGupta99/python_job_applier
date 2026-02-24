"""
Lever job board scraper (JSON API).
API: https://api.lever.co/v0/postings/{site}?mode=json&skip=X&limit=Y
"""
from typing import List

import httpx

from config import Settings
from models import Job
from utils.deduplicator import Deduplicator
from utils.normalizer import normalize_lever_job
from utils.rate_limiter import RateLimiter
from utils.retry import retry_async


BASE_URL = "https://api.lever.co/v0/postings"
PAGE_SIZE = 100


async def _fetch_page(
    client: httpx.AsyncClient,
    company: str,
    skip: int,
    settings: Settings,
) -> List[dict]:
    url = f"{BASE_URL}/{company}"
    params = {"mode": "json", "skip": skip, "limit": PAGE_SIZE}

    async def _get() -> List[dict]:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

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
    jobs: List[Job] = []
    skip = 0
    while True:
        chunk = await _fetch_page(client, company, skip, settings)
        if not chunk:
            break
        for raw in chunk:
            apply_url = raw.get("hostedUrl") or raw.get("applyUrl") or ""
            if not apply_url:
                continue
            job_id = deduplicator.is_new(apply_url)
            if job_id is None:
                continue
            job = normalize_lever_job(raw, company, job_id)
            jobs.append(job)
        if len(chunk) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
        await rate_limiter.acquire()
    return jobs
