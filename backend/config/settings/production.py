from .base import *  # noqa: F403

DEBUG = False

# Production security controls
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# FreeRADIUS connects to Gunicorn over plain HTTP on loopback (127.0.0.1:8090).
# Exclude RADIUS API endpoints from SSL redirect so FreeRADIUS rlm_rest gets direct JSON responses.
# Nginx already handles SSL termination and HTTP->HTTPS redirection for external users.
SECURE_REDIRECT_EXEMPT = [r'^api/v1/radius/']
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['https://wifi.swahilicode.tech'])  # noqa: F405
