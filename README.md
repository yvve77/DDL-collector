# 📚 DDL Collector

Automatically tracks assignment deadlines across courses, sends a daily email digest, and provides an interactive dashboard to check off completed work.

**Live Dashboard →** https://yvve77.github.io/DDL-collector

---

## Features

- ☀️ **Daily email** — sent every morning at 8:00 AM CT to your Illinois inbox, showing only incomplete assignments
- 📅 **Monday reminder** — special banner on Mondays reminding you BioE 210 is due that day
- ✅ **Interactive dashboard** — check off assignments as you complete them; completed tasks are excluded from future emails
- 🎨 **Color-coded by course** — BioE 210 (orange) / CS 128 (blue) / CS 173 (green) / Math 285 (purple)

---

## Courses Covered

| Course | Assignment Type | Platform | Due Schedule |
|--------|----------------|----------|--------------|
| BioE 210 | Weekly HW | Canvas | Every Monday 11:59 PM |
| CS 128 | Machine Problems | PrairieLearn | Every other Monday 11:59 PM |
| CS 173 | Pre-unit HW | PrairieLearn | Every Monday 11:59 PM |
| Math 285 | Weekly HW + Quizzes | PrairieLearn | HW every Monday; Quiz after each lecture |

---

## File Structure

```
DDL-collector/
├── sync_assignments.py       # Main script: builds task list, sends email, updates tasks.json
├── tasks.json                # Task state database (auto-committed by GitHub Actions)
├── index.html                # Dashboard (hosted on GitHub Pages)
└── .github/
    └── workflows/
        └── sync.yml          # GitHub Actions schedule configuration
```

---

## How It Works

```
Every day at 8:00 AM CT
        │
        ▼
GitHub Actions runs sync_assignments.py
        │
        ├── Generates full assignment list (hardcoded due dates)
        ├── Reads tasks.json to filter out completed tasks
        ├── Sends HTML email to @illinois.edu
        └── Commits updated tasks.json back to the repo
                                    │
                                    ▼
                        Dashboard reads tasks.json
                        User checks off tasks → saved in localStorage
```

---

## GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `GMAIL_ADDRESS` | Gmail address used to send emails |
| `GMAIL_APP_PASSWORD` | 16-character Gmail app password |
| `TO_EMAIL` | Recipient address (@illinois.edu) |

---

## Manual Trigger

Go to **Actions** → **Daily DDL Digest** → **Run workflow** to sync immediately without waiting for the daily schedule.

---

## Adding or Editing Assignments

Edit the `all_assignments()` function in `sync_assignments.py`. Follow the existing format:

```python
# Canvas assignment
canvas("HW 5", "BioE 210", ct(3, 3))

# PrairieLearn assignment
pl("Pre-unit HW", "CS 173", ct(3, 3))
```

`ct(month, day)` defaults to 11:59 PM CT on that date.

---

*Spring 2026 · University of Illinois Urbana-Champaign*
