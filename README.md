# Full-Stack-Project-Job-Listing-Web-App
Full-stack actuarial job board. Flask + SQLAlchemy + PostgreSQL API with CRUD, search/filter/sort. React (Vite + Tailwind) UI to view/add/edit/delete jobs. Selenium scraper seeds the DB from actuarylist.com and de-dupes by URL. Includes basic validation, pagination-ready API, and clear setup docs.


* **Backend:** Flask REST API + SQLAlchemy + PostgreSQL
* **Scraper:** Selenium bot that pulls jobs from **actuarylist.com** and seeds the DB
* **Frontend:** React (Vite 5) + TailwindCSS with filtering/sorting and CRUD

> Goal: demonstrate a realistic end-to-end build — clean API, reliable scraper, and a simple, responsive UI.

---

## Project Structure

```
.
├─ backend/
│  ├─ app.py
│  ├─ db.py
│  ├─ models/
│  │  └─ job.py
│  ├─ routes/
│  │  └─ job_routes.py
│  ├─ requirements.txt
│  └─ .env.example
├─ scraper/
│  ├─ scrape_actuarylist.py
│  ├─ requirements.txt
│  └─ output/           # CSV/JSON saved here when scraping
└─ job-frontend/
   ├─ src/
   │  ├─ api.js
   │  ├─ hooks/useJobs.js
   │  └─ components/
   │     ├─ FilterBar.jsx
   │     ├─ JobCard.jsx
   │     ├─ JobForm.jsx
   │     └─ JobList.jsx
   ├─ index.html
   ├─ tailwind.config.js
   ├─ postcss.config.js
   ├─ package.json
   └─ .env.example
```

---

## Prerequisites

* **PostgreSQL 16+** (local or remote)
* **Python 3.11+** (virtualenv recommended)
* **Node.js**

  * Vite 5 works well with Node **18+** or Node **20.15+**
* **Google Chrome** (for Selenium). `webdriver-manager` auto-installs the matching driver.

---

## 1) Backend (Flask API)

### Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```ini
# backend/.env
DATABASE_URL=postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs
FLASK_ENV=development
FLASK_RUN_PORT=5001
# If you run frontend on a different host/port, add it here (comma-separated)
CORS_ORIGINS=http://localhost:5173
```

Create DB/schema (first run will auto-create via SQLAlchemy, or run a quick init script if provided).

Start the API:

```bash
python app.py
# → Running on http://127.0.0.1:5001
```

### API Overview

Base URL: `http://localhost:5001/api`

#### Health

```
GET /api/health
→ { "ok": true, "db_rows": 123 }
```

#### List jobs (filter/sort/paginate)

```
GET /api/jobs
Query params:
  q            = text search in title/company
  job_type     = "Full-time" | "Part-time" | "Contract" | "Internship"
  city         = string
  country      = string
  location     = string
  tag          = repeatable, e.g. ?tag=Life&tag=Pricing  (matches ANY)
  sort         = date_desc | date_asc | title_asc | company_asc
  page         = 1+
  page_size    = 1..100
```

Example:

```
GET /api/jobs?q=analyst&job_type=Full-time&tag=Pricing&sort=date_desc&page=1&page_size=12
```

Response:

```json
{
  "page": 1,
  "page_size": 12,
  "total": 87,
  "items": [
    {
      "id": 1,
      "title": "Actuarial Analyst",
      "company": "WTW",
      "city": "London",
      "country": "UK",
      "location": "London, UK",
      "posting_date": "2025-10-21",
      "job_type": "Full-time",
      "tags": ["Pricing", "Python"],
      "job_url": "https://www.actuarylist.com/actuarial-jobs/xxxxx"
    }
  ]
}
```

#### Get single job

```
GET /api/jobs/:id
→ 200 with job JSON | 404
```

#### Create job

```
POST /api/jobs
Content-Type: application/json
{
  "title": "...",
  "company": "...",
  "city": "London",
  "country": "UK",
  "location": "London, UK",
  "posting_date": "2025-10-21",
  "job_type": "Full-time",
  "tags": ["Life", "Pricing"],
  "job_url": "https://…"
}
→ 201 with created job
→ 400 on validation error
→ 409 if job_url not unique
```

#### Update job

```
PATCH /api/jobs/:id
PUT   /api/jobs/:id
→ 200 with updated job | 404
```

#### Delete job

```
DELETE /api/jobs/:id
→ 200 { "ok": true } | 404
```

---

## 2) Scraper (Selenium)

### Setup & Run

```bash
cd scraper
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Run (saves CSV/JSON and upserts into Postgres)
python scrape_actuarylist.py \
  --limit 200 \
  --outdir output \
  --db-url postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs
```

**Notes**

* Works headless (Chrome) by default; `webdriver-manager` fetches the correct driver.
* Fields captured: title, company, city, country, location, posting_date, job_type, tags, job_url.
* **De-dupe** on `job_url` so repeated runs don’t create duplicates.
* Output files: `scraper/output/jobs.json` & `scraper/output/jobs.csv`.

---

## 3) Frontend (React + Vite + Tailwind)

### Setup

```bash
cd job-frontend
npm install
cp .env.example .env
```

Edit `.env`:

```ini
# job-frontend/.env
VITE_API_BASE=http://localhost:5001/api
```

Start dev server:

```bash
npm run dev
# → http://localhost:5173
```

### Features

* Responsive grid of job cards
* Search, filters (type/city/country/tags), sorting
* Add/Edit/Delete jobs (modal form, client-side validation)
* Async feedback (disable while saving), basic error messages
* Tag chips; “any” vs “all” toggle is included in the UI (backend currently matches **any** tag)

---

## Seeding Flow (End-to-End)

1. Start **Postgres**
2. Run **backend** (`python app.py`)
3. Run **scraper** (see command above) → verifies “Upserted N rows”
4. Start **frontend** (`npm run dev`) → data appears, filter/sort/CRUD

---

## Environment Examples

**backend/.env.example**

```ini
DATABASE_URL=postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs
FLASK_ENV=development
FLASK_RUN_PORT=5001
CORS_ORIGINS=http://localhost:5173
```

**job-frontend/.env.example**

```ini
VITE_API_BASE=http://localhost:5001/api
```

> If your DB is on another machine (e.g., Ubuntu on LAN), change the host in `DATABASE_URL`, and ensure the firewall allows port 5432.

---

**Happy building!** If anything doesn’t work exactly as written on your machine, ping me with the error text and I’ll patch the README or code to match your environment.
