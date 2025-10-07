# Narsun Studios LangGraph Agent

An intelligent AI assistant for Narsun Studios with automatic lead capture, Google Calendar integration, and company knowledge retrieval.

## 🚀 Features

- **Smart Meeting Scheduling** - Natural language meeting creation with Google Calendar & Google Meet
- **Automatic Lead Capture** - Intelligent lead qualification and storage during meetings
- **Company Knowledge Base** - RAG-powered answers about Narsun Studios services
- **Lead Management** - Google Sheets integration for lead tracking and scoring
- **LangGraph Studio Ready** - Optimized for LangGraph Cloud deployment

## 📁 Project Structure

```
narsun-agent/
├── langgraph.json              # LangGraph Studio configuration
├── src/
│   ├── agent/
│   │   └── graph.py            # Main agent graph
│   ├── tools/
│   │   ├── calendar_tools.py   # Enhanced calendar tools
│   │   └── lead_tools.py       # Lead management tools
│   ├── rag/
│   │   └── retriever.py        # Company knowledge retrieval
│   └── utils/
│       └── calendar_creator.py # Google Calendar integration
├── rag_documents/              # Company PDF documents
├── credentials.json            # Google OAuth credentials
├── narsungpt-service-account.json # Google Sheets service account
└── .env                        # Environment variables
```

## 🛠️ Setup Instructions

### 1. Project Setup

```bash
# Clone or create the project directory
mkdir narsun-agent
cd narsun-agent

# Create the directory structure
mkdir -p src/{agent,tools,rag,utils} rag_documents
```

### 2. Google Calendar Setup

1. **Enable Google Calendar API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select a project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download as `credentials.json`

2. **Place credentials:**
   ```bash
   # Place your downloaded credentials.json in the project root
   cp ~/Downloads/credentials.json ./credentials.json
   ```

### 3. Google Sheets Setup (Lead Storage)

1. **Create Service Account:**
   - In Google Cloud Console, go to IAM & Admin > Service Accounts
   - Create a new service account
   - Generate and download JSON key
   - Rename to `narsungpt-service-account.json`

2. **Create Google Sheet:**
   - Create a new Google Sheet for lead storage
   - Share it with your service account email (found in the JSON)
   - Copy the sheet ID from the URL

### 4. Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values
nano .env
```

Required environment variables:
```bash
OPENAI_API_KEY=sk-...
GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE=./narsungpt-service-account.json
LEADS_SHEET_ID=your_google_sheet_id_from_url
LEADS_WORKSHEET_NAME=Lead_Info
```

### 5. Company Documents

```bash
# Add your company PDF documents to rag_documents/
cp "path/to/Narsun Studios Profile.pdf" ./rag_documents/
```

## 🧪 Local Testing

### Test Calendar Integration

```python
# test_calendar.py
from src.utils.calendar_creator import GoogleCalendarMeetingCreator
from datetime import datetime, timedelta

def test_calendar():
    calendar = GoogleCalendarMeetingCreator()
    
    # Test basic meeting creation
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    
    event = calendar.create_meeting_with_google_meet(
        title="Test Meeting",
        description="Testing calendar integration",
        start_time=start_time,
        end_time=end_time,
        attendees=["test@example.com"]
    )
    
    if event:
        print("✅ Calendar integration working!")
        print(f"Event ID: {event['id']}")
        return event['id']
    else:
        print("❌ Calendar test failed")
        return None

if __name__ == "__main__":
    test_calendar()
```

### Test Lead Capture

```python
# test_leads.py
from src.tools.lead_tools import auto_capture_meeting_lead

def test_lead_capture():
    result = auto_capture_meeting_lead.invoke({
        "name": "John Doe",
        "email": "john@example.com", 
        "organization": "Tech Corp",
        "project_description": "Need AR app for retail stores",
        "meeting_time": "2024-08-16 14:00 EST",
        "meeting_id": "test-meeting-123"
    })
    
    print("Lead capture result:", result)

if __name__ == "__main__":
    test_lead_capture()
```

### Test RAG System

```python
# test_rag.py
from src.rag.retriever import retriever_tool

def test_rag():
    result = retriever_tool.invoke({
        "query": "What services does Narsun Studios offer?"
    })
    
    print("RAG result:", result)

if __name__ == "__main__":
    test_rag()
```

### Test Complete Agent

```python
# test_agent.py
from src.agent.graph import graph

def test_agent():
    # Test meeting scheduling with lead capture
    test_input = {
        "messages": [{
            "role": "user",
            "content": "I'd like to schedule a meeting. My name is Sarah Chen, email sarah@techcorp.com, from TechCorp. We need help with an AR shopping app for our retail chain. Can we meet tomorrow at 2pm for 1 hour?"
        }]
    }
    
    result = graph.invoke(test_input)
    print("Agent response:", result["messages"][-1]["content"])

if __name__ == "__main__":
    test_agent()
```

## 🚀 LangGraph Studio Deployment

### 1. Prepare for Studio

```bash
# Ensure all dependencies are listed correctly
cat langgraph.json

# Test locally first
langgraph dev
```

### 2. Upload to LangGraph Cloud

1. Open LangGraph Studio
2. Create new project
3. Upload project files:
   - All `src/` directory contents
   - `langgraph.json`
   - `credentials.json`
   - `narsungpt-service-account.json`
   - Company documents in `rag_documents/`

### 3. Configure Environment

In LangGraph Studio, set environment variables:
- `OPENAI_API_KEY`
- `GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE`
- `LEADS_SHEET_ID` 
- `LEADS_WORKSHEET_NAME`

### 4. Deploy and Test

1. Deploy the agent
2. Test with sample conversations
3. Verify lead capture is working
4. Check calendar integration

## 🎯 Key Improvements Over Original

### Automatic Lead Capture
- **Before:** Manual lead capture via separate tool calls
- **After:** Automatic capture during meeting scheduling
- **Benefit:** Higher conversion rates, no missed leads

### Enhanced Meeting Flow
- **Before:** Basic scheduling without context
- **After:** Rich meeting creation with attendee details, project context, and automatic lead scoring
- **Benefit:** Better preparation and follow-up

### Production Ready Structure  
- **Before:** Flat file structure, hardcoded paths
- **After:** Proper package structure, environment configuration, error handling
- **Benefit:** Scalable, maintainable, deployable

### Smart Lead Scoring
- **Before:** Manual scoring
- **After:** LLM-powered assessment with business context
- **Benefit:** Better lead prioritization

## 🔧 Usage Examples

### Schedule Meeting with Auto Lead Capture
```
User: "Hi, I'm Alex from StartupCo. We need help building a VR training app. Can we meet Friday at 3pm?"

Agent: Uses schedule_by_natural_with_lead_capture automatically
- Creates calendar meeting
- Captures lead (Alex, StartupCo, VR training needs) 
- Scores lead based on business context
- Provides meeting confirmation
```

### Company Information Query
```
User: "What's Narsun's experience with AR projects?"

Agent: Uses retriever_tool
- Searches company documents
- Returns relevant project examples
- Provides specific capabilities
```

## 🚨 Troubleshooting

### Common Issues

1. **Calendar authentication fails:**
   ```bash
   # Delete existing token and re-authenticate
   rm token.json
   python test_calendar.py
   ```

2. **RAG returns no results:**
   ```bash
   # Check if documents are in rag_documents/
   ls rag_documents/
   # Ensure PDF files are readable
   ```

3. **Lead capture fails:**
   ```bash
   # Verify Google Sheets access
   # Check service account permissions
   # Ensure sheet ID is correct
   ```

### Debug Mode

Set environment variable for detailed logging:
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT=narsun_agent_debug
```

## 📊 Monitoring & Analytics

The agent automatically tracks:
- Meeting creation success rates
- Lead capture effectiveness
- Lead quality scores
- User interaction patterns

Access metrics through LangSmith dashboard when tracing is enabled.

---

**Ready to deploy!** Follow the setup steps, test locally, then deploy to LangGraph Cloud for production use.