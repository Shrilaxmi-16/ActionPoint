import json
import os
import datetime
from typing import Optional, List, Dict, Any
from app.storage import get_db, save_meeting_data
from google import genai
from google.genai import types

def confirm_and_save_meeting(
    title: str,
    summary: str,
    meeting_date: str = "",
    project: str = "General",
    attendees_json: str = "[]",
    decisions_json: str = "[]",
    action_items_json: str = "[]",
    open_questions_json: str = "[]",
    transcript_text: str = ""
) -> str:
    """Saves confirmed meeting data, decisions, action items, and open questions to the database."""
    try:
        attendees = json.loads(attendees_json) if isinstance(attendees_json, str) else attendees_json
        decisions = json.loads(decisions_json) if isinstance(decisions_json, str) else decisions_json
        action_items = json.loads(action_items_json) if isinstance(action_items_json, str) else action_items_json
        open_questions = json.loads(open_questions_json) if isinstance(open_questions_json, str) else open_questions_json
    except Exception as e:
        return f"Error parsing input JSON: {str(e)}"

    if not meeting_date:
        meeting_date = datetime.date.today().isoformat()

    meeting_id = save_meeting_data(
        title=title,
        meeting_date=meeting_date,
        summary=summary,
        attendees=attendees,
        decisions=decisions,
        action_items=action_items,
        open_questions=open_questions,
        transcript_text=transcript_text,
        project=project
    )
    return f"Successfully saved meeting '{title}' (ID: {meeting_id}) with {len(action_items)} action items, {len(decisions)} decisions, and {len(open_questions)} open questions."

def query_action_items(
    project: Optional[str] = None,
    owner: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False
) -> str:
    """Queries action items filtered by project, owner, status, or overdue flag."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM action_items WHERE 1=1"
    params = []

    if project:
        query += " AND LOWER(project) LIKE ?"
        params.append(f"%{project.lower()}%")
    if owner:
        query += " AND LOWER(owner) LIKE ?"
        params.append(f"%{owner.lower()}%")
    if status:
        query += " AND LOWER(status) = ?"
        params.append(status.lower())

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    items = [dict(r) for r in rows]
    return json.dumps(items, indent=2)

def update_action_item_status(item_id: str, new_status: str) -> str:
    """Updates the status of a specific action item."""
    valid_statuses = {"pending", "in_progress", "blocked", "done"}
    if new_status.lower() not in valid_statuses:
        return f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE action_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status.lower(), item_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return f"Action item '{item_id}' not found."
    return f"Action item '{item_id}' status updated to '{new_status}'."

def generate_follow_up_agenda(meeting_id_or_project: str = "") -> str:
    """Generates a structured, professional follow-up meeting agenda focusing on open questions, blocked tasks, and priority items."""
    conn = get_db()
    cursor = conn.cursor()

    if meeting_id_or_project:
        cursor.execute(
            "SELECT * FROM open_questions WHERE status != 'resolved' AND (meeting_id = ? OR meeting_id IN (SELECT id FROM meetings WHERE LOWER(project) LIKE ? OR LOWER(title) LIKE ?))",
            (meeting_id_or_project, f"%{meeting_id_or_project.lower()}%", f"%{meeting_id_or_project.lower()}%")
        )
        questions = cursor.fetchall()

        cursor.execute(
            "SELECT * FROM action_items WHERE status IN ('pending', 'blocked', 'in_progress') AND (meeting_id = ? OR LOWER(project) LIKE ?)",
            (meeting_id_or_project, f"%{meeting_id_or_project.lower()}%")
        )
        items = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM open_questions WHERE status != 'resolved' ORDER BY created_at DESC LIMIT 10")
        questions = cursor.fetchall()
        cursor.execute("SELECT * FROM action_items WHERE status IN ('pending', 'blocked', 'in_progress') ORDER BY created_at DESC LIMIT 15")
        items = cursor.fetchall()

    conn.close()

    target_name = meeting_id_or_project if meeting_id_or_project else "Active Projects"
    
    agenda = f"# 📋 Follow-Up Sync Agenda: {target_name}\n\n"
    agenda += f"**Date:** {datetime.date.today().strftime('%B %d, %Y')} | **Meeting Purpose:** Progress review, blocker removal, and upcoming deliverable alignment.\n\n"
    agenda += "---\n\n"
    
    agenda += "### 1. In-Flight Tasks & Ownership Check (15 Mins)\n"
    if items:
        agenda += "| Status | Priority | Task Description | Assignee | Deadline |\n"
        agenda += "| :--- | :--- | :--- | :--- | :--- |\n"
        for it in items:
            p_badge = f"`{it['priority'].upper()}`" if it['priority'] else "`MED`"
            s_badge = f"**{it['status'].capitalize()}**"
            agenda += f"| {s_badge} | {p_badge} | {it['title']} | **{it['owner']}** | {it['due_date']} |\n"
    else:
        agenda += "*All action items are completed or none recorded.*\n"

    agenda += "\n### 2. Unresolved Questions & Technical Decisions (20 Mins)\n\n"
    if questions:
        agenda += "| # | Discussion Question / Technical Blocker | Lead Investigator | Status |\n"
        agenda += "| :-: | :--- | :--- | :-: |\n"
        for idx, q in enumerate(questions, 1):
            q_status = f"`{q['status'].upper()}`"
            agenda += f"| **Q{idx}** | ❓ {q['question']} | **{q['assigned_to']}** | {q_status} |\n"
    else:
        agenda += "*No unresolved questions logged for this topic.*\n"

    agenda += "\n### 3. Blockers, Risks & Open Floor (10 Mins)\n"
    agenda += "* Go-around for any team member to raise new external dependencies, timeline risks, or technical debt.\n\n"
    agenda += "---\n*Generated by ActionPoint Agenda Intelligence*"
    return agenda

def draft_follow_up_email(meeting_id_or_title: str = "", project: str = "") -> str:
    """Drafts an executive, beautifully formatted general recap email scoped by project or specific meeting."""
    conn = get_db()
    cursor = conn.cursor()

    if meeting_id_or_title:
        cursor.execute(
            "SELECT * FROM meetings WHERE id = ? OR LOWER(title) LIKE ? ORDER BY created_at DESC LIMIT 1",
            (meeting_id_or_title, f"%{meeting_id_or_title.lower()}%")
        )
    elif project and project != "ALL":
        cursor.execute(
            "SELECT * FROM meetings WHERE LOWER(project) LIKE ? ORDER BY created_at DESC LIMIT 1",
            (f"%{project.lower()}%",)
        )
    else:
        cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
        
    meeting_raw = cursor.fetchone()
    if not meeting_raw:
        conn.close()
        return "No meetings found in database. Please ingest and confirm a meeting first."
    meeting = dict(meeting_raw)

    meeting_id = meeting["id"]
    cursor.execute("SELECT * FROM decisions WHERE meeting_id = ?", (meeting_id,))
    decisions = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM action_items WHERE meeting_id = ?", (meeting_id,))
    action_items = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM open_questions WHERE meeting_id = ?", (meeting_id,))
    questions = [dict(r) for r in cursor.fetchall()]
    conn.close()

    attendees = json.loads(meeting["attendees"]) if meeting.get("attendees") else []

    email = f"**Subject:** 📌 [{meeting.get('project', 'Project')} Recap & Action Items] {meeting['title']} — {meeting['meeting_date']}\n"
    email += f"**To:** {', '.join(attendees) if attendees else 'All Meeting Attendees'}\n"
    email += f"**Project Team:** {meeting.get('project', 'General')}\n\n"
    email += "---\n\n"
    email += f"Hi {meeting.get('project', 'Team')} Team,\n\nThank you for participating in our sync on **{meeting['meeting_date']}**. Below is the executive recap, confirmed decisions, and clear next steps:\n\n"
    
    email += "### 📝 Executive Summary\n"
    email += f"{meeting['summary']}\n\n"

    if decisions:
        email += "### 🎯 Key Decisions Made\n"
        for d in decisions:
            email += f"* **{d['decision']}**\n  * *Context/Rationale:* {d['context']}\n  * *Owner:* {d['made_by']}\n"
        email += "\n"

    if action_items:
        email += "### 🚀 Action Items & Deliverables\n\n"
        email += "| Priority | Action Item | Assignee | Due Date | Status |\n"
        email += "| :--- | :--- | :--- | :--- | :--- |\n"
        for a in action_items:
            email += f"| `{a['priority'].upper()}` | {a['title']} | **{a['owner']}** | {a['due_date']} | {a['status']} |\n"
        email += "\n"

    if questions:
        email += "### ❓ Open Questions for Follow-up\n"
        for q in questions:
            email += f"* **{q['question']}** (Assigned to: **{q['assigned_to']}**)\n"
        email += "\n"

    email += "Please review your deliverables and keep the team updated in ActionPoint.\n\nBest regards,\n**ActionPoint Co-Pilot**"
    return email

def draft_individual_emails(meeting_id_or_title: str = "", project: str = "") -> str:
    """Drafts personalized follow-up emails for each attendee highlighting their specific assigned tasks, scoped to their project team."""
    conn = get_db()
    cursor = conn.cursor()

    if meeting_id_or_title:
        cursor.execute(
            "SELECT * FROM meetings WHERE id = ? OR LOWER(title) LIKE ? ORDER BY created_at DESC LIMIT 1",
            (meeting_id_or_title, f"%{meeting_id_or_title.lower()}%")
        )
    elif project and project != "ALL":
        cursor.execute(
            "SELECT * FROM meetings WHERE LOWER(project) LIKE ? ORDER BY created_at DESC LIMIT 1",
            (f"%{project.lower()}%",)
        )
    else:
        cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")

    meeting_raw = cursor.fetchone()
    if not meeting_raw:
        conn.close()
        return "No meetings found in database."
    meeting = dict(meeting_raw)

    meeting_id = meeting["id"]
    cursor.execute("SELECT * FROM action_items WHERE meeting_id = ?", (meeting_id,))
    all_items = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM open_questions WHERE meeting_id = ?", (meeting_id,))
    all_questions = [dict(r) for r in cursor.fetchall()]
    conn.close()

    attendees = json.loads(meeting["attendees"]) if meeting["attendees"] else []
    if not attendees:
        # Extract unique owners from action items if attendees list is empty
        attendees = list(set([it["owner"] for it in all_items if it.get("owner") and it["owner"] != "Unassigned"]))

    proj_name = meeting.get("project", "General")
    result = f"# 📬 Individualized Attendee Follow-Up Emails\n\n"
    result += f"*Project Team: **{proj_name}** | Meeting: **{meeting['title']}** ({meeting['meeting_date']})*\n\n---\n\n"

    for person in attendees:
        p_clean = person.split("(")[0].strip()
        # Find tasks owned by this person safely handling None values
        p_items = [it for it in all_items if it.get("owner") and p_clean.lower() in str(it["owner"]).lower()]
        p_questions = [q for q in all_questions if q.get("assigned_to") and p_clean.lower() in str(q["assigned_to"]).lower()]

        result += f"## ✉️ Email to: {person}\n"
        result += f"**Subject:** [{proj_name}] Your Action Items: {meeting['title']}\n"
        result += f"**Project Team:** {proj_name}\n\n"
        result += f"Hi {p_clean},\n\nThanks for your contribution in today's **{proj_name}** sync (**{meeting['title']}**). Here are your direct action items and follow-up deliverables:\n\n"
        
        if p_items:
            result += "### 🎯 Your Assigned Deliverables:\n"
            for it in p_items:
                result += f"* [ ] **{it['title']}**\n  * **Due Date:** `{it['due_date']}` | **Priority:** `{it['priority'].upper()}`\n  * **Details:** {it['description'] or 'See meeting notes'}\n"
        else:
            result += "* *You have no direct action items assigned from this meeting.*\n"

        if p_questions:
            result += "\n### ❓ Open Questions Assigned to You:\n"
            for q in p_questions:
                result += f"* **{q['question']}**\n"

        result += f"\nPlease let the team know if you hit any blockers. You can track your task status in ActionPoint.\n\nBest regards,\nActionPoint Co-Pilot ({proj_name})\n\n---\n\n"

    return result

def generate_meeting_visual_summary(meeting_id_or_title: str) -> str:
    """Generates an executive visual infographic card for the meeting using Gemini image generation."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM meetings WHERE id = ? OR LOWER(title) LIKE ?",
        (meeting_id_or_title, f"%{meeting_id_or_title.lower()}%")
    )
    meeting = cursor.fetchone()
    conn.close()

    if not meeting:
        return f"Meeting '{meeting_id_or_title}' not found."

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-ee8fb0191fd4")
    client = genai.Client(vertexai=True, project=project, location="us-central1")

    prompt = f"""
A clean, modern, professional executive visual summary card for a business meeting titled '{meeting['title']}'.
Featuring high-tech infographic widgets, task checklist cards, roadmap timelines, minimal modern design, tech startup theme, crisp typography, 4k digital illustration.
"""

    cards_dir = "/config/Desktop/BuildWithGemini/simple-agent/summary_cards"
    os.makedirs(cards_dir, exist_ok=True)
    card_path = os.path.join(cards_dir, f"{meeting['id']}_summary.png")

    try:
        result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            )
        )
        for generated_image in result.generated_images:
            with open(card_path, "wb") as f:
                f.write(generated_image.image.image_bytes)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE meetings SET summary_image_path = ? WHERE id = ?", (card_path, meeting["id"]))
            conn.commit()
            conn.close()
            return f"Generated visual summary card for meeting '{meeting['title']}' saved to {card_path}"
    except Exception as e:
        return f"Visual card generation skipped: {str(e)}"
