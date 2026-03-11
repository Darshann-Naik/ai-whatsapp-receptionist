import asyncio
import sys

sys.path.append("./src")
from sqlalchemy import delete, select, update
from app.db.session import AsyncSessionLocal
from app.models.domain import Message, Conversation

async def hard_reset():
    # Your test phone number
    target_phone = "918147680871" 
    
    async with AsyncSessionLocal() as db:
        # 1. Find the conversation
        conv_stmt = select(Conversation).where(Conversation.customer_phone == target_phone)
        conv = (await db.execute(conv_stmt)).scalar_one_or_none()
        
        if conv:
            # 2. Unmute the AI
            conv.requires_human = False
            
            # 3. Delete the corrupted, non-alternating history
            await db.execute(delete(Message).where(Message.conversation_id == conv.id))
            
            await db.commit()
            print(f"✅ HARD RESET COMPLETE: AI unmuted and chat history wiped for {target_phone}!")
        else:
            print("❌ Could not find that conversation in the database.")

if __name__ == "__main__":
    asyncio.run(hard_reset())