# -*- coding: utf-8 -*-
from django.db import models

class Task(models.Model):
    """Gantt chart task model"""
    id = models.AutoField(primary_key=True, editable=False)
    text = models.CharField(blank=True, max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    duration = models.IntegerField()
    progress = models.FloatField()
    parent = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#4CAF50', help_text='Hex color code for the task')

    class Meta:
        db_table = 'dashboard_task'

    def __str__(self):
        return self.text or f"Task {self.id}"


class Link(models.Model):
    """Gantt chart link model for task dependencies"""
    id = models.AutoField(primary_key=True, editable=False)
    source = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    lag = models.IntegerField(blank=True, default=0)

    class Meta:
        db_table = 'dashboard_link'

    def __str__(self):
        return f"Link {self.source} -> {self.target}"
