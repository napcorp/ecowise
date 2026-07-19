import subprocess
import sys
import os
import signal
import time
from threading import Thread

def stream_output(pipe, prefix):
    """Reads lines from a subprocess pipe and prints them with a prefix."""
    try:
        for line in iter(pipe.readline, b''):
            line_str = line.decode('utf-8', errors='replace').rstrip()
            print(f"[{prefix}] {line_str}")
    except ValueError:
        pass # Pipe closed

def load_env():
    """Loads environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

def main():
    print("=" * 60)
    print(" EcoWise Integrated Launcher (Backend + Frontend) ".center(60, "="))
    print("=" * 60)
    
    # Load .env so GROQ_API_KEY is available
    load_env()
    
    backend_process = None
    frontend_process = None

    try:
        # 1. Start Python Backend
        print("Starting Flask Backend on port 5000...")
        backend_process = subprocess.Popen(
            [sys.executable, "-u", "simulation_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(__file__)
        )
        
        Thread(target=stream_output, args=(backend_process.stdout, "BACKEND"), daemon=True).start()

        # Wait a moment for backend to initialize
        time.sleep(2)
        
        # 2. Start React Frontend
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
        print("Starting Vite Frontend on port 5173...")
        
        # Use shell=True for npm on Windows
        is_windows = sys.platform.startswith('win')
        npm_cmd = ["npm.cmd", "run", "dev"] if is_windows else ["npm", "run", "dev"]
        
        frontend_process = subprocess.Popen(
            npm_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=frontend_dir,
            shell=is_windows
        )
        
        Thread(target=stream_output, args=(frontend_process.stdout, "FRONTEND"), daemon=True).start()

        print("=" * 60)
        print(" Both servers are running. Press Ctrl+C to stop.")
        print("=" * 60)

        # Keep main thread alive
        while True:
            time.sleep(1)
            
            # Check if either process crashed
            if backend_process.poll() is not None:
                print("Backend process terminated unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("Frontend process terminated unexpectedly.")
                break

    except KeyboardInterrupt:
        print("\nShutting down servers...")
    
    finally:
        # Cleanup processes
        if backend_process and backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait()
            print("Backend stopped.")
            
        if frontend_process and frontend_process.poll() is None:
            # On Windows, terminating the shell doesn't kill the child Node process cleanly
            if sys.platform.startswith('win'):
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                frontend_process.terminate()
                frontend_process.wait()
            print("Frontend stopped.")

if __name__ == "__main__":
    main()
