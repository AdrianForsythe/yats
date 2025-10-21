#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import pyodbc
import json

from yats.shortcuts import get_ticket_model
from yats.models import organisation
# Import with the correct module path
from dashboard.views import get_hades_connection


class Command(BaseCommand):
    help = 'Create YATS tickets for ongoing sequencing projects from HADES2017'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not save tickets, just print what would be done')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        conn = get_hades_connection()
        if not conn:
            raise CommandError('Could not connect to sequencing database')

        cursor = conn.cursor()

        # StatusID IN (2,3,4,7,10) used by dashboard for "ongoing" states
        query = """
        SELECT RequestID, CustomerName, 
               COALESCE(ApplicationName, 'Unknown') as ApplicationName, 
               StatusDescription, ReceiveDate
        FROM [HADES2017].[dbo].[tblD00Requests]
          LEFT JOIN [HADES2017].[dbo].[tbl_Customers]
            ON [HADES2017].[dbo].[tblD00Requests].CustomerID = [HADES2017].[dbo].[tbl_Customers].CustomerID
          LEFT JOIN [HADES2017].[dbo].[tblD00Status]
            ON [HADES2017].[dbo].[tblD00Requests].StatusID = [HADES2017].[dbo].[tblD00Status].StatusID
          LEFT JOIN [HADES2017].[dbo].[tblD00Applications]
            ON [HADES2017].[dbo].[tblD00Requests].ApplicationID = [HADES2017].[dbo].[tblD00Applications].ApplicationID
        WHERE [HADES2017].[dbo].[tblD00Requests].StatusID IN (2,3,4,7,10)
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        Ticket = get_ticket_model()
        User = get_user_model()

        # determine system user for creating tickets
        system_user = None
        if hasattr(settings, 'SEQUENCING_TICKET_USER') and settings.SEQUENCING_TICKET_USER:
            try:
                system_user = User.objects.get(username=settings.SEQUENCING_TICKET_USER)
            except User.DoesNotExist:
                system_user = None

        if not system_user:
            try:
                system_user = User.objects.get(pk=1)
            except Exception:
                system_user = User.objects.first()

        if not system_user:
            raise CommandError('No user available to assign as creator for tickets')

        created = 0
        for row in rows:
            request_id = row[0]
            customer_name = row[1] or 'Unknown'
            application = row[2] or ''
            status = row[3] or ''
            receive_date = timezone.make_aware(row[4]) if row[4] else timezone.now()

            # Find or create an organization for this customer
            org = organisation.objects.filter(name__icontains=customer_name).first()
            if not org and not dry_run:
                org = organisation()
                org.name = customer_name
                org.save(user=system_user)
                self.stdout.write(f"Created organization for customer: {customer_name}")

            caption = f"Sequencing project {request_id} ({application})"
            description = (
                f"Sequencing request {request_id}\n"
                f"Customer: {customer_name}\n"
                f"Application: {application}\n"
                f"Status: {status}\n"
                f"Received: {receive_date}"
            )

            # avoid duplicates: look for tickets with a matching uuid or caption containing request id
            exists = Ticket.objects.filter(uuid__icontains=str(request_id)).first() or Ticket.objects.filter(caption__icontains=str(request_id)).first()
            if exists:
                self.stdout.write(f"Skipping existing ticket for request {request_id} (ticket {exists.pk})")
                continue

            tic = Ticket()
            tic.caption = caption
            tic.description = description
            tic.priority = None
            tic.customer = org  # Set the organization we found/created
            tic.assigned = None
            tic.resolution = None
            tic.closed = False
            tic.state = None
            tic.keep_it_simple = True
            tic.uuid = f"sequencing:{request_id}"
            tic.hasAttachments = False
            tic.hasComments = False
            tic.show_start = receive_date

            if dry_run:
                self.stdout.write(f"Would create ticket: {caption}")
            else:
                tic.save(user=system_user)
                created += 1
                self.stdout.write(f"Created ticket {tic.pk} for sequencing request {request_id}")

        conn.close()
        self.stdout.write(self.style.SUCCESS(f'Done. Created {created} tickets'))