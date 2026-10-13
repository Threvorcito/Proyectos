import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parent.parent

PROBE = (
    'import json, mysite.settings as s; '
    'print(json.dumps({"debug": s.DEBUG, "session_secure": s.SESSION_COOKIE_SECURE, '
    '"csrf_secure": s.CSRF_COOKIE_SECURE, "ssl_redirect": s.SECURE_SSL_REDIRECT, '
    '"hsts": s.SECURE_HSTS_SECONDS, "proxy": s.SECURE_PROXY_SSL_HEADER}))'
)


def load_settings(**overrides):
    """Import mysite.settings in a fresh interpreter with a controlled environment."""
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(('DJANGO_', 'SECURE_'))
    }
    # Point the .env loader at a missing file so the local .env cannot leak in.
    env['DJANGO_ENV_FILE'] = str(BASE_DIR / 'does-not-exist.env')
    env.update(overrides)
    return subprocess.run(
        [sys.executable, '-c', PROBE],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


class SettingsDefaultsTests(SimpleTestCase):
    def test_debug_defaults_to_false_and_requires_secret_key(self):
        result = load_settings()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ImproperlyConfigured', result.stderr)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)

    def test_production_settings_are_secure_by_default(self):
        result = load_settings(DJANGO_SECRET_KEY='x' * 50)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"debug": false', result.stdout)
        self.assertIn('"session_secure": true', result.stdout)
        self.assertIn('"csrf_secure": true', result.stdout)
        self.assertIn('"ssl_redirect": true', result.stdout)
        self.assertIn('"hsts": 31536000', result.stdout)
        self.assertIn('"proxy": null', result.stdout)

    def test_debug_mode_keeps_insecure_dev_fallback(self):
        result = load_settings(DJANGO_DEBUG='True')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"debug": true', result.stdout)
        self.assertIn('"session_secure": false', result.stdout)
        self.assertIn('"ssl_redirect": false', result.stdout)

    def test_proxy_ssl_header_is_opt_in(self):
        result = load_settings(DJANGO_SECRET_KEY='x' * 50, DJANGO_SECURE_PROXY_SSL_HEADER='True')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"proxy": ["HTTP_X_FORWARDED_PROTO", "https"]', result.stdout)
