"""
Professional RAG System for Apec Digital Solutions

Enhanced with:
- Better query understanding
- Contextual answer generation
- Specific case study extraction
- Smart content matching
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# CRITICAL: Load .env file FIRST before any OpenAI imports
load_dotenv()

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_core.documents import Document
import openai


# Configuration from environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAG_DOCUMENTS_PATH = PROJECT_ROOT / "rag_documents"
PERSIST_DIRECTORY = PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", "rag_store")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "apec_knowledge")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))
MIN_RELEVANCE = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.7"))

# Ensure directories exist
RAG_DOCUMENTS_PATH.mkdir(exist_ok=True)
PERSIST_DIRECTORY.mkdir(exist_ok=True)

# Initialize embeddings
embeddings = OpenAIEmbeddings(
    model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
)


class ProfessionalRAG:
    """
    Production-grade RAG system with contextual understanding
    """
    
    def __init__(self):
        self.vectorstore = None
        self.retriever = None
        self._initialize()
    
    def _initialize(self):
        """Initialize or load vector store"""
        try:
            if (PERSIST_DIRECTORY / "chroma.sqlite3").exists():
                print("📚 Loading existing knowledge base...")
                self.vectorstore = Chroma(
                    persist_directory=str(PERSIST_DIRECTORY),
                    collection_name=COLLECTION_NAME,
                    embedding_function=embeddings
                )
            else:
                print("🔨 Building new knowledge base...")
                self._build_vectorstore()
            
            if self.vectorstore:
                self.retriever = self.vectorstore.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={
                        "k": TOP_K,
                        "score_threshold": MIN_RELEVANCE
                    }
                )
                print(f"✅ RAG system ready with {self._get_doc_count()} chunks")
            else:
                print("⚠️ No knowledge base available")
                
        except Exception as e:
            print(f"❌ RAG initialization error: {e}")
            self.vectorstore = None
            self.retriever = None
    
    def _build_vectorstore(self):
        """Build vector store from documents"""
        documents = self._load_documents()
        
        if not documents:
            print("⚠️ No documents found in rag_documents/")
            return
        
        print(f"📄 Loaded {len(documents)} documents")
        
        chunks = self._chunk_documents(documents)
        print(f"✂️ Created {len(chunks)} chunks")
        
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(PERSIST_DIRECTORY),
            collection_name=COLLECTION_NAME
        )
        
        print("✅ Knowledge base built successfully!")
    
    def _load_documents(self) -> List[Document]:
        """Load all documents from rag_documents folder"""
        documents = []
        
        # Load text files
        for txt_file in RAG_DOCUMENTS_PATH.glob("*.txt"):
            try:
                loader = TextLoader(str(txt_file), encoding='utf-8')
                docs = loader.load()
                for doc in docs:
                    doc.metadata.update({
                        "source": txt_file.name,
                        "type": "text",
                        "filename": txt_file.name
                    })
                documents.extend(docs)
                print(f"  ✓ Loaded {txt_file.name}")
            except Exception as e:
                print(f"  ✗ Error loading {txt_file.name}: {e}")
        
        # Load PDF files
        for pdf_file in RAG_DOCUMENTS_PATH.glob("*.pdf"):
            try:
                loader = PyPDFLoader(str(pdf_file))
                docs = loader.load()
                for i, doc in enumerate(docs):
                    doc.metadata.update({
                        "source": pdf_file.name,
                        "type": "pdf",
                        "page": i + 1,
                        "filename": pdf_file.name
                    })
                documents.extend(docs)
                print(f"  ✓ Loaded {pdf_file.name} ({len(docs)} pages)")
            except Exception as e:
                print(f"  ✗ Error loading {pdf_file.name}: {e}")
        
        # Load JSON company info if exists
        json_file = PROJECT_ROOT / "apec_company_info.json"
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    company_data = json.load(f)
                
                content = self._json_to_text(company_data)
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": "apec_company_info.json",
                        "type": "structured_data",
                        "filename": "apec_company_info.json"
                    }
                )
                documents.append(doc)
                print(f"  ✓ Loaded apec_company_info.json")
            except Exception as e:
                print(f"  ✗ Error loading JSON: {e}")
        
        return documents
    
    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Smart document chunking with metadata preservation"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["chunk_size"] = len(chunk.page_content)
        
        return chunks
    
    def _json_to_text(self, data: dict, prefix: str = "") -> str:
        """Convert JSON company data to searchable text"""
        lines = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"\n{key.replace('_', ' ').title()}:")
                lines.append(self._json_to_text(value, prefix=f"{prefix}  "))
            elif isinstance(value, list):
                lines.append(f"\n{key.replace('_', ' ').title()}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(self._json_to_text(item, prefix=f"{prefix}  "))
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(lines)
    
    def _get_doc_count(self) -> int:
        """Get number of chunks in vector store"""
        if self.vectorstore:
            try:
                return self.vectorstore._collection.count()
            except:
                return 0
        return 0
    
    def _expand_query(self, query: str) -> str:
        """Use LLM to expand query for better retrieval"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Rewrite the user's query to be more detailed and include relevant keywords for semantic search. Keep it under 50 words."
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}"
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            expanded = response.choices[0].message.content.strip()
            print(f"🔍 Query expansion: '{query}' → '{expanded}'")
            return expanded
        except:
            return query


# Initialize RAG system
_rag_system = None

def get_rag_system() -> ProfessionalRAG:
    """Get or create RAG system instance"""
    global _rag_system
    if _rag_system is None:
        _rag_system = ProfessionalRAG()
    return _rag_system


@tool
def retriever_tool(query: str) -> str:
    """
    Search Apec Digital Solutions knowledge base with intelligent context matching.
    
    Use this tool to answer questions about:
    - Company services and capabilities
    - Technologies and expertise
    - Past projects and case studies
    - Pricing and engagement models
    - Team and company background
    - Specific service offerings
    
    Args:
        query: Question about Apec Digital Solutions
    
    Returns:
        Contextual answer with company-specific details
    """
    try:
        rag = get_rag_system()
        
        if not rag.retriever:
            return (
                "I apologize, but the knowledge base is not available right now. "
                "Please ensure company documents are in the rag_documents folder."
            )
        
        # Expand query for better matching
        expanded_query = rag._expand_query(query)
        
        # Search with expanded query and lower threshold for specific queries
        docs_with_scores = rag.vectorstore.similarity_search_with_relevance_scores(
            expanded_query, 
            k=5  # Get more results for better context
        )
        
        if not docs_with_scores:
            return (
                f"I couldn't find specific information about '{query}' in our knowledge base. "
                "Could you rephrase your question or ask about our core services?"
            )
        
        # Collect ALL relevant content (lower threshold for specific queries)
        relevant_content = []
        sources_used = set()
        
        # Accept results with score >= 0.35 (more lenient for specific queries)
        for doc, score in docs_with_scores:
            if score >= 0.35:
                content = doc.page_content.strip()
                source = doc.metadata.get("source", "Unknown")
                
                relevant_content.append(content)
                sources_used.add(source)
        
        if not relevant_content:
            return (
                f"I found some information but it wasn't relevant enough to answer your specific question about '{query}'. "
                "Could you rephrase or ask about our general services?"
            )
        
        # Combine all relevant content (up to 3000 chars for better context)
        combined_content = "\n\n---\n\n".join(relevant_content[:3])[:3000]
        
        # Use LLM to create CONTEXTUAL, SPECIFIC answer
        summary_prompt = f"""You are answering a question about Apec Digital Solutions based on their company documents.

User's Question: {query}

Company Information from Documents:
{combined_content}

Instructions:
1. Answer the user's SPECIFIC question directly
2. Use 2-3 bullet points maximum
3. Each bullet should be ONE line: "Category – Specific detail with example/number"
4. Include specific examples, case studies, or numbers from the documents when available
5. Make it relevant to what they asked (don't give generic service lists)
6. Keep total response under 150 words
7. If they ask about a specific service, focus on that service with details
8. Sound professional and conversational

Format:
[Brief intro sentence]
• Bullet 1 – Specific capability with example/result
• Bullet 2 – Another relevant capability with detail
• Bullet 3 (optional) – Third point if needed

[Optional follow-up question]

Example for "Do you do business automation?":
"Yes, we specialize in business automation:
• AI-Powered Chatbots – Reduced support costs 60% for TechRetail's e-commerce platform
• Process Automation – Saved $2M annually for manufacturing clients with ML forecasting
• Workflow Systems – Built multi-agent LangChain solutions for enterprise clients

Would you like to discuss your automation needs?"

Now answer their question using the company information provided."""
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional company representative. Always use specific details from documents. Be concise but informative."
                },
                {
                    "role": "user", 
                    "content": summary_prompt
                }
            ],
            temperature=0.4,  # Slightly higher for more natural responses
            max_tokens=300
        )
        
        contextual_answer = response.choices[0].message.content.strip()
        
        # Add compact source attribution
        sources_list = ", ".join(sorted(sources_used))
        final_response = f"{contextual_answer}\n\n*Source: {sources_list}*"
        
        return final_response
        
    except Exception as e:
        print(f"❌ Retriever tool error: {e}")
        import traceback
        traceback.print_exc()
        return (
            f"I encountered an error searching for information about '{query}'. "
            "Please try rephrasing your question."
        )


# CLI for testing
if __name__ == "__main__":
    print("🧠 Professional RAG System - Testing")
    print("=" * 50)
    
    rag = get_rag_system()
    
    # Test multiple queries
    test_queries = [
        "What services does Apec Digital Solutions offer?",
        "Do you offer services related to automating business solutions?",
        "What's your experience with AI and machine learning?",
        "Give me a brief overview of this company"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("=" * 50)
        result = retriever_tool.invoke({"query": query})
        print(result)
        print("\n" + "=" * 50)
    
    print("\n✅ RAG system test complete!")