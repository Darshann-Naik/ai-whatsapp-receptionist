import httpx
from app.core.config import settings
from app.core.logging import logger

class MetaClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v22.0"
        self.headers = {
            "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        # 10-second timeout. If Meta takes longer than this, drop it.
        self.timeout = httpx.Timeout(10.0)

    async def send_text_message(self, whatsapp_number_id: str, to_phone: str, text: str) -> bool:
        url = f"{self.base_url}/{whatsapp_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": text}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                logger.info(
                    "Message sent successfully", 
                    extra_info={"to_phone": to_phone, "whatsapp_number_id": whatsapp_number_id}
                )
                return True

        except httpx.HTTPStatusError as e:
            # Meta returns detailed JSON errors (e.g., 'number not on WhatsApp'). 
            # We must log the response body, not just the status code.
            error_details = e.response.text
            logger.error(
                f"Meta API rejected message. Status: {e.response.status_code}",
                extra_info={"meta_error": error_details, "to_phone": to_phone}
            )
            return False
            
        except httpx.RequestError as e:
            logger.error(
                "Network failure communicating with Meta API",
                extra_info={"error": str(e), "url": e.request.url}
            )
            return False

async def send_document(self, whatsapp_number_id: str, to_phone: str, document_url: str, filename: str = "Brochure.pdf"):
        """Sends a document (PDF) via URL using the Meta Cloud API."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename
            }
        }
        # Note: Replace 'self._send_request' with your client's actual internal HTTP POST method
        return await self._send_request(whatsapp_number_id, payload)

async def send_image(self, whatsapp_number_id: str, to_phone: str, image_url: str):
        """Sends an image via URL using the Meta Cloud API."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        return await self._send_request(whatsapp_number_id, payload)

meta_client = MetaClient()