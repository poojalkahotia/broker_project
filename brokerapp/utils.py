from functools import wraps
from django.shortcuts import redirect

def require_org(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not getattr(request, "current_org", None):
            return redirect("org_switch")
        return view_func(request, *args, **kwargs)
    return _wrapped
