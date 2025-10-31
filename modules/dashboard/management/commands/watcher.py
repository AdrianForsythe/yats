from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from dashboard.models import Runfolder
from yats.models import tickets
import os
import time
import tempfile
import subprocess
import socket
from datetime import datetime
from typing import Dict, Any, Optional
from dashboard.utils import get_hades_connection

class Command(BaseCommand):
    help = 'Monitor sequencing runfolders and update their status in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--watch-dirs',
            nargs='+',
            default=['/data/runs'],
            help='Directories to monitor for runfolders'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once instead of continuously'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds (default: 60)'
        )

    def handle(self, *args, **options):
        watch_dirs = options['watch_dirs']
        once = options['once']
        interval = options['interval']

        # Read remote configuration from environment variables
        remote_config = self._get_remote_config()

        # Get current hostname to determine local vs remote watching
        current_hostname = socket.gethostname()

        # Determine watching mode based on hostname comparison
        if remote_config and remote_config['host'] == current_hostname:
            # We're running on the target host - watch locally using the remote path
            self.stdout.write(
                self.style.SUCCESS(f'Running on target host ({current_hostname}) - watching locally: {remote_config["path"]}')
            )
            actual_watch_dirs = [remote_config['path']]
            actual_remote_config = None
            monitoring_targets = [f"local:{remote_config['path']}"]
        elif remote_config:
            # We're running on a different host - watch remotely via SSH
            self.stdout.write(
                self.style.SUCCESS(f'Running on {current_hostname}, watching remote host {remote_config["host"]}:{remote_config["path"]}')
            )
            actual_watch_dirs = []  # Don't watch any local directories
            actual_remote_config = remote_config
            monitoring_targets = [f"remote:{remote_config['host']}:{remote_config['path']}"]
        else:
            # No remote config - watch local directories as before
            self.stdout.write(
                self.style.SUCCESS(f'No remote configuration - watching local directories: {", ".join(watch_dirs)}')
            )
            actual_watch_dirs = watch_dirs
            actual_remote_config = None
            monitoring_targets = [f"local:{d}" for d in watch_dirs]

        self.stdout.write(
            self.style.SUCCESS(f'Starting runfolder watcher monitoring: {", ".join(monitoring_targets)}')
        )

        while True:
            try:
                self.scan_runfolders(actual_watch_dirs, actual_remote_config)
                self.update_ticket_statuses()

                if once:
                    break

                self.stdout.write(f'Sleeping for {interval} seconds...')
                time.sleep(interval)

            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Watcher interrupted by user'))
                break
            except Exception as e:
                self.stderr.write(f'Error during scan: {e}')
                if once:
                    raise CommandError(f'Watcher failed: {e}')
                time.sleep(interval)

        self.stdout.write(self.style.SUCCESS('Watcher finished'))

    def _get_remote_config(self) -> Optional[Dict[str, str]]:
        """Read remote configuration from environment variables."""
        # Try different environment variable formats for flexibility

        # Option 1: Single combined variable (RUNFOLDER_WATCHER_REMOTE_CONFIG=user@host:/path)
        remote_config = os.environ.get('RUNFOLDER_WATCHER_REMOTE_CONFIG')
        if remote_config:
            try:
                if ':' not in remote_config:
                    self.stderr.write('Invalid RUNFOLDER_WATCHER_REMOTE_CONFIG format: expected user@host:path')
                    return None

                host_part, path = remote_config.split(':', 1)
                if '@' in host_part:
                    user, host = host_part.split('@', 1)
                else:
                    user = None
                    host = host_part

                return {
                    'host': host,
                    'user': user,
                    'path': path,
                    'password': os.environ.get('RUNFOLDER_WATCHER_REMOTE_PASSWORD')
                }
            except ValueError:
                self.stderr.write('Invalid RUNFOLDER_WATCHER_REMOTE_CONFIG format')
                return None

        # Option 2: Separate variables
        host = os.environ.get('RUNFOLDER_WATCHER_REMOTE_HOST')
        user = os.environ.get('RUNFOLDER_WATCHER_REMOTE_USER')
        path = os.environ.get('RUNFOLDER_WATCHER_REMOTE_PATH')
        password = os.environ.get('RUNFOLDER_WATCHER_REMOTE_PASSWORD')

        if host and path:
            return {
                'host': host,
                'user': user,  # Can be None
                'path': path,
                'password': password
            }

        # No remote configuration found
        return None

    def _check_sshpass_available(self) -> bool:
        """Check if sshpass is available on the system."""
        try:
            result = subprocess.run(
                ['which', 'sshpass'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def scan_runfolders(self, watch_dirs, remote_config=None):
        """Scan directories for runfolders and update database"""

        self.stdout.write('Scanning runfolders...')

        scanned_count = 0
        updated_count = 0

        # Scan local directories
        for watch_dir in watch_dirs:
            if not os.path.exists(watch_dir):
                self.stdout.write(
                    self.style.WARNING(f'Local watch directory does not exist: {watch_dir}')
                )
                continue

            for root, dirs, files in os.walk(watch_dir):
                for dirname in dirs:
                    if dirname.startswith('.'):
                        continue

                    runfolder_path = os.path.join(root, dirname)
                    scanned_count += 1

                    if self.process_runfolder(runfolder_path):
                        updated_count += 1

        # Scan remote directory if configured
        if remote_config:
            try:
                remote_runfolders = self.scan_remote_runfolders(remote_config)
                for runfolder_info in remote_runfolders:
                    scanned_count += 1
                    if self.process_remote_runfolder(runfolder_info, remote_config):
                        updated_count += 1
            except Exception as e:
                self.stderr.write(f'Error scanning remote host {remote_config["host"]}: {e}')

        self.stdout.write(
            f'Scanned {scanned_count} directories, updated {updated_count} runfolders'
        )

    def scan_remote_runfolders(self, remote_config):
        """Scan runfolders on a remote host for directories associated with open tickets"""
        try:
            ssh_user = remote_config.get('user')
            remote_host = remote_config['host']
            password = remote_config.get('password')

            runfolders = []

            # Build SSH command prefix based on authentication method
            if password:
                # Check if sshpass is available for password authentication
                if not self._check_sshpass_available():
                    self.stderr.write(f'sshpass not found. Install sshpass for password authentication, or use SSH keys instead.')
                    return []

                # Use sshpass for password authentication
                if ssh_user:
                    ssh_prefix = f"sshpass -p '{password}' ssh {ssh_user}@{remote_host}"
                    scp_prefix = f"sshpass -p '{password}' scp {ssh_user}@{remote_host}:"
                else:
                    ssh_prefix = f"sshpass -p '{password}' ssh {remote_host}"
                    scp_prefix = f"sshpass -p '{password}' scp {remote_host}:"
                self.stdout.write(f'Using password authentication for {remote_host} (SSH keys recommended for security)')
            else:
                # Use SSH key authentication (default)
                if ssh_user:
                    ssh_prefix = f"ssh {ssh_user}@{remote_host}"
                    scp_prefix = f"scp {ssh_user}@{remote_host}:"
                else:
                    ssh_prefix = f"ssh {remote_host}"
                    scp_prefix = f"scp {remote_host}:"

            # Query database for run directories associated with open tickets
            conn = get_hades_connection()
            if not conn:
                self.stderr.write('Failed to connect to HADES database')
                return []

            try:
                cursor = conn.cursor()

                # Query for RunDirectory from tblD00FlowCells for open tickets
                # Join with tblD00Requests to get only active/open requests
                query = """
                SELECT DISTINCT
                    fc.RunDirectory
                FROM [HADES2017].[dbo].[tblD00FlowCells] fc
                INNER JOIN [HADES2017].[dbo].[tblD00Requests] req
                    ON fc.FlowCellID = req.FlowCellID
                WHERE req.StatusID IN (2,3,4,7,10)  -- Active statuses
                AND fc.RunDirectory IS NOT NULL
                AND fc.RunDirectory != ''
                """

                cursor.execute(query)
                run_directories = [row[0] for row in cursor.fetchall() if row[0]]

                self.stdout.write(f'Found {len(run_directories)} run directories associated with open tickets')

                # Process each run directory
                for runfolder_path in run_directories:
                    if not runfolder_path:
                        continue

                    runfolder_name = os.path.basename(runfolder_path)
                    runfolder_info = self._get_remote_runfolder_info_ssh(
                        remote_host, runfolder_path, runfolder_name, ssh_prefix, scp_prefix
                    )
                    if runfolder_info:
                        runfolders.append(runfolder_info)

                conn.close()

            except Exception as e:
                self.stderr.write(f'Error querying HADES database: {e}')
                conn.close()
                return []

            self.stdout.write(f'Found {len(runfolders)} runfolders to monitor on {remote_host}')

            return runfolders

        except subprocess.TimeoutExpired:
            self.stderr.write(f'SSH command timed out monitoring {remote_config["host"]}')
            return []
        except Exception as e:
            self.stderr.write(f'Error scanning remote runfolders on {remote_config["host"]}: {e}')
            return []

    def process_remote_runfolder(self, runfolder_info, remote_config):
        """Process a remote runfolder info dictionary"""
        try:
            runfolder_name = runfolder_info['name']
            remote_host = remote_config['host']

            # Get or create runfolder record
            # Use a unique identifier that includes the remote host
            unique_path = f"ssh://{remote_host}{runfolder_info['path']}"

            runfolder, created = Runfolder.objects.get_or_create(
                runfolder_path=unique_path,
                defaults={'runfolder_name': f"{remote_host}:{runfolder_name}"}
            )

            if created:
                self.stdout.write(f'Found new remote runfolder: {remote_host}:{runfolder_name}')

            # Update status based on remote file presence
            old_status = runfolder.status
            runfolder.status = runfolder_info.get('status', 'initializing')

            # Update metadata from parsed XML
            if 'instrument' in runfolder_info:
                runfolder.instrument_id = runfolder_info['instrument']
            if 'flowcell' in runfolder_info:
                runfolder.flowcell_id = runfolder_info['flowcell']
            if 'date' in runfolder_info and runfolder_info['date']:
                try:
                    # Handle various date formats
                    date_str = runfolder_info['date']
                    if len(date_str) == 8:  # YYYYMMDD format
                        runfolder.run_date = datetime.strptime(date_str, '%Y%m%d').date()
                except ValueError:
                    pass

            # Update timestamps
            if runfolder_info.get('run_start_time'):
                try:
                    runfolder.run_start_time = datetime.fromisoformat(runfolder_info['run_start_time'].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        runfolder.run_start_time = datetime.strptime(runfolder_info['run_start_time'], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            if runfolder_info.get('run_end_time'):
                try:
                    runfolder.run_end_time = datetime.fromisoformat(runfolder_info['run_end_time'].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        runfolder.run_end_time = datetime.strptime(runfolder_info['run_end_time'], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            # Update completion status
            if runfolder_info.get('completion_status'):
                runfolder.completion_status = runfolder_info['completion_status']
            if runfolder_info.get('completion_time'):
                try:
                    runfolder.completion_time = datetime.fromisoformat(runfolder_info['completion_time'].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        runfolder.completion_time = datetime.strptime(runfolder_info['completion_time'], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            # Link to ticket if possible
            self.link_to_ticket(runfolder)

            # Save if changed
            if runfolder.status != old_status or created:
                runfolder.save()
                if runfolder.status != old_status:
                    self.stdout.write(
                        f'Updated remote runfolder {remote_host}:{runfolder_name}: {old_status} -> {runfolder.status}'
                    )
                return True

            return False

        except Exception as e:
            self.stderr.write(f'Error processing remote runfolder {runfolder_info.get("name", "unknown")}: {e}')
            return False

    def _get_remote_runfolder_info_ssh(self, remote_host: str, runfolder_path: str, runfolder_name: str,
                                      ssh_prefix: str, scp_prefix: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a remote runfolder using SSH commands."""
        try:
            info = {
                'name': runfolder_name,
                'path': runfolder_path,
                'host': remote_host,
                'files_present': {},
                'status': 'initializing'
            }

            # Check for key files using SSH
            key_files = [
                'RunInfo.xml',
                'RunParameters.xml',
                'RunCompletionStatus.xml',
                'CopyComplete.txt',
                'RTAComplete.txt',
                'SequenceComplete.txt'
            ]

            for filename in key_files:
                exists = self._check_remote_file_exists_ssh(ssh_prefix, runfolder_path, filename)
                info['files_present'][filename] = exists

            # Determine status based on file presence
            if (info['files_present'].get('RunParameters.xml') and
                info['files_present'].get('CopyComplete.txt') and
                info['files_present'].get('RTAComplete.txt') and
                (info['files_present'].get('RunCompletionStatus.xml') or
                 info['files_present'].get('SequenceComplete.txt'))):
                info['status'] = 'finished'
            elif (info['files_present'].get('RunParameters.xml') and
                  info['files_present'].get('CopyComplete.txt') and
                  info['files_present'].get('RTAComplete.txt')):
                info['status'] = 'sequencing'
            elif info['files_present'].get('RunParameters.xml'):
                info['status'] = 'copying'

            # Parse XML files remotely if they exist
            if info['files_present'].get('RunInfo.xml'):
                xml_info = self._parse_remote_xml_ssh(ssh_prefix, runfolder_path, 'RunInfo.xml')
                info.update(xml_info)

            if info['files_present'].get('RunParameters.xml'):
                run_params = self._parse_remote_xml_ssh(ssh_prefix, runfolder_path, 'RunParameters.xml')
                if run_params:
                    info['run_start_time'] = run_params.get('run_start_time')
                    info['run_end_time'] = run_params.get('run_end_time')

            # Get completion time from RunCompletionStatus.xml if available
            if info['files_present'].get('RunCompletionStatus.xml'):
                completion_data = self._parse_remote_xml_ssh(ssh_prefix, runfolder_path, 'RunCompletionStatus.xml')
                if completion_data:
                    info['completion_status'] = completion_data.get('completion_status')
                    info['completion_time'] = completion_data.get('completion_time')
            # Otherwise, use SequenceComplete.txt modification time if available
            elif info['files_present'].get('SequenceComplete.txt'):
                completion_time = self._get_remote_file_mtime_ssh(ssh_prefix, runfolder_path, 'SequenceComplete.txt')
                if completion_time:
                    info['completion_status'] = 'Completed'
                    info['completion_time'] = completion_time.isoformat()

            return info

        except Exception as e:
            self.stderr.write(f'Error getting runfolder info for {runfolder_name} on {remote_host}: {e}')
            return None

    def _check_remote_file_exists_ssh(self, ssh_prefix: str, runfolder_path: str, filename: str) -> bool:
        """Check if a file exists on the remote server using SSH."""
        try:
            cmd = f'{ssh_prefix} "test -f \'{runfolder_path}/{filename}\' && echo EXISTS || echo NOT_EXISTS"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0 and 'EXISTS' in result.stdout
        except Exception as e:
            self.stderr.write(f'Error checking remote file {filename}: {e}')
            return False

    def _get_remote_file_mtime_ssh(self, ssh_prefix: str, runfolder_path: str, filename: str) -> Optional[datetime]:
        """Get the modification time of a remote file using SSH."""
        try:
            cmd = f'{ssh_prefix} "stat -c %Y \'{runfolder_path}/{filename}\'"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                # stat -c %Y returns seconds since epoch
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp)
            return None
        except Exception as e:
            self.stderr.write(f'Error getting mtime for remote file {filename}: {e}')
            return None

    def _filter_ssh_login_banner(self, stderr: str) -> str:
        """Filter out common SSH login banners that aren't actual errors."""
        # Common login banner patterns that should be ignored
        banner_patterns = [
            'Authorized uses only',
            'All activity may be monitored and reported',
            'Last login:',
            'Welcome to',
            'Unauthorized access is prohibited',
        ]

        lines = stderr.split('\n')
        filtered_lines = []

        for line in lines:
            line = line.strip()
            if line and not any(pattern.lower() in line.lower() for pattern in banner_patterns):
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _parse_remote_xml_ssh(self, ssh_prefix: str, runfolder_path: str, filename: str) -> Dict[str, Any]:
        """Parse XML file from remote server using SSH cat command."""
        try:
            # First check if the file exists remotely
            check_cmd = f"{ssh_prefix} \"test -f '{runfolder_path}/{filename}' && echo EXISTS || echo NOT_EXISTS\""
            check_result = subprocess.run(
                check_cmd, shell=True, capture_output=True, text=True, timeout=30
            )

            if check_result.returncode != 0:
                # SSH connection failed
                stderr_clean = self._filter_ssh_login_banner(check_result.stderr.strip())
                self.stderr.write(f'SSH connection failed for {filename}: {stderr_clean}')
                if check_result.stdout.strip():
                    self.stdout.write(f'SSH check stdout: {check_result.stdout.strip()}')
                return {}

            if 'NOT_EXISTS' in check_result.stdout:
                # File doesn't exist
                self.stdout.write(f'Remote XML file {filename} does not exist at {runfolder_path}')
                return {}

            if 'EXISTS' not in check_result.stdout:
                # Unexpected response
                self.stderr.write(f'Unexpected SSH check response for {filename}: stdout="{check_result.stdout.strip()}", stderr="{check_result.stderr.strip()}"')
                return {}

            # File exists, now try to read it
            ssh_cmd = f"{ssh_prefix} \"cat '{runfolder_path}/{filename}'\""
            result = subprocess.run(
                ssh_cmd, shell=True, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                # Filter out common login banners that aren't actual errors
                stderr_clean = self._filter_ssh_login_banner(result.stderr.strip())
                if stderr_clean:
                    self.stderr.write(f'Failed to read remote XML file {filename}: {stderr_clean}')
                else:
                    self.stderr.write(f'Failed to read remote XML file {filename} (SSH command failed)')
                return {}

            xml_content = result.stdout.strip()
            if not xml_content:
                self.stderr.write(f'Remote XML file {filename} is empty')
                return {}

            # Parse the XML content directly from string
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)

                # Parse based on filename
                if filename == 'RunInfo.xml':
                    run = root.find("Run")
                    if run is not None:
                        return {
                            "run_id": run.get("Id"),
                            "run_number": run.get("Number"),
                            "flowcell": run.find("Flowcell").text if run.find("Flowcell") is not None else None,
                            "instrument": run.find("Instrument").text if run.find("Instrument") is not None else None,
                            "date": run.find("Date").text if run.find("Date") is not None else None
                        }
                elif filename == 'RunParameters.xml':
                    return {
                        "run_start_time": root.find("RunStartTime").text if root.find("RunStartTime") is not None else None,
                        "run_end_time": root.find("RunEndTime").text if root.find("RunEndTime") is not None else None
                    }
                elif filename == 'RunCompletionStatus.xml':
                    completion_status = root.find("CompletionStatus")
                    completion_time = root.find("CompletionTime")
                    return {
                        "completion_status": completion_status.text if completion_status is not None else None,
                        "completion_time": completion_time.text if completion_time is not None else None
                    }

            except ET.ParseError as e:
                self.stderr.write(f'XML parsing error for {filename}: {e}')
            except Exception as e:
                self.stderr.write(f'Error parsing XML {filename}: {e}')

            return {}

        except subprocess.TimeoutExpired:
            self.stderr.write(f'Timeout reading remote XML file {filename}')
            return {}
        except Exception as e:
            self.stderr.write(f'Error reading remote XML {filename}: {e}')
            return {}

    def process_runfolder(self, runfolder_path):
        """Process a single runfolder"""
        runfolder_name = os.path.basename(runfolder_path)

        # Get or create runfolder record
        runfolder, created = Runfolder.objects.get_or_create(
            runfolder_path=runfolder_path,
            defaults={'runfolder_name': runfolder_name}
        )

        if created:
            self.stdout.write(f'Found new runfolder: {runfolder_name}')

        # Update status based on files
        old_status = runfolder.status
        runfolder.update_status_from_files()

        # Parse XML files if they exist
        self.parse_runfolder_data(runfolder)

        # Link to ticket if possible
        self.link_to_ticket(runfolder)

        # Save if changed
        if runfolder.status != old_status or created:
            runfolder.save()
            if runfolder.status != old_status:
                self.stdout.write(
                    f'Updated {runfolder_name}: {old_status} -> {runfolder.status}'
                )
            return True

        return False

    def parse_runfolder_data(self, runfolder):
        """Parse XML files and update runfolder data"""
        # Parse RunInfo.xml
        run_info = runfolder.parse_run_info()
        if run_info:
            runfolder.instrument_id = run_info.get("instrument")
            runfolder.flowcell_id = run_info.get("flowcell")

            # Parse run date
            if run_info.get("date"):
                try:
                    # Handle various date formats
                    date_str = run_info["date"]
                    if len(date_str) == 8:  # YYYYMMDD format
                        runfolder.run_date = datetime.strptime(date_str, '%Y%m%d').date()
                    else:
                        # Try other formats or set to None
                        pass
                except ValueError:
                    pass

        # Parse RunParameters.xml
        run_params = runfolder.parse_run_parameters()
        if run_params:
            # Parse timestamps - handle various formats
            if run_params.get("run_start_time"):
                try:
                    # Try parsing as ISO format first
                    runfolder.run_start_time = datetime.fromisoformat(run_params["run_start_time"].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Try other common formats
                        runfolder.run_start_time = datetime.strptime(run_params["run_start_time"], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            if run_params.get("run_end_time"):
                try:
                    runfolder.run_end_time = datetime.fromisoformat(run_params["run_end_time"].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        runfolder.run_end_time = datetime.strptime(run_params["run_end_time"], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

        # Parse RunCompletionStatus.xml
        completion_data = runfolder.parse_completion_status()
        if completion_data:
            runfolder.completion_status = completion_data.get("completion_status")

            if completion_data.get("completion_time"):
                try:
                    runfolder.completion_time = datetime.fromisoformat(completion_data["completion_time"].replace('Z', '+00:00'))
                except ValueError:
                    try:
                        runfolder.completion_time = datetime.strptime(completion_data["completion_time"], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

    def link_to_ticket(self, runfolder):
        """Try to link runfolder to a sequencing ticket"""
        if runfolder.ticket:
            return  # Already linked

        # Look for tickets that might be related to this runfolder
        # This is a simple implementation - you might want to make this more sophisticated
        # based on how runfolders are named vs ticket UUIDs

        # For now, try to match based on flowcell ID or runfolder name in ticket description
        if runfolder.flowcell_id:
            # Look for tickets with this flowcell ID in the description or UUID
            related_tickets = tickets.objects.filter(
                active_record=True,
                description__icontains=runfolder.flowcell_id
            ) | tickets.objects.filter(
                active_record=True,
                uuid__icontains=runfolder.flowcell_id
            )

            if related_tickets.exists():
                runfolder.ticket = related_tickets.first()
                self.stdout.write(
                    f'Linked runfolder {runfolder.runfolder_name} to ticket #{runfolder.ticket.id}'
                )

    def update_ticket_statuses(self):
        """Update ticket statuses based on runfolder progress"""
        self.stdout.write('Updating ticket statuses...')

        updated_count = 0

        # Get all runfolders with associated tickets
        runfolders_with_tickets = Runfolder.objects.filter(ticket__isnull=False)

        for runfolder in runfolders_with_tickets:
            ticket = runfolder.ticket

            # Define status mappings from runfolder status to ticket workflow
            # This depends on your ticket workflow - adjust as needed
            status_mapping = {
                'finished': 'completed',  # Map runfolder finished to ticket completed
                'sequencing': 'in_progress',  # Map sequencing to in progress
                'copying': 'processing',  # Map copying to processing
                'initializing': 'pending',  # Map initializing to pending
                'completed': 'completed'  # Map completed to completed
            }

            new_status_name = status_mapping.get(runfolder.status)
            if not new_status_name:
                continue

            # Find the corresponding ticket flow state
            try:
                from yats.models import ticket_flow
                new_state = ticket_flow.objects.get(
                    name__icontains=new_status_name,
                    active_record=True
                )

                # Update ticket state if different
                if ticket.state != new_state:
                    ticket.state = new_state
                    ticket.save()
                    updated_count += 1
                    self.stdout.write(
                        f'Updated ticket #{ticket.id} status to "{new_state.name}" based on runfolder {runfolder.runfolder_name}'
                    )

            except ticket_flow.DoesNotExist:
                # State doesn't exist in workflow, skip
                continue

        if updated_count > 0:
            self.stdout.write(f'Updated {updated_count} ticket statuses')