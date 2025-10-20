#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    # Add modules directory to path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    modules_path = os.path.join(BASE_DIR, '..', '..', '..', 'modules')
    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
