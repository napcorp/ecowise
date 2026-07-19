import json
import os
from supabase import create_client

# Path to the shared state file
if os.environ.get("VERCEL"):
    DEVICES_FILE = '/tmp/devices.json'
else:
    DEVICES_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')

DEFAULT_DEVICES = [
  {
    "id": "thermostat",
    "name": "Living Room Thermostat",
    "icon": "🌡️",
    "status": "OFF",
    "value": 74,
    "mode": "OFF",
    "eco_mode": True,
    "power_watts": 0
  },
  {
    "id": "coffee_plug",
    "name": "Kitchen Smart Plug",
    "icon": "☕",
    "status": "OFF",
    "value": 0,
    "mode": "OFF",
    "eco_mode": False,
    "power_watts": 0
  },
  {
    "id": "bedroom_lamp",
    "name": "Bedroom Lamp",
    "icon": "💡",
    "status": "OFF",
    "value": 50,
    "mode": "OFF",
    "eco_mode": False,
    "power_watts": 0
  },
  {
    "id": "garden_irrigation",
    "name": "Smart Garden Irrigation",
    "icon": "💦",
    "status": "OFF",
    "value": 0,
    "mode": "OFF",
    "eco_mode": False,
    "power_watts": 0
  }
]

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
            print(f"Failed to initialize Supabase client: {e}")
    return None

def load_devices():
    """Loads all devices from Supabase, falling back to JSON file."""
    client = get_supabase_client()
    if client:
        try:
            response = client.table("devices").select("*").execute()
            data = response.data
            if data:
                return sorted(data, key=lambda x: x['id'])
            else:
                # Try to seed database
                res = client.table("devices").insert(DEFAULT_DEVICES).execute()
                if getattr(res, 'data', None):
                    return sorted(res.data, key=lambda x: x['id'])
                else:
                    print("Supabase returned empty data on insert. RLS is likely active. Falling back to local JSON.")
        except Exception as e:
            print(f"Error reading devices from Supabase: {e}")
            
    if not os.path.exists(DEVICES_FILE):
        save_devices(DEFAULT_DEVICES)
        return sorted(DEFAULT_DEVICES, key=lambda x: x['id'])
    try:
        with open(DEVICES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading devices: {e}")
        return sorted(DEFAULT_DEVICES, key=lambda x: x['id'])

def save_devices(devices):
    """Saves all devices back to the JSON file (local fallback)."""
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2)
    except Exception as e:
        print(f"Error saving devices: {e}")

def get_devices():
    """Returns list of devices."""
    return load_devices()

def update_device(device_id, key, value):
    """
    Updates a single field in a device.
    Converts data types as appropriate. Supports Supabase and local file fallback.
    """
    # Parse parameter values into correct Python types
    if key in ('value', 'power_watts'):
        try:
            clean_val = str(value).replace('°', '').replace('%', '').strip()
            value = int(clean_val)
        except ValueError:
            pass
    elif key == 'eco_mode':
        value = str(value).lower() in ('true', 'yes', 'on', 'active')
        
    client = get_supabase_client()
    if client:
        try:
            res = client.table("devices").update({key: value}).eq("id", device_id).execute()
            if getattr(res, 'data', None):
                print(f"[Supabase Device Manager] Updated {device_id} -> {key}: {value}")
                return True
            else:
                print("Supabase update returned empty data. RLS is likely active. Falling back to local.")
        except Exception as e:
            print(f"Error updating device in Supabase: {e}")

    # Local fallback
    devices_list = load_devices()
    updated = False
    for device in devices_list:
        if device['id'] == device_id:
            device[key] = value
            updated = True
            break
            
    if updated:
        save_devices(devices_list)
        print(f"[Device Manager] Updated {device_id} -> {key}: {value} (Local)")
    return updated

def format_devices_for_chatbot(devices):
    """Formats the device database into a clean string block for the AI prompt context."""
    if not devices:
        return "  (No smart devices detected)"
        
    formatted = []
    for d in devices:
        dtype = d.get('type')
        name = d.get('name')
        status = d.get('status', 'OFF')
        
        if dtype == 'thermostat':
            mode = d.get('mode', 'Cooling')
            val = d.get('value', 74)
            eco = "Eco-Mode active" if d.get('eco_mode') else "Eco-Mode inactive"
            formatted.append(f"  - {name}: {status}, set to {val}°F ({mode}, {eco})")
        elif dtype == 'plug':
            conn = d.get('device_connected', 'Unknown')
            watts = d.get('power_watts', 0)
            formatted.append(f"  - {name}: {status} ({conn} connected, consuming {watts}W)")
        elif dtype == 'light':
            val = d.get('value', 100)
            formatted.append(f"  - {name}: {status} (Brightness: {val}%)")
        elif dtype == 'irrigation':
            next_run = d.get('next_run', 'Not scheduled')
            formatted.append(f"  - {name}: {status} (Next run scheduled for {next_run})")
        else:
            formatted.append(f"  - {name}: {status}")
            
    return "\n".join(formatted)
