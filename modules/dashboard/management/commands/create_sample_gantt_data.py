# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from dashboard.models import Task, Link


class Command(BaseCommand):
    help = 'Create sample Gantt chart data for testing'

    def handle(self, *args, **options):
        # Clear existing data
        Task.objects.all().delete()
        Link.objects.all().delete()
        
        # Create sample tasks
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
            self.style.SUCCESS('Successfully created sample Gantt chart data')
        )
