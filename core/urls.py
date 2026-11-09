from django.contrib import admin
from django.urls import include, path

from .yasg import urlpatterns as doc_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.otp.urls')),  # запрос кода, вход, профиль
]

urlpatterns += doc_urls
