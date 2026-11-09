"""Одноразовые коды: выдача, проверка, лимиты. Всё состояние — в Redis."""
import hashlib
import hmac
import secrets
import time

from django.conf import settings
from django.core.cache import cache


class CooldownError(Exception):
    """Код уже отправлялся недавно — нужно подождать."""

    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f"Повторная отправка через {retry_after} с")


def normalize_email(email):
    return email.strip().lower()


def _code_key(email):
    return f"otp:code:{email}"


def _attempts_key(email):
    return f"otp:attempts:{email}"


def _cooldown_key(email):
    return f"otp:cooldown:{email}"


def _hash(email, code):
    # В Redis лежит не сам код, а HMAC от него: утечка дампа не даёт войти
    msg = f"{email}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def issue_code(email):
    """Генерирует 6-значный код и сохраняет его хэш. Возвращает сам код для отправки.

    cache.add атомарен: два параллельных запроса не получат два кода.
    """
    email = normalize_email(email)
    cooldown = settings.OTP_RESEND_COOLDOWN
    if not cache.add(_cooldown_key(email), time.time() + cooldown, cooldown):
        until = cache.get(_cooldown_key(email)) or time.time()
        raise CooldownError(max(1, int(until - time.time())))

    code = f"{secrets.randbelow(10 ** 6):06d}"
    ttl = settings.OTP_CODE_TTL
    cache.set(_code_key(email), _hash(email, code), ttl)
    # Новый код — новые попытки
    cache.set(_attempts_key(email), 0, ttl)
    return code


def verify_code(email, code):
    """True, если код верный. Код одноразовый, после OTP_MAX_ATTEMPTS ошибок сгорает."""
    email = normalize_email(email)
    stored = cache.get(_code_key(email))
    if stored is None:
        return False

    try:
        # incr атомарен в Redis — параллельный перебор не обойдёт лимит
        attempts = cache.incr(_attempts_key(email))
    except ValueError:
        return False
    if attempts > settings.OTP_MAX_ATTEMPTS:
        _burn(email)
        return False

    if not hmac.compare_digest(stored, _hash(email, code)):
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            _burn(email)
        return False

    _burn(email)
    return True


def _burn(email):
    cache.delete_many([_code_key(email), _attempts_key(email)])
