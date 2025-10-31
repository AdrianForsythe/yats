# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone

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
    external_id = models.CharField(max_length=255, default='')
    readonly = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default='ticket')

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


class Runfolder(models.Model):
    """Model for tracking sequencing runfolders and their status"""
    STATUS_CHOICES = [
        ('initializing', 'Initializing'),
        ('sequencing', 'Sequencing'),
        ('finished', 'Finished'),
        ('copying', 'Copying'),
        ('completed', 'Completed'),
    ]

    runfolder_name = models.CharField(max_length=255, unique=True, help_text="Unique identifier for the runfolder")
    runfolder_path = models.CharField(max_length=500, unique=True, help_text="Full path to the runfolder directory")

    # Run metadata
    instrument_id = models.CharField(max_length=255, null=True, blank=True)
    flowcell_id = models.CharField(max_length=255, null=True, blank=True)
    run_date = models.DateField(null=True, blank=True)
    run_start_time = models.DateTimeField(null=True, blank=True)
    run_end_time = models.DateTimeField(null=True, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initializing')

    # Completion details
    completion_status = models.CharField(max_length=255, null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)

    # Link to ticket (sequencing project)
    ticket = models.ForeignKey('yats.tickets', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='runfolders', help_text="Associated sequencing ticket")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Runfolder'
        verbose_name_plural = 'Runfolders'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.runfolder_name} - {self.status}"

    def update_status_from_files(self):
        """Update status based on file presence in runfolder directory"""
        import os

        if not os.path.exists(self.runfolder_path):
            self.status = 'initializing'
            return

        # Check for key files
        run_completion_status_path = os.path.join(self.runfolder_path, "RunCompletionStatus.xml")
        sequence_complete_path = os.path.join(self.runfolder_path, "SequenceComplete.txt")
        copy_complete_path = os.path.join(self.runfolder_path, "CopyComplete.txt")
        rta_complete_path = os.path.join(self.runfolder_path, "RTAComplete.txt")
        run_parameters_path = os.path.join(self.runfolder_path, "RunParameters.xml")

        has_run_completion = os.path.exists(run_completion_status_path)
        has_sequence_complete = os.path.exists(sequence_complete_path)
        has_copy_complete = os.path.exists(copy_complete_path)
        has_rta_complete = os.path.exists(rta_complete_path)
        has_run_parameters = os.path.exists(run_parameters_path)

        # Determine status based on file presence
        if has_run_parameters and has_copy_complete and has_rta_complete and (has_run_completion or has_sequence_complete):
            self.status = 'finished'
        elif has_run_parameters and has_copy_complete and has_rta_complete:
            self.status = 'sequencing'
        elif has_run_parameters:
            self.status = 'copying'
        else:
            self.status = 'initializing'

    def parse_run_info(self):
        """Parse RunInfo.xml file"""
        import os
        import xml.etree.ElementTree as ET

        xml_path = os.path.join(self.runfolder_path, "RunInfo.xml")
        if not os.path.exists(xml_path):
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            run = root.find("Run")
            if run is None:
                return None

            return {
                "run_id": run.get("Id"),
                "run_number": run.get("Number"),
                "flowcell": run.find("Flowcell").text if run.find("Flowcell") is not None else None,
                "instrument": run.find("Instrument").text if run.find("Instrument") is not None else None,
                "date": run.find("Date").text if run.find("Date") is not None else None
            }
        except (ET.ParseError, AttributeError) as e:
            print(f"Error parsing RunInfo.xml: {e}")
            return None

    def parse_run_parameters(self):
        """Parse RunParameters.xml file"""
        import os
        import xml.etree.ElementTree as ET

        xml_path = os.path.join(self.runfolder_path, "RunParameters.xml")
        if not os.path.exists(xml_path):
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            return {
                "run_start_time": root.find("RunStartTime").text if root.find("RunStartTime") is not None else None,
                "run_end_time": root.find("RunEndTime").text if root.find("RunEndTime") is not None else None
            }
        except (ET.ParseError, AttributeError) as e:
            print(f"Error parsing RunParameters.xml: {e}")
            return None

    def parse_completion_status(self):
        """Parse RunCompletionStatus.xml file or use SequenceComplete.txt"""
        import os
        import xml.etree.ElementTree as ET
        from datetime import datetime

        # First try RunCompletionStatus.xml
        xml_path = os.path.join(self.runfolder_path, "RunCompletionStatus.xml")
        if os.path.exists(xml_path):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()

                completion_status = root.find("CompletionStatus")
                completion_time = root.find("CompletionTime")

                return {
                    "completion_status": completion_status.text if completion_status is not None else None,
                    "completion_time": completion_time.text if completion_time is not None else None
                }
            except (ET.ParseError, AttributeError) as e:
                print(f"Error parsing RunCompletionStatus.xml: {e}")

        # If RunCompletionStatus.xml doesn't exist or failed to parse,
        # try SequenceComplete.txt modification time
        sequence_complete_path = os.path.join(self.runfolder_path, "SequenceComplete.txt")
        if os.path.exists(sequence_complete_path):
            try:
                # Use file modification time as completion time
                mtime = os.path.getmtime(sequence_complete_path)
                completion_datetime = datetime.fromtimestamp(mtime)

                return {
                    "completion_status": "Completed",
                    "completion_time": completion_datetime.isoformat()
                }
            except Exception as e:
                print(f"Error getting SequenceComplete.txt modification time: {e}")

        return None
