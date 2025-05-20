# Carton Caps AI Conversational Assistant - Technical Specification

**Version:** 1.0
**Date:** 5/19/25
**Author(s):** Fahad Kiani

## 1. Introduction & Overview

### 1.1. Our Mission: Building Cappy
This document details the technical blueprint for "Cappy," an AI-powered conversational assistant designed for the Carton Caps mobile app. Our main goal with Cappy is to boost user engagement by offering smart, personalized product recommendations and clear, helpful answers about the app's referral program.

### 1.2. Key Objectives for this Prototype
Our work here focuses on several core aims:
- Develop a working API prototype for Cappy.
- Establish a robust LLM strategy that effectively uses both structured database information and insights from documents like FAQs.
- Ensure Cappy's interactions consistently support Carton Caps' mission: helping users contribute to their chosen schools.

### 1.3. Who This Is For
We've written this guide primarily for the engineers building and integrating Cappy. It should also be useful for product managers and any stakeholders keen to understand the technical nitty-gritty of the solution.

### 1.4. What We're Tackling (and What's for Later)
- **What's Covered (In Scope):** This prototype nails down the API design, our LLM integration plan, the core logic for product suggestions and referral questions, how we manage conversation context, and interaction with key data like the [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite) database and the [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf).
- **Future Steps (Out of Scope for this Prototype, but on our radar):** We're acknowledging that full user authentication (we'll assume the main app handles this for now), new user sign-ups, the in-app mobile UI, deep analytics, and a full-scale production deployment setup are important future considerations beyond this initial build.

## 2. API Contract

### 2.1. The Chat Endpoint: How We Talk to Cappy
Cappy's conversational abilities are accessed through a single, straightforward API endpoint:

- **Method:** `POST`
- **Path:** `/api/v1/carton_caps/chat`
- **What it does:** This is our main channel for the mobile app to send user messages to Cappy and get its replies.

### 2.2. What the App Sends: The Request Body
To chat with Cappy, the Carton Caps mobile app sends a `POST` request to the `/api/v1/carton_caps/chat` endpoint. The heart of this request is a JSON payload, detailed below:

```json
{
  "user_id": "string",
  "session_id": "string",
  "message": {
    "text": "string",
    "timestamp": "iso_datetime_string"
  },
  "conversation_history": [
    {
      "role": "user | assistant",
      "content": "string",
      "timestamp": "iso_datetime_string"
    }
  ],
  "user_profile": {
    "preferences": ["string"],
    "past_purchases_summary": ["string"],
    "location_context": {
        "city": "string",
        "region": "string"
    },
    "school_info": {
        "school_id": "integer | string",
        "school_name": "string"
    }
  },
  "client_context": {
      "current_view": "string"
  }
}
```

**Breaking Down the Fields:**

*   **`user_id`** (string, REQUIRED):
    *   This is the unique ID for an authenticated Carton Caps user.
    *   Our backend service relies on this ID to look up user-specific details in the [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite) database—like their associated school, name, and any available purchase history.
*   **`session_id`** (string, REQUIRED):
    *   A unique ID marking the current chat session.
    *   It's crucial for keeping the conversation coherent across multiple messages, especially since we manage state on the server.
    *   The mobile app can generate this for the first message, or our server can create it and send it back in the initial response.
*   **`message`** (object, REQUIRED):
    *   This object carries the details of what the user just typed.
    *   **`message.text`** (string, REQUIRED): The actual text of the user's message.
    *   **`message.timestamp`** (iso\_datetime\_string, REQUIRED): A timestamp (ISO 8601 format) from the client showing when the user sent the message.
*   **`conversation_history`** (array of objects, OPTIONAL):
    *   A list of previous messages in this chat. Each message in the list should include:
        *   **`role`** (enum: `"user"` \| `"assistant"`, REQUIRED): Tells us if the message was from the user or from Cappy.
        *   **`content`** (string, REQUIRED): The text of that past message.
        *   **`timestamp`** (iso\_datetime\_string, REQUIRED): When that past message occurred.
    *   If the app doesn't send this, our server will try to manage or retrieve the history using the `session_id`. While our current prototype can handle this server-side, a truly stateless approach (though less ideal) would mean the client sending the full history with every message.
*   **`user_profile`** (object, OPTIONAL):
    *   This gives us extra context about the user, helping Cappy personalize its responses.
    *   The mobile app can send some of this, or our backend can fetch/enrich it using the `user_id`.
    *   **`user_profile.preferences`** (array of strings, OPTIONAL): Any preferences the user has shared (e.g., `["organic", "gluten-free"]`). *Heads-up: The current `Users` table in [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite) doesn't have a spot for this yet; it's something we're thinking about for the future.*
    *   **`user_profile.past_purchases_summary`** (array of strings, OPTIONAL): A quick list or summary of what the user has bought before. This would come from the `Purchase_History` table in [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite). *Good to know: This table is empty in our current mock dataset.*
    *   **`user_profile.location_context`** (object, OPTIONAL): The user's general area, if it's useful for local tips or info.
        *   **`city`** (string)
        *   **`region`** (string, e.g., state/province)
    *   **`user_profile.school_info`** (object, OPTIONAL): Info about the school the user is supporting, pulled from the `Users` and `Schools` tables in [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite).
        *   **`school_id`** (integer or string)
        *   **`school_name`** (string)
*   **`client_context`** (object, OPTIONAL):
    *   Information about what the user is currently doing or seeing in the mobile app.
    *   **`client_context.current_view`** (string, OPTIONAL): An ID for the screen or section the user is on (e.g., `"product_list_page"`, `"referral_section"`, `"homepage"`). This can help Cappy tailor its responses or suggestions better.

### 2.3. What Cappy Sends Back: The Response Body
When Cappy replies, the server sends back a JSON object with the following structure:

```json
{
  "session_id": "string",
  "reply": {
    "text": "string",
    "timestamp": "iso_datetime_string"
  },
  "updated_conversation_history": [
    {
      "role": "user | assistant",
      "content": "string",
      "timestamp": "iso_datetime_string"
    }
  ],
  "suggested_actions": [
    {
      "type": "quick_reply | product_link | referral_link | external_url",
      "text_label": "string",
      "payload": "string | object"
    }
  ],
  "debug_info": {
    "intent_detected": "string",
    "retrieved_context_summary": "string",
    "data_sources_used": ["string"]
  }
}
```

**Decoding Cappy's Response:**

*   **`session_id`** (string, REQUIRED):
    *   This is the unique ID for the current chat session, echoing the `session_id` from the request. If our server kicked off a new session, this ID would be freshly generated here.
*   **`reply`** (object, REQUIRED):
    *   Contains Cappy's actual response to the user.
    *   **`reply.text`** (string, REQUIRED): The message text from Cappy.
    *   **`reply.timestamp`** (iso\_datetime\_string, REQUIRED): A server-side timestamp (ISO 8601) marking when Cappy's reply was generated.
*   **`updated_conversation_history`** (array of objects, REQUIRED):
    *   The full chat history for the session, now including the user's latest message and Cappy's new reply. Each message object here matches the structure used in the request's `conversation_history`.
*   **`suggested_actions`** (array of objects, OPTIONAL):
    *   A list of things the user might want to do next. We include these to help guide the conversation or give quick access to relevant features.
    *   Each action object includes:
        *   **`type`** (enum: `"quick_reply"` \| `"product_link"` \| `"referral_link"` \| `"external_url"`, REQUIRED): Specifies what kind of action it is.
            *   `"quick_reply"`: A pre-written message the user can tap to send immediately.
            *   `"product_link"`: A way to jump to a specific product page within the app.
            *   `"referral_link"`: A link to the app's referral section or a specific referral action.
            *   `"external_url"`: A link to an outside webpage.
        *   **`text_label`** (string, REQUIRED): The text shown to the user for this action (e.g., "Tell me more about cookies", "View Product X", "How do referrals work?").
        *   **`payload`** (string or object, REQUIRED): The data that makes the action work.
            *   For a `"quick_reply"`: This is the text that will be sent.
            *   For a `"product_link"`: Usually a product ID or a deep link URI.
            *   For `"referral_link"` / `"external_url"`: The URL or deep link URI.
*   **`debug_info`** (object, OPTIONAL):
    *   This section is just for us developers during prototyping and debugging—it shouldn't be shown to actual users in the live app.
    *   **`debug_info.intent_detected`** (string, OPTIONAL): What our system thought the user was trying to do (e.g., `"product_recommendation_request"`, `"referral_question"`).
    *   **`debug_info.retrieved_context_summary`** (string, OPTIONAL): A quick note on any background info we pulled to help Cappy answer (e.g., "Pulled 3 chunks from FAQ doc", "Found 5 products matching 'snack' in DB").
    *   **`debug_info.data_sources_used`** (array of strings, OPTIONAL): A list of the data sources Cappy consulted (e.g., `["FAQ_PDF", "Product_DB"]`).

### 2.4. Keeping Track: Our Conversation State Strategy
To make sure Cappy remembers what you've been talking about, we manage conversation state (mostly the message history) on our server, using the `session_id` that comes with each request. Here's how it works:

*   **Identifying the Session:** The `session_id` is our main tag for finding and updating a specific conversation.
*   **Quick Recall (In-Memory Cache):** For chats that are currently active, our `main.py` app keeps a handy in-memory Python dictionary (`conversation_sessions`). This dictionary links each `session_id` to a list of `Message` objects (the Pydantic models we defined earlier). This setup means we can quickly grab recent messages to build Cappy's next prompt.
*   **Saving for Posterity (Database Persistence):** We also save every user message and Cappy reply to the `Conversation_History` table in our [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite) database. The `save_conversation_message` function in `db_utils.py` takes care of this, making sure conversations aren't lost even if the app restarts. While we have a function (`get_conversation_history_from_db`) to pull history from the database, our current prototype doesn't use it to refill the in-memory cache during an ongoing session; we rely on the client potentially sending history or the session staying in our quick-recall cache.
*   **Getting a Head Start (Client-Side History):** The API is flexible enough to let the mobile app send its own `conversation_history`. If our server gets a request for a `session_id` it doesn't have in its in-memory cache, it'll use the history provided by the client to get up to speed.
*   **Memory for Cappy (History in LLM Prompt):** We feed Cappy a set number of recent messages (right now, it's the last 10, user and assistant turns included) from the session history. This gives Cappy the context it needs to follow the conversational flow.

### 2.5. When Things Go Sideways: Error Handling
We've built in a few ways to handle issues gracefully:

*   **Bad Requests (Validation Errors):** FastAPI is pretty smart about checking the incoming request data against our Pydantic models. If something's off (like a missing field or the wrong type of data), FastAPI automatically sends back an HTTP 422 "Unprocessable Entity" response, helpfully pointing out what went wrong.
*   **LLM Hiccups (Interaction Errors):**
    *   **Missing API Key:** If the `GOOGLE_API_KEY` isn't set up in the environment, we log a warning, skip calling the LLM, and Cappy gives a placeholder response like "[LLM Disabled]..."
    *   **Trouble Calling Gemini:** If something goes wrong when we try to talk to the Google Gemini API (network problems, API errors like model not found, rate limits, or content filter issues), our `get_gemini_response` function catches the problem. Cappy will then say something like, "Sorry, I encountered an error...". We also print more detailed error info to our server console so we can debug it.
*   **Database Woes (Interaction Errors):** Our `db_utils.py` functions are generally built to handle missing data smoothly (e.g., if a user isn't found, `get_user_details` just returns `None` or an empty dictionary). If bigger database problems pop up (like a connection failure), these could bubble up as standard Python exceptions. If our `main.py` endpoint logic doesn't specifically catch them, FastAPI would likely return a generic HTTP 500 "Internal Server Error."
*   **Unexpected Snags (General Unhandled Exceptions):** For any other errors that slip through in `main.py`, FastAPI usually defaults to sending a generic HTTP 500 "Internal Server Error."

## 3. How Cappy Works: The System Architecture

### 3.1. A Bird's-Eye View of Cappy's Brain

At its heart, our Carton Caps AI Conversational Assistant—Cappy, for short—is a smart Python service built with the speedy FastAPI framework. To understand and chat with users, Cappy relies on Google's Gemini Large Language Model (LLM). We keep track of user details, product info, and past chats mainly using a SQLite database. For testing and seeing Cappy in action, we've also put together a straightforward HTML/CSS/JavaScript front-end.

Here's a step-by-step look at how a conversation with Cappy unfolds:
1.  You, the user, start a chat through an interface like our test UI or the Carton Caps mobile app.
2.  The app sends your message over to Cappy's brain—our FastAPI backend—using the `/api/v1/carton_caps/chat` path.
3.  The backend figures out who you are (currently, it uses your `user_id`).
4.  It then looks up your details and any school info from our SQLite database.
5.  A clever part of Cappy tries to understand what your message is about—are you looking for a product, asking about referrals, or just chatting?
6.  Depending on what Cappy thinks you need:
    *   If it's about products, it fetches relevant details from the product list in the SQLite database.
    *   If it's a referral question, Cappy currently pulls information from a prepared text (like a digital FAQ sheet).
7.  Next, Cappy carefully crafts a message for the Gemini LLM. This message includes:
    *   Instructions on how to be Cappy, your name, your school, and firm rules about using only the facts provided.
    *   The information it just gathered (like product details or FAQ answers).
    *   A snippet of your recent chat history, so Cappy remembers what you were talking about.
    *   And, of course, your latest message.
8.  The Gemini LLM thinks it over and generates a reply.
9.  Our backend service takes this reply, tidies it up, and sends it back to the app.
10. Finally, to remember your conversation for next time, we save it to the SQLite database.

### 3.2. The Key Players: Cappy's Building Blocks

Cappy is made up of several important parts working together:

*   **The Brains of the Operation: FastAPI Backend (`carton_caps_ai_service/main.py`)**
    *   **What it is:** This is the central hub of Cappy.
    *   **What it does:**
        *   It opens up the `/api/v1/carton_caps/chat` doorway for conversations.
        *   It checks incoming messages to make sure they're in the right format (thanks to Pydantic models).
        *   It keeps track of user chats (for now, in its memory, but also saves them to the database).
        *   It figures out what you're asking, finds the right information, talks to the LLM, and shapes Cappy's reply.
        *   It also shows the simple test webpage at the `/ui` address.
*   **The Memory Bank: SQLite Database & Helpers (`carton_caps_ai_service/data/CartonCapsData.sqlite` & `db_utils.py`)**
    *   **What it is:** This is where Cappy stores most of its information.
    *   **What it does:**
        *   Keeps user details (in the `Users` table) and info about their chosen school (in the `Schools` table).
        *   Holds the list of products (in the `Products` table) with their names, descriptions, prices, and types.
        *   Records what users have bought before (in the `Purchase_History` table) – *though we're not actively using this to shape Cappy's advice just yet, the info is there for the future*.
        *   Saves all chat conversations (in the `Conversation_History` table) so we can look back at them or potentially use them to make Cappy smarter later on.
        *   The `db_utils.py` file contains handy tools (functions) for all the database tasks.
*   **The Wordsmith: Google Gemini LLM (using the `google-generativeai` toolkit)**
    *   **What it is:** This is Cappy's advanced language expert.
    *   **What it does:**
        *   It reads the combined message (Cappy's personality guide, background info, chat history, and your question) to understand what you mean.
        *   It crafts replies that sound natural and make sense in the conversation.
        *   We're currently using the `gemini-1.5-pro` model, but we can change this if needed.
*   **The Test Drive Interface: Static Frontend (`carton_caps_ai_service/static/`)**
    *   **What it is:** A simple webpage for us to try out Cappy and show how it works.
    *   **What it does:**
        *   It's an HTML page (`index.html`) with a chat window.
        *   It uses CSS (`style.css`) to make it look presentable.
        *   JavaScript (`script.js`) in the page helps to:
            *   Send your messages to Cappy's backend.
            *   Show Cappy's replies.
            *   Handle a `session_id` and `user_id` (right now, we've set it to '1' for testing).
            *   Display any quick action buttons Cappy suggests.
*   **The Detective Duo: Intent Detection & Context Retrieval (mostly in `main.py` with help from `db_utils.py`)**
    *   **What they are:** The parts that figure out what you want and find the right info.
    *   **What they do:**
        *   `main.py`: This is where the main detective work happens. It looks for keywords to guess if you're asking about products, referrals, or just chatting. It then directs the search for information—either by asking `db_utils` to look in the database or by grabbing text from our FAQ document.
        *   `db_utils.py`: This helper file has specific tools for talking to the SQLite database (like `get_user_details` to find out about you, or `get_products_by_keyword` to search for products).

### 3.3. Seeing How It All Connects: The System Diagram

**(Heads-up: A picture is worth a thousand words here! This section is ideally a visual chart. Think of the description below as the script for that chart. We could use something like Mermaid.js, draw.io, or even simple text art to draw it out.)**

The diagram would show how these main pieces talk to each other:

*   **You (via Mobile App / Our Test UI):** You kick things off by sending a message (with your User ID and Session ID) to Cappy's API.
*   **Cappy's HQ – FastAPI Backend (`main.py`):**
    *   Gets your message at its main chat address (`/api/v1/carton_caps/chat`).
    *   Works with `db_utils.py` to get info from the database.
    *   Has the smarts to figure out what you're asking (Intent Detection).
    *   Builds the right questions (prompts) to send to the Google Gemini LLM.
    *   Gets the answers back from the LLM.
    *   Shapes the final reply and sends it back to you.
    *   Keeps recent chats handy in its memory (`conversation_sessions`).
*   **Database Helper (`db_utils.py`):**
    *   Acts as the go-between for all chats with the SQLite Database.
    *   Has tools like `get_user_details` (to find out about you), `get_products_by_keyword` (to look for products), and `save_conversation_message` (to save your chat).
*   **Cappy's Memory Files – SQLite Database (`CartonCapsData.sqlite`):**
    *   This is where we keep lists of `Users`, `Schools`, `Products`, `Purchase_History`, and `Conversation_History`.
*   **The Language Whiz – Google Gemini LLM (an outside helper):**
    *   Gets questions (prompts) from Cappy's backend.
    *   Sends back well-written text replies.

**Key Handshakes to Illustrate:**

1.  **You to Cappy's HQ (FastAPI):** You send your message (an HTTP POST request).
2.  **Cappy's HQ to Database Helper to Memory Files (FastAPI -> `db_utils.py` -> SQLite):** Cappy looks up your details and school info.
3.  **Inside Cappy's HQ (FastAPI):** The "what are they asking?" logic runs.
4.  **Cappy's HQ to Database Helper to Memory Files (FastAPI -> `db_utils.py` -> SQLite):** If you're asking about products, Cappy looks them up.
5.  **Inside Cappy's HQ (FastAPI):** Cappy puts together the full message for the LLM (Cappy's persona + info from database + FAQ info + chat history + your current question).
6.  **Cappy's HQ to Language Whiz (FastAPI -> Google Gemini LLM):** Cappy sends the full message.
7.  **Language Whiz to Cappy's HQ (Google Gemini LLM -> FastAPI):** Cappy gets the LLM's answer.
8.  **Cappy's HQ to Database Helper to Memory Files (FastAPI -> `db_utils.py` -> SQLite):** Cappy saves this part of the chat.
9.  **Cappy's HQ to You (FastAPI -> Client):** Cappy sends its reply back to your app (an HTTP POST response).

### 3.4. Data Flow Diagrams

**(Note: Similar to the system diagram, these are best represented visually.)**

#### 3.4.1. "Cappy, Find Me a Snack!" - The Product Recommendation Journey

Here's how Cappy figures out what product to suggest when you ask for something like, "Recommend a snack for me.":

1.  **You Ask:** You type in your request, e.g., "Recommend a snack for me."
2.  **Message to Cappy's HQ:** Your app sends this to `/api/v1/carton_caps/chat` along with your `user_id`, `session_id`, and the message itself.
3.  **"Who's Asking?" Check:** Cappy's main brain (`main.py`) asks the `db_utils.py` helper to look up your details (like your name and school) using your `user_id`.
4.  **"What Do They Want?" Deduction:** The `main.py` brain realizes you're asking for a product ("product_query"). It then pulls out key terms, like "snack."
5.  **Product Hunt:** `main.py` tells `db_utils.py` to search the database for products matching "snack."
6.  **Building the LLM's Briefing:** Cappy's `main.py` now puts together a complete package for the Gemini LLM:
    *   The main instructions for Cappy (including your name and school).
    *   The list of snacks it found (e.g., "- Name: Fruit Snacks Pouch...").
    *   Your recent chat history.
    *   Your original question: "Recommend a snack for me."
7.  **Calling the Language Whiz:** The `get_gemini_response(prompt)` function sends this whole package to Gemini.
8.  **Gemini's Reply:** The LLM thinks it over and writes a response (e.g., "Hi Tracy! How about Fruit Snacks Pouch...").
9.  **Remembering the Chat:** The `save_conversation_message` helper saves your question and Cappy's answer in the database.
10. **Cappy's Answer to You:** A nicely formatted `ChatResponse` is sent back to your app.

#### 3.4.2. "How Do Referrals Work?" - The Referral Question Path

When you ask something like, "How do referrals work?", Cappy takes this route:

1.  **You Ask:** You type, "How do referrals work?"
2.  **Message to Cappy's HQ:** Your app sends this to `/api/v1/carton_caps/chat` with your `user_id`, `session_id`, and message.
3.  **"Who's Asking?" Check:** Just like before, `main.py` uses `db_utils.py` to get your user details.
4.  **"What Do They Want?" Deduction:** `main.py` figures out you're asking a "referral_question."
5.  **Grabbing the FAQ Info:** `main.py` pulls out the pre-written text about referrals (our current stand-in for an FAQ document).
6.  **Building the LLM's Briefing:** Again, `main.py` assembles the package for Gemini:
    *   Cappy's main instructions (with your name and school).
    *   The referral information it just grabbed.
    *   Your recent chat history.
    *   Your question: "How do referrals work?"
7.  **Calling the Language Whiz:** `get_gemini_response(prompt)` sends it off to Gemini.
8.  **Gemini's Reply:** The LLM crafts an answer (e.g., "Hey Tracy! Glad you asked about referrals...").
9.  **Remembering the Chat:** `save_conversation_message` logs the exchange in the database.
10. **Cappy's Answer to You:** The formatted `ChatResponse` comes back to your app.

## 4. Cappy's Secret Sauce: Our LLM Strategy

### 4.1. How Cappy Thinks: The Big Picture

Cappy is pretty smart, using a mix of looking up facts and understanding language like a human. We use Google's Gemini Pro model (specifically `gemini-1.5-pro`) because it's great at chatting and following detailed instructions.

Here's our game plan for making Cappy helpful and accurate:

1.  **Making it Personal:** Cappy gets to know you a bit by grabbing your details (like your name and the school you support) from our [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite) database. This info goes into the message we send to the LLM, so Cappy can make the chat feel more personal.
2.  **Figuring Out What You Need (and Finding the Info):**
    *   Cappy has a simple way of guessing what you're asking about (we call this "intent detection"). It looks for keywords in your message (this logic is in `main.py`) to see if you're asking about products, referrals, or just having a general chat.
    *   If you're asking about products, Cappy pulls out keywords from your message. Then, it searches the `Products` table in our SQLite database for items that match. If it finds any, it formats them nicely and adds them to the "Retrieved Context" part of the message for the LLM.
    *   If you're asking about referrals, Cappy actually reads our [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf) document (using a tool called PyMuPDF, or `fitz`) and pulls out the relevant text. This text also goes into the "Retrieved Context" for the LLM. This is a simple way of doing something called Retrieval Augmented Generation (RAG), which basically means Cappy can use documents to answer questions.
3.  **Letting the LLM Craft the Reply:** The LLM then takes all this information and writes a response. The message Cappy sends to the LLM is carefully put together and includes:
    *   A detailed "system message" that tells the LLM how to act like Cappy, gives it your details, and lays down strict rules about using (and not making up) the information provided.
    *   The information Cappy just found (like product details or text from the FAQ).
    *   A bit of your recent chat history so Cappy can remember what you've been talking about.
    *   And, of course, your latest message.
4.  **Keeping Cappy Honest (Grounding):** This is super important. We tell the LLM very clearly that for facts (like product details or how referrals work), it *must only* use the information Cappy gives it in the "Retrieved Context." If Cappy can't find the info, the LLM has to say so, not just invent an answer. For general chit-chat, the LLM can use its wider knowledge, but it still needs to sound like Cappy.

### 4.2. Cappy the Detective: Figuring Out What You Mean

Right now, Cappy plays detective to understand what you're asking for. Inside `main.py`, we've set up a straightforward system that looks for specific keywords in your message (after converting it to lowercase, just to be safe). It's a simple approach, but it works pretty well for what we need in this prototype.

Here's how Cappy categorizes your questions:

*   **"I'm Looking for a Product!" (Product Query Intent):** If your message includes words like "product," "recommend," "buy," "find," "search," or names of product types (like "cereal" or "snack"), Cappy flags it as a product request. Then, it kicks off a process to find more specific keywords in your message and asks our database helper (`db_utils.get_products_by_keyword()`) to go find those items.
*   **"Tell Me About Referrals!" (Referral Question Intent):** When Cappy spots words like "referral," "refer," or "friend," it knows you're asking about our referral program. For these questions, Cappy prepares by getting the relevant text from our FAQ information ready to send to the LLM.
*   **"Just Chatting!" (General Conversation Intent):** If your message doesn't have any of the keywords Cappy is looking for, it assumes you're just up for a general chat. In this case, Cappy doesn't go looking for specific information in the database; it lets the LLM handle the conversation based on Cappy's personality and your chat history.

**Thinking Ahead (Future Enhancements):** If Cappy needs to understand a much wider range of questions or more complicated phrasing, we could give it some more advanced detective tools. This might mean using a specialized NLU (Natural Language Understanding) system, perhaps even a dedicated model that's trained to classify intents, or we could explore using the LLM itself to figure out the intent if that proves to be a smart and quick option.

### 4.3. Cappy's Toolkit: How It Gathers Information (Our Current Approach)

You might hear about advanced AIs using "tool calling" or "function calling"—where the AI itself decides to use a specific tool to find information. Cappy isn't quite there yet. Instead, our backend service is the one that does the legwork *before* talking to the LLM. It gathers all the necessary info and then hands it over to the LLM as part of the instructions.

Think of it like Cappy having these built-in information-gathering skills:

*   **`getUserDetails(user_id)` (Finding out about you):** This is handled by the `db_utils.get_user_details()` function. It fetches your name and school information so Cappy can talk to you personally.
*   **`getProductsByKeyword(keywords)` (Hunting for products):** The `db_utils.get_products_by_keyword()` function takes care of this. It looks for products in the database that match your search terms. Cappy then formats these findings and includes them in its message to the LLM.
*   **`getReferralInfo()` (Getting the scoop on referrals):** This happens when `main.py` uses its `get_text_from_pdf()` function (which uses PyMuPDF/`fitz` as its helper) to read the [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf). The text it pulls out is then given to the LLM as context. This is our straightforward way of doing that RAG thing we mentioned earlier.

Once Cappy has gathered everything, the LLM is told (through the main system instructions) to use all the information found under the "Retrieved Context:" heading to answer your questions.

### 4.4. Teaching Cappy How to Talk: Our Prompt Strategy

Getting Cappy to behave the way we want—giving accurate, relevant, and safe answers—is all about crafting the right instructions for the LLM. This is what we call "prompt engineering." It's like writing a very detailed job description and set of rules for Cappy before every conversation.

#### 4.4.1. The Main Rulebook: Cappy's System Prompt

Before Cappy even sees your first message, we give the LLM a "system prompt" (you can find this in `main.py`). This sets the stage for everything Cappy does. Here are the key ingredients:

*   **"This is You, Cappy!":** We tell the LLM its role: "You are a friendly and helpful AI assistant for Carton Caps... Your name is Cappy."
*   **"Here's Who You're Talking To":** We give it context about you: "You are assisting user '{user_name}' who supports '{user_school_name}'."
*   **"Your Mission, Should You Choose to Accept It":** We define Cappy's main jobs: "Your primary goals are to help users find personalized product recommendations and understand the referral process."
*   **The Golden Rules (Super Important!):** These are Cappy's grounding instructions:
    *   "Stick to the script! Your answers must *only* come from the 'Retrieved Context' we give you and the 'Conversation History'."
    *   "For product suggestions, *only* list items if they're in the 'Retrieved Context'."
    *   "If the 'Retrieved Context' is empty, or says something like 'No specific products found', you *must* say you couldn't find matching products. No making things up!"
    *   "Same goes for referral questions: *only* use the 'Retrieved Context'. Don't invent referral program details."
*   **"Keep it Snappy!":** A little style advice: "Be concise and engaging."

#### 4.4.2. Giving Cappy the Facts: Adding Specific Information

Instead of writing brand new instructions for every single type of question, Cappy cleverly adds specific information into the main set of rules under a clear heading:

```
Retrieved Context:
{what_cappy_found_for_this_question}
```

*   **When you ask about products:** The `{what_cappy_found_for_this_question}` part will be filled with a list of products (like "- Name: Fruit Snacks Pouch, Price: $7.44, Description: ... ") or a note like "Sorry, no specific products found that match what you're looking for in our database."
*   **When you ask about referrals:** This part will contain all the text Cappy pulled from the [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf) document. If Cappy can't get that info, it will use a backup message.
*   **When you're just chatting:** The "Retrieved Context:" part might be left out, or Cappy might clearly state that it didn't need to look up any specific info for your question.

By doing this—combining the main rulebook with these just-in-time facts—we guide the LLM to use the information correctly for whatever you're asking about.

### 4.5. Helping Cappy Remember: Managing Chat History

To make sure Cappy can follow along with your conversation and not get lost, we help it remember what's been said. This "short-term memory" is key for smooth, back-and-forth chats.

Here's how Cappy keeps track:

*   **A Quick Peek at Recent Chats:** We send the LLM the last 10 messages from your current chat (this number can be changed, and it's handled by `session_history[-10:]` in `main.py`). These messages are formatted so the Gemini API knows who said what ("user" for you, "model" for Cappy). It looks something like this:
    ```
    Conversation History (most recent first):
    user: Your last message
    model: Cappy's last reply
    ... and so on for the last few turns
    ```
*   **Highlighting Your Latest Message:** Your *very latest* message isn't just thrown into the history pile. We add it separately after the history block. This makes it crystal clear to the LLM what specific question or statement it needs to respond to right now. Like this:
    ```
    User '{user_name}' (current query): {your_actual_message_text}
    Assistant Cappy:
    ```
*   **Where the History Lives:** As we talked about back in Section 2.4 (Keeping Track: Our Conversation State Strategy), we keep the chat history in a couple of places: quickly accessible in the computer's memory for the current chat session, and also saved more permanently in the `Conversation_History` table in our SQLite database.

This whole setup helps the LLM stay up-to-date with the flow of your conversation. It means Cappy can understand when you ask follow-up questions, refer back to something you said earlier, and (hopefully!) not repeat itself too much.

## 5. Where Cappy Gets Its Facts: Data Handling and Sources

### 5.1. Cappy's Main Filing Cabinet: The SQLite Database ([CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite))
This trusty database is where Cappy keeps its organized records about users and products. To get anything from this filing cabinet, Cappy uses special helper functions found in `carton_caps_ai_service/db_utils.py`.

#### 5.1.1. The `Schools` File: Keeping Track of Schools
*   **What it's for:** Cappy uses this file to find out the name of the school (`school_name`) you're supporting. It does this by looking up the `school_id` that's linked to you in the `Users` file (we'll get to that one next!). Knowing your school's name helps Cappy make the chat more personal (for instance, it might ask, "...to help out {user_school_name}?").
*   **Key Info Inside:** `school_id`, `school_name`.

#### 5.1.2. The `Users` File: Remembering Our Friends (You!)
*   **What it's for:** This file is all about you! Cappy uses it to find your first name (`first_name`) and the `school_id` for the school you're supporting. This info is super important for Cappy to chat with you personally and understand what you care about.
*   **Key Info Inside:** `user_id` (this is how Cappy looks you up), `first_name`, `school_id`.
*   **Room for Growth (Limitations):** Right now, this file doesn't have a place to remember things like your favorite snacks or if you prefer gluten-free options. It also doesn't store detailed location info that could help Cappy give even more tailored advice. We do have a spot for an email address, but Cappy isn't using that at the moment.

#### 5.1.3. `Products` Table
*   **Usage:** This is the catalog of products available through Carton Caps. When a user makes a product-related query, this table is searched (via `db_utils.get_products_by_keyword()`) using keywords extracted from the user's message. Matching products (name, price, description) are retrieved and presented to the user via the LLM.
*   **Fields Used:** `product_id`, `name`, `description`, `price`, `category` (though `category` is not explicitly used in the current keyword search logic, it is available).
*   **Limitations:** The `category` field could be better leveraged for more targeted searches if the keyword extraction logic was enhanced or if users queried by category directly. Product descriptions are relatively brief. No image URLs or stock information is available.

#### 5.1.4. `Purchase_History` Table
*   **Usage:** This table is designed to store records of past purchases. While the table structure exists and `db_utils.py` includes a function to fetch purchase history, this data is **not currently used** to inform LLM prompts or personalize recommendations in the prototype due to the mock data being empty and the complexity of summarizing purchase history effectively for an LLM being out of scope for the initial prototype.
*   **Fields Available:** `purchase_id`, `user_id`, `product_id`, `purchase_date`, `quantity`, `total_price`.
*   **Limitations:** The mock data for this table is empty. Integrating this meaningfully would require logic to summarize purchase patterns or identify frequently bought items.

#### 5.1.5. `Conversation_History` Table
*   **Usage:** This table logs every user message and assistant reply, linking them to a `session_id` and `user_id`. It serves as a persistent record of interactions.
*   **Fields Used:** `message_id` (auto-incrementing primary key), `session_id`, `user_id`, `role` (user/assistant), `content` (message text), `timestamp`.
*   **Functionality:** Primarily for logging and potential future analysis or rehydration of conversation state if the in-memory cache is lost (though rehydration from DB is not actively implemented for ongoing sessions in the prototype).

### 5.2. PDF Document: [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf)
*   **Role in Prototype:** This document serves as the primary knowledge source for answering user questions about the Carton Caps referral program.
*   **Implementation (Basic RAG):** The system implements a basic form of Retrieval Augmented Generation (RAG) for this document.
    *   When a "referral_question" intent is detected, the `get_text_from_pdf()` function in `main.py` is invoked.
    *   This function uses the PyMuPDF (`fitz`) library to open the [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf) file (located via a relative path from `main.py` to `goldenverba/data/Carton Caps Referral FAQs.pdf`) and extract its entire text content.
    *   The extracted text is then cleaned slightly (normalizing whitespace) and provided as the "Retrieved Context" to the LLM.
    *   If the PDF cannot be found or an error occurs during text extraction, a predefined fallback message is used as context, and an error is logged to the console.
*   **Benefit:** This allows the LLM to base its answers about referrals on the actual content of the FAQ document rather than a static, hardcoded string, making the information more dynamic and maintainable (by updating the PDF).
*   **Limitations:**
    *   The entire PDF text is currently loaded as context. For very large documents, this might exceed LLM context window limits or be inefficient. A more advanced RAG system would involve chunking the document and performing semantic search to retrieve only the most relevant snippets.
    *   The PDF text extraction quality depends on the PDF's structure; complex layouts or image-based text might not extract cleanly.
    *   No OCR is performed; text must be selectable in the PDF.

### 5.3. Data Limitations and Assumptions
*   **Static Product Categories:** The keyword matching for products relies on a predefined list of terms in `main.py` and the product names/descriptions. More dynamic or fuzzy matching against product categories or attributes is not implemented.
*   **Empty Purchase History:** The `Purchase_History` table in the mock data is empty, preventing its use for personalized recommendations based on past behavior.
*   **No User Preferences Data:** The `Users` table lacks fields for explicit user preferences (dietary, brand), limiting another vector for personalization.
*   **Basic RAG for PDF:** While text is extracted from the PDF, it's the entire document content. Advanced RAG techniques like chunking and semantic search are not used.
*   **Assumed Data Integrity:** The prototype assumes the data in the SQLite database is accurate and well-structured for the lookups being performed.

## 6. Integration with Carton Caps Mobile App (Conceptual)

This section outlines how the prototyped AI Conversational Assistant API could be integrated into the existing Carton Caps mobile application. The integration points assume the mobile app can make HTTP requests and handle JSON responses.

### 6.1. API Invocation
*   **Triggering the Chat Interface:** The mobile app would feature a dedicated chat interface (e.g., a floating action button, a menu item leading to a chat screen).
*   **Sending Messages:** When a user types and sends a message in this interface:
    *   The mobile app would construct a JSON payload matching the `ChatRequest` Pydantic model defined in `main.py` (and Section 2.2 of this document).
    *   An HTTP POST request would be made to the deployed AI service's endpoint: `https://<your_deployed_service_host>/api/v1/carton_caps/chat`.
    *   Standard HTTP headers (e.g., `Content-Type: application/json`, `Authorization` if applicable) would be included.

### 6.2. User Authentication Context
*   **Leveraging Existing Auth:** The Carton Caps mobile app is assumed to have an existing user authentication system.
*   **Passing `user_id`:** Once a user is authenticated in the app, their unique `user_id` (as known by the Carton Caps backend system and present in the `Users` table of [CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite)) **must** be included in the `user_id` field of the `ChatRequest` payload sent to the AI service.
*   **Authorization (Optional Enhancement):** For enhanced security, the AI service endpoint could be protected. The mobile app might send an auth token (e.g., JWT) obtained from the main Carton Caps backend. The AI service would then need a mechanism to validate this token (e.g., by calling an endpoint on the main backend or using a shared secret).

### 6.3. Displaying Responses and Suggested Actions
*   **Receiving Responses:** The mobile app would asynchronously await the HTTP response from the AI service.
*   **Parsing the `ChatResponse`:** The JSON response (conforming to the `ChatResponse` Pydantic model, see Section 2.3) would be parsed.
*   **Displaying Assistant's Reply:** The `reply.text` field would be displayed as a new message from the assistant in the chat UI.
*   **Updating Conversation History:** The app should manage its local display of conversation history. The `updated_conversation_history` from the response can be used to ensure synchronization, though the app might also optimistically append messages.
*   **Rendering Suggested Actions:** If the `suggested_actions` array is present in the response:
    *   The mobile app would dynamically render these as interactive UI elements (e.g., tappable chips or buttons below the latest message).
    *   **`quick_reply`:** Tapping this would pre-fill the user's input field with the `payload` string and potentially auto-send it.
    *   **`product_link`:** Tapping this would navigate the user to the relevant product details screen within the app, using the `payload` (e.g., product ID) to identify the product.
    *   **`referral_link`:** Tapping this would navigate the user to the referral section of the app, using the `payload` (e.g., a deep link URI).
    *   **`external_url`:** Tapping this would open the `payload` URL in the app's in-app browser or the device's default web browser.
*   **Handling Loading States and Errors:** The mobile app UI should handle loading states (while awaiting API response) and display user-friendly error messages if the API call fails or returns an error (e.g., network issues, server errors based on HTTP status codes).

## 7. Conversation Design Principles

Effective conversation design is key to creating an engaging and helpful AI assistant. The following principles guide the design of "Cappy," the Carton Caps AI assistant.

### 7.1. Persona: "Cappy"
*   **Friendly and Approachable:** Cappy should have a warm, welcoming, and positive tone. It should use emojis where appropriate to enhance friendliness but avoid overuse.
*   **Helpful and Knowledgeable (within its domain):** Cappy's primary goal is to assist users with product discovery and referral information related to Carton Caps. It should confidently provide information it has access to (from the database or simulated FAQs).
*   **Supportive of School Fundraising:** Cappy should subtly reinforce the Carton Caps mission by mentioning how user actions (like purchases or referrals) support their chosen school.
*   **Trustworthy and Transparent:** Cappy should be honest about its limitations. If it cannot fulfill a request or doesn't have specific information, it should say so clearly rather than guessing or providing misleading information. This is reinforced by the grounding instructions in the system prompt.
*   **Not Overly Chatty:** While friendly, Cappy should be concise and get to the point, respecting the user's time.

### 7.2. Key Interaction Principles
*   **Clarity:** Responses should be easy to understand, using simple language and avoiding jargon.
*   **Personalization:** Address the user by their name (e.g., "Hi Tracy!") and mention their supported school (e.g., "...to support Brookside Elementary?") when contextually appropriate to make the interaction feel more personal and relevant.
*   **Guidance and Proactivity:** Use suggested actions to guide the user towards common tasks or relevant next steps (e.g., offering to find a snack after a referral query).
*   **Efficiency:** Help users achieve their goals quickly. Product recommendations should be direct and include key information like price.
*   **Contextual Awareness:** Maintain conversation context using history to understand follow-up questions and provide coherent dialogue.
*   **Graceful Error Handling:** If an error occurs or a query cannot be understood, provide a polite and helpful message, and if possible, suggest alternative actions.
*   **Confirmation (Implicit/Explicit):** For important actions or information, Cappy might implicitly confirm understanding (e.g., "Looking for a tasty snack that also supports their school?"). Explicit confirmation might be needed for more critical (future) actions.

### 7.3. Handling Ambiguity and Errors (User-Facing)
*   **When Information is Not Found:** As per the system prompt, if product search yields no results or if referral information isn't available for a very specific edge case (beyond the current FAQ scope), Cappy should state this clearly. For example: "I couldn't find any [product type] matching that description right now. Would you like to try searching for something else?" or "I can help with general questions about how referrals work. For very specific account issues, you might need to check the main app help section."
*   **When User Intent is Unclear:** If a user's query is too vague for the current intent detection (e.g., just "Help"), Cappy could respond with its core capabilities: "I can help you find products that support your school or explain how the referral program works. What are you looking for today?" Suggested actions can also help clarify intent.
*   **Fallback Responses:** For queries completely outside its scope (e.g., "What's the weather like?"), Cappy should gently state its limitations: "I'm Cappy, your Carton Caps assistant! I can help with finding products and understanding referrals here. I don't have information on [off-topic subject] though."

## 8. Privacy Considerations

Protecting user privacy is paramount. While this is a prototype, the following privacy aspects are considered in its design and would require careful attention in a production system.

### 8.1. Data Sensitivity
*   **Personally Identifiable Information (PII):**
    *   **`user_id`:** While often an internal identifier, it links directly to a user.
    *   **User Name (`first_name` from `Users` table):** Directly PII, used for personalization.
    *   **Email (`email` from `Users` table):** PII, present in the database but *not* actively used by the AI assistant or included in LLM prompts.
    *   **School Name (`school_name` from `Schools` table):** While not directly PII for an individual, it can be sensitive in context with other user data.
*   **Conversation Content:** User messages can inadvertently contain PII or sensitive personal details. The `Conversation_History` table stores this content.
*   **Purchase History (`Purchase_History` table):** Records of purchases are sensitive user data. (Currently not used by the AI in the prototype).

### 8.2. Data Storage and Access
*   **SQLite Database ([CartonCapsData.sqlite](mdc:goldenverba/data/CartonCapsData.sqlite)):**
    *   **Access Control:** In a production environment, the database file itself and the server hosting the AI service would need strong access controls (e.g., file permissions, network ACLs, authentication for the service accessing the DB if it were a separate DB server).
    *   **Encryption at Rest:** For sensitive data, consider encrypting the database file at rest.
*   **Conversation Logs (`Conversation_History` table):**
    *   **Purpose:** Stored for session continuity and potential (future) analytics or fine-tuning.
    *   **Retention Policies:** In production, a clear data retention policy for conversation logs would be needed (e.g., anonymize or delete after a certain period).
    *   **Access Audits:** Mechanisms to audit access to conversation logs should be considered.
*   **In-Memory Data:** User-specific details and conversation history are temporarily held in memory (`conversation_sessions` in `main.py`) during an active session. This is cleared when the service restarts.

### 8.3. LLM Interactions
*   **Data Sent to LLM:** The prompt sent to the Google Gemini API includes:
    *   User's first name and their supported school's name.
    *   The user's current query.
    *   Recent conversation history (which may contain PII shared by the user).
    *   Contextual data retrieved from the database (product names, descriptions, prices) or simulated FAQs.
*   **Google's Data Usage Policies:** It is crucial to be aware of and comply with Google's data usage policies for the Gemini API. As of typical LLM API terms, data sent may be temporarily processed by Google to provide the service and potentially for service improvement, subject to their terms. Opt-out capabilities for data usage in model training should be investigated if available and aligned with privacy requirements.
*   **Minimizing PII to LLM:** While personalization is a goal, only necessary PII should be sent. For instance, the user's email is correctly *not* sent. The system avoids sending superfluous user details.
*   **Output Filtering (Safety):** The Gemini API has built-in safety filters to prevent the generation of harmful content. The AI service relies on these, but additional client-side or server-side checks could be added if specific concerns arise.

### 8.4. User Consent and Transparency
*   In a live application, users should be informed that their conversations with the AI assistant are processed and may be logged.
*   Clear terms of service and a privacy policy accessible from within the app would be necessary.

## 9. Trade-offs and Reasoning

Several design decisions were made during the development of this prototype, often balancing complexity, rapid development for a proof-of-concept, and robustness.

*   **Choice of FastAPI:**
    *   **Reasoning:** FastAPI was chosen for its high performance, ease of use, automatic data validation with Pydantic, and built-in OpenAPI/Swagger documentation. This allowed for rapid API development and clear contract definition.
    *   **Trade-off:** For a very small service, a simpler framework like Flask might have slightly less boilerplate, but FastAPI's benefits were deemed to outweigh this for building a well-structured API quickly.

*   **SQLite for Database:**
    *   **Reasoning:** SQLite is file-based, requires no separate server setup, and is easily bundled, making it ideal for a self-contained prototype and for working with the provided mock dataset.
    *   **Trade-off:** SQLite is not designed for high-concurrency production workloads that a popular mobile app might generate. A production system would likely use a more robust database server (e.g., PostgreSQL, MySQL, or a NoSQL alternative).

*   **Rule-Based Intent Detection:**
    *   **Reasoning:** Simple keyword matching is quick to implement and transparent for a limited set of intents (product queries, referral questions). It performed well for the defined scope.
    *   **Trade-off:** This approach is not scalable to a large number of intents or nuanced user utterances. It can be brittle if users phrase their queries in unexpected ways. A more sophisticated NLU component or LLM-based intent detection would be needed for a production system with broader capabilities.

*   **Simulated RAG for PDF FAQs:**
    *   **Reasoning:** Implementing a full RAG pipeline (PDF parsing, chunking, embedding, vector store, semantic search) was deemed out of scope for the initial prototype given time constraints. Using a hardcoded string provides the *effect* of RAG for the referral intent, allowing testing of the LLM's ability to use provided context.
    *   **Trade-off:** The system cannot answer questions about referrals beyond the content of the hardcoded string. It lacks the dynamic retrieval capabilities of a true RAG system.

*   **In-Memory Session Cache with DB Persistence for Conversation History:**
    *   **Reasoning:** The in-memory dictionary (`conversation_sessions`) provides fast access to recent conversation history for prompt construction. Persisting to the `Conversation_History` table ensures data isn't lost if the service restarts and allows for potential future analytics.
    *   **Trade-off:** If the service restarts, the in-memory cache is lost. While the API allows the client to send history, and history is in the DB, the current prototype doesn't automatically rehydrate the in-memory cache from the DB for an *existing session_id* upon a new request (it primarily relies on the client or the session still being in memory). A more robust session management system (e.g., using Redis) would be better for production.

*   **Direct Context Injection vs. LLM Tool Calling:**
    *   **Reasoning:** Retrieving data from the DB/FAQs *before* calling the LLM and injecting it directly into the prompt is a straightforward and reliable way to provide context for the current scope. It gives explicit control over what information the LLM sees.
    *   **Trade-off:** This approach is less flexible than LLM tool/function calling, where the LLM itself might decide which tools to use to gather information. However, for a well-defined set of tasks, direct injection can be more efficient and predictable.

*   **Google Gemini Pro Model (`gemini-1.5-pro`):**
    *   **Reasoning:** This model offers a good balance of advanced conversational capabilities, instruction following, and availability.
    *   **Trade-off:** Costs associated with LLM API calls need to be considered for a production system. Different models might offer varying performance/cost trade-offs.

*   **Limited Scope for User Profile Usage:**
    *   **Reasoning:** While the API contract includes a `user_profile` section, its use in the prototype is limited to name and school for personalization. Fully leveraging purchase history or preferences would significantly increase complexity.
    *   **Trade-off:** Personalization is currently basic. Deeper personalization is a clear area for future enhancement.

## 10. Future Evolution

This prototype lays a solid foundation. Several areas offer potential for future enhancements to create a more robust, capable, and intelligent AI assistant:

*   **Full RAG Implementation for FAQs:**
    *   Replace the hardcoded referral FAQ string with a proper RAG pipeline. This would involve:
        *   Processing the [Carton Caps Referral FAQs.pdf](mdc:goldenverba/data/Carton Caps Referral FAQs.pdf) (and potentially other documents) into text chunks.
        *   Generating embeddings for these chunks using a sentence transformer or similar model.
        *   Storing these embeddings in a vector database (e.g., Weaviate, Pinecone, FAISS).
        *   When a referral-related (or other FAQ-based) query is detected, perform a semantic search against the vector database to retrieve the most relevant chunks to inject into the LLM prompt.
*   **Enhanced Intent Detection and NLU:**
    *   Move beyond simple keyword matching to a more sophisticated NLU model for intent classification and slot filling. This could involve training a custom model or leveraging LLM capabilities for intent recognition.
    *   Support for a wider range of user intents (e.g., checking order status, managing account preferences, asking about specific school fundraising goals).
*   **Deeper Personalization:**
    *   **Utilize Purchase History:** Implement logic to analyze the `Purchase_History` table to offer recommendations based on past buying behavior, frequently bought items, or items often bought together.
    *   **User Preferences:** Allow users to specify preferences (e.g., dietary, brand, product categories) and store these in the `Users` table (or a new table). Use these preferences to filter and rank recommendations.
    *   **Location-Based Context:** If relevant (e.g., for promotions or region-specific products), incorporate location context more actively.
*   **Richer Product Interaction:**
    *   **Product Categories:** Improve product search and recommendations by fully utilizing the `Products.category` field or introducing tags.
    *   **Comparative Queries:** Enable users to compare products (e.g., "Which is healthier, X or Y?").
    *   **Multi-Modal Support (Conceptual):** If product images are available, future versions could conceptually support displaying images alongside recommendations.
*   **Advanced Conversational Features:**
    *   **Disambiguation:** When user queries are ambiguous, proactively ask clarifying questions.
    *   **Contextual Follow-ups:** More sophisticated proactive suggestions based on conversation flow.
    *   **Slot Filling for Complex Queries:** For multi-part requests (e.g., "Find me organic snacks under $5"), systematically gather all necessary information.
*   **Proactive Notifications/Engagement (with user consent):**
    *   Conceptually, the AI could (if integrated deeply with the app) proactively notify users about new products they might like, or special promotions for their school.
*   **Scalability and Productionization:**
    *   **Database:** Migrate from SQLite to a production-grade database system.
    *   **Session Management:** Implement a more robust distributed session store (e.g., Redis).
    *   **Deployment:** Containerize the application (e.g., using Docker) and deploy it on a scalable cloud platform (e.g., Kubernetes, AWS ECS, Google Cloud Run).
    *   **Monitoring and Logging:** Implement comprehensive logging and monitoring for performance, errors, and API usage.
*   **A/B Testing and Analytics:**
    *   Implement analytics to track common user queries, successful interactions, points of confusion, etc.
    *   Enable A/B testing of different prompts, LLM models, or features to optimize performance and user satisfaction.
*   **Security Enhancements:**
    *   Implement robust authentication/authorization for the API endpoint if deployed publicly.
    *   Regular security audits.

## 11. Glossary of Terms

*   **API (Application Programming Interface):** A set of rules and protocols that allows different software applications to communicate with each other.
*   **CRUD:** Create, Read, Update, Delete - basic operations for persistent storage.
*   **FastAPI:** A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
*   **Gemini:** A family of multimodal AI models developed by Google DeepMind.
*   **HTTP (Hypertext Transfer Protocol):** The foundation of data communication for the World Wide Web.
*   **Intent Detection/Recognition:** The process of identifying the user's goal or purpose behind a given utterance.
*   **JSON (JavaScript Object Notation):** A lightweight data-interchange format that is easy for humans to read and write and easy for machines to parse and generate.
*   **LLM (Large Language Model):** A type of artificial intelligence model trained on vast amounts of text data to understand, generate, and manipulate human language.
*   **NLG (Natural Language Generation):** A subfield of AI that focuses on producing natural language text from structured data or communicative intents.
*   **NLU (Natural Language Understanding):** A subfield of AI that focuses on machine reading comprehension, i.e., enabling computers to understand human language.
*   **PII (Personally Identifiable Information):** Any data that could potentially identify a specific individual.
*   **Prompt Engineering:** The process of designing and refining input prompts to guide LLMs toward desired outputs.
*   **Pydantic:** A Python library for data validation and settings management using Python type annotations.
*   **RAG (Retrieval Augmented Generation):** An AI framework for improving the quality of LLM responses by grounding the model on external sources of knowledge. It involves retrieving relevant information from a knowledge base and providing it as context to the LLM when generating a response.
*   **REST (Representational State Transfer):** An architectural style for designing networked applications, often used for web services.
*   **SQLite:** A C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine.
*   **SDK (Software Development Kit):** A collection of software development tools in one installable package.
*   **UI (User Interface):** The means by which a user and a computer system interact.
*   **UX (User Experience):** The overall experience of a person using a product, especially in terms of how easy or pleasing it is to use.

---