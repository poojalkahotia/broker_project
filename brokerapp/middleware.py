from .models import Membership

class CurrentOrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        request.current_org = None
        if request.user.is_authenticated:
            org_id = request.session.get("current_org_id")
            if org_id:
                try:
                    request.current_org = Membership.objects.select_related("org").get(
                        user=request.user, org_id=org_id
                    ).org
                except Membership.DoesNotExist:
                    request.session.pop("current_org_id", None)
        return self.get_response(request)
