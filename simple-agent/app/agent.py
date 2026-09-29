# ruff: noqa
import json
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.extraction import extract_meeting_action_items
from app.tools import (
    confirm_and_save_meeting,
    query_action_items,
    update_action_item_status,
    generate_follow_up_agenda,
    draft_follow_up_email,
    draft_individual_emails,
    generate_meeting_visual_summary
)

MODEL = "gemini-2.5-flash"

root_agent = Agent(
    name="actionpoint_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are ActionPoint, an intelligent meeting action tracking and communication assistant.
Your job is to convert raw meeting transcripts into high-fidelity structured records and craft tailored follow-up communications.

Formatting Guidelines:
1. Tables for Action Items: Whenever presenting task lists, render them in Markdown tables with columns: Status, Priority, Task Description, Assignee, and Deadline.
2. Distinct Email vs Agenda:
   - When asked to draft an email or recap email: Call `draft_follow_up_email`. Format with professional Subject, Attendees, Executive Summary, Decisions, and Deliverables.
   - When asked to draft individual or personalized emails: Call `draft_individual_emails` to generate targeted messages for each attendee highlighting only their assigned tasks.
   - When asked for a follow-up agenda: Call `generate_follow_up_agenda`. Focus on time-boxed sections (15m status check, 20m questions/blockers, 10m open floor).
3. Do not confuse email and agenda requests: they have completely separate formats and purposes.
""",
    tools=[
        extract_meeting_action_items,
        confirm_and_save_meeting,
        query_action_items,
        update_action_item_status,
        generate_follow_up_agenda,
        draft_follow_up_email,
        draft_individual_emails,
        generate_meeting_visual_summary
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
