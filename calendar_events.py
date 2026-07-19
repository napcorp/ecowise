import json
import os
import uuid
from supabase import create_client

CALENDAR_FILE = os.path.join(os.path.dirname(__file__), 'calendar.json')

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        try:
            _supabase_client = create_client(url, key)
            return _supabase_client
        except Exception as e:
            print(f"Failed to initialize Supabase client in Calendar: {e}")
    return None

def load_events():
    client = get_supabase_client()
    if client:
        try:
            response = client.table("calendar_events").select("*").execute()
            return response.data
        except Exception as e:
            print(f"Error reading calendar from Supabase: {e}")

    if not os.path.exists(CALENDAR_FILE):
        return []
    try:
        with open(CALENDAR_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading events: {e}")
        return []

def save_events(events):
    try:
        with open(CALENDAR_FILE, 'w') as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"Error saving events: {e}")

def get_events():
    return load_events()

def add_event(title, time_str):
    new_event = {
        'id': str(uuid.uuid4())[:8],
        'title': title,
        'time': time_str
    }
    
    client = get_supabase_client()
    if client:
        try:
            client.table("calendar_events").insert(new_event).execute()
            print(f"[Supabase Calendar Manager] Added event: {title} at {time_str}")
            return new_event
        except Exception as e:
            print(f"Error adding event to Supabase: {e}")
            
    events = load_events()
    events.append(new_event)
    save_events(events)
    print(f"[Calendar Manager] Added event: {title} at {time_str} (Local)")
    return new_event

def delete_event(event_id):
    client = get_supabase_client()
    if client:
        try:
            response = client.table("calendar_events").delete().eq("id", event_id).execute()
            # If any rows were deleted, response.data will have entries
            if response.data:
                print(f"[Supabase Calendar Manager] Deleted event: {event_id}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting event in Supabase: {e}")
            
    events = load_events()
    initial_length = len(events)
    events = [e for e in events if e['id'] != event_id]
    if len(events) < initial_length:
        save_events(events)
        print(f"[Calendar Manager] Deleted event: {event_id} (Local)")
        return True
    return False

def format_events_for_chatbot(events):
    if not events:
        return "  (No upcoming events)"
    
    formatted = []
    for e in events:
        formatted.append(f"  - {e['time']}: {e['title']}")
    return "\n".join(formatted)
