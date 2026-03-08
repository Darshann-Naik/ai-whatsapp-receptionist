import asyncio
from typing import Any, Dict
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, func
from app.db.session import AsyncSessionLocal
from app.models.domain import Tenant, Conversation, Message
from app.services.meta_client import meta_client
from app.services.llm_service import llm_service
from app.core.logging import logger
from app.services.vector_service import vector_service

class WhatsAppProcessor:
    async def process_event(self, payload: Dict[str, Any]):
        """
        Production Orchestrator:
        - 200 OK Guaranteed for Meta
        - Internal Soft-Drop Rate Limiting
        - AI-to-Human Handoff Logic
        - RAG-Enhanced Generation
        - First-Touch Welcome Media
        """
        # --- 1. SAFE JSON PARSING ---
        try:
            entries = payload.get("entry", [])
            if not entries: return False
            
            value = entries[0].get("changes", [{}])[0].get("value", {})
            metadata = value.get("metadata", {})
            business_phone_id = metadata.get("phone_number_id")
            
            messages = value.get("messages", [])
            if not messages: return False
            
            msg = messages[0]
            customer_phone = msg.get("from")
            msg_body = msg.get("text", {}).get("body")
            msg_type = msg.get("type")

            if msg_type != "text" or not msg_body:
                return False

        except Exception as e:
            logger.error(f"Webhook Parsing Error: {str(e)}", exc_info=True)
            return False

        # Context variables to bridge sessions
        tenant_id = None
        tenant_owner_phone = None
        conversation_id = None
        formatted_history = []
        system_note_to_append = ""

        # --- 2. DB SESSION 1: IDENTIFICATION & FIREWALLS ---
        try:
            async with AsyncSessionLocal() as db:
                # Identify Tenant
                tenant_stmt = select(Tenant).where(Tenant.whatsapp_number_id == business_phone_id)
                tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
                if not tenant:
                    logger.error(f"Tenant missing for Phone ID: {business_phone_id}")
                    return False
                
                tenant_id = tenant.id
                tenant_owner_phone = tenant.owner_phone

                # Get/Create Conversation
                is_new_conversation = False
                conv_stmt = select(Conversation).where(
                    Conversation.tenant_id == tenant_id,
                    Conversation.customer_phone == customer_phone
                )
                conv = (await db.execute(conv_stmt)).scalar_one_or_none()
                
                if not conv:
                    conv = Conversation(tenant_id=tenant_id, customer_phone=customer_phone)
                    db.add(conv)
                    await db.flush()
                    is_new_conversation = True
                
                conversation_id = conv.id

                # --- FIRST-TOUCH INTERCEPTOR (WELCOME MEDIA) ---
                if is_new_conversation and tenant.welcome_media:
                    media_tasks = []
                    pdf_url = tenant.welcome_media.get("pdf_url")
                    image_urls = tenant.welcome_media.get("image_urls", [])

                    if pdf_url:
                        media_tasks.append(
                            meta_client.send_document(business_phone_id, customer_phone, pdf_url)
                        )
                    
                    for img_url in image_urls:
                        media_tasks.append(
                            meta_client.send_image(business_phone_id, customer_phone, img_url)
                        )

                    # Fire-and-forget to avoid webhook timeouts
                    if media_tasks:
                        asyncio.create_task(asyncio.gather(*media_tasks))
                        system_note_to_append = "\n[SYSTEM NOTE: The user was just automatically sent the Welcome PDF brochure and photos. Acknowledge this briefly.]"

                # A) HUMAN HANDOVER KILL-SWITCH
                if conv.requires_human:
                    logger.info(f"Handoff active for {customer_phone}. Dropping message.")
                    return True 

                # B) SOFT-DROP RATE LIMITER (Logical 200 OK)
                time_threshold = datetime.now(timezone.utc) - timedelta(seconds=60)
                spam_stmt = select(func.count(Message.id)).where(
                    Message.conversation_id == conversation_id,
                    Message.role == "user",
                    Message.created_at >= time_threshold
                )
                recent_msg_count = (await db.execute(spam_stmt)).scalar() or 0

                if recent_msg_count >= 5:
                    logger.warning(f"Soft-drop triggered for {customer_phone}. Count: {recent_msg_count}")
                    return True # Silently ignore while keeping Meta happy

                # Fetch Chat History for LLM (Last 10 messages)
                hist_stmt = select(Message).where(
                    Message.conversation_id == conversation_id
                ).order_by(Message.id.desc()).limit(10)
                db_history = (await db.execute(hist_stmt)).scalars().all()
                
                formatted_history = [
                    {"role": m.role, "parts": [{"text": m.content}]} 
                    for m in reversed(db_history)
                ]

                # Commit user message (saving raw msg_body, not the system note)
                db.add(Message(conversation_id=conversation_id, role="user", content=msg_body))
                await db.commit()
                
        except Exception as e:
            logger.error(f"DB Session 1 Failure: {str(e)}", exc_info=True)
            return False

        # --- 3. RAG: KNOWLEDGE RETRIEVAL ---
        try:
            business_context = await vector_service.query_business_info(
                tenant_id=tenant_id, 
                query_text=msg_body
            )
        except Exception as e:
            logger.error(f"RAG Search Failure: {str(e)}")
            business_context = ""

        # --- 4. LLM: GENERATE RESPONSE ---
        # Append the hidden system note if media was just sent
        enhanced_msg_body = msg_body + system_note_to_append
        
        ai_text_raw = await llm_service.generate_response(
            user_text=enhanced_msg_body, 
            chat_history=formatted_history,
            context_text=business_context
        )

        # Detect [HANDOFF] tag and clean for customer view
        handoff_detected = "[HANDOFF]" in ai_text_raw
        clean_ai_text = ai_text_raw.replace("[HANDOFF]", "").strip()

        # --- 5. DB SESSION 2: STATE UPDATES & ALERTS ---
        try:
            async with AsyncSessionLocal() as db:
                if handoff_detected:
                    await db.execute(
                        update(Conversation)
                        .where(Conversation.id == conversation_id)
                        .values(requires_human=True)
                    )
                    
                    if tenant_owner_phone:
                        alert_msg = f"🚨 AI Handoff Alert: Customer {customer_phone} needs help. AI muted."
                        await meta_client.send_text_message(
                            whatsapp_number_id=business_phone_id, 
                            to_phone=tenant_owner_phone, 
                            text=alert_msg
                        )

                # Save AI Message
                db.add(Message(conversation_id=conversation_id, role="model", content=clean_ai_text))
                await db.commit()
        except Exception as e:
            logger.error(f"DB Session 2 Failure: {str(e)}", exc_info=True)

        # --- 6. FINAL SEND TO CUSTOMER ---
        await meta_client.send_text_message(
            whatsapp_number_id=business_phone_id, 
            to_phone=customer_phone, 
            text=clean_ai_text
        )
        
        return True

whatsapp_processor = WhatsAppProcessor()