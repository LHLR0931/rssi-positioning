# backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def ping(request):
    print(">>> PING", request.META.get("REMOTE_ADDR"))
    return JsonResponse({"ok": True})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ping/', ping),          
    path('api/', include('api.urls')),
]
