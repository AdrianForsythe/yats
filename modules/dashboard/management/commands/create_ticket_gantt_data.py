# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from dashboard.models import Task, Link
from yats.shortcuts import get_ticket_model
from yats.models import ticket_flow

class Command(BaseCommand):
    help = 'Create Gantt chart data from real ticket data'
    
    # Note: This implementation creates subtasks for current ticket metadata only.
    # The HADES database doesn't appear to have status history tables, so we can't
    # create subtasks for status changes over time. Future enhancement could:
    # 1. Query HADES for status history tables if they exist
    # 2. Use YATS tickets_history table to track status changes
    # 3. Create a hybrid approach combining both data sources

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing Gantt data before creating new data')
        parser.add_argument('--include-closed', action='store_true', help='Include closed tickets in the Gantt chart')

    def handle(self, *args, **options):
        clear_data = options.get('clear', False)
        include_closed = options.get('include_closed', False)
        
        if clear_data:
            # Clear existing data
            Task.objects.all().delete()
            Link.objects.all().delete()
            self.stdout.write('Cleared existing Gantt chart data')

        self.create_ticket_tasks(include_closed)

    def create_ticket_tasks(self, include_closed=False):
        """Create Gantt chart tasks from ticket data"""
        Ticket = get_ticket_model()
        
        # Get closed state names to filter out
        closed_states = ['Finished', 'Canceled', 'Deleted']
        
        # Get all tickets
        tickets = Ticket.objects.filter(active_record=True)
        
        if not include_closed:
            # Filter out tickets with closed states
            tickets = tickets.exclude(
                state__name__in=closed_states
            ).exclude(closed=True)
        
        self.stdout.write(f'Processing {tickets.count()} tickets...')
        
        # Define colors for different ticket types/priorities
        type_colors = {
            'Bug': '#F44336',      # Red
            'Feature': '#4CAF50',  # Green
            'Task': '#2196F3',     # Blue
            'Enhancement': '#FF9800',  # Orange
            'Sequencing': '#9C27B0',   # Purple
        }
        
        priority_colors = {
            'High': '#F44336',     # Red
            'Medium': '#FF9800',   # Orange
            'Low': '#4CAF50',      # Green
            'Critical': '#D32F2F', # Dark Red
        }
        
        created_tasks = 0
        
        for ticket in tickets:
            # Determine task color based on type or priority
            color = '#757575'  # Default grey
            
            if ticket.type and ticket.type.name in type_colors:
                color = type_colors[ticket.type.name]
            elif ticket.priority and ticket.priority.name in priority_colors:
                color = priority_colors[ticket.priority.name]
            
            # Calculate task dates
            start_date = ticket.c_date
            if ticket.show_start:
                start_date = ticket.show_start
            
            # For closed tickets, use close_date as end_date
            # For open tickets, use current time as end_date
            if ticket.closed and ticket.close_date:
                end_date = ticket.close_date
            else:
                end_date = timezone.now()
            
            # Calculate duration in days
            duration = (end_date - start_date).days + 1  # +1 to include both start and end days
            
            # Calculate progress based on ticket state
            progress = 0.0
            if ticket.closed:
                progress = 1.0
            elif ticket.state:
                # Simple progress calculation based on state
                # This could be enhanced with more sophisticated logic
                progress = 0.3  # Default progress for open tickets
            
            # Create main task
            task = Task.objects.create(
                text=f"#{ticket.id}: {ticket.caption}",
                start_date=start_date,
                end_date=end_date,
                duration=duration,
                progress=progress,
                parent="0",
                sort_order=ticket.id,
                color=color,
                external_id=f"ticket_{ticket.id}",
                readonly=False,
                source="ticket"
            )
            created_tasks += 1
            
            # Create subtasks if additional information is present
            subtasks_created = self.create_subtasks_for_ticket(ticket, task)
            
            if subtasks_created:
                self.stdout.write(f'Created task {task.id} with {subtasks_created} subtasks for ticket #{ticket.id}')
            else:
                self.stdout.write(f'Created task {task.id} for ticket #{ticket.id}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_tasks} tasks from ticket data')
        )

    def create_subtasks_for_ticket(self, ticket, parent_task):
        """Create subtasks for a ticket if additional information is present.
        Since HADES database doesn't have status history, we create subtasks for current status only.
        """
        subtasks_created = 0
        
        # Only create subtasks if there's meaningful information to show
        # Skip creating subtasks if the ticket has minimal information
        
        # Create subtask for current state if present and meaningful
        if ticket.state and ticket.state.name not in ['', 'New', 'Open']:
            state_task = Task.objects.create(
                text=f"Status: {ticket.state.name}",
                start_date=parent_task.start_date,
                end_date=parent_task.end_date,
                duration=parent_task.duration,
                progress=parent_task.progress,
                parent=str(parent_task.id),
                sort_order=1,
                color=self.lighten_color(parent_task.color, 0.3),
                external_id=f"ticket_{ticket.id}_state",
                readonly=True,
                source="ticket"
            )
            subtasks_created += 1
        
        # Create subtask for assigned user if present
        if ticket.assigned:
            assigned_task = Task.objects.create(
                text=f"Assigned: {ticket.assigned.get_full_name() or ticket.assigned.username}",
                start_date=parent_task.start_date,
                end_date=parent_task.end_date,
                duration=parent_task.duration,
                progress=parent_task.progress,
                parent=str(parent_task.id),
                sort_order=2,
                color=self.lighten_color(parent_task.color, 0.3),
                external_id=f"ticket_{ticket.id}_assigned",
                readonly=True,
                source="ticket"
            )
            subtasks_created += 1
        
        # Create subtask for priority if present and meaningful
        if ticket.priority and ticket.priority.name not in ['', 'Normal', 'Medium']:
            priority_task = Task.objects.create(
                text=f"Priority: {ticket.priority.name}",
                start_date=parent_task.start_date,
                end_date=parent_task.end_date,
                duration=parent_task.duration,
                progress=parent_task.progress,
                parent=str(parent_task.id),
                sort_order=3,
                color=self.lighten_color(parent_task.color, 0.3),
                external_id=f"ticket_{ticket.id}_priority",
                readonly=True,
                source="ticket"
            )
            subtasks_created += 1
        
        # Create subtask for customer/organization if present and meaningful
        if ticket.customer and ticket.customer.name not in ['', 'Unknown']:
            customer_task = Task.objects.create(
                text=f"Customer: {ticket.customer.name}",
                start_date=parent_task.start_date,
                end_date=parent_task.end_date,
                duration=parent_task.duration,
                progress=parent_task.progress,
                parent=str(parent_task.id),
                sort_order=4,
                color=self.lighten_color(parent_task.color, 0.3),
                external_id=f"ticket_{ticket.id}_customer",
                readonly=True,
                source="ticket"
            )
            subtasks_created += 1
        
        return subtasks_created

    def lighten_color(self, hex_color, factor):
        """Lighten a hex color by a factor (0-1)"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"
