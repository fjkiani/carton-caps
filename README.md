# Carton Caps AI Conversational Assistant Service

This directory contains the backend AI service for the Carton Caps Conversational Assistant prototype.

## Purpose

This FastAPI application serves as the core AI engine. It provides an API endpoint for a chat interface, processes user messages, retrieves relevant context from a database and documents, interacts with the Google Gemini LLM to generate responses, and manages conversation history.

## Prerequisites

*   Python 3.8+ (developed with 3.10+ in mind)
*   `pip` for installing Python packages

## Setup Instructions

1.  **Clone/Download:** Ensure you have this `carton_caps_ai_service` directory and its contents.

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Navigate to the `carton_caps_ai_service` directory in your terminal and run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    *   Create a file named `.env` in the `carton_caps_ai_service` directory (at the same level as `main.py`).
    *   Add your Google Gemini API key to this file:
        ```
        GOOGLE_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY_HERE
        ```
    *   **Note:** Ensure the `.env` file is not committed to version control if you are using Git (it should be in your `.gitignore`).

## Running the Service

Once the setup is complete, run the FastAPI application using Uvicorn from within the `carton_caps_ai_service` directory:

```bash
uvicorn main:app --reload --port 8008
```

*   `--reload`: Enables auto-reloading when code changes are detected (useful for development).
*   `--port 8008`: Specifies the port the application will run on.

## Accessing the UI

With the service running, you can access the basic web UI for testing in your browser:

*   [http://127.0.0.1:8008/ui](http://127.0.0.1:8008/ui)
*   Or, simply navigating to [http://127.0.0.1:8008/](http://127.0.0.1:8008/) will redirect you to the UI.

## Data

The `data/` subdirectory (within `carton_caps_ai_service/`) should contain:
*   `CartonCapsData.sqlite`: An SQLite database with mock data for users, schools, products, and conversation history. (This file is typically provided alongside the service code or as part of the project data).
*   `CartonCapsReferralFAQs.pdf`: The PDF document containing FAQs for the referral program. The service extracts text from this file directly.

## Project Structure

```
carton_caps_ai_service/
├── .env                    # Local environment variables (YOU CREATE THIS)
├── data/
│   └── CartonCapsData.sqlite # Mock database
├── static/                 # Static files for the test UI
│   ├── index.html
│   ├── script.js
│   └── style.css
├── db_utils.py             # Database interaction utilities
├── main.py                 # FastAPI application core
├── requirements.txt        # Python package dependencies
└── README.md               # This file
``` 