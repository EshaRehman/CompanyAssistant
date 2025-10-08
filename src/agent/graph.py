"""
Apex Digital Solutions AI Assistant
Production-grade LangGraph agent with strict RAG usage

Key features:
- Mandatory RAG for all company questions
- Automatic lead qualification
- Google Calendar integration
- Clean architecture
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
import sys
import json
import os
from pathlib import Path

# Setup paths
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import tools
from tools.calendar_tools import (
    create_google_calendar_meeting,
    create_google_meet_meeting,
    list_upcoming_google_calendar_events,
    schedule_by_natural_with_lead_capture,
    parse_datetime,
    parse_duration
)

from tools.lead_tools import (
    auto_capture_meeting_lead,
    store_lead_to_sheet,
    capture_lead_from_conversation
)

from rag.retriever import retriever_tool

load_dotenv()


class AgentState(TypedDict):
    """
    Agent state with conversation tracking
    
    Attributes:
        messages: Conversation history
        lead_context: Tracked lead information
        meeting_context: Meeting scheduling context
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    lead_context: dict
    meeting_context: dict


# All available tools
tools = [
    # Company knowledge (RAG) - PRIORITY TOOL
    retriever_tool,
    
    # Lead management (Supabase CRM)
    auto_capture_meeting_lead,
    store_lead_to_sheet,
    capture_lead_from_conversation,
    
    # Meeting scheduling (Google Calendar)
    schedule_by_natural_with_lead_capture,
    create_google_calendar_meeting,
    create_google_meet_meeting,
    list_upcoming_google_calendar_events,
    
    # Utilities
    parse_datetime,
    parse_duration
]

# Initialize LLM with tools
model_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    model_kwargs={"top_p": 0.9}  # Add some variety while staying focused
).bind_tools(tools=tools)


def model_call(state: AgentState) -> AgentState:
    """
    Main agent reasoning node with strict RAG enforcement
    
    Loads system prompt and generates responses with tool calls
    """
    # Load system prompt
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.json"
    
    try:
        with open(prompt_path, "r", encoding='utf-8') as f:
            prompt_data = json.load(f)
        system_content = prompt_data["content"]
    except Exception as e:
        print(f"⚠️ Could not load system prompt: {e}")
        # Strict fallback prompt
        company_name = os.getenv("COMPANY_NAME", "Apex Digital Solutions")
        system_content = f"""You are the professional AI assistant for {company_name}.

🚨 CRITICAL: ALWAYS call retriever_tool for ANY question about the company.

Core capabilities:
1. Answer company questions using retriever_tool (MANDATORY - use it for EVERY company question)
2. Schedule meetings with automatic lead capture
3. Qualify and store leads in Supabase CRM

NEVER answer company questions from memory. ALWAYS use retriever_tool first.

Be professional, concise, and helpful. Format responses with 2-3 bullets maximum."""
    
    system_prompt = SystemMessage(content=system_content)
    
    # Generate response
    response = model_llm.invoke([system_prompt] + state["messages"])
    
    # Update state
    new_state = {"messages": [response]}
    if "lead_context" not in state:
        new_state["lead_context"] = {}
    if "meeting_context" not in state:
        new_state["meeting_context"] = {}
    
    return new_state


def should_continue(state: AgentState) -> str:
    """
    Routing logic: determine if we need to call tools
    
    Returns:
        "continue" if tools need to be called, "end" otherwise
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"


# Build the graph
print("🔨 Building LangGraph agent...")

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("agent", model_call)
tool_node = ToolNode(tools=tools)
graph.add_node("tools", tool_node)

# Set entry point
graph.set_entry_point("agent")

# Add conditional edges
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    }
)

# Tool outputs always go back to agent
graph.add_edge("tools", "agent")

# Compile the graph
graph = graph.compile()

print("✅ LangGraph agent compiled successfully!")


# Test function
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(f"🚀 {os.getenv('COMPANY_NAME', 'Apex Digital Solutions')} AI Assistant")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "What services does Apec Digital Solutions offer?",
        "Do you offer services related to automating business solutions?",
        "Give me a brief overview of this company"
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing: {query}")
        print("=" * 60)
        
        test_input = {
            "messages": [{"role": "user", "content": query}],
            "lead_context": {},
            "meeting_context": {}
        }
        
        try:
            result = graph.invoke(test_input)
            
            # Show if retriever_tool was called
            tool_calls_made = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_made.append(tc['name'])
            
            if tool_calls_made:
                print(f"✅ Tools called: {', '.join(set(tool_calls_made))}")
            
            # Show final response
            final_response = result["messages"][-1].content
            print(f"\n🤖 Response:")
            print("-" * 60)
            print(final_response)
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📊 System Status:")
    print(f"   Tools available: {len(tools)}")
    print(f"   Graph compiled: ✅")
    print(f"   RAG store: {os.getenv('CHROMA_PERSIST_DIR', './rag_store')}")
    print("=" * 60)