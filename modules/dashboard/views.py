# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from yats.models import tickets, ticket_type, ticket_priority, organisation, ticket_flow
import json
import pyodbc
from django.conf import settings
from .sequencing_config import SEQUENCING_DB_CONFIG
from .models import Task, Link
from .serializers import TaskSerializer, LinkSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response


def get_sequencing_connection():
    """Get connection to HADES2017 sequencing database"""
    try:
        # Try FreeTDS first (works on Ubuntu 24.04)
        if SEQUENCING_DB_CONFIG['driver'] == 'FreeTDS':
            connection_string = (
                f"DRIVER={{{SEQUENCING_DB_CONFIG['driver']}}};"
                f"SERVER={SEQUENCING_DB_CONFIG['server']};"
                f"PORT={SEQUENCING_DB_CONFIG['port']};"
                f"DATABASE={SEQUENCING_DB_CONFIG['database']};"
                f"UID={SEQUENCING_DB_CONFIG['username']};"
                f"PWD={SEQUENCING_DB_CONFIG['password']};"
                f"TDS_Version=8.0;"
            )
        else:
            # Microsoft ODBC Driver
            connection_string = (
                f"DRIVER={{{SEQUENCING_DB_CONFIG['driver']}}};"
                f"SERVER={SEQUENCING_DB_CONFIG['server']};"
                f"DATABASE={SEQUENCING_DB_CONFIG['database']};"
                f"UID={SEQUENCING_DB_CONFIG['username']};"
                f"PWD={SEQUENCING_DB_CONFIG['password']};"
            )
        
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


@login_required
def dashboard_home(request):
    """Main dashboard view with analytics overview"""
    context = {
        'page_title': 'Dashboard',
        'breadcrumbs': [{'name': 'Dashboard', 'url': '/dashboard/'}]
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def gantt_view(request):
    """Gantt chart view for project timeline"""
    context = {
        'page_title': 'Gantt Chart',
        'breadcrumbs': [
            {'name': 'Dashboard', 'url': '/dashboard/'},
            {'name': 'Gantt Chart', 'url': '/dashboard/gantt/'}
        ]
    }
    return render(request, 'dashboard/gantt.html', context)


@login_required
def sequencing_analytics(request):
    """Sequencing analytics based on Monday List data"""
    conn = get_sequencing_connection()
    if not conn:
        # Provide demo data when database is not available
        context = {
            'error': 'Database connection not available. Showing demo data.',
            'status_counts': {
                'Received': 45,
                'Accepted': 32,
                'Library prepared': 28,
                'Solexa Assigned': 15,
                'Data Analysed': 67
            },
            'application_counts': {
                'RNA-seq': 45,
                'WGS': 32,
                'ChIP-seq': 28,
                'ATAC-seq': 15,
                'scRNA-seq': 67
            },
            'user_counts': {
                'John Doe': 45,
                'Jane Smith': 32,
                'Bob Johnson': 28,
                'Alice Brown': 15,
                'Charlie Wilson': 67
            },
            'total_samples': 187,
            'recent_samples': 23,
            'monday_list_data': [
                ('Received', 'RNA-seq', '150bp', 'PE', 'John Doe', 5, 8, '2025/09/20'),
                ('Accepted', 'WGS', '100bp', 'SE', 'Jane Smith', 3, 4, '2025/09/19'),
                ('Library prepared', 'ChIP-seq', '75bp', 'PE', 'Bob Johnson', 2, 3, '2025/09/18'),
            ],
            'page_title': 'Sequencing Analytics'
        }
        return render(request, 'dashboard/sequencing_analytics_simple.html', context)
    
    try:
        cursor = conn.cursor()
        
        # Get Monday List data (similar to the R query)
        monday_list_query = """
        SELECT
          StatusDescription as [Status],
          ApplicationName as [Application],
          RRLengthDisplay as [Machine_Read],
        CASE
            WHEN [HADES2017].[dbo].[tblD00Requests].PairedEndOption = 0 THEN 'SE'
            WHEN [HADES2017].[dbo].[tblD00Requests].PairedEndOption = 1 THEN 'PE'
            ELSE NULL
        END as [Paired_end],
        CustomerName as [User],
        COUNT(*) as [N_samples],
        PoolSize as [Pool_size],
        convert(varchar, ReceiveDate, 111) as [Date_accepted]
        FROM [HADES2017].[dbo].[tblD00Requests]
          LEFT JOIN [HADES2017].[dbo].[tblD00Status]
          ON [HADES2017].[dbo].[tblD00Requests].StatusID = [HADES2017].[dbo].[tblD00Status].StatusID
          LEFT JOIN [HADES2017].[dbo].[tblD00RReadLength]
          ON [HADES2017].[dbo].[tblD00Requests].RReadLengthID = [HADES2017].[dbo].[tblD00RReadLength].RReadLengthID
          LEFT JOIN [HADES2017].[dbo].[tbl_Customers]
          ON [HADES2017].[dbo].[tblD00Requests].CustomerID = [HADES2017].[dbo].[tbl_Customers].CustomerID
          LEFT JOIN [HADES2017].[dbo].[tbl_Groups]
          ON [HADES2017].[dbo].[tbl_Customers].GroupID = [HADES2017].[dbo].[tbl_Groups].GroupID
          LEFT JOIN [HADES2017].[dbo].[tblD00SampleTypes]
          ON [HADES2017].[dbo].[tblD00Requests].SampleTypeID =[HADES2017].[dbo].[tblD00SampleTypes].SampleTypeID
          LEFT JOIN [HADES2017].[dbo].[tblD00Applications]
          ON [HADES2017].[dbo].[tblD00Requests].ApplicationID =[HADES2017].[dbo].[tblD00Applications].ApplicationID
        WHERE [HADES2017].[dbo].[tblD00Requests].StatusID IN (2,3,4,7,10)
        GROUP BY ApplicationName,
            CustomerName,
            StatusDescription,
            RRLengthDisplay,
            PairedEndOption,
            PoolSize,
            convert(varchar,ReceiveDate, 111)
        ORDER BY CASE
            WHEN StatusDescription = 'Received' THEN '1'
            WHEN StatusDescription = 'Accepted' THEN '2'
            ELSE StatusDescription END ASC,
          convert(varchar,ReceiveDate, 111), 
          ApplicationName,
            RRLengthDisplay,
            CustomerName
        """
        
        cursor.execute(monday_list_query)
        monday_list_data = cursor.fetchall()
        
        # Process data for analytics
        status_counts = {}
        application_counts = {}
        user_counts = {}
        total_samples = 0
        
        for row in monday_list_data:
            status = row[0]
            application = row[1]
            user = row[4]
            n_samples = row[5]
            
            # Count by status
            status_counts[status] = status_counts.get(status, 0) + n_samples
            
            # Count by application
            application_counts[application] = application_counts.get(application, 0) + n_samples
            
            # Count by user
            user_counts[user] = user_counts.get(user, 0) + n_samples
            
            total_samples += n_samples
        
        # Get recent activity (last 30 days)
        recent_query = """
        SELECT COUNT(*) as recent_samples
        FROM [HADES2017].[dbo].[tblD00Requests]
        WHERE ReceiveDate >= DATEADD(day, -30, GETDATE())
        """
        cursor.execute(recent_query)
        recent_samples = cursor.fetchone()[0]
        
        conn.close()
        
        context = {
            'status_counts': status_counts,
            'application_counts': application_counts,
            'user_counts': dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'total_samples': total_samples,
            'recent_samples': recent_samples,
            'monday_list_data': monday_list_data,
            'page_title': 'Sequencing Analytics'
        }
        
        return render(request, 'dashboard/sequencing_analytics_simple.html', context)
        
    except Exception as e:
        conn.close()
        context = {
            'error': f'Database query error: {str(e)}',
            'page_title': 'Sequencing Analytics'
        }
        return render(request, 'dashboard/sequencing_analytics_simple.html', context)


@login_required
def analytics_overview(request):
    """Analytics overview with key metrics"""
    # Get date range (last 30 days by default)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Basic ticket statistics
    total_tickets = tickets.objects.filter(active_record=True).count()
    open_tickets = tickets.objects.filter(active_record=True, closed=False).count()
    closed_tickets = tickets.objects.filter(active_record=True, closed=True).count()
    
    # Recent activity
    recent_tickets = tickets.objects.filter(
        active_record=True,
        c_date__gte=start_date
    ).count()
    
    recent_closed = tickets.objects.filter(
        active_record=True,
        closed=True,
        close_date__gte=start_date
    ).count()
    
    # Tickets by type
    tickets_by_type = tickets.objects.filter(active_record=True).values(
        'type__name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Tickets by priority
    tickets_by_priority = tickets.objects.filter(active_record=True).values(
        'priority__name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Tickets by organisation
    tickets_by_org = tickets.objects.filter(active_record=True).values(
        'customer__name'
    ).annotate(count=Count('id')).order_by('-count')[:10]
    
    # Average resolution time (for closed tickets)
    avg_resolution_time = None
    closed_with_dates = tickets.objects.filter(
        active_record=True,
        closed=True,
        close_date__isnull=False,
        c_date__isnull=False
    )
    
    if closed_with_dates.exists():
        resolution_times = []
        for ticket in closed_with_dates:
            if ticket.c_date and ticket.close_date:
                delta = ticket.close_date - ticket.c_date
                resolution_times.append(delta.total_seconds() / 3600)  # hours
        
        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
    
    context = {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'closed_tickets': closed_tickets,
        'recent_tickets': recent_tickets,
        'recent_closed': recent_closed,
        'tickets_by_type': list(tickets_by_type),
        'tickets_by_priority': list(tickets_by_priority),
        'tickets_by_org': list(tickets_by_org),
        'avg_resolution_time': avg_resolution_time,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'dashboard/analytics.html', context)


@login_required
def calendar_view(request):
    """Calendar view for tickets with deadlines and scheduling"""
    # Get tickets with show_start dates (scheduled tickets)
    scheduled_tickets = tickets.objects.filter(
        active_record=True,
        show_start__isnull=False
    ).order_by('show_start')
    
    # Get tickets with close dates (recently closed)
    recently_closed = tickets.objects.filter(
        active_record=True,
        closed=True,
        close_date__isnull=False
    ).order_by('-close_date')[:50]
    
    # Get tickets by creation date for timeline
    timeline_tickets = tickets.objects.filter(
        active_record=True
    ).order_by('-c_date')[:100]
    
    context = {
        'scheduled_tickets': scheduled_tickets,
        'recently_closed': recently_closed,
        'timeline_tickets': timeline_tickets,
    }
    
    return render(request, 'dashboard/calendar.html', context)


@login_required
def analytics_data_api(request):
    """API endpoint for analytics data (for AJAX requests)"""
    # Get date range from request
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Daily ticket creation data
    daily_created = []
    daily_closed = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        next_date = date + timedelta(days=1)
        
        created_count = tickets.objects.filter(
            active_record=True,
            c_date__gte=date,
            c_date__lt=next_date
        ).count()
        
        closed_count = tickets.objects.filter(
            active_record=True,
            closed=True,
            close_date__gte=date,
            close_date__lt=next_date
        ).count()
        
        daily_created.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': created_count
        })
        
        daily_closed.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': closed_count
        })
    
    return JsonResponse({
        'daily_created': daily_created,
        'daily_closed': daily_closed,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    })


@login_required
def ticket_timeline_api(request):
    """API endpoint for ticket timeline data"""
    # Get tickets with their key dates
    tickets_data = []
    
    for ticket in tickets.objects.filter(active_record=True).order_by('-c_date')[:50]:
        ticket_data = {
            'id': ticket.id,
            'caption': ticket.caption,
            'created': ticket.c_date.isoformat() if ticket.c_date else None,
            'last_action': ticket.last_action_date.isoformat() if ticket.last_action_date else None,
            'closed': ticket.close_date.isoformat() if ticket.close_date else None,
            'show_start': ticket.show_start.isoformat() if ticket.show_start else None,
            'priority': ticket.priority.name if ticket.priority else None,
            'type': ticket.type.name if ticket.type else None,
            'assigned': ticket.assigned.username if ticket.assigned else None,
            'closed_status': ticket.closed
        }
        tickets_data.append(ticket_data)
    
    return JsonResponse({
        'tickets': tickets_data
    })


# Gantt Chart API endpoints
@login_required
@api_view(['GET'])
def gantt_data_list(request, offset=0):
    """API endpoint for Gantt chart data"""
    if request.method == 'GET':
        tasks = Task.objects.all()
        links = Link.objects.all()
        taskData = TaskSerializer(tasks, many=True)
        linkData = LinkSerializer(links, many=True)
        return Response({
            "tasks": taskData.data,
            "links": linkData.data
        })


@login_required
@api_view(['POST'])
def gantt_task_add(request):
    """API endpoint to add a new task"""
    if request.method == 'POST':
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save()
            return JsonResponse({'action': 'inserted', 'tid': task.id})
        return JsonResponse({'action': 'error'})


@login_required
@api_view(['PUT', 'DELETE'])
def gantt_task_update(request, pk):
    """API endpoint to update or delete a task"""
    try:
        task = Task.objects.get(pk=pk)
    except Task.DoesNotExist:
        return JsonResponse({'action': 'error2'})

    # Prevent modification of readonly tasks
    if task.readonly:
        return JsonResponse({
            'action': 'error',
            'message': 'Cannot modify readonly task'
        }, status=403)

    if request.method == 'PUT':
        serializer = TaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'action': 'updated'})
        return JsonResponse({'action': 'error'})

    if request.method == 'DELETE':
        task.delete()
        return JsonResponse({'action': 'deleted'})


@login_required
@api_view(['POST'])
def gantt_link_add(request):
    """API endpoint to add a new link"""
    if request.method == 'POST':
        serializer = LinkSerializer(data=request.data)
        if serializer.is_valid():
            link = serializer.save()
            return JsonResponse({'action': 'inserted', 'tid': link.id})
        return JsonResponse({'action': 'error'})


@login_required
@api_view(['PUT', 'DELETE'])
def gantt_link_update(request, pk):
    """API endpoint to update or delete a link"""
    try:
        link = Link.objects.get(pk=pk)
    except Link.DoesNotExist:
        return JsonResponse({'action': 'error'})

    if request.method == 'PUT':
        serializer = LinkSerializer(link, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'action': 'updated'})
        return JsonResponse({'action': 'error'})

    if request.method == 'DELETE':
        link.delete()
        return JsonResponse({'action': 'deleted'})
