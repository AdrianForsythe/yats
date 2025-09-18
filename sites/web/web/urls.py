from django.urls import include, re_path
from django.contrib import admin

admin.autodiscover()

handler500 = 'yats.errors.server_error'

urlpatterns = [
    re_path(r'^', include('yats.check.urls')),
    re_path(r'^', include('yats.urls')),
    re_path(r'^admin/', admin.site.urls),
    # No CalDAV URLs
]