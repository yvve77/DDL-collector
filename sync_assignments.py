#!/usr/bin/env python3
"""
Assignment DDL Digest
- PrairieLearn: auto-fetched via API
- BioE 210: auto-generated weekly schedule
- Sends daily HTML email (Monday = special reminder)
- Skips tasks marked as completed in tasks.json
"""

import os, sys, json, requests, smtplib, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

# ── Config ─────────────────────────────────────────────────────────────────────
PL_TOKEN            = os.environ["PL_TOKEN"]
GMAIL_ADDRESS       = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD  = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL            = os.environ["TO_EMAIL"]

PL_BASE             = "https://us.prairielearn.com"
PL_COURSE_INSTANCES = [203794, 205972, 143407]
CENTRAL_TZ          = pytz.timezone("America/Chicago")
TASKS_FILE          = "tasks.json"

# BioE 210: every Monday 11:59 PM CT, from now until May 10
BIOE_COURSE         = "BioE 210"
BIOE_DDL_TIME       = "23:59"
SEMESTER_END        = datetime(2025, 5, 10, tzinfo=pytz.timezone("America/Chicago"))

# ── Helpers ────────────────────────────────────────────────────────────────────

def now_ct():
    return datetime.now(CENTRAL_TZ)

def parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(CENTRAL_TZ)

def task_id(title, due: datetime):
    """Stable unique ID for a task."""
    safe = re.sub(r"[^a-z0-9]", "_", title.lower())
    return f"{safe}__{due.strftime('%Y%m%d')}"

# ── BioE 210 schedule generator ────────────────────────────────────────────────

def generate_bioe_assignments():
    """Return one BioE 210 assignment per Monday from today until May 10."""
    results = []
    today = now_ct().date()
    # find next Monday (or today if Monday)
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # always next Monday, not today
    current = today + timedelta(days=days_until_monday)

    week = 1
    while True:
        due_naive = datetime.combine(current, datetime.strptime(BIOE_DDL_TIME, "%H:%M").time())
        due = CENTRAL_TZ.localize(due_naive)
        if due > SEMESTER_END:
            break
        results.append({
            "id":     task_id(f"bioe210_hw{week}", due),
            "title":  f"BioE 210 — Weekly Assignment (Week {week})",
            "course": BIOE_COURSE,
            "due":    due,
            "source": "Canvas",
            "url":    "https://canvas.illinois.edu",
        })
        current += timedelta(weeks=1)
        week += 1
    return results

# ── PrairieLearn ───────────────────────────────────────────────────────────────

def fetch_pl():
    print("📝 Fetching PrairieLearn...")
    headers = {"Private-Token": PL_TOKEN}
    results = []
    for cid in PL_COURSE_INSTANCES:
        url = f"{PL_BASE}/pl/api/v1/course_instances/{cid}/assessments"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 401:
                print(f"  ⚠️  Course {cid}: unauthorized"); continue
            r.raise_for_status()
            for a in r.json():
                due_str = a.get("close_date") or a.get("closeDate") or a.get("close_at")
                due = parse_iso(due_str) if due_str else None
                if due and due > now_ct():
                    title = a.get("title") or a.get("label", "Untitled")
                    results.append({
                        "id":     task_id(title, due),
                        "title":  title,
                        "course": f"PL-{cid}",
                        "due":    due,
                        "source": "PrairieLearn",
                        "url":    f"{PL_BASE}/pl/course_instance/{cid}/assessment/{a.get('assessment_id','')}",
                    })
            print(f"  ✅ Course {cid}: ok")
        except Exception as e:
            print(f"  ❌ Course {cid}: {e}")
    return results

# ── Task state (tasks.json) ────────────────────────────────────────────────────

def load_tasks():
    """Load existing tasks from tasks.json (in repo root)."""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {}

def save_tasks(tasks: dict):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2, default=str)

def merge_tasks(existing: dict, fresh_assignments: list) -> dict:
    """Add new assignments; preserve completed status for existing ones."""
    updated = dict(existing)
    for a in fresh_assignments:
        tid = a["id"]
        if tid not in updated:
            updated[tid] = {
                "id":        tid,
                "title":     a["title"],
                "course":    a["course"],
                "due":       a["due"].isoformat(),
                "source":    a["source"],
                "url":       a["url"],
                "completed": False,
            }
        else:
            # keep completed flag, but refresh metadata
            updated[tid].update({
                "title":  a["title"],
                "course": a["course"],
                "due":    a["due"].isoformat(),
                "url":    a["url"],
            })
    # Remove tasks that are past due AND not in fresh list (auto-cleanup)
    fresh_ids = {a["id"] for a in fresh_assignments}
    now = now_ct()
    to_remove = [
        tid for tid, t in updated.items()
        if tid not in fresh_ids and parse_iso(t["due"]) and parse_iso(t["due"]) < now
    ]
    for tid in to_remove:
        del updated[tid]
    return updated

# ── Email builder ──────────────────────────────────────────────────────────────

def urgency_color(due: datetime):
    days = (due - now_ct()).days
    if days < 1:  return "#e53e3e"
    if days <= 3: return "#dd6b20"
    if days <= 7: return "#d69e2e"
    return "#38a169"

def urgency_label(due: datetime):
    delta = due - now_ct()
    hours = int(delta.total_seconds() // 3600)
    if hours < 24:      return f"⚠️ {hours}h left"
    if delta.days == 1: return "🔴 Tomorrow"
    if delta.days <= 3: return f"🟠 {delta.days} days"
    if delta.days <= 7: return f"🟡 {delta.days} days"
    return f"🟢 {delta.days} days"

def make_table(items):
    if not items:
        return "<p style='color:#a0aec0;text-align:center;padding:20px 0;'>🎉 Nothing here!</p>"

    rows = ""
    for a in items:
        due = parse_iso(a["due"])
        color = urgency_color(due)
        label = urgency_label(due)
        link  = f'<a href="{a["url"]}" style="color:#3182ce;text-decoration:none;">{a["title"]}</a>' if a.get("url") else a["title"]
        badge_bg    = "#ebf8ff" if a["source"] == "Canvas" else "#f0fff4"
        badge_color = "#2b6cb0" if a["source"] == "Canvas" else "#276749"
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">{link}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#718096;font-size:13px;">{a['course']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:{color};">{label}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#718096;font-size:13px;">{due.strftime('%b %d, %H:%M')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">
            <span style="background:{badge_bg};color:{badge_color};padding:2px 8px;border-radius:9999px;font-size:12px;">{a['source']}</span>
          </td>
        </tr>"""

    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead>
        <tr style="background:#f7fafc;">
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Assignment</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Course</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Urgency</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Due (CT)</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Source</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""

def build_html(pending: list, is_monday: bool):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in pending if parse_iso(a["due"]) <= week_end]
    later    = [a for a in pending if parse_iso(a["due"]) >  week_end]
    due_today = [a for a in pending if (parse_iso(a["due"]) - today).days < 1]

    monday_banner = ""
    if is_monday:
        monday_banner = """
        <div style="background:#fff5f5;border-left:4px solid #e53e3e;padding:14px 20px;margin-bottom:20px;border-radius:4px;">
          <strong style="color:#c53030;">📅 今天是周一！</strong>
          <span style="color:#742a2a;font-size:14px;"> BioE 210 作业今天截止，记得提交！</span>
        </div>"""

    title    = f"☀️ Daily DDL Digest — {today.strftime('%A, %b %d')}"
    subtitle = f"{len(pending)} pending assignments · {len(due_today)} due within 24h"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:740px;margin:24px auto;background:white;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;">

    <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:24px 32px;">
      <h1 style="margin:0;color:white;font-size:20px;">{title}</h1>
      <p style="margin:5px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">{subtitle}</p>
    </div>

    <div style="display:flex;padding:16px 32px;background:#f8f9ff;border-bottom:1px solid #e2e8f0;gap:40px;">
      <div><div style="font-size:26px;font-weight:700;color:#667eea;">{len(pending)}</div><div style="font-size:12px;color:#718096;">Pending</div></div>
      <div><div style="font-size:26px;font-weight:700;color:#e53e3e;">{len(soon)}</div><div style="font-size:12px;color:#718096;">This week</div></div>
      <div><div style="font-size:26px;font-weight:700;color:#38a169;">{len(later)}</div><div style="font-size:12px;color:#718096;">Later</div></div>
    </div>

    <div style="padding:20px 32px 32px;">
      {monday_banner}
      <h2 style="color:#2d3748;font-size:15px;margin:0 0 8px;">🔥 Due This Week</h2>
      {make_table(soon)}
      <h2 style="color:#2d3748;font-size:15px;margin:28px 0 8px;">📆 Coming Up Later</h2>
      {make_table(later)}
      <p style="margin-top:24px;font-size:13px;color:#a0aec0;text-align:center;">
        ✅ Mark tasks complete on your
        <a href="https://yvetteq2.github.io/assignment-ddl-digest" style="color:#667eea;">DDL Dashboard</a>
        — completed tasks won't appear in future emails.
      </p>
    </div>

    <div style="padding:14px 32px;background:#f7fafc;border-top:1px solid #e2e8f0;text-align:center;color:#a0aec0;font-size:12px;">
      Auto-generated {today.strftime('%Y-%m-%d %H:%M %Z')} · PrairieLearn + Canvas (BioE 210)
    </div>
  </div>
</body></html>"""

# ── Send email ─────────────────────────────────────────────────────────────────

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
    today      = now_ct()
    is_monday  = today.weekday() == 0

    # Gather all assignments
    all_assignments = fetch_pl() + generate_bioe_assignments()
    print(f"📋 Total fetched: {len(all_assignments)}")

    # Merge with saved task state
    existing = load_tasks()
    merged   = merge_tasks(existing, all_assignments)
    save_tasks(merged)
    print(f"💾 tasks.json updated ({len(merged)} tasks)")

    # Only email pending (not completed) tasks
    pending = sorted(
        [t for t in merged.values() if not t["completed"] and parse_iso(t["due"]) > today],
        key=lambda x: x["due"]
    )
    print(f"📬 Pending (unsent): {len(pending)}")

    if not pending:
        print("Nothing pending, skipping email."); return

    html = build_html(pending, is_monday)

    due_today_count = len([t for t in pending if (parse_iso(t["due"]) - today).days < 1])
    if is_monday:
        subject = f"📅 周一DDL提醒 — BioE 210今天截止！ {today.strftime('%b %d')}"
    elif due_today_count:
        subject = f"⚠️ {due_today_count} assignment(s) due soon — {today.strftime('%a %b %d')}"
    else:
        subject = f"☀️ Daily DDL Digest — {today.strftime('%a %b %d')} ({len(pending)} pending)"

    send_email(html, subject)

if __name__ == "__main__":
    main()
