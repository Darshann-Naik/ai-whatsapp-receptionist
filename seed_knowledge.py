import asyncio
import sys
from sqlalchemy import select

# Ensure Python can find your 'app' module if running from project root
sys.path.append("./src")

from app.db.session import AsyncSessionLocal
from app.models.domain import Tenant
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.core.logging import logger

# Sample Knowledge Block for an Indian Dental Clinic
DENTIST_KNOWLEDGE = """
Business Name: SmileCare Dental Clinic Bangalore
Address: 45, 100 Feet Road, Indiranagar, Bangalore, Karnataka 560038.
Working Hours: Monday to Saturday, 10:00 AM to 8:00 PM. Sunday Closed.

Services and Pricing:
1. General Consultation: ₹500 (Free for returning patients within 30 days)
2. Teeth Cleaning & Scaling: ₹1,500
3. Root Canal Treatment (RCT): Starts at ₹4,500 per tooth (Takes 2-3 sessions)
4. Teeth Whitening: ₹3,500
5. Dental Implants: Starts at ₹35,000 per implant
6. Braces / Orthodontics: Starts at ₹40,000 (EMI options available)

Policies:
- Appointments are highly recommended. Walk-ins wait time can be up to 1 hour.
- We accept cash, UPI (PhonePe, GPay), and all major Credit/Debit cards.
- We do NOT accept insurance directly, but we provide all necessary bills for reimbursement.
- For dental emergencies outside working hours, please visit the nearest general hospital.
"""

async def seed_and_test(tenant_id: int):
    # 1. Validate Tenant exists in MySQL
    print(f"\n[1/3] Validating Tenant ID {tenant_id}...")
    async with AsyncSessionLocal() as db:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        
        if not tenant:
            print(f"❌ ERROR: Tenant ID {tenant_id} not found in MySQL database.")
            print("Please insert a tenant into the 'tenants' table first.")
            return
            
        print(f"✅ Found Tenant: {tenant.business_name}")

    # 2. Upsert Knowledge into ChromaDB
    print("\n[2/3] Chunking and embedding knowledge into ChromaDB...")
    # Note: The first time this runs, it will download the embedding model
    await vector_service.upsert_business_info(tenant_id, DENTIST_KNOWLEDGE)
    print("✅ Knowledge seeded successfully.")

    # 3. Interactive Test Loop
    print("\n[3/3] Commencing RAG Test Loop. Type 'quit' to exit.")
    print("-" * 50)
    
    while True:
        question = input("\n👤 You (Test Question): ")
        if question.lower() in ['quit', 'exit', 'q']:
            break
            
        if not question.strip():
            continue

        # Fetch Context
        print("🔍 Searching Vector DB...")
        context = await vector_service.query_business_info(tenant_id, question)
        
        if context:
            print(f"📄 Retrieved Context Snippet:\n{context[:200]}...\n")
        else:
            print("📄 Retrieved Context Snippet: NONE\n")

        # Call LLM
        print("🧠 Asking Gemini...")
        response = await llm_service.generate_response(
            user_text=question, 
            chat_history=[], # Empty history for isolated testing
            context_text=context
        )
        
        print(f"🤖 AI Receptionist:\n{response}")

if __name__ == "__main__":
    try:
        target_tenant = input("Enter the target Tenant ID to seed (e.g., 1): ")
        tenant_id = int(target_tenant)
        asyncio.run(seed_and_test(tenant_id))
    except ValueError:
        print("❌ Invalid input. Tenant ID must be an integer.")
    except KeyboardInterrupt:
        print("\nExiting.")