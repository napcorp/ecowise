import os
import logging
import re
import tempfile
import asyncio
import edge_tts
from flask import Flask, render_template, jsonify, request, send_file
from groq import Groq

import devices
import safety_gatekeeper
import chatbot_logic as chatbot_app
import brain_manager
import calendar_events

FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend', 'dist'))

if os.path.exists(FRONTEND_DIST_DIR):
    app = Flask(__name__, static_folder=FRONTEND_DIST_DIR, static_url_path='')
else:
    app = Flask(__name__)

# Disable standard Flask request logging to keep the console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# In-memory web companion chat history (thread-safe session simulation)
WEB_CHAT_HISTORY = []

@app.route('/')
def index():
    """Serves the premium companion dashboard & chatbot page."""
    if os.path.exists(os.path.join(FRONTEND_DIST_DIR, 'index.html')):
        return send_file(os.path.join(FRONTEND_DIST_DIR, 'index.html'))
    return render_template('index.html')

@app.route('/api/devices', methods=['GET'])
def get_devices_api():
    """Returns the current list of smart devices and their states."""
    return jsonify(devices.get_devices())

@app.route('/api/events', methods=['GET'])
def get_events_api():
    """Returns the current list of calendar events."""
    return jsonify(calendar_events.get_events())

@app.route('/api/events', methods=['POST'])
def add_event_api():
    data = request.get_json() or {}
    title = data.get('title')
    time_str = data.get('time')
    if not title or not time_str:
        return jsonify({"error": "Missing title or time"}), 400
    new_event = calendar_events.add_event(title, time_str)
    return jsonify({"success": True, "event": new_event})

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event_api(event_id):
    success = calendar_events.delete_event(event_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": f"Event '{event_id}' not found"}), 404

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry_api():
    """Returns live date/time, location, and weather telemetry from APIs."""
    current_time, location, weather = chatbot_app.get_live_context()
    return jsonify({
        "time": current_time,
        "location": location,
        "weather": weather
    })

@app.route('/api/devices/<device_id>', methods=['POST'])
def update_device_api(device_id):
    """Updates a single attribute of a device from the simulator UI."""
    data = request.get_json() or {}
    key = data.get('key')
    value = data.get('value')
    
    if not key:
        return jsonify({"error": "Missing parameter 'key'"}), 400
        
    success = devices.update_device(device_id, key, value)
    
    if success:
        # Helper simulation rules to make the interface feel responsive:
        # 1. If Coffee Plug is turned ON, simulate coffee maker consuming power. If OFF, power is 0.
        if device_id == 'coffee_plug' and key == 'status':
            power = 15 if value == 'ON' else 0
            devices.update_device(device_id, 'power_watts', power)
            
        # 2. If thermostat mode is set to 'OFF', set status to 'OFF', else set to 'ON'
        if device_id == 'thermostat' and key == 'mode':
            status = 'OFF' if value == 'OFF' else 'ON'
            devices.update_device(device_id, 'status', status)
            
        # 3. If thermostat is turned ON/OFF via status switch, sync mode
        if device_id == 'thermostat' and key == 'status':
            mode = 'OFF' if value == 'OFF' else 'Cooling'
            devices.update_device(device_id, 'mode', mode)

        updated_device = next((d for d in devices.get_devices() if d['id'] == device_id), None)
        return jsonify({"success": True, "device": updated_device})
        
    return jsonify({"error": f"Device '{device_id}' not found"}), 404

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Handles messages from the web chatbot interface."""
    global WEB_CHAT_HISTORY
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message is empty"}), 400
        
    # 1. Safety Gatekeeper check
    is_safe, blocked_response = safety_gatekeeper.validate_input(message)
    if not is_safe:
        # Log to chat history so user sees blocked dialogue flow
        WEB_CHAT_HISTORY.append({"role": "user", "content": message})
        WEB_CHAT_HISTORY.append({"role": "assistant", "content": blocked_response})
        return jsonify({
            "response": blocked_response,
            "action_triggered": False
        })
        
    # 2. Groq Llama 4 Scout API Call
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        err_msg = "[System Warning: GROQ_API_KEY is not set. Configure it in your .env to enable chatbot replies.]"
        return jsonify({
            "response": err_msg,
            "action_triggered": False
        })
        
    try:
        client = Groq()
        # Build prompt messages payload dynamically inserting weather, coordinates location, time and active alerts
        brain_context = brain_manager.get_brain_context()
        messages_payload = chatbot_app.build_messages_payload(message, history_list=WEB_CHAT_HISTORY, brain_context=brain_context)
        
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages_payload,
            temperature=0.7,
            timeout=10.0
        )
        response_text = response.choices[0].message.content or "[No response generated]"
    except Exception as e:
        return jsonify({
            "response": f"[Could not reach EcoWise. Error: {str(e)}]",
            "action_triggered": False
        })
        
    # 3. Parse device control instructions ([ACTION: ...])
    action_triggered = False
    
    # Match the overall action block (or multiple blocks) and parse all updates inside it
    action_blocks = re.findall(r"\[ACTION:\s*(.*?)\s*\]", response_text, re.DOTALL)
    for block in action_blocks:
        calls = re.findall(r"update_device\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]\)", block)
        for device_id, field_key, new_value in calls:
            success = devices.update_device(device_id, field_key, new_value)
            if success:
                action_triggered = True
                
                # Sync dependencies immediately in simulation DB
                if device_id == 'coffee_plug' and field_key == 'status':
                    power = 15 if new_value == 'ON' else 0
                    devices.update_device(device_id, 'power_watts', power)
                if device_id == 'thermostat' and field_key == 'mode':
                    status = 'OFF' if new_value == 'OFF' else 'ON'
                    devices.update_device(device_id, 'status', status)
                if device_id == 'thermostat' and field_key == 'status':
                    mode = 'OFF' if new_value == 'OFF' else 'Cooling'
                    devices.update_device(device_id, 'mode', mode)
                    
        event_calls = re.findall(r"add_event\(['\"]([^'\"]*)['\"],\s*['\"]([^'\"]*)['\"]\)", block)
        for title, time_str in event_calls:
            calendar_events.add_event(title, time_str)
            action_triggered = True
                    
    # Clean response string of any control directives completely
    response_text = re.sub(r"\[ACTION:\s*.*?\s*\]", "", response_text, flags=re.DOTALL).strip()
        
    # Record conversation history turns
    WEB_CHAT_HISTORY.append({"role": "user", "content": message})
    WEB_CHAT_HISTORY.append({"role": "assistant", "content": response_text})
    
    # Cap conversation history at 40 entries
    if len(WEB_CHAT_HISTORY) > 40:
        WEB_CHAT_HISTORY = WEB_CHAT_HISTORY[-40:]
    
    # Save persistent chat history and trigger background brain compilation
    brain_manager.save_history(list(WEB_CHAT_HISTORY))
    brain_manager.trigger_background_compile()
        
    return jsonify({
        "response": response_text,
        "action_triggered": action_triggered
    })

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat_history_api():
    """Clears the session-specific chat history and resets the brain."""
    global WEB_CHAT_HISTORY
    WEB_CHAT_HISTORY = []
    brain_manager.clear_all()
    return jsonify({"success": True})

@app.route('/api/stt', methods=['POST'])
def stt_api():
    """Handles Speech-to-Text conversion using Groq Whisper."""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
        
    audio_file = request.files['audio']
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY is not set."}), 500
        
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name
            
        client = Groq()
        with open(temp_audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(temp_audio_path), file.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )
            
        os.remove(temp_audio_path)
        return jsonify({"text": transcription})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts', methods=['POST'])
def tts_api():
    """Handles Text-to-Speech conversion using Groq TTS (Orpheus)."""
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"tts_{os.urandom(4).hex()}.wav")
        
        client = Groq()
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice="daniel",
            input=text,
            response_format="wav"
        )
        
        # Save audio binary to temp file
        response.write_to_file(temp_audio_path)
            
        return send_file(temp_audio_path, mimetype="audio/wav", as_attachment=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_msg = str(e)
        if "model_terms_required" in err_msg or "terms acceptance" in err_msg:
            return jsonify({
                "error": "The Groq model 'canopylabs/orpheus-v1-english' requires terms acceptance. Please accept them at: https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
            }), 400
        elif "model_permission_blocked_org" in err_msg or "blocked at the organization level" in err_msg:
            return jsonify({
                "error": "The Groq model 'canopylabs/orpheus-v1-english' is blocked at the organization level. Please enable it in org settings at: https://console.groq.com/settings/limits"
            }), 403
        elif "model_permission_blocked_project" in err_msg or "blocked at the project level" in err_msg:
            return jsonify({
                "error": "The Groq model 'canopylabs/orpheus-v1-english' is blocked at the project level. Please enable it in project settings at: https://console.groq.com/settings/project/limits"
            }), 403
        elif "rate_limit_exceeded" in err_msg or "Rate limit reached" in err_msg or "429" in err_msg:
            return jsonify({
                "error": "Groq TTS rate limit reached. Continuing in text-only mode."
            }), 429
        return jsonify({"error": err_msg}), 500


if __name__ == '__main__':
    print("=" * 60)
    print(" EcoWise Smart Device Simulation Server ".center(60, "="))
    print("=" * 60)
    import sys, groq
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"Groq Version: {groq.__version__}")
    print("=" * 60)
    
    # Load persistent chat history and brain profile from disk
    brain_manager.load_all()
    saved_history = brain_manager.get_history()
    if saved_history:
        WEB_CHAT_HISTORY.extend(saved_history)
        print(f"Loaded {len(saved_history)} chat turns from persistent history.")
    brain = brain_manager.get_brain_context()
    print(f"Brain profile loaded. Routines: {len(brain.get('routines', []))} | Preferences: {len(brain.get('user_preferences', {}))}")
    
    print("=" * 60)
    print("Simulation server starting on: http://127.0.0.1:5000")
    print("Open this URL in your web browser to control devices.")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5000, debug=False)
