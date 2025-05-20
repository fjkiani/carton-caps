import datetime
import os
from typing import List, Optional, Literal, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# NEW IMPORTS for static files and redirect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Import your database utility functions
from db_utils import get_user_details, get_products_by_keyword, get_purchase_history, save_conversation_message, get_conversation_history_from_db

# NEW IMPORT for Google Gemini
import google.generativeai as genai

# NEW IMPORT for PDF parsing
import fitz  # PyMuPDF

# Load environment variables from .env file
load_dotenv()

# --- Configure Google Gemini API --- 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY not found in .env file. Gemini integration will not work.")
    # You could raise an error here or allow the app to run with Gemini disabled
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Google Gemini API configured successfully.")
    except Exception as e:
        print(f"Error configuring Google Gemini API: {e}")

# --- Pydantic Models (Based on our API Specification) ---

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class MessageInput(BaseModel):
    text: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class SchoolInfo(BaseModel):
    school_id: Optional[str | int] = None # Changed to str | int
    school_name: Optional[str] = None

class UserProfile(BaseModel):
    preferences: Optional[List[str]] = None
    past_purchases_summary: Optional[List[str]] = None
    location_context: Optional[Dict[str, str]] = None # e.g., {"city": "string", "region": "string"}
    school_info: Optional[SchoolInfo] = None

class ClientContext(BaseModel):
    current_view: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: MessageInput
    conversation_history: Optional[List[Message]] = []
    user_profile: Optional[UserProfile] = None
    client_context: Optional[ClientContext] = None

class Reply(BaseModel):
    text: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class SuggestedAction(BaseModel):
    type: Literal["quick_reply", "product_link", "referral_link", "external_url"]
    text_label: str
    payload: str | Dict[str, Any]

class DebugInfo(BaseModel):
    intent_detected: Optional[str] = None
    retrieved_context_summary: Optional[str] = None
    data_sources_used: Optional[List[str]] = None
    llm_prompt: Optional[str] = None # Added for debugging LLM prompts

class ChatResponse(BaseModel):
    session_id: str
    reply: Reply
    updated_conversation_history: List[Message]
    suggested_actions: Optional[List[SuggestedAction]] = None
    debug_info: Optional[DebugInfo] = None

# --- FastAPI Application ---
app = FastAPI(
    title="Carton Caps AI Conversational Assistant",
    version="1.0.0",
    description="API for the Carton Caps AI chat agent.",
)

# --- Mount static files directory (for the simple UI) ---
# This will serve files from the 'static' directory at the '/ui' path
# For example, your index.html will be at http://127.0.0.1:8008/ui/index.html
# If 'static' directory is directly inside 'carton_caps_ai_service' along with main.py
app.mount("/ui", StaticFiles(directory="static"), name="static-ui")

# --- In-memory store for conversation history (for prototype) ---
# In a production system, this would be a database like Redis or the Conversation_History table.
conversation_sessions: Dict[str, List[Message]] = {}

# --- NEW: PDF Text Extraction Function ---
def get_text_from_pdf(pdf_path: str) -> Optional[str]:
    """Extracts all text content from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
        # Basic cleaning: replace multiple newlines/spaces with a single space
        text = ' '.join(text.replace('\n', ' ').split())
        return text
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"Error reading PDF file {pdf_path}: {e}")
        return None

# --- NEW: Gemini LLM Interaction Function ---
async def get_gemini_response(prompt: str, model_name: str = "gemini-1.5-pro") -> Optional[str]:
    if not GOOGLE_API_KEY:
        print("Gemini API key not configured. Skipping LLM call.")
        return "[LLM Disabled] This is a placeholder response as the LLM is not configured."
    try:
        print(f"\n--- Sending prompt to Gemini ({model_name}) ---")
        print(prompt)
        print("-------------------------------------\n")
        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async(prompt) # Use async for FastAPI
        
        # Extract text from the response parts
        response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        
        print(f"--- Gemini Response ---")
        print(response_text)
        print("-----------------------\n")
        return response_text if response_text else "Sorry, I couldn't generate a response at this moment."
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Check for specific API errors if needed, e.g., related to safety settings
        if hasattr(e, 'parts') and e.parts:
            print(f"Gemini API Error Parts: {e.parts}")
        if hasattr(e, 'message'):
            print(f"Gemini API Error Message: {e.message}")
        return f"Sorry, I encountered an error trying to understand that. Error: {str(e)[:100]}"

# --- API Endpoint ---

@app.post("/api/v1/carton_caps/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Main endpoint for sending user messages and receiving assistant replies.
    """
    print(f"Received request for session_id: {request.session_id}, user_id: {request.user_id}")
    print(f"User message: {request.message.text}")

    session_history = conversation_sessions.get(request.session_id, [])
    if not session_history and request.conversation_history:
        session_history = request.conversation_history
        print(f"Initialized session {request.session_id} history from client.")

    user_message_record = Message(role="user", content=request.message.text, timestamp=request.message.timestamp)
    session_history.append(user_message_record)
    save_conversation_message(request.session_id, request.user_id, "user", request.message.text, request.message.timestamp)

    user_details = get_user_details(request.user_id)
    user_name = user_details.get("user_name", request.user_id) if user_details else request.user_id
    user_school_name = user_details.get("school_name", "their school") if user_details else "their school"

    # --- Intent Detection and Context Retrieval --- 
    detected_intent = "unknown"
    retrieved_db_context_str = ""
    data_sources = []
    llm_prompt_for_debug = ""

    lower_message = request.message.text.lower()
    # More specific keywords first
    if "referral" in lower_message or "refer" in lower_message or "friend" in lower_message:
        detected_intent = "referral_question"
        data_sources.append("Referral_FAQ_PDF") # Changed from _Simulated
        
        # --- MODIFIED: Use actual PDF text extraction ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # CORRECTED PDF PATH:
        # Assumes 'CartonCapsReferralFAQs.pdf' is in the 'data' subdirectory 
        # relative to where main.py is (i.e., carton_caps_ai_service/data/)
        pdf_path = os.path.join(current_dir, "data", "CartonCapsReferralFAQs.pdf")
        
        pdf_path = os.path.normpath(pdf_path) # Normalize path for OS compatibility

        print(f"Attempting to load PDF from: {pdf_path}")
        referral_faq_text = get_text_from_pdf(pdf_path)

        if referral_faq_text:
            retrieved_db_context_str = f"Context from Referral FAQ Document:\n{referral_faq_text}"
        else:
            retrieved_db_context_str = "I found our general referral information, but I'm having a little trouble accessing the detailed FAQ document right now. Generally, Carton Caps offers a referral program where you can earn rewards for your school by inviting friends. You can usually find your unique referral link in the app's 'Refer a Friend' section."
            print("Fallback referral context used due to PDF loading issue.")
        # --- END MODIFICATION ---
    elif any(kw in lower_message for kw in ["product", "recommend", "buy", "find", "search", "cereal", "snack", "fruit", "cheese", "oatmeal", "flakes", "bars"]):
        detected_intent = "product_query"
        data_sources.append("Product_DB")
        
        # Improved keyword extraction for product search
        keyword_to_search = None
        # Prioritize specific product types mentioned
        product_type_keywords = ["cereal", "snack", "fruit", "cheese", "oatmeal", "flakes", "bar", "bars", "juice", "milk", "yogurt", "pasta", "bread"]
        for pt_kw in product_type_keywords:
            if pt_kw in lower_message:
                keyword_to_search = pt_kw
                break
        
        # If no specific type, and it's a general recommendation, try broader terms or the original query
        if not keyword_to_search:
            if "recommend" in lower_message or "suggest" in lower_message:
                # For general recommendations, we might not have a good single keyword.
                # Could try to pull out nouns, or for now, let LLM handle broader query if no specific keyword found.
                # For this iteration, let's try with the original text if no better keyword is found.
                keyword_to_search = request.message.text # Or try a very generic term like "product" if that makes sense for your DB
            else:
                # If not a recommendation, use the original text as a search term
                keyword_to_search = request.message.text 

        print(f"Product query detected. Searching for keyword: '{keyword_to_search}'")
        products = get_products_by_keyword(keyword_to_search)
        if products:
            retrieved_db_context_str = "Available products related to your query:"
            for prod in products:
                retrieved_db_context_str += f"\n- Name: {prod['name']}, Price: ${prod['price']}, Description: {prod['description']}"
        else:
            retrieved_db_context_str = "No specific products found matching your query in the database."
    else:
        detected_intent = "general_conversation"
        # No specific data source for general chat, LLM will rely on its general knowledge and persona

    # --- Construct Prompt for Gemini --- 
    system_prompt = (
        f"You are a friendly and helpful AI assistant for Carton Caps, an app that empowers consumers to raise money for schools. "
        f"Your name is Cappy. You are assisting user '{user_name}' who supports '{user_school_name}'. "
        f"Your primary goals are to help users find personalized product recommendations and understand the referral process. "
        f"Be concise and engaging. Your responses should be based *only* on the information provided in the 'Retrieved Context' section of this prompt and the 'Conversation History'. "
        f"When asked for product recommendations, list products *only* if they are present in the 'Retrieved Context'. "
        f"If the 'Retrieved Context' is empty or contains a message like 'No specific products found', you must state that you couldn't find specific products matching the query and should not invent any. You can then offer to search for something else or pivot to another topic like referrals. "
        f"Similarly, for referral information, base your answer *only* on the 'Retrieved Context' if provided for referral questions. Do not make up referral program details."
    )

    # Build conversation history for the prompt (role: user/model for Gemini)
    gemini_history_prompt = []
    for msg in session_history[-10:]: # Use last 10 messages for context window
        role = "model" if msg.role == "assistant" else "user"
        gemini_history_prompt.append(f"{role}: {msg.content}")
    
    full_prompt = f"{system_prompt}\n\n"
    if retrieved_db_context_str:
        full_prompt += f"Retrieved Context:\n{retrieved_db_context_str}\n\n"
    full_prompt += "Conversation History (most recent first):\n" + "\n".join(reversed(gemini_history_prompt[:-1])) # Show history, excluding current user query
    full_prompt += f"\n\nUser '{user_name}' (current query): {request.message.text}\nAssistant Cappy:"

    llm_prompt_for_debug = full_prompt # For debug output

    # --- Get Response from Gemini --- 
    assistant_reply_text = await get_gemini_response(full_prompt)
    if assistant_reply_text is None:
        assistant_reply_text = "I'm having a little trouble connecting right now. Please try again in a moment."

    assistant_message_record = Message(role="assistant", content=assistant_reply_text, timestamp=datetime.datetime.now())
    session_history.append(assistant_message_record)
    
    # MODIFIED: Map 'assistant' role to 'bot' for database saving
    db_sender_role = "bot" if assistant_message_record.role == "assistant" else assistant_message_record.role
    save_conversation_message(request.session_id, request.user_id, db_sender_role, assistant_reply_text, assistant_message_record.timestamp)
    
    conversation_sessions[request.session_id] = session_history

    # TODO: Implement logic to generate relevant suggested_actions based on LLM response or intent
    current_suggested_actions = [
        SuggestedAction(type="quick_reply", text_label="Recommend a snack", payload="Recommend a snack for me"),
        SuggestedAction(type="quick_reply", text_label="How do referrals work?", payload="How do referrals work?")
    ]
    if detected_intent == "product_query" and products:
         current_suggested_actions.append(SuggestedAction(type="quick_reply", text_label=f"Tell me more about {products[0]['name']}", payload=f"Tell me more about {products[0]['name']}"))

    return ChatResponse(
        session_id=request.session_id,
        reply=Reply(text=assistant_reply_text, timestamp=assistant_message_record.timestamp),
        updated_conversation_history=session_history,
        suggested_actions=current_suggested_actions,
        debug_info=DebugInfo(
            intent_detected=detected_intent,
            retrieved_context_summary=retrieved_db_context_str if retrieved_db_context_str else "No specific context retrieved.",
            data_sources_used=data_sources if data_sources else ["none"],
            llm_prompt=llm_prompt_for_debug
        )
    )

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

# --- Add a root redirect to the UI for convenience ---
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/ui/index.html")

# --- To run the application (e.g., using uvicorn) ---
# uvicorn main:app --reload --port 8008
