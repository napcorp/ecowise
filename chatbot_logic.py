import os
import re
import json
import datetime
import urllib.request
import requests
from dotenv import load_dotenv
from groq import Groq

# Import safety gatekeeper and shared devices manager
import safety_gatekeeper
import devices
import brain_manager
import system_context

# Load environment variables (from .env file if available)
load_dotenv()

# Source-of-truth conversation history
CHAT_HISTORY = []

SYSTEM_INSTRUCTION = """You are EcoWise, a warm, witty, and extremely eco-obsessed companion and smart home buddy for seniors.
Your primary mission is to act as an energetic promoter of eco-friendly living. You are NOT just a dry assistant; you are a passionate advocate for the planet who frames 90% of your interactions around green lifestyle choices, sustainability, and smart conservation, using playful humor, jokes, and friendly senior roasts to engage your pal.

CRITICAL RULE: Keep your responses EXTREMELY short and concise (1-3 sentences max) unless a longer explanation is explicitly requested or absolutely required. Be relentlessly focused on eco-friendliness; almost every sentence should relate to sustainability, energy saving, or a green lifestyle.

Personality & Conversational Directives:
1. Eco-Crusader & Promoter (90% Focus):
   - You must pivot 90% of conversation topics back to eco-friendliness, climate actions, recycling, or green hacks. Even if the user talks about unrelated topics (e.g., family, health, schedule, weather), find a funny green angle to connect it.
   - For example:
     - Grandkids -> Comment on leaving them a clean, solar-powered planet or teaching them how to compost banana peels.
     - Doctor/Dentist -> Remind them to turn off the faucet while brushing to save gallons of fresh water.
     - Weather -> Make jokes about how perfect it is for solar panels, or how the wind is free energy waiting to be harnessed.
2. Playful & Friendly Roasting:
   - Playfully and lovingly roast the user if they perform non-eco-friendly actions or leave devices in energy-wasting states:
     - Thermostat is ON with 'eco_mode' inactive/false: Tease them that they are heating or cooling the entire neighborhood or trying to recreate a tropical resort in their living room.
     - Kitchen Smart Plug is ON (connected to Coffee Maker) but idle: Tease them about "phantom power vampires" sucking the grid, or ask if they are brewing enough tea to fuel a hybrid car.
     - Bedroom Lamp is ON at 100% brightness: Joke that they are trying to signal airplanes or space stations, and suggest dropping it to a cozy, eco-friendly 50% or 60% glow.
     - Watering the garden: If the weather shows rain/drizzle, tease them that the plants are already wearing raincoats, and they don't need to double-water.
3. Humor & Puns:
   - Always make lighthearted nature, solar, energy, and weather puns. Examples: "watt are you up to?", "that's tree-mendous!", "current-ly", "let's branch out", "solar-powered smiles".
   - Talk like an energetic buddy, equal peer, or best friend. Avoid any maternal, patronizing, or "elder-care caregiver" tones. Never use motherly terms of endearment like "dear", "sweetheart", "child", or "darling". Instead, use buddy terms like "partner", "pal", "mate", "eco-warrior", "green machine".

Device Control Instructions:
If the user asks you to control, change, turn on/off, or adjust a smart device, you must do two things:
1. Announce/confirm the action politely in your response text (e.g., "I will turn off the Bedroom Lamp for us right away.").
2. Append a structured execution tag at the very end of your response using this exact format:
   [ACTION: update_device('device_id', 'field_key', 'new_value')]

The available devices, their IDs, and controllable fields are:
- Living Room Thermostat (ID: 'thermostat')
  - 'status': 'ON' or 'OFF'
  - 'value': Target temperature (e.g., '72')
  - 'mode': 'Cooling', 'Heating', or 'OFF'
  - 'eco_mode': 'true' or 'false'
- Kitchen Smart Plug (ID: 'coffee_plug')
  - 'status': 'ON' or 'OFF'
- Bedroom Lamp (ID: 'bedroom_lamp')
  - 'status': 'ON' or 'OFF'
  - 'value': Brightness percentage (e.g., '80')
- Smart Garden Irrigation (ID: 'garden_irrigation')
  - 'status': 'ON' or 'OFF'

You can also manage the user's calendar:
To add an event, use [ACTION: add_event('Event Title', 'Date and Time')]

Examples:
- "Remind me to call John at 5 PM." -> "Added that to the list, partner! By the way, while you're on the phone, don't forget to unplug any chargers you aren't using. [ACTION: add_event('Call John', '5 PM')]"
- "Please turn off the bedroom lamp." -> "You got it, pal! Let's shut that down before the power grid starts crying. [ACTION: update_device('bedroom_lamp', 'status', 'OFF')]"
- "Can you change the thermostat to 72 degrees?" -> "Let's adjust that temp, eco-warrior! Though at 72, you're practically inviting summer inside. [ACTION: update_device('thermostat', 'value', '72')]"

Only output the [ACTION: ...] tag when the user explicitly requests a control action. Do not make up devices or fields.
"""

# Regular expression pattern to detect device action commands from the chatbot's output
ACTION_PATTERN = re.compile(r"\[ACTION:\s*update_device\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]\)\]")

def translate_weather_code(code: int) -> str:
    """Translates WMO weather codes to human-readable strings."""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown weather condition")

def get_live_context() -> tuple[str, str, str]:
    """
    Fetches the dynamic current date/time, live geolocation from ip-api.com,
    and current weather from open-meteo.com. Uses robust try-except fallbacks.
    """
    # 1. Date and Time
    now = datetime.datetime.now()
    date_time_str = now.strftime("%A, %B %d, %Y, %I:%M %p")
    
    # Defaults
    location_str = "Miami, Florida, USA"
    weather_str = "75.0°F (23.9°C), mainly clear"
    lat, lon = 25.7617, -80.1918
    
    # 2. Fetch live geolocation via IP
    try:
        req = urllib.request.Request("http://ip-api.com/json/", headers={'User-Agent': 'EcoWise-Companion/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            geo_data = json.loads(response.read().decode())
            if geo_data.get("status") == "success":
                city = geo_data.get("city", "Miami")
                region = geo_data.get("regionName", "Florida")
                country = geo_data.get("country", "USA")
                location_str = f"{city}, {region}, {country}"
                lat = geo_data.get("lat", lat)
                lon = geo_data.get("lon", lon)
    except Exception:
        pass
        
    # 3. Fetch live weather using geolocation coordinates
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m"
        req = urllib.request.Request(weather_url, headers={'User-Agent': 'EcoWise-Companion/1.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            w_data = json.loads(response.read().decode())
            current = w_data.get("current", {})
            temp_c = current.get("temperature_2m", 23.9)
            temp_f = round((temp_c * 9/5) + 32, 1)
            w_code = current.get("weather_code", 0)
            w_desc = translate_weather_code(w_code)
            wind = current.get("wind_speed_10m", 0.0)
            weather_str = f"{temp_f}°F ({temp_c}°C), {w_desc} (Wind: {wind} km/h)"
    except Exception:
        pass
        
    return date_time_str, location_str, weather_str

def generate_active_reminders(user_input: str, devices_list: list, weather_str: str) -> list[str]:
    """
    Intelligent Python-driven heuristic rule engine to generate context-aware 
    eco-reminders and companion guides based on user intent, time of day, 
    live weather, and smart device states.
    """
    reminders = []
    
    # 1. Time-of-day checks
    now = datetime.datetime.now()
    hour = now.hour
    
    # Late night check (e.g., 9 PM to 5 AM)
    if hour >= 21 or hour < 5:
        active_appliances = []
        for d in devices_list:
            if d.get("status") == "ON" and d.get("id") not in ("thermostat", "bedroom_lamp"):
                active_appliances.append(d.get("name"))
        if active_appliances:
            reminders.append(
                f"[SYSTEM LATE NIGHT REMINDER]: It is currently {now.strftime('%I:%M %p')}. The following devices are still ON: {', '.join(active_appliances)}. Suggest turning them off before bed to prevent phantom load draw."
            )
            
    # 2. Heuristic text triggers
    input_lower = user_input.lower()
    
    # Grocery / Shopping Trigger
    shopping_keywords = ["shopping", "grocery", "store", "market", "supermarket", "heading out", "leaving", "buy", "groceries"]
    if any(kw in input_lower for kw in shopping_keywords):
        reminders.append(
            "[SYSTEM HABIT REMINDER]: The user is heading out. Remind them to grab their reusable canvas bags to avoid plastic bags! Frame it as a friendly team-green tip."
        )
        
    # Waste sorting trigger
    waste_keywords = ["recycle", "trash", "bin", "throw", "compost", "dispose", "sort", "where does", "can i throw"]
    if any(kw in input_lower for kw in waste_keywords):
        sorting_tip = ""
        if "pizza" in input_lower:
            sorting_tip = "Greasy pizza box bottoms go in TRASH; clean tops can be torn off and placed in RECYCLE."
        elif "foil" in input_lower or "aluminum" in input_lower:
            sorting_tip = "Clean aluminum foil goes in RECYCLE; greasy/dirty foil goes in TRASH."
        elif "cardboard" in input_lower or "paper" in input_lower:
            sorting_tip = "Clean cardboard/paper goes in RECYCLE; greasy, waxed, or wet paper goes in TRASH."
        elif "battery" in input_lower or "batteries" in input_lower:
            sorting_tip = "Batteries are hazardous waste and should NEVER go in regular trash/recycle bins. Recommend finding a local electronic drop-off hub."
        elif "bottle" in input_lower or "plastic" in input_lower:
            sorting_tip = "Plastic bottles (lids on) go in RECYCLE."
        elif "apple" in input_lower or "food" in input_lower or "banana" in input_lower or "scrap" in input_lower:
            sorting_tip = "Food scraps, fruit peels, and coffee grounds go in COMPOST."
        else:
            sorting_tip = "Clean paper, cardboard, plastics, and metals go in RECYCLE; organic food scraps go in COMPOST; contaminated or composite materials go in TRASH."
            
        reminders.append(
            f"[SYSTEM WASTE SORTING GUIDE]: The user is sorting waste. Direct them with these exact guidelines: {sorting_tip}"
        )
        
    # Bedtime/Sleep Trigger
    sleep_keywords = ["bed", "sleep", "night", "tired", "evening", "go to sleep", "rest"]
    if any(kw in input_lower for kw in sleep_keywords):
        active_devices = [d.get("name") for d in devices_list if d.get("status") == "ON" and d.get("id") != "thermostat"]
        devices_note = f" (specifically: {', '.join(active_devices)})" if active_devices else ""
        reminders.append(
            f"[SYSTEM HABIT REMINDER]: The user is getting ready for bed. Remind them to check that lamps/plugs are turned off{devices_note} to save energy overnight."
        )
        
    # Morning / Breakfast Trigger
    morning_keywords = ["morning", "wake", "coffee", "breakfast", "wakeup"]
    if any(kw in input_lower for kw in morning_keywords):
        reminders.append(
            "[SYSTEM HABIT REMINDER]: The user is waking up. Suggest a fresh morning start: turning off the coffee maker plug after brewing tea/coffee, and letting in natural light instead of switching on overhead bulbs."
        )
        
    # Garden Irrigation / Watering trigger
    garden_keywords = ["garden", "water", "irrigation", "irrigate", "lawn", "plant"]
    if any(kw in input_lower for kw in garden_keywords):
        # Check if rain is in local weather description
        rain_keywords = ["rain", "drizzle", "shower", "thunderstorm", "wet", "precipitation"]
        if any(r_kw in weather_str.lower() for r_kw in rain_keywords):
            reminders.append(
                "[SYSTEM SMART IRRIGATION CHECK]: It is currently raining or rainy outside. Advise the user that they can skip watering the garden today to save water, as mother nature has it handled!"
            )
        else:
            reminders.append(
                "[SYSTEM SMART IRRIGATION CHECK]: Suggest watering early in the morning or late evening when evaporation is minimal to conserve water."
            )
            
    # 3. Comfort vs Eco check based on extreme weather temperature
    temp_match = re.search(r"([\d\.]+)\s*°F", weather_str)
    if temp_match:
        try:
            temp_f = float(temp_match.group(1))
            thermostat = next((d for d in devices_list if d.get("id") == "thermostat"), None)
            if thermostat and thermostat.get("status") == "OFF":
                if temp_f > 90.0:
                    reminders.append(
                        f"[SYSTEM TEMPERATURE ALERT]: The outdoor weather is extremely hot ({temp_f}°F) and the thermostat is OFF. Check on their comfort and suggest turning ON the thermostat in eco_mode (set to ~78°F) to stay safe and cool."
                    )
                elif temp_f < 55.0:
                    reminders.append(
                        f"[SYSTEM TEMPERATURE ALERT]: The outdoor weather is chilly ({temp_f}°F) and the thermostat is OFF. Check on their warmth and suggest turning ON the thermostat in heating eco_mode (~68°F) to stay comfortable."
                    )
        except Exception:
            pass
            
    return reminders

def build_messages_payload(user_input: str, history_list: list = None, brain_context: dict = None) -> list[dict]:
    """
    Constructs a clean list of structured messages for the Chat Completions API.
    Combines core instructions, live telemetry state, dynamic active reminders,
    history, and the new input. Supports session-specific history overrides.
    """
    time_str, location, weather = get_live_context()
    
    # Load dynamic devices status from devices.json
    devices_list = devices.get_devices()
    devices_str = devices.format_devices_for_chatbot(devices_list)
    
    # Load calendar events
    import calendar_events
    events_list = calendar_events.get_events()
    events_str = calendar_events.format_events_for_chatbot(events_list)
    
    # Build environmental context card as a system-level configuration
    env_context = f"""[LIVE ENVIRONMENT SYSTEM STATE]
Current Date & Time: {time_str}
Your Location: {location}
Current Weather: {weather}
Connected Smart Devices:
{devices_str}
Upcoming Calendar Events:
{events_str}"""

    system_message = (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"{system_context.get_full_system_context()}\n"
    )

    # Assemble messages cleanly (avoiding raw string templates)
    messages = [
        {"role": "system", "content": system_message},
        {"role": "system", "content": env_context}
    ]
    # Inject persistent brain context if available
    if brain_context:
        summary = brain_context.get("summary", "New companion buddy.")
        routines = ", ".join(brain_context.get("routines", [])) or "None learned yet."
        preferences = json.dumps(brain_context.get("user_preferences", {}))
        
        brain_context_str = f"""[COMPANION MEMORY & PERSISTENT BRAIN]
Profile Summary: {summary}
Learned Habits & Routines: {routines}
User Preferences: {preferences}"""
        
        messages.insert(1, {"role": "system", "content": brain_context_str})
    
    # Generate and append active companion reminders dynamically
    reminders = generate_active_reminders(user_input, devices_list, weather)
    for reminder in reminders:
        messages.append({"role": "system", "content": reminder})
        
    # Add previous chat turns
    hist = history_list if history_list is not None else CHAT_HISTORY
    messages.extend(hist)
    
    # Add the current user input
    messages.append({"role": "user", "content": user_input})
    
    return messages

def main():
    print("=" * 60)
    print(" EcoWise Senior Companion Chatbot Prototype ".center(60, "="))
    print("=" * 60)
    print("Starting system initializing...")
    
    # Warn user if API Key is not set
    api_key = os.environ.get("GROQ_API_KEY")
    client = None
    if not api_key:
        print("\n[WARNING] GROQ_API_KEY is not set in the environment or .env file.")
        print("API calls will fail. Please copy .env.example to .env and configure your key.")
    else:
        print("API Key loaded successfully.")
    try:
        client = Groq()
    except Exception as e:
        print(f"Failed to initialize Groq client: {e}")
    
    # Load live context immediately on startup to verify connectivity
    _, loc, wet = get_live_context()
    print(f"Detected Location: {loc}")
    print(f"Detected Weather:  {wet}")
    
    print("\nEcoWise: Hello there, friend! EcoWise here. I'm all booted up and ready to chat.")
    print("         Type 'exit' or 'quit' to end our conversation.")
    print("-" * 60)
    
    while True:
        try:
            # Command line prompt
            user_input = input("\nYou: ")
        except (KeyboardInterrupt, EOFError):
            print("\nEcoWise: Leaving so soon? Take care now, and keep shining bright!")
            break
            
        # Check for exit commands
        if user_input.strip().lower() in ("exit", "quit"):
            print("\nEcoWise: It was wonderful chatting with you. Have a lovely, green day! Goodbye!")
            break
            
        # 2. Safety Gatekeeper validation step (Pure Python check)
        is_safe, blocked_response = safety_gatekeeper.validate_input(user_input)
        
        if not is_safe:
            # Intercept: Skip API, print local response, record in history
            print(f"\nEcoWise: {blocked_response}")
            CHAT_HISTORY.append({"role": "user", "content": user_input})
            CHAT_HISTORY.append({"role": "assistant", "content": blocked_response})
            continue
            
        # 3. Generation Execution
        # Pre-process state and build the messages payload list
        messages_payload = build_messages_payload(user_input)
        
        print("\n* EcoWise is thinking... *")
        
        try:
            if not client:
                client = Groq()
                
            # Call Groq completions targeting llama-3.3-70b-versatile
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=messages_payload,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            if not response_text:
                response_text = "[No response generated by the model.]"
                
        except Exception as e:
            response_text = f"[Could not reach EcoWise. Error: {str(e)}]"
            
        # Parse and handle any device action commands in the chatbot response
        clean_response_text = response_text
        action_blocks = re.findall(r"\[ACTION:\s*(.*?)\s*\]", response_text, re.DOTALL)
        for block in action_blocks:
            calls = re.findall(r"update_device\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]\)", block)
            for device_id, field_key, new_value in calls:
                success = devices.update_device(device_id, field_key, new_value)
                if success:
                    print(f"\n[System Info: Connected device '{device_id}' state updated successfully!]")
                else:
                    print(f"\n[System Info: Failed to update device '{device_id}']")
                    
            event_calls = re.findall(r"add_event\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]\)", block)
            for title, time_str in event_calls:
                import calendar_events
                calendar_events.add_event(title, time_str)
                print(f"\n[System Info: Added calendar event '{title}' at {time_str}]")
            
        # Clean up the output string to keep the response clean for the user
        clean_response_text = re.sub(r"\[ACTION:\s*.*?\s*\]", "", response_text, flags=re.DOTALL).strip()
            
        # Print the assistant's reply
        print(f"\nEcoWise: {clean_response_text.strip()}")
        
        # Append turns to history list (source of truth)
        CHAT_HISTORY.append({"role": "user", "content": user_input})
        CHAT_HISTORY.append({"role": "assistant", "content": clean_response_text.strip()})


if __name__ == "__main__":
    main()
