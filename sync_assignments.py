#!/usr/bin/env python3
"""
Assignment DDL Digest
All assignments hardcoded - no API needed.
Sends daily HTML email, skips completed tasks.
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

# ── Helper ─────────────────────────────────────────────────────────────────────

def ct(month, day, hour=23, minute=59):
    """Create a Central Time datetime for 2025."""
    return CENTRAL_TZ.localize(datetime(2025, month, day, hour, minute))

def now_ct():
    return datetime.now(CENTRAL_TZ)

def parse_iso(s):
    if not s: return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(CENTRAL_TZ)

def task_id(title, due):
    safe = re.sub(r"[^a-z0-9]", "_", title.lower())
    return f"{safe}__{due.strftime('%Y%m%d')}"

def make_assignment(title, course, due, source="Canvas", url="https://canvas.illinois.edu"):
    return {"title": title, "course": course, "due": due, "source": source, "url": url}

# ── All assignments ────────────────────────────────────────────────────────────

def all_assignments():
    tasks = []

    # ── BioE 210 (Canvas) ──────────────────────────────────────────────────────
    # Weekly HW, due every Monday 11:59 PM
    bioe_mondays = [
        ct(2,24), ct(3,3), ct(3,10), ct(3,17), ct(3,24),
        ct(3,31), ct(4,7), ct(4,14), ct(4,21), ct(4,28), ct(5,5),
    ]
    for i, due in enumerate(bioe_mondays, 1):
        tasks.append(make_assignment(f"BioE 210 — Weekly HW {i}", "BioE 210", due))

    # ── BioE 210 Quizzes (from Canvas data) ───────────────────────────────────
    bioe_quizzes = [
        ("Q14: Quiz for Lecture 14", ct(2,25)),
        ("Q15: Quiz for Lecture 15", ct(2,27)),
        ("Q16: Quiz for Lecture 16", ct(3,2)),
        ("Q17: Quiz for Lecture 17", ct(3,4)),
        ("Q18: Quiz for Lecture 18", ct(3,6)),
        ("Q19: Quiz for Lecture 19", ct(3,9)),
        ("Q20: Quiz for Lecture 20", ct(3,11)),
        ("Q21: Quiz for Lecture 21", ct(3,13)),
        ("Q22: Quiz for Lecture 22", ct(3,23)),
        ("Q23: Quiz for Lecture 23", ct(3,25)),
        ("Q24: Quiz for Lecture 24", ct(3,30)),
        ("Q25: Quiz for Lecture 25", ct(4,1)),
        ("Q26: Quiz for Lecture 26", ct(4,3)),
        ("Q27: Quiz for Lecture 27", ct(4,6)),
        ("Q28: Quiz for Lecture 28", ct(4,8)),
        ("Q29: Quiz for Lecture 29", ct(4,10)),
        ("Q30: Quiz for Lecture 30", ct(4,13)),
        ("Q31: Quiz for Lecture 31", ct(4,15)),
        ("Q32: Quiz for Lecture 32", ct(4,17)),
        ("Q33: Quiz for Lecture 33", ct(4,20)),
        ("Q34: Quiz for Lecture 34", ct(4,22)),
        ("Q35: Quiz for Lecture 35", ct(4,24)),
        ("Q36: Quiz for Lecture 36", ct(4,27)),
        ("Q37: Quiz for Lecture 37", ct(4,29)),
        ("Q38: Quiz for Lecture 38", ct(5,4)),
        ("Q39: Quiz for Lecture 39", ct(5,6)),
    ]
    bioe_hws = [
        ("HW5: Homework 5",          ct(3,2)),
        ("HW6: Homework 6",          ct(3,6)),
        ("HW7: Homework 7: Worksheet", ct(3,13)),
        ("HW8: Homework 8",          ct(4,13)),
        ("HW9: Homework 9",          ct(4,27)),
        ("HW10: Homework 10",        ct(5,4)),
    ]
    for title, due in bioe_quizzes + bioe_hws:
        tasks.append(make_assignment(title, "BioE 210", due))

    # ── CS 128 Machine Problems (Canvas) ──────────────────────────────────────
    # ~every 2 weeks, released Friday, due Monday two weeks later
    cs128_mps = [
        ("MP2", ct(3,2)),
        ("MP3", ct(3,17)),   # estimated
        ("MP4", ct(3,31)),   # estimated
        ("MP5", ct(4,14)),   # estimated
        ("MP6", ct(4,28)),   # estimated
    ]
    for name, due in cs128_mps:
        tasks.append(make_assignment(f"CS 128 — {name}", "CS 128", due))

    # ── CS 173 Pre-unit Homework (Canvas) ─────────────────────────────────────
    # Released Thursday, due following Monday 11:59 PM
    cs173_preunits = [
        ("Pre-unit HW (due Feb 24)",  ct(2,24)),
        ("Pre-unit HW (due Mar 3)",   ct(3,3)),
        ("Pre-unit HW (due Mar 10)",  ct(3,10)),
        ("Pre-unit HW (due Mar 17)",  ct(3,17)),
        ("Pre-unit HW (due Mar 24)",  ct(3,24)),
        ("Pre-unit HW (due Mar 31)",  ct(3,31)),
        ("Pre-unit HW (due Apr 7)",   ct(4,7)),
        ("Pre-unit HW (due Apr 14)",  ct(4,14)),
        ("Pre-unit HW (due Apr 21)",  ct(4,21)),
        ("Pre-unit HW (due Apr 28)",  ct(4,28)),
        ("Pre-unit HW (due May 5)",   ct(5,5)),
    ]
    for title, due in cs173_preunits:
        tasks.append(make_assignment(title, "CS 173", due))

    # ── Math 285 (Canvas) ─────────────────────────────────────────────────────
    # Weekly HW + per-lecture quizzes (MWF, due before next class)
    math285_hws = [
        ("Math 285 — HW (due Mar 3)",   ct(3,3)),
        ("Math 285 — HW (due Mar 10)",  ct(3,10)),
        ("Math 285 — HW (due Mar 17)",  ct(3,17)),
        ("Math 285 — HW (due Mar 24)",  ct(3,24)),
        ("Math 285 — HW (due Mar 31)",  ct(3,31)),
        ("Math 285 — HW (due Apr 7)",   ct(4,7)),
        ("Math 285 — HW (due Apr 14)",  ct(4,14)),
        ("Math 285 — HW (due Apr 21)",  ct(4,21)),
        ("Math 285 — HW (due Apr 28)",  ct(4,28)),
        ("Math 285 — HW (due May 5)",   ct(5,5)),
    ]
    # MWF quizzes: due before next class (so Mon quiz due Wed 8am, Wed due Fri 8am, Fri due Mon 8am)
    # Generating from Feb 24 (Mon) through May 9
    math285_quizzes = []
    # MWF schedule: generate quiz due dates
    mwf_dates = []
    start = datetime(2025, 2, 24)
    end   = datetime(2025, 5, 9)
    d = start
    while d <= end:
        if d.weekday() in (0, 2, 4):  # Mon, Wed, Fri
            mwf_dates.append(d)
        d += timedelta(days=1)
    # skip spring break: Mar 15-23
    spring_break = {datetime(2025, 3, d) for d in range(15, 24)}
    mwf_dates = [d for d in mwf_dates if d not in spring_break]

    for i, lecture_day in enumerate(mwf_dates):
        # quiz due before NEXT class day
        if i + 1 < len(mwf_dates):
            next_class = mwf_dates[i + 1]
            due = CENTRAL_TZ.localize(datetime(next_class.year, next_class.month, next_class.day, 8, 0))
        else:
            due = CENTRAL_TZ.localize(datetime(2025, 5, 10, 23, 59))
        label = lecture_day.strftime("%b %d")
        math285_quizzes.append(make_assignment(f"Math 285 — Quiz (Lec {label})", "Math 285", due))

    for title, due in math285_hws:
        tasks.append(make_assignment(title, "Math 285", due))
    tasks.extend(math285_quizzes)

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
    # Remove past tasks not in fresh list
    for tid in list(updated.keys()):
        if tid not in fresh_ids:
            due = parse_iso(updated[tid]["due"])
            if due and due < now:
                del updated[tid]
    return updated

# ── Email ──────────────────────────────────────────────────────────────────────

def urgency_color(due):
    h = (due - now_ct()).total_seconds() / 3600
    if h < 24:  return "#e53e3e"
    if h < 72:  return "#dd6b20"
    if h < 168: return "#d69e2e"
    return "#38a169"

def urgency_label(due):
    h = int((due - now_ct()).total_seconds() / 3600)
    if h < 24:  return f"⚠️ {h}h left"
    d = h // 24
    if d == 1:  return "🔴 Tomorrow"
    if d <= 3:  return f"🟠 {d} days"
    if d <= 7:  return f"🟡 {d} days"
    return f"🟢 {d} days"

def make_table(items):
    if not items:
        return "<p style='color:#a0aec0;text-align:center;padding:16px;'>🎉 Nothing here!</p>"
    rows = ""
    for a in items:
        due   = parse_iso(a["due"])
        color = urgency_color(due)
        label = urgency_label(due)
        link  = f'<a href="{a["url"]}" style="color:#3182ce;text-decoration:none;">{a["title"]}</a>'
        bb    = "#ebf8ff" if a["source"] == "Canvas" else "#f0fff4"
        bc    = "#2b6cb0" if a["source"] == "Canvas" else "#276749"
        rows += f"""<tr>
          <td style="padding:9px 12px;border-bottom:1px solid #e2e8f0;">{link}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #e2e8f0;color:#718096;font-size:13px;">{a['course']}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:{color};white-space:nowrap;">{label}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #e2e8f0;color:#718096;font-size:13px;white-space:nowrap;">{due.strftime('%b %d %H:%M')}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #e2e8f0;">
            <span style="background:{bb};color:{bc};padding:2px 7px;border-radius:9999px;font-size:11px;">{a['source']}</span>
          </td></tr>"""
    return f"""<table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead><tr style="background:#f7fafc;">
        <th style="padding:9px 12px;text-align:left;color:#4a5568;font-size:13px;">Assignment</th>
        <th style="padding:9px 12px;text-align:left;color:#4a5568;font-size:13px;">Course</th>
        <th style="padding:9px 12px;text-align:left;color:#4a5568;font-size:13px;">Urgency</th>
        <th style="padding:9px 12px;text-align:left;color:#4a5568;font-size:13px;">Due (CT)</th>
        <th style="padding:9px 12px;text-align:left;color:#4a5568;font-size:13px;">Source</th>
      </tr></thead><tbody>{rows}</tbody></table>"""

def build_html(pending, is_monday):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in pending if parse_iso(a["due"]) <= week_end]
    later    = [a for a in pending if parse_iso(a["due"]) >  week_end]
    urgent   = [a for a in pending if (parse_iso(a["due"]) - today).total_seconds() < 86400]

    banner = ""
    if is_monday:
        bioe_today = [a for a in urgent if "BioE" in a["course"]]
        if bioe_today:
            banner = """<div style="background:#fff5f5;border-left:4px solid #e53e3e;
                        padding:12px 18px;margin-bottom:20px;border-radius:4px;">
                        <strong style="color:#c53030;">📅 今天是周一！</strong>
                        <span style="color:#742a2a;font-size:14px;"> BioE 210 作业今天截止，记得提交！</span></div>"""

    repo_user = "yvve77"  # GitHub username
    dash_url  = f"https://{repo_user}.github.io/DDL-collector"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:740px;margin:24px auto;background:white;border-radius:12px;
            box-shadow:0 1px 3px rgba(0,0,0,.1);overflow:hidden;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px 32px;">
    <h1 style="margin:0;color:white;font-size:20px;">☀️ Daily DDL Digest — {today.strftime('%A, %b %d')}</h1>
    <p style="margin:5px 0 0;color:rgba(255,255,255,.8);font-size:13px;">
      {len(pending)} pending · {len(urgent)} due within 24h</p>
  </div>
  <div style="display:flex;padding:16px 32px;background:#f8f9ff;border-bottom:1px solid #e2e8f0;gap:40px;">
    <div><div style="font-size:26px;font-weight:700;color:#667eea;">{len(pending)}</div>
         <div style="font-size:12px;color:#718096;">Pending</div></div>
    <div><div style="font-size:26px;font-weight:700;color:#e53e3e;">{len(soon)}</div>
         <div style="font-size:12px;color:#718096;">This week</div></div>
    <div><div style="font-size:26px;font-weight:700;color:#38a169;">{len(later)}</div>
         <div style="font-size:12px;color:#718096;">Later</div></div>
  </div>
  <div style="padding:20px 32px 32px;">
    {banner}
    <h2 style="color:#2d3748;font-size:15px;margin:0 0 8px;">🔥 Due This Week</h2>
    {make_table(soon)}
    <h2 style="color:#2d3748;font-size:15px;margin:28px 0 8px;">📆 Coming Up Later</h2>
    {make_table(later)}
    <p style="margin-top:24px;font-size:13px;color:#a0aec0;text-align:center;">
      ✅ Mark tasks done on your <a href="{dash_url}" style="color:#667eea;">DDL Dashboard</a>
      — completed items won't appear in future emails.
    </p>
  </div>
  <div style="padding:14px 32px;background:#f7fafc;border-top:1px solid #e2e8f0;
              text-align:center;color:#a0aec0;font-size:12px;">
    Auto-generated {today.strftime('%Y-%m-%d %H:%M %Z')} · BioE 210 · CS 128 · CS 173 · Math 285
  </div>
</div></body></html>"""

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
        print(f"   {parse_iso(t['due']).strftime('%m/%d')} {t['course']} — {t['title']}")
    if len(pending) > 5:
        print(f"   ... and {len(pending)-5} more")

    if not pending:
        print("Nothing pending, skipping email."); return

    urgent_count = len([t for t in pending if (parse_iso(t["due"]) - today).total_seconds() < 86400])
    if is_monday:
        subject = f"📅 周一DDL提醒 — {today.strftime('%b %d')} ({len(pending)} pending)"
    elif urgent_count:
        subject = f"⚠️ {urgent_count} due within 24h — {today.strftime('%a %b %d')}"
    else:
        subject = f"☀️ DDL Digest — {today.strftime('%a %b %d')} ({len(pending)} pending)"

    html = build_html(pending, is_monday)
    send_email(html, subject)

if __name__ == "__main__":
    main()
