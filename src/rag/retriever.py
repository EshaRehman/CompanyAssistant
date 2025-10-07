"""
RAG retriever for Narsun Studios company information
"""
import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool


# Initialize embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAG_DOCUMENTS_PATH = PROJECT_ROOT / "rag_documents"
PERSIST_DIRECTORY = PROJECT_ROOT / "rag_store"
COLLECTION_NAME = "narsun_knowledge"

# Ensure directories exist
RAG_DOCUMENTS_PATH.mkdir(exist_ok=True)
PERSIST_DIRECTORY.mkdir(exist_ok=True)


def initialize_vectorstore():
    """Initialize or load the vector store with company documents"""
    try:
        # Look for PDF files in rag_documents directory
        pdf_files = list(RAG_DOCUMENTS_PATH.glob("*.pdf"))

        if not pdf_files:
            print("Warning: No PDF files found in rag_documents directory")
            print(f"Please add company documents to: {RAG_DOCUMENTS_PATH}")
            return None

        # Check if vectorstore already exists
        if (PERSIST_DIRECTORY / "chroma.sqlite3").exists():
            print("Loading existing vector store...")
            vectorstore = Chroma(
                persist_directory=str(PERSIST_DIRECTORY),
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings
            )
            return vectorstore

        print("Creating new vector store...")

        # Load and process documents
        all_documents = []
        for pdf_file in pdf_files:
            print(f"Processing: {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file))
            documents = loader.load()
            all_documents.extend(documents)

        if not all_documents:
            print("No documents loaded successfully")
            return None

        print(f"Loaded {len(all_documents)} document pages")

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        splits = text_splitter.split_documents(all_documents)
        print(f"Created {len(splits)} text chunks")

        # Create vector store
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=str(PERSIST_DIRECTORY),
            collection_name=COLLECTION_NAME
        )

        print("Vector store created successfully!")
        return vectorstore

    except Exception as e:
        print(f"Error initializing vector store: {e}")
        return None


# Initialize the retriever
_vectorstore = None
_retriever = None

def get_retriever():
    """Get or create the document retriever"""
    global _vectorstore, _retriever

    if _retriever is None:
        _vectorstore = initialize_vectorstore()
        if _vectorstore:
            _retriever = _vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
        else:
            print("Warning: Could not initialize retriever")

    return _retriever


@tool
def retriever_tool(query: str) -> str:
    """
    Search and retrieve information from Narsun Studios company documents.

    Use this tool to answer questions about:
    - Company services and capabilities
    - Past projects and portfolio
    - Technical expertise and technologies
    - Team information and experience
    - Company background and history

    Args:
        query: The search query about Narsun Studios

    Returns:
        Relevant information from company documents
    """
    try:
        retriever = get_retriever()

        if not retriever:
            return (
                "I apologize, but I don't have access to the company knowledge base right now. "
                "Please ensure the company documents are properly loaded in the rag_documents folder. "
                "For general information, Narsun Studios specializes in 2D/3D games, Unreal Engine "
                "renderings, Web3 solutions, mobile & desktop applications, and AI services."
            )

        # Retrieve relevant documents
        docs = retriever.invoke(query)

        if not docs:
            return (
                f"I couldn't find specific information about '{query}' in our company documents. "
                "Could you rephrase your question or ask about our general services like game development, "
                "AR/VR solutions, Web3 projects, or AI implementations?"
            )

        # Format the results
        results = []
        for i, doc in enumerate(docs):
            content = doc.page_content.strip()
            if content:  # Only include non-empty content
                results.append(f"Document {i+1}:\n{content}")

        if not results:
            return "I found some relevant documents but couldn't extract meaningful content. Please try rephrasing your question."

        # Combine results with clear separation
        combined_results = "\n\n---\n\n".join(results)

        # Add a helpful note
        response = f"Based on our company documents:\n\n{combined_results}"

        return response

    except Exception as e:
        print(f"Error in retriever_tool: {e}")
        return (
            f"I encountered an error while searching for information about '{query}'. "
            "Please try again or contact our team directly for assistance with your inquiry."
        )


# Utility function to add new documents
def add_documents_to_vectorstore(pdf_paths: list):
    """
    Add new PDF documents to the existing vector store

    Args:
        pdf_paths: List of paths to PDF files to add
    """
    try:
        vectorstore = get_retriever()._vectorstore if get_retriever() else None

        if not vectorstore:
            print("No existing vector store found. Initialize first.")
            return False

        # Load new documents
        new_documents = []
        for pdf_path in pdf_paths:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            new_documents.extend(docs)

        if not new_documents:
            print("No new documents loaded")
            return False

        # Split new documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(new_documents)

        # Add to existing vector store
        vectorstore.add_documents(splits)

        print(f"Added {len(splits)} new chunks to vector store")
        return True

    except Exception as e:
        print(f"Error adding documents: {e}")
        return False


if __name__ == "__main__":
    # Test the retriever
    print("Testing RAG retriever...")
    test_query = "What services does Narsun Studios offer?"
    result = retriever_tool.invoke({"query": test_query})
    print(f"Test query: {test_query}")
    print(f"Result: {result}")