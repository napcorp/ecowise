import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import traceback
from flask import Flask
from simulation_server import app, chat_api

# Create mock Flask application context
with app.test_request_context(json={"message": "hello"}):
    try:
        print("Calling chat_api()...")
        res = chat_api()
        print("Response:", res)
        print("Body:", res.get_data(as_text=True))
    except Exception as e:
        print("Caught exception directly:")
        traceback.print_exc()
