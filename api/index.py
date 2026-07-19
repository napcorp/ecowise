import os
import sys

# Add root folder to sys.path so Vercel can find simulation_server.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation_server import app
