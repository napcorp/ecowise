import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import traceback
from flask import Flask
from simulation_server import app, tts_api

long_text = "Hi there, buddy! Noticed you're not taking advantage of the clear sky today. Want to open those curtains and let some natural light in? We can save some energy and enjoy the view while we're at it! I've got the smart home devices right here, and I can guide you through it. Shall I help you get started on that, partner?"

# Create mock Flask application context
with app.test_request_context(json={"text": long_text}):
    try:
        print("Calling tts_api() with long text...")
        res = tts_api()
        print("Response:", res)
        if isinstance(res, tuple) and len(res) > 1 and res[1] == 500:
            print("Response body:", res[0].get_data(as_text=True))
    except Exception as e:
        print("Caught exception directly:")
        traceback.print_exc()
