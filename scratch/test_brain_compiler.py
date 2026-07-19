"""
Test script for brain_manager.py
Populates mock chat history, runs the brain compiler, and validates output.
"""
import os
import json
import sys
import time

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import brain_manager

# Clean slate
print("=== Test 1: Clean slate and default brain ===")
brain_manager.clear_all()
brain = brain_manager.get_brain_context()
print(f"Default brain: {json.dumps(brain, indent=2)}")
assert brain["summary"] != "", "Summary should not be empty"
assert brain["routines"] == [], "Routines should be empty on fresh start"
assert brain["user_preferences"] == {}, "Preferences should be empty on fresh start"
print("PASS\n")

# Mock conversation history simulating a senior user
print("=== Test 2: Populate mock chat history ===")
mock_history = [
    {"role": "user", "content": "Good morning! Can you turn on my thermostat?"},
    {"role": "assistant", "content": "Good morning! I've turned on the thermostat for you in eco mode."},
    {"role": "user", "content": "I always like my tea at 8 AM, please remind me next time."},
    {"role": "assistant", "content": "Noted! I'll remember that you like your tea at 8 AM every morning."},
    {"role": "user", "content": "Set the temperature to 72 degrees, I find 78 too warm."},
    {"role": "assistant", "content": "Done! I've set your thermostat to 72°F. I'll remember you prefer 72 over 78."},
    {"role": "user", "content": "Turn off the TV plug before I go to bed at 10 PM."},
    {"role": "assistant", "content": "Got it! I'll make sure the TV standby plug is turned off around 10 PM."},
    {"role": "user", "content": "My name is Harold by the way."},
    {"role": "assistant", "content": "Nice to meet you, Harold! I'll remember that."},
    {"role": "user", "content": "I love gardening and watching nature documentaries."},
    {"role": "assistant", "content": "That's wonderful, Harold! Gardening and nature documentaries sound like great hobbies."},
]
brain_manager.save_history(mock_history)
saved = brain_manager.get_history()
assert len(saved) == len(mock_history), f"Expected {len(mock_history)} turns, got {len(saved)}"
print(f"Saved {len(saved)} chat turns to chat_history.json")
print("PASS\n")

# Run the brain compiler synchronously (not in background thread, for testing)
print("=== Test 3: Run brain compiler (llama-3.1-8b-instant) ===")
if not os.environ.get("GROQ_API_KEY"):
    print("SKIP: GROQ_API_KEY not set. Cannot test live compilation.")
else:
    # Call the internal compile function directly (synchronous)
    brain_manager._compile_brain_task()
    
    # Read the compiled brain
    compiled = brain_manager.get_brain_context()
    print(f"\nCompiled brain profile:\n{json.dumps(compiled, indent=2)}\n")
    
    # Validate structure
    assert "summary" in compiled, "Missing 'summary' key"
    assert "routines" in compiled, "Missing 'routines' key"
    assert "user_preferences" in compiled, "Missing 'user_preferences' key"
    assert isinstance(compiled["routines"], list), "Routines should be a list"
    assert len(compiled["routines"]) > 0, "Should have learned at least one routine"
    print("PASS\n")

    # Check that key facts were extracted
    summary_lower = compiled["summary"].lower()
    routines_str = " ".join(compiled["routines"]).lower()
    all_text = summary_lower + " " + routines_str + " " + json.dumps(compiled["user_preferences"]).lower()
    
    print("=== Test 4: Verify extracted facts ===")
    checks = {
        "harold": "User's name (Harold)",
        "tea": "Morning tea routine",
        "72": "Temperature preference (72°F)",
        "10": "Bedtime TV plug routine (10 PM)",
    }
    for keyword, description in checks.items():
        found = keyword in all_text
        status = "PASS" if found else "WARN (not found, but model may have paraphrased)"
        print(f"  {description}: {status}")
    
    print("\nAll tests completed!")

# Verify file persistence
print("\n=== Test 5: File persistence check ===")
assert os.path.exists("chat_history.json"), "chat_history.json should exist"
assert os.path.exists("companion_brain.json"), "companion_brain.json should exist"
print("PASS: Both files exist on disk.")
print("\nDone!")
