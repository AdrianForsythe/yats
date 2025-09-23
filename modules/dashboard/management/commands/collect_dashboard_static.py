from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Collect static files for dashboard'

    def handle(self, *args, **options):
        self.stdout.write('Collecting dashboard static files...')
        
        # Ensure static directory exists
        static_dir = os.path.join(settings.BASE_DIR, 'data', 'static', 'dashboard')
        os.makedirs(static_dir, exist_ok=True)
        
        # Copy dashboard static files
        dashboard_static = os.path.join(settings.BASE_DIR, 'modules', 'dashboard', 'static', 'dashboard')
        if os.path.exists(dashboard_static):
            import shutil
            shutil.copytree(dashboard_static, static_dir, dirs_exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS('Successfully collected dashboard static files')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Dashboard static files not found')
            )
