#!/usr/bin/env python3
"""
DDL Digest, Fall 2026
Courses: CS 225, BIOE 206, BIOE 310, DANC 340 (+ BIOE 210 grading, Admin dates)

Each task has:
  title, course, due (datetime), source, url,
  kind   : hw | quiz | lab | potd | project | exam | grading | admin
  start  : optional window start (exam windows)
  allday : True when only the date is known
"""

import os, sys, json, re, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, date
import pytz

# ── Config ─────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
TO_EMAIL           = os.environ.get("TO_EMAIL", "")

CT         = pytz.timezone("America/Chicago")
YEAR       = 2026
TASKS_FILE = "tasks.json"
DASH_URL   = "https://yvve77.github.io/DDL-collector"
SEMESTER   = "Fall 2026"

COURSE_COLORS = {
    "CS 225":   {"bg": "#f0fff4", "text": "#276749"},
    "BIOE 206": {"bg": "#fff5eb", "text": "#c05621"},
    "BIOE 310": {"bg": "#faf5ff", "text": "#6b46c1"},
    "DANC 340": {"bg": "#fff0f6", "text": "#97266d"},
    "BIOE 210 Grading": {"bg": "#eef4fb", "text": "#1e4e8c"},
    "Admin":    {"bg": "#f1f5f9", "text": "#475569"},
}

# Personal buffer: aim to finish this many days before the real DDL.
# Exams: start reviewing this many days before the exam (or window start).
BUFFER_DAYS = {"potd": 0, "lab": 1, "hw": 1, "quiz": 0, "project": 3,
               "exam": 5, "grading": 0, "admin": 0}

# BIOE 210 grader: (homework, due) as shown in Gradescope. Add new rows as HWs are posted.
# Rule: finish grading HW n three days before HW n+1 is due.
# The newest HW has no successor yet, so its grading date assumes a 7-day gap.
GRADER_HWS = [
    ("HW 2", "2026-09-18 09:00"),
    ("HW 3", "2026-09-28 09:00"),
    ("HW 4", "2026-10-05 09:00"),
]

URLS = {
    "Canvas":       "https://canvas.illinois.edu",
    "PrairieLearn": "https://us.prairielearn.com",
    "PrairieTest":  "https://us.prairietest.com",
    "Registrar":    "https://registrar.illinois.edu/academic-calendars/",
    "Gradescope":   "https://www.gradescope.com",
}

# No-class days
LABOR_DAY  = date(YEAR, 9, 7)
FALL_BREAK = {date(YEAR, 11, 21) + timedelta(days=i) for i in range(9)}  # 11/21-11/29
LAST_DAY   = date(YEAR, 12, 9)

# ── Helpers ────────────────────────────────────────────────────────────────────

def ct(month, day, hour=23, minute=59):
    return CT.localize(datetime(YEAR, month, day, hour, minute))

def now_ct():
    return datetime.now(CT)

def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(CT) if s else None

def task_id(title, course, due):
    safe = re.sub(r"[^a-z0-9]+", "_", f"{course} {title}".lower()).strip("_")
    return f"{safe}__{due.strftime('%Y%m%d_%H%M')}"

def T(title, course, due, source, kind, start=None, allday=False, end=None,
      stable=False, keep=False, done=False, key=None):
    """stable: id ignores the date, so an estimate can later be corrected in place.
    keep: add even if already past due.  done: start out checked."""
    return {"title": title, "course": course, "due": due, "source": source,
            "url": URLS.get(source, ""), "kind": kind, "start": start, "allday": allday,
            "end": end.isoformat() if end else None, "stable": stable or bool(key), "keep": keep, "done": done, "key": key}

def target_of(t):
    """When to aim to be done (or, for exams, start reviewing)."""
    due = parse_iso(t["due"]) if isinstance(t["due"], str) else t["due"]
    days = BUFFER_DAYS.get(t.get("kind"), 0)
    if t.get("kind") == "exam":
        base = parse_iso(t["start"]) if t.get("start") else due
        naive = (base.replace(tzinfo=None) - timedelta(days=days)).replace(hour=9, minute=0)
    else:
        naive = due.replace(tzinfo=None) - timedelta(days=days)
    return CT.localize(naive)  # re-localize so DST changes don't shift the clock time

def no_class(d):
    return d == LABOR_DAY or d in FALL_BREAK

def next_class_weekday(d):
    d += timedelta(days=1)
    while d.weekday() >= 5 or no_class(d):
        d += timedelta(days=1)
    return d

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)

# ── All assignments ────────────────────────────────────────────────────────────

def all_assignments():
    tasks = []

    # ── CS 225 — PrairieLearn ─────────────────────────────────────────────────
    # POTD: one per class weekday, due that day 23:59
    for d in daterange(date(YEAR, 8, 24), LAST_DAY):
        if d.weekday() < 5 and not no_class(d):
            tasks.append(T(f"POTD {d.strftime('%b %d')}", "CS 225",
                           ct(d.month, d.day), "PrairieLearn", "potd"))

    # Lab every Sunday 23:59
    for d in daterange(date(YEAR, 8, 30), date(YEAR, 12, 6)):
        if d.weekday() == 6 and d not in FALL_BREAK:
            wk = d - timedelta(days=6)
            tasks.append(T(f"Lab (week of {wk.strftime('%b %d')})", "CS 225",
                           ct(d.month, d.day), "PrairieLearn", "lab"))

    # MPs: every 2 weeks, due Monday 23:59. MP1/MP2 confirmed, later ones estimated.
    tasks.append(T("MP1 mp_lists", "CS 225", ct(9, 28), "PrairieLearn", "project", done=True))
    tasks.append(T("MP_EC2 mp_mosaics extra credit", "CS 225", ct(10, 5), "PrairieLearn", "hw"))
    tasks.append(T("MP2 mp_mosaics", "CS 225", ct(10, 12), "PrairieLearn", "project"))
    for n, (m, d) in [(3, (10, 26)), (4, (11, 9)), (5, (11, 30))]:
        tasks.append(T(f"MP{n} (est.)", "CS 225", ct(m, d), "PrairieLearn", "project", key=f"MP{n}"))

    # Extra credit + feedback
    tasks.append(T("LabEC0 lab_trees (extra credit)", "CS 225", ct(10, 7), "PrairieLearn", "hw"))
    tasks.append(T("Informal Early Feedback survey", "CS 225", ct(10, 7), "PrairieLearn", "quiz"))
    tasks.append(T("Research consent form", "CS 225", ct(10, 12), "PrairieLearn", "admin"))

    # Exam windows (CBTF)
    for title, (sm, sd), (em, ed) in [
        ("Exam 0",      (9, 2),  (9, 4)),
        ("Exam 1",      (9, 16), (9, 18)),
        ("Exam 2",      (9, 30), (10, 2)),
        ("Exam 3",      (10, 21),(10, 23)),
        ("Exam 4",      (11, 11),(11, 13)),
        ("Exam 5",      (12, 2), (12, 4)),
        ("Retake Exam", (12, 6), (12, 8)),
        ("Final Exam",  (12, 10),(12, 17)),
    ]:
        tasks.append(T(title, "CS 225", ct(em, ed), "PrairieTest", "exam",
                       start=ct(sm, sd, 0, 0).isoformat(), allday=True))

    # Registration openings: book the CBTF slot the day it opens
    for title, (m, d) in [
        ("Book Exam 3 slot",     (10, 8)),
        ("Book Final Exam slot (aim for 12/17)", (10, 19)),
        ("Book Exam 4 slot",     (10, 29)),
        ("Book Exam 5 slot",     (11, 12)),
        ("Decide on Retake + book slot", (11, 19)),
    ]:
        tasks.append(T(title, "CS 225", ct(m, d), "PrairieTest", "admin", allday=True))

    # ── BIOE 206 — Canvas (HW due Thursdays, not every week) ──────────────────
    for n, (m, d) in enumerate([(9,3),(9,10),(9,17),(10,1),(10,8),(10,15),(10,29),(11,5),(11,12),(12,3)], 1):
        tasks.append(T(f"HW {n}", "BIOE 206", ct(m, d), "Canvas", "hw"))

    for title, due in [("Exam 1 (weeks 1-4)", ct(9, 22)), ("Exam 2 (weeks 5-8)", ct(10, 20)),
                       ("Exam 3 (weeks 9-12)", ct(11, 17))]:
        tasks.append(T(title, "BIOE 206", due, "Canvas", "exam", allday=True))
    tasks.append(T("Final Exam (cumulative)", "BIOE 206", ct(12, 11, 13, 30), "Canvas", "exam",
                   end=ct(12, 11, 16, 30)))

    # ── BIOE 310 — HW on PrairieLearn, exams at CBTF ──────────────────────────
    # HWs appear on PrairieLearn irregularly; add each new one here.
    for title, due, done in [
        ("HW 1", ct(9, 18), True),
        ("HW 2", ct(9, 28), True),
    ]:
        tasks.append(T(title, "BIOE 310", due, "PrairieLearn", "hw", done=done))

    for key, title, (sm, sd), (em, ed) in [
        ("Midterm 1", "Midterm 1 (50 min)",            (9, 29),  (10, 1)),
        ("Midterm 2", "Midterm 2 (50 min, tentative)", (11, 3),  (11, 5)),
        ("Final",     "Final Exam (1h50, tentative)",  (12, 10), (12, 15)),
    ]:
        tasks.append(T(title, "BIOE 310", ct(em, ed), "PrairieTest", "exam",
                       start=ct(sm, sd, 0, 0).isoformat(), allday=True, key=key))
    for title, (m, d) in [
        ("Register for Final Exam slot", (10, 19)),
        ("Reserve Midterm 2 slot",       (10, 22)),
    ]:
        tasks.append(T(title, "BIOE 310", ct(m, d), "PrairieTest", "admin", allday=True))

    # ── DANC 340 — Canvas (Sundays 23:59) ─────────────────────────────────────
    for n, (m, d) in enumerate([(8,30),(9,13),(9,27),(10,11),(10,25),(11,8),(11,22),(12,6)], 1):
        tasks.append(T(f"Module {n} Glossary", "DANC 340", ct(m, d), "Canvas", "hw"))

    for (m, d), items in [
        ((9, 6),   [("Module 1 Quiz", "quiz"), ("EE 1: The Knee Bone Bent", "hw")]),
        ((9, 20),  [("Module 2 Quiz", "quiz"), ("EE 2: Dance Manual", "hw"), ("EE 2: Writing", "hw")]),
        ((10, 4),  [("Module 3 Quiz", "quiz"), ("Project 1: Interview", "project"), ("Project 1: Writing", "project")]),
        ((10, 18), [("Module 4 Quiz", "quiz"), ("EE 3: Playlist Lineage", "hw")]),
        ((11, 1),  [("Module 5 Quiz", "quiz"), ("EE 4: Dance Floor Connections", "hw")]),
        ((11, 15), [("Module 6 Quiz", "quiz"), ("Project 2: Mapping", "project")]),
        ((11, 29), [("Module 7 Quiz", "quiz"), ("Project 3: Final Synthesis draft", "project")]),
        ((12, 13), [("Module 8 Quiz", "quiz"), ("Project 3: Final Synthesis", "project")]),
    ]:
        for title, kind in items:
            tasks.append(T(title, "DANC 340", ct(m, d), "Canvas", kind))

    # ── BIOE 210 grading (Gradescope) ─────────────────────────────────────────
    for i, (hw, due_s) in enumerate(GRADER_HWS):
        if i + 1 < len(GRADER_HWS):
            nxt = CT.localize(datetime.strptime(GRADER_HWS[i + 1][1], "%Y-%m-%d %H:%M"))
            title = f"Grade {hw}"
        else:
            nxt = CT.localize(datetime.strptime(due_s, "%Y-%m-%d %H:%M")) + timedelta(days=7)
            title = f"Grade {hw} (est.)"
        tasks.append(T(title, "BIOE 210 Grading", nxt - timedelta(days=3), "Gradescope", "grading",
                       key=f"Grade {hw}", keep=True))

    # ── Admin ─────────────────────────────────────────────────────────────────
    for title, (m, d) in [
        ("Last day to drop without a W",          (10, 16)),
        ("SP27 priority registration opens",      (11, 2)),
        ("Last day of instruction",               (12, 9)),
    ]:
        tasks.append(T(title, "Admin", ct(m, d), "Registrar", "admin", allday=True))

    return tasks

# ── Task state ─────────────────────────────────────────────────────────────────

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {}

def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2, default=str)

def merge_tasks(existing, fresh):
    """Add new tasks, keep user state (completed, edits, notes) on existing ones.
    Tasks already more than 2 days past due on first sight are skipped, so a
    reset tasks.json doesn't flood Past Due with old items."""
    updated = dict(existing)
    now = now_ct()
    fresh_ids = set()
    for a in fresh:
        if a["stable"]:   # id survives date changes (e.g. grading dates move when a new HW is posted)
            base = a["key"] or re.sub(r"\s*\(est\.\)", "", a["title"])
            tid = re.sub(r"[^a-z0-9]+", "_", f"{a['course']} {base}".lower()).strip("_")
        else:
            tid = task_id(a["title"], a["course"], a["due"])
        fresh_ids.add(tid)
        if tid in updated:
            t = updated[tid]
            for k in ("kind", "start", "allday", "end"):
                t.setdefault(k, a[k])
            if a["stable"] and not t.get("edited"):
                t["title"], t["due"] = a["title"], a["due"].isoformat()
                t["start"], t["end"], t["allday"] = a["start"], a["end"], a["allday"]
            continue
        if a["due"] < now - timedelta(days=2) and not a["keep"]:
            continue
        updated[tid] = {
            "id": tid, "title": a["title"], "course": a["course"],
            "due": a["due"].isoformat(), "source": a["source"], "url": a["url"],
            "kind": a["kind"], "start": a["start"], "allday": a["allday"], "end": a["end"],
            "completed": a["done"],
        }
    # Drop tasks that were removed from the schedule and are already past
    for tid in list(updated):
        t = updated[tid]
        if t.get("custom"):
            continue
        if tid not in fresh_ids and parse_iso(t["due"]) < now:
            del updated[tid]
    # Drop courses no longer taken
    for tid in list(updated):
        if updated[tid]["course"] not in COURSE_COLORS:
            del updated[tid]
    return updated

# ── Email ──────────────────────────────────────────────────────────────────────

def urgency_info(due):
    h = (due - now_ct()).total_seconds() / 3600
    if h < 0:   return "#991b1b", "⛔ Overdue"
    if h < 24:  return "#e53e3e", f"⚠️ {int(h)}h left"
    d = int(h // 24)
    if d == 1:  return "#e53e3e", "🔴 Tomorrow"
    if d <= 3:  return "#dd6b20", f"🟠 {d} days"
    if d <= 7:  return "#d69e2e", f"🟡 {d} days"
    return "#38a169", f"🟢 {d} days"

def fmt_target(a):
    tg, due = target_of(a), parse_iso(a["due"])
    if a.get("kind") == "exam":
        return f"review from {tg.strftime('%b %d')}"
    if tg == due:
        return ""
    return f"aim {tg.strftime('%a %b %d')}"

def fmt_due(a):
    due = parse_iso(a["due"])
    if a.get("start"):
        s = parse_iso(a["start"])
        return f"{s.strftime('%b %d')} to {due.strftime('%b %d')}"
    if a.get("allday"):
        return due.strftime("%b %d")
    return due.strftime("%b %d, %I:%M %p")

def make_table(items):
    if not items:
        return "<p style='color:#a0aec0;text-align:center;padding:20px 0;font-size:14px;'>🎉 Nothing here!</p>"
    th = "padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;"
    td = "padding:11px 14px;border-bottom:1px solid #edf2f7;"
    rows = ""
    for a in items:
        tg, due = target_of(a), parse_iso(a["due"])
        now = now_ct()
        if due > now and tg <= now and a.get("kind") != "exam":
            uc, ul = "#dd6b20", "⏰ Buffer"
        else:
            uc, ul = urgency_info(tg if tg > now else due)
        cc = COURSE_COLORS.get(a["course"], {"bg": "#f7fafc", "text": "#4a5568"})
        title = ("📝 " if a.get("kind") == "exam" else "") + a["title"]
        rows += f"""
        <tr>
          <td style="{td}"><a href="{a['url']}" style="color:#2d3748;text-decoration:none;font-weight:500;font-size:14px;">{title}</a></td>
          <td style="{td}"><span style="background:{cc['bg']};color:{cc['text']};padding:3px 9px;border-radius:9999px;font-size:12px;font-weight:500;white-space:nowrap;">{a['course']}</span></td>
          <td style="{td}font-weight:600;color:{uc};font-size:13px;white-space:nowrap;">{ul}</td>
          <td style="{td}color:#718096;font-size:13px;white-space:nowrap;">{fmt_due(a)}<div style="font-size:11px;color:#b7791f;">{fmt_target(a)}</div></td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
        <th style="{th}">Assignment</th><th style="{th}">Course</th><th style="{th}">Urgency</th><th style="{th}">Due</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""

def build_html(overdue, pending):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in pending if target_of(a) <= week_end]
    later    = [a for a in pending if target_of(a) >  week_end]
    urgent   = [a for a in pending if (parse_iso(a["due"]) - today).total_seconds() < 86400]

    counts = {}
    for a in pending:
        counts[a["course"]] = counts.get(a["course"], 0) + 1
    pills = "".join(
        f'<span style="background:{COURSE_COLORS[c]["bg"]};color:{COURSE_COLORS[c]["text"]};padding:4px 10px;border-radius:9999px;font-size:12px;font-weight:500;margin-left:6px;">{c} {n}</span>'
        for c, n in sorted(counts.items()) if c in COURSE_COLORS)

    def sec(title, items, icon, color="#2d3748"):
        return f"""
        <div style="margin-bottom:28px;">
          <h2 style="color:{color};font-size:14px;font-weight:700;margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid #edf2f7;">
            {icon} {title} <span style="color:#a0aec0;font-size:13px;font-weight:400;margin-left:4px;">({len(items)})</span>
          </h2>
          {make_table(items)}
        </div>"""

    stat = lambda n, c, label: f'<div style="text-align:center;"><div style="font-size:26px;font-weight:800;color:{c};line-height:1;">{n}</div><div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">{label}</div></div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:720px;margin:28px auto;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">
  <div style="background:linear-gradient(135deg,#5a67d8,#805ad5);padding:28px 32px;">
    <div style="font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Daily Digest · {SEMESTER}</div>
    <h1 style="margin:0;color:white;font-size:24px;font-weight:700;letter-spacing:-0.5px;">{today.strftime('%A, %B %d')}</h1>
    <p style="margin:7px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">{len(pending)} pending · {len(urgent)} due within 24h{f' · {len(overdue)} overdue' if overdue else ''}</p>
  </div>
  <div style="background:white;border-bottom:1px solid #e2e8f0;padding:16px 32px;display:flex;align-items:center;">
    <div style="display:flex;gap:28px;flex:1;">
      {stat(len(overdue), '#991b1b', 'Overdue') if overdue else ''}
      {stat(len(soon), '#e53e3e', 'This week')}
      {stat(len(later), '#38a169', 'Later')}
    </div>
    <div style="text-align:right;">{pills}</div>
  </div>
  <div style="background:white;padding:24px 32px 12px;">
    {sec("Past Due", overdue, "⛔", "#991b1b") if overdue else ''}
    {sec("This Week (by your target date)", soon, "🔥")}
    {sec("Coming Up Later", later, "📆")}
  </div>
  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:14px 32px;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:12px;color:#a0aec0;">{SEMESTER} · CS 225 · BIOE 206 · BIOE 310 · DANC 340 · BIOE 210 grading</span>
    <a href="{DASH_URL}" style="background:#5a67d8;color:white;text-decoration:none;padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;">✅ Dashboard →</a>
  </div>
</div>
</body></html>"""

def send_email(html, subject):
    missing = [k for k, v in [("GMAIL_ADDRESS", GMAIL_ADDRESS),
                              ("GMAIL_APP_PASSWORD", GMAIL_APP_PASSWORD),
                              ("TO_EMAIL", TO_EMAIL)] if not v]
    if missing:
        print(f"❌ Missing GitHub secret(s): {', '.join(missing)}")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        print("❌ Gmail rejected the login. The app password is expired or revoked.")
        print("   Fix: create a new one at https://myaccount.google.com/apppasswords")
        print("   then update the GMAIL_APP_PASSWORD secret in the repo settings.")
        print(f"   ({e.smtp_code} {e.smtp_error!r})")
        return False
    except Exception as e:
        print(f"❌ Email failed: {type(e).__name__}: {e}")
        return False
    print(f"✅ Email sent → {TO_EMAIL}")
    return True

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today = now_ct()
    print(f"🕐 {today.strftime('%Y-%m-%d %H:%M %Z')}")

    merged = merge_tasks(load_tasks(), all_assignments())
    save_tasks(merged)
    print(f"💾 tasks.json: {len(merged)} tasks saved")

    open_tasks = [t for t in merged.values() if not t["completed"]]
    overdue = sorted([t for t in open_tasks if parse_iso(t["due"]) <= today], key=lambda x: x["due"])
    pending = sorted([t for t in open_tasks if parse_iso(t["due"]) >  today], key=target_of)
    print(f"📬 Pending: {len(pending)} · Overdue: {len(overdue)}")
    for t in pending[:5]:
        print(f"   {parse_iso(t['due']).strftime('%m/%d %H:%M')} [{t['course']}] {t['title']}")

    if not pending and not overdue:
        print("Nothing pending, skipping email.")
        return

    urgent = len([t for t in pending if (parse_iso(t["due"]) - today).total_seconds() < 86400])
    if urgent:
        subject = f"⚠️ {urgent} due within 24h · {today.strftime('%a %b %d')}"
    else:
        subject = f"☀️ DDL Digest · {today.strftime('%a %b %d')} · {len(pending)} pending"

    if not send_email(build_html(overdue, pending), subject):
        sys.exit(1)  # tasks.json is already saved; the commit step still runs

if __name__ == "__main__":
    main()
