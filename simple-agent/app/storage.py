import json
import os
import sqlite3
import uuid
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("ACTIONPOINT_DB_PATH", "/config/Desktop/BuildWithGemini/simple-agent/actionpoint.db")
TRANSCRIPTS_DIR = os.environ.get("ACTIONPOINT_TRANSCRIPTS_DIR", "/config/Desktop/BuildWithGemini/simple-agent/transcripts")

os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Projects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # People
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS people (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE,
        role TEXT,
        email TEXT,
        aliases TEXT
    )
    """)
    
    # Meetings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id TEXT PRIMARY KEY,
        title TEXT,
        meeting_date TEXT,
        summary TEXT,
        attendees TEXT,
        project TEXT,
        transcript_path TEXT,
        summary_image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Decisions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        meeting_id TEXT,
        decision TEXT,
        context TEXT,
        made_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Action Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_items (
        id TEXT PRIMARY KEY,
        meeting_id TEXT,
        project TEXT,
        title TEXT,
        description TEXT,
        owner TEXT,
        due_date TEXT,
        priority TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Open Questions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS open_questions (
        id TEXT PRIMARY KEY,
        meeting_id TEXT,
        question TEXT,
        assigned_to TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize database schema on module load
init_db()

def save_meeting_data(
    title: str,
    meeting_date: str,
    summary: str,
    attendees: List[str],
    decisions: List[Dict[str, Any]],
    action_items: List[Dict[str, Any]],
    open_questions: List[Dict[str, Any]],
    transcript_text: str = "",
    project: str = "General"
) -> str:
    """Saves confirmed meeting data, decisions, action items, and open questions to the database."""
    conn = get_db()
    cursor = conn.cursor()
    
    meeting_id = f"MTG-{uuid.uuid4().hex[:6].upper()}"
    
    transcript_path = ""
    if transcript_text:
        transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{meeting_id}.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
            
    cursor.execute(
        "INSERT INTO meetings (id, title, meeting_date, summary, attendees, project, transcript_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (meeting_id, title, meeting_date, summary, json.dumps(attendees), project, transcript_path)
    )
    
    # Ensure project exists
    cursor.execute("INSERT OR IGNORE INTO projects (id, name, description) VALUES (?, ?, ?)",
                   (project.lower().replace(" ", "-"), project, f"Project {project}"))
                   
    # Save attendees as people
    for person in attendees:
        p_name = person.split("(")[0].strip()
        cursor.execute("INSERT OR IGNORE INTO people (id, name, aliases) VALUES (?, ?, ?)",
                       (p_name.lower().replace(" ", "-"), p_name, json.dumps([p_name])))

    # Save decisions using INSERT OR REPLACE and unique prefixed IDs
    for dec in decisions:
        raw_id = dec.get("id") or "DEC"
        # Always scope ID to meeting to guarantee uniqueness across meetings
        dec_id = f"{meeting_id}-{raw_id}"
        cursor.execute(
            "INSERT OR REPLACE INTO decisions (id, meeting_id, decision, context, made_by) VALUES (?, ?, ?, ?, ?)",
            (dec_id, meeting_id, dec.get("decision", ""), dec.get("context", ""), dec.get("made_by", "Team"))
        )
        
    # Save action items using INSERT OR REPLACE and unique prefixed IDs
    for item in action_items:
        raw_id = item.get("id") or "ACT"
        act_id = f"{meeting_id}-{raw_id}"
        cursor.execute(
            """INSERT OR REPLACE INTO action_items 
               (id, meeting_id, project, title, description, owner, due_date, priority, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                act_id,
                meeting_id,
                item.get("project") or project,
                item.get("title", ""),
                item.get("description", ""),
                item.get("owner", "Unassigned"),
                item.get("due_date", "TBD"),
                item.get("priority", "medium").lower(),
                item.get("status", "pending").lower()
            )
        )
        
    # Save open questions using INSERT OR REPLACE and unique prefixed IDs
    for q in open_questions:
        raw_id = q.get("id") or "Q"
        q_id = f"{meeting_id}-{raw_id}"
        cursor.execute(
            "INSERT OR REPLACE INTO open_questions (id, meeting_id, question, assigned_to, status) VALUES (?, ?, ?, ?, ?)",
            (q_id, meeting_id, q.get("question", ""), q.get("assigned_to", "Unassigned"), q.get("status", "open").lower())
        )
        
    conn.commit()
    conn.close()
    return meeting_id
