import json
import pytest
from app.tools import (
    confirm_and_save_meeting,
    query_action_items,
    update_action_item_status,
    generate_follow_up_agenda,
    draft_follow_up_email
)
from app.storage import get_db

def test_save_and_query_tools():
    # Save a meeting
    result = confirm_and_save_meeting(
        title="Project Horizon Sprint Sync",
        summary="Team aligned on auth and monitoring.",
        project="Project Horizon",
        attendees_json=json.dumps(["Sarah", "Dave", "Elena", "Marcus"]),
        decisions_json=json.dumps([{"id": "DEC-1", "decision": "Migrate to Cloud Identity", "context": "Fix auth latency", "made_by": "Dave"}]),
        action_items_json=json.dumps([
            {"id": "ACT-101", "title": "Draft Cloud Identity Migration RFC", "owner": "Dave", "due_date": "Thursday", "priority": "high", "status": "pending", "project": "Project Horizon"},
            {"id": "ACT-102", "title": "Analyze Mobile Viewport Analytics", "owner": "Elena", "due_date": "Friday", "priority": "medium", "status": "pending", "project": "Project Horizon"}
        ]),
        open_questions_json=json.dumps([{"id": "Q-101", "question": "Separate staging project for Agent Engine?", "assigned_to": "Marcus", "status": "open"}])
    )
    assert "Successfully saved" in result

    # Query Dave's tasks
    dave_items = json.loads(query_action_items(owner="Dave"))
    assert len(dave_items) >= 1
    assert any(i["id"] == "ACT-101" for i in dave_items)

    # Update task status
    update_res = update_action_item_status("ACT-101", "in_progress")
    assert "in_progress" in update_res

    # Query updated task
    updated_items = json.loads(query_action_items(owner="Dave", status="in_progress"))
    assert any(i["id"] == "ACT-101" for i in updated_items)

    # Generate follow-up agenda
    agenda = generate_follow_up_agenda("Project Horizon")
    assert "Follow-Up Sync Agenda" in agenda
    assert "ACT-101" in agenda
    assert "Q-101" in agenda

    # Draft follow-up email
    email = draft_follow_up_email("Project Horizon")
    assert "Subject: Recap & Action Items" in email
    assert "Cloud Identity" in email
