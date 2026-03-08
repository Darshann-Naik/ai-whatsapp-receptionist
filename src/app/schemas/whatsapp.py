# src/app/schemas/whatsapp.py
from pydantic import BaseModel
from typing import List, Dict, Any

class WebhookPayload(BaseModel):
    object: str
    entry: List[Dict[str, Any]]