# -*- coding: utf-8 -*-
from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.dashboard_home, name='dashboard_home'),
    re_path(r'^analytics/$', views.analytics_overview, name='analytics'),
    re_path(r'^sequencing/$', views.sequencing_analytics, name='sequencing_analytics'),
    re_path(r'^calendar/$', views.calendar_view, name='calendar'),
    re_path(r'^api/analytics/$', views.analytics_data_api, name='analytics_api'),
    re_path(r'^api/timeline/$', views.ticket_timeline_api, name='timeline_api'),
]
