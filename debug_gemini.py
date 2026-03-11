import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append("./src")
load_dotenv()

from app.services.llm_service import llm_service

async def debug():
    print(f"🔑 Checking API Key: {os.getenv('GEMINI_API_KEY')[:5]}****")
    try:
        # We are simulating a real request
        response = await llm_service.generate_response(
            user_text="Hi",
            chat_history=[],
            context_text="The clinic is open 10am to 8pm."
        )
        print(f"✅ Gemini Response: {response}")
    except Exception as e:
        print(f"❌ LLM Service Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())