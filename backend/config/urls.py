from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path
from django.views import View
from django.views.static import serve

from apps.companies.api.public_views import HotspotSettingsAdminView


class SpaIndexView(View):
    """
    Serves the React Single Page Application (SPA) index.html
    for all frontend routes (e.g. /payments, /walled-garden, /entitlements).
    """
    def get(self, request, *args, **kwargs):
        index_file = settings.BASE_DIR.parent / 'frontend' / 'dist' / 'index.html'
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read(), content_type='text/html')
        raise Http404("Frontend index.html not found. Please run 'npm run build' in frontend/.")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('health/', include('apps.core.api.urls')),
        path('accounts/', include('apps.accounts.api.urls')),
        path('companies/', include('apps.companies.api.urls')),
        path('plans/', include('apps.plans.api.urls')),
        path('entitlements/', include('apps.entitlements.api.urls')),
        path('sessions/', include('apps.hotspot_sessions.api.urls')),
        path('hotspots/', include('apps.companies.api.hotspot_urls')),
        path('public/hotspots/', include('apps.companies.api.public_urls')),
        path('settings/hotspot/', HotspotSettingsAdminView.as_view(), name='settings-hotspot'),
        path('', include('apps.vouchers.api.urls')),
        path('', include('apps.notifications.api.urls')),
        path('radius/', include('apps.radius.api.urls')),
        path('locations/', include('apps.locations.api.urls')),
        path('routers/', include('apps.routers.api.urls')),
        path('payments/', include('apps.payments.api.urls')),
        path('public/', include('apps.payments.api.public_urls')),
        path('', include('apps.customers.api.urls')),
    ])),
    # Static assets for built frontend
    re_path(
        r'^assets/(?P<path>.*)$',
        serve,
        {'document_root': str(settings.BASE_DIR.parent / 'frontend' / 'dist' / 'assets')}
    ),
    # Catch-all for React SPA client routes
    re_path(r'^(?!api/|admin/|static/|media/).*$', SpaIndexView.as_view(), name='spa-fallback'),
]
