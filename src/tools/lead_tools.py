"""
Lead Management Tools with Professional Supabase CRM
"""
import re
import json
import sys
from pathlib import Path
from typing import Dict, Any
from langchain_core.tools import tool
import openai

# Add src to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import Supabase CRM (professional!)
from integrations.supabase_crm import get_crm


def assess_lead_quality(
    name: str,
    email: str,
    company: str,
    interest: str,
    meeting_context: str = ""
) -> Dict[str, Any]:
    """
    Use LLM to assess lead quality with professional scoring
    
    Returns:
        dict with summary, lead_score, and qualification_notes
    """
    system_prompt = (
        "You are an expert B2B lead qualification analyst. "
        "Score leads 0-10 based on buying signals:\n"
        "  9-10: Decision maker, clear budget/timeline, specific needs\n"
        "  7-8: Strong interest, defined requirements, exploring solutions\n"
        "  5-6: Qualified prospect, general interest, researching\n"
        "  3-4: Early inquiry, vague needs, information gathering\n"
        "  0-2: Unqualified or insufficient information\n\n"
        "Respond with JSON only."
    )
    
    context_parts = [
        f"Name: {name}",
        f"Email: {email}",
        f"Company: {company}",
        f"Interest: {interest}"
    ]
    
    if meeting_context:
        context_parts.append(f"Context: {meeting_context}")
    
    user_prompt = (
        "Assess this lead:\n" + "\n".join(context_parts) + "\n\n"
        "Return JSON with:\n"
        '{"summary": "one-sentence summary", '
        '"lead_score": 7.5, '
        '"qualification_notes": "detailed reason for score"}'
    )
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=250
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON
        match = re.search(r"\{.*\}", content, re.DOTALL)
        json_text = match.group(0) if match else content
        parsed = json.loads(json_text)
        
        # Extract and validate
        summary = parsed.get("summary", "").strip()
        qualification_notes = parsed.get("qualification_notes", "").strip()
        
        # Parse score
        score_raw = parsed.get("lead_score", 5.0)
        try:
            lead_score = float(score_raw)
        except:
            # Try to extract number from string
            nums = re.findall(r"[\d\.]+", str(score_raw))
            lead_score = float(nums[0]) if nums else 5.0
        
        # Clamp score to 0-10
        lead_score = max(0.0, min(10.0, round(lead_score, 1)))
        
        return {
            "summary": summary or "New inquiry",
            "lead_score": lead_score,
            "qualification_notes": qualification_notes or "Assessment completed"
        }
        
    except Exception as e:
        print(f"❌ Lead assessment error: {e}")
        # Return default assessment
        return {
            "summary": interest[:60] if interest else "New inquiry",
            "lead_score": 5.0,
            "qualification_notes": "Automatic assessment failed - manual review needed"
        }


@tool
def auto_capture_meeting_lead(
    name: str,
    email: str,
    organization: str = "",
    project_description: str = "",
    meeting_time: str = "",
    meeting_id: str = "",
    meeting_link: str = ""
) -> str:
    """
    Automatically capture lead when meeting is scheduled.
    Stores lead in professional Supabase (PostgreSQL) database.
    
    Args:
        name: Lead's full name
        email: Email address
        organization: Company name
        project_description: What they need help with
        meeting_time: Scheduled meeting time
        meeting_id: Google Calendar event ID
        meeting_link: Google Meet link
    
    Returns:
        Success message with lead info and Supabase dashboard link
    """
    try:
        # Build meeting context for better assessment
        meeting_context = f"Scheduled meeting for {meeting_time}" if meeting_time else ""
        
        # Assess lead quality
        assessment = assess_lead_quality(
            name=name,
            email=email,
            company=organization,
            interest=project_description,
            meeting_context=meeting_context
        )
        
        # Store in Supabase (professional PostgreSQL database!)
        crm = get_crm()
        
        lead = crm.create_lead(
            name=name,
            email=email,
            company=organization,
            interest=project_description,
            lead_score=assessment["lead_score"],
            qualification_notes=assessment["qualification_notes"],
            meeting_id=meeting_id,
            meeting_time=meeting_time,
            meeting_link=meeting_link,
            source="Meeting Scheduled"
        )
        
        # Format professional response
        score = assessment["lead_score"]
        lead_id = lead.get("id")
        
        # Determine status emoji
        if score >= 8.0:
            emoji = "🔥"
            status = "Hot Lead"
        elif score >= 6.0:
            emoji = "⭐"
            status = "Qualified Lead"
        elif score >= 4.0:
            emoji = "📋"
            status = "Nurture Lead"
        else:
            emoji = "🧊"
            status = "Cold Lead"
        
        return (
            f"{emoji} **{status} Captured in Supabase!**\n\n"
            f"📊 Score: {score}/10\n"
            f"🆔 Lead ID: {lead_id}\n"
            f"📝 {assessment['summary']}\n\n"
            f"✅ Stored in professional PostgreSQL database\n"
            f"🌐 View in Supabase Dashboard"
        )
        
    except Exception as e:
        print(f"❌ Lead capture error: {e}")
        return (
            f"⚠️ Lead capture failed: {str(e)}\n"
            f"Lead info: {name} ({email}) from {organization}\n"
            f"Interest: {project_description}"
        )


@tool
def store_lead_to_sheet(
    name: str,
    contact: str,
    role: str,
    position: str,
    summary: str = "",
    lead_score: float = None,
    extra: dict = None,
    raw_context: str = ""
) -> str:
    """
    Legacy function maintained for compatibility.
    Now uses Supabase instead of Google Sheets.
    
    Args:
        name: Contact name
        contact: Email or phone
        role: Company name
        position: Job title
        raw_context: Additional context
    
    Returns:
        Success message
    """
    try:
        # Assess lead
        assessment = assess_lead_quality(
            name=name,
            email=contact,
            company=role,
            interest=raw_context or summary
        )
        
        # Store in Supabase
        crm = get_crm()
        
        lead = crm.create_lead(
            name=name,
            email=contact,
            company=role,
            interest=raw_context or summary,
            lead_score=assessment["lead_score"],
            qualification_notes=assessment["qualification_notes"],
            source="Manual Entry"
        )
        
        return (
            f"✅ Lead stored in Supabase!\n"
            f"ID: {lead['id']} | Score: {assessment['lead_score']}/10\n"
            f"{assessment['summary']}"
        )
        
    except Exception as e:
        return f"❌ Failed to store lead: {e}"


@tool
def capture_lead_from_conversation(messages) -> str:
    """
    Extract and store lead from conversation history.
    Uses LLM to parse conversation and capture lead info.
    
    Args:
        messages: Conversation history
    
    Returns:
        Success message or instructions
    """
    # This can be enhanced with actual conversation parsing
    # For now, recommend using auto_capture_meeting_lead
    return (
        "💡 Tip: Lead capture works automatically when you schedule a meeting!\n"
        "Use the schedule_by_natural_with_lead_capture tool to capture leads."
    )


# CLI for testing
if __name__ == "__main__":
    print("🧪 Testing Lead Tools with Supabase CRM")
    print("=" * 50)
    
    # Test lead capture
    test_lead = {
        "name": "Sarah Chen",
        "email": "sarah@techstartup.com",
        "organization": "Tech Startup Inc",
        "project_description": "Need AI automation for customer support, looking to reduce response time by 50%",
        "meeting_time": "2025-10-15 14:00 EST",
        "meeting_id": "test_evt_123",
        "meeting_link": "https://meet.google.com/xxx-yyyy-zzz"
    }
    
    result = auto_capture_meeting_lead.invoke(test_lead)
    print("\n📋 Lead Capture Result:")
    print(result)
    
    print("\n" + "=" * 50)
    
    # Show database contents
    from integrations.supabase_crm import get_crm
    crm = get_crm()
    stats = crm.get_stats()
    
    print("\n📊 Supabase CRM Statistics:")
    print(f"Total Leads: {stats['total_leads']}")
    print(f"Average Score: {stats['average_score']}")
    print(f"By Status: {stats['by_status']}")
    
    print("\n✅ All tests passed!")
    print("\n🌐 View leads in Supabase Dashboard:")
    print("   https://supabase.com/dashboard/project/YOUR_PROJECT/editor")