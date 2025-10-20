# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import Task, Link


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Gantt chart tasks"""
    start_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    end_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M')

    class Meta:
        model = Task
        fields = ('id', 'text', 'start_date', 'end_date', 'duration', 'progress', 'parent', 'sort_order', 'color', 'readonly', 'source', 'external_id')


class LinkSerializer(serializers.ModelSerializer):
    """Serializer for Gantt chart links"""
    
    class Meta:
        model = Link
        fields = ('id', 'source', 'target', 'type', 'lag')
