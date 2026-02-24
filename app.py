from contextlib import asynccontextmanager
from time import perf_counter
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from config import get_settings, Settings
from models import Job, JobsResponse
from sources import greenhouse, lever
from utils.deduplicator import Deduplicator
from utils.logger import get_logger, setup_logging
from utils.rate_limiter import RateLimiter
from utils.filter_engine import (
    FilterCriteria,
    filter_jobs,
    criteria_to_applied_dict,
)


load_dotenv()
settings: Settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)
rate_limiter = RateLimiter(settings.rate_limit_delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        app.state.http_client = client
        yield


app = FastAPI(title="Job Scraper Service", lifespan=lifespan)


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_settings_dep() -> Settings:
    return settings


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        {
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_host": request.client.host if request.client else None,
        }
    )
    return response


@app.exception_handler(httpx.HTTPError)
async def httpx_exception_handler(request: Request, exc: httpx.HTTPError):
    logger.error(
        {
            "event": "external_http_error",
            "detail": str(exc),
            "url": str(getattr(exc, "request", None).url) if getattr(exc, "request", None) else None,
        }
    )
    return JSONResponse(
        status_code=502,
        content={"detail": "Error communicating with external job source."},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/scrape/greenhouse/{company}", response_model=JobsResponse)
async def scrape_greenhouse(
    company: str,
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
    cfg: Settings = Depends(get_settings_dep),
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_only: Optional[bool] = Query(None),
    employment_type: Optional[str] = Query(
        None,
        description="employment type: internship | full-time | part-time | contract",
    ),
    min_salary: Optional[int] = Query(None),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated skills (e.g. python,fastapi,aws)",
    ),
    posted_within_days: Optional[int] = Query(None),
    min_match_score: Optional[int] = Query(None),
) -> JobsResponse:
    start = perf_counter()
    deduplicator = Deduplicator()
    try:
        jobs: List[Job] = await greenhouse.scrape_company_jobs(
            company=company,
            client=client,
            settings=cfg,
            rate_limiter=rate_limiter,
            deduplicator=deduplicator,
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            {
                "event": "scrape_error",
                "source": "greenhouse",
                "company": company,
                "status_code": exc.response.status_code,
            }
        )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Failed to scrape Greenhouse for {company}.",
        )

    # Build criteria from query params and filter in-memory
    skills_list = [s.strip() for s in skills.split(",")] if skills else []

    criteria = FilterCriteria(
        keyword=keyword,
        location=location,
        remote_only=remote_only,
        employment_type=employment_type,
        min_salary=min_salary,
        skills=skills_list,
        posted_within_days=posted_within_days,
        min_match_score=min_match_score,
    )

    filtered_jobs = filter_jobs(jobs, criteria)
    filters_applied = criteria_to_applied_dict(criteria)

    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        {
            "event": "scrape_completed",
            "source": "greenhouse",
            "company": company,
            "count": len(filtered_jobs),
            "duration_ms": round(duration_ms, 2),
            "filters_applied": filters_applied,
        }
    )
    return JobsResponse(
        count=len(filtered_jobs),
        jobs=filtered_jobs,
        duration_ms=round(duration_ms, 2),
        filters_applied=filters_applied,
    )


@app.get("/scrape/lever/{company}", response_model=JobsResponse)
async def scrape_lever(
    company: str,
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
    cfg: Settings = Depends(get_settings_dep),
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_only: Optional[bool] = Query(None),
    employment_type: Optional[str] = Query(
        None,
        description="employment type: internship | full-time | part-time | contract",
    ),
    min_salary: Optional[int] = Query(None),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated skills (e.g. python,fastapi,aws)",
    ),
    posted_within_days: Optional[int] = Query(None),
    min_match_score: Optional[int] = Query(None),
) -> JobsResponse:
    start = perf_counter()
    deduplicator = Deduplicator()
    try:
        jobs: List[Job] = await lever.scrape_company_jobs(
            company=company,
            client=client,
            settings=cfg,
            rate_limiter=rate_limiter,
            deduplicator=deduplicator,
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            {
                "event": "scrape_error",
                "source": "lever",
                "company": company,
                "status_code": exc.response.status_code,
            }
        )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Failed to scrape Lever for {company}.",
        )

    skills_list = [s.strip() for s in skills.split(",")] if skills else []

    criteria = FilterCriteria(
        keyword=keyword,
        location=location,
        remote_only=remote_only,
        employment_type=employment_type,
        min_salary=min_salary,
        skills=skills_list,
        posted_within_days=posted_within_days,
        min_match_score=min_match_score,
    )

    filtered_jobs = filter_jobs(jobs, criteria)
    filters_applied = criteria_to_applied_dict(criteria)

    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        {
            "event": "scrape_completed",
            "source": "lever",
            "company": company,
            "count": len(filtered_jobs),
            "duration_ms": round(duration_ms, 2),
            "filters_applied": filters_applied,
        }
    )
    return JobsResponse(
        count=len(filtered_jobs),
        jobs=filtered_jobs,
        duration_ms=round(duration_ms, 2),
        filters_applied=filters_applied,
    )


@app.get("/scrape/all", response_model=JobsResponse)
async def scrape_all(
    companies: str = Query(..., description="Comma-separated list of company identifiers"),
    request: Request = None,
    client: httpx.AsyncClient = Depends(get_http_client),
    cfg: Settings = Depends(get_settings_dep),
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_only: Optional[bool] = Query(None),
    employment_type: Optional[str] = Query(
        None,
        description="employment type: internship | full-time | part-time | contract",
    ),
    min_salary: Optional[int] = Query(None),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated skills (e.g. python,fastapi,aws)",
    ),
    posted_within_days: Optional[int] = Query(None),
    min_match_score: Optional[int] = Query(None),
) -> JobsResponse:
    start = perf_counter()
    company_list = [c.strip() for c in companies.split(",") if c.strip()]
    if not company_list:
        raise HTTPException(status_code=400, detail="At least one company must be provided.")

    deduplicator = Deduplicator()
    jobs: List[Job] = []

    import asyncio

    tasks = []
    for company in company_list:
        tasks.append(
            greenhouse.scrape_company_jobs(
                company=company,
                client=client,
                settings=cfg,
                rate_limiter=rate_limiter,
                deduplicator=deduplicator,
            )
        )
        tasks.append(
            lever.scrape_company_jobs(
                company=company,
                client=client,
                settings=cfg,
                rate_limiter=rate_limiter,
                deduplicator=deduplicator,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error(
                {
                    "event": "scrape_partial_error",
                    "detail": str(result),
                }
            )
            continue
        jobs.extend(result)

    # Apply filters across combined result set from both sources
    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    criteria = FilterCriteria(
        keyword=keyword,
        location=location,
        remote_only=remote_only,
        employment_type=employment_type,
        min_salary=min_salary,
        skills=skills_list,
        posted_within_days=posted_within_days,
        min_match_score=min_match_score,
    )
    filtered_jobs = filter_jobs(jobs, criteria)
    filters_applied = criteria_to_applied_dict(criteria)

    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        {
            "event": "scrape_completed",
            "source": "all",
            "companies": company_list,
            "count": len(filtered_jobs),
            "duration_ms": round(duration_ms, 2),
            "filters_applied": filters_applied,
        }
    )
    return JobsResponse(
        count=len(filtered_jobs),
        jobs=filtered_jobs,
        duration_ms=round(duration_ms, 2),
        filters_applied=filters_applied,
    )


def _parse_company_list(raw: str, max_items: int) -> List[str]:
    items = [c.strip() for c in (raw or "").split(",") if c.strip()]
    return items[: max(max_items, 0)]


@app.get("/search", response_model=JobsResponse)
async def search(
    request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
    cfg: Settings = Depends(get_settings_dep),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated sources to search: greenhouse,lever (default: both)",
    ),
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_only: Optional[bool] = Query(None),
    employment_type: Optional[str] = Query(
        None,
        description="employment type: internship | full-time | part-time | contract",
    ),
    min_salary: Optional[int] = Query(None),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated skills (e.g. python,fastapi,aws)",
    ),
    posted_within_days: Optional[int] = Query(None),
    min_match_score: Optional[int] = Query(None),
) -> JobsResponse:
    """
    Skill-based search across a configured pool of companies (no company param required).
    The company pools come from env vars GREENHOUSE_COMPANIES and LEVER_COMPANIES.
    """
    start = perf_counter()

    requested_sources = (
        {s.strip().lower() for s in sources.split(",") if s.strip()}
        if sources
        else {"greenhouse", "lever"}
    )
    requested_sources &= {"greenhouse", "lever"}

    greenhouse_companies = (
        _parse_company_list(cfg.greenhouse_companies, cfg.search_max_companies)
        if "greenhouse" in requested_sources
        else []
    )
    lever_companies = (
        _parse_company_list(cfg.lever_companies, cfg.search_max_companies)
        if "lever" in requested_sources
        else []
    )

    if not greenhouse_companies and not lever_companies:
        raise HTTPException(
            status_code=400,
            detail=(
                "No company pools configured for /search. "
                "Set GREENHOUSE_COMPANIES and/or LEVER_COMPANIES in .env."
            ),
        )

    import asyncio

    deduplicator = Deduplicator()
    tasks = []
    for company in greenhouse_companies:
        tasks.append(
            greenhouse.scrape_company_jobs(
                company=company,
                client=client,
                settings=cfg,
                rate_limiter=rate_limiter,
                deduplicator=deduplicator,
            )
        )
    for company in lever_companies:
        tasks.append(
            lever.scrape_company_jobs(
                company=company,
                client=client,
                settings=cfg,
                rate_limiter=rate_limiter,
                deduplicator=deduplicator,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    jobs: List[Job] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error({"event": "search_partial_error", "detail": str(result)})
            continue
        jobs.extend(result)

    skills_list = [s.strip() for s in skills.split(",")] if skills else []
    criteria = FilterCriteria(
        keyword=keyword,
        location=location,
        remote_only=remote_only,
        employment_type=employment_type,
        min_salary=min_salary,
        skills=skills_list,
        posted_within_days=posted_within_days,
        min_match_score=min_match_score,
    )
    filtered_jobs = filter_jobs(jobs, criteria)
    filters_applied = criteria_to_applied_dict(criteria)

    duration_ms = (perf_counter() - start) * 1000
    logger.info(
        {
            "event": "search_completed",
            "sources": sorted(requested_sources),
            "greenhouse_companies": greenhouse_companies,
            "lever_companies": lever_companies,
            "count": len(filtered_jobs),
            "duration_ms": round(duration_ms, 2),
            "filters_applied": filters_applied,
        }
    )
    return JobsResponse(
        count=len(filtered_jobs),
        jobs=filtered_jobs,
        duration_ms=round(duration_ms, 2),
        filters_applied=filters_applied,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )

