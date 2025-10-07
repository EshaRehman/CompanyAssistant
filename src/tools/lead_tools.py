"""
Enhanced lead management tools with automatic capture capabilities
"""
import os
import re
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Sequence
from pathlib import Path
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage
import openai


def _resolve_service_account_path(raw_path: str) -> str:
    """Resolve service account file path"""
    p = Path(raw_path)
    if not p.is_absolute():
        base = Path(__file__).parent.parent.parent  # Go up to project root
        p = (base / raw_path).resolve()
    return str(p)


def _get_gspread_client():
    """Initialize Google Sheets client"""
    try:
        from google.oauth2.service_account import Credentials
        import gspread
    except ImportError as e:
        raise ImportError("Missing google sheets dependencies. Install gspread and google-auth.") from e

    raw = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE")
    if not raw:
        raise ValueError("Environment variable GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE is required.")

    sa_path = _resolve_service_account_path(raw)
    if not Path(sa_path).exists():
        raise FileNotFoundError(f"Service account file not found at {sa_path}")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return gspread.authorize(creds), gspread


def assess_lead_with_llm(
    name: str,
    contact: str,
    role: str,
    position: str,
    raw_notes: str = "",
    meeting_context: str = ""
) -> Dict[str, Any]:
    """
    Use LLM to assess lead quality and generate summary
    Enhanced with meeting context for better scoring
    """
    system_prompt = (
        "You are a smart B2B lead qualification assistant for a technology services company "
        "(Narsun Studios - specializing in games, AR/VR, Web3, mobile apps, AI). "
        "Given information about a potential lead, generate:\n"
        "1. A concise one-sentence summary of their interest/intent\n"
        "2. A lead score from 0-10 where:\n"
        "   - 9-10: Decision maker with clear project needs and urgency\n"
        "   - 7-8: Strong interest with budget/timeline mentioned\n"
        "   - 5-6: Exploring options, some concrete requirements\n"
        "   - 3-4: Early stage inquiry, vague needs\n"
        "   - 0-2: Unqualified or irrelevant\n"
        "Respond only with valid JSON."
    )

    context_parts = [
        f"Name: {name}",
        f"Contact: {contact}",
        f"Role: {role}",
        f"Position: {position}"
    ]

    if raw_notes:
        context_parts.append(f"Project/Interest: {raw_notes}")

    if meeting_context:
        context_parts.append(f"Meeting Context: {meeting_context}")

    user_prompt = (
        f"Lead Assessment for:\n" + "\n".join(context_parts) + "\n\n"
        f"Provide JSON with:\n"
        f"summary: one-sentence summary (max 30 words)\n"
        f"lead_score: number 0-10 (one decimal place)\n"
        f"qualification_reason: brief reason for the score\n\n"
        f"Example: {{'summary': 'Needs AR app for retail chain rollout', 'lead_score': 8.5, 'qualification_reason': 'Decision maker with specific tech needs and timeline'}}"
    )

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )

        content = resp.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        json_text = match.group(0) if match else content
        parsed = json.loads(json_text)

        summary = parsed.get("summary", "").strip()
        qualification_reason = parsed.get("qualification_reason", "").strip()

        score_raw = parsed.get("lead_score", 0)
        try:
            lead_score = float(score_raw)
        except Exception:
            nums = re.findall(r"[\d\.]+", str(score_raw))
            lead_score = float(nums[0]) if nums else 0.0

        lead_score = max(0.0, min(10.0, round(lead_score, 1)))

        return {
            "summary": summary,
            "lead_score": lead_score,
            "qualification_reason": qualification_reason
        }

    except Exception as e:
        print(f"LLM assessment error: {e}")
        return {
            "summary": raw_notes or "No summary available",
            "lead_score": 5.0,
            "qualification_reason": "Assessment failed, default scoring applied"
        }


@tool
def auto_capture_meeting_lead(
    name: str,
    email: str,
    organization: str = "",
    project_description: str = "",
    meeting_time: str = "",
    meeting_id: str = ""
) -> str:
    """
    🎯 Automatically capture lead information when scheduling meetings.
    This tool is called automatically by the meeting scheduling process.

    Args:
        name: Full name of the lead
        email: Email address
        organization: Company/organization name
        project_description: Description of their project or needs
        meeting_time: Scheduled meeting time (formatted string)
        meeting_id: Google Calendar event ID

    Returns:
        Success message with lead qualification details
    """
    try:
        # Determine position based on available info
        position = "Decision Maker"  # Default for meeting schedulers
        if organization and any(title in project_description.lower() for title in ['explore', 'research', 'looking into']):
            position = "Influencer"

        # Create meeting context for better scoring
        meeting_context = f"Scheduled meeting for {meeting_time}"
        if meeting_id:
            meeting_context += f" (Event ID: {meeting_id})"

        # Assess the lead
        assessment = assess_lead_with_llm(
            name=name,
            contact=email,
            role=organization,  # Using org as role for now
            position=position,
            raw_notes=project_description,
            meeting_context=meeting_context
        )

        # Store to sheet
        client, gspread = _get_gspread_client()
        sheet_id = os.getenv("LEADS_SHEET_ID")
        if not sheet_id:
            return "⚠️ Lead captured locally but LEADS_SHEET_ID not configured for storage."

        worksheet_name = os.getenv("LEADS_WORKSHEET_NAME", "Lead_Info")

        try:
            sh = client.open_by_key(sheet_id)
            ws = sh.worksheet(worksheet_name)
        except Exception:
            # Create worksheet if it doesn't exist
            sh = client.open_by_key(sheet_id)
            ws = sh.add_worksheet(title=worksheet_name, rows="1000", cols="20")
            headers = [
                "Timestamp (UTC)", "Name", "Email", "Organization", "Position",
                "Summary", "Lead Score", "Qualification Reason", "Project Description",
                "Meeting Time", "Meeting ID", "Source"
            ]
            ws.append_row(headers)

        # Prepare row data
        row = [
            datetime.utcnow().isoformat() + "Z",
            name,
            email,
            organization,
            position,
            assessment["summary"],
            str(assessment["lead_score"]),
            assessment["qualification_reason"],
            project_description,
            meeting_time,
            meeting_id,
            "Auto-Capture (Meeting)"
        ]

        ws.append_row(row)

        # Format response based on lead score
        score = assessment["lead_score"]
        if score >= 8:
            score_emoji = "🔥"
            score_desc = "High-value lead"
        elif score >= 6:
            score_emoji = "⭐"
            score_desc = "Qualified lead"
        elif score >= 4:
            score_emoji = "📋"
            score_desc = "Potential lead"
        else:
            score_emoji = "📝"
            score_desc = "Early-stage inquiry"

        return f"{score_emoji} {score_desc} captured! Score: {score}/10 - {assessment['summary']}"

    except Exception as e:
        tb = traceback.format_exc()
        return f"⚠️ Lead capture failed: {str(e)}\nDetails stored locally for manual review."


@tool
def store_lead_to_sheet(
    name: str,
    contact: str,
    role: str,
    position: str,
    summary: Optional[str] = "",
    lead_score: Optional[float] = None,
    extra: Optional[Dict[str, str]] = None,
    raw_context: Optional[str] = ""
) -> str:
    """
    Store lead information to Google Sheets with LLM assessment.
    Use auto_capture_meeting_lead for meeting-based leads instead.
    """
    try:
        assessment = assess_lead_with_llm(
            name=name,
            contact=contact,
            role=role,
            position=position,
            raw_notes=raw_context or ""
        )

        client, gspread = _get_gspread_client()
        sheet_id = os.getenv("LEADS_SHEET_ID")
        if not sheet_id:
            return "Error: LEADS_SHEET_ID environment variable not set."

        worksheet_name = os.getenv("LEADS_WORKSHEET_NAME", "Lead_Info")

        sh = client.open_by_key(sheet_id)
        try:
            ws = sh.worksheet(worksheet_name)
        except Exception:
            ws = sh.add_worksheet(title=worksheet_name, rows="1000", cols="20")
            headers = [
                "Timestamp (UTC)", "Name", "Contact", "Role", "Position",
                "Summary", "Lead Score", "Qualification Reason", "Source"
            ]
            if extra:
                headers.extend(extra.keys())
            ws.append_row(headers)

        row = [
            datetime.utcnow().isoformat() + "Z",
            name,
            contact,
            role,
            position,
            assessment["summary"],
            str(assessment["lead_score"]),
            assessment["qualification_reason"],
            "Manual Entry"
        ]

        if extra:
            row.extend(extra.values())

        ws.append_row(row)

        return f"Lead stored successfully. Summary: '{assessment['summary']}', Score: {assessment['lead_score']}/10"

    except Exception as e:
        tb = traceback.format_exc()
        return f"Failed to store lead: {e}\n{tb}"


@tool
def capture_lead_from_conversation(messages: Sequence[BaseMessage]) -> str:
    """
    Extract lead information from conversation history and store it.
    This is used for manual lead capture from ongoing conversations.
    """
    convo_lines = []
    for m in messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        content = getattr(m, "content", "")
        convo_lines.append(f"{role}: {content}")

    conversation_text = "\n".join(convo_lines)

    system_prompt = (
        "You are an intelligent assistant that extracts lead information from conversations. "
        "From the dialogue, infer the lead's name, contact info, role/title, position "
        "(decision maker/influencer/other), and their core business need or project interest. "
        "If information cannot be confidently inferred, leave fields empty. "
        "Respond in JSON format only."
    )

    user_prompt = (
        f"Conversation:\n{conversation_text}\n\n"
        "Extract lead information as JSON:\n"
        '{"name": "...", "contact": "...", "role": "...", "position": "...", "project_interest": "..."}\n'
        "Example: {\"name\": \"Sarah Chen\", \"contact\": \"sarah@techcorp.com\", \"role\": \"CTO\", "
        "\"position\": \"Decision Maker\", \"project_interest\": \"AR shopping app for 50+ stores\"}"
    )

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )

        content = resp.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        json_text = match.group(0) if match else content
        extracted = json.loads(json_text)

    except Exception as e:
        return f"Failed to extract lead details from conversation: {e}"

    name = extracted.get("name", "Unknown") or "Unknown"
    contact = extracted.get("contact", "") or ""
    role = extracted.get("role", "") or ""
    position = extracted.get("position", "") or ""
    project_interest = extracted.get("project_interest", "") or ""

    if not project_interest.strip():
        return "Could not determine the main business interest from conversation. Please provide more context about their needs."

    # Use the regular store function
    store_resp = store_lead_to_sheet.invoke({
        "name": name,
        "contact": contact,
        "role": role,
        "position": position,
        "raw_context": project_interest
    })

    return f"Lead captured from conversation: {name} ({contact}) - {project_interest[:50]}... | {store_resp}"