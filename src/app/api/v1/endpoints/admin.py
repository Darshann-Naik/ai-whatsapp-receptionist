from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import verify_admin_key
from app.models.domain import Tenant, KnowledgeBase
from app.services.vector_service import vector_service

router = APIRouter(dependencies=[Depends(verify_admin_key)])

class KnowledgeUpdate(BaseModel):
    content_text: str

from sqlalchemy import delete # Add this import

@router.post("/tenant/{tenant_id}/knowledge", status_code=status.HTTP_201_CREATED)
async def update_tenant_knowledge(
    tenant_id: int,
    data: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db)
):
    # 1. Verify Tenant Existence
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 2. WIPE OLD DATA (Idempotency Patch)
    # Clear ChromaDB vectors
    await vector_service.clear_business_info(tenant_id)
    
    # Clear MySQL Audit Trail for this tenant (Optional but Recommended)
    await db.execute(delete(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id))

    # 3. REPLACE WITH NEW DATA
    # Sync to ChromaDB
    await vector_service.upsert_business_info(tenant_id, data.content_text)

    # Save new record to MySQL
    new_entry = KnowledgeBase(
        tenant_id=tenant_id,
        content_text=data.content_text
    )
    db.add(new_entry)
    await db.commit()

    return {"status": "success", "message": f"Knowledge refreshed for {tenant.business_name}"}