#!/usr/bin/env python3
"""
Development server script for YATS
This script sets up the environment and runs the Django development server.
"""

import os
import sys
import subprocess

def main():
    # Set up the environment
    project_root = os.path.dirname(os.path.abspath(__file__))
    modules_path = os.path.join(project_root, 'modules')
    
    # Add modules to Python path
    env = os.environ.copy()
    pythonpath = env.get('PYTHONPATH', '')
    if pythonpath:
        pythonpath = f"{modules_path}:{project_root}:{pythonpath}"
    else:
        pythonpath = f"{modules_path}:{project_root}"
    env['PYTHONPATH'] = pythonpath
    
    # Change to the web directory
    web_dir = os.path.join(project_root, 'sites', 'web')
    
    # Run the Django development server
    cmd = [
        'uv', 'run', 'python', 'manage.py', 'runserver', 
        '--settings=web.settings_local', '0.0.0.0:8000'
    ]
    
    print("Starting YATS development server...")
    print("Server will be available at: http://localhost:8000")
    print("Admin interface: http://localhost:8000/admin")
    print("Username: admin, Password: admin")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run(cmd, cwd=web_dir, env=env)
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    main()

