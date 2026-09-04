from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# In dev mode, append BrowsableAPIRenderer for testing in browser
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)
