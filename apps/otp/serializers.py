from rest_framework import serializers

from .services import normalize_email


class RequestCodeSerializer(serializers.Serializer):
    # 150 — лимит username, email используется как логин
    email = serializers.EmailField(max_length=150)

    def validate_email(self, value):
        return normalize_email(value)


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=150)
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Код — 6 цифр."})

    def validate_email(self, value):
        return normalize_email(value)


class CodeSentSerializer(serializers.Serializer):
    detail = serializers.CharField()
    resend_in = serializers.IntegerField(help_text="Через сколько секунд можно запросить снова")


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    is_new = serializers.BooleanField(help_text="Аккаунт создан этим входом")


class MeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    date_joined = serializers.DateTimeField()
