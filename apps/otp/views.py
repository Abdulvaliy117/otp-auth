from django.conf import settings
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import (CodeSentSerializer, MeSerializer, RequestCodeSerializer,
                          TokenSerializer, VerifyCodeSerializer)
from .services import CooldownError, issue_code, verify_code
from .tasks import send_code_email

User = get_user_model()


class OtpThrottle(AnonRateThrottle):
    scope = "otp"


class RequestCodeView(APIView):
    """POST /api/v1/auth/code/ — отправить код на email.

    Повторно — не раньше OTP_RESEND_COOLDOWN секунд, иначе 429.
    Ответ одинаковый для новых и существующих email — по нему нельзя узнать, есть ли аккаунт.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OtpThrottle]

    @swagger_auto_schema(request_body=RequestCodeSerializer, responses={202: CodeSentSerializer})
    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            code = issue_code(email)
        except CooldownError as e:
            return Response({"detail": str(e), "resend_in": e.retry_after},
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={"Retry-After": str(e.retry_after)})

        send_code_email.delay(email, code)
        return Response({"detail": "Код отправлен", "resend_in": settings.OTP_RESEND_COOLDOWN},
                        status=status.HTTP_202_ACCEPTED)


class VerifyCodeView(APIView):
    """POST /api/v1/auth/verify/ — вход по коду. Нет аккаунта — создаётся."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OtpThrottle]

    @swagger_auto_schema(request_body=VerifyCodeSerializer, responses={200: TokenSerializer})
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if not verify_code(email, serializer.validated_data["code"]):
            return Response({"detail": "Неверный или просроченный код"},
                            status=status.HTTP_400_BAD_REQUEST)

        user, is_new = User.objects.get_or_create(username=email, defaults={"email": email})
        if is_new:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "is_new": is_new})


class MeView(APIView):
    """GET /api/v1/auth/me/ — кто я. Для проверки токена."""

    @swagger_auto_schema(responses={200: MeSerializer})
    def get(self, request):
        return Response(MeSerializer(request.user).data)
