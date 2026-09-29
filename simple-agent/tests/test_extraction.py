import json
import pytest
from app.extraction import extract_meeting_action_items
from app.models import MeetingAnalysis

def test_extract_meeting_action_items():
    with open("tests/sample_transcript.txt", "r") as f:
        transcript = f.read()

    result_json = extract_meeting_action_items(transcript, meeting_title="Project Horizon Launch Readiness")
    data = json.loads(result_json)
    
    # Validate against Pydantic schema
    analysis = MeetingAnalysis.model_validate(data)
    
    assert analysis.title
    assert len(analysis.attendees) >= 4
    assert any("Dave" in a for a in analysis.attendees)
    assert any("Sarah" in a for a in analysis.attendees)
    
    # Validate decisions
    assert len(analysis.decisions) >= 1
    auth_decision = [d for d in analysis.decisions if "Identity" in d.decision or "auth" in d.decision.lower()]
    assert len(auth_decision) > 0
    
    # Validate action items
    assert len(analysis.action_items) >= 3
    owners = [item.owner.lower() for item in analysis.action_items]
    assert any("dave" in o for o in owners)
    assert any("elena" in o for o in owners)
    assert any("marcus" in o for o in owners)
    
    # Validate open questions
    assert len(analysis.open_questions) >= 1

if __name__ == "__main__":
    test_extract_meeting_action_items()
    print("Test passed successfully!")
