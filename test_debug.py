import sys
from pathlib import Path

src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from agent.graph import graph

test_input = {
    "messages": [{"role": "user", "content": "What AI services does Apec Digital Solutions offer?"}],
    "lead_context": {},
    "meeting_context": {}
}

print(" Testing with detailed query...")
print("=" * 60)

result = graph.invoke(test_input)

print("\n Messages in result:")
for i, msg in enumerate(result["messages"]):
    print(f"\nMessage {i+1}:")
    print(f"  Type: {type(msg).__name__}")
    if hasattr(msg, 'tool_calls'):
        print(f"  Tool calls: {msg.tool_calls}")
    if hasattr(msg, 'content'):
        print(f"  Content: {msg.content[:200]}...")

print("\n" + "=" * 60)
