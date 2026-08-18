from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path('', include('core.urls')),
    path('cuentas/', include('accounts.urls')),
    path('aprender/', include('learning.urls')),
    path('actividades/', include('activities.urls')),
    path('juegos/', include('games.urls')),
    path('lecturas/', include('readings.urls')),
    path('progreso/', include('progress.urls')),
    path('panel/', include('dashboard.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
