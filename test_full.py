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

print(" Testing Agent with Full Output")
print("=" * 60)

result = graph.invoke(test_input)

print("\n FULL CONVERSATION:\n")

for i, msg in enumerate(result["messages"], 1):
    print(f"{'='*60}")
    print(f"Message {i}: {type(msg).__name__}")
    print(f"{'='*60}")
    
    if hasattr(msg, 'content') and msg.content:
        print(msg.content)
    
    if hasattr(msg, 'tool_calls') and msg.tool_calls:
        print(f"\n Tool Calls:")
        for tc in msg.tool_calls:
            print(f"  - {tc['name']}")
            print(f"    Args: {tc['args']}")
    
    print()

print("=" * 60)
print(" Test Complete!")
