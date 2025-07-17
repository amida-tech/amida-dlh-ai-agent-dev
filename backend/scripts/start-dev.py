#!/usr/bin/env python3
"""
Development startup script for Amida AI Ticket Orchestrator
"""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def run_command(cmd, name, background=False):
    """Run a command and optionally run it in background"""
    print(f"Starting {name}...")
    
    if background:
        return subprocess.Popen(cmd, shell=True)
    else:
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0

def check_dependencies():
    """Check if required services are running"""
    print("Checking dependencies...")
    
    # Check if PostgreSQL is accessible
    try:
        import psycopg2
        # This is a basic check - in production you'd want more robust checking
        print("✓ PostgreSQL driver available")
    except ImportError:
        print("✗ PostgreSQL driver not found. Please install psycopg2-binary")
        return False
    
    # Check if Redis is accessible
    try:
        import redis
        # This is a basic check
        print("✓ Redis driver available")
    except ImportError:
        print("✗ Redis driver not found. Please install redis")
        return False
    
    return True

def main():
    """Main development startup function"""
    print("=" * 50)
    print("Amida AI Ticket Orchestrator - Development Mode")
    print("=" * 50)
    
    # Change to the backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    if not check_dependencies():
        print("\nPlease install missing dependencies and try again.")
        return
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("\nWarning: .env file not found!")
        print("Please copy .env.example to .env and configure your settings.")
        create_env = input("Would you like to create a basic .env file now? (y/n): ")
        
        if create_env.lower() == 'y':
            with open(".env.example", "r") as source:
                with open(".env", "w") as target:
                    target.write(source.read())
            print("Created .env file. Please edit it with your actual configuration.")
    
    processes = []
    
    try:
        # Start FastAPI server
        fastapi_process = run_command(
            "uvicorn main:app --host 0.0.0.0 --port 8000 --reload",
            "FastAPI server",
            background=True
        )
        processes.append(("FastAPI", fastapi_process))
        
        # Give FastAPI a moment to start
        time.sleep(2)
        
        # Start Celery worker
        celery_process = run_command(
            "celery -A app.tasks.celery_app worker --loglevel=info",
            "Celery worker",
            background=True
        )
        processes.append(("Celery Worker", celery_process))
        
        print("\n" + "=" * 50)
        print("Development server started successfully!")
        print("=" * 50)
        print("API Server: http://localhost:8000")
        print("API Docs: http://localhost:8000/docs")
        print("Admin Interface: http://localhost:8000/admin (if implemented)")
        print("\nPress Ctrl+C to stop all services...")
        
        # Wait for interrupt
        while True:
            time.sleep(1)
            
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print(f"\n{name} has stopped unexpectedly!")
                    break
    
    except KeyboardInterrupt:
        print("\n\nShutting down services...")
        
        # Terminate all processes
        for name, process in processes:
            print(f"Stopping {name}...")
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Force killing {name}...")
                process.kill()
        
        print("All services stopped.")

if __name__ == "__main__":
    main()