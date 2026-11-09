import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.otp.services import issue_code, verify_code


def code_from_mail():
    return re.search(r"\d{6}", mail.outbox[-1].body).group()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LoginFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def request_code(self, email='Dev@Example.com'):
        return self.api.post('/api/v1/auth/code/', {'email': email}, format='json')

    def verify(self, code, email='dev@example.com'):
        return self.api.post('/api/v1/auth/verify/', {'email': email, 'code': code}, format='json')

    def test_full_login_creates_user_and_token(self):
        res = self.request_code()
        self.assertEqual(res.status_code, 202)
        self.assertEqual(mail.outbox[0].to, ['dev@example.com'])

        res = self.verify(code_from_mail())
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['is_new'])

        self.api.credentials(HTTP_AUTHORIZATION=f"Token {res.data['token']}")
        me = self.api.get('/api/v1/auth/me/')
        self.assertEqual(me.data['email'], 'dev@example.com')

    def test_second_login_reuses_account(self):
        self.request_code()
        first = self.verify(code_from_mail()).data
        cache.clear()  # сбрасываем кулдаун
        self.request_code()
        second = self.verify(code_from_mail()).data
        self.assertFalse(second['is_new'])
        self.assertEqual(first['token'], second['token'])

    def test_code_is_single_use(self):
        self.request_code()
        code = code_from_mail()
        self.assertEqual(self.verify(code).status_code, 200)
        self.assertEqual(self.verify(code).status_code, 400)

    def test_resend_cooldown(self):
        self.request_code()
        res = self.request_code()
        self.assertEqual(res.status_code, 429)
        self.assertGreater(int(res['Retry-After']), 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_wrong_code_format(self):
        self.assertEqual(self.verify('12ab').status_code, 400)

    def test_me_requires_token(self):
        self.assertEqual(self.api.get('/api/v1/auth/me/').status_code, 401)


@override_settings(OTP_MAX_ATTEMPTS=3)
class VerifyCodeTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_code_burns_after_max_attempts(self):
        code = issue_code('a@b.com')
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(3):
            self.assertFalse(verify_code('a@b.com', wrong))
        # Даже верный код уже не подходит — перебор остановлен
        self.assertFalse(verify_code('a@b.com', code))

    def test_code_stored_hashed(self):
        code = issue_code('a@b.com')
        self.assertNotEqual(cache.get('otp:code:a@b.com'), code)

    def test_email_case_insensitive(self):
        code = issue_code('A@B.com')
        self.assertTrue(verify_code(' a@b.COM ', code))

    def test_unknown_email(self):
        self.assertFalse(verify_code('nobody@b.com', '123456'))
