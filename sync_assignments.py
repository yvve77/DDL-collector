#!/usr/bin/env python3
"""
Assignment DDL Digest
All assignments hardcoded. Sends daily HTML email, skips completed tasks.
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
    "BioE 210": {"bg": "#fff5eb", "text": "#c05621"},
    "CS 128":   {"bg": "#ebf8ff", "text": "#2b6cb0"},
    "CS 173":   {"bg": "#f0fff4", "text": "#276749"},
    "Math 285": {"bg": "#faf5ff", "text": "#6b46c1"},
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
    return f"{safe}__{due.strftime('%Y%m%d')}"

def canvas(title, course, due):
    return {"title": title, "course": course, "due": due,
            "source": "Canvas", "url": "https://canvas.illinois.edu"}

def pl(title, course, due):
    return {"title": title, "course": course, "due": due,
            "source": "PrairieLearn", "url": "https://us.prairielearn.com"}

# ── All assignments ────────────────────────────────────────────────────────────

def all_assignments():
    tasks = []

    # ── BioE 210 — Canvas — Weekly HW only, HW1-4 already done ───────────────
    for num, due in [
        (5,  ct(3,3)),  (6,  ct(3,10)), (7,  ct(3,17)), (8,  ct(3,24)),
        (9,  ct(3,31)), (10, ct(4,7)),  (11, ct(4,14)), (12, ct(4,21)),
        (13, ct(4,28)), (14, ct(5,5)),
    ]:
        tasks.append(canvas(f"HW {num}", "BioE 210", due))

    # ── CS 128 — PrairieLearn — Machine Problems every ~2 weeks ──────────────
    for name, due in [
        ("MP2", ct(3,2)),  ("MP3", ct(3,17)), ("MP4", ct(3,31)),
        ("MP5", ct(4,14)), ("MP6", ct(4,28)),
    ]:
        tasks.append(pl(name, "CS 128", due))

    # ── CS 173 — PrairieLearn — Pre-unit HW, due every Monday ────────────────
    for due in [
        ct(3,3),  ct(3,10), ct(3,17), ct(3,24), ct(3,31),
        ct(4,7),  ct(4,14), ct(4,21), ct(4,28), ct(5,5),
    ]:
        tasks.append(pl("Pre-unit HW", "CS 173", due))

    # ── Math 285 — PrairieLearn — Weekly HW + per-lecture Quiz ───────────────
    for due in [
        ct(3,3),  ct(3,10), ct(3,17), ct(3,24), ct(3,31),
        ct(4,7),  ct(4,14), ct(4,21), ct(4,28), ct(5,5),
    ]:
        tasks.append(pl("Weekly HW", "Math 285", due))

    for title, due in [
        ("Quiz — Lecture 14", ct(2,25)), ("Quiz — Lecture 15", ct(2,27)),
        ("Quiz — Lecture 16", ct(3,2)),  ("Quiz — Lecture 17", ct(3,4)),
        ("Quiz — Lecture 18", ct(3,6)),  ("Quiz — Lecture 19", ct(3,9)),
        ("Quiz — Lecture 20", ct(3,11)), ("Quiz — Lecture 21", ct(3,13)),
        ("Quiz — Lecture 22", ct(3,23)), ("Quiz — Lecture 23", ct(3,25)),
        ("Quiz — Lecture 24", ct(3,30)), ("Quiz — Lecture 25", ct(4,1)),
        ("Quiz — Lecture 26", ct(4,3)),  ("Quiz — Lecture 27", ct(4,6)),
        ("Quiz — Lecture 28", ct(4,8)),  ("Quiz — Lecture 29", ct(4,10)),
        ("Quiz — Lecture 30", ct(4,13)), ("Quiz — Lecture 31", ct(4,15)),
        ("Quiz — Lecture 32", ct(4,17)), ("Quiz — Lecture 33", ct(4,20)),
        ("Quiz — Lecture 34", ct(4,22)), ("Quiz — Lecture 35", ct(4,24)),
        ("Quiz — Lecture 36", ct(4,27)), ("Quiz — Lecture 37", ct(4,29)),
        ("Quiz — Lecture 38", ct(5,4)),  ("Quiz — Lecture 39", ct(5,6)),
    ]:
        tasks.append(pl(title, "Math 285", due))

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
        sb = "#ebf8ff" if a["source"] == "Canvas" else "#f0fff4"
        sc = "#2b6cb0" if a["source"] == "Canvas" else "#276749"
        rows += f"""
        <tr>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <a href="{a['url']}" style="color:#2d3748;text-decoration:none;font-weight:500;font-size:14px;">{a['title']}</a>
          </td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <span style="background:{cc['bg']};color:{cc['text']};padding:3px 9px;
                         border-radius:9999px;font-size:12px;font-weight:500;white-space:nowrap;">{a['course']}</span>
          </td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;
                     font-weight:600;color:{uc};font-size:13px;white-space:nowrap;">{ul}</td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;
                     color:#718096;font-size:13px;white-space:nowrap;">{due.strftime('%b %d, %I:%M %p')}</td>
          <td style="padding:11px 14px;border-bottom:1px solid #edf2f7;">
            <span style="background:{sb};color:{sc};padding:3px 9px;
                         border-radius:9999px;font-size:11px;">{a['source']}</span>
          </td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;">
      <thead>
        <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
          <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Assignment</th>
          <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Course</th>
          <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Urgency</th>
          <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Due</th>
          <th style="padding:10px 14px;text-align:left;color:#718096;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Platform</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""

def build_html(pending, is_monday):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in pending if parse_iso(a["due"]) <= week_end]
    later    = [a for a in pending if parse_iso(a["due"]) >  week_end]
    urgent   = [a for a in pending if (parse_iso(a["due"]) - today).total_seconds() < 86400]

    banner = ""
    if is_monday:
        banner = """
        <div style="background:#fff5f5;border:1px solid #fed7d7;border-radius:10px;
                    padding:14px 18px;margin-bottom:24px;display:flex;align-items:center;gap:12px;">
          <span style="font-size:22px;">📅</span>
          <div>
            <div style="font-weight:700;color:#c53030;font-size:14px;">今天是周一！</div>
            <div style="color:#742a2a;font-size:13px;margin-top:2px;">BioE 210 Weekly HW 今天截止，记得提交！</div>
          </div>
        </div>"""

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
          <h2 style="color:#2d3748;font-size:14px;font-weight:700;margin:0 0 12px;
                     padding-bottom:8px;border-bottom:2px solid #edf2f7;display:flex;
                     align-items:center;gap:6px;">
            {icon} {title}
            <span style="color:#a0aec0;font-size:13px;font-weight:400;margin-left:4px;">({n})</span>
          </h2>
          {make_table(items)}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:720px;margin:28px auto;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">

  <div style="background:linear-gradient(135deg,#5a67d8,#805ad5);padding:28px 32px;">
    <div style="font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Daily Digest</div>
    <h1 style="margin:0;color:white;font-size:24px;font-weight:700;letter-spacing:-0.5px;">{today.strftime('%A, %B %d')}</h1>
    <p style="margin:7px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">{len(pending)} pending · {len(urgent)} due within 24h</p>
  </div>

  <div style="background:white;border-bottom:1px solid #e2e8f0;padding:16px 32px;display:flex;align-items:center;">
    <div style="display:flex;gap:28px;flex:1;">
      <div style="text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#5a67d8;line-height:1;">{len(pending)}</div>
        <div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">Total</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#e53e3e;line-height:1;">{len(soon)}</div>
        <div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">This week</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#38a169;line-height:1;">{len(later)}</div>
        <div style="font-size:11px;color:#a0aec0;margin-top:3px;text-transform:uppercase;letter-spacing:0.05em;">Later</div>
      </div>
    </div>
    <div style="text-align:right;">{pills}</div>
  </div>

  <div style="background:white;padding:24px 32px 12px;">
    {banner}
    {sec("Due This Week", soon, "🔥")}
    {sec("Coming Up Later", later, "📆")}
  </div>

  <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:14px 32px;
              display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:12px;color:#a0aec0;">Auto-synced {today.strftime('%b %d %H:%M %Z')}</span>
    <a href="{DASH_URL}" style="background:#5a67d8;color:white;text-decoration:none;
       padding:7px 16px;border-radius:8px;font-size:12px;font-weight:600;letter-spacing:0.02em;">
      ✅ Open Dashboard →
    </a>
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
        print(f"   {parse_iso(t['due']).strftime('%m/%d')} [{t['course']}] {t['title']}")
    if len(pending) > 5:
        print(f"   ... and {len(pending)-5} more")

    if not pending:
        print("Nothing pending, skipping email."); return

    urgent_count = len([t for t in pending if (parse_iso(t["due"]) - today).total_seconds() < 86400])
    if is_monday:
        subject = f"📅 周一提醒 — {today.strftime('%b %d')} · {len(pending)} pending"
    elif urgent_count:
        subject = f"⚠️ {urgent_count} due within 24h — {today.strftime('%a %b %d')}"
    else:
        subject = f"☀️ DDL Digest — {today.strftime('%a %b %d')} · {len(pending)} pending"

    send_email(build_html(pending, is_monday), subject)

if __name__ == "__main__":
    main()
