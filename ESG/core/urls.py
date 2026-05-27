from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ingestion/', include('ingestion.urls')),
    path('api/emissions/', include('emissions.urls')),
]