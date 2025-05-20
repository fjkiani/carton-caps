document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const suggestedActionsContainer = document.getElementById('suggestedActionsContainer');

    // --- Configuration ---
    const API_URL = 'http://127.0.0.1:8008/api/v1/carton_caps/chat'; // Your FastAPI backend URL
    let currentSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`; // Simple unique session ID
    let currentUserId = '1'; // Replace with actual user ID if/when auth is available
    let conversationHistory = [];

    // --- Helper Functions ---
    function appendMessage(text, sender, isHTML = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender.toLowerCase());
        if (isHTML) {
            messageDiv.innerHTML = text; // Use innerHTML if text contains HTML, otherwise use textContent
        } else {
            const p = document.createElement('p');
            p.textContent = text;
            messageDiv.appendChild(p);
        }
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom
    }

    function displaySuggestedActions(actions) {
        suggestedActionsContainer.innerHTML = ''; // Clear previous actions
        if (actions && actions.length > 0) {
            actions.forEach(action => {
                const button = document.createElement('button');
                button.classList.add('suggested-action-button');
                button.textContent = action.text_label;
                button.addEventListener('click', () => {
                    // Send the payload of the quick reply as a new message
                    if (action.type === 'quick_reply') {
                        userInput.value = action.payload; // Put text in input
                        sendMessage(); // Send it
                    } else if (action.type === 'product_link' || action.type === 'referral_link' || action.type === 'external_url'){
                        // For links, you might want to handle them differently, 
                        // e.g., open in a new tab or trigger in-app navigation.
                        // For this basic UI, we can just append a message saying a link was clicked.
                        appendMessage(`<i>Clicked: ${action.text_label} (Payload: ${action.payload})</i>`, 'system', true);
                        // Optionally, if it's a URL, you could try to open it:
                        // if (action.payload.startsWith('http')) { window.open(action.payload, '_blank'); }
                    }
                });
                suggestedActionsContainer.appendChild(button);
            });
        }
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (messageText === '') return;

        appendMessage(messageText, 'user');
        userInput.value = ''; // Clear input field
        suggestedActionsContainer.innerHTML = ''; // Clear suggested actions after sending

        // Add user message to local history for sending
        conversationHistory.push({ 
            role: "user", 
            content: messageText, 
            timestamp: new Date().toISOString()
        });

        // Prepare request payload
        const payload = {
            user_id: currentUserId,
            session_id: currentSessionId,
            message: {
                text: messageText,
                timestamp: new Date().toISOString()
            },
            conversation_history: conversationHistory.slice(-10), // Send last 10 messages for context
            user_profile: { // Example: populate as needed
                school_info: {
                    // school_id: "1", // Example, fetch dynamically if possible
                    // school_name: "Sunnydale Elementary" // Example
                }
            }
            // client_context: { current_view: "chat_test_page" }
        };

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error occurred."}));
                console.error('API Error:', response.status, errorData);
                appendMessage(`Error: ${errorData.detail || 'Could not reach server.'}`, 'assistant');
                return;
            }

            const data = await response.json();
            
            appendMessage(data.reply.text, 'assistant');
            displaySuggestedActions(data.suggested_actions);

            // Update conversation history with the full history from the server
            if (data.updated_conversation_history) {
                conversationHistory = data.updated_conversation_history.map(msg => ({
                    ...msg,
                    // Ensure timestamp is in a consistent format if needed, though API should provide ISO
                })); 
            }
            
        } catch (error) {
            console.error('Fetch Error:', error);
            appendMessage('Error: Could not connect to the AI assistant.', 'assistant');
        }
    }

    // Event Listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Initial greeting or setup can go here if needed
    // For example, you could make an initial call to get a greeting
    // or set user_id and session_id more robustly.
}); 