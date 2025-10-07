import sys
from pathlib import Path

src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from rag.retriever import get_rag_system

print("🧪 Testing RAG Search Directly")
print("=" * 60)

rag = get_rag_system()

if not rag.vectorstore:
    print(" Vector store not initialized!")
    sys.exit(1)

print(f" Vector store has {rag._get_doc_count()} chunks")

test_query = "What services does Apec Digital Solutions offer?"
print(f"\n Query: {test_query}\n")

docs_with_scores = rag.vectorstore.similarity_search_with_relevance_scores(test_query, k=5)

print(f" Found {len(docs_with_scores)} results:\n")

for i, (doc, score) in enumerate(docs_with_scores, 1):
    print(f"Result #{i}")
    print(f"  Score: {score:.4f}")
    print(f"  Source: {doc.metadata.get('source', 'Unknown')}")
    print(f"  Content: {doc.page_content[:150]}...")
    print()
