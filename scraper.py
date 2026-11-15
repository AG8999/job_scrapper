"""
India Frontend / Software Engineer Jobs Scraper
Target profile: Angular / React / Frontend Software Engineer (~3.5 yrs, Senior SE level)
Cities: Pune, Bangalore, Hyderabad, Mumbai + Remote (India)
Uses JobSpy (free, no API key) to scrape LinkedIn + Indeed + Google Jobs
Runs once daily at 9pm IST via GitHub Actions
"""

import json
import re
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

# ─────────────────────────────────────────────
# CONFIGURATION — edit these
# ─────────────────────────────────────────────

SEARCH_TERMS = [
    # Angular (core strength)
    "Angular Developer",
    "Senior Angular Developer",
    "Angular Engineer",
    "Angular Frontend Developer",
    "Angular Lead",
    "Software Engineer Angular",
    # React
    "React Developer",
    "Senior React Developer",
    "React.js Developer",
    "React Frontend Engineer",
    "Software Engineer React",
    # Frontend / UI (stack-agnostic titles)
    "Frontend Developer",
    "Frontend Engineer",
    "Senior Frontend Developer",
    "Senior Frontend Engineer",
    "Front End Software Engineer",
    "Lead Frontend Engineer",
    "Frontend Lead",
    "UI Developer",
    "UI Engineer",
    "Senior UI Developer",
    "UI Lead",
    "Web UI Developer",
    "Micro Frontend Developer",
    # Language-led titles
    "TypeScript Developer",
    "JavaScript Developer",
    "JavaScript Engineer",
    # Other frameworks she can credibly target
    "Vue.js Developer",
    "Next.js Developer",
    # SDE / Software Engineer titles with frontend focus
    "SDE 2 Frontend",
    "Software Development Engineer Frontend",
    "Software Engineer Frontend",
    "Senior Software Engineer Frontend",
    "Software Engineer II Frontend",
    # Full stack with a frontend-heavy stack
    "Full Stack Developer Angular",
    "Full Stack Developer React",
    "MEAN Stack Developer",
    "MERN Stack Developer",
    # Web / design system
    "Web Developer Angular",
    "Design System Engineer",
]

SITES          = ["linkedin", "indeed", "google"]
HOURS_OLD      = 48        # 48h window catches jobs that 24h misses at edges
RESULTS_EACH   = 15        # Per search term per site per city
COUNTRY_INDEED = "India"

# Indian cities — scraper loops through each one
LOCATIONS = [
    "Pune, Maharashtra, India",
    "Bangalore, Karnataka, India",
    "Hyderabad, Telangana, India",
    "Mumbai, Maharashtra, India",
]

# Extra pass: remote jobs anywhere in India (set False to skip)
INCLUDE_REMOTE = True

# Experience: drop jobs whose minimum required experience is above this.
# She has ~3.5 yrs, so 2-4, 3-5, 4-6 and 5-7 style ranges still show up.
MAX_MIN_EXPERIENCE = 6

# ─────────────────────────────────────────────
# ALLOWLIST — keep only if title matches one
# ─────────────────────────────────────────────

ALLOWLIST = [
    # Frameworks / libraries
    r"angular",
    r"react",                    # react, react.js, reactjs, react native excluded below
    r"\bvue",
    r"next\.?js",
    r"\bsvelte",
    # Frontend / UI wording
    r"front.?end",               # frontend, front-end, front end
    r"\bui\b",
    r"\bui/ux dev",
    r"\bui dev",
    r"\bui eng",
    r"user interface",
    r"web ui",
    r"micro.?front",
    r"design system",
    r"component library",
    # Languages
    r"typescript",
    r"javascript",
    r"\bjs dev",
    r"\bjs eng",
    # Web dev
    r"web dev",
    r"web eng",
    r"web application dev",
    # Stacks
    r"\bmean\b",
    r"\bmern\b",
    r"full.?stack",
    # Generic SE titles — only kept if the frontend relevance check passes
    r"software eng",
    r"software dev",
    r"\bsde\b",
    r"\bsde.?(i|ii|iii|1|2|3)\b",
    r"member of technical staff",
    r"\bmts\b",
    r"application dev",
    r"application eng",
    r"programmer analyst",
]

# ─────────────────────────────────────────────
# BLOCKLIST — discard even if allowlist matched
# ─────────────────────────────────────────────

BLOCKLIST = [
    # Wrong level: too junior for 3.5 yrs
    r"\bintern\b",
    r"internship",
    r"\bfresher",
    r"\btrainee\b",
    r"\bgraduate\b",
    r"\bapprentice",
    r"entry.?level",
    r"campus",
    # Wrong level: too senior / management
    r"\bprincipal\b",
    r"(?<!technical )\bstaff\b",
    r"distinguished",
    r"\barchitect\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bhead of\b",
    r"\bvp\b",
    r"\bavp\b",
    r"\bsvp\b",
    r"vice president",
    r"\bchief\b",
    r"\bcto\b",
    r"engineering manager",
    # Experience in title: 7+ years
    r"\b([7-9]|[1-9][0-9])\s*\+?\s*(years?|yrs?)",
    r"\b([7-9]|[1-9][0-9])\s*-\s*[0-9]+\s*(years?|yrs?)",
    r"minimum\s+([7-9]|[1-9][0-9])\s*(years?|yrs?)",
    # Not frontend / not her stack
    r"react native",
    r"\bios\b",
    r"android",
    r"flutter",
    r"mobile app dev",
    r"\bjava\b(?!script)",
    r"spring boot",
    r"\.net\b",
    r"\bc#",
    r"\bc\+\+",
    r"golang|\bgo dev",
    r"python",
    r"django",
    r"ruby",
    r"\bphp\b",
    r"laravel",
    r"wordpress",
    r"shopify",
    r"drupal",
    r"magento",
    r"salesforce",
    r"servicenow",
    r"\bsap\b",
    r"mainframe",
    r"cobol",
    r"devops",
    r"\bsre\b",
    r"site reliability",
    r"data eng",
    r"data scien",
    r"machine learning",
    r"\bml\b",
    r"\bai eng",
    r"embedded",
    r"firmware",
    r"hardware",
    r"network",
    r"cyber",
    r"security eng",
    r"\bqa\b",
    r"quality assurance",
    r"\btest(ing|er)?\b",
    r"\bsdet\b",
    r"automation eng",
    r"game dev|unity|unreal",
    r"blockchain|web3|solidity",
    r"\bui/ux designer",
    r"ux designer",
    r"ui designer",
    r"graphic design",
    r"visual design",
    r"product design",
    r"ux research",
    r"support eng",
    r"customer support",
    r"technical support",
    r"sales",
    r"pre.?sales",
    r"recruit",
    r"talent",
    r"teacher|tutor|trainer|faculty|instructor",
    r"(?i)peroptyx",
]

# Frontend keywords used to judge generic "Software Engineer" titles
FRONTEND_KEYWORDS = [
    r"angular", r"react", r"\bvue", r"next\.?js", r"typescript", r"javascript",
    r"front.?end", r"\bui\b", r"rxjs", r"redux", r"micro.?front", r"html5?", r"\bcss",
    r"tailwind", r"webpack", r"module federation",
]

# Search terms that are frontend specific, so a generic title found by
# them is trusted even when the site gives no description (LinkedIn)
FRONTEND_TERM_HINTS = [
    "angular", "react", "frontend", "front end", "ui", "vue", "next.js",
    "typescript", "javascript", "mean", "mern", "design system",
]

# ─────────────────────────────────────────────
# ROLE CATEGORY MAPPING (checked in order)
# ─────────────────────────────────────────────

ROLE_CATEGORIES = {
    "Lead / Senior Frontend": [r"\blead\b", r"\bsenior\b", r"\bsr\.?\b", r"sde.?(ii|iii|2|3)\b",
                               r"software engineer\s*(ii|iii|2|3)\b"],
    "Full Stack (FE heavy)":  [r"full.?stack", r"\bmean\b", r"\bmern\b"],
    "Angular Developer":      [r"angular"],
    "React Developer":        [r"react", r"next\.?js"],
    "Vue Developer":          [r"\bvue"],
    "UI Developer":           [r"\bui\b", r"user interface", r"design system", r"component library"],
    "Frontend Developer":     [r"front.?end", r"micro.?front", r"javascript", r"typescript",
                               r"\bjs\b", r"web dev", r"web eng", r"web ui"],
    "Software Engineer":      [r"software", r"\bsde\b", r"technical staff", r"\bmts\b",
                               r"application", r"programmer"],
}

# Tech stack tags shown in the report (from title + description)
STACK_TAGS = {
    "Angular":    r"angular",
    "React":      r"react(?!\s*native)",
    "Vue":        r"\bvue",
    "Next.js":    r"next\.?js",
    "TypeScript": r"typescript",
    "RxJS":       r"rxjs",
    "Redux":      r"redux",
    "Node.js":    r"\bnode(\.?js)?\b",
    "Micro FE":   r"micro.?front|module federation",
}


# ─────────────────────────────────────────────
# FILTER LOGIC
# ─────────────────────────────────────────────

def _text(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).lower()

def passes_allowlist(title: str) -> bool:
    t = _text(title)
    return any(re.search(p, t) for p in ALLOWLIST)

def passes_blocklist(title: str) -> bool:
    """Returns True if the title is CLEAN (not blocked)."""
    t = _text(title)
    if any(re.search(p, t) for p in BLOCKLIST):
        return False
    # Backend-only titles out; "Full Stack (Frontend + Backend)" stays
    if re.search(r"back.?end", t) and not re.search(r"front.?end|full.?stack|angular|react", t):
        return False
    return True

def is_frontend_title(title: str) -> bool:
    t = _text(title)
    return any(re.search(p, t) for p in FRONTEND_KEYWORDS)

def frontend_relevance_check(row) -> bool:
    """
    Titles that already say Angular / React / Frontend / UI pass straight away.
    Generic titles ("Software Engineer", "SDE 2", "Full Stack Developer") are only
    kept if the description mentions frontend tech, or, when no description is
    available, if they came from a frontend-specific search term.
    """
    title = _text(row.get("title"))
    if is_frontend_title(title):
        return True
    desc = _text(row.get("description"))
    if desc:
        hits = sum(1 for p in FRONTEND_KEYWORDS if re.search(p, desc))
        return hits >= 2
    term = _text(row.get("search_term"))
    return any(h in term for h in FRONTEND_TERM_HINTS)

EXP_PATTERNS = [
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)",
    r"(\d{1,2})\s*\+\s*(?:years?|yrs?)",
    r"(?:minimum|min\.?|at least)\s*(?:of\s*)?(\d{1,2})\s*(?:years?|yrs?)",
    r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
]

def extract_experience(row):
    """Return (min_years, label) from title + description, or (None, '—')."""
    text = _text(row.get("title")) + " " + _text(row.get("description"))[:4000]
    for p in EXP_PATTERNS:
        m = re.search(p, text)
        if m:
            nums = [int(g) for g in m.groups() if g is not None]
            nums = [n for n in nums if n <= 25]
            if not nums:
                continue
            lo = nums[0]
            label = f"{nums[0]}-{nums[1]} yrs" if len(nums) > 1 else f"{lo}+ yrs"
            return lo, label
    return None, "—"

def get_role_category(title: str) -> str:
    t = _text(title)
    for category, patterns in ROLE_CATEGORIES.items():
        if any(re.search(p, t) for p in patterns):
            return category
    return "Frontend Developer"  # fallback

def get_stack(row) -> str:
    text = _text(row.get("title")) + " " + _text(row.get("description"))
    tags = [name for name, p in STACK_TAGS.items() if re.search(p, text)]
    return ", ".join(tags) if tags else "—"

def filter_jobs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "description" not in df.columns:
        df["description"] = ""
    mask = (
        df["title"].apply(passes_allowlist) &
        df["title"].apply(passes_blocklist) &
        df.apply(frontend_relevance_check, axis=1)
    )
    df = df[mask].copy()
    if df.empty:
        return df

    exp = df.apply(extract_experience, axis=1)
    df["exp_min"] = exp.apply(lambda x: x[0])
    df["experience"] = exp.apply(lambda x: x[1])
    too_senior = df["exp_min"].apply(lambda v: v is not None and not pd.isna(v) and v > MAX_MIN_EXPERIENCE)
    print(f"Dropped for experience > {MAX_MIN_EXPERIENCE} yrs min: {int(too_senior.sum())}")
    df = df[~too_senior].copy()

    df["role_category"] = df["title"].apply(get_role_category)
    df["stack"] = df.apply(get_stack, axis=1)
    return df


# ─────────────────────────────────────────────
# SCRAPING
# ─────────────────────────────────────────────

def scrape_all() -> pd.DataFrame:
    all_frames = []
    passes = [(city, False) for city in LOCATIONS]
    if INCLUDE_REMOTE:
        passes.append(("India", True))
    total_searches = len(SEARCH_TERMS) * len(passes)
    print(f"\n{'='*55}")
    print(f"  India Frontend Jobs Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {len(SEARCH_TERMS)} terms × {len(passes)} locations ({len(SITES)} platforms each) = {total_searches} searches")
    print(f"{'='*55}\n")

    for city, remote in passes:
        print(f"\n📍 City: {city}")
        print(f"  {'─'*45}")
        for i, term in enumerate(SEARCH_TERMS, 1):
            print(f"  [{i:02d}/{len(SEARCH_TERMS)}] Searching: '{term}'")
            try:
                jobs = scrape_jobs(
                    site_name=SITES,
                    search_term=term,
                    location=city,
                    is_remote=remote,
                    results_wanted=RESULTS_EACH,
                    hours_old=HOURS_OLD,
                    country_indeed=COUNTRY_INDEED,
                    linkedin_fetch_description=False,
                    verbose=0,
                )
                if not jobs.empty:
                    jobs["search_term"] = term
                    jobs["city"] = "Remote" if remote else city.split(",")[0]
                    all_frames.append(jobs)
                    print(f"           → {len(jobs)} raw results")
                else:
                    print(f"           → 0 results")
            except Exception as e:
                print(f"           ✗ Error: {e}")

    if not all_frames:
        print("\nNo results from any search.")
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    print(f"\nTotal raw results across all cities: {len(combined)}")

    # Deduplicate by job_url (catches same job from multiple search terms)
    if "job_url" in combined.columns:
        combined = combined.drop_duplicates(subset=["job_url"], keep="first")
    elif "id" in combined.columns:
        combined = combined.drop_duplicates(subset=["site", "id"], keep="first")

    print(f"After deduplication: {len(combined)}")

    # Apply title filters
    filtered = filter_jobs(combined)
    print(f"After title filter:  {len(filtered)}")

    # Cross-platform duplicate detection
    if not filtered.empty:
        filtered = filtered.copy()
        filtered["_key"] = filtered["title"].str.lower().str.strip() + "|" + \
                           filtered["company"].fillna("").str.lower().str.strip()
        key_to_platforms = defaultdict(list)
        for _, row in filtered.iterrows():
            key_to_platforms[row["_key"]].append(str(row.get("site", "")))

        def get_also_on(row):
            platforms = key_to_platforms[row["_key"]]
            others = [p for p in platforms if p != str(row.get("site", ""))]
            return ", ".join(set(others)) if others else ""

        filtered["cross_platform"] = filtered["_key"].apply(
            lambda k: len(key_to_platforms[k]) > 1
        )
        filtered["also_on"] = filtered.apply(get_also_on, axis=1)
        filtered = filtered.drop(columns=["_key"])

    print(f"\nFinal jobs for output: {len(filtered)}")
    return filtered


# ─────────────────────────────────────────────
# HTML GENERATION
# ─────────────────────────────────────────────

def safe(val) -> str:
    if pd.isna(val) or val is None or str(val).strip() in ("", "nan", "None"):
        return "—"
    return str(val).strip()

def platform_badge(site: str) -> str:
    site = str(site).lower()
    if "linkedin" in site:
        return '<span class="badge badge-linkedin">LinkedIn</span>'
    elif "indeed" in site:
        return '<span class="badge badge-indeed">Indeed</span>'
    elif "google" in site:
        return '<span class="badge badge-google">Google Jobs</span>'
    return f'<span class="badge badge-unknown">{site}</span>'

def type_badge(job_type: str) -> str:
    t = str(job_type).lower()
    if "full" in t:
        return '<span class="badge badge-fulltime">Full-time</span>'
    if "contract" in t or "permanent" in t:
        return '<span class="badge badge-contract">Contract</span>'
    if "part" in t:
        return '<span class="badge badge-parttime">Part-time</span>'
    if "intern" in t:
        return '<span class="badge badge-intern">Internship</span>'
    return '<span class="badge badge-unknown">—</span>'

def build_html(df: pd.DataFrame) -> str:
    fetch_time = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    if df.empty:
        jobs_json = "[]"
        total = 0
        platform_summary = "No results"
        role_summary = "No results"
        cross_count = 0
    else:
        # Build JSON for JS
        rows = []
        for _, r in df.iterrows():
            applicants_raw = safe(r.get("num_applicants", "—"))
            try:
                applicants_num = int(str(applicants_raw).replace(",", "").split()[0])
            except:
                applicants_num = 0

            rows.append({
                "title":        safe(r.get("title")),
                "company":      safe(r.get("company")),
                "location":     safe(r.get("location")),
                "site":         safe(r.get("site")),
                "job_type":     safe(r.get("job_type")),
                "salary":       safe(r.get("min_amount")) if safe(r.get("min_amount")) != "—"
                                else safe(r.get("salary_source", "—")),
                "applicants":   applicants_raw,
                "applicants_num": applicants_num,
                "posted":       safe(r.get("date_posted")),
                "url":          safe(r.get("job_url")),
                "role_category": safe(r.get("role_category")),
                "cross_platform": bool(r.get("cross_platform", False)),
                "also_on":      safe(r.get("also_on", "")),
                "seniority":    safe(r.get("job_level", "—")),
                "city":         safe(r.get("city", "—")),
                "stack":        safe(r.get("stack", "—")),
                "experience":   safe(r.get("experience", "—")),
            })

        jobs_json = json.dumps(rows, indent=2, default=str)
        total = len(rows)

        pc = Counter(r["site"] for r in rows)
        platform_summary = "  |  ".join(f"{k.title()}: {v}" for k, v in pc.most_common())

        rc = Counter(r["role_category"] for r in rows)
        role_summary = "  |  ".join(f"{k}: {v}" for k, v in rc.most_common())

        cross_count = sum(1 for r in rows if r["cross_platform"])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>India Frontend Jobs · Daily Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet"/>
<style>
:root {{
  --bg:       #080b10;
  --surf:     #0d1017;
  --surf2:    #121620;
  --border:   #1a1f2e;
  --border2:  #232a3a;
  --text:     #dde3f0;
  --muted:    #5a6480;
  --muted2:   #8a93ad;
  --accent:   #4f9eff;
  --accent2:  #a78bfa;
  --green:    #34d399;
  --amber:    #fbbf24;
  --rose:     #fb7185;
  --sky:      #38bdf8;
  --linkedin: #818cf8;
  --indeed:   #60a5fa;
  --glass:    #34d399;
}}
*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
html {{ scroll-behavior: smooth; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  min-height: 100vh;
}}

/* ── TOP BAR ── */
.topbar {{
  background: var(--surf);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 52px;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 200;
}}
.logo {{
  font-family: 'Syne', sans-serif;
  font-size: 16px; font-weight: 800;
  letter-spacing: -.02em;
  display: flex; align-items: center; gap: 10px;
}}
.logo-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent);
  animation: breathe 3s ease-in-out infinite;
}}
@keyframes breathe {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(79,158,255,.5); }}
  50%      {{ box-shadow: 0 0 0 6px rgba(79,158,255,0); }}
}}
.logo-text {{ color: var(--text); }}
.logo-text span {{ color: var(--accent); }}
.topbar-meta {{
  font-size: 10px; color: var(--muted);
  display: flex; gap: 14px; align-items: center;
}}
.topbar-meta strong {{ color: var(--muted2); }}

/* ── FILTER BAR ── */
.filterbar {{
  background: var(--surf);
  border-bottom: 1px solid var(--border);
  padding: 10px 24px;
  display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
  position: sticky; top: 52px; z-index: 190;
}}
.search-wrap {{
  position: relative; flex: 1; min-width: 180px;
}}
.search-wrap .ico {{
  position: absolute; left: 10px; top: 50%;
  transform: translateY(-50%);
  color: var(--muted); pointer-events: none;
  font-size: 13px;
}}
input[type=text] {{
  width: 100%;
  background: var(--surf2);
  border: 1px solid var(--border2);
  color: var(--text);
  padding: 7px 10px 7px 30px;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  outline: none;
  transition: border-color .2s, box-shadow .2s;
}}
input[type=text]:focus {{
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(79,158,255,.12);
}}
select {{
  background: var(--surf2);
  border: 1px solid var(--border2);
  color: var(--text);
  padding: 7px 10px;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  outline: none;
  cursor: pointer;
  transition: border-color .2s;
}}
select:focus {{ border-color: var(--accent); }}
.btn-clear {{
  background: transparent;
  border: 1px solid var(--border2);
  color: var(--muted);
  padding: 7px 12px;
  border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; cursor: pointer;
  transition: all .2s; white-space: nowrap;
}}
.btn-clear:hover {{ border-color: var(--rose); color: var(--rose); }}

/* ── STATS STRIP ── */
.stats-strip {{
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 7px 24px;
  display: flex; gap: 20px; align-items: center;
  font-size: 10px; color: var(--muted);
  flex-wrap: wrap;
}}
.stats-strip b {{ color: var(--text); font-weight: 500; }}
.stats-strip .sep {{ color: var(--border2); }}

/* ── TABLE ── */
.table-outer {{
  overflow-x: auto;
  padding-bottom: 72px;
}}
table {{
  width: 100%; border-collapse: collapse;
  min-width: 860px;
}}
thead th {{
  background: var(--surf);
  border-bottom: 1px solid var(--border);
  padding: 9px 12px;
  text-align: left;
  font-size: 9px; font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .1em;
  white-space: nowrap;
  cursor: pointer; user-select: none;
  position: sticky; top: var(--thTop, 111px);
  transition: color .15s;
}}
thead th:hover {{ color: var(--accent); }}
thead th.asc  {{ color: var(--accent); }}
thead th.asc::after  {{ content: " ▲"; }}
thead th.desc {{ color: var(--accent); }}
thead th.desc::after {{ content: " ▼"; }}

tbody tr {{
  border-bottom: 1px solid var(--border);
  transition: background .1s;
  animation: rowIn .25s ease both;
}}
tbody tr:nth-child(odd) {{ background: rgba(255,255,255,.008); }}
tbody tr:hover {{ background: var(--surf2); }}
tbody tr.hidden {{ display:none!important; }}

@keyframes rowIn {{
  from {{ opacity:0; transform: translateY(4px); }}
  to   {{ opacity:1; transform: translateY(0); }}
}}

td {{
  padding: 9px 12px;
  vertical-align: middle;
  font-size: 12px;
  white-space: nowrap;
}}
td.wide {{ white-space: normal; max-width: 260px; }}
td.num  {{ color: var(--muted); font-size: 10px; width: 36px; }}

/* ── BADGES ── */
.badge {{
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 9px; font-weight: 600;
  letter-spacing: .04em;
  white-space: nowrap;
  vertical-align: middle;
}}
.badge-linkedin  {{ background:rgba(129,140,248,.12); color:#a5b4fc; border:1px solid rgba(129,140,248,.25); }}
.badge-indeed    {{ background:rgba(96,165,250,.12);  color:#93c5fd; border:1px solid rgba(96,165,250,.25); }}

.badge-google    {{ background:rgba(251,191,36,.10);  color:#fde68a; border:1px solid rgba(251,191,36,.25); }}
.badge-stack     {{ background:rgba(52,211,153,.08);  color:#6ee7b7; border:1px solid rgba(52,211,153,.18); font-size:9px; margin:1px 2px 1px 0; }}
.badge-glass     {{ background:rgba(52,211,153,.12);  color:#6ee7b7; border:1px solid rgba(52,211,153,.25); }}
.badge-unknown   {{ background:rgba(90,100,128,.12);  color:#94a3b8; border:1px solid rgba(90,100,128,.25); }}
.badge-fulltime  {{ background:rgba(52,211,153,.1);   color:#6ee7b7; border:1px solid rgba(52,211,153,.2); }}
.badge-contract  {{ background:rgba(251,191,36,.1);   color:#fde68a; border:1px solid rgba(251,191,36,.2); }}
.badge-parttime  {{ background:rgba(56,189,248,.1);   color:#7dd3fc; border:1px solid rgba(56,189,248,.2); }}
.badge-intern    {{ background:rgba(167,139,250,.1);  color:#c4b5fd; border:1px solid rgba(167,139,250,.2); }}
.badge-role      {{ background:rgba(79,158,255,.08);  color:#93c5fd; border:1px solid rgba(79,158,255,.18); font-size:9px; }}

/* ── TITLE CELL ── */
.title-link {{
  color: var(--text); text-decoration: none;
  font-weight: 500; font-size: 12px;
  transition: color .15s;
  display: block; line-height: 1.4;
}}
.title-link:hover {{ color: var(--accent); }}
.title-flags {{ display:flex; gap:5px; margin-top:4px; align-items:center; }}

.flag-fire {{ font-size:12px; }}
.tooltip-wrap {{
  position: relative; display: inline-block;
  cursor: help;
}}
.tooltip-wrap .tip {{
  display: none;
  position: absolute;
  bottom: calc(100% + 5px); left: 0;
  background: var(--surf2);
  border: 1px solid var(--border2);
  padding: 4px 9px; border-radius: 5px;
  font-size: 10px; color: var(--muted2);
  white-space: nowrap; z-index: 300;
  pointer-events: none;
}}
.tooltip-wrap:hover .tip {{ display:block; }}

/* ── VIEW BUTTON ── */
.btn-view {{
  display: inline-block;
  border: 1px solid var(--border2);
  color: var(--muted2);
  padding: 4px 10px;
  border-radius: 4px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; cursor: pointer;
  text-decoration: none;
  transition: all .15s;
  white-space: nowrap;
}}
.btn-view:hover {{
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(79,158,255,.07);
}}

/* ── NO RESULTS ── */
.no-results {{
  display: none;
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
  font-size: 13px;
}}
.no-results.show {{ display:block; }}
.no-results span {{ font-size: 32px; display:block; margin-bottom:12px; }}

/* ── FOOTER ── */
.footer {{
  position: fixed; bottom:0; left:0; right:0;
  background: var(--surf);
  border-top: 1px solid var(--border);
  padding: 8px 24px;
  display: flex; justify-content: space-between;
  align-items: center; flex-wrap: wrap; gap:6px;
  font-size: 10px; color: var(--muted);
  z-index: 100;
}}
.footer b {{ color: var(--text); font-weight:500; }}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">
    <div class="logo-dot"></div>
    <div class="logo-text">india<span>.</span>frontendjobs</div>
  </div>
  <div class="topbar-meta">
    <span>LinkedIn · Indeed · Google Jobs</span>
    <span style="color:var(--border2)">·</span>
    <span>Last <strong>48h</strong> · Pune · Bangalore · Hyderabad · Mumbai · Remote</span>
    <span style="color:var(--border2)">·</span>
    <span>Updated <strong>{fetch_time}</strong></span>
  </div>
</div>

<div class="filterbar">
  <div class="search-wrap">
    <span class="ico">⌕</span>
    <input type="text" id="q" placeholder="Search title, company, location…" oninput="filter()"/>
  </div>
  <select id="fCity" onchange="filter()">
    <option value="">All Cities</option>
    <option value="Pune">Pune</option>
    <option value="Bangalore">Bangalore</option>
    <option value="Hyderabad">Hyderabad</option>
    <option value="Mumbai">Mumbai</option>
    <option value="Remote">Remote</option>
  </select>
  <select id="fPlatform" onchange="filter()">
    <option value="">All Platforms</option>
    <option value="linkedin">LinkedIn</option>
    <option value="indeed">Indeed</option>
    <option value="google">Google Jobs</option>
  </select>
  <select id="fType" onchange="filter()">
    <option value="">All Types</option>
    <option value="full">Full-time</option>
    <option value="contract">Contract</option>
    <option value="part">Part-time</option>
    <option value="intern">Internship</option>
  </select>
  <select id="fRole" onchange="filter()">
    <option value="">All Categories</option>
    <option value="Lead / Senior Frontend">Lead / Senior Frontend</option>
    <option value="Angular Developer">Angular Developer</option>
    <option value="React Developer">React Developer</option>
    <option value="Vue Developer">Vue Developer</option>
    <option value="Frontend Developer">Frontend Developer</option>
    <option value="UI Developer">UI Developer</option>
    <option value="Full Stack (FE heavy)">Full Stack (FE heavy)</option>
    <option value="Software Engineer">Software Engineer</option>
  </select>
  <select id="fStack" onchange="filter()">
    <option value="">All Stacks</option>
    <option value="Angular">Angular</option>
    <option value="React">React</option>
    <option value="Vue">Vue</option>
    <option value="Next.js">Next.js</option>
    <option value="TypeScript">TypeScript</option>
    <option value="Micro FE">Micro Frontend</option>
  </select>
  <button class="btn-clear" onclick="clearFilters()">✕ Clear</button>
</div>

<div class="stats-strip">
  <span>Showing <b id="visCount">{total}</b> of <b>{total}</b> jobs</span>
  <span class="sep">·</span>
  <span>{platform_summary}</span>
  <span class="sep">·</span>
  <span>🔁 <b>{cross_count}</b> cross-platform</span>
  <span class="sep">·</span>
  <span>{role_summary}</span>
</div>

<div class="table-outer">
  <table>
    <thead>
      <tr>
        <th onclick="sort(0)">#</th>
        <th onclick="sort(1)">Platform</th>
        <th onclick="sort(2)">Job Title</th>
        <th onclick="sort(3)">Company</th>
        <th onclick="sort(4)">Location</th>
        <th onclick="sort(5)">Type</th>
        <th onclick="sort(6)">Category</th>
        <th onclick="sort(7)">Stack</th>
        <th onclick="sort(8)">Experience</th>
        <th onclick="sort(9)">Salary</th>
        <th onclick="sort(10)">Applicants</th>
        <th onclick="sort(11)">Posted</th>
        <th>View</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="no-results" id="noRes">
    <span>🔍</span>No jobs match your filters.
  </div>
</div>

<div class="footer">
  <span><b>{total} jobs</b> · {fetch_time} · 48h window · Pune · Bangalore · Hyderabad · Mumbai · Remote · LinkedIn · Indeed · Google Jobs</span>
  <span>{platform_summary} · {role_summary}</span>
</div>

<script>
const JOBS = {jobs_json};

function platBadge(s) {{
  s = (s||'').toLowerCase();
  if(s.includes('linkedin'))  return '<span class="badge badge-linkedin">LinkedIn</span>';
  if(s.includes('indeed'))    return '<span class="badge badge-indeed">Indeed</span>';
  if(s.includes('google'))    return '<span class="badge badge-google">Google Jobs</span>';
  return `<span class="badge badge-unknown">${{s}}</span>`;
}}
function typeBadge(t) {{
  t = (t||'').toLowerCase();
  if(t.includes('full'))                    return '<span class="badge badge-fulltime">Full-time</span>';
  if(t.includes('contract')||t.includes('permanent')) return '<span class="badge badge-contract">Contract</span>';
  if(t.includes('part'))                    return '<span class="badge badge-parttime">Part-time</span>';
  if(t.includes('intern'))                  return '<span class="badge badge-intern">Internship</span>';
  return '<span class="badge badge-unknown">—</span>';
}}

function render(jobs) {{
  const tb = document.getElementById('tbody');
  tb.innerHTML = '';
  jobs.forEach((j,i) => {{
    const flags = [];
    if(j.applicants_num >= 200) flags.push('<span class="flag-fire" title="200+ applicants">🔥</span>');
    if(j.cross_platform) flags.push(`<span class="tooltip-wrap">🔁<span class="tip">Also on: ${{j.also_on}}</span></span>`);

    const titleHtml = j.url && j.url !== '—'
      ? `<a class="title-link" href="${{j.url}}" target="_blank" rel="noopener">${{j.title}}</a>`
      : `<span class="title-link">${{j.title}}</span>`;

    const viewBtn = j.url && j.url !== '—'
      ? `<a class="btn-view" href="${{j.url}}" target="_blank" rel="noopener">View →</a>`
      : '<span class="btn-view" style="opacity:.3;cursor:default">N/A</span>';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="num">${{i+1}}</td>
      <td>${{platBadge(j.site)}}</td>
      <td class="wide">
        ${{titleHtml}}
        ${{flags.length ? `<div class="title-flags">${{flags.join('')}}</div>` : ''}}
      </td>
      <td style="color:var(--muted2)">${{j.company}}</td>
      <td style="color:var(--muted)">${{j.location}}</td>
      <td>${{typeBadge(j.job_type)}}</td>
      <td><span class="badge badge-role">${{j.role_category}}</span></td>
      <td class="wide">${{j.stack === '—' ? '<span style="color:var(--muted)">—</span>' : j.stack.split(', ').map(x => `<span class="badge badge-stack">${{x}}</span>`).join('')}}</td>
      <td style="color:var(--muted2)">${{j.experience}}</td>
      <td style="color:var(--muted2)">${{j.salary}}</td>
      <td style="color:var(--muted)">${{j.applicants === '—' ? '—' : j.applicants}}</td>
      <td style="color:var(--muted)">${{j.posted}}</td>
      <td>${{viewBtn}}</td>`;
    tb.appendChild(tr);
  }});
  document.getElementById('visCount').textContent = jobs.length;
  document.getElementById('noRes').classList.toggle('show', jobs.length === 0);
}}

function filter() {{
  const q    = document.getElementById('q').value.toLowerCase();
  const city = document.getElementById('fCity').value;
  const plat = document.getElementById('fPlatform').value.toLowerCase();
  const type = document.getElementById('fType').value.toLowerCase();
  const role = document.getElementById('fRole').value;
  const stack = document.getElementById('fStack').value;
  const out = JOBS.filter(j => {{
    if(q    && !`${{j.title}} ${{j.company}} ${{j.location}}`.toLowerCase().includes(q)) return false;
    if(city && j.city !== city) return false;
    if(plat && !(j.site||'').toLowerCase().includes(plat)) return false;
    if(type && !(j.job_type||'').toLowerCase().includes(type)) return false;
    if(role && j.role_category !== role) return false;
    if(stack && !(j.stack||'').split(', ').includes(stack)) return false;
    return true;
  }});
  render(out);
}}

function clearFilters() {{
  document.getElementById('q').value='';
  ['fCity','fPlatform','fType','fRole','fStack'].forEach(id => document.getElementById(id).value='');
  render(JOBS);
}}

let sortCol=-1, sortDir=1;
function sort(col) {{
  document.querySelectorAll('thead th').forEach((th,i) => {{
    th.classList.remove('asc','desc');
  }});
  if(sortCol===col) sortDir*=-1; else {{ sortCol=col; sortDir=1; }}
  document.querySelectorAll('thead th')[col].classList.add(sortDir===1?'asc':'desc');
  const rows=[...document.querySelectorAll('#tbody tr')];
  rows.sort((a,b)=>{{
    const av=a.cells[col]?.textContent.trim()||'';
    const bv=b.cells[col]?.textContent.trim()||'';
    return av.localeCompare(bv,undefined,{{numeric:true}})*sortDir;
  }});
  document.getElementById('tbody').append(...rows);
}}

function fixHeaderOffset() {{
  const h = document.querySelector('.topbar').offsetHeight + document.querySelector('.filterbar').offsetHeight;
  document.documentElement.style.setProperty('--thTop', h + 'px');
}}
window.addEventListener('resize', fixHeaderOffset);
fixHeaderOffset();
render(JOBS);
</script>
</body>
</html>'''


def send_email(html_content: str, df: pd.DataFrame):
    # .strip() guards against secrets pasted with a trailing newline/space
    sender    = (os.getenv("EMAIL_FROM") or "").strip()
    recipient = (os.getenv("EMAIL_TO") or "").strip()
    password  = (os.getenv("EMAIL_PASSWORD") or "").replace(" ", "").strip()  # Gmail App Password

    if not all([sender, recipient, password]):
        print("\n⚠️  Email secrets not configured.")
        print("   Add EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD to GitHub repo secrets.")
        print("   See README.md → Optional: Email Setup for instructions.")
        return

    job_count   = len(df) if not df.empty else 0
    date_str    = datetime.now().strftime("%a %d %b %Y")
    today_roles = df["role_category"].value_counts().to_dict() if not df.empty else {}
    roles_str   = "  ·  ".join(f"{k}: {v}" for k, v in today_roles.items()) or "No matching jobs today"

    # Subject line varies based on results
    if job_count == 0:
        subject = f"🔍 India Frontend Jobs — No new results today ({date_str})"
    elif job_count < 5:
        subject = f"📋 India Frontend Jobs — {job_count} jobs today ({date_str})"
    else:
        subject = f"🧑‍💻 India Frontend Jobs — {job_count} new jobs today ({date_str})"

    # Plain text fallback body
    plain_text = f"""India Frontend Jobs — Daily Report
Date: {date_str}
Jobs found: {job_count}
Breakdown: {roles_str}

Open the attached HTML file in your browser to view the full interactive report.
"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = f"Job Tracker <{sender}>"
    msg["To"]      = recipient

    # Attach plain text fallback
    msg.attach(MIMEText(plain_text, "plain"))

    # Attach the full interactive HTML as a file (opens in browser when clicked)
    from email.mime.base import MIMEBase
    from email import encoders
    attachment = MIMEBase("text", "html")
    attachment.set_payload(html_content.encode("utf-8"))
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"india-frontend-jobs-{datetime.now().strftime('%Y-%m-%d')}.html"
    )
    msg.attach(attachment)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, [r.strip() for r in recipient.split(",") if r.strip()], msg.as_string())
        print(f"\n✅ Email sent to {recipient}")
        print(f"   Subject: {subject}")
    except smtplib.SMTPAuthenticationError:
        print("\n❌ Email authentication failed.")
        print("   Make sure EMAIL_PASSWORD is a Gmail App Password, not your regular password.")
        print("   Guide: myaccount.google.com → Security → 2-Step Verification → App passwords")
    except Exception as e:
        print(f"\n❌ Email failed: {e}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    df = scrape_all()
    html = build_html(df)

    out_path = Path("output/index.html")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"\n✅ HTML written → {out_path}")

    # Always attempt email — will warn clearly if secrets not configured
    send_email(html, df)
