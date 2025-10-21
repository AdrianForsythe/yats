#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    # Set up environment
    project_root = os.path.dirname(os.path.abspath(__file__))
    modules_path = os.path.join(project_root, 'modules')
    
    env = os.environ.copy()
    pythonpath = env.get('PYTHONPATH', '')
    if pythonpath:
        pythonpath = f"{modules_path}:{project_root}:{pythonpath}"
    else:
        pythonpath = f"{modules_path}:{project_root}"
    env['PYTHONPATH'] = pythonpath
    
    # Change to web directory
    web_dir = os.path.join(project_root, 'sites', 'web')
    
    print("Syncing tickets already existing in HADES")
    pre_cmd = ['uv', 'run', 'python', 'manage.py', 'create_sequencing_tickets']
    subprocess.run(pre_cmd, cwd=web_dir, env=env)

    print("🚀 Starting YATS Development Server...")
    print("📁 Project root:", project_root)
    print("🌐 Server will be available at: http://localhost:8000")
    print("�� Admin interface: http://localhost:8000/admin")
    print("�� Username: admin, Password: admin")
    print("\nPress Ctrl+C to stop the server\n")

    # Run Django development server with simplified settings
    cmd = [
        'uv', 'run', 'python', 'manage.py', 'runserver', 
        '--settings=web.settings', '0.0.0.0:8000'
    ]
    
    try:
        subprocess.run(cmd, cwd=web_dir, env=env)
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")

if __name__ == '__main__':
    main()