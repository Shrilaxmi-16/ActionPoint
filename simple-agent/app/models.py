from typing import List, Optional
from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    id: str = Field(description="Unique short ID e.g. ACT-1, ACT-2")
    title: str = Field(description="Clear, actionable title starting with an imperative verb")
    description: str = Field(description="Details and context for this action item")
    owner: str = Field(description="Name of the person responsible for completing this action")
    due_date: Optional[str] = Field(default="TBD", description="Explicit due date or timeframe mentioned (e.g., '2026-10-05', 'End of Week', 'Friday')")
    priority: str = Field(default="medium", description="Priority level: low, medium, high, or critical")
    status: str = Field(default="pending", description="Current status: pending, in_progress, blocked, done")
    project: Optional[str] = Field(default="General", description="Project or workstream this belongs to")

class Decision(BaseModel):
    id: str = Field(description="Unique short ID e.g. DEC-1, DEC-2")
    decision: str = Field(description="Clear statement of what was decided")
    context: str = Field(description="Why this decision was made and rationale discussed")
    made_by: Optional[str] = Field(default="Team", description="Person or group that finalized the decision")

class OpenQuestion(BaseModel):
    id: str = Field(description="Unique short ID e.g. Q-1, Q-2")
    question: str = Field(description="Unresolved question or blocker requiring follow-up")
    assigned_to: Optional[str] = Field(default="Unassigned", description="Person tasked with investigating or finding an answer")
    status: str = Field(default="open", description="open or resolved")

class MeetingAnalysis(BaseModel):
    title: str = Field(description="Descriptive meeting title based on agenda and topics discussed")
    meeting_date: Optional[str] = Field(default="Today", description="Date of the meeting if mentioned or implied")
    summary: str = Field(description="Executive summary of the discussion (2-3 concise paragraphs)")
    attendees: List[str] = Field(default_factory=list, description="List of participant names identified in the transcript")
    decisions: List[Decision] = Field(default_factory=list, description="Key architectural, product, or organizational decisions reached")
    action_items: List[ActionItem] = Field(default_factory=list, description="Action items assigned with owners and deadlines")
    open_questions: List[OpenQuestion] = Field(default_factory=list, description="Open questions and unresolved discussion points")
