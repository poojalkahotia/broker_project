# brokerapp/context_processors.py
def current_org(request):
    """
    Expose request.current_org to templates.
    Works with SingleOrgMiddleware which sets request.current_org
    to Organization.objects.first() for every request.
    """
    return {"current_org": getattr(request, "current_org", None)}
