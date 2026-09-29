import os
import sys
import json

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-04-ee8fb0191fd4"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, "/config/Desktop/BuildWithGemini/simple-agent")

from app.agent import root_agent
from app.storage import get_db, save_meeting_data
from app.extraction import extract_meeting_action_items
from app.tools import draft_follow_up_email, draft_individual_emails, generate_follow_up_agenda
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

app = FastAPI(title="ActionPoint Local Gateway")

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="app", session_service=session_service)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-user-session"

class ExtractRequest(BaseModel):
    transcript: str
    meeting_title: str = "Meeting Sync"

class ConfirmSaveRequest(BaseModel):
    meeting_analysis: dict
    project: str = "Project Horizon"

class MeetingActionRequest(BaseModel):
    meeting_id: str = ""
    project: str = ""
    individual: str = ""

@app.post("/api/extract")
async def extract_api(req: ExtractRequest):
    try:
        raw_json_str = extract_meeting_action_items(req.transcript, req.meeting_title)
        analysis_dict = json.loads(raw_json_str)
        return {"status": "success", "data": analysis_dict}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/confirm_save")
async def confirm_save_api(req: ConfirmSaveRequest):
    try:
        data = req.meeting_analysis
        meeting_id = save_meeting_data(
            title=data.get("title", "Meeting"),
            meeting_date=data.get("meeting_date") or "Today",
            summary=data.get("summary", ""),
            attendees=data.get("attendees", []),
            decisions=data.get("decisions", []),
            action_items=data.get("action_items", []),
            open_questions=data.get("open_questions", []),
            transcript_text="",
            project=req.project
        )
        return {"status": "success", "meeting_id": meeting_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tasks")
async def get_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM action_items ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/projects")
async def get_projects():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT project FROM meetings WHERE project IS NOT NULL AND project != '' ORDER BY project")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

@app.get("/api/attendees")
async def get_attendees(project: str = ""):
    conn = get_db()
    cursor = conn.cursor()
    if project and project != "ALL":
        cursor.execute(
            "SELECT DISTINCT owner FROM action_items WHERE owner IS NOT NULL AND owner != '' AND owner != 'Unassigned' AND LOWER(project) LIKE ? ORDER BY owner",
            (f"%{project.lower()}%",)
        )
    else:
        cursor.execute("SELECT DISTINCT owner FROM action_items WHERE owner IS NOT NULL AND owner != '' AND owner != 'Unassigned' ORDER BY owner")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

@app.get("/api/metrics")
async def get_metrics():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM meetings")
    mtg_count = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM action_items WHERE status != 'done'")
    act_count = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM decisions")
    dec_count = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM open_questions WHERE status != 'resolved'")
    q_count = cursor.fetchone()["c"]

    # Priority breakdown
    cursor.execute("SELECT priority, COUNT(*) as c FROM action_items GROUP BY priority")
    p_rows = cursor.fetchall()
    priority_dist = {r["priority"].lower(): r["c"] for r in p_rows if r["priority"]}

    # Status breakdown
    cursor.execute("SELECT status, COUNT(*) as c FROM action_items GROUP BY status")
    s_rows = cursor.fetchall()
    status_dist = {r["status"].lower(): r["c"] for r in s_rows if r["status"]}

    # Top Owners
    cursor.execute("SELECT owner, COUNT(*) as c FROM action_items WHERE owner != 'Unassigned' GROUP BY owner ORDER BY c DESC LIMIT 5")
    owner_rows = cursor.fetchall()
    owner_dist = {r["owner"]: r["c"] for r in owner_rows}

    # Latest Meeting details for Visual Summary Card
    cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
    latest_mtg = cursor.fetchone()
    mtg_info = dict(latest_mtg) if latest_mtg else None
    if mtg_info and mtg_info.get("attendees"):
        mtg_info["attendees"] = json.loads(mtg_info["attendees"])

    conn.close()
    return {
        "meetings": mtg_count,
        "active_items": act_count,
        "decisions": dec_count,
        "open_questions": q_count,
        "priority_dist": priority_dist,
        "status_dist": status_dist,
        "owner_dist": owner_dist,
        "latest_meeting": mtg_info
    }

@app.post("/api/draft_email")
async def draft_email_endpoint(req: MeetingActionRequest):
    try:
        content = draft_follow_up_email(meeting_id_or_title=req.meeting_id, project=req.project)
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "content": f"**Error drafting email:** {str(e)}"}

@app.post("/api/draft_individual_emails")
async def draft_individual_emails_endpoint(req: MeetingActionRequest):
    try:
        content = draft_individual_emails(meeting_id_or_title=req.meeting_id, project=req.project)
        # If a specific individual was requested, filter to that individual's section
        if req.individual and req.individual != "ALL":
            lines = content.split("## ✉️ Email to:")
            header = lines[0]
            matched_section = ""
            for sec in lines[1:]:
                first_line = sec.strip().split("\n")[0]
                if req.individual.lower() in first_line.lower():
                    matched_section = "## ✉️ Email to:" + sec
                    break
            if matched_section:
                content = f"{header}\n{matched_section}"
            else:
                content = f"{header}\n*No tasks found assigned to {req.individual} in this project team.*"

        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "content": f"**Error drafting individual email:** {str(e)}"}

@app.post("/api/generate_agenda")
async def generate_agenda_endpoint(req: MeetingActionRequest):
    try:
        content = generate_follow_up_agenda(req.meeting_id)
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "content": f"**Error generating agenda:** {str(e)}"}

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        user_id = "local_user"
        session_id = req.session_id

        session = await session_service.get_session(
            app_name="app",
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name="app",
                user_id=user_id,
                session_id=session_id
            )

        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=req.message)]
        )

        events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content
        ):
            events.append(event)

        response_text = ""
        for event in events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text

        if not response_text:
            response_text = "Processed successfully."

        return {"parts": [{"text": response_text}]}
    except Exception as e:
        return {"parts": [{"text": f"Error: {str(e)}"}]}

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
