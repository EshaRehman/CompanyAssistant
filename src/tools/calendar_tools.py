"""
Enhanced calendar tools with automatic lead capture integration and availability checking
"""
import re
from datetime import datetime, timedelta
from dateparser import parse as dp_parse
from dateutil import tz
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
import openai
import requests
import sys
import os
from pathlib import Path

# Add src directory to Python path for absolute imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from utils.calendar_creator import GoogleCalendarMeetingCreator
# Note: auto_capture_meeting_lead imported locally to avoid circular imports

# Initialize Google Calendar Creator
_calendar_creator = None

#-----------------------------------------------------------------------------
# CALENDLY INTEGRATION
#-----------------------------------------------------------------------------
API_TOKEN = os.getenv("CALENDLY_ACCESS_TOKEN")
if not API_TOKEN:
    raise ValueError("Missing CALENDLY_ACCESS_TOKEN in environment variables.")
API_BASE = "https://api.calendly.com"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def get_user_uri() -> str:
    resp = requests.get(f"{API_BASE}/users/me", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["resource"]["uri"]

USER_URI = get_user_uri()

@tool
def list_availability_schedules(user_uri: str = None) -> List[Dict[str, Any]]:
    """Retrieve Calendly availability schedules for a given user URI."""
    if user_uri is None:
        user_uri = USER_URI
    url = f"{API_BASE}/user_availability_schedules"
    resp = requests.get(url, params={"user": user_uri}, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

@tool
def list_busy_times(start: datetime, end: datetime, user_uri: str = None) -> Dict[str, Any]:
    """Retrieve busy time slots between two datetimes for a given user."""
    if user_uri is None:
        user_uri = USER_URI
    url = f"{API_BASE}/user_busy_times"
    params = {
        "user": user_uri,
        "start_time": start.isoformat(),
        "end_time": end.isoformat()
    }
    resp = requests.get(url, params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def check_availability(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """
    Check if a specific time slot is available using Calendly API.

    Returns:
        Dict with 'available' boolean and 'conflicts' list
    """
    try:
        # Check the day containing the requested slot
        day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        busy_resp = list_busy_times.invoke({"start": day_start, "end": day_end})
        busy_slots = busy_resp.get("collection", [])

        conflicts = []
        for slot in busy_slots:
            slot_start = datetime.fromisoformat(slot["start_time"].replace("Z", "+00:00"))
            slot_end = datetime.fromisoformat(slot["end_time"].replace("Z", "+00:00"))

            # Convert to same timezone if needed
            if slot_start.tzinfo != start_dt.tzinfo:
                slot_start = slot_start.astimezone(start_dt.tzinfo)
                slot_end = slot_end.astimezone(start_dt.tzinfo)

            # Check for overlap
            if not (end_dt <= slot_start or start_dt >= slot_end):
                conflicts.append({
                    "start": slot_start,
                    "end": slot_end,
                    "title": slot.get("event_type", "Busy")
                })

        return {
            "available": len(conflicts) == 0,
            "conflicts": conflicts
        }

    except Exception as e:
        print(f"Availability check failed: {e}")
        # If availability check fails, assume available to not block booking
        return {"available": True, "conflicts": []}

@tool
def suggest_alternative_times(
    start_text: str,
    duration_text: str,
    num_suggestions: int = 3
) -> str:
    """
    Suggest alternative meeting times if the requested slot is busy.

    Args:
        start_text: Original requested time
        duration_text: Meeting duration
        num_suggestions: Number of alternatives to suggest
    """
    try:
        original_start = parse_datetime.invoke({"text": start_text})
        duration = parse_duration.invoke({"text": duration_text})

        suggestions = []
        current_time = original_start

        # Look for alternatives within the next 7 days
        max_attempts = 50  # Limit search to prevent infinite loops
        attempts = 0

        while len(suggestions) < num_suggestions and attempts < max_attempts:
            current_end = current_time + duration
            availability = check_availability(current_time, current_end)

            if availability["available"]:
                suggestions.append({
                    "start": current_time,
                    "end": current_end,
                    "formatted": current_time.strftime('%A, %B %d at %I:%M %p %Z')
                })

            # Move to next hour, but skip outside business hours
            current_time += timedelta(hours=1)

            # Skip to next business day if outside hours (9 AM - 6 PM)
            if current_time.hour < 9 or current_time.hour >= 18:
                # Move to 9 AM next day
                next_day = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
                if current_time.hour >= 18:
                    next_day += timedelta(days=1)
                # Skip weekends
                while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    next_day += timedelta(days=1)
                current_time = next_day

            attempts += 1

        if not suggestions:
            return "❌ No available alternative times found in the next week. Please contact us directly to discuss scheduling options."

        result = f"📅 Alternative meeting times available:\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            result += f"{i}. {suggestion['formatted']}\n"

        result += f"\nWould you like to book one of these alternative times instead?"
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
    Handles "next <weekday>", relative phrases, and complex expressions.
    """
    if ref is None:
        ref = datetime.now(tz=tz.tzlocal())

    # Handle "next <weekday>" via regex
    m = re.match(r"\s*next\s+(\w+)(.*)", text, re.I)
    if m and m.group(1).lower() in WEEKDAYS:
        target = WEEKDAYS[m.group(1).lower()]
        today = ref.weekday()
        days_ahead = (target - today + 7) % 7 or 7
        date_str = (ref + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        text = f"{date_str}{m.group(2)}"

    # Try dateparser first
    dt = dp_parse(text, settings={
        "RELATIVE_BASE": ref,
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": True
    })
    if dt is not None:
        return dt

    # Fallback to LLM
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
# ENHANCED MEETING SCHEDULING WITH AVAILABILITY CHECKING
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
    description: str = ""
) -> str:
    """
    🎯 ENHANCED: Schedule meeting with availability checking and automatic lead capture

    This tool first checks if the requested time slot is available before booking.
    If unavailable, it suggests alternative times.

    Args:
        start_text: Natural language start time (e.g., "Monday at 11 am")
        duration_text: Natural language duration (e.g., "1 hour")
        attendee_name: Full name of the attendee
        attendee_email: Email address of the attendee
        organization: Company/organization name (optional)
        project_description: Brief description of their project/needs (optional)
        title: Meeting title (auto-generated if not provided)
        description: Meeting description (auto-generated if not provided)
    """
    try:
        # Parse time and duration
        start_dt = parse_datetime.invoke({"text": start_text})
        duration = parse_duration.invoke({"text": duration_text})
        end_dt = start_dt + duration

        print(f"🔍 Checking availability for {start_dt.strftime('%A, %B %d at %I:%M %p %Z')}")

        # Check availability first
        availability = check_availability(start_dt, end_dt)

        if not availability["available"]:
            # Time slot is busy - suggest alternatives
            conflicts_info = []
            for conflict in availability["conflicts"]:
                conflict_time = f"{conflict['start'].strftime('%I:%M %p')} - {conflict['end'].strftime('%I:%M %p')}"
                conflicts_info.append(f"• {conflict_time}: {conflict.get('title', 'Busy')}")

            conflicts_text = "\n".join(conflicts_info)

            # Get alternative suggestions
            alternatives = suggest_alternative_times.invoke({
                "start_text": start_text,
                "duration_text": duration_text,
                "num_suggestions": 3
            })

            return f"""⚠️ The requested time slot is not available.

📅 Requested: {start_dt.strftime('%A, %B %d at %I:%M %p %Z')}
❌ Conflicts found:
{conflicts_text}

{alternatives}

Please let me know which alternative time works for you, and I'll schedule the meeting with automatic lead capture."""

        # Time slot is available - proceed with booking
        print(f"✅ Time slot available, proceeding with booking...")

        # Auto-generate title if not provided
        if not title:
            title = f"Narsun Studios Consultation - {attendee_name}"

        # Auto-generate description if not provided
        if not description:
            desc_parts = [f"Meeting with {attendee_name}"]
            if organization:
                desc_parts.append(f"from {organization}")
            if project_description:
                desc_parts.append(f"regarding: {project_description}")
            description = " ".join(desc_parts)

        # Create the calendar meeting
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
            return "❌ Failed to create meeting. Please check your inputs and try again."

        # Extract meeting details
        event_id = event['id']
        meeting_link = event.get('htmlLink', 'N/A')
        meet_link = "N/A"
        if 'conferenceData' in event:
            entry_points = event['conferenceData'].get('entryPoints', [])
            if entry_points:
                meet_link = entry_points[0].get('uri', 'N/A')

        # Automatically capture the lead
        try:
            # Import here to avoid circular imports
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

        # Format success response
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
        return f"❌ Error scheduling meeting with availability check: {str(e)}"

#-----------------------------------------------------------------------------
# BASIC CALENDAR OPERATIONS (unchanged)
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
    """Create a basic Google Calendar meeting without availability checking"""
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
            return f"✅ Meeting '{title}' created! Event ID: {event['id']}, Link: {event.get('htmlLink', 'N/A')}"
        else:
            return "❌ Failed to create meeting. Please check your inputs."

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
    """Create a Google Calendar meeting with Google Meet video conferencing"""
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

            return f"✅ Google Meet meeting '{title}' created! Event ID: {event['id']}, Meet Link: {meet_link}"
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
            return f"✅ Event {event_id} updated successfully! Link: {updated_event.get('htmlLink', 'N/A')}"
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
            return f"✅ Recurring meeting '{title}' created! Event ID: {event['id']}, Recurrence: {recurrence_rule}"
        else:
            return "❌ Failed to create recurring meeting."

    except Exception as e:
        return f"❌ Error creating recurring meeting: {str(e)}"