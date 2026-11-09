from django.urls import path

from .views import MeView, RequestCodeView, VerifyCodeView

urlpatterns = [
    path('code/', RequestCodeView.as_view(), name='otp-request'),
    path('verify/', VerifyCodeView.as_view(), name='otp-verify'),
    path('me/', MeView.as_view(), name='me'),
]
