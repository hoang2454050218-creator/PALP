import os

from django.core.wsgi import get_wsgi_application

if "DJANGO_SETTINGS_MODULE" not in os.environ:
    raise RuntimeError(
        "DJANGO_SETTINGS_MODULE is not set. Set it explicitly (e.g. palp.settings.production) before deploying."
    )

application = get_wsgi_application()
