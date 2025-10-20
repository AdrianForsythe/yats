# -*- coding: utf-8 -*-
"""
Management command to sync MinKNOW sequencing runs to Gantt chart
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import logging
import os

from dashboard.models import Task
from runner.gc_connect.nanopore_utils import NanoporeConnector
from dashboard.config import MinKNOWConfig
from dotenv import load_dotenv

# import sensitive data from .env file
load_dotenv()
nanopore_host = os.getenv("NANOPORE_HOST")
nanopore_port = os.getenv("NANOPORE_PORT")
nanopore_ssh_user = os.getenv("NANOPORE_SSH_USER")
nanopore_password = os.getenv("NANOPORE_PASSWORD")
sync_days = os.getenv("MINKNOW_SYNC_DAYS", 30)

logger = logging.getLogger(__name__)

POSITION_COLORS = {
    'X1': '#607D8B',  # Blue Grey - MinKNOW position 1
    'X2': '#795548',  # Brown - MinKNOW position 2
    'X3': '#FFC107',  # Amber - MinKNOW position 3
    'X4': '#4CAF50',  # Green - MinKNOW position 4
    'X5': '#9C27B0',  # Purple - MinKNOW position 5
    '1A': '#00BCD4',  # Cyan - Alternative naming
    '1B': '#FF5722',  # Deep Orange
    '1C': '#3F51B5',  # Indigo
    '1D': '#8BC34A',  # Light Green
    '1E': '#CDDC39',  # Lime
}

class Command(BaseCommand):
    help = 'Sync MinKNOW sequencing runs to Gantt chart'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=sync_days,
            help=f'Number of days in the past to sync runs from (default: {sync_days})'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing Nanopore tasks before syncing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually creating tasks'
        )

    def handle(self, *args, **options):
        days_back = options['days']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']

        # Validate environment variables
        if not nanopore_host or not nanopore_port or not nanopore_ssh_user:
            raise CommandError(
                'Missing required environment variables. Please set:\n'
                '  NANOPORE_HOST\n'
                '  NANOPORE_PORT\n'
                '  NANOPORE_SSH_USER\n'
                'in your .env file'
            )

        self.stdout.write(
            self.style.NOTICE(f'Connecting to MinKNOW at {nanopore_host}:{nanopore_port}...')
        )

        # Initialize connector with SSH tunnel support
        try:
            connector = NanoporeConnector(
                host=nanopore_host, 
                port=int(nanopore_port), 
                ssh_user=nanopore_ssh_user,
                ssh_password=nanopore_password,
                use_ssh_tunnel=True
            )
            success = connector.connect()
            if not success:
                raise CommandError('Failed to establish connection to MinKNOW')
        except Exception as e:
            raise CommandError(f'Failed to connect to MinKNOW: {e}')

        # Clear existing Nanopore tasks if requested
        if clear_existing:
            if dry_run:
                existing_count = Task.objects.filter(source='nanopore').count()
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Would delete {existing_count} existing Nanopore tasks'
                    )
                )
            else:
                deleted_count = Task.objects.filter(source='nanopore').delete()[0]
                self.stdout.write(
                    self.style.WARNING(f'Deleted {deleted_count} existing Nanopore tasks')
                )

        # Get runs from the specified time period
        since = timezone.now() - timedelta(days=days_back)
        self.stdout.write(
            self.style.NOTICE(f'Fetching runs since {since.strftime("%Y-%m-%d %H:%M")}...')
        )

        try:
            all_runs = self.get_all_runs_from_connector(connector, since)
        except Exception as e:
            raise CommandError(f'Failed to fetch runs from MinKNOW: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'Found {len(all_runs)} protocol runs')
        )

        # Create or update tasks for each run
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Group runs by position to create parent tasks
        runs_by_position = {}
        for run in all_runs:
            position = run['position_name']
            if position not in runs_by_position:
                runs_by_position[position] = []
            runs_by_position[position].append(run)

        # Get position colors from config
        position_colors = MinKNOWConfig.POSITION_COLORS

        for position_name, runs in runs_by_position.items():
            # Get or create parent task for this position
            parent_task_id = self.get_or_create_position_parent(
                position_name,
                position_colors.get(position_name, '#607D8B'),
                dry_run
            )

            # Process each run
            for run in runs:
                external_id = f"{position_name}_{run['run_id']}"
                
                # Check if task already exists
                existing_task = Task.objects.filter(
                    source='nanopore',
                    external_id=external_id
                ).first()

                # Prepare task data
                task_data = self.prepare_task_data(run, parent_task_id, position_colors.get(position_name, '#607D8B'))

                if dry_run:
                    if existing_task:
                        self.stdout.write(
                            f'[DRY RUN] Would update: {task_data["text"]} '
                            f'({task_data["start_date"]} - {task_data["end_date"]})'
                        )
                    else:
                        self.stdout.write(
                            f'[DRY RUN] Would create: {task_data["text"]} '
                            f'({task_data["start_date"]} - {task_data["end_date"]})'
                        )
                    continue

                if existing_task:
                    # Update existing task
                    for key, value in task_data.items():
                        setattr(existing_task, key, value)
                    existing_task.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated: {task_data["text"]}')
                    )
                else:
                    # Create new task
                    Task.objects.create(**task_data)
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created: {task_data["text"]}')
                    )

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.NOTICE('\n[DRY RUN] No changes were made')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSync complete: {created_count} created, '
                    f'{updated_count} updated, {skipped_count} skipped'
                )
            )

        connector.disconnect()

    def get_all_runs_from_connector(self, connector: NanoporeConnector, since: datetime) -> list:
        """
        Get all protocol runs from all positions using NanoporeConnector.
        Adapts the NanoporeConnector API to match the expected format.
        """
        all_runs = []
        
        try:
            # Get all positions
            positions = connector.get_positions()
            
            for position_name, position_info in positions.items():
                try:
                    # Get position connection
                    conn = connector.get_position_connection(position_name)
                    
                    # List all protocol runs for this position
                    run_ids = connector.list_protocol_runs(position_name)
                    
                    for run_id in run_ids:
                        try:
                            # Get detailed run information
                            run_info = conn.protocol.get_run_info(run_id=run_id)
                            
                            # Extract run data
                            run_data = {
                                'run_id': run_id,
                                'position_name': position_name,
                                'position_location': position_info.get('location', 'Unknown'),
                                'protocol_id': getattr(run_info, 'protocol_id', ''),
                                'user_info': {},
                                'start_time': None,
                                'end_time': None,
                                'state': 'unknown',
                                'acquisition_run_ids': []
                            }
                            
                            # Extract user info if available
                            if hasattr(run_info, 'user_info'):
                                ui = run_info.user_info
                                run_data['user_info'] = {
                                    'protocol_group_id': getattr(ui, 'protocol_group_id', ''),
                                    'sample_id': getattr(ui, 'sample_id', ''),
                                    'flow_cell_id': getattr(ui, 'flow_cell_id', ''),
                                }
                            
                            # Extract timestamps
                            if hasattr(run_info, 'start_time') and run_info.start_time:
                                run_data['start_time'] = datetime.fromtimestamp(run_info.start_time.seconds)
                            
                            if hasattr(run_info, 'end_time') and run_info.end_time and run_info.end_time.seconds > 0:
                                run_data['end_time'] = datetime.fromtimestamp(run_info.end_time.seconds)
                            
                            # Get state
                            if hasattr(run_info, 'state'):
                                run_data['state'] = str(run_info.state)
                            
                            # Filter by date if specified
                            if since and run_data['start_time']:
                                if run_data['start_time'] < since:
                                    continue
                            
                            all_runs.append(run_data)
                            
                        except Exception as e:
                            logger.warning(f"Failed to get details for run {run_id}: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Failed to get runs for position {position_name}: {e}")
                    continue
            
            return all_runs
            
        except Exception as e:
            logger.error(f"Failed to get all runs: {e}")
            raise

    def get_or_create_position_parent(self, position_name: str, color: str, dry_run: bool = False):
        """Get or create parent task for a flow cell position"""
        if dry_run:
            # For dry run, just return a placeholder ID
            return "0"

        parent_task = Task.objects.filter(
            source='nanopore',
            external_id=f'position_{position_name}'
        ).first()

        if not parent_task:
            # Calculate the span of all runs for this position
            position_runs = Task.objects.filter(
                source='nanopore',
                external_id__startswith=f'{position_name}_'
            )

            if position_runs.exists():
                earliest_start = min(run.start_date for run in position_runs)
                latest_end = max(run.end_date for run in position_runs)
            else:
                # Default to current time if no runs
                earliest_start = timezone.now()
                latest_end = timezone.now() + timedelta(hours=1)

            duration = (latest_end - earliest_start).total_seconds() / 3600  # hours

            parent_task = Task.objects.create(
                text=f'Nanopore - {position_name}',
                start_date=earliest_start,
                end_date=latest_end,
                duration=duration,
                progress=0.0,
                parent='0',
                color=color,
                readonly=True,
                source='nanopore',
                external_id=f'position_{position_name}',
                sort_order=1000  # Place Nanopore tasks towards the end
            )

        return str(parent_task.id)

    def prepare_task_data(self, run: dict, parent_id: str, color: str) -> dict:
        """Prepare task data from Nanopore run information"""
        # Extract run details
        position_name = run['position_name']
        run_id = run['run_id']
        external_id = f"{position_name}_{run_id}"
        
        # Build task text
        sample_id = run['user_info'].get('sample_id', '')
        protocol_group = run['user_info'].get('protocol_group_id', '')
        
        if sample_id:
            task_text = f"{sample_id}"
        elif protocol_group:
            task_text = f"{protocol_group}"
        else:
            task_text = f"Nanopore Run {run_id[:8]}"
        
        # Get timestamps
        start_date = run['start_time']
        if not start_date:
            start_date = timezone.now()
        
        # Make start_date timezone-aware if it isn't
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)
        
        end_date = run['end_time']
        if end_date:
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
        else:
            # Estimate end date for running protocols (default 48 hours)
            end_date = start_date + timedelta(hours=48)
        
        # Calculate duration in hours
        duration = (end_date - start_date).total_seconds() / 3600
        
        # Calculate progress
        if run['end_time']:
            progress = 1.0  # Completed
        else:
            # For running protocols, estimate progress based on elapsed time
            elapsed = (timezone.now() - start_date).total_seconds()
            estimated_total = duration * 3600  # Convert back to seconds
            progress = min(elapsed / estimated_total, 0.99) if estimated_total > 0 else 0.0
        
        # Lighten the color for child tasks
        child_color = self.lighten_color(color, 0.3)
        
        return {
            'text': task_text,
            'start_date': start_date,
            'end_date': end_date,
            'duration': duration,
            'progress': progress,
            'parent': parent_id,
            'color': child_color,
            'readonly': True,
            'source': 'nanopore',
            'external_id': external_id,
            'sort_order': 1001  # Place after parent
        }

    def lighten_color(self, hex_color: str, factor: float) -> str:
        """Lighten a hex color by a factor (0-1)"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"

