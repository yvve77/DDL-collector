#!/usr/bin/env python3
"""
Assignment DDL Digest — Fall 2026
Courses: CS 361, CS 225, BIOE 206, BIOE 310, DANC 340
"""

import os, json, re, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

# ── Config ─────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL           = os.environ["TO_EMAIL"]

CENTRAL_TZ = pytz.timezone("America/Chicago")
TASKS_FILE = "tasks.json"
DASH_URL   = "https://yvve77.github.io/DDL-collector"

COURSE_COLORS = {
    "CS 361":   {"bg": "#ebf8ff", "text": "#2b6cb0"},
    "CS 225":   {"bg": "#f0fff4", "text": "#276749"},
    "BIOE 206": {"bg": "#fff5eb", "text": "#c05621"},
    "BIOE 310": {"bg": "#faf5ff", "text": "#6b46c1"},
    "DANC 340": {"bg": "#fff0f6", "text": "#97266d"},
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def ct(month, day, hour=23, minute=59):
    return CENTRAL_TZ.localize(datetime(2026, month, day, hour, minute))

def now_ct():
    return datetime.now(CENTRAL_TZ)

def parse_iso(s):
    if not s: return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(CENTRAL_TZ)

def task_id(title, due):
    safe = re.sub(r"[^a-z0-9]", "_", title.lower())
    return f"{safe}__{due.strftime('%Y%m%d_%H%M')}"

def canvas(title, course, due):
    return {"title": title, "course": course, "due": due,
            "source": "Canvas", "url": "https://canvas.illinois.edu"}

def pl(title, course, due):
    return {"title": title, "course": course, "due": due,
            "source": "PrairieLearn", "url": "https://us.prairielearn.com"}

def gs(title, course, due):
    return {"title": title, "course": course, "due": due,
            "source": "Gradescope", "url": "https://www.gradescope.com"}

def next_weekday(d):
    d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    return d

# ── All assignments ────────────────────────────────────────────────────────────

def all_assignments():
    tasks = []

    fall_break = set()
    d = datetime(2026, 11, 21)
    while d <= datetime(2026, 11, 29):
        fall_break.add(d.date())
        d += timedelta(days=1)

    # ── CS 361 — PrairieLearn / Gradescope ────────────────────────────────────
    # Homeworks (Gradescope, typed PDF)
    for title, due in [
        ("HW 1",  ct(9,3)),
        ("HW 2",  ct(9,10)),
        ("HW 3",  ct(9,17)),
        ("HW 4",  ct(9,25)),
        ("HW 5",  ct(10,2)),
        ("HW 6",  ct(10,15)),
        ("HW 7",  ct(10,23)),
        ("HW 8",  ct(10,30)),
        ("HW 9",  ct(11,12)),
        ("HW 10", ct(12,1)),
    ]:
        tasks.append(gs(title, "CS 361", due))

    # Quizzes (PrairieTest)
    for title, due in [
        ("Orientation Quiz", ct(8,25)),
        ("Quiz 1",  ct(9,1)),
        ("Quiz 2",  ct(9,3)),
        ("Quiz 3",  ct(9,17)),
        ("Quiz 4",  ct(10,1)),
        ("Quiz 5",  ct(10,15)),
        ("Quiz 6",  ct(10,29)),
        ("Quiz 7",  ct(11,17)),
    ]:
        tasks.append(pl(title, "CS 361", due))

    # Group Discussions (Canvas)
    for num, due in [
        (1,  ct(9,2)),  (2,  ct(9,9)),  (3,  ct(9,16)), (4,  ct(9,23)),
        (5,  ct(10,1)), (6,  ct(10,14)),(7,  ct(10,21)),(8,  ct(10,28)),
        (9,  ct(11,11)),(10, ct(11,30)),
    ]:
        tasks.append(canvas(f"Group Discussion {num}", "CS 361", due))

    # Examlets & Finals
    for title, due in [
        ("Examlet 1 (CBTF)",     ct(9,29,  23,59)),
        ("Examlet 2 (in-class)", ct(10,8,  23,59)),
        ("Examlet 3 (CBTF)",     ct(11,3,  23,59)),
        ("Examlet 4 (in-class)", ct(11,19, 23,59)),
        ("Examlet 5 + Replacement Exam", ct(12,15, 10,0)),
        ("Project",              ct(12,3)),
    ]:
        tasks.append(pl(title, "CS 361", due))

    # ── CS 225 — PrairieLearn ─────────────────────────────────────────────────
    # POTD: every weekday 8/24-12/9, due next weekday 17:00
    start_potd = datetime(2026, 8, 24)
    end_potd   = datetime(2026, 12, 9)
    d = start_potd
    while d <= end_potd:
        if d.weekday() < 5 and d.date() not in fall_break:
            nd = next_weekday(d)
            due = CENTRAL_TZ.localize(datetime(nd.year, nd.month, nd.day, 17, 0))
            tasks.append(pl(f"POTD - {d.strftime('%b %d')}", "CS 225", due))
        d += timedelta(days=1)

    # Labs: every Sunday 23:59 starting 8/30
    d = datetime(2026, 8, 30)
    while d <= datetime(2026, 12, 6):
        if d.weekday() == 6 and d.date() not in fall_break:
            week_start = d - timedelta(days=6)
            due = CENTRAL_TZ.localize(datetime(d.year, d.month, d.day, 23, 59))
            tasks.append(pl(f"Lab - Week of {week_start.strftime('%b %d')}", "CS 225", due))
        d += timedelta(days=1)

    # MPs: estimated every ~2 weeks from week 3, due Sunday 23:59
    for title, due in [
        ("MP 1", ct(9,13)),
        ("MP 2", ct(9,27)),
        ("MP 3", ct(10,11)),
        ("MP 4", ct(10,25)),
        ("MP 5", ct(11,8)),
        ("MP 6", ct(11,22)),
        ("MP 7", ct(12,6)),
    ]:
        tasks.append(pl(title, "CS 225", due))

    # Exams (CBTF)
    for title, due in [
        ("Exam 0",       ct(9,4,  23,59)),
        ("Exam 1",       ct(9,18, 23,59)),
        ("Exam 2",       ct(10,2, 23,59)),
        ("Exam 3",       ct(10,23,23,59)),
        ("Exam 4",       ct(11,13,23,59)),
        ("Exam 5",       ct(12,4, 23,59)),
        ("Retake Exam",  ct(12,8, 23,59)),
        ("Final Exam",   ct(12,17,23,59)),
    ]:
        tasks.append(pl(title, "CS 225", due))

    # ── BIOE 206 — Canvas ─────────────────────────────────────────────────────
    # HW every Thursday 23:59, from 8/27, skip fall break
    d = datetime(2026, 8, 27)
    hw_num = 1
    while d <= datetime(2026, 11, 19):
        if d.weekday() == 3 and d.date() not in fall_break:
            due = CENTRAL_TZ.localize(datetime(d.year, d.month, d.day, 23, 59))
            tasks.append(canvas(f"HW {hw_num}", "BIOE 206", due))
            hw_num += 1
        d += timedelta(days=1)

    # Estimated exams
    for title, due in [
        ("Midterm 1 (est.)", ct(10,1)),
        ("Midterm 2 (est.)", ct(11,5)),
        ("Midterm 3 (est.)", ct(12,3)),
        ("Final Exam",       ct(12,11, 16,30)),
    ]:
        tasks.append(canvas(title, "BIOE 206", due))

    # ── BIOE 310 — (platform TBD, using Canvas for now) ──────────────────────
    for title, due in [
        ("Midterm 1 (est.)", ct(10,9,  23,59)),
        ("Midterm 2 (est.)", ct(11,13, 23,59)),
        ("Final Exam (est.)", ct(12,17, 23,59)),
    ]:
        tasks.append(canvas(title, "BIOE 310", due))

    # ── DANC 340 — Canvas ─────────────────────────────────────────────────────
    for title, due in [
        # Glossaries
        ("Module 1 Glossary",  ct(8,30)),
        ("Module 2 Glossary",  ct(9,13)),
        ("Module 3 Glossary",  ct(9,27)),
        ("Module 4 Glossary",  ct(10,11)),
        ("Module 5 Glossary",  ct(10,25)),
        ("Module 6 Glossary",  ct(11,8)),
        ("Module 7 Glossary",  ct(11,22)),
        ("Module 8 Glossary",  ct(12,6)),
        # Embodied Exercises + Quizzes
        ("EE 1 + Module 1 Quiz",                ct(9,6)),
        ("EE 2: Dance Manual + Module 2 Quiz",  ct(9,20)),
        ("EE 3: Playlist Lineage + Module 3 Quiz", ct(10,18)),
        ("EE 4: Dance Floor Connections + Module 5 Quiz", ct(11,1)),
        # Projects
        ("Project 1: Interview + Module 3 Quiz", ct(10,4)),
        ("Project 2: Mapping + Module 6 Quiz",   ct(11,15)),
        ("Project 3: Final Synthesis (Draft) + Module 7 Quiz", ct(11,29)),
        ("Project 3: Final Synthesis + Module 8 Quiz",         ct(12,13)),
    ]:
        tasks.append(canvas(title, "DANC 340", due))

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
    updated = dict(existing)
    now = now_ct()
    fresh_ids = set()
    for a in fresh:
        tid = task_id(a["title"], a["due"])
        fresh_ids.add(tid)
        if tid not in updated:
            updated[tid] = {
                "id": tid, "title": a["title"], "course": a["course"],
                "due": a["due"].isoformat(), "source": a["source"],
                "url": a["url"], "completed": False,
            }
    for tid in list(updated.keys()):
        if tid not in fresh_ids and parse_iso(updated[tid]["due"]) < now:
            del updated[tid]
    return updated

# ── Email ──────────────────────────────────────────────────────────────────────

def urgency_info(due):
    h = (due - now_ct()).total_seconds() / 3600
    if h < 24:  return "#e53e3e", f"⚠️ {int(h)}h left"
    d = int(h // 24)
    if d == 1:  return "#e53e3e", "🔴 Tomorrow"
    if d <= 3:  return "#dd6b20", f"🟠 {d} days"
    if d <= 7:  return "#d69e2e", f"🟡 {d} days"
    return "#38a169", f"🟢 {d} days"

def make_table(items):
    if not items:
        return "<p style='color:#a0aec0;text-align:center;padding:20px 0;font-size:14px;'>🎉 Nothing here!</p>"
    rows = ""
    for a in items:
        due = parse_iso(a["due"])
        uc, ul = urgency_info(due)
        cc = COURSE_COLORS.get(a["course"], {"bg": "#f7fafc", "text": "#4a5568"})
        sb = "#ebf8ff" if a["source"] == "Canvas" else "#f0fff4" if a["source"] == "PrairieLearn" else "#fef9c3"
        sc = "#2b6cb0" if a["source"] == "Canvas" else "#276749" if a["source"] == "PrairieLearn" else "#854d0e"
        rows += f"""
        <tr>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <a href="{a['url']}" style="color:#2d3748;text-decoration:none;font-weight:500;font-size:14px;">{a['title']}</a>
          </td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <span style="background:{cc['bg']};color:{cc['text']};padding:3px 9px;border-radius:9999px;font-size:12px;font-weight:500;white-space:nowrap;">{a['course']}</span>
          </td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;font-weight:600;color:{uc};font-size:13px;white-space:nowrap;">{ul}</td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;color:#718096;font-size:13px;white-space:nowrap;">{due.strftime('%b %d, %I:%M %p')}</td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <span style="background:{sb};color:{sc};padding:3px 9px;border-radius:9999px;font-size:11px;">{a['source']}</span>
          </td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
        <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Assignment</th>
        <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Course</th>
        <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Urgency</th>
        <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Due</th>
        <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Platform</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""

def build_html(pending, is_monday):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in pending if parse_iso(a["due"]) <= week_end]
    later    = [a for a in pending if parse_iso(a["due"]) >  week_end]
    urgent   = [a for a in pending if (parse_iso(a["due"]) - today).total_seconds() < 86400]

    course_counts = {}
    for a in pending:
        course_counts[a["course"]] = course_counts.get(a["course"], 0) + 1
    pills = ""
    for course, count in sorted(course_counts.items()):
        cc = COURSE_COLORS.get(course, {"bg": "#f7fafc", "text": "#4a5568"})
        pills += f'<span style="background:{cc["bg"]};color:{cc["text"]};padding:4px 10px;border-radius:9999px;font-size:12px;font-weight:500;margin-left:6px;">{course} {count}</span>'

    def sec(title, items, icon):
        n = len(items)
        return f"""
        <div style="margin-bottom:28px;">
          <h2 style="color:#2d3748;font-size:14px;font-weight:700;margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid #edf2f7;">
            {icon} {title} <span style="color:#a0aec0;font-size:13px;font-weight:400;margin-left:4px;">({n})</span>
          </h2>
          {make_table(items)}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:720px;margin:28px auto;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">
  <div style="background:linear-gradient(135deg,#5a67d8,#805ad5);padding:28px 32px;">
    <div style="font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Daily Digest · Fall 2026</div>
    <h1 style="margin:0;color:white;font-size:24px;font-weight:700;letter-spacing:-0.5px;">{today.strftime('%A, %B %d')}</h1>
    <p style="margin:7px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">{len(pending)} pending · {len(urgent)} due within 24h</p>
  </div>
  <div style="background:white;border-bottom:1px solid #e2e8f0;padding:16px 32px;display:flex;align-items:center;">
    <div style="display:flex;gap:28px;flex:1;">
      <div style="text-align:center;"><div style="font-size:26px;font-weight:800;color:#5a67d8;line-height:1;">{len(pending)}</div><div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">Total</div></div>
      <div style="text-align:center;"><div style="font-size:26px;font-weight:800;color:#e53e3e;line-height:1;">{len(soon)}</div><div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">This week</div></div>
      <div style="text-align:center;"><div style="font-size:26px;font-weight:800;color:#38a169;line-height:1;">{len(later)}</div><div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">Later</div></div>
    </div>
    <div style="text-align:right;">{pills}</div>
  </div>
  <div style="background:white;padding:24px 32px 12px;">
    {sec("Due This Week", soon, "🔥")}
    {sec("Coming Up Later", later, "📆")}
  </div>
  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:14px 32px;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:12px;color:#a0aec0;">Fall 2026 · CS 361 · CS 225 · BIOE 206 · BIOE 310 · DANC 340</span>
    <a href="{DASH_URL}" style="background:#5a67d8;color:white;text-decoration:none;padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;">✅ Dashboard →</a>
  </div>
</div>
</body></html>"""

def send_email(html, subject):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        s.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    print(f"✅ Email sent → {TO_EMAIL}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today     = now_ct()
    is_monday = today.weekday() == 0
    print(f"🕐 {today.strftime('%Y-%m-%d %H:%M %Z')} | Monday={is_monday}")

    fresh    = all_assignments()
    existing = load_tasks()
    merged   = merge_tasks(existing, fresh)
    save_tasks(merged)
    print(f"💾 tasks.json: {len(merged)} tasks saved")

    pending = sorted(
        [t for t in merged.values()
         if not t["completed"] and parse_iso(t["due"]) > today],
        key=lambda x: x["due"]
    )
    print(f"📬 Pending: {len(pending)}")
    for t in pending[:5]:
        print(f"   {parse_iso(t['due']).strftime('%m/%d %H:%M')} [{t['course']}] {t['title']}")
    if len(pending) > 5:
        print(f"   ... and {len(pending)-5} more")

    if not pending:
        print("Nothing pending, skipping email."); return

    urgent_count = len([t for t in pending if (parse_iso(t["due"]) - today).total_seconds() < 86400])
    if urgent_count:
        subject = f"⚠️ {urgent_count} due within 24h — {today.strftime('%a %b %d')}"
    else:
        subject = f"☀️ DDL Digest — {today.strftime('%a %b %d')} · {len(pending)} pending"

    send_email(build_html(pending, is_monday), subject)

if __name__ == "__main__":
    main()
