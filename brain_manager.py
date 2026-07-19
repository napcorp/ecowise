import os
import json
import threading
from groq import Groq
from supabase import create_client

CHAT_HISTORY_FILE = "chat_history.json"
COMPANION_BRAIN_FILE = "companion_brain.json"

# In-memory caches
_chat_history = []
_brain_data = {
    "summary": "The user is a senior who has just started using the EcoWise Companion.",
    "routines": [],
    "user_preferences": {}
}

# Thread lock for file and memory updates
_lock = threading.Lock()

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        try:
            _supabase_client = create_client(url, key)
            return _supabase_client
        except Exception as e:
            print(f"Failed to initialize Supabase client in Brain Manager: {e}")
    return None

def load_all():
    """Loads chat history and compiled brain data from Supabase, falling back to local files."""
    global _chat_history, _brain_data
    with _lock:
        client = get_supabase_client()
        if client:
            try:
                # Load history
                hist_res = client.table("brain_memory").select("value").eq("key", "history").execute()
                if hist_res.data:
                    _chat_history = hist_res.data[0]["value"]
                else:
                    _chat_history = []
                
                # Load brain data
                brain_res = client.table("brain_memory").select("value").eq("key", "brain_profile").execute()
                if brain_res.data:
                    _brain_data = brain_res.data[0]["value"]
                else:
                    client.table("brain_memory").upsert({"key": "brain_profile", "value": _brain_data}).execute()
                return
            except Exception as e:
                print(f"[Brain Manager] Error loading from Supabase: {e}. Falling back to local files.")

        # Local Fallback
        # Load Chat History
        if os.path.exists(CHAT_HISTORY_FILE):
            try:
                with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                    _chat_history = json.load(f)
            except Exception as e:
                print(f"[Brain Manager] Error loading chat history: {e}")
                _chat_history = []
        else:
            _chat_history = []

        # Load Companion Brain Profile
        if os.path.exists(COMPANION_BRAIN_FILE):
            try:
                with open(COMPANION_BRAIN_FILE, "r", encoding="utf-8") as f:
                    _brain_data = json.load(f)
            except Exception as e:
                print(f"[Brain Manager] Error loading brain profile: {e}")
        else:
            # Save default
            save_brain(_brain_data)

def save_history(history):
    """Saves the provided chat history list to memory and database/disk."""
    global _chat_history
    with _lock:
        _chat_history = history
        client = get_supabase_client()
        if client:
            try:
                client.table("brain_memory").upsert({"key": "history", "value": _chat_history}).execute()
                return
            except Exception as e:
                print(f"[Brain Manager] Error saving history to Supabase: {e}")

        try:
            with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(_chat_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Brain Manager] Error saving chat history: {e}")

def save_brain(brain_data):
    """Saves the provided brain profile to memory and database/disk."""
    global _brain_data
    _brain_data = brain_data
    client = get_supabase_client()
    if client:
        try:
            client.table("brain_memory").upsert({"key": "brain_profile", "value": _brain_data}).execute()
            return
        except Exception as e:
            print(f"[Brain Manager] Error saving brain profile to Supabase: {e}")

    try:
        with open(COMPANION_BRAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(_brain_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Brain Manager] Error saving brain profile: {e}")

def get_history():
    """Returns a copy of the current chat history list."""
    with _lock:
        return list(_chat_history)

def get_brain_context():
    """Returns the compiled brain context formatted as a dictionary."""
    with _lock:
        return dict(_brain_data)

def clear_all():
    """Clears history and resets brain profile."""
    global _chat_history, _brain_data
    with _lock:
        _chat_history = []
        _brain_data = {
            "summary": "The user is a senior who has just started using the EcoWise Companion.",
            "routines": [],
            "user_preferences": {}
        }
        
        client = get_supabase_client()
        if client:
            try:
                client.table("brain_memory").upsert({"key": "history", "value": []}).execute()
                client.table("brain_memory").upsert({"key": "brain_profile", "value": _brain_data}).execute()
                # Clear calendar events too
                client.table("calendar_events").delete().neq("id", "0").execute()
                return
            except Exception as e:
                print(f"[Brain Manager] Error clearing database: {e}")

        if os.path.exists(CHAT_HISTORY_FILE):
            try:
                os.remove(CHAT_HISTORY_FILE)
            except Exception:
                pass
        save_brain(_brain_data)

def trigger_background_compile():
    """Triggers the asynchronous brain compiler in a separate thread."""
    thread = threading.Thread(target=_compile_brain_task)
    thread.daemon = True
    thread.start()

def _compile_brain_task():
    """Background task that runs Groq Llama 3.1 8B to summarize chat logs and learn routines."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[Brain Compiler] Skipping compilation: GROQ_API_KEY not found in environment.")
        return

    # Snapshot current history and brain state under lock
    with _lock:
        history_snapshot = list(_chat_history)
        brain_snapshot = dict(_brain_data)

    if not history_snapshot:
        return

    print("[Brain Compiler] Starting background chat history compilation...")

    system_prompt = """You are the companion profile compiler for 'EcoWise' smart home companion.



Your job is to read the conversation history, analyze the user's personality, routines, habits, and preferences, and update their persistent memory profile.

You must output a single JSON object with the following exact keys:
1. "summary": A concise, paragraph-level background summary about who the user is (e.g. name, hobbies, temperament, memory flags).
2. "routines": A JSON array of strings detailing their learned daily habits and routines (e.g., "Boils morning tea at 8:00 AM", "Turns off TV standby plug before bed at 10 PM").
3. "user_preferences": A JSON object containing key-value mappings of explicit likes, dislikes, temperature settings, and device behaviors.

You will be provided with:
- The previous compiled memory profile JSON.
- The recent conversation history.

Combine the previous memory with the new conversation history. Refine, correct, or append details as learned from new dialog turns. Do not invent details; only compile facts explicitly stated or strongly implied by the user's statements.
"""

    user_payload = {
        "previous_brain": brain_snapshot,
        "recent_chat_history": history_snapshot
    }

    try:
        client = Groq()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, indent=2)}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=15.0
        )
        
        output_text = response.choices[0].message.content
        new_brain_data = json.loads(output_text)
        
        # Validate keys in the response
        if "summary" in new_brain_data and "routines" in new_brain_data and "user_preferences" in new_brain_data:
            with _lock:
                save_brain(new_brain_data)
            print("[Brain Compiler] Background compilation complete. Profile updated successfully.")
        else:
            print("[Brain Compiler] Compilation error: Model output JSON is missing required keys.")
            
    except Exception as e:
        print(f"[Brain Compiler] Error compiling brain profile: {e}")
