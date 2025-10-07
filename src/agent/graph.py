"""
Main LangGraph agent for Narsun Studios with automatic lead capture
"""
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv

import sys
import json
from pathlib import Path

# Add src directory to Python path for absolute imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from tools.calendar_tools import (
    create_google_calendar_meeting,
    create_google_meet_meeting,
    create_recurring_meeting,
    list_upcoming_google_calendar_events,
    delete_google_calendar_event,
    update_google_calendar_event,
    schedule_by_natural_with_lead_capture,
    parse_datetime,
    parse_duration,
    suggest_alternative_times,
    list_availability_schedules,
    list_busy_times,
)
from tools.lead_tools import (
    store_lead_to_sheet,
    capture_lead_from_conversation,
    auto_capture_meeting_lead
)
from rag.retriever import retriever_tool

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    lead_context: dict  # Track potential lead information
    meeting_context: dict  # Track meeting-related context


# All available tools
tools = [
    # Enhanced meeting tools with lead capture
    schedule_by_natural_with_lead_capture,
    create_google_calendar_meeting,
    create_google_meet_meeting,
    create_recurring_meeting,

    # Calendar management
    list_upcoming_google_calendar_events,
    delete_google_calendar_event,
    update_google_calendar_event,

    # Date/time utilities
    parse_datetime,
    parse_duration,

    # Lead management
    store_lead_to_sheet,
    capture_lead_from_conversation,
    auto_capture_meeting_lead,

    # Company information
    retriever_tool
]

model_llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools=tools)


def model_call(state: AgentState) -> AgentState:
    """Main agent reasoning and tool calling"""
    # system_prompt = SystemMessage(content="""
    # You are a professional AI assistant for Narsun Studios—experts in 2D/3D games, Unreal Engine renderings, Web3, mobile & desktop apps, and AI solutions.
    #
    # **Core Capabilities:**
    # 1. **Smart Meeting Management** - Full Google Calendar integration with automatic lead capture
    # 2. **Company Knowledge** - RAG-powered answers about Narsun Studios services and experience
    # 3. **Lead Intelligence** - Automatic qualification and capture during conversations
    #
    # **Key Behaviors:**
    # - Be concise and professional (1-3 sentences by default)
    # - Use retriever_tool for company-specific questions
    # - **AUTOMATICALLY capture leads when scheduling meetings** - use schedule_by_natural_with_lead_capture
    # - Ask for: Full Name, Email, Organization, and preferred time for meetings
    # - Always end with engagement (project details or company background questions)
    #
    # **Meeting Flow with Auto Lead Capture:**
    # 1. Collect: Name, Email, Organization, preferred time
    # 2. Use schedule_by_natural_with_lead_capture (handles both meeting + lead capture)
    # 3. Provide meeting confirmation and next steps
    #
    # **Lead Capture Triggers:**
    # - Any meeting scheduling request
    # - Project inquiries with contact details
    # - Service discussions with business context
    #
    # Keep conversations contextual - never claim to "forget" previous messages.
    # """)
    with open("prompts/system_prompt.json", "r") as f:
        prompt_data = json.load(f)

    system_prompt = SystemMessage(content=prompt_data["content"])

    response = model_llm.invoke([system_prompt] + state["messages"])

    # Initialize context if missing
    new_state = {"messages": [response]}
    if "lead_context" not in state:
        new_state["lead_context"] = {}
    if "meeting_context" not in state:
        new_state["meeting_context"] = {}

    return new_state


def should_continue(state: AgentState) -> str:
    """Determine if we should continue to tools or end"""
    messages = state["messages"]
    last_message = messages[-1]

    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


# Build the graph
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("agent", model_call)
tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)

# Set entry point
graph.set_entry_point("agent")

# Add edges
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    }
)

graph.add_edge("tools", "agent")

# Compile the graph
graph = graph.compile()