import asyncio
import sys

# Tell Python to look in the src folder
sys.path.append("./src")

from app.services.vector_service import vector_service
from app.core.config import settings

# This is the "Brain" of your AI
DENTIST_KNOWLEDGE = """
Business Name: SmileCare Dental Clinic Bangalore
Address: 45, 100 Feet Road, Indiranagar, Bangalore, Karnataka 560038.
Working Hours: Monday to Saturday, 10:00 AM to 8:00 PM. Sunday Closed.

Services and Pricing:
1. General Consultation: ₹500
2. Teeth Cleaning & Scaling: ₹1,500
3. Root Canal Treatment (RCT): Starts at ₹4,500 per tooth
4. Teeth Whitening: ₹3,500
5. Dental Implants: Starts at ₹35,000 per implant
6. Braces / Orthodontics: Starts at ₹40,000 (EMI options available)

Policies:
- Appointments are highly recommended.
- We accept UPI (PhonePe, GPay) and Cards.
- Emergency? Visit the nearest general hospital after 8 PM.
"""

async def seed_knowledge():
    # Use the Tenant ID from your database (likely 3 based on your last log)
    tenant_id = 4 
    
    print(f"🧠 Feeding knowledge for Tenant ID {tenant_id} into ChromaDB...")
    
    try:
        # This breaks the text into chunks and creates embeddings
        await vector_service.upsert_business_info(tenant_id, DENTIST_KNOWLEDGE)
        print("✅ Success! The AI is now an expert on SmileCare Dental Clinic.")
    except Exception as e:
        print(f"❌ Error seeding knowledge: {e}")

if __name__ == "__main__":
    asyncio.run(seed_knowledge())