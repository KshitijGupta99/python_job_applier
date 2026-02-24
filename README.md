# Job Scraper Service

A modular FastAPI microservice that scrapes job postings from **Greenhouse** and **Lever** job boards (via their public JSON APIs), normalizes them into a common schema, and exposes REST endpoints with rate limiting, retries, and deduplication.

## Tech stack

- Python 3.12
- FastAPI, httpx (async), Pydantic, uvicorn, python-dotenv

## Project structure

```
scraper-service/
├── app.py              # FastAPI app, routes, middleware
├── config.py           # Settings from env
├── models.py           # Pydantic Job & JobsResponse
├── sources/
│   ├── greenhouse.py   # Greenhouse API client
│   └── lever.py       # Lever API client
├── utils/
│   ├── rate_limiter.py
│   ├── normalizer.py
│   ├── deduplicator.py
│   ├── retry.py
│   └── logger.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

## Configuration

Copy `.env.example` to `.env` and adjust if needed:

- `RATE_LIMIT_DELAY` – seconds between requests (default: 1.0)
- `REQUEST_TIMEOUT` – HTTP timeout in seconds (default: 10)
- `MAX_RETRIES` – retries with exponential backoff (default: 3)
- `LOG_LEVEL` – DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `PORT` – server port (default: 8000)

## Run locally

```bash
# Optional: create venv and install deps
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Run server (uses PORT from env or 8000)
python app.py
# Or with uvicorn directly:
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Run with Docker

```bash
docker build -t job-scraper .
docker run -p 8000:8000 --env-file .env job-scraper
```

## API endpoints

Base URL: `http://localhost:8000` (or your host/port).

### Health

```bash
curl -s http://localhost:8000/health
```

Example response: `{"status":"ok"}`

### Scrape Greenhouse (single company)

Company is the Greenhouse **board token** (e.g. from `https://boards.greenhouse.io/<company>`).

```bash
curl -s "http://localhost:8000/scrape/greenhouse/vaulttec"
curl -s "http://localhost:8000/scrape/greenhouse/embed"
```

Example response: `{"count": N, "jobs": [...], "duration_ms": 123.45, "filters_applied": {}}`

#### Greenhouse with filters

```bash
# Software engineer roles in USA
curl -s "http://localhost:8000/scrape/greenhouse/mycompany?keyword=software%20engineer&location=usa"

# Remote-only internships mentioning 'data'
curl -s "http://localhost:8000/scrape/greenhouse/mycompany?keyword=data&remote_only=true&employment_type=internship"

# Jobs with at least one of the listed skills, posted in last 7 days
curl -s "http://localhost:8000/scrape/greenhouse/mycompany?skills=python,fastapi,aws&posted_within_days=7"

# Salary filter + minimum skill overlap score
curl -s "http://localhost:8000/scrape/greenhouse/mycompany?min_salary=120000&skills=python,aws&min_match_score=2"
```

### Scrape Lever (single company)

Company is the Lever **site name** (e.g. from `https://jobs.lever.co/<company>`).

```bash
curl -s "http://localhost:8000/scrape/lever/lever"
curl -s "http://localhost:8000/scrape/lever/leverdemo"
```

Example response: `{"count": N, "jobs": [...], "duration_ms": 123.45}`

### Scrape all (multiple companies, both sources)

Comma-separated list of company identifiers (Greenhouse board tokens and/or Lever site names). Results are deduplicated by apply URL across all returned jobs.

```bash
curl -s "http://localhost:8000/scrape/all?companies=lever,leverdemo"
curl -s "http://localhost:8000/scrape/all?companies=vaulttec,embed,lever"
```

Example response: `{"count": N, "jobs": [...], "duration_ms": 456.78}`

## Job model (response)

Each job in the `jobs` array has:

- `id` – SHA256 of `apply_url`
- `title` – job title
- `company` – company identifier used in the request
- `location` – location string
- `description` – job description
- `apply_url` – URL to apply
- `skills` – list of strings (tags/skills when provided by API)
- `source` – `"greenhouse"` or `"lever"`
- `scraped_at` – ISO datetime (UTC)

## Testing

1. **Health**  
   `curl -s http://localhost:8000/health` → `{"status":"ok"}`

2. **Greenhouse**  
   Use a known board token, e.g. `vaulttec` or `embed`:  
   `curl -s "http://localhost:8000/scrape/greenhouse/embed"`

3. **Lever**  
   Use a known site, e.g. `lever` or `leverdemo`:  
   `curl -s "http://localhost:8000/scrape/lever/leverdemo"`

4. **All**  
   `curl -s "http://localhost:8000/scrape/all?companies=leverdemo,embed"`

Invalid or missing company boards return 4xx/5xx; check response body and server logs (structured JSON logs) for details.
