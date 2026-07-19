"""
Full integration test for the EcoWise companion app.
Tests: chat API, device control, TTS error handling, brain persistence, memory recall, clear chat.
"""
import requests
import json
import time
import os

BASE = "http://127.0.0.1:5000"

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if condition:
        passed += 1
    else:
        failed += 1
    return condition

# ============================================================
# STEP 0: Clear everything for a fresh start
# ============================================================
print("\n=== SETUP: Clear chat and brain for clean test ===")
requests.post(f"{BASE}/api/chat/clear", timeout=10)
print("  Cleared.\n")

# ============================================================
print("=== TEST 1: GET /api/devices ===")
r = requests.get(f"{BASE}/api/devices")
data = r.json()
test("Status 200", r.status_code == 200)
test("Returns list of devices", isinstance(data, list) and len(data) > 0, f"{len(data)} devices")
device_names = [d.get("name", "") for d in data]
test("Thermostat exists", any("thermostat" in n.lower() for n in device_names))

# ============================================================
print("\n=== TEST 2: POST /api/chat — introduce ourselves ===")
r = requests.post(f"{BASE}/api/chat", json={"message": "Hello! My name is Margaret. I drink chamomile tea every night at 9 PM before bed."}, timeout=20)
data = r.json()
test("Status 200", r.status_code == 200)
test("Has response", len(data.get("response", "")) > 10, data.get("response", "")[:100])
test("No ACTION leak", "[ACTION:" not in data.get("response", ""))

# ============================================================
print("\n=== TEST 3: POST /api/chat — share more preferences ===")
r = requests.post(f"{BASE}/api/chat", json={"message": "I like keeping my house at 70 degrees. Also I watch the news every morning at 7 AM."}, timeout=20)
data = r.json()
test("Status 200", r.status_code == 200)
test("Has response", len(data.get("response", "")) > 10, data.get("response", "")[:100])

# ============================================================
print("\n=== TEST 4: POST /api/chat — device control action ===")
r = requests.post(f"{BASE}/api/chat", json={"message": "Turn on the thermostat to 70 degrees in eco mode"}, timeout=20)
data = r.json()
test("Status 200", r.status_code == 200)
test("Has response", len(data.get("response", "")) > 5, data.get("response", "")[:100])
test("No ACTION leak", "[ACTION:" not in data.get("response", ""))

# Check thermostat state
r2 = requests.get(f"{BASE}/api/devices")
devs = r2.json()
thermo = next((d for d in devs if d.get("id") == "thermostat"), None)
if thermo:
    test("Thermostat responded to command", thermo.get("status") in ["ON", "on", True, "true", "True"], f"status={thermo.get('status')}")
else:
    test("Thermostat found", False)

# ============================================================
print("\n=== TEST 5: POST /api/tts — rate limit handling ===")
r = requests.post(f"{BASE}/api/tts", json={"text": "Hello world test"}, timeout=15)
if r.status_code == 200:
    test("TTS returned audio", r.headers.get("Content-Type", "").startswith("audio"))
elif r.status_code == 429:
    data = r.json()
    test("Rate limit returns 429 with clear message", "rate limit" in data.get("error", "").lower(), data.get("error", ""))
else:
    data = r.json() if "json" in r.headers.get("Content-Type", "") else {}
    test("TTS returns handled error", "error" in data, f"status={r.status_code}")

# ============================================================
print("\n=== TEST 6: Brain persistence — wait for compilation ===")
print("  Waiting 5 seconds for background brain compiler...")
time.sleep(5)

test("chat_history.json exists", os.path.exists("chat_history.json"))
with open("chat_history.json", "r", encoding="utf-8") as f:
    hist = json.load(f)
test("History has entries", len(hist) >= 6, f"{len(hist)} entries")

hist_text = json.dumps(hist).lower()
test("Margaret's name persisted in history", "margaret" in hist_text)
test("Chamomile tea persisted in history", "chamomile" in hist_text)

# ============================================================
print("\n=== TEST 7: Brain compilation — companion_brain.json ===")
test("companion_brain.json exists", os.path.exists("companion_brain.json"))
with open("companion_brain.json", "r", encoding="utf-8") as f:
    brain = json.load(f)

print(f"\n  --- Compiled Brain Profile ---")
print(f"  Summary: {brain.get('summary', 'N/A')}")
print(f"  Routines: {json.dumps(brain.get('routines', []), indent=4)}")
print(f"  Preferences: {json.dumps(brain.get('user_preferences', {}), indent=4)}")
print()

test("Brain has summary", "summary" in brain and len(brain["summary"]) > 10)
test("Brain has routines", "routines" in brain and isinstance(brain["routines"], list))
test("Brain has user_preferences", "user_preferences" in brain and isinstance(brain["user_preferences"], dict))

brain_text = json.dumps(brain).lower()
test("Brain learned Margaret's name", "margaret" in brain_text)
test("Brain learned chamomile tea routine", "chamomile" in brain_text or "tea" in brain_text)
test("Brain learned 70 degree preference", "70" in brain_text)
test("Brain learned news morning routine", "news" in brain_text or "7" in brain_text)

# ============================================================
print("\n=== TEST 8: MEMORY RECALL — ask the bot what it remembers ===")
r = requests.post(f"{BASE}/api/chat", json={"message": "What is my name? And what do I drink before bed?"}, timeout=20)
data = r.json()
test("Status 200", r.status_code == 200)
response_lower = data.get("response", "").lower()
print(f"  Bot response: {data.get('response', '')[:200]}")
test("Bot remembers Margaret", "margaret" in response_lower)
test("Bot remembers chamomile tea", "chamomile" in response_lower or "tea" in response_lower)

# ============================================================
print("\n=== TEST 9: MEMORY RECALL — ask about preferences ===")
r = requests.post(f"{BASE}/api/chat", json={"message": "What temperature do I prefer for my house?"}, timeout=20)
data = r.json()
test("Status 200", r.status_code == 200)
response_lower = data.get("response", "").lower()
print(f"  Bot response: {data.get('response', '')[:200]}")
test("Bot remembers 70 degrees", "70" in response_lower)

# ============================================================
print("\n=== TEST 10: Clear chat + brain reset ===")
r = requests.post(f"{BASE}/api/chat/clear", timeout=10)
data = r.json()
test("Clear returns success", data.get("success") == True)

with open("companion_brain.json", "r", encoding="utf-8") as f:
    brain_after = json.load(f)
test("Brain routines reset to empty", brain_after.get("routines") == [])
test("Brain preferences reset to empty", brain_after.get("user_preferences") == {})

# ============================================================
print(f"\n{'='*60}")
print(f"  RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
print(f"{'='*60}")
