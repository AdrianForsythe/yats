from django.contrib import admin
from .models import Task, Link, Runfolder

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('text', 'start_date', 'end_date', 'progress', 'source', 'external_id')
    list_filter = ('source', 'readonly')
    search_fields = ('text', 'external_id')

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('source', 'target', 'type', 'lag')

@admin.register(Runfolder)
class RunfolderAdmin(admin.ModelAdmin):
    list_display = ('runfolder_name', 'status', 'instrument_id', 'flowcell_id', 'run_date', 'created_at', 'ticket')
    list_filter = ('status', 'instrument_id', 'created_at', 'updated_at')
    search_fields = ('runfolder_name', 'instrument_id', 'flowcell_id', 'ticket__caption')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('ticket',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ticket')
