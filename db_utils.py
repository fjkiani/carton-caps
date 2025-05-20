import sqlite3
import os
import datetime # Ensure datetime is imported
from typing import Optional, List, Dict, Any

# --- IMPORTANT: Adjust this path if your DB is located elsewhere relative to this file ---
# Assuming 'data' subdirectory at the same level as db_utils.py
DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DATABASE_NAME = 'CartonCapsData.sqlite' # Make sure this matches your actual DB file name
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_NAME)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DATABASE_PATH):
        print(f"Database file not found at: {DATABASE_PATH}")
        raise FileNotFoundError(f"Database file not found at: {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Makes rows accessible by column name
    return conn

def get_user_details(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetches user details and their associated school name."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                u.id as user_id, 
                u.name as user_name, 
                u.email as user_email,
                s.id as school_id,
                s.name as school_name,
                s.address as school_address
            FROM Users u
            LEFT JOIN Schools s ON u.school_id = s.id
            WHERE u.id = ?;
        """
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_details: {e}")
        return None
    except FileNotFoundError:
        # Error already printed by get_db_connection
        return None

def get_products_by_keyword(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetches products matching a keyword in name or description."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Using two LIKE clauses for broader search
        query = """
            SELECT id, name, description, price 
            FROM Products 
            WHERE name LIKE ? OR description LIKE ? 
            LIMIT ?;
        """
        search_term = f"%{keyword}%"
        cursor.execute(query, (search_term, search_term, limit))
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return products
    except sqlite3.Error as e:
        print(f"Database error in get_products_by_keyword: {e}")
        return []
    except FileNotFoundError:
        return []

def get_purchase_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetches purchase history for a user, joining with product names."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT 
                ph.id as purchase_id,
                ph.product_id,
                p.name as product_name,
                ph.quantity,
                ph.purchased_at
            FROM Purchase_History ph
            JOIN Products p ON ph.product_id = p.id
            WHERE ph.user_id = ?
            ORDER BY ph.purchased_at DESC
            LIMIT ?;
        """
        cursor.execute(query, (user_id, limit))
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return history
    except sqlite3.Error as e:
        print(f"Database error in get_purchase_history: {e}")
        return []
    except FileNotFoundError:
        return []

# --- Functions for Conversation History (Task 2.4) ---
def save_conversation_message(session_id: str, user_id: str, role: str, content: str, timestamp: datetime.datetime) -> Optional[int]:
    """Saves a message to the Conversation_History table."""
    # Ensure this table exists and matches the schema in your DB.
    # The current DB dump has `Conversation_History` with (id, user_id, message, sender, timestamp)
    # We'll map `role` to `sender` and `content` to `message`.
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO Conversation_History (user_id, message, sender, timestamp) 
            VALUES (?, ?, ?, ?);
        """
        # Assuming 'sender' in DB corresponds to 'role'
        cursor.execute(query, (user_id, content, role, timestamp.isoformat()))
        conn.commit()
        message_db_id = cursor.lastrowid
        conn.close()
        print(f"Saved message for session {session_id} (DB ID: {message_db_id})")
        return message_db_id
    except sqlite3.Error as e:
        print(f"Database error in save_conversation_message for session {session_id}: {e}")
        return None
    except FileNotFoundError:
        return None


def get_conversation_history_from_db(session_id: str, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches conversation history for a user from the Conversation_History table."""
    # Note: The DB table doesn't have session_id.
    # This function will fetch by user_id for now, which might mix sessions if one user has multiple.
    # For true session isolation with DB, the Conversation_History table would need a session_id column.
    # Or, we rely on the in-memory `conversation_sessions` for strict session isolation in the prototype.
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, user_id, message as content, sender as role, timestamp 
            FROM Conversation_History
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?;
        """
        cursor.execute(query, (user_id, limit))
        # Convert timestamps back to datetime objects if stored as strings
        history_raw = [dict(row) for row in cursor.fetchall()]
        history = []
        for msg_raw in reversed(history_raw): # Reverse to get chronological order
            try:
                msg_raw['timestamp'] = datetime.datetime.fromisoformat(msg_raw['timestamp'])
                history.append(msg_raw)
            except (TypeError, ValueError) as e:
                print(f"Warning: Could not parse timestamp for message ID {msg_raw.get('id')}: {msg_raw.get('timestamp')}, error: {e}")
                # Add with original timestamp string or skip
                history.append(msg_raw)

        conn.close()
        return history
    except sqlite3.Error as e:
        print(f"Database error in get_conversation_history_from_db for user {user_id}: {e}")
        return []
    except FileNotFoundError:
        return [] 