import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')

from main import chat, ChatRequest

async def run():
    print("=== STARTING CHAT ENDPOINT STREAM VERIFICATION ===")
    
    queries = [
        ("HIGH_CONFIDENCE", "Give me the top 5 opportunities stalling in the negotiation stage."),
        ("LOW_CONFIDENCE", "what is up?")
    ]
    
    for label, query in queries:
        print(f"\n=============================================")
        print(f" TESTING QUERY ({label}): '{query}'")
        print(f"=============================================")
        request = ChatRequest(query=query)
        response = await chat(request)
        
        print("\n--- STREAMING START ---")
        async for chunk in response.body_iterator:
            print(chunk, end="", flush=True)
        print("\n--- STREAMING END ---")
        
    print("\n=== CHAT ENDPOINT STREAM VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run())
