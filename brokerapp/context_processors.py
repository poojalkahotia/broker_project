def current_org(request):
    return {"CURRENT_ORG": getattr(request, "current_org", None)}
