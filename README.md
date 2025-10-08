# AI-Powered Company Assistant

> Professional LangGraph agent with intelligent lead capture, meeting scheduling, and company knowledge base

[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-blue)](https://github.com/langchain-ai/langgraph)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🎯 Overview

An enterprise-grade AI assistant that combines RAG (Retrieval Augmented Generation), CRM, and calendar integration to provide intelligent customer interactions, automatic lead qualification, and seamless meeting scheduling.

**Perfect for:** Digital agencies, consulting firms, SaaS companies, and service providers looking to automate lead capture and client interactions.

## ✨ Key Features

### 🤖 Intelligent Company Knowledge
- **Advanced RAG System**: Semantic search with ChromaDB vector database
- **Query Expansion**: AI-powered query rewriting for better results
- **Multi-format Support**: PDF, TXT, and JSON document processing
- **Source Citations**: Always provides referenced answers

### 📅 Smart Meeting Scheduling
- **Google Calendar Integration**: Direct calendar event creation
- **Google Meet Links**: Automatic video conference generation
- **Natural Language**: "Schedule meeting tomorrow at 2pm" → ✅ Booked
- **Time Zone Support**: Intelligent time zone handling

### 🎯 Automatic Lead Capture
- **Supabase CRM**: Professional PostgreSQL database
- **AI Lead Scoring**: GPT-4 powered qualification (0-10 scale)
- **Real-time Dashboard**: Beautiful Supabase admin interface
- **Lead Status Tracking**: Hot 🔥, Qualified ⭐, Nurture 📋, Cold 🧊

### 🔧 Production-Ready Architecture
- **LangGraph Framework**: State-based agent orchestration
- **Proper Error Handling**: Comprehensive exception management
- **Environment Configuration**: Secure .env setup
- **Modular Design**: Clean separation of concerns

## 🚀 Quick Start

### Prerequisites

```bash
# Requirements
- Python 3.9+
- OpenAI API key
- Google Cloud project (for Calendar API)
- Supabase account (free tier available)
```

### Installation

1. **Clone Repository**
```bash
git clone <your-repo-url>
cd company-agent
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - OPENAI_API_KEY
# - SUPABASE_URL
# - SUPABASE_KEY
# - COMPANY_NAME
```

4. **Setup Google Calendar**
```bash
# Place your OAuth credentials
cp ~/Downloads/credentials.json ./credentials.json

# Authenticate (opens browser)
python auth_calendar.py
```

5. **Add Company Documents**
```bash
# Add your PDFs, TXTs to rag_documents/
cp "Company Profile.pdf" rag_documents/
cp company_info.json rag_documents/
```

6. **Initialize Database**
```bash
# Create Supabase table (run this SQL in Supabase dashboard)
CREATE TABLE leads (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  company TEXT,
  interest TEXT,
  lead_score FLOAT DEFAULT 0,
  status TEXT DEFAULT 'Cold',
  qualification_notes TEXT,
  meeting_id TEXT,
  meeting_time TEXT,
  meeting_link TEXT,
  source TEXT DEFAULT 'Unknown',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email ON leads(email);
CREATE INDEX idx_status ON leads(status);
CREATE INDEX idx_lead_score ON leads(lead_score DESC);
```

## 📖 Usage

### Running the Agent

**Option 1: LangGraph Studio (Recommended)**
```bash
langgraph dev
# Open http://localhost:8000
```

**Option 2: Python Script**
```python
from src.agent.graph import graph

result = graph.invoke({
    "messages": [{"role": "user", "content": "Tell me about your services"}],
    "lead_context": {},
    "meeting_context": {}
})

print(result["messages"][-1].content)
```

**Option 3: LangGraph Cloud**
```bash
langgraph deploy
```

### Example Conversations

**Company Information Query:**
```
User: What services do you offer?

AI: We specialize in three core areas:
• AI/ML Solutions – Custom chatbots, LLM integrations, automation
• Enterprise Software – Full-stack web/mobile apps, cloud-native architecture  
• Digital Transformation – Process automation, legacy modernization, consulting

Would you like to schedule a consultation?
```

**Meeting Scheduling:**
```
User: I need help with AI automation. Can we schedule a call?

AI: I'd be happy to schedule a consultation. Please provide:
• Your full name
• Email address
• Company name
• Preferred meeting time

User: John Smith, john@techcorp.com, TechCorp, need customer service automation, tomorrow at 2pm

AI: ✅ Meeting scheduled for October 9, 2025 at 2:00 PM EST with john@techcorp.com
```

## 🏗️ Architecture

```
company-agent/
├── src/
│   ├── agent/
│   │   └── graph.py              # Main LangGraph agent
│   ├── tools/
│   │   ├── calendar_tools.py     # Google Calendar integration
│   │   └── lead_tools.py         # CRM and lead management
│   ├── rag/
│   │   └── retriever.py          # RAG system with ChromaDB
│   ├── integrations/
│   │   └── supabase_crm.py       # Supabase database client
│   └── utils/
│       └── calendar_creator.py   # Google Calendar helper
├── rag_documents/                # Company knowledge base
├── prompts/
│   └── system_prompt.json        # Agent instructions
├── langgraph.json                # LangGraph configuration
├── requirements.txt              # Python dependencies
└── .env                          # Environment variables
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
COMPANY_NAME=Your Company Name

# Optional
EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
RAG_TOP_K=3
```

### Customization

**Update Company Information:**
1. Edit `rag_documents/apec_company_info.json`
2. Add PDFs to `rag_documents/`
3. Restart agent to rebuild knowledge base

**Modify Agent Behavior:**
- Edit `prompts/system_prompt.json` for response style
- Adjust `src/agent/graph.py` for workflow logic
- Customize tools in `src/tools/`

## 📊 Features in Detail

### Lead Scoring Algorithm

The AI automatically scores leads 0-10 based on:
- **9-10 (🔥 Hot)**: Decision maker, clear budget/timeline, specific needs
- **7-8 (⭐ Qualified)**: Strong interest, defined requirements
- **5-6 (📋 Nurture)**: Qualified prospect, general interest
- **3-4 (🧊 Cold)**: Early inquiry, vague needs

### Meeting Scheduling Flow

1. User expresses interest in meeting
2. Agent collects: name, email, company, needs, time preference
3. Validates availability (business hours check)
4. Creates Google Calendar event + Meet link
5. **Automatically captures lead** with AI scoring
6. Stores in Supabase with meeting details

### RAG System

- **Semantic Search**: Finds relevant content using vector embeddings
- **Query Expansion**: AI rewrites queries for better matching
- **Relevance Filtering**: Only returns high-confidence results (>0.4 score)
- **Source Attribution**: Always cites document sources

## 🧪 Testing

```bash
# Test RAG system
python src/rag/retriever.py

# Test lead capture
python src/tools/lead_tools.py

# Test calendar integration
python src/utils/calendar_creator.py

# Test full agent
python src/agent/graph.py
```

## 🐛 Troubleshooting

### Common Issues

**"RAG returns no results"**
```bash
# Rebuild vector database
rm -rf rag_store/
python src/rag/retriever.py
```

**"Google Calendar authentication failed"**
```bash
# Re-authenticate
rm token.json
python auth_calendar.py
```

**"Supabase connection error"**
```bash
# Verify credentials
echo $SUPABASE_URL
echo $SUPABASE_KEY
# Check table exists in Supabase dashboard
```

## 📈 Monitoring

**LangSmith Integration:**
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_PROJECT=company_agent
export LANGSMITH_API_KEY=ls__...
```

**Supabase Dashboard:**
- View all leads: `https://supabase.com/dashboard`
- Real-time updates
- SQL editor for custom queries
- Automatic backups

## 🔐 Security

- ✅ OAuth 2.0 for Google Calendar
- ✅ Environment variable configuration
- ✅ Supabase Row Level Security (RLS)
- ✅ No hardcoded credentials
- ✅ Parameterized SQL queries

## 🎯 Best Practices

1. **Keep documents updated**: Regularly refresh company info in `rag_documents/`
2. **Monitor lead quality**: Review AI scoring accuracy in Supabase
3. **Customize prompts**: Adjust `system_prompt.json` for your brand voice
4. **Test regularly**: Run test conversations before deploying changes
5. **Backup database**: Use Supabase automatic backups

## 🚀 Deployment

### LangGraph Cloud

```bash
# Deploy to LangGraph Cloud
langgraph deploy

# Configure environment variables in dashboard
# Upload credentials.json and token.json
```

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["langgraph", "dev"]
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Email: esharehmantech@gmail.com

## 🌟 Roadmap

- [ ] Slack integration
- [ ] Email automation
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] WhatsApp integration
- [ ] Voice call integration

---

**Built with ❤️ using LangGraph, OpenAI, and Supabase**