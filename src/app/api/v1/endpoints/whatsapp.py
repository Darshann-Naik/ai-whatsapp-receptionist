import json
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, status
from slowapi.util import get_remote_address

from app.core.security import limiter
from app.services.whatsapp_service import whatsapp_processor
from app.core.logging import logger

router = APIRouter()

async def whatsapp_phone_key_func(request: Request) -> str:
    """
    Extracts phone number for rate limiting. 
    Caches the body in request.state to prevent double-consumption errors.
    """
    try:
        body = await request.json()
        # Store for the route handler to use later
        request.state.body = body 
        
        # Navigate Meta's nested JSON safely
        entries = body.get("entry", [])
        if entries:
            changes = entries[0].get("changes", [])
            if changes:
                messages = changes[0].get("value", {}).get("messages", [])
                if messages:
                    return str(messages[0].get("from"))
        
        return get_remote_address(request)
    except Exception:
        return get_remote_address(request)

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta Webhook Verification (Handshake)"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # verify_token should be in your config/settings
    if mode == "subscribe" and token == "YOUR_SECURE_VERIFY_TOKEN":
        return int(challenge)
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

@router.post("/webhook")
@limiter.limit("5/minute", key_func=whatsapp_phone_key_func)
async def handle_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receives messages from Meta. 
    Uses cached body from request.state (populated by rate limiter).
    """
    payload = getattr(request.state, "body", None)
    
    if not payload:
        # Fallback if rate limiter didn't run or failed to parse
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    # Offload to Background Task to respond to Meta within 5s
    background_tasks.add_task(whatsapp_processor.process_event, payload)

    return {"status": "accepted"}