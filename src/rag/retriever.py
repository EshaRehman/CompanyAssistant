"""
Professional RAG System for Apec Digital Solutions

Advanced features:
- Semantic chunking with overlap
- Metadata filtering
- Query expansion (LLM rewrites query)
- Relevance scoring
- Source citations
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
    Production-grade RAG system
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
    
    def search(
        self,
        query: str,
        use_expansion: bool = True,
        top_k: int = TOP_K
    ) -> List[Dict[str, Any]]:
        """Search knowledge base with advanced features"""
        if not self.retriever:
            return []
        
        try:
            search_query = self._expand_query(query) if use_expansion else query
            
            docs_with_scores = self.vectorstore.similarity_search_with_relevance_scores(
                search_query,
                k=top_k
            )
            
            results = []
            for doc, score in docs_with_scores:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": round(score, 3),
                    "source": doc.metadata.get("source", "Unknown")
                })
            
            return results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []


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
    Search Apec Digital Solutions knowledge base.
    
    Use this tool to answer questions about:
    - Company services and capabilities
    - Technologies and expertise
    - Past projects and case studies
    - Pricing and engagement models
    - Team and company background
    
    Args:
        query: Question about Apec Digital Solutions
    
    Returns:
        Professional answer with source citations
    """
    try:
        rag = get_rag_system()
        
        if not rag.retriever:
            return (
                "I apologize, but the knowledge base is not available right now. "
                "Please ensure company documents are in the rag_documents folder."
            )
        
        # Use vectorstore directly with relevance scores
        docs_with_scores = rag.vectorstore.similarity_search_with_relevance_scores(query, k=3)
        
        if not docs_with_scores:
            return (
                f"I couldn't find specific information about '{query}' in our knowledge base. "
                "Could you rephrase your question or ask about our core services?"
            )
        
        answer_parts = []
        sources_used = set()
        
        # Accept results with score >= 0.4 (OpenAI embeddings typically score 0.4-0.7)
        for doc, score in docs_with_scores:
            if score >= 0.4:
                content = doc.page_content.strip()
                source = doc.metadata.get("source", "Unknown")
                
                answer_parts.append(f"**From {source}:**\n{content}\n")
                sources_used.add(source)
        
        if not answer_parts:
            return "I found some information but it wasn't relevant enough. Could you rephrase your question?"
        
        answer = "\n---\n\n".join(answer_parts)
        sources_list = "\n".join([f"• {s}" for s in sorted(sources_used)])
        
        response = f"{answer}\n\n📚 **Sources:**\n{sources_list}"
        
        return response
        
    except Exception as e:
        print(f"❌ Retriever tool error: {e}")
        return (
            f"I encountered an error searching for information about '{query}'. "
            "Please try rephrasing your question."
        )


# CLI for testing
if __name__ == "__main__":
    print("🧠 Professional RAG System - Testing")
    print("=" * 50)
    
    rag = get_rag_system()
    
    test_query = "What services does Apec Digital Solutions offer?"
    print(f"\n🔍 Test Query: {test_query}")
    print("\n" + "=" * 50)
    
    result = retriever_tool.invoke({"query": test_query})
    print(result)
    
    print("\n" + "=" * 50)
    print("✅ RAG system test complete!")