import json
import os
from google import genai
from google.genai import types
from app.models import MeetingAnalysis

def extract_meeting_action_items(transcript: str, meeting_title: str = "") -> str:
    """Extracts structured summary, decisions, action items, and open questions from a meeting transcript.

    Args:
        transcript: The full text or transcript of the meeting discussion.
        meeting_title: Optional suggested title for the meeting.

    Returns:
        JSON string containing the structured MeetingAnalysis with summary, decisions, action_items, and open_questions.
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-ee8fb0191fd4")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    # Initialize Gemini client via Vertex AI
    client = genai.Client(
        vertexai=True,
        project=project,
        location=location if location != "global" else "us-central1"
    )

    prompt = f"""
You are ActionPoint's specialized Meeting Intelligence extractor.
Analyze the following meeting transcript and extract structured information with high precision:

1. Meeting Title: Give a clear, descriptive title reflecting the core objective (suggested: '{meeting_title}' if appropriate).
2. Summary: A concise, executive summary of the discussion, context, and key milestones.
3. Attendees: All speakers and mentioned stakeholders.
4. Decisions: Explicit choices or agreements made during the meeting, including rationale.
5. Action Items: Concrete, assignable tasks. For each item:
   - Use an imperative title (e.g. "Draft API schema", "Finalize Q4 budget")
   - Identify the owner/assignee explicitly mentioned
   - Capture due dates or deadlines (e.g. "Friday EOD", "2026-10-02")
   - Assign priority: 'critical', 'high', 'medium', or 'low'
   - Status defaults to 'pending'
6. Open Questions: Any unresolved issues, ambiguities, or topics explicitly deferred to follow-ups.

Meeting Transcript:
---
{transcript}
---
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MeetingAnalysis,
            temperature=0.1,
        )
    )

    return response.text
