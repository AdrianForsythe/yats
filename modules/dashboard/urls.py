# -*- coding: utf-8 -*-
from django.urls import re_path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    re_path(r'^$', views.dashboard_home, name='dashboard_home'),
    re_path(r'^analytics/$', views.analytics_overview, name='analytics'),
    re_path(r'^sequencing/$', views.sequencing_analytics, name='sequencing_analytics'),
    re_path(r'^calendar/$', views.calendar_view, name='calendar'),
    re_path(r'^gantt/$', views.gantt_view, name='gantt'),
    re_path(r'^api/analytics/$', views.analytics_data_api, name='analytics_api'),
    re_path(r'^api/timeline/$', views.ticket_timeline_api, name='timeline_api'),
    # Gantt chart API endpoints
    re_path(r'^gantt/data/task/(?P<pk>[0-9]+)$', views.gantt_task_update),
    re_path(r'^gantt/data/task', views.gantt_task_add),
    re_path(r'^gantt/data/link/(?P<pk>[0-9]+)$', views.gantt_link_update),
    re_path(r'^gantt/data/link', views.gantt_link_add),
    re_path(r'^gantt/data/(.*)$', views.gantt_data_list),
]

urlpatterns = format_suffix_patterns(urlpatterns)
