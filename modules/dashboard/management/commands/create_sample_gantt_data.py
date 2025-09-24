# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from dashboard.models import Task, Link

# load machine_flowcell_default_runtime from tsv files
import pandas as pd

class Command(BaseCommand):
    help = 'Create sample Gantt chart data for testing'

    def handle(self, *args, **options):
        # Clear existing data
        Task.objects.all().delete()
        Link.objects.all().delete()

        self.create_sequencing_project()
        self.create_machine_projects()

    def create_sequencing_project(self):
        start_date = timezone.now()
        # Define all subtasks first to calculate parent task span
        subtasks_data = [
            {"text": "Samples received", "duration": 1, "progress": 1.0, "offset": 0},
            {"text": "Quality Control", "duration": 1, "progress": 0.8, "offset": 1},
            {"text": "Library Preparation", "duration": 2, "progress": 0.3, "offset": 2},
            {"text": "Quality Control", "duration": 2, "progress": 0.0, "offset": 4},
            {"text": "Sequencing", "duration": 1, "progress": 0.0, "offset": 6},
            {"text": "Quality Control", "duration": 1, "progress": 0.0, "offset": 7},
            {"text": "Transfer Data", "duration": 1, "progress": 0.0, "offset": 8},
        ]
        
        # Calculate parent task span (from start of first task to end of last task)
        first_task_start = start_date
        last_task_end = start_date + timedelta(days=9)  # 8 + 1 day duration
        total_duration = 9  # Total project duration
        
        # Create parent task that spans the entire project
        project_task = Task.objects.create(
            text="Sample Sequencing Project",
            start_date=first_task_start,
            end_date=last_task_end,
            duration=total_duration,
            progress=0.1,
            parent="0",
            sort_order=1
        )
        
        # Create subtasks sequentially (no overlaps)
        tasks = []
        for i, task_data in enumerate(subtasks_data):
            task_start = start_date + timedelta(days=task_data["offset"])
            task_end = task_start + timedelta(days=task_data["duration"])
            
            task = Task.objects.create(
                text=task_data["text"],
                start_date=task_start,
                end_date=task_end,
                duration=task_data["duration"],
                progress=task_data["progress"],
                parent=str(project_task.id),
                sort_order=i + 1
            )
            tasks.append(task)
        
        # Create sequential links between tasks (end-to-start, no overlaps)
        for i in range(len(tasks) - 1):
            Link.objects.create(
                source=str(tasks[i].id),
                target=str(tasks[i + 1].id),
                type="0"  # finish-to-start
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample Gantt chart data for sequencing project')
        )

    def create_machine_projects(self):
        """Create sample timeline of machine projects
        - Create parent tasks for each machine
        - Create subtasks for each flowcell+type combination
        - Skip rows with missing runtime values
        - Parent tasks span the entire duration of their subtasks
        """
        start_date = timezone.now()
        machine_flowcell_default_runtime = pd.read_csv('modules/dashboard/machine_default_run_times.tsv', sep='\t')
        
        # Group by machine to create parent tasks
        machines = machine_flowcell_default_runtime['machine'].unique()
        machine_tasks = {}
        
        # First pass: collect all subtasks for each machine to calculate parent span
        machine_subtasks = {}
        for index, row in machine_flowcell_default_runtime.iterrows():
            machine = row['machine']
            runtime = row['runtime']
            
            # Skip rows with missing runtime values
            if pd.isna(runtime) or runtime == '' or runtime is None:
                continue
                
            if machine not in machine_subtasks:
                machine_subtasks[machine] = []
            
            machine_subtasks[machine].append({
                'flowcell': row['flowcell'],
                'type': row['type'],
                'runtime': runtime,
                'index': index
            })
        
        # Create parent tasks and subtasks
        for machine, subtasks in machine_subtasks.items():
            if not subtasks:
                continue
                
            # Calculate parent task span (from start of first task to end of last task)
            # For simplicity, we'll use the longest runtime as the parent duration
            max_runtime = max(subtask['runtime'] for subtask in subtasks)
            parent_duration = max_runtime / 24  # Convert hours to days
            
            # Create parent task that spans the entire machine project
            machine_task = Task.objects.create(
                text=f"{machine}",
                start_date=start_date,
                end_date=start_date + timedelta(hours=max_runtime),
                duration=parent_duration,
                progress=0.0,
                parent="0",
                sort_order=len(machine_tasks) + 1
            )
            machine_tasks[machine] = machine_task
            
            # Create subtasks for this machine
            for subtask in subtasks:
                flowcell = subtask['flowcell']
                type_val = subtask['type']
                runtime = subtask['runtime']
                
                # Handle empty type values
                if pd.isna(type_val) or type_val == '' or type_val == 'nan':
                    type_str = ""
                else:
                    type_str = f" {type_val}"
                
                # Create subtask
                task = Task.objects.create(
                    text=f"{flowcell}{type_str}",
                    start_date=start_date,
                    end_date=start_date + timedelta(hours=runtime),
                    duration=runtime,
                    progress=0.0,
                    parent=str(machine_task.id),
                    sort_order=subtask['index']
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample Gantt chart data for machine projects')
        )