# brokerapp/middleware.py
from django.conf import settings
from .models import Organization

class SingleOrgMiddleware:
    """
    Single-company mode:
    - Always use one shared Organization record
    - Auto-create it if not found, using DEFAULT_ORG_NAME from settings
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ensure default org exists
        org, created = Organization.objects.get_or_create(
            name=settings.DEFAULT_ORG_NAME
        )

        # Attach to request so whole app uses same org
        request.current_org = org

        return self.get_response(request)
