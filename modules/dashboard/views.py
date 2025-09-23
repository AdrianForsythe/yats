# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from yats.models import tickets, ticket_type, ticket_priority, organisation, ticket_flow
import json


@login_required
def dashboard_home(request):
    """Main dashboard view with analytics overview"""
    context = {
        'page_title': 'Dashboard',
        'breadcrumbs': [{'name': 'Dashboard', 'url': '/dashboard/'}]
    }
    return render(request, 'dashboard/home.html', context)


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
