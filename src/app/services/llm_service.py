from google import genai
from google.genai import types
from app.core.config import settings
from app.core.logging import logger

class LLMService:
    def __init__(self):
        # Explicitly pass the API key to the client
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "gemini-2.5-flash"
        
        # The Hallucination Firewall & Sales Closer Logic
        self.system_instruction = (
            "You are a polite, professional, and concise Indian business receptionist. "
            "Your goal is to assist customers using ONLY the provided Business Context. "
            "1. If the answer is NOT in the context, or if the user asks for a human, "
            "manager, or operator, you must answer politely and append the tag [HANDOFF] at the end. "
            "2. If the user is angry or frustrated, append the tag [HANDOFF]. "
            "3. Never invent facts. If unsure, use [HANDOFF]. "
            "4. The Booking & Static QR Code Handoff (CRITICAL): "
            "You are responsible for closing the sale and calculating the final price, but you cannot verify payments. "
            "When a customer explicitly agrees to book a specific date/package and asks to pay, you MUST follow these exact steps in a single message: "
            "Summarize their booking details (Date, Package, Number of people). "
            "Calculate and state the EXACT total amount they need to pay. "
            "Provide them with the business's official payment QR code link: [INSERT_REAL_URL_HERE] "
            "Instruct the customer to scan the QR code, manually enter the exact total amount, and reply with a screenshot of the successful payment. "
            "Tell them a human instructor will verify the screenshot and officially confirm their slot shortly. "
            "You MUST append the exact string [HANDOFF] at the very end of your response to mute yourself and alert the human owner. "
        )

    async def generate_response(self, user_text: str, chat_history: list, context_text: str = "") -> str:
        """
        chat_history: list of objects with 'role' and 'content' 
        """
        try:
            # 1. Convert DB history to SDK-compatible Content objects
            formatted_history = []
            for msg in chat_history:
                # Assuming msg["parts"][0]["text"] exists based on your snippet
                text_content = msg["parts"][0]["text"]
                formatted_history.append(
                    types.Content(
                        role=msg["role"],
                        parts=[types.Part(text=text_content)] # Fixed: Using direct Part init
                    )
                )

            # 2. Construct the current message with Context + User Prompt
            current_message_parts = []
            if context_text:
                current_message_parts.append(types.Part(text=f"BUSINESS CONTEXT:\n{context_text}"))
            
            current_message_parts.append(types.Part(text=f"USER QUESTION: {user_text}"))
            
            current_turn = types.Content(
                role="user",
                parts=current_message_parts
            )

            # 3. Combine History and Current Turn
            all_contents = formatted_history + [current_turn]

            # 4. Execute Async Call
            # Note: client.aio.models.generate_content is correct for the newer SDK
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=all_contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.0,
                    max_output_tokens=300,
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE",
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE",
                        ),
                    ]
                )
            )

            if not response.text:
                return "I'm sorry, I cannot answer that. How else can I help your business?"
                
            return response.text

# Inside llm_service.py
        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}", exc_info=True)
            # Remove the return string and RAISE the error so the processor catches it!
            raise e
llm_service = LLMService()