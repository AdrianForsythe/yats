# yats/management.py
#!/usr/bin/env python3
"""
YATS Management Scripts
"""
import os
import sys
import subprocess
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent

def get_web_dir():
    """Get the web application directory."""
    return get_project_root() / "sites" / "web"

def run_command(cmd, cwd=None, env=None):
    """Run a command with proper environment setup."""
    if cwd is None:
        cwd = get_web_dir()
    
    if env is None:
        env = os.environ.copy()
    
    # Set up Python path
    project_root = get_project_root()
    modules_path = project_root / "modules"
    
    pythonpath = env.get('PYTHONPATH', '')
    if pythonpath:
        pythonpath = f"{modules_path}:{project_root}:{pythonpath}"
    else:
        pythonpath = f"{modules_path}:{project_root}"
    env['PYTHONPATH'] = pythonpath
    
    return subprocess.run(cmd, cwd=cwd, env=env)

def run_migrations():
    """Run Django migrations."""
    print("🔄 Running Django migrations...")
    cmd = ["uv", "run", "python", "manage.py", "migrate", "--settings=web.settings"]
    result = run_command(cmd)
    if result.returncode == 0:
        print("✅ Migrations completed successfully!")
    else:
        print("❌ Migration failed!")
    return result.returncode

def collect_static():
    """Collect static files."""
    print("�� Collecting static files...")
    cmd = ["uv", "run", "python", "manage.py", "collectstatic", "--noinput", "--settings=web.settings"]
    result = run_command(cmd)
    if result.returncode == 0:
        print("✅ Static files collected successfully!")
    else:
        print("❌ Static file collection failed!")
    return result.returncode

def create_superuser():
    """Create a Django superuser."""
    print("👤 Creating Django superuser...")
    cmd = ["uv", "run", "python", "manage.py", "createsuperuser", "--settings=web.settings"]
    result = run_command(cmd)
    if result.returncode == 0:
        print("✅ Superuser created successfully!")
    else:
        print("❌ Superuser creation failed!")
    return result.returncode

def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    cmd = ["uv", "run", "pytest", "sites/web/", "-v"]
    result = run_command(cmd, cwd=get_project_root())
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    return result.returncode

def format_code():
    """Format code with black."""
    print("🎨 Formatting code...")
    cmd = ["uv", "run", "black", "modules/", "sites/"]
    result = run_command(cmd, cwd=get_project_root())
    if result.returncode == 0:
        print("✅ Code formatted successfully!")
    else:
        print("❌ Code formatting failed!")
    return result.returncode

def lint_code():
    """Lint code with flake8."""
    print("�� Linting code...")
    cmd = ["uv", "run", "flake8", "modules/", "sites/"]
    result = run_command(cmd, cwd=get_project_root())
    if result.returncode == 0:
        print("✅ Code linting passed!")
    else:
        print("❌ Code linting failed!")
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  migrate     - Run Django migrations")
        print("  collectstatic - Collect static files")
        print("  createsuperuser - Create Django superuser")
        print("  test        - Run tests")
        print("  format      - Format code with black")
        print("  lint        - Lint code with flake8")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "migrate":
        sys.exit(run_migrations())
    elif command == "collectstatic":
        sys.exit(collect_static())
    elif command == "createsuperuser":
        sys.exit(create_superuser())
    elif command == "test":
        sys.exit(run_tests())
    elif command == "format":
        sys.exit(format_code())
    elif command == "lint":
        sys.exit(lint_code())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)