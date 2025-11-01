from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from .forms import (
    OrganizationCreateForm, OrganizationUpdateForm,
    EmployeeCreateForm, EmployeeUpdateForm, OrgSwitchForm
)
from .models import Organization, Membership




@login_required
def org_create(request):
    if request.method == "POST":
        form = OrganizationCreateForm(request.POST)
        if form.is_valid():
            org = form.save(commit=False)
            org.owner = request.user
            org.save()
            Membership.objects.create(org=org, user=request.user, role=Membership.Role.OWNER)
            request.session["current_org_id"] = org.id
            messages.success(request, "Organization created.")
            return redirect("dashboard")
    else:
        form = OrganizationCreateForm()
    return render(request, "brokerapp/org/org_create.html", {"form": form})

@login_required
def org_edit(request):
    if not request.current_org:
        return redirect("org_switch")
    me = Membership.objects.get(org=request.current_org, user=request.user)
    if me.role != Membership.Role.OWNER:
        return HttpResponseForbidden("Only owner can edit organization.")
    if request.method == "POST":
        form = OrganizationUpdateForm(request.POST, instance=request.current_org)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization updated.")
            return redirect("org_switch")
    else:
        form = OrganizationUpdateForm(instance=request.current_org)
    return render(request, "brokerapp/org/org_edit.html", {"form": form})

@login_required
def org_switch(request):
    form = OrgSwitchForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.session["current_org_id"] = form.cleaned_data["org"].id
        messages.success(request, "Switched organization.")
        return redirect(request.GET.get("next") or "dashboard")
    return render(request, "brokerapp/org/org_switch.html", {"form": form})

@login_required
def employee_add(request):
    if not request.current_org:
        return redirect("org_switch")
    my_role = Membership.objects.get(org=request.current_org, user=request.user).role
    if my_role not in [Membership.Role.OWNER, Membership.Role.MANAGER]:
        messages.error(request, "Permission denied.")
        return redirect("dashboard")

    form = EmployeeCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u, created = User.objects.get_or_create(
            username=form.cleaned_data["username"],
            defaults={"email": form.cleaned_data["email"]}
        )
        if created:
            u.set_password(form.cleaned_data["password"]); u.save()
        Membership.objects.get_or_create(
            org=request.current_org, user=u, defaults={"role": form.cleaned_data["role"]}
        )
        messages.success(request, "Employee added.")
        return redirect("employee_list")
    return render(request, "brokerapp/employee/employee_add.html", {"form": form})

@login_required
def employee_edit(request, user_id):
    if not request.current_org:
        return redirect("org_switch")
    myrole = Membership.objects.get(org=request.current_org, user=request.user).role
    if myrole not in [Membership.Role.OWNER, Membership.Role.MANAGER]:
        return HttpResponseForbidden("Permission denied.")
    member = get_object_or_404(Membership, org=request.current_org, user_id=user_id)
    u = member.user
    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST)
        if form.is_valid():
            u.email = form.cleaned_data["email"]
            if form.cleaned_data["new_password"]:
                u.set_password(form.cleaned_data["new_password"])
            u.save()
            member.role = form.cleaned_data["role"]
            member.save()
            messages.success(request, "Employee updated.")
            return redirect("employee_list")
    else:
        form = EmployeeUpdateForm(initial={"email": u.email, "role": member.role})
    return render(request, "brokerapp/employee/employee_edit.html", {"form": form, "emp": u})

@login_required
def employee_remove(request, user_id):
    if not request.current_org:
        return redirect("org_switch")
    myrole = Membership.objects.get(org=request.current_org, user=request.user).role
    if myrole not in [Membership.Role.OWNER, Membership.Role.MANAGER]:
        return HttpResponseForbidden("Permission denied.")
    member = get_object_or_404(Membership, org=request.current_org, user_id=user_id)
    if request.method == "POST":
        member.delete()
        messages.success(request, "Employee removed from organization.")
        return redirect("employee_list")
    return render(request, "brokerapp/employee/employee_confirm_remove.html", {"member": member})





@login_required
def employee_list(request):
    if not request.current_org:
        return redirect("org_switch")
    members = Membership.objects.select_related("user").filter(org=request.current_org)
    return render(request, "brokerapp/employee/employee_list.html", {"members": members})
