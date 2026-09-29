# Project Brief: ActionPoint

## Overview
ActionPoint is an agentic application that turns raw meeting transcripts into structured, trackable action items, decisions, and follow-ups.

## Key Capabilities & Tools
1. **Extraction**:
   - Parses unstructured meeting transcripts into structured JSON: Executive summary, Key decisions, Action items (owner, due date, priority, description), and Open questions.
2. **Review & Confirm**:
   - Presents extracted items to the user for confirmation and edits before persisting.
3. **Storage & Database**:
   - Database for projects, people, meetings, decisions, action items, and open questions.
   - Storage for raw transcripts.
4. **Action Item Management Tools**:
   - Query items by project, owner, status, or overdue filter.
   - Update action item status (Todo, In Progress, Blocked, Done).
   - Generate follow-up agendas from unresolved open questions & overdue items.
   - Draft follow-up email summaries for attendees.
5. **Memory & Personalization**:
   - Cross-session memory for team members, name aliases, projects, and user preferences.
6. **Visual Summaries**:
   - Generates visual meeting summary cards.
7. **Frontend Web UI**:
   - Upload screen, review screen with editable cards, Kanban action board, analytics dashboard, and chat panel.
