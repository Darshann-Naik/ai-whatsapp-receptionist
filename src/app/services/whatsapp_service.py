import asyncio
from typing import Any, Dict
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, func, delete
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
        - Admin Alerts with Chat Context & wa.me Links
        - Admin Chat Commands (/resume)
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

        # Context variables
        tenant_id = None
        tenant_owner_phone = None
        conversation_id = None
        formatted_history = []
        system_note_to_append = ""
        chat_context_str = "" # Stores the recent chat for the admin alert

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

                # --- 🔴 ADMIN COMMAND INTERCEPTOR ---
                if customer_phone == tenant_owner_phone and msg_body.strip().startswith("/resume"):
                    parts = msg_body.strip().split()
                    if len(parts) >= 2:
                        target_phone = parts[1]
                        
                        # Find the target conversation
                        target_conv_stmt = select(Conversation).where(
                            Conversation.tenant_id == tenant_id, 
                            Conversation.customer_phone == target_phone
                        )
                        target_conv = (await db.execute(target_conv_stmt)).scalar_one_or_none()
                        
                        if target_conv:
                            # 1. Unmute the AI
                            target_conv.requires_human = False
                            
                            # 2. THE FIX: Wipe the corrupted history so Gemini doesn't crash!
                            await db.execute(delete(Message).where(Message.conversation_id == target_conv.id))
                            await db.commit()
                            
                            # Tell the admin it worked
                            await meta_client.send_text_message(
                                whatsapp_number_id=business_phone_id,
                                to_phone=tenant_owner_phone,
                                text=f"✅ System Update: AI unmuted and chat history reset for {target_phone}. Ready for their next message!"
                            )
                        else:
                            await meta_client.send_text_message(
                                whatsapp_number_id=business_phone_id,
                                to_phone=tenant_owner_phone,
                                text=f"❌ Could not find a conversation for {target_phone}."
                            )
                        return True # Stop processing this message
                # --- END ADMIN BLOCK ---

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

                # A) HUMAN HANDOVER KILL-SWITCH
                if conv.requires_human:
                    logger.info(f"Handoff active for {customer_phone}. Dropping message.")
                    return True 

                # B) SOFT-DROP RATE LIMITER
                time_threshold = datetime.now(timezone.utc) - timedelta(seconds=60)
                spam_stmt = select(func.count(Message.id)).where(
                    Message.conversation_id == conversation_id,
                    Message.role == "user",
                    Message.created_at >= time_threshold
                )
                recent_msg_count = (await db.execute(spam_stmt)).scalar() or 0

                if recent_msg_count >= 5:
                    return True

                # Fetch Chat History for LLM
                hist_stmt = select(Message).where(
                    Message.conversation_id == conversation_id
                ).order_by(Message.id.desc()).limit(10)
                db_history = (await db.execute(hist_stmt)).scalars().all()
                
                # Format history for LLM
                formatted_history = [
                    {"role": m.role, "parts": [{"text": m.content}]} 
                    for m in reversed(db_history)
                ]

                # --- 🔴 BUILD CHAT CONTEXT FOR ADMIN ALERT ---
                # Grab the last 3 messages from history to show the admin what happened
                recent_context_msgs = list(reversed(db_history[:3])) if db_history else []
                for m in recent_context_msgs:
                    role_emoji = "🤖 AI" if m.role == "model" else "👤 Cust"
                    chat_context_str += f"{role_emoji}: {m.content}\n"
                
                # Add the message the customer JUST sent right now
                chat_context_str += f"👤 Cust: {msg_body}\n"

                # Commit user message
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

        # --- 4. STRICT LLM GENERATION & FALLBACK BLOCK ---
        enhanced_msg_body = msg_body + system_note_to_append
        
        # Pre-build the Admin Alert template so we can use it in both error and success paths
        admin_alert_template = (
            f"🚨 *HUMAN NEEDED*\n"
            f"Customer {customer_phone} needs help. AI is now muted.\n\n"
            f"💬 *Recent Chat Context:*\n"
            f"{chat_context_str}\n"
            f"👉 *Tap here to reply to them directly:*\n"
            f"https://wa.me/{customer_phone}"
        )

        try:
            ai_text_raw = await llm_service.generate_response(
                user_text=enhanced_msg_body, 
                chat_history=formatted_history,
                context_text=business_context
            )
        except Exception as e:
            logger.error(f"LLM Generation Failed for {customer_phone}: {str(e)}", exc_info=True)
            
            # Crash Step A: Update the database to mute the AI
            try:
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Conversation)
                        .where(Conversation.id == conversation_id)
                        .values(requires_human=True)
                    )
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update db during fallback: {str(db_err)}")
            
            # Crash Step B: Tell customer to wait
            await meta_client.send_text_message(
                whatsapp_number_id=business_phone_id,
                to_phone=customer_phone,
                text="I am experiencing technical difficulties. Please hold, I am connecting you to a human instructor."
            )
            
            # Crash Step C: Alert Admin with context
            if tenant_owner_phone:
                try:
                    await meta_client.send_text_message(
                        whatsapp_number_id=business_phone_id,
                        to_phone=tenant_owner_phone,
                        text=f"⚠️ *SYSTEM CRASH*\n{admin_alert_template}"
                    )
                except Exception as meta_err:
                    logger.error(f"Could not send Admin Crash Alert: {str(meta_err)}")
            
            return True # Exit immediately so we don't run the rest of the code

        # --- 5. NORMAL DB SESSION 2: STATE UPDATES & ALERTS ---
        handoff_detected = "[HANDOFF]" in ai_text_raw
        clean_ai_text = ai_text_raw.replace("[HANDOFF]", "").strip()

        try:
            async with AsyncSessionLocal() as db:
                if handoff_detected:
                    await db.execute(
                        update(Conversation)
                        .where(Conversation.id == conversation_id)
                        .values(requires_human=True)
                    )
                    
                    if tenant_owner_phone:
                        try:
                            # Send the formatted alert to the Admin
                            await meta_client.send_text_message(
                                whatsapp_number_id=business_phone_id, 
                                to_phone=tenant_owner_phone, 
                                text=admin_alert_template
                            )
                        except Exception as meta_err:
                            logger.error(f"Could not send Handoff Admin Alert: {str(meta_err)}")

                # Save AI Message
                db.add(Message(conversation_id=conversation_id, role="model", content=clean_ai_text))
                await db.commit()
        except Exception as e:
            logger.error(f"DB Session 2 Failure: {str(e)}", exc_info=True)

        # --- 6. FINAL SEND TO CUSTOMER ---
        try:
            await meta_client.send_text_message(
                whatsapp_number_id=business_phone_id, 
                to_phone=customer_phone, 
                text=clean_ai_text
            )
        except Exception as e:
            logger.error(f"Failed to send final Meta message: {str(e)}")

        return True

whatsapp_processor = WhatsAppProcessor()