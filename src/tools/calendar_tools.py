"""
Enhanced calendar tools with automatic lead capture integration
Google Calendar only - Calendly integration removed
"""
import re
from datetime import datetime, timedelta
from dateparser import parse as dp_parse
from dateutil import tz
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
import openai
import sys
import os
from pathlib import Path

# Add src directory to Python path for absolute imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from utils.calendar_creator import GoogleCalendarMeetingCreator

# Initialize Google Calendar Creator
_calendar_creator = None

#-----------------------------------------------------------------------------
# AVAILABILITY CHECKING (Simplified - No Calendly)
#-----------------------------------------------------------------------------

def check_availability(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """
    Simplified availability check without Calendly.
    Always returns available.
    
    Returns:
        Dict with 'available' boolean and 'conflicts' list
    """
    return {
        "available": True,
        "conflicts": []
    }

@tool
def suggest_alternative_times(
    start_text: str,
    duration_text: str,
    num_suggestions: int = 3
) -> str:
    """
    Suggest alternative meeting times based on business hours.
    
    Args:
        start_text: Original requested time
        duration_text: Meeting duration
        num_suggestions: Number of alternatives to suggest
    """
    try:
        original_start = parse_datetime.invoke({"text": start_text})
        
        suggestions = []
        current_time = original_start + timedelta(days=1)
        
        max_attempts = 50
        attempts = 0

        while len(suggestions) < num_suggestions and attempts < max_attempts:
            if current_time.hour >= 9 and current_time.hour < 18 and current_time.weekday() < 5:
                suggestions.append({
                    "start": current_time,
                    "formatted": current_time.strftime('%A, %B %d at %I:%M %p %Z')
                })

            current_time += timedelta(hours=1)

            if current_time.hour < 9 or current_time.hour >= 18:
                next_day = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
                if current_time.hour >= 18:
                    next_day += timedelta(days=1)
                while next_day.weekday() >= 5:
                    next_day += timedelta(days=1)
                current_time = next_day

            attempts += 1

        if not suggestions:
            return "❌ No available alternative times found. Please contact us directly."

        result = f"📅 Suggested meeting times:\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            result += f"{i}. {suggestion['formatted']}\n"

        result += f"\nWould you like to book one of these times instead?"
        return result

    except Exception as e:
        return f"❌ Error finding alternative times: {str(e)}"

#-----------------------------------------------------------------------------
# CALENDAR UTILITIES
#-----------------------------------------------------------------------------

def get_calendar_creator() -> GoogleCalendarMeetingCreator:
    """Get or create a singleton Google Calendar creator instance."""
    global _calendar_creator
    if _calendar_creator is None:
        try:
            _calendar_creator = GoogleCalendarMeetingCreator()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Calendar: {e}")
    return _calendar_creator

def llm_parse_datetime(text: str, ref: datetime) -> datetime:
    """Use LLM to parse complex natural language datetime expressions"""
    system_prompt = (
        "You are a precise date/time parser. Given the current time and a user's "
        "natural-language expression, return exactly one ISO-8601 datetime with "
        "timezone, and nothing else."
    )
    user_prompt = f"Current time: {ref.isoformat()}\nConvert this into an ISO-8601 datetime: \"{text}\""

    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    iso_ts = resp.choices[0].message.content.strip().strip('"')
    try:
        dt = datetime.fromisoformat(iso_ts)
    except Exception as e:
        raise ValueError(f"LLM returned invalid timestamp: {iso_ts}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ref.tzinfo or tz.tzlocal())
    return dt

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

@tool
def parse_datetime(text: str, ref: datetime = None) -> datetime:
    """
    Parse any natural-language date/time string into a timezone-aware datetime.
    """
    if ref is None:
        ref = datetime.now(tz=tz.tzlocal())

    m = re.match(r"\s*next\s+(\w+)(.*)", text, re.I)
    if m and m.group(1).lower() in WEEKDAYS:
        target = WEEKDAYS[m.group(1).lower()]
        today = ref.weekday()
        days_ahead = (target - today + 7) % 7 or 7
        date_str = (ref + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        text = f"{date_str}{m.group(2)}"

    dt = dp_parse(text, settings={
        "RELATIVE_BASE": ref,
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": True
    })
    if dt is not None:
        return dt

    return llm_parse_datetime(text, ref)

@tool
def parse_duration(text: str) -> timedelta:
    """Parse human-readable duration into a timedelta"""
    patterns = [
        r'(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hour|hours)',
        r'(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>m|min|minute|minutes)',
        r'(?P<hours>\d+)\s*h(?:our)?s?\s*(?P<minutes>\d+)\s*m(?:in)?(?:ute)?s?',
        r'(?P<hours>\d+)\s*hours?\s*(?P<minutes>\d+)\s*minutes?'
    ]
    t = text.lower().strip()
    for pat in patterns:
        m = re.match(pat, t)
        if not m:
            continue
        g = m.groupdict()
        if "hours" in g and "minutes" in g:
            return timedelta(hours=float(g["hours"]), minutes=float(g["minutes"]))
        if "value" in g:
            v = float(g["value"])
            return timedelta(hours=v) if g["unit"].startswith("h") else timedelta(minutes=v)
    raise ValueError(f"Unrecognized duration: {text}")

#-----------------------------------------------------------------------------
# ENHANCED MEETING SCHEDULING WITH LEAD CAPTURE
#-----------------------------------------------------------------------------

@tool
def schedule_by_natural_with_lead_capture(
    start_text: str,
    duration_text: str,
    attendee_name: str,
    attendee_email: str,
    organization: str = "",
    project_description: str = "",
    title: str = "",
    description: str = "",
    timezone: str = "America/New_York"  # Default to EST/EDT
) -> str:
    """
    Schedule meeting with automatic lead capture
    
    Args:
        start_text: Natural language start time
        duration_text: Natural language duration
        attendee_name: Full name
        attendee_email: Email address
        organization: Company name
        project_description: Project needs
        title: Meeting title (auto-generated if empty)
        description: Meeting description (auto-generated if empty)
        timezone: IANA timezone (e.g., 'America/New_York', 'Asia/Karachi')
    """
    try:
        start_dt = parse_datetime.invoke({"text": start_text})
        duration = parse_duration.invoke({"text": duration_text})
        end_dt = start_dt + duration

        print(f"🔍 Scheduling meeting for {start_dt.strftime('%A, %B %d at %I:%M %p %Z')}")

        if not title:
            title = f"Apec Digital Solutions Consultation - {attendee_name}"

        if not description:
            desc_parts = [f"Meeting with {attendee_name}"]
            if organization:
                desc_parts.append(f"from {organization}")
            if project_description:
                desc_parts.append(f"regarding: {project_description}")
            description = " ".join(desc_parts)

        calendar = get_calendar_creator()
        event = calendar.create_meeting_with_google_meet(
            title=title,
            description=description,
            start_time=start_dt,
            end_time=end_dt,
            attendees=[attendee_email],
            timezone='America/New_York'
        )

        if not event:
            return "❌ Failed to create meeting. Please check your inputs."

        event_id = event['id']
        meeting_link = event.get('htmlLink', 'N/A')
        meet_link = "N/A"
        if 'conferenceData' in event:
            entry_points = event['conferenceData'].get('entryPoints', [])
            if entry_points:
                meet_link = entry_points[0].get('uri', 'N/A')

        try:
            from tools.lead_tools import auto_capture_meeting_lead
            lead_capture_result = auto_capture_meeting_lead.invoke({
                "name": attendee_name,
                "email": attendee_email,
                "organization": organization,
                "project_description": project_description,
                "meeting_time": start_dt.strftime('%Y-%m-%d %H:%M %Z'),
                "meeting_id": event_id
            })
        except Exception as e:
            lead_capture_result = f"⚠️ Lead capture failed: {str(e)}"

        response_parts = [
            f"✅ Meeting scheduled successfully!",
            f"📅 {title}",
            f"🕐 {start_dt.strftime('%B %d, %Y at %I:%M %p %Z')}",
            f"⏱️ Duration: {duration_text}",
            f"👤 Attendee: {attendee_name} ({attendee_email})",
        ]

        if organization:
            response_parts.append(f"🏢 Organization: {organization}")

        response_parts.extend([
            f"🔗 Calendar: {meeting_link}",
            f"📹 Google Meet: {meet_link}",
            "",
            f"🎯 Lead Status: {lead_capture_result}"
        ])

        return "\n".join(response_parts)

    except Exception as e:
        return f"❌ Error scheduling meeting: {str(e)}"

#-----------------------------------------------------------------------------
# BASIC CALENDAR OPERATIONS
#-----------------------------------------------------------------------------

@tool
def create_google_calendar_meeting(
    title: str,
    description: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    attendees: Optional[List[str]] = None,
    location: str = "",
    timezone: str = 'America/New_York'
) -> str:
    """Create a basic Google Calendar meeting"""
    try:
        calendar = get_calendar_creator()
        event = calendar.create_meeting(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees or [],
            location=location,
            timezone=timezone
        )

        if event:
            return f"✅ Meeting '{title}' created! Event ID: {event['id']}"
        else:
            return "❌ Failed to create meeting."

    except Exception as e:
        return f"❌ Error creating meeting: {str(e)}"

@tool
def create_google_meet_meeting(
    title: str,
    description: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    attendees: Optional[List[str]] = None,
    timezone: str = 'America/New_York'
) -> str:
    """Create a Google Calendar meeting with Google Meet"""
    try:
        calendar = get_calendar_creator()
        event = calendar.create_meeting_with_google_meet(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees or [],
            timezone=timezone
        )

        if event:
            meet_link = "N/A"
            if 'conferenceData' in event:
                entry_points = event['conferenceData'].get('entryPoints', [])
                if entry_points:
                    meet_link = entry_points[0].get('uri', 'N/A')

            return f"✅ Google Meet meeting '{title}' created! Meet Link: {meet_link}"
        else:
            return "❌ Failed to create Google Meet meeting."

    except Exception as e:
        return f"❌ Error creating Google Meet meeting: {str(e)}"

@tool
def list_upcoming_google_calendar_events(max_results: int = 10) -> str:
    """List upcoming Google Calendar events"""
    try:
        calendar = get_calendar_creator()
        events = calendar.list_upcoming_events(max_results=max_results)

        if not events:
            return "📅 No upcoming events found."

        result = f"📅 Upcoming {len(events)} events:\n"
        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            result += f"{i}. {event['summary']} - {start}\n"

        return result.strip()

    except Exception as e:
        return f"❌ Error listing events: {str(e)}"

@tool
def delete_google_calendar_event(event_id: str) -> str:
    """Delete a Google Calendar event"""
    try:
        calendar = get_calendar_creator()
        success = calendar.delete_event(event_id)

        if success:
            return f"✅ Event {event_id} deleted successfully!"
        else:
            return f"❌ Failed to delete event {event_id}."

    except Exception as e:
        return f"❌ Error deleting event: {str(e)}"

@tool
def update_google_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
    timezone: str = 'America/New_York'
) -> str:
    """Update an existing Google Calendar event"""
    try:
        calendar = get_calendar_creator()
        updated_event = calendar.update_event(
            event_id=event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            location=location,
            timezone=timezone
        )

        if updated_event:
            return f"✅ Event {event_id} updated successfully!"
        else:
            return f"❌ Failed to update event {event_id}."

    except Exception as e:
        return f"❌ Error updating event: {str(e)}"

@tool
def create_recurring_meeting(
    title: str,
    description: str = "",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    attendees: Optional[List[str]] = None,
    location: str = "",
    timezone: str = 'America/New_York',
    recurrence_rule: str = "WEEKLY"
) -> str:
    """Create a recurring Google Calendar meeting"""
    try:
        calendar = get_calendar_creator()
        event = calendar.create_recurring_meeting(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees or [],
            location=location,
            timezone=timezone,
            recurrence_rule=recurrence_rule
        )

        if event:
            return f"✅ Recurring meeting '{title}' created! Recurrence: {recurrence_rule}"
        else:
            return "❌ Failed to create recurring meeting."

    except Exception as e:
        return f"❌ Error creating recurring meeting: {str(e)}"