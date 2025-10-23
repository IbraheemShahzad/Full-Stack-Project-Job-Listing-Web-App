#!/usr/bin/env python3
"""
ActuaryList Scraper — Single File (CSV/JSON + PostgreSQL Upsert)

What it does
------------
- Collects actuarial job links from multiple seed/listing pages on https://www.actuarylist.com
- Opens each job detail page and extracts:
  title, company, city, country, location, posting_date (ISO), job_type, tags[], job_url
- Saves results to JSON and CSV
- (If DB enabled) Upserts rows into PostgreSQL with UNIQUE(job_url)

Run examples
------------
# Headless, fetch 100, save CSV/JSON and upsert into Postgres (default DB_URL shown below)
python scrape_actuarylist_singlefile.py --limit 100 \
  --db-url postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs

# Show browser for debugging, skip DB, save only CSV/JSON
python scrape_actuarylist_singlefile.py --limit 60 --no-headless --no-db

Requirements (install once)
---------------------------
pip install \
  selenium webdriver-manager beautifulsoup4 pandas python-dateutil \
  sqlalchemy psycopg2-binary

Notes
-----
- De-dupe by job_url (both in-memory and in DB via ON CONFLICT)
- Relative dates (e.g., "3 days ago") => absolute ISO (YYYY-MM-DD)
- Handles cookie/signup popups, supports Load more / infinite scroll
- Uses robust selectors (tries multiple patterns, avoids brittle absolute XPaths)
"""

from __future__ import annotations
import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, Iterable, List, Optional, Set

import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# --- DB (SQLAlchemy / Postgres) ---
from sqlalchemy import (
    create_engine, Integer, String, Date, Text, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert

# ------------------------ Config ------------------------
SEED_URLS = [
    # Home and a few rich lists (good coverage & speed)
    "https://www.actuarylist.com/",
    "https://www.actuarylist.com/experience-levels/part-qualified",
    "https://www.actuarylist.com/experience-levels/graduate",
    "https://www.actuarylist.com/experience-levels/qualified",
    "https://www.actuarylist.com/experience-levels/senior-actuary",
    "https://www.actuarylist.com/sectors/health",
]
BASE = "https://www.actuarylist.com"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
DEFAULT_TAG_LIMIT = 6      # Max tags to keep per job card
MAX_SCROLL_TRIES = 6       # How many times to try infinite-scroll with no growth before giving up
SCROLL_PAUSE_RANGE = (0.8, 1.6)
PAGE_TIMEOUT = 18

# Default DB URL if not provided via --db-url or env DB_URL
DEFAULT_DB_URL = os.getenv(
    "DB_URL",
    "postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs"
)

# ------------------------ DB Model ------------------------
class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    job_type: Mapped[str] = mapped_column(String(60), default="Full-time")
    tags: Mapped[Any] = mapped_column(JSONB, default=list)  # JSON array
    job_url: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_url", name="uq_jobs_job_url"),
    )

# ------------------------ Helpers ------------------------
def jitter(a: float, b: float) -> float:
    return random.uniform(a, b)

def sleep_jitter(a=0.25, b=0.7):
    time.sleep(jitter(a, b))

def to_absolute_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"{BASE}{href}"
    return f"{BASE}/{href.lstrip('/')}"

RELATIVE_RE = re.compile(r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s+ago", re.I)

def parse_date(text: str) -> Optional[str]:
    """Accepts '19-Oct-2025' or 'May 1, 2025' or '3 days ago' -> ISO YYYY-MM-DD"""
    if not text:
        return None
    t = text.strip()
    m = RELATIVE_RE.search(t)
    if m:  # relative date
        n = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now(timezone.utc)
        # Approx months/years
        if "month" in unit:
            dt = now - timedelta(days=30 * n)
        elif "year" in unit:
            dt = now - timedelta(days=365 * n)
        elif "week" in unit:
            dt = now - timedelta(weeks=n)
        elif "day" in unit:
            dt = now - timedelta(days=n)
        elif "hour" in unit:
            dt = now - timedelta(hours=n)
        else:
            dt = now - timedelta(minutes=n)
        return dt.date().isoformat()
    # explicit date
    try:
        dt = dateparser.parse(t, dayfirst=False, fuzzy=True)
        if dt:
            return dt.date().isoformat()
    except Exception:
        return None
    return None

def headless_driver(headless=True, user_agent=None, proxy=None) -> webdriver.Chrome:
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,1100")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def wait(driver, seconds=PAGE_TIMEOUT):
    return WebDriverWait(driver, seconds)

def click_if_exists(driver, by, value) -> bool:
    try:
        el = wait(driver, 4).until(EC.element_to_be_clickable((by, value)))
        el.click()
        return True
    except Exception:
        return False

def dismiss_popups(driver):
    """Try common cookie / signup dismissors."""
    selectors = [
        (By.XPATH, "//button[normalize-space()='Accept' or contains(translate(., 'ACEPTLO', 'aceptlo'), 'accept') or contains(., 'Got it') or contains(., 'OK')]") ,
        (By.XPATH, "//button[contains(., 'Close') or contains(., 'close') or contains(., '×') or contains(., 'Dismiss')]") ,
        (By.XPATH, "//*[contains(@class,'cookie') and .//button]//button") ,
        (By.XPATH, "//div[contains(@aria-label,'cookie') or contains(@class,'cookie')]//button") ,
        (By.XPATH, "//button[contains(.,'No thanks') or contains(.,'no thanks')]") ,
    ]
    for by, val in selectors:
        try:
            btns = driver.find_elements(by, val)
            for b in btns:
                try:
                    if b.is_displayed() and b.is_enabled():
                        b.click()
                        sleep_jitter()
                except Exception:
                    pass
        except Exception:
            pass

def scroll_collect_job_links(driver, limit: int) -> List[str]:
    """Collect anchors that contain '/actuarial-jobs/' from a listing page."""
    seen: Set[str] = set()
    same_count_tries = 0
    last_count = 0

    while True:
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/actuarial-jobs/']")
        for a in anchors:
            href = a.get_attribute("href") or a.get_attribute("data-href") or ""
            u = to_absolute_url(href)
            if "/actuarial-jobs/" in u:
                seen.add(u)

        if len(seen) >= limit:
            break

        load_more_clicked = click_if_exists(driver, By.XPATH, "//button[contains(., 'Load more') or contains(., 'More jobs')]")
        if load_more_clicked:
            sleep_jitter(0.8, 1.4)
        else:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep_jitter(*SCROLL_PAUSE_RANGE)

        if len(seen) == last_count:
            same_count_tries += 1
        else:
            same_count_tries = 0
        last_count = len(seen)
        if same_count_tries >= MAX_SCROLL_TRIES:
            break

    return list(seen)[:limit]

def extract_label_value(soup: BeautifulSoup, label_candidates: List[str]) -> Optional[str]:
    """Find 'Label: Value' pairs anywhere on the page."""
    texts = soup.find_all(string=True)
    for t in texts:
        s = (t or "").strip()
        if not s:
            continue
        for lab in label_candidates:
            if s.lower().startswith(lab.lower()):
                parts = s.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    return parts[1].strip()
                try:
                    if t.parent and t.parent.next_sibling:
                        ns = t.parent.next_sibling.get_text(strip=True)
                        if ns:
                            return ns
                except Exception:
                    pass
    for strong in soup.select("strong,b"):
        k = strong.get_text(strip=True)
        for lab in label_candidates:
            if lab.lower() in k.lower():
                nxt = strong.find_next(string=True)
                if nxt:
                    val = (nxt or "").strip().strip(":").strip()
                    if val and lab.lower() not in val.lower():
                        return val
    return None

def guess_job_type(texts: List[str]) -> Optional[str]:
    joined = " ".join(texts).lower()
    if "intern" in joined or "internship" in joined:
        return "Internship"
    if "part-time" in joined or "part time" in joined:
        return "Part-time"
    if "contract" in joined or "temporary" in joined or "temp" in joined:
        return "Contract"
    if "full-time" in joined or "full time" in joined:
        return "Full-time"
    if "working schedule: full-time" in joined:
        return "Full-time"
    return None

def extract_tags(soup: BeautifulSoup, limit=DEFAULT_TAG_LIMIT) -> List[str]:
    tags: List[str] = []
    for sel in [
        ".tags a", ".tags span", ".chips a", ".chips span", "a.badge, span.badge",
        "main a", "main span"
    ]:
        for el in soup.select(sel):
            txt = el.get_text(strip=True)
            if not txt:
                continue
            if len(txt) > 2 and len(txt) <= 30 and not txt.lower().startswith((
                "posted", "job id", "country", "location", "working schedule", "work arrangement"
            )):
                tags.append(txt)
    seen: Set[str] = set()
    uniq: List[str] = []
    for t in tags:
        tl = t.lower()
        if tl not in seen:
            uniq.append(t)
            seen.add(tl)
    return uniq[:limit]

def parse_job_detail(driver, url: str) -> Optional[Dict[str, Any]]:
    try:
        driver.get(url)
        dismiss_popups(driver)
        wait(driver).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        sleep_jitter(0.4, 0.9)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        title_el = soup.find("h1") or soup.select_one("h1,h2")
        title = title_el.get_text(strip=True) if title_el else ""

        company = None
        for sel in ["h1 + div a", "h1 + p a", ".company a", ".company", "a[href*='company']"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                company = el.get_text(strip=True)
                break
        if not company:
            possible = soup.find(string=re.compile(r"Company:", re.I))
            if possible:
                v = extract_label_value(soup, ["Company", "Company Name"])
                if v:
                    company = v

        posting_raw = extract_label_value(soup, ["Posted Date", "Date Posted", "Posted"]) or ""
        posting_date = parse_date(posting_raw) or datetime.utcnow().date().isoformat()

        city = None
        country = None
        loc_val = extract_label_value(soup, ["Location", "City"])
        if loc_val and ("," in loc_val):
            parts = [p.strip() for p in loc_val.split(",") if p.strip()]
            if len(parts) >= 2:
                city = parts[0]
                country = parts[-1]
        elif loc_val:
            city = loc_val

        ctry_val = extract_label_value(soup, ["Country"])
        if ctry_val:
            country = ctry_val.strip()

        job_type = extract_label_value(soup, ["Job Type", "Working Schedule"]) or guess_job_type([soup.get_text(" ")]) or "Full-time"
        tags = extract_tags(soup)

        location = ", ".join([p for p in [city, country] if p])

        data = {
            "title": title or "",
            "company": company or "",
            "city": city or "",
            "country": country or "",
            "location": location or "",
            "posting_date": posting_date,
            "job_type": job_type,
            "tags": tags,
            "job_url": url,
        }
        # minimal validation — skip unusable
        if not data["title"] or not data["company"] or not data["job_url"]:
            return None
        return data
    except Exception as e:
        print(f"[WARN] Failed to parse {url}: {e}")
        return None

# ------------------------ DB helpers ------------------------

def init_db(db_url: str):
    engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def upsert_jobs(engine, records: Iterable[Dict[str, Any]]) -> int:
    rows: List[Dict[str, Any]] = []
    for r in records:
        pdv = r.get("posting_date")
        if isinstance(pdv, str):
            try:
                pdv = date.fromisoformat(pdv)
            except Exception:
                pdv = datetime.utcnow().date()
        rows.append({
            "title": (r.get("title") or "")[:255],
            "company": (r.get("company") or "")[:255],
            "city": (r.get("city") or "")[:120],
            "country": (r.get("country") or "")[:120],
            "location": (r.get("location") or "")[:255],
            "posting_date": pdv,
            "job_type": (r.get("job_type") or "Full-time")[:60],
            "tags": r.get("tags") or [],
            "job_url": r.get("job_url") or "",
        })

    affected = 0
    with Session(engine) as s:
        for start in range(0, len(rows), 200):
            chunk = rows[start:start+200]
            if not chunk:
                break
            stmt = pg_insert(Job.__table__).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Job.__table__.c.job_url],
                set_={
                    "title": stmt.excluded.title,
                    "company": stmt.excluded.company,
                    "city": stmt.excluded.city,
                    "country": stmt.excluded.country,
                    "location": stmt.excluded.location,
                    "posting_date": stmt.excluded.posting_date,
                    "job_type": stmt.excluded.job_type,
                    "tags": stmt.excluded.tags,
                },
            )
            res = s.execute(stmt)
            affected += res.rowcount or 0
        s.commit()
    return affected

# ------------------------ Main flow ------------------------

def run(limit: int, headless: bool, proxy: Optional[str], outdir: str, db_url: Optional[str], use_db: bool):
    os.makedirs(outdir, exist_ok=True)
    driver = None
    engine = None

    try:
        if use_db and db_url:
            engine = init_db(db_url)

        ua = random.choice(USER_AGENTS)
        driver = headless_driver(headless=headless, user_agent=ua, proxy=proxy)

        # Step 1: Gather detail links from seed pages
        detail_links: List[str] = []
        seen_links: Set[str] = set()

        for seed in SEED_URLS:
            print(f"[INFO] Visiting list: {seed}")
            driver.get(seed)
            dismiss_popups(driver)
            wait(driver).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            sleep_jitter(0.5, 1.0)

            links = scroll_collect_job_links(driver, limit=limit)
            new_links = [u for u in links if u not in seen_links]
            detail_links.extend(new_links)
            seen_links.update(new_links)

            print(f"[INFO] Collected {len(seen_links)} links so far")
            if len(seen_links) >= limit:
                break

        detail_links = detail_links[:limit]
        print(f"[INFO] Total unique job links to parse: {len(detail_links)}")

        # Step 2: Visit each detail page and extract fields
        results: List[Dict[str, Any]] = []
        for idx, url in enumerate(detail_links, start=1):
            print(f"[{idx}/{len(detail_links)}] {url}")
            data = parse_job_detail(driver, url)
            if data and not any(r.get("job_url") == data["job_url"] for r in results):
                results.append(data)
            sleep_jitter(0.3, 0.8)

        # Step 3: Save outputs
        json_path = os.path.join(outdir, "jobs.json")
        csv_path = os.path.join(outdir, "jobs.csv")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        df = pd.DataFrame(results)
        if "tags" in df.columns:
            # store tags as comma-separated in CSV for quick viewing
            df["tags"] = df["tags"].apply(lambda x: ",".join(x) if isinstance(x, list) else (x or ""))
        df.to_csv(csv_path, index=False, encoding="utf-8")

        print(f"[OK] Saved {len(results)} jobs")
        print(f"[OK] JSON: {json_path}")
        print(f"[OK] CSV : {csv_path}")

        # Step 4: Persist to DB
        if use_db and engine:
            affected = upsert_jobs(engine, results)
            print(f"[OK] Upserted {affected} rows into Postgres")

    except WebDriverException as e:
        print(f"[FATAL] WebDriver error: {e}")
        sys.exit(2)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

# ------------------------ CLI ------------------------

def cli():
    ap = argparse.ArgumentParser(description="Scrape ActuaryList jobs to CSV/JSON and PostgreSQL")
    ap.add_argument("--limit", type=int, default=100, help="How many jobs to fetch (default 100)")
    ap.add_argument("--headless", action="store_true", default=True, help="Run Chrome in headless mode")
    ap.add_argument("--no-headless", dest="headless", action="store_false", help="Run with visible browser")
    ap.add_argument("--proxy", type=str, default=None, help="HTTP proxy, e.g., http://user:pass@host:port")
    ap.add_argument("--outdir", type=str, default=os.path.join("scraper", "output"), help="Output directory")
    ap.add_argument("--db-url", type=str, default=DEFAULT_DB_URL, help="SQLAlchemy DB URL for Postgres")
    ap.add_argument("--no-db", action="store_true", help="Skip DB upsert (only write CSV/JSON)")
    args = ap.parse_args()

    run(limit=args.limit,
        headless=args.headless,
        proxy=args.proxy,
        outdir=args.outdir,
        db_url=None if args.no_db else args.db_url,
        use_db=not args.no_db)

if __name__ == "__main__":
    cli()


   
