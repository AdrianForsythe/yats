from django.urls import include, re_path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

admin.autodiscover()

handler500 = 'yats.errors.server_error'

urlpatterns = [
    re_path(r'^', include('yats.check.urls')),
    re_path(r'^', include('yats.urls')),
    re_path(r'^dashboard/', include('dashboard.urls')),  # Add dashboard URLs
    re_path(r'^admin/', admin.site.urls),
    # No CalDAV URLs
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)