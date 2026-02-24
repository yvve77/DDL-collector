#!/usr/bin/env python3
"""
Assignment DDL Email Digest
Fetches assignments from Canvas (UIUC) + PrairieLearn, sends HTML email summary.
"""

import os
import sys
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pytz

# ── Configuration ──────────────────────────────────────────────────────────────
CANVAS_TOKEN   = os.environ["CANVAS_TOKEN"]
PL_TOKEN       = os.environ.get("PL_TOKEN", "")
GMAIL_ADDRESS  = os.environ["GMAIL_ADDRESS"]       # your Gmail (sender)
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASSWORD"]  # Gmail App Password
TO_EMAIL       = os.environ["TO_EMAIL"]            # your @illinois.edu

CANVAS_BASE         = "https://canvas.illinois.edu/api/v1"
PL_BASE             = "https://us.prairielearn.com"
PL_COURSE_INSTANCES = [203794, 205972, 143407]
CENTRAL_TZ          = pytz.timezone("America/Chicago")

# ── Helpers ────────────────────────────────────────────────────────────────────

def now_ct():
    return datetime.now(CENTRAL_TZ)

def parse_iso(dt_str):
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt.astimezone(CENTRAL_TZ)

# ── Canvas ─────────────────────────────────────────────────────────────────────

def paginated_get(url, headers):
    results = []
    while url:
        r = requests.get(url, headers=headers, timeout=15)
        if not r.ok:
            break
        results.extend(r.json())
        url = None
        for part in r.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    return results

def fetch_all_canvas():
    print("📚 Fetching Canvas...")
    headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}
    try:
        courses = paginated_get(f"{CANVAS_BASE}/courses?enrollment_state=active&per_page=50", headers)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    results = []
    for c in courses:
        if not isinstance(c, dict) or not c.get("id"):
            continue
        name = c.get("course_code") or c.get("name", f"Course {c['id']}")
        try:
            assignments = paginated_get(
                f"{CANVAS_BASE}/courses/{c['id']}/assignments?per_page=50&order_by=due_at",
                headers
            )
            for a in assignments:
                due = parse_iso(a.get("due_at"))
                if due and due > now_ct():
                    results.append({
                        "title": a["name"],
                        "course": name,
                        "due": due,
                        "source": "Canvas",
                        "url": a.get("html_url", ""),
                    })
        except Exception:
            continue

    print(f"  ✅ {len(results)} upcoming")
    return results

# ── PrairieLearn ───────────────────────────────────────────────────────────────

def fetch_all_pl():
    print("📝 Fetching PrairieLearn...")
    headers = {"Private-Token": PL_TOKEN} if PL_TOKEN else {}
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
                    results.append({
                        "title": a.get("title") or a.get("label", "Untitled"),
                        "course": f"PL-{cid}",
                        "due": due,
                        "source": "PrairieLearn",
                        "url": f"{PL_BASE}/pl/course_instance/{cid}/assessment/{a.get('assessment_id','')}",
                    })
        except Exception as e:
            print(f"  ❌ Course {cid}: {e}")
    print(f"  ✅ {len(results)} upcoming")
    return results

# ── Email HTML builder ─────────────────────────────────────────────────────────

def urgency_color(due: datetime):
    days = (due - now_ct()).days
    if days <= 1:  return "#e53e3e"
    if days <= 3:  return "#dd6b20"
    if days <= 7:  return "#d69e2e"
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
    header = """
    <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;">
      <thead>
        <tr style="background:#f7fafc;">
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Assignment</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Course</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Urgency</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Due Date (CT)</th>
          <th style="padding:10px 12px;text-align:left;color:#4a5568;">Source</th>
        </tr>
      </thead><tbody>"""

    if not items:
        return header + "<tr><td colspan='5' style='padding:20px;text-align:center;color:#a0aec0;'>🎉 Nothing here!</td></tr></tbody></table>"

    rows = ""
    for a in items:
        color = urgency_color(a["due"])
        label = urgency_label(a["due"])
        link  = f'<a href="{a["url"]}" style="color:#3182ce;text-decoration:none;">{a["title"]}</a>' if a["url"] else a["title"]
        badge_bg    = "#ebf8ff" if a["source"] == "Canvas" else "#f0fff4"
        badge_color = "#2b6cb0" if a["source"] == "Canvas" else "#276749"
        rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">{link}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#718096;">{a['course']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:{color};">{label}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#718096;">{a['due'].strftime('%b %d, %H:%M')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">
            <span style="background:{badge_bg};color:{badge_color};padding:2px 8px;border-radius:9999px;font-size:12px;">{a['source']}</span>
          </td>
        </tr>"""

    return header + rows + "</tbody></table>"

def build_html(assignments, mode):
    today    = now_ct()
    week_end = today + timedelta(days=7)
    soon     = [a for a in assignments if a["due"] <= week_end]
    later    = [a for a in assignments if a["due"] >  week_end]

    if mode == "weekly":
        title    = f"📅 Weekly Assignment Digest — Week of {today.strftime('%b %d')}"
        subtitle = "All upcoming assignments sorted by due date"
        sections = f"""
        <h2 style="color:#2d3748;font-size:15px;margin:24px 0 4px;">🔥 Due This Week ({len(soon)})</h2>
        {make_table(soon)}
        <h2 style="color:#2d3748;font-size:15px;margin:32px 0 4px;">📆 Coming Up Later ({len(later)})</h2>
        {make_table(later)}"""
    else:
        title    = f"☀️ Daily DDL Digest — {today.strftime('%A, %b %d')}"
        subtitle = "Stay on top of your deadlines"
        sections = f"""
        <h2 style="color:#2d3748;font-size:15px;margin:24px 0 4px;">🔥 Due This Week ({len(soon)})</h2>
        {make_table(soon)}
        <h2 style="color:#2d3748;font-size:15px;margin:32px 0 4px;">📆 Coming Up Later ({len(later)})</h2>
        {make_table(later)}"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f7fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:740px;margin:32px auto;background:white;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;">

    <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:28px 32px;">
      <h1 style="margin:0;color:white;font-size:22px;">{title}</h1>
      <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">{subtitle}</p>
    </div>

    <div style="display:flex;padding:20px 32px;background:#f8f9ff;border-bottom:1px solid #e2e8f0;gap:40px;">
      <div><div style="font-size:26px;font-weight:700;color:#667eea;">{len(assignments)}</div><div style="font-size:12px;color:#718096;">Total upcoming</div></div>
      <div><div style="font-size:26px;font-weight:700;color:#e53e3e;">{len(soon)}</div><div style="font-size:12px;color:#718096;">Due this week</div></div>
      <div><div style="font-size:26px;font-weight:700;color:#38a169;">{len(later)}</div><div style="font-size:12px;color:#718096;">Later</div></div>
    </div>

    <div style="padding:8px 32px 32px;">{sections}</div>

    <div style="padding:16px 32px;background:#f7fafc;border-top:1px solid #e2e8f0;text-align:center;color:#a0aec0;font-size:12px;">
      Auto-generated {today.strftime('%Y-%m-%d %H:%M %Z')} · Canvas (UIUC) + PrairieLearn
    </div>
  </div>
</body></html>"""

# ── Send email ─────────────────────────────────────────────────────────────────

def send_email(html_body, subject):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL, msg.as_string())
    print(f"✅ Email sent to {TO_EMAIL}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    mode  = sys.argv[1] if len(sys.argv) > 1 else "daily"
    today = now_ct()
    print(f"Mode: {mode} | {today.strftime('%Y-%m-%d %H:%M %Z')}")

    assignments = sorted(fetch_all_canvas() + fetch_all_pl(), key=lambda x: x["due"])
    print(f"\n📋 Total: {len(assignments)} upcoming assignments")

    html = build_html(assignments, mode)

    due_soon = len([a for a in assignments if (a["due"] - today).total_seconds() < 86400])
    if mode == "weekly":
        subject = f"📅 Weekly Assignment Digest — {today.strftime('%b %d')}"
    else:
        urgency = f"⚠️ {due_soon} due within 24h! — " if due_soon else ""
        subject = f"☀️ {urgency}Daily DDL — {today.strftime('%a %b %d')}"

    send_email(html, subject)

if __name__ == "__main__":
    main()
