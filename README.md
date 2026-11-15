# India Frontend Jobs Tracker

Free, automated daily job scraper for **Angular / React / Frontend Software Engineer** roles.
LinkedIn, Indeed and Google Jobs → filtered → emailed to you as an interactive HTML report.

Runs every day at **9:00 PM IST** on GitHub Actions. **Cost: ₹0**

---

## What it searches for

**40 search terms** across **Pune, Bangalore, Hyderabad, Mumbai + Remote (India)**, last 48 hours:

| Group | Titles |
|---|---|
| Angular | Angular Developer, Senior Angular Developer, Angular Engineer, Angular Frontend Developer, Angular Lead, Software Engineer Angular |
| React | React Developer, Senior React Developer, React.js Developer, React Frontend Engineer, Software Engineer React |
| Frontend / UI | Frontend Developer / Engineer, Senior Frontend Developer / Engineer, Front End Software Engineer, Lead Frontend Engineer, Frontend Lead, UI Developer, UI Engineer, Senior UI Developer, UI Lead, Web UI Developer, Micro Frontend Developer |
| Language led | TypeScript Developer, JavaScript Developer, JavaScript Engineer |
| Other frameworks | Vue.js Developer, Next.js Developer |
| SDE titles | SDE 2 Frontend, Software Development Engineer Frontend, Software Engineer Frontend, Senior Software Engineer Frontend, Software Engineer II Frontend |
| Full stack (FE heavy) | Full Stack Developer Angular / React, MEAN Stack Developer, MERN Stack Developer |
| Web / design system | Web Developer Angular, Design System Engineer |

## How the filtering works

- **Level:** keeps Senior, Lead, SDE 2 and SE II roles. Drops intern, fresher, trainee, graduate, and also principal, staff, architect, manager, director, VP.
- **Experience:** drops jobs that ask for **7+ years** minimum (set by `MAX_MIN_EXPERIENCE = 6`).
- **Stack:** drops React Native, iOS/Android/Flutter, Java/.NET/Python/PHP backend, QA/testing, DevOps, data, designer (UI/UX designer) and support roles.
- **Generic titles** like "Software Engineer" or "Full Stack Developer" are kept only when the description mentions frontend tech (Angular, React, TypeScript, RxJS...) or they came from a frontend-specific search.

## What the report shows

Open the attached `.html` file in any browser:
- Search bar plus filters for **City**, **Platform**, **Job Type**, **Category** and **Stack** (Angular / React / Vue / Next.js / TypeScript / Micro Frontend)
- **Stack** tags and **Experience** range pulled from each job
- Categories: Lead / Senior Frontend, Angular, React, Vue, Frontend, UI, Full Stack (FE heavy), Software Engineer
- 🔥 for 200+ applicants, 🔁 for jobs posted on several platforms
- Sortable columns and direct links to each posting

---

## Setup (about 15 minutes, one time)

### 1. Create the repo
1. Go to https://github.com/new
2. Name: `frontend-job-tracker`, visibility **Private**
3. Click **Create repository**

### 2. Upload the files
In the new repo: **Add file → Upload files**, drag in everything from this folder **including the `.github` folder**, then **Commit changes**.

> The `.github` folder is hidden on Windows/Mac by default. If drag and drop skips it, create the file manually:
> **Add file → Create new file**, name it `.github/workflows/daily_scrape.yml`, paste in the contents, commit.

Final structure:
```
frontend-job-tracker/
├── scraper.py
├── requirements.txt
├── README.md
├── .nojekyll
└── .github/
    └── workflows/
        └── daily_scrape.yml
```

### 3. Create a Gmail App Password
1. Turn on **2-Step Verification**: myaccount.google.com → Security
2. Go to **myaccount.google.com/apppasswords**, create one named "job tracker"
3. Copy the 16-character password

### 4. Add the secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `EMAIL_FROM` | the Gmail address that sends the report |
| `EMAIL_TO` | where the report goes (can be the same; several addresses allowed, comma separated) |
| `EMAIL_PASSWORD` | the 16-character App Password |

Paste values without trailing spaces or new lines.

### 5. First run
1. Repo → **Actions** tab → enable workflows if asked
2. Click **Daily India Frontend Jobs Scrape** → **Run workflow**
3. A full run takes roughly 30 to 60 minutes (200 searches)
4. Check the inbox (and spam) for `India Frontend Jobs — X new jobs today`

After that it runs by itself every evening at 9 PM IST.

---

## Customising (top of `scraper.py`)

```python
SEARCH_TERMS        = [...]   # add or remove job titles
LOCATIONS           = [...]   # add cities, e.g. "Chennai, Tamil Nadu, India"
INCLUDE_REMOTE      = True    # remote-in-India pass
HOURS_OLD           = 48      # time window
RESULTS_EACH        = 15      # results per term per site per city
MAX_MIN_EXPERIENCE  = 6       # drop jobs needing more than this minimum
```

Change the time in `.github/workflows/daily_scrape.yml` (cron is UTC, IST = UTC + 5:30):
```yaml
- cron: "30 15 * * *"     # 9:00 PM IST daily
- cron: "30 3 * * 1-5"    # 9:00 AM IST, Mon to Fri
```

## Troubleshooting

| Problem | Fix |
|---|---|
| No email | Actions tab: did the run succeed? Check spam |
| Authentication error | `EMAIL_PASSWORD` must be the App Password, not the Gmail password |
| 0 jobs | LinkedIn sometimes rate limits; the next run usually recovers |
| Workflow not listed | The `.github/workflows/daily_scrape.yml` file was not uploaded |
| Email missing but run passed | Actions → the run → **Artifacts** → download the report (kept 7 days) |
