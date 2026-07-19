import os
import re
from dotenv import load_dotenv
from groq import Groq

import devices
import app

# Load environmental context
load_dotenv()

def run_test():
    # 1. Reset state (Bedroom Lamp OFF)
    print("Setting Bedroom Lamp to OFF...")
    devices.update_device("bedroom_lamp", "status", "OFF")
    print(f"Current Bedroom Lamp status in DB: {next(d['status'] for d in devices.get_devices() if d['id'] == 'bedroom_lamp')}")
    
    # 2. Reset Living Room Thermostat value to 74
    print("Setting Thermostat value to 74...")
    devices.update_device("thermostat", "value", 74)
    
    # Verify API key is present
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n[ERROR] GROQ_API_KEY is not set in your .env file.")
        print("Please configure GROQ_API_KEY to test Groq functionality.")
        return
        
    client = Groq()
    
    # Target Llama 3.3 70B versatile on Groq
    test_model = 'llama-3.3-70b-versatile'
    
    # Mock User: "EcoWise, please turn off the Living Room Thermostat."
    user_input = "EcoWise, please turn off the Living Room Thermostat."
    print(f"\nUser says: {user_input}")
    
    # Build clean messages list via app utility
    messages_payload = app.build_messages_payload(user_input)
    
    try:
        response = client.chat.completions.create(
            model=test_model,
            messages=messages_payload,
            temperature=0.7
        )
        response_text = response.choices[0].message.content
        print(f"Raw Model response:\n{response_text}")
        
        # Check if ACTION pattern matches
        match = app.ACTION_PATTERN.search(response_text)
        if match:
            device_id, field_key, new_value = match.groups()
            print(f"\nFound ACTION tag: device_id={device_id}, field_key={field_key}, new_value={new_value}")
            success = devices.update_device(device_id, field_key, new_value)
            print(f"Database update status: {success}")
            
            # Verify the database contains the update
            updated_val = next(d[field_key] for d in devices.get_devices() if d['id'] == device_id)
            print(f"New state in database: {device_id}.{field_key} = {updated_val}")
            
            clean_text = app.ACTION_PATTERN.sub("", response_text).strip()
            print(f"Cleaned response: {clean_text}")
        else:
            print("\nNo ACTION tag found in response!")
            
    except Exception as e:
        print(f"API Call failed: {e}")

if __name__ == "__main__":
    run_test()
